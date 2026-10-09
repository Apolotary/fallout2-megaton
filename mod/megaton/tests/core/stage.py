# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Stage of the main-quest ("core") tests: the compacted town with the core cast.

    python3 mod/megaton/test.py --group core --stage tests/core/stage.py \\
        --only megaton,mgweld,mgsimms,mgburke,mgbomb,mgharden,mghitman,mgspgate,mgspsims,mgsprad,mggate,mghouse,mgcabin \\
        --steps tests/core/<scenario>.txt

tests/core/run_all.py runs every scenario and prints one line per result.

Nothing here ships. On top of cast/core.py the stage has three test rigs, plain
signposts that carry tests/core/scripts/mgcabin.ssl (a rig borrowing the
script slot of the password cabinet: the stage's SCRIPTS_DIR is searched
before scripts/, and only this group's staging dir is built from it). A step
file presses a rig's "buttons" with `use @RIG` and `skill <n> @RIG`, after
`dude @RIG/0` (the rigs stand one row above the exit grids: a player who walks
up to one from the wrong side steps onto the world map):

    @RIG    use: +10 hours   Repair 13: +3 days   Science 12: +8 days
            Lockpick 9: a kit (Tool, 2 Mentats, Geiger counter, $500)
            Traps 11: Fusion Pulse Charge and Moira's notes into the pack
    @RIG2   use: Intelligence -3 (a player of very few words)
            Repair 13: Speech and Barter +100     Science 12: Perception +3, Science +40
            Lockpick 9: Traps +40                 Traps 11: Agility -3, Small Guns
            and Unarmed -60 (nothing to offer when Burke draws)
    @RIG3   use: probes into unassigned GVARs, for `expect gvar`:
            692 money carried, 691 experience, 690 rads, 688 day * 100 + hour,
            689 = pulse charges * 1000 + house keys * 100 + Mentats * 10 + contracts
            Repair 13: Unarmed +200 and three ranks of Bonus HtH Damage: a punch
            that does not miss and gets through the sheriff's armour, for the
            killing tests (on stage_weak.py, where three hit points are a life)

The first premade character the tests play (Narg) is Gifted: PE 6, IN 5, AG 8,
ST 8 or more, every skill ten points down. Traps 14, Science 10, Speech and
Barter far below any gate, Small Guns and Unarmed below the saloon scene's.
"""
import cast
import stagekit

SCRIPTS_DIR = "scripts"                       # the rig: mgcabin

SPOTS = stagekit.compact()
_ex, _ey, _ = SPOTS["ENTRY"]
SPOTS["RIG"] = (_ex + 3, _ey + 1, 0)          # stage-only spots, on the free row behind the entrance
SPOTS["RIG2"] = (_ex - 3, _ey + 1, 0)
SPOTS["RIG3"] = (_ex + 1, _ey + 1, 0)

EXTRA = [
    cast.thing("RIG", cast.STAND_INS["scenery"], script="mgcabin"),
    cast.thing("RIG2", cast.STAND_INS["scenery"], script="mgcabin"),
    cast.thing("RIG3", cast.STAND_INS["scenery"], script="mgcabin"),
]


def build_maps(out_dir):
    stagekit.build(out_dir, groups=["core"], spots=SPOTS, extra=EXTRA)
