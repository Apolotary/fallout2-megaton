# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Stage of the flavour group's tests: the flavour cast on the town's REAL coordinates.

    python3 mod/megaton/test.py --group flavour --stage tests/flavour/stage.py \
        --only megaton,mgcrom,mgmaya,mgstock,mgmicky,mgbilly,mgmaggie,mgnathan,mgsettlr,mgarmory,mgweld,mgsimms,mgharden \
        --steps tests/flavour/<scenario>.txt

Flat desert, no buildings: what is tested here is scripts, not architecture.
The spots are NOT compacted (no SPOTS name in this file), so the settlers walk
the same distances as in the town and nobody stands within earshot of
everybody else. Reach people with `dude @NAME/3`.

Besides cast/flavour.py the stage places (nothing of this ships):

    RIG           a robot running the test rig scripts/mgweld.ssl: step files
                  drive it through GVAR 692 (command) and 690 (argument / answer)
                  to change the clock, the player's pockets, Intelligence and
                  Lockpick, and to read values back. Commands: see mgweld.ssl.
    SIMMS, HARDEN stand-ins (scripts/mgsimms.ssl, mgharden.ssl) carrying the real
                  script numbers, which is how mgarmory.ssl recognises its
                  witnesses. GVAR 691 sends them out of sight: bit 1 Simms,
                  bit 2 Harden.
    SETTLER_IDLE  a settler on no SETTLERn spot: he keeps still, for dialogue tests.
    VICTIM1, 2    two more spare settlers in the south-west corner, 24 hexes or more
                  from anybody, for the test that kills them (kill.txt). VICTIM2 has
                  1 hit point.
    ARMORY_DOOR   gets the stage's stand-in wooden door, standing in the open.
"""
import cast
import stagekit

SCRIPTS_DIR = "scripts"                       # the rig and the two witnesses

_ex, _ey, _ = stagekit.town.SPOTS["ENTRY"]
# Stage-only places; not called SPOTS, so no script is recompiled with moved tiles.
PLACES = {
    "RIG": (_ex + 10, _ey + 1, 0),            # on the free row behind the entrance
    "SETTLER_IDLE": (_ex - 9, _ey - 3, 2),
    "VICTIM1": (60, 124, 2),
    "VICTIM2": (60, 131, 2),
}

EXTRA = [
    cast.critter("RIG", cast.PID_CR_REPAIR_BOT, script="mgweld", ai=cast.AI_MG_ROBOT),
    cast.critter("SIMMS", cast.PID_CR_WEAK_GUN_GUARD_71, script="mgsimms", ai=cast.AI_MG_GUARD),
    cast.critter("HARDEN", cast.PID_CR_CHILD_MALE, script="mgharden", ai=cast.AI_MG_CHILD),
    cast.critter("SETTLER_IDLE", cast.PID_CR_AVERAGE_PEASANT_65, script="mgsettlr"),
    cast.critter("VICTIM1", cast.PID_CR_AVERAGE_PEASANT_66, script="mgsettlr"),
    cast.critter("VICTIM2", cast.PID_CR_AVERAGE_PEASANT_65, script="mgsettlr", hp=1),
]


def build_maps(out_dir):
    stagekit.build(out_dir, groups=["flavour"], spots=PLACES, extra=EXTRA)
