# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Geometry helpers against a line-by-line port of fallout2-ce's tile.cc."""
import math
import random

import _env  # noqa: F401
from f2lib import geometry as g


def cdiv(a, b):
    """C integer division (truncates toward zero)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def cmod(a, b):
    return a - b * cdiv(a, b)


class Engine:
    """tile.cc with its global view state, transcribed statement by statement."""

    def __init__(self, window_width, window_height):
        self.dir_tile = [[0] * 6, [0] * 6]
        w = 200
        self.dir_tile[0][0] = -1
        self.dir_tile[0][4] = 1
        self.dir_tile[1][1] = -1
        self.dir_tile[1][3] = 1
        self.dir_tile[0][1] = w - 1
        self.dir_tile[0][2] = w
        self.dir_tile[0][3] = w + 1
        self.dir_tile[1][2] = w
        self.dir_tile[0][5] = -w
        self.dir_tile[1][0] = -w - 1
        self.dir_tile[1][4] = 1 - w
        self.dir_tile[1][5] = -w

        mask = []
        v11 = 0
        while True:                                   # tileInit, tile.cc:345-387
            v13 = 64
            while True:
                mask.append(1 if v13 > v11 else 0)
                v13 -= 4
                if not v13:
                    break
            while True:
                mask.append(2 if v13 > v11 else 0)
                v13 += 4
                if v13 == 64:
                    break
            v11 += 16
            if v11 == 64:
                break
        mask += [0] * (8 * 32)
        v11 = 0
        while True:
            v13 = 0
            while True:
                mask.append(0 if v13 > v11 else 3)
                v13 += 4
                if v13 == 64:
                    break
            v13 = 64
            while True:
                mask.append(0 if v13 > v11 else 4)
                v13 -= 4
                if not v13:
                    break
            v11 += 16
            if v11 == 64:
                break
        assert len(mask) == 512
        self.mask = mask

        self.border = False
        self.win_w, self.win_h = 640, 380             # borders are computed for the original window
        assert self.set_center(200 * 100 + 100) == 0
        self.set_border()
        self.win_w, self.win_h = window_width, window_height
        assert self.set_center(200 * 100 + 100) == 0

    def set_border(self):                             # tileSetBorder, tile.cc:462-485
        v1 = self.tile_from_screen(-320, -240)
        v2 = self.tile_from_screen(-320, 380 + 240)
        self.min_x = abs(200 - 1 - cmod(v2, 200) - self.tile_x) + 6
        self.min_y = abs(self.tile_y - cdiv(v1, 200)) + 7
        self.max_x = 200 - self.min_x - 1
        self.max_y = 200 - self.min_y - 1
        if self.min_x & 1 == 0:
            self.min_x += 1
        if self.max_x & 1 == 0:
            self.min_x -= 1
        self.border = True

    def set_center(self, tile):                       # tileSetCenter with IGNORE_SCROLL_RESTRICTIONS
        if not 0 <= tile < 40000:
            return -1
        tile_x = 200 - 1 - tile % 200
        tile_y = tile // 200
        if self.border and (tile_x <= self.min_x or tile_x >= self.max_x or tile_y <= self.min_y or tile_y >= self.max_y):
            return -1
        self.tile_y = tile_y
        self.offx = (self.win_w - 32) // 2
        self.tile_x = tile_x
        self.offy = (self.win_h - 16) // 2
        if tile_x & 1:
            self.tile_x -= 1
            self.offx -= 32
        self.square_x = self.tile_x // 2
        self.square_y = self.tile_y // 2
        self.square_offx = self.offx - 16
        self.square_offy = self.offy - 2
        if self.tile_y & 1:
            self.square_offy -= 12
            self.square_offx -= 16
        return 0

    def tile_to_screen(self, tile):                   # tileToScreenXY
        v3 = 200 - 1 - tile % 200
        v4 = tile // 200
        x, y = self.offx, self.offy
        v5 = cdiv(v3 - self.tile_x, -2)
        x += 48 * cdiv(v3 - self.tile_x, 2)
        y += 12 * v5
        if v3 & 1:
            if v3 <= self.tile_x:
                x -= 16
                y += 12
            else:
                x += 32
        v6 = v4 - self.tile_y
        return x + 16 * v6, y + 12 * v6

    def tile_from_screen(self, screen_x, screen_y):   # tileFromScreenXY
        v2 = screen_y - self.offy
        v3 = cdiv(v2, 12) if v2 >= 0 else cdiv(v2 + 1, 12) - 1
        v4 = screen_x - self.offx - 16 * v3
        v5 = v2 - 12 * v3
        v6 = cdiv(v4, 64) if v4 >= 0 else cdiv(v4 + 1, 64) - 1
        v7 = v6 + v3
        v8 = v4 - v6 * 64
        v9 = 2 * v6
        if v8 >= 32:
            v8 -= 32
            v9 += 1
        v10 = self.tile_y + v7
        v11 = self.tile_x + v9
        case = self.mask[32 * v5 + v8]
        if case == 2:
            v11 += 1
            if v11 & 1:
                v10 -= 1
        elif case == 1:
            v10 -= 1
        elif case == 3:
            v11 -= 1
            if not v11 & 1:
                v10 += 1
        elif case == 4:
            v10 += 1
        v12 = 200 - 1 - v11
        if 0 <= v12 < 200 and 0 <= v10 < 200:
            return 200 * v10 + v12
        return -1

    def square_to_screen(self, square):               # squareTileToScreenXY
        v5 = 100 - 1 - square % 100
        v6 = square // 100
        x, y = self.square_offx, self.square_offy
        v8 = v5 - self.square_x
        x += 48 * v8
        y -= 12 * v8
        v9 = v6 - self.square_y
        return x + 32 * v9, y + 24 * v9

    def square_from_screen(self, screen_x, screen_y, roof=False):     # squareTileScreenToCoord(Roof)
        v4 = screen_x - self.square_offx
        v5 = screen_y + (96 if roof else 0) - self.square_offy - 12
        v6 = 3 * v4 - 4 * v5
        cx = cdiv(v6, 192) if v6 >= 0 else cdiv(v6 + 1, 192) - 1
        v8 = 4 * v5 + v4
        cy = cdiv(v8, 128) if v8 >= 0 else cdiv(v8 + 1, 128) - 1
        cx += self.square_x
        cy += self.square_y
        cx = 100 - 1 - cx
        if 0 <= cx < 100 and 0 <= cy < 100:
            return cx + 100 * cy
        return -1

    def is_edge(self, tile):                          # tileIsEdge
        if not 0 <= tile < 40000:
            return False
        return tile < 200 or tile >= 40000 - 200 or tile % 200 == 0 or tile % 200 == 199

    def tile_in_direction(self, tile, rotation, distance):            # tileGetTileInDirection
        new_tile = tile
        for _ in range(distance):
            if self.is_edge(new_tile):
                break
            new_tile += self.dir_tile[new_tile % 200 & 1][rotation]
        return new_tile

    def rotation_to(self, tile1, tile2):              # tileGetRotationTo
        x1, y1 = self.tile_to_screen(tile1)
        x2, y2 = self.tile_to_screen(tile2)
        dy = y2 - y1
        x2 -= x1
        if x2 != 0:
            v6 = int(math.trunc(math.atan2(-dy, x2) * 180.0 * 0.3183098862851122))
            v7 = 360 - (v6 + 180) - 90
            if v7 < 0:
                v7 += 360
            v7 //= 60
            return 5 if v7 >= 6 else v7
        return 0 if dy < 0 else 2

    def distance(self, tile1, tile2):                 # tileDistanceBetween
        if tile1 == -1 or tile2 == -1:
            return 9999
        x1, y1 = self.tile_to_screen(tile2)
        v2 = tile1
        i = 0
        while v2 != tile2:
            x2, y2 = self.tile_to_screen(v2)
            dx, dy = x1 - x2, y1 - y2
            if x1 == x2:
                v9 = 0 if dy < 0 else 2
            else:
                v8 = int(math.trunc(math.atan2(-dy, dx) * 180.0 * 0.3183098862851122))
                v9 = 360 - (v8 + 180) - 90
                if v9 < 0:
                    v9 += 360
                v9 //= 60
                if v9 >= 6:
                    v9 = 5
            v2 += self.dir_tile[v2 % 200 & 1][v9]
            i += 1
        return i


def test_center_limits_match_tile_set_border():
    engine = Engine(640, 380)
    allowed = [t for t in range(g.HEX_COUNT) if engine.set_center(t) == 0]
    assert allowed == [t for t in range(g.HEX_COUNT) if g.can_center(t)]
    xs = [t % 200 for t in allowed]
    ys = [t // 200 for t in allowed]
    assert (min(xs), max(xs)) == g.CENTER_HX and (min(ys), max(ys)) == g.CENTER_HY
    # every vanilla entering tile is inside
    assert g.can_center(20100) and not g.can_center(g.tile_at(160, 117))


def test_projection_matches_engine():
    rng = random.Random(4)
    centres = [t for t in range(g.HEX_COUNT) if g.can_center(t)]
    for window in ((640, 380), (1280, 860), (800, 500)):
        engine = Engine(*window)
        for centre in rng.sample(centres, 14):
            assert engine.set_center(centre) == 0
            view = g.View(centre, *window)
            for tile in rng.sample(range(g.HEX_COUNT), 400):
                assert view.hex(tile) == engine.tile_to_screen(tile), (centre, tile)
            for square in rng.sample(range(g.SQUARE_COUNT), 300):
                x, y = engine.square_to_screen(square)
                assert view.square(square) == (x, y), (centre, square)
                assert view.roof(square) == (x, y - 96)
            for _ in range(1500):
                x = rng.randrange(-3000, 3000 + window[0])
                y = rng.randrange(-1500, 1500 + window[1])
                assert view.hex_at(x, y) == engine.tile_from_screen(x, y), (centre, x, y)
                assert view.square_at(x, y) == engine.square_from_screen(x, y), (centre, x, y)
                assert view.square_at(x, y, roof=True) == engine.square_from_screen(x, y, roof=True), (centre, x, y)


def test_world_coordinates_and_inverse():
    assert g.hex_world(199) == (0, 0) and g.hex_world(39800) == (7968, 1200)
    assert g.hex_world(0)[1] == -1188 and g.hex_world(39999)[1] == 2388
    assert g.square_world(99) == (-16, -2) and g.square_world(0) == (4736, -1190)
    assert g.square_world(9900) == (7904, 1186) and g.square_world(9999) == (3152, 2374)
    for tile in range(g.HEX_COUNT):
        x, y = g.hex_world(tile)
        assert g.hex_from_world(x + 16, y + 8) == tile
        assert g.tile_at(*g.tile_xy(tile)) == tile
    for square in range(g.SQUARE_COUNT):
        x, y = g.square_world(square)
        assert g.square_from_world(x + 40, y + 18) == square
        assert g.square_from_world(x + 40, y + 18 - 96, roof=True) == square
    assert g.hex_from_world(-500, 0) == -1 and g.square_from_world(-500, -5000) == -1


def test_directions_and_distance_match_engine():
    engine = Engine(640, 380)
    rng = random.Random(9)
    assert engine.dir_tile == [list(g.DIR_TILE[0]), list(g.DIR_TILE[1])]
    for tile in rng.sample(range(g.HEX_COUNT), 3000) + [0, 199, 200, 39800, 39999, 20100]:
        assert g.is_edge(tile) == engine.is_edge(tile)
        for rotation in range(6):
            for dist in (1, 2, 7):
                assert g.tile_in_direction(tile, rotation, dist) == engine.tile_in_direction(tile, rotation, dist)
        cx, cy = g.hex_center(tile)
        for rotation, neighbour in enumerate(g.neighbors(tile)):
            if neighbour == -1:
                continue
            nx, ny = g.hex_center(neighbour)
            assert (nx - cx, ny - cy) == g.DIR_PIXELS[rotation]
            assert g.rotation_to(tile, neighbour) == rotation == engine.rotation_to(tile, neighbour)
            if not g.is_edge(tile):
                assert g.tile_in_direction(tile, rotation) == neighbour
    for _ in range(3000):
        a, b = rng.randrange(g.HEX_COUNT), rng.randrange(g.HEX_COUNT)
        assert g.distance(a, b) == engine.distance(a, b) == g.engine_distance(a, b), (a, b)
        assert g.rotation_to(a, b) == engine.rotation_to(a, b)
    assert g.distance(-1, 5) == 9999 == engine.distance(-1, 5)


def test_hex_square_relations():
    for tile in range(g.HEX_COUNT):
        hx, hy = g.tile_xy(tile)
        assert g.roof_square(tile) == (hy // 2) * 100 + hx // 2
        # geometric: the floor square whose art covers the hex centre
        assert g.floor_square(tile) == g.square_from_world(*g.hex_center(tile)), tile
    for square in (0, 99, 4242, 9999):
        hexes = g.square_hexes(square)
        assert len(hexes) == 4 and all(g.roof_square(t) == square for t in hexes)
        # documented positions of the four hex centres inside the 80x36 tile box
        sx, sy = g.square_world(square)
        offsets = sorted((g.hex_center(t)[0] - sx, g.hex_center(t)[1] - sy) for t in hexes)
        assert offsets == [(32, 10), (48, 22), (64, 10), (80, 22)]
    assert g.square_at(*g.square_xy(4242)) == 4242 and g.square_at(100, 0) == -1


def test_shapes():
    rng = random.Random(11)
    for centre in (20100, 0, 199, 39999, 201, 12345):
        seen = set()
        for radius in range(0, 7):
            ring = g.ring(centre, radius)
            brute = {t for t in range(g.HEX_COUNT) if g.distance(centre, t) == radius}
            assert set(ring) == brute and len(ring) == len(brute), (centre, radius)
            seen |= brute
        assert set(g.disc(centre, 6)) == seen
    assert len(g.ring(20100, 3)) == 18 and len(g.disc(20100, 3)) == 37

    for _ in range(1500):
        a, b = rng.randrange(g.HEX_COUNT), rng.randrange(g.HEX_COUNT)
        path = g.line(a, b)
        assert path[0] == a and path[-1] == b and len(path) == g.distance(a, b) + 1
        assert all(g.distance(path[i], path[i + 1]) == 1 for i in range(len(path) - 1))
        raster = g.engine_line(a, b)
        assert raster[0] == a and raster[-1] == b and len(raster) >= len(path)
    assert g.line(20100, 20100) == [20100]
    for rotation in range(6):                         # straight runs stay straight
        end = g.tile_in_direction(20100, rotation, 9)
        assert g.line(20100, end) == [g.tile_in_direction(20100, rotation, i) for i in range(10)]

    box = g.rect(g.tile_at(10, 20), g.tile_at(13, 22))
    assert len(box) == 12 and box[0] == g.tile_at(10, 20) and box[-1] == g.tile_at(13, 22)
    assert g.rect(g.tile_at(13, 22), g.tile_at(10, 20)) == box
