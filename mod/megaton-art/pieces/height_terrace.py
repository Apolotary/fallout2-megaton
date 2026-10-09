# SPDX-License-Identifier: MIT
"""Crater terracing: the UPPER tier of retaining wall, so the pool sits visibly lower. (author "height")

The bomb author's rim kit (mgb_rim_*) rings the pool with a knee-high wall. These pieces are the
step above it, to be laid a few rows further out on the FAR side of the pool (towards the saloon)
and down its screen-right flank: a chest-high wall of driven piles and whatever would hold earth
back, with the earth it holds heaped on top. Two tiers of wall stepping down towards the camera
are what makes the middle read as a hole.

    piece               runs along      blocks                          chain: next copy at
    ht_terrace_u_a/_b   a hex row       hexes 0..5 of row 0             (+6, 0) / (-6, 0)
    ht_terrace_steps    a hex row       hexes 0..3 of rows 0 and 1      between two walls: decorative steps
    ht_terrace_end      one hex         (0, 0)                          a wall's end: a pile, sandbags, a lamp post base
    ht_terrace_v_a      a hex column    (0, 0) .. (0, 5)                (0, +6) / (0, -6); its face looks LEFT, so it
                                                                        goes on the screen-RIGHT flank of the pool

They are under 1.1 m, throw no ground shadow (a shadow behind a retaining wall would say the ground
there is as low as in front), and leave gaps where the town's paths come down: lay ht_terrace_end
on the hex each side of a gap.
"""
import math

from kit import piece, geo, mat, G
from kit import height_extra as H
from kit import bomb_extra as bx
from kit import gate_extra as X
from kit import signs_extra as sx

HEX = H.HEX
TOP = 0.86
EARTH = (0.20, 0.155, 0.105)
DRY = (0.30, 0.235, 0.165)
TERRACE = dict(see_through=False, shadow="none", material="dirt", convert=dict(H.GRADE, contrast=1.3))


def _earth(seed):
    return bx.mud(colour=EARTH, wet=0.05, seed=float(seed), cracks=0.3, dry=DRY)


def _bank_u(x0, x1, seed, back=-0.72, top=TOP):
    """Earth heaped behind a wall on the row line: level with the wall's head, falling away behind."""
    def height(x, y):
        t = (y - back) / (0.0 - back)                        # 0 at the back, 1 at the wall
        if t < 0.0 or t > 1.0:
            return None
        lump = 0.06 * bx.fbm(x, y, seed, 2.5)
        return max(0.01, (top + 0.04) * min(1.0, t * 1.9) ** 0.8 + lump * min(1.0, t * 2.5))
    return bx.heightfield(x0, x1, back, 0.02, height, _earth(seed), step=0.07, name="bank")


def _bank_v(y0, y1, seed, back=-0.36, top=TOP):
    def height(x, y):
        t = (x - back) / (0.0 - back)
        if t < 0.0 or t > 1.0:
            return None
        lump = 0.05 * bx.fbm(x, y, seed, 2.5)
        return max(0.01, (top + 0.04) * min(1.0, t * 2.2) ** 0.8 + lump * min(1.0, t * 2.5))
    return bx.heightfield(back, 0.02, y0, y1, height, _earth(seed), step=0.06, name="bank")


def _piles(f, us, seed, top=TOP + 0.12):
    """Driven piles in front of the lagging: I-beams, rails, a trunk; every one a little off plumb."""
    r = geo.rng(seed)
    for k, u in enumerate(us):
        x, y, _ = f.at(u, 0.1, 0.0)
        kind = ("beam", "timber", "pole", "beam", "tube")[(k + seed) % 5]
        H.post(x, y, 0.0, top + r.uniform(-0.08, 0.14), kind, seed + k, pad=False, lean=(r.uniform(-0.03, 0.03), r.uniform(0.0, 0.05)))


def _drain(f, u, z=0.34, seed=0):
    """A drain pipe through the wall and what has dribbled out of it: the stain glows faintly at night."""
    a, b = f.at(u, -0.1, z), f.at(u, 0.24, z - 0.03)
    geo.set_block(geo.pipe([a, b], 0.075, H.tube(0.8, 2.0 + seed), name="drain", resolution=9), 0.0)
    H.streak(f, u, z - 0.05, z - 0.06, 0.16, 0.085, colour=(0.03, 0.035, 0.02))
    drip = geo.box((0.05, 0.02, z - 0.1), f.at(u, 0.1, 0.03), f.rot, mat.emitter((0.25, 0.9, 0.15), 0.9), bevel=0.0, name="drip")
    geo.set_fx(drip, "slime")
    puddle = geo.cylinder(0.14, 0.012, f.at(u, 0.3, 0.0), mat.emitter((0.25, 0.9, 0.15), 0.9), 10, name="puddle")
    geo.set_fx(puddle, "slime")
    geo.set_block([drip, puddle], 0.0)


def _lagging_u(f, w, seed, plan):
    """The wall's face from segments: plan = [(share of the width, kind, paint)], kinds: w planks lying,
    h / v corrugated, p plate, t tyres, b concrete blocks, s sandbags."""
    r = geo.rng(seed)
    u = 0.0
    total = sum(p[0] for p in plan)
    for k, (share, kind, paint) in enumerate(plan):
        width = w * share / total
        top = TOP + r.uniform(-0.08, 0.06)
        if kind == "w":
            H.boards(f, u, u + width, 0.0, top, 0.0, seed + k, board=0.19, ragged=0.1, colours=(k % 5, (k + 2) % 5, 3), horizontal=True)
        elif kind in ("h", "v", "p"):
            H.sheet(f, u - 0.03, 0.0, width + 0.06, top, 0.012 * (k % 2), kind, paint, 0.6 + 0.1 * (k % 3), seed + k, roll=r.uniform(-2, 2),
                    streaks=0.7)
        elif kind == "t":
            n = max(1, int(round(width / 0.6)))
            for i in range(n):
                x, y, _ = f.at(u + width * (i + 0.5) / n, 0.02, 0.0)
                geo.tire_stack(3, (x, y, 0.0), seed=seed + k + i, radius=0.31, width=0.24)
                geo.cylinder(0.18, 0.72, (x, y, 0.0), _earth(seed + i), 10, name="fill")
        elif kind == "b":
            rows = 3
            n = max(1, int(round(width / 0.42)))
            for j in range(rows):
                for i in range(n if j % 2 == 0 else n - 1):
                    uu = u + width * (i + 0.5 + (0.5 if j % 2 else 0.0)) / n
                    geo.box((width / n - 0.02, 0.2, 0.26), f.at(uu, -0.02, j * 0.27), f.rot + r.uniform(-3, 3), mat.concrete(seed=float(seed + i + j)),
                            bevel=0.015, name="block")
        elif kind == "s":
            a, b = f.at(u, 0.0, 0.0), f.at(u + width, 0.0, 0.0)
            X.sandbags((a[0], a[1]), (b[0], b[1]), courses=4, z=0.0, seed=seed + k, size=(0.56, 0.32, 0.2))
        u += width
    return u


def _cap(f, u0, u1, seed, z=TOP):
    a, b = f.at(u0, -0.06, 0.0), f.at(u1, -0.06, 0.0)
    X.sandbags((a[0], a[1]), (b[0], b[1]), courses=1, z=z - 0.02, seed=seed, size=(0.56, 0.32, 0.17), block=0.0)


FOOT_U = H.uniq(H.hexes_in(-0.4, -0.45, 5 * HEX + 0.4, 0.05))


@piece("ht_terrace_u_a", title="Retaining Wall",
       desc="Planks, a car bonnet and roofing tin behind driven piles, holding back the upper ground. A drain weeps something that glows.",
       footprint=FOOT_U, **TERRACE)
def ht_terrace_u_a(ctx):
    x0, x1 = -0.36, 5 * HEX + 0.36
    w = x1 - x0
    f = H.face((x1, 0.06, 0.0), geo.U)
    _bank_u(x0, x1, 1)
    _lagging_u(f, w, 81, [(1.4, "w", None), (1.0, "p", H.RED), (1.2, "h", None), (0.9, "w", None), (0.9, "v", H.TEAL)])
    _piles(f, [0.1, 1.15, 2.05, 3.0, w - 0.1], 3)
    _cap(f, 0.2, 1.9, 5)
    _drain(f, 2.55, 0.36, 1)
    H.patch(f, 3.3, 0.3, 0.5, 0.36, 0.06, H.OCHRE, 0.65, 8, roll=6.0)
    # things lying on the upper ground: a plank, a tyre half buried, a stub of rail
    bx.plank((x0 + 2.4, -0.3, TOP + 0.08), (x0 + 3.9, -0.42, TOP + 0.04), 0.2, 0.04, H.wood(4, axis="X", width=0.6), name="plank")
    geo.tire((x0 + 0.9, -0.36, TOP - 0.1), radius=0.3, lying=False, rot=60.0, lean=20.0, seed=4)


@piece("ht_terrace_u_b", title="Retaining Wall",
       desc="Tyres packed with dirt, a row of concrete blocks, a road sign: anything that will hold the upper ground back.",
       footprint=FOOT_U, **TERRACE)
def ht_terrace_u_b(ctx):
    x0, x1 = -0.36, 5 * HEX + 0.36
    w = x1 - x0
    f = H.face((x1, 0.06, 0.0), geo.U)
    _bank_u(x0, x1, 2)
    _lagging_u(f, w, 91, [(1.2, "t", None), (1.0, "p", H.OCHRE), (1.3, "b", None), (1.0, "h", H.CREAM), (0.9, "s", None)])
    _piles(f, [1.2, 2.15, 3.45], 6)
    _cap(f, 2.3, 3.4, 7)
    _drain(f, 3.9, 0.3, 2)
    for k in range(3):
        H.streak(f, 1.45 + 0.25 * k, TOP - 0.1, 0.4, 0.07, 0.04)
    geo.barrel((x0 + 3.0, -0.38, TOP - 0.25), seed=5, tilt=70.0, rot=20.0, material=H.drum_paint(H.RED, 0.7, (0.3, 0.6), 2.0))


FOOT_STEPS = H.uniq(H.hexes_in(-0.4, -0.45, 3 * HEX + 0.4, 0.45))


@piece("ht_terrace_steps", title="Plank Steps",
       desc="Four plank steps down through the retaining wall, shored with sandbags. They are rotten; people go round.",
       footprint=FOOT_STEPS, **TERRACE)
def ht_terrace_steps(ctx):
    x0, x1 = -0.36, 3 * HEX + 0.36
    f = H.face((x1, 0.06, 0.0), geo.U)
    w = x1 - x0
    sw = 1.25                                                # the steps' width, in the middle
    u0 = (w - sw) / 2.0
    for ua, ub, seed in ((0.0, u0, 1), (u0 + sw, w, 2)):     # wall stubs with their banks either side
        xa, xb = x1 - ub, x1 - ua
        _bank_u(xa, xb, 3 + seed)
        H.boards(f, ua, ub, 0.0, TOP, 0.0, 100 + seed, board=0.2, ragged=0.08, colours=(seed, 3, 4), horizontal=True)
        _cap(f, ua + 0.02, ub - 0.02, 11 + seed)
    _piles(f, [u0 - 0.02, u0 + sw + 0.02], 9, top=TOP + 0.35)
    # treads from the wall's head down to the ground in front, cheeks of plank, earth showing between
    steps = 4
    for i in range(steps):
        z = TOP * (steps - i) / (steps + 0.0) - 0.04
        d = -0.32 + 0.24 * i
        a, b = f.at(u0 + 0.03, d, z), f.at(u0 + sw - 0.03, d, z)
        bx.plank(a, b, 0.26, 0.05, H.wood(i, axis="X", width=0.6), name="tread", roll=(-4.0 if i == 2 else 0.0))
        geo.box((sw - 0.06, 0.05, z), f.at(u0 + sw / 2.0, d + 0.1, 0.0), f.rot, _earth(i), bevel=0.0, name="riser")
    for u in (u0, u0 + sw):
        bx.plank(f.at(u, -0.4, TOP - 0.02), f.at(u, 0.55, 0.12), 0.24, 0.04, H.wood(3, axis="X", width=0.6), name="cheek", roll=90.0)
    a, b = f.at(u0 - 0.5, 0.42, 0.0), f.at(u0 - 0.02, 0.42, 0.0)
    X.sandbags((a[0], a[1]), (b[0], b[1]), courses=2, z=0.0, seed=4, block=0.0)


@piece("ht_terrace_end", title="Wall End",
       desc="Where the retaining wall stops: a pile driven deep, sandbags stacked against it, a tyre.",
       footprint=[(0, 0)], **TERRACE)
def ht_terrace_end(ctx):
    H.post(0.0, 0.05, 0.0, TOP + 0.4, "beam", 2, pad=False, lean=(0.02, 0.03))
    X.sandbags((0.3, 0.02), (-0.3, 0.02), courses=4, z=0.0, seed=6, size=(0.56, 0.34, 0.2), block=0.0)
    X.sandbags((0.2, -0.3), (-0.25, -0.3), courses=2, z=0.0, seed=8, size=(0.5, 0.32, 0.2), block=0.0)
    geo.tire((0.05, 0.38, 0.0), radius=0.3, lying=False, rot=geo.U + 90.0, lean=18.0, seed=3)
    H.dots([(0.0, 0.13, TOP + 0.2)], 0.07, H.tube(0.4, 7.0), name="bolt")
    H.streak(H.face((0.0, 0.14, 0.0), geo.U), 0.0, TOP + 0.18, 0.5, 0.06, 0.0)


FOOT_V = H.column(0, 5)


@piece("ht_terrace_v_a", title="Retaining Wall",
       desc="Roofing tin and planks behind driven piles, holding back the upper ground on the crater's flank.",
       footprint=FOOT_V, **TERRACE)
def ht_terrace_v_a(ctx):
    y0, y1 = -0.42, 5 * 0.8 + 0.42
    length = y1 - y0
    f = H.face((0.07, y0, 0.0), geo.V)
    _bank_v(y0, y1, 5)
    _lagging_u(f, length, 111, [(1.0, "v", H.SLATE), (1.3, "w", None), (0.9, "p", H.GREEN), (1.2, "h", None), (1.0, "w", None)])
    _piles(f, [0.1, 1.1, 2.3, 3.4, length - 0.1], 4)
    _cap(f, 1.2, 2.9, 9)
    _drain(f, 3.75, 0.34, 3)
    H.patch(f, 0.35, 0.28, 0.45, 0.34, 0.06, H.RED, 0.65, 12, roll=-5.0)
