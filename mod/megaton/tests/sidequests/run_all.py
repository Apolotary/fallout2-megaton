#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Run the side-quest scenarios in the real engine and say which passed.

    python3 mod/megaton/tests/sidequests/run_all.py                 (all of them, about 30 minutes)
    python3 mod/megaton/tests/sidequests/run_all.py walter office   (only these)

Each scenario (every *.txt of this directory) is one test.py run on the flat
side-quest stage (stage.py): staging dir mod/megaton/out-sidequests, run
directory run/mg-sidequests-<scenario>/. The first lines of every step file say
what it proves and which values it expects; the screenshots in the run directory
are the proof-reading copy of every dialogue node. Two scenarios have no `expect`
lines and always "pass": probe (prints the test character's stats) and steal-key
(a dice roll; read its last lines).

The stage is built once for the first scenario and reused for the others
(--no-build), so a script edit needs a fresh start of this runner.

Not run from here: town.steps, the same cast in the REAL town (stage_town.py
gives the command). It is the only test that walks to things and clicks them
with the mouse where the architect put them.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))

# The side-quest scripts, the map script and the rig (which takes the settler's slot).
ONLY = "megaton,mgsettlr,mgmoriar,mgsilvr,mgterm,mgoffice,mgcabin,mgstrong,mgwalter,mgleak,mglucy,mgjeri"


def scenarios():
    return sorted(name[:-4] for name in os.listdir(HERE) if name.endswith(".txt"))


def main():
    names = sys.argv[1:] or scenarios()
    unknown = [name for name in names if name not in scenarios()]
    if unknown:
        print(__doc__)
        print("unknown scenario(s):", " ".join(unknown), "- known:", " ".join(scenarios()))
        return 2
    results = {}
    built = False
    for name in names:
        command = [sys.executable, os.path.join(MOD, "test.py"), "--group", "sidequests",
                   "--stage", os.path.join(HERE, "stage.py"), "--only", ONLY,
                   "--steps", os.path.join(HERE, name + ".txt")]
        if built:
            command.append("--no-build")
        output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
        built = built or "pack:" in output
        verdict = [line for line in output.splitlines() if line.startswith("== RESULT")]
        results[name] = verdict[-1][3:] if verdict else "RESULT: FAIL (no verdict)"
        print(f"{name:<18} {results[name]}", flush=True)
        if "PASS" not in results[name]:
            print(output)
    failed = [name for name, verdict in results.items() if "PASS" not in verdict]
    print(f"{len(results) - len(failed)} of {len(results)} scenarios passed" + (f"; failed: {' '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
