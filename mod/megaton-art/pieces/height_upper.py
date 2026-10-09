# SPDX-License-Identifier: MIT
"""Upper storeys: shacks on stilts that stand BEHIND a building and rise over its roof, so the town
climbs towards the back wall. (author "height")

PLACING  Origin on row hy_lo - 3 of the building in front (even hx, even hy): the piece then blocks
         the even hexes of rows hy_lo - 2 and hy_lo - 1 (its posts) and leaves the origin row and the
         odd hexes of row hy_lo - 2 free, so a one-hex passage stays open behind it and nobody is walled in.
         The building's roof hides everything below about 2.7 m: the stilts, the stores under the
         deck, the foot of the ladder. They show when the player is inside and the roof is off.
         Hex 0 is the screen-RIGHT end; the piece runs to the screen left (rising hx).

    ht_upper_a   6 hexes: tin cabin with a lit window, a porch end with a rail and a ladder hatch
    ht_upper_b   6 hexes: a van body and a plank lean-to on one deck, washing between them
    ht_upper_c   4 hexes: a narrow two-storey crow's nest, the tallest thing in the back row
    ht_upper_d   8 hexes: a long low bunkhouse of car doors and planks, water drum on the roof
"""
import math

from kit import piece, geo, mat, G
from kit import height_extra as H
from kit import bomb_extra as bx
from kit import signs_extra as sx
from kit import gate_extra as X

DECK = 2.86                      # top of every upper deck: the stock roof's back edge just hides its joists
Y0, Y1 = 0.48, 1.86              # the deck, back to front (the building's back wall stands at y = 2.3)
CAB0, CAB1 = 0.58, 1.60          # cabin walls, back to front


def _x(dhx):
    return G.hex_xy(dhx, 0)[0]


def _foot(n, ladder=False):
    """Blocked hexes of an n-hex-long upper storey: the post hexes (even hx) of rows 1 and 2, and the odd
    hexes of row 2 between them (the stores under the deck stand there: the draw-order test painted a
    man on those hexes over the deck's front). Row 2 is the row right behind a building's back wall,
    which the town blocks anyway - except where the piece spans a gap between two buildings. The odd
    hexes of row 1 stay free, so with the origin row they leave a one-hex passage behind the stilts.
    ladder=True: (-1, 2) as well, where the ladder's foot stands."""
    return ([(dhx, dhy) for dhy in (1, 2) for dhx in range(0, n, 2)] + [(dhx, 2) for dhx in range(1, n, 2)]
            + ([(-1, 2)] if ladder else []))


def _stilts(n, seed, kinds=("tube", "timber", "beam")):
    """Deck on posts over hexes 0 .. n-1; returns (x_right, x_left)."""
    r = geo.rng(seed)
    xr, xl = _x(0) - 0.32, _x(n - 1) + 0.32
    posts = list(range(0, n, 2))
    if posts[-1] != n - 1 and (n - 1) % 2 == 0:
        posts.append(n - 1)
    for k, dhx in enumerate(posts):
        for dhy, y in ((1, 0.8), (2, 1.6)):
            H.post(_x(dhx), y, 0.0, DECK - 0.1, kinds[(k + dhy + seed) % len(kinds)], seed + k + dhy,
                   lean=(r.uniform(-0.04, 0.04), 0.0))
        H.brace((_x(dhx), 0.8, 0.25), (_x(dhx), 1.6, DECK - 0.35), 0.026)
    for a, b in zip(posts, posts[1:]):
        H.xbrace((_x(a), 1.6), (_x(b), 1.6), 0.3, DECK - 0.4, single=bool((a // 2 + seed) % 2))
    for y in (0.8, 1.6):                                    # ledgers on the post heads
        geo.pipe([(xr - 0.1, y, DECK - 0.17), (xl + 0.1, y, DECK - 0.17)], 0.05, H.tube(0.75, 4.0), name="ledger")
    H.deck(xr, Y0, xl, Y1, DECK, along="y", seed=seed, board=0.26, plates=2, overhang=0.1)
    # the deck's front edge is what shows over the roof line: a fascia board with rust runs
    f = H.face((xl, Y1 + 0.02, 0.0), geo.U)
    H.boards(f, 0.0, xl - xr, DECK - 0.2, DECK - 0.02, 0.0, seed + 5, horizontal=True, board=0.17, ragged=0.3, colours=(1, 3, 0))
    # stores in the dark under it
    H.junk("barrel", (_x(1), 1.25, 0.0), seed)
    H.junk("crate", (_x(n - 2), 1.2, 0.0), seed + 1)
    return xr, xl


def _cabin(xr, xl, seed, front=2.1, back=2.65, kinds="vvhpw", paints=H.PAINTS, rust=0.5, roof_paints=(None, H.RED, None, H.TEAL),
           y0=CAB0, y1=CAB1, z=DECK, weights=2, side_window="dark"):
    """A shack on the deck between world x = xr (screen right) and xl: front and left faces of
    scrap, a dark core so no gap shows daylight, a roof falling to the front. Returns (front face, left face)."""
    w = xl - xr
    geo.box((w - 0.08, y1 - y0 - 0.08, front - 0.05), ((xr + xl) / 2.0, (y0 + y1) / 2.0, z), 0.0, H.dark(), bevel=0.0, name="core")
    ff = H.face((xl, y1, 0.0), geo.U)
    H.scrap_wall(ff, 0.0, w, z, z + front, 0.0, seed, kinds, paints, rust, ragged=0.1, patches=2)
    fl = H.face((xl, y0, 0.0), geo.V)
    H.scrap_wall(fl, 0.0, y1 - y0, z, z + front + 0.15, 0.0, seed + 11, kinds, paints, rust, ragged=0.05, patches=1, sheet_w=(0.5, 0.7))
    # the gable triangle of the left side, under the roof slope
    gable = H.worn(y1 - y0, back - front, paints[seed % len(paints)] if paints else None, rust, float(seed + 2), streak=0.3)
    sx.plate([(0.0, 0.0), (y1 - y0, 0.0), (0.0, back - front)], fl.at(0.0, 0.0, z + front), geo.V, gable, thickness=0.02, name="gable")
    for uu in (0.0, w):                                     # corner posts
        bx.beam(ff.at(uu, 0.03, z), ff.at(uu, 0.03, z + front + 0.05), (0.1, 0.1), H.wood(3, axis="X", width=0.6), name="corner")
    H.lean_roof(ff, 0.0, w, -(y1 - y0), 0.14, z + back, z + front + 0.06, seed, roof_paints, rust, weights=weights, over=0.1)
    if side_window:
        H.window(fl, 0.2, z + 1.0, 0.5, 0.5, 0.04, side_window, seed + 4)
    return ff, fl


def _stovepipe(x, y, z0, z1, seed=0):
    geo.pipe([(x, y, z0), (x, y, z1), (x + 0.12, y + 0.05, z1 + 0.14)], 0.07, H.drum_paint((0.05, 0.05, 0.05), 0.6, (z1 - 0.2,), float(seed)),
             name="stovepipe", resolution=9)
    sx.cone(0.16, 0.1, (x + 0.12, y + 0.05, z1 + 0.2), H.tube(0.8, 2.0), name="cowl")
    H.strap([(x, y, z1 - 0.3), (x - 0.5, y + 0.3, z0 + 0.05)], 0.025)


# ----------------------------------------------------------------------- pieces
@piece("ht_upper_a", title="Stilt Shack",
       desc="Somebody built a second shack on top of the first one's back yard: tin on scaffold poles, a lamp in the window.",
       footprint=_foot(6, ladder=True), see_through=False, shadow="flat", material="metal", convert=H.GRADE)
def ht_upper_a(ctx):
    xr, xl = _stilts(6, 1)
    split = _x(1) + 0.35                                    # cabin over hexes 2..5, porch over 0..1
    ff, fl = _cabin(split, xl - 0.06, 3, front=2.05, back=2.62, kinds="vvhpvw")
    w = xl - 0.06 - split
    H.door(ff, w - 1.05, DECK + 0.02, 0.8, 1.8, 0.05, "plank", 2)
    H.window(ff, 0.55, DECK + 0.95, 0.75, 0.6, 0.05, "lit", 1)
    # porch end: rail with a sheet wired to it, the ladder hatch, a chair's worth of junk
    H.rail((split - 0.05, Y1 - 0.04), (xr + 0.02, Y1 - 0.04), DECK, 0.95, "pipe", 1, infill="sheet")
    H.rail((xr + 0.02, Y1 - 0.04), (xr + 0.02, Y0 + 0.1), DECK, 0.95, "pipe", 2, mid=True)
    X.ladder((xr - 0.12, 1.45, 0.0), (xr + 0.08, 1.2, DECK + 0.85), width=0.42)
    H.junk("can", (xr + 0.45, 1.0, DECK), 3)
    H.junk("box", (xr + 0.75, 0.8, DECK), 2)
    _stovepipe(split + 0.5, CAB0 + 0.3, DECK + 2.3, DECK + 3.0)
    # a string of bulbs from the cabin's eave to the rail post
    geo.bulb_string((split + 0.1, Y1 + 0.02, DECK + 2.0), (xr + 0.05, Y1 - 0.04, DECK + 1.05), count=4, sag=0.22,
                    colours=((1.0, 0.75, 0.4), (1.0, 0.3, 0.1), (1.0, 0.75, 0.4), (0.4, 0.9, 0.3)), radius=0.055)


def _van(x0, x1, y0, y1, z, seed=0, body=H.CREAM, band=H.RED, height=1.5):
    """The body of a delivery van set down on two baulks: flat sides, a window band, rear doors on the left end."""
    w, depth = x1 - x0, y1 - y0
    for x in (x0 + 0.3, x1 - 0.3):
        bx.beam((x, y0 - 0.05, z + 0.06), (x, y1 + 0.1, z + 0.06), (0.16, 0.12), H.wood(3, axis="X", width=0.6), name="baulk")
    z += 0.12
    geo.box((w - 0.06, depth - 0.06, height - 0.04), ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z), 0.0, H.dark(), bevel=0.0, name="core")
    ff = H.face((x1, y1, 0.0), geo.U)
    fl = H.face((x1, y0, 0.0), geo.V)
    H.sheet(ff, 0.0, z, w, height, 0.0, "p", body, 0.45, seed, bolts=False, streaks=0.5)
    H.sheet(ff, 0.0, z + height * 0.36, w, 0.2, 0.012, "p", band, 0.5, seed + 1, bolts=False, streaks=0.0)
    H.sheet(fl, 0.0, z, depth, height, 0.0, "p", body, 0.55, seed + 2, bolts=False, streaks=0.5)
    H.sheet(fl, 0.0, z + height * 0.36, depth, 0.2, 0.012, "p", band, 0.5, seed + 3, bolts=False, streaks=0.0)
    # rear doors: a seam, two handles, a window boarded with tin
    geo.box((0.03, 0.02, height - 0.2), fl.at(depth / 2.0, 0.02, z + 0.08), geo.V, H.dark(), bevel=0.0, name="door_seam")
    H.dots([fl.at(depth / 2.0 - 0.1, 0.04, z + height * 0.5), fl.at(depth / 2.0 + 0.1, 0.04, z + height * 0.5)], 0.06,
           X.bright_metal((0.4, 0.38, 0.34)), name="handles")
    H.patch(fl, depth * 0.5 + 0.08, z + height * 0.62, depth * 0.36, 0.34, 0.03, None, 0.7, seed + 5, kind="h")
    geo.box((depth * 0.34, 0.02, 0.32), fl.at(depth * 0.27, 0.02, z + height * 0.63), geo.V, mat.glass(dirt=0.8), bevel=0.0, name="rear_glass")
    # side windows: three panes, one lit, one blinded with a plank
    pane_w = (w - 0.9) / 3.0
    for k in range(3):
        u = 0.3 + k * (pane_w + 0.15)
        H.window(ff, u, z + height * 0.6, pane_w, 0.36, 0.02, ("dark", "lit", "boarded")[(k + seed) % 3], seed + k)
    # roof: a plate with a rounded gutter edge, a roof rack with a tyre and a jerrycan
    roof = H.worn(w + 0.1, depth + 0.1, body, 0.6, float(seed + 7), streak=0.0)
    geo.box((w + 0.1, depth + 0.1, 0.06), ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z + height), 0.0, roof, bevel=0.025, name="van_roof")
    geo.pipe([(x0 - 0.04, y1 + 0.04, z + height + 0.02), (x1 + 0.04, y1 + 0.04, z + height + 0.02), (x1 + 0.04, y0 - 0.02, z + height + 0.02)],
             0.04, H.drum_paint(body, 0.6, (), float(seed)), name="gutter")
    for x in (x0 + 0.4, x1 - 0.4):
        geo.pipe([(x, y0 + 0.1, z + height + 0.04), (x, y0 + 0.1, z + height + 0.2), (x, y1 - 0.1, z + height + 0.2), (x, y1 - 0.1, z + height + 0.04)],
                 0.02, H.tube(0.6, 2.0), name="rack")
    geo.tire(((x0 + x1) / 2.0 + 0.3, (y0 + y1) / 2.0, z + height + 0.22), radius=0.33, rot=30.0, seed=seed)
    H.junk("can", (x0 + 0.55, (y0 + y1) / 2.0, z + height + 0.22), seed)
    # a wheel leans where the arch used to be, and rust runs from the sill
    geo.tire(ff.at(w * 0.78, 0.14, z - 0.12), radius=0.3, lying=False, rot=geo.U + 90.0, lean=14.0, seed=seed + 2)
    for k in range(4):
        H.streak(ff, w * (0.12 + 0.22 * k), z + height * 0.36, 0.3 + 0.1 * (k % 3), 0.07, 0.03)
    return ff, fl


@piece("ht_upper_b", title="Van on Stilts",
       desc="A delivery van's body, hoisted onto a deck behind the roofs and lived in. A plank privy keeps it company.",
       footprint=_foot(6), see_through=False, shadow="flat", material="metal", convert=H.GRADE)
def ht_upper_b(ctx):
    xr, xl = _stilts(6, 2, kinds=("timber", "tube", "timber"))
    ff, fl = _van(xr + 1.45, xl - 0.08, CAB0 + 0.02, CAB1, DECK, seed=1)
    # the privy at the right end: planks, a crooked door, a tin lid for a roof
    px0, px1 = xr + 0.08, xr + 1.12
    pf, pl = _cabin(px0, px1, 6, front=1.8, back=2.05, kinds="ww", paints=(), roof_paints=(None, H.OCHRE), y0=CAB0 + 0.25, weights=1,
                    side_window=None)
    H.door(pf, 0.14, DECK + 0.02, 0.72, 1.62, 0.05, "plank", 5, ajar=True)
    # washing between the van and the privy, and a rail along the open strip of deck
    line0, line1 = (xr + 1.5, Y1 - 0.06, DECK + 1.72), (px1 - 0.05, Y1 - 0.06, DECK + 1.6)
    geo.cable(line0, line1, 0.05, 0.016)
    H.rail((xl, Y1 - 0.03), (xr, Y1 - 0.03), DECK, 0.5, "rope", 4, mid=False, posts=5)
    _stovepipe(xl - 0.6, CAB0 + 0.35, DECK + 1.6, DECK + 2.55, 2)


@piece("ht_upper_c", title="Crow's Nest",
       desc="Two storeys of scrap on scaffold legs with a lookout on top. A lamp burns up there all night.",
       footprint=_foot(4), see_through=False, shadow="flat", material="metal", light=(5, 70), light_hex=(2, 2), convert=H.GRADE)
def ht_upper_c(ctx):
    xr, xl = _stilts(4, 3, kinds=("tube", "beam", "tube"))
    x0, x1 = xr + 0.12, xl - 0.12
    w = x1 - x0
    storey = 1.5
    geo.box((w - 0.08, CAB1 - CAB0 - 0.08, storey), ((x0 + x1) / 2.0, (CAB0 + CAB1) / 2.0, DECK), 0.0, H.dark(), bevel=0.0, name="core")
    ff = H.face((x1, CAB1, 0.0), geo.U)
    fl = H.face((x1, CAB0, 0.0), geo.V)
    H.scrap_wall(ff, 0.0, w, DECK, DECK + storey, 0.0, 21, "pvhp", (H.TEAL, H.CREAM, H.RED), 0.55, ragged=0.04, patches=2, tiers=1)
    H.scrap_wall(fl, 0.0, CAB1 - CAB0, DECK, DECK + storey, 0.0, 22, "vp", (H.CREAM, H.SLATE), 0.6, ragged=0.04, patches=1, tiers=1,
                 sheet_w=(0.5, 0.7))
    H.door(ff, 0.2, DECK + 0.02, 0.72, 1.4, 0.05, "sheet", 3, paint=H.OCHRE)
    H.window(ff, 1.25, DECK + 0.7, 0.6, 0.5, 0.05, "shutter", 4)
    # the lookout deck
    z2 = DECK + storey + 0.1
    H.deck(x0 - 0.2, CAB0 - 0.1, x1 + 0.2, CAB1 + 0.22, z2, along="x", seed=8, board=0.22, plates=1, joists=False)
    corners = [(x0 - 0.05, CAB0 + 0.02), (x1 + 0.05, CAB0 + 0.02), (x0 - 0.05, CAB1 + 0.1), (x1 + 0.05, CAB1 + 0.1)]
    for k, (cx, cy) in enumerate(corners):
        geo.pipe([(cx, cy, DECK), (cx, cy, z2 + (1.36 if cy < 1.0 else 1.16))], 0.045, H.tube(0.7, 2.0 + k), name="nest_post")
    H.rail(corners[3], corners[2], z2, 0.8, "pipe", 5, posts=2, infill="sheet")
    H.rail(corners[3], corners[1], z2, 0.8, "pipe", 6, posts=2)
    X.sandbags((corners[2][0] + 0.25, corners[2][1] - 0.2), (corners[2][0] + 1.1, corners[2][1] - 0.2), courses=2, z=z2, seed=5,
               size=(0.5, 0.3, 0.16))
    top = H.face((x1 + 0.1, CAB1 + 0.1, 0.0), geo.U)
    H.lean_roof(top, 0.0, w + 0.2, -(CAB1 - CAB0) - 0.1, 0.12, z2 + 1.36, z2 + 1.16, 31, (H.RED, None, H.OCHRE), 0.6, weights=1, over=0.12,
                purlins=True)
    H.lamp(((x0 + x1) / 2.0, CAB1 - 0.2, z2 + 1.1))
    H.flood((x1 + 0.12, CAB1 + 0.2, z2 + 0.9), (0.7, 0.9, -0.5), size=0.16)
    X.ladder((x0 - 0.3, CAB1 + 0.35, DECK), (x0 - 0.22, CAB1 + 0.18, z2 + 0.6), width=0.38)
    H.junk("box", ((x0 + x1) / 2.0 - 0.3, CAB0 + 0.4, z2), 4)


@piece("ht_upper_d", title="Bunkhouse on Stilts",
       desc="A long low bunkhouse nailed together from car doors, planks and whatever was left, up where the air is better.",
       footprint=_foot(8), see_through=False, shadow="flat", material="metal", convert=H.GRADE)
def ht_upper_d(ctx):
    xr, xl = _stilts(8, 4, kinds=("timber", "beam", "tube"))
    x0 = xr + 1.25
    ff, fl = _cabin(x0, xl - 0.06, 9, front=1.78, back=2.2, kinds="pphvpw", paints=(H.RED, H.SLATE, H.CREAM, H.GREEN, H.OCHRE),
                    roof_paints=(None, None, H.SLATE, H.RED, None), weights=3)
    w = xl - 0.06 - x0
    H.door(ff, 0.35, DECK + 0.02, 0.78, 1.62, 0.05, "plank", 7)
    H.door(ff, w - 1.2, DECK + 0.02, 0.78, 1.62, 0.05, "sheet", 8, paint=H.TEAL)
    H.window(ff, 1.5, DECK + 0.85, 0.7, 0.5, 0.05, "lit", 3)
    H.window(ff, 2.6, DECK + 0.85, 0.6, 0.5, 0.05, "boarded", 4)
    # the water drum on a stand at the open end, a tarp slung from the eave to two poles
    stand = (xr + 0.6, 1.0)
    for dx in (-0.3, 0.3):
        for dy in (-0.3, 0.3):
            geo.pipe([(stand[0] + dx, stand[1] + dy, DECK), (stand[0] + dx, stand[1] + dy, DECK + 0.62)], 0.035, H.tube(0.7, 3.0), name="stand")
    geo.box((0.8, 0.8, 0.05), (stand[0], stand[1], DECK + 0.6), 0.0, H.wood(2, axis="X", width=0.6), bevel=0.006, name="stand_top")
    H.tank((stand[0], stand[1], DECK + 0.66), 0.4, 0.95, H.TEAL, seed=3, hoops=2, rust=0.6)
    H.pipe_run([(stand[0] + 0.3, stand[1] + 0.25, DECK + 0.85), (stand[0] + 0.55, stand[1] + 0.25, DECK + 0.85),
                (stand[0] + 0.55, stand[1] + 0.25, DECK + 0.3), (x0 + 0.1, CAB1 + 0.08, DECK + 0.3)], 0.04, seed=1)
    H.rail((x0 - 0.02, Y1 - 0.04), (xr + 0.02, Y1 - 0.04), DECK, 0.9, "wood", 3, infill="planks")
    H.rail((xr + 0.02, Y1 - 0.04), (xr + 0.02, Y0 + 0.1), DECK, 0.9, "wood", 4)
    _stovepipe(xl - 0.9, CAB0 + 0.3, DECK + 1.9, DECK + 2.75, 5)
    geo.bulb_string((x0 + 0.1, Y1 + 0.02, DECK + 1.75), (xr + 0.05, Y1 - 0.04, DECK + 1.0), count=3, sag=0.2, radius=0.055)
