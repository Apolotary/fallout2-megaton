#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Offline PLAYABILITY check of a mock-up map against the town it was made from.

    python3 mod/megaton-art/town/check.py <mock name | path to a mock's .map>     (town/mock.py runs it for you)

A mock-up is the town snapshot (town/snapshot/) with new pieces, roofs and floors on it. This
applies the town's own rules to it - the code of mod/megaton/layout/walk.py (the engine's blocking
rule and flood fills) and mod/megaton/layout/sight.py (which pixels a click can reach) is
IMPORTED and run as it is, read-only; the assertions of mod/megaton/tests/layout/test_layout.py
are restated here against the facts town/probe.py wrote into snapshot/town.json, so that a mock
is judged by the plan its snapshot was built from, whatever the town's sources say by now.

FAIL  = the town's own tests would fail once this is merged (or the map is broken):
    keep_free   a reserved hex (spot, doorway, gateway, path centre line, bomb access) is blocked or
                cut off; a doorstep / access group has no free reachable hex left
    doors       a doorway is blocked, has fewer than two free hexes round it, or lost its door
    reachable   a door, a room's free hexes, a spot, the bomb or the exit grid cannot be reached from ENTRY
    contained   with the gate shut the wall leaks (a replaced stretch of wall left a gap)
    dressing    a container cannot be reached, an NPC has fewer than two free hexes beside him, a
                merchant cannot be talked to across his counter, an outer door has no light within 6 hexes
    clickable   a door, cast member, scripted object, container or standing post keeps less than the
                town's share (60 %; Jenny 45 %) of the pixels a click reaches in the STOCK town; the
                bomb or the gate keeps fewer than 3,000 px
    roofs       a building lost roof squares, its roof now touches another roof region (they would
                hide together), or a room hex is no longer under its roof
    map         MapFile.validate() errors, objects whose proto or art is missing
    seen        (the town's later test) an OUTER door keeps less than half of its pixels with every roof
                on, or a cast member / standing post less than two fifths of his, indoors with only his
                own building's roof off - and the mock made it so (or made it worse)
    trim        a hex of the row behind a building's back wall, under the roof's trim, can be walked on
                (standing there would take the roof off from outside) and could not before
WARN  = legal but worth a look:
    covered     a click target lost 15 % or more of the pixels it has TODAY to something new (named)
    lane        new blocking hexes inside a path's kept-free width (the tests only guard its centre line)
    walker      somebody walking a path's centre line (a stand-in every third hex) or standing on a
                waypoint is now less than half visible, hidden by something new (named)
    pocket      free hexes that could be reached before and cannot now (the town build would seal them)
    roof        new roof squares over walkable ground that hide when the player steps under them
INFO  = what the mock changed (new / removed objects per piece, newly blocked hexes, roof and floor squares).

Not modelled (same as the town's tests): the see-through circle round the player, moving critters.
Exit status 1 when anything FAILs.
"""
import json
import os
import sys
from collections import Counter

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
TOWN = os.path.join(ROOT, "mod", "megaton")
SNAP = os.path.join(HERE, "snapshot")
for _path in (os.path.join(ROOT, "tools"),):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from f2lib import GameFiles, MapFile, geometry as g, ids      # noqa: E402

PID_STAND_IN = 0x01000003
SECRET_BLOCK = 0x02000043
COVERED_WARN = 0.15          # share of today's clickable pixels a target may lose before it is listed
WALKER_VISIBLE = 0.5
WALKER_STEP = 3
POCKET_FAIL = 12
ROOF_NEVER_HIDE = 0x20000000


def town_code():
    """(walk, sight, shot_blocked): the town's own modules, imported read-only."""
    for path in (os.path.join(TOWN, "tests", "layout"), TOWN):
        if path not in sys.path:
            sys.path.insert(0, path)
    from layout import sight, walk       # mod/megaton/layout/sight.py, walk.py
    import test_layout                   # mod/megaton/tests/layout/test_layout.py
    return walk, sight, test_layout.shot_blocked


def load_facts(snapshot_dir=SNAP):
    with open(os.path.join(snapshot_dir, "town.json")) as f:
        return json.load(f)


# ----------------------------------------------------------------- plan (from the facts)
def inside_wall(facts, hx, hy):
    """mod/megaton/layout/plan.py inside_wall(), on the outline the snapshot was built with."""
    points = [tuple(p) for p in facts["plan"]["outline"]]
    inside = False
    for i, (ax, ay) in enumerate(points):
        bx, by = points[(i + 1) % len(points)]
        if ax == bx and min(ay, by) <= hy < max(ay, by) and hx < ax:
            inside = not inside
    on_wall = any((ax == bx == hx and min(ay, by) <= hy <= max(ay, by)) or
                  (ay == by == hy and min(ax, bx) <= hx <= max(ax, bx))
                  for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]))
    return inside and not on_wall


def on_apron(facts, hx, hy):
    plan = facts["plan"]
    lo_x, hi_x = plan["apron_hx"]
    return lo_x - plan["exit_columns"] <= hx <= hi_x + plan["exit_columns"] and plan["front"] < hy <= plan["exit_rows"][-1]


# ------------------------------------------------------------------------------ helpers
def object_key(obj):
    return (obj.tile, obj.pid, obj.fid)


def difference(base, mock):
    """(objects only in the mock, objects only in the base), by (tile, pid, fid) as multisets."""
    have = Counter(object_key(o) for o in base.objects[0])
    added = []
    for obj in mock.objects[0]:
        key = object_key(obj)
        if have[key] > 0:
            have[key] -= 1
        else:
            added.append(obj)
    have = Counter(object_key(o) for o in mock.objects[0])
    removed = []
    for obj in base.objects[0]:
        key = object_key(obj)
        if have[key] > 0:
            have[key] -= 1
        else:
            removed.append(obj)
    return added, removed


def piece_names(manifest):
    names = {}
    for name, piece in (manifest or {}).get("pieces", {}).items():
        for part in piece["parts"]:
            names[int(part["pid"], 16)] = name
    return names


class Namer:
    def __init__(self, gf, manifest):
        self.gf = gf
        self.pieces = piece_names(manifest)

    def __call__(self, obj):
        try:
            title = self.gf.protos.name(obj.pid)
        except Exception:                   # noqa: BLE001
            title = f"0x{obj.pid:08X}"
        piece = self.pieces.get(obj.pid)
        hx, hy = g.tile_xy(obj.tile)
        return f"{title} [{piece}] ({hx}, {hy})" if piece else f"{title} ({hx}, {hy})"


def find_target(m, record):
    peers = [o for o in m.objects_at(record["tile"]) if o.pid == int(record["pid"], 16)]
    return peers[record["ordinal"]] if record["ordinal"] < len(peers) else (peers[0] if peers else None)


def with_stand_ins(m, facts, extra=()):
    """{name: object} of every click target on map `m`; stand-in villagers are ADDED to m
    (work on a copy). extra: [(name, tile, rotation)] more stand-ins (walkers)."""
    found = {}
    missing = []
    for record in facts["targets"]:
        if record["stand_in"]:
            found[record["name"]] = m.add_object(PID_STAND_IN, record["tile"], rotation=record["rotation"])
        else:
            obj = find_target(m, record)
            if obj is None:
                missing.append(record)
            else:
                found[record["name"]] = obj
    for name, tile, rotation in extra:
        found[name] = m.add_object(PID_STAND_IN, tile, rotation=rotation)
    return found, missing


def copy_map(m, gf):
    return MapFile.from_bytes(m.to_bytes(), gf)


def roof_regions(m):
    """(set of roofed squares, {square: region id}) by the engine's 4-neighbour fill; never-hide
    squares neither hide nor pass the fill on, so each is a region of its own."""
    import numpy as np
    words = m.tiles[0]
    roofs = (words >> 16) & 0xFFF
    roofed = {(int(sq) % 100, int(sq) // 100) for sq in np.flatnonzero(roofs != 1)}
    stay = {(int(sq) % 100, int(sq) // 100) for sq in np.flatnonzero((roofs != 1) & ((words & ROOF_NEVER_HIDE) != 0))}
    region = {}
    count = 0
    for start in sorted(roofed):
        if start in region:
            continue
        count += 1
        region[start] = count
        if start in stay:
            continue
        todo = [start]
        while todo:
            x, y = todo.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in roofed and n not in region and n not in stay:
                    region[n] = count
                    todo.append(n)
    return roofed, region, stay


# -------------------------------------------------------------------------------- check
def run(mock, gf, facts=None, base=None, manifest=None, walkers=True, snapshot_dir=SNAP):
    """Check MapFile `mock` (built from the snapshot). Returns the report dict."""
    walk, sight, shot_blocked = town_code()
    facts = facts or load_facts(snapshot_dir)
    if base is None:
        with open(os.path.join(snapshot_dir, "megaton.map"), "rb") as f:
            base = MapFile.from_bytes(f.read(), gf)
    name_of = Namer(gf, manifest)
    plan = facts["plan"]
    T = lambda h: g.tile_at(h[0], h[1])          # noqa: E731
    xy = g.tile_xy
    items = []

    def note(level, rule, text):
        items.append({"level": level, "rule": rule, "text": text})

    # ---- the map itself
    for problem in mock.validate():
        if problem.startswith("error") and "not registered in data/maps.txt" not in problem:
            note("fail", "map", problem)
    added, removed = difference(base, mock)
    for obj in added:
        try:
            gf.protos.get(obj.pid)
            if gf.art.load(obj.fid) is None:
                raise ValueError("no art")
        except Exception as error:               # noqa: BLE001
            note("fail", "map", f"new object 0x{obj.pid:08X} on {xy(obj.tile)}: its proto or art cannot be loaded ({error})")

    # ---- blocking and reach
    blocked_b, doors_b, exits_b = walk.survey(base)
    blocked, doors, exits = walk.survey(mock)
    entry = facts["entry"]
    reach_b = walk.flood(entry, blocked_b, stop=exits_b)
    reach = walk.flood(entry, blocked, stop=exits)
    newly_blocked = sorted(blocked - blocked_b)
    blockers = {}
    for obj in mock.objects[0]:
        if obj.tile in blocked and obj.tile not in blockers and obj.obj_type in (ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_WALL) \
                and not obj.flags & 0x11:
            blockers[obj.tile] = obj

    added_ids = {id(obj) for obj in added}
    new_parts = [(obj.tile, name_of.pieces[obj.pid]) for obj in added if obj.pid in name_of.pieces]

    def who(tile):
        obj = blockers.get(tile)
        if obj is None:                          # a MULTIHEX neighbour
            for n in g.neighbors(tile):
                if n in blockers and blockers[n].flags & 0x800:
                    obj = blockers[n]
        if obj is None:
            return "something"
        if obj.pid == SECRET_BLOCK and id(obj) in added_ids and new_parts:       # the invisible blocker of a new piece
            distance, piece = min((g.distance(tile, t), piece) for t, piece in new_parts)
            if distance <= 5:
                return f"a blocker of [{piece}] {xy(tile)}"
        return name_of(obj)

    # keep_free (test_keep_free)
    told = set()
    soft = {}
    for hx, hy, why in facts["keep_free"]:
        tile = g.tile_at(hx, hy)
        if why.startswith(("access", "doorstep")):
            soft.setdefault(why, []).append(tile)
            continue
        was_ok = tile not in blocked_b or tile in doors_b
        if tile in blocked and tile not in doors:
            told.add(tile)
            note("fail" if was_ok else "info", "keep_free", f"({hx}, {hy}) ({why}) is blocked by {who(tile)}"
                 + ("" if was_ok else " [already so in the snapshot]"))
        elif tile not in blocked and tile not in reach and tile in reach_b:
            note("fail", "keep_free", f"({hx}, {hy}) ({why}) can no longer be reached from ENTRY")
    for why, group in sorted(soft.items()):
        if not any(t in reach for t in group) and any(t in reach_b for t in group):
            note("fail", "keep_free", f"{why}: no free reachable hex left ({', '.join(str(xy(t)) for t in group[:6])})")

    # doors (test_doors) and reach (test_reachable)
    for door in plan["doors"]:
        tile = T(door["hex"])
        label = f"door {door['building']} / {door['name']} {tuple(door['hex'])}"
        if door["leaf"] and tile not in doors and tile in doors_b:
            note("fail", "doors", f"{label}: the door object is gone")
        if tile in blocked:
            note("fail", "doors", f"{label}: the doorway is blocked by {who(tile)}")
        free = [n for n in g.neighbors(tile) if n not in blocked and n not in doors]
        free_b = [n for n in g.neighbors(tile) if n not in blocked_b and n not in doors_b]
        if len(free) < 2 <= len(free_b):
            note("fail", "doors", f"{label}: fewer than two free hexes around the door")
        if tile not in reach and tile in reach_b:
            note("fail", "reachable", f"{label} cannot be reached from ENTRY")
    for key, building in plan["buildings"].items():
        for room, rect in building["rooms"].items():
            free = [(hx, hy) for hx in range(rect[0], rect[2] + 1) for hy in range(rect[1], rect[3] + 1)
                    if g.tile_at(hx, hy) not in blocked]
            cut = [h for h in free if T(h) not in reach and T(h) in reach_b]
            if cut:
                note("fail", "reachable", f"{key} / {room}: {len(cut)} free hexes cannot be reached any more, e.g. {cut[:4]}")
            if len(free) < 12:
                note("fail", "reachable", f"{key} / {room}: only {len(free)} free hexes")
    for name, (hx, hy, _) in facts["spots"].items():
        tile = g.tile_at(hx, hy)
        kinds = set(facts["spot_kinds"].get(name, ()))
        if name in facts["door_spots"] or name == "BOMB" or kinds & {"thing", "attach"}:
            if not any(n in reach for n in g.neighbors(tile)) and any(n in reach_b for n in g.neighbors(tile)):
                note("fail", "reachable", f"spot {name} ({hx}, {hy}): no reachable hex next to it")
        elif tile in blocked and tile not in blocked_b:
            if tile not in told:
                note("fail", "reachable", f"spot {name} ({hx}, {hy}) is blocked by {who(tile)}")
        elif tile not in blocked and tile not in reach and tile in reach_b:
            note("fail", "reachable", f"spot {name} ({hx}, {hy}) cannot be reached from ENTRY")
    bomb = T(plan["bomb"])
    if len([n for n in g.neighbors(bomb) if n in reach]) < 2:
        note("fail", "reachable", "the bomb has fewer than two reachable neighbour hexes")
    for hx, hy in facts["bomb_access"]:
        if g.tile_at(hx, hy) in blocked or g.tile_at(hx, hy) not in reach:
            note("fail", "reachable", f"bomb access hex ({hx}, {hy}) is blocked or cut off")
    if not reach & exits:
        note("fail", "reachable", "no exit-grid hex can be reached")

    # contained (test_contained)
    gate = T(plan["gate"])
    if gate not in doors:
        note("fail", "contained", "the gate is no longer a door object on the plan's gate hex")
    else:
        shut = walk.door_hexes(doors[gate])
        outside = walk.flood(entry, blocked | shut, stop=exits)
        leaked = sorted(xy(t) for t in outside if inside_wall(facts, *xy(t)))
        if leaked:
            note("fail", "contained", f"with the gate shut the town can be entered, e.g. at {leaked[:5]}")
        stray = sorted(xy(t) for t in outside if not on_apron(facts, *xy(t)))
        if stray:
            note("fail", "contained", f"ground outside the apron can be reached, e.g. {stray[:5]}")
        starts = [g.tile_at(hx, hy) for hx, hy, _ in facts["spots"].values()
                  if inside_wall(facts, hx, hy) and g.tile_at(hx, hy) not in blocked and g.tile_at(hx, hy) in reach_b]
        inside = walk.flood(starts[0], blocked | shut, stop=exits) if starts else set()
        escaped = sorted(xy(t) for t in inside if not inside_wall(facts, *xy(t)))
        if escaped:
            note("fail", "contained", f"with the gate shut the town can be left, e.g. at {escaped[:5]} "
                 f"({len(escaped)} hexes outside the wall can be reached from inside)")
        passage = {g.tile_at(plan["gate"][0] + dx, plan["gate"][1]) for dx in (-1, 0, 1)}
        loose = sorted(xy(t) for t in reach if not inside_wall(facts, *xy(t)) and not on_apron(facts, *xy(t)) and t not in passage)
        loose_b = {xy(t) for t in reach_b if not inside_wall(facts, *xy(t)) and not on_apron(facts, *xy(t)) and t not in passage}
        if len(loose) > len(loose_b):
            note("fail", "contained", f"{len(loose) - len(loose_b)} reachable hexes are neither town nor apron, e.g. "
                 f"{[h for h in loose if h not in loose_b][:5]}")

    # dressing (test_dressing): containers, room round NPCs, counters, light at doors
    for box in facts["containers"]:
        tile = T(box["hex"])
        if not any(n in reach for n in g.neighbors(tile)) and any(n in reach_b for n in g.neighbors(tile)):
            note("fail", "dressing", f"{box['place']}: {box['name']} {tuple(box['hex'])} cannot be reached any more")
    seen = set()
    for entry_ in facts["cast"]:
        if entry_["type"] != "critter" or entry_["spot"] in seen:
            continue
        seen.add(entry_["spot"])
        hx, hy, _ = facts["spots"][entry_["spot"]]
        here = g.tile_at(hx, hy)
        free = [n for n in g.neighbors(here) if n in reach and n not in blocked]
        free_b = [n for n in g.neighbors(here) if n in reach_b and n not in blocked_b]
        if len(free) < 2 <= len(free_b):
            note("fail", "dressing", f"{entry_['spot']} ({hx}, {hy}) has {len(free)} free hexes beside it (two are needed)")
    for name, limit in facts["counters"].items():
        hx, hy, _ = facts["spots"][name]
        here = g.tile_at(hx, hy)

        def can_talk(m, reachable):
            return any(g.distance(t, here) <= limit and not shot_blocked(m, gf, t, here)
                       for t in g.disc(here, limit) if t in reachable and t != here)
        if not can_talk(mock, reach) and can_talk(base, reach_b):
            note("fail", "dressing", f"{name}: no hex within {limit} left from which the player can talk to them")
    lit = [obj.tile for obj in mock.objects[0] if obj.light_distance > 0 and obj.light_intensity > 0]
    lit_b = [obj.tile for obj in base.objects[0] if obj.light_distance > 0 and obj.light_intensity > 0]
    for key, building in plan["buildings"].items():
        for door in plan["doors"]:
            if door["building"] != key or door["name"] not in [d[2] for d in building["doors"]]:
                continue
            tile = T(door["hex"])
            if not any(g.distance(tile, t) <= 6 for t in lit) and any(g.distance(tile, t) <= 6 for t in lit_b):
                note("fail", "dressing", f"no light within 6 hexes of the door of {key} any more")

    # lanes: new blockers inside a path's kept-free width
    for a, b, width in plan["paths"]:
        centre = g.line(T(a), T(b))
        near = [t for t in newly_blocked if min(g.distance(t, c) for c in centre) <= max(0, width - 1)]
        if near:
            note("warn", "lane", f"path {tuple(a)} -> {tuple(b)} (kept free {width} hexes either side): {len(near)} newly "
                 f"blocked hex(es) within {max(0, width - 1)} of its centre line: "
                 + ", ".join(f"{xy(t)} {who(t)}" for t in near[:4]) + (" ..." if len(near) > 4 else ""))

    # pockets
    cut_off = sorted(xy(t) for t in reach_b if t not in blocked and t not in reach)
    if cut_off:
        note("fail" if len(cut_off) > POCKET_FAIL else "warn", "pocket",
             f"{len(cut_off)} free hex(es) could be reached before and cannot now, e.g. {cut_off[:6]}")

    # ---- what a click reaches (layout/sight.py clickable)
    walker_points = []
    if walkers:
        for a, b, _ in plan["paths"]:
            line = g.line(T(a), T(b))
            walker_points += [t for k, t in enumerate(line) if k % WALKER_STEP == 1]
        for name, (hx, hy, _) in facts["spots"].items():
            if name.startswith("WAY_"):
                walker_points.append(g.tile_at(hx, hy))
    taken = {obj.tile for obj in mock.objects[0] if obj.obj_type == ids.OBJ_TYPE_CRITTER} | \
            {record["tile"] for record in facts["targets"] if record["stand_in"]}
    extra = []
    for tile in dict.fromkeys(walker_points):
        if tile in taken or tile in blocked or tile in blocked_b or tile in doors:
            continue
        extra.append((f"walker {xy(tile)}", tile, 2))
    measured = {}
    for label, source in (("base", base), ("mock", mock)):
        m = copy_map(source, gf)
        found, missing = with_stand_ins(m, facts, extra)
        if label == "mock":
            for record in missing:
                note("fail", "clickable", f"{record['name']} {tuple(record['hex'])}: the object is gone from the map")
        measured[label] = sight.clickable(m, gf, found)
    click = facts["click"]
    by_name = {record["name"]: record for record in facts["targets"]}
    for name, (total, free, covers) in measured["mock"].items():
        _, free_b, covers_b = measured["base"].get(name, (0, 0, {}))
        new = {who_: px for who_, px in covers.items() if px > covers_b.get(who_, 0)}
        worst = ", ".join(f"{who_} ({px - covers_b.get(who_, 0)} px)" for who_, px in sorted(new.items(), key=lambda kv: -kv[1])[:3])
        if name.startswith("walker "):
            share, share_b = free / max(1, total), free_b / max(1, total)
            if share < WALKER_VISIBLE <= share_b:
                note("warn", "walker", f"somebody at {name[7:]} is {round(share * 100)} % visible (was {round(share_b * 100)} %): "
                     f"hidden by {worst or 'a roof'}")
            continue
        record = by_name[name]
        stock = record["stock_free"]
        where = tuple(record["hex"])
        if name in ("thing BOMB", "attach GATE"):
            if free < click["bomb_gate_min_px"]:
                note("fail", "clickable", f"{name}: only {free} px of it can be clicked (the town asks for {click['bomb_gate_min_px']})")
        elif stock >= click["floor"]:
            share = click["behind_furniture"].get(name, click["share"])
            if free < stock * share and free < free_b:
                note("fail", "clickable", f"{name} {where}: {free} of {stock} stock-town pixels left ({round(100 * free / stock)} %; "
                     f"the town's test wants {round(share * 100)} %), covered by {worst or '?'}")
                continue
        if free_b and free < free_b * (1 - COVERED_WARN):
            # a target with fewer than click["floor"] reachable pixels in the stock town stands indoors, under a roof:
            # the town's own test leaves it out (it is clicked from inside, roof off - see `seen` below)
            indoors = stock < click["floor"] and name not in ("thing BOMB", "attach GATE")
            note("info" if indoors else "warn", "covered", f"{name} {where}: clickable pixels {free_b} -> {free} "
                 f"({round(100 * free / free_b)} %), covered by {worst or '?'}"
                 + (" [indoors: only stray pixels showed past its roof; not counted by the town's test]" if indoors else ""))

    # ---- seen (test_seen): the absolute share a click reaches, own roof off for whoever is indoors
    rule = facts.get("seen") or {"door": 0.5, "person": 0.4, "not_stood_on": ["post NOVA_BED"]}
    outer = {f"door {key} / {d[2]}" for key, building in plan["buildings"].items() for d in building["doors"]}

    def building_of(hx, hy):
        for key, building in plan["buildings"].items():
            lo_x, lo_y, hi_x, hi_y = building["box"]
            if lo_x <= hx <= hi_x and lo_y <= hy <= hi_y:
                return key
        return None

    def seen_table(source):
        from render_map import NO_TILE
        m = copy_map(source, gf)
        found, _ = with_stand_ins(m, facts)
        groups = {}
        for name, obj in found.items():
            kind = name.split(" ", 1)[0]
            if kind == "door":
                if name not in outer:
                    continue
                where = None
            elif kind in ("critter", "post"):
                where = building_of(*xy(obj.tile))
            else:
                continue
            groups.setdefault(where, {})[name] = obj
        squares = m.tiles[0]
        kept = squares.copy()
        table = {}
        for where, group in groups.items():
            squares[:] = kept
            if where is not None:
                for qx, qy in plan["buildings"][where]["roof_squares"]:
                    square = m._square(qx, qy, 0)
                    squares[square] = (int(squares[square]) & 0x0000FFFF) | (NO_TILE << 16)
            for name, (total, free, covers) in sight.clickable(m, gf, group).items():
                table[name] = (total, free, covers, where or "outdoors")
        squares[:] = kept
        return table

    seen_b, seen_m = seen_table(base), seen_table(mock)
    worst_seen = []
    for name, (total, free, covers, where) in seen_m.items():
        if name in rule["not_stood_on"] or not total:
            continue
        need = rule["door"] if name.startswith("door ") else rule["person"]
        _, free_b, covers_b, _ = seen_b.get(name, (0, 0, {}, where))
        worst_seen.append((free / total, name))
        if free < total * need and free < free_b:
            new = {who_: px - covers_b.get(who_, 0) for who_, px in covers.items() if px > covers_b.get(who_, 0)}
            worst = ", ".join(f"{who_} ({px} px)" for who_, px in sorted(new.items(), key=lambda kv: -kv[1])[:3])
            note("fail", "seen", f"{name} ({where}): a click reaches {free} of {total} px ({round(100 * free / total)} %, the town's "
                 f"test wants {round(100 * need)} %; {round(100 * free_b / total)} % before), covered by {worst or '?'}")
        elif free < total * need:
            note("info", "seen", f"{name} ({where}): {round(100 * free / total)} % of it can be clicked, below the town's "
                 f"{round(100 * need)} % [already so in the snapshot]")
    if worst_seen:
        low = sorted(worst_seen)[:3]
        note("info", "seen", f"{len(worst_seen)} doors / people measured; the least reachable: "
             + ", ".join(f"{name} {round(share * 100)} %" for share, name in low))

    # ---- trim (test_trim): nobody stands under a roof from behind a building
    reserved = {(hx, hy) for hx, hy, _ in facts["keep_free"]}
    for key, building in plan["buildings"].items():
        lo_x, lo_y, hi_x, hi_y = building["box"]
        squares_here = {tuple(s) for s in building["roof_squares"]}
        hy = lo_y - 1
        walkable = [(hx, hy) for hx in range(lo_x, hi_x) if (hx // 2, hy // 2) in squares_here
                    and g.tile_at(hx, hy) in reach and (hx, hy) not in reserved and g.tile_at(hx, hy) not in reach_b]
        if walkable:
            note("fail", "trim", f"{key}: {len(walkable)} hex(es) behind its back wall, under the roof's trim, can be walked on "
                 f"now, e.g. {walkable[:4]}")

    # ---- roofs (test_roofs)
    roofed_b, region_b, _ = roof_regions(base)
    roofed, region, stay = roof_regions(mock)
    owner = {}
    for key, building in plan["buildings"].items():
        squares = {tuple(s) for s in building["roof_squares"]}
        for square in squares:
            owner[square] = key
        lost = sorted(squares - roofed)
        if lost:
            note("fail", "roofs", f"{key}: {len(lost)} of its roof squares have no roof tile now, e.g. {lost[:4]} (a hole must be "
                 f"a transparent tile, not 'no tile': the roof would not hide there)")
        ids_here = {region[s] for s in squares if s in region}
        others = sorted({s for s, r in region.items() if r in ids_here and s not in squares})
        if others:
            note("fail", "roofs", f"{key}: its roof region now includes {len(others)} other square(s), e.g. {others[:4]}: "
                 f"they hide together with it")
        if len(ids_here) > 1:
            note("fail", "roofs", f"{key}: its roof is in {len(ids_here)} separate regions (never-hide squares inside it?)")
        bare = [h for h in building["interior"] if (h[0] // 2, h[1] // 2) not in roofed]
        if bare:
            note("fail", "roofs", f"{key}: {len(bare)} interior hexes are not under its roof, e.g. {bare[:4]}")
    fresh = sorted(roofed - roofed_b - set(owner))
    if fresh:
        hiding = [s for s in fresh if s not in stay]
        under = [(2 * qx + dx, 2 * qy + dy) for qx, qy in hiding for dx in (0, 1) for dy in (0, 1)
                 if g.tile_at(2 * qx + dx, 2 * qy + dy) not in blocked]
        note("info", "roofs", f"{len(fresh)} new roof square(s) outside the buildings ({len(fresh) - len(hiding)} never-hide)")
        if under:
            note("warn", "roof", f"{len(hiding)} new roof square(s) hide when the player stands under them; {len(under)} walkable "
                 f"hexes lie under them, e.g. {under[:4]} (TileSet.never_hide keeps a roof up)")
    changed_roofs = sum(1 for s in roofed & roofed_b if mock.roof(*s) != base.roof(*s))
    changed_floors = sum(1 for qy in range(100) for qx in range(100) if mock.floor(qx, qy) != base.floor(qx, qy))

    # ---- what changed
    new_by = Counter()
    for obj in added:
        piece = name_of.pieces.get(obj.pid)
        new_by[piece or ("blocker" if obj.pid == SECRET_BLOCK else name_of(obj).rsplit(" (", 1)[0])] += 1
    note("info", "objects", f"{len(added)} new object(s): " + (", ".join(f"{k} x{v}" for k, v in new_by.most_common(14)) or "none")
         + (" ..." if len(new_by) > 14 else ""))
    if removed:
        gone = Counter(name_of(obj).rsplit(" (", 1)[0] for obj in removed)
        note("info", "objects", f"{len(removed)} object(s) removed: " + ", ".join(f"{k} x{v}" for k, v in gone.most_common(10)))
    note("info", "ground", f"{len(newly_blocked)} hex(es) newly blocked, {len(blocked_b - blocked)} freed; "
         f"{len(reach)} hexes reachable (were {len(reach_b)}); {changed_roofs} roof square(s) re-tiled, "
         f"{changed_floors} floor square(s) changed")
    counts = Counter(item["level"] for item in items)
    return {"town": facts["built"], "fail": counts["fail"], "warn": counts["warn"], "items": items,
            "added": len(added), "removed": len(removed), "newly_blocked": [list(xy(t)) for t in newly_blocked]}


def print_report(report, out=print, title="playability"):
    out(f"== {title}: against the town of {report['town']['when']} (map {report['town']['map_sha1'][:12]}) ==")
    for level in ("fail", "warn", "info"):
        for item in report["items"]:
            if item["level"] == level:
                out(f"{level.upper():<5} {item['rule']:<10} {item['text']}")
    out(f"== {report['fail']} FAIL, {report['warn']} WARN ==")


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    target = argv[1]
    mock_dir = os.path.join(ART, "build", "mock", target)
    path = target if os.path.isfile(target) else os.path.join(mock_dir, "data", "maps", "mgmock.map")
    if not os.path.exists(path):
        raise SystemExit(f"no mock map at {path}")
    data_dir = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    sys.path.insert(0, ART)
    from pipeline import data
    gf = GameFiles(overlay=[data_dir, os.path.join(SNAP, "base"), data.OUT])
    with open(path, "rb") as f:
        mock = MapFile.from_bytes(f.read(), gf)
    report = run(mock, gf, manifest=data.load_manifest())
    print_report(report)
    return 1 if report["fail"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
