#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Run the flavour group's scenarios in the real engine and say which passed.

    python3 mod/megaton/tests/flavour/run_all.py                 (everything, about 15 minutes with --jobs 3)
    python3 mod/megaton/tests/flavour/run_all.py micky armory    (only these)
    python3 mod/megaton/tests/flavour/run_all.py --jobs 1        (one engine at a time, about 40 minutes)

Stage scenarios (stage.py: the cast on a flat desert with the test rig) share
one build of mod/megaton/out-flavour: the first one builds it, the others
reuse it with test.py --no-build, up to --jobs engines side by side. "town"
is different: it builds the REAL town (layout/) into mod/megaton/out-flavour-town
with this group's scripts plus the main-quest group's mgharden, and has no rig.

Every step file says in its first lines what it proves and which values it
expects. "look" has no `expect` lines and "saveload" prints the two numbers
that matter instead of asserting them: these pass in the sense that nothing
broke, and their screenshots / printed lines are the evidence. Runs land in
run/mg-flavour-<scenario>/ and run/mg-flavour-town-town/.
"""
import argparse
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))

SCRIPTS = "megaton,mgcrom,mgmaya,mgstock,mgmicky,mgbilly,mgmaggie,mgnathan,mgsettlr,mgarmory"
STAGE_ONLY = SCRIPTS + ",mgweld,mgsimms,mgharden"       # plus the rig and the two stand-in witnesses
TOWN_ONLY = SCRIPTS + ",mgharden"                        # plus the real sheriff's son

# scenario: seconds before test.py gives up on the engine
STAGE_SCENARIOS = {
    "stockholm": 240, "stockholm-lowint": 200,
    "cromwell": 300, "cromwell-states": 360,
    "maya": 300, "micky": 400, "billy": 300,
    "maggie": 300, "maggie-disarmed": 240, "nathan": 300,
    "settler-talk": 420, "settler-day": 420, "settler-clock": 480,
    "armory": 360, "armory-caught": 240,
    "kill": 300, "look": 300, "saveload": 300,
}
TOWN_SCENARIOS = {"town": 420}
STAGGER = 6        # seconds between two starts: test.py writes one .steps.txt per staging dir, read by the engine launcher


START = threading.Lock()


def run(name, timeout, extra, stagger=0):
    command = [sys.executable, os.path.join(MOD, "test.py"), "--steps", os.path.join(HERE, name + ".txt"),
               "--timeout", str(timeout)] + extra
    with START:                        # one start at a time, `stagger` seconds apart
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(stagger)
    output = process.communicate()[0]
    verdict = [line for line in output.splitlines() if line.startswith("== RESULT")]
    return (verdict[-1][3:] if verdict else "RESULT: FAIL (no verdict)"), output


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jobs", type=int, default=3, help="engines running side by side (default 3)")
    parser.add_argument("names", nargs="*", help="scenarios (default: all)")
    args = parser.parse_args()
    known = dict(STAGE_SCENARIOS, **TOWN_SCENARIOS)
    names = args.names or list(known)
    unknown = [name for name in names if name not in known]
    if unknown:
        print("unknown scenario(s):", " ".join(unknown), "- known:", " ".join(known))
        return 2

    results = {}
    lock = threading.Lock()

    def report(name, verdict, output):
        with lock:
            results[name] = verdict
            print(f"{name:<18} {verdict}", flush=True)
            if "PASS" not in verdict:
                print(output)

    stage_extra = ["--group", "flavour", "--stage", os.path.join(HERE, "stage.py"), "--only", STAGE_ONLY]
    stage_names = [name for name in names if name in STAGE_SCENARIOS]
    threads = []
    for name in names:
        if name in TOWN_SCENARIOS:      # its own staging dir: can run beside everything else
            thread = threading.Thread(target=lambda n=name: report(n, *run(n, known[n], ["--group", "flavour-town", "--only", TOWN_ONLY])))
            thread.start()
            threads.append(thread)
    if stage_names:
        first = stage_names[0]
        report(first, *run(first, known[first], stage_extra))          # this one builds out-flavour
        queue = stage_names[1:]
        slots = threading.Semaphore(max(1, args.jobs))

        def worker(name):
            with slots:
                report(name, *run(name, known[name], ["--group", "flavour", "--no-build"], STAGGER))

        for name in queue:
            thread = threading.Thread(target=worker, args=(name,))
            thread.start()
            threads.append(thread)
    for thread in threads:
        thread.join()

    failed = [name for name in names if "PASS" not in results.get(name, "")]
    print(f"{len(names) - len(failed)} of {len(names)} scenarios passed" + (f"; failed: {' '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
