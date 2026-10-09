#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Run the merchants group's scenarios in the real engine and say which passed.

    python3 mod/megaton/tests/merchants/run_all.py                 (all stage scenarios, about 45 minutes)
    python3 mod/megaton/tests/merchants/run_all.py doc nova        (some)
    python3 mod/megaton/tests/merchants/run_all.py town            (the one scenario on the real town map)

Each scenario is one step file of this directory, run through test.py on the
stage tests/merchants/stage.py (staging dir mod/megaton/out-merchants, run
directories run/mg-merchants-<scenario>/). The staging dir is built once, by
the first scenario; the others reuse it. The first lines of every step file
say what it proves. Scenarios that roll dice (theft, kill) say so: a failure
there is worth one more run before it is worth a bug hunt.

`town` is different: town.txt runs on the town built by layout/ (staging dir
mod/megaton/out-merchants-town, run run/mg-merchants-town-town/). It is only
run when named, because it depends on where the architect put the walls. `expect` lines
check GVARs (through the rig's probes: tests/merchants/scripts/mgsettlr.ssl);
what was SAID is only in the screenshots, run/mg-merchants-<scenario>/shots/.
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))

OWN = "megaton,mgmoira,mgmerc,mggob,mgdoc,mgjenny,mgtrade,mgnova,mgbed"
ONLY = OWN + ",mgsettlr"              # plus the rig (tests/merchants/scripts/mgsettlr.ssl)
REAL_TOWN = ("town",)                 # scenarios that run on the real map, not on the stage


def main():
    known = sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(HERE, "*.txt")))
    names = sys.argv[1:] or [name for name in known if name not in REAL_TOWN]
    unknown = [name for name in names if name not in known]
    if unknown:
        print(__doc__)
        print("unknown scenario(s):", " ".join(unknown), "- known:", " ".join(known))
        return 2
    results = {}
    built = False
    for name in names:
        if name in REAL_TOWN:
            command = [sys.executable, os.path.join(MOD, "test.py"), "--group", "merchants-town",
                       "--only", OWN, "--steps", os.path.join(HERE, name + ".txt")]
        else:
            command = [sys.executable, os.path.join(MOD, "test.py"), "--group", "merchants",
                       "--stage", os.path.join(HERE, "stage.py"), "--only", ONLY, "--timeout", "420",
                       "--steps", os.path.join(HERE, name + ".txt")]
            if built:
                command.append("--no-build")
            built = True
        output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
        verdict = [line for line in output.splitlines() if line.startswith("== RESULT")]
        results[name] = verdict[-1] if verdict else "== RESULT: FAIL (no verdict)"
        print(f"{name:<16} {results[name][3:]}", flush=True)
        if "PASS" not in results[name]:
            print(output)
    failed = [name for name, verdict in results.items() if "PASS" not in verdict]
    print(f"{len(results) - len(failed)} of {len(results)} scenarios passed" + (": FAILED " + " ".join(failed) if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
