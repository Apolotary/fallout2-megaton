# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Contact sheets of the built sprites: every piece as the engine assembles it, 2x, on game floor
colour, with a stock villager at the same scale beside it.

    python3 mod/megaton-art/build.py sheet [PREFIX ...]      -> build/preview/sheet-NN.png

The halo layer is shown as its yellow tint, the flat shadow as the dither it is. Pieces are drawn
from out/ (what the game will load), not from the renders.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from f2lib import GameFiles                 # noqa: E402

from . import data                          # noqa: E402
from . import proj as P                     # noqa: E402

FLOOR = np.array([131, 112, 88], np.uint8)
ORDER = {"shadow": 0, "halo": 1, "main": 2, "glow": 3}
VILLAGER_FID = 0x01000003                   # stock critter art (hmwarr): 65 px tall standing


def piece_picture(gf, piece, frame=0):
    """RGB array of one piece on floor colour, and the pixel of its origin hex in it."""
    boxes = []
    for part in piece["parts"]:
        frm = gf.art.load(int(part["fid"], 16))
        w, h = frm.size(0, 0)
        hx, hy = P.hex_px(*part["hex"])
        boxes.append((part, frm, hx + part["shift"][0] - w // 2, hy + part["shift"][1] - (h - 1), w, h))
    x0, y0 = min(b[2] for b in boxes) - 4, min(b[3] for b in boxes) - 4
    x1, y1 = max(b[2] + b[4] for b in boxes) + 4, max(b[3] + b[5] for b in boxes) + 4
    canvas = np.zeros((y1 - y0, x1 - x0, 3), np.uint8) + FLOOR
    for part, frm, left, top, w, h in sorted(boxes, key=lambda b: (ORDER[b[0]["layer"]], b[0]["hex"][1] * 200 + b[0]["hex"][0])):
        count = len(frm.stored[0])
        pixels = np.frombuffer(frm.frame(0, min(frame, count - 1)).pixels, np.uint8).reshape(h, w)
        target = canvas[top - y0:top - y0 + h, left - x0:left - x0 + w]
        if part["layer"] in ("halo", "glow"):
            mix = (target.astype(np.float32) * 0.6 + np.array([255, 220, 90], np.float32) * 0.4).astype(np.uint8)
            np.copyto(target, mix, where=(pixels > 0)[..., None])
        else:
            np.copyto(target, gf.palette.rgb[pixels], where=(pixels > 0)[..., None])
    return canvas, (-x0, -y0)


def villager(gf):
    frm = gf.art.load(VILLAGER_FID)
    w, h = frm.size(2, 0)
    pixels = np.frombuffer(frm.frame(2, 0).pixels, np.uint8).reshape(h, w)
    return pixels


def sheets(prefixes=(), zoom=2, width=1900, out_dir=None):
    from PIL import Image, ImageDraw
    gf = GameFiles(overlay=data.OUT)
    manifest = data.load_manifest()
    man = villager(gf)
    tiles = []
    for name, piece in manifest["pieces"].items():
        if prefixes and not name.startswith(tuple(prefixes)):
            continue
        picture, origin = piece_picture(gf, piece)
        h, w = picture.shape[:2]
        mh, mw = man.shape
        wide = np.zeros((max(h, origin[1] + 8), w + mw + 6, 3), np.uint8) + FLOOR
        wide[:h, :w] = picture
        top = origin[1] + 6 - mh                    # feet level with the origin hex
        if top >= 0:
            target = wide[top:top + mh, w + 3:w + 3 + mw]
            np.copyto(target, gf.palette.rgb[man], where=(man > 0)[..., None])
        tiles.append((name, Image.fromarray(wide), len(piece["parts"])))
    if not tiles:
        raise SystemExit("no piece matches")
    out_dir = out_dir or os.path.join(ART, "build", "preview")
    os.makedirs(out_dir, exist_ok=True)
    pad, page_height = 10, 1500
    pages, rows, row, x = [], [], [], 0
    for item in tiles:
        w = max(item[1].width * zoom, 170) + pad
        if row and x + w > width:
            rows.append(row)
            row, x = [], 0
        row.append(item)
        x += w
    rows.append(row)
    page, used = [], 0
    for r in rows:
        height = max(t[1].height for t in r) * zoom + 22
        if page and used + height > page_height:
            pages.append(page)
            page, used = [], 0
        page.append(r)
        used += height
    pages.append(page)
    paths = []
    for number, page in enumerate(pages):
        height = sum(max(t[1].height for t in r) * zoom + 22 for r in page)
        out = Image.new("RGB", (width, height), tuple(int(c) for c in FLOOR))
        draw = ImageDraw.Draw(out)
        y = 0
        for r in page:
            x = 0
            row_h = max(t[1].height for t in r) * zoom
            for name, image, parts in r:
                out.paste(image.resize((image.width * zoom, image.height * zoom), Image.NEAREST),
                          (x, y + 16 + row_h - image.height * zoom))
                draw.text((x + 2, y + 2), f"{name} ({parts})", fill=(255, 255, 255))
                x += max(image.width * zoom, 170) + pad
            y += row_h + 22
        path = os.path.join(out_dir, f"sheet-{number:02d}.png")
        out.save(path)
        paths.append(path)
    return paths


def tile_sheets(names=(), zoom=2, out_dir=None):
    """One picture per registered tile sheet (out/sheets/NAME.png at `zoom`, on a neutral ground)."""
    from PIL import Image
    from . import tiles
    out_dir = out_dir or os.path.join(ART, "build", "preview")
    os.makedirs(out_dir, exist_ok=True)
    gf = GameFiles()
    made = []
    for name, entry in tiles.section(data.load_manifest())["sheets"].items():
        if names and not any(name.startswith(prefix) for prefix in names):
            continue
        indices = tiles.load_sheet_picture(name)
        rgba = gf.palette.rgba[indices].copy()
        back = np.zeros(rgba.shape, np.uint8) + np.array([131, 112, 88, 255], np.uint8)
        shown = np.where(rgba[..., 3:] > 0, rgba, back)
        image = Image.fromarray(shown, "RGBA").resize((shown.shape[1] * zoom, shown.shape[0] * zoom), Image.NEAREST)
        path = os.path.join(out_dir, f"tiles-{name}.png")
        image.save(path)
        made.append(path)
    return made
