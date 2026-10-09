# SPDX-License-Identifier: MIT
"""The Children of Atom's shrine at the bomb: lectern, candles, banners, prayer flags, a mat.

Every piece here is ONE part on ONE hex (the flag line: one part per pole), because each is a
prop no bigger than the hex it blocks, or lies in front of its hex:

    mgb_lectern     the Confessor's stand. He stands on the hex BEHIND it (dhy - 1, or dhx - 1 on
                    the same row): lower tile number, painted first, so the stand hides his legs.
    mgb_candles     a tin lid of candles on the ground + its pool of light (flat, yellow)
    mgb_candles_b   candles in bottles on a crate + pool of light
    mgb_banner      red banner with the atom on a scrap mast, facing the camera
    mgb_banner_b    a yellow one, its yard to the other side (a pair frames the lectern), more torn
    mgb_flagline    prayer flags between two poles four hexes apart on a hex row; people walk under
    mgb_mat         kneeling mat. Does not block; its picture lies on and in front of its hex, so
                    whoever kneels on the hex is painted over it and nobody behind it is covered.

Flames are painted with the animated "fire" palette colours: they flicker by themselves and are
not darkened at night. The candle pieces are also real (white) engine lights of three hexes, and
carry a small pool of the engine's yellow see-through blend to warm that light. The blend is
always on, so it is kept faint; without the engine light it reads as a dark ring at night.

PLACEMENT in the town: placement.py (group "crater"; offsets from the BOMB spot). These replace
layout/outdoors.py pool(): PODIUM -> mgb_lectern, ATOM_FLAG[0] / [1] -> mgb_banner / mgb_banner_b,
INCENSE and LANTERN -> mgb_candles / mgb_candles_b.
"""
import math

from mathutils import Matrix, Vector

from kit import piece, geo, mat, G
from kit import bomb_extra as bx

RED = (0.36, 0.035, 0.02)
OCHRE = (0.50, 0.33, 0.04)
CREAM = (0.72, 0.68, 0.54)
FLAG_COLOURS = [(0.50, 0.07, 0.03), (0.62, 0.42, 0.05), (0.60, 0.56, 0.44), (0.52, 0.20, 0.03), (0.10, 0.16, 0.22)]


@piece("mgb_lectern", title="Lectern",
       desc="A lectern welded from a wheel, a pipe and a locker door. A book lies open on it; the pages glow faintly.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", material="metal")
def mgb_lectern(ctx):
    steel = mat.steel(rust=0.75, seed=4.0)
    parts = []
    # built facing local -Y (x to the right), then turned to the camera
    parts.append(geo.tire((0, 0.02, 0.0), radius=0.30, width=0.17, lying=True, seed=3))
    parts.append(geo.cylinder(0.2, 0.05, (0, 0.02, 0.15), steel, 16, name="hub"))
    parts.append(geo.pipe([(0, 0.05, 0.1), (0, 0.05, 0.95)], 0.055, steel, name="column"))
    # the body: a locker door as front, plank cheeks, a sloping desk
    front = bx.bomb_paint(colour=(0.20, 0.045, 0.03), rust=0.45, seed=6.0, bleach=0.2)
    parts.append(geo.box((0.66, 0.035, 0.74), (0, -0.2, 0.40), 0.0, front, bevel=0.008, name="front"))
    wood = mat.planks(colour=(0.23, 0.125, 0.06), axis="Z", width=0.2, seed=3.0)
    for sx in (-1, 1):
        parts.append(geo.box((0.035, 0.42, 0.66), (sx * 0.32, 0.0, 0.46), 0.0, wood, bevel=0.006, name="cheek"))
    desk = geo.box((0.76, 0.52, 0.045), (0, -0.02, 1.13), 0.0, mat.planks(colour=(0.26, 0.15, 0.07), axis="X", width=0.26, seed=5.0),
                   bevel=0.008, name="desk", tilt=20.0)
    parts.append(desk)
    # the book, open, lying on the slope (tilt about X like the desk)
    page = mat.flat((0.60, 0.56, 0.42), roughness=0.9)
    cover = mat.flat((0.16, 0.035, 0.03), roughness=0.7)
    tilt = Matrix.Rotation(math.radians(20.0), 4, "X")
    for sx in (-1, 1):
        obj = geo.box((0.2, 0.3, 0.03), (0, 0, 0), 0.0, page, bevel=0.008, centred=True, name="page")
        obj.matrix_world = Matrix.Translation((0, -0.02, 1.13)) @ tilt @ Matrix.Translation((sx * 0.105, 0.0, 0.065)) \
            @ Matrix.Rotation(math.radians(-sx * 7.0), 4, "Y")
        parts.append(obj)
    obj = geo.box((0.46, 0.34, 0.02), (0, 0, 0), 0.0, cover, bevel=0.004, centred=True, name="cover")
    obj.matrix_world = Matrix.Translation((0, -0.02, 1.13)) @ tilt @ Matrix.Translation((0.0, 0.0, 0.04))
    parts.append(obj)
    # a strip of red cloth down the front with the atom on it
    parts.append(bx.cloth(0.42, 0.78, (0, -0.235, 1.12), 0.0, bx.cloth_mat(RED, seed=2.0, fade=0.25), sag=0.0, flutter=0.012,
                          seed=3, columns=5, rows=6, ragged=0.07))
    parts += bx.atom_emblem((0, -0.262, 0.80), 0.34, (1, 0, 0), (0, 0, 1), bx.paint(CREAM, wear=0.15, seed=3.0), stroke=0.017)
    # a candle on the desk's high corner
    parts += bx.candle((0.3, 0.16, 1.2), height=0.14, radius=0.03, flame=1.2, seed=2)
    bx.move(bx.flat_list(parts), bx.turned(geo.SCREEN))


def candle_group(spots, z=0.0, seed=0, flame=1.3):
    r = geo.rng(seed)
    objects = []
    for k, (x, y, h) in enumerate(spots):
        objects += bx.candle((x, y, z), height=h, radius=r.uniform(0.03, 0.04), flame=flame * r.uniform(0.9, 1.15), seed=seed + k)
        if h < 0.12:                                                    # a burnt-down one sits in its own wax
            objects.append(geo.cylinder(0.07, 0.012, (x, y, z), bx.wax(seed=k), 10, name="wax"))
    return objects


@piece("mgb_candles", title="Candles",
       desc="Candles on a hubcap, burning low. The faithful keep them lit.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="none", material="metal", light=(3, 70), convert={"halo_levels": 2})
def mgb_candles(ctx):
    plate = mat.steel(rust=0.35, colour=(0.20, 0.20, 0.19), seed=2.0)
    geo.lathe([(0.34, 0.0), (0.36, 0.025), (0.30, 0.04), (0.12, 0.05), (0.0, 0.05)], (0, 0, 0), plate, 20, name="hubcap")
    candle_group([(0.0, 0.0, 0.34), (0.15, 0.1, 0.2), (-0.16, 0.06, 0.26), (0.05, 0.2, 0.1), (-0.07, -0.16, 0.15),
                  (0.2, -0.1, 0.09), (-0.22, -0.1, 0.08)], z=0.045, seed=3)
    geo.box((0.16, 0.11, 0.07), (0.42, 0.22, 0.0), 30.0, mat.concrete(seed=3.0), bevel=0.02, name="stone")
    geo.halo((0.0, 0.05, 0.0), radius=1.0, strength=0.7)


@piece("mgb_candles_b", title="Candles",
       desc="Candle stubs in bottles on an ammunition box, in a skin of old wax.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", material="wood", light=(3, 70), convert={"halo_levels": 2})
def mgb_candles_b(ctx):
    geo.crate((0.62, 0.42, 0.34), (0, 0, 0), 162.0, seed=6)
    glass = mat.flat((0.07, 0.10, 0.045), roughness=0.15)
    brown = mat.flat((0.10, 0.045, 0.012), roughness=0.15)
    r = geo.rng(8)
    for k, (x, y) in enumerate(((-0.19, 0.02), (0.02, -0.07), (0.2, 0.05))):
        geo.lathe([(0.045, 0.0), (0.045, 0.15), (0.018, 0.2), (0.018, 0.27), (0.0, 0.27)], (x, y, 0.34), brown if k == 1 else glass, 8,
                  name="bottle")
        bx.candle((x, y, 0.60), height=r.uniform(0.05, 0.12), radius=0.02, flame=1.3, seed=k)
    candle_group([(0.42, 0.18, 0.18), (0.5, 0.02, 0.1)], z=0.0, seed=12)
    geo.halo((0.1, 0.08, 0.0), radius=1.1, strength=0.7)


def mast(height, foot=True, seed=0, lean=(0.0, 0.0)):
    steel = mat.steel(rust=0.7, seed=3.0 + seed)
    objects = [geo.pipe([(0, 0, 0), (lean[0] * 0.5, lean[1] * 0.5, height * 0.55), (lean[0], lean[1], height)], 0.045, steel, name="mast")]
    if foot:
        objects.append(geo.tire((0, 0, 0), radius=0.27, width=0.16, lying=True, seed=seed))
        objects.append(geo.cylinder(0.17, 0.17, (0, 0, 0), mat.concrete(seed=seed + 1.0), 14, name="plug"))
    return objects


def banner(rot, colour, emblem_colour, seed, height=3.3, width=0.78, drop=1.9, ragged=0.16, yard_side=1, stroke=0.024):
    """A mast with a yard and a long banner hanging from it; the cloth's front faces local -Y of `rot`."""
    turn = bx.turned(rot)
    parts = mast(height, seed=seed)
    steel = mat.steel(rust=0.6, seed=5.0)
    yard_z = height - 0.12
    yard = geo.pipe([(-0.12, 0, yard_z), (yard_side * (width + 0.16), 0, yard_z + 0.04)], 0.03, steel, name="yard")
    stay = geo.pipe([(0, 0, height - 0.75), (yard_side * (width * 0.8), 0, yard_z)], 0.018, steel, name="yard_stay")
    cx = yard_side * (width / 2.0 + 0.1)
    flag = bx.cloth(width, drop, (cx, -0.02, yard_z - 0.01), 0.0, bx.cloth_mat(colour, seed=seed, fade=0.3), sag=0.05,
                    flutter=0.05, seed=seed, columns=8, rows=12, ragged=ragged)
    emblem = bx.atom_emblem((cx, -0.085, yard_z - drop * 0.4), width * 0.74, (1, 0, 0), (0, 0, 1),
                            bx.paint(emblem_colour, wear=0.2, seed=seed), stroke=stroke)
    hem = geo.box((width * 0.96, 0.03, 0.07), (cx, -0.02, yard_z - 0.1), 0.0, bx.cloth_mat(tuple(c * 0.5 for c in colour), seed=seed + 1),
                  bevel=0.0, name="hem")
    bx.move(bx.flat_list(yard, stay, flag, emblem, hem), turn)
    return parts


@piece("mgb_banner", title="Banner of Atom",
       desc="A long red banner on a scrap mast. Three orbits and a nucleus, daubed in white: the Children of Atom.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", material="metal")
def mgb_banner(ctx):
    banner(geo.SCREEN, RED, CREAM, seed=2)


@piece("mgb_banner_b", title="Banner of Atom",
       desc="A sun-bleached yellow banner, torn at the hem. The atom on it has been repainted many times.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", material="metal")
def mgb_banner_b(ctx):
    banner(geo.SCREEN, OCHRE, (0.07, 0.05, 0.04), seed=5, height=3.0, width=0.82, drop=1.6, ragged=0.3, stroke=0.028, yard_side=-1)


@piece("mgb_flagline", title="Prayer Flags",
       desc="Squares of dyed cloth on a line between two poles. Each one is somebody's prayer to Atom.",
       footprint=[(0, 0), (4, 0)], anchors=[(0, 0), (4, 0)], shadow="baked", material="metal")
def mgb_flagline(ctx):
    x_r, y = G.hex_xy(0, 0)
    x_l, _ = G.hex_xy(4, 0)
    steel = mat.steel(rust=0.7, seed=6.0)
    tops = []
    for x, h, lean in ((x_l, 2.75, 0.07), (x_r, 2.55, -0.06)):
        geo.pipe([(x, y, 0.0), (x + lean * 0.4, y, h * 0.5), (x + lean, y, h)], 0.04, steel, name="pole")
        geo.box((0.26, 0.26, 0.09), (x, y, 0.0), 20.0, mat.concrete(seed=x), bevel=0.02, name="pole_foot")
        tops.append((x + lean, y, h - 0.04))
    line = geo.catenary(tops[0], tops[1], sag=0.36, count=24)
    geo.pipe(line, 0.014, mat.flat((0.05, 0.045, 0.04), roughness=0.7), name="line")
    for i in range(2, 23, 2):
        k = i // 2
        p = line[i]
        bx.cloth(0.25, 0.30 + 0.05 * ((k * 5) % 3), (p[0], p[1], p[2] - 0.01), geo.U, bx.cloth_mat(FLAG_COLOURS[(k * 2) % 5], seed=k + 20),
                 sag=0.0, flutter=0.035, seed=k + 20, columns=4, rows=4, ragged=0.08, name="flag")
    # guy lines down to pegs, so the poles have a reason to stand
    geo.pipe([tops[0], (x_l + 0.5, y + 0.1, 0.0)], 0.012, mat.flat((0.05, 0.045, 0.04)), name="guy")
    geo.pipe([tops[1], (x_r - 0.5, y + 0.1, 0.0)], 0.012, mat.flat((0.05, 0.045, 0.04)), name="guy")


@piece("mgb_mat", title="Kneeling Mat",
       desc="A strip of carpet, worn through at two places a knee apart.",
       footprint=[], anchors=[(0, 0)], shadow="none", material="leather")
def mgb_mat(ctx):
    # x -0.62..0.62, y -0.18..0.52 round the hex centre: on the hex and in front of it
    def height(x, y):
        if abs(x) > 0.62 + 0.012 * math.sin(y * 40.0) or not -0.18 < y < 0.52:
            return None
        return 0.018 + 0.006 * bx.fbm(x, y, 3.0, 4.0, 2)

    def stripes():
        from kit.nodes import Graph
        g = Graph("mat")
        x, y, _ = g.separate(g.coords())
        band = g.fract(g.div(g.add(x, 0.62), 0.155))
        tone = g.ramp(band, [(0.0, RED), (0.48, RED), (0.52, OCHRE), (0.78, OCHRE), (0.82, (0.07, 0.05, 0.04))], "CONSTANT")
        worn = g.smooth(g.noise(g.coords(), scale=6.0, detail=3.0), 0.55, 0.75)
        def near(cx, cy):
            dx, dy = g.sub(x, cx), g.sub(y, cy)
            return g.smooth(g.math("SQRT", g.add(g.mul(dx, dx), g.mul(dy, dy))), 0.16, 0.05)

        knees = g.maximum(near(-0.2, 0.2), near(0.2, 0.2))
        base = g.mix(g.maximum(g.mul(worn, 0.6), g.mul(knees, 0.85)), tone, (0.20, 0.16, 0.11))
        g.principled(base=base, roughness=0.95, specular=0.05)
        return g.material

    bx.no_block(bx.heightfield(-0.66, 0.66, -0.2, 0.54, height, stripes(), step=0.03, name="mat"))
    wool = bx.cloth_mat((0.42, 0.36, 0.24), seed=4.0)
    for i in range(9):                                               # fringe at both ends
        for sx in (-1, 1):
            y = -0.14 + i * 0.08
            bx.no_block(geo.box((0.07, 0.03, 0.012), (sx * 0.665, y, 0.012), 0.0, wool, bevel=0.0, name="fringe"))
