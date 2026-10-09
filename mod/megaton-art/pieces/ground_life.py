# SPDX-License-Identifier: MIT
"""Signs of life (author "ground"): a market, animals, a fire to sit at, water, washing, children.

MARKET      gr_stall_food_u / _v     planks on drums, fruit and roots, dried meat on strings, a striped awning, a lit lantern
            gr_stall_parts_u / _v    a car bonnet for a counter, cogs and tins, hub caps on wires, a tin roof on angle iron
            gr_stall_water_u / _v    jugs and bottles under a patched beach umbrella, second-hand clothes on a rail
            Each is four hexes long: _u along a row (0..3, 0) with its front to +hy, _v along a column
            (0, 0..3) with its front to +hx. The counter blocks those four hexes; the awning hangs
            over the hexes in front (people walk under it).
PEN         gr_pen_u6 / gr_pen_v6    fence of whatever was to hand: boards, poles, a bedstead, a car door (6 hexes)
            gr_pen_u4 / gr_pen_v4    shorter run: pallets wired to posts (4 hexes)
            gr_pen_gate              a gate post with the gate hanging open (blocks only the post, (0, 0))
            gr_trough                a bath on blocks, full, with a tap that drips ((0,0), (1,0))
            gr_hay                   bales, a loose heap and a fork ((0,0), (1,0))
HEARTH      gr_cookfire              a ring of stones, a tripod and a pot, seats round it; a lamp at night.
                                     Blocks the fire (0,0) and the seats (2,0), (-2,0), (0,-2); the gaps stay open
WATER       gr_standpipe             a hand pump on a concrete pad, buckets, a puddle ((0,0))
WASHING     gr_laundry_v             a line between two posts down a column: posts on (0,0) and (0,5), walk under it
CHILDREN    gr_swing                 a pipe frame with a tyre swing and a plank swing: legs on (0,0) and (4,0)
            gr_toys                  a cart, a ball, a doll's pram: low, blocks nothing ((0,0))
            (the chalk marks are a floor decal: sheets/ground_decals.py, gr_chalk)
SLEEPERS    gr_bedrolls              a tarpaulin on two posts, bedding under it: posts (0,0), (4,0), bedding (1..3, -1)
"""
import math

from kit import piece, geo, mat, G
from kit import ground_extra as gx
from kit import bomb_extra as bx
from kit import signs_extra as sx
from kit.nodes import Graph

HU, HV = gx.HEX_U, gx.HEX_V


def umbrella_cloth(colours=((0.30, 0.06, 0.04), (0.36, 0.32, 0.22)), wedges=8, seed=0.0):
    """Beach-umbrella canvas: wedges of two colours round the pole, sun-rotted."""
    def build():
        g = Graph("gr_umbrella")
        x, y, _ = g.separate(g.coords())
        turn = g.fract(g.mul(g.div(g.math("ARCTAN2", y, x), 2.0 * math.pi), wedges / 2.0))
        base = g.mix(g.greater(turn, 0.5), colours[0], colours[1])
        stain = g.noise(mat._seeded(g, seed), scale=3.0, detail=3.0, roughness=0.7)
        base = g.mix(g.mul(g.smooth(stain, 0.5, 0.75), 0.6), base, mat.DIRT)
        g.principled(base=base, roughness=0.95, specular=0.05)
        return g.material
    return mat._cached(("gr_umbrella", colours, wedges, seed), build)


def counter(length, seed, kind="planks"):
    """Canonical counter along local x (0 .. length), 0.9 m high, its front at y = -0.3."""
    made = []
    if kind == "planks":
        for x, c in ((0.35, "oxide"), (length - 0.35, "blue")):
            made += gx.put(gx.drum(c, seed + int(x * 3), rust=0.55), (x, 0.0, 0.0))
        for k in range(3):
            made.append(geo.box((length + 0.1, 0.2, 0.045), (length / 2.0, -0.2 + 0.2 * k, 0.88), 0.0,
                                gx.wood(((0.27, 0.16, 0.07), (0.21, 0.14, 0.08), (0.30, 0.19, 0.09))[k], seed=seed + k, grey=0.3), bevel=0.006, name="counter_top",
                                roll=(0.5, -0.6, 0.3)[k]))
        made.append(sx.sag_sheet([(0.75, -0.31, 0.86), (length - 0.75, -0.31, 0.86), (length - 0.8, -0.33, 0.25), (0.8, -0.33, 0.2)], gx.canvas((0.22, 0.20, 0.13), seed=seed),
                                 sag=0.03, seed=seed, rows=4, columns=6))
    elif kind == "bonnet":
        made += gx.put(gx.crate((0.75, 0.6, 0.74), seed=seed, mark="yellow"), (0.45, 0.0, 0.0), rot=3.0)
        made += gx.put(gx.washer(seed + 1), (length - 0.42, 0.02, 0.0), rot=-4.0, scale=(1.0, 1.0, 0.86))
        made += gx.put(gx.bonnet("red", seed + 2, size=(length + 0.15, 0.95)), (length / 2.0, 0.0, 0.76))
    else:
        for x in (0.2, length - 0.2):
            for y in (-0.25, 0.25):
                made.append(bx.beam((x, y, 0.0), (x + (0.06 if x < 1 else -0.06), y, 0.86), (0.06, 0.06), gx.wood(seed=seed + x, grey=0.4), name="table_leg"))
        made.append(geo.box((length, 0.7, 0.045), (length / 2.0, 0.0, 0.86), 0.0, gx.paint("teal", rust=0.35, seed=seed, gloss=0.4), bevel=0.01, name="table_top"))
        made.append(bx.beam((0.2, -0.25, 0.3), (length - 0.2, -0.25, 0.45), (0.05, 0.05), gx.wood(seed=seed + 5, grey=0.4), name="table_brace"))
    return made


def frame_posts(length, seed, back=0.38, front=-1.05, high=2.35, low=2.0, kinds=("pole", "timber", "pipe", "pole"), feet=("stones", "none", "tyre", "none")):
    """Four posts and the two beams an awning hangs on. Returns (objects, corners) with corners =
    (back-left, back-right, front-right, front-left) tops as you face the stall."""
    made = []
    r = geo.rng(seed)
    tops = []
    for k, (x, y, h) in enumerate(((0.05, back, high), (length - 0.05, back, high), (length - 0.05, front, low), (0.05, front, low))):
        lean = (r.uniform(-0.06, 0.06), r.uniform(-0.04, 0.04))
        made += gx.post((x, y, 0.0), h + 0.12, kinds[k], seed + k, lean=lean, foot=feet[k], size=0.1)
        tops.append((x + lean[0], y + lean[1], h))
        made.append(gx.lash((x + lean[0] * 0.95, y + lean[1] * 0.95, h - 0.02), radius=0.07, height=0.12))
    made.append(gx.rail(tops[0], tops[1], "pole", seed + 5))
    made.append(gx.rail(tops[3], tops[2], "pole", seed + 6))
    return made, tops


def back_board(length, seed, z0=1.0, z1=1.9, paint=None):
    f = gx.Frame((0, 0.36, 0), 0.0)
    made = sx.plank_panel(f, 0.0, length, z0, z1, colours=((0.25, 0.15, 0.07), (0.20, 0.14, 0.08), (0.29, 0.19, 0.09)), paint=paint, seed=seed, ragged=0.08)
    return made, gx.Frame((0, 0.33, 0), 0.0)


def stall_food(length, seed):
    made = counter(length, seed, "planks")
    posts, tops = frame_posts(length, seed)
    made += posts
    made += gx.awning(tops, "patch", "red", ("cream", 0.3), seed=seed, sag=0.16)
    board, f = back_board(length, seed)
    made += board
    for k, kind in enumerate(("fruit", "roots", "fruit")):
        made += gx.put(gx.produce(seed + k, kind=kind, size=(0.62, 0.42)), (0.5 + k * (length - 1.0) / 2.0, -0.02, 0.905), rot=(-6.0, 4.0, 9.0)[k], tilt=-10.0)
    made += gx.put(gx.bottle_row(6, seed=seed), (length * 0.5, 0.26, 0.905))
    # dried meat, a pot and a lit lantern on the front beam
    a, b = tops[3], tops[2]
    for k, what in enumerate(("meat", "meat", "pot", "meat")):
        t = 0.2 + 0.2 * k
        made += gx.hang((a[0] + (b[0] - a[0]) * t, a[1] + 0.02, a[2] - 0.04), what, seed=seed + k, drop=0.22 + 0.06 * (k % 2))
    # (on the FRONT beam: under the back one the awning hid it from the camera in the _u stall)
    made += sx.lantern((a[0] + (b[0] - a[0]) * 0.9, a[1] - 0.04, a[2] - 0.02), size=1.15, lit=True, strength=2.6, fx="fire")
    # the price board: chalk scrawl you cannot quite read
    made.append(geo.box((0.6, 0.02, 0.42), f.at(length * 0.24, 0.0, 1.3), 0.0, gx.dark(0.03), bevel=0.0, name="slate", roll=-4.0))
    for i in range(3):
        made.append(geo.box((0.4 - 0.08 * i, 0.008, 0.035), f.at(length * 0.24 - 0.04 * i, 0.02, 1.58 - 0.1 * i), 0.0, mat.flat((0.50, 0.50, 0.46)), bevel=0.0, name="chalk",
                            roll=-4.0))
    made += gx.put(gx.sack(seed + 9), (length * 0.5, -0.75, 0.0), rot=10.0)
    made += gx.put(gx.crate((0.55, 0.45, 0.35), seed=seed + 10, lid=False), (length - 0.6, -0.72, 0.0), rot=-12.0)
    made += gx.put(gx.produce(seed + 11, kind="roots", size=(0.45, 0.35)), (length - 0.6, -0.72, 0.3), rot=-12.0)
    return made


def stall_parts(length, seed):
    made = counter(length, seed, "bonnet")
    posts, tops = frame_posts(length, seed, kinds=("angle", "angle", "pipe", "angle"), feet=("none", "drum", "none", "tyre"), high=2.45, low=2.1)
    made += posts
    # roof: three tin sheets falling to the front
    depth = tops[0][1] - tops[3][1] + 0.35
    slope = math.degrees(math.atan2(tops[0][2] - tops[3][2], depth))
    w = (length + 0.3) / 3.0
    for k in range(3):
        made.append(gx.tin_sheet(w + 0.06, depth + (0.0, 0.14, -0.1)[k], (-0.15 + k * w, tops[0][1] + 0.15, tops[0][2] + 0.08 + 0.015 * (k % 2)), 0.0, slope + (1.5, -1.0, 2.0)[k],
                                 (None, "teal", None)[k], seed + k, rust=0.45 + 0.15 * k))
    board, f = back_board(length, seed, paint=(0.10, 0.16, 0.17))
    made += board
    made += gx.put(gx.produce(seed, kind="parts", size=(0.6, 0.4)), (0.55, 0.02, 0.9), rot=5.0)
    made += gx.put(gx.produce(seed + 1, kind="tins", size=(0.6, 0.3)), (length * 0.52, 0.12, 0.9), rot=-4.0)
    made += gx.put(gx.tv(seed + 2), (length - 0.5, 0.05, 0.88), rot=-12.0, scale=0.85)
    a, b = tops[3], tops[2]
    for k, what in enumerate(("hubcap", "lamp", "hubcap", "pan", "bottle")):
        t = 0.14 + 0.18 * k
        made += gx.hang((a[0] + (b[0] - a[0]) * t, a[1] + 0.02, a[2] - 0.05), what, seed=seed + k, drop=0.2 + 0.08 * (k % 2))
    made += gx.put(gx.road_sign("arrow", seed + 3, post=0.8, bent=0.0, size=0.6), f.at(length * 0.36, 0.05, 1.0), rot=0.0)
    made += gx.put(gx.car_door("teal", seed + 4, glass="none"), (0.2, -0.7, 0.0), rot=-70.0, tilt=-14.0)
    made += gx.put(gx.wheel(seed + 5, hub="cream"), (length - 0.35, -0.75, 0.0), rot=12.0, tilt=-12.0)
    made += gx.put(gx.jerrycan("olive", seed + 6), (length * 0.55, -0.72, 0.0), rot=25.0)
    return made


def stall_water(length, seed):
    made = counter(length * 0.6, seed, "table")
    # the umbrella over the table: a pole in a drum of concrete, eight ribs
    px, py = length * 0.3, 0.3
    made += gx.post((px, py, 0.0), 2.5, "pipe", seed, foot="drum", lean=(0.06, -0.12))
    top = (px + 0.06, py - 0.12, 2.42)
    made.append(geo.lathe([(1.25, 0.0), (1.22, 0.03), (0.6, 0.28), (0.04, 0.42), (0.0, 0.42)], (top[0], top[1], top[2] - 0.38), umbrella_cloth(seed=seed), 16, name="umbrella",
                          tilt=10.0, roll=-5.0))
    # jugs, a demijohn, bottles, buckets
    made += gx.put(gx.bottle_row(6, colours=((0.16, 0.24, 0.22), (0.05, 0.14, 0.05), (0.22, 0.24, 0.22)), seed=seed, height=0.3), (length * 0.3, 0.12, 0.905))
    made.append(geo.lathe([(0.1, 0.0), (0.17, 0.08), (0.17, 0.24), (0.05, 0.36), (0.05, 0.42), (0.0, 0.42)], (length * 0.12, -0.08, 0.905), mat.flat((0.10, 0.20, 0.17), roughness=0.1), 12,
                          name="demijohn"))
    made += gx.put(gx.bucket("zinc", seed + 1, full=True), (length * 0.48, -0.12, 0.905))
    made += gx.put(gx.keg(seed + 2), (length * 0.52, -0.75, 0.0))
    made += gx.put(gx.bucket("blue", seed + 3, full=True), (0.25, -0.7, 0.0))
    made += gx.put(gx.jerrycan("blue", seed + 4), (0.75, -0.8, 0.0), rot=20.0)
    # the clothes rail: two posts, a pole, things on it
    x0, x1 = length * 0.66, length - 0.05
    for x in (x0, x1):
        made += gx.post((x, 0.2, 0.0), 1.95, "pole", seed + int(x * 5), foot="stones" if x == x1 else "none", lean=(0.0, 0.03))
    made.append(gx.rail((x0 - 0.1, 0.2, 1.85), (x1 + 0.12, 0.22, 1.8), "pole", seed + 7))
    f = gx.Frame((0, 0.18, 0), 0.0)
    cloths = [((0.30, 0.10, 0.07), 0.42, 0.75, 0.0), ((0.12, 0.17, 0.22), 0.36, 0.95, 0.25), ((0.36, 0.33, 0.24), 0.4, 0.6, 0.0), ((0.14, 0.18, 0.10), 0.34, 0.85, 0.2)]
    for k, (c, w, h, taper) in enumerate(cloths):
        made.append(sx.cloth(f, x0 + 0.1 + (x1 - x0 - 0.2) * k / 3.0, 1.8, w, h, sx.fabric(c, seed=seed + k), seed=seed + k, taper=taper))
    made += gx.put(gx.crate((0.6, 0.5, 0.4), seed=seed + 8, lid=False), (length - 0.5, -0.45, 0.0), rot=8.0)
    made.append(geo.box((0.5, 0.4, 0.2), (length - 0.5, -0.45, 0.32), 14.0, sx.fabric((0.30, 0.22, 0.12), seed=seed), bevel=0.06, name="folded"))
    made.append(gx.stain((0.6, -0.55), 0.45, (0.045, 0.035, 0.025), seed=seed))
    return made


def place_u(objects):
    return gx.put(objects, (3.5 * HU + 0.02, -0.12, 0.0), rot=geo.U)


def place_v(objects):
    return gx.put(objects, (-0.12, -HV / 2.0 + 0.05, 0.0), rot=geo.V)


STALL = dict(shadow="flat", material="wood")
U4, V4 = gx.row_hexes(0, 3), gx.col_hexes(0, 3)


@piece("gr_stall_food_u", title="Food Stall", desc="Fruit that grew somewhere, roots that grew here, and iguana drying on strings. The lantern is lit all day.",
       footprint=U4, see_through="u", light=(4, 80), light_hex=(1, 0), **STALL)
def gr_stall_food_u(ctx):
    place_u(stall_food(4 * HU - 0.06, 401))


@piece("gr_stall_food_v", title="Food Stall", desc="Fruit that grew somewhere, roots that grew here, and iguana drying on strings. The lantern is lit all day.",
       footprint=V4, see_through="v", light=(4, 80), light_hex=(0, 2), **STALL)
def gr_stall_food_v(ctx):
    place_v(stall_food(4 * HV - 0.1, 405))


@piece("gr_stall_parts_u", title="Parts Stall", desc="A car bonnet for a counter. Cogs, tins, a television, hub caps turning on their wires. Everything works, he says.",
       footprint=U4, see_through="u", **STALL)
def gr_stall_parts_u(ctx):
    place_u(stall_parts(4 * HU - 0.06, 411))


@piece("gr_stall_parts_v", title="Parts Stall", desc="A car bonnet for a counter. Cogs, tins, a television, hub caps turning on their wires. Everything works, he says.",
       footprint=V4, see_through="v", **STALL)
def gr_stall_parts_v(ctx):
    place_v(stall_parts(4 * HV - 0.1, 415))


@piece("gr_stall_water_u", title="Water Seller", desc="Water by the bottle, the jug and the bucket under a beach umbrella, and somebody's wardrobe for sale beside it.",
       footprint=U4, see_through="u", **STALL)
def gr_stall_water_u(ctx):
    place_u(stall_water(4 * HU - 0.06, 421))


@piece("gr_stall_water_v", title="Water Seller", desc="Water by the bottle, the jug and the bucket under a beach umbrella, and somebody's wardrobe for sale beside it.",
       footprint=V4, see_through="v", **STALL)
def gr_stall_water_v(ctx):
    place_v(stall_water(4 * HV - 0.1, 425))


# -------------------------------------------------------------------------------- pen
def fence(length, post_at, seed, infill):
    """Canonical fence along local x: posts at the given x, three rails, and one odd panel
    (infill = [(kind, x), ...]: "bedstead", "door", "pallet", "tin")."""
    r = geo.rng(seed)
    made = []
    kinds = ("timber", "pole", "angle", "pole", "timber", "pipe")
    for k, x in enumerate(post_at):
        h = r.uniform(1.15, 1.45)
        made += gx.post((x, 0.0, 0.0), h, kinds[(k + seed) % len(kinds)], seed + k, lean=(r.uniform(-0.05, 0.05), r.uniform(-0.04, 0.04)), size=0.1)
    spans = list(zip(post_at, post_at[1:]))
    for k, (a, b) in enumerate(spans):
        for level, z in enumerate((0.32, 0.68, 1.02)):
            if r.random() < 0.18:
                continue
            kind = r.choice(["board", "board", "pole", "pipe"])
            made.append(gx.rail((a - 0.08, -0.06, z + r.uniform(-0.05, 0.05)), (b + 0.08, -0.06, z + r.uniform(-0.05, 0.05)), kind, seed + k * 3 + level))
        made.append(gx.lash((b, -0.03, 0.66), radius=0.075, height=0.1))
    for kind, x in infill:
        if kind == "bedstead":
            made += gx.put(gx.bedstead(seed, width=1.0, height=1.15), (x, -0.1, 0.0), tilt=-4.0)
        elif kind == "door":
            made += gx.put(gx.car_door("oxide", seed + 1, rear=True), (x - 0.5, -0.11, 0.02), tilt=-3.0)
        elif kind == "pallet":
            made += gx.put(gx.pallet(seed + 2, broken=True), (x, -0.1, 0.62), tilt=-88.0)
        else:
            made.append(geo.corrugated_panel(0.95, 1.1, (x - 0.47, -0.1, 0.0), 0.0, gx.tin(None, rust=0.6, seed=seed + 3, top=1.1), wavelength=0.13, roll=2.0, name="fence_tin"))
    return made


PEN = dict(shadow="flat", material="wood", see_through=True)


@piece("gr_pen_u6", title="Pen Fence", desc="A fence of boards, poles and one iron bedstead, lashed with wire. The brahmin lean on it and it holds.",
       footprint=gx.row_hexes(0, 5), **PEN)
def gr_pen_u6(ctx):
    L = 6 * HU
    posts = [(6 - 0.5 - d) * HU for d in (5, 4, 2, 0)]
    gx.put(fence(L, posts, 431, [("bedstead", posts[1] + 0.7), ("tin", posts[2] + 0.75)]), (5.5 * HU, 0.0, 0.0), rot=geo.U)


@piece("gr_pen_v6", title="Pen Fence", desc="A fence of boards, poles and a car door, lashed with wire. Something has chewed the top rail.",
       footprint=gx.col_hexes(0, 5), **PEN)
def gr_pen_v6(ctx):
    posts = [(d + 0.5) * HV for d in (0, 2, 4, 5)]
    gx.put(fence(6 * HV, posts, 435, [("door", posts[0] + 0.8), ("pallet", posts[1] + 0.8)]), (0.0, -HV / 2.0, 0.0), rot=geo.V)


@piece("gr_pen_u4", title="Pen Fence", desc="Pallets wired to posts. Cheap, and a brahmin cannot see through them, which calms it.",
       footprint=gx.row_hexes(0, 3), **PEN)
def gr_pen_u4(ctx):
    posts = [(4 - 0.5 - d) * HU for d in (3, 2, 0)]
    gx.put(fence(4 * HU, posts, 441, [("pallet", posts[1] + 0.7), ("pallet", posts[0] + 0.3)]), (3.5 * HU, 0.0, 0.0), rot=geo.U)


@piece("gr_pen_v4", title="Pen Fence", desc="A length of pen fence: boards, a sheet of tin, wire.",
       footprint=gx.col_hexes(0, 3), **PEN)
def gr_pen_v4(ctx):
    posts = [(d + 0.5) * HV for d in (0, 2, 3)]
    gx.put(fence(4 * HV, posts, 445, [("tin", posts[0] + 0.8)]), (0.0, -HV / 2.0, 0.0), rot=geo.V)


@piece("gr_pen_gate", title="Pen Gate", desc="A gate of pipe and wire mesh on a post, hanging open. The loop of chain that shuts it is on the ground.",
       footprint=[(0, 0)], **PEN)
def gr_pen_gate(ctx):
    gx.post((0, 0, 0), 1.6, "timber", 451, size=0.14, foot="stones")
    steel = mat.steel(rust=0.75, seed=3)
    leaf = [gx.rod((0.1, 0, 0.2), (1.25, 0, 0.2), 0.03, steel, 8), gx.rod((0.1, 0, 1.15), (1.25, 0, 1.15), 0.03, steel, 8), gx.rod((0.1, 0, 0.2), (0.1, 0, 1.15), 0.03, steel, 8),
            gx.rod((1.25, 0, 0.2), (1.25, 0, 1.15), 0.03, steel, 8), gx.rod((0.1, 0, 0.2), (1.25, 0, 1.15), 0.024, steel, 8)]
    leaf.append(gx.quad([(0.1, 0, 0.2), (1.25, 0, 0.2), (1.25, 0, 1.15), (0.1, 0, 1.15)], gx.wire("xz", 0.14, 0.3), "gate_mesh"))
    gx.put(leaf, (0.0, 0.0, 0.0), rot=118.0, roll=-3.0, block=0)
    geo.cable((0.0, 0.1, 1.2), (0.25, 0.5, 0.02), sag=0.2, radius=0.022, material=mat.flat((0.06, 0.055, 0.05), metallic=0.5, roughness=0.5))


@piece("gr_trough", title="Water Trough", desc="A cast-iron bath on cinder blocks, filled from a tap that nobody can quite turn off. The brahmin do not mind the taste.",
       footprint=[(0, 0), (1, 0)], shadow="flat")
def gr_trough(ctx):
    cx, cy = HU / 2.0, -0.2
    for dx in (-0.5, 0.5):
        gx.put(gx.cinder(461), (cx + dx, cy, 0.0), rot=90.0)
    gx.put(gx.bathtub(462, feet=False), (cx, cy, 0.2), rot=geo.U + 4.0)
    surface = [(cx + 0.66 * math.copysign(abs(math.cos(a)) ** 0.6, math.cos(a)), cy + 0.29 * math.copysign(abs(math.sin(a)) ** 0.75, math.sin(a)), 0.63)
               for a in [2.0 * math.pi * i / 20 for i in range(20)]]
    gx.quad(surface, gx.water((0.05, 0.10, 0.07)), "trough_water")
    gx.rod((cx - 0.85, cy - 0.1, 0.0), (cx - 0.85, cy - 0.1, 1.05), 0.04, gx.pipe_paint("grey", 3), 8, name="tap_riser")
    geo.pipe([(cx - 0.85, cy - 0.1, 1.0), (cx - 0.8, cy - 0.05, 1.1), (cx - 0.6, cy, 1.08), (cx - 0.58, cy, 0.95)], 0.035, gx.pipe_paint("grey", 4), name="tap_spout")
    gx.put(gx.handwheel(0.1, "red", 5), (cx - 0.85, cy - 0.16, 1.02), block=0)
    geo.box((0.025, 0.025, 0.32), (cx - 0.58, cy, 0.63), 0.0, mat.flat((0.34, 0.40, 0.40), roughness=0.15), bevel=0.0, name="drip")
    gx.stain((cx - 0.3, cy + 0.55), 0.55, (0.045, 0.036, 0.026), seed=3)
    gx.stain((cx - 0.75, cy + 0.3), 0.3, (0.03, 0.045, 0.03), seed=4, gloss=0.7)
    gx.put(gx.bucket("zinc", 463), (cx + 0.75, cy + 0.6, 0.0), block=0)


@piece("gr_hay", title="Hay", desc="Three bales and a heap forked loose for the evening feed. It is mostly thistle.",
       footprint=[(0, 0), (1, 0)], shadow="flat", material="dirt")
def gr_hay(ctx):
    gx.put(gx.bale(471), (0.1, -0.15, 0.0), rot=geo.U + 6.0)
    gx.put(gx.bale(472), (0.75, -0.3, 0.0), rot=geo.U - 10.0)
    gx.put(gx.bale(473), (0.4, -0.22, 0.43), rot=geo.U + 22.0)

    def h(x, y):
        d = ((x - 0.55) / 0.75) ** 2 + ((y - 0.55) / 0.5) ** 2
        return None if d >= 1.0 else 0.3 * (1.0 - d) ** 0.7 * (0.8 + 0.3 * bx.fbm(x * 3.0, y * 3.0, 4)) + 0.004
    gx.no_block(bx.heightfield(-0.3, 1.4, 0.0, 1.1, h, gx.straw(5), step=0.07, name="loose_hay"))
    gx.rod((1.05, 0.25, 0.0), (1.2, -0.05, 1.4), 0.022, gx.wood(seed=6, grey=0.5), 6, name="fork_shaft")
    for dx in (-0.06, 0.0, 0.06):
        gx.rod((1.05 + dx, 0.25, 0.02), (1.03 + dx, 0.31, 0.3), 0.012, mat.steel(rust=0.6, seed=7), 6, name="fork_tine")


# ----------------------------------------------------------------------------- hearth
@piece("gr_cookfire", title="Cooking Fire", desc="The fire everybody on this side of town cooks on: a ring of stones, a pot on a tripod, and whatever there is to sit on.",
       footprint=[(0, 0), (2, 0), (-2, 0), (0, -2)], shadow="flat", material="stone", light=(5, 85))
def gr_cookfire(ctx):
    r = ctx.rng
    # ash bed, stones, logs, fire
    gx.stain((0.0, 0.0), 0.62, (0.035, 0.032, 0.03), seed=1, squash=0.9, gloss=0.0)
    for k in range(9):
        a = 2.0 * math.pi * k / 9 + r.uniform(-0.15, 0.15)
        geo.box((r.uniform(0.18, 0.28), r.uniform(0.15, 0.22), r.uniform(0.1, 0.17)), (0.42 * math.cos(a), 0.4 * math.sin(a), 0.0), math.degrees(a) + r.uniform(-20, 20),
                mat.concrete((0.20, 0.185, 0.165), cracks=0.1, seed=k), bevel=0.05, name="hearth_stone")
    for k in range(4):
        a = k * 0.9 + 0.3
        gx.rod((0.3 * math.cos(a), 0.3 * math.sin(a), 0.05), (-0.25 * math.cos(a), -0.25 * math.sin(a), 0.14), 0.045, mat.flat((0.03, 0.022, 0.018), roughness=0.9), 6, name="log")
    sx.flames((0.0, 0.0, 0.08), radius=0.24, height=0.5, count=8, seed=3)
    geo.cylinder(0.2, 0.03, (0.0, 0.0, 0.07), mat.emitter((1.0, 0.3, 0.02), 2.0), 10, name="embers")
    # tripod and pot
    apex = (0.0, 0.0, 1.55)
    for k in range(3):
        a = 2.0 * math.pi * k / 3 + 0.5
        gx.rod((0.62 * math.cos(a), 0.55 * math.sin(a), 0.0), apex, 0.028, mat.steel(rust=0.8, seed=k), 6, name="tripod")
    gx.lash((0.0, 0.0, 1.5), radius=0.05, height=0.1, colour=(0.05, 0.045, 0.04))
    geo.pipe([(0.0, 0.0, 1.48), (0.0, 0.0, 0.95)], 0.014, mat.flat((0.05, 0.045, 0.04)), name="pot_chain")
    geo.lathe([(0.0, 0.0), (0.17, 0.0), (0.21, 0.1), (0.2, 0.24), (0.22, 0.25), (0.18, 0.25), (0.17, 0.04), (0.0, 0.04)], (0.0, 0.0, 0.68), gx.iron(0.35, 4), 14, name="pot")
    geo.cylinder(0.17, 0.01, (0.0, 0.0, 0.88), mat.flat((0.16, 0.09, 0.04), roughness=0.3), 12, name="stew")
    # seats: a car seat behind the fire, a stump each side, firewood and a crate towards the viewer (low)
    gx.put(gx.car_seat(5), (0.0, -1.55, 0.0), rot=geo.U + 4.0)
    for hx_, seed in ((2, 6), (-2, 7)):
        x, y = G.hex_xy(hx_, 0)
        geo.cylinder(0.27, 0.42, (x, y, 0.0), gx.wood((0.24, 0.16, 0.09), seed=seed, axis="Z", width=0.5, grey=0.5), 12, name="stump")
        geo.cylinder(0.24, 0.012, (x, y, 0.42), gx.wood((0.33, 0.24, 0.13), seed=seed + 2, axis="X", width=0.12, grey=0.2), 12, name="stump_top")
    gx.put(gx.keg(8), (G.hex_xy(2, 0)[0] + 0.1, -0.62, 0.0), block=0)
    for k in range(5):
        gx.no_block(gx.rod((-0.9 + 0.13 * k, 1.05 + 0.03 * (k % 2), 0.06 + 0.1 * (k // 3)), (-0.3 + 0.13 * k, 1.2, 0.06 + 0.1 * (k // 3)), 0.055,
                           gx.wood((0.22, 0.14, 0.08), seed=10 + k, axis="Z", width=0.5, grey=0.4), 6, name="firewood"))
    gx.put(gx.produce(11, kind="tins", size=(0.4, 0.25)), (0.75, 1.0, 0.0), rot=20.0)
    gx.put(gx.bucket("zinc", 12, full=True), (1.1, 0.65, 0.0), block=0)
    geo.halo((0.0, 0.0, 0.0), radius=2.1, strength=0.6)


# ------------------------------------------------------------------------------ water
@piece("gr_standpipe", title="Standpipe", desc="The town's tap: a hand pump on a pad of concrete, with the buckets of whoever is next. The water is clean. Walter says so.",
       footprint=[(0, 0)], shadow="flat")
def gr_standpipe(ctx):
    geo.box((1.15, 1.05, 0.09), (0.05, 0.05, 0.0), 12.0, mat.concrete(seed=3), bevel=0.02, name="pad")
    gx.no_block(geo.box((0.34, 0.34, 0.012), (0.2, 0.35, 0.09), 12.0, gx.iron(0.7, 2), bevel=0.0, name="drain"))
    # the pump: cast body, spout to the front, a long handle, the riser it stands on
    blue = gx.paint("blue", rust=0.45, seed=5, lines=(0.9, 1.25), reach=0.35)
    geo.lathe([(0.09, 0.0), (0.09, 0.62), (0.13, 0.7), (0.13, 1.18), (0.1, 1.26), (0.05, 1.3), (0.0, 1.3)], (0.0, 0.0, 0.09), blue, 14, name="pump_body")
    geo.pipe([(0.0, -0.1, 1.0), (0.05, 0.25, 1.02), (0.07, 0.36, 0.9)], 0.045, blue, name="pump_spout")
    gx.rod((-0.02, -0.05, 1.3), (-0.3, -0.75, 1.75), 0.024, mat.steel(rust=0.4, seed=4), 8, name="pump_handle")
    gx.rod((0.0, 0.0, 1.3), (-0.02, -0.05, 1.42), 0.03, mat.steel(rust=0.5, seed=5), 6, name="pump_link")
    geo.box((0.03, 0.03, 0.5), (0.07, 0.36, 0.38), 0.0, mat.flat((0.34, 0.40, 0.40), roughness=0.15), bevel=0.0, name="water")
    gx.put(gx.bucket("zinc", 6, full=True), (0.08, 0.4, 0.09), block=0)
    gx.put(gx.bucket("oxide", 7), (-0.65, 0.5, 0.0), block=0)
    gx.put(gx.bucket("zinc", 8), (-0.8, 0.15, 0.0), tilt=85.0, rot=60.0, block=0)
    gx.put(gx.jerrycan("blue", 9), (0.75, 0.3, 0.0), rot=geo.U + 20.0, block=0)
    # the feed: a thinner pipe out of the ground behind it, with a stop valve
    geo.pipe([(0.0, -0.2, 0.3), (0.0, -0.45, 0.3), (0.0, -0.5, 0.0)], 0.05, gx.pipe_paint("oxide", 10), name="feed")
    gx.put(gx.handwheel(0.12, "red", 11), (0.0, -0.36, 0.42), tilt=90.0)
    gx.stain((0.25, 0.75), 0.6, (0.045, 0.036, 0.026), seed=5)
    gx.stain((0.45, 0.85), 0.28, (0.02, 0.03, 0.03), seed=6, gloss=0.9)


# ---------------------------------------------------------------------------- washing
@piece("gr_laundry_v", title="Washing Line", desc="A line of washing between two posts. The sheet has been a tent, a sail and a shroud, and is a sheet again.",
       footprint=[(0, 0), (0, 5)], shadow="flat", material="wood", see_through="v")
def gr_laundry_v(ctx):
    y1 = 5 * HV
    gx.post((0, 0, 0), 2.2, "pole", 481, foot="stones", lean=(0.0, -0.06))
    gx.post((0, y1, 0), 2.1, "timber", 482, foot="tyre", lean=(0.02, 0.05), size=0.1)
    geo.box((0.9, 0.07, 0.07), (0.0, -0.06, 2.1), 0.0, gx.wood(seed=3, grey=0.4), bevel=0.006, name="cross_arm")
    geo.box((0.9, 0.07, 0.07), (0.02, y1 + 0.05, 2.0), 0.0, gx.wood(seed=4, grey=0.4), bevel=0.006, name="cross_arm")
    rope = mat.flat((0.26, 0.21, 0.13), roughness=0.9)
    lines = []
    for dx, sag in ((-0.38, 0.22), (0.38, 0.3)):
        a, b = (dx, -0.06, 2.14), (dx + 0.02, y1 + 0.05, 2.04)
        geo.cable(a, b, sag=sag, radius=0.018, material=rope, count=20)
        lines.append((a, b, sag))
    things = [(0, 0.16, (0.34, 0.31, 0.23), 0.9, 1.05, 0.0), (0, 0.42, (0.12, 0.17, 0.22), 0.4, 0.8, 0.25), (0, 0.58, (0.28, 0.09, 0.06), 0.45, 0.55, 0.0),
              (0, 0.8, (0.30, 0.26, 0.16), 0.5, 0.6, 0.0), (1, 0.22, (0.13, 0.17, 0.10), 0.42, 0.85, 0.3), (1, 0.45, (0.36, 0.34, 0.28), 0.4, 0.5, 0.0),
              (1, 0.72, (0.20, 0.10, 0.12), 0.75, 0.7, 0.0)]
    for k, (which, t, colour, w, h, taper) in enumerate(things):
        a, b, sag = lines[which]
        x = a[0] + (b[0] - a[0]) * t
        y = a[1] + (b[1] - a[1]) * t
        z = a[2] + (b[2] - a[2]) * t - sag * 4.0 * t * (1.0 - t)
        f = gx.Frame((x, y, 0.0), geo.V)
        sx.cloth(f, 0.0, z, w, h, sx.fabric(colour, stripes=((0.14, 0.16, 0.2), 0.08) if k == 0 else None, seed=490 + k), seed=k, taper=taper, sway=0.06 * (k % 3))
    gx.put(gx.bucket("zinc", 498), (0.5, 1.0, 0.0), block=0)
    gx.no_block(geo.box((0.62, 0.45, 0.24), (0.55, 1.75, 0.0), 20.0, sx.fabric((0.30, 0.20, 0.10), seed=5), bevel=0.05, name="basket"))


# --------------------------------------------------------------------------- children
@piece("gr_swing", title="Swing", desc="A frame of old gas pipe with a tyre on chains and a plank on ropes. The plank is the one they fight over.",
       footprint=[(0, 0), (4, 0)], shadow="flat", see_through="u")
def gr_swing(ctx):
    x1 = 4 * HU
    steel = gx.pipe_paint("oxide", 501)
    top = 2.35
    for x in (0.0, x1):
        for side in (-1.0, 1.0):
            gx.rod((x, side * 0.7, 0.0), (x, 0.0, top), 0.05, steel, 10, name="swing_leg")
        gx.no_block(gx.rod((x, -0.4, 1.0), (x, 0.4, 1.0), 0.03, steel, 8, name="swing_tie"))
    gx.no_block(gx.rod((-0.2, 0.0, top), (x1 + 0.2, 0.0, top), 0.055, gx.pipe_paint("green", 502), 10, name="swing_bar"))
    chain = mat.flat((0.06, 0.055, 0.05), metallic=0.5, roughness=0.5)
    # the tyre, hung upright on two chains, pushed a little off plumb
    tx = x1 * 0.3
    for dx in (-0.2, 0.2):
        geo.pipe([(tx + dx * 0.4, 0.0, top), (tx + dx, 0.12, 1.02)], 0.018, chain, name="swing_chain")
    gx.put([geo.tire((0, 0, 0), radius=0.36, lying=True, seed=5)], (tx, 0.02, 0.76), rot=geo.U, tilt=97.0, block=0)
    # the plank seat on ropes
    px = x1 * 0.7
    rope = mat.flat((0.26, 0.21, 0.13), roughness=0.9)
    for dx in (-0.24, 0.24):
        geo.pipe([(px + dx, 0.0, top), (px + dx, -0.1, 0.5)], 0.018, rope, name="swing_rope")
    gx.no_block(geo.box((0.6, 0.2, 0.04), (px, -0.1, 0.47), 0.0, gx.wood(seed=6, grey=0.3), bevel=0.006, name="swing_seat", tilt=6.0))
    gx.stain((tx, 0.1), 0.45, (0.10, 0.08, 0.055), seed=7, gloss=0.0)
    gx.stain((px, 0.0), 0.45, (0.10, 0.08, 0.055), seed=8, gloss=0.0)


@piece("gr_toys", title="Toys", desc="A cart made from a crate and four tin lids, a ball that has lost its bounce, a doll with one arm.",
       footprint=[], anchors=[(0, 0)], shadow="baked", material="wood")
def gr_toys(ctx):
    red = gx.paint("red", rust=0.3, seed=511, gloss=0.5)
    made = [geo.box((0.55, 0.3, 0.14), (0, 0, 0.09), 20.0, red, bevel=0.01, name="cart")]
    made.append(geo.box((0.5, 0.25, 0.01), (0, 0, 0.225), 20.0, gx.dark(0.03), bevel=0.0, name="cart_inside"))
    for dx, dy in ((-0.2, -0.17), (0.2, -0.17), (-0.2, 0.17), (0.2, 0.17)):
        a = math.radians(20.0)
        made.append(geo.cylinder(0.075, 0.03, (dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a), 0.075), gx.chrome(0.5), 8, name="cart_wheel",
                                 tilt=90.0, rot=20.0))
    made.append(geo.pipe([(0.25, 0.1, 0.12), (0.7, 0.3, 0.02)], 0.014, mat.flat((0.26, 0.21, 0.13)), name="cart_string"))
    made.append(sx.sphere(0.13, (-0.55, 0.35, 0.13), mat.flat((0.34, 0.20, 0.05), roughness=0.5), name="ball"))
    made.append(geo.box((0.12, 0.3, 0.07), (0.45, -0.3, 0.0), -30.0, sx.fabric((0.36, 0.30, 0.22), seed=3), bevel=0.03, name="doll"))
    made.append(sx.sphere(0.055, (0.53, -0.44, 0.06), mat.flat((0.40, 0.28, 0.18)), name="doll_head"))
    gx.no_block(made)


# --------------------------------------------------------------------------- sleepers
@piece("gr_bedrolls", title="Sleeping Place", desc="A tarpaulin on two poles, pegged down at the back. Two bedrolls, a mattress, a lantern: somebody's whole house.",
       footprint=[(0, 0), (4, 0), (1, -1), (2, -1), (3, -1)], shadow="flat", material="leather", see_through="u")
def gr_bedrolls(ctx):
    x1 = 4 * HU
    gx.post((0, 0, 0), 1.75, "pole", 521, foot="stones", lean=(-0.05, 0.03))
    gx.post((x1, 0, 0), 1.65, "pipe", 522, foot="tyre", lean=(0.04, 0.02))
    back = -1.75
    corners = [(x1 + 0.25, back, 0.22), (-0.25, back, 0.18), (-0.08, 0.05, 1.66), (x1 + 0.06, 0.04, 1.58)]
    gx.awning(corners, "patch", (0.14, 0.18, 0.11), None, seed=5, sag=0.2)
    for x in (-0.25, x1 * 0.5, x1 + 0.25):
        gx.no_block(gx.rod((x, back - 0.12, 0.0), (x, back + 0.02, 0.3), 0.025, gx.wood(seed=6, grey=0.4), 6, name="peg"))
    for x, top in ((-0.08, 1.66), (x1 + 0.06, 1.58)):
        geo.cable((x, 0.05, top), (x + (0.35 if x > 1 else -0.35), 0.9, 0.0), sag=0.0, radius=0.016, material=mat.flat((0.26, 0.21, 0.13), roughness=0.9))
    gx.put(gx.mattress(523), (x1 * 0.42, -0.8, 0.0), rot=geo.U + 6.0)
    gx.put(gx.bedroll(524, colour=(0.30, 0.10, 0.07)), (x1 * 0.2, -0.85, 0.16), rot=geo.V + 10.0)
    gx.put(gx.bedroll(525), (x1 * 0.82, -1.0, 0.0), rot=geo.U + 20.0)
    gx.put(gx.sack(526, colour=(0.20, 0.22, 0.14)), (x1 * 0.75, -0.55, 0.0), rot=-15.0)
    gx.no_block(sx.lantern((x1 * 0.5, 0.03, 1.5), size=0.9, lit=False))
    gx.put(gx.bucket("zinc", 527), (x1 * 0.15, -0.2, 0.0), block=0)
    gx.no_block(geo.box((0.2, 0.3, 0.12), (x1 * 0.62, -0.25, 0.0), 30.0, mat.flat((0.06, 0.04, 0.03), roughness=0.7), bevel=0.03, name="boots"))
