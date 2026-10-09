# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The side-quest cast in the REAL town: layout/ builds the architecture, this group's
cast stands on its real spots, nobody else is on the map, and the test rig is added.

    python3 mod/megaton/test.py --group sidequests-town --stage tests/sidequests/stage_town.py \
        --only megaton,mgsettlr,mgmoriar,mgsilvr,mgterm,mgoffice,mgcabin,mgstrong,mgwalter,mgleak,mglucy,mgjeri \
        --steps tests/sidequests/town.steps --res 1280x960

(staging dir mod/megaton/out-sidequests-town, run directory run/mg-sidequests-town-town.)
It answers what the flat stage cannot: is the office door a real door in a wall, can the
terminal, the cabinet, the strongbox and the three leaks be walked to, do the NPCs stand
where they can be talked to. The step file is town.steps (not .txt, so run_all.py, which
runs every *.txt on the flat stage, leaves it alone).

Depends on the layout package's build(), test_names() and SPOTS_FILE; if those change,
this file is the only thing here that has to follow. Step files get the town's own
names (@IN_SALOON_OFFICE, @TRACK, @POOL, ... see layout.test_names) plus @RIG.
"""
import json
import os

import cast
import layout
from f2lib import GameFiles, geometry as g

SCRIPTS_DIR = "scripts"                       # the rig: mgsettlr (see stage.py)

RIG_OFFSET = (-9, -1)                         # from ENTRY: on the apron, out of everybody's way


def build_maps(out_dir):
    gf = GameFiles(overlay=out_dir)
    m, info = layout.build(gf, groups=["sidequests"], strict=True)
    ex, ey, _ = layout.spots.SPOTS["ENTRY"]
    rig = (ex + RIG_OFFSET[0], ey + RIG_OFFSET[1], 0)
    cast.place_cast(m, gf, groups=[], extra=[cast.critter(rig, cast.PID_CR_AVERAGE_PEASANT_65, script="mgsettlr")])
    os.makedirs(os.path.join(out_dir, "maps"), exist_ok=True)
    m.save(os.path.join(out_dir, "maps", m.file_name))
    names = layout.test_names(m)
    names["RIG"] = g.tile_at(rig[0], rig[1])
    with open(os.path.join(out_dir, layout.SPOTS_FILE), "w") as f:
        json.dump(names, f, indent=1, sort_keys=True)
