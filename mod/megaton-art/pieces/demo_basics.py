# SPDX-License-Identifier: MIT
"""Pipeline demo pieces (stage 1): the plainest possible props, to compare against stock art.

Owned by the pipeline stage; asset authors should copy the pattern, not edit this file.
"""
from kit import piece, geo, mat, G


@piece("mgt_crate", title="Crate", desc="A plank crate, nailed shut and left out in the sun.", material="wood",
       shadow="baked")
def mgt_crate(ctx):
    geo.crate((0.9, 0.9, 0.82), at=(0, 0, 0), rot=geo.U, seed=2)


@piece("mgt_wall_u", title="Corrugated Wall", desc="Sheets of rusted corrugated iron.", kind="wall",
       see_through=True)
def mgt_wall_u(ctx):
    # two floor squares (four hexes) of scrap wall along a hex row, on the stock wall line
    x_right, y = G.hex_xy(0, 0)
    x_left, _ = G.hex_xy(3, 0)
    half = G.SQ_U_M / 4
    front = 0.05                     # a thin sheet stands almost on the line through the hex centres
    geo.corrugated_wall((x_left + half, y + front), (x_right - half, y + front), height=G.STOCK_WALL_H,
                        seed=4, ragged=0.12, lean=2.0)
