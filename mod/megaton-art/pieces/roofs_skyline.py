# SPDX-License-Identifier: MIT
"""Rooftop silhouettes, first half: tanks, chimneys, a mast, a wind pump. They make the skyline jagged.

    python3 mod/megaton-art/build.py preview pieces/roofs_skyline.py [NAME]
    python3 mod/megaton-art/build.py add pieces/roofs_skyline.py

WHERE THEY STAND (the rule of pieces/signs/sg_roof.py, unchanged): roofs are painted after every object,
so nothing can stand ON a roof. These stand BEHIND a building and rise over its far edge: put the
piece's ORIGIN on row hy_lo - 3 of the building (even hx, even hy); its feet are on the piece's row 1
(hy_lo - 2), just behind the roof's edge, and the roof hides the lowest 2.6 m. Everything worth
seeing is therefore above ROOF (2.66 m); nothing reaches higher than 6 m (224 px above its hex).
Each piece is one part, anchored on the highest hx of its feet (so a walker on the same row sorts
correctly), with no ground shadow (it would fall behind the building).

    rf_tank_bowser     a road tanker's barrel on a trestle, 3 hexes wide            feet (-2,1) (0,1) (2,1)
    rf_rain_catcher    a patchwork funnel of tarpaulin over a plate tank             feet (0,1) (2,1)
    rf_chimney_drums   oil drums welded end to end, a hat on stays                   foot (0,1)
    rf_chimney_box     a square riveted flue with a wind cowl, a thin pipe beside it foot (0,1)
    rf_chimney_stack   a tapering boiler stack with a spark cage and a ladder        foot (0,1)
    rf_mast_aerials    a lattice mast with fishbone aerials and an insulator arm     foot (0,1)
    rf_windpump        a wind pump on a lattice tower; its wheel turns (4 frames,    foot (0,1)
                       one blade pitch per loop: all blades alike)
"""
import math

from kit import piece, geo, mat, G
from kit import signs_extra as sx
from kit import gate_extra as gx
from kit import bomb_extra as bx
from kit import roofs_extra as rx

ROOF = G.WALL_H                     # 2.66 m: where a roof is drawn
CONV = {"exposure": 0.25, "contrast": 1.22}
B = G.hex_xy(2, 1)[0] - G.hex_xy(0, 1)[0]          # 1.386 m: from one even hex of a row to the next


def frame_at(dhx=0.0, rot=geo.U):
    """A frame standing on row 1 at (possibly fractional) dhx: u to the screen right, d towards the viewer."""
    x0, y = G.hex_xy(0, 1)
    return sx.Frame((x0 + B * dhx / 2.0, y, 0.0), rot)


def wire():
    return mat.flat((0.03, 0.03, 0.03), roughness=0.6)


def guys(f, z, reach=1.15, d=0.22, radius=0.012, u=0.0):
    """Two guy wires from (u, z) down to the roof's edge on both sides."""
    for side in (-1.0, 1.0):
        geo.pipe([f.at(u, 0.03, z), f.at(u + side * reach, d, ROOF + 0.02)], radius, wire(), name="guy")


def strap(f, u0, u1, z, d=0.0, radius=0.016, material=None):
    return geo.pipe([f.at(u0, d, z), f.at(u1, d, z + 0.02)], radius, material or mat.steel(rust=0.8, seed=2), name="strap")


# ------------------------------------------------------------------------------- tanks
@piece("rf_tank_bowser", title="Bowser Tank",
       desc="The barrel of a road tanker, hoisted on to a trestle of scaffold tube. Somebody painted a level mark on it, "
            "and later a second one, lower.",
       footprint=[(-2, 1), (0, 1), (2, 1)], anchors=[(2, 1)], shadow="none", convert=CONV)
def rf_tank_bowser(ctx):
    f = frame_at(0)
    steel = mat.steel(rust=0.75, seed=3)
    top = 3.3
    for u in (-B, B):
        sx.lattice_post(f, u, top, width=0.42, material=steel, bay=0.55, chord=0.045)
    for a, b in ((-B, B), (B, -B)):                                         # X bracing, high enough to show
        geo.pipe([f.at(a, 0.0, ROOF - 0.25), f.at(b, 0.0, top - 0.05)], 0.026, steel, name="brace")
    for d in (-0.32, 0.32):
        geo.ibeam(3.5, f.at(-1.75, d, top), f.rot, steel, height=0.16, width=0.12)
    wood = mat.planks(colour=(0.22, 0.13, 0.06), width=0.2, axis="X", grey=0.5, seed=4)
    radius, length = 0.66, 3.3
    cz = top + 0.16 + 0.12 + radius
    for u in (-1.05, 1.05):                                                # timber saddles, chocked
        geo.box((0.26, 1.0, 0.28), f.at(u, 0.0, top + 0.16), f.rot, wood, bevel=0.01, name="saddle")
    paint = bx.bomb_paint((0.19, 0.15, 0.065), rust=0.62, seed=4, bleach=0.45,
                          bands=[(-0.25, 0.3, (0.40, 0.38, 0.32)), (1.05, 1.2, (0.30, 0.045, 0.03))])
    profile = [(0.0, -length / 2 - 0.13), (radius * 0.55, -length / 2 - 0.09), (radius * 0.92, -length / 2), (radius, -length / 2 + 0.1)]
    for z in (-0.95, 0.0, 0.95):
        profile += [(radius, z - 0.04), (radius + 0.025, z - 0.025), (radius + 0.025, z + 0.025), (radius, z + 0.04)]
    profile += [(radius, length / 2 - 0.1), (radius * 0.92, length / 2), (radius * 0.55, length / 2 + 0.09), (0.0, length / 2 + 0.13)]
    geo.lathe(profile, f.at(0.0, 0.0, cz), paint, 28, f.rot, 0.0, 90.0, name="tank")
    # filler dome, a patch plate welded over a split, a number by hand
    geo.cylinder(0.24, 0.16, f.at(-0.55, 0.0, cz + radius - 0.04), steel, 14, name="filler")
    geo.cylinder(0.27, 0.04, f.at(-0.55, 0.0, cz + radius + 0.12), mat.painted_metal((0.30, 0.045, 0.03), flaking=0.5, seed=3), 14,
                 name="filler_lid")
    geo.box((0.7, 0.03, 0.5), f.at(0.95, radius - 0.005, cz - 0.2), f.rot, mat.steel(rust=0.9, seed=8), bevel=0.01, name="patch",
            tilt=8.0)
    sx.bolts(f, [(0.66 + 0.2 * i, cz - 0.15 + 0.38 * j) for i in range(4) for j in range(2)], d=radius + 0.02, radius=0.028)
    sx.letters("2", f, -0.95, cz - 0.3, 0.6, font="impact", material=mat.sign_paint((0.045, 0.045, 0.05), wear=0.45, seed=2), d=radius + 0.012,
               depth=0.02)
    rx.runs(f, [(-1.35, cz - 0.05, 0.5), (-0.2, cz - 0.1, 0.45), (0.2, cz - 0.05, 0.5), (1.15, cz, 0.55)], d=radius + 0.004, width=0.09)
    # the draw-off: a pipe under the belly, a valve, down over the roof's edge; an overflow dribbling rust
    grey = mat.painted_metal((0.13, 0.14, 0.14), flaking=0.55, seed=5)
    geo.pipe([f.at(0.35, 0.0, cz - radius + 0.03), f.at(0.35, 0.0, top - 0.1), f.at(0.35, 0.3, top - 0.25), f.at(0.35, 0.36, ROOF - 0.3)],
             0.055, grey, name="draw_off")
    sx.disc(0.13, f.at(0.35, 0.37, top - 0.32), f.rot, sx.enamel((0.42, 0.05, 0.03), chips=0.3), thickness=0.03, hole=0.04,
            name="valve_wheel")
    geo.box((0.16, 0.012, 0.75), f.at(1.45, radius * 0.72, cz - 0.95), f.rot, mat.flat((0.07, 0.03, 0.015)), bevel=0.0,
            name="rust_run", tilt=-22.0)
    gx.ladder(f.at(-B - 0.05, 0.3, 0.0), f.at(-B - 0.05, 0.28, cz + 0.2), width=0.4, material=steel)
    guys(f, top + 0.1, reach=0.9, u=-B)
    guys(f, top + 0.1, reach=0.9, u=B)


@piece("rf_rain_catcher", title="Rain Catcher",
       desc="An upside-down umbrella of tarpaulin, no two panels alike, draining into a plate tank. It has rained twice "
            "since it was built.",
       footprint=[(0, 1), (2, 1)], anchors=[(2, 1)], shadow="none", convert=CONV)
def rf_rain_catcher(ctx):
    f = frame_at(1)                                                         # centred between the two feet
    steel = mat.steel(rust=0.7, seed=5)
    half = B / 2.0
    deck = 3.0
    for u in (-half, half):
        sx.scaffold_pole(f.at(u, 0.0, 0.0), deck, radius=0.05, material=steel)
        geo.pipe([f.at(u, 0.0, 1.2), f.at(-u, 0.0, deck - 0.1)], 0.025, steel, name="brace")
    wood = mat.planks(colour=(0.24, 0.14, 0.06), width=0.2, axis="X", grey=0.45, seed=6)
    geo.box((2.1, 1.25, 0.07), f.at(0.0, 0.0, deck), f.rot, wood, bevel=0.006, name="platform")
    # the tank: plates of three colours on an angle-iron cage, a patch, a tap
    side = 1.12
    for k, (u0, u1, colour) in enumerate(((-side / 2, -0.05, rx.TEAL), (-0.05, side / 2, (0.22, 0.20, 0.13)))):
        geo.box((u1 - u0 - 0.02, side * 0.86, 1.05), f.at((u0 + u1) / 2.0, 0.0, deck + 0.07), f.rot,
                mat.painted_metal(colour, flaking=0.5, seed=k + 2), bevel=0.01, name="tank_plate")
    for u in (-side / 2, 0.0, side / 2):
        geo.box((0.06, side * 0.9, 1.1), f.at(u, 0.0, deck + 0.06), f.rot, steel, bevel=0.004, name="cage")
    for z in (deck + 0.08, deck + 0.6, deck + 1.1):
        geo.box((side + 0.06, side * 0.9, 0.05), f.at(0.0, 0.0, z), f.rot, steel, bevel=0.004, name="cage")
    geo.box((0.4, 0.03, 0.32), f.at(0.27, side * 0.45, deck + 0.2), f.rot, mat.steel(rust=0.95, seed=9), bevel=0.006, name="patch")
    geo.pipe([f.at(-0.3, side * 0.45, deck + 0.22), f.at(-0.3, side * 0.45 + 0.2, deck + 0.22), f.at(-0.3, side * 0.45 + 0.2, deck + 0.08)],
             0.03, mat.steel(rust=0.4, seed=2), name="tap")
    # the funnel: six panels from a hoop down to a throat over the tank
    cz0, cz1 = deck + 1.35, 5.55
    rim, throat, count = 1.42, 0.16, 6
    colours = ((0.21, 0.18, 0.10), (0.085, 0.12, 0.145), (0.12, 0.13, 0.065), (0.24, 0.10, 0.05), (0.19, 0.17, 0.12), (0.10, 0.11, 0.10))
    ring_top, ring_low = [], []
    for k in range(count):
        a = math.radians(30.0 + 360.0 * k / count)
        ring_top.append(f.at(rim * math.cos(a), rim * 0.62 * math.sin(a), cz1 + 0.08 * math.sin(a * 2.0)))
        ring_low.append(f.at(throat * math.cos(a), throat * math.sin(a), cz0))
    for k in range(count):
        j = (k + 1) % count
        sx.sag_sheet([ring_top[k], ring_top[j], ring_low[j], ring_low[k]], mat.tarp(colours[k], seed=k + 1), sag=0.05, ripple=0.03,
                     seed=k, rows=6, columns=5)
        geo.pipe([ring_top[k], ring_low[k]], 0.022, steel, name="rib")
        geo.pipe([ring_top[k], ring_top[j]], 0.026, steel, name="hoop")
    geo.pipe([f.at(0.0, 0.0, cz0 + 0.02), f.at(0.0, 0.0, deck + 1.1)], 0.07, mat.steel(rust=0.5, seed=4), name="down_pipe")
    for u in (-half, half):                                                 # the hoop's two props, standing on the platform
        geo.pipe([f.at(u * 1.3, 0.0, deck + 0.05), f.at(u * 2.0, 0.0, cz1 - 0.05)], 0.035, steel, name="prop")
    guys(f, cz1 - 0.1, reach=1.2, u=-1.2, d=0.3)
    guys(f, cz1 - 0.1, reach=1.2, u=1.2, d=0.3)


# ---------------------------------------------------------------------------- chimneys
@piece("rf_chimney_drums", title="Drum Chimney",
       desc="Five oil drums with their ends cut out, welded into a chimney and stayed with wire. The top one still says what was in it.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", convert=CONV)
def rf_chimney_drums(ctx):
    f = frame_at(0)
    r = ctx.rng
    steel = mat.steel(rust=0.8, seed=3)
    colours = ((0.10, 0.045, 0.02), (0.07, 0.11, 0.15), (0.11, 0.05, 0.022), (0.24, 0.05, 0.03), (0.20, 0.16, 0.05))
    z = 0.0
    for k, colour in enumerate(colours):
        lean_u = 0.02 * (k - 2) + r.uniform(-0.012, 0.012)
        geo.barrel(f.at(lean_u, 0.0, z), radius=0.30 - 0.006 * k, height=0.9,
                   material=mat.painted_metal(colour, flaking=0.55 + 0.08 * (k % 3), seed=k + 3), tilt=r.uniform(-1.5, 1.5), rot=f.rot)
        if k:
            geo.cylinder(0.315, 0.05, f.at(lean_u, 0.0, z - 0.025), steel, 16, name="weld_band")
        z += 0.88
    top = z
    geo.cylinder(0.3, 0.3, f.at(0.04, 0.0, top - 0.3), mat.flat((0.012, 0.012, 0.012)), 16, name="soot")
    sx.cone(0.5, 0.26, f.at(0.04, 0.0, top + 0.16), steel, name="hat")
    for a in (20.0, 140.0, 260.0):
        ca, sa = math.cos(math.radians(a)) * 0.28, math.sin(math.radians(a)) * 0.28
        p = f.at(0.04, 0.0, 0.0)
        geo.pipe([(p[0] + ca, p[1] + sa, top - 0.03), (p[0] + ca * 1.6, p[1] + sa * 1.6, top + 0.18)], 0.016, steel, name="stay")
    sx.stencil("OIL", f, 0.04, top - 0.62, 0.26, colour=(0.62, 0.58, 0.45), font="din", d=0.285, wear=0.5, seed=4)
    sx.scaffold_pole(f.at(-0.42, 0.05, 0.0), 4.0, radius=0.04, material=steel)
    for zz in (2.95, 3.75):
        strap(f, -0.46, 0.34, zz, d=0.3)
    guys(f, top - 0.2, reach=1.15)


@piece("rf_chimney_box", title="Tin Flue",
       desc="A square flue riveted up from sheet, with a cowl that is supposed to turn with the wind. A thinner pipe keeps it company.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", convert=CONV)
def rf_chimney_box(ctx):
    f = frame_at(0)
    steel = mat.steel(rust=0.75, seed=6)
    tin_a = mat.painted_metal((0.17, 0.18, 0.17), flaking=0.5, seed=4)
    tin_b = mat.painted_metal((0.10, 0.13, 0.15), flaking=0.6, seed=7)
    side, top = 0.56, 4.25
    z = 0.0
    for k, hgt in enumerate((1.45, 1.4, 1.4)):
        geo.box((side - 0.02 * k, side - 0.02 * k, hgt), f.at(0.01 * k, 0.0, z), f.rot + 1.5 * (k - 1), tin_b if k == 1 else tin_a,
                bevel=0.012, name="flue")
        z += hgt
        geo.box((side + 0.08, side + 0.08, 0.07), f.at(0.0, 0.0, z - 0.035), f.rot, steel, bevel=0.006, name="flange")
    sx.bolts(f, [(-0.2 + 0.2 * i, zz) for i in range(3) for zz in (3.05, 3.9)], d=side / 2 + 0.01, radius=0.028)
    geo.box((0.36, 0.02, 0.5), f.at(0.05, side / 2 + 0.005, 3.25), f.rot, mat.steel(rust=0.95, seed=3), bevel=0.004, name="patch", roll=5.0)
    rx.runs(f, [(-0.17, 4.2, 0.75), (0.2, 4.2, 0.45), (-0.05, 2.82, 0.2), (0.12, 3.0, 0.55), (-0.2, 2.82, 0.16)], d=side / 2 + 0.012, width=0.07)
    geo.box((side + 0.01, side + 0.01, 0.3), f.at(0.0, 0.0, 3.62), f.rot, mat.painted_metal((0.22, 0.07, 0.04), flaking=0.6, seed=12), bevel=0.01,
            name="old_paint_band")
    # the cowl: a short fat drum lying across the top, open at the lee end, a vane on its back
    cz = top + 0.42
    geo.lathe([(0.0, -0.5), (0.33, -0.5), (0.36, -0.2), (0.36, 0.45), (0.3, 0.45), (0.3, -0.42), (0.0, -0.42)], f.at(0.0, 0.0, cz),
              mat.painted_metal((0.20, 0.10, 0.04), flaking=0.6, seed=9), 16, f.rot - 20.0, 0.0, 90.0, name="cowl")
    geo.cylinder(0.2, 0.2, f.at(0.0, 0.0, top), steel, 12, name="cowl_neck")
    sx.plate([(0.0, 0.0), (0.75, 0.32), (0.75, -0.3)], f.at(-0.5, 0.0, cz + 0.0), f.rot + 160.0, tin_a, thickness=0.02, name="vane")
    geo.box((0.3, 0.012, 0.4), f.at(0.0, side / 2 + 0.006, top - 0.45), f.rot, mat.flat((0.012, 0.012, 0.012)), bevel=0.0, name="soot")
    # the thin one: a stove pipe on stand-off brackets, an elbow, a cap
    u = 0.5
    geo.pipe([f.at(u, 0.05, 0.0), f.at(u, 0.05, 3.7), f.at(u + 0.22, 0.05, 3.95), f.at(u + 0.22, 0.05, 4.35)], 0.075,
             mat.corrugated(rust=0.5, seed=7), name="stove_pipe")
    sx.cone(0.17, 0.12, f.at(u + 0.22, 0.05, 4.4), steel, name="cap")
    for zz in (2.9, 3.55):
        strap(f, 0.2, u + 0.05, zz, d=0.1, radius=0.02)
    guys(f, top - 0.1, reach=1.05)


@piece("rf_chimney_stack", title="Boiler Stack",
       desc="A tapering boiler stack in riveted rings, a spark cage on top and a ladder nobody climbs twice.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", convert=CONV)
def rf_chimney_stack(ctx):
    f = frame_at(0)
    steel = mat.steel(rust=0.7, seed=4)
    black = mat.painted_metal((0.035, 0.035, 0.04), flaking=0.55, seed=5)
    oxide = mat.painted_metal((0.20, 0.06, 0.035), flaking=0.5, seed=6)
    top = 5.0
    profile = [(0.36, 0.0)]
    rings = 6
    for k in range(1, rings + 1):
        z = top * k / rings
        r0 = 0.36 - 0.13 * (k - 1) / rings
        r1 = 0.36 - 0.13 * k / rings
        profile += [(r0, z - 0.05), (r0 + 0.03, z - 0.04), (r0 + 0.03, z), (r1, z + 0.001)]
    geo.lathe(profile, f.at(0.0, 0.0, 0.0), black, 18, name="stack")
    geo.lathe([(0.305, 0.0), (0.285, 0.82)], f.at(0.0, 0.0, 3.36), oxide, 18, name="painted_ring")       # one ring is another colour
    geo.box((0.34, 0.02, 0.46), f.at(-0.03, 0.31, 2.95), f.rot, mat.steel(rust=0.95, seed=8), bevel=0.004, name="patch", roll=-6.0)
    # spark arrestor: a cage of hoops on the lip, a soot-black throat
    cz = top + 0.36
    cage = mat.steel(rust=0.5, seed=9)
    geo.cylinder(0.24, 0.1, f.at(0.0, 0.0, top), mat.flat((0.012, 0.012, 0.012)), 14, name="throat")
    for a in (0.0, 45.0, 90.0, 135.0):
        g = sx.Frame(f.at(0.0, 0.0, 0.0), f.rot + a)
        sx.ring((0.0, cz), 0.34, 0.4, g, cage, tube=0.02, count=18)
    for zz in (cz - 0.2, cz + 0.2):
        geo.pipe([f.at(0.3 * math.cos(t), 0.3 * math.sin(t), zz) for t in [2 * math.pi * i / 14 for i in range(15)]], 0.016, cage, name="hoop")
    sx.cone(0.2, 0.14, f.at(0.0, 0.0, cz + 0.4), cage, name="finial")
    # the ladder, with two safety hoops, and a collar the guys hang from
    gx.ladder(f.at(0.48, 0.12, 0.0), f.at(0.38, 0.12, top - 0.2), width=0.36, material=steel)
    for zz in (3.3, 4.2):
        geo.pipe([f.at(0.25, 0.25, zz), f.at(0.45, 0.42, zz), f.at(0.65, 0.25, zz)], 0.016, steel, name="safety_hoop")
        geo.pipe([f.at(0.3, 0.05, zz), f.at(0.46, 0.1, zz)], 0.02, steel, name="stand_off")
    geo.cylinder(0.3, 0.07, f.at(0.0, 0.0, 4.3), steel, 14, name="collar")
    guys(f, 4.33, reach=1.25)


# -------------------------------------------------------------------------------- mast
@piece("rf_mast_aerials", title="Aerial Mast",
       desc="A lattice mast hung with fishbone aerials pointing at stations that stopped two hundred years ago, and a cross-arm "
            "of insulators that still carries the town's wire.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", convert={"exposure": 0.3, "contrast": 1.25})
def rf_mast_aerials(ctx):
    f = frame_at(0)
    steel = mat.steel(rust=0.65, seed=8)
    alu = mat.aluminium(panel=6.0, rivets=False, seed=3, tint=(0.46, 0.47, 0.48))
    top = 5.55
    sx.lattice_post(f, 0.0, top, width=0.32, chord=0.04, lacing=0.024, material=steel, bay=0.42)
    geo.pipe([f.at(0.0, 0.0, top - 0.3), f.at(0.0, 0.0, top + 0.42)], 0.03, steel, name="spike")
    # two fishbones at different heights, pointing different ways; a folded dipole between them
    for z, sign, count, length in ((5.2, 1.0, 7, 1.7), (4.25, -1.0, 5, 1.25)):
        geo.pipe([f.at(-0.12 * sign, 0.04, z), f.at(sign * length, 0.04, z + 0.05 * sign)], 0.03, alu, name="boom")
        for k in range(count):
            u = sign * (0.22 + (length - 0.3) * k / (count - 1))
            half = 0.44 - 0.035 * k
            geo.pipe([f.at(u, 0.04, z - half), f.at(u, 0.04, z + half)], 0.022, alu, name="element")
    geo.pipe([f.at(-0.5, 0.06, 4.72), f.at(0.5, 0.06, 4.72), f.at(0.5, 0.06, 4.82), f.at(-0.5, 0.06, 4.82), f.at(-0.5, 0.06, 4.72)], 0.02, alu,
             name="dipole")
    # the cross-arm: timber, four insulators, wires away to both sides
    wood = mat.planks(colour=(0.20, 0.12, 0.06), width=0.3, axis="X", grey=0.5, seed=5)
    arm_z = 3.55
    geo.box((1.9, 0.1, 0.12), f.at(0.0, 0.08, arm_z), f.rot, wood, bevel=0.008, name="cross_arm")
    geo.pipe([f.at(-0.6, 0.08, arm_z + 0.02), f.at(0.0, 0.06, arm_z - 0.5)], 0.02, steel, name="arm_brace")
    geo.pipe([f.at(0.6, 0.08, arm_z + 0.02), f.at(0.0, 0.06, arm_z - 0.5)], 0.02, steel, name="arm_brace")
    china = sx.enamel((0.50, 0.48, 0.40), chips=0.2, seed=2)
    for u in (-0.85, -0.45, 0.45, 0.85):
        geo.lathe([(0.03, 0.0), (0.075, 0.03), (0.05, 0.08), (0.075, 0.12), (0.03, 0.17)], f.at(u, 0.08, arm_z + 0.12), china, 10, name="insulator")
        geo.pipe([f.at(u, 0.08, arm_z + 0.2), f.at(u + (1.6 if u > 0 else -1.6), 0.3, ROOF + 0.25 + 0.2 * abs(u))], 0.012, wire(), name="line")
    geo.box((0.34, 0.22, 0.44), f.at(0.0, 0.17, 2.85), f.rot, mat.painted_metal((0.14, 0.15, 0.12), flaking=0.5, seed=4), bevel=0.01,
            name="junction_box")
    sx.cloth(f.moved(d=0.03), -0.5, 5.9, 0.75, 0.36, sx.fabric((0.36, 0.28, 0.08), seed=4), folds=1.5, depth=0.05, seed=3, taper=0.5)
    geo.pipe([f.at(-0.9, 0.03, 5.9), f.at(0.0, 0.03, 5.92)], 0.014, steel, name="pennant_yard")
    guys(f, 4.9, reach=1.35, d=0.25)


# --------------------------------------------------------------------------- wind pump
@piece("rf_windpump", title="Wind Pump",
       desc="A wind pump on a lattice tower, its wheel rimmed in what was once fire-engine red. It lifts a bucket of brown "
            "water an hour and never stops turning.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", frames=4, fps=8, convert={"exposure": 0.3, "contrast": 1.25})
def rf_windpump(ctx):
    f = frame_at(0)
    steel = mat.steel(rust=0.7, seed=5)
    hub_z = 4.45
    # tower: a wide lattice below, a narrow one above, a ring platform between
    sx.lattice_post(f, 0.0, 3.3, width=0.62, chord=0.045, lacing=0.026, material=steel, bay=0.6)
    sx.lattice_post(f, 0.0, hub_z - 3.2, width=0.36, chord=0.04, lacing=0.022, material=steel, bay=0.42, z0=3.2)
    geo.box((1.0, 0.5, 0.05), f.at(0.0, 0.0, 3.28), f.rot, mat.planks(colour=(0.22, 0.13, 0.06), width=0.2, axis="X", grey=0.5, seed=2),
            bevel=0.006, name="platform")
    geo.pipe([f.at(0.0, 0.1, hub_z - 0.1), f.at(0.0, 0.1, 0.3)], 0.016, mat.steel(rust=0.3, seed=2), name="pump_rod")
    # the head, turned a little away from the camera so that the tail shows
    head = sx.Frame(f.at(0.0, 0.0, 0.0), geo.SCREEN - 22.0)
    geo.box((0.34, 0.5, 0.3), f.at(0.0, 0.05, hub_z - 0.15), head.rot, mat.painted_metal((0.20, 0.06, 0.035), flaking=0.5, seed=4),
            bevel=0.02, name="gearbox")
    tail_end = head.at(0.2, -1.75, hub_z + 0.1)
    geo.pipe([head.at(0.0, -0.1, hub_z), tail_end], 0.03, steel, name="tail_boom")
    tail = sx.Frame(tail_end, head.rot + 90.0)
    sx.plate([(-0.1, -0.3), (0.85, -0.45), (0.85, 0.5), (-0.1, 0.32)], tail.at(0.0, 0.0, 0.0), tail.rot,
             sx.enamel((0.42, 0.40, 0.33), chips=0.5, seed=6), thickness=0.02, name="tail_vane")
    sx.plate([(0.25, -0.38), (0.5, -0.41), (0.5, 0.43), (0.25, 0.37)], tail.at(0.0, 0.012, 0.0), tail.rot,
             sx.enamel((0.36, 0.05, 0.035), chips=0.45, seed=7), thickness=0.012, name="tail_stripe")
    # the wheel, 0.35 m in front of the tower: a dark disc behind the blades keeps the outline the same in every frame
    w = head.moved(d=0.38)
    radius = 1.02
    sx.disc(radius - 0.03, w.at(0.0, -0.03, hub_z), w.rot, mat.flat((0.02, 0.018, 0.016), roughness=0.9), thickness=0.012, name="wheel_shade",
            segments=32)
    blades = 12
    turn = 360.0 / blades * ctx.frame / max(1, ctx.frames)
    # THE LOOP: four frames turn the wheel by ONE blade pitch (30 degrees), then it starts again. That only looks like
    # turning if every blade is the same: one odd-coloured blade would creep forward three steps and jump back.
    # So the blades are alike, and the colour sits where it does not turn: the rim, the hub cap, the tail.
    blade_tin = mat.painted_metal((0.24, 0.24, 0.22), flaking=0.8, seed=1)
    for k in range(blades):
        a = math.radians(turn + 360.0 * k / blades)
        ca, sa = math.cos(a), math.sin(a)
        pts = [(0.26, -0.035), (0.95, -0.19), (0.97, 0.12), (0.27, 0.05)]
        material = blade_tin
        sx.plate([(px * ca - pz * sa, px * sa + pz * ca) for px, pz in pts], w.at(0.0, 0.0, hub_z), w.rot, material, thickness=0.014,
                 name="blade")
    sx.ring((0.0, hub_z), radius, radius, w.moved(d=0.02), sx.enamel((0.40, 0.05, 0.035), chips=0.5, seed=5), tube=0.035, count=32)
    sx.ring((0.0, hub_z), 0.56, 0.56, w.moved(d=0.03), steel, tube=0.022, count=24)
    sx.disc(0.16, w.at(0.0, 0.02, hub_z), w.rot, mat.painted_metal((0.07, 0.12, 0.16), flaking=0.5, seed=6), thickness=0.08, dome=0.06,
            name="hub")
    guys(f, 3.35, reach=1.3, d=0.25)
