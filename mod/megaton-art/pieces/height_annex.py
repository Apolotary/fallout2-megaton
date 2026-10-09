# SPDX-License-Identifier: MIT
"""The annex kit: what bolts onto a plain rectangular shack to break its outline. (author "height")

Two families, one per wall the camera sees from outside:

 _u  against a FRONT wall (a wall on hex row hy, the one with the eave towards the camera).
     Origin on row hy + 1 (even hx): the wall's face is then 0.65 m behind the origin row. Hex 0 is
     the screen-RIGHT end, the piece runs to the screen left. The stock eave covers the back of
     every roof here, as it should: the annex comes out from under it.
 _v  against a LEFT wall (a wall on hex column hx). Origin on column hx + 2 (even hy): the wall's
     face is 1.30 m to the right of the origin column, and the annex fills the odd column between.
     Row 0 is the FAR end, the piece runs towards the camera.

    piece            size        blocks                               what
    ht_shed_u_a      4 hexes     rows 0 and 1 (y 0 .. 0.4)            tin shed, padlocked, barrel and crates beside it
    ht_shed_u_b      6 hexes     rows 0 and 1                         plank store, one end open: shelves and drums in the dark
    ht_porch_u       5 hexes     rows 0 .. 1 (y 0 .. 0.8)             board floor, three posts, tin roof, bench
    ht_bay_u         3 hexes     (0, 0) (2, 0)                        a boarded-over bay on brackets, junk under it
    ht_stairs_u      6 hexes     rows 0 and 1                         stairs up the wall to a landing at the eave: to nowhere
    ht_shed_v_a      4 rows      (-1, 0 .. 3)                         tin shed with a plank door in its end
    ht_porch_v       5 rows      columns -1 and 0, rows 0 .. 4        board floor, three posts, roof falling to the left
    ht_bay_v         3 rows      (-1, 1) (-1, 2)                      boarded bay on brackets
    ht_stairs_v      6 rows      (-1, 0 .. 5)                         stairs up the wall, rising away from the camera

NEVER in front of a door or a window the town uses, nor on a doorstep (the check fails it). Nothing
here is taller than the eave except the stairs' outer hand rail, which stays under 3.4 m: higher
than that and the building's own roof would be painted over it.
"""
import math

from kit import piece, geo, mat, G
from kit import height_extra as H
from kit import bomb_extra as bx
from kit import gate_extra as X
from kit import signs_extra as sx

HEX = H.HEX
WALL_U = -0.8 + G.STOCK_WALL_FRONT_U + 0.01       # y of a front wall's face, seen from the origin row
WALL_V = -G.SQ_U_M + G.STOCK_WALL_FRONT_V + 0.01  # x of a left wall's face, seen from the origin column
# see_through "u" / "v": every annex stands in front of a wall the player can be BEHIND (he is inside the
# house). Solid, it hid him as soon as he stood near that wall; flagged like the wall it leans on, the
# engine opens its see-through circle in it exactly as it does in the wall.
ANNEX = dict(shadow="flat", material="metal", convert=H.GRADE)
ANNEX_U = dict(ANNEX, see_through="u")
ANNEX_V = dict(ANNEX, see_through="v")
# The odd hexes of the origin row lie between the origin row and the wall: the wall blocks them in every
# legal placement. Three pieces name them in their footprint so that the draw-order test (which tries a
# man on every hex a footprint leaves free) and a careless placement agree with the town.
WALL_HEXES_6 = [(1, 0), (3, 0), (5, 0)]


def _xs(n):
    """World x of the right and left ends of an n-hex piece."""
    return -0.32, (n - 1) * HEX + 0.32


def _foot_u(n, y1=0.45):
    x0, x1 = _xs(n)
    return H.uniq(H.hexes_in(x0 - 0.03, -0.05, x1 + 0.03, y1))


def _foot_v(rows, x0=-0.75, x1=-0.6):
    return H.uniq(H.hexes_in(x0, -0.45, x1, rows * 0.8 - 0.35))


def _box_u(x0, x1, y1, front, back, seed, kinds, paints, rust=0.55, roof_paints=(None, H.RED, None), weights=2, tiers=1, end=True):
    """A lean-to box against a front wall between world x0 (screen right) and x1: front face on y1,
    left end face, dark core, roof from the wall (height `back`) down to the front (`front`)."""
    w = x1 - x0
    depth = y1 - WALL_U
    geo.box((w - 0.06, depth - 0.04, front - 0.04), ((x0 + x1) / 2.0, (WALL_U + y1) / 2.0, 0.0), 0.0, H.dark(), bevel=0.0, name="core")
    ff = H.face((x1, y1, 0.0), geo.U)
    H.scrap_wall(ff, 0.0, w, 0.0, front, 0.0, seed, kinds, paints, rust, ragged=0.08, patches=2, tiers=tiers)
    fl = H.face((x1, WALL_U, 0.0), geo.V)
    if end:
        H.scrap_wall(fl, 0.0, depth, 0.0, front + 0.1, 0.0, seed + 7, kinds, paints, rust, ragged=0.04, patches=0, tiers=1, sheet_w=(0.5, 0.7))
        gable = H.worn(depth, back - front, paints[seed % len(paints)] if paints else None, rust, float(seed), streak=0.2)
        sx.plate([(0.0, 0.0), (depth, 0.0), (0.0, back - front)], fl.at(0.0, 0.0, front), geo.V, gable, thickness=0.02, name="gable")
    for uu in (0.0, w):
        bx.beam(ff.at(uu, 0.03, 0.0), ff.at(uu, 0.03, front + 0.04), (0.1, 0.1), H.wood(3, axis="X", width=0.6), name="corner")
    H.lean_roof(ff, 0.0, w, -depth, 0.14, back, front + 0.05, seed, roof_paints, rust, weights=weights, over=0.1)
    return ff, fl


def _box_v(y0, y1, x1, front, back, seed, kinds, paints, rust=0.55, roof_paints=(None, H.TEAL, None), weights=2, tiers=1):
    """The same against a left wall between world y0 (far) and y1 (near): its long face on x1, its
    near end face on y1, roof from the wall down to the left."""
    length = y1 - y0
    depth = x1 - WALL_V
    geo.box((depth - 0.04, length - 0.06, front - 0.04), ((WALL_V + x1) / 2.0, (y0 + y1) / 2.0, 0.0), 0.0, H.dark(), bevel=0.0, name="core")
    fl = H.face((x1, y0, 0.0), geo.V)
    H.scrap_wall(fl, 0.0, length, 0.0, front, 0.0, seed, kinds, paints, rust, ragged=0.08, patches=2, tiers=tiers)
    ff = H.face((x1, y1, 0.0), geo.U)
    H.scrap_wall(ff, 0.0, depth, 0.0, front + 0.1, 0.0, seed + 7, kinds, paints, rust, ragged=0.04, patches=0, tiers=1, sheet_w=(0.5, 0.7))
    gable = H.worn(depth, back - front, paints[seed % len(paints)] if paints else None, rust, float(seed), streak=0.2)
    sx.plate([(0.0, 0.0), (depth, 0.0), (depth, back - front)], ff.at(0.0, 0.0, front), geo.U, gable, thickness=0.02, name="gable")
    for uu in (0.0, length):
        bx.beam(fl.at(uu, 0.03, 0.0), fl.at(uu, 0.03, front + 0.04), (0.1, 0.1), H.wood(3, axis="X", width=0.6), name="corner")
    H.lean_roof(fl, 0.0, length, -depth, 0.14, back, front + 0.05, seed, roof_paints, rust, weights=weights, over=0.1)
    return fl, ff


def _padlock(f, u, z, d=0.1):
    H.dots([f.at(u, d, z)], 0.09, X.bright_metal((0.45, 0.40, 0.25)), name="padlock")
    H.strap([f.at(u - 0.18, d - 0.02, z + 0.1), f.at(u, d, z + 0.04), f.at(u + 0.16, d - 0.02, z + 0.12)], 0.03)


# ------------------------------------------------------------------- front walls
@piece("ht_shed_u_a", title="Tin Shed", desc="A lean-to of roofing tin against the wall, padlocked. Whatever is in it rattles when the wind gets up.",
       footprint=_foot_u(4), **ANNEX_U)
def ht_shed_u_a(ctx):
    x0, x1 = _xs(4)
    sx0 = x0 + 0.78                                          # the shed proper: hexes 1..3; hex 0 holds the overflow
    ff, fl = _box_u(sx0, x1, 0.5, 1.9, 2.3, 51, "vvhp", (H.TEAL, H.CREAM, H.RED), roof_paints=(None, H.OCHRE, None))
    H.door(ff, 0.3, 0.02, 0.8, 1.68, 0.05, "sheet", 6, paint=H.RED)
    _padlock(ff, 0.3 + 0.72, 0.9)
    H.junk("barrel", (x0 + 0.35, 0.05, 0.0), 3)
    H.junk("crate", (x0 + 0.38, -0.38, 0.0), 1)
    H.junk("can", (x0 + 0.4, -0.38, 0.5), 2)
    bx.plank((x0 + 0.1, 0.42, 0.0), (x0 + 0.25, -0.5, 1.7), 0.16, 0.035, H.wood(2, axis="X", width=0.6), name="leaning_plank")


@piece("ht_shed_u_b", title="Plank Store", desc="Boards nailed up into a store room. One end stands open: shelves, drums, and the dark.",
       footprint=_foot_u(6) + WALL_HEXES_6, **ANNEX_U)
def ht_shed_u_b(ctx):
    x0, x1 = _xs(6)
    split = x0 + 1.75
    ff, fl = _box_u(split, x1, 0.5, 1.95, 2.32, 52, "wwpw", (H.GREEN, H.CREAM), roof_paints=(H.RED, None, None, H.SLATE), weights=3)
    H.window(ff, 0.6, 0.85, 0.75, 0.55, 0.05, "boarded", 5)
    H.door(ff, (x1 - split) - 1.0, 0.02, 0.78, 1.7, 0.05, "plank", 4)
    # the open end: two posts and the roof carried on, a shelf with tins, drums, a tarp rolled up under the eave
    for x in (x0 + 0.06, x0 + 0.9):
        H.post(x, 0.44, 0.0, 1.98, "timber", 2, pad=False)
    of = H.face((split, 0.5, 0.0), geo.U)
    H.lean_roof(of, 0.0, split - x0, -(0.5 - WALL_U), 0.14, 2.3, 1.98, 53, (None, H.TEAL), 0.6, weights=1, over=0.08)
    geo.box((split - x0 - 0.1, 0.5 - WALL_U - 0.1, 1.9), ((x0 + split) / 2.0, (WALL_U + 0.5) / 2.0 - 0.3, 0.0), 0.0, H.dark(), bevel=0.0, name="dark")
    for z in (0.75, 1.3):
        bx.plank((x0 + 0.05, -0.1, z), (split - 0.05, -0.1, z), 0.32, 0.035, H.wood(1, axis="X", width=0.6), name="shelf")
    for k in range(4):
        H.junk("can", (x0 + 0.25 + 0.38 * k, -0.1, 0.77 if k % 2 else 1.32), k)
    H.junk("barrel", (x0 + 0.42, 0.2, 0.0), 1)
    H.junk("drum", (x0 + 1.2, 0.18, 0.0), 2, rot=10.0)
    geo.cylinder(0.11, split - x0 - 0.1, (x0 + 0.05, 0.5, 1.82), H.cloth((0.13, 0.16, 0.19), seed=1.0), 10, name="rolled_tarp", roll=90.0)


PORCH_N = 5


@piece("ht_porch_u", title="Porch", desc="A board floor on blocks, three posts and a tin roof. Somebody has left a bench here for the evenings.",
       footprint=_foot_u(PORCH_N, 0.85), see_through="u", shadow="flat", material="wood", light=(4, 70), light_hex=(2, 1), convert=H.GRADE)
def ht_porch_u(ctx):
    x0, x1 = _xs(PORCH_N)
    front = 0.92
    for x in (x0 + 0.2, (x0 + x1) / 2.0, x1 - 0.2):
        geo.box((0.3, front - WALL_U, 0.14), (x, (WALL_U + front) / 2.0, 0.0), 0.0, mat.concrete(seed=x), bevel=0.02, name="sleeper")
    H.deck(x0, WALL_U + 0.02, x1, front, 0.2, along="y", seed=21, board=0.2, plates=1, missing=0.0, joists=False, overhang=0.06)
    posts = [G.hex_xy(dhx, 1) for dhx in (0, 2, 4)]
    for k, (x, y) in enumerate(posts):
        H.post(x, y, 0.18, 2.06, "timber" if k != 1 else "pole", k, pad=False)
        H.brace((x, y, 1.6), (x + 0.4, y, 2.02), 0.022)
    bx.beam((x0 - 0.05, 0.8, 2.08), (x1 + 0.05, 0.8, 2.08), (0.12, 0.14), H.wood(3, axis="X", width=0.6), name="plate")
    f = H.face((x1, 0.8, 0.0), geo.U)
    H.lean_roof(f, 0.0, x1 - x0, -(0.8 - WALL_U), 0.2, 2.46, 2.1, 22, (None, H.RED, H.CREAM, None, H.TEAL), 0.55, weights=2, over=0.1)
    H.rail((posts[1][0], 0.8), (posts[0][0], 0.8), 0.2, 0.8, "wood", 3, posts=2, infill="planks")
    # the bench against the wall, a crate for a table, a lamp on the middle post
    for x in (x0 + 0.5, x0 + 1.5):
        geo.box((0.12, 0.34, 0.4), (x, WALL_U + 0.25, 0.2), 0.0, H.wood(3), bevel=0.01, name="bench_leg")
    bx.plank((x0 + 0.3, WALL_U + 0.25, 0.62), (x0 + 1.7, WALL_U + 0.25, 0.62), 0.36, 0.045, H.wood(2, axis="X", width=0.6), name="bench")
    H.junk("crate", (x1 - 0.6, 0.1, 0.2), 5)
    H.junk("can", (x1 - 0.6, 0.1, 0.7), 1)
    H.lamp((posts[1][0] + 0.25, 0.86, 1.95))
    # two plank steps off the left end
    for k in range(2):
        bx.plank((x1 + 0.2 + 0.26 * k, 0.1, 0.13 - 0.07 * k), (x1 + 0.2 + 0.26 * k, front - 0.05, 0.13 - 0.07 * k), 0.26, 0.045,
                 H.wood(k, axis="X", width=0.6), name="step")


@piece("ht_bay_u", title="Boarded Bay", desc="A window bay somebody built out on brackets and somebody else boarded over.",
       footprint=[(0, 0), (2, 0), (1, 0)], **ANNEX_U)
def ht_bay_u(ctx):
    x0, x1 = -0.05, 2 * HEX + 0.4
    y1 = -0.08
    z0, z1 = 0.78, 2.12
    w, depth = x1 - x0, y1 - WALL_U
    geo.box((w - 0.04, depth, z1 - z0), ((x0 + x1) / 2.0, (WALL_U + y1) / 2.0, z0), 0.0, H.dark(), bevel=0.0, name="core")
    ff = H.face((x1, y1, 0.0), geo.U)
    fl = H.face((x1, WALL_U, 0.0), geo.V)
    H.scrap_wall(ff, 0.0, w, z0, z1, 0.0, 61, "pw", (H.CREAM, H.SLATE), 0.5, ragged=0.03, patches=0, tiers=1, battens=False)
    H.sheet(fl, 0.0, z0, depth, z1 - z0, 0.0, "p", H.CREAM, 0.6, 62, bolts=False)
    H.window(ff, 0.4, z0 + 0.42, w - 0.8, 0.62, 0.05, "boarded", 9)
    H.lean_roof(ff, 0.0, w, -depth, 0.12, z1 + 0.3, z1 + 0.08, 63, (H.RED, None), 0.6, weights=0, over=0.08, purlins=False)
    for x in (x0 + 0.15, x1 - 0.15):                         # brackets
        H.brace((x, WALL_U + 0.02, 0.2), (x, y1 - 0.02, z0), 0.035)
    bx.beam((x0 - 0.03, y1, z0 - 0.04), (x1 + 0.03, y1, z0 - 0.04), (0.1, 0.1), H.wood(3, axis="X", width=0.6), name="sill")
    for k in range(3):
        H.streak(ff, 0.3 + 0.6 * k, z0 - 0.02, 0.3 + 0.1 * k, 0.07, 0.03)
    # under it: what makes the ground there unusable
    H.junk("crate", (0.1, -0.2, 0.0), 2)
    H.junk("tyres", (HEX * 2 - 0.05, -0.12, 0.0), 4)
    H.junk("bucket", (0.75, 0.0, 0.0), 1)


@piece("ht_stairs_u", title="Outside Stairs", desc="Steps up the outside of the wall to a landing at the eave. Whatever door they led to is gone.",
       footprint=_foot_u(6) + WALL_HEXES_6, see_through="u", shadow="flat", material="wood", convert=H.GRADE)
def ht_stairs_u(ctx):
    x0, x1 = _xs(6)
    top_z = 2.3
    ya, yb = WALL_U + 0.04, 0.34
    yc = (ya + yb) / 2.0
    land = x0 + 1.25                                         # landing at the screen-right end
    H.deck(x0, ya, land, yb, top_z, along="y", seed=31, board=0.22, plates=1, missing=0.0, joists=False, overhang=0.04)
    for x in (x0 + 0.1, land - 0.1):
        H.post(x, yb - 0.08, 0.0, top_z - 0.08, "timber", int(x * 10) % 3)
        H.brace((x, yb - 0.08, 1.5), (x, ya + 0.05, top_z - 0.12), 0.024)
    H.xbrace((x0 + 0.1, yb - 0.08), (land - 0.1, yb - 0.08), 0.3, top_z - 0.4, 0.024)
    H.stairs((x1 - 0.1, yc, 0.0), (land, yc, top_z - 0.02), width=yb - ya, seed=5, rails=(False, True) )
    H.rail((land, yb - 0.02), (x0, yb - 0.02), top_z, 0.9, "wood", 2, posts=2, infill="tarp")
    # the landing leads nowhere: the opening is boarded from outside and stuff has piled up on it
    H.junk("crate", (x0 + 0.4, ya + 0.3, top_z), 3)
    H.junk("tyres", (x0 + 0.95, ya + 0.35, top_z), 1)
    # under the flight: drums, a prop
    H.post(x0 + 2.3, yb - 0.08, 0.0, 1.25, "tube", 1)
    H.junk("barrel", (land + 0.45, yc, 0.0), 6)
    H.junk("drum", (land + 1.3, yc - 0.1, 0.0), 2, rot=85.0)


# -------------------------------------------------------------------- left walls
@piece("ht_shed_v_a", title="Tin Shed", desc="A lean-to of roofing tin against the wall, with a plank door in its end.",
       footprint=_foot_v(4), **ANNEX_V)
def ht_shed_v_a(ctx):
    y0, y1 = -0.2, 2.35
    fl, ff = _box_v(y0, y1, -0.36, 1.9, 2.3, 71, "vhvp", (H.OCHRE, H.SLATE, H.RED), roof_paints=(None, None, H.TEAL))
    H.door(ff, 0.08, 0.02, 0.72, 1.68, 0.05, "plank", 3)
    H.window(fl, 0.9, 0.9, 0.7, 0.5, 0.05, "shutter", 2)
    H.junk("can", (-0.55, y0 - 0.12, 0.0), 2)


@piece("ht_porch_v", title="Porch", desc="A board floor on blocks, three posts and a tin roof down the side of the house.",
       footprint=_foot_v(5, -0.75, 0.05), see_through="v", shadow="flat", material="wood", light=(4, 70), light_hex=(0, 2), convert=H.GRADE)
def ht_porch_v(ctx):
    y0, y1 = -0.3, 3.5
    front = 0.14
    for y in (y0 + 0.2, (y0 + y1) / 2.0, y1 - 0.2):
        geo.box((front - WALL_V, 0.3, 0.14), ((WALL_V + front) / 2.0, y, 0.0), 0.0, mat.concrete(seed=y), bevel=0.02, name="sleeper")
    H.deck(WALL_V + 0.02, y0, front, y1, 0.2, along="x", seed=23, board=0.2, plates=1, missing=0.0, joists=False, overhang=0.06)
    posts = [G.hex_xy(0, dhy) for dhy in (0, 2, 4)]
    for k, (x, y) in enumerate(posts):
        H.post(x, y, 0.18, 2.06, "timber" if k != 1 else "tube", k + 1, pad=False)
        H.brace((x, y, 1.6), (x, y + 0.45, 2.02), 0.022)
    bx.beam((0.0, y0 - 0.05, 2.08), (0.0, y1 + 0.05, 2.08), (0.12, 0.14), H.wood(3, axis="X", width=0.6), name="plate")
    f = H.face((0.0, y0, 0.0), geo.V)
    H.lean_roof(f, 0.0, y1 - y0, -(0.0 - WALL_V), 0.2, 2.46, 2.1, 24, (H.TEAL, None, H.OCHRE, None, H.RED), 0.55, weights=2, over=0.1)
    H.rail(posts[1], posts[2], 0.2, 0.8, "wood", 5, posts=2, infill="sheet")
    bx.plank((WALL_V + 0.26, y0 + 0.4, 0.62), (WALL_V + 0.26, y0 + 1.8, 0.62), 0.36, 0.045, H.wood(2, axis="X", width=0.6), name="bench")
    for y in (y0 + 0.6, y0 + 1.6):
        geo.box((0.34, 0.12, 0.4), (WALL_V + 0.26, y, 0.2), 0.0, H.wood(3), bevel=0.01, name="bench_leg")
    H.junk("barrel", (WALL_V + 0.4, y1 - 0.5, 0.2), 4)
    H.lamp((0.06, posts[1][1] + 0.3, 1.95))


@piece("ht_bay_v", title="Boarded Bay", desc="A window bay somebody built out on brackets and somebody else boarded over.",
       footprint=[(-1, 1), (-1, 2)], **ANNEX_V)
def ht_bay_v(ctx):
    y0, y1 = 0.1, 1.75
    x1 = -0.74
    z0, z1 = 0.78, 2.12
    length, depth = y1 - y0, x1 - WALL_V
    geo.box((depth, length - 0.04, z1 - z0), ((WALL_V + x1) / 2.0, (y0 + y1) / 2.0, z0), 0.0, H.dark(), bevel=0.0, name="core")
    fl = H.face((x1, y0, 0.0), geo.V)
    ff = H.face((x1, y1, 0.0), geo.U)
    H.scrap_wall(fl, 0.0, length, z0, z1, 0.0, 65, "pw", (H.GREEN, H.CREAM), 0.5, ragged=0.03, patches=0, tiers=1, battens=False)
    H.sheet(ff, 0.0, z0, depth, z1 - z0, 0.0, "p", H.GREEN, 0.6, 66, bolts=False)
    H.window(fl, 0.35, z0 + 0.42, length - 0.7, 0.62, 0.05, "boarded", 7)
    H.lean_roof(fl, 0.0, length, -depth, 0.12, z1 + 0.3, z1 + 0.08, 67, (None, H.OCHRE), 0.6, weights=0, over=0.08, purlins=False)
    for y in (y0 + 0.15, y1 - 0.15):
        H.brace((WALL_V + 0.02, y, 0.2), (x1 - 0.02, y, z0), 0.035)
    for k in range(3):
        H.streak(fl, 0.25 + 0.55 * k, z0 - 0.02, 0.3 + 0.1 * k, 0.07, 0.03)
    H.junk("barrel", (-HEX, 0.45, 0.0), 2)
    H.junk("crate", (-HEX - 0.1, 1.25, 0.0), 6)


@piece("ht_stairs_v", title="Outside Stairs", desc="Steps up the outside of the wall to a landing at the eave. Whatever door they led to is gone.",
       footprint=_foot_v(6), see_through="v", shadow="flat", material="wood", convert=H.GRADE)
def ht_stairs_v(ctx):
    y0, y1 = -0.6, 4.1
    top_z = 2.3
    xa, xb = WALL_V + 0.04, -0.4
    xc = (xa + xb) / 2.0
    land = y0 + 1.3                                          # landing at the far end
    H.deck(xa, y0, xb, land, top_z, along="x", seed=33, board=0.22, plates=1, missing=0.0, joists=False, overhang=0.04)
    for y in (y0 + 0.1, land - 0.1):
        H.post(xb - 0.08, y, 0.0, top_z - 0.08, "tube", int(y * 10) % 3)
        H.brace((xb - 0.08, y, 1.5), (xa + 0.05, y, top_z - 0.12), 0.024)
    H.xbrace((xb - 0.08, y0 + 0.1), (xb - 0.08, land - 0.1), 0.3, top_z - 0.4, 0.024)
    H.stairs((xc, y1 - 0.1, 0.0), (xc, land, top_z - 0.02), width=xb - xa, seed=6, rails=(True, False))
    H.rail((xb - 0.02, y0), (xb - 0.02, land), top_z, 0.9, "pipe", 4, posts=2, infill="sheet")
    H.junk("barrel", (xa + 0.35, y0 + 0.4, top_z), 5)
    H.junk("box", (xa + 0.4, y0 + 0.95, top_z), 3)
    H.post(xb - 0.08, y0 + 2.4, 0.0, 1.3, "timber", 2)
    H.junk("crate", (xc, land + 0.5, 0.0), 4)
    H.junk("tyres", (xc, land + 1.35, 0.0), 2)
