# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Stage of the merchants group's tests: the compacted town with the shop cast and a test rig.

    python3 mod/megaton/test.py --group merchants --stage tests/merchants/stage.py \
        --only megaton,mgmoira,mgmerc,mggob,mgdoc,mgjenny,mgtrade,mgnova,mgbed,mgsettlr --steps tests/merchants/<scenario>.txt
    python3 mod/megaton/tests/merchants/run_all.py            (every scenario)

Nothing here ships. On the stage stand the entries of cast/merchants.py (Moira,
her mercenary, Gob, Doc Church, Jenny, the caravan trader, Nova, and plain beds
on HOUSE_BED and COMMON_BED carrying mgbed) plus one stage-only object:

    RIG   a brahmin running the test rig tests/merchants/scripts/mgsettlr.ssl.
          The autotest can read and write global variables but cannot wound
          the player, hand him money, move the clock or look into a pocket;
          the rig does that on request (see the header of that file for the
          commands and the probe GVARs the `expect gvar` lines read).
"""
import cast
import stagekit

SCRIPTS_DIR = "scripts"                       # the rig: mgsettlr.ssl (a stand-in under a borrowed stem)

SPOTS = stagekit.compact()
_ex, _ey, _ = SPOTS["ENTRY"]
SPOTS["RIG"] = (_ex + 10, _ey - 3, 3)          # stage-only spot, out of everybody's way

EXTRA = [
    cast.critter("RIG", cast.PID_CR_BRAHMIN, script="mgsettlr", team=cast.TEAM_MG_ANIMAL, ai=cast.AI_MG_ANIMAL),
]


def build_maps(out_dir):
    stagekit.build(out_dir, groups=["merchants"], spots=SPOTS, extra=EXTRA)
