# SPDX-License-Identifier: MIT
"""Scrap-wall accents for the perimeter near the gate. Each replaces a stretch of the stock fence.

Every piece is a WALL on hex row dhy = +1 of its origin (the town's wall rows are odd), N hexes
long (N even). It blocks those N hexes and the odd hexes of row 2 under its front, exactly like
the stock fence with its blockers. The gate ends on EVEN hexes on both sides (96 and 104), and a
piece's origin must be even, so there are two kinds:

  for the screen RIGHT of the gate (falling hx): covers dhx 0 .. N-1, origin = its right end
    mg_wall_bus     8 hexes   the side of a school bus, windows boarded, sunk to its axles
    mg_wall_cars    6 hexes   two tiers of car doors welded to a pipe frame (some glass gone:
                              you can see through)
  for the screen LEFT of the gate (rising hx): covers dhx 1 .. N, origin = the hex right of it
    mg_wall_hull    4 hexes   a barrel section of airliner fuselage lying on timber, windows
                              and airline stripe to the front; 1.5 m deep, blocks row 0 behind it
    mg_wall_boxes   8 hexes   three shipping-container ends, one stacked on the two others;
                              1.1 m deep, so it also blocks the even hexes of row 0 behind it

Frame: s = metres from the piece's screen-LEFT end towards the right, f = towards the viewer from
the wall line, z up (W(n) returns the point function for an n-hex piece).
"""
import math

from kit import piece, geo, mat, G
from kit import gate_extra as X


def W(n, first=0):
    row = X.Row(0, 1)
    length = n * X.HEX_R

    def point(s, f=0.0, z=0.0):
        return row.p(s - (first + n - 1) * X.HEX_R - X.HEX_R / 2.0, f, z)
    return point, length


def wall_footprint(n, first=0, deep=False):
    span = range(first, first + n)
    cells = [(d, 1) for d in span] + [(d, 2) for d in span if d & 1]
    if deep:
        cells += [(d, 0) for d in span if not d & 1]
    return cells


# ------------------------------------------------------------------------ bus
BUS_YELLOW = (0.40, 0.25, 0.05)


@piece("mg_wall_bus", title="Bus Wall", desc="The side of a school bus, sunk to its axles. The children got off a long time ago.",
       kind="wall", footprint=wall_footprint(8), see_through="u", shadow="none", overhang=1.2,
       convert={"contrast": 1.42, "saturation": 1.0})          # the gate set's grade (gate_main.py GRADE)
def mg_wall_bus(ctx):
    P, length = W(8)
    r = ctx.rng
    body = X.skin(tint=BUS_YELLOW, panel=(1.38, 0.9), rust=0.55, grime=0.75, seed=14.0, metallic=0.0, tone=0.3, stagger=False,
                  bands=[("v", 0.60, 0.74, (0.03, 0.03, 0.03)), ("v", 0.10, 0.16, (0.03, 0.03, 0.03))])
    roof = X.skin(tint=(0.38, 0.25, 0.06), panel=(1.38, 0.6), rust=0.6, grime=0.8, seed=15.0, metallic=0.0, tone=0.25, stagger=False)
    dark = mat.painted_metal((0.03, 0.03, 0.03), flaking=0.5, seed=3)
    z0, sill, head, top = 0.22, 1.42, 2.12, 2.48
    f0 = 0.14                                             # front face
    # lower body, window pillars, roof band, rounded roof shoulder
    X.plate(length - 0.08, sill - z0, P(0.04, f0, z0), geo.U, body, thickness=0.06, name="bus_side", dent=0.006, seed=2)
    X.plate(length - 0.08, top - head, P(0.04, f0, head), geo.U, roof, thickness=0.06, name="bus_band", uv_offset=(0.0, 1.9))
    X.barrel_shell(0.26, length - 0.08, a0=0.0, a1=95.0, at=P(0.04, f0 - 0.26, top), rot=geo.U, material=roof, thickness=0.05,
                   segments=8, name="bus_roof", uv_offset=(0.0, 2.3))
    geo.box((length - 0.12, 0.5, 0.05), P(length / 2, f0 - 0.5, top + 0.22), geo.U, roof, bevel=0.01, name="bus_top")
    geo.box((length - 0.2, 0.2, top - z0 - 0.1), P(length / 2, f0 - 0.4, z0), geo.U, mat.flat((0.012, 0.012, 0.012)), bevel=0.0,
            name="bus_dark")                              # the dark inside, seen through the one open window
    count = 6
    pitch = (length - 0.5) / count
    wood = mat.planks(colour=(0.24, 0.14, 0.07), width=0.12, axis="Z", seed=4)
    fills = ["boards", "glass", "sheet", "open", "boards", "glass"]
    for k in range(count + 1):
        geo.box((0.13, 0.07, head - sill + 0.02), P(0.25 + k * pitch, f0 - 0.005, sill - 0.01), geo.U, body, bevel=0.015, name="bus_pillar")
    for k, fill in enumerate(fills):
        s = 0.25 + (k + 0.5) * pitch
        w = pitch - 0.14
        if fill == "glass":
            geo.box((w, 0.02, head - sill), P(s, f0 - 0.02, sill), geo.U, mat.glass(dirt=0.8), bevel=0.0, name="bus_glass")
        elif fill == "boards":
            for j in range(3):
                geo.box((w + 0.16, 0.03, 0.19), P(s + r.uniform(-0.03, 0.03), f0 + 0.03, sill + 0.03 + j * 0.23), geo.U, wood,
                        bevel=0.006, name="bus_board", roll=r.uniform(-4, 4))
        elif fill == "sheet":
            geo.corrugated_panel(w + 0.2, head - sill + 0.2, P(s - w / 2 - 0.1, f0 + 0.04, sill - 0.12), geo.U,
                                 mat.corrugated(rust=0.75, seed=9), roll=3.0, name="bus_sheet")
    # wheels in their arches, tyres flat
    for s in (1.05, length - 1.25):
        geo.box((1.02, 0.03, 0.56), P(s, f0 + 0.02, z0 - 0.04), geo.U, dark, bevel=0.14, name="wheel_arch")
        geo.tire(P(s, f0 + 0.12, -0.14), radius=0.46, width=0.26, lying=False, rot=geo.U, lean=0.0, seed=int(s * 10))
        geo.cylinder(0.2, 0.05, P(s, f0 + 0.27, 0.32), mat.steel(rust=0.8, seed=5), segments=14, name="hub", tilt=90.0, rot=geo.U)
    # lettering over the windows and what is left of the stop arm
    geo.lettering("SCHOOL BUS", P(length / 2 + 0.3, f0 + 0.045, head + 0.07), geo.U, size=0.25, depth=0.012, bevel=0.0, font="black",
                  material=mat.sign_paint((0.03, 0.03, 0.03), wear=0.45, seed=6), spacing=1.05)
    geo.box((0.34, 0.03, 0.34), P(0.62, f0 + 0.06, 1.02), geo.U + 0.0, mat.painted_metal((0.45, 0.04, 0.03), flaking=0.3, seed=7), bevel=0.09,
            name="stop_arm", roll=22.5)
    # bumper end towards the screen left, skirt dirt, a row of rebar spikes along the roof
    geo.box((0.1, 0.5, 0.2), P(0.0, f0 - 0.2, 0.42), geo.U, mat.steel(rust=0.6, seed=8), bevel=0.02, name="bumper")
    spike = mat.steel(rust=0.85, seed=2)
    s = 0.3
    while s < length - 0.2:
        h = r.uniform(0.28, 0.5)
        geo.pipe([P(s, f0 - 0.3, top + 0.2), P(s + r.uniform(-0.05, 0.05), f0 - 0.3 + r.uniform(-0.04, 0.08), top + 0.26 + h)], 0.028, spike,
                 name="spike")
        s += r.uniform(0.3, 0.5)


# ------------------------------------------------------------------ car doors
DOOR_PAINTS = [(0.26, 0.05, 0.03), (0.12, 0.17, 0.21), (0.40, 0.35, 0.24), (0.11, 0.15, 0.08), (0.045, 0.045, 0.05),
               (0.40, 0.17, 0.035), (0.26, 0.27, 0.28), (0.08, 0.16, 0.15)]


def car_door(P, s, z, width, height, colour, seed, flip=False, glass="none", roll=0.0, f=0.1):
    """One car door standing in the wall plane, s = its left edge, z = its bottom. flip: upside down."""
    paint = mat.painted_metal(colour, flaking=0.62, seed=seed)
    panel_h = height * 0.56
    win_h = height - panel_h
    bar = 0.075
    zp, zw = (z + win_h, z) if flip else (z, z + panel_h)
    geo.box((width - 0.02, 0.07, panel_h - 0.01), P(s + width / 2, f, zp), geo.U, paint, bevel=0.03, name="door_panel", roll=roll)
    # window frame: two pillars, a rail; the front pillar raked like a windscreen post
    geo.box((bar, 0.05, win_h), P(s + bar / 2 + 0.01, f, zw), geo.U, paint, bevel=0.015, name="door_pillar", roll=roll)
    geo.box((bar, 0.05, win_h + 0.03), P(s + width - bar / 2 - 0.09, f, zw - 0.015), geo.U, paint, bevel=0.015, name="door_pillar",
            roll=roll + (-12.0 if not flip else 12.0))
    geo.box((width - 0.14, 0.05, bar), P(s + width / 2 - 0.05, f, zw if flip else zw + win_h - bar), geo.U, paint, bevel=0.015,
            name="door_rail", roll=roll)
    if glass != "none":
        material = mat.glass(dirt=0.9) if glass == "glass" else mat.planks(colour=(0.22, 0.13, 0.07), width=0.12, axis="X", seed=seed)
        geo.box((width - 0.22, 0.02, win_h - bar - 0.02), P(s + width / 2 - 0.04, f - 0.01, zw + (0.0 if not flip else bar)), geo.U, material,
                bevel=0.0, name="door_glass", roll=roll)
    # handle and a trim strip: the two bright things on a door
    hz = zp + (panel_h - 0.14 if not flip else 0.10)
    geo.box((0.16, 0.03, 0.04), P(s + 0.18, f + 0.045, hz), geo.U, X.bright_metal(), bevel=0.008, name="door_handle")
    geo.box((width - 0.1, 0.02, 0.035), P(s + width / 2, f + 0.04, zp + panel_h * 0.42), geo.U, X.bright_metal((0.38, 0.38, 0.39), 0.45),
            bevel=0.0, name="door_trim", roll=roll)


@piece("mg_wall_cars", title="Car-door Wall", desc="Car doors, welded edge to edge on a frame of pipe. Two of them still wind down.",
       kind="wall", footprint=wall_footprint(6), see_through="u", shadow="none", overhang=1.2,
       convert={"contrast": 1.42, "saturation": 0.95})
def mg_wall_cars(ctx):
    P, length = W(6)
    r = ctx.rng
    steel = mat.steel(rust=0.7, seed=6)
    # the frame behind: posts and two rails
    for s in (0.08, length / 2, length - 0.08):
        geo.ibeam(2.5, P(s, -0.06, 0.0), geo.U, steel, vertical=True, height=0.13, width=0.11)
    for z in (0.55, 1.75):
        geo.pipe([P(0.0, 0.02, z), P(length, 0.02, z)], 0.045, steel, name="frame_rail")
    # two tiers of doors
    tiers = [(0.04, 1.14, [1.02, 1.10, 0.96, 1.04]), (1.20, 1.10, [0.90, 1.06, 1.08, 0.98])]
    glass = [["glass", "none", "boards", "glass"], ["none", "glass", "none", "boards"]]
    k = 0
    for t, (z, height, widths) in enumerate(tiers):
        scale = (length - 0.04) / sum(widths)
        s = 0.02
        for i, w in enumerate(widths):
            w *= scale
            car_door(P, s, z + r.uniform(-0.02, 0.03), w - 0.015, height + r.uniform(-0.05, 0.03), DOOR_PAINTS[(k * 3 + t) % len(DOOR_PAINTS)],
                     seed=20 + k, flip=(k % 3 == 1), glass=glass[t][i], roll=r.uniform(-1.5, 1.5), f=0.10 + 0.02 * ((i + t) % 2))
            s += w
            k += 1
    # welded-on extras: a bonnet as a cap at one end, hubcaps, a bumper along the top
    geo.box((1.25, 0.05, 0.62), P(0.75, 0.16, 2.02), geo.U, mat.painted_metal((0.20, 0.045, 0.03), flaking=0.6, seed=31), bevel=0.06,
            name="bonnet", roll=4.0, tilt=-6.0)
    for s, z in ((1.72, 1.02), (3.55, 2.02)):
        geo.cylinder(0.19, 0.04, P(s, 0.19, z), X.bright_metal((0.46, 0.46, 0.47), 0.35), segments=16, name="hubcap", tilt=90.0, rot=geo.U)
    geo.pipe([P(1.5, 0.1, 2.36), P(length - 0.1, 0.1, 2.42)], 0.06, X.bright_metal((0.36, 0.36, 0.37), 0.45), name="bumper")
    for s in (0.3, 1.2, 2.3, 3.1, 3.9):
        geo.pipe([P(s, -0.02, 2.3), P(s + r.uniform(-0.06, 0.06), 0.0, 2.3 + r.uniform(0.35, 0.6))], 0.028, steel, name="spike")


# ----------------------------------------------------------------- containers
def container_end(P, s, z, colour, seed, code, width=2.44, height=2.59, depth=1.1):
    """The door end of a shipping container: s = its left edge, z = its floor."""
    paint = mat.painted_metal(colour, flaking=0.4, seed=seed)
    frame = mat.painted_metal(tuple(c * 0.7 for c in colour), flaking=0.55, seed=seed + 1)
    f0 = 0.10
    geo.box((width, depth, height), P(s + width / 2, f0 - depth / 2 - 0.02, z), geo.U, paint, bevel=0.012, name="container")
    # corner posts, sill and header stand proud of the doors
    for ds in (0.07, width - 0.07):
        geo.box((0.14, 0.06, height), P(s + ds, f0, z), geo.U, frame, bevel=0.01, name="corner_post")
    for dz in (0.0, height - 0.16):
        geo.box((width, 0.06, 0.16), P(s + width / 2, f0, z + dz), geo.U, frame, bevel=0.01, name="door_header")
    for ds in (0.0, width - 0.17):
        for dz in (0.0, height - 0.12):
            geo.box((0.17, 0.09, 0.12), P(s + ds + 0.085, f0, z + dz), geo.U, mat.steel(rust=0.8, seed=seed), bevel=0.0, name="casting")
    # two door leaves of ribbed sheet, four locking bars with their handles
    leaf_w = (width - 0.30) / 2
    for i in range(2):
        geo.corrugated_panel(leaf_w, height - 0.34, P(s + 0.14 + i * (leaf_w + 0.02), f0 + 0.005, z + 0.17), geo.U,
                             mat.corrugated(paint=colour, rust=0.3 + 0.12 * i, seed=seed * 3 + i), wavelength=0.46, depth=0.05,
                             horizontal=True, name="container_door")
    bar = X.bright_metal((0.30, 0.30, 0.31), 0.5)
    for ds in (0.42, 0.98, width - 0.98, width - 0.42):
        geo.pipe([P(s + ds, f0 + 0.06, z + 0.1), P(s + ds, f0 + 0.06, z + height - 0.1)], 0.03, bar, name="lock_bar")
        geo.box((0.26, 0.03, 0.05), P(s + ds + 0.08, f0 + 0.09, z + 1.05), geo.U, bar, bevel=0.0, name="lock_handle")
    geo.lettering(code, P(s + width - 0.72, f0 + 0.045, z + height - 0.52), geo.U, size=0.2, depth=0.01, bevel=0.0, font="din",
                  material=mat.sign_paint((0.62, 0.60, 0.52), wear=0.5, seed=seed))


@piece("mg_wall_boxes", title="Container Wall", desc="Shipping containers, stood on end to end and filled with rubble. Nobody is moving these.",
       kind="wall", footprint=wall_footprint(8, 1, deep=True), see_through="u", shadow="none", overhang=1.4,
       convert={"contrast": 1.42, "saturation": 0.92})         # 0.92: the yellow box bleaches to the palette's tan
def mg_wall_boxes(ctx):
    P, length = W(8, 1)
    container_end(P, 0.06, 0.0, (0.26, 0.065, 0.035), 3, "KXU 407")
    container_end(P, length - 2.50, 0.0, (0.11, 0.17, 0.22), 5, "MGT 113")
    container_end(P, 1.42, 2.60, (0.42, 0.25, 0.05), 7, "DC 0-77")
    # the gap between the two lower boxes: tyres and a girder, and sandbags on the left roof
    x, y, _ = P(length / 2 - 0.2, -0.05)
    geo.tire_stack(5, (x, y, 0.0), seed=8, radius=0.3)
    geo.ibeam(2.6, P(length / 2 + 0.12, 0.0, 0.0), geo.U, mat.steel(rust=0.8, seed=4), vertical=True, height=0.2, width=0.16)
    X.sandbags(P(0.2, -0.1)[:2], P(1.3, -0.1)[:2], courses=2, z=2.6, seed=7)
    geo.barrel(P(length - 0.6, -0.4, 2.6), seed=12)


# ------------------------------------------------------------------- fuselage
@piece("mg_wall_hull", title="Fuselage Wall", desc="A length of airliner, rolled up to the wall and chocked with timber. Row 14, seats A to F.",
       kind="wall", footprint=wall_footprint(4, 1, deep=True) + [(1, 0), (3, 0)], see_through="u", shadow="none", overhang=1.8,
       convert={"contrast": 1.42, "saturation": 1.0})
def mg_wall_hull(ctx):
    P, length = W(4, 1)
    radius = 1.45
    axis_f, axis_z = 0.12 - radius, radius + 0.08
    red = (0.30, 0.055, 0.035)
    hull = X.skin(tint=(0.50, 0.51, 0.52), panel=(0.52, 0.80), rust=0.16, grime=0.5, seed=17.0, tone=0.2, stagger=False,
                  bands=[("v", 1.62, 1.92, red), ("v", 1.96, 2.01, (0.05, 0.05, 0.06)), ("v", 0.0, 1.05, (0.12, 0.13, 0.14))])
    a0 = -72.0
    X.barrel_shell(radius, length - 0.04, a0=a0, a1=118.0, at=P(0.02, axis_f, axis_z), rot=geo.U, material=hull, thickness=0.05,
                   segments=30, name="hull")
    # cabin windows above the stripe (arc position: 1.92 .. 2.4 m from the lower edge)
    frame = X.bright_metal((0.50, 0.51, 0.52), 0.4)
    for k in range(5):
        s = 0.34 + k * 0.52
        a_mid = a0 + math.degrees(2.36 / radius)
        for rad, half_a, half_s, material in ((radius + 0.035, 9.5, 0.17, frame), (radius + 0.05, 7.0, 0.12, mat.flat((0.012, 0.016, 0.02), roughness=0.15))):
            X.barrel_shell(rad, half_s * 2, a0=a_mid - half_a, a1=a_mid + half_a, at=P(0.0, axis_f, axis_z), rot=geo.U, material=material,
                           thickness=0.02, segments=5, name="hull_window", x0=s - half_s, block=False)
    # the cut ends: ring frames; the end towards the screen left is closed with a bulkhead
    ring = mat.steel(rust=0.5, seed=5)
    for s in (0.0, length - 0.1):
        X.barrel_shell(radius - 0.06, 0.1, a0=a0, a1=118.0, at=P(0.0, axis_f, axis_z), rot=geo.U, material=ring, thickness=0.14, segments=30,
                       name="ring_frame", x0=s, block=False)
    X.disc_sector(radius - 0.05, a0, 118.0, at=P(0.0, axis_f, axis_z), rot=geo.U, x=0.03, thickness=0.05,
                  material=X.skin(tint=(0.20, 0.23, 0.10), panel=(0.5, 0.5), rust=0.4, seed=19.0, uv=False, metallic=0.0))
    # timber cribbing under the belly, wedges, a tyre
    wood = mat.planks(colour=(0.24, 0.14, 0.07), axis="X", width=0.4, seed=6)
    for s in (0.45, length - 0.5):
        for j in range(3):
            geo.box((0.24, 1.0 - j * 0.22, 0.17), P(s, -0.38 + j * 0.06, j * 0.17), geo.U, wood, bevel=0.012, name="crib")
    geo.tire(P(length / 2, -0.12, 0.0), radius=0.4, lying=False, rot=geo.U + 12.0, lean=10.0, seed=3)
