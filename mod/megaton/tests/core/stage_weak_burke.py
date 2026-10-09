# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The core stage with Burke at three hit points: for the scenarios in which the
player kills him with one punch (kill-burke, kill-burke-allowed, kill-burke-scene).

    python3 mod/megaton/tests/core/run_all.py kill-burke        (group "core-weakb", mod/megaton/out-core-weakb)

See stage_weak.py, which does the same to Simms and Harden.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage import SCRIPTS_DIR, SPOTS  # noqa: F401  (read by build.py)
from stage_weak import build_weak


def build_maps(out_dir):
    build_weak(out_dir, ("BURKE",))
