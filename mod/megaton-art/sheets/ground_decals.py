# SPDX-License-Identifier: MIT
"""Floor DECALS of the "ground" author: things that lie flat on whatever ground is there. They block
nothing, hide nothing and take no click, so they are what goes on the lanes and doorsteps.

    gr_chalk      2 x 2 squares   the children's corner: a hopscotch, a sun, a house, a figure, in chalk
    gr_litter_a   3 x 2 squares   an oil stain, flattened tins, a drum lid, a board, bolts
    gr_litter_b   2 x 2 squares   duckboards over a wet patch, a hose, a rag
    gr_ash        2 x 2 squares   an old fire: a burnt ring, charred ends, bones

Sheet coordinates (metres): x to the screen's lower left (1.3856 per square), y to the lower right
(1.6 per square), z up from the ground.
"""
import math

from kit import sheet, geo, mat, T
from kit import sheet_kit as sk
from kit import ground_extra as gx

WET = (0.062, 0.047, 0.031)         # dirt that is wet through
MUD = (0.098, 0.072, 0.045)         # churned, damp dirt
POOL = (0.085, 0.105, 0.11)         # a skin of standing water: it shows the sky, so it is the LIGHTEST part of a puddle
ALGAE = (0.06, 0.10, 0.045)
CHALK = ((0.50, 0.50, 0.46), (0.48, 0.34, 0.30), (0.46, 0.42, 0.22), (0.32, 0.40, 0.44))


_LIFT = [0]


def stroke(points, colour, width=0.055, closed=False):
    """A chalk line through sheet points [(x, y), ...]: flat strips, 2 px wide. Every strip lies a hair
    higher than the one before and faces up: strips that share an edge (the hopscotch boxes) would
    otherwise be coplanar and render black where they overlap."""
    material = mat.flat(colour, roughness=1.0)
    pts = list(points) + ([points[0]] if closed else [])
    for (ax, ay), (bx_, by) in zip(pts, pts[1:]):
        dx, dy = bx_ - ax, by - ay
        length = math.hypot(dx, dy)
        if length < 1e-4:
            continue
        _LIFT[0] = (_LIFT[0] + 1) % 40
        z = 0.004 + 0.0012 * _LIFT[0]
        nx, ny = -dy / length * width / 2.0, dx / length * width / 2.0
        ex, ey = dx / length * width * 0.3, dy / length * width * 0.3
        gx.quad([(ax - ex - nx, ay - ey - ny, z), (bx_ + ex - nx, by + ey - ny, z), (bx_ + ex + nx, by + ey + ny, z), (ax - ex + nx, ay - ey + ny, z)],
                material, "chalk")


def ring(cx, cy, radius, colour, width=0.055, count=14, squash=1.0):
    stroke([(cx + radius * math.cos(2 * math.pi * k / count), cy + radius * squash * math.sin(2 * math.pi * k / count)) for k in range(count)], colour, width, closed=True)


@sheet("gr_chalk", kind="floor", size=(2, 2), decal=True, shadow=False, title="Chalk Marks")
def gr_chalk(ctx):
    white, pink, yellow, blue = CHALK
    # hopscotch: 1, 2, 3 | 4 5 | 6 | 7 8 up the sheet's y axis
    x0, y0, s = 0.5, 0.25, 0.42
    boxes = [(0, 0), (0, 1), (0, 2), (-0.5, 3), (0.5, 3), (0, 4), (-0.5, 5), (0.5, 5)]
    for k, (bx_, by) in enumerate(boxes):
        ax, ay = x0 + bx_ * s, y0 + by * s
        stroke([(ax, ay), (ax + s, ay), (ax + s, ay + s), (ax, ay + s)], white if k % 3 else pink, closed=True)
    ring(x0 + s / 2.0, y0 + 6.45 * s, s * 0.45, yellow)
    # a sun with rays
    cx, cy = 2.05, 0.55
    ring(cx, cy, 0.2, yellow, count=10)
    for k in range(8):
        a = 2 * math.pi * k / 8
        stroke([(cx + 0.28 * math.cos(a), cy + 0.28 * math.sin(a)), (cx + 0.44 * math.cos(a), cy + 0.44 * math.sin(a))], yellow)
    # a house and a stick figure beside it
    hx, hy = 1.65, 1.5
    stroke([(hx, hy), (hx + 0.55, hy), (hx + 0.55, hy + 0.5), (hx, hy + 0.5)], blue, closed=True)
    stroke([(hx - 0.06, hy), (hx + 0.275, hy - 0.32), (hx + 0.61, hy)], pink)
    stroke([(hx + 0.2, hy + 0.5), (hx + 0.2, hy + 0.22), (hx + 0.36, hy + 0.22), (hx + 0.36, hy + 0.5)], white)
    fx, fy = 2.4, 1.75
    ring(fx, fy - 0.3, 0.1, white, count=8)
    stroke([(fx, fy - 0.2), (fx, fy + 0.15)], white)
    stroke([(fx - 0.17, fy - 0.08), (fx + 0.17, fy - 0.08)], white)
    stroke([(fx - 0.14, fy + 0.4), (fx, fy + 0.15), (fx + 0.14, fy + 0.4)], white)
    # the bomb, as children draw it, and a throwing stone
    bx0, by0 = 1.45, 2.55
    ring(bx0, by0, 0.3, pink, count=12, squash=0.55)
    stroke([(bx0 + 0.3, by0), (bx0 + 0.5, by0 - 0.14), (bx0 + 0.5, by0 + 0.14)], pink, closed=True)
    geo.box((0.13, 0.1, 0.05), (x0 + 0.2, y0 + 0.6, 0.0), 30.0, mat.concrete((0.22, 0.2, 0.17), cracks=0.0, seed=2), bevel=0.02)
    geo.box((0.1, 0.04, 0.03), (2.2, 2.5, 0.0), -20.0, mat.flat(white, roughness=1.0), bevel=0.01)


@sheet("gr_litter_a", kind="floor", size=(3, 2), decal=True, title="Litter")
def gr_litter_a(ctx):
    r = ctx.rng
    gx.stain((1.3, 1.2), 0.62, (0.03, 0.026, 0.022), seed=3, gloss=0.25, z=0.004)
    gx.stain((1.9, 1.75), 0.3, (0.03, 0.026, 0.022), seed=4, gloss=0.25, z=0.007)
    geo.cylinder(0.29, 0.02, (3.0, 0.9, 0.0), gx.paint("oxide", rust=0.6, seed=5), 16, name="drum_lid", tilt=3.0)
    geo.box((1.25, 0.16, 0.03), (2.9, 2.35, 0.0), 24.0, gx.wood(seed=6, grey=0.5), bevel=0.004, name="board")
    geo.box((0.8, 0.15, 0.03), (0.7, 2.6, 0.0), -38.0, gx.wood(seed=7, grey=0.3), bevel=0.004, name="board")
    for k in range(9):
        x, y = r.uniform(0.3, ctx.w - 0.3), r.uniform(0.3, ctx.h - 0.3)
        kind = k % 3
        if kind == 0:
            geo.box((0.16, 0.11, 0.015), (x, y, 0.0), r.uniform(0, 180), gx.paint(r.choice(["red", "cream", "zinc", "yellow"]), rust=0.4, seed=k, gloss=0.5), bevel=0.0,
                    name="flat_tin")
        elif kind == 1:
            geo.cylinder(0.035, 0.03, (x, y, 0.0), mat.flat((0.06, 0.055, 0.05), metallic=0.5, roughness=0.5), 6, name="nut")
        else:
            geo.box((0.22, 0.16, 0.008), (x, y, 0.0), r.uniform(0, 180), mat.flat((0.36, 0.33, 0.25), roughness=1.0), bevel=0.0, name="paper")
    gx.rod((3.5, 1.6, 0.03), (3.95, 2.4, 0.03), 0.03, mat.steel(rust=0.9, seed=3), 6, name="bar")


@sheet("gr_litter_b", kind="floor", size=(2, 2), decal=True, title="Duckboards")
def gr_litter_b(ctx):
    gx.stain((1.35, 1.6), 0.95, WET, seed=5, squash=0.9, gloss=0.1, z=0.004)
    gx.stain((1.5, 1.75), 0.4, POOL, seed=6, gloss=0.3, z=0.007)
    sk.plank_deck(0.7, 0.5, 2.05, 2.75, z=0.0, along="y", board=0.2, ragged=0.4, missing=0.2, seed=9, grey=0.55)
    for y in (0.95, 2.2):
        geo.box((1.45, 0.1, 0.05), (1.37, y, -0.02), 0.0, gx.wood((0.18, 0.11, 0.06), seed=int(y * 3), grey=0.3), bevel=0.004, name="bearer")
    geo.pipe([(0.25, 0.4, 0.035), (0.45, 1.3, 0.035), (0.3, 2.2, 0.035), (0.6, 2.95, 0.035)], 0.035, mat.flat((0.05, 0.09, 0.05), roughness=0.5), name="hose")
    geo.box((0.35, 0.25, 0.03), (2.3, 0.6, 0.0), 30.0, gx.canvas((0.30, 0.10, 0.07), seed=2), bevel=0.012, name="rag")


@sheet("gr_ash", kind="floor", size=(2, 2), decal=True, title="Old Fire")
def gr_ash(ctx):
    r = ctx.rng
    cx, cy = ctx.w / 2.0, ctx.h / 2.0
    gx.stain((cx, cy), 0.8, (0.04, 0.037, 0.034), seed=7, squash=0.95, gloss=0.0, z=0.004)
    gx.stain((cx + 0.05, cy), 0.42, (0.16, 0.155, 0.145), seed=8, gloss=0.0, z=0.007)
    for k in range(7):
        a = 2 * math.pi * k / 7 + r.uniform(-0.2, 0.2)
        geo.box((r.uniform(0.14, 0.2), r.uniform(0.12, 0.16), 0.07), (cx + 0.5 * math.cos(a), cy + 0.5 * math.sin(a), 0.0), math.degrees(a), mat.concrete((0.17, 0.16, 0.15), cracks=0.0, seed=k),
                bevel=0.03, name="stone")
    for k in range(4):
        a = k * 1.1 + 0.4
        gx.rod((cx + 0.28 * math.cos(a), cy + 0.28 * math.sin(a), 0.03), (cx - 0.2 * math.cos(a), cy - 0.2 * math.sin(a), 0.04), 0.035, mat.flat((0.025, 0.02, 0.018), roughness=0.95), 6,
               name="charred")
    for k in range(3):
        gx.rod((cx + 0.75 + 0.1 * k, cy + 0.5 - 0.22 * k, 0.02), (cx + 1.0 + 0.08 * k, cy + 0.62 - 0.2 * k, 0.02), 0.022, mat.flat((0.40, 0.37, 0.30), roughness=0.8), 6, name="bone")


# ------------------------------------------------------------------ more things that lie flat (lanes, doorsteps)


@sheet("gr_plates", kind="floor", size=(2, 2), decal=True, title="Walk Plates")
def gr_plates(ctx):
    """A doorstep: two steel plates and a sheet of tin laid over the mud, a board to bridge them."""
    gx.stain((1.4, 1.6), 1.05, MUD, seed=11, squash=0.95, gloss=0.0, z=0.003)
    sk.plate(0.35, 0.45, 1.5, 1.75, thickness=0.02, material=gx.iron(rust=0.8, seed=3), rot=6.0, name="plate")
    sk.plate(1.2, 1.5, 2.45, 2.8, thickness=0.025, material=gx.paint("oxide", rust=0.7, seed=4), rot=-9.0, name="plate")
    sk.tin(1.45, 0.3, 2.4, 1.55, z=0.03, rust=0.75, seed=5, wavelength=0.16)
    geo.box((1.5, 0.2, 0.04), (0.9, 2.3, 0.01), 18.0, gx.wood(seed=3, grey=0.55), bevel=0.004, name="board")
    for k, (x, y) in enumerate(((0.45, 0.55), (1.4, 0.55), (0.45, 1.65), (1.4, 1.65), (1.3, 1.6), (2.35, 2.7))):
        geo.cylinder(0.035, 0.03, (x, y, 0.02), mat.flat((0.05, 0.035, 0.025), metallic=0.4, roughness=0.7), 6, name="rivet")
    gx.stain((0.95, 1.1), 0.3, gx.STREAK, seed=12, gloss=0.1, z=0.05)


@sheet("gr_puddle", kind="floor", size=(2, 2), decal=True, title="Leak Puddle")
def gr_puddle(ctx):
    """Where a joint has dripped for years: wet dirt, a skin of water, a rim of scale and a little green."""
    gx.stain((1.4, 1.6), 1.0, WET, seed=21, squash=0.9, gloss=0.2, lobes=4, z=0.004)
    gx.stain((1.3, 1.5), 0.72, gx.LIME, seed=22, squash=0.85, gloss=0.0, z=0.006)
    gx.stain((1.33, 1.52), 0.6, (0.045, 0.05, 0.045), seed=22, squash=0.85, gloss=0.2, z=0.008)
    gx.stain((1.28, 1.45), 0.4, POOL, seed=26, squash=0.8, gloss=0.3, z=0.010)
    gx.stain((1.9, 2.2), 0.3, ALGAE, seed=23, gloss=0.2, z=0.012)
    gx.stain((0.75, 1.0), 0.24, ALGAE, seed=24, gloss=0.2, z=0.013)
    gx.stain((2.1, 0.9), 0.26, WET, seed=25, gloss=0.3, z=0.014)
    geo.box((0.2, 0.12, 0.06), (2.0, 1.2, 0.0), 40.0, mat.concrete((0.2, 0.19, 0.17), cracks=0.0, seed=3), bevel=0.03, name="stone")


def _rut(points, width, colour, lift):
    """A wheel rut through sheet points: a ragged dark band."""
    left, right = [], []
    for k, (x, y) in enumerate(points):
        ax, ay = points[max(0, k - 1)]
        bx_, by = points[min(len(points) - 1, k + 1)]
        dx, dy = bx_ - ax, by - ay
        ln = math.hypot(dx, dy) or 1.0
        w = width / 2.0 * (1.0 + 0.35 * math.sin(k * 2.3 + lift * 900.0))
        left.append((x - dy / ln * w, y + dx / ln * w, lift))
        right.append((x + dy / ln * w, y - dx / ln * w, lift))
    gx.quad(right + left[::-1], mat.flat(colour, roughness=1.0), "rut")


@sheet("gr_ruts_v", kind="floor", size=(1, 3), decal=True, title="Cart Ruts")
def gr_ruts_v(ctx):
    """Two wheel ruts and the hoof-churned strip between them, running down a column (the main track)."""
    n = 13
    for side, x0 in enumerate((0.32, 1.05)):
        pts = [(x0 + 0.03 * math.sin(k * 0.9 + side), 0.15 + (ctx.h - 0.3) * k / (n - 1)) for k in range(n)]
        _rut(pts, 0.2, MUD, 0.004 + side * 0.001)
        _rut([(x + 0.02, y) for x, y in pts[3 + side * 4:7 + side * 5]], 0.09, WET, 0.008 + side * 0.001)
    gx.stain((0.68, 1.3), 0.17, MUD, seed=31, squash=1.3, gloss=0.0)
    gx.stain((0.7, 3.6), 0.15, MUD, seed=32, squash=1.3, gloss=0.0)
    gx.stain((1.05, 2.6), 0.16, POOL, seed=33, squash=1.9, gloss=0.3)


@sheet("gr_ruts_u", kind="floor", size=(3, 1), decal=True, title="Cart Ruts")
def gr_ruts_u(ctx):
    """The same ruts running along a row (the lanes off the pool)."""
    n = 13
    for side, y0 in enumerate((0.42, 1.2)):
        pts = [(0.15 + (ctx.w - 0.3) * k / (n - 1), y0 + 0.035 * math.sin(k * 0.8 + side * 2)) for k in range(n)]
        _rut(pts, 0.24, MUD, 0.004 + side * 0.001)
        _rut([(x, y + 0.02) for x, y in pts[2 + side * 5:6 + side * 6]], 0.11, WET, 0.008 + side * 0.001)
    gx.stain((1.2, 0.8), 0.16, MUD, seed=34, squash=0.8, gloss=0.0)
    gx.stain((3.2, 0.82), 0.14, MUD, seed=35, squash=0.8, gloss=0.0)
    gx.stain((2.2, 1.22), 0.2, POOL, seed=36, squash=0.45, gloss=0.3)


@sheet("gr_hose_v", kind="floor", size=(1, 3), decal=True, title="Cable and Hose")
def gr_hose_v(ctx):
    """A power cable and a garden hose lying across the dirt down a column, a board thrown over them where people cross."""
    geo.pipe([(0.45, 0.1, 0.04), (0.6, 0.9, 0.04), (0.38, 1.9, 0.04), (0.62, 2.9, 0.04), (0.5, 3.9, 0.04), (0.55, 4.7, 0.04)], 0.045,
             mat.flat((0.02, 0.02, 0.022), roughness=0.5), name="cable")
    geo.pipe([(0.85, 0.1, 0.035), (0.72, 1.1, 0.035), (0.98, 2.0, 0.035), (0.8, 3.1, 0.035), (0.95, 4.0, 0.035), (0.86, 4.7, 0.035)], 0.04,
             mat.flat((0.05, 0.11, 0.05), roughness=0.5), name="hose")
    geo.box((1.2, 0.34, 0.05), (0.7, 2.45, 0.03), 4.0, gx.wood(seed=41, grey=0.5), bevel=0.006, name="board")
    gx.stain((0.95, 3.6), 0.2, WET, seed=42, gloss=0.4)


@sheet("gr_hose_u", kind="floor", size=(3, 1), decal=True, title="Cable and Hose")
def gr_hose_u(ctx):
    geo.pipe([(0.1, 0.55, 0.04), (0.9, 0.7, 0.04), (1.8, 0.45, 0.04), (2.7, 0.72, 0.04), (3.5, 0.55, 0.04), (4.05, 0.6, 0.04)], 0.045,
             mat.flat((0.02, 0.02, 0.022), roughness=0.5), name="cable")
    geo.pipe([(0.1, 1.0, 0.035), (1.0, 0.86, 0.035), (1.9, 1.12, 0.035), (2.8, 0.92, 0.035), (3.5, 1.08, 0.035), (4.05, 1.0, 0.035)], 0.04,
             mat.flat((0.05, 0.11, 0.05), roughness=0.5), name="hose")
    geo.box((0.34, 1.25, 0.05), (2.3, 0.8, 0.03), -5.0, gx.wood(seed=43, grey=0.5), bevel=0.006, name="board")
    gx.stain((1.3, 1.15), 0.2, WET, seed=44, gloss=0.4)


@sheet("gr_scrap_flat", kind="floor", size=(3, 2), decal=True, title="Trodden Scrap")
def gr_scrap_flat(ctx):
    """What gets walked into the dirt beside a heap: a car bonnet skin, a flattened drum, a grating, a number plate, rust."""
    gx.stain((2.0, 1.6), 1.25, (0.10, 0.06, 0.03), seed=51, squash=0.8, gloss=0.0, lobes=4, z=0.003)
    sk.plate(0.5, 0.5, 1.75, 1.6, thickness=0.025, material=gx.paint("teal", rust=0.6, seed=6), rot=14.0, name="bonnet")
    sk.tin(2.1, 0.35, 3.1, 1.5, z=0.02, rust=0.85, seed=8, wavelength=0.16)
    sk.plate(2.6, 1.7, 3.75, 2.75, thickness=0.03, material=gx.wire(axes="xy", cell=0.16, thickness=0.34, seed=2), rot=-8.0, name="grating")
    sk.plate(1.0, 2.0, 2.05, 2.75, thickness=0.02, material=gx.paint("yellow", rust=0.55, seed=9), rot=-20.0, name="drum_skin")
    geo.box((0.5, 0.16, 0.012), (3.4, 0.9, 0.035), 30.0, gx.paint("cream", rust=0.3, seed=3), bevel=0.0, name="number_plate")
    geo.cylinder(0.22, 0.02, (0.55, 2.3, 0.0), gx.iron(rust=0.9, seed=5), 14, name="lid")
    for k, (x, y) in enumerate(((1.9, 1.75), (0.4, 1.4), (3.2, 2.9), (2.3, 2.95))):
        geo.cylinder(0.04, 0.03, (x, y, 0.0), mat.flat((0.06, 0.055, 0.05), metallic=0.5, roughness=0.5), 6, name="nut")
