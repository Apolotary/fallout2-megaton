#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Labelled thumbnail sheets of game art, for picking assets by eye.

    python3 tools/contact_sheet.py scenery --name 'junk|car|barrel' -o sheets/junk
    python3 tools/contact_sheet.py walls --used-in klamall --used-in kladwtwn -o sheets/klamath-walls
    python3 tools/contact_sheet.py walls --pid 0x03000200-0x03000260 --directions -o sheets/walls-dirs
    python3 tools/contact_sheet.py tiles --name '^(edg|shr)' -o sheets/dirt
    python3 tools/contact_sheet.py critters --name 'ghoul|robot|brahmin' --unique-art --directions -o sheets/critters

Writes <out>-01.png, <out>-02.png ... (a limited number of cells each, so a
sheet stays readable on one screen) and <out>.txt, one line per cell.

A cell shows the sprite (direction 0, or all six with --directions) and under it

    PID                      and, with --used-in, how often the maps use it
    art file and its size    sprites larger than the cell are scaled down
    proto name
    walls / scenery: what the proto's flags do (see `flag_text`)

The outlined hexagon is the hex the object stands on, so the picture also
shows how far the art reaches from its own hex. Tiles have no PID in a map: their
cell gives the tile id that goes into the map's floor / roof squares.

As a library: `collect()` returns the entries, `make_sheets()` draws them.
"""
import argparse
import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from f2lib import GameFiles, ids  # noqa: E402
from f2lib.map import OBJECT_FLAT, OBJECT_LIGHT_THRU, OBJECT_MULTIHEX, OBJECT_NO_BLOCK, OBJECT_SHOOT_THRU  # noqa: E402
from render_map import load_font, load_map  # noqa: E402

TYPES = {"items": ids.OBJ_TYPE_ITEM, "critters": ids.OBJ_TYPE_CRITTER, "scenery": ids.OBJ_TYPE_SCENERY,
         "walls": ids.OBJ_TYPE_WALL, "tiles": ids.OBJ_TYPE_TILE, "misc": ids.OBJ_TYPE_MISC}
DIRECTIONS = ("NE", "E", "SE", "SW", "W", "NW")
# Wall orientation bits of flags_ext (object.cc:4552-4582); names from the community PRO reference.
WALL_ORIENTATION = ((0x08000000, "EW"), (0x10000000, "Ncorner"), (0x20000000, "Scorner"),
                    (0x40000000, "Ecorner"), (0x80000000, "Wcorner"))
TRANS_NAMES = {0x4000: "red", 0x10000: "see-thru", 0x20000: "glass", 0x40000: "steam", 0x80000: "energy"}
LEGEND = ("BLK blocks movement / walk does not   FLAT drawn with the floor   L light passes   S shots pass   "
          "MH also blocks the 6 hexes around   walls: NS / EW / corner = orientation")

BACKGROUND = (40, 40, 46)
CELL_FILL = (74, 74, 84)                 # mid grey: the many near-black sprites keep their outline
CELL_LINE = (112, 112, 124)
HEX_LINE = (120, 235, 255, 150)
TEXT = (240, 240, 240)
TEXT_DIM = (196, 196, 206)
TEXT_ID = (255, 225, 90)
FONT_SIZE = 11
LINE_HEIGHT = 13
HEADER_HEIGHT = 34


def flag_text(proto):
    """Short description of what a wall / scenery proto's flags do to the hex it stands on."""
    flags = proto.flags
    words = ["walk" if flags & OBJECT_NO_BLOCK else "BLK"]
    if flags & OBJECT_FLAT:
        words.append("FLAT")
    if flags & OBJECT_LIGHT_THRU:
        words.append("L")
    if flags & OBJECT_SHOOT_THRU:
        words.append("S")
    if flags & OBJECT_MULTIHEX:
        words.append("MH")
    for bit, name in TRANS_NAMES.items():
        if flags & bit:
            words.append(name)
            break
    if proto.obj_type == ids.OBJ_TYPE_WALL:
        words.append(next((name for bit, name in WALL_ORIENTATION if proto.flags_ext & bit), "NS"))
    elif proto.subtype_name not in ("", "generic"):
        words.append(proto.subtype_name)
    return " ".join(words)


def parse_ranges(texts, obj_type):
    """['0x02000100-0x02000120', '300', '40-60'] -> [(low, high)] of proto indices (tile ids for tiles)."""
    ranges = []
    for text in texts:
        for part in filter(None, re.split(r"[,\s]+", text)):
            low, _, high = part.partition("-")
            values = [int(v, 0) for v in (low, high or low)]
            if obj_type != ids.OBJ_TYPE_TILE:
                values = [ids.pid_index(v) for v in values]
            ranges.append((min(values), max(values)))
    return ranges


def usage(game_maps, obj_type):
    """{pid: count} over the top-level objects and their inventories; for tiles {tile id: (floors, roofs)}."""
    counts = {}
    for game_map in game_maps:
        if obj_type == ids.OBJ_TYPE_TILE:
            for squares in game_map.tiles.values():
                for shift, slot in ((0, 0), (16, 1)):
                    values, numbers = np.unique((squares >> shift) & 0xFFF, return_counts=True)
                    for value, number in zip(values.tolist(), numbers.tolist()):
                        if value != 1:
                            pair = counts.setdefault(value, [0, 0])
                            pair[slot] += number
        else:
            for obj in game_map.all_objects(nested=True):
                if obj.obj_type == obj_type and obj.pid != -1:
                    counts[obj.pid] = counts.get(obj.pid, 0) + 1
    return counts


def collect(gf, obj_type, name=None, pid_ranges=None, used_in=None, unique_art=False, sort=None):
    """Entries (dicts) for the cells of a sheet.

    name        regular expression searched (ignoring case) in the proto name and the art file name
    pid_ranges  [(low, high)] proto indices, inclusive (tile ids for tiles)
    used_in     list of MapFile: only what those maps use; entries get a "count"
    unique_art  keep one entry per art file (the first proto's PID); "same_art" then holds the number
                of protos sharing it and "name" all their names
    sort        'pid' (default), 'name', 'art' or 'count' (default with used_in)

    Entry keys: type, pid (None for tiles), index, fid, art, name, info, count, same_art.
    """
    pattern = re.compile(name, re.IGNORECASE) if name else None
    counts = usage(used_in, obj_type) if used_in else None
    protos = gf.protos
    art_names = gf.art_list(obj_type)
    entries = []

    if obj_type == ids.OBJ_TYPE_TILE:
        proto_names = {}
        for pid in protos.pids(obj_type):
            if protos.exists(pid):
                proto_names.setdefault(ids.fid_index(protos.get(pid).fid), protos.name(pid) or "")
        candidates = [(None, index, ids.make_fid(obj_type, index), proto_names.get(index, ""), "")
                      for index in range(len(art_names))]
    else:
        candidates = []
        for pid in protos.pids(obj_type):
            if not protos.exists(pid):
                continue
            proto = protos.get(pid)
            info = flag_text(proto) if obj_type in (ids.OBJ_TYPE_WALL, ids.OBJ_TYPE_SCENERY) else proto.subtype_name
            candidates.append((pid, ids.pid_index(pid), proto.fid, protos.name(pid) or "", info))

    seen_art = {}
    for pid, index, fid, proto_name, info in candidates:
        key = index if pid is None else pid
        if counts is not None and key not in counts:
            continue
        if pid_ranges and not any(low <= index <= high for low, high in pid_ranges):
            continue
        path = gf.art.path(fid)
        art = os.path.basename(path) if path else "?"
        if pattern and not (pattern.search(proto_name) or pattern.search(art)):
            continue
        count = counts[key] if counts is not None else None
        if unique_art and fid in seen_art:
            first = seen_art[fid]
            first["same_art"] += 1
            if count is not None:
                first["count"] += count
            if proto_name and proto_name not in first["name"].split(" / "):
                first["name"] += " / " + proto_name
            continue
        entry = {"type": obj_type, "pid": pid, "index": index, "fid": fid, "art": art, "name": proto_name,
                 "info": info, "count": count, "same_art": 1}
        seen_art[fid] = entry
        entries.append(entry)

    def total(entry):
        return sum(entry["count"]) if isinstance(entry["count"], list) else (entry["count"] or 0)

    sort = sort or ("count" if counts is not None else "pid")
    if sort == "count":
        entries.sort(key=lambda e: -total(e))
    elif sort == "name":
        entries.sort(key=lambda e: (e["name"].lower(), e["index"]))
    elif sort == "art":
        entries.sort(key=lambda e: (e["art"], e["index"]))
    return entries


def entry_id(entry):
    return f"tile {entry['index']}" if entry["pid"] is None else f"{entry['pid']:08X}"


def count_text(entry):
    count = entry["count"]
    if count is None:
        return ""
    if isinstance(count, list):
        return " ".join(f"{label}{n}" for label, n in zip("FR", count) if n)
    return f"x{count}"


def _thumbnail(gf, entry, direction, box, show_hex, zoom=1):
    """RGBA picture of one direction's first frame fitted into `box`, and the frame's real size."""
    try:
        frm = gf.art.load(entry["fid"])
        frame = frm.frame(direction, 0)
    except (FileNotFoundError, ValueError, KeyError, IndexError):
        return None, None
    left, top, width, height = frm.placement(direction, 0)
    # Everything is laid out relative to the hex centre; the hex cell is 32x16 around it.
    x0, y0, x1, y1 = left, top, left + width, top + height
    if show_hex:
        x0, y0, x1, y1 = min(x0, -16), min(y0, -8), max(x1, 17), max(y1, 9)
    picture = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    picture.alpha_composite(Image.fromarray(gf.palette.rgba[frame.array()]), (left - x0, top - y0))
    if show_hex:
        outline = Image.new("RGBA", picture.size, (0, 0, 0, 0))
        corners = [(16, 0), (32, 4), (32, 12), (16, 16), (0, 12), (0, 4)]
        ImageDraw.Draw(outline).polygon([(-16 - x0 + cx, -8 - y0 + cy) for cx, cy in corners], outline=HEX_LINE)
        picture.alpha_composite(outline)
    scale = min(float(zoom), box[0] / picture.width, box[1] / picture.height)
    if scale != 1:
        size = (max(1, int(picture.width * scale)), max(1, int(picture.height * scale)))
        picture = picture.resize(size, Image.NEAREST if scale == int(scale) else Image.LANCZOS)
    return picture, (width, height)


def _fit(draw, text, font, width):
    """`text` cut to `width` pixels, ending in '..' when shortened."""
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "..", font=font) > width:
        text = text[:-1]
    return text + ".."


def make_sheets(gf, entries, out_prefix, title="", directions=False, show_hex=None, sheet_size=(1540, 1400),
                columns=None, write_index=True, zoom=1):
    """Draw `entries` (from `collect`) onto numbered PNG sheets; returns the list of files written.

    directions  six thumbnails per cell (NE .. NW) instead of direction 0
    show_hex    outline the object's own hex over the sprite (default: for everything but tiles)
    sheet_size  largest sheet in pixels; the cell size follows the sprites (the 90th percentile, within
                limits - the few larger ones are scaled down, their real size is in the label)
    zoom        integer magnification of the thumbnails (small, dark wall pieces read better at 2)
    """
    if not entries:
        return []
    obj_type = entries[0]["type"]
    if show_hex is None:
        show_hex = obj_type != ids.OBJ_TYPE_TILE
    font = load_font(FONT_SIZE)
    small = load_font(FONT_SIZE - 2)
    shown = range(6) if directions else (0,)

    # Cell geometry from the art itself.
    widths, heights = [32], [16]
    for entry in entries:
        try:
            frm = gf.art.load(entry["fid"])
            for direction in shown:
                left, top, w, h = frm.placement(direction, 0)
                if show_hex:
                    w, h = max(left + w, 17) - min(left, -16), max(top + h, 9) - min(top, -8)
                widths.append(w * zoom)
                heights.append(h * zoom)
        except (FileNotFoundError, ValueError, KeyError, IndexError):
            continue
    widest, tallest = int(np.percentile(widths, 90)), int(np.percentile(heights, 90))
    if directions:
        thumb_w = min(max(widest, 36), 84 * zoom)
        thumb_h = min(max(tallest, 30), 150 * zoom)
        cell_w = max(6 * (thumb_w + 4) + 8, 300)
    else:
        thumb_w = min(max(widest, 124), 190 * zoom)
        thumb_h = min(max(tallest, 30), 160 * zoom)
        cell_w = thumb_w + 10
    label_lines = 4 if obj_type in (ids.OBJ_TYPE_WALL, ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_ITEM) else 3
    cell_h = thumb_h + (12 if directions else 0) + label_lines * LINE_HEIGHT + 10
    columns = columns or max(1, sheet_size[0] // cell_w)
    rows = max(1, (sheet_size[1] - HEADER_HEIGHT) // cell_h)
    per_sheet = columns * rows
    pages = math.ceil(len(entries) / per_sheet)

    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    files = []
    index_lines = []
    for page in range(pages):
        chunk = entries[page * per_sheet:(page + 1) * per_sheet]
        used_rows = math.ceil(len(chunk) / columns)
        sheet = Image.new("RGB", (columns * cell_w + 1, HEADER_HEIGHT + used_rows * cell_h + 1), BACKGROUND)
        draw = ImageDraw.Draw(sheet)
        draw.text((6, 3), _fit(draw, f"{title}   [{page + 1}/{pages}]", font, sheet.width - 12), font=font, fill=TEXT)
        if obj_type in (ids.OBJ_TYPE_WALL, ids.OBJ_TYPE_SCENERY):
            draw.text((6, 19), _fit(draw, LEGEND, small, sheet.width - 12), font=small, fill=TEXT_DIM)
        for slot, entry in enumerate(chunk):
            x = slot % columns * cell_w
            y = HEADER_HEIGHT + slot // columns * cell_h
            draw.rectangle((x, y, x + cell_w, y + cell_h), fill=CELL_FILL, outline=CELL_LINE)
            size = None
            for n, direction in enumerate(shown):
                picture, real = _thumbnail(gf, entry, direction, (thumb_w, thumb_h), show_hex, zoom)
                slot_x = x + 5 + n * (thumb_w + 4) if directions else x + 5
                if directions:
                    draw.text((slot_x + thumb_w // 2, y + 2), DIRECTIONS[direction], font=small, fill=TEXT_DIM, anchor="mt")
                if picture is None:
                    continue
                size = size or real
                top = y + 4 + (12 if directions else 0) + thumb_h - picture.height
                sheet.paste(picture, (slot_x + (thumb_w - picture.width) // 2, top), picture)
            text_y = y + 6 + (12 if directions else 0) + thumb_h
            text_w = cell_w - 10
            count = count_text(entry)
            draw.text((x + 5, text_y), entry_id(entry), font=font, fill=TEXT_ID)
            right = count + (f" +{entry['same_art'] - 1}" if entry["same_art"] > 1 else "")
            if right:
                draw.text((x + cell_w - 5, text_y), right.strip(), font=font, fill=TEXT, anchor="ra")
            art = entry["art"] + (f" {size[0]}x{size[1]}" if size else " (no art)")
            draw.text((x + 5, text_y + LINE_HEIGHT), _fit(draw, art, font, text_w), font=font, fill=TEXT_DIM)
            draw.text((x + 5, text_y + 2 * LINE_HEIGHT), _fit(draw, entry["name"] or "-", font, text_w), font=font, fill=TEXT)
            if label_lines == 4:
                draw.text((x + 5, text_y + 3 * LINE_HEIGHT), _fit(draw, entry["info"], font, text_w), font=font, fill=TEXT_DIM)
            index_lines.append("\t".join([f"{page + 1:02d}", entry_id(entry), art, entry["name"], entry["info"],
                                          (count + (f" +{entry['same_art'] - 1} protos with this art"
                                                    if entry["same_art"] > 1 else "")).strip()]))
        path = f"{out_prefix}-{page + 1:02d}.png"
        sheet.save(path)
        files.append(path)
    if write_index:
        with open(out_prefix + ".txt", "w") as f:
            f.write(f"# {title}\n# sheet\tid\tart and size\tname\tflags\tuse\n" + "\n".join(index_lines) + "\n")
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("type", choices=sorted(TYPES), help="what to list")
    parser.add_argument("-o", "--out", required=True, metavar="PREFIX", help="output prefix: PREFIX-01.png ..., PREFIX.txt")
    parser.add_argument("--overlay", action="append", default=[], help="mod data directory laid over the game tree")
    parser.add_argument("--name", metavar="REGEX", help="proto name or art file name matches (case-insensitive)")
    parser.add_argument("--pid", action="append", default=[], metavar="A[-B]",
                        help="PID or PID range, full (0x02000100) or just the index; tile ids for tiles (repeatable)")
    parser.add_argument("--used-in", action="append", default=[], metavar="MAP",
                        help="only what this map uses, with use counts (repeatable: counts add up)")
    parser.add_argument("--unique-art", action="store_true", help="one cell per art file (many critter protos share art)")
    parser.add_argument("--sort", choices=("pid", "name", "art", "count"), help="cell order (default pid; count with --used-in)")
    parser.add_argument("--directions", action="store_true", help="show all six directions in each cell")
    parser.add_argument("--no-hex", action="store_true", help="do not outline the object's hex over the sprite")
    parser.add_argument("--zoom", type=int, default=1, help="integer magnification of the thumbnails (default 1)")
    parser.add_argument("--columns", type=int, help="cells per row (default: as many as fit)")
    parser.add_argument("--sheet-size", default="1540x1400", metavar="WxH", help="largest sheet in pixels (default %(default)s)")
    parser.add_argument("--title", help="sheet heading (default: describes the selection)")
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except (ValueError, KeyError, FileNotFoundError, re.error) as error:
        print(f"contact_sheet: {error}", file=sys.stderr)
        return 2


def _run(args):
    gf = GameFiles(overlay=args.overlay or None)
    obj_type = TYPES[args.type]
    maps = [load_map(name, gf) for name in args.used_in]
    entries = collect(gf, obj_type, args.name, parse_ranges(args.pid, obj_type), maps, args.unique_art, args.sort)
    if not entries:
        print("nothing matches", file=sys.stderr)
        return 1
    title = args.title
    if not title:
        parts = [args.type]
        if args.name:
            parts.append(f"name ~ /{args.name}/")
        if args.pid:
            parts.append("pid " + " ".join(args.pid))
        if args.used_in:
            parts.append("used in " + ", ".join(os.path.basename(m) for m in args.used_in))
        title = "  ".join(parts) + f"  ({len(entries)} entries)"
    size = tuple(int(v) for v in args.sheet_size.lower().split("x"))
    files = make_sheets(gf, entries, args.out, title, args.directions, False if args.no_hex else None, size,
                        args.columns, zoom=max(1, args.zoom))
    print(f"{len(entries)} entries on {len(files)} sheet(s): {files[0]} .. {os.path.basename(files[-1])}, index {args.out}.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
