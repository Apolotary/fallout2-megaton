# SPDX-License-Identifier: MIT
"""Blender side of "render piece": build every piece of a script and write its passes.

    Blender -b --python pipeline/blender_piece.py -- --script pieces/foo.py --out build/render
            [--only NAME[,NAME]] [--preview]

For every piece `NAME` registered by the script (kit.piece) this writes build/render/NAME/:
    main_f000.png ...     beauty frames of the main layer (RGBA, `ss` x supersampled)
    shadow.png            same view with the ground as shadow catcher (alpha = piece + shadow)
    pos.png               16-bit world position of the first surface under each sample
    fx_<range>_f000.png   coverage of the objects tagged with an animated palette range (geo.set_fx)
    <layer>_f000.png      beauty of every extra layer (e.g. "halo"), on its own canvas
    meta.json             spec, canvases, footprint, light rig - everything the build needs
--preview renders at 2x supersampling with 12 samples (seconds instead of tens of seconds).
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


def load_script(path):
    name = "mg_piece_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(module)
    return module


def build_scene(name, function, frame, frames):
    S.reset()
    mat.clear_cache()
    function(kit.Context(name, frame, frames))
    bpy.context.view_layer.update()


def hexes_near_geometry(points, radius, max_height):
    """Hexes whose centre is within `radius` m (on the ground) of a surface point lower than max_height."""
    radius2 = radius * radius
    found = set()
    reach = int(radius / 0.4) + 1
    for point in points:
        if not 0.04 < point.z < max_height:
            continue
        dhx, dhy = P.nearest_hex(point.x, point.y)
        for ddx in range(-reach, reach + 1):
            for ddy in range(-reach, reach + 1):
                hx, hy = dhx + ddx, dhy + ddy
                if (hx, hy) in found:
                    continue
                cx, cy = P.hex_xy(hx, hy)
                if (cx - point.x) ** 2 + (cy - point.y) ** 2 <= radius2:
                    found.add((hx, hy))
    return sorted(found, key=lambda h: (h[1], h[0]))


def render_piece(name, spec, function, out_root, preview):
    out = os.path.join(out_root, name)
    os.makedirs(out, exist_ok=True)
    for stale in os.listdir(out):
        if stale.endswith(".png") or stale == "meta.json":      # also drops fx masks of frames that no longer exist
            os.remove(os.path.join(out, stale))
    ss = 2 if preview else (spec["ss"] or S.DEFAULT_SS)
    samples = 12 if preview else (spec["samples"] or S.DEFAULT_SAMPLES)
    frames = int(spec["frames"])
    started = time.time()

    build_scene(name, function, 0, frames)
    layers = S.layers()
    if "main" not in layers:
        raise RuntimeError(f"piece {name}: no object in the main layer")
    wants_shadow = spec["shadow"] != "none"
    canvases = {"main": S.auto_canvas(S.piece_objects("main"), shadow=wants_shadow)}
    for layer in layers:
        if layer != "main":
            canvases[layer] = S.auto_canvas(S.piece_objects(layer), shadow=False)
    surface = []
    blocked = set()
    for obj in S.piece_objects("main"):
        points = S.world_points([obj], spacing=0.07)
        surface += points
        radius = spec["block_radius"]
        if radius is None:
            radius = obj.get("mg_block", 0.22)
        if radius > 0:
            blocked.update(hexes_near_geometry(points, radius, spec["block_height"]))
    footprint = spec["footprint"]
    if footprint == "auto":
        footprint = sorted(blocked, key=lambda h: (h[1], h[0]))
    footprint = [list(h) for h in footprint]
    for extra in spec.get("also_block") or []:           # kit option also_block / kit/also_block.json
        if list(extra) not in footprint:
            footprint.append(list(extra))
    heights = [p.z for p in surface]

    def fx_masks(frame):
        names = sorted({obj.get("mg_fx") for obj in S.piece_objects("main") if obj.get("mg_fx")})
        for fx in names:
            chosen = [obj for obj in S.piece_objects("main") if obj.get("mg_fx") == fx]
            S.render_mask(os.path.join(out, f"fx_{fx}_f{frame:03d}.png"), canvases["main"], chosen, "main", ss)
        return names

    S.render_beauty(os.path.join(out, "main_f000.png"), canvases["main"], "main", ss, samples)
    fx_names = set(fx_masks(0))
    if wants_shadow:
        S.render_shadow(os.path.join(out, "shadow.png"), canvases["main"], "main", ss, max(8, samples // 2))
    S.render_position(os.path.join(out, "pos.png"), canvases["main"], "main", ss)
    for layer in layers:
        if layer != "main":
            S.render_beauty(os.path.join(out, f"{layer}_f000.png"), canvases[layer], layer, ss, samples,
                            ground_bounce=False)
    for frame in range(1, frames):
        build_scene(name, function, frame, frames)
        S.render_beauty(os.path.join(out, f"main_f{frame:03d}.png"), canvases["main"], "main", ss, samples)
        fx_names.update(fx_masks(frame))
        for layer in layers:
            if layer != "main" and S.piece_objects(layer):
                S.render_beauty(os.path.join(out, f"{layer}_f{frame:03d}.png"), canvases[layer], layer, ss, samples,
                                ground_bounce=False)

    meta = {
        "name": name, "spec": spec, "ss": ss, "samples": samples, "preview": bool(preview),
        "layers": layers, "canvases": {k: list(v) for k, v in canvases.items()},
        "footprint": footprint, "height_m": max(heights), "fx": sorted(fx_names), "position": S.position_meta(), "rig": S.rig_meta(),
        "proj": P.describe(), "seconds": round(time.time() - started, 1),
    }
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(f"[piece] {name}: canvas {canvases['main']} footprint {len(footprint)} hexes, "
          f"{frames} frame(s), {meta['seconds']} s")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--list", action="store_true", help="only write the list of pieces the script defines")
    args = ap.parse_args(argv)
    kit.REGISTRY.clear()
    load_script(args.script)
    names = list(kit.REGISTRY)
    os.makedirs(args.out, exist_ok=True)
    listing = os.path.join(args.out, "pieces-" + os.path.splitext(os.path.basename(args.script))[0] + ".json")
    with open(listing, "w") as f:
        json.dump({name: kit.REGISTRY[name][0] for name in names}, f, indent=1)
    if args.list:
        return
    only = [n for n in args.only.split(",") if n]
    for unknown in set(only) - set(names):
        raise SystemExit(f"{args.script} defines no piece {unknown!r} (it has: {', '.join(names)})")
    for name in names:
        if only and name not in only:
            continue
        spec, function = kit.REGISTRY[name]
        render_piece(name, spec, function, args.out, args.preview)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.exit(1)             # make Blender's exit code non-zero so the build stops
