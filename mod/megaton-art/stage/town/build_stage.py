#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The review stage: the town as it stands, with every art piece where placement.json puts it.

    python3 mod/megaton-art/stage/town/build_stage.py                maps, patch, step files, offline pictures
    python3 mod/megaton-art/stage/town/build_stage.py --engine       ... and the real engine: day and night at
                                                                     1280x960 and at phone size (1040x480)
    python3 mod/megaton-art/stage/town/build_stage.py --walk         ... and the draw-order walk (the player
                                                                     walks by mouse round every structure)
    options: --only day|night|phone-day|phone-night   one engine run;  --stock   also build the same views of the
             untouched town (shots/stock-*.png) for before / after pictures

ONE map, three scenes, all at the town's own coordinates: the gate approach (apron, gate set, the
track inside), the street (saloon and plaza, Craterside, Brass Lantern, clinic, sheriff: signs,
string lights, awnings, dressing on the stock shacks) and the crater with the new bomb.

The map is stage/town/snapshot/megaton.map - the town mod's own map with its scripts taken out
(stage/town/snapshot.py) - changed exactly as placement.json says: the listed stock objects
removed, every placement placed the way its "how" says, the gate door given the door FRM, the bomb
created as one scripted object. So the walls, floors, roofs, dressing and NPC sprites around the
new art are the town's, and what is tested here is the hand-over itself.

Writes (all under stage/town/):
    data/                       loose game tree: maps mgtown.map (day) and mgtownn.map (night), maps.txt,
                                scripts.lst, mgnight.int (keeps the map dark), mgbstate.int (bomb states)
    patch-town.dat              the same as an archive. TEST ONLY: it replaces maps.txt and scripts.lst
                                and must never be mounted together with the town mod
    steps-*.txt                 autotest steps of each engine run
    shots/offline-<view>.png    pixel-exact offline renders (daylight, roofs on)
    shots/day-*.png, night-*.png, phone-day-*.png, phone-night-*.png, walk-*.png    engine screenshots
Engine runs: run/art-review-day, art-review-night, art-review-phone-day, art-review-phone-night,
art-review-walk.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)

from f2lib import GameFiles, MapFile, geometry as g, lst, mapstxt, write_dat2      # noqa: E402
from render_map import MapRenderer                                                 # noqa: E402

from pipeline import data                                                          # noqa: E402
from pipeline.place import Placer                                                  # noqa: E402

OVERLAY = os.path.join(HERE, "data")
PATCH = os.path.join(HERE, "patch-town.dat")
SHOTS = os.path.join(HERE, "shots")
SNAPSHOT = os.path.join(HERE, "snapshot", "megaton.map")
PLACEMENT = os.path.join(ART, "placement.json")
DAY, NIGHT, STOCK = "mgtown", "mgtownn", "mgtowns"
NIGHT_SCRIPT, STATE_SCRIPT = "mgnight", "mgbstate"
ORDER = {"shadow": 0, "halo": 1, "main": 2, "glow": 3}
PID_VILLAGER = 0x01000003

# name, centre hex: what the player sees with the view centred there
VIEWS = [
    ("arrival", (101, 136)), ("gate", (100, 126)), ("gate-left", (112, 126)), ("gate-right", (88, 126)),
    ("inside-gate", (100, 116)), ("track", (100, 108)), ("crater", (100, 95)), ("crater-far", (100, 86)),
    ("plaza", (104, 78)), ("saloon", (102, 66)), ("craterside", (76, 74)), ("lantern", (120, 106)),
    ("clinic", (88, 104)), ("sheriff", (86, 116)), ("plant", (66, 96)), ("lucy", (132, 100)), ("billy", (124, 72)),
]
PHONE_VIEWS = ["arrival", "gate", "inside-gate", "crater", "plaza", "saloon", "craterside", "lantern", "clinic"]

# Extra villagers for scale and for sorting, on hexes the town leaves free: (hx, hy, rotation)
EXTRAS = []


def load_placement():
    with open(PLACEMENT) as f:
        return json.load(f)


def apply_placement(m, gf, placer, placement, bomb_script=STATE_SCRIPT):
    """Change a copy of the town the way placement.json says. Returns a summary dict."""
    removed = 0
    for place in placement["placements"]:
        for item in place["remove"]:
            pid = int(item["pid"], 16)
            found = [obj for obj in m.objects_at(item["tile"]) if obj.pid == pid]
            if not found:
                raise SystemExit(f"stage: {item['name']} {item['pid']} is not on {item['hex']} (placement.json is stale: "
                                 f"run placement.py)")
            m.remove_object(found[0])
            removed += 1
    placed = 0
    for place in placement["placements"]:
        name, tile = place["piece"], place["tile"]
        piece = placer.piece(name)
        if place["how"] == "placer":
            placer.place(m, name, tile)
        elif place["how"] == "any":
            for part in sorted(piece["parts"], key=lambda p: ORDER[p["layer"]]):
                m.add_object(int(part["pid"], 16), tile, script=part["script"])
        elif place["how"] == "object":
            main = [part for part in piece["parts"] if part["layer"] == "main"]
            assert len(main) == 1 and main[0]["hex"] == [0, 0], f"{name}: how='object' needs one main part on the origin"
            m.add_object(int(main[0]["pid"], 16), tile, script=bomb_script)
            for hx, hy in place["blockers"]:
                m.add_object(int(piece["blocker_pid"], 16), g.tile_at(hx, hy))
        else:
            raise SystemExit(f"stage: unknown how {place['how']!r}")
        placed += 1
    door = placement["hooks"]["gate_door"]
    gate = [obj for obj in m.objects_at(g.tile_at(*door["object"]["hex"])) if obj.pid == int(door["object"]["proto"], 16)]
    if not gate:
        raise SystemExit("stage: the town's gate door object is not on plan.GATE")
    gate[0].fid = int(door["set"]["fid"], 16)
    for hx, hy, rotation in EXTRAS:
        m.add_object(PID_VILLAGER, g.tile_at(hx, hy), rotation=rotation)
    return {"removed": removed, "placed": placed}


def load_town(gf, name):
    with open(SNAPSHOT, "rb") as f:
        m = MapFile.from_bytes(f.read(), gf)
    m.name = name.upper() + ".MAP"
    m.sort_on_write = True
    return m


def offline_pictures(gf, m, tag, views=None):
    os.makedirs(SHOTS, exist_ok=True)
    renderer = MapRenderer(gf)
    made = []
    for name, (hx, hy) in VIEWS:
        if views and name not in views:
            continue
        cx, cy = g.hex_center(g.tile_at(hx, hy))
        scene = renderer.render(m, 0, roofs=True, world_rect=(cx - 640, cy - 430, cx + 640, cy + 430))
        path = os.path.join(SHOTS, f"{tag}-{name}.png")
        scene.image().save(path)
        made.append(path)
    return made


def view_steps(prefix, views, night, extras=True):
    t = lambda h: g.tile_at(*h)                                    # noqa: E731
    lines = [f"# generated by stage/town/build_stage.py ({prefix})", "wait 1200", "state"]
    for index, (name, centre) in enumerate(views):
        lines += [f"center {t(centre)}", "wait 700", f"shot shots/{prefix}-{index:02d}-{name}.ppm"]
        if night and name in ("gate", "saloon", "crater"):         # a second frame: marquee bulbs, neon, blinking lamps
            lines += ["wait 450", f"shot shots/{prefix}-{index:02d}-{name}-b.ppm"]
    if extras:
        # the gate: open it the way the player does and film the leaves; then the bomb's three quest states
        lines += [f"dude {t((100, 129))}", "wait 300", f"center {t((100, 126))}", "wait 300", f"use {t((100, 127))}", "wait 900"]
        for k in range(8):
            lines += ["wait 110", f"shot shots/{prefix}-door-{k}.ppm"]
        lines += ["wait 1500", f"shot shots/{prefix}-door-open.ppm",
                  f"dude {t((100, 127))}", "wait 400", f"shot shots/{prefix}-door-gateway.ppm",
                  f"dude {t((100, 95))}", "wait 300", f"center {t((100, 94))}", "wait 400"]
        for state in ("rigged", "disarmed", "dormant"):
            lines += [f"use {t((100, 94))}", "wait 3000", f"shot shots/{prefix}-bomb-{state}.ppm"]
    lines += ["quit 0", ""]
    return "\n".join(lines)


def build(stock=False):
    placement = load_placement()
    manifest = data.load_manifest()
    placer = Placer(manifest)
    shutil.rmtree(OVERLAY, ignore_errors=True)
    for sub in ("maps", "data", "scripts"):
        os.makedirs(os.path.join(OVERLAY, sub))
    base = GameFiles()
    maps_txt = base.read("data/maps.txt")
    indices = {}
    for lookup, name in (("MG Art Review", DAY), ("MG Art Review Night", NIGHT), ("MG Art Review Stock", STOCK)):
        maps_txt, indices[name] = mapstxt.append_map(maps_txt, lookup, name, saved=False, automap=False)
    with open(os.path.join(OVERLAY, "data", "maps.txt"), "wb") as f:
        f.write(maps_txt)
    files = {"data\\maps.txt": maps_txt}
    lines = []
    for script, comment in ((NIGHT_SCRIPT, "art review: night"), (STATE_SCRIPT, "art review: bomb states")):
        out = os.path.join(OVERLAY, "scripts", script + ".int")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ssl.py"), "compile", os.path.join(HERE, script + ".ssl"),
                        "-o", out], check=True, stdout=subprocess.DEVNULL)
        with open(out, "rb") as f:
            files[f"scripts\\{script}.int"] = f.read()
        lines.append(lst.ScriptList.format_line(script, comment, 1 if script == STATE_SCRIPT else 0))
    scripts_lst = lst.append_lines(base.read("scripts/scripts.lst"), lines)
    with open(os.path.join(OVERLAY, "scripts", "scripts.lst"), "wb") as f:
        f.write(scripts_lst)
    files["scripts\\scripts.lst"] = scripts_lst

    gf = GameFiles(overlay=[OVERLAY, data.OUT])
    summary = None
    day_map = None
    for name, night in ((DAY, False), (NIGHT, True)):
        m = load_town(gf, name)
        m.index = indices[name]
        summary = apply_placement(m, gf, placer, placement)
        if night:
            m.set_map_script(NIGHT_SCRIPT)
        problems = [p for p in m.validate() if p.startswith("error")]
        if problems:
            raise SystemExit("stage map: " + "; ".join(problems[:8]))
        m.save(os.path.join(OVERLAY, "maps", m.file_name))
        files[f"maps\\{m.file_name}"] = m.to_bytes()
        if not night:
            day_map = m
    pictures = offline_pictures(gf, day_map, "offline")
    if stock:
        m = load_town(gf, STOCK)
        m.index = indices[STOCK]
        m.save(os.path.join(OVERLAY, "maps", m.file_name))
        files[f"maps\\{m.file_name}"] = m.to_bytes()
        pictures += offline_pictures(gf, m, "stock")
    write_dat2(files, PATCH)
    views = dict(VIEWS)
    for prefix, night, names, extras in (("day", False, [v[0] for v in VIEWS], True), ("night", True, [v[0] for v in VIEWS], True),
                                         ("phone-day", False, PHONE_VIEWS, False), ("phone-night", True, PHONE_VIEWS, False)):
        with open(os.path.join(HERE, f"steps-{prefix}.txt"), "w") as f:
            f.write(view_steps(prefix, [(n, views[n]) for n in names], night, extras))
    print(f"[town stage] {summary['placed']} placements, {summary['removed']} stock objects removed; "
          f"{len(pictures)} offline pictures in {os.path.relpath(SHOTS, ROOT)}")


RUNS = {
    "day": (DAY, "1280x960"), "night": (NIGHT, "1280x960"),
    "phone-day": (DAY, "1040x480"), "phone-night": (NIGHT, "1040x480"),
}


def run_engine(prefix, map_name, res, steps_path=None, timeout=420):
    run = f"art-review-{prefix}"
    command = [sys.executable, os.path.join(ROOT, "tools", "f2test.py"), "--name", run, "--fresh",
               "--map", map_name + ".map", "--res", res, "--timeout", str(timeout), "--debug-log",
               "--patch", data.PATCH, "--patch", PATCH, "--steps", steps_path or os.path.join(HERE, f"steps-{prefix}.txt")]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = [line for line in result.stdout.splitlines() if "exit code" in line or "TIMEOUT" in line]
    states = [line for line in result.stdout.splitlines() if "state map" in line]
    print(f"[town stage] {run}: {len(states)} state line(s)" + (", first: " + states[0][:110] if states else "") + " | " + " | ".join(tail))
    shots = os.path.join(ROOT, "run", run, "shots")
    os.makedirs(SHOTS, exist_ok=True)
    count = 0
    for name in sorted(os.listdir(shots)) if os.path.isdir(shots) else []:
        if name.endswith(".png"):
            shutil.copy2(os.path.join(shots, name), os.path.join(SHOTS, name))
            count += 1
    log = os.path.join(ROOT, "run", run, "debug.log")
    if os.path.exists(log):
        with open(log, errors="replace") as f:
            bad = [line.strip() for line in f if "rror" in line or "ould not" in line or "nable" in line]
        for line in bad[:12]:
            print(f"[town stage]   debug.log: {line}")
    print(f"[town stage] {run}: {count} screenshots")
    return result.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", action="store_true")
    ap.add_argument("--walk", action="store_true")
    ap.add_argument("--only", choices=sorted(RUNS))
    ap.add_argument("--stock", action="store_true")
    args = ap.parse_args()
    build(args.stock)
    if args.engine or args.only:
        for prefix, (map_name, res) in RUNS.items():
            if args.only and prefix != args.only:
                continue
            run_engine(prefix, map_name, res)
    if args.walk:
        import walk
        walk.run()


if __name__ == "__main__":
    main()
