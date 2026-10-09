# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The core stage with Simms and Harden at three hit points: for the scenarios in
which the player has to kill one of them (kill-simms, kill-simms-scene, kill-harden).

    python3 mod/megaton/tests/core/run_all.py kill-simms        (group "core-weak", mod/megaton/out-core-weak)

Same spots, cast, rigs and scripts as stage.py; after stagekit has built the
map, the victims are weakened and the map is saved again. With the rig's
Unarmed +200 and Bonus HtH Damage (@RIG3, Repair) one punch from the premade
character lands and does 15 or 16 points: four get through the sheriff's
armour (DT 8, DR 40%). Nothing can be done about the dice of whoever shoots back.

Burke has a stage of his own (stage_weak_burke.py): a critter at three hit
points flees for as long as a fight lasts, and a fight cannot be ended while
somebody is fleeing, so a scenario that goes on after the kill needs
everybody else at full strength.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stagekit
from stage import EXTRA, SCRIPTS_DIR, SPOTS  # noqa: F401  (SPOTS and SCRIPTS_DIR are read by build.py)

WEAK = ("SIMMS", "HARDEN")


def build_weak(out_dir, victims):
    built = stagekit.build(out_dir, groups=["core"], spots=SPOTS, extra=EXTRA)
    for entry, obj in built["placed"]:
        if entry["type"] == "critter" and entry["spot"] in victims:
            obj["hp"] = 3
    m = built["map"]
    m.save(os.path.join(out_dir, "maps", m.file_name))


def build_maps(out_dir):
    build_weak(out_dir, WEAK)
