# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The real town after dark, for looking at the lamps (tests/layout/night.txt).

    python3 mod/megaton/test.py --group layout --stage tests/layout/stage_night.py --only megaton \\
        --steps tests/layout/night.txt --res 1280x960

Not a stage in the usual sense: the map is the whole town, built by layout/.
The only thing staged is the map script, replaced by night/megaton.ssl, a rig
that winds the clock on to 22:24 on entry (the test driver cannot set the time).
"""
import layout

SCRIPTS_DIR = "night"


def build_maps(out_dir):
    layout.build_maps(out_dir)
