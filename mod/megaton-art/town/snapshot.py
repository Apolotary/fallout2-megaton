#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Take a snapshot of the CURRENT playable town for mock-ups.

    python3 mod/megaton-art/town/snapshot.py              build the town, probe it, write town/snapshot/
    python3 mod/megaton-art/town/snapshot.py --no-build   reuse the staged tree of the last run
    options: --staging DIR (default run/clutter-setup/town)   --keep N (default 3 tries for a consistent pair)

What it does (mod/megaton and mod/megaton-art are only READ):
  1. python3 mod/megaton/build.py --out <staging> data protos art scripts maps lint pack
     - the town's own build, into a tree of ours. Neither its default out/ nor its `web` step is
     touched, and its `ids` step is left out because that one rewrites two generated headers
     inside mod/megaton/scripts (they are current whenever the town builds at all).
  2. town/probe.py (a process of its own) builds the same town in memory with the town's own
     modules and writes snapshot/town.json: plan, spots, reserved hexes, click targets with their
     reachable pixels. If its map is not byte-identical to the one step 1 wrote, somebody changed
     the town in between: both steps run again.
  3. Writes, next to this file:
        snapshot/megaton.map    the built map with everything taken out that needs the town's scripts
                                and tables: all scripts (map, spatial, object, critter) and the six
                                custom items in inventories. Walls, floors, roofs, the custom art as
                                placed today, furniture and every NPC sprite stay where they are.
        snapshot/base/          the part of the town's tree that map needs in the game: art/scenery,
                                art/walls, proto/scenery, proto/walls and the two proto message files
                                (the stock lists with the town's and mod/megaton-art's lines). No
                                scripts, no maps.txt: town/mock.py adds its own.
        snapshot/town.json      (step 2) plus "scripted": {tile: [pid, ...]} of what carried a script
        snapshot/overview.png   the whole town, roofs on (offline render)
Run it again whenever the town has moved on; mock-ups are always built from the last snapshot.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from f2lib import GameFiles, MapFile, ids      # noqa: E402

SNAP = os.path.join(HERE, "snapshot")
BASE = os.path.join(SNAP, "base")
STAGING = os.path.join(ROOT, "run", "clutter-setup", "town")
TOWN_BUILD = os.path.join(ROOT, "mod", "megaton", "build.py")
TOWN_STEPS = ["data", "protos", "art", "scripts", "maps", "lint", "pack"]      # every default step but `ids`
BASE_FILES = ["art/scenery", "art/walls", "proto/scenery", "proto/walls",
              "text/english/game/pro_scen.msg", "text/english/game/pro_wall.msg"]


def log(text):
    print(f"[snapshot] {text}", flush=True)


def build_town(staging):
    if not os.path.abspath(staging).startswith(os.path.join(ROOT, "run", "clutter-") ):
        raise SystemExit("the staging tree must be a directory under run/clutter-*")
    shutil.rmtree(staging, ignore_errors=True)
    result = subprocess.run([sys.executable, TOWN_BUILD, "--out", staging] + TOWN_STEPS,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = result.stdout.strip().splitlines()
    for line in lines[-4:]:
        log("   town build: " + line)
    if result.returncode != 0:
        print(result.stdout[-3000:])
        raise SystemExit("the town does not build right now (somebody may be half-way through a change): try again")


def probe(staging, out_path):
    result = subprocess.run([sys.executable, os.path.join(HERE, "probe.py"), staging, out_path],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in result.stdout.strip().splitlines()[-3:]:
        log("   " + line)
    if result.returncode != 0:
        print(result.stdout[-3000:])
        raise SystemExit("town/probe.py failed")
    with open(out_path) as f:
        return json.load(f)


def strip(staging):
    """The built map without scripts and custom items -> (bytes, scripted {tile: [pid]}, dropped items)."""
    gf = GameFiles(overlay=staging)
    stock = GameFiles()
    with open(os.path.join(staging, "maps", "megaton.map"), "rb") as f:
        m = MapFile.from_bytes(f.read(), gf)
    stock_items = stock.protos.count(ids.OBJ_TYPE_ITEM)
    scripted, dropped = {}, 0
    for obj in m.all_objects():
        if obj.sid != -1:
            scripted.setdefault(str(obj.tile), []).append(f"0x{obj.pid:08X}")
        for owner in obj.walk():
            keep = [pair for pair in owner.inventory
                    if not (pair[1].obj_type == ids.OBJ_TYPE_ITEM and (pair[1].pid & 0xFFFFFF) > stock_items)]
            dropped += len(owner.inventory) - len(keep)
            owner.inventory[:] = keep
            owner.sid = -1
            owner.script_index = -1
    for script_list in m.script_lists:
        script_list._set_live([])
    m.script_index = 0
    return m.to_bytes(), scripted, dropped


def copy_base(staging):
    shutil.rmtree(BASE, ignore_errors=True)
    count = 0
    for rel in BASE_FILES:
        source = os.path.join(staging, rel)
        target = os.path.join(BASE, rel)
        if os.path.isdir(source):
            shutil.copytree(source, target)
            count += sum(len(names) for _, _, names in os.walk(target))
        else:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(source, target)
            count += 1
    return count


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--staging", default=STAGING)
    ap.add_argument("--keep", type=int, default=3)
    args = ap.parse_args()
    staging = os.path.abspath(args.staging)
    os.makedirs(SNAP, exist_ok=True)
    scratch = os.path.join(SNAP, "town.json.tmp")
    facts = None
    for attempt in range(max(1, args.keep)):
        if not args.no_build:
            build_town(staging)
        facts = probe(staging, scratch)
        if facts["built"]["memory_build_identical"] or args.no_build:
            break
        log(f"the town changed while it was being built (try {attempt + 1}): building again")
    if not facts["built"]["memory_build_identical"]:
        log("WARNING: the facts in town.json come from sources newer than the built map; run the snapshot again")
    data, scripted, dropped = strip(staging)
    files = copy_base(staging)
    with open(os.path.join(SNAP, "megaton.map"), "wb") as f:
        f.write(data)
    facts["scripted"] = scripted
    facts["snapshot"] = {"map_sha1": hashlib.sha1(data).hexdigest(), "base_files": files, "custom_items_dropped": dropped}
    with open(os.path.join(SNAP, "town.json"), "w") as f:
        json.dump(facts, f, indent=1)
        f.write("\n")
    os.remove(scratch)
    gf = GameFiles(overlay=BASE)
    check = MapFile.from_bytes(data, gf)
    problems = [p for p in check.validate() if p.startswith("error") and "not registered in data/maps.txt" not in p]
    if problems:                                # (maps.txt is the mock-up's business: town/mock.py registers its maps)
        raise SystemExit("the stripped map does not validate on stock + snapshot/base: " + "; ".join(problems[:6]))
    from render_map import MapRenderer
    scene = MapRenderer(gf).render(check, 0, roofs=True)
    image = scene.image()
    image.resize((image.width // 2, image.height // 2)).save(os.path.join(SNAP, "overview.png"))
    log(f"{len(check.objects[0])} objects ({sum(len(v) for v in scripted.values())} had scripts, {dropped} custom item(s) dropped), "
        f"{files} base files, {len(facts['targets'])} click targets; loads on stock + snapshot/base")
    log(f"town of {facts['built']['when']}, map sha1 {facts['built']['map_sha1'][:12]}: {os.path.relpath(SNAP, ROOT)}")


if __name__ == "__main__":
    main()
