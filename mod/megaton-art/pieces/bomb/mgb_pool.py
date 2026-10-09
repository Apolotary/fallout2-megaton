# SPDX-License-Identifier: MIT
"""The pool's edge: shore pieces with glowing water, the pipe to the water plant, a warning sign.

WATER  Every water surface here is tagged with the animated "slime" palette range (kit geo.set_fx):
in the engine those four greens cycle, so the water shimmers, and they are the only colours the
night does not darken, so the shore glows after dark. The stock goo floor of the pool does not
move; these pieces are what makes the pool look alive. Keep them on the pool's rim, where the
floor's goo meets the dirt.

    mgb_shore_a     a mud bank with a half-sunk tyre; the water laps in FRONT of it  -> far shore
    mgb_shore_b     a leaking drum on its side on a bank, a trickle of glowing water -> far shore, sides
    mgb_shore_c     rubble and a rib-cage with a puddle caught between them          -> anywhere
  One hex each, blocking that hex. Water never lies BEHIND the hex (somebody standing there would
  be painted before the piece and get his shins overpainted), only on it and in front.

    mgb_pipe_intake where the water plant's pipe leaves the pool: a strainer in the water, an
                    elbow, a gate valve with a red wheel. Hexes (0..2, 0) on a hex row, the pool
                    to the screen-left (higher hx), the pipe going off to the right.
    mgb_pipe_u      four hexes of the pipe on sleepers, a flanged joint, a clamp over a leak.
                    Hexes (0..3, 0); the next length stands at (-4, 0), the intake's origin at (+4, 0).
  A run along a hex row is one part (see pieces/bomb/mgb_rim.py for why).

    mgb_sign        DANGER and a radiation trefoil, hand-painted on a car door. One hex.

PLACEMENT in the town (placement.py, group "crater"): the pipe follows plan.PATHS' lane from the
pool to the plant ((92, 94) to (71, 93)) along hy 96, the row behind the clinic's back wall and out
of the lane's middle - the clinic's roof stands in front of that row, so only the intake and the
first length show; mgb_sign replaces SIGN_RADIATION at (95, 101).
"""
import math

import bmesh
from mathutils import Matrix, Vector

from kit import piece, geo, mat, G
from kit import bomb_extra as bx

STEP = G.SQ_U_M / 2.0
COMMON = dict(footprint=[(0, 0)], anchors=[(0, 0)], shadow="none", material="dirt", convert={"forbid": ["purple", "rose"]})


def bank(outline, seed, crest=0.2, x0=-0.75, x1=0.75, y0=-0.6, y1=0.7):
    """A lump of shore mud: outline(x, y) -> 0..1 (1 deep inside, 0 at its edge, < 0 outside)."""
    def height(x, y):
        inside = outline(x, y)
        if inside <= 0.0:
            return None
        return 0.014 + crest * min(1.0, inside * 1.6) ** 0.8 * (0.75 + 0.35 * bx.fbm(x, y, seed, 2.5, 3))

    return bx.heightfield(x0, x1, y0, y1, height, bx.mud(seed=seed, dry=(0.23, 0.18, 0.125)), step=0.04, name="bank")


def puddle(outline, seed, x0=-0.8, x1=0.8, y0=-0.3, y1=0.75):
    """Glowing water: a flat sheet where outline(x, y) > 0, in the animated slime colours."""
    sheet = bx.heightfield(x0, x1, y0, y1, lambda x, y: 0.012 if outline(x, y) > 0.0 else None,
                           bx.water(seed=seed, glow=0.5), step=0.04, name="water", smooth=False)
    geo.set_fx(sheet, "slime")
    return bx.no_block(sheet)


def stones(spots, seed):
    r = geo.rng(seed)
    stone = mat.concrete(colour=(0.21, 0.19, 0.16), cracks=0.25, seed=seed)
    out = []
    for x, y, size in spots:
        out.append(geo.box((size, size * r.uniform(0.6, 0.95), size * r.uniform(0.45, 0.75)), (x, y, -0.02), r.uniform(0, 180),
                           stone, bevel=0.03, name="stone", tilt=r.uniform(-16, 16), roll=r.uniform(-16, 16)))
    return bx.no_block(out)


@piece("mgb_shore_a", title="Pool Shore",
       desc="The pool's bank. A tire lies half under the water, and the water glows.", **COMMON)
def mgb_shore_a(ctx):
    def land(x, y):
        return 1.0 - math.hypot(x / 0.72, (y + 0.22) / 0.34) + 0.18 * bx.fbm(x, y, 3.0, 3.0, 2)

    def wet(x, y):
        return (1.0 - math.hypot(x / 0.78, (y - 0.2) / 0.46) + 0.2 * bx.fbm(x, y, 5.0, 2.5, 2)) if land(x, y) < 0.25 else -1.0

    bank(land, 3.0, crest=0.24)
    puddle(wet, 2.0)
    tire = geo.tire((0.2, 0.2, -0.08), radius=0.34, lying=True, lean=17.0, rot=40.0, seed=6)
    bx.clip_ground(tire, 0.012)
    stones([(-0.45, 0.02, 0.2), (-0.2, -0.05, 0.13), (0.55, -0.02, 0.16)], 4)


@piece("mgb_shore_b", title="Pool Shore",
       desc="A drum of something has been leaking into the pool since the War. The trickle glows.", **COMMON)
def mgb_shore_b(ctx):
    def land(x, y):
        return 1.0 - math.hypot((x + 0.1) / 0.66, (y + 0.2) / 0.36) + 0.18 * bx.fbm(x, y, 8.0, 3.0, 2)

    def wet(x, y):
        stream = 0.11 - abs(x - 0.18 - 0.1 * math.sin(y * 6.0)) if -0.05 < y < 0.3 else -1.0
        pool = 1.0 - math.hypot((x - 0.1) / 0.6, (y - 0.42) / 0.3) + 0.2 * bx.fbm(x, y, 6.0, 3.0, 2)
        return max(stream * 5.0, pool) if land(x, y) < 0.5 else -1.0

    bank(land, 8.0, crest=0.2)
    puddle(wet, 4.0)
    drum = geo.barrel((-0.42, -0.2, 0.36), radius=0.27, height=0.82, tilt=0.0, rot=0.0, seed=4,
                      material=mat.painted_metal((0.30, 0.22, 0.03), flaking=0.65, seed=5.0))
    drum.rotation_euler = (Matrix.Rotation(math.radians(-25.0), 4, "Z") @ Matrix.Rotation(math.radians(96.0), 4, "Y")).to_euler()
    bx.clip_ground(drum, 0.0)
    goo = geo.cylinder(0.2, 0.02, (0, 0, 0), bx.water(seed=1.0, glow=0.7), 14, name="drum_mouth")
    goo.matrix_world = drum.matrix_world @ Matrix.Translation((0, 0, 0.83))
    geo.set_fx(goo, "slime")
    stones([(0.5, 0.0, 0.17), (0.34, -0.2, 0.12)], 9)


@piece("mgb_shore_c", title="Pool Shore",
       desc="Rubble at the water's edge, and what the pool left of somebody who drank from it.", **COMMON)
def mgb_shore_c(ctx):
    def land(x, y):
        return 1.0 - math.hypot(x / 0.6, (y + 0.05) / 0.36) + 0.22 * bx.fbm(x, y, 12.0, 3.0, 2)

    def wet(x, y):
        return 0.9 - math.hypot((x + 0.12) / 0.3, (y - 0.14) / 0.18) + 0.15 * bx.fbm(x, y, 2.0, 4.0, 2)

    bank(land, 12.0, crest=0.1)
    puddle(wet, 6.0, y0=-0.2, y1=0.5)
    stones([(-0.5, -0.05, 0.22), (0.4, -0.12, 0.26), (0.2, 0.2, 0.13), (-0.3, -0.25, 0.15)], 13)
    bone = mat.flat((0.50, 0.46, 0.36), roughness=0.8)
    for k in range(5):                                               # a rib-cage, half buried
        x = 0.18 + k * 0.075
        arch = bx.ellipse_points((x, -0.02, 0.02), 0.15, 0.2 - 0.02 * abs(k - 2), 8, x=(0.2, 1, 0), y=(0, 0, 1), closed=False,
                                 start=0.0, sweep=180.0)
        bx.no_block(geo.pipe(arch, 0.014, bone, name="rib"))
    bx.no_block(geo.pipe([(0.12, -0.02, 0.215), (0.56, 0.06, 0.2)], 0.022, bone, name="spine"))


# -------------------------------------------------------------------------------- pipe
PIPE_R = 0.17
PIPE_Z = 0.36


def pipe_metal(seed):
    return bx.bomb_paint(colour=(0.10, 0.115, 0.11), rust=0.7, seed=seed, bleach=0.4)


def pipe_run(x0, x1, seed, y=0.0, flanges=(), clamp=None, sleepers=()):
    """A length of the plant's pipe along world X from x0 to x1 (axis at PIPE_Z)."""
    parts = []
    skin = pipe_metal(seed)
    body = geo.lathe([(PIPE_R, 0.0), (PIPE_R, abs(x1 - x0))], (0, 0, 0), skin, 20, name="pipe")
    body.matrix_world = Matrix.Translation((min(x0, x1), y, PIPE_Z)) @ Matrix.Rotation(math.radians(90.0), 4, "Y")
    parts.append(body)
    steel = mat.steel(rust=0.75, seed=seed + 1.0)
    for fx in flanges:
        ring = geo.lathe([(PIPE_R + 0.06, -0.035), (PIPE_R + 0.06, 0.035)], (0, 0, 0), steel, 20, name="flange")
        ring.matrix_world = Matrix.Translation((fx, y, PIPE_Z)) @ Matrix.Rotation(math.radians(90.0), 4, "Y")
        parts.append(ring)
        for i in range(8):
            a = 2 * math.pi * i / 8
            parts.append(geo.box((0.1, 0.05, 0.05), (fx, y + (PIPE_R + 0.03) * math.cos(a), PIPE_Z + (PIPE_R + 0.03) * math.sin(a)),
                                 0.0, steel, bevel=0.008, centred=True, name="flange_bolt"))
    if clamp is not None:
        band = geo.lathe([(PIPE_R + 0.025, -0.11), (PIPE_R + 0.025, 0.11)], (0, 0, 0),
                         mat.painted_metal((0.30, 0.09, 0.05), flaking=0.5, seed=seed), 20, name="clamp")
        band.matrix_world = Matrix.Translation((clamp, y, PIPE_Z)) @ Matrix.Rotation(math.radians(90.0), 4, "Y")
        parts.append(band)
        parts.append(geo.box((0.16, 0.07, 0.14), (clamp, y + 0.02, PIPE_Z + PIPE_R + 0.01), 0.0, steel, bevel=0.01, name="clamp_lug"))
    timber = mat.planks(colour=(0.20, 0.11, 0.05), axis="Y", width=0.4, grey=0.3, seed=seed)
    for sx in sleepers:
        parts.append(geo.box((0.2, 0.62, PIPE_Z - PIPE_R + 0.03), (sx, y, 0.0), 0.0, timber, bevel=0.01, name="sleeper"))
        for side in (-1, 1):
            parts.append(geo.box((0.18, 0.1, 0.13), (sx, y + side * 0.22, PIPE_Z - PIPE_R + 0.01), 0.0, timber, bevel=0.01,
                                 name="chock", roll=0.0, tilt=side * 28.0))
    return parts


@piece("mgb_pipe_u", title="Water Pipe",
       desc="The water plant's intake pipe. It sweats where it has been patched.",
       footprint=[(0, 0), (1, 0), (2, 0), (3, 0)], anchors=[(0, 0)], shadow="baked", material="metal",
       convert={"forbid": ["purple", "rose"]})
def mgb_pipe_u(ctx):
    x_right = -STEP / 2.0
    x_left = 3.5 * STEP
    pipe_run(x_left, x_right, 4.0, flanges=(1.55 * STEP,), clamp=2.65 * STEP, sleepers=(0.45 * STEP, 2.3 * STEP))
    # the leak under the clamp: a dark run-off and a small glowing puddle
    def wet(x, y):
        return 1.0 - math.hypot((x - 2.65 * STEP) / 0.26, (y - 0.3) / 0.16)

    puddle(wet, 3.0, x0=1.4, x1=2.3, y0=0.05, y1=0.55)


@piece("mgb_pipe_intake", title="Pipe Intake",
       desc="Where the water plant drinks from the pool: a strainer, an elbow and a gate valve with a red wheel.",
       footprint=[(0, 0), (1, 0), (2, 0)], anchors=[(0, 0)], shadow="baked", material="metal",
       convert={"forbid": ["purple", "rose"]})
def mgb_pipe_intake(ctx):
    x_right = -STEP / 2.0
    elbow_x = 1.75 * STEP
    parts = pipe_run(elbow_x, x_right, 7.0, flanges=(0.25 * STEP, elbow_x - 0.04), sleepers=(0.95 * STEP,))
    skin = pipe_metal(7.0)
    steel = mat.steel(rust=0.75, seed=3.0)
    # the elbow: the pipe turns down and towards the viewer into the water
    bend = [(elbow_x, 0.0, PIPE_Z), (elbow_x + 0.2, 0.03, PIPE_Z), (elbow_x + 0.36, 0.14, PIPE_Z - 0.06),
            (elbow_x + 0.45, 0.3, PIPE_Z - 0.2), (elbow_x + 0.48, 0.42, 0.0)]
    geo.pipe(bend, PIPE_R * 0.96, skin, name="elbow", resolution=12)
    # strainer: a cage of bars round the mouth, standing in the water
    cx, cy = elbow_x + 0.48, 0.46
    for i in range(8):
        a = 2 * math.pi * i / 8
        bx.no_block(geo.pipe([(cx + 0.27 * math.cos(a), cy + 0.27 * math.sin(a), 0.0),
                              (cx + 0.2 * math.cos(a), cy + 0.2 * math.sin(a), 0.34)], 0.016, steel, name="strainer_bar"))
    bx.no_block(geo.pipe(bx.ellipse_points((cx, cy, 0.17), 0.24, 0.24, 14), 0.016, steel, name="strainer_hoop"))

    def wet(x, y):
        return 1.0 - math.hypot((x - cx) / 0.62, (y - cy - 0.05) / 0.4) + 0.15 * bx.fbm(x, y, 4.0, 3.0, 2)

    puddle(wet, 5.0, x0=cx - 0.7, x1=cx + 0.7, y0=0.02, y1=0.95)
    # gate valve: a body on the pipe, a spindle, a red handwheel facing the viewer
    vx = 0.62 * STEP
    geo.box((0.3, 0.42, 0.42), (vx, 0.0, PIPE_Z - 0.21), 0.0, mat.painted_metal((0.08, 0.10, 0.12), flaking=0.5, seed=2.0),
            bevel=0.03, name="valve_body")
    geo.pipe([(vx, 0.0, PIPE_Z + 0.2), (vx, 0.0, PIPE_Z + 0.62)], 0.035, steel, name="spindle")
    red = mat.painted_metal((0.42, 0.035, 0.02), flaking=0.25, seed=4.0)
    wheel_c = (vx, 0.0, PIPE_Z + 0.6)
    bx.no_block(geo.pipe(bx.ellipse_points(wheel_c, 0.24, 0.24, 18, x=(1, 0, 0), y=(0, 1, 0)), 0.032, red, name="wheel"))
    for i in range(3):
        a = math.pi * i / 3
        bx.no_block(geo.pipe([(vx - 0.23 * math.cos(a), -0.23 * math.sin(a), PIPE_Z + 0.6),
                              (vx + 0.23 * math.cos(a), 0.23 * math.sin(a), PIPE_Z + 0.6)], 0.02, red, name="spoke"))


# -------------------------------------------------------------------------------- sign
def trefoil(centre, size, x, y, material, thickness=0.012):
    """Radiation trefoil in the plane spanned by x and y: three 60-degree blades and a hub."""
    c, x, y = Vector(centre), Vector(x).normalized(), Vector(y).normalized()
    n = x.cross(y).normalized()
    bm = bmesh.new()
    inner, outer = size * 0.2, size * 0.5

    def ring_point(radius, angle):
        return c + x * (radius * math.cos(angle)) + y * (radius * math.sin(angle))

    for blade in range(3):
        a0 = math.radians(90.0 + 120.0 * blade - 30.0)
        steps = 6
        ring_in = [bm.verts.new(ring_point(inner, a0 + math.radians(60.0) * i / steps)) for i in range(steps + 1)]
        ring_out = [bm.verts.new(ring_point(outer, a0 + math.radians(60.0) * i / steps)) for i in range(steps + 1)]
        for i in range(steps):
            bm.faces.new((ring_in[i], ring_in[i + 1], ring_out[i + 1], ring_out[i]))
    hub = [bm.verts.new(ring_point(size * 0.11, 2 * math.pi * i / 12)) for i in range(12)]
    bm.faces.new(hub)
    obj = geo._finish(bm, "trefoil", material, (0, 0, 0), 0.0, "main", smooth=False, solidify=thickness)
    obj.location = n * (thickness / 2.0)
    bx.no_block(obj)
    return obj


@piece("mgb_sign", title="Warning Sign",
       desc="DANGER, and the three black blades everybody still knows. Somebody has added, smaller: DON'T DRINK IT.",
       footprint=[(0, 0)], anchors=[(0, 0)], shadow="baked", material="metal",
       convert={"forbid": ["purple", "rose"], "exposure": -0.3, "contrast": 1.3})
def mgb_sign(ctx):
    steel = mat.steel(rust=0.75, seed=6.0)
    parts = [geo.ibeam(2.15, (0.0, 0.03, 0.0), 0.0, steel, height=0.12, width=0.1, vertical=True, roll=-2.0, name="post"),
             geo.box((0.3, 0.3, 0.1), (0.0, 0.03, 0.0), 15.0, mat.concrete(seed=5.0), bevel=0.02, name="foot"),
             geo.pipe([(0.0, 0.06, 1.2), (-0.45, 0.5, 0.0)], 0.022, steel, name="stay")]
    # the board: a car door skin, yellow, hung from two bolts and slightly askew
    board = geo.box((1.3, 0.035, 1.22), (0.0, -0.045, 0.92), 0.0, mat.painted_metal((0.50, 0.37, 0.03), flaking=0.22, seed=9.0),
                    bevel=0.02, name="board", roll=-3.0)
    parts.append(board)
    skew = Matrix.Translation((0.0, -0.07, 0.92)) @ Matrix.Rotation(math.radians(-3.0), 4, "Y")
    black = bx.paint((0.02, 0.02, 0.022), wear=0.2, seed=2.0)
    mark = trefoil((0, 0, 0), 0.62, (1, 0, 0), (0, 0, 1), black)
    mark.matrix_world = skew @ Matrix.Translation((0.0, 0.0, 0.80)) @ mark.matrix_basis
    parts.append(mark)
    text = geo.lettering("DANGER", (0, 0, 0), 0.0, size=0.27, depth=0.012, bevel=0.0, font="impact", material=black, spacing=1.05)
    text.matrix_world = skew @ Matrix.Translation((0.0, 0.0, 0.11)) @ Matrix.Rotation(math.radians(90.0), 4, "X")
    parts.append(text)
    for sx in (-0.5, 0.5):
        bolt = geo.cylinder(0.035, 0.03, (0, 0, 0), steel, 8, name="bolt")
        bolt.matrix_world = skew @ Matrix.Translation((sx, 0.01, 1.1)) @ Matrix.Rotation(math.radians(90.0), 4, "X")
        parts.append(bolt)
    bx.move(bx.flat_list(parts), bx.turned(geo.SCREEN))
