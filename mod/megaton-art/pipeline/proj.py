# SPDX-License-Identifier: MIT
"""The game's camera, as numbers. Pure Python: imported by Blender scripts and by the build.

WHAT THE GAME'S PROJECTION REALLY IS
The hex grid of Fallout is a *regular* hex grid seen by an ordinary orthographic
camera: neighbours are 32 px apart along a screen row and rows are 12 px apart,
and for a regular grid the rows are sqrt(3)/2 * 32 = 27.71 px apart on the
ground, so the ground is squeezed vertically by 12 / 27.71 = sqrt(3)/4:

    sin(elevation) = sqrt(3) / 4      elevation = 25.659 degrees above the horizon

With that camera the two floor-tile axes (-48,+12) and (+32,+24) px come out
exactly perpendicular on the ground - but of unequal length: a floor "square"
is a 55.43 x 64 px rectangle (2 hex rows x 2 hex steps). So nothing has to be
sheared: model with true right angles and true circles in a metric scene and
render it with this camera, and it lands on the game's grid (proved by
pipeline/calibrate.py against the engine's own floor tiles and walls).

SCENE CONVENTIONS (Blender world space, metres)
    +X  the game's square-x axis: one floor square = SQ_U_M = 1.3856 m, on screen (-48, +12) px
    +Y  the game's square-y axis: one floor square = SQ_V_M = 1.6    m, on screen (+32, +24) px
    +Z  up:                                          1 m = 36.06 px
    scale: 40 px per metre across the screen (PX_PER_M); a person is 1.8 m = 65 px,
    a wall is WALL_H = 2.66 m = 96 px (the height at which the game draws roofs).
    (0, 0, 0) is the centre of the piece's ORIGIN HEX, which must have even hx and even hy.

Both +X and +Y point towards the viewer (down the screen); the camera looks
along (-0.5, -0.866) on the ground. "Screen px" below are relative to the
origin hex centre, x right, y down.
"""
import math

PX_PER_M = 40.0
SIN_E = math.sqrt(3.0) / 4.0
COS_E = math.sqrt(13.0) / 4.0
ELEVATION_DEG = math.degrees(math.asin(SIN_E))          # 25.6589
UP_PX_PER_M = PX_PER_M * COS_E                          # 36.0555 px of screen height per metre of height

SQ_U_PX = (-48.0, 12.0)                                 # screen step of one floor square along +X
SQ_V_PX = (32.0, 24.0)                                  # ... along +Y
SQ_U_M = math.hypot(SQ_U_PX[0], SQ_U_PX[1] / SIN_E) / PX_PER_M      # 1.385641
SQ_V_M = math.hypot(SQ_V_PX[0], SQ_V_PX[1] / SIN_E) / PX_PER_M      # 1.6
_DET = SQ_U_PX[0] * SQ_V_PX[1] - SQ_V_PX[0] * SQ_U_PX[1]            # -1536

WALL_PX = 96                                            # stock wall / roof height on screen
WALL_H = WALL_PX / UP_PX_PER_M                          # 2.6625 m
HUMAN_PX = 65
HUMAN_H = HUMAN_PX / UP_PX_PER_M                        # 1.80 m
HEX_M = 32.0 / PX_PER_M                                 # 0.8 m between neighbouring hex centres

# Ground unit vectors (world X, Y) of the screen directions.
SCREEN_RIGHT = (-math.sqrt(3.0) / 2.0, 0.5)             # 1 m this way = 40 px to the right
SCREEN_INTO = (-0.5, -math.sqrt(3.0) / 2.0)             # away from the viewer; 1 m = 17.32 px up the screen
# Camera: looks along VIEW_DIR, image x = CAM_RIGHT, image up = CAM_UP.
VIEW_DIR = (SCREEN_INTO[0] * COS_E, SCREEN_INTO[1] * COS_E, -SIN_E)
CAM_RIGHT = (SCREEN_RIGHT[0], SCREEN_RIGHT[1], 0.0)
CAM_UP = (SCREEN_INTO[0] * SIN_E, SCREEN_INTO[1] * SIN_E, COS_E)

# Where the scene origin lands in the engine's integer pixels. A sprite is anchored on the pixel
# (hex_x + 16, hex_y + 8); the ground point at the hex centre is the TOP-LEFT corner of the pixel
# ANCHOR_SHIFT away from it. (0, -1) is measured, not assumed: with it the Blender floor grid agrees
# with the game's painted floor seams on 99.1 % of the pixels, any other whole-pixel shift is worse
# (pipeline/calibrate.py prints the table).
ANCHOR_SHIFT = (0, -1)

# Stock shack walls, measured on the sprites (jas* along a hex row, jbs* along a hex column): at
# the hex centre's column a wall covers 96 px, from 3 px below the hex centre to 93 px above it.
# A slab STOCK_WALL_H tall and STOCK_WALL_T thick whose front face is STOCK_WALL_FRONT_* metres in
# front of the line through the hex centres has that silhouette (kit.geo.wall_u / wall_v).
STOCK_WALL_H = 2.52
STOCK_WALL_T = 0.25
STOCK_WALL_FRONT_U = 0.15      # wall along +X (a hex row): front face at y = +0.15
STOCK_WALL_FRONT_V = 0.09      # wall along +Y (a hex column): front face at x = +0.09

# Sprite reach budgets leave a margin inside the observed 320 x 240 px
# redraw range around the anchor hex. See docs/blender-boundary.md for provenance.
MAX_REACH_X = 300          # px a part may extend left / right of its anchor hex
MAX_REACH_UP = 224         # px above its anchor hex
MAX_REACH_DOWN = 200


def world_to_px(x, y, z=0.0):
    """World point (m) -> screen px relative to the origin hex centre (x right, y down)."""
    a, b = x / SQ_U_M, y / SQ_V_M
    return (a * SQ_U_PX[0] + b * SQ_V_PX[0],
            a * SQ_U_PX[1] + b * SQ_V_PX[1] - z * UP_PX_PER_M)


def px_to_ground(px, py):
    """Screen px (relative to the origin hex centre) -> ground point (x, y) in metres at z = 0."""
    a = (SQ_V_PX[1] * px - SQ_V_PX[0] * py) / _DET
    b = (SQ_U_PX[0] * py - SQ_U_PX[1] * px) / _DET
    return a * SQ_U_M, b * SQ_V_M


def px_to_world(px, py, z):
    """Screen px -> world point that shows there at height z."""
    return px_to_ground(px, py + z * UP_PX_PER_M) + (z,)


def hex_px(dhx, dhy):
    """Screen px of hex (dhx, dhy) relative to the origin hex (which has EVEN hx).

    hx grows to the screen left: an even->odd step is (-32, 0), odd->even
    (-16, +12); hy + 1 is (+16, +12). Pair the horizontal steps; an odd
    remainder uses the first step. Floor division preserves negative offsets.
    This agrees with the game; checked by pipeline/calibrate.py when run.
    """
    pairs, odd = divmod(dhx, 2)
    return (-48 * pairs - 32 * odd + 16 * dhy,
            12 * (pairs + dhy))


def hex_xy(dhx, dhy):
    """World (x, y) in metres of the centre of hex (dhx, dhy) relative to the origin hex."""
    return px_to_ground(*hex_px(dhx, dhy))


def nearest_hex(x, y):
    """(dhx, dhy) of the hex whose centre is nearest to ground point (x, y) (true distance)."""
    px, py = world_to_px(x, y)
    return nearest_hex_px(px, py)


def nearest_hex_px(px, py):
    """(dhx, dhy) of the hex nearest to the ground point shown at screen px (px, py)."""
    # average steps: hx + 1 = (-24, +6) px, hy + 1 = (+16, +12) px
    dhx0 = int(round((12.0 * px - 16.0 * py) / -384.0))
    dhy0 = int(round((-24.0 * py - 6.0 * px) / -384.0))
    best = None
    for dhy in range(dhy0 - 2, dhy0 + 3):
        for dhx in range(dhx0 - 2, dhx0 + 3):
            hx_px, hy_px = hex_px(dhx, dhy)
            d = (hx_px - px) ** 2 + ((hy_px - py) / SIN_E) ** 2
            if best is None or d < best[0]:
                best = (d, dhx, dhy)
    return best[1], best[2]


def square_corner_xy(qx, qy):
    """World (x, y) of the top (far) corner of floor square (qx, qy) relative to the square that
    logically owns the origin hex. Square (0, 0) spans x in [X0, X0 + SQ_U_M], y in [Y0, Y0 + SQ_V_M].

    The origin hex (even hx, even hy) sits 16 px right and 10 px below the top
    vertex of its square's rhombus (research/04 section 11.5).
    """
    x0, y0 = px_to_ground(-16.0, -10.0)
    return x0 + qx * SQ_U_M, y0 + qy * SQ_V_M


def tile_order_key(dhx, dhy):
    """Sort key the engine paints non-flat objects in (ascending tile number)."""
    return dhy * 200 + dhx


def describe():
    return {
        "px_per_m": PX_PER_M, "up_px_per_m": UP_PX_PER_M, "elevation_deg": ELEVATION_DEG,
        "sq_u_m": SQ_U_M, "sq_v_m": SQ_V_M, "wall_h_m": WALL_H, "human_h_m": HUMAN_H,
    }
