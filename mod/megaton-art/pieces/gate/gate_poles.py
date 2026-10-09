# SPDX-License-Identifier: MIT
"""Power poles and the cables that run from the gate's sign into the town.

    mg_pole        a timber pole with two crossarms, a pole-pig transformer and a lamp. Blocks its
                   own hex (origin). The upper crossarm (5.3 m, along the hex row) takes cables that
                   run along a hex COLUMN; the lower one (4.9 m, across) takes cables along a ROW.
    mg_wire_v      three cables between the upper crossarms of two poles on the same column, ten
                   rows apart: origin = the far pole's hex (0, 0), the near pole stands on (0, 10).
    mg_wire_u      two cables between the lower crossarms of two poles on the same row, twelve
                   hexes apart: origin = the screen-right pole (0, 0), the other stands on (12, 0).
    mg_wire_gate   the hook-up: two cables from the top of the gate sign's left upright to a pole
                   on hex (6, -6) of the GATE's origin (town: pole on (106, 120)). Placed with the
                   gate's origin.

DRAW ORDER OF A CABLE  A cable hangs 4.5 m and more above the ground. Whoever overlaps it on the
screen stands 8 to 14 hex rows in FRONT of the ground under it, and nothing behind it is tall
enough to reach it. So a cable sorts correctly if each stretch is anchored anywhere within a few
rows of the ground beneath it: the cables are cut on a handful of hexes along their run (not one
part per hex), none of which blocks.
"""
import bpy

from kit import piece, geo, mat, G
from kit import gate_extra as X

ARM_V = 5.30            # upper crossarm (cables along a column)
ARM_U = 4.90            # lower crossarm (cables along a row)
TOP = 5.62
WIRE = 0.02
V_SPAN, U_SPAN = 10, 12
GATE_POLE = (6, -6)     # where mg_wire_gate expects a pole, from the gate's origin


def _insulator(at):
    geo.lathe([(0.03, 0.0), (0.055, 0.03), (0.035, 0.06), (0.055, 0.09), (0.02, 0.13), (0.0, 0.13)], at,
              mat.flat((0.30, 0.20, 0.14), roughness=0.35), 10, name="insulator")


def pole(x=0.0, y=0.0, lamp=True, seed=1):
    wood = mat.planks(colour=(0.20, 0.13, 0.08), width=0.6, axis="Z", grey=0.5, seed=seed)
    steel = mat.steel(rust=0.6, seed=seed + 2)
    geo.lathe([(0.15, 0.0), (0.14, 0.4), (0.115, TOP - 0.3), (0.10, TOP), (0.0, TOP)], (x, y, 0.0), wood, 12, name="pole")
    geo.cylinder(0.16, 0.07, (x, y, 0.55), steel, segments=12, name="strap")
    # upper crossarm along the hex row (X), a little out of level, braced
    geo.box((1.56, 0.11, 0.12), (x, y + 0.02, ARM_V - 0.12), 0.0, wood, bevel=0.01, name="arm_v", roll=1.8)
    for side in (-1, 1):
        geo.pipe([(x + side * 0.62, y + 0.06, ARM_V - 0.1), (x, y + 0.08, ARM_V - 0.62)], 0.022, steel, name="arm_brace")
    for dx in (-0.66, 0.0, 0.66):
        _insulator((x + dx, y + 0.02, ARM_V + (0.0 if dx else 0.02)))
    # lower crossarm across (Y)
    geo.box((0.11, 1.2, 0.11), (x + 0.02, y, ARM_U - 0.11), 0.0, wood, bevel=0.01, name="arm_u", tilt=-1.5)
    for dy in (-0.5, 0.5):
        _insulator((x + 0.02, y + dy, ARM_U))
    # the pole pig: a transformer can strapped to the viewer's side, its bushings, a drop to the lamp
    can = mat.painted_metal((0.16, 0.18, 0.19), flaking=0.5, seed=seed + 4)
    geo.lathe([(0.0, 0.0), (0.19, 0.0), (0.21, 0.05), (0.21, 0.5), (0.17, 0.56), (0.0, 0.56)], (x + 0.2, y + 0.22, 3.72), can, 14, name="transformer")
    for d in (-0.08, 0.08):
        _insulator((x + 0.2 + d, y + 0.22 - d, 4.28))
    geo.cylinder(0.125, 0.06, (x, y, 3.9), steel, segments=12, name="strap")
    # a warning plate at eye level: the one clean rectangle on the pole
    geo.box((0.03, 0.26, 0.32), (x + 0.13, y + 0.02, 1.55), 0.0, mat.painted_metal((0.62, 0.42, 0.03), flaking=0.25, seed=seed), bevel=0.0,
            name="danger_plate")
    geo.box((0.035, 0.18, 0.07), (x + 0.135, y + 0.02, 1.74), 0.0, mat.flat((0.03, 0.03, 0.03)), bevel=0.0, name="danger_bar")
    # climbing pegs up the back
    for k in range(7):
        z = 1.0 + k * 0.42
        side = 1 if k % 2 else -1
        geo.pipe([(x, y, z), (x + side * 0.26, y - side * 0.08, z + 0.02)], 0.018, steel, name="peg")
    # guy wire to a stake behind
    geo.cable((x, y - 0.05, 4.5), (x - 0.5, y - 1.5, 0.0), sag=0.0, radius=0.02)
    if lamp:
        arm_end = (x + 0.55, y + 0.8, 4.36)
        geo.pipe([(x, y, 4.05), (x + 0.3, y + 0.45, 4.42), arm_end], 0.03, steel, name="lamp_arm")
        geo.lathe([(0.0, 0.12), (0.17, 0.07), (0.22, 0.0), (0.2, 0.0), (0.15, 0.05), (0.0, 0.085)], (arm_end[0], arm_end[1], arm_end[2] - 0.12),
                  steel, 14, name="lamp_shade")
        geo.bulb((arm_end[0], arm_end[1], arm_end[2] - 0.15), colour=(1.0, 0.68, 0.30), radius=0.08, strength=2.6)
        # the pool is centred on the POLE, not under the lamp: a halo is drawn at the light level of the hex
        # it is anchored on, and only on the lamp's own hex is that as bright as the ground it tints
        geo.halo((x, y, 0.0), radius=2.1, strength=0.55)


@piece("mg_pole", title="Power Pole", desc="A pole off the old grid, a transformer can still strapped to it. The lamp is the only thing it powers.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="flat", light=(5, 80), material="wood")
def mg_pole(ctx):
    # shadow="flat": baked into the sprite, a shadow this long was painted over whoever stood behind the pole
    pole()


def _ghost_pole(x, y):
    """The pole a cable ends on, as a holdout: the cable sprite has a hole where the pole hides it."""
    before = {obj.name for obj in bpy.context.scene.objects}
    pole(x, y, lamp=False)
    for obj in bpy.context.scene.objects:
        if obj.name not in before:
            obj.is_holdout = True


@piece("mg_wire_v", title="Power Cables", desc="Cables, slack between two poles. They hum when the gate moves.",
       footprint=[], anchors=[(0, 1), (0, 4), (0, 7), (0, 9)], shadow="none", material="metal", convert={"alpha_threshold": 0.3, "outline": 0.0, "outline_lit": 0.0})
def mg_wire_v(ctx):
    x1, y1 = G.hex_xy(0, V_SPAN)
    for dx, sag in ((-0.66, 0.62), (0.0, 0.74), (0.66, 0.55)):
        z = ARM_V + 0.13 + (0.0 if dx else 0.02)
        geo.cable((dx, 0.02, z), (x1 + dx, y1 + 0.02, z), sag=sag, radius=WIRE, count=28)
    _ghost_pole(0.0, 0.0)
    _ghost_pole(x1, y1)


@piece("mg_wire_u", title="Power Cables", desc="Cables, slack between two poles. They hum when the gate moves.",
       footprint=[], anchors=[(1, 0), (4, 0), (8, 0), (11, 0)], shadow="none", material="metal", convert={"alpha_threshold": 0.3, "outline": 0.0, "outline_lit": 0.0})
def mg_wire_u(ctx):
    x1, y1 = G.hex_xy(U_SPAN, 0)
    for dy, sag in ((-0.5, 0.7), (0.5, 0.58)):
        z = ARM_U + 0.13
        geo.cable((0.02, dy, z), (x1 + 0.02, y1 + dy, z), sag=sag, radius=WIRE, count=28)
    _ghost_pole(0.0, 0.0)
    _ghost_pole(x1, y1)


@piece("mg_wire_gate", title="Power Cables", desc="The feed for the sign: two cables from the old pole down to the gate.",
       footprint=[], anchors=[(6, -5), (5, -3), (4, -1)], shadow="none", material="metal", convert={"alpha_threshold": 0.3, "outline": 0.0, "outline_lit": 0.0})
def mg_wire_gate(ctx):
    row = X.Row(0, 1)                                    # the gate's frame (pieces/gate/gate_main.py)
    px, py = G.hex_xy(*GATE_POLE)
    for dx, r, sag in ((-0.66, -2.75, 0.5), (0.0, -2.60, 0.62)):
        geo.cable((px + dx, py + 0.02, ARM_V + 0.13), row.p(r, -0.04, 4.90), sag=sag, radius=WIRE, count=28)
    _ghost_pole(px, py)
