# SPDX-License-Identifier: MIT
"""Roofs of the house side (screen left): Billy Creel's, the common house, Lucy West's, the Brass Lantern's kitchen,
the empty house.

    python3 mod/megaton-art/build.py tiles preview sheets/roofs_houses.py [NAME]
    python3 mod/megaton-art/build.py tiles add sheets/roofs_houses.py

    rf_billy     rust-brown scrap: car doors and bonnets riveted in, a row of tyres, a canvas patch
    rf_common    THE POOREST: three tarpaulins held down with stones and tyres, rotten sheets, a hole over the
                 bunks with the rafters showing (the room shows through it)
    rf_lucy      the cared-for one: green and cream paint, a plank deck with planters, washing on a line
    rf_lantern   a kitchen roof: soot, a fat flue with a hat, a roof light glowing from the fire below, kegs
    rf_house     derelict until somebody earns it: the back corner fallen in (open to the sky), sheets slid off,
                 a second hole in the middle of the front slope, boards nailed crosswise
Sheet coordinates: x 0 (right wall) .. w (left wall), y from the back; the front doors are at S.door("front", hx).
"""
import math

from kit import sheet, geo, mat, T, town
from kit import sheet_kit as sk
from kit import roofs_extra as rx
from kit import signs_extra as sx
from kit import gate_extra as gx


# The rust-brown roofs came out a third darker than the stock roofs (mean 57..65 against 91): they get 0.2 stops more
# than the roof default of 0.45, which keeps the rust but lets a phone screen show what lies on them.
LIFT = {"exposure": 0.65}

# ------------------------------------------------------------------------- Billy Creel's
SB = town.shack("billy")


@sheet("rf_billy", kind="roof", size=SB.size, title="Billy Creel's Roof", convert=LIFT)
def rf_billy(ctx):
    back, front = SB.stock_back, SB.stock_front + 0.2
    kinds = (rx.kind(1.5, rx.RUST_BROWN, (0.6, 0.95), 0.0), rx.kind(1.0, rx.ZINC_DARK, (0.45, 0.8), 0.0),
             rx.kind(0.5, rx.OXIDE, (0.3, 0.6), 0.4), rx.kind(0.5, None, (0.3, 0.5), 0.0))
    rx.field(0.03, back, ctx.w - 0.03, front, kinds=kinds, seed=41, sheet=(0.9, 2.0), ragged=0.6, start_ragged=0.4)
    rx.car_door(2.1, 3.3, rot=192.0, colour=rx.DUSTY_BLUE, seed=1)
    rx.car_door(5.3, 6.3, rot=100.0, colour=rx.CREAM, seed=2)
    rx.bonnet(4.7, 2.9, rot=-20.0, colour=rx.OLIVE, seed=3)
    rx.bonnet(1.8, 7.3, rot=95.0, colour=(0.30, 0.20, 0.05), seed=4)
    rx.patch(3.0, 5.0, 4.2, 5.9, rot=-8.0, seed=5)
    rx.tyres([(0.7, 1.35), (1.55, 1.25), (2.45, 1.4), (3.3, 1.3)], seed=5)          # a row along the back edge
    rx.tyres([(6.2, 4.4), (0.7, 5.4)], seed=8)
    rx.tarp_down(3.8, 7.7, 6.6, 10.0, colour=(0.19, 0.16, 0.09), seed=6, weights="mix")
    rx.stub(6.0, 2.9, height=0.5, radius=0.085, cap="cone", seed=2)
    rx.gutter_stain(6.0, 3.05, 4.6, width=0.45)
    rx.board((0.4, 9.2), (3.4, 9.5), seed=3)
    rx.board((0.5, 4.3), (2.9, 4.6), seed=4, colour=(0.30, 0.2, 0.1), grey=0.2)
    rx.rocks([(3.5, 9.9), (0.6, 8.3), (6.3, 6.9)], seed=2)


# ---------------------------------------------------------------------- the common house
SM = town.shack("common")
COMMON_HOLE = (4.7, 3.7, 8.5, 7.3)


@sheet("rf_common", kind="roof", size=SM.size, title="Common House Roof", convert=LIFT)
def rf_common(ctx):
    back, front = SM.stock_back + 0.1, SM.stock_front
    deck = (6.1, 1.0, 9.4, 3.0)
    kinds = (rx.kind(0.8, rx.RUST_BROWN, (0.7, 1.0), 0.0), rx.kind(1.5, rx.ZINC_DARK, (0.5, 0.85), 0.0),
             rx.kind(0.5, None, (0.4, 0.7), 0.0), rx.kind(0.25, rx.OLIVE, (0.4, 0.7), 0.5))
    rx.field(0.03, back, ctx.w - 0.03, front, kinds=kinds, seed=53, sheet=(0.9, 1.8), jitter=0.3, ragged=0.8, start_ragged=0.5,
             skip=rx.any_of(rx.inside(COMMON_HOLE, 0.45), rx.inside(deck, 0.1)))
    rx.hole(*COMMON_HOLE, seed=2, spacing=0.85, purlins=False)
    # boards over the worst of the back, half of them gone again
    sk.rafters(deck[0], deck[1], deck[2], deck[3], z=-0.02, spacing=0.8, purlins=False)
    sk.plank_deck(deck[0], deck[1], deck[2], deck[3], z=0.04, along="y", board=0.24, ragged=0.5, missing=0.22, seed=6, grey=0.7)
    # three tarpaulins, none the same, each held with whatever was heavy
    rx.tarp_down(0.3, 1.3, 3.5, 4.3, colour=(0.19, 0.165, 0.10), seed=3, weights="rocks")
    rx.tarp_down(0.9, 5.0, 4.6, 8.2, colour=(0.085, 0.12, 0.145), seed=5, weights="tyres")
    rx.tarp_down(4.2, 7.9, 7.0, 10.1, colour=(0.12, 0.13, 0.065), seed=8, weights="mix")
    rx.rocks([(4.0, 4.7), (4.4, 4.9), (5.2, 8.0), (9.0, 4.4), (9.2, 7.7), (8.6, 9.6), (0.6, 9.3), (3.5, 9.6), (2.6, 4.6)], seed=4,
             radius=(0.16, 0.27))
    rx.blocks([(8.9, 6.1), (0.6, 4.7)], seed=3)
    rx.board((4.4, 3.2), (8.9, 3.45), seed=6)
    rx.board((8.85, 4.0), (9.1, 7.6), seed=7, colour=(0.2, 0.12, 0.06))
    rx.board((7.5, 8.2), (9.4, 9.0), seed=8, colour=(0.30, 0.2, 0.1), grey=0.2)
    # a bucket under nothing in particular
    geo.lathe([(0.12, 0.0), (0.16, 0.28), (0.145, 0.28), (0.11, 0.02), (0.0, 0.02)], (3.9, 9.0, 0.09),
              mat.painted_metal((0.16, 0.17, 0.17), flaking=0.6, seed=3), 10, name="bucket")


# --------------------------------------------------------------------------- Lucy West's
SU = town.shack("lucy")


@sheet("rf_lucy", kind="roof", size=SU.size, title="Lucy West's Roof")
def rf_lucy(ctx):
    back, front = SU.stock_back + 0.15, SU.stock_front + 0.1          # a scrap crate stands behind this house: show more of it
    kinds = (rx.kind(1.3, rx.BOTTLE, (0.2, 0.45), 0.3), rx.kind(1.0, rx.CREAM, (0.2, 0.45), 0.3),
             rx.kind(0.7, None, (0.15, 0.4), 0.0), rx.kind(0.2, rx.RUST_BROWN, (0.6, 0.8), 0.0))
    rx.field(0.03, back, ctx.w - 0.03, front, kinds=kinds, seed=61, sheet=(0.95, 2.2), ragged=0.2, start_ragged=0.1)
    # her deck: boards on battens, planters, a drum table. It sits in the FRONT half: what stands near the back
    # edge would hide the scrap crate behind the house
    deck = (2.3, 4.3, 5.9, 7.7)
    sk.rafters(deck[0], deck[1], deck[2], deck[3], z=0.11, spacing=0.9, purlins=False, along="y", size=(0.07, 0.07))
    sk.plank_deck(deck[0] - 0.1, deck[1], deck[2] + 0.1, deck[3], z=0.12, along="x", board=0.21, ragged=0.18, seed=4, grey=0.5,
                  colour=(0.28, 0.17, 0.08))
    rx.planter(3.0, 4.7, z=0.16, seed=1)
    rx.planter(4.6, 4.7, z=0.16, seed=2, plants=4)
    rx.planter(5.55, 6.3, z=0.16, rot=90.0, seed=3, size=(1.2, 0.45, 0.26))
    drum = mat.planks(colour=(0.25, 0.15, 0.07), width=0.2, axis="X", grey=0.4, seed=8)
    geo.cylinder(0.38, 0.05, (3.6, 6.6, 0.16), drum, 14, name="table_foot")
    geo.cylinder(0.16, 0.3, (3.6, 6.6, 0.2), drum, 10, name="table_core")
    geo.cylinder(0.4, 0.05, (3.6, 6.6, 0.5), drum, 14, name="table_top")
    geo.box((0.34, 0.34, 0.3), (2.8, 6.7, 0.16), 12.0, mat.planks(axis="Z", width=0.12, seed=4), bevel=0.01, name="seat")
    rx.washing_line((2.4, 8.6), (5.6, 9.3), height=1.35, seed=3, count=4)
    geo.barrel((6.2, 8.1, 0.05), seed=6, material=mat.painted_metal((0.05, 0.13, 0.08), flaking=0.5, seed=6))
    sx.cone(0.36, 0.22, (6.2, 8.1, 0.93 + 0.22), mat.steel(rust=0.5, seed=2), tilt=180.0, name="funnel")
    rx.tyres([(0.8, 8.9)], seed=2)
    rx.blocks([(0.7, 3.4), (6.3, 3.2)], seed=4)
    rx.patch(0.5, 5.0, 1.7, 6.3, rot=4.0, seed=3, material=mat.painted_metal(rx.CREAM, flaking=0.4, seed=5))
    rx.patch(2.6, 1.7, 4.4, 3.0, rot=-3.0, seed=6, material=mat.painted_metal(rx.BOTTLE, flaking=0.5, seed=8))


# ----------------------------------------------------------------- the Brass Lantern's kitchen
SK = town.shack("lantern")


@sheet("rf_lantern", kind="roof", size=SK.size, title="Brass Lantern Roof", convert=LIFT)
def rf_lantern(ctx):
    back, front = SK.stock_back, SK.stock_front + 0.1
    kinds = (rx.kind(1.0, rx.ZINC_DARK, (0.4, 0.8), 0.0), rx.kind(0.9, rx.BRICK, (0.3, 0.6), 0.35),
             rx.kind(0.6, rx.RUST_BROWN, (0.6, 0.9), 0.0), rx.kind(0.4, None, (0.2, 0.5), 0.0))
    rx.field(0.03, back, ctx.w - 0.03, front, kinds=kinds, seed=71, sheet=(1.0, 2.0), soot=0.35, ragged=0.35, start_ragged=0.2)
    # the stove's flue: fat, hatted, guyed, and everything down-slope of it black
    fx_, fy = 6.7, 3.3
    rx.gutter_stain(fx_, fy + 0.1, 7.0, width=1.5)
    rx.stub(fx_, fy, height=0.95, radius=0.16, cap="cone", seed=4)
    wire = mat.flat((0.03, 0.03, 0.03), roughness=0.6)
    for gx_, gy in ((fx_ - 1.3, fy - 0.6), (fx_ + 1.3, fy - 0.5), (fx_ + 0.2, fy + 1.6)):
        geo.pipe([(fx_, fy, 0.8), (gx_, gy, 0.06)], 0.014, wire, name="guy")
        geo.box((0.16, 0.16, 0.06), (gx_, gy, 0.04), 20.0, mat.steel(rust=0.8, seed=2), bevel=0.0, name="eye_plate")
    # a roof light over the range: the fire shows in it at night
    rx.skylight(2.7, 2.7, 4.6, 3.9, panes=(2, 1), lit="fire", seed=5)
    rx.box_vent(8.4, 5.2, size=(0.95, 0.7, 0.5), rot=0.0, seed=2)
    rx.gutter_stain(8.4, 5.6, 7.0, width=0.6)
    # stores kept out of reach: kegs, a crate, a sack
    geo.barrel((2.6, 5.4, 0.05), seed=3, material=mat.planks(colour=(0.22, 0.12, 0.05), axis="Z", width=0.12, seed=3))
    geo.barrel((3.3, 5.75, 0.05), seed=4, radius=0.26, height=0.7,
               material=mat.planks(colour=(0.26, 0.15, 0.07), axis="Z", width=0.12, seed=6))
    geo.crate(size=(0.7, 0.7, 0.5), at=(4.3, 5.6, 0.05), rot=14.0, seed=5)
    gx.sandbag((5.2, 5.9, 0.05), 30.0, seed=3)
    gx.sandbag((5.35, 5.8, 0.2), 60.0, seed=4)
    rx.tyres([(3.0, 4.6), (9.0, 1.8)], seed=7)
    rx.rocks([(0.7, 6.3), (1.0, 6.5), (5.4, 1.4)], seed=5)
    rx.board((0.4, 4.0), (2.2, 4.25), seed=9)


# ------------------------------------------------------------------------ the empty house
SE = town.shack("house")
HOUSE_GAP = (0.0, 0.0, 3.5, 4.4)             # the fallen corner (back right): open to the sky
HOUSE_HOLE = (5.5, 4.7, 7.4, 6.7)


@sheet("rf_house", kind="roof", size=SE.size, title="Empty House Roof", convert=LIFT)
def rf_house(ctx):
    back, front = SE.stock_back, SE.stock_front + 0.1
    kinds = (rx.kind(1.5, rx.RUST_BROWN, (0.75, 1.0), 0.0), rx.kind(0.8, rx.ZINC_DARK, (0.5, 0.9), 0.0),
             rx.kind(0.35, rx.OLIVE, (0.4, 0.7), 0.5), rx.kind(0.55, None, (0.45, 0.8), 0.0),
             rx.kind(0.3, rx.CREAM, (0.45, 0.75), 0.55))
    # the second hole: every sheet that touches its core is gone (rx.inside would need a sheet to lie wholly in it)
    core = (HOUSE_HOLE[0] + 0.55, HOUSE_HOLE[1] + 0.75, HOUSE_HOLE[2] - 0.55, HOUSE_HOLE[3] - 0.75)
    rx.field(0.03, back, ctx.w - 0.03, front, kinds=kinds, seed=83, sheet=(0.9, 1.9), jitter=0.3, ragged=0.7, start_ragged=0.5,
             skip=rx.any_of(rx.touching((HOUSE_GAP[0], HOUSE_GAP[1], HOUSE_GAP[2] - 0.5, HOUSE_GAP[3] - 0.6)),
                            rx.touching(core)))
    # the corner: rafters, one of them broken and hanging, the wall plate; two sheets slid half off, one hanging in
    timber = mat.planks(colour=(0.13, 0.075, 0.04), width=0.4, axis="X", grey=0.3, seed=3)
    sk.rafters(0.15, 1.0, 3.9, 4.6, z=-0.06, spacing=0.75, purlins=True, material=timber)
    geo.box((2.3, 0.08, 0.14), (2.4, 2.6, -0.5), 78.0, timber, bevel=0.006, name="broken_rafter", roll=-22.0)
    rx.tin(2.3, 2.7, 3.3, 4.9, z=-0.04, base=rx.RUST_BROWN, rust=0.95, seed=7, slope=13.0, roll=9.0, name="slid_a")
    rx.tin(0.3, 3.6, 1.3, 5.3, z=0.02, base=rx.ZINC_DARK, rust=0.8, seed=8, slope=-5.0, roll=-7.0, name="slid_b")
    rx.tin(3.2, 0.9, 4.1, 2.7, z=0.06, base=rx.RUST_BROWN, rust=0.9, seed=9, slope=3.0, roll=6.0, name="loose")
    rx.hole(*HOUSE_HOLE, seed=5, spacing=0.6)
    # nailed shut: boards crosswise over the middle, a tarp that nobody tied down again
    rx.board((4.3, 1.8), (7.4, 3.6), seed=3, width=0.24, colour=(0.30, 0.2, 0.1), grey=0.25)
    rx.board((4.5, 3.7), (7.2, 1.7), seed=4, width=0.24, colour=(0.27, 0.17, 0.08), grey=0.35, z=0.09)
    rx.tarp_down(7.2, 6.3, 9.4, 8.6, colour=(0.15, 0.13, 0.08), seed=9, weights="rocks", rope=False, wrinkle=0.07)
    rx.rocks([(8.9, 1.6), (9.2, 4.0), (4.6, 8.3), (1.4, 7.6), (1.7, 7.8)], seed=7, radius=(0.15, 0.26))
    rx.tyres([(3.6, 7.2)], seed=3)
