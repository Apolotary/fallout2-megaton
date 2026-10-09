# SPDX-License-Identifier: MIT
"""Junk for every corner (author "ground"): heaps of things you can name, stores, the scrap yard.

HEAPS       gr_heap_a   fridge on its back, a car door, a tipped shopping trolley, a stop sign   4 hexes
            gr_heap_b   engine on a pallet, an upturned bath, a bedstead, a radiator, pipes      4 hexes
            gr_heap_c   the big one: washer, stove, television, filing cabinet, bonnet, mattress  7 hexes
            gr_heap_d   a television on a crate, a bucket, a warning sign                        1 hex
            gr_heap_e   tyres, a wheel, cinder blocks, a bent stop sign                          1 hex
            gr_heap_f   a trolley full of bottles, jerry cans, a sack                            2 hexes
STORES      gr_drums_a / b / c      three drums / a chocked pyramid of drums on their sides / two pallets of drums
            gr_crates_a / b / c     two crates and a sack / a tarped pyramid / a wall of crates with a ladder
            gr_tyres_u / gr_tyres_v a wall of tyres, four courses, along a row / a column (4 hexes)
            gr_pallets_a / b        a stack of pallets / pallets stood on edge against a post
CRATERSIDE  gr_workbench_u / _v     Moira's outdoor bench: vice, an engine in bits, a tool board, a lamp (4 hexes)
            gr_hoist                a tripod with a chain block and an engine hanging from it (2 hexes)
SCRAP YARD  gr_sort_doors           car doors racked like roof tiles (4 hexes along a row)
            gr_sort_pipes           a rack of pipe and bar (4 hexes along a row)
            gr_sort_sheets          roofing sheets, flat and leaning (3 hexes)
            gr_sort_bins            three bins under a SCRAP board: copper, glass, hub caps (4 hexes along a row)

Footprints are given by hand (hexes from the origin). Hex centres, in metres from the origin:
(1, 0) = (0.69, -0.4), (2, 0) = (1.39, 0), (0, 1) = (0, 0.8), (1, 1) = (0.69, 0.4).
"""
import math

from kit import piece, geo, mat, G
from kit import ground_extra as gx
from kit import bomb_extra as bx
from kit import signs_extra as sx
from kit import gate_extra as gate

HU, HV = gx.HEX_U, gx.HEX_V
DIAMOND = [(0, 0), (1, 0), (1, 1), (2, 0)]              # four hexes, centre (0.69, 0)
FLOWER = [(0, 0), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (0, -1)]
TRI = [(0, 0), (1, 0), (1, 1)]


def mound(cx, cy, rx, ry, height, seed, colour=(0.115, 0.085, 0.058)):
    """The body of a heap: trodden dirt and rubble, so that what lies on it lies ON something."""
    def h(x, y):
        dx, dy = (x - cx) / rx, (y - cy) / ry
        d = dx * dx + dy * dy
        if d >= 1.0:
            return None
        return max(0.0, height * (1.0 - d) ** 0.8 * (0.8 + 0.25 * bx.fbm(x * 1.7, y * 1.7, seed))) + 0.002
    return geo.set_block(bx.heightfield(cx - rx, cx + rx, cy - ry, cy + ry, h, bx.mud(colour, wet=0.15, seed=seed, cracks=0.2), step=0.09, name="mound"), geo.BLOCK_PROP)


def shards(points, seed, z=0.0):
    """Bits of sheet, board and bar lying about at [(x, y), ...]: the small change of a scrap heap."""
    r = geo.rng(seed)
    made = []
    for k, (x, y) in enumerate(points):
        kind = r.randrange(4)
        if kind == 0:
            made.append(geo.corrugated_panel(r.uniform(0.4, 0.7), r.uniform(0.5, 0.9), (x, y, z + 0.04), r.uniform(0, 360),
                                             gx.tin(r.choice([None, "teal", "oxide"]), rust=r.uniform(0.5, 0.8), seed=seed + k), tilt=r.uniform(70, 100),
                                             wavelength=0.12, name="shard_tin"))
        elif kind == 1:
            made.append(geo.box((r.uniform(0.5, 1.0), 0.14, 0.03), (x, y, z + 0.03), r.uniform(0, 180), gx.wood(seed=seed + k, grey=r.uniform(0.2, 0.6)), bevel=0.004,
                                name="shard_plank", tilt=r.uniform(-12, 12), roll=r.uniform(-8, 8)))
        elif kind == 2:
            made.append(geo.box((r.uniform(0.3, 0.5), r.uniform(0.25, 0.4), 0.02), (x, y, z + 0.03), r.uniform(0, 180),
                                gx.paint(r.choice(["oxide", "cream", "teal", "yellow", "grey"]), rust=0.6, seed=seed + k), bevel=0.0, name="shard_plate",
                                tilt=r.uniform(-20, 20), roll=r.uniform(-15, 15)))
        else:
            a = r.uniform(0, 6.28)
            length = r.uniform(0.5, 1.1)
            made.append(gx.rod((x, y, z + 0.03), (x + length * math.cos(a), y + length * math.sin(a), z + r.uniform(0.03, 0.3)), 0.03,
                               mat.steel(rust=0.9, seed=seed + k), 8, name="shard_bar"))
    return gx.no_block(made)


# ------------------------------------------------------------------------------ heaps
@piece("gr_heap_a", title="Scrap Heap", desc="A refrigerator on its back, a car door, a shopping trolley that will never see another aisle.",
       footprint=DIAMOND, shadow="flat")
def gr_heap_a(ctx):
    cx = HU
    mound(cx, 0.0, 1.25, 0.8, 0.34, 1)
    gx.put(gx.fridge(11), (cx - 0.25, 0.25, 0.42), rot=geo.U + 12.0, tilt=-82.0, roll=4.0)
    gx.put(gx.car_door("teal", 12, glass="glass"), (cx + 1.0, 0.42, 0.05), rot=geo.U + 8.0, tilt=-24.0)
    gx.put(gx.shopping_cart(13, tipped=True), (cx - 0.95, 0.3, 0.12), rot=geo.U - 30.0)
    gx.put(gx.road_sign("stop", 14, post=2.0, bent=17.0), (cx + 0.75, -0.25, 0.0), rot=geo.SCREEN)
    geo.tire((cx + 0.2, 0.62, 0.02), lying=True, seed=3, lean=6.0)
    gx.put(gx.wheel(15, hub="cream"), (cx - 0.5, 0.75, 0.0), rot=geo.U + 15.0, tilt=-12.0)
    gx.put(gx.cinder(16), (cx + 0.75, 0.75, 0.0), rot=30.0)
    shards([(cx - 1.1, -0.3), (cx + 0.3, -0.55), (cx + 1.25, 0.0), (cx - 0.2, 0.9)], 17)


@piece("gr_heap_b", title="Scrap Heap", desc="A V8 on a pallet, a bath turned over, an iron bedstead. Somebody means to come back for the engine.",
       footprint=DIAMOND, shadow="flat")
def gr_heap_b(ctx):
    cx = HU
    mound(cx, 0.0, 1.2, 0.78, 0.26, 2)
    gx.put(gx.pallet(21), (cx - 0.55, 0.28, 0.02), rot=geo.U + 8.0)
    gx.put(gx.engine_block(22, "blue"), (cx - 0.55, 0.28, 0.14), rot=geo.U + 20.0)
    gx.put(gx.bathtub(23, feet=False), (cx + 0.55, -0.1, 0.62), rot=geo.U - 14.0, tilt=172.0)
    gx.put(gx.bedstead(24), (cx + 0.2, -0.55, 0.0), rot=geo.U + 5.0, tilt=-10.0)
    gx.put(gx.radiator(25), (cx + 0.95, 0.55, 0.0), rot=geo.U - 20.0, tilt=-14.0)
    gx.put(gx.road_sign("yield", 26, post=1.9, bent=-14.0), (cx - 1.0, -0.3, 0.0), rot=geo.SCREEN)
    for k, (a, b) in enumerate((((cx - 0.2, 0.7, 0.05), (cx + 1.3, 0.8, 0.22)), ((cx - 0.1, 0.8, 0.05), (cx + 1.1, 0.95, 0.1)))):
        gx.rod(a, b, 0.05, gx.pipe_paint("grey", 27 + k), 10, name="pipe_length")
    gx.put(gx.bucket("zinc", 28), (cx + 0.1, 0.6, 0.0), tilt=70.0, rot=40.0)
    shards([(cx - 1.1, 0.5), (cx + 1.2, -0.45), (cx + 0.5, 0.95)], 29)


@piece("gr_heap_c", title="Scrap Mountain", desc="Everything that ever plugged in: a washer, a cooker, a television with its tube still whole. Children are told not to climb it.",
       footprint=FLOWER + [(1, -1), (-1, -1)], shadow="flat")
def gr_heap_c(ctx):
    mound(0.0, 0.0, 1.55, 1.2, 0.62, 3)
    gx.put(gx.washer(31), (-0.55, 0.2, 0.3), rot=geo.U + 10.0, tilt=-9.0, roll=5.0)
    gx.put(gx.washer(32, kind="stove", colour="cream"), (0.45, 0.42, 0.22), rot=geo.U - 16.0, roll=-7.0)
    gx.put(gx.tv(33), (-0.5, 0.2, 1.2), rot=geo.U + 22.0, roll=4.0)
    gx.put(gx.cabinet(34, "olive", open_drawer=2), (0.25, -0.5, 0.75), rot=geo.U + 6.0, tilt=-80.0, roll=8.0)
    gx.put(gx.bonnet("red", 35), (1.2, -0.1, 0.55), rot=geo.V + 10.0, tilt=-58.0)
    gx.put(gx.mattress(36), (-1.05, -0.35, 0.42), rot=geo.U + 35.0, tilt=-18.0, roll=10.0)
    gx.put(gx.bumper(37), (0.2, 1.0, 0.16), rot=geo.U + 12.0, roll=6.0)
    gx.put(gx.drum("yellow", 38, lying=True), (1.15, 0.75, 0.0), rot=geo.U - 30.0)
    gx.put(gx.road_sign("speed", 39, post=2.5, bent=-9.0), (-0.1, -0.85, 0.3), rot=geo.SCREEN)
    gx.put(gx.car_door("cream", 40, rear=True), (-1.4, 0.55, 0.0), rot=geo.U + 20.0, tilt=-28.0)
    geo.tire((-0.9, 0.95, 0.0), lying=True, seed=4)
    geo.tire((-0.85, 0.98, 0.21), lying=True, seed=5, lean=8.0)
    shards([(1.4, 0.2), (-1.5, -0.1), (0.7, 1.15), (-0.3, 1.15), (0.9, -0.8)], 41)


@piece("gr_heap_d", title="Dead Television", desc="A television on a crate, facing the street as if somebody still watched it.",
       footprint=[(0, 0)], shadow="baked")
def gr_heap_d(ctx):
    gx.put(gx.crate((0.7, 0.6, 0.5), seed=51, mark="cream"), (0, 0, 0), rot=geo.U + 8.0)
    gx.put(gx.tv(52), (0.0, 0.0, 0.53), rot=geo.U + 20.0)
    gx.put(gx.bucket("oxide", 53), (0.52, 0.35, 0.0))
    gx.put(gx.road_sign("diamond", 54, post=1.7, bent=10.0), (-0.42, -0.2, 0.0), rot=geo.SCREEN)


@piece("gr_heap_e", title="Tyres and Blocks", desc="Two bald tyres, a wheel, cinder blocks and a stop sign nobody obeys.",
       footprint=[(0, 0)], shadow="baked")
def gr_heap_e(ctx):
    geo.tire((0.05, 0.0, 0.0), lying=True, seed=6)
    geo.tire((0.0, 0.05, 0.21), lying=True, seed=7, lean=7.0)
    gx.put(gx.wheel(61, hub="oxide"), (0.5, 0.2, 0.0), rot=geo.U + 30.0, tilt=-14.0)
    gx.put(gx.cinder(62), (-0.5, 0.3, 0.0), rot=20.0)
    gx.put(gx.cinder(63), (-0.45, 0.32, 0.2), rot=75.0)
    gx.put(gx.road_sign("stop", 64, post=1.8, bent=-12.0, size=0.62), (-0.2, -0.3, 0.0), rot=geo.SCREEN)


@piece("gr_heap_f", title="Loaded Trolley", desc="A shopping trolley of empties, two jerry cans and a sack of something heavy.",
       footprint=[(0, 0), (1, 0)], shadow="baked")
def gr_heap_f(ctx):
    gx.put(gx.shopping_cart(71), (0.1, 0.0, 0.0), rot=geo.U + 14.0)
    gx.put(gx.bottle_row(5, seed=72), (0.1, 0.0, 0.5), rot=geo.U + 14.0)
    gx.put(gx.bottle_row(4, seed=73), (0.12, 0.14, 0.5), rot=geo.U + 14.0)
    gx.put(gx.jerrycan("olive", 74), (0.78, -0.2, 0.0), rot=geo.U - 20.0)
    gx.put(gx.jerrycan("red", 75), (0.95, 0.12, 0.0), rot=geo.U + 40.0)
    gx.put(gx.sack(76), (0.6, 0.5, 0.0), rot=20.0)


# ------------------------------------------------------------------------------ drums
@piece("gr_drums_a", title="Oil Drums", desc="Three drums: one red, one that was blue, one with its lid cut out for a rain butt.",
       footprint=[(0, 0)], shadow="baked", block_radius=None)
def gr_drums_a(ctx):
    gx.put(gx.drum("oxide", 81, band="yellow"), (-0.3, 0.12, 0.0))
    gx.put(gx.drum("blue", 82, open_top=True), (0.3, 0.14, 0.0))
    gx.put(gx.drum("olive", 83, rust=0.65), (0.02, -0.38, 0.0))
    geo.cylinder(0.26, 0.01, (0.3, 0.14, 0.72), gx.water(), 14, name="rain")
    gx.put(gx.bucket("zinc", 84), (0.62, 0.55, 0.0))
    gx.stain((0.1, 0.5), 0.4, gx.OIL, seed=8)


@piece("gr_drums_b", title="Drum Stack", desc="Drums on their sides, chocked with timber: three below, two above. The top ones are empty. Probably.",
       footprint=[(0, 0), (1, 0), (2, 0)], shadow="flat")
def gr_drums_b(ctx):
    cx = HU
    colours = [("oxide", None), ("yellow", "black"), ("blue", None), ("olive", "white"), ("oxide", None)]
    spots = [(-0.62, 0.34), (0.0, 0.34), (0.62, 0.34), (-0.31, 0.88), (0.31, 0.88)]
    for k, ((dx, z), (c, band)) in enumerate(zip(spots, colours)):
        # lying along local Y: the lids face the viewer
        gx.put(gx.drum(c, 91 + k, band=band, lying=True, dents=0 if z > 0.5 else 1), (cx + dx, -0.05, z - 0.31), rot=geo.V + (k - 2) * 2.0)
    for dx in (-0.98, 0.98):
        geo.box((0.16, 0.9, 0.14), (cx + dx, -0.05, 0.0), 0.0, gx.wood((0.20, 0.12, 0.06), seed=95, axis="Y", grey=0.3), bevel=0.01, name="chock",
                roll=14.0 if dx < 0 else -14.0)
    bx.plank((cx - 1.0, 0.46, 0.0), (cx + 1.0, 0.48, 0.0), 0.12, 0.09, gx.wood(seed=96, grey=0.4), name="sill")
    gx.stain((cx + 0.3, 0.75), 0.45, gx.OIL, seed=9)


@piece("gr_drums_c", title="Drum Store", desc="Two pallets of drums, a second tier going up, and one left open with a hand pump in it. The yellow band means do not drink.",
       footprint=DIAMOND + [(0, 1)], shadow="flat")
def gr_drums_c(ctx):
    cx = HU
    paints = ["oxide", "blue", "olive", "yellow", "red", "grey", "oxide", "teal", "cream", "olive", "oxide"]
    bands = [None, "yellow", None, "black", None, "yellow", "white", None, None, "yellow", None]
    k = 0
    for px, py in ((cx - 0.62, 0.0), (cx + 0.62, 0.05)):
        gx.put(gx.pallet(101 + k), (px, py, 0.0), rot=geo.U + (4.0 if px < cx else -3.0))
        for dx in (-0.3, 0.3):
            for dy in (-0.26, 0.26):
                gx.put(gx.drum(paints[k], 110 + k, band=bands[k], open_top=(k == 6)), (px + dx, py + dy, 0.12))
                k += 1
    for dx, dy in ((-0.62, 0.0), (-0.36, -0.2), (0.5, 0.06)):
        gx.put(gx.drum(paints[k], 110 + k, band=bands[k], dents=2), (cx + dx, dy, 1.0))
        k += 1
    # the open one: a rotary hand pump on a riser, its hose down the side
    px, py = cx + 0.92, 0.31
    gx.rod((px, py, 0.9), (px, py, 1.5), 0.03, mat.steel(rust=0.4, seed=3), 8, name="pump_riser")
    geo.cylinder(0.11, 0.1, (px, py + 0.05, 1.42), gx.paint("red", rust=0.3, seed=4), 12, name="pump_head", tilt=90.0)
    gx.rod((px, py - 0.06, 1.42), (px + 0.2, py - 0.1, 1.62), 0.02, mat.steel(rust=0.3, seed=5), 6, name="pump_crank")
    geo.cable((px, py - 0.08, 1.4), (px + 0.5, py + 0.4, 0.05), sag=0.3, radius=0.03)
    gx.put(gx.drum("olive", 130, lying=True), (cx - 0.1, 0.95, 0.0), rot=geo.U + 20.0)
    gx.put(gx.jerrycan("red", 131), (cx + 0.9, 0.85, 0.0), rot=geo.U + 30.0)
    gx.stain((cx + 0.5, 0.85), 0.5, gx.OIL, seed=10)
    gx.stain((cx - 0.9, 0.6), 0.3, gx.OIL, seed=11)


# ----------------------------------------------------------------------------- crates
@piece("gr_crates_a", title="Crates", desc="Two crates and a sack. The stencil on the big one has been painted over twice.",
       footprint=[(0, 0)], shadow="baked")
def gr_crates_a(ctx):
    gx.put(gx.crate((0.9, 0.8, 0.7), seed=141, mark="cream"), (0, 0, 0), rot=geo.U + 6.0)
    gx.put(gx.crate((0.6, 0.5, 0.42), seed=142, colour=(0.22, 0.20, 0.10), lid=False), (0.08, 0.05, 0.73), rot=geo.U - 18.0)
    gx.put(gx.sack(143), (0.55, 0.5, 0.0), rot=30.0)
    gx.put(gx.sack(144, colour=(0.24, 0.22, 0.15)), (0.5, 0.55, 0.17), rot=-10.0)


@piece("gr_crates_b", title="Crate Stack", desc="Crates under half a tarpaulin, roped down. One has been opened and not shut.",
       footprint=TRI, shadow="flat")
def gr_crates_b(ctx):
    cx, cy = 0.46, 0.0
    spots = [(-0.5, -0.1, 0.0, (0.85, 0.75, 0.62), 4.0), (0.42, -0.05, 0.0, (0.9, 0.8, 0.7), -5.0), (0.0, 0.55, 0.0, (0.7, 0.6, 0.5), 12.0),
             (-0.42, -0.1, 0.65, (0.7, 0.62, 0.52), -8.0), (0.38, -0.02, 0.73, (0.62, 0.55, 0.45), 14.0)]
    for k, (dx, dy, z, size, turn) in enumerate(spots):
        gx.put(gx.crate(size, seed=151 + k, mark=("cream", None, "yellow", None, "red")[k], lid=(k != 2),
                        colour=((0.28, 0.17, 0.08), (0.24, 0.19, 0.10), (0.30, 0.20, 0.10))[k % 3]), (cx + dx, cy + dy, z), rot=geo.U + turn)
    sx.sag_sheet([(cx - 0.95, -0.55, 1.22), (cx + 0.2, -0.5, 1.26), (cx + 0.25, 0.42, 1.2), (cx - 0.9, 0.35, 0.72)], gx.canvas((0.13, 0.17, 0.11), seed=3), sag=0.05,
                 seed=3)
    sx.sag_sheet([(cx - 0.95, -0.55, 1.22), (cx - 0.9, 0.35, 0.72), (cx - 1.0, 0.45, 0.05), (cx - 1.02, -0.5, 0.1)], gx.canvas((0.12, 0.16, 0.10), seed=4), sag=0.04,
                 seed=4)
    geo.cable((cx - 1.0, 0.0, 0.1), (cx + 0.3, -0.05, 1.3), sag=-0.08, radius=0.02, material=mat.flat((0.25, 0.19, 0.10), roughness=0.9))
    gx.put(gx.bottle_row(4, seed=7), (cx, 0.55, 0.42), rot=geo.U + 12.0)


@piece("gr_crates_c", title="Crate Wall", desc="Crates stacked three high with a ladder against them. The top row is for show: tap one and it rings hollow.",
       footprint=gx.row_hexes(0, 3), shadow="flat", see_through="u")
def gr_crates_c(ctx):
    r = ctx.rng
    x = 3.5 * HU
    column = 0
    while x > -0.3:
        w = r.uniform(0.72, 0.95)
        z = 0.0
        levels = (3, 2, 3, 1, 2)[column % 5]
        for level in range(levels):
            h = r.uniform(0.55, 0.72)
            gx.put(gx.crate((w - 0.03 * level, 0.72 - 0.04 * level, h), seed=160 + column * 4 + level, mark=r.choice([None, "cream", "yellow", "red", None]),
                            colour=r.choice([(0.28, 0.17, 0.08), (0.23, 0.19, 0.10), (0.31, 0.21, 0.10), (0.20, 0.13, 0.07)]), lid=(level == levels - 1)),
                   (x - w / 2.0, -0.12, z), rot=geo.U + r.uniform(-5, 5))
            z += h + 0.02
        x -= w + 0.02
        column += 1
    gate.ladder((1.6 * HU, 0.75, 0.0), (1.5 * HU, 0.26, 1.95), width=0.42, material=gx.wood(seed=7, grey=0.4))
    sx.lantern((2.9 * HU, 0.3, 1.62), size=0.9, lit=False)
    gx.put(gx.sack(171), (0.3, 0.55, 0.0), rot=15.0)
    gx.put(gx.sack(172), (0.9, 0.6, 0.0), rot=-25.0)


# ------------------------------------------------------------------------------ tyres
def tyre_wall(length, seed, courses=4):
    """Canonical: tyres laid like bricks along local x from 0 to length."""
    r = geo.rng(seed)
    made = []
    step = 0.7
    count = int(length / step)
    start = (length - count * step) / 2.0 + step / 2.0
    for course in range(courses):
        n = count - (course % 2)
        for i in range(n):
            if course == courses - 1 and r.random() < 0.3:
                continue
            x = start + i * step + (step / 2.0 if course % 2 else 0.0)
            made.append(geo.tire((x + r.uniform(-0.04, 0.04), r.uniform(-0.05, 0.05), course * 0.215), radius=r.uniform(0.34, 0.38), width=0.22, lying=True,
                                 rot=r.uniform(0, 360), lean=r.uniform(-3, 3), seed=seed + course * 10 + i))
            if course >= courses - 2 and r.random() < 0.5:
                made.append(geo.cylinder(0.2, 0.02, (x, 0.0, course * 0.215 + 0.17), bx.mud((0.13, 0.10, 0.07), wet=0.1, seed=seed + i), 10, name="tyre_fill"))
    top = courses * 0.215
    made.append(bx.plank((0.3, 0.02, top + 0.02), (length * 0.55, -0.02, top + 0.03), 0.22, 0.04, gx.wood(seed=seed, grey=0.5), name="top_plank"))
    made += gx.put(gx.bucket("zinc", seed), (length * 0.32, 0.0, top + 0.05))
    made += gx.put(gx.wheel(seed + 1, radius=0.42, width=0.26, hub="yellow"), (length - 0.15, -0.5, 0.0), rot=20.0, tilt=-16.0)
    return made


@piece("gr_tyres_u", title="Tyre Wall", desc="Tyres laid like bricks and packed with dirt. It stops a bullet and it stops a brahmin.",
       footprint=gx.row_hexes(0, 3), shadow="flat", material="plastic")
def gr_tyres_u(ctx):
    gx.put(tyre_wall(4 * HU, 181, courses=5), (3.5 * HU, -0.15, 0.0), rot=geo.U)


@piece("gr_tyres_v", title="Tyre Wall", desc="Tyres laid like bricks and packed with dirt. Weeds would grow in it, if anything grew.",
       footprint=gx.col_hexes(0, 3), shadow="flat", material="plastic")
def gr_tyres_v(ctx):
    gx.put(tyre_wall(4 * HV, 185, courses=4), (0.0, -HV / 2.0, 0.0), rot=geo.V)


# ---------------------------------------------------------------------------- pallets
@piece("gr_pallets_a", title="Pallet Stack", desc="Seven pallets, not quite square on each other. The top one is firewood.",
       footprint=[(0, 0)], shadow="baked", material="wood")
def gr_pallets_a(ctx):
    r = ctx.rng
    for k in range(7):
        gx.put(gx.pallet(191 + k, broken=(k in (3, 6))), (r.uniform(-0.05, 0.05), r.uniform(-0.05, 0.05), k * 0.125), rot=geo.U + r.uniform(-9, 9),
               tilt=5.0 if k == 6 else 0.0)
    gx.put(gx.sack(198), (0.1, 0.0, 0.9), rot=20.0)
    gx.put(gx.pallet(199, broken=True), (0.75, 0.25, 0.0), rot=geo.V + 8.0, tilt=-72.0)


@piece("gr_pallets_b", title="Pallets", desc="Pallets stood on edge against a post, and one laid flat for whatever must be kept off the ground.",
       footprint=[(0, 0), (1, 0), (2, 0)], shadow="flat", material="wood")
def gr_pallets_b(ctx):
    gx.post((2 * HU, 0.0, 0.0), 1.5, "timber", 201, foot="stones")
    for k in range(4):
        gx.put(gx.pallet(202 + k, broken=(k == 2)), (2 * HU - 0.3 - k * 0.2, 0.0, 0.5 + 0.02 * k), rot=geo.V, tilt=0.0, roll=-(72.0 - 5.0 * k))
    gx.put(gx.pallet(206), (0.2, 0.1, 0.0), rot=geo.U + 6.0)
    gx.put(gx.crate((0.6, 0.5, 0.42), seed=207, mark="yellow"), (0.05, 0.1, 0.13), rot=geo.U - 10.0)
    gx.put(gx.keg(208), (0.55, 0.3, 0.13))
    gx.put(gx.cinder(209), (0.75, -0.25, 0.0), rot=40.0)


# ------------------------------------------------------------------------- Craterside
def tool(frame, u, z, kind, d=0.03):
    """A tool hanging on a board, as a flat dark shape with one bright part."""
    steel = mat.flat((0.18, 0.18, 0.19), roughness=0.4, metallic=0.6)
    handle = gx.wood((0.26, 0.13, 0.05), seed=3, grey=0.1)
    made = []
    if kind == "saw":
        made.append(sx.plate([(0.0, 0.0), (0.55, 0.06), (0.55, 0.12), (0.0, 0.2)], frame.at(u, d, z), frame.rot, steel, thickness=0.012, name="saw"))
        made.append(geo.box((0.14, 0.03, 0.2), frame.at(u - 0.05, d, z), frame.rot, handle, bevel=0.02, name="saw_handle"))
    elif kind == "hammer":
        made.append(geo.box((0.04, 0.03, 0.36), frame.at(u, d, z), frame.rot, handle, bevel=0.008, name="hammer_shaft"))
        made.append(geo.box((0.18, 0.045, 0.07), frame.at(u, d, z + 0.33), frame.rot, steel, bevel=0.01, name="hammer_head"))
    elif kind == "wrench":
        made.append(geo.box((0.05, 0.02, 0.42), frame.at(u, d, z), frame.rot, steel, bevel=0.006, name="wrench", roll=12.0))
        made.append(sx.disc(0.06, frame.at(u - 0.085, d, z + 0.44), frame.rot, steel, thickness=0.02, hole=0.025, name="wrench_jaw"))
    else:
        made.append(sx.disc(0.16, frame.at(u, d, z + 0.16), frame.rot, gx.chrome(0.35), thickness=0.03, dome=0.04, name="hubcap"))
    return gx.no_block(made)


def workbench(length, seed):
    """Canonical: bench along local x (0 .. length), its front on -y, a tool board behind it."""
    f = gx.Frame((0, 0, 0), 0.0)
    made = []
    top = 0.92
    # legs: an oil drum under one end, an angle-iron frame under the other
    made += gx.put(gx.drum("olive", seed, rust=0.6), (0.36, -0.02, 0.0))
    for x in (length - 0.1, length - 0.75):
        for y in (-0.3, 0.26):
            made.append(bx.beam((x, y, 0.0), (x, y, top - 0.05), (0.06, 0.06), gx.iron(0.8, seed), name="bench_leg"))
    made.append(bx.beam((length - 0.75, -0.3, 0.35), (length - 0.1, -0.3, 0.6), (0.05, 0.05), gx.iron(0.8, seed + 1), name="bench_brace"))
    for k in range(4):
        made.append(geo.box((length + 0.08, 0.17, 0.05), (length / 2.0, -0.3 + k * 0.18, top - 0.05), 0.0,
                            gx.wood(((0.27, 0.16, 0.07), (0.22, 0.15, 0.08), (0.30, 0.19, 0.09), (0.20, 0.12, 0.06))[k], seed=seed + k, grey=0.25 + 0.1 * k), bevel=0.006,
                            name="bench_top", roll=(0.6, -0.4, 0.3, -0.7)[k]))
    made.append(gx.stain((length * 0.55, -0.1), 0.3, gx.OIL, seed=seed, squash=0.5))
    made[-1].location.z = top + 0.004
    # the board behind: planks on two posts, tools on nails, a shelf of tins
    for x in (0.08, length - 0.08):
        made += gx.post((x, 0.42, 0.0), 2.15, "timber", seed + x, size=0.1)
    made += sx.plank_panel(gx.Frame((0, 0.38, 0), 0.0), 0.0, length, 1.05, 2.05, colours=((0.25, 0.15, 0.07), (0.20, 0.14, 0.08), (0.29, 0.19, 0.09)), seed=seed, ragged=0.07)
    board = gx.Frame((0, 0.36, 0), 0.0)
    made += tool(board, length * 0.18, 1.5, "saw")
    made += tool(board, length * 0.47, 1.42, "hammer")
    made += tool(board, length * 0.6, 1.4, "wrench")
    made += tool(board, length * 0.82, 1.5, "hubcap")
    made += gx.bolts(board, [(length * 0.47, 1.9), (length * 0.6, 1.92)], d=0.03, radius=0.022, runs=0.3, seed=seed)
    # on the bench: a vice, an engine in bits, a battery, tins
    vx = length - 0.3
    made.append(geo.box((0.2, 0.16, 0.12), (vx, -0.22, top), 0.0, gx.paint("blue", rust=0.4, seed=seed + 5), bevel=0.02, name="vice_base"))
    made.append(geo.box((0.07, 0.2, 0.16), (vx - 0.08, -0.22, top + 0.1), 0.0, gx.iron(0.3, seed), bevel=0.012, name="vice_jaw"))
    made.append(geo.box((0.07, 0.2, 0.16), (vx + 0.1, -0.22, top + 0.1), 0.0, gx.iron(0.3, seed + 1), bevel=0.012, name="vice_jaw"))
    made.append(gx.rod((vx + 0.14, -0.36, top + 0.1), (vx + 0.14, -0.1, top + 0.16), 0.014, gx.chrome(0.4), 6, name="vice_bar"))
    made += gx.put(gx.engine_block(seed + 6, "orange"), (length * 0.48, 0.0, top), rot=14.0, scale=0.85)
    made.append(geo.box((0.26, 0.17, 0.2), (0.3, -0.12, top), 12.0, gx.dark(0.035), bevel=0.02, name="battery"))
    for dx in (-0.07, 0.07):
        made.append(geo.cylinder(0.02, 0.04, (0.3 + dx, -0.12, top + 0.2), gx.chrome(0.5), 6, name="terminal"))
    made += gx.put(gx.produce(seed + 7, kind="tins", size=(0.4, 0.2)), (length * 0.25, 0.2, top))
    # under and beside it
    made += gx.put(gx.crate((0.62, 0.5, 0.45), seed=seed + 8, mark="yellow"), (length * 0.5, 0.0, 0.0), rot=6.0)
    made.append(geo.tire((length - 0.45, -0.75, 0.0), lying=True, seed=seed))
    made += gx.put(gx.jerrycan("red", seed + 9), (0.5, -0.72, 0.0), rot=30.0)
    made.append(gx.stain((length * 0.6, -0.7), 0.5, gx.OIL, seed=seed + 2))
    # a caged lamp on a bracket over the bench
    lx = length * 0.3
    made.append(gx.rod((lx, 0.38, 2.0), (lx, -0.25, 2.2), 0.022, mat.steel(rust=0.6, seed=seed), 6, name="lamp_arm"))
    made += sx.caged_lamp((lx, -0.25, 2.18), lit=True, strength=1.8)
    return made


@piece("gr_workbench_v", title="Moira's Bench", desc="Planks on an oil drum, a vice, and an engine she has had in bits since spring. The tools are back on their nails, mostly.",
       footprint=gx.col_hexes(0, 3), shadow="flat", material="wood", light=(4, 70), light_hex=(0, 1), see_through="v")
def gr_workbench_v(ctx):
    made = workbench(4 * HV - 0.1, 211)
    gx.put(made, (-0.12, -HV / 2.0 + 0.05, 0.0), rot=geo.V)
    geo.halo((0.5, 0.9, 0.0), radius=1.5, strength=0.4)


@piece("gr_workbench_u", title="Work Bench", desc="Planks on an oil drum, a vice, an engine in bits. The tools are back on their nails, mostly.",
       footprint=gx.row_hexes(0, 3), shadow="flat", material="wood", light=(4, 70), light_hex=(2, 0), see_through="u")
def gr_workbench_u(ctx):
    made = workbench(4 * HU - 0.1, 215)
    gx.put(made, (3.5 * HU - 0.05, -0.25, 0.0), rot=geo.U)
    geo.halo((2.0 * HU, 0.5, 0.0), radius=1.5, strength=0.4)


@piece("gr_hoist", title="Engine Hoist", desc="Three scaffold tubes, a chain block and a V8 turning slowly on the hook.",
       footprint=[(0, 0), (1, 0)], shadow="flat", see_through=True)
def gr_hoist(ctx):
    cx, cy = HU / 2.0, -0.2
    apex = (cx, cy, 2.75)
    steel = mat.steel(rust=0.7, seed=5)
    for k, (dx, dy) in enumerate(((-0.95, 0.5), (0.95, 0.45), (0.05, -0.85))):
        gx.rod((cx + dx, cy + dy, 0.0), apex, 0.045, steel, 10, name="hoist_leg")
        geo.box((0.2, 0.2, 0.03), (cx + dx, cy + dy, 0.0), 30.0 * k, gx.iron(0.8, k), bevel=0.0, name="hoist_foot")
    gx.lash((cx, cy, 2.68), radius=0.09, height=0.16, colour=(0.05, 0.045, 0.04))
    geo.box((0.18, 0.14, 0.24), (cx, cy, 2.3), 20.0, gx.paint("yellow", rust=0.35, seed=6), bevel=0.03, name="chain_block")
    geo.pipe([(cx, cy, 2.66), (cx, cy, 2.5)], 0.02, mat.flat((0.05, 0.045, 0.04)), name="hook")
    for dx in (-0.03, 0.03):
        geo.pipe([(cx + dx, cy, 2.3), (cx + dx, cy, 1.52)], 0.02, mat.flat((0.06, 0.055, 0.05), metallic=0.5, roughness=0.5), name="chain")
    geo.pipe([(cx + 0.12, cy, 2.36), (cx + 0.2, cy + 0.1, 1.0)], 0.016, mat.flat((0.06, 0.055, 0.05), metallic=0.5, roughness=0.5), name="hand_chain")
    gx.put(gx.engine_block(7, "blue"), (cx, cy, 0.84), rot=geo.U + 28.0, roll=-7.0, block=0)
    geo.box((0.6, 0.45, 0.07), (cx, cy + 0.05, 0.0), 14.0, gx.paint("black", rust=0.5, seed=8), bevel=0.01, name="drip_tray")
    gx.stain((cx + 0.05, cy + 0.1), 0.62, gx.OIL, seed=12)
    gx.put(gx.wheel(9, hub="grey"), (cx + 0.85, cy + 0.6, 0.0), rot=geo.U + 10.0, tilt=-14.0)
    gx.put(gx.gas_bottle("blue", 10), (cx - 0.9, cy + 0.75, 0.0), block=0)


# ------------------------------------------------------------------------- scrap yard
@piece("gr_sort_doors", title="Car Doors", desc="Car doors sorted by nothing in particular and racked like roof tiles. Two still wind down.",
       footprint=gx.row_hexes(0, 3), shadow="flat", see_through="u")
def gr_sort_doors(ctx):
    r = ctx.rng
    length = 4 * HU
    made = []
    for x in (0.1, length - 0.1):
        made += gx.post((x, 0.3, 0.0), 1.25, "pipe", 221 + int(x), foot="none")
    made.append(gx.rail((0.0, 0.3, 1.1), (length, 0.3, 1.05), "pipe", 222))
    paints = ["red", "teal", "cream", "black", "orange", "blue"]
    for k in range(6):
        x = 0.1 + k * 0.42
        made += gx.put(gx.car_door(paints[k], 230 + k, glass=("glass", "none", "none", "boards", "none", "glass")[k], rear=(k % 3 == 1), width=1.0 + 0.05 * (k % 2)),
                       (x, 0.1 - 0.05 * k, 0.03 * (k % 2)), rot=r.uniform(-4, 4), tilt=-(7.0 + 1.5 * k), roll=r.uniform(-2, 2))
    made += gx.put(gx.bumper(240), (length * 0.5, -0.75, 0.08), rot=5.0, roll=3.0)
    made += gx.put(gx.bumper(241, plate=False), (length * 0.55, -0.9, 0.06), rot=-4.0)
    made += gx.put(gx.bonnet("olive", 242), (0.2, -0.85, 0.02), rot=20.0)
    gx.put(made, (3.5 * HU, -0.3, 0.0), rot=geo.U)


@piece("gr_sort_pipes", title="Pipe Rack", desc="Pipe, bar and conduit on two trestles, long lengths at the bottom. Walter gets first pick.",
       footprint=gx.row_hexes(0, 3), shadow="flat", see_through="u")
def gr_sort_pipes(ctx):
    r = ctx.rng
    length = 4 * HU
    made = []
    for x in (0.55, length - 0.55):
        for side in (-1.0, 1.0):
            made.append(bx.beam((x, side * 0.5, 0.0), (x, side * 0.1, 0.72), (0.08, 0.08), gx.wood(seed=250 + int(x * 3), grey=0.4), name="trestle_leg"))
        made.append(geo.box((0.1, 0.95, 0.08), (x, 0.0, 0.42), 0.0, gx.wood(seed=251, axis="Y", grey=0.4), bevel=0.008, name="trestle_bar"))
        made.append(gx.rod((x, 0.46, 0.5), (x, 0.52, 1.1), 0.03, mat.steel(rust=0.8, seed=2), 6, name="stop"))
        made.append(gx.rod((x, -0.46, 0.5), (x, -0.52, 1.0), 0.03, mat.steel(rust=0.8, seed=3), 6, name="stop"))
    colours = ["oxide", "grey", "green", "oxide", "zinc", "oxide", "grey", "blue", "oxide", "zinc"]
    k = 0
    for row, count in enumerate((5, 4, 3)):
        for i in range(count):
            radius = r.choice([0.05, 0.06, 0.075, 0.09]) if row else r.choice([0.075, 0.09])
            y = (i - (count - 1) / 2.0) * 0.19 + r.uniform(-0.01, 0.01)
            z = 0.5 + 0.09 + row * 0.165
            a, b = r.uniform(-0.35, 0.15), length + r.uniform(-0.1, 0.5)
            made.append(gx.rod((a, y, z), (b, y + r.uniform(-0.03, 0.03), z + r.uniform(-0.01, 0.02)), radius, gx.pipe_paint(colours[k % len(colours)], 260 + k), 10,
                               name="racked_pipe"))
            made.append(geo.cylinder(radius * 0.72, 0.01, (a - 0.004, y, z), gx.dark(), 8, name="bore", roll=-90.0))
            k += 1
    # a coil of cable hung on the end, short ends in a drum
    made.append(geo.lathe([(0.2, 0.0), (0.26, 0.03), (0.26, 0.1), (0.2, 0.13), (0.2, 0.0)], (length - 0.5, -0.56, 0.75), mat.flat((0.03, 0.03, 0.03), roughness=0.6), 14,
                          name="cable_coil", tilt=90.0))
    made += gx.put(gx.drum("oxide", 270, open_top=True, height=0.7), (0.1, -0.75, 0.0))
    for i in range(5):
        a = i * 1.3
        made.append(gx.rod((0.1 + 0.1 * math.cos(a), -0.75 + 0.1 * math.sin(a), 0.1), (0.1 + 0.2 * math.cos(a), -0.75 + 0.2 * math.sin(a), r.uniform(1.0, 1.5)), 0.03,
                           mat.steel(rust=0.85, seed=i), 6, name="short_end"))
    gx.put(made, (3.5 * HU, -0.2, 0.0), rot=geo.U)


@piece("gr_sort_sheets", title="Roofing Sheets", desc="Corrugated iron, flat in a pile with a tyre on top so the wind does not take it, and the good ones stood against a post.",
       footprint=TRI, shadow="flat")
def gr_sort_sheets(ctx):
    r = ctx.rng
    cx, cy = 0.46, 0.0
    colours = [None, "oxide", None, "teal", None, "cream", None, None, "oxide", None]
    for k in range(10):
        geo.corrugated_panel(1.0, 1.9 + r.uniform(-0.15, 0.1), (cx + 0.55 + r.uniform(-0.06, 0.06), cy - 1.0 + r.uniform(-0.08, 0.08), 0.05 + k * 0.035), geo.U + r.uniform(-5, 5),
                             gx.tin(colours[k], rust=r.uniform(0.35, 0.8), seed=280 + k, top=1.9), tilt=90.0 + r.uniform(-1.5, 1.5), wavelength=0.13, depth=0.035,
                             name="flat_sheet")
    geo.tire((cx, cy - 0.1, 0.42), lying=True, seed=13, lean=4.0)
    gx.post((cx - 0.75, cy + 0.2, 0.0), 2.0, "timber", 291, foot="stones")
    for k in range(3):
        geo.corrugated_panel(0.95, 2.0 - 0.12 * k, (cx - 0.3 - 0.08 * k, cy + 0.55 + 0.07 * k, 0.0), geo.V + 4.0 * k, gx.tin((None, "teal", None)[k], rust=0.4 + 0.15 * k, seed=292 + k, top=2.0),
                             tilt=-(14.0 + 3.0 * k), wavelength=0.13, depth=0.035, name="leaning_sheet")


@piece("gr_sort_bins", title="Scrap Bins", desc="SCRAP, says the board, and under it three bins: copper, glass, and hub caps that somebody polishes.",
       footprint=gx.row_hexes(0, 3), shadow="flat", see_through="u")
def gr_sort_bins(ctx):
    length = 4 * HU
    made = []
    for x in (0.08, length - 0.08):
        made += gx.post((x, 0.35, 0.0), 2.75, "timber", 301 + int(x), size=0.11, lean=(0.03 if x < 1 else -0.02, 0.0))
    f = gx.Frame((0, 0.3, 0), 0.0)
    made += sx.plank_panel(f, -0.05, length + 0.05, 2.02, 2.7, paint=(0.34, 0.30, 0.20), wear=0.45, seed=5, ragged=0.08)
    made += [glyph for _, glyph, _, _ in sx.letters("SCRAP", f, length / 2.0, 2.12, 0.46, font="impact",
                                                    material=mat.sign_paint((0.26, 0.05, 0.03), wear=0.4, seed=5), d=0.012, depth=0.01, jitter=0.02, seed=5)]
    made += gx.bolts(f, [(0.12, 2.6), (length - 0.12, 2.6)], d=0.02, radius=0.03, runs=0.45, seed=6)
    made.append(gx.rail((0.08, 0.35, 1.1), (length - 0.08, 0.35, 1.05), "board", 302))
    # bin 1: half a drum of copper (the one bright warm thing)
    x1 = length * 0.17
    made += gx.put(gx.drum("oxide", 303, height=0.55, open_top=True), (x1, -0.1, 0.0))
    copper = mat.flat((0.50, 0.21, 0.06), roughness=0.35, metallic=0.7)
    for k in range(4):
        made.append(geo.lathe([(0.1, 0.0), (0.16, 0.02), (0.16, 0.07), (0.1, 0.09)], (x1 + (k % 2) * 0.1 - 0.05, -0.1 + (k // 2) * 0.1 - 0.05, 0.46 + 0.07 * k), copper, 12,
                              name="copper_coil", tilt=10.0 * k))
    # bin 2: a crate of bottles
    x2 = length * 0.5
    made += gx.put(gx.crate((0.75, 0.6, 0.5), seed=304, lid=False, mark="cream"), (x2, -0.1, 0.0), rot=4.0)
    for j in range(3):
        made += gx.put(gx.bottle_row(5, seed=305 + j, height=0.3), (x2, -0.26 + 0.16 * j, 0.36))
    # bin 3: a shopping trolley of hub caps
    x3 = length * 0.83
    made += gx.put(gx.shopping_cart(306), (x3, -0.15, 0.0), rot=-8.0)
    for k in range(4):
        made.append(sx.disc(0.17, (x3 - 0.2 + 0.13 * k, -0.15, 0.68 + 0.03 * k), 0.0, gx.chrome(0.3 + 0.05 * k), thickness=0.03, dome=0.04, tilt=-70.0 + 12.0 * k, name="hubcap"))
    # a spring balance hanging from the rail
    made.append(geo.pipe([(length * 0.34, 0.33, 1.08), (length * 0.34, 0.25, 0.86)], 0.014, mat.flat((0.05, 0.045, 0.04)), name="balance_wire"))
    made.append(sx.disc(0.11, (length * 0.34, 0.24, 0.75), 0.0, gx.paint("cream", rust=0.25, seed=7), thickness=0.04, name="balance"))
    gx.put(made, (3.5 * HU, -0.25, 0.0), rot=geo.U)
