#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Run every foundation scenario in the real engine and say which passed.

    python3 mod/megaton/tests/foundation/run_all.py            (about 6 minutes)
    python3 mod/megaton/tests/foundation/run_all.py items pipboy

Each scenario is one test.py run (group "foundation": staging dir
mod/megaton/out-foundation, runs run/mg-foundation-<scenario>/). The step
files say in their first lines what they prove; scenarios without `expect`
lines (steal) only pass in the sense that nothing broke - their screenshots
are the evidence.

Before any build, check_wording.py checks the live dialogue and art sources.
Then hdrcheck.ssl is compiled: it uses every macro of scripts/megaton.h, so a
header change that no longer compiles fails here first.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(MOD))

# scenario: (stage file, extra test.py arguments)
SCENARIOS = {
    "boot": ("stage.py", []),
    "worldmap": ("stage.py", []),
    "pipboy": ("stage.py", ["--ddraw", "PipBoyAvailableAtGameStart=1"]),
    "items": ("stage.py", []),
    "townsfolk": ("stage.py", []),
    "hostile": ("stage.py", []),
    "attack": ("stage.py", []),
    "steal": ("stage.py", []),
    "saveload": ("stage.py", []),
    "default-start": ("stage.py", ["--map", "default"]),
    "arroyo-worldmap": ("stage.py", ["--map", "arbridge.map"]),
    "real-spots": ("stage_real.py", []),
}


def header_check():
    with tempfile.TemporaryDirectory() as scratch:
        return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ssl.py"), "compile",
                               os.path.join(HERE, "hdrcheck.ssl"), "-o", os.path.join(scratch, "hdrcheck.int"),
                               "-I", os.path.join(MOD, "scripts")]).returncode


def main():
    names = sys.argv[1:] or list(SCENARIOS)
    unknown = [name for name in names if name not in SCENARIOS]
    if unknown:
        print(__doc__)
        print("unknown scenario(s):", " ".join(unknown), "- known:", " ".join(SCENARIOS))
        return 2
    if subprocess.run([sys.executable, os.path.join(HERE, "check_wording.py")]).returncode != 0:
        return 1
    subprocess.run([sys.executable, os.path.join(MOD, "build.py"), "ids"], check=True)
    if header_check() != 0:
        print("megaton.h: hdrcheck.ssl does not compile")
        return 1
    print("megaton.h: every macro compiles")
    results = {}
    for name in names:
        stage, extra = SCENARIOS[name]
        command = [sys.executable, os.path.join(MOD, "test.py"), "--group", "foundation",
                   "--stage", os.path.join(HERE, stage), "--steps", os.path.join(HERE, name + ".txt")] + extra
        output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
        verdict = [line for line in output.splitlines() if line.startswith("== RESULT")]
        results[name] = verdict[-1][3:] if verdict else "RESULT: FAIL (no verdict)"
        print(f"{name:<16} {results[name]}", flush=True)
        if "PASS" not in results[name]:
            print(output)
    failed = [name for name, verdict in results.items() if "PASS" not in verdict]
    print(f"{len(results) - len(failed)} of {len(results)} scenarios passed" + (f"; failed: {' '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
