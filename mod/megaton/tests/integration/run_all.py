#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Run the integration scenarios (the real town, every script) in the real engine.

    python3 mod/megaton/tests/integration/run_all.py                  (everything, about 40 minutes)
    python3 mod/megaton/tests/integration/run_all.py a-arrival f-moira
    python3 mod/megaton/tests/integration/run_all.py --jobs 2 --no-build b-good-path
    python3 mod/megaton/tests/integration/run_all.py --list
    python3 mod/megaton/tests/integration/run_all.py --publish        (no engine: the pictures of mod/megaton/out-preview/)

Each scenario is one step file of this directory, run by mod/megaton/test.py; its first
comment lines say what it proves and which values it expects. Two builds are used:

    group "int"       tests/integration/stage.py: the town exactly as shipped plus a
                      remote-control test rig (scripts/mgrig.ssl: money, clock, skills, probes)
                      mod/megaton/out-int, run/mg-int-<scenario>/
    group "int-ship"  no stage at all: what build.py packs into mod/megaton/out/patch001.dat
                      mod/megaton/out-int-ship, run/mg-int-ship-<scenario>/

No scenario needs a ddraw.ini switch: the Pip-Boy opens in a game begun at the gate because
megaton.ssl plays the Vault-suit movie (test.py dismisses it), and karma changes are
announced by the scripts themselves.

Scenarios run several at a time (--jobs, default 3), started three seconds apart because
test.py hands the engine its steps through one file per staging dir. Fights are dice: a
scenario marked DICE below may fail on an unlucky roll and is worth a second run.
The result table is also written to run/mg-int-results.txt.

Beside the engine scenarios this directory holds an offline text check:
    check_text.py     every script's .msg: replies that overflow the conversation window,
                      line numbers a script uses but its .msg lacks, placeholders (a second)

The engine's dice repeat from run to run while the scripts make the same random calls (its
generator is seeded from the milliseconds since start-up, which hardly vary): a DICE scenario
that passes keeps passing until a script changes, and then may fail every time. Look at the
screenshots before blaming the script.

--publish fills mod/megaton/out-preview/ from what is already there: megaton.png and
megaton-noroof.png are rendered offline from mod/megaton/out (tools/render_map.py, pixel-exact
with the engine), and six screenshots of the last z-showcase run are copied under plain
names (PUBLISH below says which shot becomes which picture).
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

BUILD_STEPS = ["ids", "data", "protos", "art", "scripts", "maps", "lint", "pack"]
STAGES = {"int": os.path.join(HERE, "stage.py"), "int-ship": None}


def long(seconds):
    return ["--timeout", str(seconds)]


# scenario: (group, extra test.py arguments)
SCENARIOS = {
    # (a) arrival, on the archive as shipped
    "a-arrival": ("int-ship", long(300)),
    # (b) the good path
    "b-good-path": ("int", long(480)),
    # (c) the evil path, and what the world map does after the blast
    "c-evil-path": ("int", long(480)),
    "c-after-blast": ("int", long(300)),
    # (d) informing on Burke: stand by (and Harden pays), warned, intervene, absent
    "d-scene-watch": ("int", ["--res", "1280x960"] + long(540)),
    "d-scene-warned": ("int", long(420)),
    "d-scene-shove": ("int", long(420)),              # DICE
    "d-scene-absent": ("int", long(420)),
    # ... and fitting Burke's charge all the same while the sheriff walks to arrest him
    "d-scene-rig": ("int", long(420)),
    "d-scene-rig-warned": ("int", long(420)),
    # (e) change of heart
    "e-change-of-heart": ("int", long(480)),          # DICE
    "e-pull-and-leave": ("int", long(360)),
    # (f) merchants and services
    "f-moira": ("int", long(360)),
    "f-gob": ("int", long(360)),
    "f-doc": ("int", long(360)),
    "f-nova-jenny-trader": ("int", long(420)),        # includes the restock after three days
    # (g) side quests
    "g-walter": ("int", long(480)),
    "g-moriarty-pay": ("int", long(420)),
    "g-moriarty-silver": ("int", long(420)),
    "g-moriarty-terminal": ("int", long(600)),
    "g-moriarty-science": ("int", long(420)),
    "g-lucy": ("int", long(420)),
    "g-walter-robbed": ("int", long(300)),
    # (h) hostility
    "h-hostile": ("int", long(420)),                  # DICE
    "h-amnesty": ("int", long(360)),
    "h-threats": ("int", long(360)),                  # talk of setting the bomb off: joke, question, the walk to the gate
    "h-banished": ("int", long(360)),                 # "I mean it": hostile, but marched out and warned first
    # (i) persistence
    "i-save-load": ("int", long(540)),
    "i-leave-return": ("int", long(480)),
    "i-hired-guns": ("int", long(420)),               # DICE (the fight)
    "i-hired-guns-gone": ("int", long(300)),          # the surviving hired guns leave after a week
    # (j) a normal new game: the world map from Arroyo, and a round trip
    "j-worldmap": ("int-ship", ["--map", "arvillag.map", "--skip-movies", "2"] + long(480)),   # DICE
    # everybody else in town
    "k-flavour": ("int", long(540)),
    # the bomb for a character with Traps 14: the notes, a hint, Moira's tools
    "l-bomb-help": ("int", long(360)),
    # karma changes are announced once, also with the engine's own announcement switched on
    "m-karma-once": ("int", ["--ddraw", "DisplayKarmaChanges=1"] + long(300)),
    # the pictures of the report
    "z-showcase": ("int", ["--res", "1280x960"] + long(420)),
}


# picture in mod/megaton/out-preview/ <- screenshot of run/mg-int-z-showcase/shots/
PUBLISH = {
    "gate.png": "02-gate-weld-greets.png",
    "sheriff-at-the-gate.png": "05c-sheriff-and-newcomer.png",
    "pool.png": "08-pool-c.png",
    "saloon.png": "10-saloon-b.png",
    "craterside-supply.png": "12-craterside-a.png",
    "night.png": "16-night-pool.png",
}


def publish():
    """Overview renders of the shipped map and the six showcase screenshots -> mod/megaton/out-preview/."""
    target = os.path.join(MOD, "out-preview")
    os.makedirs(target, exist_ok=True)
    staging = os.path.join(MOD, "out")
    render = [sys.executable, os.path.join(ROOT, "tools", "render_map.py"), os.path.join(staging, "maps", "megaton.map"),
              "--overlay", staging, "--crop", str(96 * 200 + 100), "50", "--fit", "2400"]
    for name, extra in (("megaton.png", ["--roofs"]), ("megaton-noroof.png", [])):
        subprocess.run(render + extra + ["-o", os.path.join(target, name)], cwd=ROOT, check=True)
    shots = os.path.join(ROOT, "run", "mg-int-z-showcase", "shots")
    missing = 0
    for name, shot in PUBLISH.items():
        source = os.path.join(shots, shot)
        if os.path.exists(source):
            shutil.copyfile(source, os.path.join(target, name))
            print(f"{os.path.relpath(os.path.join(target, name), ROOT)} <- {os.path.relpath(source, ROOT)}")
        else:
            print(f"missing: {os.path.relpath(source, ROOT)} (run z-showcase first)")
            missing += 1
    return 1 if missing else 0


def build(group):
    out_dir = os.path.join(MOD, "out-" + group)
    shutil.rmtree(out_dir, ignore_errors=True)
    command = [sys.executable, os.path.join(MOD, "build.py"), "--out", out_dir]
    if STAGES[group]:
        command += ["--stage", STAGES[group]]
    result = subprocess.run(command + BUILD_STEPS, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit(f"build of group {group} failed")


def run(name, delay):
    time.sleep(delay)
    group, extra = SCENARIOS[name]
    command = [sys.executable, os.path.join(MOD, "test.py"), "--group", group, "--no-build",
               "--steps", os.path.join(HERE, name + ".txt")] + extra
    if STAGES[group]:
        command += ["--stage", STAGES[group]]
    output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
    verdict = [line for line in output.splitlines() if line.startswith("== RESULT")]
    with open(os.path.join(ROOT, "run", f"mg-{group}-{name}.log"), "w") as f:
        f.write(output)
    return name, (verdict[-1][3:] if verdict else "RESULT: FAIL (no verdict)"), output


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenarios", nargs="*", help="scenario names (default: all)")
    ap.add_argument("--jobs", type=int, default=3, help="engines running at the same time (default 3)")
    ap.add_argument("--no-build", action="store_true", help="reuse the staging dirs as they are")
    ap.add_argument("--quiet", action="store_true", help="do not print the log of a failed scenario")
    ap.add_argument("--list", action="store_true", help="list the scenarios and stop")
    ap.add_argument("--publish", action="store_true", help="fill mod/megaton/out-preview/ (overview renders, showcase screenshots) and stop")
    args = ap.parse_args()
    if args.publish:
        return publish()
    if args.list:
        for name, (group, extra) in SCENARIOS.items():
            print(f"{name:<24} {group:<9} {' '.join(extra)}")
        return 0
    names = args.scenarios or [name for name in SCENARIOS if os.path.exists(os.path.join(HERE, name + ".txt"))]
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
        futures = [pool.submit(run, name, 3 * (index % max(1, args.jobs))) for index, name in enumerate(names)]
        for future in concurrent.futures.as_completed(futures):
            name, verdict, output = future.result()
            results[name] = verdict
            print(f"{name:<24} {verdict}", flush=True)
            if "PASS" not in verdict and not args.quiet:
                print(output)
    failed = [name for name in names if "PASS" not in results[name]]
    table = [f"{name:<24} {SCENARIOS[name][0]:<9} {results[name]:<40} run/mg-{SCENARIOS[name][0]}-{name}/" for name in names]
    print()
    print("\n".join(table))
    print(f"\n{len(names) - len(failed)} of {len(names)} passed" + (f"; failed: {' '.join(failed)}" if failed else ""))
    if not args.scenarios:
        with open(os.path.join(ROOT, "run", "mg-int-results.txt"), "w") as f:
            f.write("\n".join(table) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
