#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The tile proof: custom roof and floor tiles in the real engine, measured.

    python3 mod/megaton-art/stage/tiles/build_stage.py             map, patch, offline pictures
    python3 mod/megaton-art/stage/tiles/build_stage.py --engine    ... the engine by day and night, and the checks

The map (stage/tiles/data/maps/mgtiles.map; mgtilesn.map is the same at night):
    shack A   a stock shack (the town's own kit, mod/megaton/layout/kit.py) RE-ROOFED with the sheet
              mgx_roof_demo of sheets/demo_tiles.py: one picture of 7 x 7 squares, with a hole
    shack B   the same shack untouched, beside it
    shack C   a smaller one whose roof field is filled with the wrapping sheet mgx_tin_wrap
              (its trim and eave rows stay stock)
    floor     mgx_plates (solid) and mgx_junk (decal, laid over two different stock grounds)
    canopies  two roofs over open ground: one hides when the player walks under it (like any
              roof), one carries the never-hide flag (TileSet.never_hide)
    a stock lamp post between A and B (roofs get no lamp light, stock or custom)
The demo sheets are rendered at full quality but registered in a PRIVATE copy of the manifest
and written to stage/tiles/data: they claim no tile slots of the art mod.

Checks (--engine; run names clutter-setup-tiles-day / -night), printed and saved to stage/tiles/report.json:
    seams      the engine's picture of roof A, shack untouched and at full daylight, is the sheet
               pixel for pixel (compared with the offline renderer, which paints the cut tiles)
    hide       with the player inside A its roof is gone and B's is unchanged; outside again it is back
    night      roof A and roof B darken by the same factor (the engine lights every roof with the
               map's ambient light only)
    hole       pixels of the hole show what stands inside the shack
    canopies   what the two roofs over open ground do when the player stands under them
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)

import numpy as np                                                                 # noqa: E402
from PIL import Image                                                              # noqa: E402

from f2lib import GameFiles, MapFile, geometry as g, lst, mapstxt, write_dat2      # noqa: E402
from render_map import MapRenderer                                                 # noqa: E402

import build as art_build                                                          # noqa: E402
from pipeline import data, tiles                                                   # noqa: E402
from pipeline import tilegeo as TG                                                 # noqa: E402

OVERLAY = os.path.join(HERE, "data")
PATCH = os.path.join(HERE, "patch-tiles.dat")
SHOTS = os.path.join(HERE, "shots")
SCRIPT = os.path.join(ART, "sheets", "demo_tiles.py")
DAY, NIGHT = "mgtiles", "mgtilesn"
NIGHT_SCRIPT = "mgnight"
RES = (1280, 960)
BAR = 100                                   # the interface bar below the iso window
LAMP_POST = 0x02000376
VILLAGER = 0x01000003

BOX_A = (100, 101, 114, 111)                # custom roof
BOX_B = (78, 101, 92, 111)                  # stock roof
BOX_C = (122, 103, 130, 111)                # wrap fill
DOOR_A, DOOR_B = (107, 111), (85, 111)
VIEW = (96, 108)                            # view centre of every shot
CANOPY_HIDE = [(qx, qy) for qx in range(52, 55) for qy in range(62, 64)]
CANOPY_STAY = [(qx, qy) for qx in range(44, 47) for qy in range(62, 64)]
T = lambda h: g.tile_at(*h)                 # noqa: E731


def make_sheets(preview=False):
    """Render the demo sheets and put their tiles into the stage's own tree. Returns the private manifest."""
    render_dir = os.path.join(art_build.PREVIEW, "render") if preview else art_build.RENDER
    specs = art_build.run_blender(SCRIPT, render_dir, preview=preview, what="sheet")
    stock = GameFiles()
    manifest = data.load_manifest()
    relative = os.path.relpath(SCRIPT, ART)
    for name in specs:
        result = tiles.process(os.path.join(render_dir, name), stock.palette, stock)
        entry = tiles.register(manifest, result, relative, stock)
        tiles.write_sheet_files(result, stock.palette, OVERLAY)
        art_build.report_sheet(result, entry, manifest)
    tiles.write_data(manifest, OVERLAY)
    return manifest


def build_map(gf, ts, name, index, night):
    m = MapFile.new(name, gf)
    m.index = index
    ground = ("edg5000.frm", "edg5003.frm", "edg5002.frm", "edg5001.frm", "edg5004.frm")
    m.fill_floor(25, 30, 80, 80, lambda x, y: ground[(x * 7 + y * 3 + (x * y) % 5) % 5])
    m.fill_floor(40, 59, 46, 61, "edg4002.frm")                       # rough ground under one of the decals
    shack_a = art_build.preview_shack(m, BOX_A, door=DOOR_A[0], seed=7)
    art_build.preview_shack(m, BOX_B, door=DOOR_B[0], seed=7)
    art_build.preview_shack(m, BOX_C, seed=5)
    ts.reroof(m, BOX_A, "mgx_roof_demo")
    ts.reroof(m, BOX_C, "mgx_tin_wrap")
    ts.paint_floor(m, "mgx_plates", 51, 58)
    ts.paint_floor(m, "mgx_plates", 53, 58)
    ts.paint_floor(m, "mgx_junk", 47, 58)                             # on smooth ground
    ts.paint_floor(m, "mgx_junk", 41, 59)                             # on rough ground: other composed tiles
    ts.fill_roof(m, "mgx_tin_wrap", CANOPY_HIDE)
    ts.fill_roof(m, "mgx_tin_wrap", CANOPY_STAY)
    ts.never_hide(m, CANOPY_STAY)
    m.add_object(LAMP_POST, T((96, 114)), light_distance=6, light_intensity=0x10000)
    for hx, hy in ((110, 105), (88, 105), (108, 126), (92, 126)):     # inside A (under the hole), inside B, under each canopy
        m.add_object(VILLAGER, T((hx, hy)), rotation=g.SE)
    m.set_entrance(T((96, 130)), elevation=0, rotation=0)
    if night:
        m.set_map_script(NIGHT_SCRIPT)
    problems = [p for p in m.validate() if p.startswith("error")]
    if problems:
        raise SystemExit("tile stage map: " + "; ".join(problems[:8]))
    return m


def steps(prefix):
    park = f"move {RES[0] // 2} {RES[1] - 30}"               # the mouse on the interface bar: no hex cursor in the picture
    view = f"center {T(VIEW)}"                                # `dude` re-centres the view on the player: centre again after it
    home = [f"dude {T((96, 130))}", "wait 300", view, park, "wait 600"]
    lines = [f"# generated by stage/tiles/build_stage.py ({prefix})", "wait 1200"] + home + ["state", f"shot shots/{prefix}-1-outside.ppm"]
    for label, door, shot_in in (("a", DOOR_A, 2), ("b", DOOR_B, 4)):
        # in through the door ON FOOT (the roof must go the moment he steps under it), a picture, out again on foot
        lines += [f"dude {T((door[0], door[1] + 2))}", "wait 300", view, "wait 300", f"use {T(door)}", "wait 6000",
                  f"clicktile {T((door[0], door[1] - 4))}", "wait 5000", park, "wait 300", "state",
                  f"shot shots/{prefix}-{shot_in}-inside-{label}.ppm",
                  f"clicktile {T((door[0], door[1] + 5))}", "wait 6000", park, "wait 300", "state"]
        if label == "a":
            lines += [f"shot shots/{prefix}-3-outside-again.ppm"]
    lines += [f"dude {T((106, 126))}", "wait 300", view, park, "wait 600", "state", f"shot shots/{prefix}-5-under-hiding-canopy.ppm",
              f"dude {T((90, 126))}", "wait 300", view, park, "wait 600", "state", f"shot shots/{prefix}-6-under-never-hide-canopy.ppm"]
    lines += home + [f"shot shots/{prefix}-7-outside-last.ppm", "quit 0", ""]
    return "\n".join(lines)


def build(preview=False):
    shutil.rmtree(OVERLAY, ignore_errors=True)
    for sub in ("maps", "data", "scripts"):
        os.makedirs(os.path.join(OVERLAY, sub))
    manifest = make_sheets(preview)
    base = GameFiles()
    maps_txt = base.read("data/maps.txt")
    indices = {}
    for lookup, name in (("MG Tile Proof", DAY), ("MG Tile Proof Night", NIGHT)):
        maps_txt, indices[name] = mapstxt.append_map(maps_txt, lookup, name, saved=False, automap=False)
    with open(os.path.join(OVERLAY, "data", "maps.txt"), "wb") as f:
        f.write(maps_txt)
    out = os.path.join(OVERLAY, "scripts", NIGHT_SCRIPT + ".int")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ssl.py"), "compile", os.path.join(HERE, NIGHT_SCRIPT + ".ssl"),
                    "-o", out], check=True, stdout=subprocess.DEVNULL)
    scripts_lst = lst.append_lines(base.read("scripts/scripts.lst"), [lst.ScriptList.format_line(NIGHT_SCRIPT, "tile proof: night", 0)])
    with open(os.path.join(OVERLAY, "scripts", "scripts.lst"), "wb") as f:
        f.write(scripts_lst)
    gf = GameFiles(overlay=[OVERLAY])
    ts = tiles.TileSet(manifest, gf, out_dir=OVERLAY)
    built = {}
    for name, night in ((DAY, False), (NIGHT, True)):
        m = build_map(gf, ts, name, indices[name], night)
        m.save(os.path.join(OVERLAY, "maps", m.file_name))
        built[name] = m
    files = {}
    for top in ("art", "maps", "data", "scripts"):
        for root, dirs, names in os.walk(os.path.join(OVERLAY, top)):
            dirs.sort()
            for file_name in sorted(names):
                full = os.path.join(root, file_name)
                with open(full, "rb") as f:
                    files[os.path.relpath(full, OVERLAY).replace(os.sep, "\\")] = f.read()
    write_dat2(files, PATCH)
    for prefix in ("day", "night"):
        with open(os.path.join(HERE, f"steps-{prefix}.txt"), "w") as f:
            f.write(steps(prefix))
    os.makedirs(SHOTS, exist_ok=True)
    gf.refresh()
    scene = MapRenderer(gf).render(built[DAY], 0, roofs=True, view=(T(VIEW), RES[0], RES[1] - BAR))
    scene.image().save(os.path.join(SHOTS, "offline-outside.png"))
    room = tiles.budget(manifest)
    print(f"[tile stage] {len(files)} files in {os.path.relpath(PATCH, ROOT)}; {len(tiles.section(manifest)['sheets'])} demo sheets, "
          f"{room['used']} tile slots in the stage's private list")
    return manifest, gf, built


def run_engine(prefix, map_name):
    run = f"clutter-setup-tiles-{prefix}"
    command = [sys.executable, os.path.join(ROOT, "tools", "f2test.py"), "--name", run, "--fresh", "--map", map_name + ".map",
               "--res", f"{RES[0]}x{RES[1]}", "--timeout", "300", "--debug-log", "--patch", PATCH,
               "--steps", os.path.join(HERE, f"steps-{prefix}.txt")]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    states = [line.strip() for line in result.stdout.splitlines() if "state map" in line]
    tail = [line for line in result.stdout.splitlines() if "exit code" in line or "TIMEOUT" in line]
    shots = os.path.join(ROOT, "run", run, "shots")
    count = 0
    for name in sorted(os.listdir(shots)) if os.path.isdir(shots) else []:
        if name.endswith(".png"):
            shutil.copy2(os.path.join(shots, name), os.path.join(SHOTS, name))
            count += 1
    bad = []
    log = os.path.join(ROOT, "run", run, "debug.log")
    if os.path.exists(log):
        with open(log, errors="replace") as f:
            bad = [line.strip() for line in f if "rror" in line or "ould not" in line or "nable" in line]
    print(f"[tile stage] {run}: {count} screenshots, {len(states)} state line(s), {len(bad)} debug.log problem line(s) | " + " | ".join(tail))
    for line in bad[:6]:
        print(f"[tile stage]   debug.log: {line}")
    return states, bad


# --------------------------------------------------------------------- checks
def screen_masks(gf, m):
    """Screen-space masks (iso window of the shots) of roof A, roof B, the hole in A and the canopies."""
    window = (RES[1] - BAR, RES[0])
    cx, cy = g.hex_world(T(VIEW))
    dx, dy = (RES[0] - 32) // 2 - cx, (RES[1] - BAR - 16) // 2 - cy
    stock = tiles.stock_mask()
    tile_fid = 0x04000000

    def roof(squares, own_pixels=False):
        mask = np.zeros(window, bool)
        for qx, qy in squares:
            x, y = g.roof_world(qy * 100 + qx)
            x, y = x + dx, y + dy
            shape = stock
            if own_pixels:
                shape = gf.art.load(tile_fid | m.roof(qx, qy)).frame(0, 0).array() > 0
            x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + 80, window[1]), min(y + 36, window[0])
            if x0 < x1 and y0 < y1:
                mask[y0:y1, x0:x1] |= shape[y0 - y:y1 - y, x0 - x:x1 - x]
        return mask

    a, b = TG.Shack(BOX_A), TG.Shack(BOX_B)
    inner = lambda s: [(s.first[0] + i, s.first[1] + j) for j in range(1, s.size[1] - 1) for i in range(s.size[0])]   # noqa: E731
    a_drawn = roof(a.squares(), own_pixels=True)
    return {"roof_a": a_drawn, "roof_a_field": roof(inner(a)) & a_drawn, "roof_b": roof(b.squares(), own_pixels=True),
            "hole_a": roof(inner(a)) & ~a_drawn, "canopy_hide": roof(CANOPY_HIDE), "canopy_stay": roof(CANOPY_STAY)}


def load(name):
    path = os.path.join(SHOTS, name)
    return np.asarray(Image.open(path).convert("RGB"), np.int16)[:RES[1] - BAR] if os.path.exists(path) else None


def same(a, b, mask):
    return round(float(((a == b).all(axis=2) & mask).sum()) / max(1, int(mask.sum())), 4)


def luma(image, mask):
    return round(float((image[mask] @ np.array([0.299, 0.587, 0.114])).mean()), 2)


def check(gf, built, states):
    m = built[DAY]
    masks = screen_masks(gf, m)
    renderer = MapRenderer(gf)
    offline = np.asarray(renderer.render(m, 0, roofs=True, view=(T(VIEW), RES[0], RES[1] - BAR)).image().convert("RGB"), np.int16)
    indices = renderer.render(m, 0, roofs=True, view=(T(VIEW), RES[0], RES[1] - BAR)).indices
    static = indices < 229                       # the engine cycles the animated colours: not comparable
    open_a = np.asarray(renderer.render(m, 0, roofs=True, hide_roof_at=T((DOOR_A[0], DOOR_A[1] - 4)),
                                        view=(T(VIEW), RES[0], RES[1] - BAR)).image().convert("RGB"), np.int16)
    shots = {key: load(f"{prefix}-{key}.png") for prefix in ("day", "night")
             for key in ("1-outside", "2-inside-a", "3-outside-again", "4-inside-b", "5-under-hiding-canopy",
                         "6-under-never-hide-canopy", "7-outside-last")}
    day = {key: load(f"day-{key}.png") for key in ("1-outside", "2-inside-a", "3-outside-again", "4-inside-b",
                                                   "5-under-hiding-canopy", "6-under-never-hide-canopy", "7-outside-last")}
    night = {key: load(f"night-{key}.png") for key in day}
    report = {"states": states, "masks_px": {key: int(mask.sum()) for key, mask in masks.items()}}
    results = []

    def add(name, value, ok, note):
        results.append({"check": name, "value": value, "passed": bool(ok), "note": note})
        print(f"[tile stage] {'PASS' if ok else 'FAIL'}  {name}: {value}  ({note})")

    walked = []
    for prefix in ("day", "night"):
        tiles_seen = [int(line.split("dudeTile=")[1].split()[0]) for line in states.get(prefix, [])]
        if len(tiles_seen) >= 5:
            walked.append(tiles_seen[1] == T((DOOR_A[0], DOOR_A[1] - 4)) and tiles_seen[2] == T((DOOR_A[0], DOOR_A[1] + 5))
                          and tiles_seen[3] == T((DOOR_B[0], DOOR_B[1] - 4)))
    if walked:
        add("walk: the player went in through each door on foot and out again (state lines of the engine)", walked, all(walked),
            "inside shots are taken four hexes behind the door, the outside-again shot five hexes in front of it")
    if day["1-outside"] is None:
        add("engine", "no screenshots", False, "the engine run produced no pictures")
        report["checks"] = results
        return report
    out = day["1-outside"]
    v = same(out, offline, masks["roof_a"] & static)
    add("seams: engine picture of roof A == the sheet (offline render of the cut tiles), daylight", v, v >= 0.999,
        f"{int(masks['roof_a'].sum())} roof pixels compared; a seam, a shifted tile or a wrong index would differ")
    v = same(out, offline, masks["roof_b"])
    add("reference: engine picture of stock roof B == offline render", v, v >= 0.999, "the same comparison on the untouched shack")
    whole = same(out, offline, np.ones(masks["roof_a"].shape, bool) & static)
    add("whole view: engine == offline render (floor sheets, decals, canopies, shacks)", whole, whole >= 0.97,
        "differences are the player, the villagers' idle frames and lamp light")
    inside = day["2-inside-a"]
    v_a = same(inside, out, masks["roof_a"])
    v_b = same(inside, out, masks["roof_b"])
    v_open = same(inside, open_a, masks["roof_a"])
    add("hide: player inside A, roof A pixels unchanged", v_a, v_a < 0.25, "the roof must be gone: few pixels may stay the same")
    add("hide: player inside A, roof A region == offline render with that roof hidden", v_open, v_open > 0.9,
        "what shows instead is the room (minus the player and the see-through circle round him)")
    add("hide: player inside A, stock roof B unchanged", v_b, v_b >= 0.999, "only the roof the player is under hides")
    back = day["3-outside-again"]
    v = same(back, out, masks["roof_a"])
    add("show: player outside again, roof A back", v, v >= 0.999, "identical to the first picture")
    v_bb = same(day["4-inside-b"], out, masks["roof_b"])
    v_ab = same(day["4-inside-b"], out, masks["roof_a"])
    add("hide: player inside B hides B (unchanged share) and leaves A alone", [v_bb, v_ab], v_bb < 0.25 and v_ab >= 0.999,
        "[roof B unchanged, roof A unchanged]")
    hole = masks["hole_a"]
    v = same(out, open_a, hole)
    add("hole: pixels of the hole in roof A show the inside of the shack", v, v >= 0.95 and hole.sum() > 150,
        f"{int(hole.sum())} px of the sheet are transparent inside the roof field")
    v_h = same(day["5-under-hiding-canopy"], out, masks["canopy_hide"])
    v_s = same(day["6-under-never-hide-canopy"], out, masks["canopy_stay"])
    add("canopy over open ground: hides when the player stands under it (unchanged share)", v_h, v_h < 0.25, "like any roof")
    add("canopy with the never-hide flag: stays when the player stands under it (unchanged share)", v_s, v_s > 0.6,
        "what differs is the see-through circle the engine cuts round the player")
    if night["1-outside"] is not None:
        nout = night["1-outside"]
        field_a, field_b = masks["roof_a_field"], masks["roof_b"]
        ratio_a = round(luma(nout, field_a) / luma(out, field_a), 4)
        ratio_b = round(luma(nout, field_b) / luma(out, field_b), 4)
        add("night: roof A darkens like stock roof B (night / day luminance)", [ratio_a, ratio_b],
            abs(ratio_a - ratio_b) < 0.04, f"day luminance A {luma(out, field_a)}, B {luma(out, field_b)}; "
            f"night A {luma(nout, field_a)}, B {luma(nout, field_b)}")
        v_a = same(night["2-inside-a"], nout, masks["roof_a"])
        v_back = same(night["3-outside-again"], nout, masks["roof_a"])
        add("night: roof A hides with the player inside and comes back", [v_a, v_back], v_a < 0.3 and v_back >= 0.995,
            "[unchanged share inside, unchanged share outside again]")
    report["checks"] = results
    report["passed"] = all(r["passed"] for r in results)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", action="store_true")
    ap.add_argument("--preview", action="store_true", help="render the sheets at preview quality (fast)")
    ap.add_argument("--check-only", action="store_true", help="re-run the checks on the screenshots already taken")
    args = ap.parse_args()
    manifest, gf, built = build(args.preview)
    if args.engine or args.check_only:
        states = {}
        if args.engine:
            for prefix, name in (("day", DAY), ("night", NIGHT)):
                states[prefix], _ = run_engine(prefix, name)
        report = check(gf, built, states)
        with open(os.path.join(HERE, "report.json"), "w") as f:
            json.dump(report, f, indent=1)
            f.write("\n")
        print(f"[tile stage] {'ALL CHECKS PASS' if report.get('passed') else 'SOME CHECKS FAIL'}: {os.path.relpath(os.path.join(HERE, 'report.json'), ROOT)}")
        return 0 if report.get("passed") else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
