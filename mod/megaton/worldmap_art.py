# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The "MEGATON" plate for the world map's list of destinations.

    python3 mod/megaton/worldmap_art.py [preview.png]      (writes a 6x preview to look at)

The world map shows a button for every known town that has a label picture
(city.txt townmap_label_art_idx -> art/intrface/intrface.lst; worldmap.cc
wmMakeTabsLabelList). The cut "Primitive Tribe" area Megaton lives in never had
one, so the town could only be reached by clicking its circle. build.py's data
step calls build_label() and appends the picture to intrface.lst.

The plate is made from the stock KLAMATH plate (wm_klam.frm, 82 x 18, palette
indices): its two top rows and the rows under the lettering are kept, the
lettering rows are refilled with the plate's own dither of the three blues, and
MEGATON is set in the same thin capitals: one-pixel strokes in the light greys
of the stock letters, with the darker blue-grey beside each stroke that makes
the stock plates look soft. No new colours, so it sits in the list like the rest.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

LABEL_FILE = "wm_megat.frm"            # 8.3; appended to art/intrface/intrface.lst
LABEL_COMMENT = "Worldmap Megaton TownMarker (Megaton mod)"
SOURCE = "art/intrface/wm_klam.frm"

WIDTH, HEIGHT = 82, 18
TEXT_TOP = 5                           # first row of the lettering on the stock plates
BLUES = (109, 110, 111)                # the plate itself
STROKE = (35, 36, 34, 36, 35, 37)      # light greys of the stock lettering
EDGE = (106, 107)                      # the soft shadow beside a stroke
GLOW = 46                              # the faint line under the stock lettering

# 7 x 8 capitals, one-pixel strokes like the stock plates'.
GLYPHS = {
    "M": ["X.....X",
          "XX...XX",
          "X.X.X.X",
          "X..X..X",
          "X.....X",
          "X.....X",
          "X.....X",
          "X.....X"],
    "E": ["XXXXXXX",
          "X......",
          "X......",
          "XXXXX..",
          "X......",
          "X......",
          "X......",
          "XXXXXXX"],
    "G": [".XXXXX.",
          "X.....X",
          "X......",
          "X......",
          "X..XXXX",
          "X.....X",
          "X.....X",
          ".XXXXX."],
    "A": ["...X...",
          "..X.X..",
          ".X...X.",
          "X.....X",
          "X.....X",
          "XXXXXXX",
          "X.....X",
          "X.....X"],
    "T": ["XXXXXXX",
          "...X...",
          "...X...",
          "...X...",
          "...X...",
          "...X...",
          "...X...",
          "...X..."],
    "O": [".XXXXX.",
          "X.....X",
          "X.....X",
          "X.....X",
          "X.....X",
          "X.....X",
          "X.....X",
          ".XXXXX."],
    "N": ["X.....X",
          "XX....X",
          "X.X...X",
          "X..X..X",
          "X...X.X",
          "X....XX",
          "X.....X",
          "X.....X"],
}
TEXT = "MEGATON"
GAP = 3


def build_label(gf):
    """bytes of the MEGATON plate (an FRM), made from the game's own KLAMATH plate."""
    from f2lib.frm import Frame, Frm

    source = Frm.from_bytes(gf.read(SOURCE))
    frame = source.frame(0, 0)
    if (frame.width, frame.height) != (WIDTH, HEIGHT):
        raise ValueError(f"{SOURCE} is {frame.width} x {frame.height}, expected {WIDTH} x {HEIGHT}")
    pixels = [list(frame.pixels[y * WIDTH:(y + 1) * WIDTH]) for y in range(HEIGHT)]

    # Clear the stock lettering (rows 4..14 hold letters and their glow): the plate's own dither.
    for y in range(TEXT_TOP - 1, TEXT_TOP + 10):
        for x in range(WIDTH):
            if pixels[y][x] not in BLUES or TEXT_TOP <= y:
                pixels[y][x] = BLUES[0] if (x * 7 + y * 13) % 5 else BLUES[1]
            if (x * 3 + y * 5) % 11 == 0:
                pixels[y][x] = BLUES[2]

    glyph_w = len(GLYPHS["M"][0])
    total = len(TEXT) * glyph_w + (len(TEXT) - 1) * GAP
    left = (WIDTH - total) // 2
    lit = set()
    for n, letter in enumerate(TEXT):
        for gy, row in enumerate(GLYPHS[letter]):
            for gx, mark in enumerate(row):
                if mark == "X":
                    lit.add((left + n * (glyph_w + GAP) + gx, TEXT_TOP + gy))
    for x, y in lit:
        # a soft shadow to the left of and under each stroke, as on the stock plates
        for sx, sy in ((x - 1, y), (x, y + 1)):
            if (sx, sy) not in lit and 0 <= sx < WIDTH:
                pixels[sy][sx] = EDGE[(sx + sy) % len(EDGE)]
    for x, y in lit:
        pixels[y][x] = STROKE[(x + 2 * y) % len(STROKE)]
    # the faint glow under the word
    for x in range(left, left + total, 2):
        if (x, TEXT_TOP + 8) not in lit:
            pixels[TEXT_TOP + 9][x] = GLOW if x % 4 == left % 4 else BLUES[2]

    source.stored[source.direction_map[0]][0] = Frame(WIDTH, HEIGHT, bytes(v for row in pixels for v in row), frame.x, frame.y)
    return source.to_bytes()


def main(argv):
    from f2lib import GameFiles
    from f2lib.frm import Frm
    from f2lib.pal import Palette
    from PIL import Image

    gf = GameFiles()
    palette = Palette(gf.read("color.pal"))
    target = argv[1] if len(argv) > 1 else os.path.join(ROOT, "run", "mg-int-preview", "wm-megaton-label.png")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    plates = [Frm.from_bytes(gf.read("art/intrface/wm_arroy.frm")), Frm.from_bytes(gf.read(SOURCE)),
              Frm.from_bytes(build_label(gf)), Frm.from_bytes(gf.read("art/intrface/wm_navar.frm"))]
    sheet = Image.new("RGB", (WIDTH * 6, (HEIGHT + 2) * 6 * len(plates)), (30, 30, 30))
    for n, plate in enumerate(plates):
        image = plate.image(palette, 0, 0).convert("RGB").resize((WIDTH * 6, HEIGHT * 6), Image.NEAREST)
        sheet.paste(image, (0, n * (HEIGHT + 2) * 6))
    sheet.save(target)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
