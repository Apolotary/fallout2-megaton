# SPDX-License-Identifier: MIT
"""Blender side of "render tile sheet": build every sheet of a script and write its passes.

    Blender -b --python pipeline/blender_sheet.py -- --script sheets/foo.py --out build/render
            [--only NAME[,NAME]] [--preview] [--list]

For every sheet `NAME` registered by the script (kit.sheet) this writes build/render/NAME/:
    main_f000.png         beauty of the whole sheet (RGBA, `ss` x supersampled), seen by the game's
                          camera and lit by the same rig as every piece (pipeline/bscene.py)
    shadow.png            decals only: the ground as shadow catcher (alpha = things + their shadow)
    fx_<range>_f000.png   coverage of the objects tagged with an animated palette range (geo.set_fx)
    meta.json             spec, canvas, what was rendered
The picture is cut into 80 x 36 tiles by pipeline/tiles.py (system Python).

How a sheet is set up, beyond what a piece gets:
  * the builder works in SHEET coordinates (pipeline/tilegeo.py): origin on the far corner of
    square (0, 0), z = 0 on the tile plane. For a roof everything it made is then lifted by
    2.66 m, the height at which the engine draws roofs, so materials that gather dirt near the
    ground stay clean, the template's ground lies where the building's floor is and what shows
    through a hole is dark;
  * wrap=True: every object is copied eight times around the sheet (same mesh, same object-space
    texture), so whatever sticks out on one side comes back in on the other;
  * the canvas is the sheet's own px rectangle, not the geometry's: what lies outside the squares
    is simply not part of any tile.
"""
import argparse
import importlib.util
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
sys.path.insert(0, ART)

import kit                              # noqa: E402
from kit import mat                     # noqa: E402
from pipeline import bscene as S        # noqa: E402
from pipeline import proj as P          # noqa: E402
from pipeline import tilegeo as TG      # noqa: E402


def load_script(path):
    name = "mg_sheet_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(module)
    return module


def top_level(objects):
    return [obj for obj in objects if obj.parent is None]


def copy_tree(obj, offset, collection):
    """Linked copy of an object and its children, moved by `offset` (world)."""
    twin = obj.copy()                   # shares the mesh; modifiers and custom properties are copied
    collection.objects.link(twin)
    if obj.parent is None:
        twin.location = (obj.location.x + offset[0], obj.location.y + offset[1], obj.location.z + offset[2])
    for child in obj.children:
        child_twin = copy_tree(child, offset, collection)
        child_twin.parent = twin
        child_twin.matrix_parent_inverse = child.matrix_parent_inverse.copy()
    return twin


def build_scene(name, spec, function):
    S.reset()
    mat.clear_cache()
    function(kit.SheetContext(name, spec))
    scene = bpy.context.scene
    roots = top_level(S.piece_objects())
    lift = TG.ROOF_LIFT_M if spec["kind"] == "roof" else 0.0
    if lift:
        for obj in roots:
            obj.location.z += lift
    if spec["wrap"]:
        w, h = TG.size_m(*spec["size"])
        for obj in roots:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy:
                        copy_tree(obj, (dx * w, dy * h, 0.0), scene.collection)
    bpy.context.view_layer.update()
    return lift


def render_sheet(name, spec, function, out_root, preview):
    out = os.path.join(out_root, name)
    os.makedirs(out, exist_ok=True)
    for stale in os.listdir(out):
        if stale.endswith(".png") or stale == "meta.json":
            os.remove(os.path.join(out, stale))
    ss = 2 if preview else (spec["ss"] or S.DEFAULT_SS)
    samples = 12 if preview else (spec["samples"] or S.DEFAULT_SAMPLES)
    started = time.time()
    lift = build_scene(name, spec, function)
    if "main" not in S.layers():
        raise RuntimeError(f"sheet {name}: the builder made no object")
    n, m = spec["size"]
    canvas = TG.canvas(n, m, lift_px=TG.ROOF_LIFT_PX if spec["kind"] == "roof" else 0)
    S.render_beauty(os.path.join(out, "main_f000.png"), canvas, "main", ss, samples, ground_bounce=True)
    fx_names = sorted({obj.get("mg_fx") for obj in S.piece_objects("main") if obj.get("mg_fx")})
    for fx in fx_names:
        chosen = [obj for obj in S.piece_objects("main") if obj.get("mg_fx") == fx]
        S.render_mask(os.path.join(out, f"fx_{fx}_f000.png"), canvas, chosen, "main", ss)
    if spec["kind"] == "floor" and spec["decal"] and spec["shadow"]:
        S.render_shadow(os.path.join(out, "shadow.png"), canvas, "main", ss, max(8, samples // 2))
    heights = [p.z - lift for p in S.world_points(top_level(S.piece_objects("main")), spacing=1e9)]
    meta = {
        "name": name, "spec": spec, "ss": ss, "samples": samples, "preview": bool(preview),
        "canvas": list(canvas), "lift_m": lift, "fx": fx_names, "rig": S.rig_meta(), "proj": P.describe(),
        "height_m": [round(min(heights), 3), round(max(heights), 3)], "seconds": round(time.time() - started, 1),
    }
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(f"[piece] sheet {name}: {n} x {m} squares, canvas {canvas}, z {meta['height_m']}, {meta['seconds']} s")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--list", action="store_true", help="only write the list of sheets the script defines")
    args = ap.parse_args(argv)
    kit.REGISTRY.clear()
    kit.SHEETS.clear()
    load_script(args.script)
    names = list(kit.SHEETS)
    os.makedirs(args.out, exist_ok=True)
    listing = os.path.join(args.out, "sheets-" + os.path.splitext(os.path.basename(args.script))[0] + ".json")
    with open(listing, "w") as f:
        json.dump({name: kit.SHEETS[name][0] for name in names}, f, indent=1)
    if args.list:
        return
    only = [n for n in args.only.split(",") if n]
    for unknown in set(only) - set(names):
        raise SystemExit(f"{args.script} defines no sheet {unknown!r} (it has: {', '.join(names)})")
    for name in names:
        if only and name not in only:
            continue
        spec, function = kit.SHEETS[name]
        render_sheet(name, spec, function, args.out, args.preview)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.exit(1)             # make Blender's exit code non-zero so the build stops
