# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Outside the gate: the apron, the way out to the world map, and the edges of the map.

The player can stand in two places only: inside the wall, and on the apron in
front of the gate. The apron is closed on three sides by exit grids (two hexes
deep, one object per hex: stepping on any of them leaves for the world map)
backed by a line of invisible blocking hexes, so neither the player nor a
fleeing NPC can wander off around the wall. The camera is held by a frame of
scroll blockers drawn around the wall and the apron.
"""
from f2lib import geometry as g

from . import kit, plan

PID_INVISIBLE_BLOCK = 0x02000158         # "Block Hex Auto Inviso"
SHAPE_DOWN, SHAPE_LEFT, SHAPE_RIGHT = 2, 0, 1      # exit-grid pictures: strip hanging down / to the left / to the right


def exit_hexes():
    """{(hx, hy): picture shape} of the exit grid around the apron."""
    lo_x, hi_x = plan.APRON_HX
    lo_y, hi_y = plan.APRON_HY
    depth = plan.EXIT_COLUMNS
    hexes = {}
    for hy in range(lo_y, hi_y + 1):
        for i in range(1, depth + 1):
            hexes[(lo_x - i, hy)] = SHAPE_RIGHT
            hexes[(hi_x + i, hy)] = SHAPE_LEFT
    for hy in plan.EXIT_ROWS:
        for hx in range(lo_x - depth, hi_x + depth + 1):
            hexes[(hx, hy)] = SHAPE_DOWN
    return hexes


def build(m, fence_hexes):
    """Exit grids and the invisible fence behind them. Returns the set of exit hexes."""
    blocked = {g.tile_xy(obj.tile) for obj in m.all_objects(0) if obj.obj_type in (2, 3)}
    exits = set()
    for (hx, hy), shape in sorted(exit_hexes().items()):
        if (hx, hy) in blocked or (hx, hy) in fence_hexes:
            continue                     # under the wall's picture
        m.add_exit_grid(kit.tile(hx, hy), shape=shape)
        exits.add((hx, hy))
    lo_x, hi_x = plan.APRON_HX
    depth = plan.EXIT_COLUMNS
    outer_lo, outer_hi = lo_x - depth - 1, hi_x + depth + 1
    bottom = plan.EXIT_ROWS[-1] + 1
    ring = [(outer_lo, hy) for hy in range(plan.FRONT + 1, bottom + 1)]
    ring += [(outer_hi, hy) for hy in range(plan.FRONT + 1, bottom + 1)]
    ring += [(hx, bottom) for hx in range(outer_lo, outer_hi + 1)]
    for hx, hy in sorted(set(ring)):
        if (hx, hy) not in blocked and (hx, hy) not in fence_hexes:
            kit.put(m, PID_INVISIBLE_BLOCK, hx, hy)
    return exits


def scroll_frame(m, pad_x=96, pad_y=60):
    """Scroll blockers on a screen-aligned rectangle around the wall and the apron.

    The view centre cannot enter a hex that holds a scroll blocker. The engine
    scrolls 32 px sideways and 24 px up or down per step, so the top and bottom
    edges are two hex rows thick and the sides one hex per 12 px row (the
    retail convention, research/04 section 11.6). The rectangle is the bounding
    box of the wall corners and the apron, pulled IN by the pads: the centre of
    the screen never has to reach the wall itself, and less empty desert shows.
    """
    lo_x, hi_x = plan.APRON_HX
    points = plan.outline() + [(lo_x, plan.EXIT_ROWS[-1]), (hi_x, plan.EXIT_ROWS[-1])]
    centers = [g.hex_center(g.tile_at(hx, hy)) for hx, hy in points]
    x0 = min(x for x, _ in centers) + pad_x
    x1 = max(x for x, _ in centers) - pad_x
    y0 = (min(y for _, y in centers) + pad_y) // 12 * 12 + 6
    y1 = (max(y for _, y in centers) - pad_y // 3) // 12 * 12 + 6
    ring = set()
    for y in (y0, y0 + 12, y1 - 12, y1):
        for x in range(x0 - 32, x1 + 33, 16):
            ring.add(g.hex_from_world(x, y))
    for y in range(y0, y1 + 1, 12):
        for x in (x0, x0 - 16, x1, x1 + 16):
            ring.add(g.hex_from_world(x, y))
    ring.discard(-1)
    count = 0
    for tile in sorted(ring):
        if not g.is_edge(tile):
            m.add_scroll_blocker(tile)
            count += 1
    return (x0, y0, x1, y1), count
