# SPDX-License-Identifier: MIT
"""Extra kit of the "roofs" author: patchwork roofs (tile sheets) and rooftop silhouettes. Shared: anybody may use it.

    from kit import roofs_extra as rx

Everything here works in whatever coordinates the caller builds in: SHEET coordinates for roofs
(kit/sheet_kit.py: x to the screen's lower left, y to its lower right, z above the roof plane) and
piece coordinates for silhouettes. What a roof needs, and why it is built the way it is:

  WEAR IS SHAPE, NOT NOISE. On a roof a metre is 36 px across x, 25 px along y and the palette has
  some 70 browns: a rust "texture" turns to pepper. So wear here is made of big things:
    tin()            one sheet whose rust RUNS: it starts under the lap of the sheet above and under
                     its nail rows and streaks down the slope, the drip edge is eaten, the rest is
                     one flat tone. Every sheet has its own tone, so the laps read as lines.
    field()          a roof area laid with such sheets from a list of "kinds" (bare, rusted through,
                     painted), in courses with ragged ends; returns the sheets (for paint_on).
    paint_on()       PAINT on whatever is there: a shell that hugs the sheets (their own corrugation)
                     cut to a shape - letters, a cross, a star, stripes - and flaked off again.
                     This is how a roof gets a faded sign instead of a clean plate laid on top.
    patch()          a plate riveted over the roof, a strip of tar under its edges
    car_door(), bonnet(), road_sign()   scrap that people really roof with
    tarp_down()      a tarpaulin held by tyres, blocks and a rope
    hole()           sheets missing over rafters, the edges curled, one sheet hanging in
    skylight(), hatch(), stub(), mushroom()  what sticks out of a roof (keep it low: see sheet_kit)
    rocks(), tyres(), blocks(), sandbag_ring(), board()   weights and litter
    gutter_stain()   a dark run where water leaves the roof

  Cutters for paint_on: prism() (any outline), rect(), cross(), star(), ring(), text().
  Materials: tin_mat(), paint_mat(), tar(), stone().
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise as mnoise

from . import geo, mat
from . import sheet_kit as sk
from . import signs_extra as sx
from .nodes import Graph

ZINC = (0.150, 0.152, 0.148)        # weathered galvanised sheet as the stock roofs show it
ZINC_DARK = (0.095, 0.095, 0.09)
DUST = (0.17, 0.135, 0.095)          # what settles on everything
OXIDE = (0.20, 0.060, 0.035)         # red oxide primer
BRICK = (0.26, 0.085, 0.045)
CREAM = (0.30, 0.26, 0.17)
MUSTARD = (0.28, 0.19, 0.05)
OLIVE = (0.15, 0.16, 0.085)
TEAL = (0.07, 0.17, 0.17)
DUSTY_BLUE = (0.10, 0.17, 0.24)
BOTTLE = (0.05, 0.14, 0.08)
BLACKISH = (0.035, 0.033, 0.03)
WHITE = (0.34, 0.33, 0.29)
SIGNAL_RED = (0.30, 0.040, 0.030)
RUST_DEEP = (0.060, 0.022, 0.012)
RUST_BROWN = (0.135, 0.050, 0.020)
RUST_ORANGE = (0.27, 0.105, 0.030)
TAR = (0.018, 0.017, 0.018)


# =================================================================== materials
def _seeded(g, seed):
    return g.mapping(g.coords(), location=(seed * 7.31, seed * 3.17, seed * 5.53))


def _rust(g, p, hot=0.35):
    """Rust as the stock roofs have it: dull red-brown, a little orange only where it is fresh."""
    n = g.noise(p, scale=4.0, detail=3.0, roughness=0.6)
    return g.ramp(n, [(0.30, RUST_DEEP), (0.52, RUST_BROWN), (0.62 + 0.3 * (1.0 - hot), RUST_ORANGE)])


def tin_mat(base=None, rust=0.4, length=2.0, seed=0.0, lap=1.0, drip=1.0, nails=(0.5,), fade=0.3, chips=0.0,
            soot=0.0):
    """Corrugated iron for roof sheets (object space of geo.corrugated_panel: x across the ridges,
    z down the slope from the sheet's upper end, `length` m long).
    base     bare zinc (None) or the colour of old paint
    rust     0 new .. 1 rusted through: how far the runs reach and how wide they are
    lap      strength of the runs that start under the sheet above (z = 0)
    drip     how much of the lower edge is eaten
    nails    where nail rows are, as fractions of the length: each starts runs of its own
    fade     how unevenly the paint has bleached;  chips: paint flaked off to bare metal (0..1)
    soot     0..1: blackened (a kitchen roof, round a flue)"""
    nails = tuple(float(v) for v in nails)

    def build():
        g = Graph("rx_tin")
        p = _seeded(g, seed)
        x, _, z = g.separate(g.coords())
        tone = base if base is not None else ZINC
        # the sheet itself: two tones in big soft clouds (galvanising blooms, bleached paint), dust on top
        cloud = g.noise(p, scale=1.1, detail=2.0, roughness=0.5)
        light = tuple(min(1.0, c * (1.0 + 0.45 * fade) + 0.02 * fade) for c in tone)
        dark = tuple(c * (1.0 - 0.38 * fade) for c in tone)
        sheet = g.mix(g.smooth(cloud, 0.36, 0.64), dark, light)
        if chips > 0.0 and base is not None:
            chip = g.noise(p, scale=2.4, detail=2.0, roughness=0.6, distortion=0.8)
            low = g.smooth(z, length * 0.25, length)                       # paint goes first low down
            gone = g.smooth(g.add(chip, g.mul(low, 0.22)), 0.86 - chips * 0.45, 0.88 - chips * 0.45)
            sheet = g.mix(gone, sheet, ZINC_DARK)
        dust = g.noise(p, scale=0.7, detail=1.0, roughness=0.4)
        sheet = g.mix(g.mul(g.smooth(dust, 0.4, 0.7), 0.35), sheet, DUST)
        # runs: narrow across x, long down z, hanging from the lap above and from every nail row
        across = g.add(x, seed * 3.7)
        run_a = g.noise(g.combine(g.mul(across, 5.5), 0.0, g.mul(z, 0.25)), scale=1.0, detail=0.0, roughness=0.4)
        run_b = g.noise(g.combine(g.mul(across, 2.2), 3.3, 0.0), scale=1.0, detail=0.0, roughness=0.4)
        strip = g.smooth(run_a, 0.56 - 0.12 * rust, 0.60 - 0.12 * rust)           # where a run can be
        wide = g.smooth(run_a, 0.46 - 0.12 * rust, 0.58 - 0.12 * rust)
        reach = 0.25 + 1.6 * rust                                                # metres the longest run travels
        far = g.mul(g.add(0.25, g.mul(run_b, 1.3)), reach)                      # ... each run its own length
        hang = g.mul(g.smooth(g.div(z, far), 1.0, 0.75), lap)
        hang_soft = g.mul(g.smooth(g.div(z, far), 1.5, 0.3), lap)
        for share in nails:
            start = length * share
            dz = g.sub(z, start)
            below = g.mul(g.greater(dz, 0.0), g.smooth(g.div(dz, g.mul(far, 0.7)), 1.0, 0.75))
            hang = g.maximum(hang, below)
            hang_soft = g.maximum(hang_soft, g.mul(g.greater(dz, 0.0), g.smooth(g.div(dz, g.mul(far, 0.7)), 1.5, 0.3)))
        wobble = g.mul(g.sub(run_a, 0.5), 0.5)
        eaten = g.mul(g.smooth(g.add(z, wobble), length - 0.12 - 0.40 * rust, length - 0.08 - 0.40 * rust), drip)
        blotch = g.noise(p, scale=1.5, detail=1.0, roughness=0.5, distortion=0.6)
        spot = g.smooth(blotch, 0.84 - 0.32 * rust, 0.86 - 0.32 * rust)
        rusted = g.maximum(g.maximum(g.mul(strip, hang), spot), eaten)
        stained = g.maximum(g.mul(wide, hang_soft), g.smooth(blotch, 0.70 - 0.32 * rust, 0.86 - 0.32 * rust))
        colour = g.mix(g.mul(stained, 0.6), sheet, tuple(0.4 * a + 0.6 * b for a, b in zip(tone, RUST_BROWN)))
        colour = g.mix(rusted, colour, _rust(g, p, hot=0.2 + 0.3 * rust))
        if soot > 0.0:
            smoke = g.noise(p, scale=0.9, detail=2.0, roughness=0.5)
            colour = g.mix(g.mul(g.smooth(smoke, 0.75 - 0.6 * soot, 0.95 - 0.5 * soot), 0.9), colour, TAR)
        own = g.new("ShaderNodeAmbientOcclusion", samples=8, only_local=True)   # the sheet's own troughs only:
        g.put(own.inputs["Distance"], 0.10)                                      # paint shells must not darken it
        colour = g.mix(g.smooth(own.outputs["AO"], 0.80, 0.30), colour, mat.SOOT)
        g.principled(base=colour, roughness=g.mix_value(rusted, 0.7, 0.95), metallic=g.mix_value(rusted, 0.15, 0.0),
                     specular=g.mix_value(rusted, 0.2, 0.05))
        return g.material
    return mat._cached(("rx_tin", base, rust, round(length, 2), seed, lap, drip, nails, fade, chips, soot), build)


def paint_mat(colour=WHITE, wear=0.45, seed=0.0, fade=0.35, glow=0.0, scale=1.0):
    """Paint for paint_on(): flat colour, bleached in clouds, FLAKED OFF in big hard-edged pieces
    (alpha: what is underneath shows through). wear 0 = fresh, 0.8 = a ghost of a sign."""
    def build():
        g = Graph("rx_paint")
        p = _seeded(g, seed)
        cloud = g.noise(p, scale=1.3 * scale, detail=2.0, roughness=0.5)
        base = g.mix(g.smooth(cloud, 0.35, 0.65), tuple(c * (1.0 - 0.3 * fade) for c in colour),
                     tuple(min(1.0, c * (1.0 + 0.4 * fade) + 0.03 * fade) for c in colour))
        dust = g.noise(p, scale=0.8 * scale, detail=1.0, roughness=0.4)
        base = g.mix(g.mul(g.smooth(dust, 0.4, 0.7), 0.3), base, DUST)
        big = g.noise(p, scale=1.25 * scale, detail=1.5, roughness=0.55, distortion=1.0)
        edge = 0.78 - wear * 0.36
        kept = g.sub(1.0, g.smooth(big, edge - 0.012, edge + 0.012))
        g.principled(base=base, roughness=0.85, specular=0.08, alpha=kept,
                     emission=base if glow else None, emission_strength=glow)
        return g.material
    return mat._cached(("rx_paint", colour, wear, seed, fade, glow, scale), build)


def glow_glass(colour=(1.0, 0.66, 0.30), strength=1.0, seed=0.0):
    """A dirty pane with lamplight behind it: an uneven warm glow (soot clouds, a clean corner)."""
    def build():
        from pipeline.bscene import EXPOSURE
        g = Graph("rx_glow_glass")
        p = _seeded(g, seed)
        cloud = g.noise(p, scale=2.2, detail=2.0, roughness=0.55, distortion=0.5)
        amount = g.mul(g.add(0.10, g.mul(g.smooth(cloud, 0.30, 0.72), 0.90)), strength * 2.0 ** -EXPOSURE)
        g.emission(colour, amount)
        return g.material
    return mat._cached(("rx_glow_glass", colour, strength, seed), build)


def tar():
    """Roofing tar smeared round a patch, a flue, a seam."""
    return mat.flat(TAR, roughness=0.55)


def stone(seed=0.0):
    def build():
        g = Graph("rx_stone")
        p = _seeded(g, seed)
        n = g.noise(p, scale=3.0, detail=3.0, roughness=0.6)
        g.principled(base=g.mix(g.smooth(n, 0.35, 0.65), (0.10, 0.085, 0.07), (0.25, 0.21, 0.16)), roughness=0.95, specular=0.1)
        return g.material
    return mat._cached(("rx_stone", seed), build)


# ======================================================================= sheets
def tin(x0, y0, x1, y1, z=0.0, base=None, rust=0.4, seed=0, slope=0.0, roll=0.0, wavelength=0.18, depth=0.045,
        along="y", lap=1.0, drip=1.0, nails=(0.5,), fade=0.3, chips=0.0, soot=0.0, layer="main", name="tin"):
    """One roof sheet over x0..x1, y0..y1 (ridges down the slope, +y), material tin_mat()."""
    length = (y1 - y0) if along == "y" else (x1 - x0)
    material = tin_mat(base, rust, length, seed, lap, drip, nails, fade, chips, soot)
    obj = sk.tin(x0, y0, x1, y1, z, along=along, slope=slope, roll=roll, material=material, wavelength=wavelength,
                 depth=depth, layer=layer, name=name)
    obj["rx_box"] = (float(x0), float(y0), float(x1), float(y1))
    return obj


# kinds of sheet a field() draws from: (weight, base colour or None, (rust from, to), chips)
BARE = (1.0, None, (0.15, 0.5), 0.0)
BARE_OLD = (1.0, ZINC_DARK, (0.4, 0.75), 0.0)
RUSTED = (1.0, RUST_BROWN, (0.6, 0.95), 0.0)


def kind(weight, colour, rust=(0.25, 0.6), chips=0.35):
    return (float(weight), colour, tuple(rust), float(chips))


def field(x0, y0, x1, y1, z=0.0, kinds=(BARE,), sheet=(0.95, 2.2), jitter=0.22, seed=1, skip=None, ragged=0.0,
          start_ragged=0.0, lift=0.03, wavelength=0.18, soot=0.0, course_drop=0.012, choose=None):
    """Lay x0..x1, y0..y1 with roof sheets in courses (rows along x), the way a roof is laid: the
    upper course lies on the next one down. Each sheet is one of `kinds`, with its own tone.
    ragged        metres by which the sheets of the LAST course differ in length (an uneven eave)
    start_ragged  the same for the upper end of the first course (the sheets start up to this much LATER than y0,
                  never earlier: what stands behind the building must not be covered more than by the stock roof)
    skip(xa, ya, xb, yb) -> True leaves that sheet out;  choose(xa, ya, xb, yb, rng) -> a kind or None
    Returns the sheets (each carries its box as obj["rx_box"])."""
    r = random.Random(seed)
    total = sum(k[0] for k in kinds)
    width, length = sheet
    made = []
    y = y0
    course = 0
    index = 0
    while y < y1 - 0.05:
        ln = min(length * r.uniform(1.0 - jitter, 1.0 + jitter * 0.4), y1 - y)
        last = y1 - (y + ln) < length * 0.4
        if last:
            ln = y1 - y
        x = x0 - (r.uniform(0.1, width * 0.6) if course % 2 else 0.0)
        while x < x1 - 0.05:
            w = width * r.uniform(1.0 - jitter, 1.0 + jitter)
            xa, xb = max(x0, x), min(x1, x + w)
            x += w - 0.09
            if xb - xa < 0.15:
                continue
            ya = y - 0.16 if course else y + r.uniform(0.0, start_ragged)      # never further back than y0
            yb = y + ln - (r.uniform(0.0, ragged) if last else 0.0)
            index += 1
            if skip and skip(xa, ya, xb, yb):
                continue
            chosen = choose(xa, ya, xb, yb, r) if choose else None
            if chosen is None:
                pick = r.uniform(0.0, total)
                for chosen in kinds:
                    pick -= chosen[0]
                    if pick <= 0.0:
                        break
            _, colour, rust_range, chips = chosen
            if colour is None:
                t = r.uniform(0.78, 1.12)
                colour_i = tuple(round(c * t, 3) for c in ZINC)
            else:
                t = r.uniform(0.85, 1.12)
                colour_i = tuple(round(c * t, 3) for c in colour)
            height = z + lift * (0.35 + (index % 2) * 0.55) - course_drop * course + r.uniform(0.0, lift * 0.3)
            obj = tin(xa, ya, xb, yb, max(z, height), base=colour_i, rust=round(r.uniform(*rust_range), 2),
                      seed=seed * 31 + index, slope=r.uniform(-0.7, 0.7), roll=r.uniform(-1.1, 1.1), wavelength=wavelength,
                      lap=1.0 if course else 0.4, drip=1.0 if last else 0.55, nails=(r.uniform(0.4, 0.6),),
                      fade=r.uniform(0.2, 0.5), chips=chips, soot=soot, name=f"tin{index}")
            made.append(obj)
        y += ln
        course += 1
    return made


def inside(box, grow=0.0):
    """skip-function for field(): leaves out the sheets that lie inside `box` (x0, y0, x1, y1)."""
    def test(xa, ya, xb, yb):
        return xa > box[0] - grow and xb < box[2] + grow and ya > box[1] - grow and yb < box[3] + grow
    return test


def touching(box):
    def test(xa, ya, xb, yb):
        return xb > box[0] and xa < box[2] and yb > box[1] and ya < box[3]
    return test


def any_of(*tests):
    return lambda xa, ya, xb, yb: any(t(xa, ya, xb, yb) for t in tests)


# ====================================================================== cutters
def _unlinked(bm, name="cutter", triangulate=True):
    if triangulate:
        bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return bpy.data.objects.new(name, mesh)


def prism(points, z0=-2.0, z1=2.0):
    """A cutter: the closed prism over outline [(x, y), ...] (counter-clockwise or clockwise)."""
    bm = bmesh.new()
    lower = [bm.verts.new((x, y, z0)) for x, y in points]
    upper = [bm.verts.new((x, y, z1)) for x, y in points]
    n = len(points)
    bm.faces.new(lower)
    bm.faces.new(upper)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
    return _unlinked(bm)


def rect(x0, y0, x1, y1, rot=0.0):
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    half = ((x0 - cx, y0 - cy), (x1 - cx, y0 - cy), (x1 - cx, y1 - cy), (x0 - cx, y1 - cy))
    return prism([(cx + a * c - b * s, cy + a * s + b * c) for a, b in half])


def cross(cx, cy, size, arm=0.32, rot=0.0):
    """A plus sign `size` across, its arms `arm` x size wide."""
    h, a = size / 2.0, size * arm / 2.0
    outline = [(-a, -h), (a, -h), (a, -a), (h, -a), (h, a), (a, a), (a, h), (-a, h), (-a, a), (-h, a), (-h, -a), (-a, -a)]
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return prism([(cx + x * c - y * s, cy + x * s + y * c) for x, y in outline])


def star(cx, cy, radius, points=5, inner=0.42, rot=0.0, squash=(1.0, 1.0)):
    outline = []
    for i in range(points * 2):
        a = math.radians(rot) + math.pi * i / points
        r = radius if i % 2 == 0 else radius * inner
        outline.append((cx + r * math.sin(a) * squash[0], cy - r * math.cos(a) * squash[1]))
    return prism(outline)


def ring(cx, cy, rx_out, ry_out, width, rot=0.0, count=40, sweep=(0.0, 360.0)):
    """An elliptical band `width` wide (a full ring, or the arc `sweep` degrees of it)."""
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    full = abs(sweep[1] - sweep[0]) >= 359.9
    steps = count if full else max(3, int(count * abs(sweep[1] - sweep[0]) / 360.0))
    bm = bmesh.new()
    rings = []
    for k in range(steps + (0 if full else 1)):
        a = math.radians(sweep[0] + (sweep[1] - sweep[0]) * k / steps)
        quad = []
        for rx_, ry_ in ((rx_out, ry_out), (rx_out - width, ry_out - width)):
            px, py = rx_ * math.cos(a), ry_ * math.sin(a)
            for zz in (-2.0, 2.0):
                quad.append(bm.verts.new((cx + px * c - py * s, cy + px * s + py * c, zz)))
        rings.append(quad)                                                  # outer lo, outer hi, inner lo, inner hi
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if full else [])
    for a, b in pairs:
        bm.faces.new((a[0], b[0], b[1], a[1]))
        bm.faces.new((a[2], a[3], b[3], b[2]))
        bm.faces.new((a[1], b[1], b[3], a[3]))
        bm.faces.new((a[0], a[2], b[2], b[0]))
    if not full:
        for q in (rings[0], rings[-1]):
            bm.faces.new((q[0], q[1], q[3], q[2]))
    return _unlinked(bm)


def text(body, x, y, size, rot=180.0, font="impact", spacing=1.0, align="CENTER", stretch=1.0):
    """A cutter in the shape of lettering lying on the roof. (x, y): the baseline (its middle with
    align="CENTER"); size: cap height in metres; rot: direction of reading - 180 reads along -x
    (towards the screen's upper right, the letters' tops towards the back of the roof), 90 reads
    along +y (down to the right, tall narrow letters). stretch: widens the letters."""
    curve = bpy.data.curves.new("rx_text", "FONT")
    curve.body = body
    try:
        curve.font = bpy.data.fonts.load(geo.FONTS.get(font, font), check_existing=True)
    except RuntimeError:
        print(f"[kit.roofs_extra] font {font!r} not found")
    curve.size = size / 0.72
    curve.align_x = align
    curve.space_character = spacing
    curve.extrude = 2.0
    obj = bpy.data.objects.new("rx_text", curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (x, y, 0.0)
    obj.rotation_euler = (0.0, 0.0, math.radians(rot))
    obj.scale = (stretch, 1.0, 1.0)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    cutter = bpy.data.objects.new("cutter", mesh)
    cutter.matrix_world = obj.matrix_world.copy()
    bpy.context.scene.collection.objects.unlink(obj)
    bpy.data.objects.remove(obj)
    bpy.data.curves.remove(curve)
    return cutter


def _bounds(obj):
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (min(c.x for c in corners), min(c.y for c in corners), max(c.x for c in corners), max(c.y for c in corners))


def paint_on(targets, cutters, material=None, lift=0.007, layer="main", name="paint"):
    """Paint the shape of `cutters` (one cutter or a list: everything inside any of them) onto
    `targets` (sheets from field() / tin(), planks, plates). For every target that the shape
    touches a copy is made `lift` m above it and cut to the shape, so the paint follows the
    corrugation, the laps and the tilt of each sheet. Returns the painted shells."""
    material = material or paint_mat()
    cutters = [cutters] if not isinstance(cutters, (list, tuple)) else list(cutters)
    scene = bpy.context.scene
    made = []
    for cutter in cutters:
        linked = cutter.name in scene.collection.objects
        if not linked:
            scene.collection.objects.link(cutter)
        cutter.hide_render = True
    bpy.context.view_layer.update()
    boxes = [_bounds(c) for c in cutters]
    for target in targets:
        tb = _bounds(target)
        hits = [c for c, b in zip(cutters, boxes) if b[0] < tb[2] and b[2] > tb[0] and b[1] < tb[3] and b[3] > tb[1]]
        if not hits:
            continue
        for cutter in hits:
            shell = target.copy()
            shell.data = target.data.copy()
            shell.name = name
            shell.location.z += lift
            scene.collection.objects.link(shell)
            modifier = shell.modifiers.new("cut", "BOOLEAN")
            modifier.operation = "INTERSECT"
            modifier.object = cutter
            try:
                modifier.solver = "EXACT"
            except TypeError:
                pass
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            mesh = bpy.data.meshes.new_from_object(shell.evaluated_get(depsgraph))
            shell.modifiers.clear()
            old = shell.data
            shell.data = mesh
            bpy.data.meshes.remove(old)
            if not mesh.polygons:
                scene.collection.objects.unlink(shell)
                bpy.data.objects.remove(shell)
                continue
            mesh.materials.clear()
            mesh.materials.append(material)
            for polygon in mesh.polygons:
                polygon.use_smooth = True
                polygon.material_index = 0
            shell[geo.BLOCK_PROPERTY] = 0.0
            made.append(shell)
    for cutter in cutters:
        scene.collection.objects.unlink(cutter)
        bpy.data.objects.remove(cutter)
    return made


# ================================================================= things on a roof
def rivets(points, z, radius=0.035, material=None, layer="main"):
    material = material or mat.steel(rust=0.9, seed=2)
    return [geo.box((radius * 2, radius * 2, radius), (x, y, z), 0.0, material, bevel=0.0, layer=layer, name="rivet")
            for x, y in points]


def patch(x0, y0, x1, y1, z=0.05, material=None, rot=0.0, thickness=0.018, studs=0.34, tarred=True, layer="main",
          seed=0, name="patch"):
    """A plate fixed over the roof: its edge sealed with a smear of tar (a dark rim that also hides
    the gap), studs round it. rot turns it about its centre."""
    material = material or mat.steel(rust=0.75, seed=seed)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    w, h = x1 - x0, y1 - y0
    made = []
    if tarred:
        made.append(geo.box((w + 0.14, h + 0.12, 0.012), (cx, cy, z - 0.012), rot, tar(), bevel=0.0, layer=layer, name="tar"))
    made.append(geo.box((w, h, thickness), (cx, cy, z), rot, material, bevel=0.004, layer=layer, name=name))
    if studs:
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        pts = []
        nx, ny = max(2, int(w / studs) + 1), max(2, int(h / studs) + 1)
        for i in range(nx):
            for b in (-h / 2 + 0.07, h / 2 - 0.07):
                pts.append((-w / 2 + 0.07 + (w - 0.14) * i / (nx - 1), b))
        for j in range(1, ny - 1):
            for a in (-w / 2 + 0.07, w / 2 - 0.07):
                pts.append((a, -h / 2 + 0.07 + (h - 0.14) * j / (ny - 1)))
        made += rivets([(cx + a * c - b * s, cy + a * s + b * c) for a, b in pts], z + thickness, layer=layer)
    return made


def board(a, b, width=0.2, z=0.05, thickness=0.035, colour=(0.24, 0.13, 0.06), grey=0.4, seed=0, layer="main"):
    """One loose plank lying from a to b (2-tuples)."""
    at, rot, length = geo.span(a, b)
    material = mat.planks(colour=colour, width=width * 3, axis="X", grey=grey, seed=seed)
    return geo.box((length, width, thickness), ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, z), rot, material, bevel=0.006,
                   layer=layer, name="board")


def tyres(points, z=0.04, seed=1, layer="main"):
    r = random.Random(seed)
    return [geo.tire((x, y, z), radius=r.uniform(0.3, 0.37), lying=True, rot=r.uniform(0, 180), lean=r.uniform(-4, 4),
                     seed=seed + k, layer=layer) for k, (x, y) in enumerate(points)]


def blocks(points, z=0.04, seed=1, layer="main"):
    r = random.Random(seed)
    return [geo.box((0.42, 0.2, 0.2), (x, y, z), r.uniform(0, 180), mat.concrete(seed=seed + k), bevel=0.012, layer=layer,
                    name="block") for k, (x, y) in enumerate(points)]


def rock(x, y, z=0.03, radius=0.2, seed=0, layer="main"):
    r = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    sx_, sy_, sz_ = radius * r.uniform(0.8, 1.25), radius * r.uniform(0.8, 1.25), radius * r.uniform(0.5, 0.75)
    for vert in bm.verts:
        n = mnoise.noise(Vector(vert.co) * 1.7 + Vector((seed * 3.1, seed * 1.3, seed * 2.2)))
        k = 1.0 + 0.28 * n
        vert.co = Vector((vert.co.x * sx_ * k, vert.co.y * sy_ * k, (vert.co.z + 0.6) * sz_ * k))
    return geo._finish(bm, "rock", stone(seed % 4), (x, y, z), r.uniform(0, 360), layer, smooth=False)


def rocks(points, z=0.03, seed=1, radius=(0.14, 0.24), layer="main"):
    r = random.Random(seed)
    return [rock(x, y, z, r.uniform(*radius), seed + k, layer) for k, (x, y) in enumerate(points)]


def sandbag_ring(cx, cy, radius=0.9, z=0.04, courses=2, sweep=(200.0, 520.0), seed=1, layer="main"):
    """A curved breastwork of sandbags (a firing position on a roof corner)."""
    from . import gate_extra as gx
    r = random.Random(seed)
    made = []
    size = (0.6, 0.32, 0.17)
    for course in range(courses):
        count = max(3, int(radius * math.radians(abs(sweep[1] - sweep[0])) / (size[0] * 0.9)))
        for i in range(count - (course % 2)):
            a = math.radians(sweep[0] + (sweep[1] - sweep[0]) * (i + 0.5 + 0.5 * (course % 2)) / count)
            made.append(gx.sandbag((cx + radius * math.cos(a) + r.uniform(-0.03, 0.03),
                                    cy + radius * math.sin(a) + r.uniform(-0.03, 0.03), z + course * size[2] * 0.85),
                                   math.degrees(a) + 90.0 + r.uniform(-6, 6), size, seed=seed * 13 + len(made), layer=layer))
    return made


def tarp_down(x0, y0, x1, y1, z=0.06, colour=(0.17, 0.15, 0.09), seed=1, weights="mix", rope=True, sag=0.05,
              wrinkle=0.045, layer="main"):
    """A tarpaulin over a bad piece of roof: its corners and edges weighted with tyres, blocks or
    rocks ("tyres" / "blocks" / "rocks" / "mix"), a rope across it."""
    r = random.Random(seed)
    made = [sk.tarp(x0, y0, x1, y1, z=z, colour=colour, sag=sag, wrinkle=wrinkle, seed=seed, layer=layer)]
    corners = [(x0 + 0.3, y0 + 0.35), (x1 - 0.3, y0 + 0.35), (x0 + 0.3, y1 - 0.35), (x1 - 0.3, y1 - 0.35)]
    if x1 - x0 > 2.6:
        corners += [((x0 + x1) / 2.0 + r.uniform(-0.3, 0.3), y1 - 0.3)]
    for k, (px, py) in enumerate(corners):
        what = weights if weights != "mix" else r.choice(("tyres", "tyres", "blocks", "rocks"))
        if what == "tyres":
            made += tyres([(px, py)], z + 0.03, seed + k, layer)
        elif what == "blocks":
            made += blocks([(px, py)], z + 0.03, seed + k, layer)
        else:
            made += rocks([(px, py), (px + 0.25, py + 0.1)], z + 0.03, seed + k, layer=layer)
    if rope:
        ym = (y0 + y1) / 2.0 + r.uniform(-0.3, 0.3)
        made.append(geo.pipe([(x0 - 0.25, ym, z - 0.02), (x0 + 0.1, ym, z + 0.05), ((x0 + x1) / 2.0, ym + 0.1, z + sag + 0.06),
                              (x1 - 0.1, ym, z + 0.05), (x1 + 0.25, ym, z - 0.02)], 0.022,
                             mat.flat((0.20, 0.15, 0.08), roughness=0.9), layer, "rope"))
    return made


def hole(x0, y0, x1, y1, z=0.0, seed=1, hanging=True, purlins=True, spacing=0.6, curled=True, layer="main",
         rafter_colour=(0.13, 0.075, 0.04)):
    """Sheets gone over x0..x1, y0..y1: rafters and battens show (and through them the room), the
    sheets round the gap are curled up, one hangs into it. Leave the sheets out with
    skip=rx.inside((x0, y0, x1, y1), grow) in field()."""
    r = random.Random(seed)
    timber = mat.planks(colour=rafter_colour, width=0.4, axis="X", grey=0.25, seed=seed)
    made = sk.rafters(x0 - 0.5, y0 - 0.4, x1 + 0.5, y1 + 0.4, z=z - 0.06, spacing=spacing, purlins=purlins, material=timber,
                      layer=layer)
    if hanging:
        w = min(0.85, (x1 - x0) * 0.4)
        made.append(tin(x1 - w - 0.1, y0 - 0.1, x1 - 0.1, y0 + (y1 - y0) * 0.75, z - 0.03, base=RUST_BROWN, rust=0.9,
                        seed=seed + 5, slope=16.0, roll=r.uniform(-7, 7), name="hanging"))
    if curled:
        for k, (cx, cy, w, rot) in enumerate(((x0 + 0.1, (y0 + y1) / 2.0, (y1 - y0) * 0.6, 90.0),
                                              ((x0 + x1) / 2.0, y1 + 0.02, (x1 - x0) * 0.55, 0.0))):
            made.append(geo.box((w, 0.34, 0.012), (cx, cy, z + 0.07), rot, tin_mat(RUST_BROWN, 0.85, 0.4, seed + k),
                                bevel=0.0, layer=layer, name="curl", tilt=24.0 if rot else -24.0))
    return made


def skylight(x0, y0, x1, y1, z=0.0, curb=0.16, panes=(2, 1), glass=None, lit=None, broken=(), boarded=(), seed=0,
             layer="main", frame=None, pitch=0.10):
    """A roof light: a timber or steel curb `curb` m high with glass panes sloping to the front.
    lit: an animated palette range ("fire", "slime", "monitors") for panes that glow at night;
    broken / boarded: pane indices (row-major) that are a dark hole / covered with a board."""
    frame = frame or mat.painted_metal((0.10, 0.10, 0.09), flaking=0.5, seed=seed)
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    made = [geo.box((w + 0.16, h + 0.16, 0.012), (cx, cy, z + 0.02), 0.0, tar(), bevel=0.0, layer=layer, name="tar")]
    t = 0.07
    for bx, by, sx_, sy_ in ((cx, y0 + t / 2, w, t), (cx, y1 - t / 2, w, t), (x0 + t / 2, cy, t, h), (x1 - t / 2, cy, t, h)):
        made.append(geo.box((sx_, sy_, curb + (pitch if by < cy - 0.01 else 0.0) + (pitch / 2 if abs(by - cy) < 0.01 else 0.0)),
                            (bx, by, z), 0.0, frame, bevel=0.006, layer=layer, name="curb"))
    nx, ny = panes
    pw, ph = (w - t * (nx + 1)) / nx, (h - t * (ny + 1)) / ny
    slope = math.degrees(math.atan2(pitch, h))
    index = 0
    for j in range(ny):
        for i in range(nx):
            px = x0 + t + (pw + t) * i + pw / 2.0
            py = y0 + t + (ph + t) * j + ph / 2.0
            pz = z + curb + pitch * (1.0 - (py - y0) / h) - 0.02
            if index in boarded:
                made.append(geo.box((pw + 0.04, ph + 0.04, 0.03), (px, py, pz + 0.02), 0.0,
                                    mat.planks(colour=(0.25, 0.14, 0.06), width=0.18, axis="X", grey=0.5, seed=seed + index),
                                    bevel=0.004, layer=layer, name="boarded", tilt=-slope))
            elif index in broken:
                made.append(geo.box((pw, ph, 0.01), (px, py, z + 0.03), 0.0, mat.flat((0.008, 0.008, 0.01)), bevel=0.0,
                                    layer=layer, name="void"))
            elif lit and (index * 7 + seed) % 5 != 3:
                # a warm pane (baked: it dims with the night like everything, and still is the brightest thing up
                # here) and, in every other one, a small core painted with the animated range: that flickers and
                # stays lit after dark
                made.append(geo.box((pw, ph, 0.012), (px, py, pz), 0.0,
                                    glow_glass(seed=seed * 3 + index, strength=0.36 + 0.16 * ((index * 5 + seed) % 3)),
                                    bevel=0.0, layer=layer, name="pane_lit", tilt=-slope))
                if (index + seed) % 2 == 0:
                    core = geo.box((pw * 0.42, ph * 0.38, 0.012), (px + pw * 0.12, py + ph * 0.1, pz + 0.008), 0.0,
                                   mat.emitter((1.0, 0.45, 0.1), 1.2), bevel=0.0, layer=layer, name="pane_core", tilt=-slope)
                    geo.set_fx(core, lit)
                    made.append(core)
            else:
                made.append(geo.box((pw, ph, 0.012), (px, py, pz), 0.0, glass or mat.glass(dirt=0.75), bevel=0.0, layer=layer,
                                    name="pane", tilt=-slope))
            index += 1
    for i in range(1, nx):
        bx = x0 + (pw + t) * i + t / 2.0
        made.append(geo.box((t, h, curb + pitch / 2.0), (bx, cy, z), 0.0, frame, bevel=0.004, layer=layer, name="bar"))
    for j in range(1, ny):
        by = y0 + (ph + t) * j + t / 2.0
        made.append(geo.box((w, t, curb + pitch * (1.0 - (by - y0) / h)), (cx, by, z), 0.0, frame, bevel=0.004, layer=layer,
                            name="bar"))
    return made


def hatch(x0, y0, x1, y1, z=0.0, colour=(0.26, 0.20, 0.05), open_deg=0.0, seed=0, layer="main"):
    """A roof hatch: a curb, a lid of painted plate with a handle and two hinges on its far edge.
    open_deg > 0 props the lid open on a stick (a black opening under it)."""
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    steel = mat.steel(rust=0.7, seed=seed)
    made = [geo.box((w + 0.2, h + 0.2, 0.012), (cx, cy, z + 0.02), 0.0, tar(), bevel=0.0, layer=layer, name="tar"),
            geo.box((w, h, 0.12), (cx, cy, z), 0.0, steel, bevel=0.008, layer=layer, name="curb")]
    lid_mat = mat.painted_metal(colour, flaking=0.55, seed=seed + 3)
    if open_deg:
        made.append(geo.box((w - 0.1, h - 0.1, 0.01), (cx, cy, z + 0.115), 0.0, mat.flat((0.006, 0.006, 0.008)), bevel=0.0,
                            layer=layer, name="void"))
        # hinged on the far (y0) edge: the lid stands up towards the back
        lid = geo.slab(w + 0.06, h + 0.04, 0.03, (x1 + 0.03, y0, z + 0.13), geo.U, lid_mat, bevel=0.004, layer=layer,
                       name="lid", tilt=90.0 - open_deg)
        geo.set_block(lid, 0)
        made.append(lid)
        top = (cx, y0 + (h + 0.04) * math.cos(math.radians(open_deg)), z + 0.13 + (h + 0.04) * math.sin(math.radians(open_deg)))
        made.append(geo.pipe([(cx + 0.2, y1 - 0.05, z + 0.12), (top[0] + 0.2, top[1], top[2])], 0.018, steel, layer, "prop"))
    else:
        made.append(geo.box((w + 0.08, h + 0.08, 0.035), (cx, cy, z + 0.12), 0.0, lid_mat, bevel=0.006, layer=layer, name="lid"))
        made.append(geo.pipe([(cx - 0.12, y1 - 0.14, z + 0.155), (cx - 0.12, y1 - 0.14, z + 0.2), (cx + 0.12, y1 - 0.14, z + 0.2),
                              (cx + 0.12, y1 - 0.14, z + 0.155)], 0.016, steel, layer, "handle"))
        for hx_ in (x0 + 0.12, x1 - 0.12):
            made.append(geo.box((0.12, 0.09, 0.03), (hx_, y0 - 0.02, z + 0.135), 0.0, steel, bevel=0.004, layer=layer, name="hinge"))
    return made


def stub(x, y, height=0.5, radius=0.1, z=0.0, cap="cone", material=None, smoke_black=True, flashing=True, seed=0,
         layer="main"):
    """A short flue through the roof: a tarred flashing plate, the pipe, a hat ("cone", "tee", "none")."""
    material = material or mat.steel(rust=0.75, seed=seed)
    made = []
    if flashing:
        made.append(geo.box((radius * 5.2, radius * 5.2, 0.015), (x, y, z + 0.035), 12.0 * (seed % 5), tar(), bevel=0.0,
                            layer=layer, name="flashing"))
    made.append(geo.cylinder(radius, height, (x, y, z), material, 12, layer, "stub"))
    if smoke_black:
        made.append(geo.cylinder(radius + 0.004, height * 0.3, (x, y, z + height * 0.7), mat.flat((0.012, 0.012, 0.012)), 12,
                                 layer, "soot"))
    top = z + height
    if cap == "cone":
        made.append(sx.cone(radius * 2.1, radius * 1.1, (x, y, top + 0.07), material, layer=layer, name="hat"))
        for a in (0.0, 120.0, 240.0):
            ca, sa = math.cos(math.radians(a)) * radius, math.sin(math.radians(a)) * radius
            made.append(geo.pipe([(x + ca, y + sa, top - 0.02), (x + ca * 1.5, y + sa * 1.5, top + 0.08)], 0.012, material, layer,
                                 "stay"))
    elif cap == "tee":
        made.append(geo.pipe([(x - radius * 2.6, y, top), (x + radius * 2.6, y, top)], radius * 0.95, material, layer, "tee"))
    return made


def mushroom(x, y, height=0.4, radius=0.2, z=0.0, material=None, seed=0, layer="main"):
    """A mushroom ventilator: a short neck and a wide domed cap."""
    material = material or mat.painted_metal((0.20, 0.21, 0.20), flaking=0.5, seed=seed)
    return [geo.box((radius * 3.0, radius * 3.0, 0.014), (x, y, z + 0.035), 20.0, tar(), bevel=0.0, layer=layer, name="flashing"),
            geo.lathe([(radius * 0.55, 0.0), (radius * 0.55, height * 0.6), (radius, height * 0.6), (radius, height * 0.68),
                       (radius * 0.8, height * 0.9), (radius * 0.35, height), (0.0, height)], (x, y, z), material, 14,
                      layer=layer, name="mushroom")]


def box_vent(x, y, size=(0.7, 0.5, 0.4), z=0.0, rot=0.0, material=None, seed=0, layer="main"):
    """A louvred tin box (a fan housing, an air cooler): dark slats on its front face."""
    material = material or mat.painted_metal((0.17, 0.18, 0.17), flaking=0.5, seed=seed)
    w, d, h = size
    made = [geo.box((w, d, h), (x, y, z), rot, material, bevel=0.012, layer=layer, name="vent_box")]
    f = sx.Frame((x, y, z), 180.0 + rot)
    for k in range(3):
        made.append(geo.box((w * 0.78, 0.02, h * 0.12), f.at(0.0, d / 2.0 + 0.005, h * (0.22 + 0.24 * k)), f.rot,
                            mat.flat((0.01, 0.01, 0.012)), bevel=0.0, layer=layer, name="slat"))
    return made


def car_door(x, y, rot=0.0, colour=DUSTY_BLUE, z=0.05, seed=0, size=(1.05, 1.15), layer="main"):
    """A car door lying flat as a roof patch: the skin, the window opening (dark), a handle."""
    w, h = size
    paint = mat.painted_metal(colour, flaking=0.45, seed=seed)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def at(a, b, zz=0.0):
        return (x + a * c - b * s, y + a * s + b * c, z + zz)
    made = [geo.box((w + 0.12, h + 0.1, 0.012), at(0, 0, -0.012), rot, tar(), bevel=0.0, layer=layer, name="tar"),
            geo.box((w, h * 0.55, 0.05), at(0.0, h * 0.225), rot, paint, bevel=0.02, layer=layer, name="door_skin")]
    for a in (-w / 2 + 0.05, w / 2 - 0.05):
        made.append(geo.box((0.09, h * 0.45, 0.04), at(a, -h * 0.275), rot, paint, bevel=0.012, layer=layer, name="door_pillar"))
    made.append(geo.box((w, 0.09, 0.04), at(0.0, -h / 2 + 0.045), rot, paint, bevel=0.012, layer=layer, name="door_top"))
    made.append(geo.box((w - 0.18, h * 0.45 - 0.09, 0.012), at(0.0, -h * 0.23, -0.005), rot, mat.flat((0.012, 0.014, 0.016), 0.3),
                        bevel=0.0, layer=layer, name="door_window"))
    made.append(geo.box((0.16, 0.04, 0.03), at(w * 0.3, h * 0.06, 0.05), rot, mat.aluminium(rivets=False), bevel=0.006,
                        layer=layer, name="handle"))
    return made


def bonnet(x, y, rot=0.0, colour=OXIDE, z=0.05, seed=0, size=(1.45, 1.2), layer="main"):
    """A car bonnet as a patch: a bulged plate with a centre crease, narrower at the nose."""
    w, h = size
    nx, ny = 10, 8
    bm = bmesh.new()
    grid = []
    for j in range(ny + 1):
        v = j / ny
        row = []
        for i in range(nx + 1):
            u = i / nx
            half = w / 2.0 * (1.0 - 0.16 * v)
            px = (u - 0.5) * 2.0 * half
            bulge = 0.10 * math.sin(math.pi * u) * (0.5 + 0.5 * math.sin(math.pi * v)) + 0.015 * (1.0 - abs(u - 0.5) * 2.0)
            row.append(bm.verts.new((px, (v - 0.5) * h, bulge)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    made = [geo.box((w + 0.1, h + 0.1, 0.012), (x, y, z - 0.012), rot, tar(), bevel=0.0, layer=layer, name="tar"),
            geo._finish(bm, "bonnet", mat.painted_metal(colour, flaking=0.5, seed=seed), (x, y, z), rot, layer, smooth=True,
                        solidify=0.02)]
    return made


def road_sign(what, x, y, rot=0.0, z=0.05, size=1.0, seed=0, layer="main"):
    """A road sign nailed flat on the roof. what: "green" (a direction board with a border and an
    arrow), "diamond" (yellow warning), "stop" (red octagon, a white bar), "speed" (white board,
    black rim, two digits as bars), "shield" (a route marker)."""
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def at(a, b, zz=0.0):
        return (x + a * c - b * s, y + a * s + b * c, z + zz)

    def flat(points, material, zz, name):
        bm = bmesh.new()
        bm.faces.new([bm.verts.new((a, b, 0.0)) for a, b in points])
        return geo._finish(bm, name, material, at(0, 0, zz), rot, layer, smooth=False, solidify=0.012)
    white = sx.enamel((0.60, 0.59, 0.54), chips=0.35, seed=seed + 1)
    black = mat.flat((0.02, 0.02, 0.022), roughness=0.5)
    made = []
    if what == "green":
        w, h = 1.7 * size, 0.95 * size
        made.append(geo.box((w, h, 0.02), at(0, 0), rot, sx.enamel((0.03, 0.17, 0.09), chips=0.35, seed=seed), bevel=0.004,
                            layer=layer, name="sign"))
        for a, b, sw, sh in ((0, -h / 2 + 0.07, w - 0.1, 0.045), (0, h / 2 - 0.07, w - 0.1, 0.045),
                             (-w / 2 + 0.07, 0, 0.045, h - 0.1), (w / 2 - 0.07, 0, 0.045, h - 0.1)):
            made.append(geo.box((sw, sh, 0.008), at(a, b, 0.02), rot, white, bevel=0.0, layer=layer, name="border"))
        made.append(flat([(-0.5 * size, -0.07), (0.15 * size, -0.07), (0.15 * size, -0.22 * size), (0.55 * size, 0.0),
                          (0.15 * size, 0.22 * size), (0.15 * size, 0.07), (-0.5 * size, 0.07)], white, 0.024, "arrow"))
    elif what == "diamond":
        r = 0.62 * size
        made.append(flat([(0, -r), (r, 0), (0, r), (-r, 0)], sx.enamel((0.50, 0.36, 0.03), chips=0.4, seed=seed), 0.0, "sign"))
        made.append(flat([(0, -r * 0.42), (r * 0.16, -r * 0.1), (r * 0.05, -r * 0.1), (r * 0.05, r * 0.45), (-r * 0.05, r * 0.45),
                          (-r * 0.05, -r * 0.1), (-r * 0.16, -r * 0.1)], black, 0.014, "mark"))
    elif what == "stop":
        r = 0.55 * size
        made.append(flat([(r * math.cos(math.radians(22.5 + 45 * k)), r * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)],
                         sx.enamel((0.42, 0.04, 0.03), chips=0.4, seed=seed), 0.0, "sign"))
        made.append(geo.box((r * 1.3, r * 0.3, 0.008), at(0, 0, 0.014), rot, white, bevel=0.0, layer=layer, name="bar"))
    elif what == "speed":
        w, h = 0.75 * size, 0.95 * size
        made.append(geo.box((w, h, 0.02), at(0, 0), rot, white, bevel=0.004, layer=layer, name="sign"))
        for a, b, sw, sh in ((0, -h / 2 + 0.05, w - 0.06, 0.04), (0, h / 2 - 0.05, w - 0.06, 0.04),
                             (-w / 2 + 0.05, 0, 0.04, h - 0.06), (w / 2 - 0.05, 0, 0.04, h - 0.06),
                             (-0.14 * size, 0.08 * size, 0.1 * size, 0.42 * size), (0.14 * size, 0.08 * size, 0.1 * size, 0.42 * size)):
            made.append(geo.box((sw, sh, 0.008), at(a, b, 0.02), rot, black, bevel=0.0, layer=layer, name="ink"))
    else:
        r = 0.5 * size
        made.append(flat([(-r, -r * 0.8), (r, -r * 0.8), (r, r * 0.2), (0, r), (-r, r * 0.2)], white, 0.0, "sign"))
        made.append(flat([(-r * 0.8, -r * 0.62), (r * 0.8, -r * 0.62), (r * 0.8, -r * 0.2), (-r * 0.8, -r * 0.2)],
                         sx.enamel((0.07, 0.12, 0.26), chips=0.3, seed=seed), 0.014, "band"))
    made.insert(0, geo.box((1.1 * size, 1.1 * size, 0.01), at(0, 0, -0.012), rot + (45.0 if what == "diamond" else 0.0), tar(),
                           bevel=0.0, layer=layer, name="tar"))
    return made


def gutter_stain(x, y0, y1, width=0.3, z=0.045, layer="main"):
    """A dark run of dirt down the roof from (x, y0) to (x, y1): where a pipe drips or water gathers."""
    bm = bmesh.new()
    n = 8
    left, right = [], []
    for k in range(n + 1):
        t = k / n
        w = width * (0.35 + 0.65 * math.sin(math.pi * min(1.0, t * 1.4)) ** 0.7) * (1.0 - 0.5 * t)
        wob = 0.05 * math.sin(7.0 * t + x)
        left.append(bm.verts.new((x - w / 2.0 + wob, y0 + (y1 - y0) * t, z)))
        right.append(bm.verts.new((x + w / 2.0 + wob, y0 + (y1 - y0) * t, z)))
    for k in range(n):
        bm.faces.new((left[k], right[k], right[k + 1], left[k + 1]))
    return geo._finish(bm, "stain", mat.flat((0.03, 0.022, 0.016), roughness=0.9), (0, 0, 0), 0.0, layer, smooth=False)


def pipe_run(points, radius=0.06, z=0.1, material=None, seed=0, saddles=True, layer="main"):
    """A pipe lying on the roof through (x, y) points on wooden saddles, with a flange at every bend."""
    material = material or mat.steel(rust=0.7, seed=seed)
    pts = [(px, py, z + radius) for px, py in points]
    made = [geo.pipe(pts, radius, material, layer, "pipe_run")]
    for px, py, pz in pts[1:-1]:
        made.append(sx.sphere(radius * 1.5, (px, py, pz), material, layer=layer, name="elbow"))
    if saddles:
        for (ax, ay, _), (bx, by, _) in zip(pts, pts[1:]):
            length = math.hypot(bx - ax, by - ay)
            count = max(1, int(length / 1.6))
            for k in range(count):
                t = (k + 0.5) / count
                made.append(geo.box((0.3, 0.14, z), (ax + (bx - ax) * t, ay + (by - ay) * t, 0.03),
                                    math.degrees(math.atan2(by - ay, bx - ax)) + 90.0,
                                    mat.planks(colour=(0.2, 0.11, 0.05), width=0.3, axis="X", grey=0.5, seed=seed + k), bevel=0.006,
                                    layer=layer, name="saddle"))
    return made


# ================================================================== plank roofs
def plank_courses(x0, y0, x1, y1, z=0.0, courses=3, board=0.24, seed=1, colours=((0.25, 0.14, 0.065), (0.19, 0.11, 0.05)),
                  grey=0.45, ragged=0.25, missing=0.0, tarred=0.12, new=0.08, skip=None, layer="main", felt=True):
    """A boarded roof: `courses` rows of boards running down the slope, the upper row lapping the
    next. Single boards are tarred black, replaced by new pale ones or missing (the roofing felt
    shows). skip(xa, ya, xb, yb) leaves boards out. Returns the boards (for paint_on)."""
    r = random.Random(seed)
    made = []
    if felt:
        geo.box((x1 - x0, y1 - y0 - 0.1, 0.01), ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z - 0.012), 0.0,
                mat.flat((0.022, 0.02, 0.02), roughness=0.9), bevel=0.0, layer=layer, name="felt")
    length = (y1 - y0) / courses
    count = max(1, int(round((x1 - x0) / board)))
    step = (x1 - x0) / count
    for course in range(courses):
        ya = y0 + length * course - (0.14 if course else 0.0)
        yb = y0 + length * (course + 1)
        shift = r.uniform(0.0, step)
        for i in range(-1, count + 1):
            xa, xb = x0 + step * i + shift, x0 + step * (i + 1) + shift
            xa, xb = max(x0, xa), min(x1, xb)
            if xb - xa < 0.08:
                continue
            a = ya + (r.uniform(0.0, ragged * 0.4) if course == 0 else 0.0)
            b = yb - r.uniform(0.0, ragged if course == courses - 1 else ragged * 0.3)
            if skip and skip(xa, a, xb, b):
                continue
            roll = r.random()
            if roll < missing:
                continue
            if roll < missing + tarred:
                material = mat.flat((0.03, 0.028, 0.026), roughness=0.7)
            elif roll < missing + tarred + new:
                material = mat.planks(colour=(0.36, 0.26, 0.14), width=board * 3, axis="X", grey=0.1, seed=seed * 7 + i)
            else:
                colour = colours[(i + course) % len(colours)] if r.random() < 0.7 else r.choice(colours)
                t = r.uniform(0.8, 1.15)
                material = mat.planks(colour=tuple(c * t for c in colour), width=board * 3, axis="X",
                                      grey=min(1.0, grey * r.uniform(0.5, 1.7)), seed=seed * 17 + i + course * 53)
            obj = geo.box((b - a, xb - xa - 0.014, 0.035), ((xa + xb) / 2.0, (a + b) / 2.0,
                                                           z + 0.03 - 0.014 * course + r.uniform(0.0, 0.01)),
                          90.0 + r.uniform(-0.6, 0.6), material, bevel=0.005, layer=layer, name=f"board{course}_{i}")
            obj["rx_box"] = (xa, a, xb, b)
            made.append(obj)
    return made


def wing_panel(x0, y0, x1, y1, z=0.05, bands=(), tint=(0.30, 0.31, 0.32), seed=0, rust=0.3, layer="main"):
    """A piece of aircraft skin (riveted panels, painted bands in metres of its own width/length)
    laid flat as roofing over x0..x1, y0..y1."""
    from . import gate_extra as gx
    skin = gx.skin(tint=tint, panel=(1.1, 0.7), bands=bands, rust=rust, grime=0.6, wear=0.45, seed=seed, tone=0.4)
    made = [geo.box((x1 - x0 + 0.14, y1 - y0 + 0.14, 0.012), ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z - 0.012), 0.0, tar(),
                    bevel=0.0, layer=layer, name="tar")]
    panel = gx.plate(x1 - x0, y1 - y0, (x1, y0, z + 0.02), geo.U, skin, thickness=0.025, tilt=90.0, layer=layer, name="wing_skin",
                     dent=0.006, seed=seed)
    geo.set_block(panel, 0)
    made.append(panel)
    return made


def flat_text(body, x, y, z, size, material=None, rot=180.0, font="din", spacing=1.0, align="CENTER", layer="main"):
    """Thin lettering lying flat ON a plate at height z (for a wing panel or a sign used as roofing)."""
    obj = geo.lettering(body, (x, y, z), rot, size, depth=0.008, bevel=0.0, font=font, align=align, layer=layer, tilt=90.0,
                        material=material or mat.sign_paint((0.05, 0.05, 0.055), wear=0.5), spacing=spacing)
    return obj


def planter(x, y, z=0.03, size=(1.1, 0.45, 0.26), rot=0.0, seed=0, plants=5, layer="main"):
    """A plank box of earth with a row of scrubby plants."""
    r = random.Random(seed)
    w, d, h = size
    wood = mat.planks(colour=(0.22, 0.13, 0.06), width=0.14, axis="X", grey=0.4, seed=seed)
    made = [geo.box((w, d, h), (x, y, z), rot, wood, bevel=0.008, layer=layer, name="planter"),
            geo.box((w - 0.08, d - 0.08, 0.03), (x, y, z + h - 0.02), rot, mat.flat((0.045, 0.03, 0.02)), bevel=0.0, layer=layer,
                    name="soil")]
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for k in range(plants):
        a = (k + 0.5) / plants * (w - 0.2) - (w - 0.2) / 2.0
        green = mat.flat((0.05 * r.uniform(0.7, 1.4), 0.13 * r.uniform(0.7, 1.3), 0.03), roughness=0.9)
        made.append(sx.sphere(r.uniform(0.11, 0.17), (x + a * c, y + a * s, z + h + r.uniform(0.04, 0.1)), green, layer=layer,
                              name="plant", squash=r.uniform(0.8, 1.3)))
    return made


def washing_line(a, b, z=0.0, height=1.5, seed=0, layer="main", colours=None, count=4, sag=0.12):
    """Two poles (propped with a strut each) from a to b (x, y) and washing on a line between them."""
    r = random.Random(seed)
    steel = mat.steel(rust=0.7, seed=seed)
    made = []
    for px, py, lean in ((a[0], a[1], -1.0), (b[0], b[1], 1.0)):
        made.append(geo.pipe([(px, py, z), (px, py, z + height + 0.06)], 0.03, steel, layer, "pole"))
        made.append(geo.box((0.3, 0.3, 0.05), (px, py, z + 0.03), 30.0, mat.concrete(seed=seed), bevel=0.01, layer=layer, name="foot"))
        dx, dy = (b[0] - a[0]), (b[1] - a[1])
        ln = math.hypot(dx, dy)
        made.append(geo.pipe([(px, py, z + height * 0.6), (px + lean * dx / ln * 0.5, py + lean * dy / ln * 0.5, z + 0.04)], 0.02,
                             steel, layer, "strut"))
    p0, p1 = (a[0], a[1], z + height), (b[0], b[1], z + height)
    made.append(geo.cable(p0, p1, sag=sag, radius=0.014, layer=layer))
    at, rot, length = geo.span(a, b)
    f = sx.Frame((a[0], a[1], 0.0), rot)
    colours = colours or ((0.45, 0.42, 0.36), (0.30, 0.07, 0.05), (0.10, 0.16, 0.24), (0.36, 0.28, 0.10), (0.12, 0.20, 0.10))
    for k in range(count):
        u = length * (k + 0.6) / (count + 0.2)
        t = u / length
        zz = z + height - sag * 4.0 * t * (1.0 - t) - 0.01
        made.append(sx.cloth(f, u, zz, r.uniform(0.4, 0.62), r.uniform(0.45, 0.8), sx.fabric(colours[(k + seed) % len(colours)], seed=seed + k),
                             folds=1.5, depth=0.04, seed=seed + k, layer=layer))
    return made


# ============================================================== wear on upright things
def runs(frame, items, d=0.02, width=0.06, colour=(0.075, 0.032, 0.016), layer="main"):
    """Rust runs on an upright face: for every (u, z_top, length) a thin dark strip that starts at a
    fixing and tapers down the face (frame coordinates, `d` m proud of it). Three or four of unequal
    length under a rim or a row of bolts are what makes a clean panel look as if it has stood outside."""
    made = []
    material = mat.flat(colour, roughness=0.9)
    for k, (u, z_top, length) in enumerate(items):
        w = width * (0.7 + 0.5 * ((k * 37) % 5) / 4.0)
        made.append(sx.plate([(-w / 2.0, 0.0), (w / 2.0, 0.0), (w * 0.3, -length * 0.6), (w * 0.08, -length), (-w * 0.2, -length * 0.7)],
                             frame.at(u, d, z_top), frame.rot, material, thickness=0.006, layer=layer, name="run"))
    return made
