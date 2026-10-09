# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Custom floor and roof TILES: a rendered sheet -> 80 x 36 tile FRMs, tiles.lst, and the helpers
that paint them onto a map (system Python side; the Blender side is pipeline/blender_sheet.py,
the geometry pipeline/tilegeo.py).

HOW THE ENGINE USES TILE ART (checked in engines/fallout2-ce/src: tile.cc, art.cc, map.cc, object.cc)
  * A square word of the map holds two 12-bit indices into art/tiles/tiles.lst (floor: bits 0..11,
    roof: bits 16..27). Nothing else is looked up: NO PROTO is needed, and the art list is replaced
    as a whole file, so the mod ships the complete stock tiles.lst with its lines appended.
  * Stock tiles.lst has 3,102 lines; the index is 12 bits and the engine's preload table has
    4,096 entries (object.cc:3203), so there is room for 994 tiles: indices 3102..4095. They are
    numbered by manifest.json ("tiles": append-only, like the proto slots).
  * A FLOOR tile must be 80 x 36 or smaller: the floor blitter indexes a fixed 80-wide light table
    (tile.cc tileRenderFloor). A ROOF tile of another size would draw, but the redraw code only
    visits the squares whose 80 x 36 box meets the dirty rectangle, so anything larger leaves
    trails. Every tile here is exactly 80 x 36 with the stock rhombus mask.
  * Index 0 pixels are transparent in both blitters. Under a floor there is only the cleared
    (black) window, so a floor tile must be solid; under a roof are the floor and every object,
    so a ROOF TILE MAY HAVE HOLES, and a click through a hole reaches what stands below
    (tile.cc _square_roof_intersect tests the pixel).
  * Roofs are drawn 96 px above their square, after every object, at the map's AMBIENT light only
    (tile.cc tileRenderRoofsInRect): lamps do not light them, and palette indices 229..254 (the
    animated ranges, geo.set_fx) are not darkened at night on roofs either.
  * A roof hides when the player's hex belongs to a square whose roof index is not 1: the engine
    flood-fills the 4-connected region of such squares (tile.cc tile_fill_roof). So
      - every square of a building's roof must keep SOME tile, also where the picture is a hole:
        fully transparent tiles are registered as the one shared "blank" tile, never as index 1;
      - a sheet must not touch the roof squares of another building (they would hide together);
      - roof squares over open ground hide as soon as the player walks under them, and until then
        they hide everybody who does.
    Bit 29 of the square word (roof flag 2) makes a roof square that never hides and does not
    pass the flood fill on (TileSet.never_hide).

WHAT IS BUILT
    out/art/tiles/tiles.lst      the stock list + one line per tile slot
    out/art/tiles/mgtNNNN.frm    slot NNNN = tiles.lst index 3102 + NNNN (slot 0 is the blank tile)
    out/sheets/NAME.png          the whole sheet as a palette image (exact indices): what decals
                                 are composed from, and a picture to look at
manifest.json "tiles": {"first_index", "slots": [{"key"}...], "sheets": {name: {...}}}; a slot is
keyed "sheet/i,j" (or "sheet/i,j@base" for a decal tile laid over floor tile `base`) and keeps
its number for ever, exactly like the proto slots.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from f2lib import GameFiles, ids, lst      # noqa: E402
from f2lib.frm import Frame, Frm            # noqa: E402

from . import convert, data                 # noqa: E402
from . import tilegeo as TG                 # noqa: E402

PREFIX = "mgt"
LIMIT = 4096                                # tile indices are 12 bits
BLANK_KEY = "blank"
NO_TILE = 1                                 # the engine's "no tile here" index
ROOF_NEVER_HIDE = 0x20000000                # square word bit 29: roof flag 2
SHEETS_DIR = os.path.join(data.OUT, "sheets")
TILE_DIR = "art/tiles"

# Conversion defaults per kind, on top of convert.DEFAULTS (a sheet's own `convert` wins).
SHEET_CONVERT = {
    "roof": {"exposure": 0.45},                 # a roof faces the sky: stock roofs are twice as bright as stock walls
    "floor": {"outline": 0.0, "outline_lit": 0.0},
    "decal": {"outline": 0.30, "outline_lit": 0.08},
}
# Stock roofs, measured on the tiles themselves (luminance 0..255 of the opaque pixels): tin
# ruf1000 / ruf1001 mean 91, 5 / 50 / 95 % at 58 / 90 / 135; planks plk1000 / plk2000 mean 108,
# 58 / 113 / 147. Stock roofs are about twice as bright as stock walls.
STOCK_ROOF_LUMA = "stock roofs: tin mean 91 (58 / 90 / 135), planks mean 108 (58 / 113 / 147)"


def stock_mask():
    """(36, 80) bool: the opaque pixels of a full stock tile."""
    mask = np.zeros((TG.TILE_H, TG.TILE_W), bool)
    for y, (first, last) in enumerate(TG.STOCK_ROWS):
        mask[y, first:last + 1] = True
    return mask


def check_stock_mask(gf):
    """The mask in tilegeo.py against the game's own full tiles."""
    names = gf.art_list(ids.OBJ_TYPE_TILE)
    mask = stock_mask()
    for name in ("ruf1000.frm", "plk2000.frm", "cmt1000.frm"):
        frm = gf.art.load(ids.make_fid(ids.OBJ_TYPE_TILE, names.index(name)))
        if frm.size(0, 0) != (TG.TILE_W, TG.TILE_H) or not np.array_equal(frm.frame(0, 0).array() > 0, mask):
            raise AssertionError(f"tilegeo.STOCK_ROWS is not the mask of the stock tile {name}")
    return mask


def stock_count(gf=None):
    return len((gf or GameFiles()).art_list(ids.OBJ_TYPE_TILE))


# ------------------------------------------------------------------- manifest
def section(manifest, gf=None):
    """The manifest's "tiles" section (created on first use, with the blank tile as slot 0)."""
    tiles = manifest.get("tiles")
    if tiles is None:
        tiles = manifest["tiles"] = {
            "about": "Custom floor / roof tiles (pipeline/tiles.py). Slot i is art/tiles/tiles.lst index "
                     "first_index + i, file art/tiles/mgt<i:04d>.frm; append-only, edited only by build.py.",
            "first_index": stock_count(gf), "limit": LIMIT, "slots": [{"key": BLANK_KEY}], "sheets": {},
        }
    return tiles


def slot_name(slot):
    return f"{PREFIX}{slot:04d}.frm"


def slot_index(tiles, slot):
    return tiles["first_index"] + slot


def _claim(tiles, key):
    slots = tiles["slots"]
    slot = next((i for i, entry in enumerate(slots) if entry["key"] == key), None)
    if slot is None:
        slot = len(slots)
        if tiles["first_index"] + slot >= LIMIT:
            raise SystemExit(f"tiles: no index left for {key} (tiles.lst holds at most {LIMIT} lines; "
                             f"{len(slots)} custom slots are taken)")
        slots.append({"key": key})
    slots[slot].pop("retired", None)
    return slot


def budget(manifest):
    tiles = section(manifest)
    used = len(tiles["slots"])
    live = sum(1 for slot in tiles["slots"] if not slot.get("retired"))
    return {"used": used, "live": live, "free": LIMIT - tiles["first_index"] - used}


# -------------------------------------------------------------------- process
def tile_frm(pixels):
    frm = Frm()
    frm.stored = [[Frame(TG.TILE_W, TG.TILE_H, np.ascontiguousarray(pixels, np.uint8).tobytes())]]
    frm.direction_map = [0] * 6
    return frm.to_bytes()


def union_mask(n, m, mask, canvas, lift_px):
    """(h, w) bool over the canvas: the pixels some tile of an n x m sheet covers."""
    h, w = canvas[3] - canvas[1], canvas[2] - canvas[0]
    union = np.zeros((h, w), bool)
    for j in range(m):
        for i in range(n):
            bx, by = TG.box_px(i, j)
            x, y = bx - canvas[0], by - lift_px - canvas[1]
            union[y:y + TG.TILE_H, x:x + TG.TILE_W] |= mask
    return union


def assemble(grid_pixels, n, m, canvas, lift_px):
    """Paint tiles the way the engine does (qy rising, then qx rising) onto the canvas."""
    h, w = canvas[3] - canvas[1], canvas[2] - canvas[0]
    out = np.zeros((h, w), np.uint8)
    for j in range(m):
        for i in range(n):
            pixels = grid_pixels.get((i, j))
            if pixels is None:
                continue
            bx, by = TG.box_px(i, j)
            x, y = bx - canvas[0], by - lift_px - canvas[1]
            region = out[y:y + TG.TILE_H, x:x + TG.TILE_W]
            np.copyto(region, pixels, where=pixels > 0)
    return out


def eave_shadow(indices, mask, union, depth):
    """Stippled shadow under the roof's LOWER edge (what the stock eave tiles carry): the `depth`
    transparent pixels below the lowest roof pixel of every column become a black checkerboard.
    It is part of the roof, so it goes when the roof is hidden."""
    if depth <= 0:
        return 0
    h, w = mask.shape
    rows = np.arange(h)[:, None]
    lowest = np.where(mask.any(axis=0), h - 1 - np.argmax(mask[::-1], axis=0), -10 ** 6)[None, :]
    band = (rows > lowest) & (rows <= lowest + depth) & union & ~mask
    cols = np.arange(w)[None, :]
    fade = (rows - lowest) > depth * 0.6                    # thinner at its lower edge
    stipple = np.where(fade, ((rows + cols) % 2 == 0) & ((rows // 1 + cols // 2) % 2 == 0), (rows + cols) % 2 == 0)
    chosen = band & stipple
    indices[chosen] = convert.BLACK
    return int(chosen.sum())


def process(render_dir, palette, gf=None):
    """Rendered passes of one sheet -> {"tiles": {(i, j): (36, 80) uint8}, "indices", "report", ...}."""
    with open(os.path.join(render_dir, "meta.json")) as f:
        meta = json.load(f)
    spec = meta["spec"]
    name, kind, ss = meta["name"], spec["kind"], meta["ss"]
    n, m = spec["size"]
    canvas = tuple(meta["canvas"])
    lift_px = TG.ROOF_LIFT_PX if kind == "roof" else 0
    decal = bool(spec["decal"])
    opts = convert.options({**SHEET_CONVERT["decal" if decal else kind], **(spec.get("convert") or {})})
    quantiser = convert.Quantiser(palette, opts)
    mask_tile = check_stock_mask(gf or GameFiles())
    union = union_mask(n, m, mask_tile, canvas, lift_px)
    report = {"name": name, "warnings": []}

    rgba = convert.load_rgba(os.path.join(render_dir, "main_f000.png"))
    indices, mask, rgb, alpha = convert.convert_frame(rgba, ss, quantiser, opts)
    if indices.shape != union.shape:
        raise AssertionError(f"sheet {name}: render is {indices.shape}, the sheet's canvas is {union.shape}")
    fx_pixels = {}
    for fx in meta.get("fx", ()):
        fx_path = os.path.join(render_dir, f"fx_{fx}_f000.png")
        if os.path.exists(fx_path):
            _, fx_alpha = convert.downsample(convert.load_rgba(fx_path), ss)
            fx_pixels[fx] = convert.apply_fx(indices, rgb, mask, fx_alpha, fx)
    shadow_path = os.path.join(render_dir, "shadow.png")
    if decal and spec["shadow"] and os.path.exists(shadow_path):
        _, total_alpha = convert.downsample(convert.load_rgba(shadow_path), ss)
        shadow, _ = convert.shadow_mask(total_alpha, alpha, opts, origin=(canvas[0], canvas[1]))
        shadow &= ~mask
        indices[shadow] = convert.BLACK
        mask = mask | shadow
        report["shadow_pixels"] = int(shadow.sum())
    outside = int((mask & ~union).sum())
    indices[~union] = 0
    mask = mask & union
    if kind == "roof":
        report["eave_shadow_pixels"] = eave_shadow(indices, mask, union, int(spec["eave_shadow"]))
    covered = int(mask.sum())
    report["coverage"] = round(covered / int(union.sum()), 4)
    report["outside_px"] = outside
    if kind == "floor" and not decal and covered != int(union.sum()):
        ys, xs = np.nonzero(union & ~mask)
        raise SystemExit(f"sheet {name}: a floor sheet must be solid, {len(ys)} px of its squares are unpainted "
                         f"(first at canvas px ({xs[0] + canvas[0]}, {ys[0] + canvas[1]})): extend the ground "
                         f"beyond the sheet's edge, or make it decal=True")

    tiles, blank = {}, []
    for j in range(m):
        for i in range(n):
            bx, by = TG.box_px(i, j)
            x, y = bx - canvas[0], by - lift_px - canvas[1]
            pixels = np.where(mask_tile, indices[y:y + TG.TILE_H, x:x + TG.TILE_W], 0).astype(np.uint8)
            if pixels.any():
                tiles[(i, j)] = pixels
            else:
                blank.append((i, j))
    if not np.array_equal(assemble(tiles, n, m, canvas, lift_px), indices):
        raise AssertionError(f"sheet {name}: the cut tiles do not reproduce the sheet")
    report["reassembly"] = "exact"
    report["tiles"] = len(tiles)
    report["blank"] = len(blank)
    report["fx_pixels"] = fx_pixels
    for fx, count in fx_pixels.items():
        if count == 0:
            report["warnings"].append(f"objects tagged fx={fx!r} cover no whole pixel: make them thicker")
    solid = indices[(indices > 0) & (indices != convert.BLACK)]
    luma = palette.rgb[solid].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    report["mean_luminance"] = round(float(luma.mean()), 1) if len(luma) else 0.0
    report["luminance_p5_p50_p95"] = [int(round(float(np.percentile(luma, q)))) for q in (5, 50, 95)] if len(luma) else []
    report["ramps"] = convert.ramp_histogram(indices)
    report["size_px"] = [canvas[2] - canvas[0], canvas[3] - canvas[1]]
    report["height_m"] = meta.get("height_m")
    if kind == "roof" and outside > 40 and not spec["wrap"]:
        report["warnings"].append(f"{outside} px of the picture lie outside the sheet's squares and are cut off "
                                  f"(things standing near the far edges, or geometry beyond 0..w / 0..h)")
    if spec["wrap"] and report["coverage"] < 1.0 and kind == "roof":
        report["warnings"].append("a wrapping roof sheet with holes: fine, but every repeat has the same holes")
    return {"name": name, "spec": spec, "meta": meta, "canvas": canvas, "lift_px": lift_px, "indices": indices,
            "tiles": tiles, "blank": blank, "report": report}


# ------------------------------------------------------------------- register
def register(manifest, result, script, gf=None):
    """Give every tile of a processed sheet its slot and write the sheet's manifest entry."""
    tiles = section(manifest, gf)
    name, spec = result["name"], result["spec"]
    n, m = spec["size"]
    decal = bool(spec["decal"])
    live = set()
    grid = [[None] * n for _ in range(m)]
    result["slots"] = {}
    if not decal:
        for (i, j) in result["tiles"]:
            slot = _claim(tiles, f"{name}/{i},{j}")
            live.add(slot)
            grid[j][i] = slot_index(tiles, slot)
            result["slots"][(i, j)] = slot
        blank = slot_index(tiles, 0) if spec["kind"] == "roof" else None
        for (i, j) in result["blank"]:
            grid[j][i] = blank
    for slot, entry in enumerate(tiles["slots"]):
        owner = entry["key"].split("/")[0]
        if owner != name:
            continue
        composite = "@" in entry["key"]
        if composite and decal:
            continue                                        # kept: recomposed by recompose()
        if slot not in live:
            entry["retired"] = True
    tiles["sheets"][name] = {
        "script": script, "kind": spec["kind"], "size": [n, m], "wrap": bool(spec["wrap"]), "decal": decal,
        "title": spec["title"],
        "grid": grid if not decal else None,
        "grid_is": "tiles.lst index of sheet square (i, j) at grid[j][i]; the blank roof tile where the picture "
                   "is empty" if not decal else "decal: tiles are composed per floor tile, see slots keyed name/i,j@base",
        "cells": sorted([list(k) for k in result["tiles"]]),
        "picture": f"sheets/{name}.png", "canvas": list(result["canvas"]),
        "report": result["report"],
    }
    return tiles["sheets"][name]


def write_sheet_files(result, palette, out_dir=None):
    """The sheet's own tiles and its palette picture (inside the manifest lock, like part files)."""
    from PIL import Image
    out_dir = out_dir or data.OUT
    for cell, slot in result.get("slots", {}).items():
        data._write(out_dir, f"{TILE_DIR}/{slot_name(slot)}", tile_frm(result["tiles"][cell]))
    image = Image.fromarray(result["indices"], "P")
    flat = palette.rgb.astype(np.uint8).reshape(-1).tolist()
    image.putpalette(flat)
    path = os.path.join(out_dir, "sheets", result["name"] + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, transparency=0, optimize=False)


def load_sheet_picture(name, out_dir=None):
    """(h, w) uint8 palette indices of a built sheet."""
    from PIL import Image
    path = os.path.join(out_dir or data.OUT, "sheets", name + ".png")
    image = Image.open(path)
    if image.mode != "P":
        raise ValueError(f"{path} is not a palette image")
    return np.asarray(image, np.uint8)


def decal_tile(entry, i, j, out_dir=None, picture=None):
    """(36, 80) uint8 of a decal sheet's square (i, j): 0 where the ground shows."""
    picture = load_sheet_picture(entry_name(entry), out_dir) if picture is None else picture
    canvas = entry["canvas"]
    bx, by = TG.box_px(i, j)
    x, y = bx - canvas[0], by - canvas[1]
    return np.where(stock_mask(), picture[y:y + TG.TILE_H, x:x + TG.TILE_W], 0).astype(np.uint8)


def entry_name(entry):
    return os.path.splitext(os.path.basename(entry["picture"]))[0]


def base_pixels(gf, index):
    frm = gf.art.load(ids.make_fid(ids.OBJ_TYPE_TILE, index))
    pixels = frm.frame(0, 0).array()
    if pixels.shape != (TG.TILE_H, TG.TILE_W):
        padded = np.zeros((TG.TILE_H, TG.TILE_W), np.uint8)
        padded[:min(TG.TILE_H, pixels.shape[0]), :min(TG.TILE_W, pixels.shape[1])] = pixels[:TG.TILE_H, :TG.TILE_W]
        pixels = padded
    return pixels


def base_key(gf, index):
    return os.path.splitext(gf.art_list(ids.OBJ_TYPE_TILE).name(index))[0].lower()


def recompose(manifest, name, gf, out_dir=None):
    """Rebuild every composed tile of decal sheet `name` (after the sheet was rendered again)."""
    tiles = section(manifest)
    entry = tiles["sheets"][name]
    picture = load_sheet_picture(name, out_dir)
    names = gf.art_list(ids.OBJ_TYPE_TILE)
    count = 0
    for slot, record in enumerate(tiles["slots"]):
        key = record["key"]
        if not key.startswith(name + "/") or "@" not in key or record.get("retired"):
            continue
        cell, base = key[len(name) + 1:].split("@")
        i, j = (int(v) for v in cell.split(","))
        if [i, j] not in entry["cells"]:
            record["retired"] = True
            continue
        over = decal_tile(entry, i, j, out_dir, picture)
        under = base_pixels(gf, names.index(base + ".frm"))
        data._write(out_dir or data.OUT, f"{TILE_DIR}/{slot_name(slot)}", tile_frm(np.where(over > 0, over, under)))
        count += 1
    return count


def drop(manifest, name):
    """Take a sheet out of the manifest. Its slots are given back when they are the LAST ones of the
    list (nothing was registered after it); otherwise they stay, retired and blank. Working copy
    only: once a tile index has shipped in a map it must never be reused."""
    tiles = section(manifest)
    if name not in tiles["sheets"]:
        raise SystemExit(f"no tile sheet {name!r} in manifest.json")
    del tiles["sheets"][name]
    slots = tiles["slots"]
    for entry in slots:
        if entry["key"].split("/")[0] == name:
            entry["retired"] = True
            entry["dropped"] = True
    freed = 0
    while len(slots) > 1 and slots[-1].get("dropped"):
        slots.pop()
        freed += 1
    return freed


def write_data(manifest, out_dir=None):
    """tiles.lst (stock + our lines) and a blank FRM for the blank tile and every retired slot."""
    out_dir = out_dir or data.OUT
    tiles = section(manifest)
    gf = GameFiles()
    stock = gf.read("art/tiles/tiles.lst")
    if stock_count(gf) != tiles["first_index"]:
        raise SystemExit(f"tiles: the stock tiles.lst has {stock_count(gf)} lines, the manifest says {tiles['first_index']}")
    blank = tile_frm(np.zeros((TG.TILE_H, TG.TILE_W), np.uint8))
    lines = []
    for slot, entry in enumerate(tiles["slots"]):
        lines.append(slot_name(slot))
        if entry["key"] == BLANK_KEY or entry.get("retired"):
            data._write(out_dir, f"{TILE_DIR}/{slot_name(slot)}", blank)
    data._write(out_dir, f"{TILE_DIR}/tiles.lst", lst.append_lines(stock, lines))
    folder = os.path.join(out_dir, *TILE_DIR.split("/"))
    for stale in os.listdir(folder):                         # files of slots that were given back (drop)
        if stale.startswith(PREFIX) and stale.endswith(".frm") and stale not in lines:
            os.remove(os.path.join(folder, stale))
    return len(lines)


def verify(manifest, out_dir=None):
    """Read the tiles back the way the engine will and check them against the manifest."""
    out_dir = out_dir or data.OUT
    tiles = section(manifest)
    gf = GameFiles(overlay=out_dir)
    stock = GameFiles()
    problems = []
    names = gf.art_list(ids.OBJ_TYPE_TILE)
    stock_names = stock.art_list(ids.OBJ_TYPE_TILE)
    if list(names)[:len(stock_names)] != list(stock_names) or len(names) != len(stock_names) + len(tiles["slots"]):
        problems.append(f"art/tiles/tiles.lst is not the stock list plus {len(tiles['slots'])} lines")
        return problems
    if len(names) > LIMIT:
        problems.append(f"tiles.lst has {len(names)} lines; the engine can address {LIMIT}")
    mask = stock_mask()
    for slot, entry in enumerate(tiles["slots"]):
        index = slot_index(tiles, slot)
        if names.name(index).lower() != slot_name(slot):
            problems.append(f"tiles.lst line {index} is {names.name(index)}, not {slot_name(slot)}")
            continue
        try:
            frm = gf.art.load(ids.make_fid(ids.OBJ_TYPE_TILE, index))
        except Exception as error:          # noqa: BLE001 - any failure is a finding
            problems.append(f"tile {slot_name(slot)} ({entry['key']}) unreadable: {error}")
            continue
        pixels = frm.frame(0, 0).array()
        if frm.size(0, 0) != (TG.TILE_W, TG.TILE_H) or frm.frame_count != 1 or tuple(frm.shift(0)) != (0, 0):
            problems.append(f"tile {slot_name(slot)}: {frm.size(0, 0)}, {frm.frame_count} frame(s), shift {frm.shift(0)}")
        elif "@" not in entry["key"] and (pixels[~mask] != 0).any():
            # (a composed decal tile keeps the outline of the floor tile it lies on: some stock grounds,
            # the edg* desert for one, are a few pixels larger than the standard tile)
            problems.append(f"tile {slot_name(slot)}: pixels outside the stock rhombus")
        elif (entry["key"] == BLANK_KEY or entry.get("retired")) and pixels.any():
            problems.append(f"tile {slot_name(slot)} ({entry['key']}) should be blank")
    for name, entry in tiles["sheets"].items():
        if entry["decal"]:
            continue
        n, m = entry["size"]
        if len(entry["grid"]) != m or any(len(row) != n for row in entry["grid"]):
            problems.append(f"sheet {name}: grid is not {n} x {m}")
        for j, row in enumerate(entry["grid"]):
            for i, index in enumerate(row):
                if index is None:
                    if entry["kind"] == "roof":
                        problems.append(f"sheet {name}: roof square ({i}, {j}) has no tile")
                    continue
                slot = index - tiles["first_index"]
                if not 0 <= slot < len(tiles["slots"]):
                    problems.append(f"sheet {name}: square ({i}, {j}) names tile {index}, which does not exist")
                elif slot and tiles["slots"][slot]["key"] != f"{name}/{i},{j}":
                    problems.append(f"sheet {name}: square ({i}, {j}) points at {tiles['slots'][slot]['key']}")
    return problems


# ---------------------------------------------------------------------- paint
class TileSet:
    """Paint built sheets onto a map (f2lib MapFile). The map's GameFiles must see the art's out/
    tree (GameFiles(overlay=[..., TileSet().overlay])) for renders and checks to find the tiles.

        ts = TileSet()
        ts.reroof(m, plan.BUILDINGS["clinic"]["box"], "rf_clinic")      # a sheet made for that shack
        ts.paint_roof(m, "rf_leanto", qx0, qy0)                          # any sheet, first square at (qx0, qy0)
        ts.fill_roof(m, "rf_tin_a", squares)                             # a wrap sheet over any set of squares
        ts.paint_floor(m, "fl_plates", qx0, qy0)                         # solid floor sheet
        ts.paint_floor(m, "fl_junk_a", qx0, qy0)                         # decal: laid over the floor that is there
        ts.fill_floor(m, "fl_grit", squares)                             # wrap sheet (solid or decal)
        ts.flush()                                                       # after decals: lists and archive

    Squares are (qx, qy) of the 100 x 100 grid: qx = hx // 2, qy = hy // 2 for the hex the engine
    tests; +qx is towards the screen's lower left, +qy towards its lower right.
    """

    def __init__(self, manifest=None, gf=None, out_dir=None):
        self.manifest = manifest or data.load_manifest()
        self.tiles = section(self.manifest)
        self.out_dir = out_dir or data.OUT
        self.overlay = self.out_dir
        self.gf = gf or GameFiles(overlay=self.out_dir)
        self.dirty = False
        self._pictures = {}
        self.frozen = os.path.isfile(os.path.join(data.ART, "sprites", "manifest.json"))

    # .................................................................. look-ups
    def names(self):
        return list(self.tiles["sheets"])

    def sheet(self, name):
        try:
            return self.tiles["sheets"][name]
        except KeyError:
            raise KeyError(f"no tile sheet {name!r} in manifest.json (has: {', '.join(self.names()) or 'none'})") from None

    @property
    def blank(self):
        """tiles.lst index of the fully transparent roof tile (a roof square that shows nothing)."""
        return slot_index(self.tiles, 0)

    def index(self, name, i, j):
        """tiles.lst index of sheet square (i, j) (wraps for a wrap sheet); None for an empty floor cell."""
        entry = self.sheet(name)
        n, m = entry["size"]
        if entry["wrap"]:
            i, j = i % n, j % m
        if entry["decal"]:
            raise ValueError(f"{name} is a decal: its tiles depend on the floor under them (paint_floor)")
        return entry["grid"][j][i]

    # ..................................................................... roofs
    def _need(self, name, kind):
        entry = self.sheet(name)
        if entry["kind"] != kind:
            raise ValueError(f"sheet {name} is a {entry['kind']} sheet, not a {kind}")
        return entry

    def paint_roof(self, m, name, qx0, qy0, elevation=0, only=None):
        """Lay sheet `name` with its square (0, 0) on map square (qx0, qy0). Returns the squares set.
        only: a set of (qx, qy) to restrict it to."""
        entry = self._need(name, "roof")
        n, rows = entry["size"]
        painted = []
        for j in range(rows):
            for i in range(n):
                square = (qx0 + i, qy0 + j)
                if only is not None and square not in only:
                    continue
                m.set_roof(square[0], square[1], entry["grid"][j][i], elevation)
                painted.append(square)
        return painted

    def fill_roof(self, m, name, squares, phase=(0, 0), elevation=0):
        """Cover `squares` with a WRAP sheet; map square (qx, qy) shows sheet square
        ((qx - phase[0]) mod N, (qy - phase[1]) mod M)."""
        entry = self._need(name, "roof")
        if not entry["wrap"]:
            raise ValueError(f"sheet {name} does not wrap: use paint_roof")
        n, rows = entry["size"]
        for qx, qy in squares:
            m.set_roof(qx, qy, entry["grid"][(qy - phase[1]) % rows][(qx - phase[0]) % n], elevation)
        return list(squares)

    def reroof(self, m, box, name, elevation=0, edges=False):
        """Give the stock shack `box` (hx_lo, hy_lo, hx_hi, hy_hi) the roof sheet `name`, which must
        have exactly the shack's roof squares (tilegeo.Shack(box).size), or be a wrap sheet. A wrap
        sheet only fills the roof FIELD: the first and the last row keep the stock trim and eave
        tiles (they are half-tiles with a ragged edge; edges=True overwrites them with full squares,
        a roof that sticks out 1.5 m at the back and 1.6 m at the front)."""
        shack = TG.Shack(box)
        entry = self._need(name, "roof")
        if entry["wrap"]:
            rows = range(shack.size[1]) if edges else range(1, shack.size[1] - 1)
            squares = [(shack.first[0] + i, shack.first[1] + j) for j in rows for i in range(shack.size[0])]
            return self.fill_roof(m, name, squares, phase=shack.first, elevation=elevation)
        if tuple(entry["size"]) != shack.size:
            raise ValueError(f"sheet {name} is {entry['size'][0]} x {entry['size'][1]} squares; the roof of shack "
                             f"{tuple(box)} is {shack.size[0]} x {shack.size[1]}")
        return self.paint_roof(m, name, shack.first[0], shack.first[1], elevation)

    @staticmethod
    def never_hide(m, squares, on=True, elevation=0):
        """Roof squares that stay when the player walks under them and do not pass the roof flood
        fill on (square word bit 29). For roofs over ground nobody can stand on."""
        for qx, qy in squares:
            square = qy * 100 + qx
            word = int(m.tiles[elevation][square])
            m.tiles[elevation][square] = (word | ROOF_NEVER_HIDE) if on else (word & ~ROOF_NEVER_HIDE)

    @staticmethod
    def clear_roof(m, squares, elevation=0):
        for qx, qy in squares:
            m.set_roof(qx, qy, NO_TILE, elevation)

    # .................................................................... floors
    def _decal_index(self, name, entry, i, j, base_index):
        """tiles.lst index of decal square (i, j) laid over floor tile `base_index` (made on demand)."""
        if [i, j] not in entry["cells"]:
            return None                                     # nothing of the decal on this square
        key = f"{name}/{i},{j}@{base_key(self.gf, base_index)}"
        slots = self.tiles["slots"]
        slot = next((s for s, record in enumerate(slots) if record["key"] == key and not record.get("retired")), None)
        if slot is not None:
            if self.frozen and not os.path.isfile(os.path.join(self.out_dir, TILE_DIR, slot_name(slot))):
                raise ValueError("A frozen composite is missing; run python megaton.py setup.")
            return slot_index(self.tiles, slot)
        if self.frozen:
            raise ValueError("This layout needs a new tile. Rebuild and review the art manifest with the author tools before refreshing committed sprites.")
        over = decal_tile(entry, i, j, self.out_dir, self._picture(name))
        under = base_pixels(self.gf, base_index)
        pixels = tile_frm(np.where(over > 0, over, under))
        if self.out_dir == data.OUT:
            with data.locked_manifest() as manifest:        # another author may be adding tiles right now
                tiles = section(manifest)
                slot = _claim(tiles, key)
                data._write(self.out_dir, f"{TILE_DIR}/{slot_name(slot)}", pixels)
                write_data(manifest, self.out_dir)
                self.manifest, self.tiles = manifest, tiles
        else:                                               # a preview's private tree: nothing is registered
            slot = _claim(self.tiles, key)
            data._write(self.out_dir, f"{TILE_DIR}/{slot_name(slot)}", pixels)
            write_data(self.manifest, self.out_dir)
        self.gf.refresh()
        self.dirty = True
        return slot_index(self.tiles, slot)

    def _picture(self, name):
        if name not in self._pictures:
            self._pictures[name] = load_sheet_picture(name, self.out_dir)
        return self._pictures[name]

    def _floor_cell(self, m, name, entry, i, j, qx, qy, elevation):
        if entry["decal"]:
            index = self._decal_index(name, entry, i, j, m.floor(qx, qy, elevation))
        else:
            index = entry["grid"][j][i]
        if index is not None:
            m.set_floor(qx, qy, index, elevation)
        return index

    def paint_floor(self, m, name, qx0, qy0, elevation=0, only=None):
        """Lay floor sheet `name` with its square (0, 0) on map square (qx0, qy0). A decal is laid over
        the floor tile that is there (lay the terrain first; laying two decals on one square stacks them)."""
        entry = self._need(name, "floor")
        n, rows = entry["size"]
        painted = []
        for j in range(rows):
            for i in range(n):
                square = (qx0 + i, qy0 + j)
                if only is not None and square not in only:
                    continue
                if self._floor_cell(m, name, entry, i, j, square[0], square[1], elevation) is not None:
                    painted.append(square)
        return painted

    def fill_floor(self, m, name, squares, phase=(0, 0), elevation=0):
        entry = self._need(name, "floor")
        if not entry["wrap"]:
            raise ValueError(f"sheet {name} does not wrap: use paint_floor")
        n, rows = entry["size"]
        for qx, qy in squares:
            self._floor_cell(m, name, entry, (qx - phase[0]) % n, (qy - phase[1]) % rows, qx, qy, elevation)
        return list(squares)

    def flush(self):
        """After painting decals: repack out/patch-art.dat so it holds the tiles made on demand."""
        if self.dirty:
            with data.locked_manifest() as manifest:
                write_data(manifest, self.out_dir)
                if self.out_dir == data.OUT:
                    data.pack()
            self.dirty = False


def custom_roof_squares(m, manifest=None, elevation=0):
    """{(qx, qy): tiles.lst index} of the squares of map `m` that carry a custom roof tile."""
    first = section(manifest or data.load_manifest())["first_index"]
    words = m.tiles[elevation]
    roofs = (words >> 16) & 0xFFF
    return {(int(sq) % 100, int(sq) // 100): int(roofs[sq]) for sq in np.flatnonzero(roofs >= first)}
