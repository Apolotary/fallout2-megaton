# SPDX-License-Identifier: MIT
"""The roof of Moriarty's Saloon: the biggest roof in town (13 x 9 squares) and the grandest.

    python3 mod/megaton-art/build.py tiles preview sheets/roofs_saloon.py
    python3 mod/megaton-art/build.py tiles add sheets/roofs_saloon.py

rf_saloon   From the back (top of the screen) to the eave:
            - a service strip behind the billboard: duckboards along the back edge and down to a hatch,
              a lit lantern light over the bar, the still's flue, kegs, a fan box
            - a red band right across the roof with SALOON painted on it in letters three metres high,
              sun-bleached and flaking: what a trader sees from the crater's far lip
            - the front: a piece of aircraft wing roofs the rented room (its number still on it), a canvas
              patch and crates of empties over the bar end, a ragged eave
Sheet coordinates: x 0 (right wall, office and rented room under x < 7) .. w (left wall), y from the back;
the front door is at x = S.door("front", 105)[0].
"""
import math

from kit import sheet, geo, mat, T, town
from kit import sheet_kit as sk
from kit import roofs_extra as rx
from kit import signs_extra as sx
from kit import gate_extra as gx

S = town.shack("saloon")
BAND = (5.45, 9.75)                    # y of the painted band
WING = (0.45, 10.25, 6.4, 12.95)       # the wing panel over the rented room
WALK = (2.4, 0.95, 9.4, 1.85)          # duckboards behind the billboard


@sheet("rf_saloon", kind="roof", size=S.size, title="Saloon Roof")
def rf_saloon(ctx):
    back, front = S.stock_back, S.stock_front + 0.2
    kinds = (rx.kind(1.0, None, (0.15, 0.45), 0.0), rx.kind(0.8, rx.OXIDE, (0.25, 0.5), 0.3),
             rx.kind(0.5, rx.CREAM, (0.25, 0.5), 0.3), rx.kind(0.6, rx.ZINC_DARK, (0.4, 0.7), 0.0),
             rx.kind(0.3, rx.RUST_BROWN, (0.6, 0.9), 0.0))
    sheets = rx.field(0.03, back, ctx.w - 0.03, front, kinds=kinds, seed=97, sheet=(1.08, 2.5), ragged=0.45, start_ragged=0.3,
                      skip=rx.inside(WING, 0.05))
    # ---- the band and the lettering
    rx.paint_on(sheets, rx.rect(0.25, BAND[0], ctx.w - 0.25, BAND[1]), rx.paint_mat((0.20, 0.045, 0.03), wear=0.42, seed=2))
    line = rx.paint_mat(rx.CREAM, wear=0.5, seed=6)
    rx.paint_on(sheets, [rx.rect(0.5, BAND[0] + 0.22, ctx.w - 0.5, BAND[0] + 0.42),
                         rx.rect(0.5, BAND[1] - 0.42, ctx.w - 0.5, BAND[1] - 0.22)], line, lift=0.011)
    rx.paint_on(sheets, rx.text("SALOON", ctx.w / 2.0, BAND[1] - 0.72, 2.75, rot=180.0, font="impact", stretch=1.42, spacing=1.06),
                rx.paint_mat((0.36, 0.32, 0.21), wear=0.36, seed=11), lift=0.014)
    # ---- the service strip
    sk.rafters(WALK[0], WALK[1], WALK[2], WALK[3], z=0.10, spacing=1.4, purlins=False, along="y", size=(0.07, 0.07))
    sk.plank_deck(WALK[0], WALK[1], WALK[2], WALK[3], z=0.11, along="x", board=0.22, ragged=0.3, missing=0.0, seed=3, grey=0.5)
    sk.plank_deck(9.5, 1.0, 10.3, 3.85, z=0.11, along="y", board=0.26, ragged=0.25, missing=0.0, seed=5, grey=0.6)
    rx.hatch(9.4, 3.95, 10.4, 4.95, colour=(0.26, 0.05, 0.035), seed=4)
    rx.skylight(12.7, 2.3, 15.6, 4.3, panes=(3, 2), lit="fire", boarded=(4,), seed=7, curb=0.2, pitch=0.14)
    rx.stub(7.6, 3.3, height=0.7, radius=0.12, cap="cone", seed=5,
            material=mat.painted_metal((0.20, 0.10, 0.04), flaking=0.5, seed=5))                       # the still
    rx.gutter_stain(7.6, 3.45, 5.3, width=0.7)
    rx.stub(3.6, 3.4, height=0.5, radius=0.085, cap="tee", seed=2)                                    # the office stove
    rx.box_vent(16.7, 3.3, size=(1.0, 0.7, 0.5), rot=0.0, seed=4)
    rx.gutter_stain(16.7, 3.7, 5.2, width=0.55)
    keg = mat.planks(colour=(0.23, 0.13, 0.055), axis="Z", width=0.12, seed=3)
    geo.barrel((11.3, 4.3, 0.05), seed=3, material=keg)
    geo.barrel((11.95, 4.65, 0.05), seed=4, material=mat.planks(colour=(0.27, 0.16, 0.07), axis="Z", width=0.12, seed=6))
    geo.barrel((11.2, 4.95, 0.05), seed=5, radius=0.24, height=0.62, material=keg)
    geo.pipe([(9.4, 1.3, 0.2), (5.5, 1.25, 0.16), (5.5, 0.95, 0.16)], 0.03, mat.flat((0.02, 0.02, 0.022), roughness=0.5),
             name="sign_cable")
    rx.tyres([(16.9, 1.5), (16.0, 1.4), (1.0, 1.6), (12.0, 1.5)], seed=11)
    rx.blocks([(1.3, 4.4), (17.2, 4.9), (6.0, 4.6)], seed=6)
    # ---- the front: a wing for a roof
    grey = (0.31, 0.32, 0.33)
    ww = WING[2] - WING[0]
    rx.wing_panel(*WING, tint=grey, seed=4, rust=0.28,
                  bands=(("u", ww - 1.75, ww - 0.55, rx.DUSTY_BLUE), ("u", ww - 2.1, ww - 1.9, (0.42, 0.40, 0.34)),
                         ("v", 0.0, 0.16, (0.30, 0.20, 0.04))))
    rx.flat_text("N27", WING[0] + 1.75, WING[3] - 0.5, 0.105, 1.45, rot=180.0, font="din",
                 material=mat.sign_paint((0.04, 0.04, 0.045), wear=0.55, seed=3))
    gx.sandbags((WING[0] + 0.3, WING[1] + 0.25), (WING[0] + 2.2, WING[1] + 0.3), courses=1, z=0.1, seed=4)
    rx.tyres([(WING[2] - 0.5, WING[1] + 0.5), (WING[2] - 0.45, WING[3] - 0.45)], z=0.1, seed=6)
    rx.rivets([(WING[0] + 0.15 + 0.5 * k, WING[1] + 0.1) for k in range(12)] + [(WING[0] + 0.15 + 0.5 * k, WING[3] - 0.1) for k in range(12)],
              0.1)
    # the bar end: canvas over a bad place, crates of empties, the eave weighted with whatever
    rx.tarp_down(13.4, 10.4, 16.9, 12.9, colour=(0.20, 0.17, 0.10), seed=12, weights="mix")
    geo.crate(size=(0.7, 0.5, 0.4), at=(12.5, 10.8, 0.05), rot=10.0, seed=7)
    geo.crate(size=(0.7, 0.5, 0.4), at=(12.45, 10.85, 0.46), rot=-8.0, seed=8)
    geo.crate(size=(0.7, 0.5, 0.4), at=(11.6, 10.6, 0.05), rot=80.0, seed=9)
    rx.rocks([(7.4, 12.9), (7.7, 13.0), (9.8, 12.8), (17.3, 13.0), (10.6, 10.4)], seed=5)
    rx.board((6.9, 10.4), (10.6, 11.2), seed=6)
    rx.board((7.0, 11.6), (9.4, 11.5), seed=7, colour=(0.30, 0.2, 0.1), grey=0.2)
