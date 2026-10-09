# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The outer wall: a stockade of rusty corrugated sheet with one gate, and junk against it.

Megaton's wall is scrap. The wall proper is the corrugated-fence kit of the
Broken Hills and NCR caravan yards (kit.stockade): the only retail scrap wall
that has all four corner pieces, so it can be bent round the town in steps,
and whose gate - two braced leaves of the same sheet - is a real door. The
car-wreck walls of The Den are slices of large pictures that only work in
their original arrangement; two of those arrangements are stamped against the
outside as the junk the wall grew out of.
"""
import os

from f2lib import geometry as g

from . import kit, plan

PREFABS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                       "mod", "reference", "prefabs")
PID_CHAIN_LINK = range(0x03000320, 0x03000338)       # the Den's own fence comes with one prefab: left out

# (prefab, origin hex (even hx, even hy), rows of the prefab to leave out)
JUNK = [
    # A heap of wrecks, tyres and drums against the wall left of the gate, on the apron.
    ("carwall-den-b", (104, plan.FRONT - 1), {1}),
    # A truck and a line of car wrecks outside the right-hand wall: scenery, out of reach.
    ("carwall-den-a", (plan.RIGHT - 16, 82), set()),
]


def build(m, rng):
    """Wall, gate and junk. Returns (hexes of the wall, the gate's door object)."""
    from map_kit import Prefab          # tools/map_kit.py; imported here: it pulls in the renderer

    fence, gates = kit.stockade(m, plan.outline(), rng, gates=[plan.GATE])
    for name, (hx, hy), skip_rows in JUNK:
        prefab = Prefab.load(os.path.join(PREFABS, name + ".json"))
        placed = prefab.stamp(m, at=g.tile_at(hx, hy), floors=False, roofs=False)
        for obj in placed:
            ox, oy = g.tile_xy(obj.tile)
            if obj.pid in PID_CHAIN_LINK or oy - hy in skip_rows or (ox, oy) in fence:
                m.remove_object(obj)
    return fence, gates[plan.GATE]
