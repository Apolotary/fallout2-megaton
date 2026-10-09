# SPDX-License-Identifier: MIT
"""Megaton roofline clutter: flues, a water tank, an antenna mast, a patched wind-break, a fan.

WHY THESE STAND BEHIND THE BUILDING AND NOT ON IT
The visible paint order is floors, objects, then roof tiles, so a sprite
can never show in front of a roof. What CAN show is anything that rises over the roof's FAR
edge: it is painted first, the roof then covers its lower part, and the eye reads it as
standing on the back of the roof. All five pieces are built for that: legs or ducts up to
roof height (2.66 m, they are normally hidden), the part worth looking at above it.

WHERE (for a stock shack whose back wall is on row hy_lo, see mod/megaton/layout/kit.py)
  The roof's trim row ends 1.5 m behind the back wall. Put the piece's ORIGIN on row hy_lo - 3
  (an even row, 2.4 m behind the wall): its feet are on the piece's row 1 = hy_lo - 2, 0.1 m
  behind the roof edge, so the roof hides exactly the lowest 2.6 m. Any even hx inside the
  building's hx range works; the feet are listed in the manifest (footprint).
  Places that are free in today's plan (the table is placement.py, group "street"):
      saloon (back wall hy 61, origin row 58): sg_roof_vent (92, 58), sg_moriarty (96, 58), sg_roof_stack (110, 58)
      Craterside and Billy's (hy 63, row 60): sg_roof_antenna (76, 60), sg_roof_tank (122, 60)
      water plant (hy 85, row 82): sg_roof_vent (62, 82)
      sheriff's and the empty house (hy 113, row 110): sg_roof_patch (78, 110), sg_roof_stack (122, 110)
  When the player is inside the building its roof is hidden and the legs show behind the back
  wall: they are modelled for that, they are not cut off.
  They also work free-standing anywhere (the tank on its tower, the mast, the wind-break as a fence).

Each piece is one part, anchored on the highest hx of its back row (see sg_signs.py); the mast is
anchored on its own foot, so that no part of it is further than 224 px above its hex.
sg_roof_vent is animated (4 frames): the placer attaches the stock script "animfrvr".
sg_roof_antenna carries a beacon painted with the "alarm" palette range: it blinks red by itself.
"""
import math

from kit import piece, geo, mat, G
from kit import signs_extra as sx

ROOF = G.WALL_H                    # 2.66 m: where a stock roof is drawn


def hx(dhx, dhy=0):
    return G.hex_xy(dhx, dhy)


@piece("sg_roof_stack", title="Flue Pipes", desc="Three stove pipes wired together, each with a different hat.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", convert={"exposure": 0.25, "contrast": 1.25})
def sg_roof_stack(ctx):
    x, y = hx(0, 1)
    f = sx.Frame((x, y, 0.0), geo.U)
    steel = mat.steel(rust=0.8, seed=3)
    zinc = mat.corrugated(rust=0.35, seed=7)
    black = mat.painted_metal((0.03, 0.03, 0.035), flaking=0.5, seed=4)
    # the big one: riveted sections, a conical rain hat on three stays
    geo.lathe([(0.17, 0.0), (0.17, 1.3), (0.185, 1.3), (0.185, 1.36), (0.17, 1.36), (0.17, 2.7), (0.185, 2.7), (0.185, 2.76),
               (0.17, 2.76), (0.17, 4.05)], f.at(0.0, 0.0, 0.0), black, 14, name="flue_a")
    sx.cone(0.33, 0.2, f.at(0.0, 0.0, 4.2), steel, name="hat_a")
    for a in (0.0, 120.0, 240.0):
        ca, sa = math.cos(math.radians(a)) * 0.16, math.sin(math.radians(a)) * 0.16
        p = f.at(0.0, 0.0, 4.05)
        geo.pipe([(p[0] + ca, p[1] + sa, 4.02), (p[0] + ca * 1.8, p[1] + sa * 1.8, 4.2)], 0.012, steel, name="stay")
    # the thin one, taller, with an H cowl
    u = 0.42
    geo.pipe([f.at(u, 0.05, 0.0), f.at(u, 0.05, 4.45)], 0.085, zinc, name="flue_b")
    geo.pipe([f.at(u - 0.3, 0.05, 4.45), f.at(u + 0.3, 0.05, 4.45)], 0.075, zinc, name="cowl_bar")
    for du in (-0.3, 0.3):
        geo.pipe([f.at(u + du, 0.05, 4.2), f.at(u + du, 0.05, 4.72)], 0.085, zinc, name="cowl_leg")
    # the short one: an elbow with a spinning-vent ball
    u = -0.4
    geo.pipe([f.at(u, -0.03, 0.0), f.at(u, -0.03, 3.25), f.at(u - 0.12, 0.05, 3.45)], 0.11, steel, name="flue_c")
    ball = mat.aluminium(panel=0.12, rivets=False, seed=2, tint=(0.42, 0.43, 0.44))
    sx.sphere(0.22, f.at(u - 0.14, 0.07, 3.68), ball, name="turbine", squash=0.85)
    geo.cylinder(0.12, 0.08, f.at(u - 0.14, 0.07, 3.44), ball, 10, name="turbine_neck")
    # straps and wire holding the three together, a guy wire back to the roof
    for z in (3.0, 3.6):
        geo.pipe([f.at(-0.52, 0.1, z), f.at(0.52, 0.1, z + 0.03)], 0.016, steel, name="strap")
    wire = mat.flat((0.03, 0.03, 0.03), roughness=0.6)
    geo.pipe([f.at(0.0, 0.1, 3.95), f.at(0.95, 0.25, ROOF + 0.02)], 0.012, wire, name="guy")
    geo.pipe([f.at(0.0, 0.1, 3.95), f.at(-1.0, 0.25, ROOF + 0.02)], 0.012, wire, name="guy")
    # soot at the lips
    geo.lathe([(0.172, 0.0), (0.172, 0.22)], f.at(0.0, 0.0, 3.83), mat.flat((0.01, 0.01, 0.01)), 14, name="soot")


@piece("sg_roof_tank", title="Water Tank", desc="A water tank on a tower of angle iron, high enough to give the taps some pressure.",
       footprint=[(0, 0), (2, 0), (0, 1), (1, 1), (2, 1)], anchors=[(2, 0)], shadow="none",
       convert={"exposure": 0.2, "contrast": 1.2, "saturation": 1.1})
def sg_roof_tank(ctx):
    (x0, y0), (x1, _) = hx(0, 0), hx(2, 0)
    y1 = hx(0, 1)[1]
    steel = mat.steel(rust=0.8, seed=6)
    deck_z = ROOF + 0.12
    legs = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    for lx, ly in legs:
        geo.ibeam(deck_z, (lx, ly, 0.0), geo.U, steel, vertical=True, height=0.1, width=0.1)
        geo.box((0.26, 0.26, 0.08), (lx, ly, 0.0), 0.0, mat.concrete(seed=lx), bevel=0.01)
    for (ax, ay), (bx, by) in ((legs[2], legs[3]), (legs[0], legs[2]), (legs[1], legs[3])):      # X bracing on three sides
        for z0, z1 in ((0.3, 1.5), (1.5, 2.6)):
            geo.pipe([(ax, ay, z0), (bx, by, z1)], 0.02, steel, name="brace")
            geo.pipe([(bx, by, z0), (ax, ay, z1)], 0.02, steel, name="brace")
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    wood = mat.planks((0.22, 0.13, 0.06), width=0.2, axis="X", grey=0.5, seed=4)
    geo.box((x1 - x0 + 0.5, y1 - y0 + 0.45, 0.07), (cx, cy, deck_z), geo.U, wood, bevel=0.006, name="deck")
    # the tank: a riveted drum with a conical lid, hoops, a painted band and a level pipe
    r = 0.68
    shell = mat.painted_metal((0.09, 0.14, 0.12), flaking=0.5, seed=9)
    base = deck_z + 0.07
    profile = [(r * 0.97, 0.0), (r, 0.03)]
    for z in (0.35, 0.8, 1.25):
        profile += [(r, z - 0.03), (r + 0.022, z - 0.02), (r + 0.022, z + 0.02), (r, z + 0.03)]
    profile += [(r, 1.5), (r + 0.03, 1.52), (r + 0.03, 1.56), (0.12, 1.86), (0.12, 1.94), (0.0, 1.94)]
    geo.lathe(profile, (cx, cy, base), shell, 26, name="tank")
    geo.lathe([(r + 0.006, 0.0), (r + 0.006, 0.26)], (cx, cy, base + 0.47), sx.enamel((0.74, 0.70, 0.60), chips=0.55, seed=5), 26,
              name="band")
    f = sx.Frame((cx, cy, 0.0), geo.U)
    geo.pipe([f.at(-0.5, 0.52, base + 1.45), f.at(-0.5, 0.56, base - 0.1), f.at(-0.5, 0.5, 0.2)], 0.035, steel, name="down_pipe")
    sx.disc(0.11, f.at(-0.44, 0.6, base + 0.2), f.rot, sx.enamel((0.5, 0.05, 0.03), chips=0.3), thickness=0.03, hole=0.04, name="valve")
    for z in [base + 0.1 + 0.3 * k for k in range(5)]:                                           # ladder up the tank
        geo.pipe([f.at(0.25, 0.7, z), f.at(0.55, 0.62, z)], 0.016, steel, name="rung")
    geo.pipe([f.at(0.25, 0.72, 0.0), f.at(0.25, 0.7, base + 1.5)], 0.02, steel, name="ladder_rail")
    geo.pipe([f.at(0.55, 0.64, 0.0), f.at(0.55, 0.62, base + 1.5)], 0.02, steel, name="ladder_rail")
    for z in [0.4 + 0.33 * k for k in range(7)]:
        geo.pipe([f.at(0.25, 0.72, z), f.at(0.55, 0.64, z)], 0.016, steel, name="rung")
    sx.cloth(f, -0.2, base + 0.02, 0.5, 0.5, mat.tarp((0.30, 0.24, 0.12), seed=3), folds=1.5, depth=0.03, d=0.72, seed=4)


@piece("sg_roof_antenna", title="Radio Mast", desc="A mast of welded scrap with every antenna the town could find. A red lamp blinks on top.",
       footprint=[(-2, 1), (0, 1), (2, 1)], anchors=[(0, 1)], shadow="none",
       convert={"exposure": 0.3, "contrast": 1.25})
def sg_roof_antenna(ctx):
    x, y = hx(0, 1)
    f = sx.Frame((x, y, 0.0), geo.U)
    steel = mat.steel(rust=0.65, seed=8)
    top = 5.5
    sx.lattice_post(f, 0.0, top, width=0.3, chord=0.035, lacing=0.02, material=steel, bay=0.45)
    geo.pipe([f.at(0.0, 0.0, top - 0.3), f.at(0.0, 0.0, top + 0.28)], 0.03, steel, name="spike")
    geo.bulb(f.at(0.0, 0.0, top + 0.34), (1.0, 0.0, 0.0), 0.075, 2.0, fx="alarm")
    alu = mat.aluminium(panel=6.0, rivets=False, seed=3, tint=(0.44, 0.45, 0.46))
    # a yagi pointing along the row, with five elements across the view
    z = 5.05
    geo.pipe([f.at(-0.15, 0.0, z), f.at(1.45, 0.0, z)], 0.028, alu, name="yagi_boom")
    for k, u in enumerate((0.1, 0.42, 0.74, 1.06, 1.38)):
        half = 0.42 - 0.05 * k
        geo.pipe([f.at(u, -half, z), f.at(u, half, z)], 0.02, alu, name="yagi_element")
    # a dish at mid height, looking up to the left
    dish = geo.lathe([(0.0, 0.0), (0.2, 0.02), (0.4, 0.09), (0.52, 0.17), (0.5, 0.17), (0.38, 0.1), (0.2, 0.04), (0.0, 0.02)],
                     f.at(-0.25, 0.22, 4.1), mat.painted_metal((0.42, 0.42, 0.38), flaking=0.35, seed=5), 20, f.rot, 62.0, 28.0,
                     name="dish")
    geo.pipe([f.at(-0.25, 0.22, 4.1), f.at(-0.42, 0.62, 4.32)], 0.016, steel, name="feed_arm")
    sx.sphere(0.05, f.at(-0.42, 0.62, 4.32), steel, name="feed")
    geo.pipe([f.at(0.0, 0.05, 4.05), f.at(-0.22, 0.15, 4.1)], 0.03, steel, name="dish_mount")
    # a horn loudspeaker, a whip, a rag of a flag
    sx.cone(0.26, 0.42, f.at(0.34, 0.3, 3.45), mat.painted_metal((0.30, 0.28, 0.22), flaking=0.4, seed=7), tilt=100.0, rot=f.rot - 25.0,
            top=0.05, name="horn")
    geo.pipe([f.at(0.12, 0.05, 3.5), f.at(0.3, 0.12, 3.47)], 0.025, steel, name="horn_mount")
    geo.pipe([f.at(-0.14, 0.0, 4.6), f.at(-0.55, 0.0, 4.75), f.at(-0.62, 0.0, 5.85)], 0.014, steel, name="whip")
    sx.cloth(f.moved(d=0.02), 0.52, 4.62, 0.7, 0.42, sx.fabric((0.50, 0.08, 0.05), seed=3), folds=1.5, depth=0.05, seed=6, taper=0.25)
    geo.pipe([f.at(0.15, 0.02, 4.62), f.at(0.9, 0.02, 4.62)], 0.014, steel, name="flag_yard")
    # guy wires to two stakes along the row, cables down the mast
    wire = mat.flat((0.03, 0.03, 0.03), roughness=0.6)
    for dhx in (-2, 2):
        gx, gy = hx(dhx, 1)
        geo.pipe([f.at(0.0, 0.0, 4.9), (gx, gy, 0.12)], 0.013, wire, name="guy")
        geo.box((0.3, 0.3, 0.14), (gx, gy, 0.0), 20.0, mat.concrete(seed=dhx + 5), bevel=0.02, name="deadman")
    geo.cable(f.at(0.05, 0.08, 4.0), f.at(0.1, 0.08, 0.3), sag=0.0, radius=0.014, material=wire)
    geo.box((0.3, 0.2, 0.4), f.at(0.0, 0.14, 2.9), f.rot, mat.painted_metal((0.16, 0.17, 0.15), flaking=0.5, seed=4), bevel=0.01,
            name="junction_box")


@piece("sg_roof_patch", title="Patched Wind-break", desc="Sheet iron, a car door and a road sign, wired to scaffold tubes to keep the dust off the roof.",
       footprint=[(0, 1), (4, 1)], anchors=[(4, 1)], shadow="none",
       convert={"exposure": 0.25, "contrast": 1.25, "saturation": 1.15})
def sg_roof_patch(ctx):
    (x0, y), (x1, _) = hx(0, 1), hx(4, 1)
    f = sx.Frame((x1 + 0.15, y, 0.0), geo.U)               # u = 0 just left of the left tube
    span = x1 - x0 + 0.3
    steel = mat.steel(rust=0.7, seed=5)
    for u, h in ((0.15, 4.25), (span - 0.15, 4.05)):
        geo.pipe([f.at(u, 0.0, 0.0), f.at(u, 0.0, h)], 0.045, steel, name="tube")
        geo.cylinder(0.16, 0.1, f.at(u, 0.0, 0.0), mat.concrete(seed=u), 10, name="pad")
    for z in (ROOF + 0.05, 3.3, 3.95):
        geo.pipe([f.at(-0.1, 0.0, z), f.at(span + 0.1, 0.0, z + 0.03)], 0.03, steel, name="ledger")
    z0 = ROOF - 0.05
    # left to right: rusty corrugated, a car door, a green road sign, planks, painted corrugated
    geo.corrugated_panel(0.78, 1.5, f.at(-0.12, 0.05, z0), f.rot, mat.corrugated(rust=0.8, seed=11), roll=-2.0, name="sheet_a")
    door = mat.painted_metal((0.07, 0.17, 0.30), flaking=0.35, seed=6)
    geo.box((0.95, 0.06, 0.62), f.at(1.1, 0.07, z0 + 0.05), f.rot, door, bevel=0.03, roll=1.5, name="door_lower")
    for u in (0.67, 1.1, 1.53):
        geo.box((0.07, 0.05, 0.5), f.at(u, 0.07, z0 + 0.67), f.rot, door, bevel=0.01, roll=1.5 + (u - 1.1) * 14.0, name="door_pillar")
    geo.box((0.92, 0.05, 0.07), f.at(1.1, 0.07, z0 + 1.15), f.rot, door, bevel=0.01, roll=1.5, name="door_top")
    sx.disc(0.035, f.at(1.4, 0.11, z0 + 0.42), f.rot, mat.aluminium(rivets=False), thickness=0.03, name="door_handle")
    green = sx.enamel((0.03, 0.20, 0.10), chips=0.3, seed=4)
    geo.box((1.15, 0.03, 0.82), f.at(2.15, 0.09, z0 + 0.42), f.rot, green, bevel=0.02, roll=-4.0, name="road_sign")
    white = mat.sign_paint((0.75, 0.75, 0.7), wear=0.3, seed=2)
    for dz in (0.07, 0.72):
        geo.box((1.03, 0.012, 0.03), f.at(2.15 - (dz - 0.4) * 0.07, 0.11, z0 + 0.42 + dz), f.rot, white, bevel=0.0, roll=-4.0, name="border")
    sx.arrow(0.7, f.at(1.82, 0.115, z0 + 0.83), f.rot, white, shaft=0.1, head=0.26, thickness=0.012, spin=-4.0)
    sx.plank_panel(f, 1.62, 2.75, z0 - 0.02, z0 + 0.4, d=0.06, colours=((0.27, 0.15, 0.07), (0.20, 0.12, 0.06)), plank=0.2, ragged=0.1,
                   seed=5)
    geo.corrugated_panel(0.72, 1.32, f.at(2.62, 0.05, z0 - 0.03), f.rot, mat.corrugated(rust=0.45, seed=13, paint=(0.30, 0.10, 0.04)),
                         roll=3.0, name="sheet_b")
    sx.sag_sheet([f.at(0.55, 0.1, z0 + 1.42), f.at(1.5, 0.1, z0 + 1.5), f.at(1.55, 0.14, z0 + 1.1), f.at(0.6, 0.14, z0 + 1.02)],
                 mat.tarp((0.30, 0.24, 0.12), seed=6), sag=0.01, ripple=0.02, seed=3)
    geo.tire(f.at(span - 0.5, 0.12, z0 + 1.42), radius=0.3, lying=False, rot=f.rot, lean=4.0, seed=7)     # hung on the top ledger
    wire = mat.flat((0.03, 0.03, 0.03), roughness=0.6)
    geo.cable(f.at(0.15, 0.02, 4.2), f.at(span - 0.15, 0.02, 4.0), sag=0.25, radius=0.014, material=wire)
    sx.bulbs_on(geo.catenary(f.at(0.15, 0.02, 4.2), f.at(span - 0.15, 0.02, 4.0), 0.25, 5)[1:-1], [None, (1.0, 0.8, 0.45), "fire", None],
                radius=0.055, drop=0.07)


@piece("sg_roof_vent", title="Extractor Fan", desc="A fan the size of a cart wheel in a tin box, pulling the smoke out. It never stops.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", frames=4, fps=10,
       convert={"exposure": 0.25, "contrast": 1.25})
def sg_roof_vent(ctx):
    x, y = hx(0, 1)
    f = sx.Frame((x, y, 0.0), geo.U)
    zinc = mat.corrugated(rust=0.4, seed=9)
    steel = mat.steel(rust=0.7, seed=4)
    tin = mat.painted_metal((0.20, 0.21, 0.20), flaking=0.45, seed=8)
    # square duct rising from below, a fat elbow, the fan box facing the camera
    geo.box((0.6, 0.6, 3.2), f.at(0.0, -0.1, 0.0), f.rot, tin, bevel=0.012, name="riser")
    for z in (1.0, 2.0, 3.0):
        geo.box((0.66, 0.66, 0.06), f.at(0.0, -0.1, z), f.rot, steel, bevel=0.006, name="flange")
    cz = 3.72
    geo.box((1.28, 0.6, 1.28), f.at(0.0, 0.0, cz - 0.64), f.rot, tin, bevel=0.02, name="fan_box")
    geo.box((1.42, 0.7, 0.07), f.at(0.0, 0.02, cz + 0.64), f.rot + 2.0, zinc, bevel=0.006, name="rain_lid")
    # the opening: a dark throat, the blades, a guard of two hoops and a cross
    sx.disc(0.56, f.at(0.0, 0.302, cz), f.rot, mat.flat((0.012, 0.012, 0.014), roughness=0.8), thickness=0.006, name="throat")
    blade = mat.aluminium(panel=6.0, rivets=False, seed=2, tint=(0.40, 0.41, 0.42))
    angle = 90.0 * ctx.frame / max(1, ctx.frames)
    for k in range(4):
        a = math.radians(angle + 90.0 * k)
        ca, sa = math.cos(a), math.sin(a)
        pts = [(0.06, -0.05), (0.5, -0.17), (0.52, 0.1), (0.07, 0.06)]
        sx.plate([(px * ca - pz * sa, px * sa + pz * ca) for px, pz in pts], f.at(0.0, 0.325, cz), f.rot, blade, thickness=0.012,
                 name="blade")
    sx.disc(0.1, f.at(0.0, 0.33, cz), f.rot, steel, thickness=0.04, dome=0.04, name="hub")
    guard = mat.steel(rust=0.5, seed=6)
    g = f.moved(d=0.36)
    sx.ring((0.0, cz), 0.57, 0.57, g, guard, tube=0.022)
    sx.ring((0.0, cz), 0.3, 0.3, g, guard, tube=0.014)
    geo.pipe([g.at(-0.57, 0.0, cz), g.at(0.57, 0.0, cz)], 0.014, guard, name="guard_bar")
    geo.pipe([g.at(0.0, 0.0, cz - 0.57), g.at(0.0, 0.0, cz + 0.57)], 0.014, guard, name="guard_bar")
    # grease streaks under the opening, a cable, two stays to the roof
    geo.box((0.5, 0.01, 0.3), f.at(0.05, 0.305, cz - 0.64), f.rot, mat.flat((0.02, 0.018, 0.016), roughness=0.4), bevel=0.0, name="grease")
    wire = mat.flat((0.03, 0.03, 0.03), roughness=0.6)
    geo.pipe([f.at(0.6, 0.0, cz + 0.5), f.at(1.2, 0.2, ROOF)], 0.012, wire, name="stay")
    geo.pipe([f.at(-0.6, 0.0, cz + 0.5), f.at(-1.2, 0.2, ROOF)], 0.012, wire, name="stay")
    geo.cable(f.at(-0.3, 0.31, cz - 0.6), f.at(-0.34, 0.25, 0.4), sag=0.0, radius=0.014, material=wire)
