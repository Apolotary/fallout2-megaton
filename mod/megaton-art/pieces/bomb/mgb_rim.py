# SPDX-License-Identifier: MIT
"""The crater's rim: a kit that rings the pool and makes it read as the bottom of a bowl.

The engine has no height, so the bowl is suggested the way the stock art suggests ledges: on the
FAR side of the pool a low retaining wall shows its face (scrap sheet and planks held by driven
posts, sandbags and a lip of earth on top: the ground behind it reads as higher); on the NEAR
side, where a retaining wall would show nothing but its back, a pipe railing and sandbags mark
the edge of the drop; plank steps lie in the gaps where the town's paths come down.

RETAINING WALL (kind "wall", but light and sight pass: it is waist high). One piece per ground
direction a face can be seen from; each is a straight run that chains with copies of itself:

    piece        runs along (screen)                 blocks (hexes)                 next copy at
    mgb_rim_u    a hex row, rising to the right      (0..3, 0)                      (+4, 0) / (-4, 0)
    mgb_rim_u2   the same, other scrap               (0..3, 0)
    mgb_rim_h    dead level, facing the camera       (0,0) (1,0) (2,-1) (3,-1)      (+4, -2) / (-4, +2)
    mgb_rim_v    a hex column, falling to the right  (0, 0) (0, 1)                  (0, +2) / (0, -2)
    mgb_rim_w    the third hex axis, rising steeply  (-1,0) (0,0) (1,1) (2,1)       (+4, +2) / (-4, -2)
    mgb_rim_end  a wall's end: sandbags, a post, a tyre. One hex; put it on the hex after a run.

  A far arc from screen-left to right is: w ... u ... h ... v (each turn is 30 or 60 degrees on the
  ground). The faces look at the pool, so w / u go on the left half, v on the right half.

RAILING (scenery), for the near side: mgb_rail_u, mgb_rail_h, mgb_rail_v with the same hexes and
steps as the walls; mgb_sandbags / mgb_sandbags_b are one-hex piles for the diagonals and ends.

STEPS (scenery, do not block): mgb_step_u lies across a path that runs along a hex column (the
track from the gate, the path from the saloon), mgb_step_v across a path along a hex row (the
lanes to the water plant and to Lucy's). Lay three or four on successive hexes of the path.
mgb_boards_u / _v are duckboards for the wet ground inside the rim.

HOW THE CUTS SORT. A part is painted in tile order (hy * 200 + hx) of the hex it is anchored on.
 - a run along a hex ROW is one part: every hex whose number lies between those of its ends is
   under the run itself, so nobody can be painted "in between".
 - runs along the other axes get one part per pair of hexes with consecutive numbers ((0,0)+(1,0),
   (1,1)+(2,1) ...): the pictures of the two halves overlap nobody who could stand between them.
 - the steps and boards lie on and in front of their own hex, so whoever stands on the hex or
   nearer is painted over them and nobody further back is covered.
The walls throw no ground shadow on purpose: a shadow behind a retaining wall would say that the
ground there is as low as in front.
"""
import math

from mathutils import Matrix, Vector

from kit import piece, geo, mat, G
from kit import bomb_extra as bx

FLOOR = (0.215, 0.172, 0.122)       # dry crater dirt: matches the stock desert floor under the kit's light
STEP = G.SQ_U_M / 2.0               # 0.693 m: one hex along a row
HEXD = G.HEX_M                      # 0.8 m: one hex along the other two axes

# run name -> (rotation of local +x, start point, length, blocked hexes, anchors)
RUNS = {
    "u": (geo.U, (G.hex_xy(3, 0)[0] + STEP / 2.0, 0.0), 4 * STEP, [(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 0)]),
    "h": (geo.SCREEN, tuple(Vector(G.hex_xy(3, -1)) + Vector((0.866, -0.5)) * HEXD / 2.0), 4 * HEXD,
          [(0, 0), (1, 0), (2, -1), (3, -1)], [(0, 0), (2, -1)]),
    "v": (geo.V, (0.0, -0.06), 2 * HEXD, [(0, 0), (0, 1)], [(0, 0), (0, 1)]),
    "w": (210.0, tuple(Vector(G.hex_xy(3, 2)) - Vector((0.866, 0.5)) * 0.06), 4 * HEXD,
          [(-1, 0), (0, 0), (1, 1), (2, 1)], [(0, 0), (2, 1)]),
}


def place_run(objects, run):
    rot, start, _, _, _ = RUNS[run]
    return bx.move(bx.flat_list(objects), bx.turned(rot, (start[0], start[1], 0.0)))


def earth_lip(length, seed, depth=0.52, top=0.8):
    """The ground behind a retaining wall, as far as the camera can see it: a strip level with
    the wall's top that rounds off backwards. Local frame: x along the wall, +y behind it."""
    def height(x, y):
        h = top + 0.04 * bx.fbm(x, y, seed, 2.0, 2)
        if y > depth * 0.72:
            h -= 0.22 * ((y - depth * 0.72) / (depth * 0.28)) ** 2
        return h

    return bx.heightfield(-0.02, length + 0.02, 0.04, depth, height,
                          bx.mud(colour=(0.12, 0.09, 0.06), wet=0.1, seed=seed, cracks=0.35, dry=FLOOR), step=0.06, name="earth")


def revetment(length, seed, style="tin", bags=True, posts=None):
    """A waist-high retaining wall in its local frame: x 0..length along the run, its face on -y,
    the retained earth on +y. Posts stand in FRONT of the sheeting (they hold it against the earth)."""
    r = geo.rng(seed)
    steel = mat.steel(rust=0.8, seed=seed)
    parts = []
    top = 0.80
    if posts is None:
        count = max(2, int(round(length / 0.95)))
        posts = [0.1 + (length - 0.2) * i / (count - 1) for i in range(count)]
    for k, x in enumerate(posts):
        h = top + r.uniform(0.12, 0.3)
        if (k + seed) % 3 == 1:
            parts.append(geo.pipe([(x, -0.07, 0.0), (x + r.uniform(-0.03, 0.03), -0.09, h)], 0.045, steel, name="picket"))
        else:
            parts.append(geo.ibeam(h, (x, -0.07, 0.0), 0.0, steel, height=0.11, width=0.09, vertical=True,
                                   tilt=r.uniform(-4, 1), roll=r.uniform(-3, 3), name="post"))
    # sheeting
    x = 0.0
    index = 0
    while x < length - 0.04:
        w = min(r.uniform(0.75, 1.25), length - x)
        if length - (x + w) < 0.35:
            w = length - x
        kind = style if style != "mixed" else ("tin", "planks", "plate")[(index + seed) % 3]
        z0 = r.uniform(0.0, 0.03)
        if kind == "tin":
            sheet = geo.corrugated_panel(w + 0.04, top + r.uniform(-0.06, 0.05), (x - 0.02, 0.0, z0), 0.0,
                                         mat.corrugated(rust=r.uniform(0.5, 0.85), seed=seed * 3 + index,
                                                        paint=r.choice([None, None, (0.17, 0.22, 0.21), (0.30, 0.10, 0.06)])),
                                         wavelength=0.11, depth=0.035, horizontal=True, name="sheet")
            parts.append(sheet)
        elif kind == "planks":
            wood = mat.planks(colour=(0.22, 0.12, 0.055), axis="X", width=0.6, grey=0.3, seed=seed + index)
            z = z0
            while z < top - 0.1:
                bh = r.uniform(0.17, 0.23)
                parts.append(geo.box((w - 0.02, 0.035, bh - 0.015), (x + w / 2.0, 0.0, z), 0.0, wood, bevel=0.006,
                                     name="board", roll=r.uniform(-1.5, 1.5)))
                z += bh
        else:
            plate = mat.painted_metal(r.choice([(0.09, 0.12, 0.13), (0.17, 0.13, 0.05), (0.14, 0.05, 0.035)]), flaking=0.75,
                                      seed=seed + index)
            parts.append(geo.box((w - 0.02, 0.03, top - 0.03 + r.uniform(-0.08, 0.04)), (x + w / 2.0, 0.0, z0), 0.0, plate,
                                 bevel=0.01, name="plate", tilt=r.uniform(-3, 1)))
        x += w
        index += 1
    parts.append(earth_lip(length, seed, top=top - 0.02))
    if bags:
        parts += bx.sandbag_row((0.02, 0.2), (length - 0.02, 0.2), seed=seed, z=top - 0.03,
                                skip=(r.randrange(1, max(2, int(length / 0.6))),) if length > 2.0 else ())
        if length > 2.0:                                     # a second course on part of the run
            a = r.uniform(0.2, length * 0.4)
            parts += bx.sandbag_row((a, 0.24), (a + r.uniform(0.9, 1.3), 0.24), seed=seed + 5, z=top + 0.12)
    return bx.flat_list(parts)


def wall_piece(name, run, seed, style, title="Retaining Wall",
               desc="Scrap sheet and sandbags holding back the crater's slope."):
    rot, start, length, hexes, anchors = RUNS[run]

    @piece(name, title=title, desc=desc, kind="wall", sight="through", footprint=hexes, anchors=anchors, shadow="none",
           material="metal", convert={"forbid": ["purple", "rose"]})
    def build(ctx):
        place_run(revetment(length, seed, style), run)
    return build


wall_piece("mgb_rim_u", "u", 3, "mixed")
wall_piece("mgb_rim_u2", "u", 8, "tin")
wall_piece("mgb_rim_h", "h", 5, "mixed")
wall_piece("mgb_rim_v", "v", 2, "planks")
wall_piece("mgb_rim_w", "w", 6, "mixed")


@piece("mgb_rim_end", title="Sandbags", desc="The end of the retaining wall: sandbags, a tire, a post with a rag on it.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", material="dirt", convert={"forbid": ["purple", "rose"]})
def mgb_rim_end(ctx):
    r = geo.rng(4)
    for layer, count in enumerate((3, 2, 1)):
        for i in range(count):
            angle = 25.0 + r.uniform(-12, 12) + (90.0 if layer == 1 else 0.0)
            offset = (i - (count - 1) / 2.0) * 0.33
            bx.sandbag((offset * math.sin(math.radians(angle)) * -1.0, offset * math.cos(math.radians(angle)), layer * 0.16),
                       angle, seed=layer * 5 + i)
    geo.ibeam(1.25, (-0.28, -0.22, 0.0), 30.0, mat.steel(rust=0.8, seed=2.0), height=0.11, width=0.09, vertical=True, roll=4.0)
    geo.tire((0.33, 0.26, 0.0), radius=0.33, lying=False, rot=20.0, lean=-24.0, seed=4)
    bx.cloth(0.2, 0.34, (-0.3, -0.25, 1.22), 30.0, bx.cloth_mat((0.45, 0.07, 0.03), seed=3.0), flutter=0.03, seed=2, columns=3,
             rows=4, ragged=0.1)


def sandbag_pile(seed, layers=(2, 1), spread=0.3):
    r = geo.rng(seed)
    base = r.uniform(0, 180)
    for layer, count in enumerate(layers):
        for i in range(count):
            angle = base + r.uniform(-10, 10) + (90.0 if layer % 2 else 0.0)
            offset = (i - (count - 1) / 2.0) * spread * 1.15
            normal = (-math.sin(math.radians(angle)), math.cos(math.radians(angle)))
            bx.sandbag((normal[0] * offset, normal[1] * offset, layer * 0.16), angle, seed=seed * 7 + layer * 3 + i)


@piece("mgb_sandbags", title="Sandbags", desc="Sandbags, split and resewn.", footprint=[(0, 0)], anchors=[(0, 0)],
       shadow="baked", material="dirt", convert={"forbid": ["purple", "rose"]})
def mgb_sandbags(ctx):
    sandbag_pile(3, (2, 1))


@piece("mgb_sandbags_b", title="Sandbags", desc="A heap of sandbags with a plank thrown over it.", footprint=[(0, 0)],
       anchors=[(0, 0)], shadow="baked", material="dirt", convert={"forbid": ["purple", "rose"]})
def mgb_sandbags_b(ctx):
    sandbag_pile(9, (3, 2, 1), spread=0.28)
    bx.plank((-0.5, 0.12, 0.05), (0.42, -0.1, 0.52), 0.2, 0.04, mat.planks(axis="X", width=0.5, seed=4.0), name="plank")


# ------------------------------------------------------------------------------ railing
def railing(length, seed, kerb=True):
    """Pipe railing in its local frame (x 0..length): driven posts, two rails, a sandbag kerb."""
    r = geo.rng(seed)
    steel = mat.steel(rust=0.7, seed=seed)
    rail = mat.steel(rust=0.5, colour=(0.09, 0.09, 0.095), seed=seed + 1.0)
    count = max(2, int(round(length / 1.4)) + 1)
    xs = [0.06 + (length - 0.12) * i / (count - 1) for i in range(count)]
    parts = []
    tops = []
    for x in xs:
        h = 1.02 + r.uniform(-0.04, 0.05)
        lean = r.uniform(-0.03, 0.03)
        parts.append(geo.pipe([(x, 0.0, 0.0), (x + lean, 0.0, h)], 0.042, steel, name="rail_post"))
        parts.append(geo.box((0.16, 0.16, 0.05), (x, 0.0, 0.0), r.uniform(0, 60), steel, bevel=0.01, name="rail_foot"))
        tops.append((x + lean, 0.0, h))
    for level, radius in ((0.0, 0.034), (-0.46, 0.028)):
        points = [(-0.02, 0.0, tops[0][2] + level - 0.03)] + [(x, 0.0, z + level - 0.03) for x, _, z in tops] + \
                 [(length + 0.02, 0.0, tops[-1][2] + level - 0.03)]
        parts.append(geo.pipe(points, radius, rail, name="rail"))
    if kerb:
        parts += bx.sandbag_row((0.0, 0.16), (length, 0.16), seed=seed, z=0.0, skip=(r.randrange(0, 3),))
    return bx.flat_list(parts)


def rail_piece(name, run, seed, extra=None):
    rot, start, length, hexes, anchors = RUNS[run]

    @piece(name, title="Railing", desc="A railing of scaffold pipe along the edge of the crater's drop.",
           footprint=hexes, anchors=anchors, shadow="none", material="metal", convert={"forbid": ["purple", "rose"]})
    def build(ctx):
        parts = railing(length, seed)
        if extra:
            parts += extra(length)
        place_run(parts, run)
    return build


def _rag(length):
    return [bx.cloth(0.3, 0.4, (length * 0.62, -0.03, 0.99), 0.0, bx.cloth_mat((0.44, 0.30, 0.05), seed=6.0), flutter=0.04, seed=4,
                     columns=4, rows=4, ragged=0.12)]


rail_piece("mgb_rail_u", "u", 4, _rag)
rail_piece("mgb_rail_h", "h", 7)
rail_piece("mgb_rail_v", "v", 9)


# ------------------------------------------------------------------------------ steps and boards
def step(run_rot, width, seed):
    """One plank step in its local frame: the riser along local x through the hex centre, the tread
    in front of it (-y is in front for the kit's rotations)."""
    r = geo.rng(seed)
    wood = mat.planks(colour=(0.40, 0.25, 0.12), axis="X", width=0.7, grey=0.25, seed=seed)
    dark = mat.planks(colour=(0.13, 0.07, 0.035), axis="X", width=0.7, grey=0.1, seed=seed + 2.0)
    parts = [geo.box((width, 0.045, 0.17), (0.0, 0.0, 0.0), 0.0, dark, bevel=0.006, name="riser")]
    for k in range(2):
        parts.append(geo.box((width - r.uniform(0.0, 0.1), 0.2, 0.04), (r.uniform(-0.03, 0.03), -0.13 - 0.215 * k, 0.045 - 0.02 * k),
                             r.uniform(-2.5, 2.5), wood, bevel=0.006, name="tread"))
    for sx in (-1, 1):                                               # pegs that hold the riser
        parts.append(geo.box((0.06, 0.06, 0.24), (sx * (width / 2.0 - 0.06), 0.05, 0.0), 0.0, dark, bevel=0.008, name="peg"))
    return bx.no_block(bx.move(parts, bx.turned(run_rot)))


@piece("mgb_step_u", title="Plank Step", desc="A plank set on edge and a tread nailed to it: one step of the way down to the pool.",
       footprint=[], anchors=[(0, 0)], shadow="none", material="wood")
def mgb_step_u(ctx):
    step(geo.U, 1.5, 3)


@piece("mgb_step_v", title="Plank Step", desc="A plank set on edge and a tread nailed to it: one step of the way down to the pool.",
       footprint=[], anchors=[(0, 0)], shadow="none", material="wood")
def mgb_step_v(ctx):
    step(geo.V, 1.5, 6)


def boards(run_rot, length, width, seed):
    """Duckboards in their local frame: planks along local x from 0 to length on two sleepers,
    lying from y = -width .. 0.05 (in front of the hex line)."""
    r = geo.rng(seed)
    parts = []
    dark = mat.planks(colour=(0.14, 0.08, 0.04), axis="X", width=0.5, seed=seed + 1.0)
    for x in (0.2, length - 0.2):
        parts.append(geo.box((0.1, width + 0.08, 0.06), (x, -width / 2.0 + 0.03, 0.0), 0.0, dark, bevel=0.006, name="sleeper"))
    count = max(2, int(round(width / 0.2)))
    for k in range(count):
        y = 0.03 - (k + 0.5) * width / count
        wood = mat.planks(colour=(0.36 + 0.06 * (k % 2), 0.23, 0.11), axis="X", width=0.9, grey=0.3, seed=seed * 3 + k)
        gap = r.uniform(0.0, 0.12)
        parts.append(geo.box((length - gap, width / count - 0.02, 0.035), (length / 2.0 + r.uniform(-0.04, 0.04), y, 0.06),
                             r.uniform(-1.2, 1.2), wood, bevel=0.005, name="duckboard"))
    return bx.no_block(bx.move(parts, bx.turned(run_rot)))


@piece("mgb_boards_u", title="Duckboards", desc="Planks on sleepers, to keep feet out of the glowing mud.",
       footprint=[], anchors=[(0, 0)], shadow="none", material="wood")
def mgb_boards_u(ctx):
    # two hexes of a row: from half a hex right of the origin hex to half a hex left of the next
    bx.move(boards(0.0, 2 * STEP, 0.62, 5), bx.turned(geo.U, (STEP * 1.5, 0.2, 0.0)))


@piece("mgb_boards_v", title="Duckboards", desc="Planks on sleepers, to keep feet out of the glowing mud.",
       footprint=[], anchors=[(0, 0)], shadow="none", material="wood")
def mgb_boards_v(ctx):
    # one hex of a column, lying from the hex centre towards the viewer
    bx.move(boards(0.0, HEXD, 0.62, 8), bx.turned(geo.V, (0.31, -0.02, 0.0)))
