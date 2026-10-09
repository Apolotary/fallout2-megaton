#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Render one elevation of a Fallout 2 map to a PNG, without the game.

    python3 tools/render_map.py klamall --fit 1500 --tile-numbers
    python3 tools/render_map.py denbus1 --crop 21892 12 --grid --tile-numbers 2 --blockers
    python3 tools/render_map.py mod/mymod/data/maps/mymap.map --overlay mod/mymod/data --roofs --scripts
    python3 tools/render_map.py arvillag --view 20100 1280x860 -o shot.png   # what the game shows

The picture is built the way fallout2-ce composes a frame (tile.cc:634-655,
object.cc:761-859, research/04 section 12): floor squares, then every FLAT
object in ascending tile order, then all other objects in ascending tile order
(file order within a hex), then roofs. Sprites are anchored bottom-centre on
the hex centre plus the FRM's per-direction shift plus the object's x / y. The
work is done on palette indices with the engine's own colour tables, so at
full daylight a render equals a screenshot pixel for pixel
(tools/tests/compare_render.py checks that against the running engine).

Not drawn, because they only exist at run time: the player and the see-through
"egg" around him, per-hex lighting from lamps (everything is drawn at one
light level, --light), palette animation, and whatever scripts change when the
map is entered.

As a library::

    from render_map import MapRenderer, Overlay
    scene = MapRenderer(gf).render(game_map, elevation=0, roofs=True, crop=(20100, 12))
    image = Overlay(scene, scale=1).grid().tile_numbers(5).image
    scene.world_rect, scene.indices, scene.kinds      # see `Scene`
"""
import argparse
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from f2lib import GameFiles, MapFile, geometry as g, ids  # noqa: E402
from f2lib.map import OBJECT_FLAT, OBJECT_HIDDEN, OBJECT_MULTIHEX, OBJECT_NO_BLOCK, NO_TILE  # noqa: E402

LIGHT_MAX = 0x10000                     # light.h: full daylight
FIRST_ANIMATED = 229                    # palette indices the lighting code leaves alone (object.cc:2770)
MARGIN = 48                             # pixels kept around the content when no window is given

# Scene.kinds values: what was drawn last on a pixel.
KIND_NONE, KIND_FLOOR, KIND_ITEM, KIND_CRITTER, KIND_SCENERY, KIND_WALL, KIND_MISC, KIND_ROOF = range(8)
KIND_NAMES = ("empty", "floor", "item", "critter", "scenery", "wall", "misc", "roof")
_KIND_OF_TYPE = {ids.OBJ_TYPE_ITEM: KIND_ITEM, ids.OBJ_TYPE_CRITTER: KIND_CRITTER, ids.OBJ_TYPE_SCENERY: KIND_SCENERY,
                 ids.OBJ_TYPE_WALL: KIND_WALL, ids.OBJ_TYPE_MISC: KIND_MISC}

# Translucency flags (obj_types.h) -> RGB555 index of the tint (object.cc:3466-3470).
TRANS_MASK = 0xFC000
_TRANS_TINT = {0x4000: 31744, 0x10000: 25439, 0x20000: 10239, 0x40000: 32767, 0x80000: 30689}
TRANS_WALL = 0x10000
TRANS_GLASS = 0x20000

_FONT_FILES = ('/System/Library/Fonts/Menlo.ttc', '/System/Library/Fonts/Supplemental/Arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
_FONT_FILES += tuple(os.path.join(root, "Fonts", "consola.ttf")
                     for root in (os.environ.get("WINDIR") or os.environ.get("SystemRoot"),)
                     if root)
_fonts = {}


def load_font(size):
    """A small label font: the first available system TrueType font, else Pillow's built-in one."""
    font = _fonts.get(size)
    if font is None:
        for path in _FONT_FILES:
            try:
                font = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
        else:
            font = ImageFont.load_default(size)
        _fonts[size] = font
    return font


def load_map(name, gamefiles):
    """Map by game name ('klamall', 'klamall.map') or by path to a .map file."""
    if os.path.isfile(name):
        with open(name, "rb") as f:
            return MapFile.from_bytes(f.read(), gamefiles)
    return MapFile.load(os.path.basename(name), gamefiles)


def save_png(image, path, colours=None):
    """Save a PNG, as a 256-colour file when that loses nothing (an unscaled render has at most 256 colours).

    colours forces a reduction to that many colours: a third of the size for scaled overviews, at no visible cost.
    """
    if colours:
        image = image.convert("RGB").quantize(colours, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    elif image.mode == "RGB" and image.getcolors(256) is not None:
        image = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
    image.save(path, optimize=True)


class EngineColours:
    """The lookup tables fallout2-ce computes from color.pal (color.cc:168-200, 375-430).

    All of them work on palette indices: a "colour" is first reduced to RGB555
    and then mapped back through the palette file's RGB555 -> index table.
    """

    def __init__(self, palette):
        raw = np.frombuffer(palette.raw, dtype=np.uint8, count=768).reshape(256, 3).astype(np.int64)
        self.mapped = (raw <= 63).all(axis=1)
        self.rgb5 = np.where(self.mapped[:, None], raw, 0) >> 1          # Color2RGB components
        self.lut = palette.lut
        r, gr, b = self.rgb5[:, 0], self.rgb5[:, 1], self.rgb5[:, 2]
        self.common_gray = ((b + 3 * r + 6 * gr) // 10) >> 2
        self.glass_gray = ((r + 5 * gr + 4 * b) // 10) >> 2
        self._blend = {}
        self._intensity = {}

    def _pack(self, rgb5):
        return self.lut[(rgb5[..., 0] << 10) | (rgb5[..., 1] << 5) | rgb5[..., 2]]

    def intensity(self, light):
        """Column ``light // 512`` of intensityColorTable: (256,) uint8, 0 for unmapped colours."""
        index = max(0, min(light // 512, 255))
        column = self._intensity.get(index)
        if column is None:
            if index < 128:
                column = self._pack((self.rgb5 * (512 * index)) >> 16)
            else:
                column = self._pack(self.rgb5 + (((31 - self.rgb5) * (512 * (index - 128))) >> 16))
            column = self._intensity[index] = np.where(self.mapped, column, 0).astype(np.uint8)
        return column

    def shade(self, light):
        """What _dark_trans_buf_to_buf writes for each source index: lit, animated colours untouched."""
        table = self.intensity(light).copy()
        table[FIRST_ANIMATED:] = np.arange(FIRST_ANIMATED, 256)
        return table

    def blend(self, trans_flag):
        """(8, 256) table for a translucency flag: row = grey level of the sprite pixel, column = pixel under it."""
        table = self._blend.get(trans_flag)
        if table is None:
            tint = self.rgb5[self.lut[_TRANS_TINT[trans_flag]]]
            rows = [np.arange(256, dtype=np.uint8)]
            for step in range(7):
                rows.append(self._pack((tint * (step + 1) + self.rgb5 * (6 - step)) // 7))
            table = self._blend[trans_flag] = np.stack(rows).astype(np.uint8)
        return table


class Scene:
    """A rendered picture and how it maps to the game world.

    indices     (h, w) uint8 palette indices, 0 where nothing was drawn
    kinds       (h, w) uint8 KIND_* of the sprite on top, or None (render(kinds=True))
    world_rect  (x0, y0, x1, y1) in world pixels (f2lib.geometry), x1 / y1 exclusive
    skipped     {reason: count} for objects the engine would not have drawn either
    """

    def __init__(self, indices, kinds, world_rect, palette, game_map, elevation):
        self.indices = indices
        self.kinds = kinds
        self.world_rect = world_rect
        self.palette = palette
        self.map = game_map
        self.elevation = elevation
        self.skipped = {}

    @property
    def size(self):
        return self.indices.shape[1], self.indices.shape[0]

    def rgb(self):
        return self.palette.rgb[self.indices]

    def image(self):
        return Image.fromarray(self.rgb())

    def to_pixel(self, world_xy):
        return world_xy[0] - self.world_rect[0], world_xy[1] - self.world_rect[1]

    def tiles_in_view(self, pad=0):
        """Tiles whose 32x16 cell touches the picture (grown by `pad` pixels)."""
        tiles = np.arange(g.HEX_COUNT)
        a = g.HEX_WIDTH - 1 - tiles % g.HEX_WIDTH
        hy = tiles // g.HEX_WIDTH
        x = 48 * (a >> 1) + 32 * (a & 1) + 16 * hy
        y = -12 * (a >> 1) + 12 * hy
        x0, y0, x1, y1 = self.world_rect
        inside = (x + 32 > x0 - pad) & (x < x1 + pad) & (y + 16 > y0 - pad) & (y < y1 + pad)
        return tiles[inside].tolist()


class MapRenderer:
    """Draws maps of one game tree; decoded sprites are cached across `render` calls.

    light is the single light level everything is drawn at (0x10000 = full
    daylight, the engine's ambient range goes down to 0x4000).
    """

    def __init__(self, gamefiles, light=LIGHT_MAX):
        self.gf = gamefiles
        self.palette = gamefiles.palette
        self.colours = EngineColours(self.palette)
        self.light = light
        self._shade = self.colours.shade(light)
        self._sprites = {}

    # ---------------------------------------------------------------- sprites
    def sprite(self, fid, frame=0, rotation=0):
        """(pixels, mask, left, top) of a frame relative to its hex centre, or None when there is no art.

        pixels are raw palette indices; left / top do not include the object's own x / y.
        """
        key = (fid, frame, rotation)
        if key in self._sprites:
            return self._sprites[key]
        sprite = None
        try:
            frm = self.gf.art.load(fid)
            if 0 <= rotation < 6 and 0 <= frame < frm.frame_count:
                pixels = frm.frame(rotation, frame).array()
                left, top, _, _ = frm.placement(rotation, frame)
                sprite = (pixels, pixels != 0, left, top)
        except (FileNotFoundError, ValueError, KeyError, IndexError):
            pass
        self._sprites[key] = sprite
        return sprite

    def _lit(self, fid, frame=0, rotation=0):
        """Like `sprite`, with the pixels already passed through the light table."""
        key = (fid, frame, rotation, "lit")
        if key not in self._sprites:
            sprite = self.sprite(fid, frame, rotation)
            if sprite is not None:
                sprite = (self._shade[sprite[0]],) + sprite[1:]
            self._sprites[key] = sprite
        return self._sprites[key]

    # ------------------------------------------------------------------ roofs
    @staticmethod
    def hidden_roof(game_map, elevation, tile):
        """Squares whose roof the engine hides while the player stands on `tile` (tile_fill_roof)."""
        squares = game_map.tiles[elevation]
        roofs = (squares >> 16) & 0xFFF
        flags = (squares >> 28) & 0xF
        hidden = set()
        stack = [g.roof_square(tile)]
        while stack:
            square = stack.pop()
            if square in hidden or roofs[square] == NO_TILE or flags[square] & 3:
                continue
            hidden.add(square)
            qx, qy = g.square_xy(square)
            stack += [s for s in (g.square_at(qx - 1, qy), g.square_at(qx + 1, qy),
                                  g.square_at(qx, qy - 1), g.square_at(qx, qy + 1)) if s != -1]
        return hidden

    # ----------------------------------------------------------------- render
    def draw_list(self, game_map, elevation, roofs=False, hide_roof_at=None, types=None, floors=True):
        """Everything the engine would blit, in order: [(x, y, pixels, mask, kind, trans_flag)] in world pixels.

        types limits the objects to a set of object types (ids.OBJ_TYPE_*).
        The second return value counts objects left out and why.
        """
        ops = []
        skipped = {}
        squares = game_map.tiles.get(elevation)
        tile_fid = ids.make_fid(ids.OBJ_TYPE_TILE, 0)

        if squares is not None and floors:
            floor_ids = squares & 0xFFF
            # tile.cc:1466: bit 0 of the flag nibble hides a square.
            for square in np.flatnonzero((floor_ids != NO_TILE) & ((squares >> 12) & 1 == 0)).tolist():
                sprite = self._lit(tile_fid | int(floor_ids[square]))
                if sprite is None:
                    continue
                x, y = g.square_world(square)
                if g.hex_from_world(x, y + 13) == -1:        # tileRenderFloor draws nothing there (tile.cc:1668)
                    continue
                ops.append((x, y, sprite[0], sprite[1], KIND_FLOOR, 0))

        flat, upright = [], []
        for obj in game_map.objects[elevation]:
            if obj.flags & OBJECT_HIDDEN or not g.is_valid(obj.tile):
                continue
            if types is not None and ids.fid_type(obj.fid) not in types:
                continue
            (flat if obj.flags & OBJECT_FLAT else upright).append(obj)
        for group in (flat, upright):
            group.sort(key=lambda obj: obj.tile)             # stable: file order within a hex
            for obj in group:
                trans = obj.flags & TRANS_MASK
                if trans not in _TRANS_TINT:
                    trans = 0
                sprite = (self.sprite if trans else self._lit)(obj.fid, obj.frame, obj.rotation)
                if sprite is None:
                    skipped["no art"] = skipped.get("no art", 0) + 1
                    continue
                cx, cy = g.hex_center(obj.tile)
                ops.append((cx + sprite[2] + obj.x, cy + sprite[3] + obj.y, sprite[0], sprite[1],
                            _KIND_OF_TYPE.get(ids.fid_type(obj.fid), KIND_MISC), trans))

        if squares is not None and roofs:
            roof_ids = (squares >> 16) & 0xFFF
            hidden = self.hidden_roof(game_map, elevation, hide_roof_at) if hide_roof_at is not None else ()
            for square in np.flatnonzero((roof_ids != NO_TILE) & ((squares >> 28) & 1 == 0)).tolist():
                if square in hidden:
                    continue
                sprite = self._lit(tile_fid | int(roof_ids[square]))
                if sprite is not None:
                    x, y = g.roof_world(square)
                    ops.append((x, y, sprite[0], sprite[1], KIND_ROOF, 0))
        return ops, skipped

    def render(self, game_map, elevation=None, roofs=False, hide_roof_at=None, types=None, floors=True,
               view=None, crop=None, world_rect=None, full=False, kinds=False):
        """Draw one elevation and return a `Scene`.

        Window, first one given wins:
            world_rect  (x0, y0, x1, y1) in world pixels
            view        (center_tile, width, height): exactly the engine's iso window centred on a tile
            crop        (center_tile, radius): `radius` hexes to the east and west of the tile (32 px each)
                        and 2 * radius hex rows above and below it (12 px each)
            full        the whole 200 x 200 hex grid
            default     the bounding box of the objects and roofs (of the floor on a map without any),
                        plus a margin
        hide_roof_at    tile the player would stand on: the roof over it is left out, as in the game
        kinds           also fill `Scene.kinds`
        """
        if elevation is None:
            elevation = game_map.entering_elevation if game_map.entering_elevation in game_map.tiles else 0
        if not 0 <= elevation < len(game_map.objects):
            raise ValueError(f"elevation {elevation} is outside 0..{len(game_map.objects) - 1}")
        ops, skipped = self.draw_list(game_map, elevation, roofs, hide_roof_at, types, floors)

        if world_rect is None and view is not None:
            center, width, height = view
            window = g.View(center, width, height)
            world_rect = (-window.dx, -window.dy, width - window.dx, height - window.dy)
        if world_rect is None and crop is not None:
            center, radius = crop
            cx, cy = g.hex_center(center)
            world_rect = (cx - 32 * radius - 16, cy - 24 * radius - 8, cx + 32 * radius + 16, cy + 24 * radius + 8)
        if world_rect is None and full:
            world_rect = (-16, -1190 - g.ROOF_HEIGHT, 8000, 2412)
        if world_rect is None:
            # Retail maps carpet the whole grid with ground: frame the objects, or the floor if there is nothing else.
            # (1x1 sprites are the invisible blockers.)
            boxes = [(x, y, x + p.shape[1], y + p.shape[0], kind) for x, y, p, _, kind, _ in ops if p.size > 1]
            boxes = [box[:4] for box in boxes if box[4] != KIND_FLOOR] or [box[:4] for box in boxes]
            if boxes:
                boxes = np.array(boxes)
                world_rect = (int(boxes[:, 0].min()) - MARGIN, int(boxes[:, 1].min()) - MARGIN,
                              int(boxes[:, 2].max()) + MARGIN, int(boxes[:, 3].max()) + MARGIN)
            else:
                cx, cy = g.hex_center(game_map.entering_tile)
                world_rect = (cx - 320, cy - 190, cx + 320, cy + 190)

        x0, y0, x1, y1 = world_rect
        width, height = x1 - x0, y1 - y0
        canvas = np.zeros((height, width), dtype=np.uint8)
        kind_canvas = np.zeros((height, width), dtype=np.uint8) if kinds else None
        colours = self.colours
        for x, y, pixels, mask, kind, trans in ops:
            x -= x0
            y -= y0
            h, w = pixels.shape
            if x >= width or y >= height or x + w <= 0 or y + h <= 0:
                continue
            if x < 0 or y < 0 or x + w > width or y + h > height:
                sx, sy = max(-x, 0), max(-y, 0)
                ex, ey = min(w, width - x), min(h, height - y)
                pixels = pixels[sy:ey, sx:ex]
                mask = mask[sy:ey, sx:ex]
                x += sx
                y += sy
                h, w = pixels.shape
            target = canvas[y:y + h, x:x + w]
            if trans:
                # _dark_translucent_trans_buf_to_buf (object.cc:2786): tint by the sprite's grey level,
                # then light the result; see-through walls are always drawn at full light.
                gray = (colours.glass_gray if trans == TRANS_GLASS else colours.common_gray)[pixels]
                mixed = colours.blend(trans)[gray, target]
                lit = colours.intensity(LIGHT_MAX if trans == TRANS_WALL else self.light)[mixed]
                np.copyto(target, lit, where=mask)
            else:
                np.copyto(target, pixels, where=mask)
            if kind_canvas is not None:
                kind_canvas[y:y + h, x:x + w][mask] = kind
        scene = Scene(canvas, kind_canvas, world_rect, self.palette, game_map, elevation)
        scene.skipped = skipped
        return scene


def blocked_tiles(game_map, elevation):
    """{tile: KIND_*} of hexes closed to movement (_obj_blocking_at, object.cc:2387-2437).

    A hex is blocked by a critter, scenery or wall standing on it, or by a
    MULTIHEX one on a neighbouring hex; the kind is that of the first blocker found.
    """
    blocked = {}
    for obj in game_map.objects[elevation]:
        if obj.flags & (OBJECT_HIDDEN | OBJECT_NO_BLOCK) or not g.is_valid(obj.tile):
            continue
        kind = _KIND_OF_TYPE.get(ids.fid_type(obj.fid))
        if kind not in (KIND_CRITTER, KIND_SCENERY, KIND_WALL):
            continue
        blocked.setdefault(obj.tile, kind)
        if obj.flags & OBJECT_MULTIHEX:
            for neighbour in g.neighbors(obj.tile):
                if neighbour != -1:
                    blocked.setdefault(neighbour, kind)
    return blocked


class Overlay:
    """Design aids drawn over a `Scene`, in output pixels so labels stay sharp at any scale.

    Every method returns self; `image` is the RGB result.
    """

    BLOCK_COLOURS = {KIND_WALL: (255, 40, 40, 110), KIND_SCENERY: (255, 150, 0, 110), KIND_CRITTER: (255, 0, 255, 120)}

    def __init__(self, scene, scale=1.0, font_size=10):
        self.scene = scene
        self.scale = scale
        base = scene.image()
        if scale != 1:
            size = (max(1, round(base.width * scale)), max(1, round(base.height * scale)))
            base = base.resize(size, Image.NEAREST if scale > 1 and float(scale).is_integer() else Image.LANCZOS)
        self.image = base
        self.font = load_font(font_size)
        self._layer = None
        self._draw = None

    # ------------------------------------------------------------- primitives
    def _begin(self):
        self._layer = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
        self._draw = ImageDraw.Draw(self._layer)
        return self._draw

    def _end(self):
        self.image = Image.alpha_composite(self.image.convert("RGBA"), self._layer).convert("RGB")
        self._layer = self._draw = None
        return self

    def point(self, world_xy):
        x, y = self.scene.to_pixel(world_xy)
        return x * self.scale, y * self.scale

    def hex_polygon(self, tile):
        """The six corners of a hex in output pixels (the 32x16 cell with its corners cut, tile.cc:345-387)."""
        x, y = g.hex_world(tile)
        return [self.point(p) for p in ((x + 16, y), (x + 32, y + 4), (x + 32, y + 12),
                                        (x + 16, y + 16), (x, y + 12), (x, y + 4))]

    def label(self, world_xy, text, fill=(255, 255, 255, 255), back=(0, 0, 0, 170), anchor="mm", offset=(0, 0)):
        """Text on a dark plate, positioned by a world pixel."""
        x, y = self.point(world_xy)
        x, y = round(x + offset[0]), round(y + offset[1])
        box = self._draw.textbbox((x, y), text, font=self.font, anchor=anchor)
        self._draw.rectangle((box[0] - 2, box[1] - 1, box[2] + 1, box[3] + 1), fill=back)
        self._draw.text((x, y), text, font=self.font, fill=fill, anchor=anchor)

    # --------------------------------------------------------------- overlays
    def grid(self, colour=(255, 255, 255, 70)):
        """Outline of every hex in view."""
        draw = self._begin()
        for tile in self.scene.tiles_in_view():
            draw.polygon(self.hex_polygon(tile), outline=colour)
        return self._end()

    def tile_numbers(self, step=None, colour=(255, 255, 0, 255)):
        """Tile number on every `step`-th hex in both grid directions (default: about 70 px apart).

        One hex further along a row is tile + 1 (to the screen left), one row
        further down-right is tile + 200.
        """
        if not step:
            step = next((s for s in (1, 2, 5, 10, 20) if s * 24 * self.scale >= 64), 50)
        draw = self._begin()
        for tile in self.scene.tiles_in_view():
            hx, hy = g.tile_xy(tile)
            if hx % step or hy % step:
                continue
            cx, cy = self.point(g.hex_center(tile))
            draw.polygon(self.hex_polygon(tile), outline=colour)
            draw.line((cx - 2, cy, cx + 2, cy), fill=colour)
            draw.line((cx, cy - 2, cx, cy + 2), fill=colour)
            self.label(g.hex_center(tile), str(tile), fill=colour, anchor="mt", offset=(0, 8 * self.scale + 2))
        return self._end()

    def tint(self, tiles, colour=(0, 200, 255, 90)):
        """Fill the given hexes with a translucent colour (to show a selection)."""
        draw = self._begin()
        visible = set(self.scene.tiles_in_view())
        for tile in tiles:
            if tile in visible:
                draw.polygon(self.hex_polygon(tile), fill=colour)
        return self._end()

    def blockers(self):
        """Tint hexes closed to movement (red wall, orange scenery, magenta critter) and scroll blockers (blue)."""
        draw = self._begin()
        visible = set(self.scene.tiles_in_view())
        for tile, kind in blocked_tiles(self.scene.map, self.scene.elevation).items():
            if tile in visible:
                draw.polygon(self.hex_polygon(tile), fill=self.BLOCK_COLOURS[kind])
        for obj in self.scene.map.objects[self.scene.elevation]:
            if obj.pid == ids.SCROLL_BLOCKER_PID and obj.tile in visible:
                draw.polygon(self.hex_polygon(obj.tile), fill=(60, 120, 255, 130))
        return self._end()

    def scripts(self):
        """Scripted objects (cyan), spatial scripts with their trigger radius (yellow) and the entering tile (green)."""
        game_map, elevation = self.scene.map, self.scene.elevation
        names = game_map.gf.scripts if game_map.gf is not None else None

        def script_name(index):
            name = names.name(index) if names is not None else None
            return name or f"#{index}"

        draw = self._begin()
        visible = set(self.scene.tiles_in_view())
        for script in game_map.scripts(ids.SCRIPT_TYPE_SPATIAL):
            if script.elevation != elevation or not g.is_valid(script.tile):
                continue
            for tile in g.ring(script.tile, script.radius) if script.radius > 0 else ():
                if tile in visible:
                    draw.polygon(self.hex_polygon(tile), outline=(255, 230, 0, 150))
            if script.tile in visible:
                draw.polygon(self.hex_polygon(script.tile), fill=(255, 230, 0, 110), outline=(255, 230, 0, 255))
                self.label(g.hex_center(script.tile), f"{script_name(script.index)} r{script.radius}",
                           fill=(255, 230, 0, 255), anchor="mb", offset=(0, -8 * self.scale - 2))
        for obj in game_map.objects[elevation]:
            if obj.sid == -1 or obj.tile not in visible:
                continue
            record = game_map.find_script(obj.sid)
            index = record.index if record is not None else obj.script_index
            draw.polygon(self.hex_polygon(obj.tile), outline=(0, 255, 255, 255))
            self.label(g.hex_center(obj.tile), script_name(index), fill=(0, 255, 255, 255),
                       anchor="mb", offset=(0, -8 * self.scale - 2))
        if game_map.entering_elevation == elevation and game_map.entering_tile in visible:
            draw.polygon(self.hex_polygon(game_map.entering_tile), fill=(0, 255, 0, 120), outline=(0, 255, 0, 255))
            self.label(g.hex_center(game_map.entering_tile), "start", fill=(0, 255, 0, 255), anchor="mt",
                       offset=(0, 8 * self.scale + 2))
        return self._end()

    def mark(self, pids, colour=(255, 0, 255, 255)):
        """Outline the hex of every object with one of `pids` and label it with its PID."""
        pids = set(pids)
        draw = self._begin()
        visible = set(self.scene.tiles_in_view())
        for obj in self.scene.map.objects[self.scene.elevation]:
            if obj.pid in pids and obj.tile in visible:
                draw.polygon(self.hex_polygon(obj.tile), outline=colour)
                self.label(g.hex_center(obj.tile), f"{obj.pid:08X}", fill=colour, anchor="mb",
                           offset=(0, -8 * self.scale - 2))
        return self._end()


def parse_types(text):
    """'walls,scenery' -> {OBJ_TYPE_WALL, OBJ_TYPE_SCENERY}; accepts singular and directory names."""
    types = set()
    for word in filter(None, re.split(r"[,\s]+", text.lower())):
        for obj_type in range(ids.PROTO_TYPE_COUNT):
            if word in (ids.TYPE_NAMES[obj_type], ids.TYPE_DIRS[obj_type], ids.TYPE_NAMES[obj_type] + "s"):
                types.add(obj_type)
                break
        else:
            raise ValueError(f"unknown object type {word!r}")
    return types


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("map", help="map name (klamall), file name (klamall.map) or path to a .map file")
    parser.add_argument("-o", "--out", help="output PNG (default: <map>.png in the current directory)")
    parser.add_argument("--overlay", action="append", default=[],
                        help="mod data directory laid over the game tree (repeatable, first wins)")
    parser.add_argument("-e", "--elevation", type=int, help="elevation 0..2 (default: the one the map is entered on)")
    parser.add_argument("--roofs", action="store_true", help="draw roofs")
    parser.add_argument("--hide-roof-at", type=int, metavar="TILE",
                        help="with --roofs: leave out the roof the game hides while the player stands on TILE")
    parser.add_argument("--types", help="draw only these objects, e.g. walls,scenery (item, critter, scenery, wall, misc)")
    parser.add_argument("--no-floor", action="store_true", help="leave out the floor squares")
    parser.add_argument("--light", type=int, default=100, metavar="PERCENT",
                        help="light level, 100 = full daylight (default), 25 = the engine's darkest night")
    window = parser.add_mutually_exclusive_group()
    window.add_argument("--crop", nargs=2, type=int, metavar=("TILE", "RADIUS"),
                        help="window around TILE: RADIUS hexes east / west, 2 * RADIUS hex rows north / south")
    window.add_argument("--view", nargs=2, metavar=("TILE", "WxH"),
                        help="the game's own window centred on TILE (1280x860 for a 1280x960 game)")
    window.add_argument("--full", action="store_true", help="the whole 200x200 grid instead of the area holding objects")
    parser.add_argument("--grid", action="store_true", help="outline every hex")
    parser.add_argument("--tile-numbers", nargs="?", type=int, const=0, metavar="STEP",
                        help="label every STEP-th hex with its tile number (default STEP: sparse, about 70 px apart)")
    parser.add_argument("--blockers", action="store_true", help="tint hexes blocked for movement and scroll blockers")
    parser.add_argument("--scripts", action="store_true", help="mark scripted objects, spatial scripts and the entering tile")
    parser.add_argument("--mark", action="append", default=[], metavar="PID",
                        help="outline objects with this PID (hex, repeatable or comma separated)")
    size = parser.add_mutually_exclusive_group()
    size.add_argument("--scale", type=float, default=1.0, help="output scale factor (default 1)")
    size.add_argument("--fit", type=int, metavar="PIXELS", help="scale down so that the longer side is at most PIXELS")
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except (ValueError, KeyError, FileNotFoundError) as error:
        print(f"render_map: {error}", file=sys.stderr)
        return 2


def _run(args):
    gf = GameFiles(overlay=args.overlay or None)
    game_map = load_map(args.map, gf)
    light = max(0, min(args.light, 100)) * LIGHT_MAX // 100
    renderer = MapRenderer(gf, light=light)
    view = None
    if args.view:
        width, height = (int(v) for v in args.view[1].lower().split("x"))
        view = (int(args.view[0]), width, height)
    scene = renderer.render(game_map, args.elevation, roofs=args.roofs, hide_roof_at=args.hide_roof_at,
                            types=parse_types(args.types) if args.types else None, floors=not args.no_floor,
                            view=view, crop=tuple(args.crop) if args.crop else None, full=args.full)

    scale = args.scale
    if args.fit:
        scale = min(1.0, args.fit / max(scene.size))
    overlay = Overlay(scene, scale)
    if args.blockers:
        overlay.blockers()
    if args.grid:
        overlay.grid()
    if args.scripts:
        overlay.scripts()
    marks = [int(p, 16) for text in args.mark for p in text.split(",") if p]
    if marks:
        overlay.mark(marks)
    if args.tile_numbers is not None:
        overlay.tile_numbers(args.tile_numbers)

    out = args.out or f"{game_map.base_name}{'' if args.elevation is None else f'-e{scene.elevation}'}.png"
    save_png(overlay.image, out)
    x0, y0, x1, y1 = scene.world_rect
    notes = "".join(f", {count} objects skipped ({reason})" for reason, count in scene.skipped.items())
    print(f"{out}: {overlay.image.width}x{overlay.image.height}, elevation {scene.elevation}, "
          f"world x {x0}..{x1} y {y0}..{y1}, scale {scale:.3g}{notes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
