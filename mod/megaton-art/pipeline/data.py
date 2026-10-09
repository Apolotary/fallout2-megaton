# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Ids, protos, lists, message files and the patch archive.

manifest.json is the single source of truth for every id the art mod claims:

    "slots": {"scenery": [...], "wall": [...]}     append-only; slot i of "scenery" is
                                                   PID 0x02000000 | (1900 + i), art index 1863 + i,
                                                   file art/scenery/mgs<i>.frm, proto/scenery/mgs<i>.pro
                                                   ("wall": PID 0x03000000 | (1700 + i), art 1690 + i, mgw<i>)
    "pieces": {name: {...}}                        what each piece is and which slots its parts own

Slots whose key starts with "unclaimed/", "sg_free/" or "mgb_free/" are placeholders: while three
authors built at once each claimed a block of numbers up front (signs: scenery slots 50-99, bomb:
100-149 and wall slots 60-99; the gate set was appended behind them), and what they did not use
stayed reserved. They are retired slots like any other: an empty 1x1 sprite, a proto nobody places.

A slot is keyed by "piece/layer/dhx,dhy" and keeps its number for ever: rebuilding a piece
reuses the slots of the parts that still exist, new parts get new slots at the end, and a part
that disappeared leaves a retired slot (an empty 1x1 sprite) so nothing after it moves. Maps
store PIDs and FIDs, so numbers must never be reused or reordered.

Why these numbers: the stock game has 1,851 scenery and 1,633 wall protos and 1,863 / 1,690
art lines. Art lines are appended directly after the stock ones. Proto lists are padded with
lines naming "mgpad.pro" up to 1,899 / 1,699 so that our PIDs start at 1900 / 1700 and leave
the lines in between to the town mod. The engine reads a proto list line only when that PID is
asked for (proto.cc:201-248), so padding lines cost nothing.

Files written under out/ (game paths) and packed into out/patch-art.dat:
    art/scenery/scenery.lst, art/walls/walls.lst        full stock lists + our lines
    art/scenery/mgs*.frm, art/walls/mgw*.frm
    proto/scenery/scenery.lst, proto/walls/walls.lst    full stock lists + padding + our lines
    proto/scenery/mgs*.pro, proto/walls/mgw*.pro, mgpad.pro
    text/english/game/pro_scen.msg, pro_wall.msg        stock files + names and descriptions
"""
import contextlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from f2lib import GameFiles, ids, lst, msg, write_dat2      # noqa: E402
from f2lib.frm import Frame, Frm                            # noqa: E402

from . import piece as piece_module                         # noqa: E402

MANIFEST = os.path.join(ART, "manifest.json")
OUT = os.path.join(ART, "out")
PATCH = os.path.join(OUT, "patch-art.dat")

KINDS = {
    #            obj type               first pid index  art dir     proto dir   prefix  msg file                  clone source
    "scenery": (ids.OBJ_TYPE_SCENERY, 1900, "scenery", "scenery", "mgs", "game/pro_scen.msg", 0x02000005),
    "wall": (ids.OBJ_TYPE_WALL, 1700, "walls", "walls", "mgw", "game/pro_wall.msg", 0x03000082),
}
PAD_PROTO = "mgpad.pro"
PAD_ART = "mgpad.frm"
# Preserve the merged ledger: the original slots and padding below slot 400 retain
# their numbers. Later art uses scenery PIDs from 2300 and wall PIDs from 2100.
# Reserved slots name mgpad.frm / mgpad.pro without owning a file; walkers skip them.
# V2_FIRST_SLOT is the historical boundary name, not a separate active art tree.
V2_FIRST_SLOT = {"scenery": 400, "wall": 400}
BLOCKER_PID = 0x02000043            # stock "Secret Blocking Hex": invisible, blocks movement only
SCENERY_GENERIC = 5


@contextlib.contextmanager
def locked_manifest():
    """Serialize author updates with a portable exclusive lock directory."""
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    lock = MANIFEST + ".lock-directory"
    try:
        os.mkdir(lock)
    except FileExistsError:
        raise RuntimeError("Another art author holds the manifest lock. After an interrupted author job, preserve the lock directory only when all authors have stopped.") from None
    try:
        manifest = load_manifest()
        yield manifest
        temporary = MANIFEST + ".tmp"
        with open(temporary, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(manifest, stream, separators=(",", ":"))
            stream.write("\n")
        os.replace(temporary, MANIFEST)
    finally:
        os.rmdir(lock)


def reserve_v2(manifest):
    """Pad both slot lists with reserved slots up to V2_FIRST_SLOT (idempotent). Returns slots added."""
    added = 0
    for kind, first in V2_FIRST_SLOT.items():
        slots = manifest["slots"][kind]
        while len(slots) < first:
            slots.append({"key": f"reserved/megaton-art/{len(slots)}", "reserved": True, "retired": True})
            added += 1
    manifest["v2"] = {
        "about": "Working copy of mod/megaton-art for the density pass. Slots below first_slot belong to "
                 "mod/megaton-art (copied as they were, the rest reserved); new pieces start at first_slot.",
        "first_slot": dict(V2_FIRST_SLOT),
        "first_pid": {kind: f"0x{ids.make_pid(KINDS[kind][0], KINDS[kind][1] + first):08X}"
                      for kind, first in V2_FIRST_SLOT.items()},
        "first_pid_index": {kind: KINDS[kind][1] + first for kind, first in V2_FIRST_SLOT.items()},
    }
    return added


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            manifest = json.load(f)
        reserve_v2(manifest)
        return manifest
    return {
        "version": 1,
        "about": "Megaton art mod: every PID / art index it claims. Edited only by build.py (pipeline/data.py).",
        "ids": {kind: {"first_pid": f"0x{ids.make_pid(spec[0], spec[1]):08X}", "pid_index": spec[1]}
                for kind, spec in KINDS.items()},
        "slots": {"scenery": [], "wall": []},
        "pieces": {},
    }


def slot_ids(gf_stock, kind, slot):
    obj_type, first_pid, art_dir, proto_dir, prefix, _, _ = KINDS[kind]
    art_first = len(gf_stock.art_list(obj_type))
    return {
        "pid": ids.make_pid(obj_type, first_pid + slot),
        "fid": ids.make_fid(obj_type, art_first + slot),
        "frm": f"{prefix}{slot:04d}.frm",
        "pro": f"{prefix}{slot:04d}.pro",
        "art_path": f"art/{art_dir}/{prefix}{slot:04d}.frm",
        "pro_path": f"proto/{proto_dir}/{prefix}{slot:04d}.pro",
    }


def register(manifest, result, script, gf_stock):
    """Give every part of a processed piece its slot and write the piece's manifest entry."""
    name = result["name"]
    spec = result["spec"]
    live = set()
    entries = []
    for part in result["parts"]:
        kind = part["type"]
        key = f"{name}/{part['layer']}/{part['hex'][0]},{part['hex'][1]}"
        slots = manifest["slots"][kind]
        index = next((i for i, slot in enumerate(slots) if slot["key"] == key), None)
        if index is None:
            index = len(slots)
            slots.append({"key": key})
        slots[index].pop("retired", None)
        live.add((kind, index))
        numbers = slot_ids(gf_stock, kind, index)
        part["slot"] = index
        part["ids"] = numbers
        entries.append({
            "layer": part["layer"], "hex": list(part["hex"]), "type": kind, "slot": index,
            "pid": f"0x{numbers['pid']:08X}", "fid": f"0x{numbers['fid']:08X}", "frm": numbers["frm"],
            "shift": list(part["shift"]), "size": list(part["size"]), "frames": len(part["frames"]),
            "flags": f"0x{part['flags'] & 0xFFFFFFFF:08X}", "flags_ext": f"0x{part['flags_ext'] & 0xFFFFFFFF:08X}",
            "blocking": bool(part["blocking"]), "flat": bool(part["flags"] & piece_module.FLAT),
            "light": part["light"], "script": part["script"], "material": int(part["material"]),
        })
    for kind, slots in manifest["slots"].items():
        for index, slot in enumerate(slots):
            if slot["key"].split("/")[0] == name and (kind, index) not in live:
                slot["retired"] = True
    manifest["pieces"][name] = {
        "script": script, "kind": spec["kind"], "title": spec["title"], "desc": spec["desc"],
        "origin": "hex with even hx and even hy; part hexes are (dhx, dhy) from it",
        "footprint": result["footprint"], "blockers": result["blockers"], "blocker_pid": f"0x{BLOCKER_PID:08X}",
        "canvas": list(result["canvas"]), "frames": int(spec["frames"]), "fps": int(spec["fps"]),
        "shadow": spec["shadow"], "see_through": spec["see_through"], "sight": spec["sight"],
        "light": spec["light"],
        "anchor_rule": ("explicit list of hexes: every pixel on the nearest" if spec["anchors"] != "auto" else
                        f"auto: every pixel on the nearest blocked hex at or behind the surface it shows; beyond "
                        f"{spec['overhang']} m from all of them on the nearest hex at or in front (non-blocking part)"),
        "part_shift": "FRM x/y offset of all six directions; the engine puts the frame's bottom-centre pixel on "
                      "(hex x + 16 + shift x, hex y + 8 + shift y)",
        "parts": entries,
        "report": result["report"],
    }
    return manifest["pieces"][name]


def _blank_frm():
    frm = Frm()
    frm.stored = [[Frame(1, 1, b"\x00")]]
    frm.direction_map = [0] * 6
    return frm.to_bytes()


def write_part_files(part, out_dir=OUT):
    numbers = part["ids"]
    _write(out_dir, numbers["art_path"], piece_module.part_frm(part).to_bytes())


def _write(out_dir, relative, data):
    path = os.path.join(out_dir, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def write_data(manifest, out_dir=OUT):
    """Protos, lists and message files for every slot in the manifest (FRMs are written per piece)."""
    gf = GameFiles()                                # stock tree: lists are rebuilt from scratch every time
    blank = _blank_frm()
    for kind, (obj_type, first_pid, art_dir, proto_dir, prefix, msg_file, clone_pid) in KINDS.items():
        slots = manifest["slots"][kind]
        parts = {}
        for name, piece in manifest["pieces"].items():
            for part in piece["parts"]:
                if part["type"] == kind:
                    parts[part["slot"]] = (piece, part)
        stock_art = gf.read(f"art/{art_dir}/{art_dir}.lst")
        stock_proto = gf.read(f"proto/{proto_dir}/{proto_dir}.lst")
        stock_count = len(lst.proto_names(stock_proto))
        if stock_count >= first_pid:
            raise SystemExit(f"{proto_dir}.lst already has {stock_count} lines: PID {first_pid} is taken")
        art_lines, proto_lines, texts = [], [PAD_PROTO] * (first_pid - 1 - stock_count), {}
        source = gf.protos.get(clone_pid)
        for index, slot in enumerate(slots):
            numbers = slot_ids(gf, kind, index)
            if slot.get("reserved"):                    # mod/megaton-art's own future slots: a line, no files
                art_lines.append(PAD_ART)
                proto_lines.append(PAD_PROTO)
                continue
            art_lines.append(numbers["frm"])
            proto_lines.append(numbers["pro"])
            pid_index = first_pid + index
            fields = dict(pid=numbers["pid"], message_id=pid_index * 100, fid=numbers["fid"], sid=-1,
                          light_distance=0, light_intensity=0, flags=0, flags_ext=0x2000)
            if index in parts and not slot.get("retired"):
                piece, part = parts[index]
                fields.update(flags=int(part["flags"], 16), flags_ext=int(part["flags_ext"], 16),
                              light_distance=part["light"][0], light_intensity=part["light"][1],
                              material=part.get("material", 1))
                texts[pid_index * 100] = piece["title"]
                texts[pid_index * 100 + 1] = piece["desc"]
            else:
                fields.update(flags=0xA0008018)         # retired: flat, walk-through, never drawn (1x1 empty)
                _write(out_dir, numbers["art_path"], blank)
                texts[pid_index * 100] = "Nothing"
                texts[pid_index * 100 + 1] = "There is nothing here."
            if kind == "scenery":
                fields.update(sub_type=SCENERY_GENERIC, sound_id=source.sound_id)
            _write(out_dir, numbers["pro_path"], source.copy(**fields).to_bytes())
        _write(out_dir, f"art/{art_dir}/{art_dir}.lst", lst.append_lines(stock_art, art_lines))
        _write(out_dir, f"proto/{proto_dir}/{proto_dir}.lst", lst.append_lines(stock_proto, proto_lines))
        pad = source.copy(pid=ids.make_pid(obj_type, stock_count + 1), fid=source.fid).to_bytes()
        _write(out_dir, f"proto/{proto_dir}/{PAD_PROTO}", pad)
        _write(out_dir, f"art/{art_dir}/{PAD_ART}", blank)
        _write(out_dir, f"text/english/{msg_file}", msg.append_entries(gf.read(f"text/english/{msg_file}"), texts))


def pack(out_dir=OUT, patch=PATCH):
    """out/ (game paths) -> out/patch-art.dat. Returns the number of members."""
    files = {}
    for top in ("art", "proto", "text"):
        base = os.path.join(out_dir, top)
        for root, dirs, names in os.walk(base):
            dirs.sort()
            for name in sorted(names):
                if name.startswith("."):
                    continue
                full = os.path.join(root, name)
                with open(full, "rb") as f:
                    files[os.path.relpath(full, out_dir).replace(os.sep, "\\")] = f.read()
    return write_dat2(files, patch)


def verify(manifest, out_dir=OUT):
    """Read everything back the way the engine will (through an overlay) and check the numbers."""
    gf = GameFiles(overlay=out_dir)
    problems = []
    for name, piece in manifest["pieces"].items():
        for part in piece["parts"]:
            pid, fid = int(part["pid"], 16), int(part["fid"], 16)
            try:
                proto = gf.protos.get(pid)
            except Exception as error:          # noqa: BLE001 - any failure is a finding
                problems.append(f"{name}: proto {part['pid']} unreadable ({error})")
                continue
            if proto.pid != pid or proto.fid != fid:
                problems.append(f"{name}: proto {part['pid']} holds pid 0x{proto.pid:08X} fid 0x{proto.fid:08X}")
            try:
                frm = gf.art.load(fid)
            except Exception as error:          # noqa: BLE001
                problems.append(f"{name}: art {part['fid']} ({part['frm']}) unreadable ({error})")
                continue
            if list(frm.size(0, 0)) != part["size"] or list(frm.shift(0)) != part["shift"]:
                problems.append(f"{name}: {part['frm']} is {frm.size(0, 0)} shift {frm.shift(0)}, manifest says "
                                f"{part['size']} {part['shift']}")
            if gf.protos.name(pid) != piece["title"]:
                problems.append(f"{name}: {part['pid']} is named {gf.protos.name(pid)!r}")
    return problems
