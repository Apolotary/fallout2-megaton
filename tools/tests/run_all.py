#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Run the f2lib tests without pytest.

    python3 tools/tests/run_all.py              # everything except the engine test
    python3 tools/tests/run_all.py map geometry # only test_map.py and test_geometry.py
    python3 tools/tests/run_all.py --engine     # also start the real engine (about 40 s)

Every ``test_*`` function of every ``test_*.py`` here is called; the same
files work under ``python3 -m pytest tools/tests -q`` (set F2LIB_ENGINE=1 to
include the engine test there).
"""
import importlib
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _env  # noqa: E402


def main(argv):
    if "--engine" in argv:
        os.environ["F2LIB_ENGINE"] = "1"
    wanted = [a for a in argv if not a.startswith("-")]
    modules = sorted(f[:-3] for f in os.listdir(HERE) if f.startswith("test_") and f.endswith(".py"))
    if wanted:
        modules = [m for m in modules if m[5:] in wanted or m in wanted]

    passed = failed = skipped = 0
    for name in modules:
        module = importlib.import_module(name)
        for attr in sorted(vars(module)):
            test = getattr(module, attr)
            if not attr.startswith("test_") or not callable(test):
                continue
            started = time.time()
            try:
                test()
            except _env.Skip as reason:
                skipped += 1
                print(f"SKIP {name}.{attr}: {reason}")
                continue
            except Exception:
                failed += 1
                print(f"FAIL {name}.{attr}")
                traceback.print_exc()
                continue
            passed += 1
            print(f"ok   {name}.{attr} ({time.time() - started:.1f}s)")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
