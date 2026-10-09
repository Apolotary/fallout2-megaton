# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""What the mouse can reach on a built map: who and what is hidden behind what.

    cd mod/megaton && python3 -m layout.sight [staging dir]     the town with and without the custom art, side by side
    cd mod/megaton && python3 -m layout.sight --seen [staging dir]   how much of every outer door, cast member and
                                                                     standing post a click can reach at all

The engine gives a click (and the "look at" cursor, and a tap on a phone) to the LAST opaque
sprite under the cursor in its picking order, which is the painting order of the hexes: tile
number rising, row by row down the screen (object.cc _obj_create_intersect_list,
game_mouse.cc gameMouseGetObjectUnderCursor). Under a roof tile it gives it to nobody. So an
object is only as clickable as the pixels of its sprite that
  - no roof tile covers, and
  - no opaque sprite of a LATER hex covers (flat shadows count: they are opaque to the mouse;
    translucent "energy" halos do not).
A tall piece that stands between the camera and a door takes every click meant for the door,
however correct the picture is. clickable() counts those pixels for a set of objects; compare()
does it for the town with and without the custom art, which is what
tests/layout/test_layout.py (clickable) asserts on and what decided several placements
(mod/megaton-art/placement.py, CLICK RULE).

Not modelled: the see-through circle around the player (inside it roofs and walls let clicks
pass) and other critters walking in front. Both only matter while somebody stands there.
"""
import os
import sys

import numpy as np

from f2lib import geometry as g, ids

from . import plan, spots

OBJECT_HIDDEN = 0x01
OBJECT_FLAT = 0x08
TRANS_NONE = 0x8000
TRANS_ANY = 0xFC000                  # any translucency flag (obj_types.h OBJECT_FLAG_0xFC000)
PID_STAND_IN = 0x01000003            # a villager: stands in for whoever walks to a spot
# Spots nobody stands on: waypoints of a walk, the view centre, the exit, the gate's own hex.
NOT_A_POST = ("WAY_", "ARRIVAL_VIEW", "GATE_EXIT", "GATE", "ENTRY", "ARRIVAL")


def clickable(m, gf, targets):
    """{name: (pixels of the sprite, pixels the mouse can reach, {what covers it: pixels})}.

    targets: {name: object on map m}."""
    from render_map import NO_TILE, MapRenderer      # tools/render_map.py

    renderer = MapRenderer(gf)
    objects = [obj for obj in m.objects[0] if not obj.flags & OBJECT_HIDDEN and g.is_valid(obj.tile)]
    order = {id(obj): (obj.tile, 0 if obj.flags & OBJECT_FLAT else 1, index) for index, obj in enumerate(objects)}
    boxes = {}
    for obj in objects:
        sprite = renderer.sprite(obj.fid, obj.frame, obj.rotation)
        if sprite is None or sprite[0].size <= 1:
            continue
        cx, cy = g.hex_center(obj.tile)
        boxes[id(obj)] = (cx + sprite[2] + obj.x, cy + sprite[3] + obj.y, sprite[1])
    squares = m.tiles.get(0)
    roofs = []
    if squares is not None:
        roof_ids = (squares >> 16) & 0xFFF
        tile_fid = ids.make_fid(ids.OBJ_TYPE_TILE, 0)
        for square in np.flatnonzero((roof_ids != NO_TILE) & ((squares >> 28) & 1 == 0)).tolist():
            sprite = renderer.sprite(tile_fid | int(roof_ids[square]))
            if sprite is not None:
                x, y = g.roof_world(square)
                roofs.append((x, y, sprite[1]))

    result = {}
    for name, target in targets.items():
        if id(target) not in boxes:
            result[name] = (0, 0, {})
            continue
        tx, ty, mask = boxes[id(target)]
        height, width = mask.shape
        free = mask.copy()
        covers = {}

        def cut(x, y, other, who):
            x0, y0 = max(x, tx), max(y, ty)
            x1, y1 = min(x + other.shape[1], tx + width), min(y + other.shape[0], ty + height)
            if x0 >= x1 or y0 >= y1:
                return
            part = other[y0 - y:y1 - y, x0 - x:x1 - x]
            region = free[y0 - ty:y1 - ty, x0 - tx:x1 - tx]
            hit = int((region & part).sum())
            if hit:
                covers[who] = covers.get(who, 0) + hit
                region &= ~part

        for x, y, other in roofs:
            cut(x, y, other, "roof")
        for obj in objects:
            if obj is target or id(obj) not in boxes or order[id(obj)] < order[id(target)]:
                continue
            if obj.obj_type == ids.OBJ_TYPE_CRITTER or (obj.flags & TRANS_ANY and not obj.flags & TRANS_NONE):
                continue                 # people move on; translucent sprites never take a click
            x, y, other = boxes[id(obj)]
            cut(x, y, other, f"{gf.protos.name(obj.pid)} {g.tile_xy(obj.tile)}")
        result[name] = (int(mask.sum()), int(free.sum()), covers)
    return result


def targets(m, gf, info):
    """{name: object}: every door, the cast, the dressing's containers, and a stand-in villager on
    every spot somebody walks to and stands on (they are ADDED to map `m`: use a throw-away build)."""
    import cast

    found = {}
    doors = {obj.tile: obj for obj in m.objects[0]
             if obj.obj_type == ids.OBJ_TYPE_SCENERY and gf.protos.get(obj.pid).subtype_name == "door"}
    for key, name, (hx, hy), leaf in plan.all_doors():
        if leaf and g.tile_at(hx, hy) in doors:
            found[f"door {key} / {name}"] = doors[g.tile_at(hx, hy)]
    for entry, obj in info["placed"]:
        if hasattr(obj, "tile") and entry["type"] in ("critter", "thing", "attach") and isinstance(entry["spot"], str):
            label = f"{entry['type']} {entry['spot']}"
            while label in found:
                label += "'"
            found[label] = obj
    for box in info.get("dressing", {}).get("containers", ()):
        found[f"container {box['place']} {box['hex']}"] = box["obj"]
    taken = {g.tile_xy(obj.tile) for obj in m.objects[0] if obj.obj_type == ids.OBJ_TYPE_CRITTER}
    held = {entry["spot"] for entry in cast.load() if entry["type"] in ("thing", "attach")}
    for name, (hx, hy, rotation) in spots.SPOTS.items():
        if (hx, hy) in taken or name in held or name.startswith(NOT_A_POST):
            continue
        found[f"post {name}"] = m.add_object(PID_STAND_IN, g.tile_at(hx, hy), rotation=rotation)
    return found


def compare(gf, log=lambda *a: None):
    """{name: (stock pixels, art pixels, {art piece that covers it: pixels})} for every target of the
    town built without and with the custom art (two throw-away builds)."""
    import layout

    measured = {}
    for art in (False, True):
        m, info = layout.build(gf, strict=False, art=art, log=log)
        measured[art] = clickable(m, gf, targets(m, gf, info))
    table = {}
    for name, (total, free, covers) in measured[True].items():
        _, stock_free, stock_covers = measured[False].get(name, (0, 0, {}))
        new = {who: pixels for who, pixels in covers.items() if who not in stock_covers}
        table[name] = (stock_free, free, new)
    return table


def _building_of(hx, hy):
    """Key of the building whose box holds the hex, or None."""
    for key, spec in plan.BUILDINGS.items():
        lo_x, lo_y, hi_x, hi_y = spec["box"]
        if lo_x <= hx <= hi_x and lo_y <= hy <= hi_y:
            return key
    return None


def seen(gf, log=lambda *a: None):
    """{name: (pixels of the sprite, pixels a click can reach, {what covers it: pixels}, where)} for
    every OUTER door, every cast critter and every standing post of the town with the art, measured
    the way the player meets each of them:

      - somebody inside a building, with that building's roof off (the engine hides it while the
        player stands under it) and every other roof on;
      - a door in an outer wall, and anybody out of doors, with every roof on.

    `where` is the building's key or "outdoors". compare() only says what the art took away; this
    is the absolute figure, and it is what tells that a door is under its own roof or that somebody
    stands right behind his room's front wall (one throw-away build)."""
    import layout

    m, info = layout.build(gf, strict=False, art=True, log=log)
    found = targets(m, gf, info)
    groups = {}
    outer = {name for _, _, name in sum((list(spec.get("doors", ())) for spec in plan.BUILDINGS.values()), [])}
    for name, obj in found.items():
        kind = name.split(" ", 1)[0]
        if kind == "door":
            if name.split(" / ", 1)[1] not in outer:
                continue                     # an inner door is met from inside: not measured here
            where = None
        elif kind in ("critter", "post"):
            where = _building_of(*g.tile_xy(obj.tile))
        else:
            continue
        groups.setdefault(where, {})[name] = obj
    squares = m.tiles[0]
    kept = squares.copy()
    result = {}
    from render_map import NO_TILE

    for where, group in groups.items():
        squares[:] = kept
        if where is not None:
            for qx, qy in info["shacks"][where].roof_squares:
                square = m._square(qx, qy, 0)
                squares[square] = (int(squares[square]) & 0x0000FFFF) | (NO_TILE << 16)
        for name, (total, free, covers) in clickable(m, gf, group).items():
            result[name] = (total, free, covers, where or "outdoors")
    squares[:] = kept
    return result


if __name__ == "__main__":             # cd mod/megaton && python3 -m layout.sight [--seen] [staging dir]
    import layout
    from f2lib import GameFiles

    args = [a for a in sys.argv[1:] if a != "--seen"]
    staging = args[0] if args else os.path.join(os.path.dirname(layout.HERE), "out")
    if "--seen" in sys.argv:
        print("share of each sprite a click can reach (own roof off for whoever is indoors), worst first")
        table = seen(GameFiles(overlay=staging))
        for name, (total, free, covers, where) in sorted(table.items(), key=lambda kv: kv[1][1] / max(kv[1][0], 1)):
            print(f"  {round(100 * free / max(total, 1)):>3} %  {free:>5} / {total:<5} {name:<32} {where:<10} "
                  + ", ".join(f"{who} {pixels}" for who, pixels in sorted(covers.items(), key=lambda kv: -kv[1])[:3]))
        sys.exit(0)
    print("pixels a click can reach: without the art, with it; only what the art changed is listed")
    for target, (before, after, new) in compare(GameFiles(overlay=staging)).items():
        if before != after:
            share = f"{round(100 * after / before)} %" if before else "-"
            print(f"  {target:<44} {before:>5} {after:>5}  {share:>6}  "
                  + ", ".join(f"{who} {pixels}" for who, pixels in sorted(new.items(), key=lambda kv: -kv[1])[:3]))
