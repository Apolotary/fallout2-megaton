#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Kit-bashing helpers: find out what the retail maps are built from and reuse pieces of them.

    python3 tools/map_kit.py usage klamall --type walls --top 25      # most-used protos of a map
    python3 tools/map_kit.py where 0x020000E0                         # maps and tiles that use a proto
    python3 tools/map_kit.py where --name 'nuclear|bomb' --type scenery
    python3 tools/map_kit.py extract klamall 15090 17108 -o shack.json --show shack-src.png
    python3 tools/map_kit.py preview shack.json -o shack.png --roofs
    python3 tools/map_kit.py sheet prefabs/*.json -o prefabs/overview    # thumbnails of many prefabs
    python3 tools/map_kit.py stamp shack.json mymap.map --at 20100 -o mymap.map

A *prefab* is a JSON file holding a rectangular block of hexes of one
elevation: the floor and roof squares under it and its objects with their
inventories. In a build script::

    from map_kit import Prefab
    shack = Prefab.extract(MapFile.load("klamall", gf), 15090, 17108)     # two opposite corner tiles
    shack.save("mod/megaton/prefabs/shack.json")
    placed = Prefab.load("mod/megaton/prefabs/shack.json").stamp(m, at=g.tile_at(100, 96))

Rules that keep a stamped copy pixel-identical to the original:

  * The rectangle is a box in (hx, hy), which on screen is the parallelogram
    walls and floor squares follow. A prefab's origin is the hex with even hx
    and even hy at (or one before) the box's low corner, and `stamp(at=...)`
    takes a tile with even hx and even hy: an odd shift would move the hexes
    by a different number of pixels than the squares.
  * Floors are the squares lying under the box's hexes, roofs those plus the
    squares that own them (geometry.floor_square / roof_square); squares
    without a tile are not stored and leave the target untouched.
  * Objects keep art, frame, flags, light and data words, and get fresh ids.
    Left out unless asked for: critters that have a script, exit grids and
    scroll blockers. Script references are recorded by name but only attached
    again with keep_scripts=True. Stairs and ladders lose their destination
    (MapFile.validate() lists them; use MapFile.set_destination).
"""
import argparse
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from f2lib import GameFiles, MapFile, geometry as g, ids  # noqa: E402
from f2lib.map import NO_TILE, PLAYER_ID  # noqa: E402
from contact_sheet import TYPES, flag_text, usage  # noqa: E402
from render_map import MapRenderer, Overlay, load_map, save_png  # noqa: E402

FORMAT = "f2-prefab"
VERSION = 1
DUDE_PID = 0x01000000
# Common object fields a prefab keeps (id, tile, elevation and the script link are assigned on stamping).
KEPT_FIELDS = ("fid", "frame", "rotation", "x", "y", "flags", "light_distance", "light_intensity", "outline")
CRITTER_MODES = ("none", "unscripted", "all")


# ------------------------------------------------------------------ analysis
def proto_usage(gf, game_maps, obj_type):
    """[(count, id, art, name, flags)] of what `game_maps` use, most used first.

    id is the PID, or the tile id for tiles (count is then (floors, roofs)).
    """
    rows = []
    for key, count in usage(game_maps, obj_type).items():
        if obj_type == ids.OBJ_TYPE_TILE:
            path = gf.art.path(ids.make_fid(obj_type, key))
            rows.append((tuple(count), key, os.path.basename(path) if path else "?", "", ""))
            continue
        name = info = art = ""
        if gf.protos.exists(key):
            proto = gf.protos.get(key)
            path = gf.art.path(proto.fid)
            art = os.path.basename(path) if path else "?"
            name = gf.protos.name(key) or ""
            info = flag_text(proto) if obj_type in (ids.OBJ_TYPE_WALL, ids.OBJ_TYPE_SCENERY) else proto.subtype_name
        rows.append((count, key, art, name, info))
    rows.sort(key=lambda row: (-(sum(row[0]) if isinstance(row[0], tuple) else row[0]), row[1]))
    return rows


def find_uses(gf, pids=(), tile_ids=(), map_names=None):
    """Where protos (or floor / roof tile ids) are used: [(map name, elevation, key, [tiles or squares])].

    key is the PID or tile id; for tiles the list holds square numbers.
    """
    pids, tile_ids = set(pids), set(tile_ids)
    found = []
    for path in sorted(gf.glob("maps/*.map")):
        name = os.path.basename(path)[:-4]
        if map_names and name not in map_names:
            continue
        game_map = MapFile.from_bytes(gf.read(path), gf)
        for elevation in sorted(game_map.tiles):
            places = {}
            if pids:
                for obj in game_map.objects[elevation]:
                    if obj.pid in pids:
                        places.setdefault(obj.pid, []).append(obj.tile)
            if tile_ids:
                squares = game_map.tiles[elevation]
                for tile_id in tile_ids:
                    hits = ((squares & 0xFFF) == tile_id) | (((squares >> 16) & 0xFFF) == tile_id)
                    if hits.any():
                        places[tile_id] = hits.nonzero()[0].tolist()
            found += [(name, elevation, key, tiles) for key, tiles in sorted(places.items())]
    return found


# -------------------------------------------------------------------- prefab
def _object_record(game_map, obj, script_names):
    record = {"pid": f"0x{obj.pid & 0xFFFFFFFF:08X}"}
    for field in KEPT_FIELDS:
        value = getattr(obj, field)
        record[field] = f"0x{value & 0xFFFFFFFF:08X}" if field in ("fid", "flags") else value
    record["data"] = dict(zip(obj.data_names, obj.data))
    script = game_map.find_script(obj.sid)
    record["script"] = script_names.name(script.index) if script is not None else None
    if obj.inventory:
        record["inventory"] = [{"quantity": quantity, "object": _object_record(game_map, item, script_names)}
                               for quantity, item in obj.inventory]
    return record


class Prefab:
    """A block of a map: squares and objects relative to an origin hex (see the module text for the rules).

    data keys: format, version, name, source {map, elevation, corners}, origin [hx, hy] (even, even),
    box [dx0, dy0, dx1, dy1] of the hexes relative to the origin, floor / roof [[qx, qy, art name]]
    relative to the origin's square, objects [{at [dx, dy], pid, fid, ..., data {}, script,
    inventory []}], spatial_scripts [{at, radius, script}].
    """

    def __init__(self, data):
        if data.get("format") != FORMAT or data.get("version") != VERSION:
            raise ValueError("not a version 1 f2-prefab")
        self.data = data

    name = property(lambda self: self.data["name"])
    origin = property(lambda self: tuple(self.data["origin"]))
    box = property(lambda self: tuple(self.data["box"]))
    size = property(lambda self: (self.data["box"][2] - self.data["box"][0] + 1,
                                  self.data["box"][3] - self.data["box"][1] + 1))
    objects = property(lambda self: self.data["objects"])

    def __repr__(self):
        return (f"<Prefab {self.name!r} {self.size[0]}x{self.size[1]} hexes, {len(self.objects)} objects, "
                f"{len(self.data['floor'])} floor / {len(self.data['roof'])} roof squares>")

    # ----------------------------------------------------------------- build
    @classmethod
    def extract(cls, game_map, tile_a, tile_b, elevation=0, critters="unscripted", misc=False, name=None):
        """Copy the box of hexes spanned by two corner tiles out of `game_map`.

        critters  'unscripted' (default) keeps only critters without a script, 'all' / 'none'
        misc      also take exit grids and scroll blockers
        """
        if critters not in CRITTER_MODES:
            raise ValueError(f"critters must be one of {CRITTER_MODES}")
        if elevation not in game_map.tiles:
            raise ValueError(f"elevation {elevation} has no squares")
        gf = game_map.gf
        (ax, ay), (bx, by) = g.tile_xy(tile_a), g.tile_xy(tile_b)
        x0, x1, y0, y1 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
        ox, oy = x0 & ~1, y0 & ~1
        inside = set(g.rect(g.tile_at(x0, y0), g.tile_at(x1, y1)))

        tile_names = gf.art_list(ids.OBJ_TYPE_TILE)
        squares = game_map.tiles[elevation]
        floor_squares = {g.floor_square(tile) for tile in inside} - {-1}
        roof_squares = floor_squares | {g.roof_square(tile) for tile in inside}

        def tiles(wanted, shift):
            rows = []
            for square in sorted(wanted):
                tile_id = (int(squares[square]) >> shift) & 0xFFF
                if tile_id != NO_TILE and tile_names.name(tile_id):
                    qx, qy = g.square_xy(square)
                    rows.append([qx - ox // 2, qy - oy // 2, tile_names.name(tile_id)])
            return rows

        objects = []
        for obj in game_map.objects[elevation]:
            if obj.tile not in inside or obj.pid == -1 or obj.pid == DUDE_PID or obj.id >= PLAYER_ID:
                continue
            if obj.obj_type == ids.OBJ_TYPE_MISC and not misc:
                continue
            if obj.obj_type == ids.OBJ_TYPE_CRITTER and (
                    critters == "none" or (critters == "unscripted" and obj.sid != -1)):
                continue
            hx, hy = g.tile_xy(obj.tile)
            record = {"at": [hx - ox, hy - oy]}
            record.update(_object_record(game_map, obj, gf.scripts))
            objects.append(record)
        spatial = []
        for script in game_map.scripts(ids.SCRIPT_TYPE_SPATIAL):
            if script.elevation == elevation and script.tile in inside:
                hx, hy = g.tile_xy(script.tile)
                spatial.append({"at": [hx - ox, hy - oy], "radius": script.radius,
                                "script": gf.scripts.name(script.index)})
        return cls({
            "format": FORMAT, "version": VERSION,
            "name": name or f"{game_map.base_name}-{g.tile_at(x0, y0)}-{g.tile_at(x1, y1)}",
            "source": {"map": game_map.base_name, "elevation": elevation,
                       "corners": [g.tile_at(x0, y0), g.tile_at(x1, y1)]},
            "origin": [ox, oy], "box": [x0 - ox, y0 - oy, x1 - ox, y1 - oy],
            "floor": tiles(floor_squares, 0), "roof": tiles(roof_squares, 16),
            "objects": objects, "spatial_scripts": spatial,
        })

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls(json.load(f))

    def save(self, path):
        """Write JSON with one square / object per line, so prefabs diff and grep well."""
        parts = []
        for key, value in self.data.items():
            if isinstance(value, list) and value and isinstance(value[0], (list, dict)):
                rows = ",\n  ".join(json.dumps(row) for row in value)
                parts.append(f' {json.dumps(key)}: [\n  {rows}\n ]')
            else:
                parts.append(f" {json.dumps(key)}: {json.dumps(value)}")
        with open(path, "w") as f:
            f.write("{\n" + ",\n".join(parts) + "\n}\n")

    # ----------------------------------------------------------------- stamp
    def tiles_at(self, at=None):
        """Hexes the prefab's box covers when its origin is put on `at` (default: where it came from)."""
        ax, ay = self._anchor(at)
        dx0, dy0, dx1, dy1 = self.box
        return g.rect(g.tile_at(ax + dx0, ay + dy0), g.tile_at(ax + dx1, ay + dy1))

    def _anchor(self, at):
        ax, ay = self.origin if at is None else g.tile_xy(at)
        if ax & 1 or ay & 1:
            raise ValueError(f"stamp position (hx {ax}, hy {ay}) must have even hx and even hy, "
                             f"e.g. tile {g.tile_at(ax & ~1, ay & ~1)}")
        if ax + self.box[2] >= g.HEX_WIDTH or ay + self.box[3] >= g.HEX_HEIGHT:
            raise ValueError("the prefab does not fit on the grid at that position")
        return ax, ay

    def _place(self, game_map, record, tile, elevation, owner=None, quantity=1):
        fields = {}
        for field in KEPT_FIELDS:
            value = record[field]
            fields[field] = ids.s32(int(value, 16)) if isinstance(value, str) else value
        rotation = fields.pop("rotation")
        pid = int(record["pid"], 16)
        if owner is None:
            obj = game_map.add_object(pid, tile, elevation, rotation, **fields)
        else:
            obj = game_map.add_item(owner, pid, quantity, **fields)
            obj.rotation = rotation
        for word, value in record["data"].items():
            # Destinations of stairs and ladders point into the source map: they keep the "unset"
            # values add_object gave them. Words the target's layout lacks (older map version) are dropped.
            if word in obj.data_names and word not in ("dest_built_tile", "dest_map"):
                obj[word] = value
        if "dest_built_tile" in obj.data_names:
            obj["dest_built_tile"] = -1
        for entry in record.get("inventory", ()):
            self._place(game_map, entry["object"], -1, elevation, owner=obj, quantity=entry["quantity"])
        return obj

    def stamp(self, game_map, at=None, elevation=0, keep_scripts=False, floors=True, roofs=True, objects=True,
              clear=False):
        """Copy the prefab into `game_map` with its origin on tile `at`; returns the new top-level objects.

        at            tile with even hx and even hy (default: the position in the source map)
        keep_scripts  attach the recorded scripts again (they must be in the target's scripts.lst)
                      and re-create spatial scripts
        clear         first remove the objects standing on the hexes the prefab covers
        """
        ax, ay = self._anchor(at)
        if elevation not in game_map.tiles:
            game_map.add_elevation(elevation)
        if clear:
            covered = set(self.tiles_at(at))
            for obj in [o for o in game_map.objects[elevation] if o.tile in covered]:
                game_map.remove_object(obj)
        for wanted, rows, setter in ((floors, self.data["floor"], game_map.set_floor),
                                     (roofs, self.data["roof"], game_map.set_roof)):
            for qx, qy, art in rows if wanted else ():
                setter(ax // 2 + qx, ay // 2 + qy, art, elevation)
        placed = []
        if objects:
            for record in self.objects:
                tile = g.tile_at(ax + record["at"][0], ay + record["at"][1])
                obj = self._place(game_map, record, tile, elevation)
                if keep_scripts and record.get("script"):
                    game_map.attach_script(obj, record["script"])
                placed.append(obj)
        if keep_scripts:
            for entry in self.data["spatial_scripts"]:
                tile = g.tile_at(ax + entry["at"][0], ay + entry["at"][1])
                game_map.add_spatial_script(entry["script"], tile, elevation, entry["radius"])
        return placed

    # --------------------------------------------------------------- preview
    def to_map(self, gamefiles, at=None, keep_scripts=False):
        """A blank one-elevation map holding just this prefab (for previews and tests)."""
        game_map = MapFile.new("prefab", gamefiles)
        self.stamp(game_map, at, keep_scripts=keep_scripts)
        if at is None:
            at = g.tile_at(*self.origin)
        game_map.entering_tile = at
        return game_map

    def render(self, gamefiles, roofs=False, renderer=None, **options):
        """`render_map.Scene` of the prefab alone, at its source position (tile numbers match the source map)."""
        renderer = renderer or MapRenderer(gamefiles)
        return renderer.render(self.to_map(gamefiles), 0, roofs=roofs, **options)


def preview_sheet(gamefiles, prefabs, out_prefix, roofs=True, cell=(380, 300), sheet_size=(1540, 1400)):
    """Thumbnails of several prefabs with name, size and source: <out_prefix>-01.png ...; returns the files."""
    from PIL import Image, ImageDraw
    from render_map import load_font
    font = load_font(11)
    renderer = MapRenderer(gamefiles)
    columns = max(1, sheet_size[0] // cell[0])
    rows = max(1, sheet_size[1] // (cell[1] + 44))
    files = []
    for start in range(0, len(prefabs), columns * rows):
        chunk = prefabs[start:start + columns * rows]
        height = -(-len(chunk) // columns) * (cell[1] + 44)
        sheet = Image.new("RGB", (columns * cell[0] + 1, height + 1), (40, 40, 46))
        draw = ImageDraw.Draw(sheet)
        for slot, prefab in enumerate(chunk):
            x, y = slot % columns * cell[0], slot // columns * (cell[1] + 44)
            draw.rectangle((x, y, x + cell[0], y + cell[1] + 44), outline=(112, 112, 124))
            picture = prefab.render(gamefiles, roofs=roofs, renderer=renderer).image()
            scale = min(1.0, (cell[0] - 8) / picture.width, (cell[1] - 8) / picture.height)
            if scale < 1:
                picture = picture.resize((int(picture.width * scale), int(picture.height * scale)), Image.LANCZOS)
            sheet.paste(picture, (x + (cell[0] - picture.width) // 2, y + 4 + (cell[1] - 8 - picture.height) // 2))
            source = prefab.data["source"]
            lines = (prefab.name,
                     f"{prefab.size[0]}x{prefab.size[1]} hexes  {len(prefab.objects)} objects  "
                     f"{len(prefab.data['floor'])}F {len(prefab.data['roof'])}R squares",
                     f"{source['map']} e{source['elevation']} tiles {source['corners'][0]}..{source['corners'][1]}"
                     f"  shown at {scale:.2f}x")
            for n, (text, colour) in enumerate(zip(lines, ((255, 225, 90), (240, 240, 240), (196, 196, 206)))):
                draw.text((x + 5, y + cell[1] + 2 + 13 * n), text, font=font, fill=colour)
        files.append(f"{out_prefix}-{len(files) + 1:02d}.png")
        sheet.save(files[-1])
    return files


# ----------------------------------------------------------------------- CLI
def _type(name):
    for label, obj_type in TYPES.items():
        if name.lower() in (label, ids.TYPE_NAMES[obj_type]):
            return obj_type
    raise argparse.ArgumentTypeError(f"unknown type {name!r} (one of {', '.join(sorted(TYPES))})")


def _count(count):
    return " ".join(f"{label}{n}" for label, n in zip("FR", count) if n) if isinstance(count, tuple) else str(count)


def cmd_usage(args, gf):
    maps = [load_map(name, gf) for name in args.maps]
    for obj_type in args.type or [ids.OBJ_TYPE_WALL, ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_TILE]:
        rows = proto_usage(gf, maps, obj_type)
        total = sum(sum(r[0]) if isinstance(r[0], tuple) else r[0] for r in rows)
        label = "tile ids (F floors, R roofs)" if obj_type == ids.OBJ_TYPE_TILE else ids.TYPE_NAMES[obj_type] + " protos"
        print(f"{', '.join(os.path.basename(m) for m in args.maps)}: {len(rows)} {label}, {total} uses")
        for count, key, art, name, info in rows[:args.top]:
            shown = f"tile {key:<5}" if obj_type == ids.OBJ_TYPE_TILE else f"{key:08X}"
            print(f"  {_count(count):>10}  {shown}  {art:<13} {name:<28} {info}")
    return 0


def cmd_where(args, gf):
    pids, tile_ids = [], []
    for text in args.ids:
        (tile_ids if args.tiles else pids).append(int(text, 0))
    if args.name:
        pattern = re.compile(args.name, re.IGNORECASE)
        for obj_type in args.type or range(ids.PROTO_TYPE_COUNT):
            if obj_type == ids.OBJ_TYPE_TILE:
                continue
            for pid in gf.protos.pids(obj_type):
                path = gf.art.path(gf.protos.get(pid).fid) if gf.protos.exists(pid) else None
                if pattern.search(gf.protos.name(pid) or "") or (path and pattern.search(os.path.basename(path))):
                    pids.append(pid)
    if not pids and not tile_ids:
        print("nothing to look for", file=sys.stderr)
        return 1
    found = find_uses(gf, pids, tile_ids, set(args.map) if args.map else None)
    for key in sorted(set(k for _, _, k, _ in found)):
        rows = [(name, elevation, tiles) for name, elevation, k, tiles in found if k == key]
        if args.tiles:
            path = gf.art.path(ids.make_fid(ids.OBJ_TYPE_TILE, key))
            print(f"tile {key} ({os.path.basename(path) if path else '?'}): "
                  f"{sum(len(t) for _, _, t in rows)} squares on {len(rows)} map elevations")
        else:
            path = gf.art.path(gf.protos.get(key).fid)
            print(f"{key:08X} {gf.protos.name(key) or ''} ({os.path.basename(path) if path else '?'}): "
                  f"{sum(len(t) for _, _, t in rows)} objects on {len(rows)} map elevations")
        for name, elevation, tiles in sorted(rows, key=lambda row: -len(row[2])):
            listed = " ".join(str(t) for t in tiles[:args.show]) + (" ..." if len(tiles) > args.show else "")
            print(f"  {name:<9} e{elevation} x{len(tiles):<4} {'squares' if args.tiles else 'tiles'} {listed}")
    missing = [f"{p:08X}" for p in pids if p not in {k for _, _, k, _ in found}]
    if missing and not args.tiles:
        print(f"not used on any map: {' '.join(missing)}")
    return 0


def cmd_extract(args, gf):
    game_map = load_map(args.map, gf)
    elevation = args.elevation if args.elevation is not None else game_map.entering_elevation
    prefab = Prefab.extract(game_map, args.tile_a, args.tile_b, elevation, args.critters, args.misc, args.name)
    prefab.save(args.out)
    print(f"{args.out}: {prefab!r}, origin hx {prefab.origin[0]} hy {prefab.origin[1]} "
          f"(tile {g.tile_at(*prefab.origin)})")
    if args.show:
        covered = prefab.tiles_at()
        xs, ys = zip(*(g.hex_center(t) for t in covered))
        rect = (min(xs) - 120, min(ys) - 200, max(xs) + 120, max(ys) + 80)
        scene = MapRenderer(gf).render(game_map, elevation, roofs=args.roofs, world_rect=rect)
        save_png(Overlay(scene).tint(covered).tile_numbers().image, args.show)
        print(f"{args.show}: the source map with the extracted hexes tinted")
    return 0


def cmd_preview(args, gf):
    prefab = Prefab.load(args.prefab)
    scene = prefab.render(gf, roofs=args.roofs)
    overlay = Overlay(scene, args.scale)
    if args.blockers:
        overlay.blockers()
    if args.grid:
        overlay.grid()
    if args.tile_numbers is not None:
        overlay.tile_numbers(args.tile_numbers)
    save_png(overlay.image, args.out)
    print(f"{args.out}: {overlay.image.width}x{overlay.image.height}  {prefab!r}")
    return 0


def cmd_sheet(args, gf):
    files = preview_sheet(gf, [Prefab.load(path) for path in args.prefabs], args.out, roofs=not args.no_roofs)
    print(f"{len(args.prefabs)} prefabs on {len(files)} sheet(s): {' '.join(files)}")
    return 0


def cmd_stamp(args, gf):
    prefab = Prefab.load(args.prefab)
    game_map = load_map(args.map, gf)
    if not args.out and not os.path.isfile(args.map):
        print("give --out when the map is not a file path", file=sys.stderr)
        return 2
    placed = prefab.stamp(game_map, args.at, args.elevation, args.keep_scripts, clear=args.clear)
    out = args.out or args.map
    game_map.save(out)
    print(f"{out}: stamped {prefab.name} at {args.at}, {len(placed)} objects")
    for problem in game_map.validate():
        print("  " + problem)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--overlay", action="append", default=[], help="mod data directory laid over the game tree")
    commands = parser.add_subparsers(dest="command", required=True)

    sub = commands.add_parser("usage", help="most-used wall / scenery / tile ids of one or more maps")
    sub.add_argument("maps", nargs="+", help="map names or paths (counts add up)")
    sub.add_argument("--type", type=_type, action="append", help="walls, scenery, tiles, items, critters, misc (repeatable)")
    sub.add_argument("--top", type=int, default=30, help="rows per type (default %(default)s)")
    sub.set_defaults(run=cmd_usage)

    sub = commands.add_parser("where", help="which maps use a proto or tile, and on which tiles")
    sub.add_argument("ids", nargs="*", help="PIDs (0x02000123), or tile ids with --tiles")
    sub.add_argument("--tiles", action="store_true", help="the ids are floor / roof tile ids")
    sub.add_argument("--name", metavar="REGEX", help="also protos whose name or art file matches")
    sub.add_argument("--type", type=_type, action="append", help="limit --name to these types")
    sub.add_argument("--map", action="append", help="look only at this map (repeatable)")
    sub.add_argument("--show", type=int, default=8, help="tiles listed per map (default %(default)s)")
    sub.set_defaults(run=cmd_where)

    sub = commands.add_parser("extract", help="cut a box of hexes out of a map into a prefab file")
    sub.add_argument("map")
    sub.add_argument("tile_a", type=int, help="one corner tile of the (hx, hy) box")
    sub.add_argument("tile_b", type=int, help="the opposite corner tile")
    sub.add_argument("-o", "--out", required=True, help="prefab file (.json)")
    sub.add_argument("-e", "--elevation", type=int, help="default: the elevation the map is entered on")
    sub.add_argument("--critters", choices=CRITTER_MODES, default="unscripted", help="default %(default)s")
    sub.add_argument("--misc", action="store_true", help="also take exit grids and scroll blockers")
    sub.add_argument("--name", help="prefab name (default: <map>-<tile>-<tile>)")
    sub.add_argument("--show", metavar="PNG", help="also draw the source map around the box, its hexes tinted")
    sub.add_argument("--roofs", action="store_true", help="--show with roofs")
    sub.set_defaults(run=cmd_extract)

    sub = commands.add_parser("preview", help="render a prefab on its own")
    sub.add_argument("prefab")
    sub.add_argument("-o", "--out", required=True, help="output PNG")
    sub.add_argument("--roofs", action="store_true")
    sub.add_argument("--grid", action="store_true")
    sub.add_argument("--blockers", action="store_true")
    sub.add_argument("--tile-numbers", nargs="?", type=int, const=0, metavar="STEP",
                     help="tile numbers as in the source map")
    sub.add_argument("--scale", type=float, default=1.0)
    sub.set_defaults(run=cmd_preview)

    sub = commands.add_parser("sheet", help="thumbnails of several prefabs on numbered sheets")
    sub.add_argument("prefabs", nargs="+")
    sub.add_argument("-o", "--out", required=True, metavar="PREFIX", help="PREFIX-01.png ...")
    sub.add_argument("--no-roofs", action="store_true")
    sub.set_defaults(run=cmd_sheet)

    sub = commands.add_parser("stamp", help="copy a prefab into a .map file")
    sub.add_argument("prefab")
    sub.add_argument("map", help="map name or path")
    sub.add_argument("--at", type=int, help="target tile, even hx and hy (default: the source position)")
    sub.add_argument("-e", "--elevation", type=int, default=0)
    sub.add_argument("--keep-scripts", action="store_true", help="attach the recorded scripts again")
    sub.add_argument("--clear", action="store_true", help="remove what stands on the covered hexes first")
    sub.add_argument("-o", "--out", help="output .map (default: overwrite MAP when it is a path)")
    sub.set_defaults(run=cmd_stamp)

    args = parser.parse_args(argv)
    try:
        return args.run(args, GameFiles(overlay=args.overlay or None))
    except (ValueError, KeyError, FileNotFoundError) as error:
        print(f"map_kit: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
