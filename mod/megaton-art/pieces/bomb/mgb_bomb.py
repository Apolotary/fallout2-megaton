# SPDX-License-Identifier: MIT
"""THE BOMB: Megaton's undetonated atomic bomb, nose-down in its own crater, tail propped on a
trestle, dressed by the Children of Atom. Four pieces from one builder:

    mgb_bomb          dormant: access plate bolted shut
    mgb_bomb_rigged   plate open, Burke's fusion pulse charge fitted (red lamp: "alarm" palette
                      colour, it blinks in the engine without a script and at night)
    mgb_bomb_safe     disarmed: plate open, leads cut and hanging, a green tick and a tag
    mgb_bomb_states   the same three pictures as frames 0 / 1 / 2 of ONE sprite. This engine has no
                      opcode that changes an object's art, but `anim(self_obj, 1010, frame)`
                      (ANIMATE_SET_FRAME) is vanilla, keeps the object, its script and its local
                      variables. DO NOT let Placer.place() put its main part: that attaches the
                      stock "animate for ever" script and the bomb would cycle its states. Put
                      the main part yourself with the bomb script (placement.py how="object";
                      stage/town/build_stage.py does it and stage/town/mgbstate.ssl switches the frames).

FOOTPRINT (hexes from the origin = the town's BOMB spot, even hx / even hy)
    row  0:  hx -3 .. 2        the body's front edge; the origin hex is the object itself
    row -1:  hx -4 .. 4        under the body and the tail; (4, -1) is the hex at the nose: a critter there
                               would be painted BEFORE this one sprite and vanish behind the nose
                               (build.py sort found it), so it is blocked
    row -2:  hx -3 .. 3        the far side
The three hexes in front of the origin, (-1, 1) (0, 1) (1, 1), stay free: that is where the
town's bomb tests stand (layout/buildings.py BOMB_ACCESS), an arm's length from the access plate.

    mgb_bomb_shade    companion, same origin: the tail's ground shadow (flat) and a little rubble.
                      Optional; place it with Placer.place() on the bomb's hex.

ONE PART, anchored on the origin hex, and nothing else of the piece on that hex: the quest's
"use on" target is one object whatever the player clicks on. That sorts correctly because the piece runs along a hex ROW: everybody who can
stand behind it is on rows <= -3 (painted before it), everybody in front on rows >= 1 or on row 0
to the screen-left of the origin (painted after it), and the hexes at its ends where neither
would hold are inside the footprint. The ground shadow is a piece of its own (mgb_bomb_shade).

LIGHT  every bomb piece is an engine light (5 hexes, 85 %): lantern, candles and the glowing water
round the hull make it the lamp of the pool, and the sprite itself stays bright at night. The
water ring uses the animated "slime" greens, the flames "fire", the charge's lamp "alarm".

WORLD  the body's axis lies in the vertical plane y = YC, nose towards +X (screen lower-left),
tail up towards -X (screen upper-right), so the viewer and the player at the access hexes look at
its +Y flank, where the plate is. THETA is the pitch. All random detail uses fixed seeds, so the
four pieces differ only in what the quest state changes.
"""
import math

from mathutils import Matrix, Vector

from kit import piece, geo, mat, G
from kit import bomb_extra as bx

THETA = 27.0                    # pitch of the body, degrees
LENGTH, R = 4.6, 1.0            # nose tip to tail plate, largest radius (m)
TIP = (1.9, -1.15, -0.42)       # where the buried nose tip is
YC = TIP[1]
BELLY_END, TAIL_START = 2.55, 4.0    # the parallel belly ends, the tail tube starts (distance from the tip)
NOSE_JOINT, TAIL_JOINT = 1.45, 2.98  # bolted joints (flanges)
PLATE_D, PLATE_PHI = 2.18, 69.0      # access plate: distance from the tip, angle from "up" towards the viewer
TEXT_D, TEXT_PHI = 2.22, 37.0

FOOTPRINT = ([(hx, 0) for hx in range(-3, 3)] + [(hx, -1) for hx in range(-4, 5)]
             + [(hx, -2) for hx in range(-3, 4)])
STATES = ("dormant", "rigged", "safe")

_t = math.radians(THETA)
AXIS = Vector((-math.cos(_t), 0.0, math.sin(_t)))       # nose -> tail
UP = Vector((math.sin(_t), 0.0, math.cos(_t)))          # "up" across the body
SIDE = Vector((0.0, 1.0, 0.0))
M = bx.frame(TIP, x=UP, y=SIDE, z=AXIS)                 # body space (x up, y towards the viewer, z along) -> world


def radius(d):
    """Body radius at distance d from the nose tip: blunt ogive, parallel belly, boat tail, tail tube."""
    if d <= 0.0:
        return 0.0
    if d < 1.55:
        t = (1.55 - d) / 1.55
        return R * math.sqrt(max(0.0, 1.0 - t ** 2.4))
    if d < BELLY_END:
        return R
    if d < TAIL_START:
        t = (d - BELLY_END) / (TAIL_START - BELLY_END)
        return 0.36 + (R - 0.36) * (0.5 + 0.5 * math.cos(math.pi * t)) ** 0.85
    return 0.36 - 0.04 * (d - TAIL_START) / (LENGTH - TAIL_START)


BODY = bx.Lathe(radius, LENGTH, steps=92, segments=56)


def underside(x):
    """World height of the body's belly line above ground point (x, YC)."""
    best = None
    for i in range(400):
        d = LENGTH * i / 399
        p = Vector(TIP) + AXIS * d - UP * radius(d)
        if best is None or abs(p.x - x) < abs(best.x - x):
            best = p
    return best.z


def on_skin(objects, d, phi, lift=0.0, turn=0.0):
    """Place things built flat (x along the body, y up the skin, z out of it) onto the skin."""
    return bx.move(bx.flat_list(objects), M @ BODY.skin_frame(d, phi, lift, turn))


def skin_curve(points, d0, phi0, radius_m, material, lift=0.012, name="mark"):
    """A painted stroke: tube through 2D points (along, up) in metres around (d0, phi0), bent onto the skin."""
    world = []
    for along, up in points:
        d = d0 + along
        phi = phi0 - math.degrees(up / max(0.2, radius(d)))
        world.append(tuple(M @ BODY.point(d, phi, lift)))
    return geo.pipe(world, radius_m, material, name=name, resolution=4)


def skin_text(text, d0, phi, size, material, font="din", depth=0.012, gap=0.2):
    """Stencil lettering that follows the skin: every letter is its own flat glyph on the body.
    d0: where the run is centred. Reads from the nose end towards the tail (left to right on screen)."""
    import bpy
    glyphs = []
    for char in text:
        if char == " ":
            glyphs.append((None, size * 0.45))
            continue
        obj = geo.lettering(char, (0, 0, 0), 0.0, size, depth=depth, bevel=0.0, font=font, material=material,
                            align="LEFT", name="stencil")
        obj.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        glyphs.append((obj, obj.dimensions.x))
    total = sum(w for _, w in glyphs) + gap * size * (len(glyphs) - 1)
    d = d0 - total / 2.0
    for obj, width in glyphs:
        if obj is not None:
            obj.matrix_world = M @ BODY.skin_frame(d, phi + math.degrees(size * 0.5 / radius(d)), depth / 2.0 + 0.004)
        d += width + gap * size
    return [obj for obj, _ in glyphs if obj is not None]


# ------------------------------------------------------------------------------ parts
def gap(x, y):
    """Metres between ground point (x, y) and the hull (negative inside it): the waterline is gap = 0."""
    p = Vector((x, y, 0.0)) - Vector(TIP)
    d = min(LENGTH, max(0.0, p.dot(AXIS)))
    return (p - AXIS * d).length - radius(d)


def body_and_tail(rear_only=False):
    """rear_only: just the boat tail and the tail unit (what throws the shadow of mgb_bomb_shade)."""
    skin = bx.bomb_paint(colour=(0.078, 0.086, 0.075), rust=0.58, seed=3.0, bleach=0.36,
                         bands=((0.98, 1.34, (0.46, 0.32, 0.03)),))
    dents = [(3.45, 15.0, 0.5, 0.09), (2.75, 118.0, 0.5, 0.07), (1.2, 40.0, 0.4, 0.05), (3.7, 95.0, 0.3, 0.05)]
    body = BODY.build(skin, dents=dents, d0=2.9 if rear_only else 0.0)
    steel = mat.steel(rust=0.8, seed=5.0)
    dark = mat.steel(rust=0.5, colour=(0.045, 0.045, 0.05), seed=2.0)
    parts = [body]
    # joint flanges: the nose cap and the tail cone are bolted on
    for d, width in ((NOSE_JOINT, 0.11), (TAIL_JOINT, 0.12)):
        if rear_only:
            continue
        r = max(radius(d - width / 2), radius(d + width / 2))
        parts.append(bx.tube(r + 0.04, r - 0.1, d - width / 2, d + width / 2, dark, segments=56, name="flange"))
    r = radius(TAIL_JOINT) + 0.045
    for i in range(0 if rear_only else 20):                 # bolt heads round the big joint
        angle = 2 * math.pi * (i + 0.5) / 20
        parts.append(geo.box((0.075, 0.075, 0.075), (r * math.cos(angle), r * math.sin(angle), TAIL_JOINT), math.degrees(angle),
                             steel, bevel=0.01, centred=True, name="bolt"))
    # tail: four fins in an X that run forward of a dented ring shroud, the tail plate with its fuze cap
    fin_paint = bx.bomb_paint(colour=(0.07, 0.075, 0.068), rust=0.78, seed=8.0, bleach=0.3)
    ring = 0.84
    for k in range(4):
        angle = math.radians(45.0 + 90.0 * k)
        bm_points = [(radius(3.55) - 0.03, 3.55), (ring, 4.12), (ring, 4.62), (0.30, 4.62), (0.30, 3.9)]
        parts.append(fin(bm_points, angle, 0.04, fin_paint))
    parts.append(bx.tube(ring + 0.03, ring, 4.18, 4.64, fin_paint, segments=48, name="shroud",
                         dents=[(75.0, 4.64, 0.45, 0.15), (200.0, 4.3, 0.35, 0.08), (330.0, 4.6, 0.3, 0.07)]))
    parts.append(geo.lathe([(0.13, 4.6), (0.13, 4.74), (0.07, 4.79), (0.0, 4.79)], (0, 0, 0), dark, 14, name="tail_fuze"))
    bx.move(parts, M)
    bx.clip_ground(parts)
    if rear_only:
        return parts
    # weld seams along the hull and lifting lugs on the spine
    for phi in (12.0, 100.0):
        skin_curve([(a * 0.1, 0.0) for a in range(1, 14)], NOSE_JOINT, phi, 0.016, dark, lift=0.0, name="seam")
    for d in (1.8, 3.3):
        arch = bx.ellipse_points((0, 0, 0.0), 0.12, 0.14, 10, x=(1, 0, 0), y=(0, 0, 1), closed=False, sweep=180.0)
        on_skin(geo.pipe(arch, 0.032, dark, name="lug"), d, 0.0, -0.01)
    return parts


def fin(outline, angle, thickness, material):
    """A flat fin: outline [(radius, d)] in the plane through the axis at `angle` (body space)."""
    import bmesh
    bm = bmesh.new()
    c, s = math.cos(angle), math.sin(angle)
    verts = [bm.verts.new((r * c, r * s, d)) for r, d in outline]
    bm.faces.new(verts)
    return geo._finish(bm, "fin", material, (0, 0, 0), 0.0, "main", smooth=False, solidify=thickness)


def access_plate(state):
    """The quest's business end. 0.56 x 0.44 m, on the flank that faces the player."""
    steel = mat.steel(rust=0.5, seed=7.0)
    frame_mat = mat.steel(rust=0.35, colour=(0.06, 0.06, 0.065), seed=9.0)
    w, h = 0.56, 0.44
    on_skin(geo.box((w + 0.14, h + 0.14, 0.03), (0, 0, 0), 0.0, frame_mat, bevel=0.008, centred=True, name="plate_frame"),
            PLATE_D, PLATE_PHI, 0.005)
    door_mat = bx.bomb_paint(colour=(0.24, 0.25, 0.21), rust=0.35, seed=11.0, bleach=0.2)
    if state == "dormant":
        on_skin(geo.box((w, h, 0.03), (0, 0, 0), 0.0, door_mat, bevel=0.008, centred=True, name="plate"),
                PLATE_D, PLATE_PHI, 0.03)
        for sx in (-1, 1):
            for sy in (-1, 1):
                on_skin(geo.cylinder(0.035, 0.03, (sx * (w / 2 - 0.07), sy * (h / 2 - 0.07), 0.0), steel, 8, name="plate_bolt"),
                        PLATE_D, PLATE_PHI, 0.045)
        handle = [(-0.12, 0.0, 0.0), (-0.12, 0.0, 0.06), (0.12, 0.0, 0.06), (0.12, 0.0, 0.0)]
        on_skin(geo.pipe(handle, 0.02, frame_mat, name="plate_handle"), PLATE_D, PLATE_PHI, 0.045)
        return
    # open: a black hole, the plate swung down on its lower hinges and lying against the belly
    on_skin(geo.box((w, h, 0.012), (0, 0, 0), 0.0, mat.flat((0.004, 0.004, 0.005), roughness=1.0), bevel=0.0,
                    centred=True, name="cavity"), PLATE_D, PLATE_PHI, 0.022)
    down = PLATE_PHI + math.degrees((h + 0.10) / R)
    inner = mat.steel(rust=0.25, colour=(0.20, 0.20, 0.19), seed=4.0)
    on_skin([geo.box((w, h, 0.03), (0, 0, 0), 0.0, inner, bevel=0.008, centred=True, name="plate_open"),
             geo.box((w - 0.1, 0.05, 0.03), (0, 0.0, 0.02), 0.0, steel, bevel=0.006, centred=True, name="plate_rib"),
             geo.box((0.05, h - 0.1, 0.03), (0, 0.0, 0.02), 0.0, steel, bevel=0.006, centred=True, name="plate_rib")],
            PLATE_D, down, 0.06, turn=4.0)
    red = mat.flat((0.50, 0.03, 0.02), roughness=0.5)
    yellow = mat.flat((0.62, 0.46, 0.03), roughness=0.5)
    if state == "rigged":
        # the fusion pulse charge: a gunmetal box with a hazard stripe, wedged into the opening
        case = mat.flat((0.13, 0.17, 0.22), roughness=0.45, metallic=0.2)
        on_skin([geo.box((0.36, 0.27, 0.2), (-0.05, 0.02, 0.0), 0.0, case, bevel=0.02, centred=True, name="charge"),
                 geo.box((0.37, 0.08, 0.205), (-0.05, -0.06, 0.0), 0.0, yellow, bevel=0.0, centred=True, name="charge_stripe")],
                PLATE_D, PLATE_PHI, 0.08)
        lamp = geo.bulb((0.0, 0.0, 0.0), colour=(1.0, 0.05, 0.02), radius=0.055, strength=1.6, fx="alarm")
        on_skin(lamp, PLATE_D - 0.13, PLATE_PHI - 5.0, 0.22)
        # leads from the charge to the firing circuit: two fat loops
        on_skin(geo.pipe([(0.12, 0.05, 0.08), (0.22, 0.12, 0.14), (0.30, 0.10, 0.10), (0.31, 0.02, 0.02)], 0.022, red,
                         name="lead"), PLATE_D, PLATE_PHI, 0.07)
        on_skin(geo.pipe([(0.10, -0.06, 0.08), (0.20, -0.15, 0.13), (0.29, -0.16, 0.09), (0.31, -0.10, 0.02)], 0.022,
                         yellow, name="lead"), PLATE_D, PLATE_PHI, 0.07)
    else:
        # safe: the two leads cut, hanging out of the hole; a painted tick; a tag on a string
        for k, (material, along) in enumerate(((red, 0.10), (yellow, -0.08))):
            points = []
            for i in range(6):
                up = -0.05 - 0.085 * i
                points.append((along + 0.03 * math.sin(i * 1.3 + k), up))
            skin_curve(points, PLATE_D, PLATE_PHI, 0.022, material, lift=0.045 + 0.01 * k, name="cut_lead")
        tick = bx.paint((0.10, 0.62, 0.08), wear=0.15, seed=2.0)
        skin_curve([(-0.17, 0.03), (-0.04, -0.2), (0.2, 0.3)], 0.7, 52.0, 0.055, tick, name="tick")
        card = mat.flat((0.62, 0.58, 0.44), roughness=0.9)
        on_skin([geo.box((0.15, 0.22, 0.012), (0, 0, 0), 0.0, card, bevel=0.0, centred=True, name="tag"),
                 geo.box((0.11, 0.03, 0.014), (0, 0.04, 0.0), 0.0, mat.flat((0.05, 0.05, 0.05)), bevel=0.0, centred=True, name="tag_ink"),
                 geo.box((0.11, 0.03, 0.014), (0, -0.03, 0.0), 0.0, mat.flat((0.45, 0.04, 0.03)), bevel=0.0, centred=True, name="tag_ink")],
                PLATE_D - 0.42, PLATE_PHI + 16.0, 0.03, turn=-12.0)
        skin_curve([(-0.42, -0.02), (-0.36, 0.12), (-0.30, 0.20)], PLATE_D, PLATE_PHI, 0.012,
                   mat.flat((0.30, 0.25, 0.16)), lift=0.02, name="tag_string")


def markings():
    stencil = bx.paint((0.74, 0.72, 0.62), wear=0.45, seed=5.0)
    skin_text("MEGATON", TEXT_D, TEXT_PHI, 0.34, stencil)
    # the Children's mark on the tail cone: an atom, daubed in white
    white = bx.paint((0.80, 0.78, 0.70), wear=0.25, seed=1.0)
    d0, phi0 = 3.42, 50.0
    for turn in (0.0, 60.0, 120.0):
        c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))
        loop = []
        for i in range(19):
            a = 2 * math.pi * i / 18
            x, y = 0.23 * math.cos(a), 0.08 * math.sin(a)
            loop.append((x * c - y * s, x * s + y * c))
        skin_curve(loop, d0, phi0, 0.02, white, name="atom")
    dot = geo.bulb((0, 0, 0), colour=(0.8, 0.78, 0.7), radius=0.05, strength=0.0)
    dot.data.materials.clear()
    dot.data.materials.append(white)
    on_skin(dot, d0, phi0, 0.0)


def streaks():
    """Corrosion run-off: rust that has bled out of the joints, the plate and the dents and run
    down the flank. Drawn as strokes on the skin (noise alone gives stains, not streaks)."""
    r = geo.rng(19)
    colours = [mat.flat(c, roughness=0.95) for c in ((0.115, 0.048, 0.018), (0.075, 0.034, 0.015), (0.15, 0.062, 0.02))]
    starts = [(NOSE_JOINT + 0.07, phi) for phi in (58.0, 74.0, 90.0)]
    starts += [(TAIL_JOINT + 0.08, phi) for phi in (52.0, 66.0, 82.0, 98.0)]
    starts += [(PLATE_D - 0.3, PLATE_PHI + 17.0), (PLATE_D + 0.02, PLATE_PHI + 17.0), (PLATE_D + 0.31, PLATE_PHI + 17.0)]
    starts += [(3.3, 72.0), (3.75, 62.0), (0.62, 70.0), (1.15, 66.0), (1.75, 86.0), (2.7, 88.0)]
    for d0, phi0 in starts:
        length = r.uniform(0.35, 0.8)
        steps = 6
        points = []
        for i in range(steps + 1):
            t = i / steps
            points.append((0.03 * math.sin(t * 3.0 + phi0) * t, -length * t))
        skin_curve(points, d0 + r.uniform(-0.02, 0.02), phi0, r.uniform(0.022, 0.042), colours[r.randrange(3)],
                   lift=-0.006, name="streak")


def island():
    """What the bomb sits in. Round the hull a ring of the pool's glowing water (animated slime
    greens: it shimmers, and it is the one part of the picture the night does not darken); round
    that a bank of churned mud with the rubble the impact threw up, wider under the tail where the
    trestle stands. On the town's goo floor the bank reads as the lip of the bomb's own hole."""
    def lump(x, y, seed, scale=1.0):
        return bx.fbm(x, y, seed, scale, 3)

    def pool_height(x, y):
        g = gap(x, y)
        return 0.014 if g < 0.52 + 0.16 * lump(x, y, 5.0, 1.4) else None

    def mud_height(x, y):
        g = gap(x, y)
        inner = 0.30 + 0.14 * lump(x, y, 9.0, 1.7)
        outer = 0.88 + 0.30 * lump(x, y, 4.0, 0.9)
        # under the tail the bank spreads out to carry the trestle
        ex, ey = (x + 1.7) / 1.05, (y - YC) / 1.28
        tail = math.hypot(ex, ey) < 1.0 + 0.12 * lump(x, y, 6.0, 1.2)
        if g < inner or (g > outer and not tail):
            return None
        rim = min(1.0, (g - inner) / 0.16) * min(1.0, max(0.0, (outer - g) / 0.22) if not tail else 1.0)
        h = 0.03 + 0.20 * math.exp(-((g - 0.52) / 0.2) ** 2) * (0.75 + 0.4 * lump(x, y, 7.0, 2.2))
        h += 0.03 * lump(x, y, 2.0, 3.0)
        return max(0.016, h * (0.25 + 0.75 * rim))

    water = bx.heightfield(-2.2, 2.9, -3.0, 0.8, pool_height, bx.water(seed=2.0, glow=0.55), step=0.05, name="pool")
    geo.set_fx(water, "slime")
    ground = bx.heightfield(-3.1, 3.2, -3.2, 1.0, mud_height, bx.mud(seed=3.0), step=0.05, name="bank")
    r = geo.rng(41)
    rubble = []
    stone = mat.concrete(colour=(0.20, 0.18, 0.155), cracks=0.2, seed=2.0)
    for _ in range(60):
        x, y = r.uniform(-1.4, 3.0), r.uniform(-1.4, 0.7)
        g = gap(x, y)
        if not 0.42 < g < 0.8 or mud_height(x, y) is None:
            continue
        size = r.uniform(0.10, 0.26)
        rubble.append(geo.box((size, size * r.uniform(0.6, 1.0), size * r.uniform(0.5, 0.8)),
                              (x, y, mud_height(x, y) - 0.04), r.uniform(0, 180), stone, bevel=0.03, name="rubble",
                              tilt=r.uniform(-18, 18), roll=r.uniform(-18, 18)))
    return [water, ground] + rubble


def trestle():
    """What keeps the tail off the mud: a timber saddle on four splayed legs, a strap over the
    tail tube, a prop of scrap girder further forward."""
    timber = mat.planks(colour=(0.20, 0.115, 0.055), axis="X", width=0.3, grey=0.35, seed=6.0)
    steel = mat.steel(rust=0.8, seed=12.0)
    x = -1.78
    top = underside(x) - 0.02
    parts = [bx.beam((x, YC - 0.85, top - 0.09), (x, YC + 0.85, top - 0.09), (0.18, 0.18), timber, name="saddle")]
    for side in (-1, 1):
        for lean in (-1, 1):
            parts.append(bx.beam((x, YC + side * 0.66, top - 0.12), (x + lean * 0.42, YC + side * 0.98, 0.0), (0.11, 0.11),
                                 timber, name="leg"))
        parts.append(bx.plank((x - 0.33, YC + side * 0.93, 0.34), (x + 0.33, YC + side * 0.93, 0.34), 0.12, 0.035, timber,
                              roll=90.0, name="tie"))
    # strap over the tail tube, bolted to the saddle ends
    d = 3.98
    strap = []
    for i in range(13):
        phi = -92.0 + 184.0 * i / 12
        strap.append(tuple(M @ BODY.point(d, phi, 0.03)))
    strap = [(x, YC - 0.5, top)] + strap[::-1] + [(x, YC + 0.5, top)]
    parts.append(geo.pipe(strap, 0.028, steel, name="strap"))
    # a girder prop under the boat tail, leaning in from the viewer's side
    px = -1.05
    parts.append(geo.ibeam(1.05, (px, YC + 1.05, 0.0), 90.0, steel, height=0.16, width=0.12, vertical=True, tilt=0.0,
                           roll=0.0, name="prop"))
    return parts


def bunting():
    """Prayer flags from a scrap mast by the nose to the tail ring, a lantern on the mast."""
    steel = mat.steel(rust=0.7, seed=3.0)
    mx, my = G.hex_xy(3, -1)
    mx, my = mx + 0.25, my + 0.1
    top = (mx, my, 3.05)
    mast = [geo.pipe([(mx, my, 0.0), (mx - 0.03, my, 1.6), top], 0.04, steel, name="mast"),
            geo.box((0.3, 0.3, 0.1), (mx, my, 0.02), 25.0, mat.concrete(seed=4.0), name="mast_foot"),
            geo.pipe([(mx, my, 2.0), (mx + 0.4, my - 0.45, 0.0)], 0.022, steel, name="mast_stay")]
    ring_top = tuple(M @ BODY.point(4.5, 8.0, 0.88 - radius(4.5)))
    line = geo.catenary(top, ring_top, sag=0.5, count=28)
    objects = mast + [geo.pipe(line, 0.014, mat.flat((0.05, 0.045, 0.04), roughness=0.7), name="flag_line")]
    colours = [(0.50, 0.07, 0.03), (0.62, 0.42, 0.05), (0.60, 0.56, 0.44), (0.52, 0.20, 0.03), (0.10, 0.16, 0.22)]
    direction = Vector(ring_top) - Vector(top)
    rot = math.degrees(math.atan2(direction.y, direction.x))
    for i in range(2, 27, 2):
        p = line[i]
        k = i // 2
        objects.append(bx.cloth(0.26, 0.30 + 0.05 * ((k * 7) % 3), (p[0], p[1], p[2] - 0.01), rot, bx.cloth_mat(colours[k % len(colours)], seed=k),
                                sag=0.0, flutter=0.035, seed=k, columns=4, rows=4, ragged=0.08, name="flag"))
    # lantern: a tin can lamp hung from a bracket, its flame in the animated fire colours
    bx_, by_, bz_ = mx + 0.22, my + 0.1, 1.95
    objects.append(geo.pipe([(mx, my, 2.12), (bx_, by_, 2.14), (bx_, by_, bz_ + 0.2)], 0.016, steel, name="bracket"))
    objects.append(geo.lathe([(0.0, 0.2), (0.07, 0.17), (0.09, 0.15), (0.09, 0.13), (0.02, 0.13), (0.02, 0.02), (0.085, 0.02),
                              (0.085, 0.0), (0.0, 0.0)], (bx_, by_, bz_), steel, 10, name="lantern"))
    glow = geo.lathe([(0.0, 0.0), (0.062, 0.02), (0.062, 0.09), (0.0, 0.11)], (bx_, by_, bz_ + 0.025),
                     mat.emitter((1.0, 0.60, 0.20), 3.0), 10, name="lantern_flame")
    geo.set_fx(glow, "fire")
    objects.append(glow)
    return objects


def offerings():
    """What the faithful leave: a board on two blocks with candles, bottles and a bowl of caps."""
    r = geo.rng(77)
    ox, oy = G.hex_xy(2, 0)
    ox, oy = ox + 0.1, oy - 0.02
    wood = mat.planks(colour=(0.23, 0.13, 0.06), axis="X", width=0.4, seed=9.0)
    objects = [geo.box((0.16, 0.16, 0.12), (ox - 0.3, oy, 0.0), 10.0, mat.concrete(seed=6.0), name="block"),
               geo.box((0.16, 0.16, 0.12), (ox + 0.3, oy + 0.05, 0.0), -5.0, mat.concrete(seed=7.0), name="block"),
               bx.plank((ox - 0.45, oy - 0.02, 0.14), (ox + 0.45, oy + 0.06, 0.14), 0.26, 0.035, wood, name="board")]
    z = 0.16
    for k, (dx, dy, h) in enumerate(((-0.34, 0.0, 0.17), (-0.18, 0.06, 0.11), (0.33, 0.04, 0.2))):
        objects += bx.candle((ox + dx, oy + dy, z), height=h, radius=0.03, flame=1.25, seed=k)
    glass = mat.flat((0.10, 0.045, 0.012), roughness=0.15)
    for dx, dy in ((0.02, 0.07), (0.12, 0.0)):
        objects.append(geo.lathe([(0.04, 0.0), (0.04, 0.13), (0.015, 0.18), (0.015, 0.24), (0.0, 0.24)], (ox + dx, oy + dy, z),
                                 glass, 8, name="bottle"))
    objects.append(geo.lathe([(0.05, 0.0), (0.10, 0.05), (0.10, 0.06), (0.0, 0.035)], (ox + 0.2, oy - 0.04, z),
                             mat.steel(rust=0.3, colour=(0.22, 0.20, 0.16)), 12, name="bowl"))
    # candle stubs straight on the mud on the other side of the access plate
    sx, sy = G.hex_xy(-2, 0)
    for k, (dx, dy, h) in enumerate(((0.0, -0.05, 0.14), (0.16, 0.02, 0.09), (-0.14, 0.05, 0.11))):
        objects += bx.candle((sx + dx, sy + dy, 0.04), height=h, radius=0.035, flame=1.25, seed=5 + k)
    del r
    return bx.no_block(objects)


def build(state):
    body_and_tail()
    access_plate(state)
    markings()
    streaks()
    island()
    trestle()
    bunting()
    offerings()


def build_shade():
    """mgb_bomb_shade: the ground shadow of the raised tail and its trestle as a FLAT sprite, kept
    out of the bomb's own piece so that the bomb is exactly one object on its hex (the town's
    tests and scripts address "the scenery on the BOMB hex"; a flat shadow part there would be a
    second, unscripted "Atomic Bomb"). The casters are built but hidden from the camera; the only
    thing seen is a little rubble lying in the shade, which is this piece's main part."""
    casters = bx.flat_list(body_and_tail(rear_only=True), trestle())
    for obj in casters:
        obj.visible_camera = False
    r = geo.rng(5)
    stone = mat.concrete(colour=(0.20, 0.18, 0.155), cracks=0.2, seed=5.0)
    sx, sy = G.hex_xy(-4, -2)
    for dx, dy, size in ((0.0, 0.05, 0.2), (-0.22, 0.2, 0.13), (0.2, 0.25, 0.1)):
        geo.box((size, size * 0.8, size * 0.6), (sx + dx, sy + dy, -0.02), r.uniform(0, 180), stone, bevel=0.03, name="rubble",
                tilt=r.uniform(-15, 15), roll=r.uniform(-15, 15))


# light: the lantern, the candles and the glowing water make the bomb a lamp at night (the engine
# lights the hexes round the origin and keeps the sprite itself bright)
# use=True: the bomb is worked on by USING it (the town's mgbomb.ssl opens its menu from use_p_proc).
COMMON = dict(footprint=FOOTPRINT, anchors=[(0, 0)], shadow="none", material="metal", samples=64, light=(5, 85),
              use=True,
              convert={"forbid": ["purple", "rose"], "contrast": 1.4})      # 1.4: the stock bomb's deep darks


@piece("mgb_bomb", title="Atomic Bomb",
       desc="An atomic bomb, nose-down in the crater its airplane dug. MEGATON, says the stencil.", **COMMON)
def mgb_bomb(ctx):
    build("dormant")


@piece("mgb_bomb_rigged", title="Atomic Bomb",
       desc="The bomb. Its access plate hangs open; a charge is wired into the firing circuit and a red lamp blinks.",
       **COMMON)
def mgb_bomb_rigged(ctx):
    build("rigged")


@piece("mgb_bomb_safe", title="Atomic Bomb",
       desc="The bomb, with its firing leads cut and hanging. Somebody has painted a tick on it.", **COMMON)
def mgb_bomb_safe(ctx):
    build("safe")


@piece("mgb_bomb_states", title="Atomic Bomb",
       desc="An atomic bomb, nose-down in the crater its airplane dug. MEGATON, says the stencil.",
       frames=3, fps=1, **COMMON)
def mgb_bomb_states(ctx):
    build(STATES[ctx.frame])


@piece("mgb_bomb_shade", title="Rubble", desc="Lumps of crater floor, in the shadow of the bomb's tail.",
       footprint=[], anchors=[(-4, -2)], shadow="flat", material="stone")
def mgb_bomb_shade(ctx):
    build_shade()
