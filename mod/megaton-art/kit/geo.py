# SPDX-License-Identifier: MIT
"""Geometry building blocks (Blender 5.x). Everything is made from numbers, nothing is loaded.

WORLD   metres. +X = the game's hex-row axis (runs to the screen lower-left), +Y = the hex
        column axis (screen lower-right), +Z up. (0, 0, 0) is the origin hex centre.
        G.hex_xy(dhx, dhy) gives the ground position of any hex (kit.G is pipeline.proj).

ROT     every helper takes `rot` = degrees about Z of the object's local +X axis. Objects are
        modelled running along local +X with their FRONT on local -Y, so the front faces the
        viewer whenever local +X points towards the screen right:
            U       = 180   along a hex row     (front faces +Y)   like stock "jas" walls
            V       =  90   along a hex column  (front faces +X)   like stock "jbs" walls
            SCREEN  = 150   flat towards the camera (billboards, signs meant to be read)
        span(a, b) returns (at, rot, length) for a run from ground point a to b; go from
        screen-left to screen-right and the front faces the viewer.

BLOCK   what a piece blocks is worked out from its geometry: a hex is blocked when its centre is
        within an object's block radius of that object's surface below 1.5 m. Props use
        BLOCK_PROP (0.22 m: only the hex they stand on), wall runs (slab, wall_u / wall_v,
        boards, corrugated_wall, chainlink_panel) use BLOCK_WALL (0.5 m, like stock walls).
        Override with set_block(objects, radius); stand posts ON hex centres (G.hex_xy).

LAYER   every helper takes `layer` ("main" by default). Objects in another layer are rendered
        into their own sprite set: "halo" is the light pool layer (see halo()).

Every helper returns the Blender object (or a list of them), already linked to the scene,
with smooth shading and bevelled edges where that helps the sprite read.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

from pipeline import proj as G
from pipeline.bscene import LAYER_PROP
from . import mat

U = 180.0
V = 90.0
SCREEN = 150.0

BLOCK_PROP = 0.22       # a prop blocks the hexes whose centre is this close to it (its own hex, not the neighbours)
BLOCK_WALL = 0.50       # a wall also blocks the half-offset hexes 0.4 m in front of and behind its line (stock convention)
BLOCK_PROPERTY = "mg_block"
FX_PROPERTY = "mg_fx"

FONTS = {
    # name -> file; all ship with macOS. Pick by look, never by file path, in piece scripts.
    "impact": "/System/Library/Fonts/Supplemental/Impact.ttf",              # heavy poster capitals
    "black": "/System/Library/Fonts/Supplemental/Arial Black.ttf",          # wide, friendly, bold
    "din": "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",     # stencil / military marking
    "rockwell": "/System/Library/Fonts/Supplemental/Rockwell.ttc",          # slab serif: saloon, bank
    "typewriter": "/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc",
    "signpainter": "/System/Library/Fonts/Supplemental/SignPainter.ttc",    # brush script
    "brush": "/System/Library/Fonts/Supplemental/Brush Script.ttf",
    "chalk": "/System/Library/Fonts/Supplemental/Chalkduster.ttf",          # rough hand lettering
    "marker": "/System/Library/Fonts/MarkerFelt.ttc",
    "phosphate": "/System/Library/Fonts/Supplemental/Phosphate.ttc",        # inline display caps
    "copperplate": "/System/Library/Fonts/Supplemental/Copperplate.ttc",
    "futura": "/System/Library/Fonts/Supplemental/Futura.ttc",
}


# ------------------------------------------------------------------ plumbing
def _link(obj, layer="main"):
    obj[LAYER_PROP] = layer
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _place(obj, at=(0, 0, 0), rot=0.0, tilt=0.0, roll=0.0):
    """Position; rot about Z, then tilt about the local X axis (positive = the top comes forward,
    towards the front / the viewer; negative = leans back), then roll about local Y (sideways)."""
    obj.location = Vector(at)
    obj.rotation_euler = (Matrix.Rotation(math.radians(rot), 4, "Z")
                          @ Matrix.Rotation(math.radians(tilt), 4, "X")
                          @ Matrix.Rotation(math.radians(roll), 4, "Y")).to_euler()
    return obj


def _finish(bm, name, material, at, rot, layer, tilt=0.0, roll=0.0, smooth=True, bevel=0.0, solidify=0.0):
    mesh = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        for polygon in mesh.polygons:
            polygon.use_smooth = True
    if material is not None:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    if solidify:
        modifier = obj.modifiers.new("solidify", "SOLIDIFY")
        modifier.thickness = solidify
        modifier.offset = 0.0
    if bevel:
        modifier = obj.modifiers.new("bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        modifier.limit_method = "ANGLE"
        modifier.angle_limit = math.radians(40)
        modifier.harden_normals = True
    _place(obj, at, rot, tilt, roll)
    return _link(obj, layer)


def set_block(objects, radius):
    """Say how far a thing keeps people away: hexes whose centre is within `radius` metres of it
    (below head height) are blocked. 0 = never blocks (bunting, a low kerb, a puddle).
    Helpers set sensible values themselves: BLOCK_WALL for wall runs, BLOCK_PROP otherwise."""
    for obj in objects if isinstance(objects, (list, tuple)) else [objects]:
        obj[BLOCK_PROPERTY] = float(radius)
    return objects


def set_fx(objects, name):
    """Paint objects with one of the game's ANIMATED palette ranges instead of fixed colours.
    Those colours cycle by themselves and are the only ones the engine does not darken at night,
    so this is how a tube glows in the dark without a script:
        "fire"      red / orange flicker (200 ms)      neon, embers, a brazier
        "embers"    dark red pulse                     dying coals, a standby light
        "alarm"     ONE colour ramping black <-> red   a blinking warning lamp
        "slime"     four close greens (reads as a steady green glow)   goo, radium paint
        "monitors"  grey-blue to bright blue flicker   a screen, an arc
        "shore"     dull browns (of no use as light)
    Every pixel of the tagged objects takes the nearest colour OF THAT RANGE, whatever its
    render colour was, so tag only the glowing surface itself (the tube, not its bracket)."""
    for obj in objects if isinstance(objects, (list, tuple)) else [objects]:
        obj[FX_PROPERTY] = name
    return objects


def span(a, b):
    """(at, rot, length) of a run from ground point a to ground point b (2- or 3-tuples)."""
    ax, ay = a[0], a[1]
    bx, by = b[0], b[1]
    az = a[2] if len(a) > 2 else 0.0
    length = math.hypot(bx - ax, by - ay)
    return (ax, ay, az), math.degrees(math.atan2(by - ay, bx - ax)), length


def rng(seed):
    """Deterministic random source for scatter / jitter: always seed it explicitly."""
    return random.Random(seed)


# ------------------------------------------------------------------- solids
def box(size, at=(0, 0, 0), rot=0.0, material=None, bevel=0.012, layer="main", name="box",
        tilt=0.0, roll=0.0, centred=False):
    """Box of size (x, y, z). Origin: centre of the bottom face (or the centre with centred=True)."""
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    if not centred:
        bmesh.ops.translate(bm, vec=(0, 0, sz / 2.0), verts=bm.verts)
    return _finish(bm, name, material, at, rot, layer, tilt, roll, smooth=bool(bevel), bevel=bevel)


def slab(length, height, thickness, at=(0, 0, 0), rot=U, material=None, bevel=0.01, layer="main",
         name="slab", front=0.0, tilt=0.0):
    """A wall-like box running along local +X from the origin: x 0..length, z 0..height,
    its FRONT face at local y = -front, its back at -front + thickness."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(length, thickness, height), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(length / 2.0, -front + thickness / 2.0, height / 2.0), verts=bm.verts)
    return set_block(_finish(bm, name, material, at, rot, layer, tilt, smooth=bool(bevel), bevel=bevel), BLOCK_WALL)


def lathe(profile, at=(0, 0, 0), material=None, segments=24, rot=0.0, tilt=0.0, roll=0.0,
          layer="main", name="lathe", bevel=0.0):
    """Solid of revolution about local Z. profile: [(radius, z), ...] from bottom to top;
    a radius of 0 closes the end."""
    bm = bmesh.new()
    rings = []
    for radius, z in profile:
        if radius <= 1e-6:
            rings.append([bm.verts.new((0.0, 0.0, z))])
        else:
            rings.append([bm.verts.new((radius * math.cos(2 * math.pi * i / segments),
                                        radius * math.sin(2 * math.pi * i / segments), z))
                          for i in range(segments)])
    for lower, upper in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if len(lower) == 1 and len(upper) == 1:
                continue
            if len(lower) == 1:
                bm.faces.new((lower[0], upper[j], upper[i]))
            elif len(upper) == 1:
                bm.faces.new((lower[i], lower[j], upper[0]))
            else:
                bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
    for ring, flip in ((rings[0], True), (rings[-1], False)):
        if len(ring) > 1:
            bm.faces.new(list(reversed(ring)) if flip else ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = _finish(bm, name, material, at, rot, layer, tilt, roll, smooth=True, bevel=bevel)
    modifier = obj.modifiers.new("edges", "EDGE_SPLIT")
    modifier.split_angle = math.radians(50)
    return obj


def cylinder(radius, height, at=(0, 0, 0), material=None, segments=20, layer="main", name="cylinder",
             tilt=0.0, roll=0.0, rot=0.0):
    return lathe([(radius, 0.0), (radius, height)], at, material, segments, rot, tilt, roll, layer, name)


def pipe(points, radius=0.04, material=None, layer="main", name="pipe", resolution=6):
    """Round tube through world points (straight segments; add points for bends)."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = max(1, resolution // 3)
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (co[0], co[1], co[2], 1.0)
    if material is not None:
        curve.materials.append(material)
    return _link(bpy.data.objects.new(name, curve), layer)


def ibeam(length, at=(0, 0, 0), rot=U, material=None, height=0.22, width=0.14, web=0.02, flange=0.022,
          vertical=False, tilt=0.0, roll=0.0, layer="main", name="ibeam"):
    """Steel I-beam along local +X (or standing up with vertical=True), origin at one end,
    bottom centre of the section."""
    material = material or mat.steel()
    h, w = height, width
    section = [(-w / 2, 0), (w / 2, 0), (w / 2, flange), (web / 2, flange), (web / 2, h - flange), (w / 2, h - flange),
               (w / 2, h), (-w / 2, h), (-w / 2, h - flange), (-web / 2, h - flange), (-web / 2, flange), (-w / 2, flange)]
    bm = bmesh.new()
    start = [bm.verts.new((0.0, y, z)) for y, z in section]
    end = [bm.verts.new((length, y, z)) for y, z in section]
    n = len(section)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((start[i], start[j], end[j], end[i]))
    bm.faces.new(list(reversed(start)))
    bm.faces.new(end)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(bm, name, material, at, rot, layer, tilt, roll - 90.0 if vertical else roll, smooth=False)


# ------------------------------------------------------------ sheets & walls
def corrugated_panel(width, height, at=(0, 0, 0), rot=U, material=None, wavelength=0.10, depth=0.03,
                     tilt=0.0, roll=0.0, layer="main", name="corrugated", thickness=0.012, horizontal=False):
    """One sheet of corrugated iron standing in the local XZ plane: x 0..width, z 0..height, ridges
    running up (or along X with horizontal=True). tilt > 0 brings the top edge forward: 90 lays
    the sheet flat towards the viewer, 90 + s is a roof sheet falling s degrees to the front
    (hinged at `at`, ridges running down the slope); negative tilt leans it back.
    wavelength 0.10 m is 3-4 px: finer ridges turn to moire."""
    material = material or mat.corrugated()
    run, rise = (height, width) if horizontal else (width, height)
    columns = max(4, int(round(run / wavelength * 8)))
    bm = bmesh.new()
    lower, upper = [], []
    for i in range(columns + 1):
        s = run * i / columns
        y = depth / 2.0 * math.sin(2 * math.pi * s / wavelength)
        if horizontal:
            lower.append(bm.verts.new((0.0, y, s)))
            upper.append(bm.verts.new((rise, y, s)))
        else:
            lower.append(bm.verts.new((s, y, 0.0)))
            upper.append(bm.verts.new((s, y, rise)))
    for i in range(columns):
        bm.faces.new((lower[i], lower[i + 1], upper[i + 1], upper[i]))
    return _finish(bm, name, material, at, rot, layer, tilt, roll, smooth=True, solidify=thickness)


def corrugated_wall(a, b, height=G.STOCK_WALL_H, material=None, sheet=0.9, ragged=0.18, seed=1,
                    lean=3.0, layer="main", rust=0.6, paints=()):
    """A scrap wall of overlapping corrugated sheets from ground point a to b.
    ragged: metres by which sheet tops differ; lean: degrees of random lean per sheet.
    paints: colours to draw sheets from besides bare zinc (each sheet picks one)."""
    r = rng(seed)
    at, rot, length = span(a, b)
    direction = Vector((math.cos(math.radians(rot)), math.sin(math.radians(rot)), 0.0))
    objects = []
    x = 0.0
    index = 0
    while x < length - 0.05:
        w = min(sheet * r.uniform(0.85, 1.1), length - x + 0.04)
        h = height - r.uniform(0.0, ragged)
        paint = r.choice([None, None] + list(paints)) if paints else None
        material_i = material or mat.corrugated(paint=paint, rust=min(1.0, max(0.0, rust + r.uniform(-0.2, 0.2))),
                                                seed=seed * 10 + index)
        position = Vector(at) + direction * x + Vector((0.0, 0.0, r.uniform(0.0, 0.03)))
        # alternate sheets sit a little in front / behind so the overlap casts a line
        normal = Vector((direction.y, -direction.x, 0.0))
        position += normal * (0.012 if index % 2 else -0.012)
        objects.append(corrugated_panel(w, h, tuple(position), rot, material_i, tilt=r.uniform(-lean, lean) * 0.4,
                                        roll=r.uniform(-lean, lean) * 0.35, layer=layer, name=f"sheet{index}"))
        x += w - 0.05
        index += 1
    return set_block(objects, BLOCK_WALL)


def boards(a, b, height=2.0, material=None, board=0.16, gap=0.012, thickness=0.03, ragged=0.1, seed=1,
           layer="main", z=0.0, lean=1.5):
    """A run of upright planks from a to b, each its own box: uneven tops, gaps, slight leans."""
    r = rng(seed)
    at, rot, length = span(a, b)
    material = material or mat.planks()
    direction = Vector((math.cos(math.radians(rot)), math.sin(math.radians(rot)), 0.0))
    count = max(1, int(round(length / (board + gap))))
    step = length / count
    objects = []
    for i in range(count):
        h = height - r.uniform(0.0, ragged)
        position = Vector(at) + direction * (step * (i + 0.5)) + Vector((0, 0, z))
        objects.append(box((step - gap, thickness, h), tuple(position), rot, material, bevel=0.006, layer=layer,
                           name=f"board{i}", roll=r.uniform(-lean, lean), tilt=r.uniform(-lean, lean) * 0.5))
    return set_block(objects, BLOCK_WALL)


def wall_u(hx0, hx1, dhy=0, height=G.STOCK_WALL_H, material=None, thickness=G.STOCK_WALL_T, layer="main"):
    """Plain wall slab along a hex row, on the line stock "jas" walls stand on: from hex hx0 to
    hx1 (inclusive, even hx: the row's straight line) of row dhy."""
    lo, hi = sorted((hx0, hx1))
    x0, y0 = G.hex_xy(lo, dhy)
    x1, _ = G.hex_xy(hi, dhy)
    half = G.SQ_U_M / 4.0                      # half a hex step along the row
    return slab((x1 - x0) + 2 * half, height, thickness, (x1 + half, y0, 0.0), U, material,
                front=G.STOCK_WALL_FRONT_U, layer=layer, name="wall_u")


def wall_v(hy0, hy1, dhx=0, height=G.STOCK_WALL_H, material=None, thickness=G.STOCK_WALL_T, layer="main"):
    """Plain wall slab along a hex column, on the line stock "jbs" walls stand on."""
    lo, hi = sorted((hy0, hy1))
    x0, y0 = G.hex_xy(dhx, lo)
    _, y1 = G.hex_xy(dhx, hi)
    half = G.SQ_V_M / 4.0
    return slab((y1 - y0) + 2 * half, height, thickness, (x0, y0 - half, 0.0), V, material,
                front=G.STOCK_WALL_FRONT_V, layer=layer, name="wall_v")


def chainlink_panel(a, b, height=2.2, post=0.035, layer="main", top_rail=True, material=None):
    """Chain-link fence from a to b: mesh quad, end posts, top rail."""
    at, rot, length = span(a, b)
    bm = bmesh.new()
    quad = [bm.verts.new(co) for co in ((0, 0, 0.05), (length, 0, 0.05), (length, 0, height), (0, 0, height))]
    bm.faces.new(quad)
    objects = [_finish(bm, "chainlink", material or mat.chainlink(), at, rot, layer, smooth=False)]
    steel = mat.steel(rust=0.7)
    ax, ay, az = at
    bx, by = b[0], b[1]
    objects.append(pipe([(ax, ay, az), (ax, ay, az + height + 0.05)], post, steel, layer, "post"))
    objects.append(pipe([(bx, by, az), (bx, by, az + height + 0.05)], post, steel, layer, "post"))
    if top_rail:
        objects.append(pipe([(ax, ay, az + height), (bx, by, az + height)], post * 0.7, steel, layer, "rail"))
    return set_block(objects, BLOCK_WALL)


# -------------------------------------------------------------------- props
def crate(size=(0.9, 0.9, 0.8), at=(0, 0, 0), rot=U, material=None, frame=0.07, layer="main", seed=0):
    """Wooden crate: a planked box with a raised frame on every face."""
    sx, sy, sz = size
    wood = material or mat.planks(axis="Z", width=0.15, seed=seed)
    dark = mat.planks(colour=(0.16, 0.115, 0.075), axis="X", width=0.3, seed=seed + 3)
    objects = [box((sx - 0.03, sy - 0.03, sz - 0.03), (at[0], at[1], at[2] + 0.015), rot, wood, bevel=0.004,
                   layer=layer, name="crate")]
    rotation = Matrix.Rotation(math.radians(rot), 4, "Z")
    origin = Vector(at)
    t = 0.025

    def bar(bx, by, bz, cx, cy, cz):
        position = origin + rotation @ Vector((cx, cy, cz))
        objects.append(box((bx, by, bz), tuple(position), rot, dark, bevel=0.004, layer=layer, name="crate_bar"))

    for side in (-1, 1):
        for other in (-1, 1):
            bar(frame, frame, sz, side * (sx - frame) / 2, other * (sy - frame) / 2, 0.0)          # corner posts
        for z in (0.0, sz - frame):
            bar(sx, t + 0.01, frame, 0.0, side * (sy / 2), z)                                     # front / back rails
            bar(t + 0.01, sy, frame, side * (sx / 2), 0.0, z)                                     # side rails
    for side in (-1, 1):                                                                          # top frame
        bar(sx, frame, t, 0.0, side * (sy - frame) / 2, sz - t / 2)
        bar(frame, sy, t, side * (sx - frame) / 2, 0.0, sz - t / 2)
    return objects


def barrel(at=(0, 0, 0), radius=0.29, height=0.88, material=None, layer="main", tilt=0.0, rot=0.0, seed=0):
    """200-litre drum with two rolling hoops and a recessed lid."""
    material = material or mat.painted_metal((0.13, 0.06, 0.022), flaking=0.7, seed=seed)
    r, h = radius, height
    rib = 0.014
    profile = [(r * 0.96, 0.0), (r, 0.02)]
    for z in (h * 0.33, h * 0.66):
        profile += [(r, z - 0.03), (r + rib, z - 0.012), (r + rib, z + 0.012), (r, z + 0.03)]
    profile += [(r, h - 0.02), (r * 0.985, h), (r * 0.93, h), (r * 0.93, h - 0.025), (0.0, h - 0.025)]
    return lathe(profile, at, material, 24, rot, tilt, 0.0, layer, "barrel")


def tire(at=(0, 0, 0), radius=0.36, width=0.22, lying=True, rot=0.0, lean=0.0, layer="main", seed=0, material=None):
    """Car tyre. lying=True: flat on the ground (origin = centre of the underside);
    lying=False: standing on its tread, facing along rot."""
    material = material or mat.rubber(seed=seed)
    r, w = radius, width
    inner = r * 0.56
    profile = [(inner, w * 0.18), (inner * 1.12, w * 0.02), (r * 0.82, 0.0), (r * 0.97, w * 0.06), (r, w * 0.22),
               (r, w * 0.78), (r * 0.97, w * 0.94), (r * 0.82, w), (inner * 1.12, w * 0.98), (inner, w * 0.82),
               (inner, w * 0.18)]
    if lying:
        return lathe(profile, at, material, 28, rot, lean, 0.0, layer, "tire")
    # standing: the lathe axis turned horizontal, raised by the radius
    obj = lathe([(pr, pz - w / 2.0) for pr, pz in profile], (at[0], at[1], at[2] + r), material, 28, rot,
                90.0 + lean, 0.0, layer, "tire")
    return obj


def tire_stack(count, at=(0, 0, 0), seed=1, radius=0.36, width=0.22, layer="main"):
    r = rng(seed)
    objects = []
    z = at[2]
    for i in range(count):
        offset = (r.uniform(-0.04, 0.04), r.uniform(-0.04, 0.04))
        objects.append(tire((at[0] + offset[0], at[1] + offset[1], z), radius * r.uniform(0.94, 1.03), width,
                            lying=True, rot=r.uniform(0, 360), lean=r.uniform(-3, 3), layer=layer, seed=seed + i))
        z += width * 0.97
    return objects


# ------------------------------------------------------------ cables & lights
def catenary(p0, p1, sag=0.3, count=16):
    """Points of a hanging cable from p0 to p1 that dips `sag` metres at its middle."""
    p0, p1 = Vector(p0), Vector(p1)
    points = []
    for i in range(count + 1):
        t = i / count
        point = p0.lerp(p1, t)
        point.z -= sag * 4.0 * t * (1.0 - t)
        points.append(tuple(point))
    return points


def cable(p0, p1, sag=0.3, radius=0.012, material=None, layer="main", count=16):
    """A hanging cable. 0.012 m is under a pixel and renders as a broken hairline;
    use 0.02 for power lines, 0.03 for rope."""
    return pipe(catenary(p0, p1, sag, count), radius, material or mat.flat((0.03, 0.03, 0.03), roughness=0.6),
                layer, "cable")


def bulb(at, colour=(1.0, 0.75, 0.4), radius=0.05, strength=2.5, layer="main", fx=None):
    """A bare light bulb (2-4 px across: radius 0.05 is deliberately oversized so it survives).
    fx: animated palette range to paint it with (see set_fx), e.g. "alarm" for a blinking red lamp."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=radius)
    obj = _finish(bm, "bulb", mat.emitter(colour, strength), at, 0.0, layer, smooth=True)
    return set_fx(obj, fx) if fx else obj


def bulb_string(p0, p1, count=8, sag=0.35, colours=((1.0, 0.75, 0.4),), radius=0.05, strength=2.5,
                layer="main", lit=None):
    """A string of bulbs: cable plus `count` bulbs hanging just under it.
    lit: optional list of booleans (one per bulb): unlit bulbs are dark glass - use it per
    animation frame for a flicker."""
    objects = [cable(p0, p1, sag, 0.014, layer=layer, count=max(16, count * 2))]
    points = catenary(p0, p1, sag, count + 1)[1:-1]
    for i, point in enumerate(points):
        colour = colours[i % len(colours)]
        on = True if lit is None else bool(lit[i % len(lit)])
        position = (point[0], point[1], point[2] - radius * 1.1)
        if on:
            objects.append(bulb(position, colour, radius, strength, layer))
        else:
            bm = bmesh.new()
            bmesh.ops.create_icosphere(bm, subdivisions=2, radius=radius)
            objects.append(_finish(bm, "bulb_off", mat.flat(tuple(c * 0.12 for c in colour), roughness=0.3),
                                   position, 0.0, layer, smooth=True))
    return objects


def neon_tube(points, colour=(1.0, 0.25, 0.12), radius=0.025, strength=1.2, layer="main", fx=None):
    """A glowing tube through world points. fx="fire" paints it with the animated fire colours:
    it then flickers and stays lit at night (see set_fx)."""
    obj = pipe(points, radius, mat.emitter(colour, strength), layer, "neon")
    return set_fx(obj, fx) if fx else obj


def halo(at=(0, 0, 0), radius=1.6, strength=1.0, layer="halo"):
    """A pool of light on the ground, rendered into its own see-through sprite (the engine tints
    whatever is under it yellow: the only coloured light the game has). strength 1 reaches the
    strongest tint step the piece allows at the centre (convert option halo_levels, default 3
    of 7 = 43 % yellow); 0.5 is a gentle lamp. The tint is there by day too: keep it gentle,
    or keep halos for places that are only seen at night."""
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=radius, segments=40)
    graph = mat.Graph("halo")
    position = graph.coords()
    x, y, _ = graph.separate(position)
    distance = graph.math("SQRT", graph.add(graph.mul(x, x), graph.mul(y, y)))
    falloff = graph.power(graph.smooth(distance, radius, 0.0), 1.6)
    from pipeline.bscene import EXPOSURE
    graph.emission((1.0, 1.0, 1.0), graph.mul(falloff, strength * 2.0 ** -EXPOSURE))
    return _finish(bm, "halo", graph.material, (at[0], at[1], 0.004), 0.0, layer, smooth=False)


# ------------------------------------------------------------------ lettering
def lettering(text, at=(0, 0, 0), rot=U, size=0.5, depth=0.04, bevel=0.006, font="impact", material=None,
              align="CENTER", layer="main", tilt=0.0, spacing=1.0, outline=0.0, name="lettering"):
    """Extruded letters standing upright, reading along local +X, facing local -Y.
    size: cap height in metres (0.5 m = 18 px: the smallest that stays legible is about 0.3).
    at: position of the baseline (centre of the run with align="CENTER", else its left end).
    outline > 0: glyph outlines only, as tubes of that radius (neon lettering)."""
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = text
    path = FONTS.get(font, font)
    try:
        curve.font = bpy.data.fonts.load(path, check_existing=True)
    except RuntimeError:
        print(f"[kit.geo] font {font!r} not found, using Blender's built-in font")
    curve.size = size / 0.72                 # Blender's size is the em box; caps are about 0.72 of it
    curve.align_x = align
    curve.space_character = spacing
    if outline:
        curve.fill_mode = "NONE"
        curve.bevel_depth = outline
        curve.bevel_resolution = 2
        curve.extrude = 0.0
    else:
        curve.extrude = depth / 2.0
        curve.bevel_depth = bevel
        curve.bevel_resolution = 1
    curve.materials.append(material or mat.sign_paint())
    obj = bpy.data.objects.new(name, curve)
    obj.location = Vector(at)
    obj.rotation_euler = (Matrix.Rotation(math.radians(rot), 4, "Z")
                          @ Matrix.Rotation(math.radians(90.0 - tilt), 4, "X")).to_euler()
    return _link(obj, layer)


def sign(text, at=(0, 0, 2.0), rot=U, size=0.45, board=(0.34, 0.07, 0.05), ink=(0.78, 0.72, 0.55),
         font="impact", margin=0.14, thickness=0.05, layer="main", seed=0, tilt=0.0, width=None):
    """A hand-painted sign board with raised lettering, centred on `at` (its bottom edge centre).
    width: board width in metres; by default fitted to the text."""
    text_obj = lettering(text, (0, 0, 0), rot, size, depth=0.03, font=font, layer=layer,
                         material=mat.sign_paint(ink, seed=seed), tilt=tilt)
    bpy.context.view_layer.update()
    w = (text_obj.dimensions.x if width is None else width - 2 * margin) + 2 * margin
    h = size + 2 * margin
    rotation = Matrix.Rotation(math.radians(rot), 4, "Z") @ Matrix.Rotation(math.radians(-tilt), 4, "X")
    origin = Vector(at)
    text_obj.location = origin + rotation @ Vector((0.0, -thickness / 2.0 - 0.012, margin))
    plate = box((w, thickness, h), tuple(origin), rot, mat.sign_board(board, seed=seed), bevel=0.008,
                layer=layer, name="sign_board", tilt=-tilt)
    return [plate, text_obj]
