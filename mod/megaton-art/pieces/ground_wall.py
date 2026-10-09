# SPDX-License-Identifier: MIT
"""Perimeter jumble (author "ground"): stretches of scrap that REPLACE the plain tin stockade, and
the junk piled against its inside.

WHERE THEY GO   The town's wall has two faces the camera sees from INSIDE: the BACK runs (along a hex
row, hy 57 / 63 / 69) and the RIGHT runs (down a column, hx 56 / 62 / 68). Nothing stands behind
them, so these pieces are tall (to 5 m) and deep (they lean out over the waste ground behind).
Do not use them on the front and left runs: there the wall is between the camera and the town.

ALONG A ROW ("u")   Like the gate's wall pieces: the wall row is hex row dhy = +1 of the origin
(wall rows are odd, origins even). A piece covers hexes (0 .. n-1, 1), n even, and blocks them and
the odd hexes of row 2 in front, exactly as the stock fence with its "Wall s.t." blockers does.
Take away the fence objects on (origin hx .. origin hx + n - 1, wall row) and the blockers on the
odd hexes of the row in front, then place the piece on (origin hx, wall row - 1).
    gr_wall_scrap_ua / ub   4 hexes   sheets of every height, patches riveted over patches, a car door, a bulge held by a prop
    gr_wall_cars_u          6 hexes   three car bodies stacked and chained, the top two crushed
    gr_wall_wing_u          4 hexes   two airliner wing sections stood on end, a slab of fuselage between
    gr_wall_boat_u          6 hexes   a boat on her beam ends, keel to the town, a fence of sheets along her upper side
    gr_wall_bill_u          6 hexes   a roadside hoarding on lattice legs, half its panels gone, tin under it
    gr_wall_cont_u          6 hexes   a shipping container's long side with a second one skewed on top
DOWN A COLUMN ("v")   The origin is ON the wall column (the right runs stand on even hx); a piece
covers (0, 0 .. n-1) and blocks just those. Take away the fence objects on those hexes.
    gr_wall_scrap_va / vb   4 hexes
    gr_wall_cars_v          6 hexes
    gr_wall_bill_v          6 hexes
AGAINST THE WALL   junk leaning on the inside of a plain stretch (the wall stays):
    gr_lean_ua / ub         on the row IN FRONT of a row wall: origin on it, covers (0 .. 3, 0)
    gr_lean_va / vb         on the column in front of a column wall: origin = the WALL's hex, covers (1, 0 .. 3)
"""
import math

from kit import piece, geo, mat, G
from kit import ground_extra as gx
from kit import bomb_extra as bx
from kit import signs_extra as sx
from kit import gate_extra as gate

HU, HV = gx.HEX_U, gx.HEX_V
WALL_U = dict(kind="wall", see_through="u", shadow="none", overhang=1.3)
WALL_V = dict(kind="wall", see_through="v", shadow="none", overhang=1.3)
FACE = -0.14                                  # canonical y of a wall piece's main face (0.14 m in front of the wall line)


def place_u(objects, n):
    """Canonical wall (local x = 0 .. n hexes from its screen-left end, front on -y) -> row +1."""
    return gx.put(objects, ((n - 0.5) * HU, HV, 0.0), rot=geo.U)


def place_v(objects):
    return gx.put(objects, (0.0, -HV / 2.0, 0.0), rot=geo.V)


def spikes(x0, x1, z, seed, y=0.1):
    r = geo.rng(seed)
    made = []
    x = x0
    steel = mat.steel(rust=0.85, seed=seed)
    while x < x1:
        made.append(geo.pipe([(x, y, z - 0.2), (x + r.uniform(-0.06, 0.06), y + r.uniform(-0.04, 0.06), z + r.uniform(0.25, 0.55))], 0.028, steel, name="spike"))
        x += r.uniform(0.3, 0.55)
    return gx.no_block(made)


def backing(length, seed, height=3.2, every=1.38):
    """Posts and rails the scrap is hung on (they show through every gap, and above the low sheets)."""
    r = geo.rng(seed)
    made = []
    x = 0.12
    k = 0
    while x < length:
        h = height * r.uniform(0.85, 1.12)
        made += gx.post((x, 0.12, 0.0), h, ("timber", "angle", "pole", "timber")[k % 4], seed + k, lean=(r.uniform(-0.08, 0.08), r.uniform(-0.03, 0.06)), size=0.13)
        x += every
        k += 1
    for z in (0.7, 1.9, height - 0.5):
        made.append(gx.rail((0.0, 0.08, z + r.uniform(-0.08, 0.08)), (length, 0.08, z + r.uniform(-0.08, 0.08)), ("pole", "pipe", "board")[int(z * 3) % 3], seed + int(z * 7)))
    return made


def scrap(length, seed, variant):
    """Canonical scrap wall: sheets, patches, things."""
    r = geo.rng(seed)
    made = backing(length, seed, height=3.3 if variant == "a" else 3.0)
    f = gx.Frame((0.0, FACE, 0.0), 0.0)
    paints = [None, "oxide", None, "teal", "cream", None, "olive", None, "yellow", None]
    # the sheets: every one its own height, lean and colour, lapped over the last
    x = -0.04
    k = 0
    heights = (2.6, 3.5, 2.3, 3.0, 3.8, 2.5) if variant == "a" else (3.2, 2.4, 3.6, 2.2, 2.9, 3.4)
    while x < length - 0.1:
        w = min(r.uniform(0.7, 0.98), length - x + 0.04)
        h = heights[k % len(heights)] + r.uniform(-0.12, 0.12)
        z0 = r.choice([0.0, 0.0, 0.25])
        made.append(geo.corrugated_panel(w, h - z0, (x, FACE + (0.02 if k % 2 else -0.02), z0), 0.0, gx.tin(paints[(k + seed) % len(paints)], rust=r.uniform(0.4, 0.8), seed=seed + k, top=h - z0),
                                         wavelength=0.12, depth=0.035, tilt=r.uniform(-2.5, 2.5), roll=r.uniform(-2.5, 2.5), name="scrap_sheet"))
        x += w - 0.07
        k += 1
    geo.set_block(made, geo.BLOCK_WALL)
    if variant == "a":
        # a car door riveted on, a patch over a patch, a bulge held in by a prop, a road sign, a tyre on a spike
        made += gx.put(gx.car_door("red", seed + 1, glass="boards"), (0.25, FACE - 0.06, 0.55), tilt=-2.0, roll=-3.0, block=0)
        made += gx.patch(f, 1.55, 1.3, 0.85, 0.7, gx.paint("grey", rust=0.6, seed=seed + 2), d=0.03, seed=seed, runs=0.6)
        made += gx.patch(f, 1.75, 1.55, 0.5, 0.42, gx.paint("yellow", rust=0.45, seed=seed + 3), d=0.055, roll=6.0, seed=seed + 1, runs=0.45)
        made.append(gate.plate(0.95, 1.5, (length - 1.15, FACE - 0.02, 0.2), 0.0, gx.paint("oxide", rust=0.6, seed=seed + 4, scale=1.6, sills=1.0), thickness=0.03, bulge=0.3,
                               name="bulge", dent=0.02, seed=seed))
        made.append(bx.beam((length - 0.7, FACE - 1.0, 0.0), (length - 0.68, FACE - 0.3, 1.25), (0.1, 0.1), gx.wood(seed=seed + 5, grey=0.4), name="prop"))
        made.append(geo.box((0.3, 0.3, 0.06), (length - 0.7, FACE - 1.02, 0.0), 10.0, mat.concrete(seed=seed), bevel=0.01, name="prop_foot"))
        made += gx.put(gx.road_sign("round", seed + 6, post=0.6, bent=0.0, size=0.66), (1.15, FACE - 0.07, 2.25), block=0)
        made.append(geo.tire((0.7, 0.1, 2.95), radius=0.36, lying=False, rot=0.0, lean=8.0, seed=seed))
        made += gx.bolts(f, [(0.3, 1.75), (1.1, 1.72), (0.3, 0.62), (1.1, 0.6)], d=-0.02, radius=0.035, runs=0.5, seed=seed)
    else:
        # a fridge door, planks nailed across a gap, hazard chevrons, a number plate, a bedspring
        white = gx.enamel("white", rust=0.4, seed=seed + 1, lines=(1.5,))
        made.append(geo.box((0.7, 0.07, 1.45), (0.45, FACE - 0.05, 0.4), 0.0, white, bevel=0.035, name="fridge_door", roll=2.0))
        made.append(geo.box((0.035, 0.05, 0.4), (0.2, FACE - 0.1, 1.2), 0.0, gx.chrome(0.35), bevel=0.012, name="fridge_handle"))
        made.append(gx.streak(f, -0.25 + 0.45, 1.2, 0.6, 0.07, d=0.09))
        for i in range(3):
            made.append(geo.box((1.15, 0.03, 0.17), (1.75 + r.uniform(-0.04, 0.04), FACE - 0.03, 0.9 + i * 0.42), 0.0, gx.wood(seed=seed + i, grey=0.45), bevel=0.005, name="nailed_plank",
                                roll=r.uniform(-5, 5)))
        made.append(geo.box((0.9, 0.025, 0.6), (length - 0.55, FACE - 0.035, 1.45), 0.0, gate.hazard(seed=seed, uv=False), bevel=0.0, name="chevron", roll=-4.0))
        made += gx.bolts(f, [(length - 0.93, 1.98), (length - 0.17, 1.95), (length - 0.93, 1.52), (length - 0.17, 1.5)], d=0.04, radius=0.03, runs=0.5, seed=seed + 2)
        made += gx.put(gx.bedspring(seed + 3, size=(1.3, 0.8)), (length - 0.85, FACE - 0.07, 0.75), tilt=88.0, roll=0.0, block=0)
        made += gx.put(gx.road_sign("diamond", seed + 4, post=0.5, bent=0.0, size=0.6), (1.3, FACE - 0.08, 2.6), roll=14.0, block=0)
    made += spikes(0.2, length - 0.2, 3.0, seed)
    made.append(geo.cable((0.0, 0.1, 3.2), (length, 0.1, 3.1), sag=0.14, radius=0.02))
    return made


@piece("gr_wall_scrap_ua", title="Scrap Wall", desc="Every sheet a different height and a different colour of rust. A car door has been riveted over one hole and a plate over another, and a timber prop holds the bulge in.",
       footprint=gx.wall_u_cells(4), **WALL_U)
def gr_wall_scrap_ua(ctx):
    place_u(scrap(4 * HU, 701, "a"), 4)


@piece("gr_wall_scrap_ub", title="Scrap Wall", desc="A refrigerator door, a bedspring, planks nailed across the gap between two sheets, and chevrons off a road barrier. It keeps the wind out.",
       footprint=gx.wall_u_cells(4), **WALL_U)
def gr_wall_scrap_ub(ctx):
    place_u(scrap(4 * HU, 711, "b"), 4)


@piece("gr_wall_scrap_va", title="Scrap Wall", desc="Every sheet a different height and a different colour of rust, with a car door riveted over the worst hole.",
       footprint=gx.col_hexes(0, 3), **WALL_V)
def gr_wall_scrap_va(ctx):
    place_v(scrap(4 * HV, 721, "a"))


@piece("gr_wall_scrap_vb", title="Scrap Wall", desc="A refrigerator door, a bedspring and chevrons off a road barrier, wired to a fence of posts.",
       footprint=gx.col_hexes(0, 3), **WALL_V)
def gr_wall_scrap_vb(ctx):
    place_v(scrap(4 * HV, 731, "b"))


# ------------------------------------------------------------------------------- cars
def car_stack(length, seed):
    made = []
    y = 0.62                                              # the cars' centre line: behind the wall line, their near sides on FACE
    paints = ["oxide", "teal", "cream"]
    car_l = min(4.3, length - 0.1)
    made += gx.put(gx.car_body(paints[seed % 3], seed, length=car_l, crush=0.25, wheels=(False, False)), ((length - car_l) / 2.0, y, -0.2))
    made += gx.put(gx.car_body(paints[(seed + 1) % 3], seed + 1, length=car_l * 0.94, crush=0.75, bumper=False), ((length - car_l) / 2.0 + 0.35, y + 0.06, 0.9), rot=1.5, roll=-2.5)
    made += gx.put(gx.car_body(paints[(seed + 2) % 3], seed + 2, length=car_l * 0.9, crush=0.85), ((length - car_l) / 2.0 - 0.1, y + 0.02, 1.72), rot=-2.0, roll=3.5, tilt=-3.0)
    # baulks between them, chains round the lot, a bonnet and a tyre on top, sheet over the gaps at the ends
    for z, x in ((0.98, 0.8), (0.98, length - 1.0), (1.78, 1.2), (1.78, length - 1.4)):
        made.append(geo.box((0.16, 1.9, 0.14), (x, y, z), 0.0, gx.wood((0.20, 0.12, 0.06), seed=seed + int(x * 5), axis="Y", grey=0.3), bevel=0.01, name="baulk"))
    chain = mat.flat((0.05, 0.045, 0.04), metallic=0.5, roughness=0.5)
    for x in (length * 0.3, length * 0.68):
        made.append(geo.pipe([(x, y - 0.86, 0.1), (x + 0.03, y - 0.87, 1.2), (x - 0.02, y - 0.84, 2.4), (x, y - 0.3, 2.62), (x, y + 0.5, 2.6)], 0.028, chain, name="chain"))
    made += gx.put(gx.bonnet("olive", seed + 4), (length * 0.55, y - 0.1, 2.6), rot=12.0, roll=4.0)
    made.append(geo.tire((length * 0.2, y - 0.2, 2.56), lying=True, seed=seed, lean=7.0))
    for x0, w in ((-0.02, 0.5), (length - 0.48, 0.5)):
        made.append(geo.corrugated_panel(w, 2.7, (x0, FACE + 0.02, 0.0), 0.0, gx.tin(None, rust=0.65, seed=seed + int(x0)), wavelength=0.12, tilt=-2.0, name="end_sheet"))
    made += gx.put(gx.wheel(seed + 6, hub="oxide"), (length * 0.42, y - 1.02, 0.0), tilt=-18.0, rot=6.0)
    made += spikes(0.4, length - 0.4, 2.65, seed, y=y + 0.5)
    return geo.set_block(made, geo.BLOCK_WALL)


@piece("gr_wall_cars_u", title="Car Stack", desc="Three cars, one on another, chained. The bottom one still has its bumpers; the top two went under something heavy first.",
       footprint=gx.wall_u_cells(6, deep=True), **WALL_U)
def gr_wall_cars_u(ctx):
    place_u(car_stack(6 * HU, 741), 6)


@piece("gr_wall_cars_v", title="Car Stack", desc="Three cars, one on another, chained, with timber baulks between so they do not slide.",
       footprint=gx.col_hexes(0, 5), **WALL_V)
def gr_wall_cars_v(ctx):
    place_v(car_stack(6 * HV, 745))


# ------------------------------------------------------------------------------- wing
def stand_wing(x, span, chord_root, chord_tip, material, lean=0.0, y=0.0):
    wing = gate.wing(span, chord_root, chord_tip, thickness=0.13, sweep=0.5, material=material, tip_length=0.5)
    wing.matrix_world = bx.frame((x, y, 0.0), x=(lean, 0.0, 1.0), y=(1.0, 0.0, -lean), z=None)
    return geo.set_block(wing, geo.BLOCK_WALL)


@piece("gr_wall_wing_u", title="Wing Wall", desc="Two lengths of airliner wing stood on end and a slab of fuselage between them, windows and all. The red tip was a navigation light.",
       footprint=gx.wall_u_cells(4), **WALL_U)
def gr_wall_wing_u(ctx):
    length = 4 * HU
    made = []
    red = (0.30, 0.055, 0.035)
    skin_a = gate.skin(tint=(0.42, 0.44, 0.45), panel=(0.55, 0.45), rust=0.3, grime=0.85, seed=21.0, tone=0.4, bands=[("u", 3.6, 4.4, red), ("u", 1.2, 1.32, (0.05, 0.05, 0.06))])
    skin_b = gate.skin(tint=(0.36, 0.38, 0.37), panel=(0.6, 0.4), rust=0.42, grime=0.9, seed=23.0, tone=0.45, bands=[("u", 0.4, 1.0, (0.09, 0.15, 0.22))])
    made.append(stand_wing(-0.02, 4.4, 1.25, 0.8, skin_a, lean=0.03, y=FACE + 0.08))
    made.append(stand_wing(length - 1.2, 3.5, 1.2, 0.85, skin_b, lean=-0.05, y=FACE + 0.02))
    hull = gate.skin(tint=(0.46, 0.47, 0.48), panel=(0.5, 0.7), rust=0.25, grime=0.8, seed=25.0, tone=0.3, stagger=False,
                     bands=[("v", 1.5, 1.72, red), ("v", 1.76, 1.8, (0.05, 0.05, 0.06))])
    made.append(gate.plate(1.0, 2.7, (1.05, FACE + 0.1, 0.0), 0.0, hull, thickness=0.04, bulge=0.12, name="fuselage", dent=0.01, seed=3))
    for k in range(2):
        made.append(geo.box((0.24, 0.02, 0.34), (1.33 + 0.44 * k, FACE - 0.03, 1.95), 0.0, gx.dark(0.014), bevel=0.08, name="cabin_window"))
        made.append(geo.box((0.3, 0.015, 0.4), (1.33 + 0.44 * k, FACE - 0.02, 1.92), 0.0, gx.chrome(0.5), bevel=0.1, name="window_frame"))
    # what holds it: raking shores behind (their heads show over the top), wire ties, a concrete kerb
    for x in (0.5, 1.5, length - 0.5):
        made.append(bx.beam((x, 1.3, 0.0), (x, 0.2, 2.9), (0.12, 0.12), gx.wood(seed=30 + int(x), grey=0.4), name="shore"))
    made.append(gx.rail((0.0, 0.16, 2.55), (length, 0.16, 2.45), "pipe", 31))
    made.append(geo.box((length, 0.3, 0.22), (length / 2.0, FACE - 0.05, 0.0), 0.0, mat.concrete(seed=4), bevel=0.02, name="kerb"))
    f = gx.Frame((0.0, FACE - 0.02, 0.0), 0.0)
    made += gx.bolts(f, [(0.5, 2.6), (1.1, 2.55), (2.1, 2.5)], d=0.02, radius=0.035, runs=0.7, seed=5)
    made += [glyph for _, glyph, _, _ in sx.stencil("N7", gx.Frame((0.0, FACE + 0.02, 0.0), 0.0), 0.55, 0.75, 0.5, colour=(0.05, 0.05, 0.06), d=0.02, seed=6)]
    place_u(made, 4)


# ------------------------------------------------------------------------------- boat
def hull(length=4.0, beam=1.5, depth=0.8, seed=0):
    """A clinker boat hull, upright along local X (stem at x = length), keel on z = 0."""
    stations, around = 12, 12
    points, uvs = [], []
    for i in range(stations + 1):
        t = i / stations
        w = beam / 2.0 * (0.72 + 0.28 * math.sin(math.pi * t)) * (1.0 if t < 0.6 else max(0.03, 1.0 - ((t - 0.6) / 0.4) ** 1.7))
        rise = depth * 0.35 * max(0.0, (t - 0.55) / 0.45) ** 2
        ring, ring_uv = [], []
        for k in range(around + 1):
            a = math.pi * k / around                       # 0 = port gunwale, pi/2 = keel, pi = starboard gunwale
            y = -w * math.cos(a) * (1.0 - 0.25 * math.sin(a) ** 6)
            z = depth * (1.0 - math.sin(a) ** 0.7) + rise * math.sin(a)
            ring.append((length * t, y, z))
            ring_uv.append((length * t, k / around * 2.4))
        points.append(ring)
        uvs.append(ring_uv)
    skin = gx.paint("white", rust=0.42, seed=seed, band=(-1.0, depth * 0.5, "oxide"), runs=0.5, scale=1.6, gloss=0.4)
    shell = gate.grid_mesh("hull", points, uvs, skin, solidify=0.05)
    made = [shell]
    made.append(geo.pipe([(0.0, 0.0, -0.03), (length * 0.62, 0.0, -0.03), (length * 0.9, 0.0, depth * 0.2), (length + 0.03, 0.0, depth + 0.05)], 0.045, gx.wood((0.16, 0.10, 0.06), seed=seed, grey=0.3),
                         name="keel"))
    for side in (-1.0, 1.0):
        made.append(geo.pipe([(points[i][0 if side < 0 else around][0], points[i][0 if side < 0 else around][1], points[i][0][2] + 0.02) for i in range(stations + 1)], 0.04,
                             gx.wood((0.20, 0.12, 0.06), seed=seed + 1, grey=0.3), name="gunwale"))
    return made


@piece("gr_wall_boat_u", title="Boat Wall", desc="A fishing boat on stocks, wheelhouse and mast and all, built into the wall. Nobody can say how she got this far from water.",
       footprint=gx.wall_u_cells(6, deep=True), **WALL_U)
def gr_wall_boat_u(ctx):
    length = 6 * HU
    r = ctx.rng
    y = 0.64                                              # her centre line: the near side of the hull is the wall's face
    made = gx.put(hull(length - 0.2, 1.55, 1.05, 752), (0.1, y, 0.22), rot=0.0, roll=-1.5, tilt=3.0)
    deck = 1.27
    made.append(geo.box((length * 0.62, 1.2, 0.05), (length * 0.4, y, deck - 0.08), 0.0, gx.wood((0.22, 0.14, 0.08), seed=3, axis="X", width=0.18, grey=0.5), bevel=0.0,
                        name="deck"))
    # wheelhouse: planked, a strip of dark windows, a tin roof with the paint gone
    wx = length * 0.3
    made.append(geo.box((1.25, 0.95, 1.0), (wx, y, deck - 0.05), 0.0, gx.paint("cream", rust=0.3, seed=753, lines=(0.95,), reach=0.6, runs=0.6), bevel=0.02, name="wheelhouse"))
    made.append(geo.box((1.05, 0.02, 0.3), (wx, y - 0.48, deck + 0.5), 0.0, gx.dark(0.016), bevel=0.0, name="wheelhouse_window"))
    made.append(geo.box((0.02, 0.7, 0.3), (wx + 0.63, y, deck + 0.5), 0.0, gx.dark(0.016), bevel=0.0, name="wheelhouse_window"))
    for dx in (-0.18, 0.18):
        made.append(geo.box((0.04, 0.03, 0.32), (wx + dx, y - 0.49, deck + 0.49), 0.0, gx.paint("cream", rust=0.3, seed=754), bevel=0.0, name="mullion"))
    made.append(geo.box((1.45, 1.15, 0.06), (wx, y, deck + 0.95), 0.0, gx.paint("teal", rust=0.6, seed=755), bevel=0.01, name="wheelhouse_roof", roll=2.0))
    # mast and boom, stays, a lamp at the masthead, nets over the boom
    mx = length * 0.58
    made.append(gx.rod((mx, y, deck - 0.1), (mx + 0.06, y, 4.5), 0.05, gx.wood((0.24, 0.16, 0.09), seed=5, axis="Z", width=0.8, grey=0.5), 10, name="mast"))
    made.append(gx.rod((mx + 0.02, y, 2.3), (length - 0.5, y - 0.1, 2.0), 0.035, gx.wood((0.24, 0.16, 0.09), seed=6, axis="Z", width=0.8, grey=0.5), 8, name="boom"))
    for end in ((length - 0.15, y, 1.45), (0.25, y, 1.35), (wx, y + 0.5, deck + 1.0)):
        made.append(geo.cable((mx + 0.06, y, 4.4), end, sag=0.06, radius=0.02))
    made.append(sx.sag_sheet([(mx + 0.3, y - 0.12, 2.28), (length - 0.6, y - 0.14, 2.02), (length - 0.75, y - 0.3, 1.4), (mx + 0.45, y - 0.25, 1.55)], gx.canvas((0.16, 0.13, 0.08), seed=7),
                             sag=0.08, seed=7, rows=5, columns=6))
    made += sx.lantern((mx + 0.06, y - 0.06, 4.3), size=0.8, lit=False)
    # her name, shores under the turn of the bilge, keel blocks, tin along the far gunwale to finish the wall
    made += [glyph for _, glyph, _, _ in sx.stencil("MARY", gx.Frame((0.0, y - 0.74, 0.0), 0.0), length * 0.74, 0.9, 0.26, colour=(0.05, 0.05, 0.06), d=0.0, seed=7)]
    for x in (0.8, length * 0.45, length - 1.3):
        made.append(bx.beam((x, FACE - 0.55, 0.0), (x + 0.05, y - 0.6, 0.62), (0.1, 0.1), gx.wood(seed=770 + int(x), grey=0.4), name="shore"))
        made += gx.put(gx.cinder(771 + int(x)), (x + 0.3, y, 0.0), rot=90.0)
    x, k = -0.04, 0
    while x < length - 0.1:
        w = min(r.uniform(0.75, 0.98), length - x + 0.04)
        h = (2.9, 2.4, 3.3, 2.6, 3.1)[k % 5]
        made.append(geo.corrugated_panel(w, h, (x, y + 0.72, 0.0), 0.0, gx.tin((None, "teal", None, "oxide", None)[k % 5], rust=r.uniform(0.45, 0.8), seed=760 + k, top=h), wavelength=0.12,
                                         tilt=r.uniform(-2, 2), roll=r.uniform(-2, 2), name="fence_sheet"))
        x += w - 0.07
        k += 1
    made.append(geo.tire((length - 0.6, FACE - 0.55, 0.0), lying=True, seed=5))
    geo.set_block(made, geo.BLOCK_WALL)
    place_u(made, 6)


# -------------------------------------------------------------------------- hoarding
def hoarding(length, seed, word="NUKA"):
    made = []
    f = gx.Frame((0.0, FACE, 0.0), 0.0)
    for x in (0.25, length / 2.0, length - 0.25):
        made += sx.lattice_post(gx.Frame((0.0, 0.25, 0.0), 0.0), x, 4.0, width=0.3, material=gx.iron(0.8, seed + int(x)), z0=0.0)
    z0, z1 = 1.5, 3.85
    panels = 4
    w = length / panels
    red = gx.paint("red", rust=0.3, seed=seed, fade=0.5, runs=0.5, scale=1.8, reach=0.8, lines=(z1,))
    for k in range(panels):
        if k == 2:
            made.append(geo.corrugated_panel(w - 0.03, z1 - z0 - 0.3, (k * w, FACE + 0.02, z0 + 0.1), 0.0, gx.tin(None, rust=0.6, seed=seed + k, top=z1 - z0), wavelength=0.12, roll=2.0,
                                             name="tin_panel"))
            continue
        material = red if k != 3 else gx.paint("yellow", rust=0.35, seed=seed + 3, fade=0.5, runs=0.5, scale=1.8)
        made.append(geo.box((w - 0.03, 0.035, z1 - z0 - (0.0, 0.05, 0.0, 0.2)[k]), (k * w + w / 2.0, FACE + 0.02, z0 + (0.0, 0.02, 0.0, 0.14)[k]), 0.0, material, bevel=0.006,
                            name="hoarding_panel", roll=(0.5, -0.7, 0.0, 3.0)[k]))
    white = mat.sign_paint((0.58, 0.56, 0.48), wear=0.3, seed=seed)
    made += [glyph for _, glyph, _, _ in sx.letters(word, f, w * 1.02, z0 + 0.55, 1.05, font="brush", material=white, d=0.012, depth=0.012, gap=0.02, seed=seed)]
    made.append(geo.box((w * 1.7, 0.012, 0.09), (w, FACE - 0.012, z0 + 0.3), 0.0, white, bevel=0.0, name="swash", roll=3.0))
    made += [glyph for _, glyph, _, _ in sx.letters("5", gx.Frame((0.0, FACE, 0.0), 0.0), w * 3.5, z0 + 0.7, 0.95, font="impact", material=mat.flat((0.03, 0.03, 0.03)), d=0.012,
                                                    depth=0.012, seed=seed + 1)]
    made += gx.bolts(f, [(k * w + dx, z) for k in range(panels) for dx in (0.1, w - 0.12) for z in (z1 - 0.12,)], d=0.03, radius=0.03, runs=0.9, seed=seed)
    made.append(gx.rail((0.0, 0.14, z0 + 0.05), (length, 0.14, z0), "pipe", seed + 5))
    made.append(gx.rail((0.0, 0.14, z1 - 0.1), (length, 0.14, z1 - 0.05), "pipe", seed + 6))
    # two dead floodlights on arms over the top
    for x in (length * 0.22, length * 0.7):
        made.append(geo.pipe([(x, 0.14, z1 - 0.1), (x, 0.0, z1 + 0.35), (x, -0.5, z1 + 0.45)], 0.025, mat.steel(rust=0.7, seed=3), name="lamp_arm"))
        made += gate.floodlight((x, -0.5, z1 + 0.42), (0.0, 0.6, -1.0), size=0.16, lit=False)
    # the wall under the hoarding: tin, a car door, planks
    r = geo.rng(seed)
    x, k = -0.04, 0
    while x < length - 0.1:
        wd = min(r.uniform(0.75, 0.98), length - x + 0.04)
        made.append(geo.corrugated_panel(wd, r.uniform(1.75, 2.1), (x, FACE + 0.08, 0.0), 0.0, gx.tin((None, "oxide", None, "olive")[k % 4], rust=r.uniform(0.45, 0.8), seed=seed + 10 + k, top=1.9),
                                         wavelength=0.12, tilt=r.uniform(-2, 2), roll=r.uniform(-2, 2), name="base_sheet"))
        x += wd - 0.07
        k += 1
    made += gx.put(gx.car_door("blue", seed + 7, glass="boards", rear=True), (length * 0.56, FACE - 0.0, 0.3), tilt=-2.0, roll=2.0)
    return geo.set_block(made, geo.BLOCK_WALL)


@piece("gr_wall_bill_u", title="Hoarding", desc="A roadside hoarding on lattice legs. Two panels still say what to drink; the others were needed elsewhere.",
       footprint=gx.wall_u_cells(6), **WALL_U)
def gr_wall_bill_u(ctx):
    place_u(hoarding(6 * HU, 781), 6)


@piece("gr_wall_bill_v", title="Hoarding", desc="A roadside hoarding on lattice legs, most of an advertisement still on it.",
       footprint=gx.col_hexes(0, 5), **WALL_V)
def gr_wall_bill_v(ctx):
    place_v(hoarding(6 * HV, 785, "COLA"))


# ------------------------------------------------------------------------ containers
def box_side(length, height, depth, colour, seed, code):
    """A shipping container seen side-on: canonical x 0 .. length, its long side on y = 0, body behind."""
    made = [geo.box((length, depth, height), (length / 2.0, depth / 2.0 + 0.04, 0.0), 0.0, gx.paint(colour, rust=0.45, seed=seed, scale=1.8), bevel=0.01, name="container")]
    made.append(geo.corrugated_panel(length - 0.3, height - 0.36, (0.15, 0.03, 0.18), 0.0, gx.tin(colour, rust=0.42, seed=seed + 1, top=height - 0.36, climb=0.4), wavelength=0.28,
                                     depth=0.06, name="container_side"))
    frame = gx.paint(tuple(c * 0.7 for c in gx.col(colour)), rust=0.55, seed=seed + 2)
    for z in (0.0, height - 0.18):
        made.append(geo.box((length, 0.08, 0.18), (length / 2.0, 0.0, z), 0.0, frame, bevel=0.01, name="rail"))
    for x in (0.08, length - 0.08):
        made.append(geo.box((0.16, 0.08, height), (x, 0.0, 0.0), 0.0, frame, bevel=0.01, name="corner_post"))
        for z in (0.0, height - 0.13):
            made.append(geo.box((0.18, 0.1, 0.13), (x, -0.005, z), 0.0, gx.iron(0.8, seed), bevel=0.0, name="casting"))
    f = gx.Frame((0.0, -0.04, 0.0), 0.0)
    made += [glyph for _, glyph, _, _ in sx.stencil(code, f, length * 0.7, height * 0.62, 0.32, colour=(0.56, 0.54, 0.46), d=0.03, seed=seed)]
    made.append(geo.box((length * 0.22, 0.012, 0.5), (length * 0.2, -0.045, height * 0.38), 0.0, mat.sign_paint((0.56, 0.54, 0.46), wear=0.5, seed=seed), bevel=0.0, name="logo",
                        roll=-28.0))
    for x in (length * 0.3, length * 0.62):
        made.append(gx.streak(f, x, height - 0.2, 1.1, 0.09, d=0.05))
    return made


@piece("gr_wall_cont_u", title="Container Wall", desc="A shipping container end to end along the wall, and a second one on top of it that the crane did not set down straight.",
       footprint=gx.wall_u_cells(6, deep=True), **WALL_U)
def gr_wall_cont_u(ctx):
    length = 6 * HU
    made = gx.put(box_side(length - 0.06, 2.59, 2.3, "oxide", 791, "MGTU 22"), (0.03, FACE, 0.0))
    made += gx.put(box_side(length * 0.74, 2.5, 2.3, "blue", 795, "KX 407"), (length * 0.2, FACE + 0.12, 2.6), rot=-3.0, roll=-1.5)
    made += gx.put(gx.drum("yellow", 797, band="black"), (0.4, FACE + 0.5, 2.6))
    made.append(geo.tire((0.35, FACE + 1.1, 2.6), lying=True, seed=3))
    for x in (0.55, length * 0.5):
        made.append(bx.beam((x, FACE - 0.02, 2.56), (x + 0.3, FACE - 0.02, 2.66), (0.14, 0.2), gx.wood(seed=798 + int(x), grey=0.3), name="chock"))
    made += spikes(length * 0.25, length * 0.9, 5.1, 799, y=FACE + 0.6)
    geo.set_block(made, geo.BLOCK_WALL)
    place_u(made, 6)


# ------------------------------------------------------------------- against the wall
def lean(length, seed, variant, wall=0.55):
    """Canonical: junk standing on y = 0 .. -0.3 and leaning back on a wall whose face is at y = +wall."""
    made = []
    if variant == "a":
        for k in range(3):
            made += gx.put(gx.pallet(seed + k, broken=(k == 1)), (0.55 + 0.1 * k, 0.12 - 0.12 * k, 0.56), tilt=-(72.0 - 4.0 * k), rot=3.0 * k)
        for k in range(2):
            made.append(geo.corrugated_panel(0.95, 2.1 - 0.2 * k, (1.25 + 0.5 * k, -0.02 - 0.06 * k, 0.0), 0.0, gx.tin((None, "teal")[k], rust=0.55 + 0.15 * k, seed=seed + 5 + k, top=2.1),
                                             wavelength=0.12, tilt=-(13.0 + 3.0 * k), roll=2.0 - 4.0 * k, name="leaning_sheet"))
        made += gate.ladder((length - 0.6, -0.25, 0.0), (length - 0.5, wall - 0.08, 2.3), width=0.42, material=gx.wood(seed=seed + 8, grey=0.45))
        made += gx.put(gx.drum("olive", seed + 9, rust=0.6), (length - 0.3, 0.12, 0.0))
        made.append(geo.tire((0.2, -0.05, 0.0), lying=True, seed=seed))
        made.append(geo.tire((0.22, -0.02, 0.21), lying=True, seed=seed + 1, lean=6.0))
    else:
        made += gx.put(gx.fridge(seed, colour="cream"), (0.45, 0.14, 0.0), rot=6.0, tilt=-5.0)
        made += gx.put(gx.car_door("black", seed + 1, glass="glass"), (0.95, -0.02, 0.0), tilt=-17.0, roll=2.0)
        made += gx.put(gx.car_door("orange", seed + 2, rear=True), (1.3, -0.12, 0.0), tilt=-20.0, roll=-3.0)
        made += gx.put(gx.bedstead(seed + 3), (length - 0.75, 0.08, 0.0), tilt=-15.0)
        made += gx.put(gx.road_sign("yield", seed + 4, post=1.9, bent=6.0), (length - 0.25, 0.1, 0.0), tilt=-10.0)
        made += gx.put(gx.crate((0.6, 0.5, 0.45), seed=seed + 5, mark="cream"), (length * 0.52, -0.3, 0.0), rot=14.0)
        made += gx.put(gx.cinder(seed + 6), (0.2, -0.4, 0.0), rot=30.0)
    return made


LEAN = dict(shadow="flat")


@piece("gr_lean_ua", title="Stored Against the Wall", desc="Pallets, two good sheets of tin and a ladder, leaning where the wall keeps the wind off them.",
       footprint=gx.row_hexes(0, 3), **LEAN)
def gr_lean_ua(ctx):
    gx.put(lean(4 * HU, 801, "a", wall=0.5), (3.5 * HU, -0.13, 0.0), rot=geo.U)


@piece("gr_lean_ub", title="Stored Against the Wall", desc="A refrigerator, two car doors and a bedstead, waiting for somebody to need them.",
       footprint=gx.row_hexes(0, 3), **LEAN)
def gr_lean_ub(ctx):
    gx.put(lean(4 * HU, 811, "b", wall=0.5), (3.5 * HU, -0.13, 0.0), rot=geo.U)


@piece("gr_lean_va", title="Stored Against the Wall", desc="Pallets, two good sheets of tin and a ladder, leaning where the wall keeps the wind off them.",
       footprint=gx.col_hexes(0, 3, 1), **LEAN)
def gr_lean_va(ctx):
    gx.put(lean(4 * HV, 821, "a", wall=0.5), (HU - 0.1, -HV, 0.0), rot=geo.V)


@piece("gr_lean_vb", title="Stored Against the Wall", desc="A refrigerator, two car doors and a bedstead, waiting for somebody to need them.",
       footprint=gx.col_hexes(0, 3, 1), **LEAN)
def gr_lean_vb(ctx):
    gx.put(lean(4 * HV, 831, "b", wall=0.5), (HU - 0.1, -HV, 0.0), rot=geo.V)
