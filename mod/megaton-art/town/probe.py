#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""What the town knows about itself, written down for the mock-up tools. Runs in a process of its own.

    python3 mod/megaton-art/town/probe.py <staging dir> <out.json>

<staging dir> is a tree `python3 mod/megaton/build.py --out <dir> ...` has built. This script
imports the town's own modules (mod/megaton/layout, cast, tests/layout/test_layout.py) READ-ONLY,
builds the town in memory the way the build's `maps` step does, and writes:

    plan        gate, bomb, buildings (box, doors, rooms, roof squares), paths, the wall's outline
    spots       every named spot
    keep_free   the hexes the town reserves, with the reason (layout.keep_free())
    targets     everything the player clicks: doors, cast, containers, and a stand-in villager for
                every post somebody walks to (layout/sight.py targets()), each with the pixels a
                click can reach in the STOCK town (no custom art) and in the town as it is now
    click       the thresholds of the town's `clickable` test (tests/layout/test_layout.py)
    counters    who is talked to across a counter, and from how far
    cast        who stands on which spot
It runs in a separate process to isolate the town builder's bare `placement` and
`pipeline` imports from modules already loaded by an art-author tool.
"""
import hashlib
import json
import os
import sys
import time

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TOWN = os.path.join(ROOT, "mod", "megaton")
for path in (os.path.join(TOWN, "tests", "layout"), TOWN, os.path.join(ROOT, "tools")):
    sys.path.insert(0, path)


def main(staging, out_path):
    from f2lib import GameFiles, geometry as g, ids

    import cast
    import layout
    from layout import plan, sight, spots, walk
    import test_layout

    quiet = lambda *a: None                                 # noqa: E731
    gf = GameFiles(overlay=staging)
    built_path = os.path.join(staging, "maps", "megaton.map")
    with open(built_path, "rb") as f:
        built_bytes = f.read()

    measured = {}
    for art in (False, True):
        m, info = layout.build(gf, strict=False, art=art, log=quiet)
        if art:
            same = m.to_bytes() == built_bytes
        found = sight.targets(m, gf, info)                  # adds the stand-in villagers to m
        measured[art] = (m, info, found, sight.clickable(m, gf, found))
    m, info, found, now = measured[True]
    _, _, _, stock = measured[False]

    targets = []
    for name, obj in found.items():
        hx, hy = g.tile_xy(obj.tile)
        peers = [o for o in m.objects_at(obj.tile) if o.pid == obj.pid]
        total, free, _ = now[name]
        targets.append({
            "name": name, "kind": name.split(" ")[0], "tile": obj.tile, "hex": [hx, hy], "pid": f"0x{obj.pid:08X}",
            "ordinal": peers.index(obj), "rotation": obj.rotation,
            "stand_in": bool(name.startswith("post ") and obj.pid == sight.PID_STAND_IN),
            "total": total, "now_free": free, "stock_free": stock.get(name, (0, 0, {}))[1],
        })

    buildings = {}
    for key, spec in plan.BUILDINGS.items():
        shack = info["shacks"][key]
        buildings[key] = {
            "title": spec["title"], "box": list(spec["box"]), "roof": spec["roof"],
            "doors": [list(d) for d in spec.get("doors", ())],
            "rooms": {room: list(rect) for room, rect in spec["rooms"].items()},
            "roof_squares": sorted([list(s) for s in shack.roof_squares]),
            "interior": sorted([list(h) for h in shack.interior()]),
        }
    held = {}
    for entry in cast.load():
        if isinstance(entry["spot"], str):
            held.setdefault(entry["spot"], []).append(entry["type"])
    record = info.get("dressing", {})
    document = {
        "about": "Facts about the town as built (mod/megaton-art/town/probe.py). The mock-up checker reads this "
                 "instead of importing the plan, so it always matches the snapshot map beside it.",
        "built": {"when": time.strftime("%Y-%m-%d %H:%M:%S"), "staging": os.path.relpath(staging, ROOT),
                  "map_sha1": hashlib.sha1(built_bytes).hexdigest(), "memory_build_identical": bool(same),
                  "objects": len(m.objects[0])},
        "plan": {
            "gate": list(plan.GATE), "bomb": list(plan.BOMB), "right": plan.RIGHT, "left": plan.LEFT,
            "back": plan.BACK, "front": plan.FRONT, "apron_hx": list(plan.APRON_HX), "apron_hy": list(plan.APRON_HY),
            "exit_rows": list(plan.EXIT_ROWS), "exit_columns": plan.EXIT_COLUMNS,
            "paths": [[list(a), list(b), width] for a, b, width in plan.PATHS], "pool_ring": plan.POOL_RING,
            "outline": [list(p) for p in plan.outline()], "lantern_stall": list(plan.LANTERN_STALL),
            "lantern_bar": list(plan.LANTERN_BAR), "buildings": buildings,
            "doors": [{"building": key, "name": name, "hex": list(pos), "leaf": bool(leaf)}
                      for key, name, pos, leaf in plan.all_doors()],
        },
        "spots": {name: list(value) for name, value in spots.SPOTS.items()},
        "spot_kinds": held,
        "door_spots": {name: list(pos) for name, pos in test_layout.DOOR_SPOTS.items()},
        "keep_free": [[hx, hy, why] for (hx, hy), why in sorted(layout.keep_free().items())],
        "bomb_access": [[plan.BOMB[0] + dx, plan.BOMB[1] + dy] for dx, dy in layout.buildings.BOMB_ACCESS],
        "pool": sorted([list(h) for h in info["pool"]]),
        "targets": targets,
        "click": {"share": test_layout.CLICK_SHARE, "floor": test_layout.CLICK_FLOOR,
                  "behind_furniture": dict(test_layout.BEHIND_FURNITURE), "bomb_gate_min_px": 3000},
        # the town's two later tests (seen, trim): thresholds as the tests state them today
        "seen": {"door": getattr(test_layout, "SEEN_DOOR", 0.5), "person": getattr(test_layout, "SEEN_PERSON", 0.4),
                 "not_stood_on": list(getattr(test_layout, "NOT_STOOD_ON", ()))},
        "tests": [t.__name__[5:] for t in getattr(test_layout, "TESTS", ())],
        "counters": dict(test_layout.COUNTERS),
        "cast": [{"spot": entry["spot"], "type": entry["type"]} for entry in cast.load() if isinstance(entry["spot"], str)],
        "containers": [{"place": box["place"], "name": box["name"], "hex": list(box["hex"]), "locked": bool(box["locked"])}
                       for box in record.get("containers", ())],
        "art": [{"piece": name, "origin": list(origin), "how": how} for name, origin, how, _ in info.get("art", {}).get("placed", ())],
        "outhouse_pid": f"0x{layout.outdoors.OUTHOUSE:08X}",
        "entry": spots.tile("ENTRY"),
    }
    with open(out_path, "w") as f:
        json.dump(document, f, indent=1)
        f.write("\n")
    print(f"[probe] {len(targets)} click targets, {len(document['keep_free'])} reserved hexes, {len(buildings)} buildings; "
          f"in-memory build {'equals' if same else 'DIFFERS FROM'} {os.path.relpath(built_path, ROOT)}")


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]))
