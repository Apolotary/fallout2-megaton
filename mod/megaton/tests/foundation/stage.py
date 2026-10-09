# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Stage of the foundation tests: the compacted town with a little cast of its own.

    python3 mod/megaton/test.py --group foundation --stage tests/foundation/stage.py --steps tests/foundation/<scenario>.txt

Nothing here ships. The cast groups' own files (cast/core.py, ...) are NOT placed
(groups=[]): the flavour group's real settlers stand on SETTLER1 and SETTLER2 too, and
the foundation tests are about the machinery, not the town's people. The entries below
exercise every kind of cast entry with the stand-in scripts of tests/foundation/scripts/:

    SETTLER1, SETTLER2   two townspeople running the reference NPC script (mgsettlr.ssl)
    ITEM_BOX             a footlocker holding the mod's six new items
    HOUSE_DOOR           a stand-in door with the house-door stand-in (opens for the house key)
    SIMMS_GREET          a spatial trigger (mgspgate.ssl) that reports the player walking in
"""
import cast
import stagekit

SCRIPTS_DIR = "scripts"                       # stand-ins: mgsettlr, mghouse, mgspgate

SPOTS = stagekit.compact()
_ex, _ey, _ = SPOTS["ENTRY"]
SPOTS["ITEM_BOX"] = (_ex + 3, _ey + 1, 0)      # stage-only spot, on the free row behind the entrance

EXTRA = [
    cast.critter("SETTLER1", cast.PID_CR_AVERAGE_PEASANT_65, script="mgsettlr",
                 items=[(cast.PID_KNIFE, 1, "right"), (cast.PID_MONEY, 20)]),
    cast.critter("SETTLER2", cast.PID_CR_AVERAGE_PEASANT_66, script="mgsettlr", ai=cast.AI_MG_TOUGH_CITIZEN, hp=20),
    cast.thing("ITEM_BOX", cast.PID_FOOTLOCKER_128,
               items=[(cast.PID_MG_PULSE_CHARGE, 1), (cast.PID_MG_HOUSE_KEY, 1), (cast.PID_MG_LUCY_LETTER, 1),
                      (cast.PID_MG_MOIRA_NOTES, 1), (cast.PID_MG_CONTRACT, 1), (cast.PID_MG_OFFICE_KEY, 1)]),
    cast.attach("HOUSE_DOOR", "door", script="mghouse"),
    cast.spatial("SIMMS_GREET", radius=2, script="mgspgate"),
]


def build_maps(out_dir):
    stagekit.build(out_dir, groups=[], spots=SPOTS, extra=EXTRA)
