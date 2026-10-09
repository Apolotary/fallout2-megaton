# SPDX-License-Identifier: MIT
"""Megaton lights: strings of mismatched bulbs, the pole they hang from, a work lamp, a fire barrel.

STRING RUNS  sg_string_u3 / u5 run along a hex row, sg_string_v3 / v5 along a hex column, from
hex (0, 0) to the hex named below, hook to hook at 3.25 m - the top of sg_pole, and a hand above
the eave of a stock shack (2.66 m), so a run may also be tied to a building corner. Runs chain:
the next one starts on the hex the last one ended on.

    piece          from     to        length    anchor hex (= where its light is)
    sg_string_u3   (0, 0)   (6, 0)    4.16 m    (4, 0)
    sg_string_u5   (0, 0)   (10, 0)   6.93 m    (6, 0)
    sg_string_v3   (0, 0)   (0, 6)    4.80 m    (0, 3)
    sg_string_v5   (0, 0)   (0, 10)   8.00 m    (0, 5)

A run is ONE sprite, blocks nothing and is anchored in its middle. That sorts correctly because
its lowest bulb hangs 2.75 m up: a head (1.8 m) only reaches the cable on screen from at least
1.3 m BEHIND it, and whoever stands behind it is painted before it. The only thing that can sort
wrongly is something taller than 2.7 m standing within a hex in FRONT of the far half of a
column run; keep such runs clear of tall poles on their camera side.
The run's proto is a lamp (`light=`): its own hex is lit, so the whole sprite keeps its daylight
colours at night, and the ground under its middle is lit. A few bulbs are painted with the
animated palette ranges (orange "fire", green "slime", blue "monitors"): those flicker.

PLACEMENT (the table with hexes is placement.py, group "street")
  sg_pole          under every hook that is not a building corner.
  strings          at least five rows in front of a FRONT wall (the roof's eave is painted over
                   anything higher than 1.85 m + 0.48 m per metre in front of the wall), or
                   between buildings: across the saloon's approach on row 80, over the Brass
                   Lantern's customers on row 110, down both sides of the track from the pool.
  sg_worklamp      replaces the stock lamp posts 0x02000376 at the plant door and inside the gate.
  sg_fire_barrel   CUT in the review (placement.py VERDICTS): the stock burning barrel 0x02000001 has a
                   frame-animated flame and looks better. Not placed.
  sg_walllamp_u    beside a door in a FRONT wall (door on (hx, hy), hx odd): origin (hx + 3, hy + 1);
                   the lamp hangs at shoulder height over the blocked hex between origin and door,
                   because the eave hides anything higher on a front wall.
  sg_walllamp_v    over a door in a LEFT wall (door on (hx, hy), hy even): origin (hx + 2, hy + 2).
                   Both replace the invisible "Light Source" 0x0200008D the town puts on every
                   doorstep (layout/buildings.py add_lights): the lamp's proto gives the light.
The halo parts (layer "halo" in the manifest) tint the ground yellow by day too; a map script
may hide those objects until dusk.
"""
import math

from kit import piece, geo, mat, G
from kit import signs_extra as sx

HOOK_Z = 3.25
WARM = (1.0, 0.80, 0.45)
AMBER = (1.0, 0.55, 0.15)
PALE = (0.95, 0.95, 0.80)


def string_run(end_hex, count, sag, kinds, seed):
    x1, y1 = G.hex_xy(*end_hex)
    p0, p1 = (0.0, 0.0, HOOK_Z), (x1, y1, HOOK_Z)
    wire = mat.flat((0.025, 0.022, 0.02), roughness=0.6)
    geo.cable(p0, p1, sag, 0.019, wire, count=max(18, count * 2))
    points = geo.catenary(p0, p1, sag, count + 1)[1:-1]
    r = geo.rng(seed)
    sockets = mat.flat((0.03, 0.03, 0.03), roughness=0.5)
    for point in points:                                   # a socket above every bulb: the bulb needs something to hang from
        geo.cylinder(0.035, 0.07, (point[0], point[1], point[2] - 0.075), sockets, 8, name="socket")
    sx.bulbs_on(points, kinds, radius=0.066, drop=0.13, strength=1.9)
    # a second, dead cable looped along the first, and the knots at both hooks
    geo.cable((p0[0], p0[1], p0[2] - 0.05), (x1, y1, HOOK_Z - 0.05), sag + 0.16 + r.uniform(0.0, 0.08), 0.013, wire, count=18)
    for p in (p0, p1):
        sx.sphere(0.05, p, wire, name="knot")


KINDS_A = [WARM, WARM, "fire", PALE, None, WARM, "slime", WARM, AMBER, "monitors", WARM, None, WARM, "fire", PALE]
KINDS_B = [PALE, "fire", WARM, WARM, "monitors", AMBER, None, WARM, "slime", WARM, PALE, WARM, "fire", None, WARM]


@piece("sg_string_u3", title="String of Lights", desc="A cable of mismatched bulbs. Most of them work.",
       footprint=[], anchors=[(4, 0)], shadow="none", light=(5, 90), light_hex=(4, 0), material="glass")
def sg_string_u3(ctx):
    string_run((6, 0), 7, 0.38, KINDS_A, 1)


@piece("sg_string_u5", title="String of Lights", desc="A long cable of mismatched bulbs, sagging in the middle.",
       footprint=[], anchors=[(6, 0)], shadow="none", light=(7, 90), light_hex=(6, 0), material="glass")
def sg_string_u5(ctx):
    string_run((10, 0), 11, 0.5, KINDS_B, 2)


@piece("sg_string_v3", title="String of Lights", desc="A cable of mismatched bulbs. Most of them work.",
       footprint=[], anchors=[(0, 3)], shadow="none", light=(5, 90), light_hex=(0, 3), material="glass")
def sg_string_v3(ctx):
    string_run((0, 6), 7, 0.38, KINDS_B, 3)


@piece("sg_string_v5", title="String of Lights", desc="A long cable of mismatched bulbs, sagging in the middle.",
       footprint=[], anchors=[(0, 5)], shadow="none", light=(7, 90), light_hex=(0, 5), material="glass")
def sg_string_v5(ctx):
    string_run((0, 10), 11, 0.5, KINDS_A, 4)


@piece("sg_pole", title="Light Pole", desc="A scaffold tube in a tire full of concrete, with a cross arm for cables.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked")
def sg_pole(ctx):
    steel = mat.steel(rust=0.7, seed=3)
    wood = mat.planks((0.20, 0.12, 0.06), width=2.0, axis="X", grey=0.4, seed=2)
    geo.pipe([(0.0, 0.0, 0.0), (0.0, 0.0, HOOK_Z + 0.12)], 0.05, steel, name="pole")
    geo.tire((0.0, 0.0, 0.0), radius=0.37, seed=3)
    geo.cylinder(0.21, 0.24, (0.0, 0.0, 0.0), mat.concrete(seed=5), 12, name="plug")
    f = sx.Frame((0.0, 0.0, 0.0), geo.SCREEN)
    geo.box((0.9, 0.07, 0.09), f.at(0.0, 0.0, HOOK_Z - 0.2), f.rot, wood, bevel=0.008, roll=4.0, name="cross_arm")
    for u in (-0.36, 0.36):                                # two porcelain insulators
        geo.cylinder(0.04, 0.1, f.at(u, 0.0, HOOK_Z - 0.1), mat.flat((0.55, 0.52, 0.45), roughness=0.3), 8, name="insulator")
    geo.pipe([f.at(-0.3, 0.0, HOOK_Z - 0.2), f.at(0.0, 0.0, HOOK_Z - 0.6)], 0.018, steel, name="brace")
    geo.pipe([f.at(0.3, 0.0, HOOK_Z - 0.2), f.at(0.0, 0.0, HOOK_Z - 0.6)], 0.018, steel, name="brace")
    geo.box((0.2, 0.12, 0.28), f.at(0.0, 0.07, 1.5), f.rot, mat.painted_metal((0.16, 0.17, 0.15), flaking=0.5, seed=4), bevel=0.01,
            name="fuse_box")
    wire = mat.flat((0.025, 0.022, 0.02), roughness=0.6)
    geo.pipe([f.at(0.0, 0.06, 1.78), f.at(0.03, 0.06, 2.4), f.at(-0.02, 0.06, HOOK_Z - 0.25)], 0.014, wire, name="riser")
    geo.pipe([f.at(0.36, 0.0, HOOK_Z - 0.02), f.at(0.2, 0.02, HOOK_Z - 0.5), f.at(0.05, 0.06, HOOK_Z - 0.28)], 0.013, wire, name="loop")


@piece("sg_worklamp", title="Work Lamp", desc="A caged bulb on a long flex, slung from a scaffold pole. It hums.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", light=(5, 100), convert={"halo_levels": 3})
def sg_worklamp(ctx):
    f = sx.Frame((0.0, 0.0, 0.0), geo.SCREEN)
    steel = mat.steel(rust=0.6, seed=8)
    geo.pipe([(0.0, 0.0, 0.0), f.at(0.05, 0.0, 3.0)], 0.048, steel, name="pole")
    geo.box((0.4, 0.34, 0.1), (0.0, 0.0, 0.0), 25.0, mat.concrete(seed=7), bevel=0.02, name="pad")
    geo.box((0.36, 0.3, 0.28), (0.0, 0.0, 0.1), 25.0, mat.painted_metal((0.20, 0.13, 0.03), flaking=0.5, seed=3), bevel=0.02,
            name="battery")
    tip = f.at(-0.85, 0.0, 2.88)
    geo.pipe([f.at(0.05, 0.0, 2.72), tip], 0.032, steel, name="arm")
    geo.pipe([f.at(0.04, 0.0, 2.25), f.at(-0.5, 0.0, 2.8)], 0.022, steel, name="strut")
    wire = mat.flat((0.025, 0.022, 0.02), roughness=0.6)
    hook = (tip[0], tip[1], 2.38)
    geo.pipe([tip, hook], 0.014, wire, name="flex")
    geo.cable(f.at(0.03, 0.03, 0.4), f.at(0.05, 0.03, 2.7), sag=0.0, radius=0.014, material=wire)
    geo.cable(f.at(0.05, 0.0, 2.72), tip, sag=0.22, radius=0.013, material=wire)
    sx.caged_lamp(hook, size=1.25, strength=4.5)
    geo.halo((hook[0], hook[1], 0.0), radius=2.3, strength=0.9)


@piece("sg_fire_barrel", title="Fire Barrel", desc="An oil drum with holes punched in it and something burning inside.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", light=(4, 95), convert={"halo_levels": 3, "saturation": 1.15})
def sg_fire_barrel(ctx):
    drum = mat.painted_metal((0.08, 0.035, 0.02), flaking=0.85, seed=5)
    geo.barrel((0.0, 0.0, 0.0), radius=0.3, height=0.9, material=drum, seed=5)
    geo.lathe([(0.27, 0.0), (0.27, 0.05), (0.2, 0.05)], (0.0, 0.0, 0.86), mat.flat((0.012, 0.01, 0.01)), 16, name="soot_rim")
    # punched air holes glowing with the coals behind them: on the two sides the camera sees
    r = geo.rng(5)
    holes = []
    for k in range(9):
        a = math.radians(r.uniform(-65.0, 115.0))               # angle round the drum, 0 = towards +X
        z = r.uniform(0.14, 0.62)
        holes.append(sx.sphere(0.042, (0.292 * math.cos(a), 0.292 * math.sin(a), z), mat.emitter((1.0, 0.3, 0.02), 2.5), name="hole"))
    geo.set_fx(holes, "fire")
    sx.flames((0.0, 0.0, 0.84), radius=0.24, height=0.62, count=9, seed=3)
    # scrap wood sticking out, a few bricks to keep it level
    wood = mat.planks((0.10, 0.06, 0.03), width=2.0, axis="Z", grey=0.1, seed=4)
    geo.box((0.07, 0.03, 0.7), (0.08, -0.05, 0.55), 20.0, wood, bevel=0.004, tilt=14.0, roll=10.0, name="stick")
    geo.box((0.06, 0.03, 0.6), (-0.1, 0.06, 0.55), 80.0, wood, bevel=0.004, tilt=-12.0, roll=-14.0, name="stick")
    brick = mat.concrete((0.26, 0.12, 0.08), cracks=0.2, seed=3)
    geo.box((0.22, 0.11, 0.07), (0.33, 0.2, 0.0), 30.0, brick, bevel=0.008, name="brick")
    geo.box((0.22, 0.11, 0.07), (-0.3, 0.26, 0.0), 100.0, brick, bevel=0.008, name="brick")
    geo.halo((0.0, 0.0, 0.0), radius=2.1, strength=1.0)


def _wall_lamp(f, steel, z=2.22, rise=0.3, reach=0.6):
    """Gooseneck on the face `f`: back plate, conduit down to a switch box, shade and bulb."""
    geo.box((0.2, 0.03, 0.2), f.at(0.0, 0.015, z - 0.1), f.rot, steel, bevel=0.006, name="back_plate")
    sx.gooseneck(f, 0.0, z, reach=reach, rise=rise, d0=0.02, strength=3.5, shade=0.15)
    wire = mat.steel(rust=0.4, colour=(0.07, 0.07, 0.07), seed=3)
    geo.pipe([f.at(0.0, 0.03, z - 0.02), f.at(0.5, 0.03, z + 0.03), f.at(0.5, 0.03, 1.2)], 0.02, wire, name="conduit")
    geo.box((0.16, 0.08, 0.22), f.at(0.5, 0.04, 1.0), f.rot, mat.painted_metal((0.20, 0.20, 0.18), flaking=0.5, seed=6), bevel=0.01,
            name="switch_box")
    for cz in (z - 0.4, 1.3):
        geo.box((0.07, 0.03, 0.04), f.at(0.5, 0.035, cz), f.rot, steel, bevel=0.0, name="clip")


@piece("sg_walllamp_u", title="Door Lamp", desc="A tin shade on a bent pipe beside the door. The switch works.",
       footprint=[], anchors=[(0, 0)], shadow="none", light=(4, 90), convert={"halo_levels": 3})
def sg_walllamp_u(ctx):
    # On a FRONT wall the stock roof overhangs by 1.7 m and hides everything above 1.9 m at the wall
    # (2.1 m half a metre out), so this lamp sits at shoulder height BESIDE the door, over the
    # blocked hex (-1, 0) in front of the wall, where nobody can walk into it.
    x = G.hex_xy(-1, 0)[0]
    f = sx.Frame((x, -0.8 + G.STOCK_WALL_FRONT_U + 0.01, 0.0), geo.U)
    _wall_lamp(f, mat.steel(rust=0.6, seed=4), z=1.66, rise=0.26, reach=0.5)
    geo.halo(f.at(0.0, 0.8, 0.0)[:2] + (0.0,), radius=1.6, strength=0.85)


@piece("sg_walllamp_v", title="Door Lamp", desc="A tin shade on a bent pipe over the door. The switch works.",
       footprint=[], anchors=[(0, 0)], shadow="none", light=(4, 90), convert={"halo_levels": 3})
def sg_walllamp_v(ctx):
    y = G.hex_xy(0, -2)[1]                                  # over the door hex, two rows behind the origin
    f = sx.Frame((-G.SQ_U_M + G.STOCK_WALL_FRONT_V + 0.01, y, 0.0), geo.V)
    _wall_lamp(f, mat.steel(rust=0.6, seed=5))
    geo.halo(f.at(0.0, 0.75, 0.0)[:2] + (0.0,), radius=1.6, strength=0.85)
