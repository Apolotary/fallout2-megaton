# SPDX-License-Identifier: MIT
"""Roofs of the shop side (screen right): Craterside Supply, the church, the water plant, the clinic, the sheriff's.

    python3 mod/megaton-art/build.py tiles preview sheets/roofs_shops.py [NAME]
    python3 mod/megaton-art/build.py tiles add sheets/roofs_shops.py

One sheet per building, sized from the town snapshot (kit.town). Every roof has one thing the eye
finds from the far side of town:
    rf_craterside   road signs nailed down as patches between blue and teal sheets, an open hatch, crates
    rf_church       a boarded roof with the Children's atom painted over all of it, a green-glowing oculus
    rf_plant        dark industrial sheet, pipe runs, mushroom vents, an OPEN BAY over the pump hall (rafters only)
    rf_clinic       white cross on a worn green panel, a tarp over one corner
    rf_sheriff      the tidiest: sound boards, a white star on a dark panel, a sandbagged corner over the door
Sheet coordinates: x 0 (right wall) .. w (left wall, where these buildings' doors are), y from the back.
"""
import math

from kit import sheet, geo, mat, T, town
from kit import sheet_kit as sk
from kit import roofs_extra as rx
from kit import signs_extra as sx
from kit import gate_extra as gx


# --------------------------------------------------------------------- Craterside Supply
SC = town.shack("craterside")


@sheet("rf_craterside", kind="roof", size=SC.size, title="Craterside Supply Roof")
def rf_craterside(ctx):
    r = ctx.rng
    back, front = SC.stock_back, SC.stock_front + 0.25
    kinds = (rx.kind(1.0, None, (0.2, 0.5), 0.0), rx.kind(0.9, rx.DUSTY_BLUE, (0.25, 0.55), 0.35),
             rx.kind(0.6, rx.TEAL, (0.3, 0.6), 0.4), rx.kind(0.3, rx.MUSTARD, (0.3, 0.6), 0.4),
             rx.kind(0.45, rx.RUST_BROWN, (0.6, 0.9), 0.0))
    rx.field(0.03, back, ctx.w - 0.03, front, kinds=kinds, seed=17, sheet=(1.0, 2.4), ragged=0.5, start_ragged=0.3)
    # what Moira roofs with: the highway department's signs
    rx.road_sign("green", 2.7, 3.3, rot=188.0, size=1.15, seed=1)
    rx.road_sign("diamond", 6.6, 2.9, rot=52.0, size=1.1, seed=2)
    rx.road_sign("stop", 6.0, 6.6, rot=8.0, size=1.15, seed=3)
    rx.road_sign("speed", 1.3, 6.4, rot=172.0, size=1.2, seed=4)
    rx.road_sign("shield", 3.5, 8.6, rot=195.0, size=1.2, seed=5)
    rx.road_sign("green", 6.5, 10.0, rot=96.0, size=0.85, seed=6)
    rx.bonnet(1.5, 10.2, rot=18.0, colour=rx.OXIDE, seed=7)
    # the way up: a hatch propped open, her stock beside it under a net of rope
    rx.hatch(3.3, 4.7, 4.3, 5.7, open_deg=55.0, seed=2, colour=(0.30, 0.22, 0.05))
    geo.crate(size=(0.8, 0.8, 0.55), at=(5.0, 4.4, 0.05), rot=24.0, seed=3)
    geo.crate(size=(0.6, 0.6, 0.45), at=(5.7, 5.0, 0.05), rot=-12.0, seed=5)
    geo.barrel((4.9, 5.4, 0.05), seed=4, material=mat.painted_metal((0.07, 0.13, 0.19), flaking=0.6, seed=4))
    # a cable drum on its side, wire trailing to the back edge (to the mast behind the shop)
    drum = mat.planks(colour=(0.23, 0.13, 0.06), width=0.2, axis="X", grey=0.5, seed=8)
    for z in (0.05, 0.42):
        geo.cylinder(0.42, 0.05, (2.6, 5.9, z), drum, 16, name="drum_cheek")
    geo.cylinder(0.2, 0.37, (2.6, 5.9, 0.08), mat.flat((0.025, 0.025, 0.028), roughness=0.5), 12, name="drum_core")
    geo.pipe([(2.75, 5.7, 0.2), (3.0, 4.2, 0.08), (2.4, 2.4, 0.07), (2.7, 1.0, 0.07)], 0.025,
             mat.flat((0.02, 0.02, 0.022), roughness=0.5), name="wire")
    rx.tyres([(7.6, 4.6), (0.8, 8.4), (4.6, 11.2)], seed=9)
    rx.rocks([(0.6, 2.0), (0.9, 2.2), (7.7, 8.4), (5.2, 1.5)], seed=3)
    rx.board((0.5, 4.4), (2.3, 4.7), seed=2)
    rx.board((6.6, 8.2), (7.9, 7.7), seed=3, colour=(0.30, 0.2, 0.1))


# ---------------------------------------------------------------------------- the church
SH = town.shack("church")


@sheet("rf_church", kind="roof", size=SH.size, title="Church Roof")
def rf_church(ctx):
    back, front = SH.stock_back, SH.stock_front + 0.1
    patch = (0.0, 7.0, 2.7, front + 0.2)                 # the rotten corner, roofed over with tin
    boards = rx.plank_courses(0.03, back, ctx.w - 0.03, front, courses=3, board=0.27, seed=7,
                              colours=((0.25, 0.145, 0.07), (0.19, 0.115, 0.055), (0.30, 0.19, 0.10)), grey=0.6, missing=0.025,
                              tarred=0.10, new=0.05, skip=rx.inside(patch, 0.1))
    rx.field(patch[0] + 0.03, patch[1] - 0.2, patch[2] + 0.1, patch[3] - 0.15, z=0.02, kinds=(rx.RUSTED, rx.BARE_OLD), seed=5,
             sheet=(0.95, 1.9), ragged=0.3)
    # the Children's mark, as big as the roof: three orbits and, for a nucleus, a round roof light that glows
    cx, cy = ctx.w / 2.0 + 0.15, 5.45
    yellow = rx.paint_mat((0.40, 0.31, 0.07), wear=0.33, seed=9, fade=0.4)
    for k, turn in enumerate((0.0, 60.0, 120.0)):                  # each orbit its own height: where they cross
        rx.paint_on(boards, rx.ring(cx, cy, 3.95, 1.5, 0.44, rot=turn), yellow, lift=0.007 + 0.004 * k)   # they must not coincide
    steel = mat.steel(rust=0.6, seed=4)
    geo.cylinder(0.80, 0.012, (cx, cy, 0.05), rx.tar(), 20, name="tar")
    geo.lathe([(0.66, 0.0), (0.66, 0.18), (0.54, 0.18), (0.54, 0.0)], (cx, cy, 0.05), steel, 20, name="oculus_curb")
    geo.set_fx(geo.cylinder(0.54, 0.02, (cx, cy, 0.17), mat.emitter((0.3, 1.0, 0.25), 1.2), 20, name="oculus_glass"), "slime")
    for a in (30.0, 150.0):
        ca, sa = math.cos(math.radians(a)) * 0.6, math.sin(math.radians(a)) * 0.6
        geo.pipe([(cx - ca, cy - sa, 0.22), (cx + ca, cy + sa, 0.22)], 0.025, steel, name="oculus_bar")
    # candles where the orbits cross, burnt down to stubs in tins
    wax = mat.flat((0.42, 0.37, 0.27), roughness=0.6)
    for k in range(6):
        a = math.radians(30.0 + 60.0 * k)
        px, py = cx + 1.72 * math.cos(a), cy + 1.72 * math.sin(a)
        geo.cylinder(0.09, 0.07, (px, py, 0.05), steel, 8, name="tin")
        geo.cylinder(0.05, 0.16, (px, py, 0.08), wax, 8, name="candle")
        geo.bulb((px, py, 0.31), (1.0, 0.6, 0.2), 0.065, 2.5, fx="fire")
    # a ladder left lying, a row of stones along the patched corner, loose boards
    gx.ladder((8.3, 6.9, 0.10), (7.5, 10.0, 0.10), width=0.42)
    rx.rocks([(2.8, 7.3), (2.9, 8.2), (2.75, 9.1), (2.9, 9.9)], seed=6)
    rx.tyres([(1.2, 8.6)], seed=2)
    rx.board((0.4, 1.6), (2.6, 1.3), seed=7, colour=(0.30, 0.2, 0.1), grey=0.2)
    rx.board((6.5, 1.5), (9.2, 1.9), seed=8)


# ----------------------------------------------------------------------- the water plant
SP = town.shack("plant")
BAY = (4.25, 5.5, 7.55, 9.3)                  # the open bay over the pump hall: x0, y0, x1, y1


@sheet("rf_plant", kind="roof", size=SP.size, title="Water Plant Roof", convert={"exposure": 0.65})   # dark sheet: 0.2 stops over the roof default
def rf_plant(ctx):
    back, front = SP.stock_back, SP.stock_front + 0.2
    blue = (0.085, 0.115, 0.135)
    kinds = (rx.kind(1.0, rx.ZINC_DARK, (0.4, 0.75), 0.0), rx.kind(0.8, blue, (0.3, 0.6), 0.4),
             rx.kind(0.45, rx.RUST_BROWN, (0.65, 0.95), 0.0), rx.kind(0.5, None, (0.25, 0.5), 0.0))
    sheets = rx.field(0.03, back, ctx.w - 0.03, front, kinds=kinds, seed=23, sheet=(1.05, 2.5), ragged=0.3, start_ragged=0.2,
                      skip=rx.inside(BAY, 0.5))
    # the open bay: nothing but rafters over the pumps, a hazard stripe painted round it, a steel kerb
    rx.hole(*BAY, hanging=False, curled=False, spacing=0.75, seed=3)
    stripe = gx.hazard(width=0.42, wear=0.4, seed=3, uv=False)
    g = 0.85
    for box in ((BAY[0] - g, BAY[1] - g, BAY[2] + g, BAY[1] - 0.25), (BAY[0] - g, BAY[3] + 0.25, BAY[2] + g, BAY[3] + g),
                (BAY[0] - g, BAY[1] - g, BAY[0] - 0.25, BAY[3] + g), (BAY[2] + 0.25, BAY[1] - g, BAY[2] + g, BAY[3] + g)):
        rx.paint_on(sheets, rx.rect(*box), stripe)
    steel = mat.steel(rust=0.55, seed=6)
    for x0, y0, x1, y1 in ((BAY[0] - 0.3, BAY[1] - 0.3, BAY[2] + 0.3, BAY[1] - 0.18), (BAY[0] - 0.3, BAY[3] + 0.18, BAY[2] + 0.3, BAY[3] + 0.3),
                           (BAY[0] - 0.3, BAY[1] - 0.3, BAY[0] - 0.18, BAY[3] + 0.3), (BAY[2] + 0.18, BAY[1] - 0.3, BAY[2] + 0.3, BAY[3] + 0.3)):
        geo.box((x1 - x0, y1 - y0, 0.16), ((x0 + x1) / 2.0, (y0 + y1) / 2.0, 0.02), 0.0, steel, bevel=0.01, name="kerb")
    # pipes: the rising main from the back, across the roof to the tanks in the yard (front right)
    grey = mat.painted_metal((0.14, 0.15, 0.15), flaking=0.5, seed=8)
    rx.pipe_run([(1.25, 1.15), (1.25, 8.6), (2.3, 10.0), (2.3, 15.0)], radius=0.10, z=0.13, material=grey, seed=2)
    rx.pipe_run([(2.05, 1.15), (2.05, 3.9), (3.3, 4.6), (3.3, 12.2), (1.0, 13.3), (1.0, 15.0)], radius=0.07, z=0.11,
                material=mat.steel(rust=0.85, seed=3), seed=5)
    red = sx.enamel((0.42, 0.05, 0.03), chips=0.35, seed=2)
    for px, py in ((1.25, 3.0), (2.3, 12.0)):                                   # valve hand wheels
        geo.cylinder(0.035, 0.34, (px, py, 0.33), steel, 8, name="valve_stem")
        sx.ring_xy((px, py, 0.67), 0.2, red, tube=0.03)
        geo.pipe([(px - 0.2, py, 0.67), (px + 0.2, py, 0.67)], 0.02, red, name="spoke")
        geo.pipe([(px, py - 0.2, 0.67), (px, py + 0.2, 0.67)], 0.02, red, name="spoke")
    rx.gutter_stain(1.25, 3.2, 5.4, width=0.55)
    rx.gutter_stain(3.3, 12.3, 14.6, width=0.5)
    # a row of vents over the back room, the generator's cooler box, plate where feet go
    for k, (px, hgt) in enumerate(((4.6, 0.42), (5.6, 0.5), (6.6, 0.36))):
        rx.mushroom(px, 11.3, height=hgt, radius=0.24, seed=k)
    rx.box_vent(6.1, 13.2, size=(1.3, 0.8, 0.55), rot=0.0, seed=3)
    rx.gutter_stain(6.1, 13.7, 15.0, width=0.6)
    rx.patch(4.5, 2.2, 7.2, 4.2, material=mat.steel(rust=0.45, colour=(0.075, 0.075, 0.08), seed=5), rot=2.0, seed=4)
    rx.patch(5.0, 2.6, 6.2, 3.6, z=0.075, material=mat.steel(rust=0.9, seed=7), rot=-9.0, seed=6)   # a patch on the patch
    rx.tyres([(7.5, 1.6), (0.6, 6.0)], seed=4)
    rx.blocks([(7.4, 14.4), (4.4, 14.2), (3.9, 9.9)], seed=2)


# ---------------------------------------------------------------------------- the clinic
SL = town.shack("clinic")


@sheet("rf_clinic", kind="roof", size=SL.size, title="Clinic Roof")
def rf_clinic(ctx):
    back, front = SL.stock_back, SL.stock_front + 0.15
    kinds = (rx.kind(1.0, None, (0.15, 0.45), 0.0), rx.kind(1.5, rx.WHITE, (0.2, 0.5), 0.3),
             rx.kind(0.45, rx.RUST_BROWN, (0.6, 0.9), 0.0), rx.kind(0.3, rx.TEAL, (0.3, 0.6), 0.4))
    sheets = rx.field(0.03, back, ctx.w - 0.03, front, kinds=kinds, seed=31, ragged=0.4, start_ragged=0.25)
    cx, cy = ctx.w / 2.0 + 0.3, (SL.back + SL.front) / 2.0 - 0.15
    rx.paint_on(sheets, rx.rect(cx - 2.75, cy - 3.3, cx + 2.75, cy + 3.3), rx.paint_mat((0.035, 0.25, 0.10), wear=0.4, seed=3))
    rx.paint_on(sheets, rx.cross(cx, cy, 4.7, arm=0.3), rx.paint_mat(rx.WHITE, wear=0.3, seed=5), lift=0.013)
    rx.tarp_down(0.35, 7.0, 3.0, 9.9, colour=(0.10, 0.14, 0.16), seed=4, weights="tyres")
    rx.skylight(0.5, 4.2, 1.9, 5.6, panes=(1, 2), boarded=(1,), seed=3)
    rx.patch(8.0, 1.5, 9.3, 2.9, rot=6.0, seed=2)
    rx.stub(8.5, 8.3, height=0.5, radius=0.09, cap="tee", seed=3)
    rx.gutter_stain(8.5, 8.5, 10.1, width=0.5)
    rx.tyres([(4.3, 9.6), (6.0, 9.7)], seed=3)
    rx.blocks([(4.2, 1.3), (9.1, 5.6)], seed=5)
    rx.board((6.5, 9.5), (9.2, 9.75), seed=4)


# ------------------------------------------------------------------------- the sheriff's
SS = town.shack("sheriff")


@sheet("rf_sheriff", kind="roof", size=SS.size, title="Sheriff's Roof")
def rf_sheriff(ctx):
    back, front = SS.stock_back, SS.stock_front + 0.05
    boards = rx.plank_courses(0.03, back, ctx.w - 0.03, front, courses=2, board=0.25, seed=11,
                              colours=((0.235, 0.14, 0.07), (0.205, 0.12, 0.06)), grey=0.3, tarred=0.05, new=0.10, ragged=0.08)
    cx, cy = 5.0, 4.55
    rx.paint_on(boards, rx.rect(cx - 2.35, cy - 2.5, cx + 2.35, cy + 2.5), rx.paint_mat((0.045, 0.06, 0.085), wear=0.28, seed=2))
    rx.paint_on(boards, rx.star(cx, cy, 2.15, rot=-30.0), rx.paint_mat(rx.WHITE, wear=0.22, seed=4), lift=0.013)
    # the armoury end (right): plate bolted over the boards, a second plate over the seam
    plate = mat.steel(rust=0.4, colour=(0.07, 0.07, 0.075), seed=3)
    rx.patch(0.25, 1.5, 2.2, 4.6, material=plate, seed=1, studs=0.3)
    rx.patch(0.25, 4.5, 2.2, 7.9, material=mat.steel(rust=0.6, colour=(0.07, 0.07, 0.075), seed=5), seed=2, studs=0.3)
    rx.patch(0.6, 4.1, 1.9, 5.0, z=0.075, material=mat.steel(rust=0.85, seed=9), rot=-4.0, seed=3)
    # a sandbagged corner over the door, looking down the track to the gate: ammunition box, a stool, a lamp
    rx.sandbag_ring(8.25, 7.2, radius=0.95, courses=2, sweep=(-60.0, 200.0), seed=4)
    geo.box((0.5, 0.3, 0.26), (8.1, 6.9, 0.05), 20.0, mat.painted_metal((0.11, 0.13, 0.07), flaking=0.4, seed=2), bevel=0.01,
            name="ammo_box")
    geo.cylinder(0.17, 0.3, (8.7, 6.6, 0.05), mat.planks(axis="Z", seed=3), 10, name="stool")
    gx.floodlight((7.9, 8.0, 0.45), (7.4, 14.0, -1.5), size=0.2, lit=False)
    geo.pipe([(7.9, 8.0, 0.04), (7.9, 8.0, 0.45)], 0.03, mat.steel(rust=0.5, seed=2), name="lamp_post")
    rx.tyres([(3.2, 8.1)], seed=6)
    rx.board((6.0, 1.4), (8.8, 1.2), seed=5, colour=(0.33, 0.23, 0.12), grey=0.15)
