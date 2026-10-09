# SPDX-License-Identifier: MIT
"""Extra kit of the "height" author (pieces/height_*.py): what Megaton is piled up from.

    from kit import height_extra as H

Everything here is built on a FACE (signs_extra.Frame): `f = H.face(origin, rot)`, then
    f.at(u, d, z)      u metres along the face to the screen right, d metres OUT of it towards the
                       viewer, z up. rot = geo.U: a face along a hex row (u = -X, d = +Y);
                       rot = geo.V: a face along a hex column (u = +Y, d = +X).

WEAR    The surfaces are the point of this kit (last round's art was judged too clean):
        worn()          sheet metal that knows its own size: rust eats in from the edges and the foot,
                        streaks run down from every fixing, paint survives in the middle in hard-edged
                        patches, soot sits where sheets overlap. Shapes of 10 cm and more, no fine noise.
        sheet()         one sheet with that material ("v" / "h" corrugated, "p" dented flat plate) and
                        a row of bolt heads the streaks start from
        scrap_wall()    a wall of mismatched sheets, planks and plates in one or two tiers, battens
                        and patches riveted over the joints
        streak()        one long rust / soot run as a decal, for places the material cannot know
STRUCTURE  post(), brace(), xbrace(), deck(), rail(), stairs(), lean_roof(), tank(), door(), window(),
        junk(): everything is propped, strapped or hung from something; nothing floats.
HEXES   hexes_in(x0, y0, x1, y1) / row(dhx0, dhx1, dhy): footprints from world rectangles, so the
        blocked hexes of a piece are written down as geometry, not counted by hand.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from pipeline import proj as G
from . import geo, mat
from . import bomb_extra as bx
from . import gate_extra as X
from . import signs_extra as sx
from .nodes import Graph

HEX = G.SQ_U_M / 2.0            # 0.6928 m between neighbouring hexes of a row
ROW = G.SQ_V_M / 2.0            # 0.8 m between hex rows (along +Y)
GRADE = {"contrast": 1.3, "saturation": 1.05, "forbid": ["purple", "rose"]}

RED = (0.30, 0.085, 0.045)
TEAL = (0.07, 0.19, 0.20)
CREAM = (0.36, 0.30, 0.18)
OCHRE = (0.40, 0.26, 0.045)
GREEN = (0.12, 0.17, 0.08)
SLATE = (0.17, 0.20, 0.23)
WHITE = (0.46, 0.44, 0.38)
PAINTS = (RED, TEAL, CREAM, OCHRE, GREEN, SLATE)
WOODS = ((0.40, 0.22, 0.10), (0.31, 0.18, 0.085), (0.46, 0.30, 0.14), (0.22, 0.14, 0.08), (0.40, 0.33, 0.23))
BOLT_STEP = 0.22                # bolts and the streaks under them share this grid


def face(origin=(0.0, 0.0, 0.0), rot=geo.U):
    return sx.Frame(origin, rot)


# ------------------------------------------------------------------------- hexes
def hex_xy(dhx, dhy):
    return G.hex_xy(dhx, dhy)


def hexes_in(x0, y0, x1, y1, pad=0.0):
    """Every hex whose centre lies in the world rectangle (metres), grown by `pad`."""
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    found = []
    for dhy in range(int(math.floor(y0 / ROW)) - 2, int(math.ceil(y1 / ROW)) + 3):
        for dhx in range(int(math.floor(x0 / HEX)) - 2, int(math.ceil(x1 / HEX)) + 3):
            x, y = G.hex_xy(dhx, dhy)
            if x0 - pad - 1e-6 <= x <= x1 + pad + 1e-6 and y0 - pad - 1e-6 <= y <= y1 + pad + 1e-6:
                found.append((dhx, dhy))
    return found


def row(dhx0, dhx1, dhy=0):
    lo, hi = sorted((dhx0, dhx1))
    return [(dhx, dhy) for dhx in range(lo, hi + 1)]


def column(dhy0, dhy1, dhx=0):
    lo, hi = sorted((dhy0, dhy1))
    return [(dhx, dhy) for dhy in range(lo, hi + 1)]


def uniq(hexes):
    seen, out = set(), []
    for h in hexes:
        h = (int(h[0]), int(h[1]))
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


# --------------------------------------------------------------------- materials
def worn(w, h, paint=None, rust=0.5, seed=0.0, base=mat.GALVANISED, streak=0.6, metallic=0.5, fix=0.06, gain=1.0):
    """Sheet metal of size w x h (object space: x 0..w along, z 0..h up, any thickness in y).
    paint: what is left of its paint, or None for bare zinc. rust 0..1. streak 0..1: share of the
    fixings (one every BOLT_STEP along the top, `fix` below the edge) that have bled a rust run.
    gain: brightness of the whole surface. Upright faces get 1.45 (sheet() does it): they take half
    the sun a roof takes and came out near black beside the stock walls at 1.0."""
    w, h = round(float(w), 2), round(float(h), 2)
    paint = tuple(paint) if paint is not None else None

    def build():
        g = Graph("ht_worn")
        x, y, z = g.separate(g.coords())
        p = g.combine(g.add(x, seed * 7.31), g.add(y, seed * 3.17), g.add(z, seed * 5.53))
        tone = g.noise(p, scale=1.3, detail=2.0)
        colour = g.mix(g.remap(tone, 0.35, 0.65), tuple(c * 0.66 for c in base), tuple(min(1.0, c * 1.12) for c in base))
        side = g.minimum(x, g.sub(w, x))
        edge = g.minimum(side, g.sub(h, z))                       # distance to the left / right / top edge
        wob = g.noise(p, scale=4.5, detail=2.0, roughness=0.5)
        if paint is not None:
            chips = g.noise(p, scale=2.4, detail=3.0, roughness=0.6, distortion=0.6)
            keep = g.add(chips, g.mul(g.smooth(g.minimum(edge, z), 0.0, 0.3), 0.24))
            painted = g.smooth(keep, 0.50, 0.535)                 # hard edge: paint chips, it does not fade
            faded = g.mix(g.remap(tone, 0.3, 0.7), paint, tuple(min(1.0, c * 1.35 + 0.02) for c in paint))
            colour = g.mix(painted, colour, faded)
        band = g.mul(g.remap(wob, 0.25, 0.75, 0.25, 1.0), 0.04 + 0.16 * rust)
        edge_rust = g.smooth(edge, band, g.mul(band, 0.55))
        foot = g.mul(g.remap(wob, 0.25, 0.75, 0.35, 1.0), 0.10 + 0.50 * rust)
        foot_rust = g.smooth(z, foot, g.mul(foot, 0.6))
        level = 0.76 - 0.24 * rust
        blotch = g.smooth(g.noise(p, scale=1.9, detail=3.0, roughness=0.55, distortion=0.7), level, level + 0.03)
        mask = g.maximum(g.maximum(edge_rust, foot_rust), blotch)
        rust_colour = g.ramp(g.noise(p, scale=4.0, detail=3.0, roughness=0.6),
                             [(0.28, mat.RUST_DARK), (0.5, mat.RUST_MID), (0.76, mat.RUST_LIGHT)])
        colour = g.mix(mask, colour, rust_colour)
        if streak > 0.0:
            cx = g.div(x, BOLT_STEP)
            index = g.floor(cx)
            r1 = g.white_noise(g.combine(index, seed + 0.5, 1.0))
            r2 = g.white_noise(g.combine(index, seed + 0.5, 2.0))
            off = g.absolute(g.sub(g.fract(cx), 0.5))
            length = g.mul(g.add(0.25, g.mul(r2, 0.75)), max(0.25, min(h, 1.7) * 0.9))
            t = g.div(g.sub(h - fix, z), length)                   # 0 at the fixing, 1 where the run ends
            alive = g.mul(g.greater(t, 0.0), g.less(t, 1.0))
            core = g.smooth(off, 0.26, 0.11)
            fade = g.sub(1.0, g.mul(t, t))
            run = g.mul(g.mul(g.mul(g.greater(r1, 1.0 - streak), alive), core), fade)
            colour = g.mix(g.mul(run, 0.92), colour, g.mix(r2, mat.RUST_DARK, mat.RUST_MID))
            mask = g.maximum(mask, run)
        if gain != 1.0:
            colour = g.hsv(colour, value=gain)
        colour = g.mix(g.mul(g.smooth(g.ao(0.12), 0.75, 0.25), 0.6), colour, mat.SOOT)
        colour = mat._ground_dirt(g, colour, height=0.45, amount=0.6)
        g.principled(base=colour, roughness=g.mix_value(mask, 0.55, 0.95), metallic=g.mix_value(mask, metallic * (0.5 if gain > 1.0 else 1.0), 0.0),
                     specular=g.mix_value(mask, 0.35, 0.06), bump=g.bump(mask, 0.004, strength=0.6))
        return g.material
    return mat._cached(("ht_worn", w, h, paint, round(rust, 2), seed, tuple(base), streak, metallic, fix, gain), build)


def drum_paint(colour=SLATE, rust=0.5, rings=(), seed=0.0, top=None):
    """Paint for round things (tanks, drums, pipes): chipped in hard patches, and under every ring
    height in `rings` (object z, metres) and under `top` a fringe of rust runs."""
    rings = tuple(float(r) for r in rings) + ((float(top),) if top is not None else ())

    def build():
        g = Graph("ht_drum")
        x, y, z = g.separate(g.coords())
        p = g.combine(g.add(x, seed * 7.3), g.add(y, seed * 3.1), g.add(z, seed * 5.5))
        tone = g.noise(p, scale=1.5, detail=2.0)
        base = g.mix(g.remap(tone, 0.3, 0.7), tuple(c * 0.7 for c in colour), tuple(min(1.0, c * 1.3 + 0.02) for c in colour))
        chips = g.noise(p, scale=2.6, detail=3.0, roughness=0.6, distortion=0.6)
        level = 0.74 - 0.24 * rust
        mask = g.smooth(chips, level, level + 0.03)
        columns = g.noise(g.combine(g.mul(x, 9.0), g.mul(y, 9.0), seed), scale=1.0, detail=1.0)   # constant down a line
        for ring in rings:
            below = g.sub(ring, z)
            length = g.mul(g.remap(columns, 0.3, 0.7, 0.05, 0.9), 0.75)
            t = g.div(below, length)
            run = g.mul(g.mul(g.greater(below, 0.0), g.less(t, 1.0)), g.sub(1.0, g.mul(t, t)))
            mask = g.maximum(mask, g.mul(run, g.smooth(columns, 0.44, 0.52)))
        rust_colour = g.ramp(g.noise(p, scale=4.0, detail=3.0, roughness=0.6),
                             [(0.28, mat.RUST_DARK), (0.5, mat.RUST_MID), (0.76, mat.RUST_LIGHT)])
        result = g.mix(mask, base, rust_colour)
        result = g.mix(g.smooth(g.ao(0.16), 0.8, 0.3), result, mat.SOOT)
        result = mat._ground_dirt(g, result, amount=0.5)
        g.principled(base=result, roughness=g.mix_value(mask, 0.55, 0.95), metallic=0.0, specular=g.mix_value(mask, 0.3, 0.06),
                     bump=g.bump(mask, 0.004, strength=0.6))
        return g.material
    return mat._cached(("ht_drum", tuple(colour), round(rust, 2), rings, seed), build)


def streak_mat(colour=mat.RUST_DARK, length=0.6):
    """For streak(): opaque at the top of the decal, gone at its foot, frayed at the sides."""
    def build():
        g = Graph("ht_streak")
        x, y, z = g.separate(g.coords())
        t = g.div(g.sub(0.0, z), length)
        wobble = g.noise(g.combine(g.mul(x, 30.0), 0.0, g.mul(z, 3.0)), scale=1.0, detail=1.0)
        alpha = g.mul(g.sub(1.0, g.mul(t, t)), g.remap(wobble, 0.3, 0.7, 0.55, 1.0))
        g.principled(base=colour, roughness=0.95, specular=0.03, alpha=g.smooth(alpha, 0.25, 0.6))
        return g.material
    return mat._cached(("ht_streak", tuple(colour), round(length, 2)), build)


def wood(i=0, axis="Z", width=0.18, grey=0.38, gain=1.0):
    colour = tuple(min(0.8, c * gain) for c in WOODS[i % len(WOODS)])
    return mat.planks(colour, width=width, axis=axis, grey=grey, seed=float(i))


def tube(rust=0.7, seed=3.0):
    return mat.steel(rust=rust, seed=seed)


def dark():
    return mat.flat((0.012, 0.011, 0.010), roughness=0.9)


def cloth(colour=(0.30, 0.25, 0.16), seed=0.0):
    return mat.tarp(colour, seed=seed)


# ------------------------------------------------------------------ small meshes
def _matrix(at, rot=0.0, tilt=0.0, roll=0.0):
    return (Matrix.Translation(Vector(at)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
            @ Matrix.Rotation(math.radians(tilt), 4, "X") @ Matrix.Rotation(math.radians(roll), 4, "Y"))


def dots(points, size=0.05, material=None, layer="main", name="bolts"):
    """Bolt heads / nail heads / rivets at world points, as ONE mesh (2 px each: they read as fixings)."""
    if not points:
        return None
    bm = bmesh.new()
    for point in points:
        made = bmesh.ops.create_cube(bm, size=size)
        bmesh.ops.translate(bm, vec=Vector(point), verts=made["verts"])
    obj = geo._finish(bm, name, material or mat.flat((0.035, 0.03, 0.026), roughness=0.5, metallic=0.4), (0, 0, 0), 0.0, layer,
                      smooth=False)
    return geo.set_block(obj, 0.0)


def panel(w, h, at, rot=geo.U, material=None, dent=0.012, seed=0, tilt=0.0, roll=0.0, thickness=0.016, layer="main",
          name="plate"):
    """A flat plate x 0..w, z 0..h, knocked about: a few soft dents `dent` metres deep."""
    r = geo.rng(seed)
    nx, nz = max(2, int(w / 0.12)), max(2, int(h / 0.12))
    bumps = [(r.uniform(0, w), r.uniform(0, h), r.uniform(0.15, 0.35), r.uniform(-1.0, 1.0)) for _ in range(3)]
    bm = bmesh.new()
    grid = []
    for i in range(nx + 1):
        column_ = []
        for k in range(nz + 1):
            x, z = w * i / nx, h * k / nz
            y = 0.0
            for bx_, bz_, radius, depth in bumps:
                q = math.hypot(x - bx_, z - bz_) / radius
                if q < 1.0:
                    y += dent * depth * (1.0 - q * q) ** 2
            column_.append(bm.verts.new((x, y, z)))
        grid.append(column_)
    for i in range(nx):
        for k in range(nz):
            bm.faces.new((grid[i][k], grid[i + 1][k], grid[i + 1][k + 1], grid[i][k + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return geo._finish(bm, name, material, at, rot, layer, tilt, roll, smooth=True, solidify=thickness)


def streak(f, u, z, length=0.6, width=0.07, d=0.022, colour=mat.RUST_DARK, layer="main"):
    """A run of rust (or soot) down a face from (u, z): a decal that fades out at its foot."""
    bm = bmesh.new()
    quad = [bm.verts.new(co) for co in ((-width / 2, 0, 0), (width / 2, 0, 0), (width * 0.3, 0, -length), (-width * 0.3, 0, -length))]
    bm.faces.new(quad)
    obj = geo._finish(bm, "streak", streak_mat(colour, length), f.at(u, d, z), f.rot, layer, smooth=False)
    return geo.set_block(obj, 0.0)


# ------------------------------------------------------------------------ sheets
def sheet(f, u, z, w, h, d=0.0, kind="v", paint=None, rust=0.5, seed=0, tilt=0.0, roll=0.0, bolts=True, streaks=0.6,
          layer="main", base=mat.GALVANISED, gain=1.45):
    """One sheet on face f, its lower left corner on (u, z): kind "v" / "h" corrugated (ridges up /
    along), "p" flat plate. Bolt heads along the top; the material lets rust run from them."""
    material = worn(w, h, paint, rust, float(seed), base=base, streak=streaks, metallic=0.5 if kind != "p" else 0.25, gain=gain)
    at = f.at(u, d, z)
    if kind == "p":
        obj = panel(w, h, at, f.rot, material, seed=seed, tilt=tilt, roll=roll, layer=layer)
        proud = 0.03
    else:
        obj = geo.corrugated_panel(w, h, at, f.rot, material, wavelength=0.11, depth=0.035, tilt=tilt, roll=roll, layer=layer,
                                   horizontal=(kind == "h"))
        proud = 0.04
    if bolts:
        m = _matrix(at, f.rot, tilt, roll)
        count = int(w / BOLT_STEP)
        dots([tuple(m @ Vector(((i + 0.5) * BOLT_STEP, -proud, h - 0.06))) for i in range(count)], 0.045, layer=layer)
    return obj


def patch(f, u, z, w, h, d=0.05, paint=None, rust=0.6, seed=0, kind="p", roll=0.0, layer="main"):
    """A small plate riveted over something: bolts in its corners, a rust run under it."""
    obj = sheet(f, u, z, w, h, d, kind, paint, rust, seed, roll=roll, bolts=False, streaks=0.0, layer=layer)
    m = _matrix(f.at(u, d, z), f.rot, 0.0, roll)
    inset = 0.06
    dots([tuple(m @ Vector((x, -0.035, zz))) for x in (inset, w - inset) for zz in (inset, h - inset)], 0.045, layer=layer)
    r = geo.rng(seed + 77)
    for k in range(2):
        streak(f, u + w * r.uniform(0.15, 0.85), z + 0.02, r.uniform(0.25, 0.6), 0.06, d=d + 0.03, layer=layer)
    return obj


def boards(f, u0, u1, z0, z1, d=0.0, seed=0, board=0.17, ragged=0.12, colours=(0, 1, 2), lean=1.2, horizontal=False,
           gap=0.012, missing=0.0, layer="main"):
    """Planks nailed up one by one between u0..u1, z0..z1 (upright, or lying with horizontal=True):
    mixed woods, ragged ends, a nail-rust dot at each end."""
    r = geo.rng(seed)
    objects, nails = [], []
    span, rise = (z1 - z0, u1 - u0) if horizontal else (u1 - u0, z1 - z0)
    count = max(1, int(round(span / (board + gap))))
    step = span / count
    for i in range(count):
        if missing and r.random() < missing:
            continue
        length = rise - r.uniform(0.0, ragged)
        shift = r.uniform(0.0, ragged * 0.5)
        material = wood(colours[r.randrange(len(colours))], axis="X" if horizontal else "Z", width=0.5, gain=1.4)
        if horizontal:
            at = f.at(u0 + shift + length / 2.0, d, z0 + step * i)
            objects.append(geo.box((length, 0.03, step - gap), at, f.rot, material, bevel=0.005, layer=layer, name="board",
                                   roll=r.uniform(-lean, lean)))
            nails += [f.at(u0 + shift + 0.07, d + 0.02, z0 + step * (i + 0.5)), f.at(u0 + shift + length - 0.07, d + 0.02, z0 + step * (i + 0.5))]
        else:
            at = f.at(u0 + step * (i + 0.5), d, z0 + shift)
            objects.append(geo.box((step - gap, 0.03, length), at, f.rot, material, bevel=0.005, layer=layer, name="board",
                                   roll=r.uniform(-lean, lean)))
            nails += [f.at(u0 + step * (i + 0.5), d + 0.02, z0 + shift + length - 0.09)]
    dots(nails, 0.035, mat.flat((0.06, 0.03, 0.015), roughness=0.9), layer)
    return objects


def batten(f, u0, u1, z, d=0.05, size=0.09, colour=1, roll=0.0, layer="main", steel=False):
    """A timber (or angle iron) nailed along a face from u0 to u1 at height z."""
    material = tube(0.8, 5.0) if steel else wood(colour, axis="X", width=0.5)
    a, b = Vector(f.at(u0, d, z)), Vector(f.at(u1, d, z + roll))
    return bx.beam(tuple(a), tuple(b), (size, 0.045), material, layer=layer, name="batten")


def door(f, u, z, w=0.85, h=1.95, d=0.03, kind="plank", seed=0, paint=None, ajar=False, layer="main"):
    """A door ON a face (the wall behind it stays whole): a dark reveal, a leaf of planks or sheet,
    a frame of battens, a handle, a rust run under each hinge."""
    r = geo.rng(seed)
    geo.box((w + 0.04, 0.02, h + 0.02), f.at(u + w / 2.0, d, z), f.rot, dark(), bevel=0.0, layer=layer, name="door_reveal")
    leaf_w = w * (0.62 if ajar else 1.0) - 0.04
    if kind == "plank":
        boards(f, u + 0.02, u + 0.02 + leaf_w, z + 0.03, z + h - 0.02, d + 0.03, seed, board=0.19, ragged=0.03,
               colours=(seed % 5, (seed + 2) % 5), lean=0.4, layer=layer)
        for zz in (z + 0.3, z + h - 0.35):
            batten(f, u + 0.02, u + 0.02 + leaf_w, zz, d + 0.065, 0.1, colour=3, layer=layer)
    else:
        sheet(f, u + 0.02, z + 0.03, leaf_w, h - 0.05, d + 0.03, "p", paint or PAINTS[seed % len(PAINTS)], 0.55, seed, bolts=False,
              streaks=0.0, layer=layer)
        patch(f, u + 0.12, z + h * 0.55, leaf_w * 0.6, 0.32, d + 0.06, None, 0.7, seed + 3, layer=layer)
    frame = wood(3, axis="Z", width=0.5)
    for uu in (u - 0.04, u + w + 0.04):
        geo.box((0.09, 0.05, h + 0.08), f.at(uu, d + 0.03, z), f.rot, frame, bevel=0.006, layer=layer, name="jamb",
                roll=r.uniform(-1.0, 1.0))
    geo.box((w + 0.26, 0.06, 0.1), f.at(u + w / 2.0, d + 0.035, z + h + 0.03), f.rot, wood(1, axis="X", width=0.5), bevel=0.006,
            layer=layer, name="lintel", roll=r.uniform(-1.5, 1.5))
    dots([f.at(u + leaf_w - 0.1, d + 0.09, z + h * 0.48)], 0.07, X.bright_metal((0.42, 0.40, 0.36)), layer, "handle")
    for zz in (z + 0.35, z + h - 0.3):
        dots([f.at(u + 0.06, d + 0.09, zz)], 0.06, layer=layer, name="hinge")
        streak(f, u + 0.06, zz - 0.03, r.uniform(0.25, 0.45), 0.06, d + 0.085, layer=layer)


def window(f, u, z, w=0.7, h=0.6, d=0.03, kind="dark", seed=0, layer="main", strength=1.6):
    """A window ON a face. kind: "dark" (dirty glass), "lit" (a lamp burns inside: warm by day, and
    it keeps flickering at night - the pane is painted with the fire colours), "boarded", "shutter"."""
    r = geo.rng(seed)
    if kind == "lit":
        pane = geo.box((w, 0.02, h), f.at(u + w / 2.0, d, z), f.rot, mat.emitter((1.0, 0.50, 0.12), strength), bevel=0.0,
                       layer=layer, name="pane")
        geo.set_fx(pane, "fire")
        geo.box((w * 0.42, 0.02, h * 0.8), f.at(u + w * 0.24, d + 0.012, z + h * 0.2), f.rot, cloth((0.10, 0.07, 0.05), seed=float(seed)),
                bevel=0.0, layer=layer, name="rag")
    else:
        geo.box((w, 0.02, h), f.at(u + w / 2.0, d, z), f.rot, mat.glass(dirt=0.7) if kind == "dark" else dark(), bevel=0.0,
                layer=layer, name="pane")
    frame = wood(3, axis="X", width=0.5)
    geo.box((w + 0.16, 0.05, 0.08), f.at(u + w / 2.0, d + 0.02, z + h), f.rot, frame, bevel=0.005, layer=layer, name="head")
    geo.box((w + 0.22, 0.09, 0.07), f.at(u + w / 2.0, d + 0.04, z - 0.07), f.rot, frame, bevel=0.005, layer=layer, name="sill")
    for uu in (u - 0.04, u + w + 0.04):
        geo.box((0.08, 0.05, h + 0.02), f.at(uu, d + 0.02, z), f.rot, wood(3, axis="Z", width=0.5), bevel=0.005, layer=layer,
                name="jamb")
    if kind in ("dark", "lit"):
        geo.box((0.05, 0.035, h), f.at(u + w / 2.0, d + 0.015, z), f.rot, frame, bevel=0.0, layer=layer, name="mullion")
    if kind == "boarded":
        for k in range(3):
            zz = z + h * (0.18 + 0.3 * k)
            bx.beam(f.at(u - 0.1, d + 0.05, zz + r.uniform(-0.08, 0.08)), f.at(u + w + 0.1, d + 0.05, zz + r.uniform(-0.08, 0.08)),
                    (0.13, 0.03), wood(k, axis="X", width=0.5), layer=layer, name="board")
    if kind == "shutter":
        sheet(f, u - 0.02, z - 0.02, w * 0.55, h + 0.04, d + 0.04, "h", PAINTS[seed % len(PAINTS)], 0.6, seed, roll=r.uniform(-4, 4),
              bolts=False, streaks=0.3, layer=layer)
    streak(f, u + w * 0.2, z - 0.1, r.uniform(0.3, 0.6), 0.07, d + 0.05, colour=(0.03, 0.026, 0.022), layer=layer)
    streak(f, u + w * 0.85, z - 0.1, r.uniform(0.2, 0.45), 0.06, d + 0.05, layer=layer)


def scrap_wall(f, u0, u1, z0, z1, d=0.0, seed=1, kinds="vvhpw", paints=PAINTS, rust=0.5, ragged=0.18, tiers=None,
               patches=2, battens=True, layer="main", sheet_w=(0.6, 1.1), lean=1.6):
    """A wall face of mismatched scrap between u0..u1 and z0..z1: every sheet its own kind, size,
    paint and rust, lapped over its neighbour; taller than 2 m it is laid in two tiers, the upper
    lapping over the lower; patches are riveted across joints and a batten holds it together.
    kinds: letters to draw from - v / h corrugated, p plate, w planks."""
    r = geo.rng(seed)
    height = z1 - z0
    if tiers is None:
        tiers = 2 if height > 2.05 else 1
    joints = []
    split = z0 + height * r.uniform(0.48, 0.6) if tiers == 2 else z1
    for tier in range(tiers):
        lo, hi = (z0, split + 0.1) if tier == 0 else (split - 0.02, z1)
        if tiers == 1:
            hi = z1
        u = u0
        index = 0
        while u < u1 - 0.08:
            w = min(r.uniform(*sheet_w), u1 - u)
            if u1 - (u + w) < 0.3:
                w = u1 - u
            kind = kinds[r.randrange(len(kinds))]
            top = hi - (r.uniform(0.0, ragged) if tier == tiers - 1 else r.uniform(0.0, 0.06))
            depth = d + 0.02 * tier + (0.014 if index % 2 else 0.0)
            if kind == "w":
                boards(f, u, u + w, lo, top, depth, seed * 17 + index + tier * 5, colours=(index % 5, (index + 1) % 5, (index + 3) % 5),
                       layer=layer)
            else:
                paint = paints[r.randrange(len(paints))] if (paints and r.random() < 0.6) else None
                sheet(f, u - 0.03, lo + r.uniform(0.0, 0.03), w + 0.06, top - lo, depth, kind, paint,
                      min(1.0, max(0.1, rust + r.uniform(-0.25, 0.25))), seed * 13 + index + tier * 7,
                      roll=r.uniform(-lean, lean), tilt=r.uniform(-lean, lean) * 0.4, layer=layer)
            joints.append((u + w, lo, top))
            u += w
            index += 1
    for k in range(patches):
        if not joints:
            break
        ju, lo, top = joints[r.randrange(len(joints))]
        pw, ph = r.uniform(0.35, 0.6), r.uniform(0.3, 0.55)
        ju = min(max(u0 + 0.05, ju - pw / 2.0), u1 - pw - 0.05)
        patch(f, ju, lo + (top - lo) * r.uniform(0.2, 0.65), pw, ph, d + 0.07, paints[r.randrange(len(paints))] if paints else None,
              0.65, seed * 5 + k, kind="p" if k % 2 == 0 else "h", roll=r.uniform(-5, 5), layer=layer)
    if battens:
        if tiers == 2:
            batten(f, u0 - 0.04, u1 + 0.04, split + 0.03, d + 0.075, colour=seed % 5, roll=r.uniform(-0.04, 0.04), layer=layer)
        batten(f, u0 - 0.04, u1 + 0.04, z0 + 0.08, d + 0.06, 0.11, colour=3, layer=layer)
    return split


# --------------------------------------------------------------------- structure
def post(x, y, z0, z1, kind="tube", seed=0, layer="main", pad=True, lean=(0.0, 0.0)):
    """A prop from (x, y, z0) up to z1: "tube" (scaffold pole with clamps), "timber", "beam" (I-beam), "pole" (a trunk)."""
    if kind == "tube":
        geo.pipe([(x, y, z0), (x + lean[0], y + lean[1], z1)], 0.05, tube(0.7, 3.0 + seed % 3), layer, "post")
    elif kind == "timber":
        bx.beam((x, y, z0), (x + lean[0], y + lean[1], z1), (0.13, 0.13), wood(seed, axis="X", width=0.6, grey=0.4), layer=layer,
                name="post")
    elif kind == "beam":
        geo.ibeam(z1 - z0, (x, y, z0), geo.U, tube(0.75, 2.0 + seed % 3), vertical=True, height=0.15, width=0.12, layer=layer)
    else:
        geo.lathe([(0.09, 0.0), (0.075, (z1 - z0) * 0.5), (0.06, z1 - z0)], (x, y, z0), wood(3, axis="Z", width=0.6, grey=0.5),
                  10, layer=layer, name="post")
    if pad and z0 < 0.05:
        if seed % 2:
            geo.cylinder(0.17, 0.09, (x, y, z0), mat.concrete(seed=float(seed)), 10, layer=layer, name="pad")
        else:
            geo.box((0.3, 0.3, 0.07), (x, y, z0), 18.0 * seed, mat.concrete(seed=float(seed)), bevel=0.01, layer=layer, name="pad")


def brace(a, b, radius=0.03, material=None, layer="main"):
    return geo.set_block(geo.pipe([tuple(a), tuple(b)], radius, material or tube(0.75, 4.0), layer, "brace"), 0.0)


def xbrace(a, b, z0, z1, radius=0.028, layer="main", single=False):
    """Cross bracing between two posts standing on ground points a and b, from z0 to z1."""
    brace((a[0], a[1], z0), (b[0], b[1], z1), radius, layer=layer)
    if not single:
        brace((b[0], b[1], z0), (a[0], a[1], z1), radius, layer=layer)


def strap(points, width=0.06, material=None, layer="main"):
    """A steel strap / rope / cable through world points."""
    return geo.set_block(geo.pipe([tuple(p) for p in points], width / 2.0, material or mat.flat((0.05, 0.045, 0.04), roughness=0.6, metallic=0.4),
                                  layer, "strap"), 0.0)


def deck(x0, y0, x1, y1, z, along="x", seed=1, board=0.24, missing=0.06, plates=1, overhang=0.12, layer="main", joists=True,
         colours=(0, 1, 2, 4)):
    """A plank deck with its top on height z over the world rectangle: boards laid across (`along` =
    the axis the boards RUN along), ragged ends, a gap or two, a board replaced by a steel plate, and
    joists under it. Returns nothing; it never blocks (set the footprint yourself)."""
    r = geo.rng(seed)
    objects = []
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    across0, across1 = (y0, y1) if along == "x" else (x0, x1)
    run0, run1 = (x0, x1) if along == "x" else (y0, y1)
    count = max(1, int(round((across1 - across0) / board)))
    step = (across1 - across0) / count
    plate_at = {r.randrange(count) for _ in range(plates)} if count > 2 else set()
    for i in range(count):
        if r.random() < missing and i not in (0, count - 1):
            continue
        a = run0 - r.uniform(0.0, overhang)
        b = run1 + r.uniform(0.0, overhang)
        c = across0 + step * (i + 0.5)
        if i in plate_at:
            material = worn(b - a, step, PAINTS[r.randrange(len(PAINTS))], 0.6, float(seed + i), streak=0.0, metallic=0.3)
            size = (b - a, step - 0.01, 0.02) if along == "x" else (step - 0.01, b - a, 0.02)
        else:
            material = wood(colours[r.randrange(len(colours))], axis="X" if along == "x" else "Y", width=0.6, grey=0.45)
            size = (b - a, step - 0.02, 0.045) if along == "x" else (step - 0.02, b - a, 0.045)
        centre = ((a + b) / 2.0, c, z - size[2]) if along == "x" else (c, (a + b) / 2.0, z - size[2])
        objects.append(geo.box(size, centre, 0.0, material, bevel=0.006, layer=layer, name="deck_board",
                               roll=r.uniform(-1.2, 1.2) if along == "y" else 0.0, tilt=r.uniform(-1.2, 1.2) if along == "x" else 0.0))
    if joists:
        steel = tube(0.75, 6.0)
        if along == "x":            # boards run along x, so joists run along y under them
            n = max(2, int((x1 - x0) / 1.0) + 1)
            for k in range(n):
                x = x0 + 0.15 + (x1 - x0 - 0.3) * k / (n - 1)
                objects.append(bx.beam((x, y0 - 0.05, z - 0.11), (x, y1 + 0.05, z - 0.11), (0.08, 0.11), wood(3, axis="X", width=0.6),
                                       layer=layer, name="joist"))
        else:
            n = max(2, int((y1 - y0) / 1.0) + 1)
            for k in range(n):
                y = y0 + 0.15 + (y1 - y0 - 0.3) * k / (n - 1)
                objects.append(bx.beam((x0 - 0.05, y, z - 0.11), (x1 + 0.05, y, z - 0.11), (0.08, 0.11), wood(3, axis="X", width=0.6),
                                       layer=layer, name="joist"))
        del steel
    return geo.set_block(objects, 0.0)


def rail(a, b, z, height=0.95, kind="pipe", seed=0, posts=None, mid=True, infill=None, layer="main", sag=0.0):
    """A guard rail from ground point a to b standing on height z. kind "pipe" / "wood" / "rope".
    infill: None, "sheet" (a scrap sheet wired on), "mesh" (chain-link), "planks", "tarp"."""
    r = geo.rng(seed)
    a, b = Vector((a[0], a[1], z)), Vector((b[0], b[1], z))
    length = (b - a).length
    n = posts if posts is not None else max(2, int(round(length / 1.3)) + 1)
    steel = tube(0.7, 2.0 + seed % 4)
    timber = wood(seed, axis="X", width=0.6, grey=0.4)
    up = Vector((0, 0, height))
    for k in range(n):
        p = a.lerp(b, k / (n - 1))
        top = p + up + Vector((r.uniform(-0.03, 0.03), r.uniform(-0.03, 0.03), r.uniform(-0.05, 0.03)))
        if kind == "wood":
            bx.beam(tuple(p - Vector((0, 0, 0.12))), tuple(top), (0.08, 0.08), timber, layer=layer, name="rail_post")
        else:
            geo.pipe([tuple(p - Vector((0, 0, 0.12))), tuple(top)], 0.032, steel, layer, "rail_post")
    for level in ((1.0, 0.52) if mid else (1.0,)):
        p0, p1 = a + up * level, b + up * level
        if kind == "wood":
            bx.plank(tuple(p0), tuple(p1 + Vector((0, 0, r.uniform(-0.04, 0.04)))), 0.1, 0.035, timber, layer=layer, roll=90.0,
                     name="rail")
        elif kind == "rope":
            geo.cable(tuple(p0), tuple(p1), 0.08 + sag, 0.022, mat.flat((0.17, 0.13, 0.08), roughness=0.9), layer)
        else:
            geo.pipe([tuple(p0), tuple(p1)], 0.028, steel, layer, "rail")
    if infill:
        at, rot, _ = geo.span(tuple(a), tuple(b))
        fr = face((at[0], at[1], 0.0), rot)
        u0 = length * r.uniform(0.05, 0.2)
        w = min(length - u0 - 0.05, r.uniform(0.8, 1.3))
        if infill == "sheet":
            sheet(fr, u0, z + 0.05, w, height * 0.92, -0.04, "h" if seed % 2 else "v", PAINTS[seed % len(PAINTS)], 0.6, seed,
                  roll=r.uniform(-3, 3), streaks=0.5, layer=layer)
        elif infill == "planks":
            boards(fr, u0, u0 + w, z + 0.05, z + height * 0.95, -0.04, seed, colours=(seed % 5, (seed + 1) % 5), layer=layer)
        elif infill == "mesh":
            geo.set_block(geo.chainlink_panel(fr.at(0.0, 0.0, z + 0.02), fr.at(length, 0.0, z + 0.02), height=height * 0.95, post=0.02,
                                              layer=layer, top_rail=False), 0.0)
        elif infill == "tarp":
            sx.cloth(fr, u0, z + height, w, height * 0.85, cloth((0.12, 0.17, 0.22), seed=float(seed)), folds=2.0, depth=0.04,
                     seed=seed, layer=layer, d=0.05)


def stairs(foot, top, width=0.8, seed=0, rails=(True, True), layer="main", tread=0.26, steel=False):
    """A flight from world point `foot` (centre of the lowest tread, on the ground) up to `top` (centre
    of the landing edge): two stringers, treads (one missing, one a steel plate), hand rails."""
    r = geo.rng(seed)
    foot, top = Vector(foot), Vector(top)
    run = Vector((top.x - foot.x, top.y - foot.y, 0.0))
    side = Vector((-run.y, run.x, 0.0)).normalized() * (width / 2.0)
    rise = top.z - foot.z
    count = max(3, int(round(rise / 0.24)))
    timber = wood(1 + seed, axis="X", width=0.6, grey=0.4)
    stringer = tube(0.8, 7.0) if steel else wood(3, axis="X", width=0.6, grey=0.3)
    for sign in (-1.0, 1.0):
        bx.beam(tuple(foot + side * sign + Vector((0, 0, 0.02))), tuple(top + side * sign - Vector((0, 0, 0.1))), (0.2, 0.05),
                stringer, layer=layer, name="stringer", roll=90.0)
    gone = r.randrange(2, count - 1) if count > 5 else -1
    for i in range(1, count + 1):
        if i == gone:
            continue
        p = foot + run * ((i - 0.5) / count) + Vector((0, 0, rise * i / count))
        material = timber if i % 4 else worn(width, tread, None, 0.7, float(seed + i), streak=0.0)
        bx.plank(tuple(p - side * 1.04), tuple(p + side * 1.04), tread, 0.04, material, layer=layer, name="tread")
    steel_m = tube(0.7, 5.0)
    for sign, wanted in zip((-1.0, 1.0), rails):
        if not wanted:
            continue
        a, b = foot + side * sign, top + side * sign
        for k in range(3):
            p = a.lerp(b, k / 2.0)
            geo.pipe([tuple(p), tuple(p + Vector((0, 0, 0.95)))], 0.028, steel_m, layer, "rail_post")
        geo.pipe([tuple(a + Vector((0, 0, 0.95))), tuple(b + Vector((0, 0, 0.95)))], 0.028, steel_m, layer, "rail")


def lean_roof(f, u0, u1, d0, d1, z0, z1, seed=1, paints=(None, RED, None, TEAL), rust=0.5, sheets=None, weights=2, over=0.12,
              layer="main", purlins=True):
    """A roof of lapped scrap sheets on face f, falling from (d0, z0) at the back to (d1, z1) at the
    front, between u0 and u1: every sheet its own rust and paint, held down with tyres, blocks and a
    plank; `over` metres of overhang all round. Returns the slope in degrees."""
    r = geo.rng(seed)
    depth = math.hypot(d1 - d0, z0 - z1)
    slope = math.degrees(math.atan2(z0 - z1, d1 - d0))
    total = u1 - u0 + 2 * over
    count = sheets or max(2, int(round(total / 0.85)))
    w = total / count + 0.07
    u = u0 - over
    for i in range(count):
        paint = paints[(i + seed) % len(paints)] if paints else None
        length = depth + over + r.uniform(-0.1, 0.12) + 0.1
        material = worn(w, length, paint, min(1.0, max(0.1, rust + r.uniform(-0.25, 0.25))), float(seed * 9 + i), streak=0.7, fix=0.1)
        at = f.at(u, d0 - 0.1, z0 + 0.05 + 0.016 * (i % 2))
        geo.corrugated_panel(w, length, at, f.rot, material, wavelength=0.11, depth=0.035, tilt=90.0 + slope + r.uniform(-1.5, 1.5),
                             roll=r.uniform(-1.5, 1.5), layer=layer, name=f"roof{i}")
        u += w - 0.07
    if purlins:
        for dd, zz in ((d0 + 0.05, z0 - 0.02), (d1 - 0.05, z1 - 0.02)):
            bx.beam(f.at(u0 - over, dd, zz), f.at(u1 + over, dd, zz), (0.09, 0.07), wood(3, axis="X", width=0.6), layer=layer, name="purlin")

    def on_roof(u_, t, lift=0.0):
        dd = d0 + (d1 - d0) * t
        return f.at(u_, dd, z0 + (z1 - z0) * t + 0.07 + lift)

    for k in range(weights):
        uu = u0 + (u1 - u0) * r.uniform(0.12, 0.88)
        t = r.uniform(0.25, 0.8)
        choice = (seed + k) % 3
        if choice == 0:
            geo.tire(on_roof(uu, t), radius=r.uniform(0.28, 0.34), lean=slope if f.rot == geo.U else 0.0, rot=r.uniform(0, 360),
                     seed=seed + k, layer=layer)
        elif choice == 1:
            geo.box((0.38, 0.19, 0.17), on_roof(uu, t), r.uniform(0, 180), mat.concrete(seed=float(k)), bevel=0.012, layer=layer,
                    name="block")
        else:
            a, b = on_roof(uu - 0.6, t, 0.02), on_roof(uu + 0.6, t + r.uniform(-0.1, 0.1), 0.02)
            bx.plank(a, b, 0.15, 0.035, wood(k, axis="X", width=0.6, grey=0.5), layer=layer, name="roof_plank")
    return slope


def tank(at, radius=0.7, height=1.5, colour=SLATE, seed=0, hoops=3, lid=True, layer="main", rust=0.55, stripe=None):
    """A riveted water tank standing on `at`: hoops with rust running from each, a domed lid, a hatch."""
    x, y, z = at
    rings = [height * (k + 1) / (hoops + 1) for k in range(hoops)]
    material = drum_paint(colour, rust, rings, float(seed), top=height)
    profile = [(radius * 0.97, 0.0), (radius, 0.03)]
    for ring in rings:
        profile += [(radius, ring - 0.035), (radius + 0.022, ring - 0.015), (radius + 0.022, ring + 0.015), (radius, ring + 0.035)]
    profile += [(radius, height - 0.03), (radius + 0.02, height), (radius * 0.96, height)]
    if lid:
        profile += [(radius * 0.7, height + radius * 0.16), (radius * 0.3, height + radius * 0.22), (0.0, height + radius * 0.23)]
    else:
        profile += [(radius * 0.93, height - 0.05), (0.0, height - 0.05)]
    obj = geo.lathe(profile, (x, y, z), material, 28, layer=layer, name="tank")
    if stripe:
        geo.lathe([(radius + 0.006, height * 0.42), (radius + 0.006, height * 0.62)], (x, y, z),
                  drum_paint(stripe, rust * 0.8, (height * 0.62,), float(seed + 3)), 28, layer=layer, name="tank_stripe")
    if lid:
        geo.cylinder(radius * 0.2, 0.08, (x + radius * 0.3, y + radius * 0.3, z + height + radius * 0.15), tube(0.5, 2.0), 10,
                     layer=layer, name="hatch")
    return obj


def junk(kind, at, seed=0, rot=0.0, layer="main"):
    """Small things to stand on decks and roofs: "barrel", "crate", "tyres", "drum" (lying), "box", "can", "bucket"."""
    x, y, z = at
    if kind == "barrel":
        return geo.barrel((x, y, z), seed=seed, layer=layer,
                          material=drum_paint(PAINTS[seed % len(PAINTS)], 0.6, (0.3, 0.6), float(seed), top=0.88))
    if kind == "crate":
        return geo.crate((0.6, 0.55, 0.5), (x, y, z), rot or 20.0 * seed, seed=seed, layer=layer)
    if kind == "tyres":
        return geo.tire_stack(2 + seed % 2, (x, y, z), seed=seed, layer=layer)
    if kind == "drum":
        return geo.barrel((x, y, z + 0.29), seed=seed, tilt=90.0, rot=rot, layer=layer,
                          material=drum_paint(PAINTS[(seed + 2) % len(PAINTS)], 0.7, (0.3, 0.6), float(seed)))
    if kind == "box":
        return geo.box((0.45, 0.3, 0.26), (x, y, z), rot or 15.0 * seed, worn(0.45, 0.26, GREEN, 0.5, float(seed), streak=0.0),
                       bevel=0.012, layer=layer, name="ammo_box")
    if kind == "can":
        return geo.cylinder(0.14, 0.36, (x, y, z), drum_paint(RED, 0.5, (0.3,), float(seed)), 10, layer=layer, name="can")
    if kind == "bucket":
        return geo.lathe([(0.11, 0.0), (0.15, 0.26), (0.13, 0.26), (0.10, 0.03), (0.0, 0.03)], (x, y, z), tube(0.5, 1.0), 12,
                         layer=layer, name="bucket")
    raise ValueError(kind)


def lamp(at, strength=1.5, layer="main", size=0.8):
    """A caged work lamp hanging from the hook point `at` (kept small and warm: a big bulb burns out to a white egg)."""
    return geo.set_block(sx.caged_lamp(at, size=size, strength=strength, layer=layer, colour=(1.0, 0.66, 0.26)), 0.0)


def flood(at, aim, size=0.14, lit=True, layer="main"):
    """A floodlight head: warm, not white, and no bigger than a head (a 0.2 m lens burns out to a white egg)."""
    return X.floodlight(at, aim, size=min(size, 0.14), strength=1.3, colour=(1.0, 0.66, 0.26), lit=lit, layer=layer)


def pipe_run(points, radius=0.07, colour=None, seed=0, flanges=True, layer="main"):
    """A pipe through world points with a flange at every corner."""
    material = drum_paint(colour, 0.6, (), float(seed)) if colour else tube(0.8, 8.0 + seed)
    obj = geo.set_block(geo.pipe([tuple(p) for p in points], radius, material, layer, "pipe_run", resolution=9), 0.0)
    if flanges:
        dots([tuple(p) for p in points[1:-1]], radius * 2.9, tube(0.6, 1.0), layer, "flange")
    return obj
