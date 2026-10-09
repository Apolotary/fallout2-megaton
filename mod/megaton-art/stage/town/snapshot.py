#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Take a private, self-contained snapshot of the town for the art review stage.

    python3 mod/megaton-art/stage/town/snapshot.py

Builds the town in memory from mod/megaton/layout WITHOUT the custom art (layout.build(art=False):
the stock dressing that placement.py replaces is all there; mod/megaton/out is only read, for the
compiled scripts and protos) and writes, next to this file:
    snapshot/megaton.map     the town map with everything that needs the town's own patch taken out:
                             all scripts (map, spatial, object, critter) and the six custom items the
                             town adds to inventories. Walls, floors, roofs, stock scenery and the NPC
                             sprites stay where the town put them. It loads on the stock game plus
                             out/patch-art.dat.
    snapshot/scripted.json   {tile: [pid, ...]} of the objects that carried a script in the town:
                             placement.py uses it to warn when a piece replaces a scripted object
    snapshot/spots.json      the town's named places (tile numbers), copied from mod/megaton/out
Run it again whenever the town layout has moved, then `python3 mod/megaton-art/placement.py`.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from f2lib import GameFiles, MapFile, ids      # noqa: E402

TOWN = os.path.join(ROOT, "mod", "megaton", "out")
SNAP = os.path.join(HERE, "snapshot")


def main():
    if not os.path.exists(os.path.join(TOWN, "scripts", "scripts.lst")):
        raise SystemExit("mod/megaton/out has no staged tables: build the town first (python3 mod/megaton/build.py)")
    sys.path.insert(0, os.path.join(ROOT, "mod", "megaton"))
    import layout                                   # mod/megaton/layout
    gf = GameFiles(overlay=[TOWN, os.path.join(ART, "out")])
    stock = GameFiles()
    built, _ = layout.build(gf, art=False, log=lambda *a: None)
    m = MapFile.from_bytes(built.to_bytes(), gf)
    art_bomb = [obj for obj in m.all_objects() if (obj.pid >> 24) == 2 and (obj.pid & 0xFFFFFF) >= 1900]
    for obj in art_bomb:                            # the cast's bomb is the art's own sprite: the stage places it itself
        m.remove_object(obj)
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
    os.makedirs(SNAP, exist_ok=True)
    with open(os.path.join(SNAP, "megaton.map"), "wb") as f:
        f.write(m.to_bytes())
    with open(os.path.join(SNAP, "scripted.json"), "w") as f:
        json.dump(scripted, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(SNAP, "spots.json"), "w") as f:
        json.dump(layout.test_names(built), f, indent=1, sort_keys=True)
        f.write("\n")
    check = MapFile.from_bytes(open(os.path.join(SNAP, "megaton.map"), "rb").read(), stock)
    print(f"[snapshot] {len(list(check.all_objects()))} objects, {sum(len(v) for v in scripted.values())} had scripts, "
          f"{dropped} custom item(s) dropped; loads on the stock game")


if __name__ == "__main__":
    main()
