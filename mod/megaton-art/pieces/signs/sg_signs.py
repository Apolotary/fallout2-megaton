# SPDX-License-Identifier: MIT
"""Megaton shop signs: one piece per establishment, each ONE sprite part.

Every sign faces the way stock wall signs do (kit.geo.U: along a hex row, reading up to the
right) unless noted, stands on its own legs or post and so does not care which wall kit the
building behind it is made of. Lettering is never below 0.28 m cap height.

WHY ONE PART IS ENOUGH (and where it is anchored)
A sign that runs along a hex row is cut as a single sprite on its screen-left foot (the
highest hx of the row). The engine paints rows far to near and each row right to left, so
that hex is painted after everything behind the sign and before everything in front of it;
the only hexes that sort the other way are the ones beside its right end, where nothing
overlaps but a post. The other feet are footprint hexes without a picture: the placer puts an
invisible blocker there. Boards hang at 1.9 m or higher wherever people walk under them, so a
head never reaches them. (sg_moriarty is anchored on its screen-RIGHT leg instead: a row slopes
up to the right on screen, and from the left leg its top would be more than the 224 px above
its hex within which the engine repaints an object. With nothing but two lattice legs at ground
level either end sorts the same.)

NIGHT
Fixed colours are darkened by the engine at night. A sign stays readable in one of two ways,
both built in: `light=` makes the piece a lamp (its own hex is lit, so the whole sprite keeps
its daylight colours and the ground round its foot is lit white), and tubes / bulbs tagged
with an animated palette range ("fire" red neon, "slime" radium green) glow by themselves.

PLACEMENT
The table with hexes, reasons and the stock objects each sign replaces is placement.py (group
"street"), which writes placement.json. In short:
  sg_moriarty behind the saloon (origin (96, 58)): the board rises over the far edge of the
  saloon roof like a rooftop sign and the roof hides its legs. The others stand beside their
  doors. THE EAVE RULE decides how near: the engine paints roofs after all objects and a stock
  roof overhangs a front wall by 1.7 m, so a sign d metres in front of a front wall is cut off
  above 1.85 m + 0.48 d. That is why sg_craterside (2.7 m with its lamp) stands three rows out
  and sg_brass_lantern (3.75 m) five rows out. Left walls have no overhang.
  A building IN FRONT hides as much: the church's roof covers everything lower than 2.2 m in
  Craterside's yard (hx 70..84), so sg_craterside stands at the shop's right corner (64, 78).
"""
import math

from mathutils import Matrix

from kit import piece, geo, mat, G
from kit import signs_extra as sx

HEX = G.SQ_U_M / 2.0                 # 0.69 m: one hex along a row (even to even is two of these)

CREAM = (0.80, 0.70, 0.42)
BONE = (0.78, 0.76, 0.66)
SIGN_RED = (0.62, 0.05, 0.03)
SIGN_YELLOW = (0.85, 0.60, 0.06)
INK = (0.03, 0.03, 0.035)


def row_x(dhx):
    """World x of hex (dhx, 0)."""
    return G.hex_xy(dhx, 0)[0]


def turn(obj, degrees, drop=0.0):
    """Turn a glyph in the plane of its face and let it slip down: a letter hanging on one bolt."""
    obj.rotation_euler = (obj.rotation_euler.to_matrix() @ Matrix.Rotation(math.radians(degrees), 3, "Z")).to_euler()
    obj.location.z -= drop


# ------------------------------------------------------------------ MORIARTY'S SALOON
@piece("sg_moriarty", title="Moriarty's Saloon Sign",
       desc="MORIARTY'S SALOON, in letters taller than a man. Half the neon still works.",
       footprint=[(0, 0), (8, 0), (7, 0)], anchors=[(0, 0)], shadow="none", light=(6, 100), light_hex=(0, 0),
       convert={"saturation": 1.15})
def sg_moriarty(ctx):
    f = sx.Frame((row_x(8), 0.0, 0.0), geo.U)          # u = 0 at the screen-left leg, 5.54 at the right one
    span = row_x(8)
    steel = mat.steel(rust=0.75, seed=7)
    for u in (0.0, span):
        sx.lattice_post(f, u, 5.05, width=0.36, material=steel)
        geo.pipe([f.at(u, 0.0, 1.95), f.at(u + (0.95 if u == 0.0 else -0.95), 0.0, 2.55)], 0.03, steel)      # knee brace
    for z in (2.6, 3.75, 4.95):                         # rails the sheets are bolted to
        geo.pipe([f.at(-0.3, 0.05, z), f.at(span + 0.3, 0.05, z)], 0.035, steel)
    u0, u1, z0, z1, face = -0.32, span + 0.32, 2.5, 5.0, 0.12
    sx.sheet_panel(f, u0, u1, z0, z1, d=face, colour=(0.022, 0.045, 0.055), panels=6, flaking=0.34, seed=3,
                   patch=(4, (0.13, 0.055, 0.025)))
    step = (u1 - u0) / 6.0
    sx.bolts(f, [(u0 + step * k + side * 0.06, z) for k in range(1, 6) for side in (-1, 1) for z in (z0 + 0.12, z0 + 1.25, z1 - 0.12)],
             d=face + 0.012, radius=0.028, material=mat.flat((0.20, 0.12, 0.07), roughness=0.8))
    sx.frame_rim(f, u0, u1, z0, z1, d=face, width=0.07, depth=0.09, material=steel)

    # MORIARTY'S: sheet-iron letters, cream enamel. The T hangs on one bolt.
    cream = sx.enamel(CREAM, chips=0.35, seed=2, glow=0.25)

    def crooked(index, char, obj):
        if index == 6:
            turn(obj, -7.0, 0.06)
    sx.letters("MORIARTY'S", f, (u0 + u1) / 2.0, 3.98, 0.80, "impact", cream, d=face + 0.05, depth=0.06, gap=0.07,
               each=crooked)

    # SALOON: red neon. The second O is dead.
    def neon(index, char):
        return sx.dead_tube() if index == 4 else mat.emitter((1.0, 0.16, 0.03), 2.2)

    def tag(index, char, obj):
        if index != 4:
            geo.set_fx(obj, "fire")
    sx.letters("SALOON", f, 3.55, 2.80, 0.66, "black", neon, d=face + 0.05, depth=0.05, gap=0.10, each=tag)
    # neon underline and a neon arrow pointing down at the bar; its lowest chevron is dead
    geo.neon_tube([f.at(1.85, face + 0.04, 3.72), f.at(u1 - 0.25, face + 0.04, 3.72)], (1.0, 0.45, 0.05), 0.03, 2.0, fx="fire")
    for k, z in enumerate((3.45, 3.12, 2.79)):
        points = [f.at(0.25, face + 0.04, z + 0.2), f.at(0.72, face + 0.04, z - 0.08), f.at(1.19, face + 0.04, z + 0.2)]
        if k == 2:
            geo.pipe(points, 0.03, sx.dead_tube())
        else:
            geo.neon_tube(points, (1.0, 0.45, 0.05), 0.032, 2.0, fx="fire")

    # marquee bulbs along the top rim, a third of them dead
    count = 15
    tops = [f.at(u0 + 0.12 + (u1 - u0 - 0.24) * i / (count - 1), face + 0.07, z1 + 0.16) for i in range(count)]
    warm = (1.0, 0.78, 0.42)
    sx.bulbs_on(tops, [warm, warm, None, warm, "fire", warm, None, warm, warm, warm, None, "fire", warm, None, warm],
                radius=0.055, drop=0.0)
    for u in (1.25, 4.3):
        sx.gooseneck(f, u, z1, reach=0.55, rise=0.42, d0=face)
    # a cable sagging from the lower right corner down the leg, and a rag of old poster
    geo.cable(f.at(u1 - 0.1, face, z0), f.at(span, 0.05, 1.3), sag=0.35, radius=0.02)
    sx.cloth(f, 5.25, z0 + 0.02, 0.5, 0.45, sx.fabric((0.45, 0.40, 0.30), seed=3), folds=1.5, depth=0.03, d=face + 0.03, seed=4)


# ------------------------------------------------------------------ CRATERSIDE SUPPLY
@piece("sg_craterside", title="Craterside Supply Sign",
       desc="CRATERSIDE SUPPLY, brushed on old boards. Somebody has nailed half a scrapyard round it.",
       footprint=[(0, 0), (2, 0), (4, 0)], anchors=[(4, 0)], shadow="baked", material="wood",
       light=(3, 85), light_hex=(4, 0))
def sg_craterside(ctx):
    f = sx.Frame((row_x(4) + 0.08, 0.0, 0.0), geo.U)
    width = row_x(4) + 0.16
    wood = mat.planks((0.20, 0.11, 0.05), width=2.0, axis="Z", grey=0.4, seed=4)
    for u, h, lean in ((0.12, 2.75, 1.5), (width - 0.12, 2.45, -2.0)):                 # two scrap posts
        geo.box((0.12, 0.12, h), f.at(u, -0.07, 0.0), f.rot, wood, bevel=0.01, roll=lean, name="post")
        geo.box((0.1, 0.1, 1.5), f.at(u, -0.55, 0.0), f.rot, wood, bevel=0.01, tilt=-22.0, name="prop")   # prop behind
    z0, z1 = 0.72, 2.22
    sx.plank_panel(f, -0.05, width + 0.05, z0, z1, d=0.03, paint=(0.07, 0.20, 0.21), wear=0.42, plank=0.25, ragged=0.09,
                   seed=6, lean=1.6)
    paint = mat.sign_paint(BONE, wear=0.25, seed=3, glow=0.2)
    yellow = mat.sign_paint(SIGN_YELLOW, wear=0.2, seed=5, glow=0.2)
    sx.letters("CRATERSIDE", f, width / 2.0 + 0.05, 1.66, 0.36, "marker", paint, d=0.04, depth=0.012, gap=0.09,
               jitter=0.02, seed=2, bevel=0.0)
    sx.letters("SUPPLY", f, width / 2.0 + 0.12, 0.92, 0.52, "marker", yellow, d=0.04, depth=0.012, gap=0.12,
               jitter=0.025, seed=3, bevel=0.0)
    # junk nailed round it
    alu = mat.aluminium(panel=5.0, rivets=False, seed=2)
    sx.disc(0.24, f.at(0.02, 0.05, 2.12), f.rot, alu, thickness=0.03, dome=0.07, name="hubcap")
    sx.disc(0.2, f.at(width - 0.05, 0.05, 0.86), f.rot, mat.steel(rust=0.9, seed=3), thickness=0.04, hole=0.07, name="gear")
    diamond = [(0.0, -0.33), (0.33, 0.0), (0.0, 0.33), (-0.33, 0.0)]
    sx.plate(diamond, f.at(width - 0.22, 0.045, 2.32), f.rot, sx.enamel((0.80, 0.52, 0.03), chips=0.5, seed=4), 0.02, roll=8.0)
    sx.plate([(-0.2, -0.1), (0.2, -0.1), (0.2, 0.1), (-0.2, 0.1)], f.at(0.42, 0.05, 0.62), f.rot,
             sx.enamel((0.72, 0.70, 0.62), chips=0.5, seed=7), 0.015, roll=-6.0, name="licence")
    # (the arrow points screen-LEFT: the sign stands to the right of the shop's door)
    sx.arrow(0.75, f.at(2.45, 0.05, 0.56), f.rot, sx.enamel(SIGN_RED, chips=0.4, seed=8), shaft=0.12, head=0.3, spin=180.0)
    geo.tire(f.at(0.1, 0.22, 0.0), radius=0.37, lying=False, rot=f.rot, lean=-14.0, seed=3)     # tyre against the post
    geo.tire(f.at(0.3, 0.42, 0.0), radius=0.33, seed=4)
    sx.gooseneck(f, width * 0.55, z1 + 0.02, reach=0.5, rise=0.38, d0=0.0)
    geo.box((0.34, 0.26, 0.3), f.at(width - 0.35, 0.3, 0.0), f.rot + 20.0, mat.painted_metal((0.13, 0.17, 0.08), flaking=0.5, seed=5),
            bevel=0.02, name="ammo_box")


# ------------------------------------------------------------------ THE BRASS LANTERN
@piece("sg_brass_lantern", title="The Brass Lantern Sign",
       desc="THE BRASS LANTERN. The lantern is real brass, the size of a child, and somebody keeps it burning.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", material="wood", light=(4, 100),
       convert={"saturation": 1.15, "halo_levels": 3})
def sg_brass_lantern(ctx):
    f = sx.Frame((0.0, 0.0, 0.0), geo.U)
    wood = mat.planks((0.22, 0.12, 0.055), width=2.0, axis="Z", grey=0.35, seed=8)
    iron = mat.steel(rust=0.5, seed=6)
    geo.box((0.16, 0.16, 3.75), f.at(0.0, 0.0, 0.0), f.rot, wood, bevel=0.012, name="post")
    geo.box((0.42, 0.42, 0.22), f.at(0.0, 0.0, 0.0), f.rot + 12.0, mat.concrete(seed=6), bevel=0.02, name="footing")
    arm_z, reach = 3.3, 2.55
    geo.box((reach, 0.08, 0.1), f.at(reach / 2.0 - 0.05, 0.0, arm_z), f.rot, wood, bevel=0.008, name="arm")
    geo.pipe([f.at(0.0, 0.0, 3.72), f.at(reach - 0.15, 0.0, arm_z + 0.1)], 0.02, iron)                    # tie rod
    geo.pipe([f.at(0.0, 0.0, 2.6), f.at(0.7, 0.0, arm_z)], 0.03, iron)                                    # strut
    # the board: three planks on two chains
    b0, b1, top = 0.22, 1.9, 3.02
    for u in (b0 + 0.2, b1 - 0.2):
        geo.pipe([f.at(u, 0.0, arm_z), f.at(u, 0.0, top - 0.02)], 0.016, iron, name="chain")
    sx.plank_panel(f, b0, b1, top - 1.12, top, d=0.03, paint=(0.20, 0.045, 0.03), wear=0.3, plank=0.38, ragged=0.03, seed=9)
    sx.frame_rim(f, b0, b1, top - 1.12, top, d=0.03, width=0.04, depth=0.06, material=iron)
    cream = mat.sign_paint(BONE, wear=0.2, seed=2, glow=0.25)
    gold = mat.sign_paint((0.88, 0.60, 0.10), wear=0.15, seed=4, glow=0.3)
    mid = (b0 + b1) / 2.0
    sx.letters("THE", f, mid, top - 0.27, 0.19, "impact", cream, d=0.04, depth=0.012, gap=0.14, bevel=0.0)
    sx.letters("BRASS", f, mid, top - 0.67, 0.34, "impact", gold, d=0.04, depth=0.014, gap=0.11, bevel=0.0)
    sx.letters("LANTERN", f, mid, top - 1.05, 0.30, "impact", cream, d=0.04, depth=0.012, gap=0.10, bevel=0.0)
    # the lantern itself, at the end of the arm
    hook = f.at(reach - 0.28, 0.0, arm_z - 0.02)
    sx.lantern(hook, size=1.55, strength=3.5)
    geo.halo((hook[0], hook[1], 0.0), radius=1.9, strength=0.8)


# ------------------------------------------------------------------ MEGATON CLINIC
@piece("sg_clinic", title="Megaton Clinic Sign",
       desc="MEGATON CLINIC. A white cross on green boards; the paint is newer than the wood.",
       footprint=[(0, 0), (2, 0)], anchors=[(2, 0)], shadow="baked", material="wood", light=(3, 90), light_hex=(2, 0),
       convert={"saturation": 1.05, "exposure": -0.3, "contrast": 1.3})
def sg_clinic(ctx):
    f = sx.Frame((row_x(2) + 0.02, 0.0, 0.0), geo.U)
    width = row_x(2) + 0.04                                # between the posts; the boards overhang by `over`
    over = 0.32
    a, b = -over, width + over
    mid = width / 2.0
    wood = mat.planks((0.22, 0.13, 0.06), width=2.0, axis="Z", grey=0.45, seed=3)
    for u, h in ((0.03, 3.42), (width - 0.03, 3.3)):
        geo.box((0.11, 0.11, h), f.at(u, -0.06, 0.0), f.rot, wood, bevel=0.01, name="post")
        geo.box((0.3, 0.3, 0.16), f.at(u, -0.06, 0.0), f.rot, mat.concrete(seed=u), bevel=0.02, name="pad")
    white = (0.66, 0.65, 0.58)
    sx.plank_panel(f, a - 0.04, b + 0.04, 0.95, 1.52, d=0.03, paint=white, wear=0.28, plank=0.28, ragged=0.05, seed=3)
    sx.plank_panel(f, a, b, 1.56, 2.94, d=0.03, paint=(0.035, 0.25, 0.10), wear=0.2, plank=0.2, ragged=0.035, seed=5, vertical=True)
    sx.plank_panel(f, a - 0.06, b + 0.02, 2.98, 3.38, d=0.03, paint=white, wear=0.3, plank=0.4, ragged=0.05, seed=7)
    cross_white = sx.enamel((0.90, 0.88, 0.80), chips=0.15, seed=3, glow=0.2)
    sx.cross(1.16, f.at(mid, 0.045, 2.25), f.rot, cross_white, arm=0.34, thickness=0.02)
    ink = mat.sign_paint((0.04, 0.05, 0.09), wear=0.15, seed=6)
    sx.letters("CLINIC", f, mid, 1.05, 0.38, "impact", ink, d=0.04, depth=0.012, gap=0.13, bevel=0.0)
    sx.letters("MEGATON", f, mid, 3.05, 0.27, "impact", mat.sign_paint((0.50, 0.04, 0.03), wear=0.15, seed=8), d=0.04, depth=0.01,
               gap=0.13, bevel=0.0)
    sx.bolts(f, [(0.03, 1.25), (width - 0.03, 1.25), (0.03, 2.8), (width - 0.03, 2.8), (0.03, 1.75), (width - 0.03, 1.75),
                 (0.03, 3.2), (width - 0.03, 3.2)], d=0.035)
    sx.gooseneck(f, mid, 3.38, reach=0.45, rise=0.34, d0=0.0)
    # a first-aid tin and a crutch at the foot: small, but they give the base something to stand in
    geo.box((0.36, 0.2, 0.26), f.at(0.3, 0.3, 0.0), f.rot - 15.0, sx.enamel((0.62, 0.62, 0.56), chips=0.5, seed=9), bevel=0.02)
    geo.pipe([f.at(width - 0.1, 0.12, 0.0), f.at(width - 0.16, 0.03, 1.25)], 0.022, wood, name="crutch")
    geo.pipe([f.at(width - 0.27, 0.03, 1.25), f.at(width - 0.05, 0.03, 1.25)], 0.028, wood, name="crutch_top")


# ------------------------------------------------------------------ CHILDREN OF ATOM
@piece("sg_atom", title="Sign of the Children of Atom",
       desc="An atom welded from reinforcing bar, on a pole. CHILDREN OF ATOM. Its heart glows a little, day and night.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", convert={"saturation": 1.1})
def sg_atom(ctx):
    f = sx.Frame((0.0, 0.0, 0.0), geo.SCREEN)
    steel = mat.steel(rust=0.55, seed=4)
    bar = mat.steel(rust=0.35, colour=(0.16, 0.16, 0.17), seed=9)
    sx.scaffold_pole((0.0, 0.0, 0.0), 2.75, radius=0.05, material=steel, foot=False)
    geo.tire((0.0, 0.0, 0.0), radius=0.36, seed=6)
    geo.cylinder(0.2, 0.2, (0.0, 0.0, 0.0), mat.concrete(seed=3), 12)
    cz = 3.35
    for spin in (0.0, 60.0, 120.0):
        sx.ring((0.0, cz), 0.72, 0.25, f, bar, tube=0.034, spin=spin)
    core = sx.sphere(0.15, f.at(0.0, 0.0, cz), mat.emitter((0.25, 1.0, 0.2), 2.5), name="nucleus")
    geo.set_fx(core, "slime")
    for spin, a in ((0.0, 25.0), (60.0, 200.0), (120.0, 110.0)):          # one electron ball per orbit
        c, s = math.cos(math.radians(spin)), math.sin(math.radians(spin))
        x, z = 0.72 * math.cos(math.radians(a)), 0.25 * math.sin(math.radians(a))
        sx.sphere(0.075, f.at(x * c - z * s, 0.02, cz + x * s + z * c), sx.brass(tarnish=0.3, seed=spin), name="electron")
    for a in (60.0, 120.0):                                               # two stays from the pole top to the rings
        geo.pipe([f.at(0.0, 0.0, 2.7), f.at(0.3 * math.cos(math.radians(a)) * 1.2, 0.0, cz - 0.21)], 0.02, steel)
    # the name plate: sheet iron on two chains
    p0, p1, top = -0.86, 0.86, 2.5
    geo.pipe([f.at(-0.8, 0.08, 2.62), f.at(0.8, 0.08, 2.62)], 0.03, steel, name="yard")
    for u in (-0.7, 0.7):
        geo.pipe([f.at(u, 0.08, 2.62), f.at(u, 0.08, top)], 0.015, steel, name="chain")
    sx.sheet_panel(f, p0, p1, top - 0.86, top, d=0.1, colour=(0.62, 0.44, 0.06), panels=2, flaking=0.3, seed=5)
    ink = mat.sign_paint(INK, wear=0.2, seed=2)
    sx.letters("CHILDREN", f, 0.0, top - 0.38, 0.28, "impact", ink, d=0.11, depth=0.012, gap=0.11, bevel=0.0)
    sx.letters("OF ATOM", f, 0.0, top - 0.78, 0.28, "impact", ink, d=0.11, depth=0.012, gap=0.11, bevel=0.0)


# ------------------------------------------------------------------ SHERIFF
@piece("sg_sheriff", title="Sheriff's Sign",
       desc="SHERIFF. The star was cut from a road sign and beaten into shape over a wheel hub.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", material="wood", light=(3, 85),
       convert={"saturation": 1.12})
def sg_sheriff(ctx):
    f = sx.Frame((0.0, 0.0, 0.0), geo.U)
    wood = mat.planks((0.20, 0.11, 0.05), width=2.0, axis="Z", grey=0.35, seed=12)
    geo.box((0.15, 0.15, 2.72), f.at(0.0, 0.0, 0.0), f.rot, wood, bevel=0.012, name="post")
    geo.box((0.5, 0.36, 0.2), f.at(0.0, 0.0, 0.0), f.rot, mat.concrete(seed=8), bevel=0.02, name="footing")
    for side in (-1, 1):
        geo.box((0.09, 0.09, 0.9), f.at(side * 0.42, 0.0, 0.0), f.rot, wood, bevel=0.008, roll=side * 28.0, name="foot_brace")
    # the name board, bolted across the post
    sx.plank_panel(f, -0.92, 0.92, 1.92, 2.5, d=0.1, paint=(0.045, 0.06, 0.09), wear=0.3, plank=0.29, ragged=0.04, seed=4)
    sx.letters("SHERIFF", f, 0.0, 2.04, 0.33, "impact", mat.sign_paint(BONE, wear=0.2, seed=3, glow=0.25), d=0.11, depth=0.012,
               gap=0.12, bevel=0.0)
    sx.bolts(f, [(-0.8, 2.2), (0.8, 2.2), (0.0, 2.38)], d=0.105)
    # the star on a round shield
    cz = 3.22
    sx.disc(0.66, f.at(0.0, 0.07, cz), f.rot, sx.enamel((0.05, 0.07, 0.11), chips=0.4, seed=6), thickness=0.04, name="shield")
    sx.ring((0.0, cz), 0.66, 0.66, f.moved(d=0.1), sx.brass(tarnish=0.5, seed=3), tube=0.03)
    sx.star(0.62, f.at(0.0, 0.12, cz), f.rot, sx.brass(tarnish=0.25, seed=5), relief=0.09)
    sx.gooseneck(f, 0.0, cz + 0.62, reach=0.48, rise=0.3, d0=0.05)
    geo.pipe([f.at(-0.75, 0.05, 2.5), f.at(-0.4, 0.05, cz - 0.5)], 0.02, mat.steel(rust=0.6, seed=2))
    geo.pipe([f.at(0.75, 0.05, 2.5), f.at(0.4, 0.05, cz - 0.5)], 0.02, mat.steel(rust=0.6, seed=2))


# ------------------------------------------------------------------ WATER
@piece("sg_water", title="Water Tank",
       desc="WATER, stenciled on a boiler shell. It drips, so it is not empty.",
       footprint=[(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (1, 1), (3, 1), (-1, 1)], anchors=[(4, 0)], shadow="baked",
       convert={"saturation": 1.05})
def sg_water(ctx):
    f = sx.Frame((row_x(4) + 0.2, 0.0, 0.0), geo.U)
    length = row_x(4) + 0.4
    radius, axis_z = 0.66, 1.3
    shell = mat.painted_metal((0.05, 0.12, 0.15), flaking=0.5, seed=7)
    steel = mat.steel(rust=0.75, seed=5)
    # the shell: a lathe turned on its side, with strap hoops and domed ends
    r = radius
    profile = [(0.0, -0.12), (r * 0.6, -0.08), (r * 0.93, 0.0), (r, 0.06)]
    for z in (0.55, 1.5, 2.45):
        if z < length - 0.2:
            profile += [(r, z - 0.04), (r + 0.025, z - 0.03), (r + 0.025, z + 0.03), (r, z + 0.04)]
    profile += [(r, length - 0.06), (r * 0.93, length), (r * 0.6, length + 0.08), (0.0, length + 0.12)]
    geo.lathe(profile, f.at(0.0, 0.0, axis_z), shell, 28, f.rot, 0.0, 90.0, name="tank")
    # cradle: two saddles on timber baulks
    for u in (0.5, length - 0.5):
        geo.box((0.16, 1.05, 0.2), f.at(u, 0.0, 0.0), f.rot, mat.planks((0.18, 0.10, 0.05), width=2.0, axis="Y", seed=u), bevel=0.01)
        for d in (-0.42, 0.42):
            geo.ibeam(axis_z - 0.3, f.at(u, d, 0.2), f.rot, steel, vertical=True, height=0.12, width=0.1)
        geo.box((0.14, 1.0, 0.1), f.at(u, 0.0, axis_z - radius - 0.04), f.rot, steel, bevel=0.005)
    # WATER, stencilled where the shell faces the camera
    lean = 22.0
    zc = axis_z + radius * math.sin(math.radians(lean))
    dc = radius * math.cos(math.radians(lean)) + 0.012
    sx.stencil("WATER", f, length / 2.0 + 0.05, zc - 0.26, 0.56, colour=(0.90, 0.88, 0.78), font="impact", d=dc, wear=0.12, seed=3,
               tilt=-lean, gap=0.16, glow=0.35)
    # filler neck, a pipe run with a valve wheel, a tap and its drip bucket, a ladder of two rungs
    geo.cylinder(0.14, 0.2, f.at(length * 0.72, 0.0, axis_z + radius - 0.03), steel, 12, name="neck")
    sx.disc(0.17, f.at(length * 0.72, 0.0, axis_z + radius + 0.17), f.rot, sx.enamel((0.45, 0.05, 0.03), chips=0.5), thickness=0.03,
            tilt=-90.0, name="cap")
    geo.pipe([f.at(0.2, 0.55, 0.45), f.at(0.2, 0.55, 0.78), f.at(-0.25, 0.55, 0.78), f.at(-0.25, 0.3, 0.78), f.at(-0.25, 0.3, axis_z)],
             0.04, steel, name="pipe")
    sx.disc(0.13, f.at(0.02, 0.61, 0.78), f.rot, sx.enamel((0.55, 0.05, 0.03), chips=0.3, seed=4), thickness=0.03, hole=0.05, name="valve")
    geo.barrel(f.at(0.22, 0.6, 0.0), radius=0.19, height=0.36, material=mat.painted_metal((0.20, 0.20, 0.19), flaking=0.5, seed=2))
    sx.disc(0.16, f.at(0.22, 0.6, 0.33), f.rot, mat.flat((0.02, 0.05, 0.07), roughness=0.1), thickness=0.01, tilt=-90.0, name="water")
    for z in (0.45, 0.85):
        geo.pipe([f.at(length - 1.0, 0.62, z), f.at(length - 0.62, 0.62, z)], 0.02, steel, name="rung")
    for u in (length - 1.0, length - 0.62):
        geo.pipe([f.at(u, 0.66, 0.0), f.at(u, 0.6, 1.25)], 0.022, steel, name="rail")


# ------------------------------------------------------------------ MUNICIPAL DETONATION TALLY
@piece("sg_bomb_notice", title="Municipal Notice",
       desc="DAYS WITHOUT A DETONATION: ALL OF THEM. The municipal tally remains undefeated.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", convert={"saturation": 0.98, "exposure": -0.4, "contrast": 1.3})
def sg_bomb_notice(ctx):
    f = sx.Frame((0.0, 0.0, 0.0), geo.SCREEN)
    steel = mat.steel(rust=0.6, seed=3)
    geo.ibeam(2.25, f.at(0.0, -0.05, 0.0), f.rot, steel, vertical=True, height=0.09, width=0.08)
    geo.box((0.3, 0.3, 0.1), f.at(0.0, -0.02, 0.0), f.rot + 20.0, mat.concrete(seed=2), bevel=0.02)
    w, z0, z1 = 0.9, 0.9, 2.28
    board = sx.enamel((0.72, 0.50, 0.05), chips=0.42, seed=2)
    geo.box((2 * w, 0.03, z1 - z0), f.at(0.0, 0.015, z0), f.rot, board, bevel=0.006, roll=-2.5, name="notice")
    g2 = f.moved(d=0.0)
    ink = mat.sign_paint(INK, wear=0.15, seed=4)
    # black hazard band along the top, lettering below
    geo.box((2 * w - 0.06, 0.012, 0.13), f.at(0.0, 0.04, z1 - 0.17), f.rot, ink, bevel=0.0, roll=-2.5)
    for k in range(6):
        sx.plate([(-0.05, -0.065), (0.02, -0.065), (0.09, 0.065), (0.02, 0.065)], f.at(-0.74 + k * 0.29, 0.047, z1 - 0.105),
                 f.rot, board, 0.006, roll=-2.5)
    sx.letters("DAYS WITHOUT", g2, 0.0, z1 - 0.60, 0.21, "impact", ink, d=0.04, depth=0.01, gap=0.08, bevel=0.0)
    sx.letters("A DETONATION", g2, 0.0, z1 - 0.93, 0.21, "impact", ink, d=0.04, depth=0.01, gap=0.08, bevel=0.0)
    sx.letters("ALL OF THEM", g2, 0.0, z1 - 1.30, 0.23, "impact", mat.sign_paint((0.50, 0.03, 0.02), wear=0.1, seed=6), d=0.04,
               depth=0.01, gap=0.08, bevel=0.0)
    sx.bolts(f, [(-w + 0.07, z1 - 0.3), (w - 0.07, z1 - 0.33), (-w + 0.07, z0 + 0.1), (w - 0.07, z0 + 0.07)], d=0.045)
    # a geiger-yellow drip tin and a wilted bunch of flowers at the foot
    geo.cylinder(0.11, 0.2, f.at(0.34, 0.2, 0.0), sx.enamel((0.62, 0.62, 0.55), chips=0.6, seed=3), 10)
