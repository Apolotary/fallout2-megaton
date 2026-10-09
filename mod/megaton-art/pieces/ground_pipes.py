# SPDX-License-Identifier: MIT
"""The water plant's pipes (author "ground"): a kit of 0.3 m mains that runs across town.

GRID RULES (so any piece joins any other)
  A run ALONG A ROW ("u") lies on the straight line through the row's EVEN hexes (y = 0 of its
  origin) and blocks every hex of the row it covers. A run ALONG A COLUMN ("v") lies on the line
  through the column's hex centres. Every piece covers whole hexes and ends ON the boundary
  between two hexes, where it carries half a flange: two pieces set end to end make a bolted
  joint, a piece that ends in the open has a blank flange.
  Origins are even / even as everywhere. A piece's hexes are listed below from its origin:
      u pieces   (0, 0) .. (n - 1, 0)       n even: the next u piece starts on origin hx + n
      v pieces   (0, 0) .. (0, n - 1)       n even: the next v piece starts on origin hy + n
  ON THE GROUND the pipe's axis is 0.36 m up on saddles (cinder blocks, cradles, sleepers); it is
  knee high and blocks. OVERHEAD it runs at 2.36 m (over heads, under the eave line of a roof it
  passes in front of) and blocks nothing but its risers.

GROUND      gr_pipe_u4a / u4b / u2       straight along a row (b: a leaking joint, lime and a puddle)
            gr_pipe_v4a / v4b / v2       straight along a column
            gr_pipe_el_a .. el_d         elbows: a (+hx, +hy) covers (0,0) (1,0) (0,1); b (+hx, -hy)
                                         covers (0,0) (1,0); c (-hx, +hy) covers (0,0) (0,1);
                                         d (-hx, -hy) covers (0,0). The corner is on the origin.
            gr_pipe_tee_u / tee_v        a tee: through run on (0,0) (1,0) with a branch to +hy on
                                         (0,1) / through run on (0,0) (0,1) with a branch to +hx on (1,0)
            gr_pipe_valve_u / valve_v    two hexes with a gate valve and its hand wheel
            gr_pipe_manifold             six hexes along a row: three valves, a bypass loop, gauges
            gr_pipe_wall_u               the hex beside a wall that runs along a COLUMN: origin = the
                                         WALL's hex, pipe on (1, 0), a collar on the wall's face
            gr_pipe_wall_v               the collar where a v run meets a wall along a ROW behind
                                         it: same origin as the run's first piece, blocks nothing
CROSSINGS   gr_pipe_ramp_u / ramp_v      two hexes where people cross: the pipe half buried under a
                                         plank-and-plate ramp. Blocks nothing; walkers are drawn on it.
OVERHEAD    gr_pipe_rise_ua / ub         two hexes: up from the ground run to 2.36 m. ua: ground
                                         end towards +hx (riser on (0,0)), ub: ground end towards
                                         -hx (riser on (1,0)); the other end is overhead
            gr_pipe_rise_va / vb         same along a column: va ground end towards -hy (riser on
                                         (0,0)), vb ground end towards +hy (riser on (0,1))
            gr_pipe_hi_u4 / hi_v4        four hexes of overhead run, nothing on the ground
            gr_pipe_post_u / post_v      two hexes of overhead run on a braced post (blocks (0,0))
A crossing of the gate track along a row, from screen right to left:
    ... u4, rise_ub, hi_u4, rise_ua, u4 ...
"""
import math

from kit import piece, geo, mat, G
from kit import ground_extra as gx
from kit import bomb_extra as bx

R, Z, HI = gx.PIPE_R, gx.PIPE_Z, gx.PIPE_HIGH
HU, HV = gx.HEX_U, gx.HEX_V
OPTS = dict(material="metal", shadow="flat")


def set_u(objects, n):
    """Canonical run (local x 0 .. n hexes, front on -y) -> along the row: local 0 = the screen-left end."""
    return gx.put(objects, ((n - 0.5) * HU, 0.0, 0.0), rot=geo.U)


def set_v(objects, n=0):
    """... -> along the column: local 0 = the far end."""
    return gx.put(objects, (0.0, -HV / 2.0, 0.0), rot=geo.V)


def su(dhx, n):
    """Local x of hex dhx in a u piece of n hexes."""
    return (n - 0.5 - dhx) * HU


def sv(dhy):
    return (dhy + 0.5) * HV


def half_flange(x, z=Z, seed=0, side=1.0):
    """Half a bolted joint on the end of a piece: one disc, flush with the hex boundary."""
    material = gx.iron(0.7, seed)
    big = R * 1.55
    x0 = x - 0.045 if side > 0 else x
    made = [geo.lathe([(R, 0.0), (big, 0.0), (big, 0.045), (R, 0.045)], (x0, 0.0, z), material, 16, name="flange", roll=90.0)]
    nut = mat.flat((0.05, 0.045, 0.04), roughness=0.5, metallic=0.5)
    for k in range(6):
        a = 2.0 * math.pi * (k + 0.5) / 6
        made.append(geo.box((0.11, 0.045, 0.045), (x - side * 0.03, (R + big) / 2.0 * math.cos(a), z + (R + big) / 2.0 * math.sin(a)), 0.0, nut, bevel=0.0,
                            name="flange_bolt", centred=True))
    return gx.no_block(made)


def straight(length, colour, seed, z=Z, joints=(), sections=None):
    made = gx.pipe_run(length, colour, seed, z=z, joints=joints, ends=(False, False), sections=sections)
    made += half_flange(0.0, z, seed, -1.0)
    made += half_flange(length, z, seed + 1, 1.0)
    return made


# ------------------------------------------------------------------------- straights
@piece("gr_pipe_u4a", title="Water Main", desc="A rust-red main on cinder blocks. A steel sleeve is bolted over an old split.",
       footprint=gx.row_hexes(0, 3), **OPTS)
def gr_pipe_u4a(ctx):
    n, L = 4, 4 * HU
    run = straight(L, "oxide", 11, joints=(L * 0.52,))
    run += gx.clamp(0.75, seed=3)
    run += gx.saddle(su(3, n), kind="blocks", seed=1) + gx.saddle(su(0, n), kind="sleeper", seed=2)
    set_u(run, n)


@piece("gr_pipe_u4b", title="Leaking Main", desc="The joint weeps. Lime has built up round it and the ground under it never dries.",
       footprint=gx.row_hexes(0, 3), **OPTS)
def gr_pipe_u4b(ctx):
    n, L = 4, 4 * HU
    run = straight(L, "oxide", 21, joints=(L * 0.42,), sections=[(L * 0.42, L, "green")])
    run += gx.drip(L * 0.42, seed=4)
    run += gx.clamp(L * 0.78, seed=5, kind="rag")
    run += gx.gauge(0.55, seed=6)
    run += gx.saddle(su(2, n), kind="cradle", seed=3) + gx.saddle(su(0, n) + 0.1, kind="tyre", seed=4)
    set_u(run, n)


@piece("gr_pipe_u2", title="Water Main", desc="A short length of main on a timber sleeper.", footprint=gx.row_hexes(0, 1), **OPTS)
def gr_pipe_u2(ctx):
    n, L = 2, 2 * HU
    run = straight(L, "grey", 31)
    run += gx.clamp(L * 0.4, seed=7, kind="rubber")
    run += gx.saddle(su(0, n), kind="sleeper", seed=5)
    set_u(run, n)


@piece("gr_pipe_v4a", title="Water Main", desc="A main painted green once. It hums when the pumps run.",
       footprint=gx.col_hexes(0, 3), **OPTS)
def gr_pipe_v4a(ctx):
    L = 4 * HV
    run = straight(L, "green", 41, joints=(L * 0.5,), sections=[(0.0, L * 0.5, "oxide")])
    run += gx.clamp(L * 0.75, seed=8)
    run += gx.saddle(sv(0), kind="blocks", seed=6) + gx.saddle(sv(3), kind="cradle", seed=7)
    set_v(run)


@piece("gr_pipe_v4b", title="Leaking Main", desc="Somebody wound an inner tube round the split. It still drips.",
       footprint=gx.col_hexes(0, 3), **OPTS)
def gr_pipe_v4b(ctx):
    L = 4 * HV
    run = straight(L, "oxide", 51, joints=(L * 0.6,))
    run += gx.drip(L * 0.6, seed=9)
    run += gx.clamp(L * 0.28, seed=10, kind="rubber")
    run += gx.saddle(sv(1), kind="tyre", seed=8) + gx.saddle(sv(3), kind="blocks", seed=9)
    set_v(run)


@piece("gr_pipe_v2", title="Water Main", desc="A short length of main.", footprint=gx.col_hexes(0, 1), **OPTS)
def gr_pipe_v2(ctx):
    L = 2 * HV
    run = straight(L, "grey", 61)
    run += gx.saddle(sv(1), kind="sleeper", seed=10)
    set_v(run)


# --------------------------------------------------------------------------- corners
def elbow(to_x, to_y, colour, seed):
    """An elbow whose corner is on the origin hex: legs to +-X and +-Y, each to its hex boundary."""
    x_end = 1.5 * HU if to_x > 0 else -0.5 * HU
    y_end = 1.5 * HV if to_y > 0 else -0.5 * HV
    gx.bend([(x_end, 0.0, Z), (0.0, 0.0, Z), (0.0, y_end, Z)], colour=colour, seed=seed, corner=0.3)
    gx.put(half_flange(0.0, Z, seed, 1.0), (x_end, 0.0, 0.0), rot=0.0 if to_x > 0 else 180.0)
    gx.put(half_flange(0.0, Z, seed + 1, 1.0), (0.0, y_end, 0.0), rot=90.0 if to_y > 0 else -90.0)
    # a thrust block under the corner: poured concrete, a strap over the pipe
    geo.box((0.5, 0.5, Z - R + 0.03), (0.0, 0.0, 0.0), 20.0, mat.concrete(seed=seed), bevel=0.03, name="thrust_block")
    if to_x > 0:
        gx.put(gx.saddle(0.0, kind="sleeper", seed=seed), (HU, 0.0, 0.0))
    if to_y > 0:
        gx.put(gx.saddle(0.0, kind="blocks", seed=seed), (0.0, HV, 0.0), rot=90.0)


@piece("gr_pipe_el_a", title="Pipe Elbow", desc="The main turns a corner on a block of poured concrete.",
       footprint=[(0, 0), (1, 0), (0, 1)], **OPTS)
def gr_pipe_el_a(ctx):
    elbow(1, 1, "oxide", 71)


@piece("gr_pipe_el_b", title="Pipe Elbow", desc="The main turns a corner on a block of poured concrete.", footprint=[(0, 0), (1, 0)], **OPTS)
def gr_pipe_el_b(ctx):
    elbow(1, -1, "oxide", 72)


@piece("gr_pipe_el_c", title="Pipe Elbow", desc="The main turns a corner on a block of poured concrete.", footprint=[(0, 0), (0, 1)], **OPTS)
def gr_pipe_el_c(ctx):
    elbow(-1, 1, "green", 73)


@piece("gr_pipe_el_d", title="Pipe Elbow", desc="The main turns a corner on a block of poured concrete.", footprint=[(0, 0)], **OPTS)
def gr_pipe_el_d(ctx):
    elbow(-1, -1, "oxide", 74)


@piece("gr_pipe_tee_u", title="Pipe Tee", desc="A cast tee. The branch was added later, and it shows.",
       footprint=[(0, 0), (1, 0), (0, 1)], **OPTS)
def gr_pipe_tee_u(ctx):
    n, L = 2, 2 * HU
    run = straight(L, "oxide", 81)
    s0 = su(0, n)
    run.append(geo.lathe([(R * 1.3, 0.0), (R * 1.3, 0.5)], (s0 - 0.25, 0.0, Z), gx.paint("blue", rust=0.5, seed=81), 14, name="tee_body", roll=90.0))
    run.append(gx.rod((s0, 0.0, Z), (s0, -1.5 * HV, Z), R, gx.pipe_paint("grey", 82), name="branch"))
    run.append(geo.lathe([(R * 1.3, 0.0), (R * 1.3, 0.3)], (s0, -0.12, Z), gx.paint("blue", rust=0.5, seed=82), 14, name="tee_neck", tilt=90.0))
    run += gx.put(half_flange(0.0, Z, 83, 1.0), (s0, -1.5 * HV, 0.0), rot=-90.0)
    run += gx.put(gx.saddle(0.0, kind="blocks", seed=11), (s0, -HV, 0.0), rot=90.0)
    run += gx.saddle(su(1, n) - 0.1, kind="sleeper", seed=12)
    set_u(run, n)


@piece("gr_pipe_tee_v", title="Pipe Tee", desc="A cast tee. The branch was added later, and it shows.",
       footprint=[(0, 0), (0, 1), (1, 0)], **OPTS)
def gr_pipe_tee_v(ctx):
    L = 2 * HV
    run = straight(L, "green", 85)
    s0 = sv(0)
    run.append(geo.lathe([(R * 1.3, 0.0), (R * 1.3, 0.5)], (s0 - 0.25, 0.0, Z), gx.paint("oxide", rust=0.55, seed=85), 14, name="tee_body", roll=90.0))
    run.append(gx.rod((s0, 0.0, Z), (s0, -1.5 * HU, Z), R, gx.pipe_paint("oxide", 86), name="branch"))
    run.append(geo.lathe([(R * 1.3, 0.0), (R * 1.3, 0.3)], (s0, -0.12, Z), gx.paint("oxide", rust=0.55, seed=86), 14, name="tee_neck", tilt=90.0))
    run += gx.put(half_flange(0.0, Z, 87, 1.0), (s0, -1.5 * HU, 0.0), rot=-90.0)
    run += gx.put(gx.saddle(0.0, kind="sleeper", seed=13), (s0, -HU, 0.0), rot=90.0)
    run += gx.saddle(sv(1), kind="blocks", seed=14)
    set_v(run)


# ---------------------------------------------------------------------------- valves
@piece("gr_pipe_valve_u", title="Gate Valve", desc="A gate valve with a red hand wheel. The spindle is bright where hands have turned it.",
       footprint=[(0, 0), (1, 0)], **OPTS)
def gr_pipe_valve_u(ctx):
    n, L = 2, 2 * HU
    run = straight(L, "oxide", 91)
    run += gx.valve(L * 0.5, seed=91, colour="red", wheel="front", body="blue")
    run += gx.gauge(L * 0.14, seed=92)
    run += gx.saddle(L * 0.86, kind="blocks", seed=15)
    run.append(gx.stain((L * 0.5, -0.45), 0.3, (0.04, 0.03, 0.022), seed=3))
    set_u(run, n)


@piece("gr_pipe_valve_v", title="Gate Valve", desc="A gate valve, its yellow wheel chained so that nobody shuts the town's water off for fun.",
       footprint=[(0, 0), (0, 1)], **OPTS)
def gr_pipe_valve_v(ctx):
    L = 2 * HV
    run = straight(L, "green", 95)
    run += gx.valve(L * 0.5, seed=95, colour="yellow", wheel="top", body="oxide")
    run += gx.saddle(L * 0.14, kind="sleeper", seed=16)
    run.append(geo.cable((L * 0.5 + 0.2, 0.0, Z + 0.62), (L * 0.9, -0.1, Z + 0.1), sag=0.12, radius=0.02))
    set_v(run)


@piece("gr_pipe_manifold", title="Valve Manifold", desc="Three valves, a bypass loop and two gauges that disagree. Walter knows which wheel does what; nobody else does.",
       footprint=gx.row_hexes(0, 5), **OPTS)
def gr_pipe_manifold(ctx):
    n, L = 6, 6 * HU
    run = straight(L, "oxide", 101, joints=(L * 0.5,), sections=[(L * 0.5, L * 0.82, "green")])
    run += gx.valve(L * 0.17, seed=101, colour="red", wheel="front", body="blue")
    run += gx.valve(L * 0.66, seed=102, colour="yellow", wheel="front", body="oxide")
    run += gx.valve(L * 0.88, seed=103, colour="red", wheel="top", body="grey")
    run += gx.gauge(L * 0.33, seed=104) + gx.gauge(L * 0.5 + 0.2, seed=105)
    # bypass loop: a thinner pipe that leaves the main, arches over the middle valve and rejoins
    run.append(gx.bend([(L * 0.42, 0.0, Z + R), (L * 0.42, 0.0, Z + 0.95), (L * 0.80, 0.0, Z + 0.95), (L * 0.80, 0.0, Z + R)], radius=0.075, colour="grey", seed=106,
                       corner=0.22))
    run.append(geo.lathe([(0.1, 0.0), (0.1, 0.12)], (L * 0.6, 0.0, Z + 0.95), gx.paint("red", rust=0.4, seed=107), 10, name="bypass_valve", roll=90.0))
    run += gx.put(gx.handwheel(0.13, "red", 108), (L * 0.6 + 0.06, 0.0, Z + 1.1), tilt=90.0)
    # a vent stack with a cowl at the screen-left end
    run.append(gx.rod((0.3, 0.0, Z + R - 0.02), (0.3, 0.0, 1.9), 0.06, gx.pipe_paint("grey", 109), 10, name="vent"))
    run.append(geo.lathe([(0.0, 0.14), (0.16, 0.0), (0.13, 0.0), (0.0, 0.1)], (0.3, 0.0, 1.88), gx.iron(0.6, 3), 10, name="cowl"))
    run += gx.saddle(su(5, n), kind="blocks", seed=17) + gx.saddle(su(3, n) + 0.12, kind="cradle", seed=18) + gx.saddle(su(0, n) - 0.1, kind="blocks", seed=19)
    run += gx.drip(L * 0.5, seed=12, pool=0.5)
    set_u(run, n)


# ----------------------------------------------------------------------------- walls
def collar(x, seed, side=1.0):
    """The plate where a pipe goes through a wall (local x = the wall's face, the pipe to +x)."""
    plate = gx.paint("grey", rust=0.6, seed=seed)
    made = [geo.box((0.035, 0.62, 0.62), (x + side * 0.018, 0.0, Z - 0.31), 0.0, plate, bevel=0.006, name="collar")]
    for dy in (-0.25, 0.25):
        for dz in (-0.25, 0.25):
            made.append(geo.box((0.03, 0.05, 0.05), (x + side * 0.045, dy, Z + dz), 0.0, mat.flat((0.05, 0.045, 0.04), roughness=0.5, metallic=0.5), bevel=0.0,
                                name="collar_bolt", centred=True))
    made.append(gx.quad([(x + side * 0.04, -0.2, Z - 0.3), (x + side * 0.04, 0.2, Z - 0.3), (x + side * 0.04, 0.06, 0.02), (x + side * 0.04, -0.1, 0.02)],
                        mat.flat(gx.STREAK, roughness=0.95), "collar_run"))
    return gx.no_block(made)


@piece("gr_pipe_wall_u", title="Pipe Through Wall", desc="The main goes through the wall here, in a collar of plate that somebody cut with a torch.",
       footprint=[(1, 0)], anchors=[(1, 0)], **OPTS)
def gr_pipe_wall_u(ctx):
    # the wall stands on the origin hex's column; the pipe covers hex (1, 0) and ends on the boundary to (2, 0)
    face = G.STOCK_WALL_FRONT_V + 0.01
    end = 1.5 * HU
    made = [gx.rod((face, 0.0, Z), (end, 0.0, Z), R, gx.pipe_paint("oxide", 111), name="pipe")]
    made += gx.put(half_flange(0.0, Z, 111, 1.0), (end, 0.0, 0.0))
    made += collar(face, 112)
    made += gx.put(gx.clamp(0.0, seed=13, kind="rag", length=0.26), (HU * 0.8, 0.0, 0.0))


@piece("gr_pipe_wall_v", title="Pipe Collar", desc="A collar of plate where the main goes through the wall.",
       footprint=[], anchors=[(0, 0)], **OPTS)
def gr_pipe_wall_v(ctx):
    face = -HV + G.STOCK_WALL_FRONT_U + 0.01           # the front of a wall on the row behind the origin's
    made = [gx.rod((0.0, face, Z), (0.0, -HV / 2.0, Z), R, gx.pipe_paint("oxide", 115), name="pipe")]
    made += gx.put(collar(0.0, 116), (0.0, face, 0.0), rot=90.0)


# ------------------------------------------------------------------------- crossings
def ramp(length, seed):
    """Canonical: a pipe along local x, sunk to its middle, with a ramp of planks and one chequer
    plate laid over it (people cross along local y)."""
    made = [gx.rod((0.0, 0.0, 0.02), (length, 0.0, 0.02), R, gx.pipe_paint("oxide", seed), name="pipe")]
    made += half_flange(0.0, 0.02, seed, -1.0) + half_flange(length, 0.02, seed + 1, 1.0)
    r = geo.rng(seed)
    w = 0.26
    count = int((length - 0.36) / w)
    x = (length - count * w) / 2.0
    for k in range(count):
        if k == count // 2:
            made.append(geo.box((w - 0.02, 1.25, 0.03), (x + w / 2.0, 0.0, 0.17), 0.0, gx.paint("grey", rust=0.6, seed=seed + k), bevel=0.004, name="ramp_plate"))
        else:
            for side in (-1.0, 1.0):
                made.append(bx.plank((x + w / 2.0, side * 0.62 + r.uniform(-0.04, 0.04), 0.01), (x + w / 2.0 + r.uniform(-0.02, 0.02), 0.0, 0.2), w - 0.03, 0.035,
                                     gx.wood(seed=seed + k, grey=r.uniform(0.2, 0.6)), name="ramp_plank"))
        x += w
    for side in (-1.0, 1.0):
        made.append(gx.quad([(0.12, side * 0.2, 0.004), (length - 0.12, side * 0.2, 0.004), (length - 0.2, side * 0.75, 0.004), (0.2, side * 0.75, 0.004)],
                            mat.flat((0.09, 0.07, 0.05), roughness=1.0), "ramp_dirt"))
    return gx.no_block(made)


@piece("gr_pipe_ramp_u", title="Pipe Crossing", desc="Planks and a chequer plate laid over the main where everybody walks.",
       footprint=[], anchors=[(0, 0), (1, 0)], shadow="none", material="wood")
def gr_pipe_ramp_u(ctx):
    set_u(ramp(2 * HU, 121), 2)


@piece("gr_pipe_ramp_v", title="Pipe Crossing", desc="Planks and a chequer plate laid over the main where everybody walks.",
       footprint=[], anchors=[(0, 0), (0, 1)], shadow="none", material="wood")
def gr_pipe_ramp_v(ctx):
    set_v(ramp(2 * HV, 125))


# -------------------------------------------------------------------------- overhead
def riser(length, x_riser, ground_first, colour, seed):
    """Canonical two-hex riser: ground run on one side of x_riser, overhead run on the other."""
    if ground_first:
        points = [(0.0, 0.0, Z), (x_riser, 0.0, Z), (x_riser, 0.0, HI), (length, 0.0, HI)]
    else:
        points = [(0.0, 0.0, HI), (x_riser, 0.0, HI), (x_riser, 0.0, Z), (length, 0.0, Z)]
    made = [gx.bend(points, colour=colour, seed=seed, corner=0.3)]
    made += half_flange(0.0, points[0][2], seed, -1.0) + half_flange(length, points[-1][2], seed + 1, 1.0)
    # what holds it up: a timber post beside the riser with two strap bands, a concrete foot
    side = -0.26
    made += gx.post((x_riser + 0.02, side, 0.0), HI + 0.2, "timber", seed, size=0.13)
    for z in (0.9, 1.75):
        made.append(geo.box((0.4, 0.5, 0.06), (x_riser, side / 2.0, z), 0.0, gx.iron(0.7, seed), bevel=0.01, name="riser_strap"))
    made.append(geo.box((0.55, 0.6, Z - R + 0.04), (x_riser, -0.05, 0.0), 12.0, mat.concrete(seed=seed), bevel=0.03, name="riser_foot"))
    made += gx.put(gx.flange(0.0, 0.0, R, seed + 2), (x_riser, 0.0, 1.3), roll=-90.0)
    made.append(gx.streak(gx.Frame((x_riser, -R - 0.004, 0.0), 0.0), 0.0, 1.25, 0.6, 0.08, d=0.0))
    return made


@piece("gr_pipe_rise_ua", title="Pipe Riser", desc="The main climbs a post here and goes on over people's heads.",
       footprint=[(0, 0), (1, 0)], see_through=True, **OPTS)
def gr_pipe_rise_ua(ctx):
    set_u(riser(2 * HU, su(0, 2), True, "oxide", 131), 2)


@piece("gr_pipe_rise_ub", title="Pipe Riser", desc="The main comes down a post here from over people's heads.",
       footprint=[(0, 0), (1, 0)], see_through=True, **OPTS)
def gr_pipe_rise_ub(ctx):
    set_u(riser(2 * HU, su(1, 2), False, "green", 135), 2)


@piece("gr_pipe_rise_va", title="Pipe Riser", desc="The main climbs a post here and goes on over people's heads.",
       footprint=[(0, 0), (0, 1)], see_through=True, **OPTS)
def gr_pipe_rise_va(ctx):
    set_v(riser(2 * HV, sv(0), True, "oxide", 141))


@piece("gr_pipe_rise_vb", title="Pipe Riser", desc="The main comes down a post here from over people's heads.",
       footprint=[(0, 0), (0, 1)], see_through=True, **OPTS)
def gr_pipe_rise_vb(ctx):
    set_v(riser(2 * HV, sv(1), False, "oxide", 145))


def high(length, colour, seed, extra="rag"):
    made = straight(length, colour, seed, z=HI, joints=(length * 0.5,))
    if extra == "rag":
        # washing somebody hung on the pipe
        f = gx.Frame((0.0, -R - 0.01, 0.0), 0.0)
        for k, (x, w, h, c) in enumerate(((length * 0.22, 0.4, 0.5, (0.36, 0.33, 0.25)), (length * 0.34, 0.3, 0.36, (0.30, 0.10, 0.07)))):
            made.append(gx.sx.cloth(f, x, HI + R * 0.4, w, h, gx.canvas(c, seed=seed + k), seed=seed + k))
    else:
        made += gx.clamp(length * 0.3, HI, seed=seed, kind="sleeve")
        made += gx.hang((length * 0.72, 0.0, HI - R), "shoe", seed=seed, drop=0.3)
    return gx.no_block(made)


@piece("gr_pipe_hi_u4", title="Overhead Main", desc="The main, slung over the path. Somebody dries rags on it.",
       footprint=[], anchors=gx.row_hexes(0, 3), shadow="none", material="metal")
def gr_pipe_hi_u4(ctx):
    set_u(high(4 * HU, "oxide", 151, "rag"), 4)


@piece("gr_pipe_hi_v4", title="Overhead Main", desc="The main, slung over the path. A pair of boots hangs from it by the laces.",
       footprint=[], anchors=gx.col_hexes(0, 3), shadow="none", material="metal")
def gr_pipe_hi_v4(ctx):
    set_v(high(4 * HV, "oxide", 155, "shoe"))


def trestle(length, x_post, seed):
    made = straight(length, "oxide", seed, z=HI)
    made += gx.post((x_post, 0.0, 0.0), HI - R, "timber", seed, size=0.15, foot="stones")
    made.append(geo.box((0.2, 0.62, 0.1), (x_post, 0.0, HI - R - 0.1), 0.0, gx.wood((0.21, 0.13, 0.07), seed=seed, axis="Y", grey=0.4), bevel=0.01, name="cross_head"))
    for side in (-1.0, 1.0):
        made.append(bx.beam((x_post, 0.0, HI - 1.0), (x_post, side * 0.28, HI - R - 0.1), (0.07, 0.07), gx.wood(seed=seed + 2, grey=0.4), name="knee"))
        made.append(bx.beam((x_post + side * 0.05, 0.0, HI - 1.05), (x_post + side * 0.55, 0.0, HI - R - 0.02), (0.07, 0.07), gx.wood(seed=seed + 3, grey=0.4), name="knee"))
    made.append(geo.lathe([(R + 0.012, 0.0), (R + 0.012, 0.08)], (x_post - 0.04, 0.0, HI), gx.iron(0.7, seed), 14, name="strap", roll=90.0))
    return made


@piece("gr_pipe_post_u", title="Pipe Trestle", desc="A post with a cross head that carries the main overhead.",
       footprint=[(0, 0)], see_through=True, **OPTS)
def gr_pipe_post_u(ctx):
    set_u(trestle(2 * HU, su(0, 2), 161), 2)


@piece("gr_pipe_post_v", title="Pipe Trestle", desc="A post with a cross head that carries the main overhead.",
       footprint=[(0, 0)], see_through=True, **OPTS)
def gr_pipe_post_v(ctx):
    set_v(trestle(2 * HV, sv(0), 165))
