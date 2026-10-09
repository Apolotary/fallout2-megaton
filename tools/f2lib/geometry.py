"""Hex and square grid maths, matching fallout2-ce's tile.cc.

Grids (map_defs.h): hexes 200 x 200 (``tile = hy * 200 + hx``), floor / roof
squares 100 x 100 (``sq = sqy * 100 + sqx``). On screen **x grows to the left**
for both grids: larger hx / sqx is further west, larger hy / sqy is further
down-right.

"World pixels" are screen pixels of an imaginary view whose origin is fixed:
``screen = world + constant`` for any view centre (`View` computes the
constant). Closed forms below were checked against a line-by-line port of the
engine functions (tools/tests/test_geometry.py).

Directions (Rotation, obj_types.h:7-15): 0 NE, 1 E, 2 SE, 3 SW, 4 W, 5 NW.
"""
import math

HEX_WIDTH = 200
HEX_HEIGHT = 200
HEX_COUNT = HEX_WIDTH * HEX_HEIGHT
SQUARE_WIDTH = 100
SQUARE_HEIGHT = 100
SQUARE_COUNT = SQUARE_WIDTH * SQUARE_HEIGHT

NE, E, SE, SW, W, NW = range(6)
DIR_NAMES = ("NE", "E", "SE", "SW", "W", "NW")
# Pixel step of the hex centre per direction (tile.cc:93-110).
DIR_PIXELS = ((16, -12), (32, 0), (16, 12), (-16, 12), (-32, 0), (-16, -12))
# Tile-number step per direction, indexed by parity of hx (_dir_tile, tile.cc:308-337).
DIR_TILE = ((-1, 199, 200, 201, 1, -200), (-201, -1, 200, 1, -199, -200))

# tileSetCenter refuses view centres outside this box (tileSetBorder computed
# for the original 640x380 window); a map's entering tile must be inside it.
CENTER_HX = (44, 156)
CENTER_HY = (45, 154)

ROOF_HEIGHT = 96            # roofs are drawn this many pixels above the floor


# ------------------------------------------------------------------- hex grid
def tile_xy(tile):
    return tile % HEX_WIDTH, tile // HEX_WIDTH


def tile_at(hx, hy):
    """Tile number, or -1 outside the grid."""
    if 0 <= hx < HEX_WIDTH and 0 <= hy < HEX_HEIGHT:
        return hy * HEX_WIDTH + hx
    return -1


def is_valid(tile):
    return 0 <= tile < HEX_COUNT


def is_edge(tile):
    """tileIsEdge: first/last row or column."""
    if not is_valid(tile):
        return False
    hx, hy = tile_xy(tile)
    return hy == 0 or hy == HEX_HEIGHT - 1 or hx == 0 or hx == HEX_WIDTH - 1


def can_center(tile):
    """True when the engine accepts `tile` as a view centre / entering tile."""
    hx, hy = tile_xy(tile)
    return is_valid(tile) and CENTER_HX[0] <= hx <= CENTER_HX[1] and CENTER_HY[0] <= hy <= CENTER_HY[1]


def tile_in_direction(tile, rotation, distance=1):
    """tileGetTileInDirection: step `distance` hexes, stopping at an edge tile."""
    for _ in range(distance):
        if is_edge(tile):
            break
        tile += DIR_TILE[tile % HEX_WIDTH & 1][rotation]
    return tile


def neighbors(tile):
    """The six adjacent tiles in direction order (-1 where the grid ends)."""
    hx, hy = tile_xy(tile)
    if hx & 1:
        steps = ((-1, -1), (-1, 0), (0, 1), (1, 0), (1, -1), (0, -1))
    else:
        steps = ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (0, -1))
    return [tile_at(hx + dx, hy + dy) for dx, dy in steps]


# ----------------------------------------------------------------- projection
def hex_world(tile):
    """Top-left of the hex's 32x16 cell (tileToScreenXY)."""
    hx, hy = tile_xy(tile)
    a = HEX_WIDTH - 1 - hx
    return 48 * (a >> 1) + 32 * (a & 1) + 16 * hy, -12 * (a >> 1) + 12 * hy


def hex_center(tile):
    """World position of the hex centre, where object sprites are anchored."""
    x, y = hex_world(tile)
    return x + 16, y + 8


def square_world(square):
    """Top-left of the square's 80x36 floor tile (squareTileToScreenXY)."""
    qx, qy = square % SQUARE_WIDTH, square // SQUARE_WIDTH
    b = SQUARE_WIDTH - 1 - qx
    return 48 * b + 32 * qy - 16, -12 * b + 24 * qy - 2


def roof_world(square):
    """Top-left of the square's roof tile (squareTileToRoofScreenXY)."""
    x, y = square_world(square)
    return x, y - ROOF_HEIGHT


def _build_tile_mask():
    mask = []
    for v11 in (0, 16, 32, 48):
        mask += [1 if v13 > v11 else 0 for v13 in range(64, 0, -4)]
        mask += [2 if v13 > v11 else 0 for v13 in range(0, 64, 4)]
    mask += [0] * (8 * 32)
    for v11 in (0, 16, 32, 48):
        mask += [0 if v13 > v11 else 3 for v13 in range(0, 64, 4)]
        mask += [0 if v13 > v11 else 4 for v13 in range(64, 0, -4)]
    return mask


_TILE_MASK = _build_tile_mask()


def hex_from_world(x, y):
    """Tile whose hexagon contains world pixel (x, y), or -1 (tileFromScreenXY)."""
    v3 = y // 12
    v4 = x - 16 * v3
    v5 = y - 12 * v3
    v6 = v4 // 64
    v10 = v6 + v3
    v8 = v4 - v6 * 64
    v11 = 2 * v6
    if v8 >= 32:
        v8 -= 32
        v11 += 1
    corner = _TILE_MASK[32 * v5 + v8]
    if corner == 2:
        v11 += 1
        if v11 & 1:
            v10 -= 1
    elif corner == 1:
        v10 -= 1
    elif corner == 3:
        v11 -= 1
        if not v11 & 1:
            v10 += 1
    elif corner == 4:
        v10 += 1
    return tile_at(HEX_WIDTH - 1 - v11, v10)


def square_coords_from_world(x, y, roof=False):
    """(sqx, sqy) of the floor (or roof) square under a world pixel; may lie outside the grid."""
    v4 = x + 16
    v5 = y + 2 - 12 + (ROOF_HEIGHT if roof else 0)
    return SQUARE_WIDTH - 1 - (3 * v4 - 4 * v5) // 192, (4 * v5 + v4) // 128


def square_from_world(x, y, roof=False):
    """Square index under a world pixel, or -1 (squareTileFromScreenXY)."""
    qx, qy = square_coords_from_world(x, y, roof)
    if 0 <= qx < SQUARE_WIDTH and 0 <= qy < SQUARE_HEIGHT:
        return qy * SQUARE_WIDTH + qx
    return -1


class View:
    """Screen coordinates for a view centred on a tile.

    width / height are those of the iso window: the game resolution minus the
    100-pixel interface bar (640x380 for 640x480, 1280x860 for 1280x960).
    """

    def __init__(self, center_tile, width=640, height=380):
        cx, cy = hex_world(center_tile)
        self.center_tile = center_tile
        self.width = width
        self.height = height
        self.dx = (width - 32) // 2 - cx
        self.dy = (height - 16) // 2 - cy

    def to_screen(self, world):
        return world[0] + self.dx, world[1] + self.dy

    def hex(self, tile):
        return self.to_screen(hex_world(tile))

    def hex_center(self, tile):
        return self.to_screen(hex_center(tile))

    def square(self, square):
        return self.to_screen(square_world(square))

    def roof(self, square):
        return self.to_screen(roof_world(square))

    def hex_at(self, x, y):
        return hex_from_world(x - self.dx, y - self.dy)

    def square_at(self, x, y, roof=False):
        return square_from_world(x - self.dx, y - self.dy, roof)


# ------------------------------------------------------- distance / direction
def _sector(dx, dy):
    """Direction 0..5 of a pixel delta, as computed in tileGetRotationTo."""
    if dx == 0:
        return NE if dy < 0 else SE
    angle = int(math.atan2(-dy, dx) * 180.0 * 0.3183098862851122)       # trunc toward zero
    v = 360 - (angle + 180) - 90
    if v < 0:
        v += 360
    return min(v // 60, 5)


def rotation_to(tile_from, tile_to):
    """tileGetRotationTo: direction to face `tile_to` from `tile_from`."""
    x1, y1 = hex_world(tile_from)
    x2, y2 = hex_world(tile_to)
    return _sector(x2 - x1, y2 - y1)


def distance(tile_a, tile_b):
    """Hex distance (equals tileDistanceBetween for valid tiles; 9999 if either is -1)."""
    if tile_a == -1 or tile_b == -1:
        return 9999
    qa, ra = _axial(tile_a)
    qb, rb = _axial(tile_b)
    dq, dr = qb - qa, rb - ra
    return max(abs(dq), abs(dr), abs(dq + dr))


def engine_distance(tile_a, tile_b):
    """Literal port of tileDistanceBetween (greedy walk by 60-degree sectors)."""
    if tile_a == -1 or tile_b == -1:
        return 9999
    x1, y1 = hex_world(tile_b)
    steps = 0
    tile = tile_a
    while tile != tile_b:
        x2, y2 = hex_world(tile)
        tile += DIR_TILE[tile % HEX_WIDTH & 1][_sector(x1 - x2, y1 - y2)]
        steps += 1
    return steps


# ------------------------------------------------------------- hex <-> square
def roof_square(tile):
    """Square that logically owns a hex (object.cc:1445-1448): decides which roof hides."""
    hx, hy = tile_xy(tile)
    return (hy // 2) * SQUARE_WIDTH + hx // 2


def floor_square(tile):
    """Square whose floor art lies under the hex centre, or -1 at the grid edge.

    Odd-hx hexes sit on their logical square, even-hx hexes on the one to the
    screen right, hence (hx - 1) // 2.
    """
    hx, hy = tile_xy(tile)
    qx = (hx - 1) // 2
    return (hy // 2) * SQUARE_WIDTH + qx if qx >= 0 else -1


def square_hexes(square):
    """The four hexes a square logically owns (inverse of `roof_square`)."""
    qx, qy = square % SQUARE_WIDTH, square // SQUARE_WIDTH
    return [tile_at(2 * qx + dx, 2 * qy + dy) for dy in (0, 1) for dx in (0, 1)]


def square_xy(square):
    return square % SQUARE_WIDTH, square // SQUARE_WIDTH


def square_at(qx, qy):
    if 0 <= qx < SQUARE_WIDTH and 0 <= qy < SQUARE_HEIGHT:
        return qy * SQUARE_WIDTH + qx
    return -1


# --------------------------------------------------------------------- shapes
def line(tile_from, tile_to):
    """Shortest hex path closest to the straight line: distance + 1 hexes, both ends included.

    Use this to lay out walls and paths; `engine_line` is what the engine's
    own scroll code samples.
    """
    qa, ra = _axial(tile_from)
    qb, rb = _axial(tile_to)
    steps = max(abs(qb - qa), abs(rb - ra), abs(qb - qa + rb - ra))
    tiles = []
    for i in range(steps + 1):
        t = i / steps if steps else 0.0
        # Nudge off exact hex borders so ties always round the same way.
        fx = qa + (qb - qa) * t + 1e-6
        fz = ra + (rb - ra) * t + 2e-6
        fy = -fx - fz
        x, y, z = round(fx), round(fy), round(fz)
        dx, dy, dz = abs(x - fx), abs(y - fy), abs(z - fz)
        if dx > dy and dx > dz:
            x = -y - z
        elif dy <= dz:
            z = -x - y
        tiles.append(_from_axial(x, z))
    return tiles


def engine_line(tile_from, tile_to):
    """Hexes hit by the pixel line between two hex centres (_tile_make_line, tile.cc:1835-1943).

    The raster line can clip the corner of a hex beside the path, so the
    result may hold more than distance + 1 hexes.
    """
    if tile_from == tile_to:
        return [tile_from]
    x, y = hex_center(tile_from)
    to_x, to_y = hex_center(tile_to)
    step_x = (to_x > x) - (to_x < x)
    step_y = (to_y > y) - (to_y < y)
    span_x = 2 * abs(to_x - x)
    span_y = 2 * abs(to_y - y)
    tiles = [tile_from]
    steep = span_x <= span_y
    error = (span_x - span_y // 2) if steep else (span_y - span_x // 2)
    while True:
        tile = hex_from_world(x, y)
        if tile == tile_to:
            tiles.append(tile)
            break
        if tile != tiles[-1] and (len(tiles) == 1 or tile != tiles[-2]):
            tiles.append(tile)
        if steep:
            if y == to_y:
                break
            if error >= 0:
                x += step_x
                error -= span_y
            error += span_x
            y += step_y
        else:
            if x == to_x:
                break
            if error >= 0:
                y += step_y
                error -= span_x
            error += span_y
            x += step_x
    return tiles


def rect(tile_a, tile_b):
    """All hexes of the grid-aligned box spanned by two corner tiles (row by row).

    A box in (hx, hy) is a parallelogram on screen, aligned with walls and
    floor squares.
    """
    ax, ay = tile_xy(tile_a)
    bx, by = tile_xy(tile_b)
    return [hy * HEX_WIDTH + hx
            for hy in range(min(ay, by), max(ay, by) + 1)
            for hx in range(min(ax, bx), max(ax, bx) + 1)]


def _axial(tile):
    """Axial coordinates (q along E, r along SE): hex_world(tile) == (32 * q + 16 * r, 12 * r)."""
    hx, hy = tile_xy(tile)
    q = HEX_WIDTH - 1 - hx
    return q, hy - (q >> 1)


def _from_axial(q, r):
    return tile_at(HEX_WIDTH - 1 - q, r + (q >> 1))


def ring(center, radius):
    """Hexes at exactly `radius` steps from `center`, clockwise from the NW corner (grid-clipped)."""
    if radius == 0:
        return [center]
    q, r = _axial(center)
    r -= radius                                        # the hex `radius` steps NW
    tiles = []
    for dq, dr in ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)):      # E SE SW W NW NE
        for _ in range(radius):
            tile = _from_axial(q, r)
            if tile != -1:
                tiles.append(tile)
            q += dq
            r += dr
    return tiles


def disc(center, radius):
    """Hexes within `radius` steps of `center`, nearest first."""
    tiles = []
    for d in range(radius + 1):
        tiles += ring(center, d)
    return tiles
