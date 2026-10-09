# SPDX-License-Identifier: MIT
"""More height: lane footbridges, the gate's watch tower, a stacked container, two more annexes. (author "height")

    piece              where it goes
    ht_bridge_v_a/b/c  a footbridge ALONG A HEX COLUMN over a lane five rows wide, from the eave of one
                       building (front wall on row hy0) to the roof of the next (back wall on row hy0 + 6).
                       Origin = (even hx, hy0 + 3), two hexes or more inside both buildings' hx range.
                       Blocks nothing: the lane under it stays a lane. Seen from the camera it lies over
                       the FAR building's front wall from the origin column to four hexes right of it,
                       so no door, window or sign may be there (the playability check names them).
                       Its rails start low at the far end and reach full height 2.4 m out: anything
                       taller, nearer that roof, would be painted over by it (roofs come last).
    ht_tower_gate      the watch tower by the gate: 2 x 2 posts like the other towers (origin = the
                       back-right post, the rest on (2, 0) (0, 2) (2, 2)), an armoured cab with a sentry,
                       a gun on the parapet and a searchlight. A lamp. 6 m: nothing to click within 13
                       rows behind it.
    ht_upper_e         6 hexes, placed like the other ht_upper_* (origin on row hy_lo - 3 behind a
                       building): a shipping container on the stilts with a tin hutch on its roof.
    ht_shed_v_b        against a LEFT wall like ht_shed_v_a (origin on column hx + 2, even hy), 5 rows:
                       a plank lean-to, its near end open over a work bench.
    ht_shed_u_c        against a FRONT wall like ht_shed_u_a (origin on row hy + 1), 3 hexes: a rain butt
                       on a stand under a scrap of roof, fed from the eave.
"""
import math

from kit import piece, geo, mat, G
from kit import height_extra as H
from kit import bomb_extra as bx
from kit import gate_extra as X
from kit import signs_extra as sx

HEX = H.HEX
ROW = H.ROW
WALL_U = -0.8 + G.STOCK_WALL_FRONT_U + 0.01       # y of a front wall's face, seen from the row in front of it
WALL_V = -G.SQ_U_M + G.STOCK_WALL_FRONT_V + 0.01  # x of a left wall's face, seen from the column two hexes left


# ============================================================================ lane footbridges
BR_Z = 2.76
BR_FAR, BR_NEAR = -3.0 * ROW, 3.0 * ROW           # the two wall lines
BR_Y0, BR_Y1 = BR_FAR + 0.62, BR_NEAR - 0.5       # deck: from under the far eave onto the near roof's back edge
BR_FULL = BR_FAR + 0.82 + 2.45                    # from here on a 0.95 m rail clears the far roof


def _rail_v(x, seed, kind="pipe", infill=None):
    """One side of a lane bridge: a rope climbing from the deck at the far end to a full-height
    stanchion, then a proper rail to the near end."""
    top = BR_Z + 0.95
    geo.pipe([(x, BR_FULL, BR_Z - 0.1), (x, BR_FULL, top + 0.04)], 0.028, H.tube(0.7, 2.0 + seed), name="stanchion")
    half = (BR_Y0 + BR_FULL) / 2.0
    geo.pipe([(x, half, BR_Z - 0.1), (x, half, BR_Z + 0.95 * (half - BR_Y0) / (BR_FULL - BR_Y0) - 0.02)], 0.024, H.tube(0.7, 4.0 + seed),
             name="stanchion")
    for share in (1.0, 0.5):                                 # the climbing ropes
        geo.pipe([(x, BR_Y0 + 0.08, BR_Z + 0.03), (x, BR_FULL, BR_Z + 0.95 * share)], 0.016, mat.flat((0.20, 0.15, 0.09)), name="rope")
    H.rail((x, BR_FULL), (x, BR_Y1 - 0.02), BR_Z, 0.95, kind, seed, posts=2, infill=infill, mid=kind != "rope")
    bx.plank((x, BR_Y0, BR_Z + 0.06), (x, BR_FULL, BR_Z + 0.06), 0.12, 0.035, H.wood(1, axis="X", width=0.6), name="kerb", roll=90.0)


def _bridge_v(seed, rails=("pipe", "rope"), infill=(None, None), pipe=None, lamp=True, wash=False, boards=0.24):
    r = geo.rng(seed)
    x0, x1 = -0.5, 0.5
    for x in (-0.36, 0.36):                                  # two bearers from wall head to wall head
        bx.beam((x, BR_Y0 - 0.12, BR_Z - 0.12), (x, BR_Y1 + 0.12, BR_Z - 0.12), (0.1, 0.16), H.wood(3, axis="X", width=0.6), name="bearer")
        H.brace((x, BR_FAR + G.STOCK_WALL_FRONT_U + 0.03, 1.8), (x, BR_FAR + 1.1, BR_Z - 0.2), 0.028)      # knee braces off the far wall
    H.deck(x0, BR_Y0, x1, BR_Y1, BR_Z, along="x", seed=seed, board=boards, plates=1, missing=0.1, joists=False)
    _rail_v(x1 - 0.03, seed, rails[0], infill[0])            # the side towards the camera
    _rail_v(x0 + 0.03, seed + 3, rails[1], infill[1])
    if pipe:                                                 # a water main slung under the near edge
        z = BR_Z - 0.34
        H.pipe_run([(x1 - 0.1, BR_Y0 - 0.1, z), (x1 - 0.1, BR_Y1 + 0.1, z)], 0.075, pipe, seed, flanges=False)
        for y in (BR_Y0 + 0.5, 0.1, BR_Y1 - 0.5):
            H.strap([(x1 - 0.02, y, BR_Z - 0.05), (x1 - 0.2, y, z - 0.09), (x1 - 0.02, y, z - 0.02)], 0.03)
        H.dots([(x1 - 0.1, -0.6, z)], 0.2, H.tube(0.6, 1.0), name="flange")
    if lamp:
        geo.pipe([(0.0, 0.5, BR_Z - 0.1), (0.0, 0.5, BR_Z - 0.3)], 0.012, mat.flat((0.03, 0.03, 0.03)), name="flex")
        H.lamp((0.0, 0.5, BR_Z - 0.3))
    if wash:                                                 # washing on a line under the far edge
        f = H.face((x0 + 0.12, BR_Y0 + 0.5, 0.0), geo.V)
        geo.cable((x0 + 0.12, BR_Y0 + 0.4, BR_Z - 0.26), (x0 + 0.12, BR_Y1 - 0.3, BR_Z - 0.3), 0.08, 0.014)
        u, k = 0.1, 0
        while u < (BR_Y1 - BR_Y0) - 1.3:
            w = r.uniform(0.35, 0.55)
            colour = ((0.40, 0.13, 0.08), (0.36, 0.33, 0.26), (0.10, 0.17, 0.22), (0.30, 0.22, 0.08))[(k + seed) % 4]
            sx.cloth(f, u, BR_Z - 0.36, w, r.uniform(0.4, 0.62), sx.fabric(colour, seed=float(seed + k)), folds=2.0, depth=0.03, seed=seed + k)
            u += w + r.uniform(0.2, 0.45)
            k += 1
    # a cable looped from rail to rail, as everywhere
    geo.cable((x1 - 0.03, BR_FULL, BR_Z + 0.95), (x1 - 0.03, BR_Y1 - 0.05, BR_Z + 0.9), r.uniform(0.15, 0.25), 0.016)


BRIDGE_V = dict(footprint=[], see_through=True, shadow="flat", material="wood", overhang=0.5, convert=H.GRADE)
BRIDGE_V_DESC = "Planks from one roof to the next, over the lane. The rail is rope where it starts and pipe where somebody fell off."


@piece("ht_bridge_v_a", title="Footbridge", desc=BRIDGE_V_DESC, light=(4, 70), light_hex=(0, 0), **BRIDGE_V)
def ht_bridge_v_a(ctx):
    _bridge_v(11, rails=("pipe", "rope"), infill=("sheet", None), pipe=H.TEAL)
    H.junk("can", (-0.2, 1.3, BR_Z), 1)


@piece("ht_bridge_v_b", title="Footbridge", desc=BRIDGE_V_DESC, **BRIDGE_V)
def ht_bridge_v_b(ctx):
    _bridge_v(12, rails=("wood", "wood"), infill=(None, "planks"), pipe=None, lamp=False, wash=True, boards=0.3)
    H.junk("bucket", (0.15, 1.45, BR_Z), 2)


@piece("ht_bridge_v_c", title="Footbridge", desc=BRIDGE_V_DESC, light=(4, 70), light_hex=(0, 0), **BRIDGE_V)
def ht_bridge_v_c(ctx):
    _bridge_v(13, rails=("pipe", "pipe"), infill=(None, None), pipe=H.RED)
    # a tarp tied over the near rail and a crate somebody left on the deck
    sx.sag_sheet([(0.47, BR_FULL + 0.05, BR_Z + 0.93), (0.47, BR_Y1 - 0.1, BR_Z + 0.93), (0.52, BR_Y1 - 0.1, BR_Z + 0.15), (0.52, BR_FULL + 0.05, BR_Z + 0.2)],
                 H.cloth((0.12, 0.17, 0.20), seed=4.0), sag=0.04, seed=3)
    H.junk("box", (-0.15, 0.2, BR_Z), 3)


# ============================================================================ the gate's watch tower
X1, Y1 = G.hex_xy(2, 2)
LEGS = [(0.0, 0.0), (X1, 0.0), (0.0, Y1), (X1, Y1)]
FOOT = H.uniq(H.hexes_in(-0.05, -0.05, X1 + 0.05, Y1 + 0.05))
CX, CY = X1 / 2.0, Y1 / 2.0


def _ring(z, kind="timber", out=0.14):
    for a, b in ((LEGS[2], LEGS[3]), (LEGS[3], LEGS[1]), (LEGS[0], LEGS[1]), (LEGS[0], LEGS[2])):
        (ax, ay), (bx_, by) = a, b
        length = math.hypot(bx_ - ax, by - ay)
        ux, uy = (bx_ - ax) / length, (by - ay) / length
        p0, p1 = (ax - ux * out, ay - uy * out, z), (bx_ + ux * out, by + uy * out, z)
        if kind == "timber":
            bx.beam(p0, p1, (0.14, 0.08), H.wood(1, axis="X", width=0.6), name="girt", roll=90.0)
        else:
            geo.pipe([p0, p1], 0.04, H.tube(0.75, 5.0), name="girt")


@piece("ht_tower_gate", title="Gate Tower",
       desc="The gate's watch tower: tree trunks, a cab plated with whatever would stop a bullet, a gun on the parapet and a man behind it.",
       footprint=FOOT, see_through=True, shadow="flat", material="metal", light=(6, 80), light_hex=(2, 2), convert=H.GRADE)
def ht_tower_gate(ctx):
    mid, deck = 1.95, 3.55
    for k, (x, y) in enumerate(LEGS):
        H.post(x, y, 0.0, deck + (1.95 if k < 2 else 1.7), "pole" if k != 1 else "beam", k + 3, lean=(0.015 * (1 - 2 * (k % 2)), 0.0))
        H.dots([(x, y + 0.09, mid - 0.05), (x, y + 0.09, deck - 0.3)], 0.07)
    _ring(mid - 0.1, "timber")
    _ring(deck - 0.16, "timber", out=0.3)
    H.xbrace(LEGS[2], LEGS[3], 0.2, mid - 0.25, 0.03)
    H.xbrace(LEGS[3], LEGS[1], 0.2, mid - 0.25, 0.03)
    H.xbrace(LEGS[2], LEGS[3], mid + 0.1, deck - 0.3, 0.028, single=True)
    H.xbrace(LEGS[3], LEGS[1], mid + 0.1, deck - 0.3, 0.028, single=True)
    H.xbrace(LEGS[0], LEGS[1], 0.3, deck - 0.3, 0.026, single=True)
    # a half landing where the ladder changes sides, with the watch's stores on it
    H.deck(-0.1, 0.25, X1 + 0.1, Y1 + 0.12, mid, along="y", seed=8, board=0.26, plates=0, missing=0.12, joists=False)
    H.junk("barrel", (0.4, 0.75, mid), 2)
    H.junk("box", (1.0, 1.1, mid), 4)
    # hazard board on the front girt and two tyres hung on the legs as fenders
    X.plate(X1 + 0.2, 0.34, (X1 + 0.1, Y1 + 0.1, mid - 0.32), geo.U, X.hazard(width=0.32, wear=0.65, seed=5.0), thickness=0.02, name="hazard_board")
    geo.tire((X1 + 0.02, Y1 + 0.2, 1.0), radius=0.33, lying=False, rot=geo.U + 90.0, lean=6.0, seed=3)
    geo.tire((0.05, Y1 + 0.2, 0.75), radius=0.3, lying=False, rot=geo.U + 90.0, lean=-5.0, seed=5)
    # the cab deck, wider than the legs, on two bearers
    for y in (0.0, Y1):
        bx.beam((-0.45, y, deck - 0.07), (X1 + 0.45, y, deck - 0.07), (0.18, 0.14), H.wood(3, axis="X", width=0.6), name="bearer")
    H.deck(-0.45, -0.3, X1 + 0.45, Y1 + 0.45, deck, along="y", seed=9, board=0.25, plates=1, joists=False)
    # armour: chest-high plate on the front and left, a car door, a firing slit cut in a taller plate
    ff = H.face((X1 + 0.42, Y1 + 0.4, 0.0), geo.U)
    fl = H.face((X1 + 0.42, -0.26, 0.0), geo.V)
    wf, wl = X1 + 0.84, Y1 + 0.66
    H.scrap_wall(ff, 0.0, wf, deck, deck + 1.02, 0.0, 61, "pphp", (H.SLATE, H.GREEN, H.OCHRE), 0.65, ragged=0.14, patches=2, tiers=1)
    H.scrap_wall(fl, 0.0, wl, deck, deck + 1.02, 0.0, 62, "pvp", (H.RED, H.SLATE, H.CREAM), 0.65, ragged=0.14, patches=1, tiers=1)
    H.sheet(ff, wf - 0.95, deck + 0.55, 0.9, 1.05, 0.03, "p", H.GREEN, 0.6, 7)           # the tall plate with the slit
    geo.box((0.5, 0.03, 0.1), ff.at(wf - 0.5, 0.045, deck + 1.2), geo.U, H.dark(), bevel=0.0, name="slit")
    H.patch(fl, 0.25, deck + 0.3, 0.6, 0.5, 0.04, H.OCHRE, 0.7, 9, kind="h")
    sx.stencil("M-1", ff, wf * 0.36, deck + 0.42, 0.26, colour=(0.62, 0.58, 0.46), d=0.03, wear=0.6, seed=4)
    X.sandbags((X1 + 0.3, Y1 + 0.3), (0.55, Y1 + 0.3), courses=1, z=deck + 1.0, seed=11, size=(0.5, 0.3, 0.16))
    X.sandbags((X1 + 0.3, 0.0), (X1 + 0.3, Y1 + 0.2), courses=1, z=deck + 1.0, seed=12, size=(0.5, 0.3, 0.16))
    # the gun: a pintle on the front parapet, the barrel out over the track
    pin = (0.35, Y1 + 0.34, deck + 1.05)
    geo.pipe([(pin[0], pin[1], deck + 0.7), (pin[0], pin[1], pin[2] + 0.12)], 0.035, H.tube(0.4, 1.0), name="pintle")
    gun = mat.flat((0.035, 0.035, 0.04))
    geo.pipe([(pin[0] + 0.3, pin[1] - 0.22, pin[2] + 0.2), (pin[0] - 0.75, pin[1] + 0.5, pin[2] + 0.05)], 0.034, gun, name="barrel")
    geo.box((0.42, 0.12, 0.16), (pin[0] + 0.22, pin[1] - 0.17, pin[2] + 0.1), geo.U + 34.0, gun, bevel=0.01, name="receiver")
    H.junk("box", (pin[0] + 0.5, pin[1] - 0.4, deck), 1)
    # the sentry: enough of a man to read as one above the plate
    sy_ = Y1 + 0.08
    geo.box((0.44, 0.26, 0.62), (CX + 0.25, sy_, deck + 0.85), 12.0, mat.flat((0.30, 0.19, 0.10)), bevel=0.05, name="sentry_coat")
    geo.cylinder(0.105, 0.2, (CX + 0.25, sy_, deck + 1.47), mat.flat((0.60, 0.38, 0.25)), 10, name="sentry_head")
    sx.cone(0.16, 0.13, (CX + 0.25, sy_, deck + 1.62), mat.flat((0.10, 0.11, 0.08)), name="sentry_helmet", top=0.07)
    geo.box((0.5, 0.2, 0.14), (CX + 0.25, sy_ + 0.02, deck + 1.36), 12.0, mat.flat((0.26, 0.17, 0.09)), bevel=0.04, name="sentry_shoulders")
    # roof: tin on the leg heads, falling to the front, a tarp hung down the back as a wind break
    top = H.face((X1 + 0.38, Y1 + 0.3, 0.0), geo.U)
    H.lean_roof(top, 0.0, X1 + 0.76, -(Y1 + 0.6), 0.25, deck + 2.0, deck + 1.72, 63, (H.OCHRE, None, H.TEAL, None), 0.6, weights=2, over=0.14)
    sx.sag_sheet([(-0.08, -0.04, deck + 1.82), (X1 + 0.08, -0.04, deck + 1.82), (X1 + 0.08, -0.1, deck + 0.9), (-0.08, -0.1, deck + 0.9)],
                 H.cloth((0.20, 0.15, 0.09), seed=6.0), sag=0.04, seed=8)
    # searchlight on an arm off the front-left leg, a caged lamp under the roof
    head = (X1 + 0.5, Y1 + 0.55, deck + 1.5)
    geo.pipe([(X1, Y1, deck + 1.1), (X1 + 0.3, Y1 + 0.3, deck + 1.3), head], 0.03, H.tube(0.5, 2.0), name="lamp_arm")
    H.flood(head, (0.7, 0.85, -0.5), size=0.2)
    H.lamp((CX - 0.2, Y1 - 0.25, deck + 1.66))
    # flag: a staff lashed to the back-left leg, the rag of a flag on it
    staff = (X1 + 0.05, 0.02)
    geo.pipe([(staff[0], staff[1], deck + 1.3), (staff[0] + 0.03, staff[1], deck + 2.42)], 0.02, H.tube(0.4, 1.0), name="staff")
    fz = deck + 2.38
    bx.cloth(0.5, 0.34, (staff[0] + 0.03, staff[1], fz - 0.34), geo.U, bx.cloth_mat((0.36, 0.07, 0.04), seed=2.0, fade=0.5), sag=0.04, flutter=0.05, seed=3)
    # ladders: ground to the landing on the front, landing to the cab up the right side
    X.ladder((0.3, Y1 + 0.55, 0.0), (0.3, Y1 + 0.2, mid + 0.6), width=0.4)
    X.ladder((-0.2, 0.75, mid), (-0.36, 0.7, deck + 0.9), width=0.38)
    # at its feet
    X.sandbags((X1 + 0.35, Y1 + 0.45), (0.75, Y1 + 0.45), courses=2, z=0.0, seed=14, block=0.0)
    X.sandbags((X1 + 0.42, 0.15), (X1 + 0.42, Y1 + 0.3), courses=2, z=0.0, seed=15, block=0.0)
    H.junk("crate", (0.5, 0.6, 0.0), 5)
    H.junk("drum", (1.0, 1.15, 0.0), 2, rot=35.0)


# ============================================================================ a stacked container
DECK = 2.86
Y0, Y1U = 0.48, 1.86
CAB0, CAB1 = 0.58, 1.60


def _x(dhx):
    return G.hex_xy(dhx, 0)[0]


def _foot_upper(n):
    """As height_upper._foot(n, ladder=True): post hexes of rows 1 and 2, the odd hexes of row 2, the ladder's foot."""
    return [(dhx, dhy) for dhy in (1, 2) for dhx in range(0, n, 2)] + [(dhx, 2) for dhx in range(1, n, 2)] + [(-1, 2)]


def _stilts(n, seed, kinds=("beam", "tube", "timber")):
    r = geo.rng(seed)
    xr, xl = _x(0) - 0.32, _x(n - 1) + 0.32
    posts = list(range(0, n, 2))
    for k, dhx in enumerate(posts):
        for dhy, y in ((1, 0.8), (2, 1.6)):
            H.post(_x(dhx), y, 0.0, DECK - 0.1, kinds[(k + dhy + seed) % len(kinds)], seed + k + dhy, lean=(r.uniform(-0.03, 0.03), 0.0))
        H.brace((_x(dhx), 0.8, 0.25), (_x(dhx), 1.6, DECK - 0.35), 0.026)
    for a, b in zip(posts, posts[1:]):
        H.xbrace((_x(a), 1.6), (_x(b), 1.6), 0.3, DECK - 0.4, single=bool((a // 2 + seed) % 2))
    for y in (0.8, 1.6):
        geo.pipe([(xr - 0.1, y, DECK - 0.17), (xl + 0.1, y, DECK - 0.17)], 0.05, H.tube(0.75, 4.0), name="ledger")
    H.deck(xr, Y0, xl, Y1U, DECK, along="y", seed=seed, board=0.26, plates=2, overhang=0.1)
    f = H.face((xl, Y1U + 0.02, 0.0), geo.U)
    H.boards(f, 0.0, xl - xr, DECK - 0.2, DECK - 0.02, 0.0, seed + 5, horizontal=True, board=0.17, ragged=0.3, colours=(1, 3, 0))
    H.junk("barrel", (_x(1), 1.25, 0.0), seed)
    H.junk("tyres", (_x(n - 2), 1.2, 0.0), seed + 1)
    return xr, xl


@piece("ht_upper_e", title="Container Stack",
       desc="A shipping container somebody got up onto stilts, and a tin hutch somebody else got up onto the container.",
       footprint=_foot_upper(6), see_through=False, shadow="flat", material="metal", convert=H.GRADE)
def ht_upper_e(ctx):
    xr, xl = _stilts(6, 4)
    cx0, cx1 = xr + 0.95, xl - 0.05                          # container over hexes 1.5 .. 5, a strip of open deck at the right end
    w, depth, height = cx1 - cx0, CAB1 - CAB0, 1.98
    z = DECK + 0.1
    for x in (cx0 + 0.3, cx1 - 0.3):
        bx.beam((x, CAB0 - 0.05, DECK + 0.05), (x, CAB1 + 0.08, DECK + 0.05), (0.16, 0.1), H.wood(3, axis="X", width=0.6), name="baulk")
    geo.box((w - 0.06, depth - 0.06, height - 0.04), ((cx0 + cx1) / 2.0, (CAB0 + CAB1) / 2.0, z), 0.0, H.dark(), bevel=0.0, name="core")
    ff = H.face((cx1, CAB1, 0.0), geo.U)
    fl = H.face((cx1, CAB0, 0.0), geo.V)
    # the long side: three bays of deep corrugation in one faded paint, each rusted its own way
    bay = w / 3.0
    for k in range(3):
        H.sheet(ff, k * bay, z, bay + 0.02, height, 0.0, "v", H.OCHRE if k != 1 else H.CREAM, 0.45 + 0.12 * k, 80 + k, bolts=False, streaks=0.7)
    for zz in (z + 0.02, z + height - 0.1):                  # top and bottom rails
        geo.box((w + 0.04, 0.07, 0.1), ff.at(w / 2.0, 0.035, zz), geo.U, H.worn(w, 0.1, H.OCHRE, 0.75, 3.0, streak=0.0), bevel=0.01, name="rail")
    for uu in (0.0, w):
        geo.box((0.1, 0.09, height), ff.at(uu, 0.03, z), geo.U, H.worn(0.1, height, H.OCHRE, 0.7, 5.0 + uu, streak=0.0), bevel=0.01, name="corner_post")
    sx.stencil("C8-3", ff, w * 0.7, z + height * 0.62, 0.3, colour=(0.66, 0.63, 0.52), d=0.05, wear=0.65, seed=6)
    H.patch(ff, w * 0.12, z + 0.5, 0.7, 0.55, 0.06, H.SLATE, 0.7, 12, kind="p")
    H.window(ff, w * 0.36, z + 0.95, 0.6, 0.45, 0.06, "lit", 3)
    for k in range(5):
        H.streak(ff, w * (0.08 + 0.2 * k), z + height - 0.1, 0.35 + 0.12 * (k % 3), 0.08, 0.05)
    # the door end: two leaves, lock rods, one leaf chained
    H.sheet(fl, 0.0, z, depth / 2.0 - 0.01, height, 0.0, "p", H.OCHRE, 0.6, 85, bolts=False, streaks=0.5)
    H.sheet(fl, depth / 2.0 + 0.01, z, depth / 2.0 - 0.01, height, 0.0, "p", H.OCHRE, 0.5, 86, bolts=False, streaks=0.5)
    for u in (depth * 0.2, depth * 0.42, depth * 0.58, depth * 0.8):
        geo.pipe([fl.at(u, 0.04, z + 0.08), fl.at(u, 0.04, z + height - 0.08)], 0.02, H.tube(0.6, 2.0), name="lock_rod")
    H.dots([fl.at(depth * 0.42, 0.07, z + 0.9), fl.at(depth * 0.58, 0.07, z + 0.9)], 0.09, X.bright_metal((0.4, 0.38, 0.3)), name="handles")
    H.strap([fl.at(depth * 0.38, 0.06, z + 1.05), fl.at(depth * 0.5, 0.09, z + 0.95), fl.at(depth * 0.62, 0.06, z + 1.05)], 0.035)
    top = z + height
    roof = H.worn(w + 0.06, depth + 0.06, H.OCHRE, 0.75, 9.0, streak=0.0)
    geo.box((w + 0.06, depth + 0.06, 0.05), ((cx0 + cx1) / 2.0, (CAB0 + CAB1) / 2.0, top), 0.0, roof, bevel=0.01, name="container_roof")
    # the hutch on its roof: tin, a hatch, a rail round the rest of the roof and a water drum
    hx0, hx1 = cx0 + 0.15, cx0 + 1.75
    hf = H.face((hx1, CAB1 - 0.08, 0.0), geo.U)
    hl = H.face((hx1, CAB0 + 0.1, 0.0), geo.V)
    hw, hd = hx1 - hx0, CAB1 - CAB0 - 0.18
    geo.box((hw - 0.06, hd - 0.06, 0.68), ((hx0 + hx1) / 2.0, CAB0 + 0.1 + hd / 2.0, top + 0.05), 0.0, H.dark(), bevel=0.0, name="hutch_core")
    H.scrap_wall(hf, 0.0, hw, top + 0.05, top + 0.74, 0.0, 91, "vhp", (H.TEAL, None, H.RED), 0.6, ragged=0.08, patches=1, tiers=1)
    H.scrap_wall(hl, 0.0, hd, top + 0.05, top + 0.8, 0.0, 92, "vp", (H.SLATE, H.TEAL), 0.6, ragged=0.05, patches=0, tiers=1, sheet_w=(0.45, 0.6))
    H.lean_roof(hf, 0.0, hw, -hd, 0.12, top + 0.9, top + 0.76, 93, (None, H.RED, None), 0.6, weights=0, over=0.1)
    H.window(hf, 0.5, top + 0.32, 0.5, 0.28, 0.04, "dark", 2)
    H.rail((cx1 - 0.04, CAB1 - 0.05), (hx1 + 0.1, CAB1 - 0.05), top + 0.05, 0.6, "pipe", 6, posts=2, mid=False)
    H.rail((cx1 - 0.04, CAB1 - 0.05), (cx1 - 0.04, CAB0 + 0.08), top + 0.05, 0.6, "pipe", 7, posts=2, mid=False)
    H.junk("drum", (cx1 - 0.75, CAB0 + 0.5, top + 0.05), 3, rot=12.0)
    H.junk("can", (cx1 - 0.35, CAB1 - 0.4, top + 0.05), 2)
    # the open strip of deck: rail, the ladder up from the yard, a second ladder to the roof
    H.rail((cx0 - 0.02, Y1U - 0.04), (xr + 0.02, Y1U - 0.04), DECK, 0.95, "pipe", 3, posts=2, infill="planks")
    X.ladder((xr - 0.12, 1.45, 0.0), (xr + 0.06, 1.2, DECK + 0.85), width=0.42)
    X.ladder((cx0 - 0.3, CAB1 - 0.1, DECK), (cx0 - 0.04, CAB1 - 0.2, top + 0.5), width=0.38)
    H.junk("crate", (xr + 0.4, 0.95, DECK), 2)
    geo.bulb_string((hx0 + 0.1, CAB1 - 0.06, top + 0.72), (xr + 0.05, Y1U - 0.04, DECK + 1.0), count=4, sag=0.3,
                    colours=((1.0, 0.75, 0.4), (0.4, 0.9, 0.3), (1.0, 0.75, 0.4), (1.0, 0.3, 0.1)), radius=0.055)


# ============================================================================ two more annexes
ANNEX = dict(shadow="flat", material="metal", convert=H.GRADE)      # see_through per family, as in height_annex.py


def _foot_u(n, y1=0.45):
    return H.uniq(H.hexes_in(-0.32 - 0.03, -0.05, (n - 1) * HEX + 0.32 + 0.03, y1))


def _foot_v(rows, x0=-0.75, x1=-0.6):
    return H.uniq(H.hexes_in(x0, -0.45, x1, rows * 0.8 - 0.35))


@piece("ht_shed_v_b", title="Lean-to Workshop", desc="Planks against the wall and a roof over them. The near end stands open over a bench, a vice and things in tins.",
       footprint=_foot_v(5), see_through="v", **ANNEX)
def ht_shed_v_b(ctx):
    y0, y1 = -0.2, 3.15
    split = 1.95                                             # closed store to the far side of it, open bench on the near side
    x1 = -0.36
    depth = x1 - WALL_V
    front, back = 1.92, 2.34
    geo.box((depth - 0.04, split - y0 - 0.06, front - 0.04), ((WALL_V + x1) / 2.0, (y0 + split) / 2.0, 0.0), 0.0, H.dark(), bevel=0.0, name="core")
    fl = H.face((x1, y0, 0.0), geo.V)
    H.scrap_wall(fl, 0.0, split - y0, 0.0, front, 0.0, 74, "wwpw", (H.CREAM, H.GREEN), 0.55, ragged=0.1, patches=2, tiers=1)
    H.window(fl, 0.45, 0.95, 0.65, 0.5, 0.05, "boarded", 4)
    fe = H.face((x1, split, 0.0), geo.U)                    # the partition that faces the open end
    H.scrap_wall(fe, 0.0, depth, 0.0, front + 0.1, 0.0, 75, "wp", (H.SLATE,), 0.6, ragged=0.04, patches=0, tiers=1, sheet_w=(0.5, 0.7))
    H.door(fe, 0.1, 0.02, 0.7, 1.66, 0.05, "plank", 6)
    # the open end: two posts, the roof carried on over them, a bench against the wall
    for k, y in enumerate((split + 0.15, y1 - 0.06)):
        H.post(x1 - 0.04, y, 0.0, front + 0.02, "timber" if k else "tube", 4 + k, pad=False)
    bx.beam((x1 - 0.04, y0 - 0.05, front + 0.06), (x1 - 0.04, y1 + 0.08, front + 0.06), (0.1, 0.12), H.wood(3, axis="X", width=0.6), name="plate")
    H.lean_roof(fl, 0.0, y1 - y0, -depth, 0.14, back, front + 0.1, 76, (None, H.OCHRE, None, H.RED, None), 0.6, weights=2, over=0.1)
    geo.box((0.06, y1 - split - 0.1, 1.9), (WALL_V + 0.04, (split + y1) / 2.0, 0.0), 0.0, H.dark(), bevel=0.0, name="shade")   # the wall in shadow
    bench_x = WALL_V + 0.3
    bx.plank((bench_x, split + 0.12, 0.85), (bench_x, y1 - 0.1, 0.85), 0.5, 0.05, H.wood(2, axis="X", width=0.6, gain=1.5), name="bench")
    for k, z in enumerate((1.25, 1.55)):                     # tool boards on the wall behind it
        bx.plank((WALL_V + 0.09, split + 0.2, z), (WALL_V + 0.09, y1 - 0.2, z), 0.12, 0.03, H.wood(k, axis="X", width=0.6, gain=1.4), name="tool_rail", roll=90.0)
    for y in (split + 0.25, y1 - 0.25):
        geo.box((0.45, 0.1, 0.84), (bench_x, y, 0.0), 0.0, H.wood(3), bevel=0.01, name="bench_leg")
    geo.box((0.16, 0.2, 0.2), (bench_x + 0.1, split + 0.45, 0.88), 10.0, H.tube(0.5, 3.0), bevel=0.02, name="vice")
    H.junk("can", (bench_x - 0.02, y1 - 0.4, 0.88), 3)
    H.junk("box", (bench_x + 0.05, split + 0.85, 0.88), 1)
    H.junk("drum", (x1 - 0.1, y1 + 0.42, 0.0), 4, rot=80.0)
    geo.tire((x1 + 0.1, split + 0.6, 0.0), radius=0.33, lying=False, rot=geo.V + 90.0, lean=16.0, seed=7)
    geo.pipe([(x1 - 0.04, split + 0.6, front - 0.05), (x1 - 0.04, split + 0.6, front - 0.3)], 0.012, mat.flat((0.03, 0.03, 0.03)), name="flex")


@piece("ht_shed_u_c", title="Rain Butt", desc="A tank on a stand under a scrap of roof, fed from the eave by a pipe that mostly holds.",
       footprint=_foot_u(3), see_through="u", **ANNEX)
def ht_shed_u_c(ctx):
    x0, x1 = -0.32, 2.0 * HEX + 0.32
    cx = (x0 + x1) / 2.0 + 0.1
    stand = 0.82
    # the stand: four short posts, bearers, a plank top
    for x in (cx - 0.5, cx + 0.5):
        for y in (-0.42, 0.3):
            H.post(x, y, 0.0, stand - 0.1, "timber", int(x * 7 + y * 3) % 5, pad=False)
        bx.beam((x, -0.5, stand - 0.06), (x, 0.4, stand - 0.06), (0.12, 0.1), H.wood(3, axis="X", width=0.6), name="bearer")
        H.brace((x, -0.42, 0.15), (x, 0.3, stand - 0.2), 0.022)
    H.deck(cx - 0.62, -0.52, cx + 0.62, 0.42, stand, along="y", seed=31, board=0.2, plates=0, missing=0.0, joists=False, overhang=0.04)
    H.tank((cx, -0.05, stand), 0.48, 1.12, H.GREEN, seed=6, hoops=2, rust=0.6, stripe=None)
    # fed from the eave: a pipe down the wall, an elbow, and the overflow's stain
    H.pipe_run([(cx + 0.2, WALL_U + 0.08, 2.4), (cx + 0.2, WALL_U + 0.08, stand + 1.32), (cx + 0.1, -0.2, stand + 1.2)], 0.045, H.TEAL, 7)
    H.pipe_run([(cx - 0.46, 0.2, stand + 0.16), (cx - 0.46, 0.34, stand + 0.16), (cx - 0.46, 0.34, 0.5)], 0.035, None, 3)   # the tap pipe
    H.junk("bucket", (cx - 0.46, 0.4, 0.0), 2)
    # a scrap of roof over it, off the wall on two struts
    f = H.face((x1 - 0.1, 0.42, 0.0), geo.U)
    H.lean_roof(f, 0.0, x1 - x0 - 0.5, -(0.42 - WALL_U), 0.12, 2.42, 2.2, 33, (H.RED, None), 0.65, weights=1, over=0.08)
    for x in (x0 + 0.5, x1 - 0.14):
        H.brace((x, WALL_U + 0.05, 1.7), (x, 0.4, 2.2), 0.026)
    # beside it: a drum cut down for a trough and a plank to stand on
    H.junk("drum", (x0 + 0.2, 0.05, 0.0), 5, rot=5.0)
    bx.plank((cx - 0.5, 0.52, 0.03), (cx + 0.5, 0.5, 0.03), 0.26, 0.04, H.wood(1, axis="X", width=0.6), name="duckboard")
