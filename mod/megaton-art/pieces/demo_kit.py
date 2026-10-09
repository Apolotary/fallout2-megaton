# SPDX-License-Identifier: MIT
"""Kit sampler (stage 1): one small piece per family of kit helpers, so every material and
geometry helper is rendered, converted and shown in the stage gallery next to stock art.
Owned by the pipeline stage; copy the pattern.
"""
from kit import piece, geo, mat, G


@piece("mgt_fence", title="Chain-link Fence", desc="Sagging chain-link on scaffold poles.",
       see_through=True, sight="through", shadow="none", convert={"alpha_threshold": 0.42})
def mgt_fence(ctx):
    # along a hex COLUMN (the other wall direction): hexes (0, 0) .. (0, 3)
    x, y0 = G.hex_xy(0, 0)
    _, y1 = G.hex_xy(0, 3)
    geo.chainlink_panel((x, y0 - 0.4), (x, y1 + 0.4), height=2.1)
    geo.cable((x, y0 - 0.4, 2.15), (x, y1 + 0.4, 2.15), sag=0.12, radius=0.02)      # barbed-wire strand


@piece("mgt_junk", title="Junk", desc="Tires, a drum and something under a tarpaulin.", shadow="baked",
       footprint=[(0, 0), (1, 0)])
def mgt_junk(ctx):
    x1, y1 = G.hex_xy(1, 0)
    geo.tire_stack(3, (0.0, 0.0, 0.0), seed=5)
    geo.tire((0.45, 0.42, 0.0), lying=False, rot=35.0, lean=-18.0, seed=9)
    geo.barrel((x1, y1, 0.0), seed=6)
    geo.box((0.7, 0.5, 0.45), (x1 + 0.25, y1 + 0.6, 0.0), 20.0, mat.tarp((0.16, 0.19, 0.11), seed=2), bevel=0.06)
    geo.set_block(geo.box((0.5, 0.35, 0.06), (x1 - 0.5, y1 + 0.75, 0.0), 70.0, mat.concrete(seed=3), bevel=0.01), 0)


@piece("mgt_hull", title="Fuselage Panel", desc="A slab of airliner skin, riveted and stenciled, propped on a girder.",
       see_through=True)
def mgt_hull(ctx):
    # aircraft aluminium with rivets and a stencilled marking, leaning against two I-beams
    x_r, y = G.hex_xy(0, 0)
    x_l, _ = G.hex_xy(2, 0)
    half = G.SQ_U_M / 4
    panel = geo.slab(x_l - x_r + 2 * half, 2.0, 0.05, (x_l + half, y + 0.05, 0.25), geo.U,
                     mat.aluminium(panel=0.55, seed=1), tilt=-8.0)
    geo.lettering("N-23", ((x_l + x_r) / 2, y + 0.19, 1.25), geo.U, size=0.42, depth=0.008, bevel=0.0, font="din",
                  material=mat.sign_paint((0.05, 0.05, 0.06), wear=0.6, seed=4), tilt=-8.0)
    geo.box((x_l - x_r + 2 * half + 0.1, 0.3, 0.25), ((x_l + x_r) / 2, y, 0.0), geo.U, mat.concrete(seed=1), bevel=0.02)
    for x in (x_l + half - 0.1, x_r - half + 0.1):
        geo.ibeam(2.3, (x, y - 0.22, 0.0), geo.U, mat.steel(rust=0.8, seed=3), vertical=True)
    geo.pipe([(x_l + half, y - 0.3, 1.9), (x_r - half, y - 0.3, 1.9)], 0.04, mat.steel(rust=0.4))
