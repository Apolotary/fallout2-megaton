#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Measure the town snapshot for the density pass and write mod/megaton-art/density.json.

    python3 mod/megaton-art/town/density.py          measures town/snapshot, writes density.json
                                                        and town/snapshot/density.png (the map of it)

Every number comes from the snapshot map and town.json (town/snapshot.py): run this again after
a new snapshot. The plan itself - who makes what, and how much - is the PLAN table below; its
counts are scaled from the measured areas, so they move with the town.

HOW A HEX IS CLASSED (outdoors, inside the wall or on the apron)
    roofed      its square carries a roof: whatever stands there is hidden until the player walks in
    blocked     something stands on it already (walls, furniture, art, the pool's goo) or it is cut off
    reserved    the town keeps it free: spots, doorways and doorsteps, the gateway, access hexes of
                scripted objects, the centre line of every path, the bomb's lip (layout.keep_free())
    lane        within a path's kept-free width: nothing that blocks, floor decals only
    flat        free, but a piece 1.1 m high standing here would cover a quarter or more of something
                the player clicks (a door, a person, a container, the bomb): floor decals only
    low         free, a 1.1 m piece is fine, a 3 m piece would cover a click target or hide somebody
                walking a path: junk, crates, pens, low stalls
    behind      free, but the hex itself lies under some roof's PICTURE (it is behind a building):
                a piece here is hidden up to `hidden_px` and shows above it - the place for rooftop
                silhouettes, upper-storey fronts and stilted shacks
    tall        free for anything up to the engine's limit (224 px = 6 m up, 300 px sideways per part)
Roofs are painted after every object, so a piece that stands in FRONT of a building is cut off where
its top reaches that building's roof on screen: a hex with a roof less than 110 px above it is at
most 'low', less than 40 px 'flat'.
"Covers" is what the engine does with a click: the last sprite painted on a pixel takes it, and
hexes are painted in rising tile number (down the screen). The test piece is 52 px wide.
"""
import json
import os
import sys
from collections import deque

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)
sys.path.insert(0, HERE)

import numpy as np                                                   # noqa: E402

from f2lib import GameFiles, MapFile, geometry as g, ids             # noqa: E402
from render_map import KIND_ROOF, MapRenderer, Overlay               # noqa: E402

from pipeline import data, tiles                                     # noqa: E402
from pipeline import tilegeo as TG                                   # noqa: E402

import check as playability                                          # noqa: E402
import districts as D                                                # noqa: E402

SNAP = os.path.join(HERE, "snapshot")
OUT = os.path.join(ART, "density.json")
LOW_PX, TALL_PX, HALF_W = 40, 110, 26
COVER_SHARE = 0.25
WALKER_SHARE = 0.5
AREA_MIN = 8
VIEW = (1280, 860)

# ------------------------------------------------------------------------------- the plan
AUTHORS = {
    "roofs": {
        "prefix": "rf_ (sheets) and rt_ (pieces)",
        "makes": "one roof SHEET per building (kit.sheet, kind='roof', size = T.Shack(box).size) and the rooftop "
                 "silhouettes: pieces that stand BEHIND a building's back wall and rise over its roof",
        "why": "the eleven identical stock roofs fill a third to a half of every view inside the wall; nothing "
               "else changes the picture as much",
        "rules": [
            "A sheet covers exactly its building's roof squares; a hole is transparent pixels, never a missing tile.",
            "Everything ON the roof is part of the sheet (patches, tarps, tyres, planks, hatches, low vents, a glowing "
            "skylight via geo.set_fx): keep it under about 0.6 m, or 1.5 squares away from the two far edges, or it is cut off.",
            "Each sheet different: other sheet sizes, another dominant material, one feature the eye finds "
            "(hole with rafters, plank patch, tarp, a painted sign seen from above, a collapsed corner).",
            "Mean luminance 85..110 like the stock roofs (the build prints it); streaked rust, grime along laps and edges.",
            "Silhouettes: origin on row hy_lo - 3 (even hx, even hy), feet on hy_lo - 2: the roof hides the lowest 2.6 m. "
            "density.json lists the free origins per building under buildings[*].behind.origins.",
        ],
    },
    "height": {
        "prefix": "hg_",
        "makes": "what fakes a second level: upper-storey shack fronts and stilted platforms that stand behind a "
                 "building and rise over its roof, towers in the wall's corners, lean-to annexes against shack "
                 "walls, ramps and stairs that lead up to all of it, and catwalk DECKS (roof tiles 96 px up)",
        "why": "Fallout 3's Megaton is a pile; ours is one storey high everywhere except the gate",
        "rules": [
            "Tall pieces only on hexes classed 'tall' (areas[*].tall) or in the behind-building strips; a part may reach "
            "224 px up and 300 px sideways from its hex - split bigger things into parts on several hexes.",
            "Nothing tall on a square in FRONT of a roof it should show over: roofs are painted after every object.",
            "A catwalk deck is roof tiles with TileSet.never_hide: one square deep along a hex row it hides nobody "
            "walking under it (the camera sees under a 2.66 m deck for 1.8 m); deeper decks hide heads. It takes "
            "the click of anything behind it on screen, so keep it off doors and people (the check says so).",
            "Stand posts on hex centres; see_through=True on anything the player can walk behind.",
        ],
    },
    "ground": {
        "prefix": "gd_ (pieces) and fl_ (floor sheets)",
        "makes": "everything at ground level: pipe runs from the water plant, cables and poles, junk heaps, stalls, "
                 "pens, the jumble against the outer wall, and FLOOR sheets - solid patches (plates, duckboards) "
                 "and decals (scrap, stains, planks, hoses lying on whatever ground is there)",
        "why": "the lanes and yards are bare dirt and the stockade is one clean line of identical sheets",
        "rules": [
            "Decals cost nothing in play: they block nothing, hide nothing and take no click. Use them on 'lane' and "
            "'flat' hexes, where nothing else may go.",
            "Low pieces (under 1.1 m) on 'low' hexes, anything on 'tall' hexes; never on 'reserved' or 'lane' hexes.",
            "Wall jumble: against the BACK and RIGHT runs of the outer wall the inner face is on camera and nothing "
            "stands behind it - build up to 224 px. The FRONT and LEFT runs stand between the camera and the town: "
            "replace sheets by same-height scrap, add height only where nothing clickable is within 8 rows behind.",
            "A decal square laid over a new kind of ground costs one tile slot (the build composes it): reuse the same "
            "decal on the same ground rather than making many near-equal ones.",
        ],
    },
}
# Per district: what goes there, by author. Counts are per 100 hexes of the class named (scaled below).
PLAN = {
    "apron": {
        "character": "what the newcomer sees first: caravan camp, the gate set, wrecks. Already layered at the gate; "
                     "the two flanks of the front wall and the ground are bare.",
        "roofs": "none (no building); rooftop silhouettes over the FRONT wall count for 'gate'",
        "height": "two watch platforms or lean-to stalls against the outside of the front wall, well left and right of the gate set",
        "ground": "decals over the whole trodden strip (ruts, dung, scrap), junk against the wall's foot, a pen for the "
                  "caravan's brahmin, front-wall jumble on the stretches the gate set does not cover",
    },
    "perimeter": {
        "character": "the strip along the inside of the stockade: empty dirt and a ruler-straight fence",
        "roofs": "none",
        "height": "a tower in each of the four cut corners and one or two stilted platforms against the back wall",
        "ground": "wall jumble along the back and right runs (car doors, fridges, signs, sheet scrap), junk heaps in the "
                  "corner pockets, the plant's pipes along the east wall",
    },
    "crater": {
        "character": "the bomb, the pool and its ring: the best dressed part of town; keep sight lines to the bomb",
        "roofs": "none",
        "height": "nothing tall inside the ring; the ring's outer edge may carry low retaining walls and steps",
        "ground": "decals on the ring (duckboards, hoses, candle wax, footprints through goo), a few low things only",
    },
    "gate": {
        "character": "the track from the gate to the pool between the sheriff's and the empty house",
        "roofs": "silhouettes behind the sheriff's and the empty house (their back strips face the pool)",
        "height": "lean-to annexes against the two houses' walls that face the track, a signal mast",
        "ground": "decals down the whole track (ruts, oil, scrap), cable runs from the power poles, junk along the walls",
    },
    "street": {
        "character": "the plaza in front of the saloon and the two lanes off the pool: the town's street, mostly lane",
        "roofs": "none (the buildings along it belong to their sides)",
        "height": "a catwalk deck across each lane mouth (never-hide, one square deep), awnings on posts",
        "ground": "market stalls on the plaza's edges, decals everywhere (the lanes are 'lane' hexes), overhead cables",
    },
    "saloon": {
        "character": "the saloon fills the back of every view of the plaza: 117 roof squares, the biggest roof in town",
        "roofs": "the saloon's sheet (13 x 9: the showpiece) and silhouettes along its back wall beside the billboard",
        "height": "an upper-storey front or stilted shack behind the saloon's right half; stairs up its side",
        "ground": "junk and kegs in the strip behind it, back-wall jumble",
    },
    "shops": {
        "character": "screen right: Craterside, church, clinic, water plant, sheriff's - five roofs, four narrow yards",
        "roofs": "five sheets; silhouettes behind Craterside, the plant and the sheriff's",
        "height": "an upper storey behind Craterside, a pipe gantry at the plant, lean-tos in the yards",
        "ground": "the plant's pipe runs and tanks, junk in the yards, right-wall jumble, decals in the yards",
    },
    "houses": {
        "character": "screen left: Billy's, common house, Lucy's, Brass Lantern, empty house - five roofs and the emptiest yards",
        "roofs": "five sheets; silhouettes behind Billy's, the common house and Lucy's",
        "height": "a stilted shack behind the common house, lean-tos against Lucy's and Billy's, a tower in the west pocket",
        "ground": "junk and a pen in the west pocket, laundry and stalls by the Brass Lantern, decals in every yard",
    },
}
# How dense: placements per 100 hexes of a class (a placement = one piece set down once).
RATE = {"tall": 4.0, "behind": 3.0, "low": 7.0, "decal_squares": 0.30}      # decal: share of the open squares that get a decal square


def log(text):
    print(f"[density] {text}", flush=True)


def measure():
    facts = playability.load_facts(SNAP)
    walk, sight, _ = playability.town_code()
    gf = GameFiles(overlay=[os.path.join(SNAP, "base"), data.OUT])
    with open(os.path.join(SNAP, "megaton.map"), "rb") as f:
        m = MapFile.from_bytes(f.read(), gf)
    plan = facts["plan"]
    T = lambda h: g.tile_at(h[0], h[1])          # noqa: E731
    blocked, doors, exits = walk.survey(m)
    reach = walk.flood(facts["entry"], blocked, stop=exits)
    roofed, _, _ = playability.roof_regions(m)

    # --- the outer wall and the distance to it
    outline = [tuple(p) for p in plan["outline"]]
    wall = set()
    segments = []
    for (ax, ay), (bx, by) in zip(outline, outline[1:] + outline[:1]):
        run = [(hx, ay) for hx in range(min(ax, bx), max(ax, bx) + 1)] if ay == by else \
              [(ax, hy) for hy in range(min(ay, by), max(ay, by) + 1)]
        wall.update(run)
        segments.append(run)
    hx_range, hy_range = range(plan["right"] - 4, plan["left"] + 5), range(plan["back"] - 4, plan["exit_rows"][-1] + 2)
    inside = {(hx, hy) for hx in hx_range for hy in hy_range if playability.inside_wall(facts, hx, hy)}
    distance = {h: 0 for h in wall}
    queue = deque(wall)
    while queue:
        h = queue.popleft()
        if distance[h] >= D.PERIMETER_DEPTH + 1:
            continue
        for n in g.neighbors(g.tile_at(*h)):
            if n == -1:
                continue
            nh = g.tile_xy(n)
            if nh not in distance and nh in inside:
                distance[nh] = distance[h] + 1
                queue.append(nh)

    # --- reserved hexes and lanes
    reserved = {(hx, hy): why for hx, hy, why in facts["keep_free"]}
    lane = set()
    centre_line = []
    for a, b, width in plan["paths"]:
        line = g.line(T(a), T(b))
        centre_line += line
        for tile in line:
            for near in g.disc(tile, max(0, width - 1)):
                lane.add(g.tile_xy(near))

    # --- what a piece standing on a hex would cover
    renderer = MapRenderer(gf)
    boxes = []                                   # (tile, x0, y0, x1, y1, name) of click targets that are on camera today
    for record in facts["targets"]:
        if record["stock_free"] < facts["click"]["floor"] and record["now_free"] < facts["click"]["floor"]:
            continue
        if record["stand_in"]:
            fid, frame, rotation = gf.protos.get(playability.PID_STAND_IN).fid, 0, record["rotation"]
            tile = record["tile"]
        else:
            obj = playability.find_target(m, record)
            if obj is None:
                continue
            fid, frame, rotation, tile = obj.fid, obj.frame, obj.rotation, obj.tile
        sprite = renderer.sprite(fid, frame, rotation)
        if sprite is None:
            continue
        cx, cy = g.hex_center(tile)
        h, w = sprite[1].shape
        boxes.append((tile, cx + sprite[2], cy + sprite[3], cx + sprite[2] + w, cy + sprite[3] + h, record["name"]))
    walker_boxes = []
    for tile in dict.fromkeys(centre_line):
        cx, cy = g.hex_center(tile)
        walker_boxes.append((tile, cx - 14, cy - 62, cx + 14, cy + 2, "walker"))

    def covered(hx, hy, height, targets, share):
        tile = g.tile_at(hx, hy)
        cx, cy = g.hex_center(tile)
        px0, py0, px1, py1 = cx - HALF_W, cy - height, cx + HALF_W, cy + 6
        for t_tile, x0, y0, x1, y1, name in targets:
            if t_tile >= tile:
                continue
            ox, oy = min(px1, x1) - max(px0, x0), min(py1, y1) - max(py0, y0)
            if ox > 0 and oy > 0 and ox * oy >= share * (x1 - x0) * (y1 - y0):
                return name
        return None

    # --- roofs over each hex's column on screen (they are painted over whatever stands there)
    scene = renderer.render(m, 0, roofs=True, kinds=True)
    roof_px = scene.kinds == KIND_ROOF
    sx0, sy0 = scene.world_rect[0], scene.world_rect[1]

    def roof_column(hx, hy):
        """(px from the hex centre up to the first roof pixel or None, px a piece here is hidden up to)."""
        cx, cy = g.hex_center(g.tile_at(hx, hy))
        x, y = cx - sx0, cy - sy0
        if not (0 <= x < roof_px.shape[1] and 0 <= y < roof_px.shape[0]):
            return None, 0
        column = roof_px[max(0, y - 224):y + 1, x][::-1]          # from the hex centre upwards
        if not column.any():
            return None, 0
        first = int(np.argmax(column))
        if first > 2:
            return first, 0
        clear = np.flatnonzero(~column)
        return 0, int(clear[0]) if len(clear) else 224

    hidden_px = {}
    # --- class of every hex
    classes = {}
    district = {}
    apron_box = D.DISTRICTS["apron"]["boxes"][0]
    for hx in hx_range:
        for hy in hy_range:
            h = (hx, hy)
            on_apron = playability.on_apron(facts, hx, hy)
            if h not in inside and not on_apron:
                continue
            name = D.district_of(hx, hy, distance.get(h)) if h in inside else ("apron" if D.in_box(hx, hy, apron_box) else None)
            if name is None:
                continue
            district[h] = name
            tile = g.tile_at(hx, hy)
            if (hx // 2, hy // 2) in roofed:
                classes[h] = "roofed"
            elif tile in blocked or tile in doors or tile in exits or tile not in reach:
                classes[h] = "blocked"
            elif h in reserved:
                classes[h] = "reserved"
            elif h in lane:
                classes[h] = "lane"
            else:
                above, hidden = roof_column(hx, hy)
                if covered(hx, hy, LOW_PX, boxes, COVER_SHARE) or (above is not None and 0 < above < LOW_PX):
                    classes[h] = "flat"
                elif above == 0:
                    classes[h] = "behind" if hidden < 200 and not covered(hx, hy, 224, boxes, COVER_SHARE) else "flat"
                    hidden_px[h] = hidden
                elif covered(hx, hy, TALL_PX, boxes, COVER_SHARE) or covered(hx, hy, TALL_PX, walker_boxes, WALKER_SHARE) \
                        or (above is not None and above < TALL_PX):
                    classes[h] = "low"
                else:
                    classes[h] = "tall"
    return dict(facts=facts, gf=gf, m=m, classes=classes, district=district, segments=segments, wall=wall, distance=distance,
                roofed=roofed, blocked=blocked, reach=reach, reserved=reserved, lane=lane, renderer=renderer, inside=inside,
                hidden_px=hidden_px)


def areas_of(classes, district, name):
    """Connected patches of free ground (tall / low / flat) of one district, biggest first."""
    free = {h for h, c in classes.items() if c in ("tall", "low", "flat", "behind") and district[h] == name}
    seen, found = set(), []
    for start in sorted(free):
        if start in seen:
            continue
        patch, todo = [], [start]
        seen.add(start)
        while todo:
            h = todo.pop()
            patch.append(h)
            for n in g.neighbors(g.tile_at(*h)):
                nh = g.tile_xy(n) if n != -1 else None
                if nh in free and nh not in seen:
                    seen.add(nh)
                    todo.append(nh)
        if len(patch) >= AREA_MIN:
            xs, ys = [h[0] for h in patch], [h[1] for h in patch]
            counts = {c: sum(1 for h in patch if classes[h] == c) for c in ("tall", "behind", "low", "flat")}
            centre = min(patch, key=lambda h: (h[0] - sum(xs) / len(xs)) ** 2 + (h[1] - sum(ys) / len(ys)) ** 2)
            found.append({"hexes": len(patch), "box": [min(xs), min(ys), max(xs), max(ys)], "centre": list(centre), **counts})
    return sorted(found, key=lambda a: -a["hexes"])


def side_of(run, plan):
    (ax, ay), (bx, by) = run[0], run[-1]
    mid_x, mid_y = (plan["right"] + plan["left"]) / 2, (plan["back"] + plan["front"]) / 2
    if ay == by:
        return "back" if ay < mid_y else "front"
    return "right" if ax < mid_x else "left"


def main():
    s = measure()
    facts, gf, m, classes, district = s["facts"], s["gf"], s["m"], s["classes"], s["district"]
    plan = facts["plan"]
    manifest = data.load_manifest()
    art_wall_pids = {int(part["pid"], 16) for piece in manifest["pieces"].values() for part in piece["parts"] if part["type"] == "wall"}
    art_pids = {int(part["pid"], 16): name for name, piece in manifest["pieces"].items() for part in piece["parts"]}

    # ---- buildings: roofs and the strips behind them
    buildings = {}
    for key, building in plan["buildings"].items():
        shack = TG.Shack(building["box"])
        hx_lo, hy_lo, hx_hi, hy_hi = building["box"]
        origins, taken = [], []
        for hx in range(hx_lo + 2, hx_hi - 1, 2):
            origin = (hx, hy_lo - 3)
            feet = [(hx, hy_lo - 2), (hx + 1, hy_lo - 2)]
            here = [art_pids[o.pid] for h in [origin] + feet for o in m.objects_at(g.tile_at(*h)) if o.pid in art_pids]
            if here:
                taken.append({"origin": list(origin), "piece": here[0]})
            elif all(classes.get(h) in ("tall", "low", "flat", "behind") for h in feet):
                origins.append(list(origin))
        strip = [(hx, hy) for hx in range(hx_lo, hx_hi + 1) for hy in range(hy_lo - 4, hy_lo)]
        buildings[key] = {
            "title": building["title"], "district": D.BUILDING_DISTRICT[key], "box": building["box"],
            "roof": {"stock": building["roof"], "sheet_size": list(shack.size), "first_square": list(shack.first),
                     "squares": len(building["roof_squares"]),
                     "wall_lines_m": {"back": round(shack.back, 2), "front": round(shack.front, 2),
                                      "right": round(shack.right, 2), "left": round(shack.left, 2),
                                      "stock_back": round(shack.stock_back, 2), "stock_front": round(shack.stock_front, 2),
                                      "w": round(shack.w, 2), "h": round(shack.h, 2)}},
            "doors": building["doors"],
            "behind": {"rows": [hy_lo - 4, hy_lo - 1], "origin_row": hy_lo - 3,
                       "free_hexes": sum(1 for h in strip if classes.get(h) in ("tall", "low", "flat", "behind")),
                       "hidden_px_on_feet_row": sorted({s["hidden_px"].get((hx, hy_lo - 2), 0) for hx in range(hx_lo + 2, hx_hi - 1, 2)}),
                       "lane_or_reserved_hexes": sum(1 for h in strip if classes.get(h) in ("lane", "reserved")),
                       "origins": origins, "taken": taken,
                       "note": "tall pieces with their origin here stand behind the back wall and show over the roof"},
        }

    # ---- roofs on camera: share of each view that is roof
    renderer = s["renderer"]
    views = {}
    for name, (hx, hy) in D.VIEWS.items():
        scene = renderer.render(m, 0, roofs=True, view=(g.tile_at(hx, hy), VIEW[0], VIEW[1]), kinds=True)
        roof_px = scene.kinds == KIND_ROOF
        x0, y0, _, _ = scene.world_rect
        seen = {}
        for key, building in plan["buildings"].items():
            count = 0
            for qx, qy in building["roof_squares"]:
                x, y = g.roof_world(qy * 100 + qx)
                cx, cy = x + 40 - x0, y + 18 - y0
                if 0 <= cx < VIEW[0] and 0 <= cy < VIEW[1]:
                    count += 1
            if count:
                seen[key] = round(count / len(building["roof_squares"]), 2)
        views[name] = {"centre": [hx, hy], "roof_share_of_view": round(float(roof_px.mean()), 3),
                       "roofs_in_view": seen}

    # ---- the outer wall, run by run
    walls = []
    for index, run in enumerate(s["segments"]):
        side = side_of(run, plan)
        replaced = sum(1 for h in run if any(o.pid in art_wall_pids or o.pid in art_pids for o in m.objects_at(g.tile_at(*h))))
        walls.append({
            "run": index, "from": list(run[0]), "to": list(run[-1]), "hexes": len(run), "side": side,
            "along": "row" if run[0][1] == run[-1][1] else "column",
            "face_on_camera": "inner" if side in ("back", "right") else "outer",
            "already_art": replaced, "stock_hexes": len(run) - replaced,
            "advice": "inner face on camera, nothing behind it: replace or pile against it up to 224 px" if side in ("back", "right")
                      else "stands between the camera and the town: keep new pieces at stock wall height (2.5 m) unless "
                           "nothing clickable is within 8 rows behind them",
        })

    # ---- what stands outdoors today, per district (walls, blockers, doors and flat things left out)
    dressing_now = {}
    for obj in m.objects[0]:
        h = g.tile_xy(obj.tile) if g.is_valid(obj.tile) else None
        if h not in district or (h[0] // 2, h[1] // 2) in s["roofed"]:
            continue
        if obj.obj_type not in (ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_ITEM) or obj.pid == playability.SECRET_BLOCK or obj.flags & 0x09:
            continue
        if obj.light_distance and gf.protos.name(obj.pid) in ("Light Source",):
            continue
        dressing_now[district[h]] = dressing_now.get(district[h], 0) + 1

    # ---- districts
    out_districts = {}
    totals = {"tall": 0, "behind": 0, "low": 0, "flat": 0, "lane": 0}
    for name in D.DISTRICT_ORDER:
        hexes = [h for h, d in district.items() if d == name]
        count = {c: sum(1 for h in hexes if classes[h] == c)
                 for c in ("roofed", "blocked", "reserved", "lane", "flat", "low", "behind", "tall")}
        for c in totals:
            totals[c] += count[c]
        outdoor = len(hexes) - count["roofed"]
        open_now = count["lane"] + count["flat"] + count["low"] + count["tall"] + count["behind"] + count["reserved"]
        areas = areas_of(classes, district, name)
        own = [key for key, b in buildings.items() if b["district"] == name]
        decal_squares = round((count["lane"] + count["flat"] + count["low"] + count["tall"]) / 4 * RATE["decal_squares"])
        behind_spots = round(count["behind"] / 100 * RATE["behind"])
        targets = {
            "roofs": {"roof_sheets": len(own), "roof_squares": sum(buildings[k]["roof"]["squares"] for k in own),
                      "silhouette_placements": sum(min(4, max(2, len(buildings[k]["behind"]["origins"]) // 2)) for k in own
                                                   if buildings[k]["behind"]["origins"])},
            "height": {"tall_placements": round(count["tall"] / 100 * RATE["tall"] * 0.5),
                       "behind_roof_placements": behind_spots, "note": PLAN[name]["height"]},
            "ground": {"low_placements": round((count["low"] + count["tall"] * 0.5) / 100 * RATE["low"]),
                       "decal_squares": decal_squares, "note": PLAN[name]["ground"]},
        }
        out_districts[name] = {
            "title": D.DISTRICTS[name]["title"], "character": PLAN[name]["character"],
            "boxes": [list(b) for b in D.DISTRICTS[name]["boxes"]] or f"every hex within {D.PERIMETER_DEPTH} of the outer wall",
            "views": [v for v, (vx, vy) in D.VIEWS.items() if district.get((vx, vy)) == name],
            "hexes": {"all": len(hexes), "outdoors": outdoor, **count,
                      "open_ground_share_of_outdoors": round(open_now / max(1, outdoor), 2)},
            "buildings": own,
            "dressing_objects_now": dressing_now.get(name, 0),
            "areas": areas[:10],
            "assign": {"roofs": PLAN[name]["roofs"], "height": PLAN[name]["height"], "ground": PLAN[name]["ground"]},
            "targets": targets,
        }
        log(f"{name:<10} {len(hexes):>5} hexes: roofed {count['roofed']:>4}, blocked {count['blocked']:>4}, reserved {count['reserved']:>3}, "
            f"lane {count['lane']:>3}, flat {count['flat']:>3}, low {count['low']:>3}, behind {count['behind']:>3}, tall {count['tall']:>4}; "
            f"{len(areas)} free area(s) of {AREA_MIN}+ hexes")

    room = tiles.budget(manifest)
    roof_squares = sum(b["roof"]["squares"] for b in buildings.values())
    summary = {
        "dressing_objects_outdoors_now": sum(dressing_now.values()),
        "art_placements_now": len(facts["art"]),
        "roof_squares_all_buildings": roof_squares,
        "free_hexes": totals,
        "targets": {
            "roofs": {"roof_sheets": len(buildings), "roof_tiles": roof_squares,
                      "new_silhouette_designs": 10,
                      "silhouette_placements": sum(d["targets"]["roofs"]["silhouette_placements"] for d in out_districts.values())},
            "height": {"new_designs": 14, "tall_placements": sum(d["targets"]["height"]["tall_placements"] for d in out_districts.values()),
                       "behind_roof_placements": sum(d["targets"]["height"]["behind_roof_placements"] for d in out_districts.values()),
                       "of_which": "at least 5 upper-storey fronts or stilted shacks behind buildings, 4 corner towers, "
                                   "8 lean-to annexes, 6 stairs or ramps, 4 catwalk decks"},
            "ground": {"new_designs": 20, "floor_sheets": 10,
                       "low_placements": sum(d["targets"]["ground"]["low_placements"] for d in out_districts.values()),
                       "decal_squares": sum(d["targets"]["ground"]["decal_squares"] for d in out_districts.values()),
                       "wall_jumble_hexes": round(sum(w["stock_hexes"] for w in walls if w["face_on_camera"] == "inner") * 0.6)},
        },
    }
    document = {
        "about": "Density plan for the Megaton clutter pass: measured on the town snapshot, then who fills what. "
                 "Written by mod/megaton-art/town/density.py; density.png beside the snapshot is the same thing as a map.",
        "town": facts["built"],
        "hex_classes": {
            "roofed": "under a roof square: hidden until the player is inside", "blocked": "taken or cut off",
            "reserved": "kept free by the town (layout.keep_free)", "lane": "inside a path's kept-free width: decals only",
            "flat": f"a {LOW_PX} px piece here would cover {int(COVER_SHARE * 100)} % of a click target: decals only",
            "low": f"a {TALL_PX} px piece here would cover a click target or half of a walker on a path: low pieces (to 1.1 m)",
            "behind": "the hex is under a roof's picture (behind a building): a piece shows only above hidden_px - "
                      "silhouettes, upper-storey fronts, stilted shacks",
            "tall": "free for anything (a part reaches at most 224 px up and 300 px sideways from its hex)",
        },
        "ids": {"scenery_pid_from": manifest["v2"]["first_pid_index"]["scenery"], "wall_pid_from": manifest["v2"]["first_pid_index"]["wall"],
                "tile_index_from": tiles.section(manifest)["first_index"] + 1, "tile_slots_free": room["free"],
                "tile_budget": {"roofs": 600, "ground": 280, "height": 80,
                                "note": f"all eleven roofs as unique sheets need {roof_squares} tiles; a decal square costs one "
                                        "tile per kind of ground it lies on; a deck square costs one"}},
        "authors": AUTHORS,
        "summary": summary,
        "views": views,
        "districts": out_districts,
        "buildings": buildings,
        "outer_wall": walls,
        "checks": "every mock goes through town/check.py (python3 mod/megaton-art/town/mock.py mocks/<name>.py): "
                  "0 FAIL is the condition for handing a placement over",
    }
    with open(OUT, "w") as f:
        json.dump(document, f, indent=1)
        f.write("\n")

    # ---- the same as a picture
    scene = renderer.render(m, 0, roofs=True)
    overlay = Overlay(scene, 1.0)
    colours = {"tall": (60, 220, 90, 120), "behind": (220, 90, 230, 130), "low": (240, 220, 60, 120), "flat": (70, 150, 255, 120),
               "lane": (255, 255, 255, 70), "reserved": (255, 70, 70, 130)}
    for cls, colour in colours.items():
        overlay.tint([g.tile_at(*h) for h, c in classes.items() if c == cls], colour)
    image = overlay.image.convert("RGB")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    legend = [("tall: anything", colours["tall"]), ("behind a roof: shows over it", colours["behind"]), ("low: up to 1.1 m", colours["low"]), ("flat: decals only (covers a click target)", colours["flat"]),
              ("lane: decals only (path width)", colours["lane"]), ("reserved by the town", colours["reserved"])]
    for k, (text, colour) in enumerate(legend):
        draw.rectangle((20, 20 + 26 * k, 44, 40 + 26 * k), fill=colour[:3])
        draw.text((52, 22 + 26 * k), text, fill=(255, 255, 255))
    picture = os.path.join(SNAP, "density.png")
    image.save(picture)
    log(f"free hexes: tall {totals['tall']}, behind a roof {totals['behind']}, low {totals['low']}, flat {totals['flat']}, lane {totals['lane']}; "
        f"{roof_squares} roof squares on {len(buildings)} buildings; {room['free']} tile slots free")
    log(f"wrote {os.path.relpath(OUT, ROOT)} and {os.path.relpath(picture, ROOT)}")


if __name__ == "__main__":
    main()
