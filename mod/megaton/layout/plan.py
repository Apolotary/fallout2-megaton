# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The town plan of Megaton: every coordinate the map builder uses, in one place.

All positions are hexes (hx, hy); tile = hy * 200 + hx. On screen rising hx
goes LEFT and rising hy goes DOWN-RIGHT, so the plan below is drawn with hx
decreasing to the right: it is what the player sees, not a mirror image.

                    back wall, hy 57
          +-------------------------------------------+
        /   Billy        SALOON          Craterside     \        hy 61..75
       |  118..128      88..114            70..82        |
       |                 (plaza)                         |
       | Lucy   Common            Church        Water    |       hy 81..101
       | 130..  112..126   POOL   74..88        plant    |
       | 140               bomb                 58..70   |
       |        Brass    100,94   Clinic                 |       hy 97..107
       |        Lantern           74..88                 |
       |        Empty             Sheriff                |       hy 113..121
        \       house   (track)   74..88                /
          +----------------- GATE -------------------+           front wall, hy 127
     hx 144                  100,127                   hx 56
                        apron, hy 128..137
                     exit grid, hy 138..139

Compared with the design brief (research/09 section 4) the arrangement is the
same: gate at the camera-facing edge, bomb in the centre pool, saloon at the
back, shops and services on the right, houses on the left. Sizes follow the
wall kit instead of the brief's cell grid: shacks need even hx and odd hy
bounds, the town is 12 hexes wider and 4 deeper so that every lane is at
least three hexes wide, and each building's roof is separated from the next
by at least one unroofed square (the engine hides roofs by flood fill).
"""

# --- outer wall ------------------------------------------------------------------
RIGHT, LEFT = 56, 144            # hx of the right and left runs of the wall
BACK, FRONT = 57, 127            # hy of the back and front runs
STEP, STEPS = 6, 2               # the four corners are cut off in two steps of six hexes
GATE = (100, FRONT)              # door hex of the gate (even hx); the passage is this one hex

# --- pool ------------------------------------------------------------------------
BOMB = (100, 94)                 # the bomb; its support base lies on the hex above (hy - 1)

# --- apron (outside the gate) ---------------------------------------------------------
APRON_HX = (72, 128)             # walkable ground outside the wall, right and left limit
APRON_HY = (FRONT + 1, 137)
EXIT_ROWS = (138, 139)           # world-map exit grid along the bottom of the apron
EXIT_COLUMNS = 2                 # ... and two hexes deep up both sides

# --- buildings ---------------------------------------------------------------------
# box = (hx_lo, hy_lo, hx_hi, hy_hi): the outer walls stand ON these lines.
# doors: (side, position, name). side front / back takes an odd hx, left any hy,
#        right an even hy. The name is how tests and the report refer to the door.
#        OUTER doors go in a FRONT or a LEFT wall only. Those two face the camera. A door in a
#        back or right wall is painted under its own building's roof: nobody outside can see it,
#        and a click (or a tap) on the place where it is goes to nobody (the common house, Lucy's
#        and the player's house had theirs in the right wall, facing the track, and could only be
#        found by clicking blind from the next hex). tests/layout (clickable) holds every outer
#        door to a share of its pixels that a click can reach.
# ns: north-south partitions (hx, [(door hy, leaf, name)]); ew: east-west
#     partitions (hy, left end hx or None for the left wall, [(door hx, leaf, name)]).
# windows: even hx on the back wall (a window covers hx, hx - 1, hx - 2).
BUILDINGS = {
    "saloon": dict(
        title="Moriarty's Saloon", box=(88, 61, 114, 75), roof="plank", floor="wood", corner="blocks",
        doors=[("front", 105, "saloon")], windows=[110, 104, 94],
        ns=[(98, [(64, True, "office"), (72, True, "rented room")])],
        ew=[(67, 98, [])],
        rooms={"hall": (99, 62, 113, 74), "office": (89, 62, 97, 66), "rented room": (89, 68, 97, 74)}),
    "craterside": dict(
        title="Craterside Supply", box=(70, 63, 82, 75), roof="tin", floor="plate", corner="post",
        doors=[("front", 77, "craterside")], windows=[78],
        rooms={"shop": (71, 64, 81, 74)}),
    "billy": dict(
        title="Billy Creel's House", box=(118, 63, 128, 73), roof="tin", floor="wood", corner="post",
        doors=[("front", 123, "billy")], windows=[124],
        rooms={"room": (119, 64, 127, 72)}),
    "church": dict(
        title="Church of the Children of Atom", box=(74, 81, 88, 91), roof="plank", floor="wood", corner="post",
        doors=[("left", 86, "church")], windows=[84, 80],
        rooms={"chapel": (75, 82, 87, 90)}),
    "common": dict(
        title="Common House", box=(112, 81, 126, 91), roof="tin", floor="wood", corner="post",
        doors=[("front", 123, "common")], windows=[122, 118],
        rooms={"bunkroom": (113, 82, 125, 90)}),
    "plant": dict(
        title="Water Processing Plant", box=(58, 85, 70, 101), roof="tin", floor="plate", corner="blocks",
        doors=[("left", 92, "plant")], windows=[66],
        ew=[(95, None, [(65, True, "plant back room")])],
        rooms={"machine hall": (59, 86, 69, 94), "back room": (59, 96, 69, 100)}),
    "lucy": dict(
        title="Lucy West's House", box=(130, 87, 140, 97), roof="tin", floor="wood", corner="post",
        doors=[("front", 135, "lucy")], windows=[136],
        rooms={"room": (131, 88, 139, 96)}),
    "clinic": dict(
        title="Megaton Clinic", box=(74, 97, 88, 107), roof="tin", floor="plate", corner="post",
        doors=[("left", 102, "clinic")], windows=[84, 80],
        rooms={"ward": (75, 98, 87, 106)}),
    "lantern": dict(
        title="The Brass Lantern (kitchen)", box=(112, 97, 126, 103), roof="tin", floor="plate", corner="post",
        doors=[("front", 119, "lantern kitchen")], windows=[124, 116],
        rooms={"kitchen": (113, 98, 125, 102)}),
    "sheriff": dict(
        title="Sheriff's House", box=(74, 113, 88, 121), roof="plank", floor="wood", corner="post",
        doors=[("left", 116, "sheriff")], windows=[86],
        ns=[(78, [(116, True, "armory")])],
        rooms={"living room": (79, 114, 87, 120), "armory": (75, 114, 77, 120)}),
    "house": dict(
        title="Empty House (the player's)", box=(112, 113, 126, 121), roof="tin", floor="plate", corner="post",
        doors=[("left", 116, "house")], windows=[122, 118],
        rooms={"room": (113, 114, 125, 120)}),
}

# The Brass Lantern's open-air half, in front of the kitchen: no walls, no roof.
# One bar counter closes it towards the camera; Jenny serves from behind it,
# customers stand in front. The counter's picture runs left from LANTERN_BAR.
LANTERN_STALL = (113, 104, 125, 108)         # hx_lo, hy_lo, hx_hi, hy_hi of the stall floor
LANTERN_BAR = (117, 108)                     # hex of the bar object (odd hx)

# Paths kept free of rough ground and of dressing: (from, to, half width in hexes).
PATHS = [
    ((100, 138), (100, 103), 3),             # the track: exit grid - gate - pool
    ((105, 77), (105, 84), 2),               # saloon door to the pool
    ((92, 94), (71, 93), 2),                 # pool to the water plant, between church and clinic
    ((108, 94), (129, 94), 2),               # pool to Lucy's, between common house and Brass Lantern
    ((77, 77), (93, 79), 2),                 # Craterside to the plaza in front of the saloon
    ((123, 75), (110, 79), 2),               # Billy's to the plaza
    ((93, 79), (110, 79), 2),                # the plaza
]
POOL_RING = 10                               # a path circles the pool at this distance from the bomb


def outline():
    """Corners of the outer wall, in order, starting at the left end of the back run.

    A rectangle RIGHT..LEFT x BACK..FRONT whose four corners are cut off in
    STEPS steps of STEP hexes, which is as round as a wall of straight tin
    sheets gets."""
    cut = STEP * STEPS
    points = [(LEFT - cut, BACK), (RIGHT + cut, BACK)]
    for i in range(STEPS):                               # N corner: down and right
        x = RIGHT + cut - STEP * i
        points += [(x, BACK + STEP * (i + 1)), (x - STEP, BACK + STEP * (i + 1))]
    points.append((RIGHT, FRONT - cut))
    for i in range(STEPS):                               # E corner: left and down
        x = RIGHT + STEP * (i + 1)
        points += [(x, FRONT - cut + STEP * i), (x, FRONT - cut + STEP * (i + 1))]
    points.append((LEFT - cut, FRONT))
    for i in range(STEPS):                               # S corner: up and left
        x = LEFT - cut + STEP * i
        points += [(x, FRONT - STEP * (i + 1)), (x + STEP, FRONT - STEP * (i + 1))]
    points.append((LEFT, BACK + cut))
    for i in range(STEPS):                               # W corner: right and up
        x = LEFT - STEP * (i + 1)
        points += [(x, BACK + cut - STEP * i), (x, BACK + cut - STEP * (i + 1))]
    points.pop()                                         # the last point is the first one again
    return points


def inside_wall(hx, hy):
    """True for hexes strictly inside the outer wall (even-odd rule on the outline)."""
    points = outline()
    inside = False
    for i, (ax, ay) in enumerate(points):
        bx, by = points[(i + 1) % len(points)]
        if ax == bx and min(ay, by) <= hy < max(ay, by) and hx < ax:
            inside = not inside
    on_wall = any((ax == bx == hx and min(ay, by) <= hy <= max(ay, by)) or
                  (ay == by == hy and min(ax, bx) <= hx <= max(ax, bx))
                  for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]))
    return inside and not on_wall


def door_hex(building, name):
    """(hx, hy) of a named door of a building."""
    spec = BUILDINGS[building]
    lo_x, lo_y, hi_x, hi_y = spec["box"]
    for side, pos, door in spec.get("doors", ()):
        if door == name:
            return {"front": (pos, hi_y), "back": (pos, lo_y), "left": (hi_x, pos), "right": (lo_x, pos)}[side]
    for hx, doors in spec.get("ns", ()):
        for hy, _, door in doors:
            if door == name:
                return (hx, hy)
    for hy, _, doors in spec.get("ew", ()):
        for hx, _, door in doors:
            if door == name:
                return (hx, hy)
    raise KeyError(f"{building} has no door called {name!r}")


def all_doors():
    """[(building, door name, (hx, hy), has a leaf)] for every doorway of the town."""
    found = []
    for key, spec in BUILDINGS.items():
        for _, _, name in spec.get("doors", ()):
            found.append((key, name, door_hex(key, name), True))
        for _, doors in spec.get("ns", ()):
            for _, leaf, name in doors:
                found.append((key, name, door_hex(key, name), leaf))
        for _, _, doors in spec.get("ew", ()):
            for _, leaf, name in doors:
                found.append((key, name, door_hex(key, name), leaf))
    return found
