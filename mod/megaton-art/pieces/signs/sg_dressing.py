# SPDX-License-Identifier: MIT
"""Megaton street dressing: awnings, a noodle counter, clusters of junk, a bench, a cart, a washing line.

Each piece is one rich sprite (plus a flat shadow part for the two awnings), not a kit of small
props: the layering is in the model, so the town only has to put down one object.

HOW ONE PART SORTS (see sg_signs.py for the row rule)
  Things that stand along a hex ROW are anchored on the highest hx of their BACK row: painted
  after everybody behind, before everybody in front. Hexes they cover without a picture get the
  stock invisible blocker from the placer (manifest "blockers").
  The awnings are a roof on two thin posts. A roof 2.15 m up is never reached by a head in
  front of it, and whoever is under or behind it must be painted first: so the whole awning is
  one part on its camera-side post for the row awning (the screen-left post). The column awning
  is TWO parts, one per post: as one sprite on the near post its far post was painted over
  whoever stood in front of it (`build.py sort` measures this for every piece).
  Nothing here runs along a hex COLUMN at ground level: that needs one part per hex.

PLACEMENT (the table with hexes and the stock objects replaced is placement.py, group "street")
  sg_awning_u    against a FRONT wall (a wall on row hy, seen from outside): origin on row hy + 1,
                 posts on (0, 1) and (4, 1), sheets reach back to the wall 0.8 m behind the origin
                 row. The stock roof's eave covers the back 0.9 m of the sheets: the awning comes
                 out from under it, which is how it should look.
  sg_awning_v    against a LEFT wall (a wall on column hx, seen from outside): origin = far post
                 (hx + 2, hy), near post on (0, 4), sheets reach back to the wall 1.39 m away.
  sg_noodle_bar  origin (118, 108): replaces the stock "Bar" 0x0200005E on plan.LANTERN_BAR and
                 covers the same hexes, plus three stools on row 109.
  the rest       anywhere on open ground that is not right behind a building or the town's front
                 wall (both hide what is lower than a man for three rows).
"""
import math

from kit import piece, geo, mat, G
from kit import signs_extra as sx

HEX = G.SQ_U_M / 2.0
WARM = (1.0, 0.80, 0.45)


def hx(dhx, dhy=0):
    return G.hex_xy(dhx, dhy)


# ---------------------------------------------------------------------- awnings
def _awning_dressing(points_front, lamp_at, r):
    """Bulbs under the front beam and a caged lamp: what makes the lean-to glow at night."""
    wire = mat.flat((0.025, 0.022, 0.02), roughness=0.6)
    a, b = points_front
    geo.cable(a, b, 0.12, 0.014, wire)
    hang = geo.catenary(a, b, 0.12, 6)[1:-1]
    sx.bulbs_on(hang, [WARM, "fire", WARM, None, WARM], radius=0.055, drop=0.07, strength=2.2)
    sx.caged_lamp(lamp_at, size=1.0, strength=3.5)


@piece("sg_awning_u", title="Lean-to Awning",
       desc="Corrugated sheets and a tarpaulin on two props, weighted down with tires. It keeps the sun off.",
       footprint=[(0, 1), (4, 1)], anchors=[(4, 1)], shadow="flat", material="metal", light=(4, 80), light_hex=(4, 1),
       convert={"shadow_max": 0.5})
def sg_awning_u(ctx):
    r = ctx.rng
    (x0, yp), (x1, _) = hx(0, 1), hx(4, 1)                # posts: screen-right and screen-left
    back = -0.8 + G.STOCK_WALL_FRONT_U + 0.02             # the face of a stock wall one row behind the origin row
    top_back, top_front = 2.52, 2.14
    xl, xr = x1 + 0.38, x0 - 0.38                         # roof ends (xl is screen-left)
    wood = mat.planks((0.21, 0.12, 0.06), width=2.0, axis="Z", grey=0.4, seed=2)
    beam = mat.planks((0.19, 0.11, 0.05), width=2.0, axis="X", grey=0.3, seed=5)
    steel = mat.steel(rust=0.75, seed=4)
    geo.box((0.11, 0.11, top_front), (x1, yp, 0.0), geo.U, wood, bevel=0.01, roll=1.5, name="post")
    geo.pipe([(x0, yp, 0.0), (x0, yp, top_front)], 0.045, steel, name="post")        # the other prop is a scaffold tube
    geo.box((0.3, 0.3, 0.12), (x1, yp, 0.0), 15.0, mat.concrete(seed=3), bevel=0.02, name="pad")
    geo.cylinder(0.16, 0.1, (x0, yp, 0.0), mat.concrete(seed=4), 10, name="pad")
    geo.box((xl - xr, 0.09, 0.13), ((xl + xr) / 2.0, yp, top_front - 0.02), geo.U, beam, bevel=0.008, name="front_beam")
    geo.box((xl - xr, 0.05, 0.14), ((xl + xr) / 2.0, back + 0.03, top_back - 0.12), geo.U, beam, bevel=0.006, name="ledger")
    depth = yp - back + 0.42
    slope = math.degrees(math.atan2(top_back - top_front, yp - back))
    for x in (x1 + 0.1, (x0 + x1) / 2.0, x0 - 0.1):                                   # rafters
        geo.box((0.07, depth - 0.1, 0.09), (x, (back + yp + 0.3) / 2.0, (top_back + top_front) / 2.0 - 0.08), geo.U, beam,
                bevel=0.005, tilt=-slope, name="rafter")
    for side, x in ((1, x1), (-1, x0)):                                               # knee braces
        geo.pipe([(x, yp, 1.55), (x - side * 0.5, yp, top_front - 0.06)], 0.022, steel, name="knee")
    # the roof: four sheets, each its own rust and paint, overlapping like shingles
    paints = [None, (0.07, 0.19, 0.21), None, (0.28, 0.10, 0.04)]
    total = xl - xr
    x = xl
    for i in range(4):
        w = total / 4.0 + 0.07
        geo.corrugated_panel(w, depth + r.uniform(-0.1, 0.1), (x, back - 0.02, top_back + 0.05 + 0.014 * (i % 2)), geo.U,
                             mat.corrugated(rust=0.35 + 0.18 * ((i * 2) % 3), seed=30 + i, paint=paints[i]),
                             tilt=90.0 + slope + r.uniform(-1.2, 1.2), name=f"roof{i}")
        x -= w - 0.07
    # a tarpaulin patch tied over the right end, two tyres and a plank to hold everything down
    zf = top_front + 0.1
    sx.sag_sheet([(xr + 1.0, back + 0.25, top_back + 0.06), (xr - 0.12, back + 0.3, top_back + 0.04),
                  (xr - 0.16, yp + 0.34, zf - 0.03), (xr + 0.9, yp + 0.3, zf)],
                 mat.tarp((0.10, 0.16, 0.24), seed=3), sag=0.02, ripple=0.012, seed=2)
    mid_z = (top_back + top_front) / 2.0
    geo.tire(((x0 + x1) / 2.0 + 0.5, (back + yp) / 2.0 - 0.1, mid_z + 0.17), radius=0.34, lean=slope, rot=180.0, seed=2)
    geo.tire((x1 - 0.1, (back + yp) / 2.0 + 0.45, mid_z + 0.02), radius=0.3, lean=slope, rot=180.0, seed=5)
    geo.box((1.5, 0.14, 0.035), ((x0 + x1) / 2.0 - 0.3, yp + 0.02, top_front + 0.14), geo.U + 6.0, beam, bevel=0.004,
            tilt=-slope, name="batten")
    _awning_dressing(((xl - 0.2, yp + 0.06, top_front - 0.09), (xr + 0.2, yp + 0.06, top_front - 0.09)),
                     (x1 - 0.7, yp - 0.55, top_front + 0.02), r)
    # a ragged strip of cloth nailed under the front edge at the left
    f = sx.Frame((xl, yp + 0.08, 0.0), geo.U)
    sx.cloth(f, 0.55, top_front - 0.08, 0.8, 0.34, sx.fabric((0.42, 0.14, 0.08), seed=4), folds=2.0, depth=0.03, seed=3)


@piece("sg_awning_v", title="Lean-to Awning",
       desc="Corrugated sheets and a tarpaulin on two props, weighted down with tires. It keeps the sun off.",
       footprint=[(0, 0), (0, 4)], anchors=[(0, 0), (0, 4)], shadow="flat", material="metal", light=(4, 80), light_hex=(0, 4),
       convert={"shadow_max": 0.5})
def sg_awning_v(ctx):
    # anchors: TWO parts. As one sprite on the near post the far post was painted over anybody standing in front of it.
    r = ctx.rng
    (xp, y0), (_, y1) = hx(0, 0), hx(0, 4)                 # posts: far and near
    back = -G.SQ_U_M + G.STOCK_WALL_FRONT_V + 0.02         # the face of a stock wall two hexes to the right of the origin
    top_back, top_front = 2.52, 2.14
    ya, yb = y0 - 0.38, y1 + 0.38                          # roof ends (yb is nearer the camera)
    wood = mat.planks((0.21, 0.12, 0.06), width=2.0, axis="Z", grey=0.4, seed=6)
    beam = mat.planks((0.19, 0.11, 0.05), width=2.0, axis="X", grey=0.3, seed=7)
    steel = mat.steel(rust=0.75, seed=9)
    geo.box((0.11, 0.11, top_front), (xp, y1, 0.0), geo.V, wood, bevel=0.01, roll=-1.5, name="post")
    geo.pipe([(xp, y0, 0.0), (xp, y0, top_front)], 0.045, steel, name="post")
    geo.box((0.3, 0.3, 0.12), (xp, y1, 0.0), 15.0, mat.concrete(seed=3), bevel=0.02, name="pad")
    geo.cylinder(0.16, 0.1, (xp, y0, 0.0), mat.concrete(seed=4), 10, name="pad")
    geo.box((yb - ya, 0.09, 0.13), (xp, (ya + yb) / 2.0, top_front - 0.02), geo.V, beam, bevel=0.008, name="front_beam")
    geo.box((yb - ya, 0.05, 0.14), (back + 0.03, (ya + yb) / 2.0, top_back - 0.12), geo.V, beam, bevel=0.006, name="ledger")
    depth = xp - back + 0.42
    slope = math.degrees(math.atan2(top_back - top_front, xp - back))
    for y in (y0 - 0.1, (y0 + y1) / 2.0, y1 + 0.1):
        geo.box((0.07, depth - 0.1, 0.09), ((back + xp + 0.3) / 2.0, y, (top_back + top_front) / 2.0 - 0.08), geo.V, beam,
                bevel=0.005, tilt=-slope, name="rafter")
    for side, y in ((1, y0), (-1, y1)):
        geo.pipe([(xp, y, 1.55), (xp, y + side * 0.5, top_front - 0.06)], 0.022, steel, name="knee")
    paints = [(0.26, 0.10, 0.04), None, (0.07, 0.19, 0.21), None]
    total = yb - ya
    y = ya
    for i in range(4):
        w = total / 4.0 + 0.07
        geo.corrugated_panel(w, depth + r.uniform(-0.1, 0.1), (back - 0.02, y, top_back + 0.05 + 0.014 * (i % 2)), geo.V,
                             mat.corrugated(rust=0.35 + 0.18 * ((i * 2 + 1) % 3), seed=40 + i, paint=paints[i]),
                             tilt=90.0 + slope + r.uniform(-1.2, 1.2), name=f"roof{i}")
        y += w - 0.07
    zf = top_front + 0.1
    sx.sag_sheet([(back + 0.25, ya + 1.0, top_back + 0.06), (back + 0.3, ya - 0.12, top_back + 0.04),
                  (xp + 0.34, ya - 0.16, zf - 0.03), (xp + 0.3, ya + 0.9, zf)],
                 mat.tarp((0.22, 0.17, 0.08), seed=5), sag=0.02, ripple=0.012, seed=4)
    mid_z = (top_back + top_front) / 2.0
    geo.tire(((back + xp) / 2.0 - 0.1, (y0 + y1) / 2.0 + 0.5, mid_z + 0.17), radius=0.34, lean=slope, rot=90.0, seed=2)
    geo.tire(((back + xp) / 2.0 + 0.4, y1 - 0.1, mid_z + 0.04), radius=0.3, lean=slope, rot=90.0, seed=5)
    geo.box((1.5, 0.14, 0.035), (xp + 0.02, (y0 + y1) / 2.0 + 0.3, top_front + 0.14), geo.V - 6.0, beam, bevel=0.004,
            tilt=-slope, name="batten")
    _awning_dressing(((xp + 0.06, ya + 0.2, top_front - 0.09), (xp + 0.06, yb - 0.2, top_front - 0.09)),
                     (xp - 0.55, y0 + 0.7, top_front + 0.02), r)
    f = sx.Frame((xp + 0.08, yb, 0.0), geo.V)
    sx.cloth(f, -0.55, top_front - 0.08, 0.8, 0.34, sx.fabric((0.10, 0.20, 0.30), seed=6), folds=2.0, depth=0.03, seed=5)


# ------------------------------------------------------------------- junk clusters
@piece("sg_tires", title="Tire Pile", desc="Tires stacked, leaning and half sunk into the dirt. One still has its rim.",
       footprint=[(0, 0), (1, 0), (2, 0), (1, 1)], anchors=[(2, 0)], shadow="baked", material="plastic",
       convert={"exposure": 0.35, "contrast": 1.25})       # (1, 1): the leaning tyre lies on that hex
def sg_tires(ctx):
    (xa, ya), (xb, yb), (xc, yc) = hx(0), hx(1), hx(2)
    geo.tire_stack(4, (xc, yc, 0.0), seed=11, radius=0.38, width=0.23)
    geo.tire_stack(5, (xb + 0.05, yb + 0.02, 0.0), seed=14, radius=0.36, width=0.22)
    geo.tire_stack(2, (xa, ya - 0.05, 0.0), seed=17, radius=0.37, width=0.22)
    geo.tire((xa + 0.05, ya - 0.02, 0.44), radius=0.33, width=0.2, rot=40.0, lean=9.0, seed=3)
    geo.tire((xc - 0.55, yc + 0.42, 0.0), radius=0.4, lying=False, rot=20.0, lean=-24.0, seed=6)          # leaning on the tall stack
    geo.tire((xa + 0.5, ya + 0.5, -0.07), radius=0.36, lean=7.0, seed=8)                                    # half sunk
    rim = mat.steel(rust=0.5, colour=(0.2, 0.2, 0.2), seed=3)
    geo.lathe([(0.0, 0.03), (0.21, 0.03), (0.22, 0.0), (0.24, 0.02), (0.24, 0.16), (0.2, 0.18), (0.2, 0.08), (0.0, 0.08)],
              (xa + 0.5, ya + 0.5, 0.0), rim, 16, 0.0, 7.0, name="rim")
    f = sx.Frame((xc, yc + 0.4, 0.0), geo.U)
    geo.box((0.09, 0.03, 1.5), f.at(0.1, 0.0, 0.0), f.rot, mat.planks((0.2, 0.12, 0.06), width=2.0, axis="Z", seed=1), bevel=0.004,
            tilt=-14.0, roll=6.0, name="plank")
    sx.disc(0.2, (xb - 0.3, yb + 0.72, 0.0), 100.0, mat.aluminium(panel=5.0, rivets=False, seed=4), thickness=0.02, dome=0.06,
            tilt=-78.0, name="hubcap")


def _crate(size, at, rot, seed, colour=(0.33, 0.20, 0.09)):
    wood = mat.planks(colour, width=0.16, axis="Z", grey=0.3, seed=seed)
    return geo.crate(size, at, rot, material=wood, seed=seed)


@piece("sg_crates", title="Stacked Crates", desc="Crates, a sack and a jerry can under half a tarpaulin. Somebody's stock.",
       footprint=[(0, 0), (1, 0), (2, 0)], anchors=[(2, 0)], shadow="baked", material="wood",
       convert={"exposure": 0.35, "contrast": 1.25, "saturation": 1.2})
def sg_crates(ctx):
    (xa, ya), (xb, yb), (xc, yc) = hx(0), hx(1), hx(2)
    _crate((0.95, 0.9, 0.85), (xc - 0.05, yc - 0.02, 0.0), geo.U + 4.0, 3)
    _crate((0.7, 0.66, 0.6), (xc - 0.02, yc - 0.05, 0.85), geo.U - 14.0, 5, colour=(0.30, 0.17, 0.07))
    _crate((0.85, 0.8, 0.72), (xb - 0.05, yb - 0.02, 0.0), geo.U - 6.0, 7, colour=(0.36, 0.23, 0.11))
    _crate((0.62, 0.6, 0.5), (xa + 0.02, ya - 0.05, 0.0), geo.U + 18.0, 9)
    # the open small crate: bottle necks
    glassy = mat.glass((0.10, 0.30, 0.12), dirt=0.3)
    amber = mat.glass((0.40, 0.20, 0.04), dirt=0.3)
    r = geo.rng(4)
    for i in range(7):
        geo.cylinder(0.045, 0.2, (xa + 0.02 + r.uniform(-0.2, 0.2), ya - 0.05 + r.uniform(-0.2, 0.2), 0.42), r.choice([glassy, amber]), 8,
                     name="bottle")
    # tarpaulin thrown over the middle crate, hanging down its front
    sx.sag_sheet([(xb + 0.42, yb - 0.5, 0.76), (xb - 0.5, yb - 0.5, 0.76), (xb - 0.52, yb + 0.44, 0.74), (xb + 0.44, yb + 0.44, 0.74)],
                 mat.tarp((0.12, 0.19, 0.11), seed=4), sag=-0.03, ripple=0.02, seed=6)
    f = sx.Frame((xb + 0.44, yb + 0.43, 0.0), geo.U)
    sx.cloth(f, 0.46, 0.75, 0.94, 0.48, mat.tarp((0.12, 0.19, 0.11), seed=4), folds=2.5, depth=0.035, seed=8)
    # sack, jerry can, a coil of rope on the big crate
    sx.sphere(0.27, (xa + 0.55, ya + 0.4, 0.17), mat.tarp((0.34, 0.27, 0.15), seed=6), name="sack", squash=0.72)
    sx.sphere(0.22, (xa + 0.4, ya + 0.52, 0.42), mat.tarp((0.32, 0.25, 0.14), seed=7), name="sack", squash=0.7)
    can = sx.enamel((0.42, 0.05, 0.03), chips=0.5, seed=5)
    geo.box((0.34, 0.16, 0.44), (xc + 0.5, yc + 0.5, 0.0), geo.U + 25.0, can, bevel=0.03, name="jerry_can")
    geo.cylinder(0.035, 0.07, (xc + 0.58, yc + 0.47, 0.44), mat.steel(rust=0.3), 8, name="spout")
    rope = mat.flat((0.30, 0.22, 0.11), roughness=0.95)
    for k in range(3):
        geo.lathe([(0.15, 0.0), (0.2, 0.0), (0.2, 0.05), (0.15, 0.05), (0.15, 0.0)], (xc + 0.1, yc + 0.1, 1.45 + 0.045 * k), rope, 14,
                  name="rope")
    # a hazard diamond stuck on the big crate's front
    g = sx.Frame((xc - 0.05, yc - 0.02 + 0.47, 0.0), geo.U + 4.0)
    sx.plate([(0.0, -0.17), (0.17, 0.0), (0.0, 0.17), (-0.17, 0.0)], g.at(0.12, 0.0, 0.45), g.rot,
             sx.enamel((0.80, 0.52, 0.04), chips=0.3, seed=3), 0.012)


def _drum(at, colour, seed, band=None, height=0.88, radius=0.29, tilt=0.0, rot=0.0, flaking=0.55):
    drum = geo.barrel(at, radius=radius, height=height, material=mat.painted_metal(colour, flaking=flaking, seed=seed),
                      tilt=tilt, rot=rot, seed=seed)
    if band and not tilt:
        geo.lathe([(radius + 0.004, 0.0), (radius + 0.004, 0.16)], (at[0], at[1], at[2] + height * 0.42),
                  sx.enamel(band, chips=0.5, seed=seed), 24, name="band")
    return drum


@piece("sg_barrels", title="Oil Drums", desc="Drums on a pallet, one on its side and leaking. The yellow band means do not drink.",
       footprint=[(0, 0), (1, 0), (2, 0)], anchors=[(2, 0)], shadow="baked",
       convert={"contrast": 1.25, "saturation": 1.1})
def sg_barrels(ctx):
    (xa, ya), (xb, yb), (xc, yc) = hx(0), hx(1), hx(2)
    wood = mat.planks((0.25, 0.15, 0.07), width=0.14, axis="X", grey=0.5, seed=3)
    geo.box((1.3, 1.1, 0.035), (xb + 0.42, yb + 0.25, 0.1), geo.U + 3.0, wood, bevel=0.004, name="pallet_top")
    for d in (-0.5, 0.0, 0.5):
        geo.box((1.3, 0.1, 0.1), (xb + 0.42, yb + 0.25 + d, 0.0), geo.U + 3.0, wood, bevel=0.004, name="pallet_runner")
    top = 0.135
    _drum((xc - 0.05, yc - 0.08, top), (0.36, 0.06, 0.03), 3)
    _drum((xb + 0.12, yb - 0.02, top), (0.05, 0.14, 0.22), 5, band=(0.80, 0.55, 0.05))
    _drum((xb + 0.42, yb + 0.6, top), (0.16, 0.17, 0.15), 7, flaking=0.75)
    _drum((xc - 0.1, yc + 0.45, top), (0.52, 0.36, 0.04), 9, height=0.6, radius=0.24)
    # one on its side on the ground at the right, a dark stain under its bung
    _drum((xa + 0.35, ya - 0.1, 0.3), (0.10, 0.20, 0.10), 11, tilt=90.0, rot=68.0)
    sx.disc(0.34, (xa + 0.12, ya + 0.48, 0.004), 0.0, mat.flat((0.012, 0.012, 0.014), roughness=0.25), thickness=0.004, tilt=-90.0,
            name="stain")
    # funnel on a drum, a hand pump, a bucket
    steel = mat.steel(rust=0.4, seed=6)
    sx.cone(0.16, 0.2, (xb + 0.12, yb - 0.02, top + 0.86), mat.painted_metal((0.4, 0.4, 0.38), flaking=0.3, seed=2), top=0.03)
    geo.pipe([(xc - 0.05, yc - 0.08, top + 0.8), (xc - 0.05, yc - 0.08, top + 1.45), (xc - 0.3, yc + 0.02, top + 1.42),
              (xc - 0.33, yc + 0.03, top + 1.2)], 0.03, steel, name="pump")
    geo.pipe([(xc - 0.05, yc - 0.08, top + 1.25), (xc + 0.2, yc - 0.15, top + 1.5)], 0.022, steel, name="pump_handle")
    geo.barrel((xa + 0.02, ya + 0.62, 0.0), radius=0.15, height=0.28, material=mat.painted_metal((0.3, 0.3, 0.28), flaking=0.4, seed=4))


# ----------------------------------------------------------------- noodle counter
@piece("sg_noodle_bar", title="Noodle Counter",
       desc="The Brass Lantern's counter: a plank bar, a stove built from an oil drum, three stools. The soup is always on.",
       footprint=[(-1, 0), (0, 0), (1, 0), (2, 0), (3, 0), (-1, -1), (0, -1), (1, -1), (2, -1), (3, -1), (2, -2),
                  (-1, 1), (1, 1), (3, 1)],
       anchors=[(3, 0)], shadow="baked", material="wood", light=(4, 90), light_hex=(3, 0),
       convert={"exposure": 0.2, "contrast": 1.2, "saturation": 1.15})
def sg_noodle_bar(ctx):
    f = sx.Frame((hx(3)[0] + 0.3, 0.0, 0.0), geo.U)        # u = 0 at the screen-left end of the counter
    length = hx(3)[0] - hx(-1)[0] + 0.6                    # 3.37 m
    wood = mat.planks((0.26, 0.15, 0.07), width=0.17, axis="Z", grey=0.3, seed=3)
    top = mat.aluminium(panel=1.2, rivets=True, seed=5, tint=(0.34, 0.35, 0.36))
    steel = mat.steel(rust=0.6, seed=2)
    # the serving counter: plank front, tin top, a foot rail
    geo.boards(f.at(0.0, 0.22, 0.0)[:2], f.at(length, 0.22, 0.0)[:2], height=1.0, seed=6, ragged=0.03, material=wood, lean=0.6)
    geo.box((length + 0.1, 0.52, 0.05), f.at(length / 2.0, 0.0, 1.0), f.rot, top, bevel=0.008, name="counter_top")
    for u in (0.03, length - 0.03):
        geo.box((0.05, 0.44, 1.0), f.at(u, -0.02, 0.0), f.rot, wood, bevel=0.004, name="counter_end")
    geo.pipe([f.at(0.1, 0.34, 0.2), f.at(length - 0.1, 0.34, 0.2)], 0.025, sx.brass(tarnish=0.5), name="foot_rail")
    # a painted strip along the counter front: red lacquer with a cream line
    geo.box((length - 0.3, 0.012, 0.3), f.at(length / 2.0, 0.245, 0.55), f.rot, sx.enamel((0.45, 0.05, 0.03), chips=0.4, seed=4),
            bevel=0.0, name="lacquer")
    geo.box((length - 0.5, 0.012, 0.035), f.at(length / 2.0, 0.255, 0.69), f.rot, mat.sign_paint((0.8, 0.7, 0.4), wear=0.3), bevel=0.0)
    # on the counter: bowls, a jar of chopsticks, a stack of bowls, a teapot
    white = sx.enamel((0.68, 0.66, 0.58), chips=0.2, seed=6)
    blue = sx.enamel((0.10, 0.20, 0.38), chips=0.2, seed=7)
    for u, m in ((0.5, white), (1.25, blue), (2.55, white)):
        geo.lathe([(0.05, 0.0), (0.12, 0.07), (0.13, 0.09), (0.11, 0.08), (0.0, 0.03)], f.at(u, 0.08, 1.05), m, 12, name="bowl")
    for k in range(4):
        geo.lathe([(0.05, 0.0), (0.12, 0.07), (0.13, 0.09)], f.at(2.05, -0.08, 1.05 + 0.035 * k), white, 12, name="bowl_stack")
    geo.cylinder(0.06, 0.16, f.at(1.7, 0.02, 1.05), mat.glass((0.25, 0.3, 0.2), dirt=0.4), 10, name="jar")
    for k in range(5):
        geo.pipe([f.at(1.7, 0.02, 1.1), f.at(1.66 + 0.02 * k, 0.0, 1.38)], 0.008, mat.flat((0.5, 0.36, 0.18)), name="chopstick")
    geo.lathe([(0.07, 0.0), (0.1, 0.06), (0.08, 0.13), (0.03, 0.15), (0.0, 0.17)], f.at(0.9, -0.1, 1.05), sx.brass(tarnish=0.3, seed=3), 12,
              name="teapot")
    # behind it: the stove (an oil drum on bricks with a wok), a stock pot, a shelf of jars, a gas bottle
    back = -0.95
    drum = mat.painted_metal((0.07, 0.04, 0.03), flaking=0.8, seed=8)
    geo.barrel(f.at(0.75, back, 0.0), radius=0.31, height=0.82, material=drum, seed=8)
    wok = geo.lathe([(0.0, 0.0), (0.2, 0.03), (0.36, 0.12), (0.38, 0.14), (0.2, 0.06), (0.0, 0.04)], f.at(0.75, back, 0.84),
                    mat.flat((0.02, 0.02, 0.022), roughness=0.3, metallic=0.6), 16, name="wok")
    fire = sx.flames(f.at(0.75, back, 0.8), radius=0.3, height=0.2, count=8, seed=5)
    geo.pipe([f.at(0.4, back, 0.95), f.at(0.05, back - 0.05, 1.02)], 0.02, steel, name="wok_handle")
    pot = mat.aluminium(panel=3.0, rivets=False, seed=7, tint=(0.36, 0.36, 0.37))
    geo.cylinder(0.26, 0.48, f.at(1.65, back, 0.62), pot, 16, name="stock_pot")
    geo.lathe([(0.0, 0.0), (0.27, 0.0), (0.27, 0.03), (0.04, 0.06), (0.04, 0.1), (0.0, 0.1)], f.at(1.65, back, 1.1), pot, 16, name="lid")
    geo.box((0.8, 0.62, 0.62), f.at(1.65, back, 0.0), f.rot, mat.concrete((0.26, 0.12, 0.08), cracks=0.6, seed=5), bevel=0.02,
            name="brick_hob")
    shelf = mat.planks((0.22, 0.13, 0.06), width=2.0, axis="X", grey=0.3, seed=9)
    for u in (2.25, 3.25):
        geo.box((0.07, 0.3, 1.75), f.at(u, back - 0.1, 0.0), f.rot, shelf, bevel=0.005, name="shelf_side")
    r = geo.rng(7)
    for z in (0.6, 1.1, 1.6):
        geo.box((1.07, 0.32, 0.04), f.at(2.75, back - 0.1, z), f.rot, shelf, bevel=0.004, name="shelf")
        for k in range(5):
            colour = r.choice([(0.40, 0.20, 0.04), (0.10, 0.30, 0.12), (0.5, 0.45, 0.3), (0.45, 0.08, 0.05), (0.2, 0.25, 0.3)])
            h = r.uniform(0.14, 0.28)
            geo.cylinder(r.uniform(0.05, 0.08), h, f.at(2.35 + 0.2 * k, back - 0.08, z + 0.04), mat.glass(colour, dirt=0.3), 8, name="jar")
    geo.lathe([(0.0, 0.0), (0.17, 0.02), (0.17, 0.5), (0.1, 0.6), (0.04, 0.62), (0.04, 0.68), (0.0, 0.68)], f.at(3.05, back + 0.42, 0.0),
              sx.enamel((0.42, 0.20, 0.03), chips=0.4, seed=4), 12, name="gas_bottle")
    # stove pipe with a cowl, ladles on a rail, a paper lantern over the counter's left end
    geo.pipe([f.at(0.75, back - 0.3, 0.6), f.at(0.75, back - 0.42, 0.9), f.at(0.75, back - 0.42, 2.55)], 0.07, steel, name="flue")
    sx.cone(0.17, 0.14, f.at(0.75, back - 0.42, 2.62), steel, name="cowl")
    geo.pipe([f.at(1.1, back - 0.2, 0.0), f.at(1.1, back - 0.2, 1.72)], 0.025, steel, name="rail_post")
    geo.pipe([f.at(2.22, back - 0.1, 1.72), f.at(1.1, back - 0.2, 1.72)], 0.022, steel, name="rail")
    for k, u in enumerate((1.3, 1.52, 1.76, 1.98)):
        geo.pipe([f.at(u, back - 0.17, 1.72), f.at(u, back - 0.17, 1.4 - 0.05 * (k % 2))], 0.012, steel, name="ladle")
        sx.sphere(0.05, f.at(u, back - 0.17, 1.37 - 0.05 * (k % 2)), pot, name="ladle_cup", squash=0.6)
    geo.pipe([f.at(0.05, 0.1, 0.0), f.at(0.05, 0.1, 2.3), f.at(0.45, 0.2, 2.42)], 0.025, steel, name="lantern_post")
    hook = f.at(0.45, 0.2, 2.42)
    geo.lathe([(0.0, -0.46), (0.09, -0.44), (0.17, -0.34), (0.19, -0.23), (0.17, -0.12), (0.09, -0.03), (0.0, 0.0)], hook,
              mat.emitter((1.0, 0.16, 0.04), 1.3), 12, name="paper_lantern")
    for z, rr in ((-0.34, 0.172), (-0.23, 0.192), (-0.12, 0.172)):                    # bamboo ribs
        geo.lathe([(rr, -0.012), (rr + 0.006, 0.0), (rr, 0.012)], (hook[0], hook[1], hook[2] + z), mat.flat((0.10, 0.02, 0.01)), 12,
                  name="rib")
    for z in (-0.47, 0.0):
        geo.cylinder(0.08, 0.035, (hook[0], hook[1], hook[2] + z - 0.02), mat.flat((0.03, 0.02, 0.02)), 8, name="lantern_cap")
    # three stools on the customers' side
    seat = mat.planks((0.30, 0.17, 0.08), width=2.0, axis="X", grey=0.2, seed=11)
    for dhx in (-1, 1, 3):
        sxw, syw = hx(dhx, 1)
        geo.cylinder(0.19, 0.05, (sxw, syw, 0.5), seat, 12, name="stool_seat")
        for a in (30.0, 150.0, 270.0):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            geo.pipe([(sxw + ca * 0.1, syw + sa * 0.1, 0.5), (sxw + ca * 0.2, syw + sa * 0.2, 0.0)], 0.02, steel, name="stool_leg")
        geo.lathe([(0.15, 0.0), (0.165, 0.0), (0.165, 0.02), (0.15, 0.02), (0.15, 0.0)], (sxw, syw, 0.18), steel, 12, name="stool_ring")


# ------------------------------------------------------------------------ bench
@piece("sg_bench", title="Bench", desc="A car's back seat on cinder blocks. The springs are still good.",
       footprint=[(0, 0), (2, 0)], anchors=[(2, 0)], shadow="baked", material="leather",
       convert={"exposure": 0.25, "contrast": 1.2, "saturation": 1.15})
def sg_bench(ctx):
    f = sx.Frame((hx(2)[0] + 0.1, 0.0, 0.0), geo.U)
    length = hx(2)[0] + 0.2
    block = mat.concrete((0.33, 0.32, 0.30), cracks=0.3, seed=4)
    for u in (0.2, length - 0.2):
        geo.box((0.2, 0.42, 0.2), f.at(u, 0.05, 0.0), f.rot, block, bevel=0.01, name="block")
        geo.box((0.2, 0.42, 0.2), f.at(u + 0.02, 0.05, 0.2), f.rot + 6.0, block, bevel=0.01, name="block")
    wood = mat.planks((0.25, 0.15, 0.07), width=2.0, axis="X", grey=0.35, seed=5)
    geo.box((length, 0.5, 0.04), f.at(length / 2.0, 0.05, 0.4), f.rot, wood, bevel=0.005, name="base_board")
    hide = mat.tarp((0.30, 0.08, 0.05), seed=3)
    geo.box((length - 0.06, 0.48, 0.16), f.at(length / 2.0, 0.06, 0.44), f.rot, hide, bevel=0.06, name="seat")
    geo.box((length - 0.06, 0.16, 0.55), f.at(length / 2.0, -0.2, 0.52), f.rot, hide, bevel=0.06, tilt=-14.0, name="back")
    for k in range(1, 3):                                  # seams
        geo.box((0.02, 0.5, 0.165), f.at(length * k / 3.0, 0.06, 0.44), f.rot, mat.flat((0.05, 0.02, 0.015)), bevel=0.0, name="seam")
    geo.box((0.34, 0.3, 0.02), f.at(length - 0.45, 0.1, 0.6), f.rot + 10.0, mat.tarp((0.34, 0.30, 0.20), seed=8), bevel=0.008,
            name="patch")
    geo.pipe([f.at(0.02, -0.18, 0.4), f.at(0.02, -0.28, 1.05)], 0.02, mat.steel(rust=0.5), name="frame")
    geo.pipe([f.at(length - 0.02, -0.18, 0.4), f.at(length - 0.02, -0.28, 1.05)], 0.02, mat.steel(rust=0.5), name="frame")
    geo.cylinder(0.045, 0.24, f.at(0.3, 0.42, 0.0), mat.glass((0.35, 0.18, 0.04), dirt=0.3), 8, name="bottle")
    geo.cylinder(0.11, 0.14, f.at(length + 0.12, 0.3, 0.0), sx.enamel((0.5, 0.5, 0.45), chips=0.6, seed=2), 10, name="tin")


@piece("sg_bench_plank", title="Plank Bench", desc="Two planks on a pair of paint tins. Somebody left a mug.",
       footprint=[(0, 0), (2, 0)], anchors=[(2, 0)], shadow="baked", material="wood",
       convert={"exposure": 0.3, "contrast": 1.2, "saturation": 1.1})
def sg_bench_plank(ctx):
    f = sx.Frame((hx(2)[0] + 0.12, 0.0, 0.0), geo.U)
    length = hx(2)[0] + 0.24
    for k, u in enumerate((0.26, length - 0.26)):
        geo.barrel(f.at(u, 0.0, 0.0), radius=0.17, height=0.4,
                   material=mat.painted_metal(((0.36, 0.30, 0.10), (0.10, 0.20, 0.26))[k], flaking=0.5, seed=k + 2), seed=k)
    for k, d in enumerate((-0.09, 0.1)):
        wood = mat.planks(((0.30, 0.18, 0.08), (0.24, 0.14, 0.07))[k], width=2.0, axis="X", grey=0.4, seed=k + 3)
        geo.box((length + 0.1 * k, 0.17, 0.045), f.at(length / 2.0 + 0.04 * k, d, 0.4), f.rot + (1.5 - 3.0 * k), wood, bevel=0.005, name="plank")
    geo.box((0.34, 0.26, 0.09), f.at(0.4, 0.0, 0.445), f.rot + 8.0, mat.tarp((0.36, 0.12, 0.08), seed=5), bevel=0.03, name="blanket")
    geo.cylinder(0.05, 0.1, f.at(length - 0.42, 0.04, 0.445), sx.enamel((0.62, 0.62, 0.56), chips=0.4, seed=3), 8, name="mug")
    radio = mat.painted_metal((0.20, 0.10, 0.05), flaking=0.3, seed=7)
    geo.box((0.3, 0.14, 0.2), f.at(length - 0.85, -0.03, 0.445), f.rot - 6.0, radio, bevel=0.02, name="radio")
    sx.disc(0.06, f.at(length - 0.92, 0.045, 0.545), f.rot - 6.0, mat.flat((0.03, 0.03, 0.03)), thickness=0.012, name="speaker")
    geo.pipe([f.at(length - 0.74, -0.03, 0.64), f.at(length - 0.66, -0.03, 0.98)], 0.008, mat.steel(rust=0.2), name="aerial")
    geo.cylinder(0.045, 0.24, f.at(length + 0.1, 0.3, 0.0), mat.glass((0.10, 0.30, 0.12), dirt=0.3), 8, name="bottle")


# ------------------------------------------------------------------------- cart
@piece("sg_cart", title="Hand Cart", desc="A two-wheeled cart loaded with whatever was worth dragging home.",
       footprint=[(0, 0), (1, 0), (2, 0), (1, 1), (3, 0)], anchors=[(3, 0)], shadow="baked", material="wood",
       convert={"exposure": 0.25, "contrast": 1.2, "saturation": 1.15})
def sg_cart(ctx):
    f = sx.Frame((hx(2)[0] + 0.25, 0.0, 0.0), geo.U)       # u = 0: the handle end of the bed, u grows to the screen right
    bed_len, bed_w, bed_z = 1.75, 0.95, 0.62
    wood = mat.planks((0.28, 0.16, 0.07), width=0.16, axis="X", grey=0.35, seed=4)
    dark = mat.planks((0.19, 0.11, 0.05), width=2.0, axis="X", grey=0.3, seed=6)
    steel = mat.steel(rust=0.7, seed=5)
    geo.box((bed_len, bed_w, 0.05), f.at(bed_len / 2.0, 0.0, bed_z), f.rot, wood, bevel=0.005, name="bed")
    for d in (-bed_w / 2.0, bed_w / 2.0):                  # side boards
        geo.box((bed_len, 0.035, 0.3), f.at(bed_len / 2.0, d, bed_z), f.rot, wood, bevel=0.004, name="side")
    geo.box((0.035, bed_w, 0.3), f.at(bed_len, 0.0, bed_z), f.rot, wood, bevel=0.004, name="tail")
    for d in (-0.34, 0.34):                                # shafts: run forward and down to the ground
        geo.box((bed_len, 0.07, 0.07), f.at(bed_len / 2.0, d, bed_z - 0.07), f.rot, dark, bevel=0.005, name="shaft")
        geo.pipe([f.at(0.0, d, bed_z - 0.03), f.at(-0.75, d, bed_z + 0.02)], 0.03, dark, name="handle")
    geo.pipe([f.at(-0.72, -0.36, bed_z + 0.02), f.at(-0.72, 0.36, bed_z + 0.02)], 0.028, dark, name="grip")
    geo.pipe([f.at(0.12, 0.0, bed_z), f.at(0.02, 0.0, 0.0)], 0.03, steel, name="prop_leg")
    axle_u = bed_len * 0.62
    geo.pipe([f.at(axle_u, -0.62, 0.42), f.at(axle_u, 0.62, 0.42)], 0.03, steel, name="axle")
    for d in (-0.58, 0.58):                                # two car wheels: tyre and rim
        geo.tire(f.at(axle_u, d, 0.0), radius=0.42, width=0.2, lying=False, rot=f.rot, seed=int(d * 10) + 20)
        sx.disc(0.25, f.at(axle_u, d + (0.11 if d > 0 else -0.11), 0.42), f.rot, mat.steel(rust=0.55, colour=(0.2, 0.2, 0.2), seed=2),
                thickness=0.02, dome=0.05 if d > 0 else 0.0, name="wheel_rim")
    # the load
    _crate((0.6, 0.55, 0.5), f.at(1.35, 0.05, bed_z + 0.05), f.rot + 5.0, 13)
    sx.sphere(0.3, f.at(0.75, -0.1, bed_z + 0.26), mat.tarp((0.34, 0.27, 0.15), seed=3), name="sack", squash=0.75)
    sx.sphere(0.26, f.at(0.4, 0.15, bed_z + 0.22), mat.tarp((0.30, 0.25, 0.14), seed=5), name="sack", squash=0.7)
    sx.sphere(0.24, f.at(0.7, 0.05, bed_z + 0.62), mat.tarp((0.36, 0.28, 0.16), seed=7), name="sack", squash=0.7)
    for k, (d, z) in enumerate(((0.3, 0.42), (0.36, 0.5), (0.24, 0.5))):      # scrap pipes sticking out the back
        geo.pipe([f.at(0.2, d, bed_z + z - 0.1), f.at(2.25 + 0.1 * k, d + 0.03 * k, bed_z + z + 0.25)], 0.03, steel, name="scrap_pipe")
    geo.tire(f.at(1.3, 0.0, bed_z + 0.56), radius=0.33, lean=8.0, seed=9)
    geo.cylinder(0.14, 0.34, f.at(0.25, -0.25, bed_z + 0.05), sx.enamel((0.10, 0.22, 0.36), chips=0.4, seed=3), 12, name="water_can")
    rope = mat.flat((0.30, 0.22, 0.11), roughness=0.95)
    geo.pipe([f.at(0.55, -0.49, bed_z + 0.25), f.at(0.7, -0.1, bed_z + 0.9), f.at(0.85, 0.49, bed_z + 0.25)], 0.014, rope, name="lashing")
    geo.pipe([f.at(1.15, -0.49, bed_z + 0.25), f.at(1.3, 0.0, bed_z + 0.86), f.at(1.45, 0.49, bed_z + 0.25)], 0.014, rope, name="lashing")
    geo.barrel(f.at(-0.3, 0.75, 0.0), radius=0.16, height=0.3, material=mat.painted_metal((0.3, 0.3, 0.28), flaking=0.4, seed=4))


# ---------------------------------------------------------------------- laundry
@piece("sg_laundry", title="Washing Line", desc="Two lines of washing between T-posts. The blue overalls have a number on the back.",
       footprint=[(0, 0), (2, 0), (4, 0), (6, 0), (1, 1), (5, 1)], anchors=[(6, 0)], shadow="baked", material="leather",
       convert={"exposure": 0.2, "saturation": 1.15})
def sg_laundry(ctx):
    f = sx.Frame((hx(6)[0], 0.0, 0.0), geo.U)
    span = hx(6)[0]
    wood = mat.planks((0.22, 0.13, 0.06), width=2.0, axis="Z", grey=0.45, seed=4)
    line_z = 2.0
    for u, lean in ((0.0, 2.0), (span, -2.5)):
        geo.box((0.09, 0.09, line_z + 0.12), f.at(u, 0.0, 0.0), f.rot, wood, bevel=0.008, roll=lean, name="post")
        geo.box((0.07, 0.8, 0.07), f.at(u, 0.0, line_z), f.rot, wood, bevel=0.006, name="tee")
        geo.box((0.26, 0.26, 0.1), f.at(u, 0.0, 0.0), f.rot + 10.0, mat.concrete(seed=u), bevel=0.02, name="pad")
    rope = mat.flat((0.34, 0.27, 0.15), roughness=0.95)
    for d, sag in ((-0.33, 0.13), (0.33, 0.17)):
        geo.cable(f.at(0.0, d, line_z + 0.04), f.at(span, d, line_z + 0.04), sag, 0.014, rope)

    def hang(u, d, sag):
        t = u / span
        return line_z + 0.03 - sag * 4.0 * t * (1.0 - t)

    # back line: a sheet and a blanket; front line: overalls, a shirt, long johns, socks
    back = f.moved(d=-0.33)
    sx.cloth(back, 1.05, hang(1.05, -0.33, 0.13), 1.25, 1.15, sx.fabric((0.62, 0.60, 0.52), seed=2), folds=2.0, depth=0.07, seed=2)
    sx.cloth(back, 2.75, hang(2.75, -0.33, 0.13), 1.2, 0.9, sx.fabric((0.45, 0.12, 0.07), stripes=((0.60, 0.50, 0.28), 0.12), seed=3),
             folds=1.5, depth=0.06, seed=5)
    front = f.moved(d=0.33)
    blue = sx.fabric((0.05, 0.16, 0.42), seed=4)
    u = 0.75
    z = hang(u, 0.33, 0.17)
    sx.cloth(front, u, z, 0.55, 0.62, blue, folds=1.5, depth=0.04, seed=6, name="overall_top")
    for side in (-1, 1):
        sx.cloth(front, u + side * 0.14, z - 0.6, 0.25, 0.72, blue, folds=1.0, depth=0.03, seed=7 + side, taper=0.1, name="overall_leg")
        sx.cloth(front, u + side * 0.4, z - 0.02, 0.26, 0.5, blue, folds=1.0, depth=0.03, seed=9 + side, taper=0.2, name="overall_arm")
    geo.box((0.05, 0.012, 0.55), front.at(u, 0.045, z - 0.6), f.rot, sx.fabric((0.85, 0.62, 0.08), seed=1), bevel=0.0, name="stripe")
    u = 1.85
    z = hang(u, 0.33, 0.17)
    grey = sx.fabric((0.50, 0.47, 0.40), seed=6)
    sx.cloth(front, u, z, 0.6, 0.62, grey, folds=2.0, depth=0.04, seed=12, name="shirt")
    for side in (-1, 1):
        sx.cloth(front, u + side * 0.42, z - 0.02, 0.26, 0.42, grey, folds=1.0, depth=0.03, seed=13 + side, taper=0.2, name="sleeve")
    u = 2.8
    z = hang(u, 0.33, 0.17)
    red = sx.fabric((0.48, 0.07, 0.05), seed=8)
    sx.cloth(front, u, z, 0.5, 0.36, red, folds=1.5, depth=0.03, seed=16, name="long_johns_top")
    for side in (-1, 1):
        sx.cloth(front, u + side * 0.13, z - 0.34, 0.23, 0.72, red, folds=1.0, depth=0.03, seed=17 + side, taper=0.15, name="long_johns_leg")
    for k, u in enumerate((3.4, 3.62)):
        z = hang(u, 0.33, 0.17)
        sx.cloth(front, u, z, 0.14, 0.36, sx.fabric((0.55, 0.52, 0.45), seed=k), folds=0.5, depth=0.02, seed=20 + k, name="sock")
    # the wash tub and a basket by the left post
    tub = mat.aluminium(panel=4.0, rivets=False, seed=3, tint=(0.34, 0.35, 0.36))
    geo.lathe([(0.0, 0.02), (0.3, 0.02), (0.36, 0.3), (0.38, 0.3), (0.31, 0.0), (0.0, 0.0)], f.at(0.55, 0.5, 0.0), tub, 16, name="tub")
    sx.disc(0.31, f.at(0.55, 0.5, 0.22), f.rot, mat.flat((0.25, 0.28, 0.27), roughness=0.15), thickness=0.01, tilt=-90.0, name="suds")
    geo.lathe([(0.0, 0.0), (0.2, 0.0), (0.25, 0.26), (0.23, 0.26), (0.19, 0.03), (0.0, 0.03)], f.at(span - 0.5, 0.5, 0.0),
              mat.flat((0.36, 0.26, 0.12), roughness=0.95), 12, name="basket")
    sx.sphere(0.2, f.at(span - 0.5, 0.5, 0.2), sx.fabric((0.6, 0.58, 0.5), seed=9), name="wet_washing", squash=0.6)
