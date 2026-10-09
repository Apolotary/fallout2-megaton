#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Run the main-quest ("core") scenarios in the real engine and say which passed.

    python3 mod/megaton/tests/core/run_all.py                 (everything, about 15 minutes)
    python3 mod/megaton/tests/core/run_all.py bomb-menu scene-watch
    python3 mod/megaton/tests/core/run_all.py --jobs 1        (one engine at a time)

Each scenario is one step file of this directory, run by mod/megaton/test.py.
The first lines of a step file say what it proves and which values it expects.
Three stages are used, each built once into its own staging dir:

    stage.py             group "core"        mod/megaton/out-core         run/mg-core-<scenario>/
    stage_weak.py        group "core-weak"   mod/megaton/out-core-weak    run/mg-core-weak-<scenario>/
                         (Simms and Harden at three hit points, for the killing tests)
    stage_weak_burke.py  group "core-weakb"  mod/megaton/out-core-weakb   run/mg-core-weakb-<scenario>/
                         (Burke at three hit points)

The town-*.txt step files are not in the list: they run on the architect's real
map (their first lines give the command) and belong to the integration stage.

Two checks in this directory need no engine: check_text.py (does every reply fit
the conversation window, does every line number a script uses exist) and
check_route.py (can Simms and Burke walk across the built town, leg by leg,
within the engine pathfinder's limits).

Scenarios run several at a time (--jobs, default 3), started two seconds apart
because test.py hands the engine its steps through one file per staging dir.
A scenario that fails prints its whole log. Fights are dice: scene-shove, scene-tackle
and the kill-* scenarios may fail on an unlucky roll and are worth a second run.
"""
import argparse
import concurrent.futures
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(MOD))

ONLY = "megaton,mgweld,mgsimms,mgburke,mgbomb,mgharden,mghitman,mgspgate,mgspsims,mgsprad,mggate,mghouse,mgcabin"
BUILD_STEPS = ["ids", "data", "protos", "art", "scripts", "maps", "lint", "pack"]
STAGES = {"core": "stage.py", "core-weak": "stage_weak.py", "core-weakb": "stage_weak_burke.py"}
PIPBOY = ["--ddraw", "PipBoyAvailableAtGameStart=1"]

# scenario: (group, extra test.py arguments)
SCENARIOS = {
    "smoke": ("core", []),
    "arrival": ("core", []),
    "weld": ("core", []),
    "simms-quest": ("core", PIPBOY),
    "simms-haggle": ("core", []),
    "simms-probono": ("core", []),
    "simms-threat": ("core", []),
    "simms-twice": ("core", []),
    "simms-dumb": ("core", []),
    "simms-misc": ("core", []),
    "simms-bounty": ("core", []),
    "bomb-menu": ("core", []),
    "bomb-skills": ("core", []),
    "bomb-rig-pull": ("core", []),
    "burke-deal": ("core", PIPBOY),
    "burke-haggle": ("core", []),
    "burke-lost": ("core", []),
    "burke-leave": ("core", ["--timeout", "300"]),
    "burke-dumb": ("core", []),
    "burke-b7": ("core", []),
    "burke-doublecross": ("core", []),
    "detonate": ("core", ["--timeout", "300"]),
    "blast-reentry": ("core", ["--timeout", "300"]),
    "standdown": ("core", []),
    "scene-watch": ("core", []),
    "scene-shove": ("core", ["--timeout", "300"]),           # DICE
    "scene-tackle": ("core", ["--timeout", "300"]),          # DICE
    "scene-warned": ("core", []),
    "scene-save": ("core", ["--timeout", "300"]),
    "away-scene": ("core", ["--timeout", "300"]),
    "away-warned": ("core", ["--timeout", "300"]),
    "away-burke": ("core", ["--timeout", "300"]),
    "grudge-lapse": ("core", []),
    "amnesty": ("core", ["--timeout", "300"]),
    "grudge": ("core", ["--timeout", "300"]),
    "harden": ("core", []),
    "house": ("core", []),
    "evening": ("core", []),
    "kill-burke": ("core-weakb", []),
    "kill-burke-allowed": ("core-weakb", []),
    "kill-burke-scene": ("core-weakb", []),
    "kill-simms": ("core-weak", []),
    "kill-simms-scene": ("core-weak", []),
    "kill-harden": ("core-weak", []),
}


def build(group):
    out_dir = os.path.join(MOD, "out-" + group)
    shutil.rmtree(out_dir, ignore_errors=True)
    command = [sys.executable, os.path.join(MOD, "build.py"), "--out", out_dir,
               "--stage", os.path.join(HERE, STAGES[group]), "--only", ONLY] + BUILD_STEPS
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit(f"build of group {group} failed")


def run(name, delay):
    time.sleep(delay)
    group, extra = SCENARIOS[name]
    command = [sys.executable, os.path.join(MOD, "test.py"), "--group", group, "--no-build",
               "--stage", os.path.join(HERE, STAGES[group]), "--steps", os.path.join(HERE, name + ".txt")] + extra
    output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
    verdict = [line for line in output.splitlines() if line.startswith("== RESULT")]
    return name, (verdict[-1][3:] if verdict else "RESULT: FAIL (no verdict)"), output


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenarios", nargs="*", help="scenario names (default: all)")
    ap.add_argument("--jobs", type=int, default=3, help="engines running at the same time (default 3)")
    ap.add_argument("--no-build", action="store_true", help="reuse the staging dirs as they are")
    ap.add_argument("--quiet", action="store_true", help="do not print the log of a failed scenario")
    args = ap.parse_args()
    names = args.scenarios or list(SCENARIOS)
    unknown = [name for name in names if name not in SCENARIOS]
    if unknown:
        print("unknown scenario(s):", " ".join(unknown), "- known:", " ".join(SCENARIOS))
        return 2
    if not args.no_build:
        for group in sorted({SCENARIOS[name][0] for name in names}):
            build(group)
            print(f"built out-{group}", flush=True)
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        # started two seconds apart within each wave of `jobs`
        futures = [pool.submit(run, name, 2 * (index % max(1, args.jobs))) for index, name in enumerate(names)]
        for future in concurrent.futures.as_completed(futures):
            name, verdict, output = future.result()
            results[name] = verdict
            print(f"{name:<20} {verdict}", flush=True)
            if "PASS" not in verdict and not args.quiet:
                print(output)
    failed = [name for name in names if "PASS" not in results[name]]
    print(f"{len(names) - len(failed)} of {len(names)} scenarios passed" + (f"; failed: {' '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
