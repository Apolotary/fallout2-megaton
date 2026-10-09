#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Every check of the town layout: the offline tests, then the engine scenarios.

    python3 mod/megaton/tests/layout/run_all.py            # about 6 minutes
    python3 mod/megaton/tests/layout/run_all.py --offline  # about 5 seconds

Offline: test_layout.py (validate, spots, roofs, doors, reachability, containment,
keep_free, dressing, camera, cast). Engine (run/mg-layout-<scenario>/, screenshots in shots/):
    gate   the gate shut and open, the three-hex passage, exit grid, world map and back
    walk   through the gate into seven buildings: roofs vanish and return, doors open and close
    tour   one 1280x960 screenshot per district, with every script that is written
    night  the same tour at 22:24 (stage_night.py swaps the map script for a rig that sets the
           clock): lamp posts, fire barrels and the pool must light the town
    stash  a locked container of the set dressing: locked, picked with Lockpick, looted
gate, walk, night and stash run with --only (no NPC or door scripts) so that other groups'
locks and scenes cannot change what a layout test sees. Do not run two engine tests of
one group at a time: test.py rebuilds mod/megaton/out-layout first.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
SCENARIOS = [("gate", ["--only", "megaton", "--timeout", "240"]),
             ("walk", ["--only", "megaton", "--timeout", "500"]),
             ("tour", ["--timeout", "240"]),
             ("night", ["--only", "megaton", "--timeout", "240", "--stage", os.path.join("tests", "layout", "stage_night.py")]),
             ("stash", ["--only", "megaton,mgdecor", "--timeout", "300", "--res", "640x480"])]


def main(argv):
    failed = []
    if subprocess.run([sys.executable, os.path.join(HERE, "test_layout.py")]).returncode:
        failed.append("offline")
    if "--offline" not in argv:
        for name, options in SCENARIOS:
            command = [sys.executable, os.path.join(MOD, "test.py"), "--group", "layout", "--res", "1280x960",
                       "--steps", os.path.join("tests", "layout", name + ".txt")] + options   # a later --res wins
            result = subprocess.run(command, capture_output=True, text=True)
            tail = result.stdout[result.stdout.find("== debug.log"):]
            print(f"--- {name}\n{tail}")
            if result.returncode:
                failed.append(name)
    print("layout tests: " + ("FAILED: " + ", ".join(failed) if failed else "all passed"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
