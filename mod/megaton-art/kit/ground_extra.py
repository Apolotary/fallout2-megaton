# SPDX-License-Identifier: MIT
"""Extra kit of the "ground" author (pieces/ground_*.py): pipes, cables, junk, street life and the
perimeter jumble. Shared: anybody may use it.

    from kit import ground_extra as gx

HOW THINGS ARE BUILT HERE
    Every prop below is built AROUND THE ORIGIN in the kit's canonical pose (running along local +X,
    its front on local -Y, standing on z = 0) and returns the list of its objects. Set it down with

        gx.put(gx.fridge(seed=3), at=(x, y, z), rot=geo.U, tilt=-12.0, roll=4.0)

    put() multiplies the pose onto whatever the objects already had, so groups can be nested: build
    a heap from props, then put() the whole heap. Materials are in object space and stay glued to
    their object; ground dirt, grime and rust runs are in WORLD space and follow the final pose
    (rust always runs downhill, whichever way a fridge fell).

WEAR (the point of this file: the last round's surfaces were too clean)
    paint()       sheet metal under old paint: big bleached patches, hard-edged rust eating in from
                  every EDGE (Cycles bevel node, so it works on plain boxes), rust RUNS that start
                  under fixings (`lines` = object-space heights of hoops, seams, bolt rows) and
                  fade downwards, soot in corners (ambient occlusion), splash-back at the foot
    tin()         corrugated iron: rust climbing from the ground and down from the top edge
    streak()      one rust run as geometry under a bolt / bracket: a tapering strip 2 px wide
    patch()       a plate riveted over a hole, with its own paint, four bolt heads and their runs
    stain()       a wet / oily patch on the ground under a leak
    dent()        push a lathe's skin in (a kicked drum)
    Everything is made of shapes 4 cm and bigger: no fine noise survives 40 px per metre.

SCRAP YOU CAN NAME   car_door, car_body, car_seat, bonnet, bumper, fridge, washer, stove, tv,
                     shopping_cart, engine_block, bathtub, radiator, bedstead, mattress, cabinet,
                     road_sign, gas_bottle, wheel
STORES               drum, crate, pallet, sack, cinder, bucket, jerrycan, keg, bottle_row, bale
PIPEWORK             pipe_run, flange, clamp, elbow, tee, valve, gauge, saddle, drip
STRUCTURE            post, rail, lash, awning_sheet, wire_panel
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from pipeline import proj as G
from . import geo, mat
from . import signs_extra as sx
from . import gate_extra as gate
from . import bomb_extra as bx
from .nodes import Graph

Frame = sx.Frame
HEX_U = G.SQ_U_M / 2.0            # metres between neighbouring hexes along a row (0.6928)
HEX_V = G.SQ_V_M / 2.0            # ... along a column (0.8)
ROW_BACK = 0.4                    # odd hexes of a row lie this far behind the line of the even ones

STREAK = (0.085, 0.032, 0.012)    # a rust run: darker and browner than the rust it comes from
LIME = (0.36, 0.40, 0.30)         # scale left by leaking water
OIL = (0.012, 0.011, 0.010)
PAINTS = {
    "red": (0.30, 0.045, 0.030), "oxide": (0.20, 0.060, 0.035), "orange": (0.42, 0.16, 0.030),
    "yellow": (0.44, 0.31, 0.045), "cream": (0.38, 0.33, 0.22), "white": (0.40, 0.39, 0.34),
    "green": (0.10, 0.17, 0.08), "olive": (0.17, 0.17, 0.08), "teal": (0.07, 0.17, 0.16),
    "blue": (0.09, 0.15, 0.22), "sky": (0.20, 0.30, 0.36), "grey": (0.22, 0.23, 0.23),
    "black": (0.035, 0.035, 0.04), "brown": (0.16, 0.09, 0.05), "zinc": mat.GALVANISED,
}


def col(name):
    """A paint by name (PAINTS) or an (r, g, b) passed through."""
    return PAINTS[name] if isinstance(name, str) else tuple(name)


# ============================================================================ placing
def flat(*things):
    out = []
    for thing in things:
        if isinstance(thing, (list, tuple)):
            out.extend(flat(*thing))
        elif thing is not None:
            out.append(thing)
    return out


def pose(at=(0.0, 0.0, 0.0), rot=0.0, tilt=0.0, roll=0.0, scale=1.0):
    """Matrix of a pose: rot about Z, then tilt about local X (positive = the top comes to the front),
    then roll about local Y - the same order as every kit.geo helper."""
    s = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    return (Matrix.Translation(Vector(at)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
            @ Matrix.Rotation(math.radians(tilt), 4, "X") @ Matrix.Rotation(math.radians(roll), 4, "Y")
            @ Matrix.Diagonal((s[0], s[1], s[2], 1.0)))


def put(objects, at=(0.0, 0.0, 0.0), rot=0.0, tilt=0.0, roll=0.0, scale=1.0, block=None):
    """Set a group down: world = pose @ what the objects had. Returns the flat list.
    block: metres (geo.set_block) for the whole group, e.g. 0 for things nobody bumps into."""
    matrix = pose(at, rot, tilt, roll, scale)
    objects = flat(objects)
    for obj in objects:
        obj.matrix_world = matrix @ obj.matrix_basis
    if block is not None:
        geo.set_block(objects, block)
    return objects


def no_block(objects):
    return geo.set_block(flat(objects), 0)


def hexp(dhx, dhy, z=0.0, dx=0.0, dy=0.0):
    """World point of a hex centre (plus an offset in metres)."""
    x, y = G.hex_xy(dhx, dhy)
    return (x + dx, y + dy, z)


def row_hexes(first, last, dhy=0):
    return [(d, dhy) for d in range(min(first, last), max(first, last) + 1)]


def col_hexes(first, last, dhx=0):
    return [(dhx, d) for d in range(min(first, last), max(first, last) + 1)]


def wall_u_cells(n, first=0, deep=False, front=True):
    """Footprint of a wall piece on hex row dhy = +1 (the town's wall rows are odd, origins even):
    its n hexes, the odd hexes of row 2 under its front (like the stock fence's blockers) and,
    with deep, the even hexes of row 0 behind it."""
    span = range(first, first + n)
    cells = [(d, 1) for d in span]
    if front:
        cells += [(d, 2) for d in span if d & 1]
    if deep:
        cells += [(d, 0) for d in span if not d & 1]
    return cells


# ========================================================================== materials
def _edge_wear(g, radius=0.03):
    """1 on and near every edge of the mesh, 0 on open faces (the Cycles bevel trick)."""
    bevel = g.new("ShaderNodeBevel", samples=4)
    g.put(bevel.inputs["Radius"], radius)
    geometry = g.new("ShaderNodeNewGeometry")
    dot = g.new("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    g.links.new(bevel.outputs["Normal"], dot.inputs[0])
    g.links.new(geometry.outputs["True Normal"], dot.inputs[1])
    return g.smooth(dot.outputs["Value"], 0.985, 0.90)


def _runs(g, seed=0.0, density=9.0, stretch=0.4):
    """Vertical run-off stripes in WORLD space (0..1 noise, wide across, long down)."""
    p = g.mapping(g.world_position(), scale=(density, density, stretch), location=(seed * 3.7, seed * 1.3, seed * 0.7))
    return g.noise(p, scale=1.0, detail=2.0, roughness=0.55)


def _rust(g, p, scale=1.0):
    n = g.noise(p, scale=8.0 * scale, detail=4.0, roughness=0.7)
    return g.ramp(n, [(0.25, mat.RUST_DARK), (0.5, mat.RUST_MID), (0.8, mat.RUST_LIGHT)])


def _below(g, z, line, reach):
    """1 just under object height `line`, fading to 0 `reach` metres further down, 0 above it."""
    return g.mul(g.smooth(z, line - reach, line - 0.02), g.sub(1.0, g.smooth(z, line - 0.01, line + 0.015)))


def paint(colour=(0.16, 0.22, 0.26), rust=0.45, lines=(), reach=0.4, streak=0.92, grime=0.8, fade=0.35, seed=0.0,
          gloss=0.3, edge=0.035, band=None, low=0.5, runs=0.25, metal=0.0, scale=1.0, sills=0.0):
    """Sheet metal under old paint (see WEAR in the module docstring).
    colour  a name from PAINTS or (r, g, b)
    rust    0 = fresh paint .. 1 = mostly rust; rust comes in hard-edged patches, first at edges
    lines   object-space heights (local z, metres) under which rust runs start: hoops, seams, bolts
    reach   how far the runs go down;  streak  how dark they get;  runs  runs everywhere (0..1)
    band    (z0, z1, colour): a painted stripe round the object between two local heights
    low     metres above the ground that carry splash-back dirt
    scale   size of the rust patches (2 = twice as big: use it on car bodies and wall panels)
    sills   0..1 extra rust on the lowest half metre (car sills, the foot of a wall sheet)"""
    colour = col(colour)
    lines = tuple(round(float(v), 3) for v in lines)
    band = None if band is None else (float(band[0]), float(band[1]), col(band[2]))

    def build():
        g = Graph("gx_paint")
        p = mat._seeded(g, seed)
        _, _, z = g.separate(g.coords())
        bleach = g.noise(p, scale=1.7, detail=2.0, roughness=0.5)
        light = tuple(min(0.60, c * 1.5 + 0.03) for c in colour)
        base = g.mix(g.mul(g.smooth(bleach, 0.46, 0.56), min(1.0, fade * 2.0)), colour, light)
        if band:
            mask = g.mul(g.smooth(z, band[0] - 0.01, band[0] + 0.01), g.sub(1.0, g.smooth(z, band[1] - 0.01, band[1] + 0.01)))
            base = g.mix(mask, base, band[2])
        big = g.noise(p, scale=2.3 / scale, detail=4.0 if scale <= 1.0 else 2.5, roughness=0.7 if scale <= 1.0 else 0.55, distortion=0.7)
        fine = g.noise(p, scale=9.0 / scale, detail=3.0, roughness=0.6)
        worn = _edge_wear(g, edge)
        amount = g.add(g.add(g.mul(big, 0.75), g.mul(fine, 0.28 if scale <= 1.0 else 0.16)), g.mul(worn, 0.35))
        if sills:
            _, _, wz = g.separate(g.world_position())
            amount = g.add(amount, g.mul(g.smooth(wz, 0.55, 0.0), 0.22 * sills))
        level = 0.80 - rust * 0.43                 # noise sits at 0.515 +- 0.1: rust 0.3 = a few chips, 0.5 = a quarter, 0.8 = most
        chipped = g.smooth(amount, level - 0.02, level + 0.02)
        stripes = g.smooth(_runs(g, seed), 0.42, 0.58)
        weight = runs
        for line in lines:
            weight = g.maximum(weight, _below(g, z, line, reach))
        out = g.mix(chipped, base, _rust(g, p))
        out = g.mix(g.mul(g.mul(stripes, weight), streak), out, STREAK)
        out = g.mix(g.mul(g.smooth(g.ao(0.18), 0.85, 0.35), grime), out, mat.SOOT)
        out = mat._ground_dirt(g, out, height=low, amount=0.65)
        g.principled(base=out, roughness=g.mix_value(chipped, 0.75 - gloss * 0.8, 0.95), metallic=g.mix_value(chipped, metal, 0.0),
                     specular=g.mix_value(chipped, 0.15 + gloss * 0.5, 0.06), bump=g.bump(chipped, 0.003, strength=0.6))
        return g.material
    return mat._cached(("gx_paint", colour, rust, lines, reach, streak, grime, fade, seed, gloss, edge, band, low, runs, metal,
                        scale, sills), build)


def enamel(colour="white", rust=0.3, seed=0.0, lines=(), reach=0.5, grime=0.95):
    """Stove enamel: fridges, bathtubs, washing machines. Glossy, yellowed, rust at every chip."""
    return paint(colour, rust=rust, lines=lines, reach=reach, seed=seed, gloss=0.75, grime=grime, fade=0.2, runs=0.4, streak=0.85)


def tin(colour=None, rust=0.55, seed=0.0, top=None, lines=(), grime=0.7, climb=0.9):
    """Corrugated iron (for geo.corrugated_panel) with the rust where it really is: climbing
    `climb` metres up from the ground, creeping down from the sheet's top edge (`top` = its local
    height), in runs under nail lines (`lines`), and in a few big blotches."""
    colour = None if colour is None else col(colour)
    lines = tuple(round(float(v), 3) for v in lines)

    def build():
        g = Graph("gx_tin")
        p = mat._seeded(g, seed)
        _, _, z = g.separate(g.coords())
        _, _, wz = g.separate(g.world_position())
        base = colour if colour is not None else mat.GALVANISED
        sheet = g.mix(g.smooth(g.noise(p, scale=2.6, detail=2.0), 0.35, 0.7), base, tuple(c * 0.6 for c in base))
        patches = g.noise(p, scale=1.9, detail=4.0, roughness=0.65, distortion=0.5)
        stripes = _runs(g, seed, 7.0, 0.33)
        amount = g.add(g.add(g.mul(patches, 0.62), g.mul(stripes, 0.42)), g.mul(g.smooth(wz, climb, 0.0), 0.36))
        if top is not None:
            amount = g.add(amount, g.mul(g.smooth(z, top - 0.45, top), 0.26))
        level = 1.04 - rust * 0.6
        mask = g.smooth(amount, level - 0.09, level + 0.03)
        out = g.mix(mask, sheet, _rust(g, p))
        weight = 0.0
        for line in lines:
            weight = g.maximum(weight, _below(g, z, line, 0.5))
        if lines:
            out = g.mix(g.mul(g.mul(g.smooth(stripes, 0.45, 0.62), weight), 0.8), out, STREAK)
        out = g.mix(g.mul(g.smooth(g.ao(0.12), 0.75, 0.25), grime), out, mat.SOOT)
        out = mat._ground_dirt(g, out, amount=0.6)
        g.principled(base=out, roughness=g.mix_value(mask, 0.5, 0.95), metallic=g.mix_value(mask, 0.5, 0.0),
                     specular=g.mix_value(mask, 0.4, 0.07), bump=g.bump(g.noise(p, scale=26.0, detail=2.0), 0.004))
        return g.material
    return mat._cached(("gx_tin", colour, rust, seed, top, lines, grime, climb), build)


def iron(rust=0.75, seed=0.0, colour=(0.075, 0.072, 0.07)):
    """Cast iron and bare steel: nearly black where sound, orange where not, soot in every corner."""
    def build():
        g = Graph("gx_iron")
        p = mat._seeded(g, seed)
        n = g.noise(p, scale=4.0, detail=4.0, roughness=0.7, distortion=0.4)
        worn = _edge_wear(g, 0.03)
        level = 1.0 - rust * 0.62
        mask = g.smooth(g.add(n, g.mul(worn, 0.25)), level - 0.07, level + 0.05)
        out = g.mix(mask, colour, _rust(g, p, 1.3))
        out = g.mix(g.mul(g.smooth(_runs(g, seed), 0.5, 0.7), 0.5), out, STREAK)
        out = g.mix(g.mul(g.smooth(g.ao(0.15), 0.8, 0.3), 0.8), out, mat.SOOT)
        out = mat._ground_dirt(g, out, amount=0.45)
        g.principled(base=out, roughness=g.mix_value(mask, 0.45, 0.92), metallic=g.mix_value(mask, 0.7, 0.0), specular=0.4,
                     bump=g.bump(n, 0.004))
        return g.material
    return mat._cached(("gx_iron", rust, seed, colour), build)


def chrome(dull=0.45):
    """Bumpers, handles, trim: the brightest thing on a wreck, pitted."""
    return gate.bright_metal((0.50, 0.50, 0.52), roughness=dull)


def dark(value=0.012):
    """The inside of a hole, a drum, a doorway."""
    return mat.flat((value, value, value * 1.05), roughness=0.9)


def wood(colour=(0.25, 0.14, 0.065), seed=0.0, axis="X", width=0.6, grey=0.35):
    """One board (grain along `axis`); width = the plank repeat across it."""
    return mat.planks(colour=colour, width=width, axis=axis, grey=grey, seed=seed)


def canvas(colour=(0.30, 0.25, 0.15), stripes=None, seed=0.0):
    """Awning and tent cloth (sx.fabric): stripes = (second colour, stripe width)."""
    return sx.fabric(col(colour), stripes=None if stripes is None else (col(stripes[0]), stripes[1]), seed=seed)


def wire(axes="xz", cell=0.12, thickness=0.32, colour=(0.20, 0.20, 0.21), seed=0.0):
    """Square wire mesh on a flat quad (a shopping cart's basket, a bedspring, rabbit wire): the wires
    are opaque, the rest is a hole. axes: the two object axes the quad lies in ("xz", "yz", "xy")."""
    def build():
        g = Graph("gx_wire")
        x, y, z = g.separate(g.coords())
        a, b = {"xz": (x, z), "yz": (y, z), "xy": (x, y)}[axes]
        da = g.absolute(g.sub(g.fract(g.div(a, cell)), 0.5))
        db = g.absolute(g.sub(g.fract(g.div(b, cell)), 0.5))
        mask = g.greater(g.maximum(da, db), 0.5 - thickness / 2.0)
        rusty = g.mix(g.smooth(g.noise(g.coords(), scale=5.0, detail=2.0), 0.4, 0.65), colour, mat.RUST_MID)
        g.principled(base=rusty, roughness=0.6, metallic=0.4, alpha=mask)
        return g.material
    return mat._cached(("gx_wire", axes, cell, thickness, colour, seed), build)


def water(colour=(0.05, 0.09, 0.08)):
    """Standing water in a trough or a bucket: dark, glossy."""
    return mat.flat(colour, roughness=0.08)


def straw(seed=0.0):
    def build():
        g = Graph("gx_straw")
        p = mat._seeded(g, seed)
        fibre = g.noise(g.mapping(p, scale=(3.0, 26.0, 26.0)), scale=1.0, detail=3.0, roughness=0.7)
        clump = g.noise(p, scale=3.0, detail=3.0)
        base = g.ramp(g.add(g.mul(fibre, 0.7), g.mul(clump, 0.3)), [(0.25, (0.10, 0.07, 0.03)), (0.5, (0.33, 0.25, 0.09)),
                                                                   (0.8, (0.52, 0.42, 0.17))])
        base = g.mix(g.mul(g.smooth(g.ao(0.15), 0.8, 0.3), 0.7), base, mat.SOOT)
        g.principled(base=base, roughness=0.95, specular=0.05, bump=g.bump(fibre, 0.02))
        return g.material
    return mat._cached(("gx_straw", seed), build)


# =============================================================================== wear
def quad(points, material=None, name="quad", layer="main", thickness=0.0):
    """A flat polygon through world points (never blocks)."""
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in points])
    return geo.set_block(geo._finish(bm, name, material, (0, 0, 0), 0.0, layer, smooth=False, solidify=thickness), 0)


def streak(frame, u, z, length=0.4, width=0.06, d=0.008, colour=STREAK, lean=0.0):
    """A rust run on a face: starts `width` wide at (u, z) and tapers down over `length`."""
    w = width / 2.0
    return quad([frame.at(u - w, d, z), frame.at(u + w, d, z), frame.at(u + lean + w * 0.35, d, z - length),
                 frame.at(u + lean - w * 0.35, d, z - length)], mat.flat(colour, roughness=0.95), "streak")


def bolts(frame, points, d=0.02, radius=0.03, material=None, runs=0.0, seed=0):
    """Bolt heads at [(u, z), ...]; runs > 0 hangs a rust run of up to that length under each."""
    objects = sx.bolts(frame, points, d=d, radius=radius, material=material)
    if runs:
        r = geo.rng(seed)
        for u, z in points:
            objects.append(streak(frame, u, z - radius * 0.5, length=runs * r.uniform(0.45, 1.0), width=radius * 2.2, d=d * 0.4,
                                  lean=r.uniform(-0.02, 0.02)))
    return geo.set_block(objects, 0)


def patch(frame, u, z, w, h, material=None, d=0.0, thickness=0.022, roll=0.0, runs=0.35, seed=0, bolt=0.028):
    """A plate riveted on at (u, z) = its lower left corner: its own paint, a bolt at every
    corner, a rust run under the two lower ones."""
    material = material or paint(("oxide", "grey", "cream", "teal", "olive")[seed % 5], rust=0.55, seed=seed)
    plate = geo.box((w, thickness, h), frame.at(u + w / 2.0, d + thickness / 2.0, z), frame.rot, material, bevel=0.005,
                    name="patch", roll=roll)
    inset = min(0.06, w * 0.18)
    made = [plate]
    made += bolts(frame, [(u + inset, z + h - inset), (u + w - inset, z + h - inset)], d=d + thickness + 0.004, radius=bolt)
    made += bolts(frame, [(u + inset, z + inset), (u + w - inset, z + inset)], d=d + thickness + 0.004, radius=bolt, runs=0.0)
    if runs:
        r = geo.rng(seed + 5)
        for bu in (u + inset, u + w - inset):
            made.append(streak(frame, bu, z, length=runs * r.uniform(0.5, 1.0), width=0.07, d=d + 0.006, lean=r.uniform(-0.03, 0.03)))
    return geo.set_block(made, 0)


def stain(at=(0.0, 0.0), radius=0.4, colour=OIL, seed=0, squash=0.75, gloss=0.3, lobes=3, z=0.006):
    """A wet or oily patch on the ground: an irregular blob, flat on the dirt. Stains laid over one
    another need different z (a millimetre or two apart): coplanar faces render black."""
    r = geo.rng(seed)
    phase = [r.uniform(0.0, 6.28) for _ in range(lobes)]
    amp = [r.uniform(0.08, 0.22) for _ in range(lobes)]
    points = []
    for i in range(22):
        a = 2.0 * math.pi * i / 22
        k = 1.0 + sum(amp[j] * math.sin((j + 2) * a + phase[j]) for j in range(lobes))
        points.append((at[0] + radius * k * math.cos(a), at[1] + radius * squash * k * math.sin(a), z))
    return quad(points, mat.flat(colour, roughness=1.0 - gloss), "stain")


def dent(obj, angle=200.0, z=0.45, radius=0.28, depth=0.06):
    """Push the skin of a lathe in around (angle, z): a drum that was dropped."""
    a = math.radians(angle)
    mesh = obj.data
    reach2 = radius * radius
    centre = None
    for vertex in mesh.vertices:
        co = vertex.co
        r = math.hypot(co.x, co.y)
        if r < 1e-4:
            continue
        if centre is None:
            centre = Vector((r * math.cos(a), r * math.sin(a), z))
        d2 = (co - centre).length_squared
        if d2 < reach2:
            push = depth * (1.0 - d2 / reach2) ** 2
            vertex.co = Vector((co.x * (1.0 - push / r), co.y * (1.0 - push / r), co.z))
    return obj


# ============================================================================= stores
def drum(colour="oxide", seed=0, band=None, rust=0.5, height=0.88, radius=0.29, open_top=False, dents=1, lying=False,
         bung=True):
    """200-litre drum. band: colour of a painted band round its middle. open_top: lid gone, dark inside.
    lying: on its side along local X (resting on z = 0)."""
    r, h, rib = radius, height, 0.016
    hoops = (h * 0.33, h * 0.66)
    profile = [(r * 0.95, 0.0), (r, 0.025)]
    for z in hoops:
        profile += [(r, z - 0.035), (r + rib, z - 0.014), (r + rib, z + 0.014), (r, z + 0.035)]
    profile += [(r, h - 0.03), (r + 0.006, h - 0.012), (r + 0.006, h)]
    if open_top:
        profile += [(r * 0.95, h), (r * 0.95, h - 0.06)]
    else:
        profile += [(r * 0.93, h), (r * 0.93, h - 0.03), (0.0, h - 0.03)]
    material = paint(colour, rust=rust, lines=() if lying else (h - 0.02,) + hoops, reach=0.24, seed=seed, runs=0.3,
                     band=None if band is None else (h * 0.40, h * 0.60, band), low=0.3)
    body = geo.lathe(profile, (0, 0, 0), material, 24, name="drum")
    rr = geo.rng(seed * 13 + 1)
    for _ in range(dents):
        dent(body, rr.uniform(150.0, 300.0), rr.uniform(0.2, h - 0.2), rr.uniform(0.2, 0.3), rr.uniform(0.03, 0.07))
    made = [body]
    if open_top:
        made.append(geo.cylinder(r * 0.95, 0.02, (0, 0, h - 0.08), dark(), 20, name="drum_inside"))
    elif bung:
        made.append(geo.cylinder(0.04, 0.02, (r * 0.55, -r * 0.2, h - 0.03), dark(0.03), 8, name="bung"))
    if lying:
        put(made, (-h / 2.0, 0.0, r + rib), tilt=0.0, roll=90.0)
    return made


def keg(seed=0, height=0.62, radius=0.24):
    """A beer keg: bulged steel, two rolled chimes, hand holes."""
    r, h = radius, height
    profile = [(r * 0.86, 0.0), (r * 0.9, 0.04), (r * 0.9, 0.07), (r, 0.12), (r * 1.04, h * 0.5), (r, h - 0.12), (r * 0.9, h - 0.07),
               (r * 0.9, h - 0.02), (r * 0.84, h), (r * 0.80, h - 0.05), (0.0, h - 0.06)]
    return [geo.lathe(profile, (0, 0, 0), paint("zinc", rust=0.25, lines=(h - 0.1, h * 0.5), seed=seed, gloss=0.6, metal=0.6), 18,
                      name="keg")]


def crate(size=(0.8, 0.7, 0.6), seed=0, colour=(0.28, 0.17, 0.08), slats=True, mark=None, lid=True):
    """A slatted crate: boards with dark gaps (you see into it), corner battens, a stencil mark.
    mark: colour of a painted rectangle on the front (a faded label)."""
    sx_, sy, sz = size
    r = geo.rng(seed)
    made = [geo.box((sx_ - 0.06, sy - 0.06, sz - 0.04), (0, 0, 0.02), 0.0, dark(0.02), bevel=0.0, name="crate_dark")]
    count = max(2, int(round(sz / 0.2)))
    step = sz / count
    for face, (length, depth, rot, off) in enumerate(((sx_, sy, 0.0, -1), (sx_, sy, 0.0, 1), (sy, sx_, 90.0, -1), (sy, sx_, 90.0, 1))):
        for i in range(count):
            if slats and r.random() < 0.08:
                continue
            board = wood(tuple(c * r.uniform(0.75, 1.25) for c in colour), seed=seed * 7 + face * 5 + i, axis="X", grey=r.uniform(0.15, 0.5))
            gap = 0.03 if slats else 0.008
            y = off * (depth / 2.0 - 0.012)
            at = (0.0, y, i * step + gap / 2.0) if rot == 0.0 else (-y, 0.0, i * step + gap / 2.0)
            made.append(geo.box((length - 0.02, 0.024, step - gap), at, rot, board, bevel=0.004, name="crate_slat"))
    batten = wood(tuple(c * 0.6 for c in colour), seed=seed + 3, axis="Z", grey=0.2)
    for ax in (-1, 1):
        for ay in (-1, 1):
            made.append(geo.box((0.07, 0.07, sz), (ax * (sx_ / 2.0 - 0.02), ay * (sy / 2.0 - 0.02), 0.0), 0.0, batten, bevel=0.004,
                                name="crate_batten"))
    if lid:
        for i in range(3):
            w = (sy - 0.02) / 3.0
            made.append(geo.box((sx_ + 0.02, w - 0.012, 0.022), (0.0, -sy / 2.0 + w * (i + 0.5), sz), 0.0,
                                wood(tuple(c * r.uniform(0.8, 1.3) for c in colour), seed=seed * 3 + i, axis="X", grey=0.4),
                                bevel=0.004, name="crate_lid", roll=r.uniform(-1.0, 1.0)))
    if mark is not None:
        made.append(geo.box((sx_ * 0.42, 0.006, sz * 0.3), (sx_ * 0.08, -sy / 2.0 - 0.003, sz * 0.36), 0.0,
                            mat.sign_paint(col(mark), wear=0.55, seed=seed), bevel=0.0, name="crate_mark"))
    return made


def pallet(seed=0, size=(1.2, 1.0), broken=False):
    """A shipping pallet: three runners, deck boards with gaps (one missing if broken)."""
    r = geo.rng(seed)
    w, d = size
    made = []
    for y in (-d / 2.0 + 0.05, 0.0, d / 2.0 - 0.05):
        made.append(geo.box((w, 0.09, 0.10), (0.0, y, 0.0), 0.0, wood((0.20, 0.12, 0.06), seed=seed + 1, axis="X", grey=0.3), bevel=0.004,
                            name="pallet_runner"))
    count = 6
    for i in range(count):
        if broken and i == 2:
            continue
        x = -w / 2.0 + (w - 0.1) * i / (count - 1) + 0.05
        made.append(geo.box((0.11, d, 0.022), (x, 0.0, 0.10), 0.0,
                            wood(tuple(c * r.uniform(0.8, 1.3) for c in (0.27, 0.17, 0.08)), seed=seed * 5 + i, axis="Y", grey=r.uniform(0.2, 0.6)),
                            bevel=0.003, name="pallet_board"))
    return made


def sack(seed=0, size=(0.62, 0.36, 0.2), colour=(0.30, 0.24, 0.14)):
    """A filled sack lying down (bomb_extra's sandbag with a cloth of its own)."""
    return [bx.sandbag((0, 0, 0), 0.0, size, bx.burlap(colour, seed=seed % 5), seed=seed)]


def cinder(seed=0, size=(0.40, 0.20, 0.20)):
    """A cinder block with its two holes."""
    sx_, sy, sz = size
    made = [geo.box(size, (0, 0, 0), 0.0, mat.concrete((0.27, 0.26, 0.24), cracks=0.2, seed=seed), bevel=0.008, name="cinder")]
    for x in (-sx_ * 0.23, sx_ * 0.23):
        made.append(geo.box((sx_ * 0.3, sy * 0.5, 0.01), (x, 0.0, sz - 0.004), 0.0, dark(0.02), bevel=0.0, name="cinder_hole"))
    return made


def bucket(colour="zinc", seed=0, full=False, radius=0.16, height=0.28, handle=True):
    """A pail: open top, dark inside (or water), a wire bail."""
    r, h = radius, height
    material = paint(colour, rust=0.4, lines=(h,), reach=0.2, seed=seed, gloss=0.5, metal=0.4, low=0.15)
    made = [geo.lathe([(r * 0.72, 0.0), (r, h), (r + 0.012, h), (r + 0.012, h - 0.02), (r * 0.74, 0.02)], (0, 0, 0), material, 16, name="bucket")]
    made.append(geo.cylinder(r * 0.9, 0.01, (0, 0, h * (0.82 if full else 0.3)), water() if full else dark(), 14, name="bucket_inside"))
    if handle:
        points = [(r * math.cos(a), 0.0, h - 0.02 + r * 0.9 * math.sin(a) * 0.9) for a in [math.pi * i / 8.0 for i in range(9)]]
        made.append(geo.pipe(points, 0.014, mat.steel(rust=0.5, seed=seed), name="bail"))
    return made


def jerrycan(colour="olive", seed=0):
    """A jerry can: slab sides, a pressed X, the three-bar handle and a spout cap."""
    material = paint(colour, rust=0.4, seed=seed, lines=(0.44,), reach=0.3)
    made = [geo.box((0.34, 0.16, 0.44), (0, 0, 0), 0.0, material, bevel=0.035, name="jerrycan")]
    made.append(geo.box((0.16, 0.04, 0.03), (-0.02, 0.0, 0.46), 0.0, material, bevel=0.01, name="can_handle"))
    made.append(geo.cylinder(0.035, 0.05, (0.12, 0.0, 0.43), dark(0.04), 8, name="can_cap", roll=30.0))
    return made


def bottle_row(count=5, colours=((0.05, 0.14, 0.05), (0.16, 0.09, 0.03), (0.20, 0.22, 0.20)), seed=0, spacing=0.11, height=0.26):
    """Bottles standing in a row along local X (glass that still shines: one bright pixel each)."""
    r = geo.rng(seed)
    made = []
    for i in range(count):
        c = colours[r.randrange(len(colours))]
        h = height * r.uniform(0.8, 1.15)
        made.append(geo.lathe([(0.04, 0.0), (0.042, h * 0.55), (0.016, h * 0.78), (0.016, h), (0.0, h)],
                              ((i - (count - 1) / 2.0) * spacing + r.uniform(-0.015, 0.015), r.uniform(-0.02, 0.02), 0.0),
                              mat.flat(c, roughness=0.12), 8, name="bottle"))
    return no_block(made)


def bale(seed=0, size=(0.95, 0.5, 0.42)):
    """A hay bale, bound twice."""
    made = [geo.box(size, (0, 0, 0), 0.0, straw(seed), bevel=0.05, name="bale")]
    for x in (-size[0] * 0.25, size[0] * 0.25):
        made.append(geo.box((0.03, size[1] + 0.012, size[2] + 0.006), (x, 0.0, 0.0), 0.0, mat.flat((0.10, 0.07, 0.04)), bevel=0.0, name="twine"))
    return made


def gas_bottle(colour="red", seed=0, height=1.25, radius=0.115):
    """A welding gas cylinder: tall, domed, a valve guard on top."""
    r, h = radius, height
    material = paint(colour, rust=0.35, lines=(h * 0.86,), reach=0.5, seed=seed, band=(h * 0.74, h * 0.82, "white"))
    made = [geo.lathe([(r * 0.9, 0.0), (r, 0.03), (r, h * 0.84), (r * 0.8, h * 0.93), (r * 0.36, h * 0.985), (r * 0.36, h), (0.0, h)],
                      (0, 0, 0), material, 14, name="gas_bottle")]
    made.append(geo.cylinder(r * 0.5, 0.09, (0, 0, h), iron(0.5, seed), 8, name="gas_cap"))
    return made


def wheel(seed=0, radius=0.34, width=0.2, hub="oxide", standing=True):
    """A car wheel with its rim (tyre + dished steel disc). standing: on its tread, axle along local Y."""
    made = [geo.tire((0, 0, 0), radius, width, lying=True, seed=seed)]
    made.append(geo.lathe([(0.0, width * 0.42), (radius * 0.2, width * 0.42), (radius * 0.26, width * 0.55), (radius * 0.5, width * 0.62),
                           (radius * 0.57, width * 0.9), (radius * 0.6, width * 0.9), (radius * 0.6, width * 0.2), (0.0, width * 0.2)],
                          (0, 0, 0), paint(hub, rust=0.6, seed=seed, gloss=0.4), 16, name="rim"))
    if standing:
        put(made, (0.0, width / 2.0, radius), tilt=90.0)
    return made


# ============================================================================== scrap
def car_door(colour="red", seed=0, width=1.05, height=1.12, glass="none", rear=False, inside=False):
    """A car door standing in the local XZ plane (x 0..width, z 0..height), outside to the front.
    A door, not a panel: the skin's lower rear corner is cut round for the wheel arch (rear) or the
    front edge is raked like a windscreen pillar; a chrome handle and trim strip; the window frame
    stands on top. glass: "none" (hole), "glass" (dirty pane) or "boards". inside: the trim side
    is towards the viewer instead (grey door card, an armrest, a crank)."""
    c = col(colour)
    skin = paint(c, rust=0.55, seed=seed, lines=(height * 0.52,), reach=0.3, gloss=0.5, low=0.3)
    panel_h = height * 0.54
    f = Frame((0, 0, 0), 0.0)
    made = []
    if rear:
        outline = [(0.0, 0.0), (width - 0.34, 0.0)]
        outline += [(width - 0.34 + 0.34 * math.sin(a), 0.34 - 0.34 * math.cos(a) * 1.0) for a in
                    [math.pi / 2.0 * i / 5.0 for i in range(1, 6)]]
        outline += [(width, panel_h), (0.0, panel_h)]
    else:
        outline = [(0.0, 0.0), (width - 0.05, 0.0), (width, 0.10), (width, panel_h), (0.0, panel_h)]
    made.append(sx.plate(outline, (0, 0, 0), 0.0, skin, thickness=0.06, name="door_skin", bevel=0.012))
    bar = 0.07
    rake = 0.22 if not rear else 0.08
    made.append(geo.box((bar, 0.045, height - panel_h), (bar / 2.0 + 0.01, 0.0, panel_h - 0.01), 0.0, skin, bevel=0.012, name="door_post"))
    top = height - bar
    made.append(bx.beam((width - bar / 2.0, 0.0, panel_h - 0.01), (width - bar / 2.0 - rake, 0.0, height - 0.01), (0.045, bar), skin, name="door_pillar"))
    made.append(geo.box((width - rake - 0.02, 0.045, bar), ((width - rake) / 2.0 + 0.01, 0.0, top), 0.0, skin, bevel=0.012, name="door_rail"))
    if glass == "glass":
        made.append(sx.plate([(bar, panel_h), (width - bar, panel_h), (width - bar - rake, top), (bar, top)], (0, 0.012, 0), 0.0,
                             mat.glass(dirt=0.85), thickness=0.012, name="door_glass"))
    elif glass == "boards":
        for i in range(2):
            made.append(geo.box((width - rake * 0.6, 0.025, 0.16), (width / 2.0 - rake * 0.3, -0.02, panel_h + 0.04 + i * 0.2), 0.0,
                                wood(seed=seed + i, grey=0.5), bevel=0.004, name="door_board", roll=3.0 - 6.0 * i))
    if inside:
        made.append(geo.box((width - 0.16, 0.02, panel_h - 0.12), (width / 2.0, -0.04, 0.06), 0.0,
                            mat.flat((0.13, 0.12, 0.10), roughness=0.8), bevel=0.01, name="door_card"))
        made.append(geo.box((width * 0.45, 0.07, 0.06), (width * 0.45, -0.07, panel_h * 0.55), 0.0, dark(0.03), bevel=0.02, name="armrest"))
        made.append(geo.cylinder(0.035, 0.03, (width * 0.78, -0.06, panel_h * 0.4), chrome(), 8, name="crank", tilt=90.0))
    else:
        made.append(geo.box((0.17, 0.03, 0.04), (0.2, -0.045, panel_h - 0.13), 0.0, chrome(), bevel=0.008, name="door_handle"))
        made.append(geo.box((width - 0.08, 0.018, 0.035), (width / 2.0, -0.036, panel_h * 0.40), 0.0, chrome(0.5), bevel=0.0, name="door_trim"))
    return made


CAR_PROFILE = [(0.0, 0.30), (0.02, 0.74), (0.85, 0.84), (1.28, 1.34), (2.55, 1.38), (3.06, 0.93), (4.22, 0.82), (4.38, 0.62), (4.40, 0.30)]


def car_body(colour="red", seed=0, length=4.2, width=1.65, crush=0.0, wheels=(False, False), glass=True, bumper=True):
    """A car shell lying along local X (rear at x = 0, nose at x = length), on z = 0: the side
    silhouette of a sedan (boot, roof, raked screens, bonnet) with both wheel arches cut out, dark
    window holes with a chrome sill, bumpers. crush 0..1 flattens the cabin (a car that has had two
    more stacked on it). wheels: (rear, front) still on."""
    c = col(colour)
    s = length / 4.4
    squash = 1.0 - 0.5 * crush

    def pz(z):
        return 0.30 + (z - 0.30) * (squash if z > 0.9 else 1.0 - 0.15 * crush)

    top = [(x * s, pz(z)) for x, z in CAR_PROFILE]
    bottom = []
    for cx in (3.55, 0.92):                               # front arch first (we walk back along the sill)
        arch = [(cx * s + 0.40 * math.cos(a), 0.30 + 0.36 * math.sin(a)) for a in [math.pi * i / 6.0 for i in range(7)]]
        bottom += arch
    outline = top + bottom
    skin = paint(c, rust=0.42 + 0.1 * crush, seed=seed, lines=(pz(0.84), pz(1.36)), reach=0.35, gloss=0.5, low=0.35, runs=0.4, scale=2.2,
                 sills=1.0)
    body = sx.plate(outline, (0, 0, 0), 0.0, skin, thickness=width, name="car_body", bevel=0.05)
    made = [geo.set_block(body, geo.BLOCK_PROP)]
    black = dark(0.014)
    half = width / 2.0
    for side in (-1.0, 1.0):
        y = side * (half + 0.004)
        # side windows: two panes under the roof, split by the B post
        z0, z1 = pz(0.93), pz(1.30)
        for x0, x1, r0, r1 in ((1.42, 1.98, 0.14, 0.0), (2.08, 2.92, 0.0, 0.34)):
            pane = [(x0 * s, 0.0, z0), (x1 * s, 0.0, z0), ((x1 - r1) * s, 0.0, z1), ((x0 + r0 * 0.4) * s, 0.0, z1)]
            if glass:
                made.append(quad([(x, y, z) for x, _, z in pane], black, "car_window"))
        made.append(geo.box((1.6 * s, 0.012, 0.03), (2.17 * s, y, z0 - 0.03), 0.0, chrome(0.5), bevel=0.0, name="car_sill"))
        for cx, on in zip((0.92, 3.55), wheels):
            made.append(quad([(cx * s + 0.38 * math.cos(a), side * (half - 0.03), 0.30 + 0.34 * math.sin(a)) for a in
                              [math.pi * i / 6.0 for i in range(7)]], black, "car_arch"))
            if on:
                made += put(wheel(seed=seed + int(cx), radius=0.33, hub="grey"), (cx * s, side * (half - 0.13), 0.0))
    # screens (front and rear), bonnet seam, lamps
    made.append(quad([(3.03 * s, -half + 0.12, pz(0.96)), (3.03 * s, half - 0.12, pz(0.96)), (2.62 * s, half - 0.2, pz(1.33)),
                      (2.62 * s, -half + 0.2, pz(1.33))], black, "windscreen"))
    made.append(quad([(0.90 * s, -half + 0.14, pz(0.88)), (0.90 * s, half - 0.14, pz(0.88)), (1.24 * s, half - 0.22, pz(1.30)),
                      (1.24 * s, -half + 0.22, pz(1.30))], black, "rear_screen"))
    if bumper:
        made.append(geo.box((0.09, width + 0.08, 0.13), (length + 0.02, 0.0, 0.36), 0.0, chrome(), bevel=0.03, name="bumper_front"))
        made.append(geo.box((0.09, width + 0.06, 0.12), (-0.03, 0.0, 0.40), 0.0, chrome(0.55), bevel=0.03, name="bumper_rear"))
    for side in (-1.0, 1.0):
        made.append(geo.cylinder(0.10, 0.03, (length - 0.015, side * (half - 0.26), pz(0.62)), mat.flat((0.30, 0.29, 0.24), roughness=0.2), 10,
                                 name="headlamp", roll=90.0))
    return made


def car_seat(seed=0, width=1.25, colour=(0.16, 0.07, 0.04)):
    """A bench seat pulled out of a car: cushion and a raked back, split and patched."""
    cloth = bx.burlap(colour, seed=seed % 5)
    made = [geo.box((width, 0.52, 0.2), (0, 0, 0.12), 0.0, cloth, bevel=0.07, name="seat_cushion")]
    made.append(geo.box((width, 0.16, 0.56), (0.0, 0.26, 0.2), 0.0, cloth, bevel=0.06, name="seat_back", tilt=-14.0))
    made.append(geo.box((width - 0.1, 0.5, 0.1), (0, 0, 0.02), 0.0, iron(0.7, seed), bevel=0.01, name="seat_frame"))
    made.append(geo.box((0.22, 0.01, 0.2), (width * 0.2, 0.172, 0.45), 0.0, mat.tarp((0.30, 0.26, 0.2), seed=seed), bevel=0.0, name="seat_patch",
                        tilt=-14.0))
    return made


def bonnet(colour="teal", seed=0, size=(1.35, 1.1)):
    """A car bonnet lying flat (its bulge up, nose to local +X): a curved sheet with a centre crease."""
    w, d = size
    points, uvs = [], []
    for i in range(9):
        x = w * i / 8.0
        row = []
        for j in range(7):
            t = j / 6.0
            y = (t - 0.5) * d * (1.0 - 0.18 * (i / 8.0) ** 2)
            z = 0.10 * math.sin(math.pi * t) * (0.6 + 0.4 * math.sin(math.pi * i / 8.0)) + 0.02 * (1.0 - abs(t - 0.5) * 2.0)
            row.append((x - w / 2.0, y, z))
        points.append(row)
        uvs.append([(p[0], p[1]) for p in row])
    return [geo.set_block(gate.grid_mesh("bonnet", points, uvs, paint(colour, rust=0.6, seed=seed, gloss=0.5), solidify=0.03), geo.BLOCK_PROP)]


def bumper(seed=0, length=1.6, plate=True):
    """A chrome bumper bar (along local X) with its two over-riders and, perhaps, a number plate."""
    made = [geo.box((length, 0.09, 0.13), (0, 0, 0), 0.0, chrome(0.4), bevel=0.04, name="bumper")]
    for x in (-length * 0.28, length * 0.28):
        made.append(geo.box((0.07, 0.11, 0.2), (x, -0.02, -0.02), 0.0, chrome(0.35), bevel=0.03, name="overrider"))
    if plate:
        made.append(geo.box((0.32, 0.012, 0.15), (0.0, -0.055, -0.01), 0.0, paint("yellow", rust=0.3, seed=seed), bevel=0.0, name="number_plate"))
    return made


def fridge(seed=0, colour="white", size=(0.74, 0.68, 1.55), door="shut"):
    """A round-shouldered refrigerator standing on z = 0, its door to the front (local -Y).
    door: "shut", "ajar" (swung open on its hinge: dark inside, wire shelves) or "none"."""
    w, d, h = size
    body = enamel(colour, rust=0.32, seed=seed, lines=(h * 0.66, h - 0.05), reach=0.6)
    made = [geo.box((w, d, h), (0, 0.04, 0), 0.0, body, bevel=0.07, name="fridge")]
    made.append(geo.box((w - 0.08, 0.02, 0.1), (0.0, -d / 2.0 + 0.035, 0.03), 0.0, dark(0.02), bevel=0.0, name="fridge_kick"))
    split = h * 0.66
    if door == "shut":
        made.append(geo.box((w - 0.03, 0.05, split - 0.18), (0.0, -d / 2.0 + 0.02, 0.16), 0.0, body, bevel=0.03, name="fridge_door"))
        made.append(geo.box((w - 0.03, 0.05, h - split - 0.07), (0.0, -d / 2.0 + 0.02, split + 0.02), 0.0, body, bevel=0.03, name="freezer_door"))
        for z0, z1 in ((split - 0.42, split - 0.06), (split + 0.08, split + 0.3)):
            made.append(geo.box((0.035, 0.05, z1 - z0), (-w / 2.0 + 0.1, -d / 2.0 - 0.03, z0), 0.0, chrome(0.35), bevel=0.012, name="fridge_handle"))
        made.append(geo.box((0.2, 0.012, 0.05), (w * 0.16, -d / 2.0 - 0.012, split + 0.36), 0.0, chrome(0.5), bevel=0.0, name="fridge_badge"))
        f = Frame((0, -d / 2.0 - 0.006, 0), 0.0)
        made.append(streak(f, -w / 2.0 + 0.1, split - 0.44, 0.5, 0.07))
        made.append(streak(f, w * 0.2, split + 0.0, 0.34, 0.05))
    else:
        made.append(geo.box((w - 0.1, 0.03, h - 0.3), (0.0, -d / 2.0 + 0.045, 0.16), 0.0, dark(0.02), bevel=0.0, name="fridge_inside"))
        for z in (0.5, 0.82, 1.14):
            made.append(geo.box((w - 0.12, 0.02, 0.025), (0.0, -d / 2.0 + 0.02, z), 0.0, chrome(0.5), bevel=0.0, name="fridge_shelf"))
        if door == "ajar":
            leaf = [geo.box((w - 0.03, 0.06, h - 0.2), ((w - 0.03) / 2.0, 0.0, 0.0), 0.0, body, bevel=0.03, name="fridge_door")]
            leaf.append(geo.box((w - 0.14, 0.02, h - 0.34), ((w - 0.03) / 2.0, 0.035, 0.07), 0.0, paint("cream", rust=0.2, seed=seed + 2), bevel=0.0,
                                name="door_liner"))
            made += put(leaf, (w / 2.0 - 0.015, -d / 2.0, 0.16), rot=-68.0)
    return made


def washer(seed=0, colour="white", kind="washer"):
    """A white box you know by its face: "washer" (round dark porthole, a control strip) or
    "stove" (oven door with a window, four burner rings on top, a back splash)."""
    w, d, h = (0.62, 0.6, 0.88)
    body = enamel(colour, rust=0.36, seed=seed, lines=(h - 0.14,), reach=0.5)
    made = [geo.box((w, d, h), (0, 0, 0), 0.0, body, bevel=0.03, name=kind)]
    front = -d / 2.0
    made.append(geo.box((w - 0.04, 0.02, 0.1), (0.0, front - 0.004, h - 0.13), 0.0, mat.flat((0.10, 0.10, 0.11), roughness=0.4), bevel=0.0,
                        name="controls"))
    for x in (-0.18, -0.06, 0.2):
        made.append(geo.cylinder(0.028, 0.03, (x, front - 0.02, h - 0.08), chrome(), 8, name="knob", tilt=90.0))
    if kind == "washer":
        made.append(geo.cylinder(0.21, 0.03, (0.0, front - 0.012, 0.42), chrome(0.5), 18, name="port_ring", tilt=90.0))
        made.append(geo.cylinder(0.165, 0.035, (0.0, front - 0.016, 0.42), dark(0.015), 18, name="port", tilt=90.0))
    else:
        made.append(geo.box((w - 0.1, 0.03, 0.46), (0.0, front - 0.008, 0.14), 0.0, body, bevel=0.02, name="oven_door"))
        made.append(geo.box((w - 0.24, 0.035, 0.2), (0.0, front - 0.012, 0.3), 0.0, dark(0.02), bevel=0.0, name="oven_window"))
        made.append(geo.box((w - 0.16, 0.04, 0.03), (0.0, front - 0.04, 0.62), 0.0, chrome(), bevel=0.01, name="oven_handle"))
        for x in (-0.15, 0.15):
            for y in (-0.13, 0.15):
                made.append(geo.cylinder(0.09, 0.012, (x, y, h), dark(0.02), 12, name="burner"))
        made.append(geo.box((w, 0.04, 0.16), (0.0, d / 2.0 - 0.02, h), 0.0, body, bevel=0.01, name="splash"))
    return made


def tv(seed=0, colour=(0.20, 0.11, 0.05)):
    """A television: wooden box, bulging grey-green screen, two knobs, rabbit ears."""
    w, d, h = 0.66, 0.46, 0.5
    made = [geo.box((w, d, h), (0, 0, 0), 0.0, wood(colour, seed=seed, axis="X", width=0.25, grey=0.15), bevel=0.03, name="tv")]
    made.append(geo.box((w * 0.62, 0.03, h * 0.66), (-w * 0.13, -d / 2.0 - 0.006, h * 0.17), 0.0,
                        mat.flat((0.09, 0.12, 0.10), roughness=0.12), bevel=0.05, name="tv_screen"))
    for z in (h * 0.62, h * 0.38):
        made.append(geo.cylinder(0.035, 0.03, (w * 0.33, -d / 2.0 - 0.02, z), chrome(), 8, name="tv_knob", tilt=90.0))
    for side in (-1.0, 1.0):
        made.append(geo.pipe([(0.0, 0.05, h), (side * 0.3, 0.05, h + 0.42)], 0.012, chrome(0.4), name="tv_ear"))
    return made


def shopping_cart(seed=0, tipped=False):
    """A supermarket trolley: wire basket (real mesh you see through), tube frame, a red handle,
    castors. Along local X (handle at -X). tipped: lying on its side."""
    steel = mat.flat((0.22, 0.22, 0.23), roughness=0.4, metallic=0.6)
    L, w0, w1, z0, z1 = 0.86, 0.42, 0.56, 0.42, 0.98
    made = []
    # basket faces (wire): two sides, front, back, bottom
    for side in (-1.0, 1.0):
        pts = [(-L / 2.0, side * w1 / 2.0, z0), (L / 2.0, side * w0 / 2.0, z0 + 0.04), (L / 2.0, side * w0 / 2.0 * 1.05, z1 - 0.06),
               (-L / 2.0, side * w1 / 2.0 * 1.05, z1)]
        made.append(quad(pts, wire("xz", 0.11, 0.34), "cart_side"))
    made.append(quad([(L / 2.0, -w0 / 2.0, z0 + 0.04), (L / 2.0, w0 / 2.0, z0 + 0.04), (L / 2.0, w0 / 2.0 * 1.05, z1 - 0.06),
                      (L / 2.0, -w0 / 2.0 * 1.05, z1 - 0.06)], wire("yz", 0.11, 0.34), "cart_front"))
    made.append(quad([(-L / 2.0, -w1 / 2.0, z0), (-L / 2.0, w1 / 2.0, z0), (-L / 2.0, w1 / 2.0 * 1.05, z1), (-L / 2.0, -w1 / 2.0 * 1.05, z1)],
                     wire("yz", 0.11, 0.34), "cart_back"))
    made.append(quad([(-L / 2.0, -w1 / 2.0, z0), (L / 2.0, -w0 / 2.0, z0 + 0.04), (L / 2.0, w0 / 2.0, z0 + 0.04), (-L / 2.0, w1 / 2.0, z0)],
                     wire("xy", 0.11, 0.34), "cart_floor"))
    # rim and frame tubes
    for side in (-1.0, 1.0):
        a, b = (-L / 2.0, side * w1 / 2.0 * 1.05, z1), (L / 2.0, side * w0 / 2.0 * 1.05, z1 - 0.06)
        made.append(geo.pipe([a, b], 0.02, steel, name="cart_rim"))
        made.append(geo.pipe([(-L / 2.0 - 0.1, side * w1 / 2.0, z1 + 0.08), (-L / 2.0, side * w1 / 2.0, z1), (-L / 2.0 + 0.05, side * w1 / 2.0, 0.16),
                              (L / 2.0 - 0.05, side * w0 / 2.0, 0.12), (L / 2.0, side * w0 / 2.0, z0 + 0.04)], 0.02, steel, name="cart_frame"))
        for x in (-L / 2.0 + 0.08, L / 2.0 - 0.1):
            made.append(geo.cylinder(0.06, 0.04, (x, side * 0.2 - 0.02, 0.06), mat.rubber(seed), 10, name="castor", tilt=90.0))
    made.append(geo.pipe([(L / 2.0, -w0 / 2.0 * 1.05, z1 - 0.06), (L / 2.0, w0 / 2.0 * 1.05, z1 - 0.06)], 0.02, steel, name="cart_rim"))
    made.append(geo.pipe([(-L / 2.0 - 0.1, -w1 / 2.0, z1 + 0.08), (-L / 2.0 - 0.1, w1 / 2.0, z1 + 0.08)], 0.028,
                         paint("red", rust=0.25, seed=seed, gloss=0.6), name="cart_handle"))
    geo.set_block(made, geo.BLOCK_PROP)
    if tipped:
        put(made, (0.0, 0.0, 0.3), tilt=84.0)
    return made


def engine_block(seed=0, colour="orange"):
    """A V8 out of its car, on its sump: the V of two rocker covers, a round air cleaner on top,
    a fan and pulleys at the front (local +X), a bell housing behind, rusty manifolds."""
    cast = iron(0.6, seed)
    cover = paint(colour, rust=0.45, seed=seed, gloss=0.5)
    made = [geo.box((0.62, 0.42, 0.34), (0, 0, 0.16), 0.0, cast, bevel=0.03, name="block")]
    made.append(geo.box((0.52, 0.34, 0.16), (0, 0, 0.0), 0.0, cast, bevel=0.05, name="sump"))
    for side in (-1.0, 1.0):
        made.append(geo.box((0.6, 0.2, 0.2), (0.0, side * 0.22, 0.42), 0.0, cast, bevel=0.02, name="head", tilt=side * 38.0))
        made.append(geo.box((0.56, 0.17, 0.09), (0.0, side * 0.335, 0.555), 0.0, cover, bevel=0.03, name="rocker_cover", tilt=side * 38.0))
        made.append(geo.pipe([(0.24, side * 0.36, 0.36), (-0.2, side * 0.38, 0.34), (-0.34, side * 0.36, 0.2)], 0.045, mat.steel(rust=0.95, seed=seed),
                             name="manifold"))
    made.append(geo.cylinder(0.2, 0.09, (0.02, 0.0, 0.66), chrome(0.5), 16, name="air_cleaner"))
    made.append(geo.cylinder(0.07, 0.1, (0.02, 0.0, 0.57), cast, 8, name="carb"))
    made.append(geo.cylinder(0.12, 0.05, (0.34, 0.0, 0.28), cast, 12, name="pulley", roll=90.0))
    made.append(geo.cylinder(0.08, 0.05, (0.36, 0.0, 0.5), cast, 10, name="pulley_top", roll=90.0))
    for k in range(4):
        made.append(geo.box((0.02, 0.1, 0.24), (0.4, 0.0, 0.5), 0.0, paint("grey", rust=0.5, seed=seed + k), bevel=0.0, name="fan_blade",
                            centred=True))
        made[-1].rotation_euler = (math.radians(45.0 + 90.0 * k), 0.0, 0.0)
    made.append(geo.lathe([(0.0, 0.0), (0.26, 0.0), (0.26, 0.05), (0.14, 0.2), (0.0, 0.2)], (-0.31, 0.0, 0.3), cast, 14, name="bell", roll=-90.0))
    return made


def bathtub(seed=0, length=1.5, width=0.68, height=0.52, feet=True, plug_stain=True):
    """A cast-iron bath: enamel shell with a rolled rim, a dark inside with a tide mark, claw feet.
    Lying along local X on z = 0 (put it down with tilt=180 for one turned over: the rough iron
    underside shows)."""
    rings = []
    uvs = []
    steps, around = 6, 22
    for k in range(steps + 1):
        t = k / steps
        zz = (0.12 if feet else 0.0) + (height - (0.12 if feet else 0.0)) * t
        grow = 0.72 + 0.28 * math.sin(t * math.pi / 2.0)
        ring, ring_uv = [], []
        for i in range(around + 1):
            a = 2.0 * math.pi * i / around
            ca, sa = math.cos(a), math.sin(a)
            x = math.copysign(abs(ca) ** 0.6, ca) * length / 2.0 * grow
            y = math.copysign(abs(sa) ** 0.75, sa) * width / 2.0 * grow
            ring.append((x, y, zz))
            ring_uv.append((i / around * 3.0, zz))
        rings.append(ring)
        uvs.append(ring_uv)
    shell = gate.grid_mesh("bath", rings, uvs, enamel("white", rust=0.38, seed=seed, lines=(height,), reach=0.3), solidify=0.035)
    made = [geo.set_block(shell, geo.BLOCK_PROP)]
    z0 = 0.12 if feet else 0.0
    floor = [(math.copysign(abs(math.cos(a)) ** 0.6, math.cos(a)) * length / 2.0 * 0.74, math.copysign(abs(math.sin(a)) ** 0.75, math.sin(a)) * width / 2.0 * 0.74, z0 + 0.02)
             for a in [2.0 * math.pi * i / around for i in range(around)]]
    made.append(quad(floor, paint("cream", rust=0.5, seed=seed + 4, grime=1.0), "bath_floor"))
    rim = [(x, y, height + 0.01) for x, y, _ in rings[-1]]
    made.append(geo.pipe(rim, 0.03, enamel("white", rust=0.3, seed=seed + 1), name="bath_rim"))
    if feet:
        for ax in (-1.0, 1.0):
            for ay in (-1.0, 1.0):
                made.append(geo.box((0.1, 0.08, 0.14), (ax * length * 0.3, ay * width * 0.26, 0.0), 0.0, iron(0.7, seed), bevel=0.02, name="bath_foot"))
    return made


def radiator(seed=0, sections=9, height=0.62):
    """A house radiator: a row of cast-iron sections on two feet."""
    material = paint("cream", rust=0.5, seed=seed, lines=(height,), reach=0.3)
    made = []
    for i in range(sections):
        made.append(geo.box((0.06, 0.14, height - 0.08), ((i - (sections - 1) / 2.0) * 0.085, 0.0, 0.08), 0.0, material, bevel=0.025, name="rad_section"))
    width = sections * 0.085
    for z in (0.14, height - 0.06):
        made.append(geo.pipe([(-width / 2.0 - 0.06, 0.0, z), (width / 2.0 + 0.04, 0.0, z)], 0.028, material, name="rad_pipe"))
    for x in (-width / 2.0 + 0.05, width / 2.0 - 0.05):
        made.append(geo.box((0.05, 0.16, 0.08), (x, 0.0, 0.0), 0.0, iron(0.6, seed), bevel=0.01, name="rad_foot"))
    return made


def bedstead(seed=0, width=0.95, height=1.1, colour="cream"):
    """The end of an iron bed: two posts with knobs, a bowed top rail, upright bars. Stands in the
    local XZ plane."""
    material = paint(colour, rust=0.55, seed=seed, gloss=0.4)
    made = []
    for x in (-width / 2.0, width / 2.0):
        made.append(geo.pipe([(x, 0.0, 0.0), (x, 0.0, height)], 0.028, material, name="bed_post"))
        made.append(sx.sphere(0.045, (x, 0.0, height + 0.03), chrome(0.5), name="bed_knob"))
    made.append(geo.pipe([(-width / 2.0, 0.0, height * 0.9), (0.0, 0.0, height * 0.98), (width / 2.0, 0.0, height * 0.9)], 0.024, material, name="bed_rail"))
    made.append(geo.pipe([(-width / 2.0, 0.0, height * 0.4), (width / 2.0, 0.0, height * 0.4)], 0.022, material, name="bed_rail"))
    for i in range(1, 5):
        x = -width / 2.0 + width * i / 5.0
        made.append(geo.pipe([(x, 0.0, height * 0.4), (x, 0.0, height * (0.9 + 0.08 * math.sin(math.pi * i / 5.0)))], 0.018, material, name="bed_bar"))
    return made


def bedspring(seed=0, size=(1.9, 0.9)):
    """A bed's spring frame: angle iron round a wire mesh. Lies in the local XY plane."""
    w, d = size
    made = [quad([(-w / 2.0, -d / 2.0, 0.02), (w / 2.0, -d / 2.0, 0.02), (w / 2.0, d / 2.0, 0.02), (-w / 2.0, d / 2.0, 0.02)], wire("xy", 0.13, 0.3),
                 "spring_mesh")]
    steel = mat.steel(rust=0.8, seed=seed)
    for y in (-d / 2.0, d / 2.0):
        made.append(geo.pipe([(-w / 2.0, y, 0.02), (w / 2.0, y, 0.02)], 0.024, steel, name="spring_rail"))
    for x in (-w / 2.0, w / 2.0):
        made.append(geo.pipe([(x, -d / 2.0, 0.02), (x, d / 2.0, 0.02)], 0.024, steel, name="spring_rail"))
    return geo.set_block(made, geo.BLOCK_PROP)


def mattress(seed=0, size=(1.85, 0.85, 0.16), stripes=True):
    """A stained mattress with ticking stripes, lying along local X."""
    cloth = sx.fabric((0.42, 0.40, 0.34), stripes=((0.16, 0.19, 0.24), 0.07) if stripes else None, seed=seed)
    made = [geo.box(size, (0, 0, 0), 0.0, cloth, bevel=0.06, name="mattress")]
    made.append(stain((0.2, 0.05), 0.3, (0.10, 0.07, 0.04), seed=seed, gloss=0.0))
    made[-1].location.z = size[2] + 0.001
    return made


def bedroll(seed=0, length=0.75, radius=0.13, colour=(0.16, 0.20, 0.12)):
    """A rolled blanket tied with two straps, lying along local X."""
    made = [geo.cylinder(radius, length, (-length / 2.0, 0.0, radius), sx.fabric(col(colour), seed=seed), 14, name="bedroll", roll=90.0)]
    for x in (-length * 0.28, length * 0.28):
        made.append(geo.cylinder(radius + 0.008, 0.035, (x - 0.017, 0.0, radius), mat.flat((0.07, 0.045, 0.025)), 14, name="strap", roll=90.0))
    return made


def cabinet(seed=0, colour="olive", drawers=4, open_drawer=1):
    """A steel filing cabinet: drawer fronts with handles and label slots, one drawer pulled out."""
    w, d, h = 0.46, 0.6, 0.33 * drawers + 0.06
    body = paint(colour, rust=0.4, seed=seed, lines=tuple(0.04 + 0.33 * (i + 1) for i in range(drawers)), reach=0.2)
    made = [geo.box((w, d, h), (0, 0, 0), 0.0, body, bevel=0.012, name="cabinet")]
    for i in range(drawers):
        out = 0.28 if i == open_drawer else 0.0
        z = 0.04 + 0.33 * i
        made.append(geo.box((w - 0.04, 0.03 + out, 0.3), (0.0, -d / 2.0 - out / 2.0, z), 0.0, body, bevel=0.01, name="drawer"))
        made.append(geo.box((0.16, 0.03, 0.03), (0.0, -d / 2.0 - out - 0.025, z + 0.2), 0.0, chrome(), bevel=0.008, name="drawer_handle"))
        made.append(geo.box((0.12, 0.008, 0.05), (0.0, -d / 2.0 - out - 0.018, z + 0.09), 0.0, mat.flat((0.42, 0.38, 0.28)), bevel=0.0, name="drawer_label"))
        if out:
            made.append(geo.box((w - 0.08, out - 0.02, 0.01), (0.0, -d / 2.0 - out / 2.0, z + 0.29), 0.0, dark(0.03), bevel=0.0, name="drawer_inside"))
    return made


SIGN_SHAPES = ("stop", "yield", "diamond", "speed", "arrow", "street", "round")


def road_sign(kind="stop", seed=0, post=2.3, bent=8.0, text=None, size=0.72):
    """A road sign on its channel post (standing at the origin, face to the front, leaning `bent`
    degrees). kind: one of SIGN_SHAPES. The SHAPES carry the meaning; text is only added where it
    is big enough to read (speed: two numerals 0.3 m tall)."""
    r = geo.rng(seed * 7 + 3)
    f = Frame((0, 0, 0), 0.0)
    made = [geo.box((0.07, 0.035, post), (0, 0.02, 0), 0.0, paint("green" if seed % 2 else "zinc", rust=0.55, seed=seed, lines=(post * 0.8,)),
                    bevel=0.008, name="sign_post")]
    z = post - size * 0.55
    s = size
    if kind == "stop":
        face = paint("red", rust=0.3, seed=seed, gloss=0.5, edge=0.06)
        pts = [(s / 2.0 * math.cos(math.radians(22.5 + 45.0 * i)), z + s / 2.0 * math.sin(math.radians(22.5 + 45.0 * i))) for i in range(8)]
        made.append(sx.plate(pts, (0, 0, 0), 0.0, face, thickness=0.02, name="sign_face"))
        made.append(geo.box((s * 0.62, 0.008, s * 0.2), (0.0, -0.016, z - s * 0.1), 0.0, mat.sign_paint((0.62, 0.60, 0.54), wear=0.5, seed=seed), bevel=0.0,
                            name="sign_bar"))
    elif kind == "yield":
        pts = [(-s / 2.0, z + s * 0.42), (s / 2.0, z + s * 0.42), (0.0, z - s * 0.45)]
        made.append(sx.plate(pts, (0, 0, 0), 0.0, paint("red", rust=0.3, seed=seed, gloss=0.5), thickness=0.02, name="sign_face"))
        inner = [(-s * 0.28, z + s * 0.30), (s * 0.28, z + s * 0.30), (0.0, z - s * 0.2)]
        made.append(sx.plate(inner, (0, -0.014, 0), 0.0, paint("white", rust=0.25, seed=seed + 1), thickness=0.008, name="sign_inner"))
    elif kind == "diamond":
        pts = [(0.0, z - s * 0.55), (s * 0.55, z), (0.0, z + s * 0.55), (-s * 0.55, z)]
        made.append(sx.plate(pts, (0, 0, 0), 0.0, paint("yellow", rust=0.35, seed=seed, gloss=0.5), thickness=0.02, name="sign_face"))
        made.append(sx.arrow(s * 0.5, (-0.0, -0.016, z - s * 0.22), 0.0, mat.flat((0.02, 0.02, 0.02)), shaft=0.07, head=0.2, thickness=0.008, spin=90.0))
    elif kind == "speed":
        made.append(geo.box((s * 0.78, 0.02, s), (0.0, 0.0, z - s / 2.0), 0.0, paint("white", rust=0.3, seed=seed, gloss=0.5), bevel=0.02, name="sign_face"))
        made.append(geo.lettering(text or "35", (0.0, -0.014, z - s * 0.36), 0.0, size=s * 0.44, depth=0.008, bevel=0.0, font="din",
                                  material=mat.flat((0.02, 0.02, 0.02))))
        made.append(geo.box((s * 0.6, 0.008, 0.05), (0.0, -0.014, z + s * 0.26), 0.0, mat.flat((0.02, 0.02, 0.02)), bevel=0.0, name="sign_rule"))
    elif kind == "arrow":
        made.append(geo.box((s * 1.3, 0.02, s * 0.42), (0.0, 0.0, z - s * 0.2), 0.0, paint("black", rust=0.3, seed=seed), bevel=0.01, name="sign_face"))
        made.append(sx.arrow(s * 1.05, (-s * 0.52, -0.016, z + 0.01), 0.0, mat.sign_paint((0.60, 0.58, 0.50), wear=0.4, seed=seed), shaft=0.1, head=0.24,
                             thickness=0.008))
    elif kind == "street":
        made.append(geo.box((s * 1.5, 0.02, s * 0.3), (s * 0.3, 0.0, z), 0.0, paint("green", rust=0.35, seed=seed, gloss=0.5), bevel=0.008, name="sign_face"))
        made.append(geo.box((s * 1.1, 0.008, s * 0.09), (s * 0.3, -0.014, z + s * 0.1), 0.0, mat.sign_paint((0.60, 0.60, 0.54), wear=0.6, seed=seed), bevel=0.0,
                            name="sign_text"))
    else:
        made.append(sx.disc(s / 2.0, (0.0, 0.0, z), 0.0, paint("white", rust=0.3, seed=seed, gloss=0.5), thickness=0.02, name="sign_face"))
        made.append(sx.disc(s / 2.0, (0.0, -0.002, z), 0.0, paint("red", rust=0.2, seed=seed + 1), thickness=0.024, hole=s * 0.36, name="sign_ring"))
        made.append(geo.box((s * 0.74, 0.01, 0.09), (0.0, -0.03, z - 0.045), 0.0, paint("red", rust=0.2, seed=seed + 2), bevel=0.0, name="sign_slash", roll=45.0))
    made += bolts(f, [(0.0, z + s * 0.2), (0.0, z - s * 0.2)], d=0.03, radius=0.026)
    put(made, (0, 0, 0), tilt=r.uniform(-0.3, 0.3) * bent, roll=bent)
    return made


# =========================================================================== pipework
PIPE_R = 0.15             # a water main: 12 px across, the thinnest that still reads as a PIPE
PIPE_Z = 0.36             # axis height of a run lying on saddles
PIPE_HIGH = 2.36          # axis height of a run on trestles: over heads, under a roof's eave line


def pipe_paint(colour="oxide", seed=0, rust=0.55):
    """Paint for pipes: rust runs all round (water sweats off a pipe everywhere), grimy underside."""
    return paint(colour, rust=rust, seed=seed, runs=0.75, streak=0.9, gloss=0.35, grime=0.9, low=0.22, fade=0.3)


def rod(a, b, radius=PIPE_R, material=None, segments=16, name="rod", layer="main"):
    """A straight round bar or pipe from world point a to b (a real cylinder: its paint wears like
    any other object's, which a curve's does not)."""
    a, b = Vector(a), Vector(b)
    axis = b - a
    length = axis.length
    obj = geo.lathe([(radius, 0.0), (radius, length)], (0, 0, 0), material, segments, name=name, layer=layer)
    z = axis.normalized()
    ref = Vector((0.0, 0.0, 1.0)) if abs(z.z) < 0.95 else Vector((1.0, 0.0, 0.0))
    x = ref.cross(z).normalized()
    obj.matrix_world = bx.frame(a, x=x, y=z.cross(x), z=z)
    return obj


def flange(x, z=PIPE_Z, radius=PIPE_R, seed=0, colour=None, bolts_=6):
    """A bolted flange pair on a pipe along local X at (x, 0, z): two thick discs, a dark gasket
    line between them, a ring of bolt heads."""
    material = iron(0.7, seed) if colour is None else paint(colour, rust=0.5, seed=seed)
    R = radius * 1.55
    made = []
    for dx in (-0.055, 0.012):
        made.append(geo.lathe([(radius, 0.0), (R, 0.0), (R, 0.043), (radius, 0.043)], (x + dx, 0.0, z), material, 16, name="flange", roll=90.0))
    made.append(geo.lathe([(radius, 0.0), (R * 0.93, 0.0), (R * 0.93, 0.03), (radius, 0.03)], (x - 0.015, 0.0, z), dark(0.01), 16, name="gasket", roll=90.0))
    nut = mat.flat((0.05, 0.045, 0.04), roughness=0.5, metallic=0.5)
    for k in range(bolts_):
        a = 2.0 * math.pi * (k + 0.5) / bolts_
        made.append(geo.box((0.15, 0.045, 0.045), (x, (radius + R) / 2.0 * math.cos(a), z + (radius + R) / 2.0 * math.sin(a)), 0.0, nut, bevel=0.0,
                            name="flange_bolt", centred=True))
    return no_block(made)


def clamp(x, z=PIPE_Z, radius=PIPE_R, seed=0, kind="sleeve", length=0.34):
    """A repair on a pipe along local X: "sleeve" (a bolted steel sleeve, brighter than the pipe),
    "rubber" (inner tube wound round and wired) or "rag" (cloth and wire, soaked)."""
    made = []
    if kind == "sleeve":
        made.append(geo.lathe([(radius + 0.022, 0.0), (radius + 0.022, length)], (x - length / 2.0, 0.0, z), paint("zinc", rust=0.3, seed=seed, gloss=0.6, metal=0.5),
                              16, name="sleeve", roll=90.0))
        for dx in (-length * 0.3, length * 0.3):
            made.append(geo.box((0.05, 0.06, 0.1), (x + dx, 0.0, z + radius + 0.01), 0.0, iron(0.6, seed), bevel=0.008, name="sleeve_lug"))
    else:
        cloth = mat.rubber(seed) if kind == "rubber" else sx.fabric((0.30, 0.27, 0.20), seed=seed)
        made.append(geo.lathe([(radius + 0.012, 0.0), (radius + 0.03, length * 0.3), (radius + 0.022, length * 0.6), (radius + 0.034, length * 0.8),
                               (radius + 0.012, length)], (x - length / 2.0, 0.0, z), cloth, 14, name="wrap", roll=90.0))
        for dx in (-length * 0.32, 0.0, length * 0.3):
            made.append(geo.lathe([(radius + 0.036, 0.0), (radius + 0.036, 0.025)], (x + dx, 0.0, z), mat.flat((0.06, 0.05, 0.04), metallic=0.4), 12,
                                  name="wrap_wire", roll=90.0))
    return no_block(made)


def handwheel(radius=0.27, colour="red", seed=0, spokes=4):
    """A valve wheel in the local XZ plane, centred on the origin, its face to the front."""
    material = paint(colour, rust=0.4, seed=seed, gloss=0.5, runs=0.0)
    rim = [(radius * math.cos(2.0 * math.pi * i / 16.0), 0.0, radius * math.sin(2.0 * math.pi * i / 16.0)) for i in range(18)]
    made = [geo.pipe(rim, 0.032, material, name="wheel_rim", resolution=6)]
    for k in range(spokes):
        a = math.pi * k / spokes + 0.4
        made.append(geo.pipe([(-radius * math.cos(a), 0.0, -radius * math.sin(a)), (radius * math.cos(a), 0.0, radius * math.sin(a))], 0.022, material,
                             name="wheel_spoke"))
    made.append(geo.cylinder(0.055, 0.06, (0.0, 0.03, 0.0), iron(0.5, seed), 10, name="wheel_hub", tilt=90.0))
    return no_block(made)


def valve(x, z=PIPE_Z, radius=PIPE_R, seed=0, colour="red", wheel="front", body="blue"):
    """A gate valve on a pipe along local X: a fat cast body between two flanges, a bonnet, a stem
    and the hand wheel - "front" (facing the viewer, on a stem that comes out of the body's front)
    or "top" (lying flat over the bonnet)."""
    cast = paint(body, rust=0.5, seed=seed, gloss=0.4)
    made = [geo.lathe([(radius * 1.05, 0.0), (radius * 1.45, 0.06), (radius * 1.45, 0.3), (radius * 1.05, 0.36)], (x - 0.18, 0.0, z), cast, 14, name="valve_body",
                      roll=90.0)]
    made += flange(x - 0.22, z, radius, seed)
    made += flange(x + 0.22, z, radius, seed + 1)
    if wheel == "top":
        made.append(geo.lathe([(radius * 0.9, 0.0), (radius * 0.6, 0.22), (radius * 0.6, 0.34), (0.0, 0.34)], (x, 0.0, z + radius), cast, 12, name="bonnet"))
        made.append(geo.cylinder(0.03, 0.26, (x, 0.0, z + radius + 0.3), chrome(0.5), 8, name="stem"))
        made += put(handwheel(0.27, colour, seed), (x, 0.0, z + radius + 0.52), tilt=90.0)
    else:
        made.append(geo.lathe([(radius * 0.9, 0.0), (radius * 0.6, 0.2), (radius * 0.6, 0.3), (0.0, 0.3)], (x, -radius, z), cast, 12, name="bonnet", tilt=90.0))
        made.append(geo.cylinder(0.03, 0.2, (x, -radius - 0.28, z), chrome(0.5), 8, name="stem", tilt=90.0))
        made += put(handwheel(0.27, colour, seed), (x, -radius - 0.46, z))
    return geo.set_block(made, geo.BLOCK_PROP)


def gauge(x, z=PIPE_Z, radius=PIPE_R, seed=0):
    """A pressure gauge on a stub above the pipe: one pale disc with a dark rim."""
    made = [geo.cylinder(0.022, 0.16, (x, 0.0, z + radius - 0.01), iron(0.4, seed), 8, name="gauge_stub")]
    made.append(sx.disc(0.10, (x, -0.03, z + radius + 0.2), 0.0, mat.flat((0.05, 0.05, 0.05), roughness=0.4, metallic=0.5), thickness=0.05, name="gauge_case"))
    made.append(sx.disc(0.078, (x, -0.062, z + radius + 0.2), 0.0, mat.flat((0.55, 0.53, 0.45), roughness=0.3), thickness=0.012, name="gauge_face"))
    return no_block(made)


def saddle(x, z=PIPE_Z, radius=PIPE_R, kind="blocks", seed=0):
    """What a ground run rests on at local x: "blocks" (cinder blocks and a timber wedge), "cradle"
    (a welded angle-iron X with a strap over the pipe), "tyre" (a tyre, the pipe in its dip),
    "sleeper" (a baulk of timber across, notched)."""
    made = []
    foot = z - radius
    if kind == "blocks":
        level = 0.0
        while level + 0.2 <= foot + 0.02:
            made += put(cinder(seed + int(level * 10)), (x, 0.0, level), rot=90.0 if int(level * 5) % 2 else 0.0)
            level += 0.2
        made.append(geo.box((0.34, 0.12, max(0.03, foot - level + 0.04)), (x + 0.02, 0.0, level - 0.01), 8.0, wood(seed=seed, grey=0.3), bevel=0.006, name="wedge"))
    elif kind == "cradle":
        steel = iron(0.75, seed)
        for side in (-1.0, 1.0):
            made.append(bx.beam((x, side * 0.36, 0.0), (x, -side * 0.12, z + radius * 0.6), (0.06, 0.06), steel, name="cradle_leg"))
        made.append(geo.lathe([(radius + 0.012, 0.0), (radius + 0.012, 0.07)], (x - 0.035, 0.0, z), steel, 14, name="cradle_strap", roll=90.0))
        made.append(geo.box((0.1, 0.8, 0.04), (x, 0.0, 0.0), 0.0, steel, bevel=0.004, name="cradle_foot"))
    elif kind == "tyre":
        made.append(geo.tire((x, 0.0, 0.0), 0.36, max(0.14, foot + 0.05), lying=True, seed=seed))
    else:
        made.append(geo.box((0.2, 0.9, foot + 0.05), (x, 0.0, 0.0), 0.0, wood((0.20, 0.12, 0.06), seed=seed, axis="Y", grey=0.3), bevel=0.012, name="sleeper"))
    return geo.set_block(made, geo.BLOCK_PROP)


def drip(x, z=PIPE_Z, radius=PIPE_R, seed=0, pool=0.42, wet=True, stream=True):
    """A leak at local x on a pipe along X: lime scale round the joint and down its side, a thread
    of water to the ground, a dark wet patch with a puddle in it."""
    r = geo.rng(seed)
    made = [geo.lathe([(radius + 0.008, 0.0), (radius + 0.014, 0.05), (radius + 0.008, 0.12)], (x - 0.06, 0.0, z), mat.flat(LIME, roughness=0.9), 14,
                      name="scale", roll=90.0)]
    f = Frame((x, -radius - 0.004, 0.0), 0.0)
    for k in range(3):
        made.append(streak(f, r.uniform(-0.08, 0.08), z + radius * 0.3, r.uniform(0.2, 0.34), 0.07, d=0.0, colour=LIME))
    if stream:
        made.append(geo.box((0.03, 0.03, z - radius), (x + 0.02, -0.03, 0.0), 0.0, mat.flat((0.34, 0.40, 0.40), roughness=0.15), bevel=0.0, name="water_thread"))
    if wet:
        made.append(stain((x, -0.1), pool, (0.045, 0.035, 0.025), seed=seed, gloss=0.2))
        made.append(stain((x + 0.03, -0.12), pool * 0.5, (0.02, 0.03, 0.03), seed=seed + 1, gloss=0.9))
        made[-1].location.z = 0.002
    return no_block(made)


def pipe_run(length, colour="oxide", seed=0, z=PIPE_Z, radius=PIPE_R, joints=(), ends=(True, True), sections=None, x0=0.0):
    """A straight pipe along local X from x0 to x0 + length at height z.
    joints   local x of flange pairs along it;  ends  flanges at the two ends
    sections [(x_from, x_to, colour), ...] lengths repainted (pipe bought in pieces never matches)"""
    made = []
    cuts = [(x0, x0 + length, colour)] if not sections else sections
    if sections:
        covered = sorted(sections)
        last = x0
        plain = []
        for a, b, _ in covered:
            if a > last + 1e-3:
                plain.append((last, a, colour))
            last = b
        if last < x0 + length - 1e-3:
            plain.append((last, x0 + length, colour))
        cuts = plain + list(sections)
    for k, (a, b, c) in enumerate(cuts):
        made.append(rod((a, 0.0, z), (b, 0.0, z), radius, pipe_paint(c, seed + k), name="pipe"))
    for k, x in enumerate(joints):
        made += flange(x, z, radius, seed + k)
    if ends[0]:
        made += flange(x0 + 0.06, z, radius, seed + 7)
    if ends[1]:
        made += flange(x0 + length - 0.02, z, radius, seed + 8)
    return made


def bend(points, radius=PIPE_R, colour="oxide", seed=0, steps=6, corner=0.34):
    """A pipe through world points with rounded corners (an elbow is three points)."""
    path = [Vector(points[0])]
    for i in range(1, len(points) - 1):
        p, a, b = Vector(points[i]), Vector(points[i - 1]), Vector(points[i + 1])
        ca = p + (a - p).normalized() * min(corner, (a - p).length * 0.5)
        cb = p + (b - p).normalized() * min(corner, (b - p).length * 0.5)
        for k in range(steps + 1):
            t = k / steps
            path.append(ca.lerp(p, t).lerp(p.lerp(cb, t), t))
    path.append(Vector(points[-1]))
    return geo.pipe([tuple(v) for v in path], radius, pipe_paint(colour, seed), name="bend", resolution=12)


# ========================================================================== structure
def post(at=(0.0, 0.0, 0.0), height=2.4, kind="timber", seed=0, lean=(0.0, 0.0), foot="none", size=0.11):
    """A post standing on `at` (stand it on a hex centre). kind: "timber" (a squared baulk),
    "pole" (a peeled trunk), "pipe" (scaffold tube), "angle" (rusty angle iron).
    foot: "none" (sunk in the dirt), "tyre" (a tyre full of concrete), "stones", "drum" (set in half a drum)."""
    x, y, z = at[0], at[1], at[2] if len(at) > 2 else 0.0
    top = (x + lean[0], y + lean[1], z + height)
    made = []
    if kind == "timber":
        made.append(bx.beam((x, y, z), top, (size, size), wood((0.21, 0.13, 0.07), seed=seed, axis="X", width=0.5, grey=0.45), name="post"))
    elif kind == "pole":
        made.append(rod((x, y, z), top, size * 0.6, wood((0.24, 0.16, 0.09), seed=seed, axis="Z", width=0.8, grey=0.55), 10, name="post"))
    elif kind == "pipe":
        made.append(rod((x, y, z), top, 0.045, mat.steel(rust=0.7, seed=seed), 10, name="post"))
    else:
        made.append(bx.beam((x, y, z), top, (0.07, 0.07), iron(0.85, seed), name="post"))
    if foot == "tyre":
        made.append(geo.tire((x, y, z), 0.34, 0.2, lying=True, seed=seed))
        made.append(geo.cylinder(0.2, 0.19, (x, y, z), mat.concrete(seed=seed), 12, name="foot"))
    elif foot == "stones":
        r = geo.rng(seed + 9)
        for k in range(4):
            a = k * 1.7 + r.uniform(0, 0.5)
            made.append(geo.box((r.uniform(0.16, 0.24), r.uniform(0.14, 0.2), r.uniform(0.1, 0.16)), (x + 0.16 * math.cos(a), y + 0.16 * math.sin(a), z), r.uniform(0, 90),
                                mat.concrete((0.24, 0.22, 0.19), cracks=0.1, seed=seed + k), bevel=0.04, name="stone"))
    elif foot == "drum":
        made += put(drum("oxide", seed, height=0.42, open_top=True, dents=0), (x, y, z))
        made.append(geo.cylinder(0.26, 0.02, (x, y, z + 0.36), mat.concrete(seed=seed), 12, name="foot"))
    return geo.set_block(made, geo.BLOCK_PROP)


def lash(at, radius=0.07, height=0.1, colour=(0.20, 0.15, 0.08), axis="z"):
    """A lashing (rope or wire wound round a joint): what holds two poles together here."""
    roll = {"z": 0.0, "x": 90.0}.get(axis, 0.0)
    tilt = 90.0 if axis == "y" else 0.0
    a = at if axis == "z" else ((at[0] - height / 2.0, at[1], at[2]) if axis == "x" else (at[0], at[1] + height / 2.0, at[2]))
    obj = geo.lathe([(radius, 0.0), (radius + 0.012, height * 0.3), (radius + 0.004, height * 0.6), (radius + 0.012, height * 0.8), (radius, height)],
                    (a[0], a[1], a[2] - (height / 2.0 if axis == "z" else 0.0)), mat.flat(colour, roughness=0.95), 10, name="lashing", roll=roll, tilt=tilt)
    return geo.set_block(obj, 0)


def rail(a, b, kind="board", seed=0, width=0.14):
    """A fence rail / tie between two world points: "board", "pole" (round timber), "pipe"."""
    if kind == "board":
        return bx.plank(a, b, width, 0.03, wood(seed=seed, axis="X", grey=0.4), seed=seed, roll=90.0, name="rail")
    if kind == "pole":
        return rod(a, b, 0.04, wood((0.24, 0.16, 0.09), seed=seed, axis="Z", width=0.8, grey=0.5), 8, name="rail")
    return rod(a, b, 0.035, mat.steel(rust=0.75, seed=seed), 8, name="rail")


def tin_sheet(width, length, at, rot=0.0, slope=8.0, colour=None, seed=0, rust=0.55, wavelength=0.13, roll=0.0):
    """One roofing sheet: hinged at `at` (its upper left corner as you face it), falling `slope`
    degrees to the front over `length` metres, `width` wide along local X."""
    return geo.set_block(geo.corrugated_panel(width, length, at, rot, tin(colour, rust=rust, seed=seed, top=length), wavelength=wavelength, depth=0.035,
                                              tilt=90.0 + slope, roll=roll, name="tin_sheet"), 0)


def awning(corners, kind="tarp", colour=(0.30, 0.25, 0.15), stripes=None, seed=0, sag=0.14):
    """A cover slung between four world points (back-left, back-right, front-right, front-left as
    you face it): "tarp" (one canvas, bellied), "patch" (three cloths lashed edge to edge)."""
    if kind == "tarp":
        return [sx.sag_sheet(corners, canvas(colour, stripes, seed), sag=sag, seed=seed, rows=8, columns=10)]
    a, b, c, d = (Vector(p) for p in corners)
    cloths = [canvas(colour, stripes, seed), canvas((0.22, 0.20, 0.13), None, seed + 1), canvas(colour if stripes else (0.34, 0.16, 0.08), None, seed + 2)]
    made = []
    for k in range(3):
        t0, t1 = k / 3.0, (k + 1) / 3.0 + 0.02
        made.append(sx.sag_sheet([tuple(a.lerp(b, t0)), tuple(a.lerp(b, min(1.0, t1))), tuple(d.lerp(c, min(1.0, t1)) + Vector((0, 0, 0.02 * (k % 2)))),
                                  tuple(d.lerp(c, t0) + Vector((0, 0, 0.02 * (k % 2))))], cloths[k], sag=sag * (0.6 + 0.3 * k), seed=seed + k, rows=6, columns=5))
    return made


def hang(at, what="pot", seed=0, drop=0.25):
    """Something hanging on a wire from world point `at`: "pot", "pan", "lamp" (unlit storm lantern),
    "meat" (a dried iguana on a string), "hubcap", "bottle", "shoe" (a pair of boots by their laces)."""
    x, y, z = at
    made = [geo.pipe([(x, y, z), (x, y, z - drop)], 0.012, mat.flat((0.05, 0.045, 0.04)), name="hang_wire")]
    low = z - drop
    if what == "pot":
        made.append(geo.lathe([(0.0, 0.0), (0.12, 0.0), (0.14, 0.14), (0.15, 0.15), (0.12, 0.15), (0.11, 0.02), (0.0, 0.02)], (x, y, low - 0.15), iron(0.4, seed), 12,
                              name="pot"))
    elif what == "pan":
        made.append(sx.disc(0.14, (x, y, low - 0.14), geo.SCREEN, iron(0.5, seed), thickness=0.03, name="pan"))
    elif what == "lamp":
        made += sx.lantern((x, y, low + 0.04), size=0.9, lit=False)
    elif what == "meat":
        made.append(geo.box((0.09, 0.05, 0.3), (x, y, low - 0.3), geo.SCREEN, mat.flat((0.20, 0.08, 0.05), roughness=0.7), bevel=0.03, name="meat"))
    elif what == "hubcap":
        made.append(sx.disc(0.17, (x, y, low - 0.17), geo.SCREEN, chrome(0.35), thickness=0.03, dome=0.04, name="hubcap"))
    elif what == "bottle":
        made.append(geo.lathe([(0.04, 0.0), (0.045, 0.14), (0.018, 0.2), (0.018, 0.25), (0.0, 0.25)], (x, y, low - 0.25), mat.flat((0.05, 0.14, 0.05), roughness=0.12), 8,
                              name="bottle"))
    else:
        for dx in (-0.05, 0.06):
            made.append(geo.box((0.09, 0.2, 0.1), (x + dx, y, low - 0.12), 25.0 + dx * 300.0, mat.flat((0.06, 0.04, 0.03), roughness=0.7), bevel=0.03, name="boot"))
    return no_block(made)


def produce(seed=0, size=(0.5, 0.36), kind="fruit"):
    """A tray of goods for a counter: "fruit" (orange and green balls), "roots" (brown lumps),
    "tins" (stacked cans), "parts" (cogs, a coil of wire, bolts)."""
    r = geo.rng(seed)
    w, d = size
    made = [geo.box((w, d, 0.09), (0, 0, 0), 0.0, wood((0.24, 0.15, 0.07), seed=seed, grey=0.35), bevel=0.006, name="tray")]
    made.append(geo.box((w - 0.05, d - 0.05, 0.01), (0, 0, 0.085), 0.0, dark(0.03), bevel=0.0, name="tray_dark"))
    if kind in ("fruit", "roots"):
        colours = ((0.50, 0.20, 0.03), (0.16, 0.26, 0.06), (0.45, 0.33, 0.05)) if kind == "fruit" else ((0.18, 0.11, 0.06), (0.26, 0.18, 0.09))
        nx, ny = max(2, int(w / 0.12)), max(2, int(d / 0.12))
        for i in range(nx):
            for j in range(ny):
                if r.random() < 0.15:
                    continue
                made.append(sx.sphere(0.055 * r.uniform(0.85, 1.15), (-w / 2.0 + 0.07 + (w - 0.14) * i / max(1, nx - 1), -d / 2.0 + 0.07 + (d - 0.14) * j / max(1, ny - 1), 0.12),
                                      mat.flat(colours[r.randrange(len(colours))], roughness=0.5), name="fruit", squash=0.9 if kind == "fruit" else 0.7))
    elif kind == "tins":
        for i in range(max(2, int(w / 0.13))):
            for level in range(2 if i % 2 == 0 else 1):
                made.append(geo.cylinder(0.05, 0.12, (-w / 2.0 + 0.08 + i * 0.125, r.uniform(-0.05, 0.05), 0.09 + level * 0.12),
                                         paint(("red", "zinc", "yellow", "cream")[r.randrange(4)], rust=0.3, seed=seed + i, gloss=0.6, metal=0.3), 10, name="tin_can"))
    else:
        made.append(sx.disc(0.11, (-w * 0.22, 0.0, 0.1), 0.0, iron(0.6, seed), thickness=0.04, hole=0.04, tilt=-90.0, name="cog"))
        made.append(geo.lathe([(0.05, 0.0), (0.1, 0.0), (0.1, 0.08), (0.05, 0.08)], (w * 0.2, 0.02, 0.09), mat.flat((0.42, 0.20, 0.06), roughness=0.4, metallic=0.6), 12, name="wire_coil"))
        made.append(geo.box((0.16, 0.05, 0.04), (0.0, -d * 0.2, 0.09), 30.0, chrome(0.4), bevel=0.01, name="spanner"))
    return no_block(made)
