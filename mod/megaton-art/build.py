#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Art-author tools for the Megaton mod.

Players restore reviewed sprite bytes with `python megaton.py setup`. The
`clone-data` subcommand restores committed own FRMs and reconstructs mixed floor
tiles from the selected player's game. It preserves the frozen IDs and previous
art output; it does not run Blender or recreate render-pass and sheet PNG files.

Author commands (from the repository root with the author environment active):
    python mod/megaton-art/build.py preview pieces/gate.py [NAME ...]
        Render a local preview without registering IDs. Outputs may include stock
        game art for comparison and must remain local.
    python mod/megaton-art/build.py piece NAME ...
        Render and register existing named pieces.
    python mod/megaton-art/build.py add pieces/example.py
        Render/register a source module. New pieces claim append-only IDs.
    python mod/megaton-art/build.py tiles preview sheets/example.py [NAME ...]
        Preview a tile sheet without registering it.
    python mod/megaton-art/build.py tiles add sheets/example.py [NAME ...]
        Render/register sheets; tile indices are append-only.
    python mod/megaton-art/build.py tiles
        Re-render every registered sheet.
    python mod/megaton-art/build.py tiles list
        List the sheet inventory and available tile slots.
    python mod/megaton-art/build.py
        Re-render all registered art and generated data. Does not run the legacy
        standalone stage/town review map.
    python mod/megaton-art/build.py data
        Rebuild generated lists, prototypes, messages and the local art archive
        from existing author outputs. This is not the player restore operation.
    python mod/megaton-art/build.py clone-data
        Restore committed own sprites and compose player-owned floor tiles.

The other author tools are `stage`, `sort`, `sheet`, `calibrate` and `palette`;
`--engine` runs native checks for stage/calibration and needs the optional test
engine. The merged-town regression suites live in mod/megaton/tests/layout and
mod/megaton/tests/art. Consult docs/testing.md before authoring or running tests.

Rendering uses BLENDER or a `blender` executable on PATH, with four threads.
MG_ART_DEVICE=CPU avoids GPU palette-threshold variation. OpenCV is needed by
render conversion/slicing; it is unnecessary for clone-data. Local fonts affect
sign rendering; no font software is included.

Author changes can invalidate sprites/manifest.json. Review and refresh the own
sprite inventory and its manifest binding before a release; setup restores only
the committed reviewed art. Keep mixed stock composites, game-derived lists,
palettes, render passes, previews and test captures out of source commits.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

# Keep Python bytecode caches out of source directories in this process and its children.
# Author rendering can update the art manifest and generated outputs; player restore is clone-data.
sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

ART = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)

from f2lib import GameFiles, MapFile, geometry as g      # noqa: E402

from pipeline import convert, data, piece as piece_module, slicer, tiles   # noqa: E402
from pipeline import tilegeo as TG                       # noqa: E402
from pipeline import proj as P                           # noqa: E402
from pipeline.place import Placer                        # noqa: E402

BLENDER = os.environ.get("BLENDER") or shutil.which("blender") or "blender"
RENDER = os.path.join(ART, "build", "render")
PREVIEW = os.path.join(ART, "build", "preview")


def log(text):
    print(f"[art] {text}", flush=True)


# -------------------------------------------------------------------- blender
def run_blender(script, out_dir, only=(), preview=False, list_only=False, what="piece"):
    """Run pipeline/blender_piece.py (what="piece") or pipeline/blender_sheet.py (what="sheet") on a
    script; returns {name: spec} of the pieces / sheets it defines."""
    script = os.path.abspath(script)
    command = [BLENDER, "-b", "--threads", "4", "--python", os.path.join(ART, "pipeline", f"blender_{what}.py"), "--",
               "--script", script, "--out", out_dir]
    if only:
        command += ["--only", ",".join(only)]
    if preview:
        command.append("--preview")
    if list_only:
        command.append("--list")
    started = time.time()
    for attempt in range(3):
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if process.returncode >= 0:
            break
        # killed by a signal: Cycles' Metal back end now and then aborts while it loads its kernels
        # (NSInvalidArgumentException in MetalKernelPipeline::compile). Nothing was written; run it again.
        log(f"Blender crashed on {os.path.basename(script)} (signal {-process.returncode}), attempt {attempt + 1} of 3")
    tail = [line for line in process.stdout.splitlines()
            if line.startswith("[piece]") or "Error" in line or "Traceback" in line or line.startswith("  File")
            or line.startswith("[kit")]
    for line in tail:
        print("   " + line)
    listing = os.path.join(out_dir, f"{what}s-" + os.path.splitext(os.path.basename(script))[0] + ".json")
    if process.returncode != 0 or not os.path.exists(listing):
        print(process.stdout[-4000:])
        raise SystemExit(f"Blender failed on {script} (exit code {process.returncode})")
    with open(listing) as f:
        names = json.load(f)
    if not list_only:
        log(f"rendered {os.path.relpath(script, ART)} in {time.time() - started:.0f} s")
    return names


def script_path(script):
    """Path of a piece script relative to mod/megaton-art (what the manifest stores)."""
    full = os.path.abspath(script if os.path.exists(script) else os.path.join(ART, script))
    if not os.path.exists(full):
        raise SystemExit(f"no such piece script: {script}")
    return os.path.relpath(full, ART)


# ---------------------------------------------------------------------- build
def build_script(script, only=(), manifest_path=None):
    """Render and register the pieces of one script. Returns the processed results."""
    relative = script_path(script)
    specs = run_blender(os.path.join(ART, relative), RENDER, only)
    names = [name for name in specs if not only or name in only]
    gf = GameFiles()
    results = []
    for name in names:
        result = piece_module.process(os.path.join(RENDER, name), gf.palette)
        with data.locked_manifest() as manifest:
            owner = manifest["pieces"].get(name, {}).get("script")
            if owner and owner != relative:
                raise SystemExit(f"piece {name!r} is already defined by {owner}; pick another name")
            entry = data.register(manifest, result, relative, gf)
            for part in result["parts"]:                 # inside the lock: nobody packs half-written art
                data.write_part_files(part)
        report(result, entry)
        results.append(result)
    return results


def report(result, entry):
    rep = result["report"]
    main = [p for p in entry["parts"] if p["layer"] == "main"]
    others = [p for p in entry["parts"] if p["layer"] != "main"]
    ramps = ", ".join(f"{name} {count}" for name, count in list(rep["ramps"].items())[:6])
    log(f"{result['name']}: {rep['size'][0]}x{rep['size'][1]} px, {len(main)} part(s) + {len(others)} flat/light, "
        f"footprint {len(entry['footprint'])} hex(es), blockers {len(entry['blockers'])}, reassembly {rep['reassembly']}")
    log(f"   luminance mean {rep['mean_luminance']}, 5 / 50 / 95 % at {rep['luminance_p5_p50_p95']} "
        f"(stock props and walls: mean 35-60, about 12-25 / 43-56 / 84-95)")
    log(f"   colours: {ramps}")
    for warning in rep["warnings"]:
        log(f"   WARNING {warning}")


# --------------------------------------------------------------------- sheets
def build_sheets(script, only=()):
    """Render and register the tile sheets of one script (kit.sheet). Returns the processed results."""
    relative = script_path(script)
    specs = run_blender(os.path.join(ART, relative), RENDER, only, what="sheet")
    names = [name for name in specs if not only or name in only]
    gf = GameFiles()
    results = []
    for name in names:
        result = tiles.process(os.path.join(RENDER, name), gf.palette, gf)
        with data.locked_manifest() as manifest:
            section = tiles.section(manifest, gf)
            owner = section["sheets"].get(name, {}).get("script")
            if owner and owner != relative:
                raise SystemExit(f"sheet {name!r} is already defined by {owner}; pick another name")
            if name in manifest["pieces"]:
                raise SystemExit(f"{name!r} is already the name of a piece; pick another name")
            entry = tiles.register(manifest, result, relative, gf)
            tiles.write_sheet_files(result, gf.palette)
            tiles.write_data(manifest)
            recomposed = tiles.recompose(manifest, name, GameFiles(overlay=data.OUT)) if entry["decal"] else 0
        report_sheet(result, entry, manifest)
        if recomposed:
            log(f"   {recomposed} composed decal tile(s) rebuilt")
        results.append(result)
    return results


def report_sheet(result, entry, manifest):
    rep = result["report"]
    n, m = entry["size"]
    kind = ("decal " if entry["decal"] else "") + entry["kind"] + (" (wraps)" if entry["wrap"] else "")
    room = tiles.budget(manifest)
    ramps = ", ".join(f"{name} {count}" for name, count in list(rep["ramps"].items())[:6])
    log(f"{result['name']}: {kind} sheet {n} x {m} squares, {rep['size_px'][0]}x{rep['size_px'][1]} px, {rep['tiles']} tile(s) "
        f"+ {rep['blank']} empty, {round(rep['coverage'] * 100)} % painted, reassembly {rep['reassembly']}; "
        f"tile slots {room['used']} used, {room['free']} free")
    log(f"   luminance mean {rep['mean_luminance']}, 5 / 50 / 95 % at {rep['luminance_p5_p50_p95']} ({tiles.STOCK_ROOF_LUMA})")
    log(f"   colours: {ramps}")
    for warning in rep["warnings"]:
        log(f"   WARNING {warning}")


def tiles_table():
    manifest = data.load_manifest()
    section = tiles.section(manifest)
    room = tiles.budget(manifest)
    log(f"tiles.lst: stock {section['first_index']} lines + {room['used']} custom slot(s) ({room['live']} live), "
        f"{room['free']} free of {tiles.LIMIT - section['first_index']}")
    composed = {}
    for slot in section["slots"]:
        if "@" in slot["key"] and not slot.get("retired"):
            composed[slot["key"].split("/")[0]] = composed.get(slot["key"].split("/")[0], 0) + 1
    for name, entry in section["sheets"].items():
        kind = ("decal " if entry["decal"] else "") + entry["kind"] + (" wrap" if entry["wrap"] else "")
        log(f"   {name:<24} {kind:<16} {entry['size'][0]:>2} x {entry['size'][1]:<2}  {len(entry['cells']):>3} tile(s)"
            + (f", {composed[name]} composed" if name in composed else "") + f"   {entry['script']}")


LEGACY_KEYS = ("placement_signs", "gate_set")       # the authors' placement notes: placement.py replaced them


def finish():
    """Protos, lists, messages, archive; the gate's door FRM; verdicts; then read it all back."""
    import placement
    with data.locked_manifest() as manifest:
        for key in LEGACY_KEYS:
            manifest.pop(key, None)
        for name, entry in manifest["pieces"].items():
            entry.pop("placement", None)
        placement.sync_verdicts(manifest)
        manifest["placement"] = "placement.json (generated by placement.py): where each piece goes, what it replaces, hooks"
        data.write_data(manifest)
        tiles.write_data(manifest)
        count = data.pack()
        problems = data.verify(manifest) + tiles.verify(manifest)
        has_door = "mg_gate_door" in manifest["pieces"]
    for problem in problems:
        log(f"VERIFY {problem}")
    if problems:
        raise SystemExit("the built data does not match the manifest")
    if has_door:
        # the pipeline wrote a one-frame (shut) picture into the door's art slot: put the five frames back
        subprocess.run([sys.executable, os.path.join(ART, "pieces", "gate", "gate_door.py")], check=True)
    problems = integrity(data.load_manifest())
    for problem in problems:
        log(f"INTEGRITY {problem}")
    if problems:
        raise SystemExit("manifest.json / out/ are not consistent")
    room = tiles.budget(manifest)
    log(f"out/patch-art.dat: {count} files, {len(manifest['pieces'])} piece(s), "
        f"{len(manifest['slots']['scenery'])} scenery + {len(manifest['slots']['wall'])} wall protos, "
        f"{len(tiles.section(manifest)['sheets'])} tile sheet(s) in {room['used']} tile slot(s) ({room['free']} free)")


def integrity(manifest):
    """Checks beyond data.verify: no id is used twice, every slot has its files, the lists and the
    message files in out/ (and inside the packed archive) are the stock ones plus exactly our lines."""
    from f2lib import dat2, lst, msg
    problems = []
    stock = GameFiles()
    seen = {}
    for name, piece in manifest["pieces"].items():
        for part in piece["parts"]:
            for key in ("pid", "fid"):
                owner = seen.setdefault((key, part[key]), name + "/" + part["layer"] + str(part["hex"]))
                if owner != name + "/" + part["layer"] + str(part["hex"]):
                    problems.append(f"{key} {part[key]} is claimed by {owner} and by {name}")
            if manifest["slots"][part["type"]][part["slot"]]["key"] != f"{name}/{part['layer']}/{part['hex'][0]},{part['hex'][1]}":
                problems.append(f"{name}: slot {part['slot']} belongs to {manifest['slots'][part['type']][part['slot']]['key']}")
    with dat2.Dat2(data.PATCH) as archive:               # the archive is exactly out/art, out/proto, out/text
        for key in archive.order:
            path = os.path.join(data.OUT, key)
            if not os.path.exists(path):
                problems.append(f"patch-art.dat holds {key}, which is not in out/")
                continue
            with open(path, "rb") as f:
                if f.read() != archive.read(key):
                    problems.append(f"patch-art.dat: {key} differs from out/")
        loose = sum(len(names) for top in ("art", "proto", "text") for _, _, names in os.walk(os.path.join(data.OUT, top)))
        if loose != len(archive.order):
            problems.append(f"patch-art.dat has {len(archive.order)} members, out/ has {loose} files")
    for kind, (obj_type, first_pid, art_dir, proto_dir, prefix, msg_file, _) in data.KINDS.items():
        slots = manifest["slots"][kind]
        stock_proto = lst.proto_names(stock.read(f"proto/{proto_dir}/{proto_dir}.lst"))
        with open(os.path.join(data.OUT, "proto", proto_dir, proto_dir + ".lst"), "rb") as f:
            proto_lines = lst.proto_names(f.read())
        with open(os.path.join(data.OUT, "art", art_dir, art_dir + ".lst"), "rb") as f:
            art_lines = lst.art_names(f.read())
        stock_art = lst.art_names(stock.read(f"art/{art_dir}/{art_dir}.lst"))
        if art_lines[:len(stock_art)] != stock_art or len(art_lines) != len(stock_art) + len(slots):
            problems.append(f"art/{art_dir}/{art_dir}.lst is not the stock list plus {len(slots)} lines")
        if proto_lines[:len(stock_proto)] != stock_proto or len(proto_lines) != first_pid - 1 + len(slots):
            problems.append(f"proto/{proto_dir}/{proto_dir}.lst does not end on PID {first_pid - 1 + len(slots)}")
        if len(stock_art) + len(slots) > 4095 or first_pid + len(slots) > 0xFFFFFF:
            problems.append(f"{kind}: too many slots")
        for index in range(len(slots)):
            numbers = data.slot_ids(stock, kind, index)
            if slots[index].get("reserved"):             # mod/megaton-art's future slots: padding lines, no files
                if art_lines[len(stock_art) + index].lower() != data.PAD_ART or proto_lines[first_pid - 1 + index].lower() != data.PAD_PROTO:
                    problems.append(f"{kind} slot {index} is reserved but its list lines are not padding")
                continue
            if art_lines[len(stock_art) + index].lower() != numbers["frm"] or proto_lines[first_pid - 1 + index].lower() != numbers["pro"]:
                problems.append(f"{kind} slot {index}: list lines do not name {numbers['frm']} / {numbers['pro']}")
            for path in (numbers["art_path"], numbers["pro_path"]):
                if not os.path.exists(os.path.join(data.OUT, path)):
                    problems.append(f"{kind} slot {index}: out/{path} is missing")
        with open(os.path.join(data.OUT, "text", "english", msg_file), "rb") as f:
            texts = msg.parse(f.read())
        stock_texts = msg.parse(stock.read(f"text/english/{msg_file}"))
        if any(texts.get(number) != entry for number, entry in stock_texts.items()):
            problems.append(f"{msg_file}: a stock entry was changed")
        for index, slot in enumerate(slots):
            if slot.get("reserved"):
                continue
            if (first_pid + index) * 100 not in texts or (first_pid + index) * 100 in stock_texts:
                problems.append(f"{msg_file}: no (or a stock) name for PID {first_pid + index}")
    return problems


def build_all():
    manifest = data.load_manifest()
    scripts = {}
    for name, entry in manifest["pieces"].items():
        scripts.setdefault(entry["script"], []).append(name)
    if not scripts:
        raise SystemExit("manifest.json lists no pieces yet: use `build.py add pieces/<script>.py`")
    for script, names in scripts.items():
        defined = run_blender(os.path.join(ART, script), RENDER, list_only=True)
        build_script(script, only=[name for name in names if name in defined])
        for name in names:
            if name not in defined:
                log(f"WARNING {script} no longer defines {name}: its slots stay reserved (retired)")
    build_all_sheets()
    finish()


def build_all_sheets():
    scripts = {}
    for name, entry in tiles.section(data.load_manifest())["sheets"].items():
        scripts.setdefault(entry["script"], []).append(name)
    for script, names in scripts.items():
        defined = run_blender(os.path.join(ART, script), RENDER, list_only=True, what="sheet")
        build_sheets(script, only=[name for name in names if name in defined])
        for name in names:
            if name not in defined:
                log(f"WARNING {script} no longer defines sheet {name}: its tile slots stay reserved")


# -------------------------------------------------------------------- preview
def preview(script, only=()):
    """Fast look at pieces without touching the manifest or out/."""
    from PIL import Image, ImageDraw
    from render_map import MapRenderer, Overlay

    relative = script_path(script)
    render_dir = os.path.join(PREVIEW, "render")
    specs = run_blender(os.path.join(ART, relative), render_dir, only, preview=True)
    names = [name for name in specs if not only or name in only]
    stock = GameFiles()
    for name in names:
        result = piece_module.process(os.path.join(render_dir, name), stock.palette)
        scratch = os.path.join(PREVIEW, "data-" + name)
        shutil.rmtree(scratch, ignore_errors=True)
        manifest = data.load_manifest()                      # a private copy: never saved
        entry = data.register(manifest, result, relative, stock)
        for part in result["parts"]:
            data.write_part_files(part, scratch)
        data.write_data(manifest, scratch)
        report(result, entry)

        gf = GameFiles(overlay=scratch)
        origin = g.tile_at(100, 100)
        m = MapFile.new("mgprev", gf)
        m.fill_floor(30, 30, 70, 70, "edg5000.frm")
        placer = Placer(manifest)
        placer.place(m, name, origin)
        hexes = [tuple(h) for h in entry["footprint"]] or [(0, 0)]
        lo_x, hi_x = min(h[0] for h in hexes), max(h[0] for h in hexes)
        lo_y, hi_y = min(h[1] for h in hexes), max(h[1] for h in hexes)
        blocked = set(hexes) | {tuple(p["hex"]) for p in entry["parts"] if p["blocking"]}

        def free(dhx, dhy):
            while (dhx, dhy) in blocked:
                dhy += 1
            blocked.add((dhx, dhy))
            return g.tile_at(100 + dhx, 100 + dhy)

        mid_x = (lo_x + hi_x) // 2
        for dhx, dhy in ((mid_x, hi_y + 2), (mid_x + 1, lo_y - 2), (hi_x + 2, (lo_y + hi_y) // 2), (lo_x - 2, (lo_y + hi_y) // 2)):
            m.add_object(0x01000003, free(dhx, dhy), rotation=g.SE)             # villagers around it
        m.add_object(0x020000C1, free(lo_x - 4, hi_y + 1))                       # stock crate
        m.add_object(0x02000005, free(lo_x - 5, hi_y + 3))                       # stock barrel
        for i, hx in enumerate(range(hi_x + 5, hi_x + 9)):                       # stock shack wall
            m.add_object(0x03000081 if hx & 1 else 0x03000082, free(hx, lo_y))

        rgba, canvas = piece_module.composite(result, stock.palette)
        ox, oy = g.hex_center(origin)
        x0 = ox + min(canvas[0], P.hex_px(hi_x + 9, lo_y)[0] - 40) - 30
        x1 = ox + max(canvas[2], P.hex_px(lo_x - 5, hi_y + 3)[0] + 40) + 30
        y0 = oy + min(canvas[1], P.hex_px(hi_x + 9, lo_y)[1] - 110) - 40
        y1 = oy + max(canvas[3], P.hex_px(lo_x - 5, hi_y + 3)[1] + 30) + 40
        rect = (x0, y0, x1, y1)
        panels = []
        day = MapRenderer(gf).render(m, 0, world_rect=rect)
        panels.append(("day (as the engine paints it)", day.image()))
        night = MapRenderer(gf, light=0x4000 + 0x2000).render(m, 0, world_rect=rect)
        panels.append(("night, unlit (37 % light)", night.image()))
        overlay = Overlay(day, 1.0)
        overlay.tint([g.tile_at(100 + h[0], 100 + h[1]) for h in entry["footprint"]], (255, 60, 60, 110))
        overlay.tint([g.tile_at(100 + p["hex"][0], 100 + p["hex"][1]) for p in entry["parts"]
                      if p["layer"] == "main" and not p["blocking"]], (60, 160, 255, 110))
        overlay.grid()
        panels.append(("red = blocked hexes, blue = walk-under parts", overlay.image.convert("RGB")))

        zoom = 2
        width = max(image.width for _, image in panels) * zoom
        height = sum(image.height * zoom + 18 for _, image in panels)
        sheet = Image.new("RGB", (width, height), (30, 30, 30))
        draw = ImageDraw.Draw(sheet)
        y = 0
        for title, image in panels:
            draw.text((4, y + 3), title, fill=(255, 255, 255))
            sheet.paste(image.resize((image.width * zoom, image.height * zoom), Image.NEAREST), (0, y + 18))
            y += image.height * zoom + 18
        os.makedirs(PREVIEW, exist_ok=True)
        path = os.path.join(PREVIEW, name + ".png")
        sheet.save(path)
        crops_path = os.path.join(PREVIEW, name + "-palette.png")
        palette_crops(os.path.join(render_dir, name), result, stock.palette, crops_path)
        parts_path = os.path.join(PREVIEW, name + "-parts.png")
        parts_picture(result, stock.palette, parts_path)
        log(f"preview: {os.path.relpath(path, ROOT)}, {os.path.relpath(crops_path, ROOT)}, "
            f"{os.path.relpath(parts_path, ROOT)}")


# The town's own shack kit (mod/megaton/layout/kit.py), read-only: previews and the tile stage
# put sheets on a real stock shack.
def town_kit():
    town_mod = os.path.join(ROOT, "mod", "megaton")
    if town_mod not in sys.path:
        sys.path.insert(0, town_mod)
    from layout import kit as shack_kit
    return shack_kit


def preview_shack(m, box, roof="tin", floor="plate", door=None, seed=7):
    """A stock shack on `box` with a front door; returns the kit's Shack."""
    import random
    shack_kit = town_kit()
    shack = shack_kit.Shack(m, box, random.Random(seed), roof=roof, floor=floor, name="preview")
    odd = door or (((box[0] + box[2]) // 2) | 1)
    shack.door("front", odd)
    shack.build()
    return shack


def preview_sheets(script, only=()):
    """Fast look at tile sheets without touching the manifest or out/: build/preview/NAME.png."""
    from PIL import Image, ImageDraw
    from render_map import MapRenderer, Overlay

    relative = script_path(script)
    render_dir = os.path.join(PREVIEW, "render")
    specs = run_blender(os.path.join(ART, relative), render_dir, only, preview=True, what="sheet")
    names = [name for name in specs if not only or name in only]
    stock = GameFiles()
    for name in names:
        result = tiles.process(os.path.join(render_dir, name), stock.palette, stock)
        scratch = os.path.join(PREVIEW, "data-" + name)
        shutil.rmtree(scratch, ignore_errors=True)
        manifest = data.load_manifest()                      # a private copy: never saved
        entry = tiles.register(manifest, result, relative, stock)
        tiles.write_sheet_files(result, stock.palette, scratch)
        tiles.write_data(manifest, scratch)
        report_sheet(result, entry, manifest)

        gf = GameFiles(overlay=scratch)
        ts = tiles.TileSet(manifest, gf, out_dir=scratch)
        m = MapFile.new("mgprev", gf)
        m.fill_floor(30, 30, 75, 75, lambda x, y: ("edg5000.frm", "edg5003.frm", "edg5002.frm", "edg5001.frm")[(x * 7 + y * 3) % 4])
        n, rows = entry["size"]
        squares = []
        if entry["kind"] == "roof":
            fits = not entry["wrap"] and n >= 2 and rows >= 4
            cols, deep = (n, rows) if fits else (7, 7)
            if entry["wrap"] or fits:
                box = (100, 101, 100 + 2 * cols, 101 + 2 * (deep - 2))
                preview_shack(m, box)
                squares = ts.reroof(m, box, name)
                twin = (box[0] - 2 * cols - 8, box[1], box[0] - 8, box[3])       # an untouched stock shack beside it
                preview_shack(m, twin, seed=11)
                squares += TG.Shack(twin).squares()
            else:
                squares = ts.paint_roof(m, name, 50, 50)
        elif entry["wrap"]:
            squares = ts.fill_floor(m, name, [(x, y) for x in range(46, 56) for y in range(46, 54)])
        else:
            squares = ts.paint_floor(m, name, 50, 50) or [(50, 50)]
        for dhx, dhy in ((-3, 6), (4, -3)):
            qx, qy = squares[len(squares) // 2]
            m.add_object(0x01000003, g.tile_at(2 * qx + dhx, 2 * qy + dhy + (rows if entry["kind"] == "roof" else 0)), rotation=g.SE)
        xs, ys = [], []
        lift = TG.ROOF_LIFT_PX if entry["kind"] == "roof" else 0
        for qx, qy in squares:
            x, y = g.square_world(qy * 100 + qx)
            xs += [x, x + 80]
            ys += [y - lift, y + 36]
        rect = (min(xs) - 60, min(ys) - 40, max(xs) + 60, max(ys) + 70)
        panels = []
        day = MapRenderer(gf).render(m, 0, roofs=True, world_rect=rect)
        panels.append(("day (as the engine paints it)", day.image()))
        night = MapRenderer(gf, light=0x4000 + 0x2000).render(m, 0, roofs=True, world_rect=rect)
        panels.append(("night (37 % light; roofs get the map's ambient light only)", night.image()))
        if entry["kind"] == "roof":
            open_roof = MapRenderer(gf).render(m, 0, roofs=False, world_rect=rect)
            panels.append(("roofs hidden (what a hole shows; what the player sees inside)", open_roof.image()))
        zoom = 2 if rect[2] - rect[0] < 700 else 1
        width = max(image.width for _, image in panels) * zoom
        height = sum(image.height * zoom + 18 for _, image in panels)
        picture = Image.new("RGB", (width, height), (30, 30, 30))
        draw = ImageDraw.Draw(picture)
        y = 0
        for title, image in panels:
            draw.text((4, y + 3), title, fill=(255, 255, 255))
            picture.paste(image.resize((image.width * zoom, image.height * zoom), Image.NEAREST), (0, y + 18))
            y += image.height * zoom + 18
        os.makedirs(PREVIEW, exist_ok=True)
        path = os.path.join(PREVIEW, name + ".png")
        picture.save(path)
        grid_path = os.path.join(PREVIEW, name + "-tiles.png")
        tile_grid_picture(result, stock.palette, grid_path)
        log(f"preview: {os.path.relpath(path, ROOT)}, {os.path.relpath(grid_path, ROOT)}")


def tile_grid_picture(result, palette, path, zoom=3):
    """The sheet at 3x with the seams of its tiles drawn in and every square numbered (i, j)."""
    import numpy as np
    from PIL import Image, ImageDraw
    canvas, lift = result["canvas"], result["lift_px"]
    n, m = result["spec"]["size"]
    rgba = palette.rgba[result["indices"]].copy()
    back = np.zeros(rgba.shape, np.uint8) + np.array([60, 50, 70, 255], np.uint8)
    shown = np.where(rgba[..., 3:] > 0, rgba, back)
    image = Image.fromarray(shown, "RGBA").resize((shown.shape[1] * zoom, shown.shape[0] * zoom), Image.NEAREST)
    draw = ImageDraw.Draw(image)
    for j in range(m):
        for i in range(n):
            bx, by = TG.box_px(i, j)
            x, y = (bx - canvas[0]) * zoom, (by - lift - canvas[1]) * zoom
            corners = [(x + 48 * zoom, y), (x + 80 * zoom, y + 24 * zoom), (x + 32 * zoom, y + 36 * zoom), (x, y + 12 * zoom)]
            draw.polygon(corners, outline=(255, 255, 0, 120))
            draw.text((x + 34 * zoom, y + 14 * zoom), f"{i},{j}", fill=(255, 255, 255, 255))
    image.save(path)


def palette_crops(render_dir, result, palette, path, zoom=4):
    """Before / after sheet: the 24-bit render next to its palette conversion, at 4x.

    Panels: render (box-filtered) | no dither, no outline | this piece's settings | error diffusion.
    """
    import numpy as np
    from PIL import Image, ImageDraw
    meta = result["meta"]
    rgba = convert.load_rgba(os.path.join(render_dir, "main_f000.png"))
    panels = []
    rgb, alpha = convert.downsample(rgba, meta["ss"])
    rgb = convert.grade(rgb, convert.options(result["spec"].get("convert") or {}))
    true = np.concatenate([convert.linear_to_srgb(rgb) * 255.0, alpha[..., None] * 255.0], axis=2).clip(0, 255).astype(np.uint8)
    panels.append(("render (graded), 24-bit, soft alpha", true))
    base = result["spec"].get("convert") or {}
    for title, overrides in (("nearest colour only", dict(dither="none", outline=0.0, outline_lit=0.0)),
                             ("ordered dither + outline (default)", {}),
                             ("error diffusion + outline", dict(dither="fs", dither_strength=0.6))):
        opts = convert.options({**base, **overrides})
        indices, mask, _, _ = convert.convert_frame(rgba, meta["ss"], convert.Quantiser(palette, opts), opts)
        panels.append((title, palette.rgba[indices]))
    h, w = panels[0][1].shape[:2]
    # crop to the busiest 96x96 window so the sheet stays readable for big pieces
    if w > 110 or h > 110:
        mask = result["mask"].astype(np.float32)
        cw, ch = min(w, 96), min(h, 96)
        ys, xs = np.nonzero(result["mask"])
        cx = int(np.clip(np.median(xs) - cw // 2, 0, w - cw))
        cy = int(np.clip(np.median(ys) - ch // 2, 0, h - ch))
        panels = [(title, pixels[cy:cy + ch, cx:cx + cw]) for title, pixels in panels]
        h, w = ch, cw
    sheet = Image.new("RGB", ((w * zoom + 8) * len(panels), h * zoom + 18), (131, 112, 88))
    draw = ImageDraw.Draw(sheet)
    for i, (title, pixels) in enumerate(panels):
        image = Image.fromarray(pixels, "RGBA").resize((w * zoom, h * zoom), Image.NEAREST)
        sheet.paste(image, (i * (w * zoom + 8), 18), image)
        draw.text((i * (w * zoom + 8) + 3, 3), title, fill=(255, 255, 255))
    sheet.save(path)


def parts_picture(result, palette, path, zoom=3):
    """The cut: every part tinted by its anchor hex, anchor pixels marked."""
    import numpy as np
    from PIL import Image
    canvas = result["canvas"]
    main = [p for p in result["parts"] if p["layer"] == "main"]
    width, height = canvas[2] - canvas[0], canvas[3] - canvas[1]
    out = np.zeros((height, width, 3), np.float32) + np.array([131, 112, 88], np.float32)
    tints = [(255, 80, 80), (80, 200, 255), (255, 220, 60), (120, 255, 120), (255, 120, 255), (255, 160, 60)]
    for k, part in enumerate(main):
        painted = slicer.assemble([part], canvas)
        colour = palette.rgb[painted].astype(np.float32)
        tint = np.array(tints[k % len(tints)], np.float32)
        mask = painted > 0
        out[mask] = colour[mask] * 0.55 + tint * 0.45
    image = Image.fromarray(out.clip(0, 255).astype(np.uint8)).resize((width * zoom, height * zoom), Image.NEAREST)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    for k, part in enumerate(main):
        px, py = P.hex_px(*part["hex"])
        x, y = (px - canvas[0]) * zoom, (py - canvas[1]) * zoom
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(255, 255, 255), fill=tints[k % len(tints)])
        draw.text((x + 6, y - 5), f"{part['hex'][0]},{part['hex'][1]}", fill=(255, 255, 255))
    image.save(path)


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="all",
                    choices=["all", "add", "piece", "preview", "stage", "sheet", "sort", "data", "calibrate", "palette",
                             "tiles", "clone-data"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--engine", action="store_true", help="stage / calibrate: also run the real engine")
    ap.add_argument("--walk", action="store_true", help="stage: also run the draw-order walk in the engine")
    options = ap.parse_args()
    started = time.time()
    if options.command == "clone-data":
        from pipeline.clone_assets import build, AssetError
        try:
            build()
        except AssetError as error:
            raise SystemExit(str(error)) from None
    elif options.command == "all":
        build_all()
        log("the old review stage (stage/town, placement.py) is not rebuilt: mock-ups on the current town are "
            "town/mock.py; `build.py stage` still runs the old one")
    elif options.command == "sort":
        from pipeline import sorttest
        names = options.args or list(data.load_manifest()["pieces"])
        rows = sorttest.run(names, RENDER, GameFiles().palette, PREVIEW)
        failed = 0
        for row in rows:
            if row.get("missing"):
                log(f"{row['name']:18s} no render in build/render (build the piece first)")
                continue
            failed += row["fails"]
            log(f"{row['name']:18s} {row['parts']:2d} part(s) {row['hexes']:4d} hexes  over {row['over']:5d} px at {row['over_hex']}"
                f"  under {row['under']:5d} px at {row['under_hex']}{'   FAILS' if row['fails'] else ''}")
            for key in ("over", "under"):
                if row["failing"][key]:
                    log(f"{'':18s}   {key}: " + ", ".join(f"{h} {n}" for h, n in row["failing"][key]))
        log(f"{failed} of {len(rows)} piece(s) sort wrongly somewhere (pictures: build/preview/sort-<piece>.png)")
    elif options.command == "tiles":
        action = options.args[0] if options.args else "all"
        if action == "all":
            build_all_sheets()
            finish()
        elif action == "list":
            tiles_table()
        elif action in ("add", "preview") and len(options.args) >= 2:
            if action == "add":
                build_sheets(options.args[1], only=options.args[2:])
                finish()
            else:
                preview_sheets(options.args[1], only=options.args[2:])
        elif action == "drop" and len(options.args) >= 2:
            with data.locked_manifest() as manifest:
                for name in options.args[1:]:
                    freed = tiles.drop(manifest, name)
                    log(f"sheet {name} dropped; {freed} tile slot(s) given back")
                    picture = os.path.join(tiles.SHEETS_DIR, name + ".png")
                    if os.path.exists(picture):
                        os.remove(picture)
            finish()
        elif action == "sheet":
            from pipeline import sheet
            for path in sheet.tile_sheets(options.args[1:]):
                log(os.path.relpath(path, ROOT))
        else:
            raise SystemExit("usage: build.py tiles [list | add sheets/<script>.py [NAME ...] | "
                             "preview sheets/<script>.py [NAME ...] | drop NAME ... | sheet [NAME ...]]")
    elif options.command == "sheet":
        from pipeline import sheet
        for path in sheet.sheets(options.args):
            log(os.path.relpath(path, ROOT))
    elif options.command == "add":
        if not options.args:
            raise SystemExit("usage: build.py add pieces/<script>.py [NAME ...]")
        build_script(options.args[0], only=options.args[1:])
        finish()
    elif options.command == "piece":
        manifest = data.load_manifest()
        by_script = {}
        for name in options.args:
            if name not in manifest["pieces"]:
                raise SystemExit(f"no piece {name!r} in manifest.json; register it with `build.py add <script>`")
            by_script.setdefault(manifest["pieces"][name]["script"], []).append(name)
        for script, names in by_script.items():
            build_script(script, only=names)
        finish()
    elif options.command == "preview":
        if not options.args:
            raise SystemExit("usage: build.py preview pieces/<script>.py [NAME ...]")
        preview(options.args[0], only=options.args[1:])
    elif options.command == "stage":
        run_stage(options.engine, options.walk)
    elif options.command == "data":
        finish()
    elif options.command == "calibrate":
        subprocess.run([sys.executable, os.path.join(ART, "pipeline", "calibrate.py")]
                       + (["--engine"] if options.engine else []), check=True)
    elif options.command == "palette":
        print(convert.palette_report(GameFiles().palette))
    log(f"done in {time.time() - started:.0f} s")


def run_stage(engine, walk=False):
    """placement.json, then the review map built from it (and the engine runs)."""
    subprocess.run([sys.executable, os.path.join(ART, "placement.py")], check=True)
    command = [sys.executable, os.path.join(ART, "stage", "town", "build_stage.py")]
    subprocess.run(command + (["--engine"] if engine else []) + (["--walk"] if walk else []), check=True)


if __name__ == "__main__":
    main()
