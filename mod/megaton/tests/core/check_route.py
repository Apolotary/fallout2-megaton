#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Can Simms and Burke walk across the town? The engine's pathfinder, replayed on a built map.

    python3 mod/megaton/build.py --out mod/megaton/out-core-town --only megaton,mgsimms,... ids data protos art scripts maps
    python3 mod/megaton/tests/core/check_route.py                       (reads mod/megaton/out-core-town)
    python3 mod/megaton/tests/core/check_route.py mod/megaton/out       (any staging dir with the real town)

fallout2-ce's pathfinderFindPath (animation.cc) is an A* search that gives up
once 2000 hexes have been expanded, and its estimate is so much smaller than
its step cost that in open country this happens on walks of little more than
twenty hexes: Simms, told to walk the 46 hexes from his post to Burke's table
in one order, did not move. The main-quest scripts therefore send their walkers
from waypoint to waypoint (scripts/mgcore.h, mg_way_body; layout/spots.py,
WAY_*). This script replays the search, with the engine's node limit, step and
turning costs and its dislike of radioactive goo, for every leg of

    SIMMS -> SIMMS_POOL -> WAY_POOL -> WAY_SALOON -> BURKE_TABLE          (the arrest)
    BURKE -> WAY_SALOON -> WAY_POOL -> SIMMS_POOL -> WAY_GATE -> WAY_APRON -> GATE_EXIT
    WAY_APRON -> BURKE_RENDEZVOUS                                         (Burke to the fire)

and for the walks back, and prints the steps and the hexes expanded. Doors
count as open (NPCs open unlocked doors on their way) and so does the gate
(mggate.ssl opens it for good); other critters count as obstacles, since the
engine sees them that way. Run it whenever the layout or a WAY_* spot moves.
A leg that needs more than 1200 expansions is reported: too close to the limit.

Exit status 1 when a leg has no path or is too expensive. tests/core/town-scene.txt
is the same question asked of the real engine.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(MOD))
for _path in (MOD, os.path.join(ROOT, "tools")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from f2lib import GameFiles, MapFile, geometry as g  # noqa: E402
from layout import walk  # noqa: E402

NODE_LIMIT = 2000                       # gOpenPathNodeList / gClosedPathNodeList
COMFORTABLE = 1200
GOO_PIDS = range(0x020003D9, 0x020003DC + 1)   # FIRST..LAST_RADIOACTIVE_GOO_PID: +400 a step for critters

ROUTES = [
    ["SIMMS", "SIMMS_POOL", "WAY_POOL", "WAY_SALOON", "BURKE_TABLE"],
    ["BURKE_TABLE", "WAY_SALOON", "WAY_POOL", "SIMMS_POOL", "SIMMS"],
    ["BURKE", "WAY_SALOON", "WAY_POOL", "SIMMS_POOL", "WAY_GATE", "WAY_APRON", "GATE_EXIT"],
    ["WAY_APRON", "BURKE_RENDEZVOUS"],
    ["SIMMS_GREET", "SIMMS"],
]


def estimate(a, b):
    """_idist of the two hexes' screen positions."""
    ax, ay = g.hex_center(a)
    bx, by = g.hex_center(b)
    dx, dy = abs(ax - bx), abs(ay - by)
    return dx + dy - min(dx, dy) // 2


def find_path(blocked, goo, start, goal):
    """(steps, hexes expanded), steps None when the engine would give up."""
    if goal in blocked:
        return None, 0
    open_nodes = {start: (0, estimate(start, goal), -1, None)}
    order = [start]
    seen = {start}
    closed = {}
    while open_nodes:
        best = None
        for tile in order:
            node = open_nodes.get(tile)
            if node is not None and (best is None or node[0] + node[1] < best[0]):
                best = (node[0] + node[1], tile)
        tile = best[1]
        cost, _, rotation, came_from = open_nodes.pop(tile)
        closed[tile] = came_from
        if tile == goal:
            steps = 0
            while closed[tile] is not None:
                tile = closed[tile]
                steps += 1
            return steps, len(closed)
        if len(closed) >= NODE_LIMIT:
            return None, len(closed)
        for direction in range(6):
            neighbour = g.tile_in_direction(tile, direction, 1)
            if neighbour == -1 or neighbour in seen or (neighbour != goal and neighbour in blocked):
                continue
            if len(open_nodes) + 1 >= NODE_LIMIT:
                return None, len(closed)
            seen.add(neighbour)
            step = cost + 50 + (10 if rotation != direction else 0) + (400 if neighbour in goo else 0)
            open_nodes[neighbour] = (step, estimate(neighbour, goal), direction, tile)
            order.append(neighbour)
    return None, len(closed)


def main():
    out_dir = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(MOD, "out-core-town")
    gf = GameFiles(overlay=out_dir)
    m = MapFile.load("megaton", gf)
    with open(os.path.join(out_dir, ".spots.json")) as f:
        spots = json.load(f)
    blocked, doors, _ = walk.survey(m, 0, critters=True)
    solid, _, _ = walk.survey(m, 0, critters=False)
    goo = {obj.tile for obj in m.objects[0] if obj.pid in GOO_PIDS}
    bad = 0
    for route in ROUTES:
        for a, b in zip(route, route[1:]):
            free = set(blocked)
            for end in (spots[a], spots[b]):             # the walker's own post is not in his way
                if end not in solid:
                    free.discard(end)
            steps, used = find_path(free, goo, spots[a], spots[b])
            verdict = "ok"
            if steps is None:
                verdict = "NO PATH (the engine gives up)"
            elif used > COMFORTABLE:
                verdict = "TOO CLOSE to the 2000-hex limit"
            if verdict != "ok":
                bad += 1
            print(f"{a:>16} -> {b:<17} {g.distance(spots[a], spots[b]):3} hexes apart, "
                  f"{'-' if steps is None else steps:>3} steps, {used:4} expanded  {verdict}")
        print()
    print(f"{len(doors)} doors taken as open, {len(goo)} goo hexes; " + ("every leg is walkable" if not bad else f"{bad} leg(s) need a waypoint moved or added"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
