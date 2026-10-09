#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Offline pictures of the town (pixel-exact with the engine, tools/render_map.py).

    python3 mod/megaton/layout/preview.py [--out DIR] [--staging DIR] [name ...]

Writes into DIR (default run/mg-layout-preview; not inside the staging tree, which
test.py wipes and build.py packs whole):
    overview.png, overview-roofs.png       the whole town, scaled to 1800 px
    blockers.png                           the same with blocked hexes tinted
    <building>.png, -blockers.png, -roofs.png   full-size crops per building (numbered hexes)
    <building>-plain.png                   the same without numbers: what the player sees inside
    gate.png, pool.png, apron.png
    plaza.png, alley.png, east-nook.png, west-nook.png, bus-yard.png, plant-yard.png,
    camp.png, lean-to.png                  the districts dressed by layout/outdoors.py
With names, only those pictures are made (a building key, "overview", "gate", ...).
The staging tree (default mod/megaton/out-layout) must hold the data step's
tables: python3 mod/megaton/build.py --out mod/megaton/out-layout ids data protos scripts
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(MOD))
sys.path.insert(0, MOD)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from f2lib import GameFiles, geometry as g  # noqa: E402
from render_map import MapRenderer, Overlay, save_png  # noqa: E402

import layout  # noqa: E402
from layout import plan  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out")
    parser.add_argument("--staging", default=os.path.join(MOD, "out-layout"))
    parser.add_argument("--no-cast", action="store_true")
    parser.add_argument("names", nargs="*")
    args = parser.parse_args()
    out = args.out or os.path.join(ROOT, "run", "mg-layout-preview")
    os.makedirs(out, exist_ok=True)
    gf = GameFiles(overlay=args.staging)
    m, info = layout.build(gf, with_cast=not args.no_cast, log=lambda *a: None)
    renderer = MapRenderer(gf)
    centre = g.tile_at(100, 96)

    def want(name):
        return not args.names or name in args.names

    def shot(name, tile, radius, roofs=False, scale=1.0, numbers=None, blockers=False, grid=False):
        scene = renderer.render(m, 0, roofs=roofs, crop=(tile, radius))
        if numbers or blockers or grid or scale != 1.0:
            overlay = Overlay(scene, scale)
            if blockers:
                overlay.blockers()
            if grid:
                overlay.grid()
            if numbers:
                overlay.tile_numbers(numbers)
            image = overlay.image
        else:
            image = scene.image()
        path = os.path.join(out, name + ".png")
        save_png(image, path)
        print(path)

    if want("overview"):
        shot("overview", centre, 47, scale=0.62, numbers=10)
        shot("overview-roofs", centre, 47, roofs=True, scale=0.62)
    if want("blockers"):
        shot("blockers", centre, 47, scale=0.62, blockers=True)
    for key, spec in plan.BUILDINGS.items():
        if want(key):
            lo_x, lo_y, hi_x, hi_y = spec["box"]
            tile = g.tile_at((lo_x + hi_x) // 2, (lo_y + hi_y) // 2)
            radius = max(hi_x - lo_x, hi_y - lo_y) // 2 + 6
            shot(key, tile, radius, numbers=5)
            shot(key + "-plain", tile, radius)
            shot(key + "-blockers", tile, radius, blockers=True, grid=True)
            shot(key + "-roofs", tile, radius, roofs=True)
    if want("gate"):
        shot("gate", g.tile_at(*plan.GATE), 16, numbers=5)
        shot("gate-blockers", g.tile_at(*plan.GATE), 10, blockers=True, grid=True)
    if want("pool"):
        shot("pool", g.tile_at(*plan.BOMB), 8, blockers=True, grid=True, numbers=2)
        shot("pool-plain", g.tile_at(*plan.BOMB), 14)
    if want("apron"):
        shot("apron", g.tile_at(100, 133), 34, scale=0.75)
    for name, (hx, hy), radius in (("plaza", (100, 84), 13), ("alley", (85, 68), 8), ("east-nook", (64, 77), 9),
                                   ("west-nook", (136, 78), 9), ("bus-yard", (135, 105), 10),
                                   ("plant-yard", (66, 108), 9), ("camp", (80, 133), 9), ("lean-to", (123, 133), 8)):
        if want(name):
            shot(name, g.tile_at(hx, hy), radius)


if __name__ == "__main__":
    main()
