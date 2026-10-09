# SPDX-License-Identifier: MIT
"""Extra kit helpers of the crater / bomb pieces (pieces/bomb/*.py). Blender side only.

    from kit import bomb_extra as bx

Everything here follows the kit's rules (metres, object-space patterns, seeded noise only, no
files loaded). Shared files of the kit are not touched; anything in here may be used by any
piece script.

FRAMES      frame(origin, x, y, z) / turned(rot, at) / move(objects, matrix): build a thing in its
            own handy axes, then put it into the world with one matrix. skin_frame() of a Lathe gives the
            matrix of a decal lying on a body of revolution (text, plates, painted marks).
GROUND      the beauty pass has no ground, so anything below z = 0 would be drawn "under" the
            floor: clip_ground() cuts meshes off at the floor.
SHAPES      Lathe (profile with dents, still a kit lathe), tube(), heightfield() for mounds and
            banks, sandbag() / sandbag_row(), plank(), beam(), cloth(), candle(), ellipse_points(),
            atom_emblem() (the Children of Atom's mark)
MATERIALS   bomb_paint, mud, burlap, cloth_mat, wax, water (the pool: tag it with
            geo.set_fx(obj, "slime")), bone / paper via mat.flat
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

from pipeline import proj as G
from . import geo, mat
from .nodes import Graph


# ---------------------------------------------------------------------------- frames
def frame(origin, x=None, y=None, z=None):
    """4x4 matrix whose columns are the given axes (missing one = cross product of the others)."""
    if x is None:
        x = Vector(y).cross(Vector(z))
    if y is None:
        y = Vector(z).cross(Vector(x))
    if z is None:
        z = Vector(x).cross(Vector(y))
    x, y, z = Vector(x).normalized(), Vector(y).normalized(), Vector(z).normalized()
    m = Matrix.Identity(4)
    for row in range(3):
        m[row][0], m[row][1], m[row][2], m[row][3] = x[row], y[row], z[row], origin[row]
    return m


def move(objects, matrix):
    """Re-place objects that were built in a local frame: world = matrix @ what they had."""
    objects = objects if isinstance(objects, (list, tuple)) else [objects]
    for obj in objects:
        obj.matrix_world = matrix @ obj.matrix_basis
    return objects


def flat_list(*things):
    out = []
    for thing in things:
        if isinstance(thing, (list, tuple)):
            out.extend(flat_list(*thing))
        elif thing is not None:
            out.append(thing)
    return out


def clip_ground(objects, z=0.0):
    """Cut mesh objects off at the floor (everything below world height z is removed)."""
    bpy.context.view_layer.update()
    for obj in flat_list(objects):
        if obj.type != "MESH":
            continue
        inverse = obj.matrix_world.inverted()
        plane_co = inverse @ Vector((0.0, 0.0, z))
        plane_no = (obj.matrix_world.to_3x3().transposed() @ Vector((0.0, 0.0, 1.0))).normalized()
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=plane_co,
                               plane_no=plane_no, clear_inner=True, clear_outer=False)
        bm.to_mesh(obj.data)
        bm.free()
    return objects


def no_block(objects):
    return geo.set_block(flat_list(objects), 0)


# ---------------------------------------------------------------------------- shapes
class Lathe:
    """A body of revolution about its local Z with a sampled profile radius(d), d = distance
    along the axis. Gives the mesh (with optional dents) and frames for things on its skin."""

    def __init__(self, radius, length, steps=64, segments=48):
        self.radius = radius
        self.length = length
        self.steps = steps
        self.segments = segments

    def slope(self, d, h=0.01):
        return (self.radius(min(self.length, d + h)) - self.radius(max(0.0, d - h))) / (2 * h)

    def point(self, d, phi_deg, lift=0.0):
        phi = math.radians(phi_deg)
        r = self.radius(d)
        n = self.normal(d, phi_deg)
        return Vector((r * math.cos(phi), r * math.sin(phi), d)) + n * lift

    def normal(self, d, phi_deg):
        phi = math.radians(phi_deg)
        return Vector((math.cos(phi), math.sin(phi), -self.slope(d))).normalized()

    def skin_frame(self, d, phi_deg, lift=0.0, turn=0.0):
        """Matrix of a decal at (d, phi): local X runs along the body towards its far end, local Y
        up the skin towards smaller phi, local Z out of the skin. turn: degrees about Z."""
        n = self.normal(d, phi_deg)
        phi = math.radians(phi_deg)
        along = Vector((self.slope(d) * math.cos(phi), self.slope(d) * math.sin(phi), 1.0)).normalized()
        m = frame(self.point(d, phi_deg, lift), x=along, z=n)
        return m @ Matrix.Rotation(math.radians(turn), 4, "Z") if turn else m

    def build(self, material, dents=(), name="body", layer="main", d0=0.0, d1=None):
        """dents: [(d, phi_deg, radius_m, depth_m)] smooth pits pushed into the skin."""
        d1 = self.length if d1 is None else d1
        profile = []
        for i in range(self.steps + 1):
            d = d0 + (d1 - d0) * i / self.steps
            profile.append((self.radius(d), d))
        if profile[0][0] > 1e-4:
            profile.insert(0, (0.0, profile[0][1]))
        if profile[-1][0] > 1e-4:
            profile.append((0.0, profile[-1][1]))
        obj = geo.lathe(profile, (0, 0, 0), material, self.segments, name=name, layer=layer)
        if dents:
            for vertex in obj.data.vertices:
                co = vertex.co
                r = math.hypot(co.x, co.y)
                if r < 1e-5:
                    continue
                push = 0.0
                for d, phi_deg, size, depth in dents:
                    centre = self.point(d, phi_deg)
                    distance = (co - centre).length
                    if distance < size:
                        push += depth * (0.5 + 0.5 * math.cos(math.pi * distance / size))
                if push:
                    scale = max(0.05, (r - push) / r)
                    co.x *= scale
                    co.y *= scale
        return obj


def tube(r_outer, r_inner, z0, z1, material=None, segments=40, name="tube", layer="main", dents=(), seed=0):
    """Open pipe / ring shroud about local Z from z0 to z1 with real wall thickness.
    dents: [(angle_deg, z, radius_m, depth_m)] pushed inwards."""
    bm = bmesh.new()
    loops = []
    for r, z in ((r_outer, z0), (r_outer, z1), (r_inner, z1), (r_inner, z0)):
        ring = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            rr = r
            for a_deg, dz, size, depth in dents:
                centre = Vector((r_outer * math.cos(math.radians(a_deg)), r_outer * math.sin(math.radians(a_deg)), dz))
                distance = (Vector((r_outer * math.cos(angle), r_outer * math.sin(angle), z)) - centre).length
                if distance < size:
                    rr -= depth * (0.5 + 0.5 * math.cos(math.pi * distance / size))
            ring.append(bm.verts.new((rr * math.cos(angle), rr * math.sin(angle), z)))
        loops.append(ring)
    for k in range(4):
        a, b = loops[k], loops[(k + 1) % 4]
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = geo._finish(bm, name, material, (0, 0, 0), 0.0, layer, smooth=True)
    modifier = obj.modifiers.new("edges", "EDGE_SPLIT")
    modifier.split_angle = math.radians(50)
    return obj


def fbm(x, y, seed=0.0, scale=1.0, octaves=3):
    """Deterministic fractal noise, about -1 .. 1."""
    return noise.fractal(Vector((x * scale + seed * 13.7, y * scale - seed * 7.3, seed * 3.1)), 1.0, 2.0, octaves)


def heightfield(x0, x1, y0, y1, height, material=None, step=0.06, at=(0, 0, 0), name="mound", layer="main",
                smooth=True):
    """Ground relief: a grid over x0..x1, y0..y1 (local metres) whose height is height(x, y);
    cells where it returns None (or <= 0) are left out, so the outline can be any blob.
    The sheet has no underside: keep it on the floor."""
    nx = max(2, int(round((x1 - x0) / step)))
    ny = max(2, int(round((y1 - y0) / step)))
    bm = bmesh.new()
    grid = {}
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            y = y0 + (y1 - y0) * j / ny
            h = height(x, y)
            if h is not None and h > 0.0:
                grid[(i, j)] = bm.verts.new((x, y, h))
    for j in range(ny):
        for i in range(nx):
            corners = [grid.get((i, j)), grid.get((i + 1, j)), grid.get((i + 1, j + 1)), grid.get((i, j + 1))]
            if all(c is not None for c in corners):
                bm.faces.new(corners)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for face in bm.faces:
        if face.normal.z < 0:
            face.normal_flip()
    return geo._finish(bm, name, material, at, 0.0, layer, smooth=smooth)


def sandbag(at=(0, 0, 0), rot=0.0, size=(0.62, 0.34, 0.17), material=None, seed=0, layer="main", tilt=0.0, roll=0.0):
    """One filled sandbag lying along local X: a squashed pillow with pinched ends."""
    material = material or burlap(seed=seed % 5)
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=1.0)
    r = geo.rng(seed * 31 + 7)
    for v in bm.verts:
        x, y, z = v.co
        # superellipse pillow: flat top and bottom, ends pinched to a seam
        fx = math.copysign(abs(x) ** 0.7, x)
        pinch = 1.0 - 0.45 * abs(x) ** 3
        fy = math.copysign(abs(y) ** 0.75, y) * pinch
        fz = math.copysign(abs(z) ** 0.6, z) * (1.0 - 0.55 * abs(x) ** 4)
        sag = 0.06 * fbm(x * 2.0, y * 2.0, seed)
        v.co = Vector((fx * sx / 2.0, fy * sy / 2.0, (fz * 0.5 + 0.5 + sag * 0.3) * sz))
    del r
    return geo._finish(bm, "sandbag", material, at, rot, layer, tilt, roll, smooth=True)


def sandbag_row(a, b, material=None, seed=0, z=0.0, size=(0.62, 0.34, 0.17), jitter=0.04, layer="main", skip=()):
    """Sandbags laid end to end from ground point a to b (lengthwise along the run)."""
    at, rot, length = geo.span(a, b)
    count = max(1, int(round(length / (size[0] * 0.93))))
    r = geo.rng(seed)
    direction = Vector((math.cos(math.radians(rot)), math.sin(math.radians(rot)), 0.0))
    side = Vector((-direction.y, direction.x, 0.0))
    objects = []
    for i in range(count):
        if i in skip:
            r.random(), r.random(), r.random()
            continue
        position = Vector((at[0], at[1], z)) + direction * (length * (i + 0.5) / count) + side * r.uniform(-jitter, jitter)
        objects.append(sandbag(tuple(position), rot + r.uniform(-7, 7), (length / count * 1.04, size[1], size[2]),
                               material, seed * 17 + i, layer, roll=r.uniform(-4, 4)))
    return objects


def plank(a, b, width=0.2, thickness=0.04, material=None, layer="main", seed=0, roll=0.0, name="plank"):
    """A board from point a to point b (3-tuples; its wide face up unless rolled)."""
    a, b = Vector(a), Vector(b)
    axis = b - a
    length = axis.length
    x = axis.normalized()
    up = Vector((0, 0, 1))
    if abs(x.dot(up)) > 0.98:
        up = Vector((0, 1, 0))
    y = up.cross(x).normalized()
    z = x.cross(y)
    material = material or mat.planks(axis="X", width=0.5, seed=seed)
    obj = geo.box((length, width, thickness), (0, 0, 0), 0.0, material, bevel=0.006, layer=layer, name=name, centred=True)
    obj.matrix_world = frame((a + b) / 2.0, x=x, y=y, z=z) @ Matrix.Rotation(math.radians(roll), 4, "X")
    return obj


def beam(a, b, size=(0.12, 0.12), material=None, layer="main", name="beam", roll=0.0):
    """A square timber / steel bar from a to b."""
    return plank(a, b, size[0], size[1], material or mat.steel(rust=0.7), layer, roll=roll, name=name)


def ellipse_points(centre, rx, ry, count=24, x=(1, 0, 0), y=(0, 1, 0), closed=True, start=0.0, sweep=360.0):
    """Points of an ellipse in the plane spanned by x and y (for geo.pipe)."""
    c, x, y = Vector(centre), Vector(x).normalized(), Vector(y).normalized()
    n = count + (1 if closed else 0)
    out = []
    for i in range(n):
        angle = math.radians(start + sweep * i / count)
        out.append(tuple(c + x * (rx * math.cos(angle)) + y * (ry * math.sin(angle))))
    return out


def cloth(width, height, at=(0, 0, 0), rot=geo.U, material=None, sag=0.05, flutter=0.04, seed=0, layer="main",
          columns=8, rows=8, taper=0.0, name="cloth", ragged=0.0):
    """A hanging cloth in the local XZ plane: x -width/2..width/2, top edge at z = 0, hanging down
    to -height. sag: how far the top edge dips between its corners; flutter: fold depth (m);
    taper: 0 = rectangle, 1 = pennant (bottom narrows to a point); ragged: torn bottom edge (m)."""
    material = material or cloth_mat(seed=seed)
    bm = bmesh.new()
    grid = []
    for j in range(rows + 1):
        line = []
        v = j / rows
        for i in range(columns + 1):
            u = i / columns
            half = (1.0 - taper * v) * width / 2.0
            x = (u * 2.0 - 1.0) * half
            tear = ragged * (0.5 + 0.5 * fbm(u * 5.0, 0.0, seed + 3)) if j == rows else 0.0
            z = -v * (height - tear) - sag * 4.0 * u * (1.0 - u) * (1.0 - v * 0.6)
            y = flutter * math.sin(u * math.pi * 2.3 + seed) * v + flutter * 0.6 * fbm(u * 3.0, v * 3.0, seed)
            line.append(bm.verts.new((x, y, z)))
        grid.append(line)
    for j in range(rows):
        for i in range(columns):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    return geo._finish(bm, name, material, at, rot, layer, smooth=True, solidify=0.012)


def candle(at=(0, 0, 0), height=0.16, radius=0.028, lit=True, flame=1.0, layer="main", fx="fire", seed=0,
           glow=3.0):
    """A wax candle with a flame big enough to survive at game scale (flame = size factor).
    The flame is painted with the animated fire colours (stays lit at night, flickers)."""
    objects = [geo.lathe([(radius * 1.25, 0.0), (radius * 1.1, 0.015), (radius, 0.03), (radius, height),
                          (radius * 0.6, height + 0.006), (0.0, height + 0.006)], at, wax(seed=seed), 10, name="candle")]
    objects[0][geo.BLOCK_PROPERTY] = 0.0
    if lit:
        h = 0.085 * flame
        flame_obj = geo.lathe([(0.0, 0.0), (0.03 * flame, h * 0.3), (0.022 * flame, h * 0.62), (0.0, h)],
                              (at[0], at[1], at[2] + height + 0.012), mat.emitter((1.0, 0.62, 0.18), glow), 8,
                              name="flame", layer=layer)
        flame_obj[geo.BLOCK_PROPERTY] = 0.0
        if fx:
            geo.set_fx(flame_obj, fx)
        objects.append(flame_obj)
    return objects


# ------------------------------------------------------------------------- materials
def _world_streaks(g, scale=1.0, seed=0.0):
    """Run-off streaks that always run down in the WORLD, however the object is turned."""
    stretched = g.mapping(g.world_position(), scale=(8.0 * scale, 8.0 * scale, 0.5 * scale),
                          location=(seed * 3.3, seed * 1.7, seed * 0.9))
    return g.noise(stretched, scale=1.0, detail=3.0, roughness=0.6)


def bomb_paint(colour=(0.17, 0.18, 0.16), rust=0.5, bands=(), seed=0.0, bleach=0.5):
    """Old ordnance paint on a tilted body of revolution (kit Lathe: local Z = axis).
    bands: [(z0, z1, (r, g, b))] painted rings (hazard band, colour code). Rust gathers under
    the body, in pits and joints and at both ends; stains run down in world space."""
    def build():
        g = Graph("bomb_paint")
        p = mat._seeded(g, seed)
        _, _, oz = g.separate(g.coords())
        _, _, nz = g.separate(g.new("ShaderNodeNewGeometry").outputs["Normal"])
        big = g.noise(p, scale=1.6, detail=5.0, roughness=0.68, distortion=0.5)
        fine = g.noise(p, scale=9.0, detail=3.0, roughness=0.6)
        paint = g.mix(g.remap(big, 0.3, 0.72), tuple(c * 0.78 for c in colour), tuple(min(1.0, c * 1.22) for c in colour))
        for z0, z1, band_colour in bands:
            inside = g.mul(g.greater(oz, z0), g.less(oz, z1))
            worn = g.mix(g.remap(fine, 0.3, 0.7), band_colour, tuple(c * 0.7 for c in band_colour))
            paint = g.mix(inside, paint, worn)
        top = g.smooth(nz, 0.35, 0.95)                                   # sun-bleached, dusty on top
        paint = g.mix(g.mul(top, bleach), paint, (0.215, 0.21, 0.18))
        streak = _world_streaks(g, 1.0, seed)
        side = g.smooth(nz, 0.75, -0.1)                                  # 0 on top .. 1 on the flanks and below
        under = g.smooth(nz, 0.05, -0.6)
        pits = g.smooth(g.ao(0.22), 0.92, 0.5)
        amount = g.add(g.add(g.mul(big, 0.62), g.mul(fine, 0.22)),
                       g.add(g.add(g.mul(g.mul(streak, side), 0.38), g.mul(pits, 0.34)), g.mul(under, 0.25)))
        edge = 1.16 - rust * 0.62
        mask = g.smooth(amount, edge - 0.035, edge + 0.035)
        stain = g.mul(g.smooth(g.mul(streak, side), 0.26, 0.5), 0.7)   # brown run-off that is not yet rust
        paint = g.mix(stain, paint, (0.115, 0.062, 0.030))
        result = g.mix(mask, paint, mat._rust_colour(g, p, 0.9))
        result = mat._ground_dirt(g, result, height=0.45, amount=0.7)
        g.principled(base=result, roughness=g.mix_value(mask, 0.5, 0.95), metallic=g.mix_value(mask, 0.35, 0.0),
                     specular=g.mix_value(mask, 0.35, 0.06), bump=g.bump(g.add(g.mul(mask, 0.6), g.mul(fine, 0.2)), 0.006))
        return g.material
    return mat._cached(("bomb_paint", colour, rust, tuple(bands), seed, bleach), build)


def mud(colour=(0.105, 0.078, 0.052), wet=0.5, seed=0.0, cracks=0.6, dry=(0.26, 0.21, 0.15)):
    """Churned crater mud: dark and damp in the hollows, dry and cracked on the high spots."""
    def build():
        g = Graph("mud")
        p = mat._seeded(g, seed)
        _, _, z = g.separate(g.world_position())
        blotch = g.noise(p, scale=2.4, detail=4.0, roughness=0.65)
        high = g.smooth(g.add(z, g.mul(g.sub(blotch, 0.5), 0.25)), 0.03, 0.26)
        base = g.mix(high, colour, dry)
        crack = g.voronoi(p, scale=5.5, feature="DISTANCE_TO_EDGE")
        crack_mask = g.mul(g.mul(g.smooth(crack, 0.05, 0.0), high), cracks)
        base = g.mix(crack_mask, base, mat.SOOT)
        base = g.mix(g.smooth(g.ao(0.2), 0.85, 0.35), base, tuple(c * 0.35 for c in colour))
        lumps = g.noise(p, scale=11.0, detail=3.0, roughness=0.6)
        g.principled(base=base, roughness=g.mix_value(high, 0.95 - 0.6 * wet, 0.95), specular=g.mix_value(high, 0.5 * wet + 0.1, 0.1),
                     bump=g.bump(g.sub(g.mul(lumps, 0.6), crack_mask), 0.02))
        return g.material
    return mat._cached(("mud", colour, wet, seed, cracks, dry), build)


def burlap(colour=(0.27, 0.215, 0.13), seed=0.0):
    """Sandbag sacking: sun-bleached jute, dirty in the creases."""
    def build():
        g = Graph("burlap")
        p = mat._seeded(g, seed)
        blotch = g.noise(p, scale=5.0, detail=3.0, roughness=0.6)
        tone = g.mix(g.remap(g.object_random(), 0.0, 1.0, 0.0, 0.9), tuple(c * 0.72 for c in colour),
                     tuple(min(1.0, c * 1.18) for c in colour))
        base = g.mix(g.remap(blotch, 0.35, 0.7, 0.0, 0.55), tone, tuple(c * 0.55 for c in colour))
        base = g.mix(g.smooth(g.ao(0.12), 0.8, 0.3), base, mat.SOOT)
        base = mat._ground_dirt(g, base, height=0.25, amount=0.35)
        weave = g.noise(p, scale=38.0, detail=1.0)
        g.principled(base=base, roughness=0.95, specular=0.05, bump=g.bump(weave, 0.004))
        return g.material
    return mat._cached(("burlap", colour, seed), build)


def cloth_mat(colour=(0.42, 0.10, 0.05), seed=0.0, fade=0.4, emblem=None):
    """Thin dyed cloth (prayer flag, banner): faded towards the hem, sooty at the top."""
    def build():
        g = Graph("cloth")
        p = mat._seeded(g, seed)
        stain = g.noise(p, scale=3.5, detail=3.0, roughness=0.6)
        base = g.mix(g.remap(stain, 0.3, 0.75, 0.0, fade), colour, tuple(min(1.0, c * 1.5 + 0.06) for c in colour))
        base = g.mix(g.smooth(g.ao(0.1), 0.7, 0.2), base, tuple(c * 0.4 for c in colour))
        g.principled(base=base, roughness=0.95, specular=0.05)
        return g.material
    return mat._cached(("cloth", colour, seed, fade, emblem), build)


def wax(colour=(0.42, 0.36, 0.25), seed=0.0):
    def build():
        g = Graph("wax")
        g.principled(base=colour, roughness=0.55, specular=0.3, emission=colour, emission_strength=0.1)
        return g.material
    return mat._cached(("wax", colour, seed), build)


def water(colour=(0.02, 0.30, 0.03), glow=0.9, seed=0.0):
    """The pool's glowing water. Tag the object with geo.set_fx(obj, "slime"): its pixels then take
    the four animated slime greens (they shimmer and are never darkened at night). The ripple
    pattern here decides WHICH of the four each pixel gets, so the surface does not go flat."""
    def build():
        from pipeline.bscene import EXPOSURE
        g = Graph("water")
        p = mat._seeded(g, seed)
        ripple = g.noise(g.mapping(p, scale=(1.0, 1.0, 0.2)), scale=7.0, detail=3.0, roughness=0.7, distortion=1.2)
        tone = g.ramp(ripple, [(0.30, tuple(c * 0.55 for c in colour)), (0.52, colour),
                               (0.72, tuple(min(1.0, c * 1.7 + 0.02) for c in colour))])
        g.principled(base=tone, roughness=0.25, specular=0.5, emission=tone, emission_strength=glow * 2.0 ** -EXPOSURE)
        return g.material
    return mat._cached(("water", colour, glow, seed), build)


def paint(colour=(0.78, 0.76, 0.68), wear=0.4, seed=0.0, glow=0.0):
    """Brushed-on paint for marks on metal (stencils, graffiti): the kit's sign paint, chips showing
    a dark undercoat rather than rust so that thin strokes keep their colour."""
    def build():
        g = Graph("mark_paint")
        p = mat._seeded(g, seed)
        chips = g.noise(p, scale=11.0, detail=3.0, roughness=0.7)
        mask = g.smooth(chips, 0.86 - wear * 0.4, 0.90 - wear * 0.4)
        base = g.mix(g.remap(g.noise(p, scale=4.0, detail=2.0), 0.3, 0.7, 0.0, 0.35), colour, tuple(c * 0.7 for c in colour))
        base = g.mix(mask, base, (0.10, 0.07, 0.05))
        g.principled(base=base, roughness=0.75, specular=0.15, emission=base if glow else None, emission_strength=glow)
        return g.material
    return mat._cached(("mark_paint", colour, wear, seed, glow), build)


def atom_emblem(centre, size, x=(1, 0, 0), y=(0, 0, 1), material=None, stroke=0.02, layer="main"):
    """The Children of Atom's mark: three orbits and a nucleus, as tubes in the plane spanned by
    x and y. size: overall width in metres (0.4 m is about the smallest that still reads)."""
    material = material or paint((0.80, 0.78, 0.70), wear=0.2)
    c, x, y = Vector(centre), Vector(x).normalized(), Vector(y).normalized()
    objects = []
    for turn in (0.0, 60.0, 120.0):
        a = math.radians(turn)
        ex = x * math.cos(a) + y * math.sin(a)
        ey = -x * math.sin(a) + y * math.cos(a)
        objects.append(geo.pipe(ellipse_points(c, size / 2.0, size * 0.17, 18, ex, ey), stroke, material, layer, "atom", 4))
    n = x.cross(y).normalized()
    dot = geo.pipe([tuple(c - n * 0.004), tuple(c + n * 0.004)], size * 0.09, material, layer, "atom_dot", 6)
    objects.append(dot)
    return no_block(objects)


def turned(rot_deg, at=(0, 0, 0)):
    """Matrix: rotation about Z by rot_deg, then translation - for move()."""
    return Matrix.Translation(Vector(at)) @ Matrix.Rotation(math.radians(rot_deg), 4, "Z")


def hex_at(dhx, dhy, z=0.0):
    """World point (x, y, z) of a hex centre."""
    x, y = G.hex_xy(dhx, dhy)
    return (x, y, z)
