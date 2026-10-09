# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Where one can walk on a built map: the engine's own blocking rule, and flood fills on it.

A hex is closed to movement when a critter, scenery or wall object without the
NO_BLOCK flag stands on it, or a MULTIHEX one on a neighbouring hex
(_obj_blocking_at, object.cc:2387). Items and misc objects (exit grids,
scroll blockers) never block. Doors are scenery: a closed door blocks its hex
until somebody opens it, which the player does by using it and NPCs do on
their way (animation.cc canUseDoor: unlocked doors only). The functions here
therefore take the door hexes as a separate set and let the caller decide
which of them count as open.
"""
from collections import deque

from f2lib import geometry as g, ids

OBJECT_HIDDEN = 0x01
OBJECT_NO_BLOCK = 0x10
OBJECT_MULTIHEX = 0x800


def survey(m, elevation=0, critters=False):
    """(blocked tiles, {door tile: door object}, exit-grid tiles) of one elevation.

    Door hexes are NOT in the blocked set. critters=False ignores critters:
    they move, and a spot test wants to know about the ground they stand on.
    """
    blocked = set()
    doors = {}
    exits = set()
    for obj in m.objects[elevation]:
        if not g.is_valid(obj.tile):
            continue
        if ids.is_exit_grid(obj.pid):
            exits.add(obj.tile)
            continue
        if obj.flags & (OBJECT_HIDDEN | OBJECT_NO_BLOCK):
            continue
        kind = obj.obj_type
        if kind == ids.OBJ_TYPE_CRITTER and not critters:
            continue
        if kind not in (ids.OBJ_TYPE_CRITTER, ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_WALL):
            continue
        if kind == ids.OBJ_TYPE_SCENERY and m.gf.protos.get(obj.pid).subtype_name == "door":
            doors[obj.tile] = obj
            continue
        blocked.add(obj.tile)
        if obj.flags & OBJECT_MULTIHEX:
            blocked.update(t for t in g.neighbors(obj.tile) if t != -1)
    return blocked, doors, exits


def door_hexes(door):
    """Tiles a door closes while it is shut: its own, and the six around a MULTIHEX one (the gate)."""
    tiles = {door.tile}
    if door.flags & OBJECT_MULTIHEX:
        tiles.update(t for t in g.neighbors(door.tile) if t != -1)
    return tiles


def flood(start, blocked, stop=()):
    """Tiles reachable from `start` over free hexes. Tiles in `stop` are reached but not left
    (an exit grid ends the walk: the player is on the world map)."""
    stop = set(stop)
    if start in blocked:
        return set()
    seen = {start}
    queue = deque([start])
    while queue:
        tile = queue.popleft()
        if tile in stop:
            continue
        for neighbour in g.neighbors(tile):
            if neighbour == -1 or neighbour in seen or neighbour in blocked or g.is_edge(neighbour):
                continue
            seen.add(neighbour)
            queue.append(neighbour)
    return seen


def reachable(m, start, closed_doors=(), elevation=0):
    """Tiles the player can reach from `start`, opening every door except `closed_doors`."""
    blocked, doors, exits = survey(m, elevation)
    return flood(start, blocked | set(closed_doors), stop=exits)


def camera_region(m, start, elevation=0, limit=40000):
    """Tiles the view centre can be moved to from `start` by scrolling.

    One scroll step moves the centre 32 px sideways and / or 24 px up or down
    (mapScroll, map.cc:603); a hex with a scroll blocker refuses the centre
    (tile.cc:564), as does anything outside the centre-able region."""
    blockers = {obj.tile for obj in m.objects[elevation] if obj.pid == ids.SCROLL_BLOCKER_PID}
    seen = {start}
    queue = deque([start])
    while queue and len(seen) < limit:
        tile = queue.popleft()
        x, y = g.hex_center(tile)
        for dx in (-32, 0, 32):
            for dy in (-24, 0, 24):
                if not dx and not dy:
                    continue
                target = g.hex_from_world(x + dx, y + dy)
                if target == -1 or target in seen or target in blockers or not g.can_center(target):
                    continue
                seen.add(target)
                queue.append(target)
    return seen
