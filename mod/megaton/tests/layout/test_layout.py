#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Offline checks of the town map (no engine needed, about 5 s).

    python3 mod/megaton/tests/layout/test_layout.py [--staging DIR] [test name ...]

The map is built in memory from layout/ with the cast of every group that has
delivered one, then checked the way the engine would use it:

    validate          MapFile.validate() reports nothing
    spots             every spot name of the contract exists, sits on the centre-able grid,
                      and no two critters share a hex
    roofs             each building's roof is one flood-fill region of its own (the engine
                      hides roofs by 4-neighbour flood fill from the player's square)
    doors             every door of the plan exists as a door object in a wall, and both
                      sides of it are free
    reachable         from ENTRY, opening doors: every door, every free hex of every room,
                      every NPC spot, a hex next to every scripted object, the bomb, the exit grid
    contained         with the gate shut nobody gets in or out; with it open the only ground
                      reachable outside the wall is the apron
    keep_free         nothing stands on the hexes layout.keep_free() reserves for NPCs, doorways
                      and paths (the decorator's contract)
    dressing          furniture: every container can be reached and stands on a closed hex, the
                      cast's scripted objects are the first thing on their hex, every NPC has
                      room around him, merchants can be talked to across their counters, no
                      blocker hides under a door, Walter's scrap exists, the town has lamps
    camera            the view centre cannot be scrolled out of the frame of scroll blockers
    cast              every `attach` entry finds its object (what the integration build demands)
    art               the custom art is on the map: one bomb (the three-state sprite) that is the
                      first thing on its hex with its access hexes free, the gate door wears the
                      five-frame door, the pieces that replaced described furniture carry mgdecor,
                      every lamp piece gives light, nothing of the plan is left unplaced
    clickable         no piece of art stands between the camera and something the player clicks:
                      every door, cast member, scripted object, container and standing post keeps
                      most of the pixels a click could reach in the town without the art
                      (layout/sight.py; the engine gives a click to the last sprite painted there)
    trim              the row of hexes behind every back wall, which lies under the roof's trim,
                      cannot be walked on (standing there would take the roof off from outside)
    seen              the absolute figure behind it: every OUTER door keeps half of its pixels with
                      all roofs on (none stands in a back or right wall, under its own roof), and
                      every cast member and standing post two fifths of his, indoors with only his
                      own building's roof off

Exit status 1 if any check fails. The staging tree (default mod/megaton/out-layout)
needs the data tables; they are staged on demand.
"""
import os
import shutil
import subprocess
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(MOD))
sys.path.insert(0, MOD)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from f2lib import GameFiles, geometry as g, ids  # noqa: E402

import cast  # noqa: E402
import layout  # noqa: E402
from layout import apron, buildings, outdoors, plan, spots, walk  # noqa: E402

# The spot names scripts were written against (layout/spots.py at the start of the
# layout work, plus what the script groups appended). Names may be added, never removed.
CONTRACT = """ENTRY GATE SIMMS_GREET GATE_EXIT WELD SIMMS HARDEN BURKE BURKE_TABLE BURKE_RENDEZVOUS BOMB
CROMWELL MAYA MORIARTY GOB NOVA JERICHO LUCY OFFICE_DOOR TERMINAL CABINET STRONGBOX NOVA_BED MOIRA MERC
DOC JENNY WALTER LEAK1 LEAK2 LEAK3 HOUSE_DOOR HOUSE_BED COMMON_BED ARMORY_DOOR BILLY MAGGIE NATHAN
SETTLER1 SETTLER2 SETTLER3 STOCKHOLM MICKY TRADER SILVER HITMAN1 HITMAN2 HITMAN3 SETTLER4 LOITER_SALOON
LOITER_LANTERN LOITER_COMMON LOITER_GATE LOITER_WATER ARMORY_LOCKER ARRIVAL SIMMS_POOL""".split()

# Where each spot has to be: a room of plan.BUILDINGS, "town" (inside the wall, outdoors),
# "apron" (outside the gate) or "pool". Spots not listed are only checked for being reachable.
PLACES = {
    "SIMMS_GREET": "town", "SIMMS": "town", "SIMMS_POOL": "town", "WELD": "apron", "STOCKHOLM": "apron",
    "MICKY": "apron", "TRADER": "apron", "SILVER": "apron", "BURKE_RENDEZVOUS": "apron", "ARRIVAL": "apron",
    "HITMAN1": "apron", "HITMAN2": "apron", "HITMAN3": "apron", "ENTRY": "apron",
    "BURKE": ("saloon", "hall"), "BURKE_TABLE": ("saloon", "hall"), "MORIARTY": ("saloon", "hall"),
    "GOB": ("saloon", "hall"), "NOVA": ("saloon", "hall"), "JERICHO": ("saloon", "hall"), "LUCY": ("saloon", "hall"),
    "TERMINAL": ("saloon", "office"), "CABINET": ("saloon", "office"), "STRONGBOX": ("saloon", "office"),
    "NOVA_BED": ("saloon", "rented room"), "MOIRA": ("craterside", "shop"), "MERC": ("craterside", "shop"),
    "DOC": ("clinic", "ward"), "WALTER": ("plant", "machine hall"), "MAYA": ("church", "chapel"),
    "HARDEN": ("sheriff", "living room"), "ARMORY_LOCKER": ("sheriff", "armory"), "BILLY": ("billy", "room"),
    "HOUSE_BED": ("house", "room"), "COMMON_BED": ("common", "bunkroom"), "CROMWELL": "pool",
    "ARRIVAL_VIEW": "town", "MAGGIE": "town", "NATHAN": "town", "SETTLER1": "town", "SETTLER2": "town", "SETTLER3": "town",
    "SETTLER4": "town", "LOITER_SALOON": "town", "LOITER_LANTERN": "town", "LOITER_COMMON": "town",
    "LOITER_GATE": "town", "LOITER_WATER": "town", "LEAK1": "town", "LEAK2": "town", "LEAK3": "town",
    "JENNY": "stall",
}
DOOR_SPOTS = {"GATE": plan.GATE, "OFFICE_DOOR": plan.door_hex("saloon", "office"),
              "HOUSE_DOOR": plan.door_hex("house", "house"), "ARMORY_DOOR": plan.door_hex("sheriff", "armory")}

STATE = {}


def town():
    """The built map, shared by the tests: (map, info, blocked, doors, exits)."""
    if not STATE:
        gf = GameFiles(overlay=STAGING)
        m, info = layout.build(gf, log=lambda *a: None)
        blocked, doors, exits = walk.survey(m)
        STATE.update(m=m, info=info, gf=gf, blocked=blocked, doors=doors, exits=exits,
                     entry=spots.tile("ENTRY"))
        STATE["reach"] = walk.flood(STATE["entry"], blocked, stop=exits)
    return STATE


def xy(tile):
    return g.tile_xy(tile)


def in_rect(hx, hy, rect):
    lo_x, lo_y, hi_x, hi_y = rect
    return lo_x <= hx <= hi_x and lo_y <= hy <= hi_y


def on_apron(hx, hy):
    lo_x, hi_x = plan.APRON_HX
    return lo_x - plan.EXIT_COLUMNS <= hx <= hi_x + plan.EXIT_COLUMNS and plan.FRONT < hy <= plan.EXIT_ROWS[-1]


# ----------------------------------------------------------------------------- tests
def test_validate():
    problems = [p for p in town()["m"].validate() if "locked door without a script" not in p]
    assert not problems, "\n".join(problems)


def test_spots():
    missing = [name for name in CONTRACT if name not in spots.SPOTS]
    assert not missing, f"spots removed from layout/spots.py: {missing}"
    for name, (hx, hy, rotation) in spots.SPOTS.items():
        assert 0 <= rotation < 6, f"{name}: rotation {rotation}"
        assert g.can_center(g.tile_at(hx, hy)), f"{name} ({hx}, {hy}) is outside the centre-able grid"
    s = town()
    wrong = []
    for name, place in PLACES.items():
        hx, hy, _ = spots.SPOTS[name]
        if place == "town":
            ok = plan.inside_wall(hx, hy) and not any(in_rect(hx, hy, spec["box"]) for spec in plan.BUILDINGS.values())
        elif place == "apron":
            ok = on_apron(hx, hy) and (name == "GATE_EXIT" or g.tile_at(hx, hy) not in s["exits"])
        elif place == "pool":
            ok = (hx, hy) in s["info"]["pool"]
        elif place == "stall":
            ok = in_rect(hx, hy, plan.LANTERN_STALL)
        else:
            ok = in_rect(hx, hy, plan.BUILDINGS[place[0]]["rooms"][place[1]])
        if not ok:
            wrong.append(f"{name} ({hx}, {hy}) is not in {place}")
    assert not wrong, "\n".join(wrong)
    for name, hexpos in DOOR_SPOTS.items():
        assert spots.SPOTS[name][:2] == hexpos, f"{name} {spots.SPOTS[name][:2]} is not on its door {hexpos}"
    assert spots.tile("GATE_EXIT") in s["exits"], "GATE_EXIT is not on the exit grid"
    assert spots.tile("ENTRY") not in s["exits"], "ENTRY is on the exit grid: the game would leave at once"
    assert spots.SPOTS["BOMB"][:2] == plan.BOMB
    critters = {}
    for entry in cast.load():
        if entry["type"] == "critter":
            where = cast.spot_position(entry["spot"])[:2]
            assert where not in critters, f"{entry['spot']} and {critters[where]} stand on the same hex"
            critters[where] = entry["spot"]


def test_roofs():
    s = town()
    m = s["m"]
    roofed = {(x, y) for y in range(100) for x in range(100) if m.roof(x, y) not in (None, 1)}
    expected = {key: shack.roof_squares for key, shack in s["info"]["shacks"].items()}
    assert roofed == set().union(*expected.values()), "roof squares outside the buildings' own"
    for key, squares in expected.items():
        start = next(iter(squares))
        region = {start}
        todo = [start]
        while todo:
            x, y = todo.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in roofed and n not in region:
                    region.add(n)
                    todo.append(n)
        assert region == squares, f"{key}: its roof region touches another roof ({len(region)} squares, own {len(squares)})"
    # The player must lose the roof on every free hex of a room: all of them lie under it.
    for key, shack in s["info"]["shacks"].items():
        for hx, hy in shack.interior():
            assert (hx // 2, hy // 2) in shack.roof_squares, f"{key}: interior hex ({hx}, {hy}) is not under its roof"


def test_doors():
    s = town()
    for key, name, (hx, hy), leaf in plan.all_doors():
        tile = g.tile_at(hx, hy)
        if leaf:
            assert tile in s["doors"], f"{key} / {name}: no door object on ({hx}, {hy})"
        assert tile not in s["blocked"], f"{key} / {name}: the doorway ({hx}, {hy}) is blocked"
        free = [n for n in g.neighbors(tile) if n not in s["blocked"] and n not in s["doors"]]
        assert len(free) >= 2, f"{key} / {name}: fewer than two free hexes around the door"
    gate = g.tile_at(*plan.GATE)
    assert gate in s["doors"] and s["doors"][gate] is s["info"]["gate"], "the gate is not a door object on plan.GATE"
    # A door leaf nobody planned would be a hole in a wall. (An outhouse is a door, by proto,
    # and stands in no wall.)
    planned = {g.tile_at(*pos) for _, _, pos, leaf in plan.all_doors() if leaf} | {gate}
    found = {tile for tile, obj in s["doors"].items() if obj.pid != outdoors.OUTHOUSE}
    assert found == planned, f"unplanned doors at {[xy(t) for t in found - planned]}"


def test_reachable():
    s = town()
    reach = s["reach"]
    problems = []
    for key, name, (hx, hy), _ in plan.all_doors():
        if g.tile_at(hx, hy) not in reach:
            problems.append(f"door {key} / {name} ({hx}, {hy}) cannot be reached")
    for key, spec in plan.BUILDINGS.items():
        for room, rect in spec["rooms"].items():
            free = [(hx, hy) for hx in range(rect[0], rect[2] + 1) for hy in range(rect[1], rect[3] + 1)
                    if g.tile_at(hx, hy) not in s["blocked"]]
            cut_off = [h for h in free if g.tile_at(*h) not in reach]
            if cut_off:
                problems.append(f"{key} / {room}: {len(cut_off)} of {len(free)} free hexes cannot be reached, e.g. {cut_off[:4]}")
            if len(free) < 12:
                problems.append(f"{key} / {room}: only {len(free)} free hexes")
    # Spots: critters and bare spots stand on a free reachable hex; scripted objects need a reachable neighbour.
    kinds = {}
    for entry in cast.load():
        kinds.setdefault(entry["spot"], set()).add(entry["type"])
    for name, (hx, hy, _) in spots.SPOTS.items():
        tile = g.tile_at(hx, hy)
        kind = kinds.get(name, set())
        if name in DOOR_SPOTS or name == "BOMB" or kind & {"thing", "attach"}:
            if not any(n in reach for n in g.neighbors(tile)):
                problems.append(f"{name} ({hx}, {hy}): no reachable hex next to it")
        else:
            if tile in s["blocked"]:
                problems.append(f"{name} ({hx}, {hy}) is blocked")
            elif tile not in reach:
                problems.append(f"{name} ({hx}, {hy}) cannot be reached from ENTRY")
    bomb = g.tile_at(*plan.BOMB)
    access = [n for n in g.neighbors(bomb) if n in reach]
    if len(access) < 2:
        problems.append(f"the bomb has {len(access)} reachable neighbour hexes")
    if not reach & s["exits"]:
        problems.append("no exit-grid hex can be reached")
    assert not problems, "\n".join(problems)


def test_contained():
    s = town()
    gate = g.tile_at(*plan.GATE)
    shut = walk.door_hexes(s["doors"][gate])
    assert len(shut) == 7, "the gate must block the hexes around it while shut (MULTIHEX)"
    outside = walk.flood(s["entry"], s["blocked"] | shut, stop=s["exits"])
    leaked = [xy(t) for t in outside if plan.inside_wall(*xy(t))]
    assert not leaked, f"with the gate shut the town can be entered, e.g. at {sorted(leaked)[:5]}"
    stray = [xy(t) for t in outside if not on_apron(*xy(t))]
    assert not stray, f"ground outside the apron can be reached, e.g. {sorted(stray)[:5]}"
    inside = walk.flood(spots.tile("SIMMS_GREET"), s["blocked"] | shut, stop=s["exits"])
    escaped = [xy(t) for t in inside if not plan.inside_wall(*xy(t))]
    assert not escaped, f"with the gate shut the town can be left, e.g. at {sorted(escaped)[:5]}"
    # With the gate open the whole reachable area is town + apron.
    passage = {g.tile_at(plan.GATE[0] + dx, plan.GATE[1]) for dx in (-1, 0, 1)}
    assert passage <= s["reach"], "the open gate must be three hexes wide"
    stray = [xy(t) for t in s["reach"] if not plan.inside_wall(*xy(t)) and not on_apron(*xy(t)) and t not in passage]
    assert not stray, f"reachable ground that is neither town nor apron, e.g. {sorted(stray)[:5]}"
    # Every exit hex leaves for the world map.
    for obj in s["m"].objects[0]:
        if ids.is_exit_grid(obj.pid):
            assert obj["dest_map"] == -2, f"exit grid at {xy(obj.tile)} does not lead to the world map"


def test_camera():
    s = town()
    region = walk.camera_region(s["m"], s["entry"])
    x0, y0, x1, y1 = s["info"]["frame"]
    out = [xy(t) for t in region if not (x0 - 48 <= g.hex_center(t)[0] <= x1 + 48 and y0 - 36 <= g.hex_center(t)[1] <= y1 + 36)]
    assert not out, f"the view centre escapes the scroll frame, e.g. to {sorted(out)[:5]} ({len(region)} hexes reachable)"
    # ... and everything worth looking at can be centred.
    for name in ("ENTRY", "GATE", "BOMB", "MORIARTY", "WALTER", "BILLY", "HARDEN", "HOUSE_BED", "TRADER"):
        hx, hy, _ = spots.SPOTS[name]
        near = any(g.distance(t, g.tile_at(hx, hy)) <= 6 for t in region)
        assert near, f"the view cannot be brought near {name}"


def test_cast():
    s = town()
    m, gf = s["m"], s["gf"]
    problems = []
    for entry in cast.load():
        if entry["type"] != "attach":
            continue
        hx, hy, _ = cast.spot_position(entry["spot"])
        found = [obj for obj in m.objects_at(g.tile_at(hx, hy)) if entry["kind"] in cast._kind_of(gf, obj)]
        if not found:
            problems.append(f"{cast.describe(entry)}: no {entry['kind']} on ({hx}, {hy}) for script {entry['script']}")
    assert not problems, "\n".join(problems)
    bombs = [obj for obj in m.objects[0] if obj.pid == buildings.PID_BOMB]
    assert len(bombs) == 1 and xy(bombs[0].tile) == plan.BOMB, "there must be exactly one bomb, on plan.BOMB"


def test_keep_free():
    s = town()
    reach = s["reach"]
    reserved = layout.keep_free()
    hard = {h: why for h, why in reserved.items() if not why.startswith(("access", "doorstep"))}
    bad = [f"{h} ({why}) is blocked" for h, why in sorted(hard.items())
           if g.tile_at(*h) in s["blocked"] and g.tile_at(*h) not in s["doors"]]
    cut = [f"{h} ({why}) cannot be reached" for h, why in sorted(hard.items())
           if g.tile_at(*h) not in s["blocked"] and g.tile_at(*h) not in reach]
    soft = {}
    for h, why in reserved.items():
        if why.startswith(("access", "doorstep")):
            soft.setdefault(why, []).append(g.tile_at(*h) in reach)
    none = [f"{why}: no free reachable hex" for why, oks in sorted(soft.items()) if not any(oks)]
    assert not (bad or cut or none), "\n".join(bad + cut + none)


# Who sells from behind a counter: (spot, the furthest a customer may have to stand, in hexes).
# The engine lets the player talk from up to 8 hexes if nothing solid is in the line of fire.
COUNTERS = {"MOIRA": 4, "GOB": 5, "MORIARTY": 5, "JENNY": 6, "DOC": 3}
JUNK = 98


def shot_blocked(m, gf, a, b):
    """True if a wall or scenery that stops bullets stands between two tiles (the test the
    engine applies before it lets the player talk across a counter)."""
    for tile in g.line(a, b)[1:-1]:
        for obj in m.objects_at(tile):
            if obj.obj_type in (ids.OBJ_TYPE_WALL, ids.OBJ_TYPE_SCENERY) and not obj.flags & 0x80000010:
                if obj.obj_type == ids.OBJ_TYPE_SCENERY and gf.protos.get(obj.pid).subtype_name == "door":
                    continue
                return True
    return False


def test_dressing():
    s = town()
    m, gf, reach, blocked = s["m"], s["gf"], s["reach"], s["blocked"]
    record = s["info"].get("dressing")
    assert record, "layout/dressing.py did not run"
    problems = []
    # Containers: reachable, on a closed hex, and the first object of that hex.
    for box in record["containers"]:
        tile = g.tile_at(*box["hex"])
        where = f"{box['place']}: {box['name']} {box['hex']}"
        if not any(n in reach for n in g.neighbors(tile)):
            problems.append(f"{where} cannot be reached")
        if tile not in blocked:
            problems.append(f"{where} stands on an open hex: one could walk through it")
        if tile in s["doors"] or box["hex"] in {sp[:2] for sp in spots.SPOTS.values()}:
            problems.append(f"{where} stands on a door or a spot")
    # The cast's scripted objects must be what "the object on this hex" finds.
    for entry, obj in s["info"]["placed"]:
        if entry["type"] not in ("thing", "attach") or not hasattr(obj, "tile"):
            continue
        first = next((o for o in m.objects_at(obj.tile) if o.obj_type != ids.OBJ_TYPE_CRITTER and not o.flags & 0x08), None)
        flat = [o for o in m.objects_at(obj.tile) if o.flags & 0x08 and o.pid in (0x02000043, 0x02000158)]
        scripted = [o for o in m.objects_at(obj.tile) if o.sid != -1]
        if flat or (first is not None and scripted and first.sid == -1 and first.pid == 0x02000043):
            problems.append(f"{cast.describe(entry)}: a blocker comes before the scripted object on its hex")
    # NPCs: two free hexes beside each (to walk up to them, and for them to step aside).
    seen = set()
    for entry in cast.load():
        if entry["type"] != "critter" or entry["spot"] in seen:
            continue
        seen.add(entry["spot"])
        hx, hy, _ = cast.spot_position(entry["spot"])
        free = [n for n in g.neighbors(g.tile_at(hx, hy)) if n in reach and n not in blocked]
        if len(free) < 2:
            problems.append(f"{entry['spot']} ({hx}, {hy}) has {len(free)} free hexes beside it")
    for name, limit in COUNTERS.items():
        hx, hy, _ = spots.SPOTS[name]
        here = g.tile_at(hx, hy)
        ok = any(g.distance(t, here) <= limit and not shot_blocked(m, gf, t, here)
                 for t in g.disc(here, limit) if t in reach and t != here)
        if not ok:
            problems.append(f"{name}: no hex within {limit} from which the player can talk to them")
    # Blockers never under a door or on the exit grid.
    for obj in m.objects[0]:
        if obj.pid == 0x02000043 and (obj.tile in s["doors"] or obj.tile in s["exits"]):
            problems.append(f"a blocker under a door or on the exit grid at {xy(obj.tile)}")
    # Walter's side quest counts on two pieces of scrap lying about town (brief 5.6).
    scrap = [box for box in record["containers"] if not box["locked"] and any(name == gf.protos.name(JUNK) for name, _ in box["items"])]
    if len(scrap) < 2:
        problems.append(f"only {len(scrap)} unlocked containers hold Junk; Walter's quest wants two")
    # Night: enough visible lamps, and a light of some kind near every outer door.
    lamps = [(hx, hy) for _, _, hx, hy, _, _ in record["lights"]]
    if len(lamps) < 12:
        problems.append(f"only {len(lamps)} lamps and fires")
    lit = [obj.tile for obj in m.objects[0] if obj.light_distance > 0 and obj.light_intensity > 0]
    for key, spec in plan.BUILDINGS.items():
        for _, _, name in spec["doors"]:
            door = g.tile_at(*plan.door_hex(key, name))
            if not any(g.distance(door, t) <= 6 for t in lit):
                problems.append(f"no light within 6 hexes of the door of {key}")
    # With scripts/mgdecor.ssl built, every lock can be picked and every piece that has a
    # description carries it. (A build made with --only leaves the script out: nothing to check.)
    if gf.exists("scripts/mgdecor.int"):
        from layout import dressing

        for box in record["containers"]:
            if box["locked"] and box["obj"].sid == -1:
                problems.append(f"{box['place']}: locked {box['name']} {box['hex']} has no script: it could never be opened")
        bare = [xy(obj.tile) for obj in m.objects[0] if obj.pid in dressing.described() and obj.sid == -1]
        if bare:
            problems.append(f"furniture mgdecor.ssl describes, without the script: {bare[:6]}")
    locked = [box for box in record["containers"] if box["locked"]]
    if len(locked) != 4:
        problems.append(f"{len(locked)} locked containers; the brief asks for four besides the cast's")
    if len(record.get("sealed", ())) > 30:
        problems.append(f"{len(record['sealed'])} hexes had to be sealed off: furniture is cutting rooms up")
    assert not problems, "\n".join(problems)


def test_art():
    from layout import art

    s = town()
    m, gf, info = s["m"], s["gf"], s["info"]
    assert art.staged(gf), "the custom art is not staged: run the build's `art` step"
    summary = info.get("art")
    assert summary, "layout/art.py did not run"
    problems = []
    # the bomb: one object, the first thing on its hex, usable, its front lip free
    bomb = g.tile_at(*plan.BOMB)
    on_hex = [obj for obj in m.objects_at(bomb) if obj.obj_type != ids.OBJ_TYPE_CRITTER]
    if not on_hex or on_hex[0].pid != art.bomb_pid() or len(on_hex) != 1:
        problems.append(f"the bomb's hex holds {[hex(obj.pid) for obj in on_hex]}: it must hold the one bomb object and nothing else")
    elif on_hex[0].sid == -1 and gf.exists("scripts/mgbomb.int"):
        problems.append("the bomb carries no script")
    if not gf.protos.get(art.bomb_pid()).flags_ext & 0x800:
        problems.append("the bomb's proto lacks the use action (flags_ext 0x800): a click would only examine it")
    for dx, dy in buildings.BOMB_ACCESS:
        tile = g.tile_at(plan.BOMB[0] + dx, plan.BOMB[1] + dy)
        if tile in s["blocked"] or tile not in s["reach"]:
            problems.append(f"bomb access hex {xy(tile)} is blocked or cut off")
    # the gate: the stock door proto, MULTIHEX, wearing the door FRM
    gate = info["gate"]
    frames = gf.art.load(gate.fid).frame_count
    if gate.fid != summary["gate_fid"] or gate.pid != kit_gate() or not gate.flags & 0x800 or frames != 5:
        problems.append(f"the gate is pid 0x{gate.pid:08X} fid 0x{gate.fid:08X} with {frames} frames, flags 0x{gate.flags:X}")
    # decor script on the pieces that replaced described furniture
    if gf.exists("scripts/mgdecor.int"):
        for pid in sorted(art.decor_pids()):
            found = [obj for obj in m.objects[0] if obj.pid == pid]
            if not found:
                problems.append(f"art piece 0x{pid:08X} ({gf.protos.name(pid)}) is in registry.ART_NAMES but not on the map")
            for obj in found:
                if obj.sid == -1:
                    problems.append(f"{gf.protos.name(pid)} at {xy(obj.tile)} carries no script")
    # lamps give light; animated parts carry the animation script
    for name, hx, hy, radius, percent in summary["lamps"]:
        lit = [obj for obj in m.objects_at(g.tile_at(hx, hy)) if obj.light_distance == radius and obj.light_intensity > 0]
        if not lit:
            problems.append(f"lamp piece {name} at ({hx}, {hy}) gives no light")
    manifest = summary["document"]["pieces"]
    for name, piece in manifest.items():
        if piece["verdict"] != "cut" and not piece["placed"] and not piece["optional"]:
            problems.append(f"art piece {name} is neither placed nor listed as optional")
    assert not problems, "\n".join(problems)


def kit_gate():
    from layout import kit

    return kit.GATE


# Who stands behind furniture on purpose, and how much of them has to stay in reach of a click.
BEHIND_FURNITURE = {"critter JENNY": 0.45}          # behind the Brass Lantern's counter: head and shoulders
CLICK_SHARE = 0.6        # of the pixels a click could reach in the town without the art
CLICK_FLOOR = 150        # targets with fewer reachable pixels than this in the stock town are indoors (under a roof)


def test_clickable():
    from layout import art, sight

    s = town()
    assert art.staged(s["gf"]), "the custom art is not staged: run the build's `art` step"
    table = sight.compare(s["gf"])
    problems = []
    for name, (before, after, new) in table.items():
        if before < CLICK_FLOOR or name == "attach GATE":        # the gate is itself a piece of the art: below
            continue
        share = BEHIND_FURNITURE.get(name, CLICK_SHARE)
        if after < before * share:
            worst = ", ".join(f"{who} ({pixels} px)" for who, pixels in sorted(new.items(), key=lambda kv: -kv[1])[:3])
            problems.append(f"{name}: {after} of {before} clickable pixels left ({round(100 * after / before)} %), covered by {worst}")
    for name in ("thing BOMB", "attach GATE"):
        row = table.get(name)
        if not row or row[1] < 3000:
            problems.append(f"{name}: only {row[1] if row else 0} pixels of it can be clicked")
    assert not problems, "\n".join(problems)


# What a click (or a tap on a phone) must be able to reach of each sprite, whatever stood there
# before: clickable() above only compares the town with and without the art, so a door or a person
# that was hidden in BOTH towns passed it (the playtest found three doors under their own roofs, and
# Lucy West, Harden Simms and Moira's mercenary behind their rooms' front and left walls).
SEEN_DOOR = 0.50          # an outer door, every roof on
SEEN_PERSON = 0.40        # a cast member or a standing post; indoors with that building's roof off.
                          # Jenny Stahl has 45 %: head and shoulders over the Brass Lantern's counter.
NOT_STOOD_ON = ("post NOVA_BED",)      # a marker beside a bed, nobody's post


def test_seen():
    from layout import art, sight

    s = town()
    assert art.staged(s["gf"]), "the custom art is not staged: run the build's `art` step"
    problems = []
    for name, (total, free, covers, where) in sight.seen(s["gf"]).items():
        if name in NOT_STOOD_ON:
            continue
        need = SEEN_DOOR if name.startswith("door ") else SEEN_PERSON
        if total and free < total * need:
            worst = ", ".join(f"{who} ({pixels} px)" for who, pixels in sorted(covers.items(), key=lambda kv: -kv[1])[:3])
            problems.append(f"{name} ({where}): a click reaches {free} of {total} pixels ({round(100 * free / total)} %, "
                            f"needs {round(100 * need)} %), covered by {worst}")
    for key, spec in plan.BUILDINGS.items():
        for side, pos, name in spec.get("doors", ()):
            if side not in ("front", "left"):
                problems.append(f"door {key} / {name} is in the {side} wall, under the building's own roof: "
                                f"outer doors go in a front or a left wall (layout/plan.py)")
    assert not problems, "\n".join(problems)


def test_trim():
    """Nobody can stand under a roof from BEHIND a building (the playtest: the church roof came off
    in the lane to Craterside, and a tap on Mother Maya answered "You cannot get there")."""
    s = town()
    free = layout.keep_free()
    under = []
    for key, shack in s["info"]["shacks"].items():
        hy = shack.hy_lo - 1
        for hx in range(shack.hx_lo, shack.hx_hi):
            if (hx // 2, hy // 2) not in shack.roof_squares:
                continue
            if g.tile_at(hx, hy) in s["reach"] and (hx, hy) not in free:
                under.append(f"{key}: ({hx}, {hy}) behind the back wall can be walked on and lies under the roof")
    assert not under, "\n".join(under[:12])


TESTS = [test_validate, test_spots, test_roofs, test_doors, test_reachable, test_contained, test_keep_free,
         test_dressing, test_camera, test_cast, test_art, test_clickable, test_seen, test_trim]


def main(argv):
    global STAGING
    args = argv[1:]
    STAGING = os.path.join(MOD, "out-layout")
    own = True
    if args[:1] == ["--staging"]:
        STAGING = os.path.abspath(args[1])
        args = args[2:]
        own = False
    # The default staging tree is this test's own: stage it afresh every time (a tree left from an
    # earlier build has yesterday's scripts, or no custom art at all). A tree named with --staging is
    # somebody's build and is taken as it is, unless it is empty.
    if own:
        shutil.rmtree(STAGING, ignore_errors=True)
    if own or not os.path.exists(os.path.join(STAGING, "data", "maps.txt")):
        subprocess.run([sys.executable, os.path.join(MOD, "build.py"), "--out", STAGING, "ids", "data", "protos", "art", "scripts"],
                       check=True, stdout=subprocess.DEVNULL)
    failed = 0
    for test in TESTS:
        name = test.__name__[5:]
        if args and name not in args:
            continue
        try:
            test()
            print(f"PASS  {name}")
        except AssertionError as problem:
            failed += 1
            print(f"FAIL  {name}\n      " + str(problem).replace("\n", "\n      "))
        except Exception:
            failed += 1
            print(f"ERROR {name}\n" + traceback.format_exc())
    print(f"{'FAILED' if failed else 'ok'}: {failed} failing")
    return 1 if failed else 0


STAGING = None
if __name__ == "__main__":
    sys.exit(main(sys.argv))
