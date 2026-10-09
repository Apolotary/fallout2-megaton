#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Mock-ups: new pieces, roofs and floors on the REAL town, checked for playability and shot in the engine.

    python3 mod/megaton-art/town/mock.py mocks/<name>.py                    build, check, offline pictures
    python3 mod/megaton-art/town/mock.py mocks/<name>.py --engine           ... and the real engine by day
    python3 mod/megaton-art/town/mock.py mocks/<name>.py --engine --night   ... and at night
    options:  --views a,b,c    only these views (names of town/districts.py VIEWS and of the mock's own)
              --res WxH        engine resolution (default 1280x960; the phone is 1040x480)
              --no-check       skip the playability check
              --no-before      skip the "before" pictures of the untouched snapshot

A mock file is a Python script with one function (and, if it likes, VIEWS = {name: (hx, hy)}):

    def mock(M):
        M.place("hg_tower", 92, 78)                 # a registered piece; origin hex with EVEN hx and hy
        M.remove(96, 110, name="Lamp Post")         # take something of the town off a hex (pid=0x... works too)
        M.remove_piece("sg_roof_tank", 122, 60)     # ... or a whole art piece that stands with its origin there
        M.put(0x020000C1, 95, 112)                  # any stock object by PID
        M.reroof("clinic", "rf_clinic")             # a roof sheet made for that building (or a wrap sheet)
        M.roof("rf_canopy", 47, 52, never_hide=True)    # a sheet with its first square on map square (qx, qy)
        M.fill_roof("rf_tin", [(47, 52), (48, 52)])     # a wrap sheet over any squares
        M.floor("fl_junk_a", 51, 44)                # a floor sheet or decal, first square on (qx, qy)
        M.fill_floor("fl_grit", squares)            # a wrap floor sheet
        M.villager(100, 110)                        # somebody for scale (stays out of the check's way: a critter)
        M.view("my-corner", 70, 64)                 # one more camera position
    M.facts is town/snapshot/town.json (plan, spots, reserved hexes ...), M.shack("clinic") the
    building's roof as a tilegeo.Shack, M.free(hx, hy) / M.why(hx, hy) tell what a hex is,
    M.fits(piece, hx, hy) whether a piece's footprint is free there, and M.dump(hx0, hy0, hx1, hy1)
    prints what stands in a box of hexes.

Everything is built from town/snapshot/ (take a new one with town/snapshot.py when the town has
moved) and lands in mod/megaton-art/build/mock/<name>/:
    data/                 the loose game tree of the mock: maps mgmock.map (day) and mgmockn.map
                          (night), maps.txt, scripts.lst + mgnight.int, and the art lists and proto
                          message files MERGED from the town's (snapshot/base) and this art mod's
    patch-mock.dat        everything the engine needs in one archive (TEST ONLY)
    shots/before-<view>.png, offline-<view>.png      pixel-exact offline renders, roofs on
    shots/day-<view>.png, night-<view>.png           engine screenshots (run names clutter-<name>-day / -night)
    report.json           the playability check (town/check.py); printed as well
Exit status 1 when the check FAILs.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)
sys.path.insert(0, HERE)

from f2lib import GameFiles, MapFile, geometry as g, ids, lst, mapstxt, msg, write_dat2      # noqa: E402
from render_map import MapRenderer                                                           # noqa: E402

from pipeline import data, tiles                                                             # noqa: E402
from pipeline import tilegeo as TG                                                           # noqa: E402
from pipeline.place import Placer                                                            # noqa: E402

import check as playability                                                                  # noqa: E402
import districts                                                                             # noqa: E402

SNAP = os.path.join(HERE, "snapshot")
BASE = os.path.join(SNAP, "base")
MOCKS = os.path.join(ART, "build", "mock")
DAY, NIGHT = "mgmock", "mgmockn"
NIGHT_SCRIPT = "mgnight"
PID_VILLAGER = 0x01000003
BAR = 100


def log(text):
    print(f"[mock] {text}", flush=True)


class MockError(Exception):
    pass


# ------------------------------------------------------------------------ merged tables
def merge_tables(target):
    """Art lists, proto lists and proto message files for a game that holds BOTH the town's tree
    (snapshot/base: stock + mod/megaton-art as the town staged it) and this working copy's new
    slots: the town's file, then this copy's lines / entries beyond it."""
    manifest = data.load_manifest()
    for kind, (obj_type, first_pid, art_dir, proto_dir, prefix, msg_file, _) in data.KINDS.items():
        first_new = data.V2_FIRST_SLOT[kind]
        for rel, stock_extra in ((f"art/{art_dir}/{art_dir}.lst", None), (f"proto/{proto_dir}/{proto_dir}.lst", None)):
            with open(os.path.join(BASE, rel), "rb") as f:
                town = lst.split_lines(f.read())
            with open(os.path.join(data.OUT, rel), "rb") as f:
                ours = lst.split_lines(f.read())
            limit = len(ours) - (len(manifest["slots"][kind]) - first_new)        # first line of a new slot
            if len(town) > limit:
                raise MockError(f"{rel}: the town's list has {len(town)} lines and reaches into the slots of this "
                                f"working copy (they start on line {limit + 1}): mod/megaton-art grew past its reserve")
            merged = town + ours[len(town):]
            data._write(target, rel, ("\r\n".join(merged) + "\r\n").encode("latin-1"))
        rel = f"text/english/{msg_file}"
        with open(os.path.join(BASE, rel), "rb") as f:
            town_bytes = f.read()
        with open(os.path.join(data.OUT, rel), "rb") as f:
            ours = msg.parse(f.read())
        have = msg.parse(town_bytes)
        new = {number: entry for number, entry in ours.items()
               if number >= (first_pid + first_new) * 100 and number not in have}
        data._write(target, rel, msg.append_entries(town_bytes, new) if new else town_bytes)

    # The merge round re-renders two original pieces. The immutable snapshot
    # keeps the old baseline; the mock overlay explicitly supplies the new art.
    for name in ("sg_clinic", "sg_bomb_notice"):
        for part in manifest["pieces"][name]["parts"]:
            folder = "scenery" if part["type"] == "scenery" else "walls"
            for rel in (f"art/{folder}/{part['frm']}",
                        f"proto/{folder}/{os.path.splitext(part['frm'])[0]}.pro"):
                with open(os.path.join(data.OUT, rel), "rb") as stream:
                    data._write(target, rel, stream.read())


# ---------------------------------------------------------------------------- the mock
class Mock:
    """What a mock file's mock(M) works with. Hexes are (hx, hy), squares (qx, qy)."""

    def __init__(self, name, m, gf, facts, manifest):
        self.name = name
        self.m = m
        self.gf = gf
        self.facts = facts
        self.manifest = manifest
        self.placer = Placer(manifest)
        self.tiles = tiles.TileSet(manifest, gf)
        self.views = {}
        self.log = []
        self._reserved = {(hx, hy): why for hx, hy, why in facts["keep_free"]}

    # ............................................................... pieces and objects
    def place(self, piece, hx, hy, blockers=True):
        """A registered piece (old or new) with its origin on hex (hx, hy): EVEN hx and EVEN hy."""
        created = self.placer.place(self.m, piece, g.tile_at(hx, hy), blockers=blockers)
        self.log.append(("place", piece, hx, hy))
        return created

    def put(self, pid, hx, hy, **fields):
        """Any object by PID (stock scenery, a wall piece, a critter ...)."""
        self.log.append(("put", f"0x{pid:08X}", hx, hy))
        return self.m.add_object(pid, g.tile_at(hx, hy), **fields)

    def villager(self, hx, hy, rotation=2):
        return self.m.add_object(PID_VILLAGER, g.tile_at(hx, hy), rotation=rotation)

    def objects(self, hx, hy):
        """[(object, proto name)] on a hex."""
        return [(obj, self.gf.protos.name(obj.pid)) for obj in self.m.objects_at(g.tile_at(hx, hy))]

    def remove(self, hx, hy, pid=None, name=None, every=False):
        """Take one object off hex (hx, hy): the one with that PID, or whose proto name contains `name`
        (every=True: all that match). Raises when nothing matches: the town has moved, look again."""
        found = [obj for obj, title in self.objects(hx, hy)
                 if (pid is not None and obj.pid == pid) or (name is not None and name.lower() in (title or "").lower())]
        if not found:
            here = ", ".join(f"{title} 0x{obj.pid:08X}" for obj, title in self.objects(hx, hy)) or "nothing"
            raise MockError(f"remove({hx}, {hy}, pid={pid}, name={name!r}): no such object there; the hex holds: {here}")
        for obj in (found if every else found[:1]):
            self.m.remove_object(obj)
            self.log.append(("remove", f"0x{obj.pid:08X}", hx, hy))
        return found

    def remove_piece(self, piece, hx, hy):
        """Take a placed art piece off the map: every part and blocker of `piece` whose origin is (hx, hy)."""
        entry = self.placer.piece(piece)
        gone = 0
        for part in entry["parts"]:
            tile = g.tile_at(hx + part["hex"][0], hy + part["hex"][1])
            for obj in [o for o in self.m.objects_at(tile) if o.pid == int(part["pid"], 16)][:1]:
                self.m.remove_object(obj)
                gone += 1
        for dhx, dhy in entry["blockers"]:
            tile = g.tile_at(hx + dhx, hy + dhy)
            for obj in [o for o in self.m.objects_at(tile) if o.pid == int(entry["blocker_pid"], 16)][:1]:
                self.m.remove_object(obj)
                gone += 1
        if not gone:
            raise MockError(f"remove_piece({piece!r}, {hx}, {hy}): no part of it stands there")
        self.log.append(("remove_piece", piece, hx, hy))
        return gone

    # ............................................................................ tiles
    def shack(self, building):
        """tilegeo.Shack of a building of the plan (its roof as a sheet: size, wall lines, first square)."""
        return TG.Shack(self.facts["plan"]["buildings"][building]["box"])

    def reroof(self, building, sheet, edges=False):
        self.log.append(("reroof", building, sheet))
        return self.tiles.reroof(self.m, self.facts["plan"]["buildings"][building]["box"], sheet, edges=edges)

    def roof(self, sheet, qx, qy, never_hide=False):
        squares = self.tiles.paint_roof(self.m, sheet, qx, qy)
        if never_hide:
            self.tiles.never_hide(self.m, squares)
        self.log.append(("roof", sheet, qx, qy))
        return squares

    def fill_roof(self, sheet, squares, phase=(0, 0), never_hide=False):
        squares = self.tiles.fill_roof(self.m, sheet, list(squares), phase=phase)
        if never_hide:
            self.tiles.never_hide(self.m, squares)
        self.log.append(("fill_roof", sheet, len(squares)))
        return squares

    def floor(self, sheet, qx, qy):
        self.log.append(("floor", sheet, qx, qy))
        return self.tiles.paint_floor(self.m, sheet, qx, qy)

    def fill_floor(self, sheet, squares, phase=(0, 0)):
        self.log.append(("fill_floor", sheet, len(list(squares))))
        return self.tiles.fill_floor(self.m, sheet, list(squares), phase=phase)

    # ............................................................................ looks
    def view(self, name, hx, hy):
        self.views[name] = (hx, hy)

    def why(self, hx, hy):
        """Why the town keeps hex (hx, hy) free ("spot SIMMS", "path", "doorstep clinic / clinic" ...), or None."""
        return self._reserved.get((hx, hy))

    def free(self, hx, hy):
        """True when nothing blocks the hex right now and the town does not reserve it."""
        walk, _, _ = playability.town_code()
        blocked, doors, _ = walk.survey(self.m)
        tile = g.tile_at(hx, hy)
        return tile not in blocked and tile not in doors and (hx, hy) not in self._reserved

    def fits(self, piece, hx, hy, lane=1):
        """True when every hex piece `piece` would block (origin on (hx, hy)) is free today, is not
        reserved by the town and lies more than `lane` hexes from every path's centre line. A quick
        test for choosing a spot; the playability check after the build is what counts."""
        if hx & 1 or hy & 1:
            return False
        walk, _, _ = playability.town_code()
        blocked, doors, exits = walk.survey(self.m)
        centre = [t for a, b, _ in self.facts["plan"]["paths"] for t in g.line(g.tile_at(*a), g.tile_at(*b))]
        for tile in self.placer.hexes(piece, g.tile_at(hx, hy)):
            if tile < 0 or tile in blocked or tile in doors or tile in exits or g.tile_xy(tile) in self._reserved:
                return False
            if any(g.distance(tile, c) <= lane for c in centre):
                return False
        return True

    def dump(self, hx0, hy0, hx1, hy1, out=print):
        """Print what stands on every hex of a box (walls and blockers left out)."""
        for hy in range(hy0, hy1 + 1):
            for hx in range(hx0, hx1 + 1):
                found = [f"{title} 0x{obj.pid:08X}" for obj, title in self.objects(hx, hy)
                         if obj.obj_type != ids.OBJ_TYPE_WALL and obj.pid != 0x02000043]
                if found or (hx, hy) in self._reserved:
                    out(f"({hx:>3}, {hy:>3})  {'; '.join(found)}" + (f"   [reserved: {self._reserved[(hx, hy)]}]" if (hx, hy) in self._reserved else ""))


# ------------------------------------------------------------------------------- build
def load_mock_file(path):
    spec = importlib.util.spec_from_file_location("mg_mock_" + os.path.splitext(os.path.basename(path))[0], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "mock"):
        raise SystemExit(f"{path} defines no mock(M) function")
    return module


def offline(gf, m, tag, views, shots, res):
    renderer = MapRenderer(gf)
    made = []
    for name, (hx, hy) in views.items():
        scene = renderer.render(m, 0, roofs=True, view=(g.tile_at(hx, hy), res[0], res[1] - BAR))
        path = os.path.join(shots, f"{tag}-{name}.png")
        scene.image().save(path)
        made.append(path)
    return made


def build(path, args):
    name = os.path.splitext(os.path.basename(path))[0]
    if not name.replace("_", "").replace("-", "").isalnum():
        raise SystemExit(f"mock name {name!r}: letters, digits, '-' and '_' only")
    module = load_mock_file(path)
    out = os.path.join(MOCKS, name)
    overlay = os.path.join(out, "data")
    shots = os.path.join(out, "shots")
    shutil.rmtree(overlay, ignore_errors=True)
    for sub in ("maps", "data", "scripts"):
        os.makedirs(os.path.join(overlay, sub))
    os.makedirs(shots, exist_ok=True)
    if not os.path.exists(os.path.join(SNAP, "megaton.map")):
        raise SystemExit("no town snapshot yet: run python3 mod/megaton-art/town/snapshot.py")
    facts = playability.load_facts(SNAP)
    manifest = data.load_manifest()
    merge_tables(overlay)

    stock = GameFiles()
    maps_txt = stock.read("data/maps.txt")
    indices = {}
    for lookup, map_name in ((f"MG Mock {name}"[:39], DAY), (f"MG Mock {name} N"[:39], NIGHT)):
        maps_txt, indices[map_name] = mapstxt.append_map(maps_txt, lookup, map_name, saved=False, automap=False)
    data._write(overlay, "data/maps.txt", maps_txt)
    night_int = os.path.join(overlay, "scripts", NIGHT_SCRIPT + ".int")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ssl.py"), "compile",
                    os.path.join(ART, "stage", "tiles", NIGHT_SCRIPT + ".ssl"), "-o", night_int], check=True, stdout=subprocess.DEVNULL)
    data._write(overlay, "scripts/scripts.lst", lst.append_lines(stock.read("scripts/scripts.lst"),
                                                                 [lst.ScriptList.format_line(NIGHT_SCRIPT, "mock-up: night", 0)]))

    gf = GameFiles(overlay=[overlay, BASE, data.OUT])
    with open(os.path.join(SNAP, "megaton.map"), "rb") as f:
        snapshot_bytes = f.read()
    base = MapFile.from_bytes(snapshot_bytes, gf)
    m = MapFile.from_bytes(snapshot_bytes, gf)
    m.sort_on_write = True
    M = Mock(name, m, gf, facts, manifest)
    try:
        module.mock(M)
    except MockError as problem:
        raise SystemExit(f"mock {name}: {problem}")
    M.tiles.flush()
    gf.refresh()
    views = dict(districts.VIEWS)
    views.update(getattr(module, "VIEWS", {}) or {})
    views.update(M.views)
    if args.views:
        wanted = [v for v in args.views.split(",") if v]
        unknown = [v for v in wanted if v not in views]
        if unknown:
            raise SystemExit(f"unknown view(s) {unknown}; known: {', '.join(views)}")
        views = {v: views[v] for v in wanted}

    for map_name, night in ((DAY, False), (NIGHT, True)):
        m.name = map_name.upper() + ".MAP"
        m.index = indices[map_name]
        m.script_index = 0
        if night:
            m.set_map_script(NIGHT_SCRIPT)
        m.save(os.path.join(overlay, "maps", map_name + ".map"))
    m.name = DAY.upper() + ".MAP"
    m.index = indices[DAY]
    m.script_index = 0
    with open(os.path.join(overlay, "maps", DAY + ".map"), "rb") as f:
        mock_map = MapFile.from_bytes(f.read(), gf)

    res = tuple(int(v) for v in args.res.lower().split("x"))
    pictures = []
    if not args.no_before:
        pictures += offline(gf, base, "before", views, shots, res)
    pictures += offline(gf, mock_map, "offline", views, shots, res)
    log(f"{name}: {len(M.log)} change(s) on the town of {facts['built']['when']}; {len(pictures)} offline pictures in "
        f"{os.path.relpath(shots, ROOT)}")

    report = None
    if not args.no_check:
        report = playability.run(mock_map, gf, facts=facts, base=base, manifest=manifest)
        report["mock"] = name
        report["changes"] = [list(entry) for entry in M.log]
        with open(os.path.join(out, "report.json"), "w") as f:
            json.dump(report, f, indent=1)
            f.write("\n")
        playability.print_report(report, title=f"playability of mock {name}")

    if args.engine:
        files = {}
        for top, roots in (("art", (data.OUT, BASE, overlay)), ("proto", (data.OUT, BASE, overlay)),
                           ("text", (BASE, overlay)), ("maps", (overlay,)), ("data", (overlay,)), ("scripts", (overlay,))):
            for root_dir in roots:                       # later roots win
                for folder, dirs, names in os.walk(os.path.join(root_dir, top)):
                    dirs.sort()
                    for file_name in sorted(names):
                        if file_name.startswith("."):
                            continue
                        full = os.path.join(folder, file_name)
                        with open(full, "rb") as f:
                            files[os.path.relpath(full, root_dir).replace(os.sep, "\\").lower()] = f.read()
        patch = os.path.join(out, "patch-mock.dat")
        write_dat2(files, patch)
        for prefix, map_name in [("day", DAY)] + ([("night", NIGHT)] if args.night else []):
            run_engine(name, prefix, map_name, views, patch, out, shots, args.res, facts)
    return 1 if report and report["fail"] else 0


def run_engine(name, prefix, map_name, views, patch, out, shots, res, facts):
    width, height = (int(v) for v in res.lower().split("x"))
    lines = [f"# generated by town/mock.py ({name}, {prefix})", "wait 1200", "state", f"move {width // 2} {height - 30}"]
    for view, (hx, hy) in views.items():
        lines += [f"center {g.tile_at(hx, hy)}", "wait 700", f"shot shots/{prefix}-{view}.ppm"]
    lines += ["quit 0", ""]
    steps = os.path.join(out, f"steps-{prefix}.txt")
    with open(steps, "w") as f:
        f.write("\n".join(lines))
    run = f"clutter-{name}-{prefix}"
    command = [sys.executable, os.path.join(ROOT, "tools", "f2test.py"), "--name", run, "--fresh", "--map", map_name + ".map",
               "--res", res, "--art-cache-size", "24", "--timeout", str(120 + 4 * len(views)), "--debug-log", "--patch", patch, "--steps", steps]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    states = [line for line in result.stdout.splitlines() if "state map" in line]
    tail = [line for line in result.stdout.splitlines() if "exit code" in line or "TIMEOUT" in line]
    run_shots = os.path.join(ROOT, "run", run, "shots")
    count = 0
    for file_name in sorted(os.listdir(run_shots)) if os.path.isdir(run_shots) else []:
        if file_name.endswith(".png"):
            shutil.copy2(os.path.join(run_shots, file_name), os.path.join(shots, file_name))
            count += 1
    bad = []
    debug = os.path.join(ROOT, "run", run, "debug.log")
    if os.path.exists(debug):
        with open(debug, errors="replace") as f:
            bad = [line.strip() for line in f if ("rror" in line or "ould not" in line or "nable" in line) and "Music" not in line]
    log(f"{run}: {count} screenshot(s) in {os.path.relpath(shots, ROOT)}, {len(states)} state line(s)"
        + (f" ({states[0].split('state ')[-1][:60]})" if states else "") + f", {len(bad)} debug.log problem(s) | " + " | ".join(tail))
    for line in bad[:8]:
        log(f"   debug.log: {line}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mock", help="a mock file (mocks/<name>.py)")
    ap.add_argument("--engine", action="store_true")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--views", default="")
    ap.add_argument("--res", default="1280x960")
    ap.add_argument("--no-check", action="store_true")
    ap.add_argument("--no-before", action="store_true")
    args = ap.parse_args()
    path = args.mock if os.path.exists(args.mock) else os.path.join(ART, args.mock)
    if not os.path.exists(path):
        raise SystemExit(f"no such mock file: {args.mock}")
    return build(os.path.abspath(path), args)


if __name__ == "__main__":
    sys.exit(main())
