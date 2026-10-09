# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The eleven buildings of Megaton and the bomb in its pool: shells only.

Walls, doors, partitions, floors and roofs come from plan.BUILDINGS through
the shack kit. Furniture is the decorator's job, with two exceptions that
belong to the bones because spots depend on them: the counter of the Brass
Lantern (Jenny stands behind it) and the bomb's cradle with the hexes its
picture covers.
"""
import random

from f2lib import geometry as g

import registry

from . import kit, plan, spots

PID_STOCK_BOMB = 0x02000300      # "Bomb", abomb1.frm: the bomb of a town built without the custom art
# THE bomb, placed by the cast (cast/core.py) with its script: the custom three-state sprite
# (registry.ART_NAMES; its frame is the quest state, see scripts/mgbomb.ssl).
PID_BOMB = registry.art_pids().get("PID_MGA_BOMB", PID_STOCK_BOMB)
PID_BOMB_BASE = 0x02000301       # "Support Base", abomb2.frm: flat, walkable (replaced by the art)
PID_GOO = (0x020003D9, 0x020003DA, 0x020003DB, 0x020003DC)      # "Radioactive Goo": flat, glows faintly
PID_PUDDLE = (0x02000259, 0x0200025A, 0x0200025B)               # "Slime Pool": small flat puddles
PID_BAR = 0x0200005E             # "Bar", bar01.frm: one L-shaped counter
PID_LIGHT = 0x0200008D           # "Light Source": invisible, radius 8
PID_MATTRESS = 0x020000D0        # "Bed", bed3.frm: a flat mattress, walkable, needs no blocked hexes

# Hexes under the STOCK bomb and its cradle, relative to the bomb's hex (even hx), measured from
# the two pictures. With the custom art these blockers and the cradle are replaced by the new
# sprite's own (layout/art.py; info["bomb_blocked"] then holds the new set). The cradle's front lip (the three hexes below the bomb) stays walkable:
# that is where one stands to work on the bomb, reached from the row in front of it.
BOMB_BLOCKED = [(2, -2), (1, -2), (2, -1), (1, -1), (0, -1), (-1, -1),
                (2, 0), (1, 0), (-1, 0), (-2, 0), (2, 1), (-2, 1)]
BOMB_ACCESS = [(-1, 1), (0, 1), (1, 1)]

# The Brass Lantern's counter is the "Bar" picture (a plank bar with its kegs and still),
# which stands on its right end and runs up and to the left: these offsets from the bar's
# hex (an odd hx) are the hexes under it.
BAR_BLOCKED = [(1, 0), (2, 0), (3, 0), (4, 0), (0, -1), (1, -1), (2, -1), (3, -1), (4, -1), (3, -2)]


# The wall patches, floor plates and roof patches of ALL the shacks come from one random stream, in
# the order of plan.BUILDINGS, and how much of it a shack uses depends on where its doors are. When
# a door of the finished town moves, the old door list goes here: the stream is then advanced
# exactly as it used to be (the old shack is built on a map that forgets everything it is told),
# and the real shack works from a copy of the stream. Its floor and roof stay as they were, and so
# does every wall, floor and roof of the buildings after it; without this, moving one door re-rolls
# the patches of half the town. (These three had their doors in the right wall, under their own
# roofs: see plan.py.)
STREAM_DOORS = {"common": [("right", 86)], "lucy": [("right", 92)], "house": [("right", 116)]}


class _Nowhere:
    """A map that keeps nothing: what kit.Shack needs of one, and no more."""

    def add_object(self, pid, tile, **fields):
        return None

    def objects_at(self, tile):
        return ()

    def set_floor(self, x, y, name):
        pass

    def set_roof(self, x, y, name):
        pass


def _describe(shack, spec, doors):
    for side, pos in doors:
        shack.door(side, pos)
    for hx in spec.get("windows", ()):
        shack.window(hx)
    for hx, pdoors in spec.get("ns", ()):
        shack.partition_ns(hx, doors=[(hy, leaf) for hy, leaf, _ in pdoors])
    for hy, left, pdoors in spec.get("ew", ()):
        shack.partition_ew(hy, left=left, doors=[(hx, leaf) for hx, leaf, _ in pdoors])
    return shack


def build_shacks(m, rng):
    """Build every building of plan.BUILDINGS. Returns {key: kit.Shack}."""
    shacks = {}
    for key, spec in plan.BUILDINGS.items():
        own = rng
        if key in STREAM_DOORS:
            own = random.Random()
            own.setstate(rng.getstate())
            _describe(kit.Shack(_Nowhere(), spec["box"], rng, roof=spec["roof"], floor=spec["floor"],
                                corner=spec["corner"], name=key), spec, STREAM_DOORS[key]).build()
        shack = kit.Shack(m, spec["box"], own, roof=spec["roof"], floor=spec["floor"],
                          corner=spec["corner"], name=key)
        for side, pos, _ in spec.get("doors", ()):
            shack.door(side, pos)
        for hx in spec.get("windows", ()):
            shack.window(hx)
        for hx, doors in spec.get("ns", ()):
            shack.partition_ns(hx, doors=[(hy, leaf) for hy, leaf, _ in doors])
        for hy, left, doors in spec.get("ew", ()):
            shack.partition_ew(hy, left=left, doors=[(hx, leaf) for hx, leaf, _ in doors])
        shack.build()
        shacks[key] = shack
    return shacks


def build_lantern_stall(m, rng):
    """The open-air half of the Brass Lantern: a floor of plates and the counter. No roof."""
    lo_x, lo_y, hi_x, hi_y = plan.LANTERN_STALL
    for qy in range(lo_y // 2, hi_y // 2 + 1):
        for qx in range((lo_x - 1) // 2, (hi_x - 1) // 2 + 1):
            m.set_floor(qx, qy, rng.choice(kit.FLOORS["plate"]))
    bar_hx, bar_hy = plan.LANTERN_BAR
    kit.put(m, PID_BAR, bar_hx, bar_hy)
    blocked = {(bar_hx, bar_hy)}
    for dx, dy in BAR_BLOCKED:
        kit.put(m, kit.SECRET_BLOCK, bar_hx + dx, bar_hy + dy)
        blocked.add((bar_hx + dx, bar_hy + dy))
    return blocked


def build_beds(m):
    """The two beds scripts attach to (cast/merchants.py: mgbed on HOUSE_BED and COMMON_BED).

    A bed has to stand exactly on its spot. These are plain mattresses; the
    decorator may put a better bed there as long as one scenery object stays
    on the spot's hex."""
    from . import spots

    beds = {}
    for name in ("HOUSE_BED", "COMMON_BED"):
        hx, hy, _ = spots.SPOTS[name]
        beds[name] = kit.put(m, PID_MATTRESS, hx, hy)
    return beds


def build_bomb(m, rng, pool_hexes):
    """The cradle, the blocked hexes around the bomb, goo on the slime and puddles on the bank."""
    bx, by = plan.BOMB
    kit.put(m, PID_BOMB_BASE, bx, by - 1)
    blocked = set()
    for dx, dy in BOMB_BLOCKED:
        kit.put(m, kit.SECRET_BLOCK, bx + dx, by + dy)
        blocked.add((bx + dx, by + dy))
    keep_clear = blocked | {(bx, by), (bx, by - 1)} | {(bx + dx, by + dy) for dx, dy in BOMB_ACCESS}
    # Goo: a ring of glowing blobs on the slime, a few puddles just outside it.
    slime = sorted(h for h in pool_hexes if h not in keep_clear)
    rng.shuffle(slime)
    placed = []
    for hx, hy in slime:
        if len(placed) >= 9:
            break
        if all(g.distance(g.tile_at(hx, hy), g.tile_at(*other)) >= 3 for other in placed):
            kit.put(m, rng.choice(PID_GOO), hx, hy)
            placed.append((hx, hy))
    bank = sorted({(hx + dx, hy + dy) for hx, hy in pool_hexes for dx in (-3, 3) for dy in (-2, 2)} - pool_hexes)
    rng.shuffle(bank)
    # Never on a named spot: a puddle on LEAK3 lay under Walter's pipe, and whoever used Repair
    # on the foot of the pipe was told "You cannot repair that." (the puddle is the hex's first object).
    named = {(hx, hy) for hx, hy, _ in spots.SPOTS.values()}
    puddles = []
    for hx, hy in bank:
        if len(puddles) >= 6:
            break
        if (hx, hy) in named:
            continue
        if all(g.distance(g.tile_at(hx, hy), g.tile_at(*other)) >= 5 for other in puddles):
            kit.put(m, rng.choice(PID_PUDDLE), hx, hy)
            puddles.append((hx, hy))
    return blocked


def ensure_bomb(m, art=True):
    """The bomb is a cast entry (it carries the quest script). A build without that
    group would have an empty cradle, so an unscripted bomb is put there instead
    (the stock one in a town built without the custom art)."""
    tile = g.tile_at(*plan.BOMB)
    for obj in m.objects_at(tile):
        if obj.pid in (PID_BOMB, PID_STOCK_BOMB):
            return obj
    return m.add_object(PID_BOMB if art else PID_STOCK_BOMB, tile)


def add_lights(m, shacks):
    """Invisible light sources, so the town is readable at night: the pool glows, the gate
    and every doorstep are lit, each room has a lamp. (Daylight itself is the map script's.)"""
    spots = [(plan.BOMB[0] + 3, plan.BOMB[1] - 3), (plan.BOMB[0] - 3, plan.BOMB[1] + 3),
             (plan.GATE[0] + 5, plan.GATE[1] - 4), (plan.GATE[0] - 5, plan.GATE[1] - 4),
             (plan.GATE[0] + 4, plan.GATE[1] + 4), (plan.GATE[0] - 4, plan.GATE[1] + 4)]
    for key, spec in plan.BUILDINGS.items():
        for lo_x, lo_y, hi_x, hi_y in spec["rooms"].values():
            spots.append(((lo_x + hi_x) // 2, (lo_y + hi_y) // 2))
    for key, name, (hx, hy), _ in plan.all_doors():
        spec = plan.BUILDINGS[key]
        lo_x, lo_y, hi_x, hi_y = spec["box"]
        if hx == hi_x:
            spots.append((hx + 2, hy))
        elif hx == lo_x:
            spots.append((hx - 2, hy))
        elif hy == hi_y:
            spots.append((hx, hy + 2))
    lights = []
    for hx, hy in spots:
        lights.append(m.add_object(PID_LIGHT, g.tile_at(hx, hy), light_distance=6, light_intensity=0x10000))
    return lights
