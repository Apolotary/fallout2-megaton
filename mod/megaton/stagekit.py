# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Test stages: a small flat map called megaton, built in one call.

A stage replaces the real town while scripts are being written and tested. It
is still map 151 "megaton" (same maps.txt entry, automap, script and item
ids), so everything a script does on a stage it does in the town. A stage file
is what build.py --stage and test.py --stage take::

    # tests/core/stage.py
    import stagekit

    SPOTS = stagekit.compact()                 # optional: pull every spot close to the entrance
    SCRIPTS_DIR = "scripts"                    # optional: tests/core/scripts/ holds stand-in scripts

    def build_maps(out_dir):
        stagekit.build(out_dir, groups=["core"], spots=SPOTS)

(tests/foundation/stage.py is a complete example with extra cast entries of
its own; build.py's docstring says what SPOTS and SCRIPTS_DIR do to the build.)

What build() makes
  - desert ground under every spot, walled in by invisible blocking hexes and
    framed by scroll blockers;
  - the entrance on spot ENTRY and two rows of world-map exit grids behind it
    (spot GATE_EXIT lies on them, as in the town);
  - the cast (cast/) of the chosen groups on their spots. An `attach` entry
    whose door / container / scenery nobody has built gets a stand-in object;
  - the map script megaton.ssl (if compiled);
  - three props next to the entrance, addressable in step files:
    @PROP_CHEST (footlocker: 2 stimpaks, rope), @PROP_LOCKED_CHEST (locked
    footlocker: the engine answers "It is locked."), @PROP_DOOR (wooden door in
    a short wall; unscripted, so it simply opens).

Where things stand
  - Without `spots` the cast stands on its real town coordinates (an 80 x 80
    hex field): reach people with the autotest command `dude @NAME/3`.
  - With SPOTS = stagekit.compact() the whole town shrinks to a third around
    ENTRY, keeping directions (the gate is still between the entrance and the
    bomb). Because scripts carry tile numbers, build.py recompiles them with
    TILE_<NAME> / ROT_<NAME> taken from the stage file's SPOTS; that is why
    SPOTS must be a module-level name of the stage file. Spots at or behind
    the entrance (GATE_EXIT) keep their exact offset.

build() also writes <out_dir>/.spots.json (every spot and prop with the tile
it really has on this map), which is where test.py's @NAME comes from.
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _path in (HERE, os.path.join(ROOT, "tools")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import cast  # noqa: E402
from f2lib import GameFiles, MapFile, geometry as g, ids  # noqa: E402
from layout import spots as town  # noqa: E402

MAP_NAME = "megaton"
SPOTS_FILE = ".spots.json"            # hidden: build.py does not pack names starting with a dot

# Plain desert floor variants and their relative frequency in vanilla desert1.map.
DESERT_TILES = [("edg5000.frm", 18), ("edg5003.frm", 9), ("edg5002.frm", 7), ("edg5001.frm", 6),
                ("edg5004.frm", 6), ("edg5005.frm", 5), ("edg5006.frm", 4), ("edg5007.frm", 4)]

PID_BLOCKER = 0x02000158              # "Block Hex Auto Inviso": invisible, impassable
PID_FOOTLOCKER = 0x00000080
PID_DOOR = 0x02000350                 # wooden door that fits the "jad" doorway walls
PID_WALL_ODD = 0x03000081             # jas1000: wall piece for odd hx
PID_WALL_EVEN = 0x03000082            # jas1001: wall piece for even hx
PID_DOORWAY_RIGHT = 0x03000084        # jad1001: at door hx - 1
PID_DOORWAY_LEFT = 0x03000083         # jad1000: at door hx + 1
PID_STIMPAK = 40
PID_ROPE = 127
EXIT_SHAPE = 2                        # exit-grid art hanging below its hex: reads as a band

MARGIN = 10                           # hexes of ground beyond the outermost spot
EXIT_ROWS = (2, 3)                    # exit grids at entrance hy + 2 and + 3 ...
EXIT_HALF_WIDTH = 12                  # ... from entrance hx - 12 to hx + 11
# Props: offsets (hx, hy) from the entrance, on the free row between the entrance and the exit grids.
PROPS = {"PROP_CHEST": (5, 1), "PROP_LOCKED_CHEST": (7, 1), "PROP_DOOR": (-6, 1)}


class StageError(Exception):
    pass


def compact(scale=1.0 / 3.0, anchor="ENTRY", gap=2):
    """{name: (hx, hy, rotation)} for EVERY spot, shrunk towards `anchor`.

    A spot in front of the anchor (smaller hy: the town side) moves to
    anchor + offset * scale; spots that would land on or next to an earlier
    one go to the nearest hex that keeps `gap` hexes of distance. Spots at or
    behind the anchor keep their exact offset. Deterministic: the result only
    depends on layout/spots.py.
    """
    ax, ay, _ = town.SPOTS[anchor]
    result = {}
    taken = []
    order = [anchor] + [name for name in town.SPOTS if name != anchor]
    for name in order:
        hx, hy, rotation = town.SPOTS[name]
        dx, dy = hx - ax, hy - ay
        if dy >= 0:
            tile = g.tile_at(hx, hy)
        else:
            want = g.tile_at(ax + round(dx * scale), min(ay - 1, ay + round(dy * scale)))
            tile = None
            for candidate in g.disc(want, 12):
                if g.tile_xy(candidate)[1] >= ay:                  # never onto the props / exit rows
                    continue
                if all(g.distance(candidate, other) >= gap for other in taken):
                    tile = candidate
                    break
            if tile is None:
                raise StageError(f"compact: no free hex near {name}")
        taken.append(tile)
        result[name] = g.tile_xy(tile) + (rotation,)
    return result


def scroll_frame(m, tiles, elevation=0, pad_x=160, pad_y=96):
    """Ring of scroll blockers: the screen-aligned rectangle around `tiles`, grown by the pads.

    The engine refuses to centre the view on a hex holding a scroll blocker
    and scrolls 32 px sideways / 24 px up and down per step, so the top and
    bottom edges are two adjacent hex rows and the sides one hex per row (the
    vanilla convention, research/04 section 11.6). Returns the number placed.
    """
    centers = [g.hex_center(tile) for tile in tiles]
    x0 = min(x for x, _ in centers) - pad_x
    x1 = max(x for x, _ in centers) + pad_x
    y0 = (min(y for _, y in centers) - pad_y) // 12 * 12 + 6
    y1 = (max(y for _, y in centers) + pad_y) // 12 * 12 + 6
    ring = set()
    for y in (y0, y0 + 12, y1 - 12, y1):
        for x in range(x0, x1 + 1, 16):
            ring.add(g.hex_from_world(x, y))
    for y in range(y0, y1 + 1, 12):
        for x in (x0, x1):
            ring.add(g.hex_from_world(x, y))
    ring.discard(-1)
    for tile in sorted(ring):
        if not g.is_edge(tile):
            m.add_scroll_blocker(tile, elevation)
    return len(ring)


def _has_blocker(m, tile):
    return any(obj.pid == PID_BLOCKER for obj in m.objects_at(tile))


def build(out_dir, groups=None, spots=None, extra=(), map_script="megaton", props=True, strict=False, log=print):
    """Build maps/megaton.map under out_dir (a build.py staging tree) and return what was made.

    out_dir     staging tree; its data/, scripts/ and proto/ (written by the earlier
                build steps) are read through a GameFiles overlay
    groups      cast groups to place, e.g. ["core"]; None = every group that has a file
    spots       {name: (hx, hy, rotation)} overriding layout/spots.py, normally the
                stage file's SPOTS = stagekit.compact()
    extra       additional cast entries (cast.critter(...), ...) for this stage only;
                their `spot` may also be an explicit (hx, hy[, rotation]) tuple
    map_script  scripts.lst stem of the map script, None for a map without one
    props       False leaves out the three PROP_* objects
    strict      passed to cast.place_cast (True: missing scripts are errors)

    Returns {"map": MapFile, "spots": {name: tile}, "placed": [(entry, object), ...]}.
    """
    gf = GameFiles(overlay=out_dir)
    m = MapFile.new(MAP_NAME, gf)
    positions = {name: cast.spot_position(name, spots) for name in town.SPOTS}
    for name in (spots or {}):
        positions.setdefault(name, tuple(spots[name]))
    ex, ey, entrance_rotation = positions["ENTRY"]
    extra = list(extra)

    # Ground: one hex rectangle (a rhombus on screen) under everything.
    points = [(hx, hy) for hx, hy, _ in positions.values()]
    points += [cast.spot_position(entry["spot"], spots)[:2] for entry in extra]
    points += [(ex - EXIT_HALF_WIDTH, ey + EXIT_ROWS[-1]), (ex + EXIT_HALF_WIDTH, ey + EXIT_ROWS[-1])]
    hx0 = max(8, min(x for x, _ in points) - MARGIN) & ~1
    hy0 = max(8, min(y for _, y in points) - MARGIN) & ~1
    hx1 = min(191, max(x for x, _ in points) + MARGIN) | 1
    hy1 = min(191, max(y for _, y in points) + 4) | 1
    rng = random.Random(151)
    names, weights = zip(*DESERT_TILES)
    # A hex with even hx sits on the floor square one further right (research/04 11.5): one extra column.
    m.fill_floor(max(0, hx0 // 2 - 1), hy0 // 2, hx1 // 2, hy1 // 2, lambda x, y: rng.choices(names, weights)[0])

    # Border of invisible blocking hexes, so nothing walks off the ground.
    for hx in range(hx0, hx1 + 1):
        for hy in (hy0, hy1):
            m.add_object(PID_BLOCKER, g.tile_at(hx, hy))
    for hy in range(hy0 + 1, hy1):
        for hx in (hx0, hx1):
            m.add_object(PID_BLOCKER, g.tile_at(hx, hy))

    entrance = g.tile_at(ex, ey)
    if not g.can_center(entrance):
        raise StageError(f"stage: ENTRY ({ex}, {ey}) cannot be a view centre")
    m.set_entrance(entrance, elevation=0, rotation=entrance_rotation)

    exits = []
    for dy in EXIT_ROWS:
        for hx in range(ex - EXIT_HALF_WIDTH, ex + EXIT_HALF_WIDTH):
            if hx0 < hx < hx1 and hy0 < ey + dy < hy1:
                exits.append(g.tile_at(hx, ey + dy))
                m.add_exit_grid(exits[-1], shape=EXIT_SHAPE)

    scroll_frame(m, [g.tile_at(hx, hy) for hx in (hx0, hx1) for hy in (hy0, hy1)], pad_x=-64, pad_y=-48)

    tiles = {name: g.tile_at(hx, hy) for name, (hx, hy, _) in positions.items()}

    if props:
        chest = m.add_object(PID_FOOTLOCKER, g.tile_at(ex + PROPS["PROP_CHEST"][0], ey + PROPS["PROP_CHEST"][1]))
        m.add_item(chest, PID_STIMPAK, quantity=2)
        m.add_item(chest, PID_ROPE)
        locked = m.add_object(PID_FOOTLOCKER, g.tile_at(ex + PROPS["PROP_LOCKED_CHEST"][0], ey + PROPS["PROP_LOCKED_CHEST"][1]))
        m.add_item(locked, PID_STIMPAK)
        m.lock(locked)
        door_hx, door_hy = ex + PROPS["PROP_DOOR"][0], ey + PROPS["PROP_DOOR"][1]
        for hx in range(door_hx - 2, door_hx + 3):
            if hx == door_hx:
                pid = PID_DOOR
            elif hx == door_hx - 1:
                pid = PID_DOORWAY_RIGHT
            elif hx == door_hx + 1:
                pid = PID_DOORWAY_LEFT
            else:
                pid = PID_WALL_ODD if hx & 1 else PID_WALL_EVEN
            m.add_object(pid, g.tile_at(hx, door_hy))
        for name, (dx, dy) in PROPS.items():
            tiles[name] = g.tile_at(ex + dx, ey + dy)

    # Stand-ins for what the architect would have built: one object per `attach` spot.
    for entry in cast.load(groups) + extra:
        if entry["type"] != "attach" or entry["kind"] == "critter":
            continue
        hx, hy, rotation = cast.spot_position(entry["spot"], spots)
        tile = g.tile_at(hx, hy)
        if not any(entry["kind"] in cast._kind_of(gf, obj) for obj in m.objects_at(tile)):
            m.add_object(entry.get("stand_in") or cast.STAND_INS[entry["kind"]], tile, rotation=rotation)

    placed = cast.place_cast(m, gf, groups=groups, strict=strict, spots=spots, extra=extra, log=log)

    if map_script:
        if gf.exists(f"scripts/{map_script}.int"):
            m.set_map_script(map_script)
        else:
            log(f"stage: {map_script}.ssl is not compiled, the map has no map script")

    problems = [p for p in m.validate() if "locked door without a script" not in p]
    errors = [p for p in problems if p.startswith("error")]
    for problem in problems:
        log("stage: " + problem)
    if errors:
        raise StageError(f"stage: the map has {len(errors)} error(s)")

    os.makedirs(os.path.join(out_dir, "maps"), exist_ok=True)
    m.save(os.path.join(out_dir, "maps", m.file_name))
    with open(os.path.join(out_dir, SPOTS_FILE), "w") as f:
        json.dump(tiles, f, indent=1, sort_keys=True)
    critters = sum(1 for entry, _ in placed if entry["type"] == "critter")
    log(f"stage: {m.file_name}: ground hx {hx0}..{hx1}, hy {hy0}..{hy1}; {len(m.objects[0])} objects, "
        f"{critters} cast critters, {len(m.scripts())} scripts, {len(exits)} exit hexes, entrance {entrance}")
    return {"map": m, "spots": tiles, "placed": placed}
