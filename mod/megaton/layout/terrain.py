# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Ground: desert, the cracked crater floor, worn paths and the slime pool.

Floor art is laid on squares (one square = 2 x 2 hexes). Both tile families
used here are corner tiles: every picture shows one kind of ground at each of
its four corners, so a ground map is drawn by deciding the kind at every
VERTEX of the square grid and picking, per square, a picture whose corners
agree. Vertex (vx, vy) is the top corner of square (vx, vy); that square's
corners are, clockwise from the top, the vertices (vx, vy), (vx, vy + 1),
(vx + 1, vy + 1) and (vx + 1, vy).

The corner tables below were measured from the art (slime*.frm: green or
earth at each corner; edg*.frm: share of dark crack pixels around each
corner), not taken from any documentation.
"""
import math
import random

from . import plan

# --- desert: "s"mooth sand or "R"ough cracked ground at the corners top, right, bottom, left
SMOOTH = [("edg5000.frm", 18), ("edg5003.frm", 9), ("edg5002.frm", 7), ("edg5001.frm", 6),
          ("edg5004.frm", 6), ("edg5005.frm", 5), ("edg5006.frm", 4), ("edg5007.frm", 4)]
ROUGH = ["edg4000.frm", "edg4001.frm", "edg4002.frm", "edg4003.frm", "edg4004.frm",
         "edg4005.frm", "edg4006.frm", "edg4007.frm", "edg4008.frm", "edg2003.frm"]
MIXED = {
    "RRRs": ["edg2003.frm", "edg4002.frm", "edg4003.frm", "edg4005.frm", "edg4008.frm"],
    "RRsR": ["edg4000.frm", "edgs002.frm"],
    "RsRR": ["edg4006.frm"],
    "sRRR": ["edg4007.frm", "edg3000.frm"],
    "RRss": ["edg2000.frm"],
    "RssR": ["edg1000.frm", "edg1001.frm", "edgs000.frm"],
    "sRRs": ["edg3000.frm", "edg4007.frm", "edgs004.frm"],
    "ssRR": ["edg6005.frm", "edg7003.frm"],
    "Rsss": ["edg4001.frm", "edg6007.frm", "edg6008.frm", "edg6009.frm", "edgs001.frm"],
    "sRss": ["edgs003.frm"],
    "ssRs": ["edg1002.frm", "edg2001.frm", "edg3001.frm", "edg6003.frm"],
    "sssR": ["edg6011.frm", "edg7001.frm"],
    "sRsR": ["edg6010.frm"],
    "RsRs": ["edg1000.frm", "edg3000.frm"],
}
# Smooth-looking pictures with a few cracks: scattered over open sand so it is not a carpet.
SPECKLED = ["edg1003.frm", "edg2002.frm", "edg6000.frm", "edg6001.frm", "edg6002.frm", "edg6004.frm",
            "edg6006.frm", "edg7000.frm", "edg7002.frm"]

# --- slime: "G"reen or "d"irt at the corners top, right, bottom, left
SLIME = {
    "GGGG": ["slime05.frm", "slime06.frm", "slime09.frm", "slime10.frm"],
    "dGdd": ["slime00.frm"],
    "ddGd": ["slime03.frm"],
    "Gddd": ["slime12.frm"],
    "dddG": ["slime15.frm"],
    "dGGd": ["slime01.frm", "slime02.frm", "slime25.frm", "slime26.frm"],
    "GGdd": ["slime04.frm", "slime08.frm", "slime21.frm", "slime23.frm"],
    "ddGG": ["slime07.frm", "slime11.frm", "slime20.frm", "slime22.frm"],
    "GddG": ["slime13.frm", "slime14.frm", "slime17.frm", "slime18.frm"],
    "GdGG": ["slime16.frm"],
    "dGGG": ["slime24.frm"],
    "GGGd": ["slime27.frm"],
    "GGdG": ["slime19.frm"],
}


def hex_to_vertex(hx, hy):
    """Vertex-grid position (fractional) of a hex centre.

    Square (qx, qy) lies under the hexes hx 2qx+1..2qx+2, hy 2qy..2qy+1
    (research/04 section 11.5), so its top corner - towards lower hx and
    lower hy - is at hex (2qx + 0.5, 2qy - 0.5)."""
    return (hx - 0.5) / 2.0, (hy + 0.5) / 2.0


def _distance_to_segment(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def pool_vertices(rng):
    """Vertices that are slime: a lumpy blob around the bomb, without diagonal pinches."""
    cx, cy = hex_to_vertex(*plan.BOMB)
    lumps = [(rng.uniform(0, math.tau), rng.uniform(0.35, 0.8)) for _ in range(4)]
    green = set()
    for vx in range(int(cx) - 6, int(cx) + 8):
        for vy in range(int(cy) - 6, int(cy) + 8):
            dx, dy = vx - cx, vy - cy
            angle = math.atan2(dy, dx)
            radius = 3.6 + sum(amp * math.cos(angle * (i + 2) + phase) * 0.5 for i, (phase, amp) in enumerate(lumps))
            if math.hypot(dx * 0.9, dy * 1.15) <= radius:
                green.add((vx, vy))
    # The art has no picture for two green corners touching only diagonally: fill such pinches.
    changed = True
    while changed:
        changed = False
        for vx, vy in list(green):
            for sx, sy in ((1, 1), (1, -1)):
                if (vx + sx, vy + sy) in green and (vx + sx, vy) not in green and (vx, vy + sy) not in green:
                    green.add((vx + sx, vy))
                    changed = True
    return green


def lay(m, rng):
    """Fill the whole floor grid (call it first: buildings lay their own floors on top).

    Returns {"pool": hexes on slime, "rough": vertices of cracked ground}."""
    names, weights = zip(*SMOOTH)
    bomb_v = hex_to_vertex(*plan.BOMB)
    path_segments = [(hex_to_vertex(*a), hex_to_vertex(*b), width / 2.0) for a, b, width in plan.PATHS]
    ring = plan.POOL_RING / 2.0

    def town_side(vx, vy):
        hx, hy = int(vx * 2), int(vy * 2)
        return plan.inside_wall(hx, hy)

    # 1. Rough ground: the crater floor inside the wall, thinning towards the wall and
    #    cleared along the paths; a few patches outside.
    noise = random.Random(rng.random())
    rough = set()
    for vy in range(0, 101):
        for vx in range(0, 101):
            if town_side(vx, vy):
                d = math.hypot(vx - bomb_v[0], (vy - bomb_v[1]) * 1.2)
                chance = 0.86 if d < 16 else 0.62
                on_path = any(_distance_to_segment(vx, vy, a, b) <= w for a, b, w in path_segments)
                on_ring = abs(math.hypot(vx - bomb_v[0], vy - bomb_v[1]) - ring) <= 0.9
                if on_path or on_ring:
                    chance = 0.06
            else:
                chance = 0.07
            if noise.random() < chance:
                rough.add((vx, vy))

    green = pool_vertices(rng)
    rough -= green

    def corner_code(vx, vy, group, yes, no):
        return "".join(yes if v in group else no
                       for v in ((vx, vy), (vx, vy + 1), (vx + 1, vy + 1), (vx + 1, vy)))

    pool_squares = set()
    for qy in range(100):
        for qx in range(100):
            slime = corner_code(qx, qy, green, "G", "d")
            if "G" in slime:
                m.set_floor(qx, qy, rng.choice(SLIME[slime]))
                pool_squares.add((qx, qy, slime))
                continue
            code = corner_code(qx, qy, rough, "R", "s")
            if code == "ssss":
                if rng.random() < 0.08:
                    m.set_floor(qx, qy, rng.choice(SPECKLED))
                else:
                    m.set_floor(qx, qy, rng.choices(names, weights)[0])
            elif code == "RRRR":
                m.set_floor(qx, qy, rng.choice(ROUGH))
            else:
                m.set_floor(qx, qy, rng.choice(MIXED[code]))

    # Hexes whose floor square is fully or mostly slime: where goo decals and the glow belong.
    pool_hexes = set()
    for qx, qy, slime in pool_squares:
        if slime.count("G") >= 3:
            for hx in (2 * qx + 1, 2 * qx + 2):
                for hy in (2 * qy, 2 * qy + 1):
                    pool_hexes.add((hx, hy))
    return {"pool": pool_hexes, "rough": rough}
