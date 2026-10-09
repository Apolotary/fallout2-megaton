# SPDX-License-Identifier: MIT
"""Extra kit of the "gate" author (pieces/gate/*.py): aircraft scrap, scaffolding, sandbags,
floodlights, and the ROW FRAME the gate and the perimeter accents are modelled in.

    from kit import gate_extra as X

ROW FRAME   The town's outer wall runs along ODD hex rows (hy 127 at the gate) while a piece's
            origin hex must be even / even. So everything that stands on the wall line is modelled
            on row dhy = +1 of its origin, in a frame of its own:

                row = X.Row(dhx, dhy=1)      # frame origin = ground point of hex (dhx, dhy)
                row.p(r, f, z)               # world point: r metres to the SCREEN RIGHT along the row
                                             # (falling hx), f metres towards the viewer, z up
                row.r_of(hx)                 # r of another hex of that row (even hx sit on the line,
                                             # odd hx 0.4 m behind it, like under stock walls)

            Objects placed with rot=geo.U have local +X = +r and local -Y = +f, so a helper that
            takes `at` and runs along local +X runs to the screen right from row.p(r, f, z).

SURFACES    skin() and hazard() take UV coordinates in METRES (u along the sheet, v across / up);
            every mesh builder in this file writes such UVs, so panel seams follow a curved
            fuselage or a wing instead of cutting through it in world space.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from pipeline import proj as G
from . import geo, mat
from .nodes import Graph

HEX_R = G.SQ_U_M / 2.0            # metres between neighbouring hexes along a row (0.6928)
ODD_BACK = 0.4                    # an odd-hx hex lies this far behind the row line


class Row:
    """Frame on a hex row: see the module docstring."""

    def __init__(self, dhx=0, dhy=1):
        self.dhx, self.dhy = dhx, dhy
        self.x0, self.y0 = G.hex_xy(dhx, dhy)

    def p(self, r=0.0, f=0.0, z=0.0):
        return (self.x0 - r, self.y0 + f, z)

    def r_of(self, dhx):
        return self.x0 - G.hex_xy(dhx, self.dhy)[0]

    def edge(self, dhx, side):
        """r of the left (-1) or right (+1) boundary of hex dhx's cell on the row line."""
        return self.r_of(dhx) + side * HEX_R / 2.0


# ----------------------------------------------------------------- materials
def _uv(g, uv):
    if uv:
        u, v, _ = g.separate(g.coords("UV"))
    else:
        x, _, z = g.separate(g.coords())
        u, v = x, z
    return u, v


def _band(g, value, lo, hi, soft=0.012):
    return g.mul(g.smooth(value, lo - soft, lo + soft), g.sub(1.0, g.smooth(value, hi - soft, hi + soft)))


def skin(tint=(0.40, 0.42, 0.44), panel=(0.9, 0.6), bands=(), rust=0.2, grime=0.5, wear=0.35, seed=0.0,
         uv=True, rivets=True, metallic=0.55, tone=0.45, stagger=True):
    """Aircraft skin: staggered riveted panels of slightly different tone, dark seams, run-off
    streaks, rust creeping in from the low edge, and painted bands.
    panel: (along, across) panel size in metres. bands: [(axis "u" | "v", from, to, colour), ...]
    painted stripes in metres of that axis; the paint is chipped by `wear`.
    tone: how much darker the darkest panel is (0 = all alike). stagger: every other row of panels
    is shifted half a panel (patched skin); without, the seams run straight through (ribs and spars)."""
    bands = tuple((axis, float(a), float(b), tuple(colour)) for axis, a, b, colour in bands)

    def build():
        g = Graph("skin")
        u, v = _uv(g, uv)
        pu, pv = panel
        row = g.floor(g.div(v, pv))
        u2 = g.add(u, g.mul(g.fract(g.mul(row, 0.5)), pu)) if stagger else u   # every other row half a panel on
        fu = g.fract(g.div(u2, pu))
        fv = g.fract(g.div(v, pv))
        du = g.mul(g.minimum(fu, g.sub(1.0, fu)), pu)
        dv = g.mul(g.minimum(fv, g.sub(1.0, fv)), pv)
        edge = g.minimum(du, dv)
        seam = g.smooth(edge, 0.03, 0.008)
        index = g.combine(g.floor(g.div(u2, pu)), row, seed + 0.37)
        per_panel = g.white_noise(index)
        p = g.combine(g.add(u, seed * 7.3), g.add(v, seed * 3.1), seed)
        base = g.mix(per_panel, tuple(c * (1.0 - tone) for c in tint), tint)
        # paint
        chips = g.noise(p, scale=7.0, detail=4.0, roughness=0.7)
        kept = g.smooth(chips, 0.30 + wear * 0.25, 0.36 + wear * 0.25)
        for axis, lo, hi, colour in bands:
            mask = g.mul(_band(g, u if axis == "u" else v, lo, hi), kept)
            base = g.mix(mask, base, colour)
        # grime: streaks running down from seams, soot in the seams
        streak = g.noise(g.combine(g.mul(u, 9.0), g.mul(v, 0.7), seed), scale=1.0, detail=3.0, roughness=0.6)
        base = g.mix(g.mul(g.smooth(streak, 0.42, 0.8), grime), base, (0.07, 0.06, 0.05))
        blotch = g.noise(p, scale=2.4, detail=5.0, roughness=0.7, distortion=0.5)
        rusty = g.smooth(g.add(blotch, g.mul(g.smooth(edge, 0.12, 0.0), 0.12)), 1.0 - rust * 0.62, 1.04 - rust * 0.62)
        rust_colour = g.ramp(g.noise(p, scale=9.0, detail=4.0), [(0.3, mat.RUST_DARK), (0.55, mat.RUST_MID), (0.8, mat.RUST_LIGHT)])
        base = g.mix(rusty, base, rust_colour)
        base = g.mix(seam, base, mat.SOOT)
        height = g.mul(seam, -1.0)
        if rivets:
            near = g.smooth(g.absolute(g.sub(edge, 0.075)), 0.03, 0.012)
            dots = g.smooth(g.absolute(g.sub(g.fract(g.div(g.add(u2, v), 0.16)), 0.5)), 0.30, 0.16)
            rivet = g.mul(near, dots)
            base = g.mix(g.mul(rivet, 0.55), base, (0.05, 0.05, 0.05))
            height = g.add(height, g.mul(rivet, 0.6))
        base = mat._ground_dirt(g, base, amount=0.5)
        g.principled(base=base, roughness=g.mix_value(rusty, 0.45, 0.9), metallic=g.mix_value(rusty, metallic, 0.0),
                     specular=0.4, bump=g.bump(height, 0.008))
        return g.material
    return mat._cached(("x_skin", tint, panel, bands, rust, grime, wear, seed, uv, rivets, metallic, tone, stagger), build)


def hazard(a=(0.62, 0.40, 0.03), b=(0.025, 0.025, 0.025), width=0.36, slope=1.0, wear=0.45, seed=0.0, uv=True):
    """Diagonal warning stripes, sun-faded and chipped down to rust. width: one yellow + one black."""
    def build():
        g = Graph("hazard")
        u, v = _uv(g, uv)
        t = g.fract(g.div(g.add(u, g.mul(v, slope)), width))
        paint = g.mix(g.smooth(g.absolute(g.sub(t, 0.5)), 0.24, 0.26), a, b)
        p = g.combine(g.add(u, seed * 5.1), g.add(v, seed * 2.3), seed)
        chips = g.noise(p, scale=8.0, detail=4.0, roughness=0.75)
        gone = g.smooth(chips, 0.74 - wear * 0.3, 0.78 - wear * 0.3)
        rust_colour = g.ramp(g.noise(p, scale=10.0, detail=3.0), [(0.3, mat.RUST_DARK), (0.6, mat.RUST_MID)])
        base = g.mix(gone, paint, rust_colour)
        base = g.mix(g.mul(g.noise(p, scale=2.0, detail=3.0), 0.35), base, mat.DIRT)
        base = mat._ground_dirt(g, base, amount=0.5)
        g.principled(base=base, roughness=0.8, specular=0.15)
        return g.material
    return mat._cached(("x_hazard", a, b, width, slope, wear, seed, uv), build)


def fan_face(blades=14, seed=0.0):
    """The front of a turbofan seen down the intake: dark radial blades around a hub (the disc lies in
    the object's local XY plane)."""
    def build():
        g = Graph("fan")
        x, y, _ = g.separate(g.coords())
        angle = g.div(g.math("ARCTAN2", y, x), 2.0 * math.pi)
        saw = g.fract(g.mul(angle, float(blades)))
        blade = g.mix(g.smooth(saw, 0.05, 0.95), (0.34, 0.35, 0.37), (0.02, 0.02, 0.024))
        g.principled(base=blade, roughness=0.45, metallic=0.5, specular=0.4)
        return g.material
    return mat._cached(("x_fan", blades, seed), build)


def bright_metal(colour=(0.55, 0.56, 0.58), roughness=0.3):
    """Polished lip rings, handles, fresh weld: the brightest thing on a piece."""
    return mat.flat(colour, roughness=roughness, metallic=0.85)


def sandbag_cloth(seed=0.0):
    return mat.tarp((0.30, 0.25, 0.16), seed=seed)


# ------------------------------------------------------------------- meshes
def grid_mesh(name, points, uvs, material, at=(0, 0, 0), rot=0.0, tilt=0.0, roll=0.0, layer="main",
              solidify=0.0, smooth=True, close_j=False, caps=False, bevel=0.0):
    """Quad grid points[i][j] (local metres) with UVs uvs[i][j] (metres). close_j joins the last
    column to the first (uvs then need one extra column); caps closes both i ends with an n-gon."""
    bm = bmesh.new()
    layer_uv = bm.loops.layers.uv.new("UVMap")
    verts = [[bm.verts.new(p) for p in row] for row in points]
    nj = len(points[0])
    for i in range(len(points) - 1):
        for j in range(nj if close_j else nj - 1):
            j2 = (j + 1) % nj
            face = bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j2], verts[i][j2]))
            for loop, (a, b) in zip(face.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[layer_uv].uv = uvs[a][b if b < len(uvs[a]) else 0]
    if caps:
        for i in (0, len(points) - 1):
            face = bm.faces.new(verts[i] if i else list(reversed(verts[i])))
            for loop, j in zip(face.loops, range(nj) if i else reversed(range(nj))):
                loop[layer_uv].uv = uvs[i][j]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return geo._finish(bm, name, material, at, rot, layer, tilt, roll, smooth=smooth, bevel=bevel, solidify=solidify)


def plate(width, height, at=(0, 0, 0), rot=geo.U, material=None, thickness=0.03, bulge=0.0, tilt=0.0, roll=0.0,
          layer="main", name="plate", columns=12, uv_offset=(0.0, 0.0), dent=0.0, seed=0):
    """A sheet standing in the local XZ plane (x 0..width, z 0..height), front on local -Y.
    bulge: metres the middle bows out to the front (a fuselage skin panel); dent: random waviness."""
    r = geo.rng(seed)
    rows = max(2, columns // 2)
    wobble = [[r.uniform(-dent, dent) for _ in range(rows + 1)] for _ in range(columns + 1)]
    points, uvs = [], []
    for i in range(columns + 1):
        x = width * i / columns
        y = -bulge * math.sin(math.pi * i / columns)
        points.append([(x, y + wobble[i][k], height * k / rows) for k in range(rows + 1)])
        uvs.append([(x + uv_offset[0], height * k / rows + uv_offset[1]) for k in range(rows + 1)])
    obj = grid_mesh(name, points, uvs, material or skin(), at, rot, tilt, roll, layer, solidify=thickness)
    return geo.set_block(obj, geo.BLOCK_WALL)


def barrel_shell(radius, length, a0=-70.0, a1=100.0, at=(0, 0, 0), rot=geo.U, material=None, thickness=0.05,
                 segments=28, layer="main", name="barrel_shell", x0=0.0, uv_offset=(0.0, 0.0), block=True):
    """Part of a tube lying along local +X (x x0..x0+length), its axis through `at`. Angles in
    degrees: 0 = the frontmost line (local -Y), 90 = the crown, -90 = the keel. UV: u = x, v = arc."""
    points, uvs = [], []
    stations = max(2, int(round(length / 0.25)))
    for i in range(stations + 1):
        x = x0 + length * i / stations
        ring, ring_uv = [], []
        for k in range(segments + 1):
            a = math.radians(a0 + (a1 - a0) * k / segments)
            ring.append((x, -radius * math.cos(a), radius * math.sin(a)))
            ring_uv.append((x + uv_offset[0], radius * (a - math.radians(a0)) + uv_offset[1]))
        points.append(ring)
        uvs.append(ring_uv)
    obj = grid_mesh(name, points, uvs, material or skin(), at, rot, 0.0, 0.0, layer, solidify=thickness)
    return geo.set_block(obj, geo.BLOCK_WALL if block else 0.0)


def disc_sector(radius, a0, a1, at=(0, 0, 0), rot=geo.U, material=None, layer="main", name="bulkhead", x=0.0,
                segments=24, thickness=0.04):
    """Flat piece of a disc in the local YZ plane at local x (the end wall of a barrel_shell made
    with the same radius / angles / `at`): the chord a0..a1 closed straight across."""
    bm = bmesh.new()
    ring = []
    for k in range(segments + 1):
        a = math.radians(a0 + (a1 - a0) * k / segments)
        ring.append(bm.verts.new((x, -radius * math.cos(a), radius * math.sin(a))))
    bm.faces.new(ring)
    return geo.set_block(geo._finish(bm, name, material, at, rot, layer, smooth=False, solidify=thickness), 0.0)


def _airfoil(chord, thickness, count=10):
    """Closed outline [(y from the leading edge, z)], upper side first, of a symmetric NACA section."""
    upper, lower = [], []
    for i in range(count + 1):
        xc = (1.0 - math.cos(math.pi * i / count)) / 2.0
        yt = 5.0 * thickness * (0.2969 * math.sqrt(xc) - 0.1260 * xc - 0.3516 * xc ** 2 + 0.2843 * xc ** 3
                                 - 0.1036 * xc ** 4)
        upper.append((xc * chord, yt * chord))
        lower.append((xc * chord, -yt * chord * 0.7))          # flatter underneath
    return upper + list(reversed(lower[1:-1]))


def wing(span, chord_root=1.7, chord_tip=1.1, thickness=0.14, sweep=0.25, at=(0, 0, 0), rot=geo.U, material=None,
         le_front=True, tip_length=0.45, droop=0.0, layer="main", name="wing", count=10):
    """A wing panel. Local +X = from the root (x 0, cut off square) to the rounded tip (x = span).
    Origin: the leading edge at the root, on the chord line. With le_front the leading edge is the
    object's front (the wing reaches back to local +Y); without, it is its back (the wing reaches to
    local -Y) - so rot=0 with le_front=False gives a wing whose root is on the screen right and whose
    leading edge faces the viewer. sweep: metres the tip's leading edge lies behind the root's.
    droop: metres the tip hangs lower than the root. UV: u = span, v = distance round the section."""
    stations = [span * i / 8.0 for i in range(8)]
    tip0 = span - tip_length
    stations = [s for s in stations if s < tip0] + [tip0 + tip_length * math.sin(math.pi / 2 * k / 4) for k in range(5)]
    points, uvs = [], []
    for s in stations:
        t = s / span
        chord = chord_root + (chord_tip - chord_root) * t
        le = sweep * t
        scale = 1.0
        if s > tip0:
            q = (s - tip0) / tip_length
            scale = max(0.08, math.sqrt(max(0.0, 1.0 - q * q)))
            le += chord * (1.0 - scale) * 0.5
        outline = _airfoil(chord * scale, thickness, count)
        z0 = -droop * t
        side = 1.0 if le_front else -1.0
        ring = [(s, side * (le + y), z0 + z) for y, z in outline]
        length = 0.0
        ring_uv = []
        for k, (y, z) in enumerate(outline + [outline[0]]):
            if k:
                py, pz = (outline + [outline[0]])[k - 1]
                length += math.hypot(y - py, z - pz)
            ring_uv.append((s, length))
        points.append(ring)
        uvs.append(ring_uv)
    obj = grid_mesh(name, points, uvs, material or skin(panel=(0.55, 0.42)), at, rot, 0.0, 0.0, layer,
                    close_j=True, caps=True, smooth=True)
    modifier = obj.modifiers.new("edges", "EDGE_SPLIT")
    modifier.split_angle = math.radians(55)
    return geo.set_block(obj, 0.0)


def nacelle(length=1.5, radius=0.5, at=(0, 0, 0), rot=geo.U, cowl=None, lip=None, layer="main", blades=14,
            band=None):
    """A stubby turbofan pod, its axis level, pointing at the viewer with rot=U: `at` is the centre
    of its REAR end, the intake is `length` metres to the front. Returns the list of objects:
    cowling, polished intake lip, the dark throat, fan face, spinner.
    band: optional (from, to, material): a painted ring round the cowling between those metres from
    the rear end."""
    cowl = cowl or mat.painted_metal((0.32, 0.30, 0.25), flaking=0.5, seed=5)
    lip = lip or bright_metal()
    r, n = radius, length
    profile = [(0.0, 0.0), (r * 0.52, 0.0), (r * 0.62, n * 0.08), (r * 0.90, n * 0.38), (r, n * 0.62), (r, n * 0.84),
               (r * 0.96, n * 0.93)]
    objects = [geo.lathe(profile, at, cowl, 32, rot, 90.0, 0.0, layer, "nacelle")]
    if band:
        b0, b1, band_material = band
        objects.append(geo.lathe([(r * 1.012, b0), (r * 1.012, b1)], at, band_material, 32, rot, 90.0, 0.0, layer,
                                 "nacelle_band"))
    lip_profile = [(r * 0.96, n * 0.93), (r * 0.93, n * 0.985), (r * 0.86, n), (r * 0.79, n * 0.985), (r * 0.76, n * 0.93)]
    objects.append(geo.lathe(lip_profile, at, lip, 32, rot, 90.0, 0.0, layer, "nacelle_lip"))
    throat = [(r * 0.76, n * 0.93), (r * 0.75, n * 0.80)]
    objects.append(geo.lathe(throat, at, mat.flat((0.05, 0.05, 0.055), roughness=0.6, metallic=0.3), 32, rot, 90.0,
                             0.0, layer, "nacelle_throat"))
    fan = [(r * 0.75, n * 0.80), (0.0, n * 0.80)]
    objects.append(geo.lathe(fan, at, fan_face(blades), 32, rot, 90.0, 0.0, layer, "nacelle_fan"))
    spinner = [(r * 0.26, n * 0.80), (r * 0.21, n * 0.86), (r * 0.10, n * 0.93), (0.0, n * 0.96)]
    objects.append(geo.lathe(spinner, at, mat.flat((0.50, 0.48, 0.42), roughness=0.5), 20, rot, 90.0,
                             0.0, layer, "nacelle_spinner"))
    return geo.set_block(objects, 0.0)


# ------------------------------------------------------- scaffold, bags, lamps
def sandbag(at=(0, 0, 0), rot=0.0, size=(0.62, 0.34, 0.18), material=None, seed=0, layer="main"):
    """One filled sandbag lying on `at` (centre of its underside), long axis along rot."""
    r = geo.rng(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    sag = r.uniform(-0.15, 0.15)
    for vert in bm.verts:
        x, y, z = vert.co
        x = math.copysign(abs(x) ** 0.55, x)
        y = math.copysign(abs(y) ** 0.7, y)
        z = math.copysign(abs(z) ** 0.75, z)
        vert.co = Vector((x * sx, y * sy, (z + 1.0) * sz * (1.0 + sag * x)))
    return geo._finish(bm, "sandbag", material or sandbag_cloth(seed % 5), at, rot, layer, smooth=True)


def sandbags(a, b, courses=2, z=0.0, seed=1, size=(0.62, 0.34, 0.18), layer="main", block=None):
    """A low wall of sandbags from ground point a to b, laid in bond; `courses` high."""
    r = geo.rng(seed)
    at, rot, length = geo.span(a, b)
    direction = Vector((math.cos(math.radians(rot)), math.sin(math.radians(rot)), 0.0))
    objects = []
    for course in range(courses):
        step = size[0] * 0.92
        count = max(1, int(round(length / step)))
        step = length / count
        offset = 0.5 if course % 2 == 0 else 1.0
        for i in range(count if course % 2 == 0 else count - 1):
            position = Vector((at[0], at[1], z)) + direction * (step * (i + offset)) + Vector(
                (r.uniform(-0.03, 0.03), r.uniform(-0.03, 0.03), course * size[2] * 0.86))
            objects.append(sandbag(tuple(position), rot + r.uniform(-7, 7), size, seed=seed * 31 + len(objects),
                                   layer=layer))
    if block is not None:
        geo.set_block(objects, block)
    return objects


def ladder(foot, top, width=0.44, material=None, rung_gap=0.3, layer="main"):
    """A ladder from world point `foot` (centre between the rails) to `top`."""
    material = material or mat.steel(rust=0.7, seed=6)
    foot, top = Vector(foot), Vector(top)
    along = top - foot
    side = Vector((along.y, -along.x, 0.0))
    if side.length < 1e-6:
        side = Vector((1.0, 0.0, 0.0))
    side.normalize()
    side *= width / 2.0
    objects = []
    for sign in (-1.0, 1.0):
        objects.append(geo.pipe([tuple(foot + side * sign), tuple(top + side * sign)], 0.03, material, layer, "ladder_rail"))
    count = max(2, int(along.length / rung_gap))
    for i in range(1, count):
        point = foot + along * (i / count)
        objects.append(geo.pipe([tuple(point - side), tuple(point + side)], 0.022, material, layer, "ladder_rung"))
    return geo.set_block(objects, 0.0)


def floodlight(at, aim, size=0.2, strength=6.0, colour=(1.0, 0.82, 0.52), body=None, layer="main", lit=True):
    """A lamp head at `at` pointing along the world vector `aim`: a can with a bright lens.
    Returns [housing, lens]. The lens is an emitter: its glow is baked into the sprite."""
    body = body or mat.painted_metal((0.07, 0.07, 0.07), flaking=0.5, seed=9)
    direction = Vector(aim).normalized()
    quaternion = direction.to_track_quat("Z", "Y")
    s = size
    housing = geo.lathe([(0.0, -s * 1.1), (s * 0.55, -s * 1.1), (s * 0.7, -s * 0.9), (s, -s * 0.05), (s * 1.08, 0.0),
                         (s * 1.08, s * 0.12), (s * 0.94, s * 0.12), (s * 0.94, 0.0)], at, body, 20, 0.0, 0.0, 0.0,
                        layer, "floodlight")
    lens_material = mat.emitter(colour, strength) if lit else mat.flat((0.12, 0.11, 0.09), roughness=0.3)
    lens = geo.lathe([(s * 0.94, 0.02), (0.0, 0.02)], at, lens_material, 20, 0.0, 0.0, 0.0, layer, "floodlight_lens")
    for obj in (housing, lens):
        obj.rotation_euler = quaternion.to_euler()
    return geo.set_block([housing, lens], 0.0)


def spot(at, aim, watts=60.0, colour=(1.0, 0.78, 0.48), angle=75.0, blend=0.6, radius=0.08):
    """The light a floodlight throws, as a Cycles spot lamp (part of the piece, like an emitter:
    it only paints the pool of warm light around the lamp, it is not a second sun)."""
    data = bpy.data.lights.new("MG_spot", "SPOT")
    data.energy = watts
    data.color = colour
    data.spot_size = math.radians(angle)
    data.spot_blend = blend
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new("MG_spot", data)
    obj.location = Vector(at)
    obj.rotation_euler = (-Vector(aim).normalized()).to_track_quat("Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(obj)
    return obj


def letter(char, at, size=1.0, font="impact", material=None, rot=geo.U, roll=0.0, depth=0.06, layer="main",
           outline=0.0, bevel=0.008):
    """One sign letter standing at `at` (bottom centre of the glyph), cap height `size` metres,
    rolled `roll` degrees in the plane of the sign (positive = anticlockwise as you read it)."""
    obj = geo.lettering(char, at, rot, size=size, depth=depth, bevel=bevel, font=font, material=material, layer=layer,
                        outline=outline, name="letter_" + char)
    obj.rotation_euler = (Matrix.Rotation(math.radians(rot), 4, "Z") @ Matrix.Rotation(math.radians(90.0), 4, "X")
                          @ Matrix.Rotation(math.radians(roll), 4, "Z")).to_euler()
    return geo.set_block(obj, 0.0)


def bolt_row(a, b, count=6, radius=0.03, material=None, layer="main"):
    """A row of bolt heads / rivet domes between two world points (big enough to survive: 2 px)."""
    material = material or mat.steel(rust=0.3, seed=2)
    a, b = Vector(a), Vector(b)
    objects = []
    for i in range(count):
        point = a.lerp(b, (i + 0.5) / count)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=radius)
        objects.append(geo._finish(bm, "bolt", material, tuple(point), 0.0, layer, smooth=True))
    return geo.set_block(objects, 0.0)
