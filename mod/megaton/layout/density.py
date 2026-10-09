# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Apply the reviewed density document without allocating art or replaying a mock map.

The JSON is frozen art-direction data. Parts and tiles are checked against the
staged manifest; removals and old tile indices are checked against the live map.
Only exact PIDs and coordinates affect gameplay. Display names are not selectors.
"""
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import json
from pathlib import Path

from f2lib import geometry as g
import registry


class DensityError(ValueError):
    pass


_RESERVATIONS = ContextVar("megaton_density_reservations", default=True)


@contextmanager
def reservations(enabled):
    """The no-art comparison map must retain its original stock dressing."""
    token = _RESERVATIONS.set(enabled)
    try:
        yield
    finally:
        _RESERVATIONS.reset(token)


def require(condition, message):
    if not condition:
        raise DensityError(message)


def load():
    path = Path(registry.art_dir()) / "placement-v2.json"
    if not path.exists():
        return None
    with path.open() as stream:
        return json.load(stream)


def keep_free():
    if not _RESERVATIONS.get():
        return {}
    document = load()
    return {} if document is None else {tuple(h): "density walk-under" for h in document["keep_free"]}


def is_new(piece, manifest):
    limits = manifest["v2"]["first_slot"]
    states = {p["slot"] >= limits[p["type"]] for p in piece["parts"]}
    require(len(states) == 1, "a piece mixes original and density slots")
    return states.pop()


def base_manifest(manifest, document):
    if document is None:
        require("v2" not in manifest, "density manifest requires placement-v2.json")
        return manifest
    validate(document, manifest)
    base = dict(manifest)
    base["pieces"] = {name: p for name, p in manifest["pieces"].items() if not is_new(p, manifest)}
    return base


def pid(value):
    return int(value, 16) if isinstance(value, str) else value


def object_key(item):
    hx, hy = item["hex"]
    require(0 <= hx < 200 and 0 <= hy < 200, f"object hex outside map: {item['hex']}")
    tile = g.tile_at(hx, hy)
    require(item.get("tile", tile) == tile, f"object tile/hex disagree: {item['hex']}")
    return tile, pid(item["pid"])


def expected_parts(piece, origin):
    hx, hy = origin
    return [{"layer": p["layer"], "hex": [hx+p["hex"][0], hy+p["hex"][1]],
             "pid": p["pid"], "script": p["script"],
             "light": p["light"] if p["light"] and p["light"][0] else None}
            for p in piece["parts"]]


def canonical(rows):
    return sorted(json.dumps(row, sort_keys=True) for row in rows)


def validate(document, manifest):
    pieces = manifest["pieces"]
    new = {name for name, p in pieces.items() if is_new(p, manifest)}
    require(set(document["pieces"]) == new, "density verdict table does not cover exactly the new manifest pieces")
    require(document["check"] and document["check"]["fail"] == 0, "density document has no passing mock check")
    require(document["ids"]["first_new_slot"] == manifest["v2"]["first_slot"], "density slot bases changed")
    for kind in ("scenery", "wall"):
        require(document["ids"]["slots"][kind] == len(manifest["slots"][kind]), f"density {kind} slot count changed")
    used = Counter()
    origins = set()
    free = set()
    for place in document["placements"]:
        name = place["piece"]
        require(name in pieces, f"density piece missing: {name}")
        require(name in new or name == "sg_clinic", f"unexpected original piece in density: {name}")
        piece = pieces[name]
        hx, hy = place["origin"]
        require(hx % 2 == 0 and hy % 2 == 0, f"{name}: placer origin needs even coordinates")
        require(place["how"] == "placer" and place["tile"] == g.tile_at(hx, hy), f"{name}: invalid placement method/tile")
        key = name, hx, hy
        require(key not in origins, f"duplicate placement {key}")
        origins.add(key)
        require(canonical(place["parts"]) == canonical(expected_parts(piece, (hx, hy))), f"{name}: parts differ from manifest")
        for field, offsets in (("blocks", "footprint"), ("blockers", "blockers")):
            expected = {(hx+dx, hy+dy) for dx, dy in piece[offsets]}
            require(set(map(tuple, place[field])) == expected, f"{name}: {field} differ from manifest")
            require(all(0 <= x < 200 and 0 <= y < 200 for x, y in expected), f"{name}: {field} leave map")
        expected_free = {(hx+p["hex"][0], hy+p["hex"][1]) for p in piece["parts"]
                         if p["layer"] == "main" and not p["blocking"]
                         and p["hex"] not in piece["footprint"]}
        candidates = set(map(tuple, place["free_candidates"]))
        effective = set(map(tuple, place["free"]))
        occupied = set(map(tuple, place["underlay_blocked"]))
        unreachable = set(map(tuple, place["underlay_unreachable"]))
        require(candidates == expected_free, f"{name}: walk-under candidates differ from manifest")
        require(not (effective & occupied or effective & unreachable or occupied & unreachable)
                and effective | occupied | unreachable == candidates,
                f"{name}: free/blocked/unreachable partition is incomplete or overlaps")
        free.update(effective)
        used[name] += 1
        if name in new:
            require(place["verdict"] == document["pieces"][name]["verdict"], f"{name}: placement verdict differs")
    require(set(map(tuple, document["keep_free"])) == free, "density keep_free differs from placements")
    for name, row in document["pieces"].items():
        require(row["verdict"] in ("upgrade", "acceptable", "cut"), f"{name}: invalid verdict")
        require(row["placed"] == used[name], f"{name}: placement count differs")
        require((used[name] == 0) == (row["verdict"] == "cut"), f"{name}: verdict/usage disagreement")
        require(set(map(pid, row["pids"])) == {pid(p["pid"]) for p in pieces[name]["parts"]}, f"{name}: PID table differs")
    for row in document["removed"]:
        require(row["kind"] in ("piece", "name", "put", "seal"), "unknown density object operation")
        require(row["objects"], "density object operation has no exact objects")
        for obj in row["objects"]:
            object_key(obj)
        if row["kind"] == "piece":
            name = row["piece"]
            require(name in ("sg_roof_vent", "sg_roof_antenna", "sg_clinic"), f"unexpected old piece removal: {name}")
            hx, hy = row["hex"]
            piece = pieces[name]
            expected = [(g.tile_at(hx+p["hex"][0], hy+p["hex"][1]), pid(p["pid"])) for p in piece["parts"]]
            expected += [(g.tile_at(hx+dx, hy+dy), pid(piece["blocker_pid"])) for dx, dy in piece["blockers"]]
            require(Counter(map(object_key, row["objects"])) == Counter(expected), f"{name}: incomplete old piece removal")
    section = manifest["tiles"]
    require(document["ids"]["tiles"]["first_index"] == section["first_index"], "tile base changed")
    require(document["ids"]["tiles"]["used"] == len(section["slots"]), "tile slot count changed")
    for name, roof in document["roofs"].items():
        width, height = roof["size"]
        require(roof["sheet"] in section["sheets"], f"{name}: roof sheet missing")
        sheet = section["sheets"][roof["sheet"]]
        require(not sheet["wrap"] and not sheet["decal"], f"{name}: expected a fixed roof sheet")
        require(roof["size"] == sheet["size"] == roof["sheet_size"], f"{name}: roof sheet dimensions changed")
        require(roof["tiles"] == sheet["grid"], f"{name}: roof tile positions differ from manifest sheet")
        for field in ("tiles", "was"):
            require(len(roof[field]) == height and all(len(r) == width for r in roof[field]), f"{name}: invalid roof {field} grid")
        for row in roof["tiles"]:
            for index in row:
                slot = tile_slot(index, manifest)
                require(slot["key"] == "blank" or slot["key"].startswith(roof["sheet"]+"/"), f"{name}: tile belongs to another roof sheet")
                require(index != 1, f"{name}: roof hole uses no-roof index")
    squares = set()
    for floor in document["floors"]:
        require(floor["sheet"] in section["sheets"], "floor sheet missing")
        sheet = section["sheets"][floor["sheet"]]
        require(sheet["decal"] and floor["size"] == sheet["size"], "floor sheet dimensions/type changed")
        first_x, first_y = floor["first_square"]
        width, height = floor["size"]
        for cell in floor["squares"]:
            square = tuple(cell["square"])
            dx, dy = square[0]-first_x, square[1]-first_y
            require(0 <= dx < width and 0 <= dy < height, f"floor square outside its decal: {square}")
            require(cell["key"].startswith(f"{floor['sheet']}/{dx},{dy}@"), f"floor cell belongs to another decal position: {square}")
            require(square not in squares, f"floor square repeated: {square}")
            squares.add(square)
            slot = tile_slot(cell["tile"], manifest)
            require(slot["key"] == cell["key"], f"floor slot key changed at {square}")
            require(cell["frm"] == f"mgt{cell['tile']-section['first_index']:04d}.frm", f"floor FRM changed at {square}")
            require(0 <= cell["was"] < 4096, f"floor was index invalid at {square}")
    require(document["counts"]["placements"] == len(document["placements"]), "density placement count changed")
    require(document["counts"]["floor_squares"] == len(squares), "density floor squares are missing")


def tile_slot(index, manifest):
    section = manifest["tiles"]
    offset = index-section["first_index"]
    require(0 <= offset < len(section["slots"]) and index < 4096, f"unregistered density tile {index}")
    slot = section["slots"][offset]
    require(not slot.get("reserved") and not slot.get("retired"), f"density references unavailable tile {index}")
    return slot


def tile_changes(document):
    for building, roof in document["roofs"].items():
        qx, qy = roof["first_square"]
        for dy, row in enumerate(roof["tiles"]):
            for dx, index in enumerate(row):
                yield "roof", qx+dx, qy+dy, roof["was"][dy][dx], index
    for floor in document["floors"]:
        for cell in floor["squares"]:
            yield "floor", *cell["square"], cell["was"], cell["tile"]


def prepare(m, document, manifest):
    """Validate all operations before mutating the map; return exact object removals."""
    validate(document, manifest)
    removals = []
    selected = set()
    operations = [(row["piece"] if row["kind"] == "piece" else "stock object", row["objects"]) for row in document["removed"] if row["kind"] in ("piece", "name")]
    operations += [(place["piece"], place["remove"]) for place in document["placements"]]
    for label, objects in operations:
        for item in objects:
            tile, number = object_key(item)
            found = [o for o in m.objects_at(tile) if o.pid == number and id(o) not in selected]
            require(found, f"{label}: no 0x{number:08X} on {item['hex']} to remove")
            obj = found[0]
            selected.add(id(obj))
            removals.append((obj, label, item))
    for kind, qx, qy, was, index in tile_changes(document):
        require(0 <= qx < 100 and 0 <= qy < 100, f"{kind} square outside map: {(qx,qy)}")
        require(getattr(m, kind)(qx, qy) == was, f"{kind} base changed at {(qx,qy)}: expected {was}, found {getattr(m,kind)(qx,qy)}")
    return removals


def paint(m, kind, qx, qy, index):
    """Replace only the 12-bit index, preserving the square's unrelated flags."""
    offset = qy*100+qx
    shift = 16 if kind == "roof" else 0
    mask = 0xFFF << shift
    m.tiles[0][offset] = (int(m.tiles[0][offset]) & ~mask) | (index << shift)


def combine(base, document, manifest):
    """One final placement/verdict table, retaining the original gameplay hooks."""
    result = deepcopy(base)
    dropped = {(r["piece"], tuple(r["hex"])) for r in document["removed"] if r["kind"] == "piece"}
    originals = {(p["piece"], tuple(p["origin"])) for p in base["placements"]}
    require(dropped <= originals, "density removes an absent original placement")
    result["placements"] = [p for p in result["placements"] if (p["piece"], tuple(p["origin"])) not in dropped]
    result["placements"] += deepcopy(document["placements"])
    for place in result["placements"]:
        if place["piece"] in base["pieces"]:
            place["verdict"] = base["pieces"][place["piece"]]["verdict"]
    # Retain the clinic's stock-sign replacement as provenance on its new location.
    for name, origin in dropped:
        old = next(p for p in base["placements"] if p["piece"] == name and tuple(p["origin"]) == origin)
        replacement = [p for p in result["placements"] if p["piece"] == name]
        if old["remove"]:
            require(len(replacement) == 1, f"{name}: cannot preserve stock replacement provenance")
            replacement[0]["remove"] = old["remove"] + replacement[0]["remove"]
    counts = Counter(p["piece"] for p in result["placements"])
    for name, piece in manifest["pieces"].items():
        if name in document["pieces"]:
            row = document["pieces"][name]
            result["pieces"][name] = {
                "verdict": row["verdict"], "why": row["why"], "flaws": [], "optional": None,
                "kind": piece["kind"], "script": piece["script"],
                "pids": sorted({p["pid"] for p in piece["parts"]}),
                "lamp": next(({"hex": p["hex"], "distance": p["light"][0],
                                "intensity_percent": round(p["light"][1]*100/65536)}
                               for p in piece["parts"] if p["light"] and p["light"][0]), None),
                "animated": any(p["script"] for p in piece["parts"]),
                "palette_animation": sorted(piece["report"].get("fx_pixels", {})),
                "halo": any(p["layer"] == "halo" for p in piece["parts"])}
        row = result["pieces"][name]
        row["placed"] = counts[name]
        if not counts[name] and any(n == name for n, _ in dropped):
            row.update(verdict="cut", why="Removed by the reviewed density plan; IDs remain reserved.")
        require(row["verdict"] == "cut" or counts[name] or row["optional"], f"{name}: no placement or optional reason")
    require(set(result["pieces"]) == set(manifest["pieces"]), "combined summary omits manifest pieces")
    result["density"] = deepcopy(document)
    return result


def apply(m, gf, info, summary, placer, place_rows):
    """Extend base art through the same placement/decor path, before pocket sealing."""
    from . import walk
    from .art import decor_pids

    document = load()
    if document is None:
        return summary
    manifest = placer.manifest
    removals = prepare(m, document, manifest)
    combined = combine(summary["document"], document, manifest)
    gate = info["gate"]
    gate_state = (gate.pid, gate.tile, gate.sid, gate.flags, gate.fid)
    bomb = next(p for p in combined["placements"] if p["piece"] == "mgb_bomb_states")
    require(bomb["how"] == "object", "density changed the bomb's script-owned placement")
    require(not any(o is gate for o, _, _ in removals), "density would remove the gate")
    removed_keys = set()
    for obj, label, item in removals:
        removed_keys.add((obj.tile, obj.pid))
        m.remove_object(obj)
        summary["removed"].append((tuple(item["hex"]), pid(item["pid"]), f"0x{pid(item['pid']):08X}", label))
    record = info.get("dressing")
    if record:
        record["objects"] = [row for row in record["objects"] if (g.tile_at(row[3], row[4]), row[2]) not in removed_keys]
        record["lights"] = [row for row in record["lights"]
                            if any(o.light_distance == row[4] and o.light_intensity > 0
                                   for o in m.objects_at(g.tile_at(row[2], row[3])))]
        record["scripted"] = [row for row in record["scripted"]
                              if any(o.sid != -1 for o in m.objects_at(g.tile_at(*row[2])))]
    added = []
    for row in document["removed"]:
        if row["kind"] not in ("put", "seal"):
            continue
        for item in row["objects"]:
            tile, number = object_key(item)
            require(not any(o.pid == number for o in m.objects_at(tile)), f"density stock addition already exists at {item['hex']}")
            m.add_object(number, tile)
            added.append((number, tuple(item["hex"])))
            if record:
                record["objects"].append(("density", f"0x{number:08X}", number, *item["hex"]))
    changes = list(tile_changes(document))
    for kind, qx, qy, was, index in changes:
        if kind == "roof":
            paint(m, kind, qx, qy, index)
    more_placed, _, more_scripted = place_rows(document["placements"])
    for kind, qx, qy, was, index in changes:
        if kind == "floor":
            paint(m, kind, qx, qy, index)
    dropped = {(r["piece"], tuple(r["hex"])) for r in document["removed"] if r["kind"] == "piece"}
    summary["placed"] = [row for row in summary["placed"] if (row[0], row[1]) not in dropped] + more_placed
    # Rebuild lamp rows from final placement parts, avoiding stale removed lamps.
    summary["lamps"] = [(p["piece"], *part["hex"], part["light"][0], round(part["light"][1]*100/65536))
                        for p in combined["placements"] if p["how"] != "object"
                        for part in p["parts"] if part["light"]]
    summary["scripted"] = [(name, where) for name, where in summary["scripted"]
                           if any(o.pid in {pid(p["pid"]) for p in manifest["pieces"][name]["parts"]} & decor_pids() and o.sid != -1
                                  for o in m.objects_at(g.tile_at(*where)))] + more_scripted
    summary["document"] = combined
    summary["density"] = {"added_stock": added, "roofs": len(document["roofs"]),
                          "floor_squares": sum(len(f["squares"]) for f in document["floors"]),
                          "keep_free": len(document["keep_free"])}
    require((gate.pid, gate.tile, gate.sid, gate.flags, gate.fid) == gate_state, "density changed the stock gate contract")
    require(set(map(tuple, bomb["blockers"])) == info["bomb_blocked"], "density changed the bomb blockers")
    blocked, _, exits = walk.survey(m)
    reachable = walk.flood(m.entering_tile, blocked, stop=exits)
    for hx, hy in document["keep_free"]:
        require(g.tile_at(hx, hy) not in blocked, f"density walk-under hex {(hx,hy)} is blocked")
        require(g.tile_at(hx, hy) in reachable, f"density walk-under hex {(hx,hy)} is unreachable")
    return summary
