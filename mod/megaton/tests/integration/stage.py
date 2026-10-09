# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Stage of the integration tests: the REAL town, every script, plus one test rig.

    python3 mod/megaton/test.py --group int --stage tests/integration/stage.py --steps tests/integration/<scenario>.txt
    python3 mod/megaton/tests/integration/run_all.py           (every scenario, with a result table)

The map is exactly what ships (layout.build with strict=True: every cast entry
placed, every script attached) with one addition: a signpost far beyond the
town wall that carries tests/integration/scripts/mgrig.ssl, a remote control
that step files drive through global variables (give money, move the clock,
raise a skill, read hit points ... the table is at the top of mgrig.ssl).
The rig does not borrow a script slot of the mod: this file appends
"mgrig.int" to the staging dir's scripts.lst, after the mod's own lines, and
compiles it there. Nothing of this reaches mod/megaton/out.

Scenarios that must prove the shipped archive itself (arrival, the world map)
run without this stage; run_all.py's table says which.

Step files get every name of layout.test_names (spots, @DOOR_*, @IN_*, @POOL,
@PLAZA, @TRACK, @STASH_*) and @RIG.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(MOD))

import cast
import layout
from f2lib import GameFiles, geometry as g

RIG = (150, 60, 0)                             # open desert north-east of the wall; nothing walks there
RIG_SCRIPT = "mgrig"


def _install_rig_script(out_dir):
    """Append the rig to the staged scripts.lst and compile it into the staging tree."""
    lst = os.path.join(out_dir, "scripts", "scripts.lst")
    with open(lst, "rb") as f:
        text = f.read().decode("latin-1")
    if RIG_SCRIPT + ".int" not in text:
        with open(lst, "wb") as f:
            f.write((text.rstrip("\r\n") + f"\r\n{RIG_SCRIPT}.int       ; integration test rig (not shipped)       # local_vars=4").encode("latin-1"))
    command = [sys.executable, os.path.join(ROOT, "tools", "ssl.py"), "compile",
               os.path.join(HERE, "scripts", RIG_SCRIPT + ".ssl"), "-o", os.path.join(out_dir, "scripts", RIG_SCRIPT + ".int"),
               "-I", os.path.join(ROOT, "mod", "scripts_src", "headers"), "-I", os.path.join(MOD, "scripts")]
    if subprocess.run(command).returncode != 0:
        raise SystemExit("integration stage: mgrig.ssl failed to compile")


def build_maps(out_dir):
    _install_rig_script(out_dir)
    gf = GameFiles(overlay=out_dir)
    m, info = layout.build(gf, strict=True)
    cast.place_cast(m, gf, groups=[], strict=True,
                    extra=[cast.thing(RIG, cast.STAND_INS["scenery"], script=RIG_SCRIPT)])
    problems = [p for p in m.validate() if "locked door without a script" not in p]
    if any(p.startswith("error") for p in problems):
        raise SystemExit("integration stage: " + "; ".join(problems))
    os.makedirs(os.path.join(out_dir, "maps"), exist_ok=True)
    m.save(os.path.join(out_dir, "maps", m.file_name))
    names = layout.test_names(m, info)
    names["RIG"] = g.tile_at(RIG[0], RIG[1])
    with open(os.path.join(out_dir, layout.SPOTS_FILE), "w") as f:
        json.dump(names, f, indent=1, sort_keys=True)
