# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Stage of the side-quest tests: the sidequests cast on open ground, plus a test rig.

    python3 mod/megaton/test.py --group sidequests --stage tests/sidequests/stage.py \
        --only megaton,mgsettlr,mgmoriar,mgsilvr,mgterm,mgoffice,mgcabin,mgstrong,mgwalter,mgleak,mglucy,mgjeri \
        --steps tests/sidequests/<scenario>.txt
    python3 mod/megaton/tests/sidequests/run_all.py [scenario ...]      (every scenario, with a verdict each)

Nothing here ships. The stage keeps the entrance where the town has it and
lays this group's cast out in three clusters north of it, far enough apart to
read in a screenshot (scripts are recompiled with these TILE_* values):

    saloon      MORIARTY, LUCY, JERICHO, and to their left the office:
                OFFICE_DOOR (a stand-in door), TERMINAL, CABINET, STRONGBOX
    plant       WALTER with LEAK1..3 around him
    outside     SILVER, right of the entrance

RIG is a stage-only critter running tests/sidequests/scripts/mgsettlr.ssl, a
stand-in that takes the settler's script slot. It does what the autotest
commands cannot: give items, raise skills, set money, kill or wound somebody,
and report numbers. A step file drives it through three unassigned GVARs:

    setgvar 691 <a>      first argument
    setgvar 692 <b>      second argument (also where probes put their answer)
    setgvar 690 <cmd>    the rig runs the command on its next tick and sets 690 back to 0
    wait 400

The commands are listed at the top of scripts/mgsettlr.ssl.
"""
import cast
import stagekit

SCRIPTS_DIR = "scripts"                       # the rig: mgsettlr

SPOTS = stagekit.compact()
_ex, _ey, _ = SPOTS["ENTRY"]
SPOTS.update({
    # saloon
    "MORIARTY": (_ex, _ey - 10, 2),
    "LUCY": (_ex - 4, _ey - 8, 2),
    "JERICHO": (_ex + 4, _ey - 8, 2),
    "OFFICE_DOOR": (_ex - 7, _ey - 12, 0),
    "TERMINAL": (_ex - 10, _ey - 14, 2),
    "CABINET": (_ex - 13, _ey - 12, 2),
    "STRONGBOX": (_ex - 10, _ey - 10, 2),
    # water plant
    "WALTER": (_ex + 9, _ey - 12, 2),
    "LEAK1": (_ex + 12, _ey - 9, 0),
    "LEAK2": (_ex + 14, _ey - 13, 0),
    "LEAK3": (_ex + 10, _ey - 16, 0),
    # outside the wall
    "SILVER": (_ex + 12, _ey - 2, 3),
    # stage only
    "RIG": (_ex - 11, _ey + 1, 0),
})

EXTRA = [
    cast.critter("RIG", cast.PID_CR_AVERAGE_PEASANT_65, script="mgsettlr"),
]


def build_maps(out_dir):
    stagekit.build(out_dir, groups=["sidequests"], spots=SPOTS, extra=EXTRA)
