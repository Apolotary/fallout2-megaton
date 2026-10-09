#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The gate's DOOR FRM: five frames, shut .. open, for the town's existing door object.

    python3 mod/megaton-art/pieces/gate/gate_door.py            make the FRM, repack out/patch-art.dat
    python3 mod/megaton-art/pieces/gate/gate_door.py --render   ... re-rendering all five states first

WHY THIS EXISTS  The pipeline animates by re-colouring one silhouette (all frames of a piece share
the mask of frame 0), which is right for flickering bulbs and wrong for a door: its leaves leave
the picture. A door in the engine is simply an FRM whose frame 0 is "shut" and whose last frame is
"open" (proto_instance / _obj_use_door play it forwards to open, backwards to close; the stock
gate door10.frm has five frames at 8 fps). So this script takes five pipeline renders of the
leaves (gate_main.py: mg_gate_shut, mg_gate_f25, mg_gate_ajar, mg_gate_f75, mg_gate_open; each
already has everything cut out that the fixed gate covers) and writes them as the frames of ONE
FRM into the art slot of the piece mg_gate_door.

    * every frame has the size and shift of mg_gate_door's own (shut) picture: opening leaves only
      ever uncover ground inside that rectangle, and the manifest check (data.verify) stays true;
    * the slot's proto is not used by the town. The town keeps its door object (stock proto
      0x0200071A, MULTIHEX, its script) and only gives it this art:  gate.fid = <fid below>.
      Opening, closing, blocking and the script then work exactly as before.

build.py runs this script at the end of every build (finish()): the pipeline rewrites the slot
with the one-frame shut picture each time it builds mg_gate_door, and a gate that opens but still
looks shut is not something to find out in the game.
Writes pieces/gate/gate_door.json (frm name, fid, frames) for reference.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)

import numpy as np                                          # noqa: E402

from f2lib import GameFiles                                 # noqa: E402
from f2lib.frm import Frame, Frm                            # noqa: E402

import build as art_build                                   # noqa: E402  (mod/megaton-art/build.py)
from pipeline import data, piece as piece_module            # noqa: E402
from pipeline import proj as P                              # noqa: E402

SCRIPT = os.path.join(HERE, "gate_main.py")
STATES = ["mg_gate_shut", "mg_gate_f25", "mg_gate_ajar", "mg_gate_f75", "mg_gate_open"]
SLOT_PIECE = "mg_gate_door"
FPS = 8
MARKER = os.path.join(HERE, "gate_door.json")


def stale(name):
    meta = os.path.join(art_build.RENDER, name, "meta.json")
    if not os.path.exists(meta):
        return True
    with open(meta) as f:
        if json.load(f).get("preview"):
            return True
    newest = max(os.path.getmtime(SCRIPT), os.path.getmtime(os.path.join(ART, "kit", "gate_extra.py")))
    return os.path.getmtime(meta) < newest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--render", action="store_true", help="render all five states again, even if up to date")
    args = ap.parse_args()
    manifest = data.load_manifest()
    if SLOT_PIECE not in manifest["pieces"]:
        raise SystemExit(f"{SLOT_PIECE} is not registered: run build.py add pieces/gate/gate_main.py ... {SLOT_PIECE} first")
    todo = [name for name in STATES if args.render or stale(name)]
    if todo:
        art_build.run_blender(SCRIPT, art_build.RENDER, only=todo)
    palette = GameFiles().palette
    part = manifest["pieces"][SLOT_PIECE]["parts"][0]
    width, height = part["size"]
    hx, hy = P.hex_px(*part["hex"])
    left = hx + part["shift"][0] - width // 2 - P.ANCHOR_SHIFT[0]            # slicer.assemble's placement
    top = hy + part["shift"][1] - (height - 1) - P.ANCHOR_SHIFT[1]
    frames, lost = [], 0
    for name in STATES:
        result = piece_module.process(os.path.join(art_build.RENDER, name), palette)
        indices = result["frames"][0]
        cx, cy = result["canvas"][0], result["canvas"][1]
        frame = np.zeros((height, width), np.uint8)
        x0, y0 = left - cx, top - cy
        window = indices[max(0, y0):y0 + height, max(0, x0):x0 + width]
        frame[max(0, -y0):max(0, -y0) + window.shape[0], max(0, -x0):max(0, -x0) + window.shape[1]] = window
        lost += int((indices > 0).sum()) - int((frame > 0).sum())
        frames.append(frame)
    if lost > 40:
        raise SystemExit(f"{lost} pixels of the opening leaves fall outside the shut picture: the frames do not fit")
    frm = Frm()
    frm.fps = FPS
    frm.x_offsets = [part["shift"][0]] * 6
    frm.y_offsets = [part["shift"][1]] * 6
    frm.stored = [[Frame(width, height, frame.tobytes()) for frame in frames]]
    frm.direction_map = [0] * 6
    with data.locked_manifest() as locked:
        slot = locked["pieces"][SLOT_PIECE]["parts"][0]
        if slot["size"] != part["size"] or slot["shift"] != part["shift"]:
            raise SystemExit("the manifest changed while the frames were made: run again")
        path = os.path.join(data.OUT, "art", "scenery", slot["frm"])
        with open(path, "wb") as f:
            f.write(frm.to_bytes())
        slot["frames"] = len(frames)                    # the manifest tells the truth about the slot
        locked["pieces"][SLOT_PIECE]["frames"] = len(frames)
        locked["pieces"][SLOT_PIECE]["fps"] = FPS
        locked["pieces"][SLOT_PIECE]["door_frm"] = {
            "what": "art slot of the gate's door FRM: frame 0 shut .. last frame open; worn by the town's own door object",
            "states": STATES, "built_by": "pieces/gate/gate_door.py"}
        count = data.pack()
        problems = data.verify(locked)
    if problems:
        raise SystemExit("out/ does not match the manifest: " + "; ".join(problems))
    marker = {"frm": part["frm"], "fid": part["fid"], "slot_pid_unused": part["pid"], "frames": len(frames), "fps": FPS,
              "size": part["size"], "shift": part["shift"], "hex": part["hex"], "states": STATES,
              "use": "town: keep the door object (stock proto 0x0200071A, MULTIHEX, script) and set its fid to `fid`"}
    with open(MARKER, "w") as f:
        json.dump(marker, f, indent=1)
        f.write("\n")
    print(f"[gate door] {part['frm']} (fid {part['fid']}): {len(frames)} frames of {width}x{height} at {FPS} fps, "
          f"{lost} stray pixel(s) dropped; out/patch-art.dat repacked ({count} files)")


if __name__ == "__main__":
    main()
