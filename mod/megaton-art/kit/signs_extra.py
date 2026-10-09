# SPDX-License-Identifier: MIT
"""Extra kit of the "signs" author (shop signs, lights, street dressing). Shared: anybody may use it.

    from kit import signs_extra as sx

    f = sx.Frame(origin, geo.U)            a local frame for anything that has a FACE:
    f.at(u, d, z)                          u runs along the reading direction (to the screen right for
                                           rot U, V and SCREEN), d comes OUT of the face towards the
                                           viewer, z is up. All in metres, returns a world point.

Lettering        letters()        one object per glyph, so single letters can be dead, crooked or missing
                 stencil()        letters painted ON a face (thin, flush) with stencil bridges
Sign hardware    plank_panel()    a board nailed up from separate planks (ragged ends, gaps)
                 sheet_panel()    a board riveted up from sheet-iron panels with visible seams
                 frame_rim()      angle-iron rim round a board
                 gooseneck()      a lamp on a bent pipe that lights a board from above
                 lattice_post()   trussed steel leg; scaffold_pole() a pole with a foot plate
                 bracket()        wall / post arm with a diagonal strut; bolts() fixing points on a face
Shapes           star(), plate() (any flat outline), arrow(), disc(), ring(), cross(), sphere(), cone()
Soft things      cloth()          hanging washing / flag; sag_sheet() a tarpaulin slung between points
Light            caged_lamp(), lantern(), flames(), bulbs_on() (bulbs with given colours / fx ranges)
Materials        whitewash() (paint over boards, any colour), brass(), enamel() (glossy sign tin), fabric(),
                 ember(), dead_tube() (an unlit neon tube / dead bulb)

Scale reminders (pipeline/proj.py): 1 m is 40 px across a SCREEN-facing face, 34.6 px along a
U face, 20 px along a V face and 36 px up. Lettering under 0.28 m cap height is noise; a tube
or rod thinner than 0.02 m radius breaks up; a bolt head is one pixel at 0.03 m radius.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from pipeline import proj as G
from . import geo, mat
from .nodes import Graph


# ----------------------------------------------------------------------- frame
class Frame:
    def __init__(self, origin=(0.0, 0.0, 0.0), rot=geo.U):
        self.origin = Vector((origin[0], origin[1], origin[2] if len(origin) > 2 else 0.0))
        self.rot = float(rot)
        a = math.radians(rot)
        self.right = Vector((math.cos(a), math.sin(a), 0.0))       # local +X: the reading direction
        self.front = Vector((math.sin(a), -math.cos(a), 0.0))      # local -Y: out of the face

    def at(self, u=0.0, d=0.0, z=0.0):
        p = self.origin + self.right * u + self.front * d
        return (p.x, p.y, p.z + z)

    def moved(self, u=0.0, d=0.0, z=0.0, rot=None):
        return Frame(self.at(u, d, z), self.rot if rot is None else rot)


# ------------------------------------------------------------------- materials
def _seeded(g, seed):
    return g.mapping(g.coords(), location=(seed * 7.31, seed * 3.17, seed * 5.53))


def whitewash(colour=(0.62, 0.60, 0.53), wood=(0.20, 0.12, 0.06), wear=0.35, axis="X", seed=0.0, glow=0.0):
    """Paint brushed over boards and half weathered off again. axis: local axis the grain runs along.
    Any colour works: (0.62, 0.60, 0.53) is lime wash, (0.10, 0.22, 0.24) an old teal door."""
    def build():
        g = Graph("whitewash")
        p = _seeded(g, seed)
        scale = {"X": (1.0, 10.0, 10.0), "Y": (10.0, 1.0, 10.0), "Z": (10.0, 10.0, 1.0)}[axis]
        grain = g.noise(g.mapping(p, scale=scale), scale=1.0, detail=3.0, roughness=0.6)
        big = g.noise(p, scale=2.4, detail=4.0, roughness=0.7, distortion=0.5)
        amount = g.add(g.add(g.mul(big, 0.75), g.mul(grain, 0.45)), g.mul(g.smooth(g.ao(0.15), 0.9, 0.4), 0.2))
        edge = 1.06 - wear * 0.6
        mask = g.smooth(amount, edge - 0.04, edge + 0.04)
        paint = g.mix(g.remap(grain, 0.3, 0.7, 0.0, 0.4), colour, tuple(c * 0.70 for c in colour))
        paint = g.mix(g.mul(mat._streaks(g, p), 0.30), paint, mat.DIRT)
        bare = g.mix(g.remap(grain, 0.3, 0.7), wood, tuple(c * 0.4 for c in wood))
        base = g.mix(mask, paint, bare)
        base = g.mix(g.smooth(g.ao(0.10), 0.8, 0.3), base, mat.SOOT)
        g.principled(base=base, roughness=0.85, specular=0.15,
                     bump=g.bump(g.sub(g.mul(grain, 0.3), mask), 0.006),
                     emission=base if glow else None, emission_strength=glow)
        return g.material
    return mat._cached(("sx_whitewash", colour, wood, wear, axis, seed, glow), build)


def enamel(colour=(0.5, 0.05, 0.04), chips=0.25, seed=0.0, glow=0.0):
    """Glossy sign enamel on tin: flat strong colour, a few rust chips, a highlight. glow > 0 = lit from inside."""
    def build():
        g = Graph("enamel")
        p = _seeded(g, seed)
        n = g.noise(p, scale=6.0, detail=4.0, roughness=0.75)
        mask = g.smooth(n, 0.86 - chips * 0.4, 0.89 - chips * 0.4)
        fade = g.mix(g.remap(g.noise(p, scale=1.5, detail=2.0), 0.3, 0.7), colour, tuple(min(1.0, c * 1.25 + 0.01) for c in colour))
        base = g.mix(mask, fade, mat.RUST_MID)
        g.principled(base=base, roughness=g.mix_value(mask, 0.35, 0.9), specular=0.4,
                     emission=base if glow else None, emission_strength=glow)
        return g.material
    return mat._cached(("sx_enamel", colour, chips, seed, glow), build)


def brass(tarnish=0.5, seed=0.0):
    def build():
        g = Graph("brass")
        p = _seeded(g, seed)
        n = g.noise(p, scale=5.0, detail=4.0, roughness=0.7)
        mask = g.smooth(n, 0.75 - tarnish * 0.4, 0.95 - tarnish * 0.4)
        base = g.mix(mask, (0.62, 0.40, 0.10), (0.10, 0.09, 0.04))
        g.principled(base=base, roughness=g.mix_value(mask, 0.28, 0.7), metallic=g.mix_value(mask, 0.9, 0.2), specular=0.5)
        return g.material
    return mat._cached(("sx_brass", tarnish, seed), build)


def fabric(colour=(0.5, 0.5, 0.48), stripes=None, seed=0.0):
    """Washing, flags, awning canvas. stripes: (second colour, stripe width m) across local X."""
    def build():
        g = Graph("fabric")
        p = _seeded(g, seed)
        stain = g.noise(p, scale=3.0, detail=3.0, roughness=0.7)
        base = g.mix(g.remap(stain, 0.3, 0.75), tuple(c * 0.72 for c in colour), tuple(min(1.0, c * 1.15) for c in colour))
        if stripes:
            x, _, _ = g.separate(g.coords())
            band = g.greater(g.fract(g.div(x, stripes[1] * 2.0)), 0.5)
            base = g.mix(band, base, stripes[0])
        g.principled(base=base, roughness=0.95, specular=0.05)
        return g.material
    return mat._cached(("sx_fabric", colour, stripes, seed), build)


def ember(colour=(1.0, 0.35, 0.05), strength=2.5):
    return mat.emitter(colour, strength)


def dead_tube():
    """An unlit neon tube / dead bulb: dark smoked glass."""
    return mat.flat((0.07, 0.035, 0.03), roughness=0.25)


# ----------------------------------------------------------------- flat shapes
def plate(points, at, rot=geo.U, material=None, thickness=0.02, tilt=0.0, roll=0.0, layer="main", name="plate",
          bevel=0.0):
    """Any flat outline standing in the local XZ plane: points [(x, z), ...] in metres, counter-clockwise
    or clockwise. Used for arrows, diamonds, shields, cut-out symbols."""
    bm = bmesh.new()
    verts = [bm.verts.new((x, 0.0, z)) for x, z in points]
    bm.faces.new(verts)
    return geo._finish(bm, name, material, at, rot, layer, tilt, roll, smooth=False, solidify=thickness, bevel=bevel)


def star(radius, at, rot=geo.U, material=None, points=5, inner=0.42, relief=0.06, tilt=0.0, spin=0.0,
         layer="main", name="star"):
    """A pressed-tin star: every point is two facets meeting on a ridge, so it shades like a badge."""
    bm = bmesh.new()
    centre = bm.verts.new((0.0, -relief, 0.0))
    rim = []
    for i in range(points * 2):
        r = radius if i % 2 == 0 else radius * inner
        a = math.pi / 2 + math.radians(spin) + i * math.pi / points
        rim.append(bm.verts.new((r * math.cos(a), 0.0, r * math.sin(a))))
    back = bm.verts.new((0.0, 0.03, 0.0))
    for i in range(len(rim)):
        j = (i + 1) % len(rim)
        bm.faces.new((centre, rim[i], rim[j]))
        bm.faces.new((back, rim[j], rim[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return geo._finish(bm, name, material, at, rot, layer, tilt, smooth=False)


def disc(radius, at, rot=geo.U, material=None, thickness=0.03, dome=0.0, hole=0.0, tilt=0.0, layer="main",
         name="disc", segments=24):
    """A round plate facing the front (hub cap, road sign, pot lid, gauge). dome: height of its bulge;
    hole: radius of a hole in the middle (washer, gear blank)."""
    t = thickness
    if hole > 0.0:
        profile = [(hole, 0.0), (radius, 0.0), (radius, t), (hole, t), (hole, 0.0)]
    else:
        profile = [(0.0, 0.0), (radius, 0.0), (radius, t)]
        if dome:
            profile += [(radius * 0.8, t + dome * 0.45), (radius * 0.45, t + dome * 0.9), (0.0, t + dome)]
        else:
            profile += [(0.0, t)]
    return geo.lathe(profile, at, material, segments, rot, 90.0 + tilt, 0.0, layer, name)


def ring(centre, radius_u, radius_z, frame, material=None, tube=0.03, spin=0.0, layer="main", name="ring", count=28):
    """A welded hoop (ellipse) in the plane of `frame`, turned by `spin` degrees in that plane."""
    cu, cz = centre
    c, s = math.cos(math.radians(spin)), math.sin(math.radians(spin))
    points = []
    for i in range(count + 2):
        a = 2.0 * math.pi * i / count
        x, z = radius_u * math.cos(a), radius_z * math.sin(a)
        points.append(frame.at(cu + x * c - z * s, 0.0, cz + x * s + z * c))
    return geo.pipe(points, tube, material, layer, name)


def sphere(radius, at, material=None, layer="main", name="sphere", squash=1.0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=radius)
    if squash != 1.0:
        bmesh.ops.scale(bm, vec=(1.0, 1.0, squash), verts=bm.verts)
    return geo._finish(bm, name, material, at, 0.0, layer, smooth=True)


def cross(size, at, rot=geo.U, material=None, arm=0.34, thickness=0.03, tilt=0.0, layer="main"):
    """An equal-armed cross (clinic) facing the front; size = full height, arm = arm width as a share of it."""
    a = size * arm / 2.0
    h = size / 2.0
    points = [(-a, -h), (a, -h), (a, -a), (h, -a), (h, a), (a, a), (a, h), (-a, h), (-a, a), (-h, a), (-h, -a), (-a, -a)]
    return plate(points, at, rot, material, thickness, tilt, layer=layer, name="cross")


def arrow(length, at, rot=geo.U, material=None, shaft=0.18, head=0.42, thickness=0.02, spin=0.0, layer="main", tilt=0.0):
    """A flat arrow pointing along local +X (spin turns it in its plane: -90 = pointing down)."""
    hl = min(length * 0.45, head)
    pts = [(0.0, -shaft / 2), (length - hl, -shaft / 2), (length - hl, -head / 2), (length, 0.0),
           (length - hl, head / 2), (length - hl, shaft / 2), (0.0, shaft / 2)]
    c, s = math.cos(math.radians(spin)), math.sin(math.radians(spin))
    return plate([(x * c - z * s, x * s + z * c) for x, z in pts], at, rot, material, thickness, tilt, layer=layer, name="arrow")


# ------------------------------------------------------------------- lettering
def letters(text, frame, u, z, size, font="impact", material=None, d=0.03, depth=0.03, gap=0.06, tilt=0.0,
            align="CENTER", layer="main", outline=0.0, each=None, jitter=0.0, seed=0, space=0.45, bevel=0.004):
    """Lettering made of one object per glyph. Returns [(char, object, u centre, width)] left to right.

    material   one material, or a function (index, char) -> material
    each       optional function (index, char, object) called for every glyph: turn it, drop it,
               tag it with geo.set_fx - whatever a broken sign needs
    jitter     metres of random up / down per glyph (hand-set or hand-painted lettering)
    align      where `u` is: "CENTER", "LEFT" or "RIGHT" of the whole run
    """
    r = geo.rng(seed)
    made = []
    for index, char in enumerate(text):
        if char == " ":
            made.append((char, None, size * space))
            continue
        chosen = material(index, char) if callable(material) else material
        obj = geo.lettering(char, (0.0, 0.0, 0.0), frame.rot, size, depth=depth, bevel=bevel, font=font, material=chosen,
                            align="LEFT", layer=layer, tilt=tilt, outline=outline, name=f"glyph_{index}")
        bpy.context.view_layer.update()
        made.append((char, obj, max(obj.dimensions.x, size * 0.18)))
    total = sum(width for _, _, width in made) + gap * size * (len(made) - 1)
    cursor = {"CENTER": u - total / 2.0, "LEFT": u, "RIGHT": u - total}[align]
    out = []
    for index, (char, obj, width) in enumerate(made):
        if obj is not None:
            # a FONT object's origin is the pen position; its ink starts a little to the right of it
            bearing = min((corner[0] for corner in obj.bound_box), default=0.0)
            obj.location = Vector(frame.at(cursor - bearing, d, z + (r.uniform(-jitter, jitter) if jitter else 0.0)))
            if each:
                each(index, char, obj)
            out.append((char, obj, cursor + width / 2.0, width))
        cursor += width + gap * size
    return out


def stencil(text, frame, u, z, size, colour=(0.75, 0.74, 0.68), font="din", d=0.012, wear=0.5, seed=0,
            bridges=True, layer="main", tilt=0.0, gap=0.08, align="CENTER", glow=0.0):
    """Stencilled marking: thin flush letters, with the bars a stencil leaves across every glyph."""
    paint = mat.sign_paint(colour, wear=wear, seed=seed, glow=glow)
    made = letters(text, frame, u, z, size, font, paint, d=d, depth=0.006, gap=gap, tilt=tilt, align=align, layer=layer,
                   bevel=0.0)
    return made


# --------------------------------------------------------------- sign hardware
def plank_panel(frame, u0, u1, z0, z1, d=0.0, colours=((0.27, 0.14, 0.06),), paint=None, wear=0.35, thickness=0.035,
                vertical=False, plank=0.18, ragged=0.06, gap=0.012, seed=0, layer="main", lean=1.0, glow=0.0):
    """A board nailed up from separate planks between u0..u1 and z0..z1 (frame coordinates).
    paint: colour of a coat brushed over all of them (whitewash material), else bare boards in `colours`.
    Planks run across (horizontal) unless vertical=True. Returns the plank objects."""
    r = geo.rng(seed)
    objects = []
    span = (z1 - z0) if not vertical else (u1 - u0)
    count = max(1, int(round(span / plank)))
    step = span / count
    for i in range(count):
        if paint is not None:
            material = whitewash(paint, wear=min(1.0, max(0.0, wear + r.uniform(-0.15, 0.15))),
                                 axis="Z" if vertical else "X", seed=seed * 3.0 + i, glow=glow)
        else:
            material = mat.planks(r.choice(list(colours)), width=2.0, axis="Z" if vertical else "X",
                                  grey=r.uniform(0.1, 0.5), seed=seed * 3.0 + i)
        a, b = r.uniform(-ragged, ragged), r.uniform(-ragged, ragged)
        if vertical:
            size = (step - gap, thickness, (z1 - z0) + a + b)
            where = frame.at(u0 + step * (i + 0.5), d - thickness / 2.0, z0 - a)
            objects.append(geo.box(size, where, frame.rot, material, bevel=0.005, layer=layer, name="plank",
                                   roll=r.uniform(-lean, lean)))
        else:
            size = ((u1 - u0) + a + b, thickness, step - gap)
            where = frame.at((u0 - a + u1 + b) / 2.0, d - thickness / 2.0, z0 + step * i + gap / 2.0)
            objects.append(geo.box(size, where, frame.rot, material, bevel=0.005, layer=layer, name="plank",
                                   roll=r.uniform(-lean, lean) * 0.4))
    return geo.set_block(objects, geo.BLOCK_PROP)


def sheet_panel(frame, u0, u1, z0, z1, d=0.0, colour=(0.10, 0.16, 0.17), panels=3, thickness=0.03, flaking=0.35,
                seed=0, layer="main", patch=None, corrugated=False):
    """A sign face riveted up from `panels` sheets of painted iron with dark seams between them.
    patch: (index, colour) repaints one sheet (a repair in whatever paint there was)."""
    r = geo.rng(seed)
    objects = []
    step = (u1 - u0) / panels
    for i in range(panels):
        c = colour
        if patch and patch[0] == i:
            c = patch[1]
        material = mat.painted_metal(c, flaking=min(1.0, flaking + r.uniform(-0.1, 0.15)), seed=seed * 5.0 + i)
        size = (step - 0.015, thickness, (z1 - z0) - r.uniform(0.0, 0.02))
        where = frame.at(u0 + step * (i + 0.5), d - thickness / 2.0 + (0.008 if i % 2 else 0.0), z0)
        objects.append(geo.box(size, where, frame.rot, material, bevel=0.006, layer=layer, name="sheet"))
    return geo.set_block(objects, geo.BLOCK_PROP)


def frame_rim(frame, u0, u1, z0, z1, d=0.0, width=0.06, depth=0.07, material=None, layer="main"):
    """Angle iron round a board: four bars standing `depth` proud of the face."""
    material = material or mat.steel(rust=0.7, seed=5)
    objects = []
    for z in (z0 - width, z1):
        objects.append(geo.box((u1 - u0 + 2 * width, depth, width), frame.at((u0 + u1) / 2.0, d - depth / 2.0 + 0.02, z),
                               frame.rot, material, bevel=0.004, layer=layer, name="rim"))
    for u in (u0 - width / 2.0, u1 + width / 2.0):
        objects.append(geo.box((width, depth, z1 - z0), frame.at(u, d - depth / 2.0 + 0.02, z0), frame.rot, material,
                               bevel=0.004, layer=layer, name="rim"))
    return objects


def bolts(frame, points, d=0.02, radius=0.03, material=None, layer="main"):
    """Bolt heads / nail heads at [(u, z), ...] on a face: one pixel each, they read as fixing points."""
    material = material or mat.flat((0.04, 0.035, 0.03), roughness=0.5, metallic=0.5)
    return [disc(radius, frame.at(u, d, z), frame.rot, material, thickness=0.02, layer=layer, name="bolt", segments=8)
            for u, z in points]


def scaffold_pole(at, height, radius=0.045, material=None, foot=True, layer="main", lean=(0.0, 0.0)):
    """A scaffold tube standing on a concrete-filled tyre rim or a bolted plate. lean: metres the top
    is off plumb in (x, y). Returns [pole, foot]."""
    material = material or mat.steel(rust=0.65, seed=3)
    x, y, z = at[0], at[1], at[2] if len(at) > 2 else 0.0
    objects = [geo.pipe([(x, y, z), (x + lean[0], y + lean[1], z + height)], radius, material, layer, "pole")]
    if foot:
        objects.append(geo.cylinder(0.17, 0.09, (x, y, z), mat.concrete(seed=2), 12, layer, "foot"))
    return objects


def lattice_post(frame, u, height, width=0.34, depth=0.0, chord=0.04, lacing=0.022, material=None, layer="main",
                 bay=0.5, z0=0.0):
    """A trussed leg: two chords `width` apart along the frame, zig-zag lacing between them."""
    material = material or mat.steel(rust=0.7, seed=7)
    objects = []
    a, b = u - width / 2.0, u + width / 2.0
    for x in (a, b):
        objects.append(geo.pipe([frame.at(x, depth, z0), frame.at(x, depth, z0 + height)], chord, material, layer, "chord"))
    points = []
    z, side = z0 + 0.1, 0
    while z < z0 + height - 0.05:
        points.append(frame.at(a if side == 0 else b, depth, z))
        z += bay
        side ^= 1
    points.append(frame.at(a if side == 0 else b, depth, z0 + height - 0.05))
    objects.append(geo.pipe(points, lacing, material, layer, "lacing"))
    objects.append(geo.box((width + 0.2, 0.3, 0.08), frame.at(u, depth, z0), frame.rot, mat.concrete(seed=4), layer=layer,
                           name="pad"))
    return objects


def bracket(p_wall, p_tip, material=None, radius=0.03, strut=0.55, layer="main", scroll=False):
    """An arm from p_wall out to p_tip with a diagonal strut underneath (both world points at arm height)."""
    material = material or mat.steel(rust=0.6, seed=9)
    a, b = Vector(p_wall), Vector(p_tip)
    objects = [geo.pipe([tuple(a), tuple(b)], radius, material, layer, "arm")]
    low = a - Vector((0.0, 0.0, strut))
    mid = a.lerp(b, 0.7)
    objects.append(geo.pipe([tuple(low), tuple(mid)], radius * 0.75, material, layer, "strut"))
    return objects


def gooseneck(frame, u, z, reach=0.45, rise=0.35, material=None, layer="main", lit=True, strength=3.0,
              colour=(1.0, 0.78, 0.45), shade=0.13, d0=0.0):
    """A sign lamp: a pipe rising `rise` above (u, z) on the face and bending `reach` out over it, a tin
    shade, a bulb under it. Pair it with the piece's `light=` so the sign stays lit at night."""
    material = material or mat.steel(rust=0.5, seed=11)
    tip = frame.at(u, d0 + reach, z + rise * 0.72)
    objects = [geo.pipe([frame.at(u, d0, z - 0.05), frame.at(u, d0, z + rise * 0.7), frame.at(u, d0 + reach * 0.45, z + rise),
                         frame.at(u, d0 + reach * 0.85, z + rise * 0.95), tip], 0.022, material, layer, "gooseneck")]
    objects.append(geo.lathe([(0.0, 0.10), (shade * 0.35, 0.09), (shade, 0.0), (shade * 0.9, 0.0), (shade * 0.3, 0.07), (0.0, 0.08)],
                             (tip[0], tip[1], tip[2] - 0.08), enamel((0.06, 0.12, 0.10), chips=0.5, seed=3), 14, frame.rot,
                             -28.0, 0.0, layer, "shade"))
    if lit:
        objects.append(geo.bulb((tip[0], tip[1], tip[2] - 0.09), colour, 0.05, strength, layer))
    return objects


# ---------------------------------------------------------------------- lights
def caged_lamp(at, material=None, lit=True, strength=4.0, colour=(1.0, 0.74, 0.38), layer="main", size=1.0):
    """A hanging work lamp: tin cap, bulb, wire cage. `at` is the hook point at the top."""
    material = material or mat.steel(rust=0.45, seed=13)
    x, y, z = at
    s = size
    objects = [geo.lathe([(0.0, 0.0), (0.05 * s, -0.01 * s), (0.11 * s, -0.09 * s), (0.10 * s, -0.10 * s), (0.04 * s, -0.04 * s), (0.0, -0.035 * s)][::-1],
                         (x, y, z), enamel((0.42, 0.30, 0.05), chips=0.6, seed=5), 12, 0.0, 0.0, 0.0, layer, "lamp_cap")]
    centre = (x, y, z - 0.17 * s)
    if lit:
        objects.append(geo.bulb(centre, colour, 0.065 * s, strength, layer))
    else:
        objects.append(sphere(0.065 * s, centre, dead_tube(), layer, "bulb_off"))
    for k in range(4):                      # cage: four hoops from cap to tip
        a = math.pi * k / 4.0
        dx, dy = math.cos(a) * 0.10 * s, math.sin(a) * 0.10 * s
        objects.append(geo.pipe([(x + dx, y + dy, z - 0.09 * s), (x + dx * 1.05, y + dy * 1.05, z - 0.19 * s), (x, y, z - 0.29 * s),
                                 (x - dx * 1.05, y - dy * 1.05, z - 0.19 * s), (x - dx, y - dy, z - 0.09 * s)], 0.008 * s, material,
                                layer, "cage"))
    return objects


def lantern(at, size=1.0, lit=True, strength=3.5, colour=(1.0, 0.62, 0.22), layer="main", material=None, fx=None):
    """A storm lantern hanging from `at` (its ring): brass tank and cap, four guards, a glowing chimney."""
    material = material or brass(tarnish=0.45, seed=2)
    x, y, z = at
    s = size
    objects = [ring_xy((x, y, z - 0.05 * s), 0.05 * s, material, layer)]
    top = z - 0.10 * s
    objects.append(geo.lathe([(0.0, 0.0), (0.05 * s, -0.01 * s), (0.13 * s, -0.07 * s), (0.15 * s, -0.10 * s), (0.11 * s, -0.11 * s),
                              (0.0, -0.10 * s)][::-1], (x, y, top), material, 14, 0.0, 0.0, 0.0, layer, "lantern_cap"))
    glass_top, glass_bottom = top - 0.11 * s, top - 0.38 * s
    glow = mat.emitter(colour, strength) if lit else mat.glass((0.3, 0.25, 0.15), dirt=0.8)
    glass = geo.lathe([(0.07 * s, glass_bottom - top), (0.11 * s, (glass_bottom + glass_top) / 2.0 - top - 0.03 * s),
                       (0.085 * s, glass_top - top)], (x, y, top), glow, 14, 0.0, 0.0, 0.0, layer, "lantern_glass")
    if fx and lit:
        geo.set_fx(glass, fx)
    objects.append(glass)
    objects.append(geo.lathe([(0.0, 0.0), (0.14 * s, 0.0), (0.15 * s, 0.03 * s), (0.15 * s, 0.11 * s), (0.10 * s, 0.14 * s), (0.0, 0.14 * s)],
                             (x, y, glass_bottom - 0.14 * s), material, 14, 0.0, 0.0, 0.0, layer, "lantern_tank"))
    for k in range(4):
        a = math.pi / 4.0 + math.pi * k / 2.0
        dx, dy = math.cos(a) * 0.135 * s, math.sin(a) * 0.135 * s
        objects.append(geo.pipe([(x + dx, y + dy, glass_bottom), (x + dx * 1.08, y + dy * 1.08, (glass_bottom + glass_top) / 2.0),
                                 (x + dx * 0.9, y + dy * 0.9, glass_top)], 0.012 * s, material, layer, "guard"))
    return objects


def ring_xy(centre, radius, material=None, layer="main", tube=0.012):
    """A small ring lying across the view (a hanging eye)."""
    points = []
    for i in range(10):
        a = 2.0 * math.pi * i / 8.0
        points.append((centre[0] + G.SCREEN_RIGHT[0] * radius * math.cos(a), centre[1] + G.SCREEN_RIGHT[1] * radius * math.cos(a),
                       centre[2] + radius * math.sin(a)))
    return geo.pipe(points, tube, material, layer, "eye")


def bulbs_on(points, kinds, radius=0.05, layer="main", strength=3.0, drop=0.06):
    """Bulbs hanging under the given world points. kinds: one entry per bulb, cycled:
        (r, g, b)        a lit bulb of that colour (baked glow: dims at night unless the piece is a lamp)
        "fire" / "slime" / "monitors" / "alarm"   lit with that animated palette range: glows at night by itself
        None             a dead bulb
    """
    colours = {"fire": (1.0, 0.25, 0.02), "slime": (0.1, 0.9, 0.1), "monitors": (0.3, 0.6, 1.0), "alarm": (1.0, 0.0, 0.0),
               "embers": (0.7, 0.0, 0.0)}
    objects = []
    for index, point in enumerate(points):
        kind = kinds[index % len(kinds)]
        where = (point[0], point[1], point[2] - drop)
        if kind is None:
            objects.append(sphere(radius * 0.9, where, dead_tube(), layer, "bulb_off"))
        elif isinstance(kind, str):
            objects.append(geo.bulb(where, colours[kind], radius, 2.0, layer, fx=kind))
        else:
            objects.append(geo.bulb(where, kind, radius, strength, layer))
    return objects


def flames(at, radius=0.2, height=0.5, count=7, seed=0, layer="main", fx="fire"):
    """Tongues of fire: a clump of thin leaning cones, tallest in the middle, painted with the animated
    fire colours so they flicker and stay bright at night without a script."""
    r = geo.rng(seed)
    objects = []
    for i in range(count):
        a = 2.0 * math.pi * i / count + r.uniform(-0.4, 0.4)
        dist = 0.0 if i == 0 else r.uniform(0.25, 0.85) * radius
        h = height * (1.0 if i == 0 else r.uniform(0.35, 0.8) * (1.0 - 0.45 * dist / radius))
        w = radius * (0.34 if i == 0 else r.uniform(0.2, 0.32))
        where = (at[0] + math.cos(a) * dist, at[1] + math.sin(a) * dist, at[2])
        colour = (1.0, 0.75, 0.1) if i == 0 else r.choice([(1.0, 0.45, 0.0), (1.0, 0.2, 0.0), (1.0, 0.08, 0.0), (1.0, 0.6, 0.05)])
        cone = geo.lathe([(w, 0.0), (w * 0.9, h * 0.22), (w * 0.45, h * 0.6), (w * 0.15, h * 0.85), (0.0, h)], where,
                         mat.emitter(colour, 3.0), 8, r.uniform(0, 360), r.uniform(-14, 14), r.uniform(-14, 14), layer, "flame")
        objects.append(cone)
    if fx:
        geo.set_fx(objects, fx)
    return objects


# ----------------------------------------------------------------- soft things
def cloth(frame, u, z_top, width, height, material=None, folds=2.5, depth=0.05, seed=0, layer="main", d=0.0,
          taper=0.0, sway=0.0, rows=8, columns=12, name="cloth"):
    """A piece of cloth hanging from its top edge at (u, z_top): soft vertical folds that deepen downwards.
    taper: share by which the bottom is narrower (trouser legs, a pennant); sway: metres the hem blows forward."""
    r = geo.rng(seed)
    phase = r.uniform(0.0, 6.28)
    bm = bmesh.new()
    grid = []
    for j in range(rows + 1):
        t = j / rows
        row = []
        for i in range(columns + 1):
            s = i / columns
            x = (s - 0.5) * width * (1.0 - taper * t)
            y = -(depth * t * math.sin(phase + folds * 2.0 * math.pi * s) + sway * t * t)
            z = -height * t * (1.0 + 0.03 * math.sin(phase * 2.0 + 5.0 * s))
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(rows):
        for i in range(columns):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    return geo.set_block(geo._finish(bm, name, material or fabric(), frame.at(u, d, z_top), frame.rot, layer, smooth=True,
                                     solidify=0.014), 0)


def sag_sheet(corners, material=None, sag=0.18, layer="main", rows=8, columns=8, name="tarp", thickness=0.016,
              ripple=0.02, seed=0):
    """A tarpaulin slung between four world points (in order round the sheet): it bellies down in the
    middle by `sag` metres and ripples a little."""
    r = geo.rng(seed)
    a, b, c, d = (Vector(p) for p in corners)
    phase = r.uniform(0.0, 6.28)
    bm = bmesh.new()
    grid = []
    for j in range(rows + 1):
        t = j / rows
        row = []
        for i in range(columns + 1):
            s = i / columns
            p = a.lerp(b, s).lerp(d.lerp(c, s), t)
            p.z -= sag * 16.0 * s * (1 - s) * t * (1 - t) + ripple * math.sin(phase + 9.0 * s + 5.0 * t)
            row.append(bm.verts.new(tuple(p)))
        grid.append(row)
    for j in range(rows):
        for i in range(columns):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return geo.set_block(geo._finish(bm, name, material or mat.tarp(), (0.0, 0.0, 0.0), 0.0, layer, smooth=True,
                                     solidify=thickness), 0)


def cone(radius, height, at, material=None, layer="main", segments=14, tilt=0.0, roll=0.0, rot=0.0, name="cone", top=0.0):
    return geo.lathe([(radius, 0.0), (top, height)] if top else [(radius, 0.0), (0.0, height)], at, material, segments,
                     rot, tilt, roll, layer, name)


def rope_tie(p0, p1, radius=0.014, material=None, layer="main"):
    """A taut guy rope / tie wire between two world points."""
    return geo.pipe([tuple(p0), tuple(p1)], radius, material or mat.flat((0.16, 0.12, 0.07), roughness=0.9), layer, "rope")
