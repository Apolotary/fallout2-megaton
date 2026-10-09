# SPDX-License-Identifier: MIT
"""Poles and overhead cable (author "ground"): the tangle over the lanes.

POLES   gr_pole_a      a scaffold tube in a tyre of concrete: angle-iron cross arms, a dead street lamp, boots on a wire
        gr_pole_b      a timber pole spliced from two lengths and lashed, a tannoy horn at the top
        gr_pole_lamp   as gr_pole_a with a working lamp (a light source: 5 hexes, 75 %)
        Each blocks its own hex (0, 0). All three carry cables at the same heights:
            the UPPER arm (4.3 m, along the hex row) takes cables that run down a COLUMN, 0.5 m either side
            the LOWER arm (3.9 m, across) takes cables that run along a ROW, 0.4 m either side
CABLES  gr_cable_u6 / u8   three cables between the lower arms of two poles on one row, 6 / 8 hexes
                           apart: origin = the screen-right pole (0, 0), the other stands on (6 | 8, 0)
        gr_cable_v6 / v8   three cables between the upper arms of two poles on one column: origin =
                           the far pole (0, 0), the near one stands on (0, 6 | 8)
        Cables block nothing. Each is cut on a few hexes under its run (see pieces/gate/gate_poles.py
        on why that sorts correctly), and each has something caught on it.
"""
import math

from kit import piece, geo, mat, G
from kit import ground_extra as gx
from kit import signs_extra as sx

HU, HV = gx.HEX_U, gx.HEX_V
ARM_V, ARM_U = 4.30, 3.90
KNOB = 0.13
WIRE = 0.02
POLE = dict(footprint=[(0, 0)], anchors=[(0, 0)], shadow="flat")
CABLE = dict(footprint=[], shadow="none", material="metal", convert={"alpha_threshold": 0.3, "outline": 0.0, "outline_lit": 0.0})


def knob(at):
    geo.lathe([(0.03, 0.0), (0.055, 0.03), (0.035, 0.06), (0.055, 0.09), (0.02, 0.13), (0.0, 0.13)], at, mat.flat((0.30, 0.20, 0.14), roughness=0.35), 10, name="insulator")


def arms(x=0.0, y=0.0, wood=False, seed=0):
    material = gx.wood((0.21, 0.13, 0.07), seed=seed, axis="X", grey=0.5) if wood else gx.iron(0.8, seed)
    size = (1.3, 0.09, 0.09) if wood else (1.3, 0.06, 0.06)
    geo.box(size, (x, y + 0.03, ARM_V - size[2]), 0.0, material, bevel=0.006, name="arm_v", roll=2.0)
    geo.box((size[1], 1.05, size[2]), (x + 0.03, y, ARM_U - size[2]), 0.0, material, bevel=0.006, name="arm_u", tilt=-1.5)
    for dx in (-0.5, 0.5):
        knob((x + dx, y + 0.03, ARM_V))
    for dy in (-0.4, 0.4):
        knob((x + 0.03, y + dy, ARM_U))
    steel = mat.steel(rust=0.7, seed=seed)
    for side in (-1, 1):
        geo.pipe([(x + side * 0.5, y + 0.05, ARM_V - 0.06), (x, y + 0.06, ARM_V - 0.5)], 0.02, steel, name="arm_brace")


def lamp_head(x, y, lit, seed=0):
    steel = mat.steel(rust=0.6, seed=seed)
    end = (x + 0.5, y + 0.75, 3.55)
    geo.pipe([(x, y, 3.3), (x + 0.28, y + 0.42, 3.62), end], 0.028, steel, name="lamp_arm")
    geo.lathe([(0.0, 0.12), (0.17, 0.07), (0.22, 0.0), (0.2, 0.0), (0.15, 0.05), (0.0, 0.085)], (end[0], end[1], end[2] - 0.12), gx.paint("green", rust=0.5, seed=seed), 14,
              name="lamp_shade")
    if lit:
        geo.bulb((end[0], end[1], end[2] - 0.15), colour=(1.0, 0.68, 0.30), radius=0.08, strength=2.4)
    else:
        sx.sphere(0.07, (end[0], end[1], end[2] - 0.14), sx.dead_tube(), name="bulb_off")


def scaffold_pole(lit, seed):
    steel = mat.steel(rust=0.7, seed=seed)
    gx.rod((0, 0, 0), (0.04, 0.0, 2.6), 0.055, steel, 10, name="pole")
    gx.rod((0.04, 0, 2.5), (0.0, 0.0, ARM_V + 0.3), 0.045, mat.steel(rust=0.5, seed=seed + 1), 10, name="pole_top")
    geo.lathe([(0.075, 0.0), (0.075, 0.22)], (0.04, 0.0, 2.45), gx.iron(0.6, seed), 10, name="coupler")
    geo.tire((0, 0, 0), 0.36, 0.22, lying=True, seed=seed)
    geo.cylinder(0.21, 0.21, (0, 0, 0), mat.concrete(seed=seed), 12, name="foot")
    arms(0.0, 0.0, False, seed)
    lamp_head(0.02, 0.0, lit, seed)
    # a coil of spare cable on a hook, a warning plate, a guy wire to a stake behind
    geo.lathe([(0.14, 0.0), (0.19, 0.02), (0.19, 0.07), (0.14, 0.09), (0.14, 0.0)], (0.08, 0.06, 1.9), mat.flat((0.03, 0.03, 0.03), roughness=0.6), 12, name="coil", tilt=90.0)
    geo.box((0.26, 0.02, 0.3), (0.02, 0.07, 1.25), 0.0, gx.paint("yellow", rust=0.35, seed=seed, runs=0.6), bevel=0.0, name="plate")
    geo.cable((0.0, -0.04, 3.8), (-0.45, -1.4, 0.0), sag=0.0, radius=WIRE)


@piece("gr_pole_a", title="Cable Pole", desc="Two lengths of scaffold tube coupled together and stood in a tyre of concrete. The lamp on it died before you were born.",
       **POLE)
def gr_pole_a(ctx):
    scaffold_pole(False, 601)
    gx.hang((0.45, 0.03, ARM_V - 0.08), "shoe", seed=2, drop=0.4)


@piece("gr_pole_lamp", title="Lamp Pole", desc="A scaffold tube in a tyre of concrete, with the one street lamp on this side of town that works.",
       light=(5, 75), **POLE)
def gr_pole_lamp(ctx):
    scaffold_pole(True, 605)
    geo.halo((0.0, 0.0, 0.0), radius=2.0, strength=0.5)


@piece("gr_pole_b", title="Cable Pole", desc="A timber pole, spliced where it broke and bound with wire. The horn at the top carried announcements once.",
       material="wood", **POLE)
def gr_pole_b(ctx):
    wood = gx.wood((0.20, 0.13, 0.08), seed=611, axis="Z", width=0.6, grey=0.5)
    geo.lathe([(0.14, 0.0), (0.13, 0.4), (0.11, 2.5), (0.11, 2.9)], (0, 0, 0), wood, 12, name="pole")
    geo.lathe([(0.10, 0.0), (0.085, ARM_V + 0.35 - 2.3), (0.0, ARM_V + 0.35 - 2.3)], (0.1, 0.03, 2.3), gx.wood((0.23, 0.15, 0.09), seed=612, axis="Z", width=0.6, grey=0.4), 12, name="pole_top")
    for z in (2.38, 2.6, 2.82):
        gx.lash((0.05, 0.015, z), radius=0.17, height=0.1, colour=(0.06, 0.05, 0.04))
    for k in range(4):
        geo.box((0.3, 0.26, 0.14), (0.0, 0.0, 0.0), 45.0 * k, mat.concrete((0.22, 0.20, 0.17), cracks=0.1, seed=k), bevel=0.05, name="stone")
    arms(0.1, 0.03, True, 613)
    # the horn: a grey cone on a bracket, pointing at the street
    geo.lathe([(0.05, 0.0), (0.06, 0.12), (0.26, 0.5), (0.27, 0.52), (0.24, 0.5), (0.04, 0.12), (0.0, 0.12)], (0.14, 0.12, 3.45), gx.paint("grey", rust=0.45, seed=614), 14,
              name="horn", tilt=78.0, rot=-20.0)
    geo.box((0.12, 0.12, 0.16), (0.12, 0.1, 3.37), 0.0, gx.iron(0.6, 5), bevel=0.01, name="horn_driver")
    for k in range(6):
        z = 0.9 + k * 0.42
        side = 1 if k % 2 else -1
        geo.pipe([(0.0, 0.0, z), (side * 0.24, -side * 0.07, z + 0.02)], 0.018, mat.steel(rust=0.8, seed=k), name="peg")
    geo.box((0.03, 0.3, 0.2), (0.13, 0.0, 1.45), 0.0, gx.paint("cream", rust=0.3, seed=7), bevel=0.0, name="notice", roll=0.0)


def run_u(n, sags, extra):
    x1 = n * HU
    for k, (dy, sag) in enumerate(zip((-0.4, 0.4, 0.0), sags)):
        z = ARM_U + KNOB - (0.0 if dy else 0.45)
        y = dy if dy else 0.06
        geo.cable((0.03, y, z), (x1 + 0.03, y, z), sag=sag, radius=WIRE, count=28)
    t = 0.38
    z = ARM_U + KNOB - sags[0] * 4.0 * t * (1.0 - t)
    gx.hang((x1 * t, -0.4, z), extra, seed=n, drop=0.3)
    if n >= 8:
        f = gx.Frame((0.0, 0.4, 0.0), 0.0)
        t = 0.66
        z = ARM_U + KNOB - sags[1] * 4.0 * t * (1.0 - t)
        sx.cloth(f, x1 * t, z, 0.34, 0.5, sx.fabric((0.30, 0.10, 0.07), seed=n), seed=n, taper=0.3)


def run_v(n, sags, extra):
    y1 = n * HV
    for k, (dx, sag) in enumerate(zip((-0.5, 0.5, 0.0), sags)):
        z = ARM_V + KNOB - (0.0 if dx else 0.5)
        x = dx if dx else 0.08
        geo.cable((x, 0.03, z), (x, y1 + 0.03, z), sag=sag, radius=WIRE, count=28)
    t = 0.6
    z = ARM_V + KNOB - sags[1] * 4.0 * t * (1.0 - t)
    gx.hang((0.5, y1 * t, z), extra, seed=n + 3, drop=0.35)


@piece("gr_cable_u6", title="Cables", desc="Three cables, slack between two poles. A hub cap turns on a wire somebody threw over them.",
       anchors=[(1, 0), (3, 0), (5, 0)], **CABLE)
def gr_cable_u6(ctx):
    run_u(6, (0.5, 0.62, 0.8), "hubcap")


@piece("gr_cable_u8", title="Cables", desc="Three cables, slack between two poles. A pair of boots hangs from the lowest by its laces.",
       anchors=[(1, 0), (3, 0), (5, 0), (7, 0)], **CABLE)
def gr_cable_u8(ctx):
    run_u(8, (0.62, 0.75, 1.0), "shoe")


@piece("gr_cable_v6", title="Cables", desc="Three cables, slack between two poles. A bottle swings from one, for luck or for target practice.",
       anchors=[(0, 1), (0, 3), (0, 5)], **CABLE)
def gr_cable_v6(ctx):
    run_v(6, (0.5, 0.64, 0.85), "bottle")


@piece("gr_cable_v8", title="Cables", desc="Three cables, slack between two poles. Boots hang from one by their laces.",
       anchors=[(0, 1), (0, 3), (0, 5), (0, 7)], **CABLE)
def gr_cable_v8(ctx):
    run_v(8, (0.65, 0.8, 1.05), "shoe")
