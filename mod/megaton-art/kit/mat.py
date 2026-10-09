# SPDX-License-Identifier: MIT
"""Procedural materials for Megaton set pieces. No image textures, no UVs.

All patterns are in OBJECT space and in metres, so a material looks the same on
any mesh; rotate / scale the OBJECT (not the mesh data) to turn a pattern.
Colours are linear albedo; the scene template (pipeline/bscene.py) exposes them
to stock-art brightness, so use real-world values (rust 0.1-0.3, wood 0.2,
concrete 0.3) and do not darken by hand.

At the game's scale one pixel is 2.5 cm across and 2.8 cm up. Anything finer
than about 4 cm is noise after palette conversion, so every pattern here is
built from big shapes: patches 20-60 cm, streaks, plank and panel seams,
dirt gathering at the foot of things. Every material takes `seed` (shifts
the pattern) so two copies need not look the same.

    corrugated(paint=None, rust=0.6)      rusted corrugated sheet (use with geo.corrugated_panel)
    painted_metal(colour, flaking=0.4)    sheet metal with flaking paint over rust
    planks(colour, width=0.16)            weathered boards running along local Z (see `axis`)
    concrete(), rubber(), tarp(colour)
    aluminium(panel=0.6, rivets=True)     aircraft skin: panel seams, rivet rows, streaks
    steel(rust=0.5)                       beams, pipes, frames
    sign_paint(colour), sign_board(colour) hand-painted lettering / the board under it
    chainlink()                           see-through wire mesh on a plain quad
    emitter(colour, strength)             neon tube, bulb, lamp glass (bakes its glow into the sprite)
    flat(colour)                          plain matte colour
"""
import bpy

from .nodes import Graph

_cache = {}

RUST_DARK = (0.095, 0.030, 0.012)
RUST_MID = (0.24, 0.080, 0.022)
RUST_LIGHT = (0.42, 0.17, 0.040)
GALVANISED = (0.21, 0.215, 0.21)
DIRT = (0.16, 0.12, 0.08)
SOOT = (0.02, 0.018, 0.016)


def _cached(key, build):
    material = _cache.get(key)
    if material is None or material.name not in bpy.data.materials:
        material = _cache[key] = build()
    return material


def clear_cache():
    """Called by the scene reset: materials die with the file they were made in."""
    _cache.clear()


def _seeded(g, seed):
    return g.mapping(g.coords(), location=(seed * 7.31, seed * 3.17, seed * 5.53))


def _ground_dirt(g, base, height=0.5, amount=0.6):
    """Darken towards the ground: splash-back and dust on the lowest half metre."""
    _, _, z = g.separate(g.world_position())
    near = g.smooth(z, height, 0.0)
    wobble = g.noise(g.world_position(), scale=5.0, detail=2.0)
    factor = g.mul(g.mul(near, g.remap(wobble, 0.3, 0.7, 0.4, 1.0)), amount)
    return g.mix(factor, base, DIRT)


def _rust_colour(g, p, scale=1.0):
    n = g.noise(p, scale=7.0 * scale, detail=5.0, roughness=0.65)
    return g.ramp(n, [(0.25, RUST_DARK), (0.5, RUST_MID), (0.78, RUST_LIGHT)])


def _streaks(g, p, scale=1.0):
    """Vertical run-off streaks: noise stretched along Z."""
    stretched = g.mapping(p, scale=(9.0 * scale, 9.0 * scale, 0.6 * scale))
    return g.noise(stretched, scale=1.0, detail=3.0, roughness=0.6)


def corrugated(paint=None, rust=0.6, seed=0.0):
    """Rusted corrugated iron. paint: old paint colour still clinging to it, or None for bare zinc.
    rust 0 = nearly new sheet, 1 = rusted through."""
    def build():
        g = Graph("corrugated")
        p = _seeded(g, seed)
        base = paint if paint is not None else GALVANISED
        patches = g.noise(p, scale=2.2, detail=4.0, roughness=0.6, distortion=0.4)
        streak = _streaks(g, p)
        amount = g.add(g.mul(patches, 0.7), g.mul(streak, 0.5))
        edge = 1.02 - rust * 0.62
        mask = g.smooth(amount, edge - 0.14, edge + 0.04)
        sheet = g.mix(g.remap(g.noise(p, scale=14.0, detail=2.0), 0.35, 0.7), base,
                      tuple(c * 0.72 for c in base))
        colour = g.mix(mask, sheet, _rust_colour(g, p))
        # darker in the troughs and where sheets are buried in corners
        colour = g.mix(g.smooth(g.ao(0.12), 0.75, 0.25), colour, SOOT)
        colour = _ground_dirt(g, colour)
        roughness = g.mix_value(mask, 0.55, 0.95)
        g.principled(base=colour, roughness=roughness, metallic=g.mix_value(mask, 0.55, 0.0),
                     bump=g.bump(g.noise(p, scale=30.0, detail=2.0), 0.004), specular=g.mix_value(mask, 0.4, 0.08))
        return g.material
    return _cached(("corrugated", paint, rust, seed), build)


def painted_metal(colour=(0.16, 0.22, 0.26), flaking=0.4, seed=0.0):
    """Sheet metal with old paint: flakes off in patches (more at edges and low down) to rust."""
    def build():
        g = Graph("painted_metal")
        p = _seeded(g, seed)
        big = g.noise(p, scale=2.6, detail=5.0, roughness=0.7, distortion=0.6)
        fine = g.noise(p, scale=11.0, detail=3.0, roughness=0.6)
        exposed = g.smooth(g.ao(0.2), 0.9, 0.45)                # corners and joints rust first
        amount = g.add(g.add(g.mul(big, 0.8), g.mul(fine, 0.25)), g.mul(exposed, 0.25))
        edge = 1.05 - flaking * 0.6
        mask = g.smooth(amount, edge - 0.03, edge + 0.03)       # hard edge: paint chips, it does not fade
        faded = g.mix(g.remap(g.noise(p, scale=1.3, detail=2.0), 0.3, 0.7),
                      colour, tuple(min(1.0, c * 1.35 + 0.02) for c in colour))
        faded = g.mix(g.mul(_streaks(g, p), 0.45), faded, DIRT)
        result = g.mix(mask, faded, _rust_colour(g, p))
        result = _ground_dirt(g, result)
        g.principled(base=result, roughness=g.mix_value(mask, 0.6, 0.95), metallic=0.0,
                     bump=g.bump(mask, 0.002, strength=0.6), specular=g.mix_value(mask, 0.2, 0.06))
        return g.material
    return _cached(("painted_metal", colour, flaking, seed), build)


def planks(colour=(0.27, 0.14, 0.06), width=0.16, axis="Z", grey=0.2, seed=0.0):
    """Weathered boards. axis: the LOCAL axis the boards run along ("X", "Y" or "Z"); they are
    laid side by side across the other horizontal direction. grey 0..1: how sun-bleached."""
    def build():
        g = Graph("planks")
        p = _seeded(g, seed)
        x, y, z = g.separate(p)
        if axis == "Z":
            along, across = z, g.add(x, y)          # works for walls facing either way
        elif axis == "X":
            along, across = x, g.add(y, z)
        else:
            along, across = y, g.add(x, z)
        index = g.floor(g.div(across, width))
        per_plank = g.white_noise(g.combine(index, 0.0, seed))
        gap = g.absolute(g.sub(g.fract(g.div(across, width)), 0.5))        # 0 centre .. 0.5 seam
        seam = g.smooth(gap, 0.36, 0.48)
        grain_p = g.combine(g.mul(across, 40.0), g.add(g.mul(along, 2.5), g.mul(per_plank, 20.0)), index)
        grain = g.noise(grain_p, scale=1.0, detail=3.0, roughness=0.6)
        tone = g.mix(g.remap(per_plank, 0.0, 1.0, 0.0, 0.8),
                     tuple(c * 0.62 for c in colour), tuple(min(1.0, c * 1.3) for c in colour))
        bleached = g.mix(g.mul(g.noise(p, scale=1.6, detail=3.0), grey * 1.6), tone, (0.27, 0.24, 0.20))
        wood = g.mix(g.remap(grain, 0.3, 0.7, 0.0, 0.75), bleached, tuple(c * 0.3 for c in colour))
        wood = g.mix(seam, wood, SOOT)
        wood = g.mix(g.smooth(g.ao(0.15), 0.8, 0.3), wood, SOOT)         # grime where boards meet
        wood = _ground_dirt(g, wood, amount=0.5)
        height = g.sub(g.mul(grain, 0.3), seam)
        g.principled(base=wood, roughness=0.9, bump=g.bump(height, 0.012), specular=0.15)
        return g.material
    return _cached(("planks", colour, width, axis, grey, seed), build)


def concrete(colour=(0.30, 0.29, 0.265), cracks=0.5, seed=0.0):
    def build():
        g = Graph("concrete")
        p = _seeded(g, seed)
        blotch = g.noise(p, scale=1.8, detail=5.0, roughness=0.7)
        base = g.mix(g.remap(blotch, 0.3, 0.7), tuple(c * 0.7 for c in colour), tuple(min(1, c * 1.15) for c in colour))
        base = g.mix(g.mul(_streaks(g, p, 0.7), 0.5), base, tuple(c * 0.45 for c in colour))
        crack = g.voronoi(g.mapping(p, scale=(1.0, 1.0, 1.0)), scale=2.3, feature="DISTANCE_TO_EDGE")
        crack_mask = g.mul(g.smooth(crack, 0.035, 0.0), cracks)
        base = g.mix(crack_mask, base, SOOT)
        base = _ground_dirt(g, base, amount=0.5)
        pits = g.noise(p, scale=22.0, detail=2.0)
        g.principled(base=base, roughness=0.95, bump=g.bump(g.sub(g.mul(pits, 0.4), crack_mask), 0.01), specular=0.2)
        return g.material
    return _cached(("concrete", colour, cracks, seed), build)


def rubber(seed=0.0):
    """Tyre rubber: nearly black, dusty on top."""
    def build():
        g = Graph("rubber")
        p = _seeded(g, seed)
        dust = g.mul(g.noise(p, scale=6.0, detail=3.0), 0.6)
        colour = g.mix(dust, (0.022, 0.022, 0.024), (0.10, 0.085, 0.07))
        g.principled(base=colour, roughness=0.75, specular=0.35,
                     bump=g.bump(g.noise(p, scale=25.0, detail=1.0), 0.004))
        return g.material
    return _cached(("rubber", seed), build)


def tarp(colour=(0.20, 0.17, 0.10), seed=0.0):
    """Canvas / tarpaulin: soft folds, stains, sun-fading."""
    def build():
        g = Graph("tarp")
        p = _seeded(g, seed)
        folds = g.noise(g.mapping(p, scale=(1.0, 1.0, 0.35)), scale=4.0, detail=2.0, roughness=0.4, distortion=0.8)
        stain = g.noise(p, scale=2.0, detail=4.0, roughness=0.7)
        base = g.mix(g.remap(stain, 0.3, 0.75), tuple(c * 0.6 for c in colour), tuple(min(1, c * 1.3) for c in colour))
        base = _ground_dirt(g, base, amount=0.4)
        g.principled(base=base, roughness=0.95, specular=0.1, bump=g.bump(folds, 0.03))
        return g.material
    return _cached(("tarp", colour, seed), build)


def aluminium(panel=0.6, rivets=True, tint=(0.40, 0.42, 0.44), seed=0.0, axis="X"):
    """Aircraft skin: riveted panels, darker seams, oily streaks. panel: panel size in metres.
    axis: local axis the panel rows run along; rows are stacked along local Z."""
    def build():
        g = Graph("aluminium")
        p = _seeded(g, seed)
        x, y, z = g.separate(p)
        run = g.add(x, y) if axis == "X" else y
        # panel seams
        fu = g.fract(g.div(run, panel * 1.6))
        fv = g.fract(g.div(z, panel))
        du = g.minimum(fu, g.sub(1.0, fu))
        dv = g.minimum(fv, g.sub(1.0, fv))
        seam = g.smooth(g.minimum(g.mul(du, panel * 1.6), g.mul(dv, panel)), 0.012, 0.0)
        # per-panel tone
        index = g.combine(g.floor(g.div(run, panel * 1.6)), g.floor(g.div(z, panel)), seed)
        tone = g.white_noise(index)
        base = g.mix(g.remap(tone, 0.0, 1.0, 0.0, 1.0), tuple(c * 0.55 for c in tint), tint)
        base = g.mix(g.mul(g.smooth(_streaks(g, p, 0.8), 0.35, 0.75), 0.8), base, (0.09, 0.08, 0.07))
        base = g.mix(seam, base, SOOT)
        height = g.mul(seam, -1.0)
        if rivets:
            # rivet rows 5 cm inside each seam, every 6 cm
            near_u = g.smooth(g.absolute(g.sub(g.mul(du, panel * 1.6), 0.05)), 0.014, 0.004)
            near_v = g.smooth(g.absolute(g.sub(g.mul(dv, panel), 0.05)), 0.014, 0.004)
            dots_u = g.smooth(g.absolute(g.sub(g.fract(g.div(z, 0.07)), 0.5)), 0.22, 0.10)
            dots_v = g.smooth(g.absolute(g.sub(g.fract(g.div(run, 0.07)), 0.5)), 0.22, 0.10)
            rivet = g.maximum(g.mul(near_u, dots_u), g.mul(near_v, dots_v))
            base = g.mix(g.mul(rivet, 0.75), base, (0.07, 0.07, 0.07))
            height = g.add(height, rivet)
        base = _ground_dirt(g, base, amount=0.45)
        g.principled(base=base, roughness=0.5, metallic=0.6, specular=0.4, bump=g.bump(height, 0.008))
        return g.material
    return _cached(("aluminium", panel, rivets, tint, seed, axis), build)


def steel(rust=0.5, colour=(0.10, 0.10, 0.105), seed=0.0):
    """Structural steel: dark mill scale going to rust. For I-beams, pipes, frames, chain."""
    def build():
        g = Graph("steel")
        p = _seeded(g, seed)
        n = g.noise(p, scale=5.0, detail=5.0, roughness=0.7, distortion=0.3)
        edge = 0.98 - rust * 0.6
        mask = g.smooth(n, edge - 0.1, edge + 0.06)
        result = g.mix(mask, colour, _rust_colour(g, p, 1.5))
        result = _ground_dirt(g, result, amount=0.4)
        g.principled(base=result, roughness=g.mix_value(mask, 0.5, 0.9), metallic=g.mix_value(mask, 0.6, 0.0),
                     specular=0.4, bump=g.bump(n, 0.003))
        return g.material
    return _cached(("steel", rust, colour, seed), build)


def sign_paint(colour=(0.75, 0.70, 0.55), wear=0.35, seed=0.0, glow=0.0):
    """Hand-brushed paint for lettering: uneven coverage, chipped. glow > 0 makes it self-lit
    (a painted sign under its own lamp) - baked into the sprite, see emitter()."""
    def build():
        g = Graph("sign_paint")
        p = _seeded(g, seed)
        brush = g.noise(g.mapping(p, scale=(3.0, 3.0, 14.0)), scale=2.0, detail=3.0, roughness=0.6)
        chips = g.noise(p, scale=9.0, detail=4.0, roughness=0.75)
        chip_mask = g.smooth(chips, 0.80 - wear * 0.35, 0.84 - wear * 0.35)
        base = g.mix(g.remap(brush, 0.3, 0.7, 0.0, 0.5), colour, tuple(c * 0.6 for c in colour))
        base = g.mix(chip_mask, base, RUST_MID)
        g.principled(base=base, roughness=0.7, specular=0.25,
                     emission=base if glow else None, emission_strength=glow)
        return g.material
    return _cached(("sign_paint", colour, wear, seed, glow), build)


def sign_board(colour=(0.34, 0.07, 0.05), seed=0.0):
    """The board under hand-painted lettering: sheet metal, sun-faded paint, rust at the rim."""
    return painted_metal(colour, flaking=0.3, seed=seed + 11.0)


def chainlink(wire=(0.16, 0.15, 0.14), cell=0.15, thickness=0.36, seed=0.0):
    """Chain-link mesh for a flat quad: diamond wire pattern, everything else transparent.
    cell: diamond size in metres (0.15 = 6 px reads as mesh at game scale; a real 5 cm mesh turns
    to mush); thickness: wire width as a share of the cell (under 0.3 the 1-bit alpha breaks it up).
    The quad must be vertical; the pattern uses the object's local X / Y run and Z."""
    def build():
        g = Graph("chainlink")
        x, y, z = g.separate(g.coords())
        run = g.add(x, y)
        a = g.absolute(g.sub(g.fract(g.div(g.add(run, z), cell)), 0.5))
        b = g.absolute(g.sub(g.fract(g.div(g.sub(run, z), cell)), 0.5))
        wire_mask = g.greater(g.maximum(a, b), 0.5 - thickness / 2.0)
        rusty = g.mix(g.noise(g.coords(), scale=4.0, detail=2.0), wire, RUST_MID)
        g.principled(base=rusty, roughness=0.7, metallic=0.3, alpha=wire_mask)
        return g.material
    return _cached(("chainlink", wire, cell, thickness, seed), build)


def emitter(colour=(1.0, 0.72, 0.35), strength=1.5):
    """Self-lit surface: neon tube, bulb, lamp lens. The glow is baked into the sprite and also
    lights the piece around it. strength 1 shows exactly `colour` at full brightness; 2-4 burns
    out towards white (a bulb's hot core) and spills more light; above that everything is white.
    The engine still darkens baked glow at night unless the piece is a lamp (`light=`) or the
    colour falls into an animated palette range the piece asked for (convert={"fx": [...]})."""
    def build():
        from pipeline.bscene import EXPOSURE
        g = Graph("emitter")
        g.principled(base=colour, roughness=0.4, emission=colour, emission_strength=strength * 2.0 ** -EXPOSURE)
        return g.material
    return _cached(("emitter", colour, strength), build)


def flat(colour=(0.5, 0.5, 0.5), roughness=0.9, metallic=0.0):
    def build():
        g = Graph("flat")
        g.principled(base=colour, roughness=roughness, metallic=metallic)
        return g.material
    return _cached(("flat", colour, roughness, metallic), build)


def glass(colour=(0.25, 0.32, 0.30), dirt=0.6):
    """Dirty window glass: mostly a dark, slightly glossy pane (true transparency reads as holes)."""
    def build():
        g = Graph("glass")
        p = g.coords()
        grime = g.mul(g.noise(p, scale=5.0, detail=4.0), dirt)
        base = g.mix(grime, tuple(c * 0.25 for c in colour), DIRT)
        g.principled(base=base, roughness=g.mix_value(grime, 0.08, 0.7), specular=0.8)
        return g.material
    return _cached(("glass", colour, dirt), build)
