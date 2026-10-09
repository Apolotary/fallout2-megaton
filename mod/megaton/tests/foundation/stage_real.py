# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The foundation cast on the town's REAL coordinates (no stagekit.compact()).

    python3 mod/megaton/test.py --group foundation --stage tests/foundation/stage_real.py --steps tests/foundation/real-spots.txt

Same entries as stage.py; only where they stand differs, so scripts are
compiled with the TILE_* values of tiles.h.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stagekit
from stage import EXTRA, SCRIPTS_DIR  # noqa: F401  (SCRIPTS_DIR is read by build.py)

# The stage-only spot ITEM_BOX needs a place here too; no SPOTS name, so nothing is recompiled.
_ex, _ey, _ = stagekit.town.SPOTS["ENTRY"]
PLACES = {"ITEM_BOX": (_ex + 3, _ey + 1, 0)}


def build_maps(out_dir):
    stagekit.build(out_dir, groups=[], spots=PLACES, extra=EXTRA)
