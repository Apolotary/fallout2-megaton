# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Find the hexes a piece must ALSO block to pass the draw-order test, without rendering anything.

    python3 mod/megaton-art/pipeline/sortfix.py [NAME ...]        default: every piece of the v2 set that fails

For every failing piece the test's failing hexes (a critter standing there is painted over something in front of him,
or the piece over him) are added to the footprint in build/render/<piece>/meta.json and the test is run again, until
the piece passes or six rounds are over. The result is merged into kit/also_block.json, which the kit reads as the
default of the piece option `also_block`: rebuild the named pieces afterwards (`build.py piece NAME ...`), so that
manifest.json, the cut and the blockers follow. Nothing here touches manifest.json or out/.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)
sys.dont_write_bytecode = True

from f2lib import GameFiles                    # noqa: E402
from pipeline import data, sorttest            # noqa: E402

RENDER = os.path.join(ART, "build", "render")
TABLE = os.path.join(ART, "kit", "also_block.json")
ROUNDS = 6


def main(argv):
    palette = GameFiles().palette
    manifest = data.load_manifest()
    first = manifest["v2"]["first_slot"]
    names = argv[1:] or [name for name, entry in manifest["pieces"].items()
                         if all(part["slot"] >= first[part["type"]] for part in entry["parts"])]
    table = {}
    if os.path.exists(TABLE):
        with open(TABLE) as f:
            table = json.load(f)
    scratch = os.path.join(ART, "build", "preview")
    still = []
    for name in names:
        meta_path = os.path.join(RENDER, name, "meta.json")
        if not os.path.exists(meta_path):
            continue
        added = []
        for attempt in range(ROUNDS + 1):
            row = sorttest.run([name], RENDER, palette, scratch)[0]
            bad = [tuple(h) for key in ("over", "under") for h, _ in row["failing"][key]]
            if not row["fails"] or not bad:
                break
            if attempt == ROUNDS:
                still.append(name)
                break
            with open(meta_path) as f:
                meta = json.load(f)
            for h in bad:
                if list(h) not in meta["footprint"]:
                    meta["footprint"].append(list(h))
                    added.append(list(h))
            with open(meta_path, "w") as f:
                json.dump(meta, f)
        if added:
            merged = [list(h) for h in table.get(name, [])]
            merged += [h for h in added if h not in merged]
            table[name] = merged
            print(f"{name:<20} +{len(added)} hex(es): {added}  -> {'passes' if name not in still else 'STILL FAILS'}")
    table["_about"] = ("hexes blocked in addition to a piece's automatic footprint (kit option also_block), found by "
                       "pipeline/sortfix.py from the draw-order test")
    with open(TABLE, "w") as f:
        json.dump(table, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"{len([n for n in table if not n.startswith('_')])} piece(s) in kit/also_block.json; {len(still)} still fail: {still}")
    return 1 if still else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
