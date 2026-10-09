# SPDX-License-Identifier: MIT
"""Towers: what stands up over the wall. (author "height")

PLACING  All three stand on a 2 x 2 square of posts: origin = the hex of the back-right post, the
         others on (2, 0), (0, 2), (2, 2); the hexes between are blocked too (stores, ballast), and so
         are the hexes their ballast and ladder feet stand on (water: (1,0) (3,1) (3,2); watch: (-1,3)
         (1,3); rig: (1,2)) - the draw-order test painted a man standing there over the sandbags.
         They are 5.3 .. 5.9 m tall: stand them where nothing that must be clicked lies within 12
         rows BEHIND them (the back wall, the cut corners, the yards), and never in front of a roof
         they should show over (a roof is painted after every object).

    ht_tower_water   timber trestle with a riveted tank, down pipe and tap
    ht_tower_watch   scaffold tower with a sandbagged cab, tin roof, searchlight and ladder (a lamp)
    ht_tower_light   a lighting rig: ladder frame with three floodlights on a bar (a lamp)
    ht_mast          signal mast: lattice, two dishes, a blinking light, guy wires (one hex)
"""
import math

from kit import piece, geo, mat, G
from kit import height_extra as H
from kit import bomb_extra as bx
from kit import gate_extra as X
from kit import signs_extra as sx

X1, Y1 = G.hex_xy(2, 2)                 # (1.386, 1.6): the post diagonally opposite the origin
LEGS = [(0.0, 0.0), (X1, 0.0), (0.0, Y1), (X1, Y1)]
FOOT = H.uniq(H.hexes_in(-0.05, -0.05, X1 + 0.05, Y1 + 0.05))
CX, CY = X1 / 2.0, Y1 / 2.0


def _girts(z, kind="timber", out=0.12):
    """A ring of horizontal members round the four legs at height z."""
    for a, b in ((LEGS[2], LEGS[3]), (LEGS[3], LEGS[1]), (LEGS[0], LEGS[1]), (LEGS[0], LEGS[2])):
        ax, ay = a
        bx_, by = b
        dx, dy = (bx_ - ax), (by - ay)
        length = math.hypot(dx, dy)
        ux, uy = dx / length, dy / length
        p0, p1 = (ax - ux * out, ay - uy * out, z), (bx_ + ux * out, by + uy * out, z)
        if kind == "timber":
            bx.beam(p0, p1, (0.14, 0.07), H.wood(1, axis="X", width=0.6), name="girt", roll=90.0)
        else:
            geo.pipe([p0, p1], 0.04, H.tube(0.75, 5.0), name="girt")


def _braces(z0, z1, radius=0.028, back=True):
    H.xbrace(LEGS[2], LEGS[3], z0, z1, radius)              # the front face
    H.xbrace(LEGS[3], LEGS[1], z0, z1, radius)              # the left face
    if back:
        H.xbrace(LEGS[0], LEGS[1], z0, z1, radius, single=True)
        H.xbrace(LEGS[0], LEGS[2], z0, z1, radius, single=True)


@piece("ht_tower_water", title="Water Tower",
       desc="A riveted tank on a timber trestle. Rust has run down from every hoop; the tap at the bottom still drips.",
       footprint=FOOT + [(1, 0), (3, 1), (3, 2)], see_through=True, shadow="flat", material="metal", convert=H.GRADE)
def ht_tower_water(ctx):
    top = 3.25
    for k, (x, y) in enumerate(LEGS):
        H.post(x, y, 0.0, top, "timber", k)
        H.dots([(x, y + 0.08, 1.25), (x, y + 0.08, 2.35)], 0.06)
    for z in (1.25, 2.35):
        _girts(z)
    _braces(0.2, 1.2)
    _braces(1.35, 2.3)
    for y in (0.0, Y1):                                      # bearers and the deck the tank sits on
        bx.beam((-0.3, y, top + 0.06), (X1 + 0.3, y, top + 0.06), (0.16, 0.12), H.wood(3, axis="X", width=0.6), name="bearer")
    H.deck(-0.32, -0.3, X1 + 0.32, Y1 + 0.3, top + 0.2, along="x", seed=3, board=0.26, plates=1, missing=0.0, joists=False)
    tz = top + 0.2
    H.tank((CX, CY, tz), 0.84, 1.72, H.TEAL, seed=2, hoops=3, rust=0.55, stripe=H.CREAM)
    # straps from the lid to the deck corners, a vent, the float arm
    for sx_, sy_ in ((-1, 1), (1, 1), (1, -1)):
        H.strap([(CX + sx_ * 0.6, CY + sy_ * 0.6, tz + 1.74), (CX + sx_ * 0.86, CY + sy_ * 0.86, tz + 1.5), (CX + sx_ * 0.74, CY + sy_ * 0.86, tz + 0.02)],
                0.03)
    geo.pipe([(CX - 0.2, CY - 0.1, tz + 1.9), (CX - 0.2, CY - 0.1, tz + 2.2), (CX - 0.05, CY - 0.1, tz + 2.28)], 0.04, H.tube(0.7, 2.0), name="vent")
    # down pipe: out of the tank's foot, down the front-left leg to a tap over a bucket
    H.pipe_run([(CX + 0.5, CY + 0.72, tz + 0.2), (X1 + 0.14, Y1 + 0.14, tz + 0.2), (X1 + 0.14, Y1 + 0.14, 0.75), (X1 - 0.1, Y1 + 0.3, 0.75)],
               0.05, H.TEAL, seed=4)
    H.junk("bucket", (X1 - 0.12, Y1 + 0.36, 0.0), 1)
    # the overflow: a short pipe under the rim and the stain it has left down the tank and the deck edge
    f = H.face((X1 + 0.3, Y1 + 0.31, 0.0), geo.U)
    geo.pipe([(CX - 0.3, CY + 0.78, tz + 1.5), (CX - 0.3, CY + 0.98, tz + 1.45)], 0.04, H.tube(0.8, 1.0), name="overflow")
    H.streak(H.face((CX - 0.3 + 0.0, CY + 0.86, 0.0), geo.U), 0.0, tz + 1.42, 1.3, 0.14, 0.0, colour=(0.035, 0.03, 0.022))
    H.streak(f, X1 + 0.3 - (CX - 0.3), top + 0.18, 0.9, 0.12, 0.02, colour=(0.035, 0.03, 0.022))
    X.ladder((0.35, Y1 + 0.42, 0.0), (0.35, Y1 + 0.32, tz + 0.5), width=0.4)
    # under the trestle: drums on a pallet and a tarp tied between the left legs
    H.junk("barrel", (0.45, 0.55, 0.0), 2)
    H.junk("barrel", (0.95, 0.95, 0.0), 5)
    H.junk("crate", (X1 + 0.62, 0.55, 0.0), 4)
    H.junk("drum", (X1 + 0.6, 1.25, 0.0), 3, rot=20.0)


@piece("ht_tower_watch", title="Watch Tower",
       desc="Scaffold poles, a sandbagged cab and a searchlight that swings over the wall at night.",
       footprint=FOOT + [(-1, 3), (1, 3)], see_through=True, shadow="flat", material="metal", light=(6, 80), light_hex=(2, 2), convert=H.GRADE)
def ht_tower_watch(ctx):
    deck = 3.35
    tops = (5.56, 5.56, 5.24, 5.24)
    for k, ((x, y), top) in enumerate(zip(LEGS, tops)):
        H.post(x, y, 0.0, top, "tube", k)
        for z in (1.2, 2.3, deck - 0.15):
            geo.cylinder(0.075, 0.12, (x, y, z - 0.06), H.tube(0.4, 7.0), 10, name="clamp")
    for z in (1.2, 2.3, deck - 0.14):
        _girts(z, "tube", out=0.25)
    _braces(0.15, 1.15, 0.026)
    _braces(1.25, 2.25, 0.026)
    _braces(2.35, deck - 0.2, 0.026, back=False)
    H.deck(-0.35, -0.3, X1 + 0.35, Y1 + 0.4, deck, along="y", seed=5, board=0.24, plates=1, joists=False)
    # the cab: waist-high scrap on the front and left, sandbags on top of it, an open back
    ff = H.face((X1 + 0.3, Y1 + 0.32, 0.0), geo.U)
    fl = H.face((X1 + 0.3, -0.25, 0.0), geo.V)
    H.scrap_wall(ff, 0.0, X1 + 0.6, deck, deck + 0.95, 0.0, 41, "hpvh", (H.GREEN, H.RED, H.CREAM), 0.6, ragged=0.1, patches=1, tiers=1)
    H.scrap_wall(fl, 0.0, Y1 + 0.57, deck, deck + 0.95, 0.0, 42, "vph", (H.SLATE, H.OCHRE), 0.6, ragged=0.1, patches=1, tiers=1)
    X.sandbags((X1 + 0.2, Y1 + 0.2), (-0.25, Y1 + 0.2), courses=1, z=deck + 0.93, seed=7, size=(0.5, 0.3, 0.16))
    H.junk("box", (CX - 0.2, CY - 0.2, deck), 2)
    geo.cylinder(0.16, 0.42, (CX + 0.3, CY + 0.1, deck), H.wood(1), 10, name="stool")
    # roof
    top = H.face((X1 + 0.3, Y1 + 0.2, 0.0), geo.U)
    H.lean_roof(top, 0.0, X1 + 0.6, -(Y1 + 0.4), 0.2, 5.6, 5.28, 43, (None, H.RED, None), 0.6, weights=1, over=0.12)
    sx.sag_sheet([(-0.05, -0.02, 5.36), (X1 + 0.05, -0.02, 5.36), (X1 + 0.05, -0.06, deck + 1.1), (-0.05, -0.06, deck + 1.1)],
                 H.cloth((0.16, 0.17, 0.10), seed=3.0), sag=0.03, seed=5)
    # light: searchlight on the front-left corner, a caged lamp under the eave
    head = (X1 + 0.22, Y1 + 0.42, deck + 1.35)
    geo.pipe([(X1, Y1, deck + 0.9), (X1, Y1, deck + 1.2), head], 0.03, H.tube(0.5, 2.0), name="lamp_arm")
    H.flood(head, (0.75, 0.8, -0.45), size=0.2)
    H.lamp((CX, Y1 - 0.2, 5.16))
    X.ladder((-0.28, Y1 + 0.55, 0.0), (-0.28, Y1 + 0.42, deck + 0.9), width=0.4)
    # aerial with a rag on it, and what the watch keeps below
    geo.pipe([(X1, 0.0, 5.5), (X1 + 0.04, -0.02, 5.9)], 0.018, H.tube(0.4, 1.0), name="aerial")
    geo.box((0.3, 0.02, 0.18), (X1 - 0.12, -0.02, 5.68), geo.U + 10.0, H.cloth((0.42, 0.07, 0.04), seed=1.0), bevel=0.0, name="pennant")
    H.junk("crate", (0.45, 0.6, 0.0), 3)
    H.junk("tyres", (1.0, 1.05, 0.0), 2)
    X.sandbags((X1 + 0.3, Y1 + 0.42), (0.35, Y1 + 0.42), courses=2, z=0.0, seed=9, block=0.0)


FOOT_RIG = H.uniq(H.hexes_in(-0.05, -0.05, X1 + 0.05, 0.85))
RY = 0.8                                # the rig's second frame stands on row 1


@piece("ht_tower_light", title="Lighting Rig",
       desc="A scaffold with a plank deck and three floodlights wired to a car battery. Two of them still work.",
       footprint=FOOT_RIG + [(1, 2)], see_through=True, shadow="flat", material="metal", light=(8, 100), light_hex=(1, 1),
       convert=dict(H.GRADE, halo_levels=2))
def ht_tower_light(ctx):
    steel = H.tube(0.65, 2.0)
    deck = 3.7
    legs = [(0.0, 0.0), (X1, 0.0), (0.0, RY), (X1, RY)]
    for k, (x, y) in enumerate(legs):
        geo.pipe([(x, y, 0.0), (x, y, deck + (1.0 if y > 0.1 else 1.9))], 0.05, H.tube(0.65, 2.0 + k), name="leg")
        geo.box((0.28, 0.28, 0.05), (x, y, 0.0), 12.0 * k, H.tube(0.5, 6.0), bevel=0.0, name="base")
    z, k = 0.5, 0
    while z < deck - 0.1:                                     # the two ladder frames: rungs, every third a ledger
        for y in (0.0, RY):
            geo.pipe([(-0.12, y, z), (X1 + 0.12, y, z)], 0.04 if k % 3 == 0 else 0.024, steel, name="rung")
        if k % 3 == 0:
            for x in (0.0, X1):
                geo.pipe([(x, -0.12, z + 0.06), (x, RY + 0.12, z + 0.06)], 0.035, steel, name="transom")
        z += 0.5
        k += 1
    H.xbrace(legs[2], legs[3], 0.55, 2.0, 0.024)
    H.xbrace(legs[2], legs[3], 2.1, 3.5, 0.024, single=True)
    H.xbrace(legs[3], legs[1], 0.55, 3.5, 0.024)
    H.deck(-0.3, -0.25, X1 + 0.3, RY + 0.3, deck, along="y", seed=6, board=0.24, plates=1, joists=False)
    H.rail((X1 + 0.25, RY + 0.25), (-0.25, RY + 0.25), deck, 0.9, "pipe", 3, posts=2, infill="sheet")
    H.rail((X1 + 0.25, RY + 0.25), (X1 + 0.25, -0.2), deck, 0.9, "pipe", 4, posts=2)
    # the bar on the two back legs and its three lamps, aimed down over the rail
    top = deck + 1.8
    geo.pipe([(-0.5, 0.04, top), (X1 + 0.5, 0.04, top)], 0.045, H.tube(0.4, 7.0), name="bar")
    for i, x in enumerate((-0.35, CX, X1 + 0.35)):
        H.flood((x, 0.24, top - 0.24 - 0.04 * (i % 2)), (0.25 * (i - 1) + 0.3, 0.85, -0.6), size=0.2, lit=(i != 1))
        geo.pipe([(x, 0.04, top), (x, 0.2, top - 0.2)], 0.025, steel, name="yoke")
    # cables down to a battery box on the deck, a hazard board on the frame, ballast at the feet
    for dx, sag in ((0.2, 0.25), (0.5, 0.4)):
        geo.cable((CX, 0.06, top - 0.04), (dx, 0.3, deck + 0.3), sag, 0.018, count=12)
    geo.box((0.5, 0.34, 0.3), (0.35, 0.3, deck), 8.0, H.worn(0.5, 0.3, H.GREEN, 0.5, 3.0, streak=0.0), bevel=0.015, name="battery_box")
    X.plate(1.0, 0.5, (X1 + 0.1, RY + 0.06, 1.1), geo.U, X.hazard(width=0.3, wear=0.6, seed=2.0), thickness=0.02, name="hazard_board")
    X.ladder((X1 + 0.3, RY + 0.5, 0.0), (X1 + 0.3, RY + 0.34, deck + 0.7), width=0.38)
    X.sandbags((X1 - 0.1, RY + 0.36), (0.1, RY + 0.36), courses=2, z=0.0, seed=4, block=0.0)
    H.junk("drum", (0.7, 0.4, 0.0), 6, rot=70.0)
    geo.halo((CX + 0.9, 2.8, 0.0), radius=2.6, strength=0.5)


@piece("ht_mast", title="Signal Mast",
       desc="A lattice mast guyed with fence wire. Two dishes listen to nothing; the red lamp on top still blinks.",
       footprint=[(0, 0)], see_through=True, shadow="flat", material="metal", convert=H.GRADE)
def ht_mast(ctx):
    steel = H.tube(0.65, 3.0)
    top = 5.75
    r = 0.17
    chords = [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in (60.0, 180.0, 300.0)]
    for cx, cy in chords:
        geo.pipe([(cx, cy, 0.0), (cx * 0.5, cy * 0.5, top)], 0.03, steel, name="chord")
    z, k = 0.25, 0
    while z < top - 0.3:
        t0, t1 = 1.0 - 0.5 * z / top, 1.0 - 0.5 * (z + 0.45) / top
        a, b = chords[k % 3], chords[(k + 1) % 3]
        geo.pipe([(a[0] * t0, a[1] * t0, z), (b[0] * t1, b[1] * t1, z + 0.45)], 0.018, steel, name="lacing")
        z += 0.3
        k += 1
    geo.box((0.6, 0.6, 0.14), (0.0, 0.0, 0.0), 15.0, mat.concrete(seed=3.0), bevel=0.02, name="footing")
    # dishes: a big one looking down the valley, a small one, a yagi
    dish = H.drum_paint((0.24, 0.23, 0.20), 0.45, (), 4.0)
    for at, radius, aim in (((0.12, 0.2, 4.3), 0.42, (0.6, 0.75, 0.25)), ((-0.05, 0.16, 3.2), 0.26, (-0.5, 0.8, 0.1))):
        obj = geo.lathe([(0.0, 0.0), (radius * 0.5, 0.03), (radius * 0.85, 0.09), (radius, 0.15), (radius * 0.97, 0.16), (0.0, 0.03)],
                        at, dish, 18, name="dish")
        from mathutils import Vector
        obj.rotation_euler = Vector(aim).normalized().to_track_quat("Z", "Y").to_euler()
        geo.set_block(obj, 0.0)
    geo.pipe([(0.0, 0.0, 5.0), (-0.7, 0.25, 5.05)], 0.02, steel, name="yagi")
    for t in (0.25, 0.5, 0.75, 1.0):
        x, y = -0.7 * t, 0.25 * t
        geo.pipe([(x - 0.1, y - 0.25, 5.03), (x + 0.1, y + 0.25, 5.03)], 0.014, steel, name="yagi_element")
    geo.bulb((0.0, 0.0, top + 0.1), colour=(1.0, 0.1, 0.05), radius=0.07, strength=3.0, fx="alarm")
    # guys: three wires to pegs, each with a rag tied on so nobody walks into it
    wire = mat.flat((0.05, 0.045, 0.04), roughness=0.5, metallic=0.5)
    for a in (40.0, 150.0, 275.0):
        px, py = 1.05 * math.cos(math.radians(a)), 1.05 * math.sin(math.radians(a))
        geo.set_block(geo.pipe([(px, py, 0.0), (0.0, 0.0, 4.6)], 0.016, wire, name="guy"), 0.0)
        geo.set_block(geo.pipe([(px, py, 0.0), (px, py, 0.22)], 0.03, steel, name="peg"), 0.0)
        geo.box((0.16, 0.02, 0.12), (px * 0.7, py * 0.7, 1.35), geo.SCREEN, H.cloth((0.45, 0.10, 0.05), seed=a), bevel=0.0, name="rag")
    # a junction box and the cable that comes down to it
    geo.box((0.3, 0.14, 0.4), (0.0, 0.2, 0.9), geo.U, H.worn(0.3, 0.4, H.SLATE, 0.5, 2.0, streak=0.0), bevel=0.01, name="junction")
    geo.cable((0.05, 0.15, 4.2), (0.05, 0.22, 1.25), 0.1, 0.016, count=10)
