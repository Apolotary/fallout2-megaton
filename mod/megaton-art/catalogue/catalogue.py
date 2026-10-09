#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Catalogue of the Megaton art mod: verification of every manifest entry, totals, contact sheets.

    python3 mod/megaton-art/catalogue/catalogue.py            verify, totals, contact sheets (a few seconds;
                                                              exit status 1 when anything is inconsistent)

Read-only on everything but this directory. Writes:

    catalogue/verify.txt          every check that ran, every inconsistency found (empty list = clean), totals
    catalogue/catalogue.json      per piece and per sprite data (PIDs, FIDs, sizes, bytes), totals, problems
    catalogue/sheet-<group>-NN.png  labelled contact sheets at 2x, grouped by author
    catalogue/best/*.png          the six engine screenshots (copied from stage/town/shots, table BEST below)

WHAT IS CHECKED (manifest.json is the claim, out/ is what was built):
  ids       slot i <-> PID 0x02000000|(1900+i) / 0x03000000|(1700+i), FID = stock art lines + i; no PID or FID or
            FRM name used twice; every PID above the stock proto count and inside the claimed block; no scenery
            or wall PID of the town mod (mod/megaton/registry.py claims item PIDs only)
  slots     each live slot has exactly one part and its key matches the part; each retired slot has none and
            is an empty 1x1 sprite with the retired proto flags; no file in out/ that no slot owns
  FRMs      exists, decodes with f2lib, one direction, same x/y shift in all six directions, size / shift /
            frame count equal the manifest, fps equals the piece's, palette indices only 0..254, not blank
  protos    exists, parses, PID / FID / flags / flags_ext / light / material equal the manifest, message id =
            PID index * 100, no script id, blocking and flat flags agree with the manifest booleans
  text      pro_scen.msg / pro_wall.msg hold the piece's title at id*100 and description at id*100+1; stock
            entries are untouched
  lists     art and proto .lst files start with the stock lines byte for byte, ours are appended, padding
            lines name mgpad.pro, line numbers match the slot numbers
  footprint every piece has footprint / blockers / canvas; footprint == hexes of blocking parts + blockers
  patch     patch-art.dat holds exactly the files under out/, byte for byte
  placement placement.json names only manifest pieces and agrees on the verdict
"""
import collections
import json
import os
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)

from f2lib import Dat2, GameFiles, ids, lst, msg                 # noqa: E402
from f2lib.frm import Frm                                       # noqa: E402
from f2lib.pro import Proto                                     # noqa: E402
from pipeline import proj as P                                  # noqa: E402

OUT = os.path.join(ART, "out")
MANIFEST = os.path.join(ART, "manifest.json")
PLACEMENT = os.path.join(ART, "placement.json")
PATCH = os.path.join(OUT, "patch-art.dat")

KINDS = {   # kind: (obj type, first pid index, art dir, proto dir, file prefix, msg file)
    "scenery": (ids.OBJ_TYPE_SCENERY, 1900, "scenery", "scenery", "mgs", "game/pro_scen.msg"),
    "wall": (ids.OBJ_TYPE_WALL, 1700, "walls", "walls", "mgw", "game/pro_wall.msg"),
}
RETIRED_FLAGS = 0xA0008018
BLOCKER_PID = 0x02000043
NO_BLOCK, FLAT = 0x10, 0x08

# "authors": the three asset authors plus the pipeline stage's own demos (script directory decides)
GROUPS = [
    ("gate", "GATE SET", "pieces/gate/*  (prefix mg_)  gate, wing, door, sign, walls of wrecks and containers, poles, wires"),
    ("bomb", "BOMB, SHRINE, RIM AND POOL", "pieces/bomb/*  (prefix mgb_)  the bomb and its states, shrine dressing, crater rim, rails, pool shore"),
    ("signs", "SIGNS, LIGHTS, DRESSING AND ROOFS", "pieces/signs/*  (prefix sg_)  shop signs, bulb strings, awnings, junk, roof furniture"),
    ("pipeline", "PIPELINE DEMOS (ALL CUT)", "pieces/demo_*.py  (prefix mgt_)  the pipeline stage's own test pieces"),
]


# Six engine screenshots (real Fallout 2 engine, review map, stage/town/shots) that show the work best:
# destination name -> source file name in stage/town/shots
BEST = [
    ("01-gate-megaton-sign-day-1280x960.png", "day-01-gate.png"),
    ("02-gate-megaton-sign-night-1280x960.png", "night-01-gate.png"),
    ("03-crater-bomb-shrine-day-1280x960.png", "day-06-crater.png"),
    ("04-crater-bomb-shrine-night-1280x960.png", "night-06-crater.png"),
    ("05-gate-and-crater-overview-day-1280x960.png", "day-04-inside-gate.png"),
    ("06-gate-phone-window-day-1040x480.png", "phone-day-01-gate.png"),
]


def group_of(script):
    if script.startswith("pieces/gate/"):
        return "gate"
    if script.startswith("pieces/bomb/"):
        return "bomb"
    if script.startswith("pieces/signs/"):
        return "signs"
    return "pipeline"


class Checker:
    def __init__(self):
        self.problems = []
        self.notes = []
        self.ran = []

    def check(self, what):
        self.ran.append(what)

    def problem(self, text):
        self.problems.append(text)

    def note(self, text):
        self.notes.append(text)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def read(path):
    with open(path, "rb") as f:
        return f.read()


# ====================================================================== verification
def verify():
    manifest = load_json(MANIFEST)
    pieces = manifest["pieces"]
    chk = Checker()
    gf_stock = GameFiles()                      # the stock tree, no overlay
    info = {}
    for kind, (obj_type, first, art_dir, proto_dir, prefix, msg_file) in KINDS.items():
        art_stock = lst.split_lines(gf_stock.read(f"art/{art_dir}/{art_dir}.lst"))
        proto_stock = lst.split_lines(gf_stock.read(f"proto/{proto_dir}/{proto_dir}.lst"))
        info[kind] = dict(art_first=len(art_stock), proto_stock=len(proto_stock), first=first,
                          art_stock=art_stock, proto_stock_lines=proto_stock,
                          slots=manifest["slots"][kind])

    # ------------------------------------------------------------- manifest header
    chk.check("manifest ids block")
    for kind, (obj_type, first, *_rest) in KINDS.items():
        claimed = manifest["ids"][kind]
        if claimed["pid_index"] != first:
            chk.problem(f"manifest ids.{kind}.pid_index is {claimed['pid_index']}, the assigned range starts at {first}")
        if int(claimed["first_pid"], 16) != ids.make_pid(obj_type, first):
            chk.problem(f"manifest ids.{kind}.first_pid {claimed['first_pid']} is not 0x{ids.make_pid(obj_type, first):08X}")
        if info[kind]["proto_stock"] >= first:
            chk.problem(f"{kind}: stock proto list has {info[kind]['proto_stock']} lines, PID {first} is not free")

    # ------------------------------------------------------------- slot <-> part table
    chk.check("slot table and part references")
    owner = {}                                  # (kind, slot) -> (piece, part)
    for name, piece in pieces.items():
        for part in piece["parts"]:
            key = (part["type"], part["slot"])
            if key in owner:
                chk.problem(f"{name}: slot {part['type']}#{part['slot']} is also owned by {owner[key][0]}")
            owner[key] = (name, part)
    seen_pid, seen_fid, seen_frm = {}, {}, {}
    for name, piece in pieces.items():
        if piece["kind"] != "wall" and piece["kind"] != "scenery":
            chk.problem(f"{name}: unknown kind {piece['kind']!r}")
        for part in piece["parts"]:
            kind, slot = part["type"], part["slot"]
            if kind not in KINDS:
                chk.problem(f"{name}: part type {kind!r}")
                continue
            slots = info[kind]["slots"]
            if not 0 <= slot < len(slots):
                chk.problem(f"{name}/{part['layer']}: slot {slot} is outside the {kind} slot table (0..{len(slots) - 1})")
                continue
            expect_key = f"{name}/{part['layer']}/{part['hex'][0]},{part['hex'][1]}"
            if slots[slot]["key"] != expect_key:
                chk.problem(f"{name}: slot {kind}#{slot} is keyed {slots[slot]['key']!r}, the part is {expect_key!r}")
            if slots[slot].get("retired"):
                chk.problem(f"{name}: part {part['frm']} sits on slot {kind}#{slot} which is marked retired")
            if part["type"] != piece["kind"]:
                chk.note(f"{name}: a {part['type']}-type part ({part['layer']} {part['frm']}) inside a {piece['kind']} piece")
            obj_type, first, art_dir, proto_dir, prefix, _ = KINDS[kind]
            want_pid = ids.make_pid(obj_type, first + slot)
            want_fid = ids.make_fid(obj_type, info[kind]["art_first"] + slot)
            want_frm = f"{prefix}{slot:04d}.frm"
            if int(part["pid"], 16) != want_pid:
                chk.problem(f"{name}: {part['frm']} PID {part['pid']} should be 0x{want_pid:08X} for slot {slot}")
            if int(part["fid"], 16) != want_fid:
                chk.problem(f"{name}: {part['frm']} FID {part['fid']} should be 0x{want_fid:08X} for slot {slot}")
            if part["frm"] != want_frm:
                chk.problem(f"{name}: slot {slot} FRM is named {part['frm']}, expected {want_frm}")
            for table, value, label in ((seen_pid, part["pid"], "PID"), (seen_fid, part["fid"], "FID"),
                                        (seen_frm, f"{kind}/{part['frm']}", "FRM name")):
                if value in table:
                    chk.problem(f"{label} {value} used by both {table[value]} and {name}/{part['layer']}")
                table[value] = f"{name}/{part['layer']}"
    for kind, data in info.items():
        for slot, entry in enumerate(data["slots"]):
            if entry.get("retired"):
                if (kind, slot) in owner:
                    chk.problem(f"retired {kind}#{slot} ({entry['key']}) is owned by {owner[(kind, slot)][0]}")
            elif (kind, slot) not in owner:
                chk.problem(f"live {kind}#{slot} ({entry['key']}) belongs to no part of any piece")
            else:
                if entry["key"].split("/")[0] not in pieces:
                    chk.problem(f"live {kind}#{slot} keyed {entry['key']!r} names no manifest piece")

    # ------------------------------------------------------------- PID ranges
    chk.check("PID ranges and collisions")
    for kind, data in info.items():
        obj_type, first = KINDS[kind][0], KINDS[kind][1]
        top = first + len(data["slots"]) - 1
        for key, (name, part) in sorted(owner.items()):
            if key[0] != kind:
                continue
            index = ids.pid_index(int(part["pid"], 16))
            if not (first <= index <= top):
                chk.problem(f"{name}: {part['pid']} (index {index}) outside the claimed block {first}..{top}")
            if index <= data["proto_stock"]:
                chk.problem(f"{name}: {part['pid']} (index {index}) collides with the stock protos 1..{data['proto_stock']}")
        if first > 1900 and kind == "scenery" or first > 1700 and kind == "wall":
            chk.problem(f"{kind}: block starts at {first}")
    # the town mod's claims (read only)
    town_registry = os.path.join(ROOT, "mod", "megaton", "registry.py")
    if os.path.exists(town_registry):
        text = open(town_registry).read()
        for token in ("proto/scenery", "proto/walls", "art/scenery", "art/walls"):
            if token in text:
                chk.note(f"mod/megaton/registry.py mentions {token}: compare ranges by hand")
        town_out = os.path.join(ROOT, "mod", "megaton", "out", "proto")
        for sub in ("scenery", "walls"):
            if os.path.isdir(os.path.join(town_out, sub)):
                chk.problem(f"the town mod's out/proto has a {sub} directory: PID overlap must be checked")

    # ------------------------------------------------------------- message files
    chk.check("names and descriptions in pro_scen.msg / pro_wall.msg")
    messages = {}
    for kind, (obj_type, first, art_dir, proto_dir, prefix, msg_file) in KINDS.items():
        built = msg.parse(read(os.path.join(OUT, "text", "english", msg_file)))
        stock = msg.parse(gf_stock.read(f"text/english/{msg_file}"))
        messages[kind] = built
        for number, value in stock.items():
            if built.get(number) != value:
                chk.problem(f"{msg_file}: stock entry {number} changed or missing")
        stock_top = max(stock)
        ours = {n for n in built if n not in stock}
        if min(ours, default=10 ** 9) <= stock_top:
            chk.problem(f"{msg_file}: one of our ids is not above the stock ids (top stock id {stock_top})")
        expected_ids = set()
        for slot, entry in enumerate(info[kind]["slots"]):
            base = (first + slot) * 100
            expected_ids.update((base, base + 1))
            if base not in built or base + 1 not in built:
                chk.problem(f"{msg_file}: slot {slot} lacks ids {base} / {base + 1}")
        extra = ours - expected_ids
        if extra:
            chk.problem(f"{msg_file}: {len(extra)} entries belong to no slot: {sorted(extra)[:6]}")

    # ------------------------------------------------------------- per part files
    chk.check("FRM files decode, re-encode byte for byte, and match the manifest")
    chk.check("PRO files parse and match the manifest")
    sprites = []
    frm_paths, pro_paths = set(), set()
    for kind, (obj_type, first, art_dir, proto_dir, prefix, msg_file) in KINDS.items():
        for slot, entry in enumerate(info[kind]["slots"]):
            frm_name, pro_name = f"{prefix}{slot:04d}.frm", f"{prefix}{slot:04d}.pro"
            frm_path = os.path.join(OUT, "art", art_dir, frm_name)
            pro_path = os.path.join(OUT, "proto", proto_dir, pro_name)
            frm_paths.add(frm_path)
            pro_paths.add(pro_path)
            owner_entry = owner.get((kind, slot))
            label = f"{kind}#{slot} {entry['key']}"
            retired = bool(entry.get("retired"))
            piece_name, part = owner_entry if owner_entry else (None, None)
            try:
                frm_raw = read(frm_path)
                frm = Frm.from_bytes(frm_raw)
            except FileNotFoundError:
                chk.problem(f"{label}: {frm_path} does not exist")
                frm = frm_raw = None
            except Exception as error:      # noqa: BLE001
                chk.problem(f"{label}: {frm_name} does not decode ({error})")
                frm = frm_raw = None
            try:
                pro_raw = read(pro_path)
                proto = Proto.from_bytes(pro_raw)
            except FileNotFoundError:
                chk.problem(f"{label}: {pro_path} does not exist")
                proto = pro_raw = None
            except Exception as error:      # noqa: BLE001
                chk.problem(f"{label}: {pro_name} does not parse ({error})")
                proto = pro_raw = None
            want_pid = ids.make_pid(obj_type, first + slot)
            want_fid = ids.make_fid(obj_type, info[kind]["art_first"] + slot)
            record = dict(kind=kind, slot=slot, key=entry["key"], retired=retired, frm=frm_name, pro=pro_name,
                          pid=want_pid, fid=want_fid, frm_bytes=len(frm_raw) if frm_raw else 0,
                          pro_bytes=len(pro_raw) if pro_raw else 0, piece=piece_name)
            if proto is not None:
                if proto.pid != want_pid:
                    chk.problem(f"{label}: {pro_name} holds PID 0x{proto.pid:08X}, expected 0x{want_pid:08X}")
                if proto.fid != want_fid:
                    chk.problem(f"{label}: {pro_name} holds FID 0x{proto.fid:08X}, expected 0x{want_fid:08X}")
                if proto.message_id != (first + slot) * 100:
                    chk.problem(f"{label}: {pro_name} message id {proto.message_id}, expected {(first + slot) * 100}")
                if proto.sid != -1:
                    chk.problem(f"{label}: {pro_name} carries script id {proto.sid}")
                if kind == "scenery" and proto.sub_type != 5:
                    chk.problem(f"{label}: scenery proto sub type {proto.sub_type} (expected 5, generic)")
            if frm is not None:
                if frm.to_bytes() != frm_raw:
                    chk.problem(f"{label}: {frm_name} does not re-encode to the same bytes (non-canonical header or size)")
                if frm.version != 4 or frm.action_frame >= max(1, frm.frame_count):
                    chk.problem(f"{label}: {frm_name} header version {frm.version}, action frame {frm.action_frame} of {frm.frame_count}")
                if frm.direction_count != 1:
                    chk.problem(f"{label}: {frm_name} stores {frm.direction_count} directions (expected 1)")
                if len(set(frm.x_offsets)) != 1 or len(set(frm.y_offsets)) != 1:
                    chk.problem(f"{label}: {frm_name} header shift differs between directions "
                                f"{frm.x_offsets} {frm.y_offsets}")
                w, h = frm.size(0, 0)
                record.update(width=w, height=h, frames=frm.frame_count, fps=frm.fps,
                              shift=list(frm.shift(0)))
                allpix = np.concatenate([np.frombuffer(f.pixels, np.uint8) for f in frm.frames(0)])
                record["opaque"] = int((allpix > 0).sum())
                record["pixels"] = int(allpix.size)
                record["animated_index_pixels"] = int(((allpix >= 229) & (allpix <= 254)).sum())
                record["index_255_pixels"] = int((allpix == 255).sum())
                if retired:
                    if (w, h) != (1, 1) or frm.frame_count != 1 or record["opaque"]:
                        chk.problem(f"{label}: retired slot is not an empty 1x1 sprite ({w}x{h}, {frm.frame_count} frames, "
                                    f"{record['opaque']} opaque)")
                    if proto is not None and (proto.flags & 0xFFFFFFFF) != RETIRED_FLAGS:
                        chk.problem(f"{label}: retired proto flags 0x{proto.flags & 0xFFFFFFFF:08X}, expected 0x{RETIRED_FLAGS:08X}")
                    if messages[kind].get((first + slot) * 100, ("", ""))[1] != "Nothing":
                        chk.problem(f"{label}: retired slot has the name {messages[kind].get((first + slot) * 100)!r}")
                elif part is not None:
                    piece = pieces[piece_name]
                    if [w, h] != part["size"]:
                        chk.problem(f"{piece_name}/{part['layer']} {frm_name}: sprite is {w}x{h}, manifest says {part['size']}")
                    if list(frm.shift(0)) != part["shift"]:
                        chk.problem(f"{piece_name}/{part['layer']} {frm_name}: shift {list(frm.shift(0))}, manifest says {part['shift']}")
                    if frm.frame_count != part["frames"]:
                        chk.problem(f"{piece_name}/{part['layer']} {frm_name}: {frm.frame_count} frames, manifest says {part['frames']}")
                    if part["frames"] != piece["frames"]:
                        chk.note(f"{piece_name}/{part['layer']} {frm_name}: {part['frames']} frame(s) while the piece declares {piece['frames']}")
                    if part["frames"] > 1 and frm.fps != piece["fps"]:
                        chk.problem(f"{piece_name}/{part['layer']} {frm_name}: FRM fps {frm.fps}, piece fps {piece['fps']}")
                    if record["opaque"] == 0:
                        chk.problem(f"{piece_name}/{part['layer']} {frm_name}: sprite is entirely transparent")
                    if any(f.width != w or f.height != h for f in frm.frames(0)):
                        chk.problem(f"{piece_name}/{part['layer']} {frm_name}: frames differ in size")
                    if record["index_255_pixels"]:
                        chk.note(f"{piece_name}/{part['layer']} {frm_name}: {record['index_255_pixels']} pixels use palette index 255")
                    if (w, h) == (1, 1):
                        chk.note(f"{piece_name}/{part['layer']} {frm_name}: a live part that is a single pixel")
            if proto is not None and part is not None and not retired:
                piece = pieces[piece_name]
                want = (("flags", int(part["flags"], 16)), ("flags_ext", int(part["flags_ext"], 16)),
                        ("light_distance", part["light"][0]), ("light_intensity", part["light"][1]),
                        ("material", part["material"]))
                for field, value in want:
                    got = getattr(proto, field)
                    if field.startswith("flags"):
                        got &= 0xFFFFFFFF
                        if got != value:
                            chk.problem(f"{piece_name}/{part['layer']} {pro_name}: {field} is 0x{got:08X}, manifest says 0x{value:08X}")
                    elif got != value:
                        chk.problem(f"{piece_name}/{part['layer']} {pro_name}: {field} is {got}, manifest says {value}")
                blocks_by_flag = not (proto.flags & NO_BLOCK)
                if blocks_by_flag != bool(part["blocking"]):
                    chk.problem(f"{piece_name}/{part['layer']} {pro_name}: flags say blocking={blocks_by_flag}, manifest says {part['blocking']}")
                if bool(proto.flags & FLAT) != bool(part["flat"]):
                    chk.problem(f"{piece_name}/{part['layer']} {pro_name}: flags say flat={bool(proto.flags & FLAT)}, manifest says {part['flat']}")
                title = messages[kind].get((first + slot) * 100, (None, None))[1]
                desc = messages[kind].get((first + slot) * 100 + 1, (None, None))[1]
                if title != piece["title"]:
                    chk.problem(f"{piece_name}: {pro_name} name in the .msg is {title!r}, manifest title {piece['title']!r}")
                if desc != piece["desc"]:
                    chk.problem(f"{piece_name}: {pro_name} description in the .msg is {desc!r}, manifest desc {piece['desc']!r}")
            sprites.append(record)

    # ------------------------------------------------------------- orphans
    chk.check("no file in out/ owned by no slot")
    for kind, (obj_type, first, art_dir, proto_dir, prefix, msg_file) in KINDS.items():
        for base, extension, paths in ((os.path.join(OUT, "art", art_dir), ".frm", frm_paths),
                                       (os.path.join(OUT, "proto", proto_dir), ".pro", pro_paths)):
            for name in sorted(os.listdir(base)):
                full = os.path.join(base, name)
                if name.endswith(extension) and full not in paths:
                    if name == "mgpad.pro":
                        continue
                    chk.problem(f"orphan file out/{os.path.relpath(full, OUT)}")
                elif not name.endswith(extension) and not name.endswith(".lst"):
                    chk.problem(f"unexpected file out/{os.path.relpath(full, OUT)}")

    # ------------------------------------------------------------- lists
    chk.check("art / proto lists: stock prefix intact, ours appended, padding")
    for kind, (obj_type, first, art_dir, proto_dir, prefix, msg_file) in KINDS.items():
        data = info[kind]
        for label, path_in_game, stock_lines, ours in (
                ("art", f"art/{art_dir}/{art_dir}.lst", data["art_stock"], None),
                ("proto", f"proto/{proto_dir}/{proto_dir}.lst", data["proto_stock_lines"], None)):
            built_bytes = read(os.path.join(OUT, *path_in_game.split("/")))
            stock_bytes = gf_stock.read(path_in_game)
            if not built_bytes.startswith(stock_bytes):
                chk.problem(f"{path_in_game}: does not start with the stock file byte for byte")
            built_lines = lst.split_lines(built_bytes)
            if built_lines[:len(stock_lines)] != stock_lines:
                chk.problem(f"{path_in_game}: a stock line changed")
            tail = built_lines[len(stock_lines):]
            if label == "art":
                names = lst.art_names(built_bytes)
                want = [f"{prefix}{slot:04d}.frm" for slot in range(len(data["slots"]))]
                if names[len(stock_lines):] != want:
                    chk.problem(f"{path_in_game}: appended lines are not mgs/mgw slot names in slot order")
                if len(built_lines) != data["art_first"] + len(data["slots"]):
                    chk.problem(f"{path_in_game}: {len(built_lines)} lines, expected {data['art_first'] + len(data['slots'])}")
            else:
                names = lst.proto_names(built_bytes)
                pad = first - 1 - data["proto_stock"]
                if names[len(stock_lines):len(stock_lines) + pad] != ["mgpad.pro"] * pad:
                    chk.problem(f"{path_in_game}: the {pad} padding lines are not all mgpad.pro")
                want = [f"{prefix}{slot:04d}.pro" for slot in range(len(data["slots"]))]
                if names[len(stock_lines) + pad:] != want:
                    chk.problem(f"{path_in_game}: appended lines are not slot names in slot order")
                for slot in range(len(data["slots"])):
                    if names[first - 1 + slot:first + slot] != [want[slot]]:
                        chk.problem(f"{path_in_game}: line {first + slot} is not {want[slot]}")
                        break
    pad_path = os.path.join(OUT, "proto", "scenery", "mgpad.pro")
    for kind, (obj_type, first, art_dir, proto_dir, *_r) in KINDS.items():
        pad = Proto.from_bytes(read(os.path.join(OUT, "proto", proto_dir, "mgpad.pro")))
        if ids.pid_type(pad.pid) != obj_type:
            chk.problem(f"proto/{proto_dir}/mgpad.pro has PID type {ids.pid_type(pad.pid)}")

    # ------------------------------------------------------------- piece records
    chk.check("piece records: title, description, footprint, blockers, canvas, verdict")
    verdicts = collections.Counter()
    for name, piece in pieces.items():
        for field in ("title", "desc", "footprint", "blockers", "canvas", "parts", "verdict", "script", "frames", "fps"):
            if field not in piece:
                chk.problem(f"{name}: manifest field {field!r} missing")
        if not piece.get("title", "").strip() or not piece.get("desc", "").strip():
            chk.problem(f"{name}: empty title or description")
        if len(piece.get("canvas", [])) != 4:
            chk.problem(f"{name}: canvas {piece.get('canvas')}")
        if piece.get("verdict") not in ("upgrade", "acceptable", "cut"):
            chk.problem(f"{name}: verdict {piece.get('verdict')!r}")
        verdicts[piece.get("verdict")] += 1
        if not os.path.exists(os.path.join(ART, piece["script"])):
            chk.problem(f"{name}: builder script {piece['script']} does not exist")
        fp = {tuple(h) for h in piece["footprint"]}
        blockers = {tuple(h) for h in piece["blockers"]}
        blocking = {tuple(p["hex"]) for p in piece["parts"] if p["blocking"]}
        if fp != (blocking | blockers):
            chk.problem(f"{name}: footprint {sorted(fp)} != blocking part hexes {sorted(blocking)} + blockers {sorted(blockers)}")
        if len(piece["footprint"]) != len(fp):
            chk.problem(f"{name}: footprint lists a hex twice")
        if blockers & blocking:
            chk.problem(f"{name}: blockers {sorted(blockers & blocking)} also carry a blocking part")
        if not fp:
            chk.note(f"{name}: empty footprint (walk-through piece)")
        if piece["blocker_pid"] != f"0x{BLOCKER_PID:08X}":
            chk.problem(f"{name}: blocker_pid {piece['blocker_pid']}")
        if not piece["parts"]:
            chk.problem(f"{name}: no parts")
        keys = [(p["layer"], tuple(p["hex"])) for p in piece["parts"]]
        if len(keys) != len(set(keys)):
            chk.problem(f"{name}: two parts on the same layer and hex")
        if piece["parts"] and not any(p["layer"] == "main" for p in piece["parts"]):
            chk.problem(f"{name}: no main part")
        for p in piece["parts"]:
            if p["script"]:
                chk.note(f"{name}/{p['layer']} {p['frm']}: part declares script {p['script']!r}")
        if piece["report"].get("warnings"):
            chk.note(f"{name}: build warnings {piece['report']['warnings']}")
        if piece["report"].get("reassembly") != "exact":
            chk.problem(f"{name}: reassembly check is {piece['report'].get('reassembly')!r}")
    # canvas, engine reach and light
    chk.check("canvas holds every non-halo sprite; engine repaint reach (300 px sideways, 224 up, 200 down); light record")
    for name, piece in pieces.items():
        x0, y0, x1, y1 = piece["canvas"]
        lit = [p for p in piece["parts"] if p["light"] != [0, 0]]
        for part in piece["parts"]:
            w, h = part["size"]
            hx, hy = P.hex_px(*part["hex"])
            left, top = hx + part["shift"][0] - w // 2, hy + part["shift"][1] - (h - 1)
            if part["layer"] != "halo" and (left < x0 or top < y0 or left + w > x1 or top + h > y1):
                chk.problem(f"{name}/{part['layer']} {part['frm']}: sprite box {(left, top, left + w, top + h)} leaves the piece canvas {piece['canvas']}")
            reach_left, reach_right = part["shift"][0] - w // 2, part["shift"][0] - w // 2 + w
            reach_up, reach_down = h - 1 - part["shift"][1], part["shift"][1]
            if (max(abs(reach_left), abs(reach_right)) > P.MAX_REACH_X or reach_up > P.MAX_REACH_UP
                    or reach_down > P.MAX_REACH_DOWN):
                chk.problem(f"{name}/{part['layer']} {part['frm']}: reaches {reach_left}..{reach_right} px sideways, {reach_up} up, "
                            f"{reach_down} down from its hex (engine limits {P.MAX_REACH_X} / {P.MAX_REACH_UP} / {P.MAX_REACH_DOWN})")
        if piece["light"]:
            distance, percent = piece["light"]
            if len(lit) != 1:
                chk.problem(f"{name}: light {piece['light']} declared but {len(lit)} parts carry light")
            for part in lit:
                if part["light"] != [distance, round(65536 * percent / 100)]:
                    chk.problem(f"{name}/{part['layer']} {part['frm']}: part light {part['light']} != piece light {piece['light']} "
                                f"({distance}, {round(65536 * percent / 100)})")
        elif lit:
            chk.problem(f"{name}: no light declared but {[p['frm'] for p in lit]} carry light")
    # the 'door_frm' record
    for name, piece in pieces.items():
        if "door_frm" in piece:
            for state in piece["door_frm"]["states"]:
                if state not in pieces and state != "mg_gate_f25" and state != "mg_gate_f75":
                    chk.problem(f"{name}.door_frm names state {state!r} that is not a piece")
            door_part = piece["parts"][0]
            if door_part["frames"] != len(piece["door_frm"]["states"]):
                chk.problem(f"{name}: door FRM has {door_part['frames']} frames, door_frm lists {len(piece['door_frm']['states'])} states")

    # ------------------------------------------------------------- palette animation
    chk.check("palette animation ranges 229..254 only where placement.json declares them")
    placement = load_json(PLACEMENT) if os.path.exists(PLACEMENT) else None
    by_piece_anim = collections.defaultdict(int)
    for rec in sprites:
        if rec["piece"]:
            by_piece_anim[rec["piece"]] += rec.get("animated_index_pixels", 0)
    if placement:
        declared = {n: p.get("palette_animation") for n, p in placement["pieces"].items()}
        for name, count in sorted(by_piece_anim.items()):
            if count and not declared.get(name):
                chk.problem(f"{name}: {count} pixels in the animated palette range 229..254, placement.json declares none")
        for name, anim in sorted(declared.items()):
            if anim and not by_piece_anim.get(name):
                chk.problem(f"{name}: placement.json declares palette animation {anim}, no pixel uses 229..254")

    # ------------------------------------------------------------- placement.json
    chk.check("placement.json agrees with the manifest")
    if placement:
        for name, entry in placement["pieces"].items():
            if name not in pieces:
                chk.problem(f"placement.json names {name!r}, which is not in the manifest")
                continue
            if entry.get("verdict") != pieces[name]["verdict"]:
                chk.problem(f"{name}: placement.json verdict {entry.get('verdict')!r}, manifest {pieces[name]['verdict']!r}")
            if entry.get("script") != pieces[name]["script"]:
                chk.problem(f"{name}: placement.json script {entry.get('script')!r}, manifest {pieces[name]['script']!r}")
            if entry.get("pids") and sorted(entry["pids"]) != sorted(p["pid"] for p in pieces[name]["parts"]):
                chk.note(f"{name}: placement.json lists pids {entry['pids']} which are not all of the manifest's part PIDs "
                         f"(placement lists the parts it places)")
        for name in pieces:
            if name not in placement["pieces"]:
                chk.problem(f"{name} is in the manifest but not in placement.json")
        for placed in placement["placements"]:
            if placed["piece"] not in pieces:
                chk.problem(f"placement of unknown piece {placed['piece']}")
            elif pieces[placed["piece"]]["verdict"] == "cut":
                chk.problem(f"placement.json places {placed['piece']}, whose verdict is cut")
            else:
                own = {p["pid"] for p in pieces[placed["piece"]]["parts"]}
                for part in placed.get("parts", []):
                    if part["pid"] not in own:
                        chk.problem(f"placement of {placed['piece']} uses {part['pid']}, not one of its parts")
        placed_names = {p["piece"] for p in placement["placements"]}
        unplaced = sorted(n for n, p in pieces.items() if p["verdict"] != "cut" and n not in placed_names)
        if unplaced:
            chk.note(f"not placed anywhere in the review map (optional or only reachable by hook): {unplaced}")

    # ------------------------------------------------------------- patch
    chk.check("patch-art.dat holds exactly the files under out/")
    files = {}
    for top in ("art", "proto", "text"):
        for root, dirs, names in os.walk(os.path.join(OUT, top)):
            for name in names:
                if name.startswith("."):
                    continue
                full = os.path.join(root, name)
                files[os.path.relpath(full, OUT).replace(os.sep, "/").lower()] = read(full)
    with Dat2(PATCH) as dat:
        members = {n.lower(): n for n in dat.names()}
        packed = {}
        for lowered, original in members.items():
            packed[lowered] = dat.read(original)
    for lowered in sorted(set(files) - set(packed)):
        chk.problem(f"patch-art.dat lacks {lowered}")
    for lowered in sorted(set(packed) - set(files)):
        chk.problem(f"patch-art.dat holds {lowered}, which is not under out/")
    for lowered in sorted(set(files) & set(packed)):
        if files[lowered] != packed[lowered]:
            chk.problem(f"patch-art.dat member {lowered} differs from out/")
    patch_members = len(packed)
    other = [p for p in os.listdir(OUT) if p not in ("art", "proto", "text", "patch-art.dat")]
    if other:
        chk.problem(f"unexpected entries in out/: {other}")
    newest = max(os.path.getmtime(os.path.join(root, n)) for root, _d, names in os.walk(OUT) for n in names if n != "patch-art.dat")
    if os.path.getmtime(PATCH) + 1 < newest:
        chk.note("patch-art.dat is older than a file under out/ (contents are identical, see the member comparison)")

    # ------------------------------------------------------------- totals
    stock_msg_bytes = {k: len(gf_stock.read(f"text/english/{KINDS[k][5]}")) for k in KINDS}
    stock_lst_bytes = {(k, which): len(gf_stock.read(f"{which}/{KINDS[k][2 if which == 'art' else 3]}/"
                                                    f"{KINDS[k][2 if which == 'art' else 3]}.lst"))
                       for k in KINDS for which in ("art", "proto")}
    lst_delta = sum(len(read(os.path.join(OUT, which, KINDS[k][2 if which == 'art' else 3],
                                          f"{KINDS[k][2 if which == 'art' else 3]}.lst"))) - stock_lst_bytes[(k, which)]
                    for k in KINDS for which in ("art", "proto"))
    msg_delta = sum(len(read(os.path.join(OUT, "text", "english", KINDS[k][5]))) - stock_msg_bytes[k] for k in KINDS)
    live = [r for r in sprites if not r["retired"]]
    retired = [r for r in sprites if r["retired"]]
    cut_names = {n for n, p in pieces.items() if p["verdict"] == "cut"}
    live_not_cut = [r for r in live if r["piece"] not in cut_names]
    pad_bytes = sum(len(read(os.path.join(OUT, "proto", KINDS[k][3], "mgpad.pro"))) for k in KINDS)

    def tally(rows):
        return dict(sprites=len(rows), frames=sum(r.get("frames", 0) for r in rows),
                    frm_bytes=sum(r["frm_bytes"] for r in rows), pro_bytes=sum(r["pro_bytes"] for r in rows),
                    opaque_pixels=sum(r.get("opaque", 0) for r in rows))
    biggest = lambda key: max(live, key=key)          # noqa: E731
    wide, tall, area = (biggest(lambda r: r.get("width", 0)), biggest(lambda r: r.get("height", 0)),
                        biggest(lambda r: r.get("width", 0) * r.get("height", 0)))
    totals = dict(
        pieces=len(pieces), pieces_by_verdict=dict(verdicts), pieces_by_kind=dict(collections.Counter(p["kind"] for p in pieces.values())),
        pieces_by_group=dict(collections.Counter(group_of(p["script"]) for p in pieces.values())),
        slots=dict(scenery=len(info["scenery"]["slots"]), wall=len(info["wall"]["slots"])),
        sprites_live=len(live), sprites_retired=len(retired), sprites_files=len(sprites),
        sprites_live_excluding_cut=len(live_not_cut),
        live=tally(live), live_excluding_cut=tally(live_not_cut), retired=tally(retired),
        animated_sprites=[(r["piece"], r["frm"], r["frames"]) for r in live if r.get("frames", 0) > 1],
        files_in_out=sum(len(names) for _r, _d, names in os.walk(OUT)),
        lst_bytes_added=lst_delta, msg_bytes_added=msg_delta, pad_pro_bytes=pad_bytes,
        patch_bytes=os.path.getsize(PATCH), patch_members=patch_members,
        content_bytes_added=sum(r["frm_bytes"] + r["pro_bytes"] for r in sprites) + pad_bytes + lst_delta + msg_delta,
        content_bytes_added_excluding_cut_and_retired=sum(r["frm_bytes"] + r["pro_bytes"] for r in live_not_cut) + lst_delta + msg_delta,
        largest_width=dict(frm=wide["frm"], piece=wide["piece"], size=[wide.get("width"), wide.get("height")]),
        largest_height=dict(frm=tall["frm"], piece=tall["piece"], size=[tall.get("width"), tall.get("height")]),
        largest_area=dict(frm=area["frm"], piece=area["piece"], size=[area.get("width"), area.get("height")]),
        proto_range=dict(scenery=[1900, 1900 + len(info["scenery"]["slots"]) - 1], wall=[1700, 1700 + len(info["wall"]["slots"]) - 1]),
    )
    return manifest, sprites, chk, totals


# ====================================================================== sheets
FLOOR = (131, 112, 88)
VERDICT_COLOUR = {"upgrade": (110, 200, 120), "acceptable": (235, 190, 90), "cut": (225, 100, 90)}
ORDER = {"shadow": 0, "halo": 1, "main": 2, "glow": 3}
VILLAGER_FID = 0x01000003


def compose(gf, piece, frame):
    """RGB picture of one piece on floor colour for one frame; returns (array, origin px, bbox of opaque px)."""
    boxes = []
    for part in piece["parts"]:
        frm = gf.art.load(int(part["fid"], 16))
        w, h = frm.size(0, 0)
        hx, hy = P.hex_px(*part["hex"])
        boxes.append((part, frm, hx + part["shift"][0] - w // 2, hy + part["shift"][1] - (h - 1), w, h))
    x0, y0 = min(b[2] for b in boxes) - 4, min(b[3] for b in boxes) - 4
    x1, y1 = max(b[2] + b[4] for b in boxes) + 4, max(b[3] + b[5] for b in boxes) + 4
    canvas = np.zeros((y1 - y0, x1 - x0, 3), np.uint8) + np.array(FLOOR, np.uint8)
    solid = np.zeros((y1 - y0, x1 - x0), bool)
    for part, frm, left, top, w, h in sorted(boxes, key=lambda b: (ORDER[b[0]["layer"]], b[0]["hex"][1] * 200 + b[0]["hex"][0])):
        count = frm.frame_count
        pixels = np.frombuffer(frm.frame(0, min(frame, count - 1)).pixels, np.uint8).reshape(h, w)
        target = canvas[top - y0:top - y0 + h, left - x0:left - x0 + w]
        mask = (pixels > 0)
        solid[top - y0:top - y0 + h, left - x0:left - x0 + w] |= mask
        if part["layer"] in ("halo", "glow"):
            mix = (target.astype(np.float32) * 0.6 + np.array([255, 220, 90], np.float32) * 0.4).astype(np.uint8)
            np.copyto(target, mix, where=mask[..., None])
        else:
            np.copyto(target, gf.palette.rgb[pixels], where=mask[..., None])
    return canvas, (-x0, -y0), solid


def extent(solid):
    ys, xs = np.nonzero(solid)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def fonts():
    from PIL import ImageFont
    def load(paths, size):
        for path, index in paths:
            try:
                return ImageFont.truetype(path, size, index=index)
            except Exception:       # noqa: BLE001
                continue
        return ImageFont.load_default()
    bold = [("/System/Library/Fonts/Helvetica.ttc", 1), ("/System/Library/Fonts/HelveticaNeue.ttc", 1)]
    mono = [("/System/Library/Fonts/Menlo.ttc", 0), ("/System/Library/Fonts/Monaco.ttf", 0)]
    return dict(title=load(bold, 22), head=load(bold, 15), mono=load(mono, 13), small=load(mono, 12))


def pid_label(piece):
    """'PID 0x0200076C', 'PID 0x02000802-080C' (low 16 bits of the last), '(gaps)' when not consecutive;
    a piece mixing types (a wall with a scenery shadow) lists each type's range joined by ' + '."""
    by_type = collections.defaultdict(list)
    for part in piece["parts"]:
        by_type[ids.pid_type(int(part["pid"], 16))].append(int(part["pid"], 16))
    texts, gaps = [], False
    for _type, pids in sorted(by_type.items()):
        pids.sort()
        gaps |= pids[-1] - pids[0] + 1 != len(pids)
        texts.append(f"0x{pids[0]:08X}" + (f"-{pids[-1] & 0xFFFF:04X}" if len(pids) > 1 else ""))
    return "PID " + " + ".join(texts) + (" (gaps)" if gaps else "")


def sheets(manifest, zoom=2, page_width=1600, page_height=1500):
    from PIL import Image, ImageDraw
    gf = GameFiles(overlay=OUT)
    fnt = fonts()
    man_frm = gf.art.load(VILLAGER_FID)
    mw, mh = man_frm.size(2, 0)
    man = np.frombuffer(man_frm.frame(2, 0).pixels, np.uint8).reshape(mh, mw)
    pad, label_h, gutter = 10, 52, 10
    written, placed_on = [], {}
    stats = {}
    by_group = {key: [] for key, _t, _d in GROUPS}
    for name, piece in manifest["pieces"].items():
        by_group[group_of(piece["script"])].append(name)

    for key, title, subtitle in GROUPS:
        tiles = []
        for name in by_group[key]:
            piece = manifest["pieces"][name]
            frames = max(p["frames"] for p in piece["parts"])
            pictures = []
            union = None
            for frame in range(frames):
                picture, origin, solid = compose(gf, piece, frame)
                bbox = extent(solid)
                union = bbox if union is None else (min(union[0], bbox[0]), min(union[1], bbox[1]),
                                                    max(union[2], bbox[2]), max(union[3], bbox[3]))
                pictures.append((picture, origin))
            size = (union[2] - union[0], union[3] - union[1])
            # crop every frame to the same box (opaque extent plus 3 px) and stand the villager on the right;
            # an animated piece shows as many frames as fit across the page (the label says how many exist)
            frame_w = (union[2] - union[0] + 6 + 4) * zoom
            shown = max(1, min(frames, (page_width - 2 * gutter - 8 - (mw + 8) * zoom) // frame_w))
            row = []
            for picture, origin in pictures[:shown]:
                ph, pw = picture.shape[:2]
                cx0, cy0 = max(0, union[0] - 3), max(0, union[1] - 3)
                cx1, cy1 = min(pw, union[2] + 3), min(ph, union[3] + 3)
                row.append((picture[cy0:cy1, cx0:cx1], (origin[0] - cx0, origin[1] - cy0)))
            ch, cw = row[0][0].shape[:2]
            origin_y = row[0][1][1]
            feet = origin_y + 6
            need_h = max(ch, feet + 6)
            total_w = sum(r[0].shape[1] for r in row) + 4 * (len(row) - 1) + mw + 8
            strip = np.zeros((need_h, total_w, 3), np.uint8) + np.array(FLOOR, np.uint8)
            x = 0
            for picture, _origin in row:
                strip[:picture.shape[0], x:x + picture.shape[1]] = picture
                x += picture.shape[1] + 4
            top = feet - mh
            if top >= 0 and feet <= need_h:
                target = strip[top:feet, total_w - mw - 3:total_w - 3]
                np.copyto(target, gf.palette.rgb[man], where=(man > 0)[..., None])
            image = Image.fromarray(strip).resize((strip.shape[1] * zoom, strip.shape[0] * zoom), Image.NEAREST)
            pids = pid_label(piece)
            slots = sorted(p["slot"] for p in piece["parts"])
            n = len(piece["parts"])
            lines = [
                (name, "head", VERDICT_COLOUR[piece["verdict"]]),
                (f"{pids}   {piece['verdict'].upper()}", "mono", (235, 235, 235)),
                (f"{size[0]}x{size[1]} px   {n} part{'s' if n != 1 else ''}"
                 + (f"   {frames} frames" + (f" (first {shown} shown)" if shown < frames else "") if frames > 1 else "")
                 + f"   {piece['kind']}", "mono", (235, 235, 235)),
            ]
            label_w = int(max(fnt[f].getlength(t) for t, f, _c in lines)) + 16
            tiles.append(dict(name=name, image=image, lines=lines, w=max(image.width + 8, label_w), h=image.height + label_h + 8))
            stats[name] = dict(size_px=list(size), parts=n, frames=frames, pid_label=pids)
        # shelf packing into pages
        rows, row, x = [], [], 0
        for tile in tiles:
            if row and x + tile["w"] + gutter > page_width - 2 * gutter:
                rows.append(row)
                row, x = [], 0
            row.append(tile)
            x += tile["w"] + gutter
        if row:
            rows.append(row)
        header_h = 64
        pages, page, used = [], [], header_h
        for r in rows:
            height = max(t["h"] for t in r) + gutter
            if page and used + height > page_height:
                pages.append(page)
                page, used = [], header_h
            page.append(r)
            used += height
        if page:
            pages.append(page)
        for number, page in enumerate(pages, 1):
            height = header_h + sum(max(t["h"] for t in r) + gutter for r in page)
            sheet = Image.new("RGB", (page_width, height), (38, 34, 30))
            draw = ImageDraw.Draw(sheet)
            draw.text((gutter, 8), f"{title}   page {number}/{len(pages)}", font=fnt["title"], fill=(245, 240, 225))
            draw.text((gutter, 36), subtitle, font=fnt["small"], fill=(190, 185, 170))
            for k, text in enumerate(("2x   size = all layers (shadow, halo included)   parts = sprites the piece is cut into",
                                      "border = verdict: green upgrade / amber acceptable / red cut   (gaps) = PIDs not consecutive",
                                      "yellow tint = halo layer (translucent in the engine)   villager = stock hmwarr, 65 px")):
                draw.text((page_width - 700, 6 + 16 * k), text, font=fnt["small"], fill=(190, 185, 170))
            y = header_h
            for r in page:
                x = gutter
                row_h = max(t["h"] for t in r)
                for t in r:
                    colour = VERDICT_COLOUR[manifest["pieces"][t["name"]]["verdict"]]
                    draw.rectangle([x, y, x + t["w"] - 1, y + t["h"] - 1], fill=FLOOR, outline=colour, width=2)
                    draw.rectangle([x + 2, y + 2, x + t["w"] - 3, y + label_h], fill=(38, 34, 30))
                    ty = y + 4
                    for text, font, fill in t["lines"]:
                        draw.text((x + 6, ty), text, font=fnt[font], fill=fill)
                        ty += 18 if font == "head" else 15
                    sheet.paste(t["image"], (x + 4, y + label_h + 6))
                    x += t["w"] + gutter
                y += row_h + gutter
            path = os.path.join(HERE, f"sheet-{key}-{number:02d}.png")
            sheet.save(path, optimize=True)
            written.append(path)
            for r in page:
                for t in r:
                    placed_on[t["name"]] = os.path.basename(path)
    return written, placed_on, stats


# ====================================================================== best screenshots
def copy_best():
    import hashlib
    import shutil
    from PIL import Image
    source_dir = os.path.join(ART, "stage", "town", "shots")
    target_dir = os.path.join(HERE, "best")
    os.makedirs(target_dir, exist_ok=True)
    for stale in os.listdir(target_dir):
        if stale.endswith(".png") and stale not in {d for d, _s in BEST}:
            os.remove(os.path.join(target_dir, stale))
    rows = []
    for dest, source in BEST:
        shutil.copyfile(os.path.join(source_dir, source), os.path.join(target_dir, dest))
        digest = hashlib.sha256(read(os.path.join(target_dir, dest))).hexdigest()
        if digest != hashlib.sha256(read(os.path.join(source_dir, source))).hexdigest():
            raise SystemExit(f"copy of {source} differs")
        size = Image.open(os.path.join(target_dir, dest)).size
        if f"{size[0]}x{size[1]}" not in dest:
            raise SystemExit(f"{dest}: file name says another size than the image ({size})")
        rows.append(dict(file=f"best/{dest}", source=f"stage/town/shots/{source}", size=list(size),
                         bytes=os.path.getsize(os.path.join(target_dir, dest)), sha256=digest))
    return rows


# ====================================================================== output
def write_outputs(manifest, sprites, chk, totals, sheet_of=None, stats=None, best=None):
    pieces = manifest["pieces"]
    lines = []
    lines.append("CATALOGUE VERIFICATION  mod/megaton-art  (python3 mod/megaton-art/catalogue/catalogue.py)")
    lines.append("")
    lines.append(f"checks run ({len(chk.ran)}):")
    lines += [f"  - {c}" for c in chk.ran]
    lines.append("")
    lines.append(f"INCONSISTENCIES ({len(chk.problems)}):")
    lines += [f"  ! {p}" for p in chk.problems] or ["  none"]
    lines.append("")
    lines.append(f"NOTES, not defects ({len(chk.notes)}):")
    lines += [f"  . {p}" for p in chk.notes] or ["  none"]
    lines.append("")
    lines.append("TOTALS")
    for key, value in totals.items():
        lines.append(f"  {key}: {json.dumps(value)}")
    with open(os.path.join(HERE, "verify.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")

    rows = []
    for name, piece in pieces.items():
        mine = [s for s in sprites if s["piece"] == name]
        rows.append(dict(
            name=name, group=group_of(piece["script"]), script=piece["script"], kind=piece["kind"], verdict=piece["verdict"],
            title=piece["title"], parts=len(piece["parts"]), frames=piece["frames"],
            pids=[p["pid"] for p in piece["parts"]], footprint=piece["footprint"], blockers=piece["blockers"],
            size_px=(stats or {}).get(name, {}).get("size_px"), sheet=(sheet_of or {}).get(name),
            frm_bytes=sum(s["frm_bytes"] for s in mine), pro_bytes=sum(s["pro_bytes"] for s in mine),
            sprites=[dict(layer=p["layer"], hex=p["hex"], pid=p["pid"], fid=p["fid"], frm=p["frm"], size=p["size"],
                          shift=p["shift"], frames=p["frames"], blocking=p["blocking"], flat=p["flat"],
                          flags=p["flags"], frm_bytes=next((s["frm_bytes"] for s in mine if s["frm"] == p["frm"] and s["kind"] == p["type"]), None))
                     for p in piece["parts"]]))
    with open(os.path.join(HERE, "catalogue.json"), "w") as f:
        json.dump(dict(totals=totals, inconsistencies=chk.problems, notes=chk.notes, checks_run=chk.ran,
                       sheets=sorted(set((sheet_of or {}).values())), best_screenshots=best or [], pieces=rows,
                       retired_slots=[dict(kind=s["kind"], slot=s["slot"], key=s["key"]) for s in sprites if s["retired"]]),
                  f, indent=1)
        f.write("\n")
    return lines


def main(argv):
    manifest, sprites, chk, totals = verify()
    for stale in os.listdir(HERE):
        if stale.startswith("sheet-") and stale.endswith(".png"):
            os.remove(os.path.join(HERE, stale))
    written, sheet_of, stats = sheets(manifest)
    best = copy_best()
    lines = write_outputs(manifest, sprites, chk, totals, sheet_of, stats, best)
    print("sheets:", *[os.path.relpath(p, ROOT) for p in written], sep="\n  ")
    print("best:", *[f"{b['file']}  <-  {b['source']}" for b in best], sep="\n  ")
    print(f"checks run: {len(chk.ran)}   inconsistencies: {len(chk.problems)}   notes: {len(chk.notes)}")
    for p in chk.problems:
        print("  !", p)
    print(json.dumps({k: v for k, v in totals.items() if k != "animated_sprites"}, indent=1))
    return 1 if chk.problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
