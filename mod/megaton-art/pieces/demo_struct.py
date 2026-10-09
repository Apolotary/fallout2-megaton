# SPDX-License-Identifier: MIT
"""Pipeline demo pieces (stage 1): a structure that must sort against a walking player, a lamp
that lights the night, a lettered sign. Owned by the pipeline stage; copy the pattern.
"""
import math

from kit import piece, geo, mat, G


@piece("mgt_stall", title="Lean-to", desc="A plank wall with a sheet-iron awning on two scrap girders.",
       material="wood", see_through=True)
def mgt_stall(ctx):
    # Hexes -1..3 of hex row 0: back wall on the row line, awning reaching 1.2 m towards the viewer
    # onto two posts that stand on hexes (-1, 2) and (3, 2). The space under the awning is walkable.
    _, y = G.hex_xy(0, 0)
    x_r = G.hex_xy(-1, 2)[0] - 0.2          # screen-right end: just outside the right post
    x_l = G.hex_xy(3, 2)[0] + 0.2           # screen-left end
    back, front = y + 0.05, G.hex_xy(3, 2)[1]
    geo.boards((x_l, back), (x_r, back), height=2.35, seed=7, ragged=0.14, material=mat.planks(seed=3))
    geo.box((x_l - x_r + 0.1, 0.06, 0.12), ((x_l + x_r) / 2, back + 0.05, 1.5), geo.U, mat.planks(axis="X", seed=5))
    steel = mat.steel(rust=0.75, seed=2)
    for dhx in (-1, 3):                     # posts stand ON hex centres (row 2), so they block cleanly
        px, py = G.hex_xy(dhx, 2)
        geo.ibeam(2.05, (px, py, 0.0), geo.U, steel, vertical=True, height=0.14, width=0.11)
    geo.ibeam(x_l - x_r + 0.3, (x_l + 0.1, front, 2.05), geo.U, steel, height=0.12, width=0.1)
    # roof: three overlapping sheets sloping from the wall (2.45 m) down to the girder (2.2 m)
    depth = front - back + 0.35
    slope = math.degrees(math.atan2(0.28, depth))
    r = ctx.rng
    x = x_l + 0.12
    for i in range(3):
        w = (x_l - x_r + 0.24) / 3 + 0.06
        geo.corrugated_panel(w, depth + r.uniform(-0.08, 0.08), (x, back - 0.15, 2.5 + 0.015 * (i % 2)), geo.U,
                             mat.corrugated(rust=0.45 + 0.2 * i, seed=20 + i, paint=(0.20, 0.27, 0.25) if i == 1 else None),
                             tilt=90.0 + slope + r.uniform(-1.5, 1.5), name=f"roof{i}")
        x -= w - 0.06
    geo.crate((0.6, 0.6, 0.55), (x_r + 0.45, back + 0.5, 0.0), geo.U, seed=4)


@piece("mgt_lamp", title="Work Lamp", desc="A bulb in a wire cage on a scaffold pole. It hums.",
       light=(5, 100), frames=4, fps=6, shadow="baked", footprint=[(0, 0)])
def mgt_lamp(ctx):
    steel = mat.steel(rust=0.6)
    geo.pipe([(0, 0, 0), (0, 0, 2.9), (-0.35, 0.2, 3.1)], 0.045, steel)
    geo.box((0.32, 0.32, 0.08), (0, 0, 0), 30.0, mat.concrete())
    lit = ctx.frame != 2                                   # one dark frame in four: a tired bulb
    head = (-0.35, 0.2, 2.98)
    geo.lathe([(0.0, 0.12), (0.16, 0.08), (0.2, 0.0), (0.18, 0.0), (0.14, 0.06), (0.0, 0.09)], head, steel, name="shade")
    if lit:
        geo.bulb((head[0], head[1], head[2] - 0.04), radius=0.085, strength=4.0)
        geo.halo((head[0], head[1], 0.0), radius=2.3, strength=1.0)
    else:
        geo.bulb((head[0], head[1], head[2] - 0.04), colour=(0.5, 0.3, 0.12), radius=0.085, strength=0.3)
        geo.halo((head[0], head[1], 0.0), radius=2.3, strength=0.35)


@piece("mgt_sign", title="Sign", desc="Hand-cut letters bolted to sheet iron. MEGATON, it says.",
       footprint=[(0, 0), (4, 0)])
def mgt_sign(ctx):
    # A board on two posts, four hexes apart along the row, high enough to walk under.
    x_r, y = G.hex_xy(0, 0)
    x_l, _ = G.hex_xy(4, 0)
    steel = mat.steel(rust=0.7, seed=4)
    for x in (x_l, x_r):
        geo.ibeam(3.3, (x, y, 0.0), geo.U, steel, vertical=True, height=0.16, width=0.12)
    centre = ((x_l + x_r) / 2, y + 0.1, 2.25)
    geo.sign("MEGATON", centre, geo.U, size=0.55, font="impact", board=(0.10, 0.16, 0.17), ink=(0.80, 0.70, 0.45),
             width=x_l - x_r + 0.5, seed=3)
    # a red neon bar under the lettering, painted with the animated fire colours: it flickers and
    # stays lit at night without any script or light source
    geo.neon_tube([(x_l + 0.1, y + 0.02, 2.2), (x_r - 0.1, y + 0.02, 2.2)], colour=(1.0, 0.16, 0.0), radius=0.03, fx="fire")
    geo.bulb_string((x_l, y + 0.05, 3.25), (x_r, y + 0.05, 3.25), count=7, sag=0.22)
