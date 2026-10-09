# SPDX-License-Identifier: MIT
"""Floor and roof TILES as numbers: where a sheet of squares lands on screen. Pure Python
(imported by Blender scripts and by the build), no engine, no numpy.

WHAT A TILE IS (measured grid dimensions; provenance in docs/blender-boundary.md)
  * The map has a 100 x 100 grid of SQUARES per elevation; one 32-bit word per square holds a
    floor art index (low 12 bits) and a roof art index (bits 16..27). The index is the 0-based
    line number of art/tiles/tiles.lst; index 1 means "nothing". No proto is involved.
  * A tile picture is an 80 x 36 FRM, drawn with its top-left corner on
        floor:  (48 * (99 - qx) + 32 * qy - 16,  -12 * (99 - qx) + 24 * qy - 2)      (world px)
        roof :  the same, 96 px higher
    so one step in qx is (-48, +12) px and one step in qy is (+32, +24) px. Palette index 0 is
    transparent in both (floors show black through it, roofs show whatever stands below).
  * The picture of a full tile is a rhombus with corners near (48, 0), (80, 24), (32, 36),
    (0, 12) of the box. Neighbouring stock tiles OVERLAP by a pixel along their seams (1,598
    opaque pixels each, 62 of them shared); who wins is the paint order (qy, then qx, rising).
    Tiles cut from one big picture carry the same pixel in both, so their seams cannot show.

A SHEET is N x M squares (N along +qx, M along +qy) cut out of one render. Sheet coordinates,
metres, as a sheet script sees them:

        (0, 0)  the far (top) corner of square (0, 0): the topmost point of the sheet on screen
        +x      along qx, towards the screen's lower LEFT: one square = SQ_U = 1.3856 m
        +y      along qy, towards the screen's lower RIGHT: one square = SQ_V = 1.6 m
        +z      up from the tile plane (the roof plane for roofs, the ground for floors)

  which is the piece coordinate system (pipeline/proj.py) moved so that the corner, not a hex
  centre, is the origin. Hex (2 qx0 + dhx, 2 qy0 + dhy) of a sheet whose first square is
  (qx0, qy0) has its centre at hex_xy(dhx, dhy).
"""
from . import proj as P

TILE_W, TILE_H = 80, 36
SQ_U, SQ_V = P.SQ_U_M, P.SQ_V_M
ROOF_LIFT_PX = 96                       # measured vertical separation of roof and floor planes
ROOF_LIFT_M = ROOF_LIFT_PX / P.UP_PX_PER_M      # 2.6625 m: the roof plane above the ground

# The far corner of a square is the point (48, -1) of its box, counted in whole pixels from the
# box's top-left corner: the hex (even hx, even hy) of the square is anchored on box pixel
# (64, 10) and its ground point is the top-left corner of the pixel ANCHOR_SHIFT from there
# (proj.ANCHOR_SHIFT, measured against the game's own floor seams), 16 px right and 10 px below
# the corner.
CORNER_IN_BOX = (48 + P.ANCHOR_SHIFT[0], 0 + P.ANCHOR_SHIFT[1])          # (48, -1)
HEX0 = P.px_to_ground(16.0, 10.0)       # sheet (x, y) of the centre of hex (2 qx0, 2 qy0): (-0.058, 0.700)

# The stock full tile: (first, last) opaque column of each of its 36 rows. Identical in every
# full stock floor and roof tile (ruf1000, plk2000, cmt1000, crbm004 ...); pipeline/tiles.py
# checks it against the game data on every build.
STOCK_ROWS = [(43, 49), (39, 50), (35, 52), (31, 53), (27, 54), (22, 56), (18, 57), (14, 58), (11, 59), (7, 61),
              (3, 62), (0, 64), (1, 65), (3, 67), (4, 68), (6, 69), (7, 71), (8, 72), (9, 73), (11, 74),
              (12, 76), (13, 77), (14, 78), (16, 79), (17, 78), (19, 74), (20, 70), (21, 66), (23, 61), (24, 57),
              (25, 53), (26, 49), (28, 45), (29, 41), (30, 38), (32, 34)]

# Where the STOCK shack roof ends inside its first and last row of squares (measured on the trim
# tiles jrt2000 / jrt2002 and the eave tiles ruf3000 / plk5000), as a fraction of a square along +y:
STOCK_TRIM_FROM = 0.55                  # the trim row is roof from here on (0.88 m into the row)
STOCK_EAVE_TO = 0.45                    # the eave row is roof up to here (0.72 m); stock paints a stippled
                                        # shadow below it down to about 0.8


def box_px(i, j):
    """Top-left corner of the box of sheet square (i, j), in whole px relative to the sheet origin
    (x right, y down), for a FLOOR. A roof is drawn ROOF_LIFT_PX higher."""
    return (-CORNER_IN_BOX[0] - 48 * i + 32 * j, -CORNER_IN_BOX[1] + 12 * i + 24 * j)


def canvas(n, m, lift_px=0):
    """(x0, y0, x1, y1): the px rectangle that holds every box of an n x m sheet."""
    x0 = box_px(n - 1, 0)[0]
    x1 = box_px(0, m - 1)[0] + TILE_W
    y0 = box_px(0, 0)[1]
    y1 = box_px(n - 1, m - 1)[1] + TILE_H
    return (x0, y0 - lift_px, x1, y1 - lift_px)


def size_m(n, m):
    return n * SQ_U, m * SQ_V


def hex_xy(dhx, dhy):
    """Sheet (x, y) of the centre of the hex (2 qx0 + dhx, 2 qy0 + dhy), (qx0, qy0) being the
    sheet's first square. Even hexes of a row lie on one line, odd ones 0.4 m behind it."""
    x, y = P.hex_xy(dhx, dhy)
    return HEX0[0] + x, HEX0[1] + y


def square_xy(i, j):
    """Sheet (x, y) of the far corner of sheet square (i, j)."""
    return i * SQ_U, j * SQ_V


class Shack:
    """The roof of a stock shack `box` = (hx_lo, hy_lo, hx_hi, hy_hi) (mod/megaton/layout/plan.py
    BUILDINGS[...]["box"]; walls stand ON the box lines) as a sheet:

        size            (N, M) squares of its roof: N = (hx_hi - hx_lo) / 2, M = (hy_hi - hy_lo) / 2 + 2
                        (one row behind the back wall, one row in front of the front wall)
        first           (qx0, qy0): the map square of sheet square (0, 0)
        w, h            sheet size in metres
        right, left     x of the right and the left wall line (0 and w to within 6 cm: the roof squares
                        end ON the side walls, there is no room for an overhang to the sides)
        back, front     y of the back and the front wall line (the wall's even hexes)
        stock_back, stock_front      y where the stock roof begins and ends (0.6 m behind the back wall,
                        0.8 m in front of the front wall)
        door(side, pos) sheet (x, y) of a door hex: side front / back takes hx, left / right hy
    """

    def __init__(self, box):
        self.box = hx_lo, hy_lo, hx_hi, hy_hi = tuple(box)
        if hx_lo & 1 or hx_hi & 1 or not hy_lo & 1 or not hy_hi & 1:
            raise ValueError(f"shack box {box}: hx bounds must be even and hy bounds odd")
        self.first = (hx_lo // 2, (hy_lo - 1) // 2)
        self.size = ((hx_hi - hx_lo) // 2, (hy_hi - hy_lo) // 2 + 2)
        self.w, self.h = size_m(*self.size)
        self.right = self.hex(hx_lo, hy_lo + 1)[0]
        self.left = self.hex(hx_hi, hy_lo + 1)[0]
        self.back = self.hex(hx_lo, hy_lo)[1]
        self.front = self.hex(hx_lo, hy_hi)[1]
        self.stock_back = STOCK_TRIM_FROM * SQ_V
        self.stock_front = (self.size[1] - 1 + STOCK_EAVE_TO) * SQ_V

    def hex(self, hx, hy):
        """Sheet (x, y) of the centre of map hex (hx, hy)."""
        return hex_xy(hx - 2 * self.first[0], hy - 2 * self.first[1])

    def door(self, side, pos):
        hx_lo, hy_lo, hx_hi, hy_hi = self.box
        return self.hex(*{"front": (pos, hy_hi), "back": (pos, hy_lo), "left": (hx_hi, pos), "right": (hx_lo, pos)}[side])

    def squares(self):
        """[(qx, qy)] of the roof, row by row."""
        return [(self.first[0] + i, self.first[1] + j) for j in range(self.size[1]) for i in range(self.size[0])]

    def __repr__(self):
        return (f"Shack(box={self.box}, size={self.size}, first={self.first}, back={self.back:.2f}, front={self.front:.2f}, "
                f"left={self.left:.2f}, right={self.right:.2f})")
