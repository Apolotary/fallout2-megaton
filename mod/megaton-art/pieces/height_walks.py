# SPDX-License-Identifier: MIT
"""Catwalks, a pipe gantry and footbridges: the level the player walks UNDER. (author "height")

Everything here is decorative: nobody goes up. The decks stand 2.8 m up on trestle bents, and
the hexes under them stay walkable (the slicer cuts the deck onto the walkable hexes under it as
parts that do not block), so a critter under a deck sorts correctly.

    piece              runs along        blocks (the bent's two posts)     chain: next copy at
    ht_walk_u_a / _b   a hex row         (1, 0) (1, 1)                     (+4, 0) / (-4, 0)
    ht_walk_u_c / _d   a hex row         (0, 0): ONE post, the light kind   (+4, 0) / (-4, 0)   use these in front of a path
    ht_walk_u_e        the same, rope rails and a bare deck: the one that hides least
    ht_walk_v_a / _b   a hex column      (-1, 1) (1, 1)                    (0, +4) / (0, -4)
    ht_walk_stair_u    a hex row         its landing bent (1,0) (1,1) and everything under the flight,
                                         which comes down to the screen LEFT: put it at (+4, 0) of the
                                         last ht_walk_u (its landing laps that deck's end)
    ht_walk_stair_v    a hex column      landing bent (-1,1) (1,1) and the flight, which comes down
                                         TOWARDS the camera: put it at (0, +4) of the last ht_walk_v
    ht_gantry          a hex row         (-1,0) (-1,1) and (9,0) (9,1): nine hexes of clear span between
                                         the bents (hexes 0..8); the truss is 2.95 .. 3.75 m up
    ht_bridge_6        a hex row         nothing: it lies from roof edge to roof edge across a 6-hex gap
                                         between two buildings. Origin = (hx of the right-hand building's
                                         LEFT wall + 2, any even row between their back and front walls)
    ht_bridge_4        the same for a 4-hex gap

WHAT A DECK HIDES. Seen from the camera a deck 2.8 m up covers the ground 5.8 m (8 rows) behind it,
its rail what is up to 11 rows behind: keep doors, people and containers out of that band (the
playability check names every target a deck covers). Roofs are painted after every object: a rail
that stands within a metre to the LEFT of a roofed building, or within 2.6 m in FRONT of one, is cut
off by that roof - the bridges have no rail on their right-hand metre for that reason.
"""
import math

from kit import piece, geo, mat, G
from kit import height_extra as H
from kit import bomb_extra as bx
from kit import gate_extra as X
from kit import signs_extra as sx

DECK = 2.82
HEX = H.HEX
BENT_U = (HEX, -0.4), (HEX, 0.4)                # hexes (1, 0) and (1, 1)
BENT_V = (-HEX, 0.4), (HEX, 0.4)                # hexes (-1, 1) and (1, 1)


def _bent(posts, seed, kinds=("tube", "timber")):
    """Two posts, a cap beam on their heads, cross bracing, knee braces: one trestle bent."""
    (ax, ay), (bx_, by) = posts
    for k, (x, y) in enumerate(posts):
        H.post(x, y, 0.0, DECK - 0.18, kinds[(seed + k) % len(kinds)], seed + k)
    dx, dy = bx_ - ax, by - ay
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    cap0, cap1 = (ax - ux * 0.35, ay - uy * 0.35, DECK - 0.15), (bx_ + ux * 0.35, by + uy * 0.35, DECK - 0.15)
    bx.beam(cap0, cap1, (0.14, 0.14), H.wood(3, axis="X", width=0.6), name="cap")
    H.xbrace((ax, ay), (bx_, by), 0.5, DECK - 0.5, 0.026, single=bool(seed % 2))
    H.dots([(ax, ay, DECK - 0.42), (bx_, by, DECK - 0.42), (ax, ay, 0.55), (bx_, by, 0.55)], 0.11, H.tube(0.4, 7.0), name="clamps")
    return (ux, uy)


def _walk_u(seed, rails=("pipe", "pipe"), infill=(None, None), lamp=True, pipes=True, tarp=False):
    r = geo.rng(seed)
    _bent(BENT_U, seed)
    x0, x1 = HEX - 1.45, HEX + 1.45
    y0, y1 = -0.62, 0.62
    for y in (-0.42, 0.42):                                  # ledgers along the run, on the cap beam
        geo.pipe([(x0 - 0.05, y, DECK - 0.07), (x1 + 0.05, y, DECK - 0.07)], 0.045, H.tube(0.75, 4.0 + seed), name="ledger")
        for side in (-1, 1):                                 # knee braces from the post to the ledger
            H.brace((HEX, y, DECK - 0.75), (HEX + side * 0.75, y, DECK - 0.1), 0.024)
    H.deck(x0, y0, x1, y1, DECK, along="y", seed=seed, board=0.25, plates=1, missing=0.08, joists=False)
    H.rail((x1, y0 + 0.04), (x0, y0 + 0.04), DECK, 0.95, rails[0], seed, infill=infill[0], posts=3)        # the far side
    H.rail((x1, y1 - 0.04), (x0, y1 - 0.04), DECK, 0.95, rails[1], seed + 1, infill=infill[1], posts=3, mid=rails[1] != "rope")
    if pipes:                                                # a water pipe slung under the near edge on straps
        z = DECK - 0.32
        H.pipe_run([(x0, y1 - 0.1, z), (x1, y1 - 0.1, z)], 0.075, H.TEAL if seed % 2 else H.RED, seed, flanges=False)
        for x in (x0 + 0.4, HEX + 0.35, x1 - 0.4):
            H.strap([(x, y1 - 0.02, DECK - 0.05), (x, y1 - 0.2, z - 0.09), (x, y1 - 0.02, z - 0.02)], 0.03)
        H.dots([(HEX - 0.7, y1 - 0.1, z)], 0.2, H.tube(0.6, 1.0), name="flange")
    if lamp:
        geo.pipe([(HEX + 0.9, 0.0, DECK - 0.1), (HEX + 0.9, 0.0, DECK - 0.38)], 0.012, mat.flat((0.03, 0.03, 0.03)), name="flex")
        H.lamp((HEX + 0.9, 0.0, DECK - 0.38))
    if tarp:
        sx.sag_sheet([(x0 + 0.2, y1 - 0.02, DECK + 0.95), (x0 + 1.5, y1 - 0.02, DECK + 0.95), (x0 + 1.45, y1 + 0.06, DECK + 0.2),
                      (x0 + 0.25, y1 + 0.06, DECK + 0.25)], H.cloth((0.14, 0.17, 0.20), seed=float(seed)), sag=0.03, seed=seed)
    geo.cable((x0, y0 + 0.04, DECK + 0.9), (x1, y0 + 0.04, DECK + 0.85), r.uniform(0.25, 0.4), 0.016)
    return x0, x1, y0, y1


def _walk_v(seed, rails=("pipe", "pipe"), infill=(None, None), lamp=True, pipes=True, tarp=False):
    r = geo.rng(seed)
    _bent(BENT_V, seed, kinds=("timber", "tube"))
    x0, x1 = -0.74, 0.74
    y0, y1 = 0.4 - 1.66, 0.4 + 1.66
    for x in (-0.5, 0.5):
        geo.pipe([(x, y0 - 0.05, DECK - 0.07), (x, y1 + 0.05, DECK - 0.07)], 0.045, H.tube(0.75, 4.0 + seed), name="ledger")
        for side in (-1, 1):
            H.brace((x * 1.386, 0.4, DECK - 0.75), (x, 0.4 + side * 0.8, DECK - 0.1), 0.024)
    H.deck(x0, y0, x1, y1, DECK, along="x", seed=seed, board=0.25, plates=1, missing=0.08, joists=False)
    H.rail((x0 + 0.04, y0), (x0 + 0.04, y1), DECK, 0.95, rails[0], seed, infill=infill[0], posts=3)          # the far (right) side
    H.rail((x1 - 0.04, y0), (x1 - 0.04, y1), DECK, 0.95, rails[1], seed + 1, infill=infill[1], posts=3, mid=rails[1] != "rope")
    if pipes:
        z = DECK - 0.32
        H.pipe_run([(x1 - 0.1, y0, z), (x1 - 0.1, y1, z)], 0.075, H.TEAL if seed % 2 else H.OCHRE, seed, flanges=False)
        for y in (y0 + 0.4, 0.75, y1 - 0.4):
            H.strap([(x1 - 0.02, y, DECK - 0.05), (x1 - 0.2, y, z - 0.09), (x1 - 0.02, y, z - 0.02)], 0.03)
    if lamp:
        geo.pipe([(0.0, 1.5, DECK - 0.1), (0.0, 1.5, DECK - 0.38)], 0.012, mat.flat((0.03, 0.03, 0.03)), name="flex")
        H.lamp((0.0, 1.5, DECK - 0.38))
    if tarp:
        sx.sag_sheet([(x1 - 0.02, y0 + 0.3, DECK + 0.95), (x1 - 0.02, y0 + 1.6, DECK + 0.95), (x1 + 0.06, y0 + 1.55, DECK + 0.2),
                      (x1 + 0.06, y0 + 0.35, DECK + 0.25)], H.cloth((0.30, 0.10, 0.06), seed=float(seed)), sag=0.03, seed=seed)
    geo.cable((x0 + 0.04, y0, DECK + 0.9), (x0 + 0.04, y1, DECK + 0.85), r.uniform(0.25, 0.4), 0.016)
    return x0, x1, y0, y1


def _walk_slim(seed, rails=("pipe", "rope"), infill=(None, None), lamp=False, kind="beam", flag=False, half=0.6, cable=True):
    """The light catwalk: ONE post on the origin hex with a T head, for runs that stand in front of a
    path - a walker behind it loses the top of his head to the deck and nothing else."""
    r = geo.rng(seed)
    H.post(0.0, 0.0, 0.0, DECK - 0.18, kind, seed)
    bx.beam((0.0, -half - 0.02, DECK - 0.15), (0.0, half + 0.02, DECK - 0.15), (0.12, 0.14), H.wood(3, axis="X", width=0.6), name="head")
    for y in (-half + 0.1, half - 0.1):
        H.brace((0.0, 0.0, DECK - 0.85), (0.0, y, DECK - 0.2), 0.024)
    x0, x1 = -1.5, 1.5
    y0, y1 = -half, half
    for y in (-half + 0.18, half - 0.18):
        geo.pipe([(x0 - 0.05, y, DECK - 0.07), (x1 + 0.05, y, DECK - 0.07)], 0.04, H.tube(0.75, 4.0 + seed), name="ledger")
    H.deck(x0, y0, x1, y1, DECK, along="y", seed=seed, board=0.25, plates=1, missing=0.08, joists=False)
    H.rail((x1, y0 + 0.04), (x0, y0 + 0.04), DECK, 0.95, rails[0], seed, infill=infill[0], posts=3)
    H.rail((x1, y1 - 0.04), (x0, y1 - 0.04), DECK, 0.95, rails[1], seed + 1, infill=infill[1], posts=3, mid=rails[1] != "rope")
    if lamp:
        geo.pipe([(0.8, 0.0, DECK - 0.1), (0.8, 0.0, DECK - 0.32)], 0.012, mat.flat((0.03, 0.03, 0.03)), name="flex")
        H.lamp((0.8, 0.0, DECK - 0.32))
    if flag:
        geo.pipe([(x0 + 0.1, y0 + 0.04, DECK + 0.9), (x0 + 0.1, y0 + 0.04, DECK + 1.75)], 0.018, H.tube(0.5, 1.0), name="staff")
        geo.box((0.42, 0.02, 0.26), (x0 + 0.1 - 0.21, y0 + 0.04, DECK + 1.45), geo.U + 8.0, H.cloth((0.42, 0.08, 0.04), seed=float(seed)),
                bevel=0.0, name="pennant")
    if cable:
        geo.cable((x0, y0 + 0.04, DECK + 0.9), (x1, y0 + 0.04, DECK + 0.85), r.uniform(0.2, 0.3), 0.016)


WALK = dict(see_through=True, shadow="flat", material="wood", overhang=0.6, convert=H.GRADE)
DESC = "Planks on scaffold poles, a pipe strapped underneath: one of the walkways the town has grown over its own head."


@piece("ht_walk_u_a", title="Catwalk", desc=DESC, footprint=[(1, 0), (1, 1)], light=(4, 70), light_hex=(1, 1), **WALK)
def ht_walk_u_a(ctx):
    x0, x1, y0, y1 = _walk_u(1, rails=("pipe", "pipe"), infill=("sheet", None))
    H.junk("can", (HEX - 0.9, -0.3, DECK), 2)


@piece("ht_walk_u_b", title="Catwalk", desc=DESC, footprint=[(1, 0), (1, 1)], **WALK)
def ht_walk_u_b(ctx):
    x0, x1, y0, y1 = _walk_u(2, rails=("wood", "rope"), infill=("planks", None), lamp=False, tarp=True)
    H.junk("bucket", (HEX + 0.8, -0.25, DECK), 1)
    geo.pipe([(HEX - 0.5, 0.3, DECK - 0.1), (HEX - 0.5, 0.3, DECK - 0.9)], 0.014, mat.flat((0.17, 0.13, 0.08)), name="rope")
    H.junk("bucket", (HEX - 0.5, 0.3, DECK - 1.16), 3)


@piece("ht_walk_v_a", title="Catwalk", desc=DESC, footprint=[(-1, 1), (1, 1)], light=(4, 70), light_hex=(1, 1), **WALK)
def ht_walk_v_a(ctx):
    _walk_v(3, rails=("pipe", "pipe"), infill=("sheet", None))
    H.junk("box", (-0.3, -0.6, DECK), 2)


@piece("ht_walk_v_b", title="Catwalk", desc=DESC, footprint=[(-1, 1), (1, 1)], **WALK)
def ht_walk_v_b(ctx):
    _walk_v(4, rails=("wood", "rope"), infill=("planks", None), lamp=False, tarp=True)
    H.junk("can", (0.25, 1.6, DECK), 1)


@piece("ht_walk_u_c", title="Catwalk", desc=DESC, footprint=[(0, 0)], light=(4, 70), light_hex=(0, 0), **WALK)
def ht_walk_u_c(ctx):
    _walk_slim(5, rails=("pipe", "pipe"), lamp=True, kind="beam")
    H.junk("can", (-0.9, -0.3, DECK), 3)


@piece("ht_walk_u_d", title="Catwalk", desc=DESC, footprint=[(0, 0)], **WALK)
def ht_walk_u_d(ctx):
    _walk_slim(6, rails=("wood", "rope"), kind="timber", flag=True)
    H.junk("bucket", (0.9, -0.25, DECK), 2)


@piece("ht_walk_u_e", title="Catwalk", desc=DESC, footprint=[(0, 0)], **WALK)
def ht_walk_u_e(ctx):
    """The barest one: rope both sides, nothing stored on it. For a spot where people pass close behind."""
    _walk_slim(8, rails=("rope", "rope"), kind="tube", half=0.42, cable=False)


# ------------------------------------------------------------------------ stairs
STAIR_U_FOOT = H.uniq([(1, 0), (1, 1)] + H.hexes_in(1.95, -0.45, 4.75, 0.45))


@piece("ht_walk_stair_u", title="Catwalk Stairs",
       desc="A flight of plank steps up to the catwalk. One tread is missing and nobody has fixed it.",
       footprint=STAIR_U_FOOT, see_through=True, shadow="flat", material="wood", overhang=0.6, convert=H.GRADE)
def ht_walk_stair_u(ctx):
    _bent(BENT_U, 5)
    H.deck(HEX - 1.9, -0.62, HEX + 0.55, 0.62, DECK, along="y", seed=7, board=0.25, plates=0, joists=False)
    for y in (-0.42, 0.42):
        geo.pipe([(HEX - 1.95, y, DECK - 0.07), (HEX + 0.6, y, DECK - 0.07)], 0.045, H.tube(0.75, 5.0), name="ledger")
    H.rail((HEX + 0.5, -0.58), (HEX - 1.9, -0.58), DECK, 0.95, "pipe", 5, posts=3)
    top, foot = (HEX + 0.55, 0.0, DECK - 0.02), (4.6, 0.0, 0.0)
    H.stairs(foot, top, width=0.95, seed=3, rails=(True, True))
    # a prop under the middle of the flight, and what has been shoved under the stairs
    mid = (2.75, 0.0)
    H.post(mid[0], -0.4, 0.0, 1.3, "timber", 2)
    H.post(mid[0], 0.4, 0.0, 1.3, "tube", 3)


STAIR_V_FOOT = H.uniq([(-1, 1), (1, 1)] + H.hexes_in(-0.45, 1.95, 0.45, 4.5))


@piece("ht_walk_stair_v", title="Catwalk Stairs",
       desc="A flight of plank steps up to the catwalk. One tread is missing and nobody has fixed it.",
       footprint=STAIR_V_FOOT, see_through=True, shadow="flat", material="wood", overhang=0.6, convert=H.GRADE)
def ht_walk_stair_v(ctx):
    _bent(BENT_V, 6, kinds=("timber", "tube"))
    H.deck(-0.74, 0.4 - 1.66, 0.74, 1.0, DECK, along="x", seed=9, board=0.25, plates=0, joists=False)
    for x in (-0.5, 0.5):
        geo.pipe([(x, 0.4 - 1.7, DECK - 0.07), (x, 1.05, DECK - 0.07)], 0.045, H.tube(0.75, 5.0), name="ledger")
    H.rail((-0.7, 0.4 - 1.66), (-0.7, 0.95), DECK, 0.95, "pipe", 6, posts=2)
    top, foot = (0.0, 1.0, DECK - 0.02), (0.0, 4.4, 0.0)
    H.stairs(foot, top, width=0.95, seed=4, rails=(True, True))
    H.post(-0.4, 2.5, 0.0, 1.45, "timber", 1)
    H.post(0.4, 2.5, 0.0, 1.45, "tube", 2)
    H.junk("tyres", (0.0, 3.15, 0.0), 3)


# ------------------------------------------------------------------------ gantry
SPAN0, SPAN1 = -HEX, 9 * HEX                       # the two bents: hexes (-1, *) and (9, *)
GANTRY_FOOT = [(-1, 0), (-1, 1), (9, 0), (9, 1)]


@piece("ht_gantry", title="Pipe Gantry",
       desc="A trussed bridge of scaffold tube carrying the water main across the street, with a plank to walk it and lamps slung underneath.",
       footprint=GANTRY_FOOT, see_through=True, shadow="flat", material="metal", overhang=0.6, light=(6, 80), light_hex=(9, 1),
       convert=H.GRADE)
def ht_gantry(ctx):
    r = ctx.rng
    low, high = 2.98, 3.72
    steel = H.tube(0.7, 3.0)
    for k, x in enumerate((SPAN0, SPAN1)):
        for j, y in enumerate((-0.4, 0.4)):
            H.post(x, y, 0.0, high + 0.1, "beam", k + j)
        H.xbrace((x, -0.4), (x, 0.4), 0.4, 1.7, 0.028)
        H.xbrace((x, -0.4), (x, 0.4), 1.8, low - 0.1, 0.028, single=True)
        X.sandbags((x + 0.3, 0.75), (x - 0.3, 0.75), courses=2, z=0.0, seed=3 + k, block=0.0)
    # the truss: two planes of chords, posts and diagonals; cross members under the plank
    bays = 5
    step = (SPAN1 - SPAN0) / bays
    for y in (-0.4, 0.4):
        for z, radius in ((low, 0.055), (high, 0.045)):
            geo.pipe([(SPAN0 - 0.25, y, z), (SPAN1 + 0.25, y, z)], radius, steel, name="chord")
        for i in range(1, bays):
            x = SPAN0 + step * i
            geo.pipe([(x, y, low), (x, y, high)], 0.03, steel, name="vertical")
        for i in range(bays):
            xa, xb = SPAN0 + step * i, SPAN0 + step * (i + 1)
            if i % 2:
                xa, xb = xb, xa
            H.brace((xa, y, low), (xb, y, high), 0.024)
    for i in range(bays + 1):
        x = SPAN0 + step * i
        geo.pipe([(x, -0.5, low + 0.02), (x, 0.5, low + 0.02)], 0.035, steel, name="transom")
        geo.pipe([(x, -0.4, high + 0.02), (x, 0.4, high + 0.02)], 0.028, steel, name="tie")
    H.deck(SPAN0 - 0.2, -0.05, SPAN1 + 0.2, 0.36, low + 0.11, along="x", seed=11, board=0.2, plates=0, missing=0.0, joists=False, overhang=0.3)
    # the main: a fat pipe with flanges on saddles, a thinner one beside it, a drip
    z = low + 0.22
    H.pipe_run([(SPAN0 - 0.5, -0.22, z), (SPAN1 + 0.5, -0.22, z)], 0.15, H.TEAL, 2, flanges=False)
    for i in range(bays + 1):
        x = SPAN0 + step * i + 0.2
        geo.cylinder(0.19, 0.07, (x, -0.22, z), H.tube(0.6, 1.0), 14, name="flange", roll=90.0)
    H.pipe_run([(SPAN0 - 0.4, -0.22, z + 0.26), (SPAN1 + 0.4, -0.22, z + 0.26)], 0.05, None, 5, flanges=False)
    for k, x in enumerate((SPAN0 - 0.5, SPAN1 + 0.5)):       # the main turns down at both ends and goes to ground
        H.pipe_run([(x, -0.22, z), (x + (0.0 if k else 0.0), -0.22, 0.25)], 0.15, H.TEAL, 3 + k, flanges=False)
        geo.cylinder(0.2, 0.08, (x, -0.22, 1.2), H.tube(0.6, 1.0), 14, name="flange")
    f = H.face((SPAN1, 0.44, 0.0), geo.U)
    for u in (1.3, 3.1, 4.4, 5.9):
        H.streak(f, u, low - 0.02, r.uniform(0.25, 0.5), 0.07, 0.0, colour=(0.03, 0.03, 0.022))
    # slung underneath: two lamps, a dead traffic light, a board with an arrow
    mid = (SPAN0 + SPAN1) / 2.0
    for x in (mid - 1.7, mid + 1.9):
        geo.pipe([(x, 0.0, low), (x, 0.0, low - 0.25)], 0.012, mat.flat((0.03, 0.03, 0.03)), name="flex")
        H.lamp((x, 0.0, low - 0.25), size=1.0)
    board_w = 1.5
    bf = H.face((mid + board_w / 2.0 - 0.4, 0.46, 0.0), geo.U)
    H.sheet(bf, 0.0, low - 0.62, board_w, 0.5, 0.0, "p", H.OCHRE, 0.45, 9, bolts=False, streaks=0.4)
    sx.arrow(1.0, bf.at(0.25, 0.03, low - 0.37), geo.U, mat.flat((0.03, 0.028, 0.025)), shaft=0.12, head=0.3, thickness=0.015)
    for u in (0.1, board_w - 0.1):
        H.strap([bf.at(u, 0.0, low - 0.12), bf.at(u, 0.0, low)], 0.02)
    tl = (mid - 2.6, 0.2)
    geo.pipe([(tl[0], tl[1], low), (tl[0], tl[1], low - 0.2)], 0.014, mat.flat((0.03, 0.03, 0.03)), name="hanger")
    geo.box((0.22, 0.2, 0.55), (tl[0], tl[1], low - 0.75), geo.U + 12.0, H.worn(0.22, 0.55, H.OCHRE, 0.6, 4.0, streak=0.0), bevel=0.02,
            name="traffic_light")
    H.dots([(tl[0] + 0.02, tl[1] + 0.11, low - 0.75 + dz) for dz in (0.1, 0.27, 0.44)], 0.1, H.dark(), name="lenses")
    geo.bulb_string((SPAN0, 0.42, high), (SPAN1, 0.42, high), count=9, sag=0.45,
                    colours=((1.0, 0.75, 0.4), (1.0, 0.3, 0.1), (1.0, 0.75, 0.4), (0.4, 0.9, 0.3)), radius=0.055)


# ----------------------------------------------------------------------- bridges
def _bridge(n, seed):
    """Footbridge over a gap of n hexes between two buildings' walls: wall lines at x = -2 HEX and (n - 2) HEX."""
    r = geo.rng(seed)
    xr, xl = -2 * HEX + 0.12, (n - 2) * HEX - 0.12
    y0, y1 = -0.5, 0.5
    z = 2.76
    for y in (-0.36, 0.36):                                 # two bearers from wall head to wall head
        bx.beam((xr - 0.15, y, z - 0.12), (xl + 0.15, y, z - 0.12), (0.1, 0.16), H.wood(3, axis="X", width=0.6), name="bearer")
    H.deck(xr, y0, xl, y1, z, along="y", seed=seed, board=0.24, plates=1, missing=0.1, joists=False)
    for x, sign in ((xr, 1.0), (xl, -1.0)):                 # knee braces down to the walls
        for y in (-0.36, 0.36):
            H.brace((x - sign * 0.1, y, 1.85), (x + sign * 0.75, y, z - 0.2), 0.028)
    rail0 = xr + 1.12                                       # no rail on the right-hand metre: that roof would cut it off
    H.rail((xl, y1 - 0.03), (rail0, y1 - 0.03), z, 0.9, "pipe" if seed % 2 else "wood", seed, infill="sheet" if n > 4 else None,
           posts=3 if n > 4 else 2)
    H.rail((xl, y0 + 0.03), (rail0, y0 + 0.03), z, 0.9, "rope", seed + 1, posts=3 if n > 4 else 2)
    bx.plank((xr + 0.02, y1 - 0.02, z + 0.06), (rail0, y1 - 0.02, z + 0.06), 0.12, 0.035, H.wood(1, axis="X", width=0.6), name="kerb", roll=90.0)
    # washing on a line under it, and a lamp
    line0, line1 = (xl - 0.1, 0.4, z - 0.3), (xr + 0.1, 0.4, z - 0.34)
    geo.cable(line0, line1, 0.1, 0.014)
    f = H.face((xl - 0.1, 0.42, 0.0), geo.U)
    u = 0.5
    k = 0
    while u < (xl - xr) - 0.9:
        w = r.uniform(0.35, 0.6)
        sx.cloth(f, u, z - 0.4, w, r.uniform(0.45, 0.75), sx.fabric(((0.42, 0.14, 0.08), (0.36, 0.33, 0.26), (0.10, 0.17, 0.22), (0.30, 0.22, 0.08))[k % 4],
                                                                     seed=float(seed + k)), folds=2.0, depth=0.03, seed=seed + k)
        u += w + r.uniform(0.15, 0.4)
        k += 1
    H.junk("bucket", (xl - 0.5, -0.2, z), seed)
    return z


BRIDGE = dict(footprint=[], see_through=True, shadow="flat", material="wood", overhang=0.5, convert=H.GRADE)
BRIDGE_DESC = "Planks from one roof to the next, a rope for a rail, and somebody's washing underneath."


@piece("ht_bridge_6", title="Footbridge", desc=BRIDGE_DESC, **BRIDGE)
def ht_bridge_6(ctx):
    _bridge(6, 1)


@piece("ht_bridge_4", title="Footbridge", desc=BRIDGE_DESC, **BRIDGE)
def ht_bridge_4(ctx):
    _bridge(4, 2)
