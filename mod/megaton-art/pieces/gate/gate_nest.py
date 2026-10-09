# SPDX-License-Identifier: MIT
"""The sniper's nest beside the gate: a scaffold tower with a plank deck, a sandbag parapet, a
sheet-iron roof and a ladder.

    mg_nest     origin = the hex of its back-right post. Posts stand on hexes (0, 0), (2, 0), (0, 2),
                (2, 2); everything between them is blocked (stores under the deck), and so is (3, 1),
                the foot of the ladder. In the town its origin is (92, 124): the front posts then
                stand on row 126, half a metre behind the front wall (row 127), four hexes to the
                screen right of the gate, and the deck (2.75 m) looks out over the wall (2.5 m).

World: +X = rising hx = screen lower-left, +Y = towards the viewer (screen lower-right).
"""
import math

from kit import piece, geo, mat, G
from kit import gate_extra as X

DECK = 2.75                 # top of the deck
X1, Y1 = G.hex_xy(2, 2)     # the post diagonally opposite the origin (1.386, 1.6)
FOOT = G.hex_xy(3, 1)       # where the ladder stands
ROOF_BACK, ROOF_FRONT = 4.95, 4.42


def _brace(a, b, steel, r=0.03):
    geo.pipe([a, b], r, steel, name="brace")


@piece("mg_nest", title="Watch Platform", desc="Scaffold poles, a plank deck, sandbags and a tin roof: a place to watch the gate from, when the town has anybody to spare.",
       footprint=[(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2), (3, 1)], see_through=True,
       shadow="flat", overhang=1.6, material="metal", light=(4, 60), light_hex=(1, 2),
       convert={"contrast": 1.42, "saturation": 1.0})          # the gate set's grade (gate_main.py GRADE)
def mg_nest(ctx):
    r = ctx.rng
    steel = mat.steel(rust=0.7, seed=4)
    dark = mat.steel(rust=0.45, seed=7)
    # posts: scaffold tube on base plates, the back pair taller (the roof falls to the front)
    for px, py, top in ((0, 0, ROOF_BACK - 0.1), (X1, 0, ROOF_BACK - 0.1), (0, Y1, ROOF_FRONT - 0.05), (X1, Y1, ROOF_FRONT - 0.05)):
        geo.pipe([(px, py, 0.0), (px, py, top)], 0.05, steel, name="post")
        geo.box((0.24, 0.24, 0.04), (px, py, 0.0), 20.0, dark, bevel=0.0, name="base_plate")
        for z in (DECK - 0.16, 3.82):                       # clamps where ledgers meet the post
            geo.cylinder(0.075, 0.12, (px, py, z - 0.06), dark, segments=10, name="clamp")
    # ledgers under the deck and a guard rail above it
    for z, rad in ((DECK - 0.1, 0.045), (1.35, 0.035), (3.82, 0.035)):
        geo.pipe([(-0.25, 0, z), (X1 + 0.25, 0, z)], rad, steel, name="ledger")
        geo.pipe([(-0.25, Y1, z), (X1 + 0.25, Y1, z)], rad, steel, name="ledger")
        geo.pipe([(0, -0.2, z + 0.07), (0, Y1 + 0.2, z + 0.07)], rad, steel, name="ledger")
        geo.pipe([(X1, -0.2, z + 0.07), (X1, Y1 + 0.2, z + 0.07)], rad, steel, name="ledger")
    # cross braces on the two faces the viewer sees, single braces behind
    _brace((0, Y1, 0.15), (X1, Y1, 1.3), steel)
    _brace((X1, Y1, 0.15), (0, Y1, 1.3), steel)
    _brace((0, Y1, 1.4), (X1, Y1, DECK - 0.2), steel)
    _brace((X1, 0, 0.15), (X1, Y1, 1.3), steel)
    _brace((X1, Y1, 1.4), (X1, 0, DECK - 0.2), steel)
    _brace((0, 0, 0.15), (X1, 0, DECK - 0.2), steel)
    # deck: planks across, ends ragged
    wood = [mat.planks(colour=(0.25, 0.14, 0.07), axis="Y", width=0.5, seed=s) for s in (1, 2, 3)]
    x = -0.34
    i = 0
    while x < X1 + 0.3:
        w = r.uniform(0.19, 0.26)
        over = r.uniform(0.18, 0.34)
        geo.box((w - 0.015, Y1 + 0.2 + over + 0.22, 0.05), (x + w / 2, Y1 / 2 + (over - 0.22) / 2, DECK - 0.05), 0.0, wood[i % 3],
                bevel=0.006, name="deck_plank", roll=r.uniform(-1.0, 1.0))
        x += w
        i += 1
    # parapet: sandbags on the three open sides, two courses, a third on the front corner
    z = DECK
    X.sandbags((X1 + 0.22, Y1 + 0.25), (-0.26, Y1 + 0.25), courses=3, z=z, seed=11, size=(0.56, 0.32, 0.17))
    X.sandbags((X1 + 0.24, -0.1), (X1 + 0.24, Y1 + 0.05), courses=2, z=z, seed=13, size=(0.56, 0.32, 0.17))
    X.sandbags((-0.26, -0.1), (-0.26, Y1 + 0.05), courses=2, z=z, seed=15, size=(0.56, 0.32, 0.17))
    # roof: three sheets on two purlins, falling to the front; one sheet slipped
    for py, pz in ((0.0, ROOF_BACK - 0.12), (Y1, ROOF_FRONT - 0.07)):
        geo.pipe([(-0.4, py, pz), (X1 + 0.4, py, pz)], 0.04, steel, name="purlin")
    depth = Y1 + 0.85
    slope = math.degrees(math.atan2(ROOF_BACK - ROOF_FRONT, Y1))
    paints = (None, (0.20, 0.07, 0.04), None)
    x_left = X1 + 0.5
    for i in range(3):
        w = (X1 + 1.0) / 3 + 0.07
        geo.corrugated_panel(w, depth + r.uniform(-0.1, 0.12), (x_left, -0.42, ROOF_BACK + 0.09 + 0.015 * (i % 2)),
                             geo.U, mat.corrugated(rust=0.5 + 0.15 * i, seed=40 + i, paint=paints[i]), wavelength=0.11, depth=0.035,
                             tilt=90.0 + slope + r.uniform(-1.2, 1.2), roll=r.uniform(-1.5, 1.5), name=f"roof{i}")
        x_left -= w - 0.07
    # windbreak: a tarpaulin lashed across the back, and half-way along the right side
    canvas = mat.tarp((0.16, 0.17, 0.10), seed=3)
    geo.box((X1 + 0.2, 0.03, 1.0), (X1 / 2, -0.06, DECK + 0.72), 0.0, canvas, bevel=0.01, name="tarp_back", tilt=3.0)
    # ladder up the screen-left side, lashed to the deck
    X.ladder((FOOT[0] + 0.1, FOOT[1] + 0.2, 0.0), (X1 + 0.12, FOOT[1] + 0.2, DECK + 0.75), width=0.42,
             material=mat.planks(colour=(0.30, 0.18, 0.09), axis="Z", width=0.3, seed=5))
    # the lamp: a caged bulb under the front eave, and a searchlight on the corner post
    geo.bulb((X1 * 0.5, Y1 - 0.1, ROOF_FRONT - 0.22), colour=(1.0, 0.66, 0.28), radius=0.07, strength=2.0)
    geo.pipe([(X1 * 0.5, Y1 - 0.1, ROOF_FRONT - 0.08), (X1 * 0.5, Y1 - 0.1, ROOF_FRONT - 0.17)], 0.02, dark, name="lamp_drop")
    head = (-0.05, Y1 + 0.18, DECK + 1.22)
    X.floodlight(head, (-0.55, 0.75, -0.42), size=0.17, strength=1.6)
    geo.pipe([(0, Y1, DECK + 1.07), head], 0.03, dark, name="lamp_arm")
    # what a watchman keeps up there: an ammunition box, a stool, a thermos-sized something
    geo.box((0.42, 0.26, 0.22), (0.45, 0.55, DECK), 25.0, mat.painted_metal((0.10, 0.13, 0.07), flaking=0.3, seed=2), bevel=0.012,
            name="ammo_box")
    geo.cylinder(0.16, 0.42, (0.95, 0.9, DECK), mat.planks(colour=(0.22, 0.13, 0.07), seed=8), segments=10, name="stool")
    # a rag of a pennant on a whip aerial
    geo.pipe([(X1, 0, ROOF_BACK - 0.1), (X1 + 0.05, -0.03, ROOF_BACK + 0.75)], 0.018, dark, name="aerial")
    geo.box((0.34, 0.02, 0.2), (X1 + 0.05 - 0.17, -0.03, ROOF_BACK + 0.5), geo.U + 12.0, mat.tarp((0.42, 0.06, 0.04), seed=1), bevel=0.0,
            name="pennant", roll=-8.0)
    # stores under the deck, in the shade
    geo.barrel((0.45, 0.6, 0.0), seed=9)
    geo.crate((0.75, 0.6, 0.6), (0.95, 1.15, 0.0), 12.0, seed=6)
    geo.crate((0.5, 0.45, 0.4), (0.85, 1.12, 0.6), -8.0, seed=7)
