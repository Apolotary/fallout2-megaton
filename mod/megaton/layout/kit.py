# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Wall kits: how Fallout 2's shack and stockade pieces go together.

Every rule here was read off retail maps (Gecko settlement and junkyard, Vault
City courtyard, the Broken Hills and NCR caravan yards) and checked by
rebuilding those buildings piece for piece. Walls are not free-form art: each
picture belongs to one face of a building and to one hex parity.

Screen geometry (research/04 section 11). Rising hx goes LEFT on screen, rising
hy goes DOWN-RIGHT. A box hx_lo..hx_hi x hy_lo..hy_hi is a parallelogram:

                 back wall (hy_lo), runs left -> right, slightly uphill
      W corner  +----------------------------------------+  N corner
    (hx_hi,hy_lo) \                                        \ (hx_lo,hy_lo)
         left wall \                                        \ right wall
           (hx_hi)  \                                        \ (hx_lo)
                     +----------------------------------------+
           S corner (hx_hi,hy_hi)     front wall (hy_hi)     E corner (hx_lo,hy_hi)

The camera looks from the bottom: front and left walls show their outside and
stand between the camera and the room, back and right walls show their inside.
That is why there are four different straight pieces and four door frames.

Along a row of constant hy the hexes zig-zag (an even hx is 32 px wide on
screen, an odd one 16 px), so every east-west piece exists as a wide picture
for even hx and a narrow one for odd hx, and the hexes just below the row with
odd hx lie under the wall's picture: retail maps block them with an invisible
wall piece. Along a column of constant hx every hex is the same step, so
north-south pieces are interchangeable.

Shacks: hx_lo and hx_hi even, hy_lo and hy_hi odd (the retail convention that
makes the roof squares line up with the walls). Roof squares are
hx_lo/2 .. hx_hi/2 - 1 by (hy_lo-1)/2 .. (hy_hi+1)/2: one row of trim behind
the back wall and one row of eave in front of the front wall. Standing under
the eave already hides the roof (the engine tests the square the player's hex
belongs to), exactly as in the retail game.
"""
import random

from f2lib import geometry as g

# ----------------------------------------------------------------------- shack kit ("junktown" tin / wood)
BACK_ODD, BACK_EVEN = 0x03000081, 0x03000082            # jas1000 (odd hx), jas1001 (even hx)
BACK_WINDOW = (0x0300007A, 0x0300007B, 0x0300007C)      # jaw1000 on even hx, then hx - 1, hx - 2
BACK_DOORWAY = (0x03000083, 0x03000084)                 # jad1000 at door hx + 1, jad1001 at door hx - 1
DOOR_BACK = 0x02000350                                  # wdoor4

RIGHT_EVEN, RIGHT_ODD = 0x03000078, 0x030000FA          # jbs1000 (even hy), jbs1002 (odd hy)
RIGHT_PLANKS = (0x03000074, 0x03000075, 0x03000076, 0x03000077)   # jbs2000..2003, four hexes downwards from an odd hy
RIGHT_DOORWAY = (0x030002EA, 0x030002EB)                # jdd1004 at door hy - 1, jdd1005 at door hy + 1
DOOR_RIGHT = 0x02000351                                 # wdoor5

LEFT = (0x03000072, 0x03000073)                         # jds1000, jds1001: plain tin, any hy
LEFT_PATCHES = ((0x03000070, 0x03000071),               # jds2000, jds2001: consecutive hexes downwards
                (0x0300006C, 0x0300006D, 0x0300006E, 0x0300006F))   # jds3000..3003
LEFT_DOORWAY = (0x030002E8, 0x030002E9)                 # jdd1002 at door hy - 1, jdd1003 at door hy + 1
DOOR_LEFT = 0x02000352                                  # wdoor6

FRONT_EVEN, FRONT_ODD = 0x03000060, 0x03000061          # jcs1000 (even hx), jcs1001 (odd hx)
FRONT_PATCHES = ((0x03000062, 0x03000063),              # jcs2000 on even hx, jcs2001 on hx - 1 (planks)
                 (0x03000064, 0x03000065),              # jcs3000 / 3001 (hazard-striped tin)
                 (0x03000066, 0x03000067))              # jcs3002 / 3003 (board and plate)
FRONT_DOORWAY = (0x03000068, 0x03000069)                # jcd1000 at door hx + 1, jcd1001 at door hx - 1
DOOR_FRONT = 0x02000196                                 # wdoor3

CORNER_W, CORNER_N, CORNER_E = 0x0300016F, 0x0300008A, 0x0300008B   # cni2008, cni1000, cnx2000
CORNER_S = 0x030002DE                                   # corn001: plain tin corner post
CORNER_S_BLOCKS = (0x03000085, 0x03000086, 0x03000087, 0x03000088, 0x03000089)   # cnx1000..1004, cinder blocks

T_BACK = 0x030002E4       # cni2023: back wall, a partition leaves downwards
T_FRONT = 0x030002E3      # cni2022: front wall, a partition arrives from above
T_RIGHT = 0x030000F4      # cni2001: right wall, a partition arrives from the left
T_LEFT = 0x030002E1       # cni2020: left wall, a partition leaves to the right
CROSS = 0x030000F7        # cni2004: north-south partition, an east-west one leaves to the right

BLOCK_OPAQUE = 0x0300026D  # invisible wall hex: the hex a wide corner picture stands on
BLOCK_CLEAR = 0x0300026E   # invisible wall hex that lets light and shots pass: under east-west walls

# Roof and floor tiles (art/tiles names).
ROOF_TIN = dict(trim=("jrt2002.frm", "jrt2000.frm"), field=("ruf1001.frm", "ruf1000.frm"),
                eave=("ruf3000.frm", "ruf3001.frm"), eave_end="ruf4000.frm",
                patch=[["ruf2000.frm", "ruf2001.frm", "ruf2002.frm"],
                       ["ruf2003.frm", "ruf2004.frm", "ruf2005.frm"],
                       ["ruf2006.frm", "ruf2007.frm", "ruf2008.frm"]])
ROOF_PLANK = dict(trim=("jrt1002.frm", "jrt1000.frm"), field=("plk2000.frm", "plk2000.frm", "plk1000.frm"),
                  eave=("plk5000.frm", "plk6000.frm"), eave_end="plk7000.frm",
                  patch=[["plk3000.frm"], ["plk3001.frm"]], single="plk4000.frm")
FLOORS = {
    "plate": ["cmt1000.frm", "cmt2000.frm", "cmt3000.frm", "cmt4000.frm", "cmt1000.frm", "cmt2000.frm",
              "cmt3000.frm", "cmt4000.frm", "cmt5000.frm", "cmt6000.frm", "cmt7000.frm", "cmt8000.frm"],
    "wood": ["crbm004.frm", "crbm007.frm", "crbm004.frm", "crbm007.frm", "crbm010.frm"],
    "carpet": ["brn1000.frm", "brn1001.frm"],
    "dirt": ["capb000.frm"],
}

# ----------------------------------------------------------------------- stockade kit (rusty corrugated fence)
FENCE_EW_EVEN = (0x030003BD, 0x030003BD, 0x030003C2, 0x030003CA, 0x030003CB, 0x030003CC)   # tfenc00, 05, 13, 14, 15
FENCE_EW_ODD = (0x030003BE, 0x030003BF)                 # tfenc01, tfenc02
FENCE_EW_END = 0x030003C3                               # tfenc06: wide piece with a post, closes a run
FENCE_NS = (0x030003C0, 0x030003C1, 0x030003C0, 0x030003C1, 0x030003CD, 0x030003CE, 0x030003CF, 0x030003D0)   # tfenc03, 04, 16..19
FENCE_NS_POST = (0x030003C4, 0x030003C5)                # tfenc07, tfenc08
FENCE_CORNER = {"N": 0x030003C6, "S": 0x030003C7, "W": 0x030003C8, "E": 0x030003C9}   # tfenc09, 10, 11, 12
GATE = 0x0200071A                                       # door10: double gate of braced corrugated sheet
GATE_SPAN = (-3, 2)                                     # the gate picture covers door hx - 3 .. hx + 2
OBJECT_MULTIHEX = 0x800                                 # object flag: also blocks the six hexes around it
SECRET_BLOCK = 0x02000043                               # invisible blocking scenery (light and shots pass)


class KitError(Exception):
    pass


def tile(hx, hy):
    t = g.tile_at(hx, hy)
    if t < 0:
        raise KitError(f"({hx}, {hy}) is off the map")
    return t


def put(m, pid, hx, hy, **fields):
    return m.add_object(pid, tile(hx, hy), **fields)


def _has(m, hx, hy, pids):
    return any(obj.pid in pids for obj in m.objects_at(tile(hx, hy)))


def block_under(m, hy, hx_from, hx_to, skip=()):
    """Invisible blockers on the odd-hx hexes of row `hy`, which lie under the wall row above it."""
    for hx in range(min(hx_from, hx_to), max(hx_from, hx_to) + 1):
        if hx & 1 and hx not in skip and not _has(m, hx, hy, (BLOCK_CLEAR, BLOCK_OPAQUE)):
            if not any(o.obj_type == 3 for o in m.objects_at(tile(hx, hy))):
                put(m, BLOCK_CLEAR, hx, hy)


class Shack:
    """One rectangular tin / wood building: outer walls, doors, windows, partitions, floor and roof.

        s = Shack(m, (86, 65, 112, 79), rng, roof="plank", floor="wood")
        s.door("front", 103)                  # hx for front / back, hy for left / right
        s.window(100)                         # back wall, on hx, hx - 1, hx - 2 (hx even)
        s.partition_ns(96, doors=[(69, True), (75, False)])     # (hy, has a door leaf)
        s.partition_ew(71, left=96, doors=[(91, True)])         # from the partition at hx 96 to the right wall
        s.build()

    After build(): s.doors = {(side, pos): door object or None}, s.interior() =
    walkable hexes inside, s.roof_squares = set of (qx, qy).
    """

    def __init__(self, m, box, rng=None, roof="tin", floor="plate", corner="post", name=""):
        self.m = m
        self.name = name
        self.hx_lo, self.hy_lo, self.hx_hi, self.hy_hi = box
        if self.hx_lo & 1 or self.hx_hi & 1 or not self.hy_lo & 1 or not self.hy_hi & 1:
            raise KitError(f"shack {name} {box}: hx bounds must be even and hy bounds odd")
        if self.hx_hi - self.hx_lo < 4 or self.hy_hi - self.hy_lo < 4:
            raise KitError(f"shack {name} {box}: too small")
        self.rng = rng or random.Random(0)
        self.roof = roof
        self.floor = floor
        self.corner = corner
        self._doors = []          # (side, pos, leaf)
        self._windows = []
        self._ns = []             # (hx, [(hy, leaf)], hy_to)
        self._ew = []             # (hy, left hx, [(hx, leaf)])
        self.doors = {}
        self.roof_squares = set()
        self.wall_hexes = set()

    # ---------------------------------------------------------------- description
    def door(self, side, pos, leaf=True):
        if side in ("front", "back"):
            if not pos & 1 or not self.hx_lo + 3 <= pos <= self.hx_hi - 3:
                raise KitError(f"shack {self.name}: a {side} door needs an odd hx at least 3 from the corners, not {pos}")
        elif side == "left":
            if not self.hy_lo + 2 <= pos <= self.hy_hi - 2:
                raise KitError(f"shack {self.name}: a left door needs hy at least 2 from the corners, not {pos}")
        elif side == "right":
            if pos & 1 or not self.hy_lo + 3 <= pos <= self.hy_hi - 3:
                raise KitError(f"shack {self.name}: a right door needs an even hy at least 3 from the corners, not {pos}")
        else:
            raise KitError(f"unknown side {side!r}")
        self._doors.append((side, pos, leaf))
        return self

    def window(self, hx):
        if hx & 1 or not self.hx_lo + 4 <= hx <= self.hx_hi - 2:
            raise KitError(f"shack {self.name}: a window starts on an even hx inside the back wall, not {hx}")
        self._windows.append(hx)
        return self

    def partition_ns(self, hx, doors=()):
        """A wall from the back wall to the front wall on column hx (even); doors = [(hy even, leaf)]."""
        if hx & 1 or not self.hx_lo + 3 <= hx <= self.hx_hi - 3:
            raise KitError(f"shack {self.name}: a north-south partition needs an even hx inside, not {hx}")
        for hy, _ in doors:
            if hy & 1 or not self.hy_lo + 3 <= hy <= self.hy_hi - 3:
                raise KitError(f"shack {self.name}: a partition door needs an even hy at least 3 from the walls, not {hy}")
        self._ns.append((hx, list(doors)))
        return self

    def partition_ew(self, hy, left=None, doors=()):
        """A wall on row hy (odd) from the left wall (or the partition on column `left`) to the right wall."""
        if not hy & 1 or not self.hy_lo + 3 <= hy <= self.hy_hi - 3:
            raise KitError(f"shack {self.name}: an east-west partition needs an odd hy inside, not {hy}")
        for hx, _ in doors:
            if not hx & 1:
                raise KitError(f"shack {self.name}: a partition door needs an odd hx, not {hx}")
        self._ew.append((hy, self.hx_hi if left is None else left, list(doors)))
        return self

    # ---------------------------------------------------------------- construction
    def _wall(self, pid, hx, hy):
        self.wall_hexes.add((hx, hy))
        return put(self.m, pid, hx, hy)

    def _door_object(self, side, pos, pid, hx, hy, leaf):
        self.wall_hexes.add((hx, hy))
        self.doors[(side, pos)] = put(self.m, pid, hx, hy) if leaf else None

    def build(self):
        m, rng = self.m, self.rng
        lo_x, hi_x, lo_y, hi_y = self.hx_lo, self.hx_hi, self.hy_lo, self.hy_hi
        doors = {side: {pos: leaf for s, pos, leaf in self._doors if s == side} for side in ("front", "back", "left", "right")}
        ns_columns = {hx for hx, _ in self._ns}
        ew_rows = {hy: left for hy, left, _ in self._ew}

        # Floor first (objects do not care, but it keeps the order of a retail map).
        self._lay_floor()

        # Back wall, left to right.
        self._wall(CORNER_W, hi_x, lo_y)
        skip = set()
        for hx in self._windows:
            for i, pid in enumerate(BACK_WINDOW):
                self._wall(pid, hx - i, lo_y)
                skip.add(hx - i)
        for hx, leaf in doors["back"].items():
            self._wall(BACK_DOORWAY[0], hx + 1, lo_y)
            self._door_object("back", hx, DOOR_BACK, hx, lo_y, leaf)
            self._wall(BACK_DOORWAY[1], hx - 1, lo_y)
            skip.update((hx - 1, hx, hx + 1))
        for hx in range(hi_x - 1, lo_x, -1):
            if hx in skip:
                continue
            if hx in ns_columns:
                self._wall(T_BACK, hx, lo_y)
            else:
                self._wall(BACK_ODD if hx & 1 else BACK_EVEN, hx, lo_y)
        self._wall(CORNER_N, lo_x, lo_y)
        block_under(m, lo_y + 1, lo_x + 1, hi_x - 1, skip=set(doors["back"]))

        # Left wall, top to bottom. The W corner picture also covers the first hex.
        self._wall(BLOCK_OPAQUE, hi_x, lo_y + 1)
        block_corner = self.corner == "blocks"
        end = hi_y - 2 if block_corner else hi_y
        skip = set()
        for hy, leaf in doors["left"].items():
            self._wall(LEFT_DOORWAY[0], hi_x, hy - 1)
            self._door_object("left", hy, DOOR_LEFT, hi_x, hy, leaf)
            self._wall(LEFT_DOORWAY[1], hi_x, hy + 1)
            skip.update((hy - 1, hy, hy + 1))
        for hy, left in ew_rows.items():
            if left == hi_x:
                self._wall(T_LEFT, hi_x, hy)
                self._wall(BLOCK_OPAQUE, hi_x, hy + 1)
                skip.update((hy, hy + 1))
        hy = lo_y + 2
        if hy - 1 in skip:                    # a doorway right under the corner needs no blocker hex
            pass
        while hy < end:
            if hy in skip:
                hy += 1
                continue
            run = 1
            while hy + run < end and hy + run not in skip:
                run += 1
            patch = rng.choice(LEFT_PATCHES) if rng.random() < 0.22 else None
            if patch and len(patch) <= run:
                for i, pid in enumerate(patch):
                    self._wall(pid, hi_x, hy + i)
                hy += len(patch)
            else:
                self._wall(LEFT[hy & 1 ^ 1], hi_x, hy)
                hy += 1

        # Front wall, left to right.
        if block_corner:
            self._wall(CORNER_S_BLOCKS[0], hi_x, hi_y - 2)
            self._wall(CORNER_S_BLOCKS[1], hi_x, hi_y - 1)
            self._wall(CORNER_S_BLOCKS[2], hi_x, hi_y)
            self._wall(CORNER_S_BLOCKS[3], hi_x - 1, hi_y)
            self._wall(CORNER_S_BLOCKS[4], hi_x - 2, hi_y)
            start = hi_x - 3
        else:
            self._wall(CORNER_S, hi_x, hi_y)
            start = hi_x - 1
        skip = set()
        for hx, leaf in doors["front"].items():
            self._wall(FRONT_DOORWAY[0], hx + 1, hi_y)
            self._door_object("front", hx, DOOR_FRONT, hx, hi_y, leaf)
            self._wall(FRONT_DOORWAY[1], hx - 1, hi_y)
            skip.update((hx - 1, hx, hx + 1))
        hx = start
        while hx > lo_x:
            if hx in skip:
                hx -= 1
                continue
            if hx in ns_columns:
                self._wall(T_FRONT, hx, hi_y)
                hx -= 1
                continue
            pair_free = not hx & 1 and hx - 1 > lo_x and hx - 1 not in skip and hx - 1 not in ns_columns
            if pair_free and rng.random() < 0.3:
                even, odd = rng.choice(FRONT_PATCHES)
                self._wall(even, hx, hi_y)
                self._wall(odd, hx - 1, hi_y)
                hx -= 2
            else:
                self._wall(FRONT_ODD if hx & 1 else FRONT_EVEN, hx, hi_y)
                hx -= 1
        self._wall(CORNER_E, lo_x, hi_y)
        block_under(m, hi_y + 1, lo_x + 1, hi_x - 1, skip=set(doors["front"]))

        # Right wall, top to bottom. The E corner picture covers the hex above it.
        self._column(lo_x, lo_y + 1, hi_y - 1, doors["right"], "right",
                     junctions={hy: T_RIGHT for hy in ew_rows})

        # Partitions.
        for hx, pdoors in self._ns:
            crossings = {hy: CROSS for hy, left in ew_rows.items() if left == hx}
            self._wall(BLOCK_OPAQUE, hx, lo_y + 1)
            self._column(hx, lo_y + 2, hi_y - 1, dict(pdoors), ("ns", hx), junctions=crossings)
        for hy, left, pdoors in self._ew:
            pdoors = dict(pdoors)
            skip = set()
            for hx, leaf in pdoors.items():
                if not lo_x + 3 <= hx <= left - 3:
                    raise KitError(f"shack {self.name}: partition door hx {hx} is too close to a wall")
                self._wall(BACK_DOORWAY[0], hx + 1, hy)
                self._door_object(("ew", hy), hx, DOOR_BACK, hx, hy, leaf)
                self._wall(BACK_DOORWAY[1], hx - 1, hy)
                skip.update((hx - 1, hx, hx + 1))
            for hx in range(left - 1, lo_x, -1):
                if hx not in skip:
                    self._wall(BACK_ODD if hx & 1 else BACK_EVEN, hx, hy)
            block_under(m, hy + 1, lo_x + 1, left - 1, skip=set(pdoors))

        self._lay_roof()
        return self

    def _column(self, hx, hy_from, hy_to, doors, side, junctions):
        """A right-wall-type column (inside face): plain pieces, door frames, T pieces.

        The hex above a junction, above a door frame and above the bottom end is
        an invisible wall hex: the wide picture below covers it."""
        special = {}
        for hy, leaf in doors.items():
            special[hy - 2] = [BLOCK_OPAQUE]
            special[hy - 1] = [RIGHT_DOORWAY[0]]
            special[hy] = ("door", leaf)
            special[hy + 1] = [RIGHT_DOORWAY[1], RIGHT_ODD]
        for hy, pid in junctions.items():
            if hy - 1 in special or hy in special:
                raise KitError(f"shack {self.name}: a door on column {hx} is too close to the partition on row {hy}")
            special[hy - 1] = [BLOCK_OPAQUE]
            special[hy] = [pid]
        if hy_to in special:
            raise KitError(f"shack {self.name}: column {hx} has a door or junction next to its lower end")
        special[hy_to] = [BLOCK_OPAQUE]
        for hy in range(hy_from, hy_to + 1):
            what = special.get(hy)
            if what is None:
                self._wall(RIGHT_ODD if hy & 1 else RIGHT_EVEN, hx, hy)
            elif isinstance(what, tuple):
                self._door_object(side, hy, DOOR_RIGHT, hx, hy, what[1])
            else:
                for pid in what:
                    self._wall(pid, hx, hy)

    def squares(self):
        """(qx range, qy range of the floor, qy range of the roof)."""
        qx = range(self.hx_lo // 2, self.hx_hi // 2)
        floor_qy = range((self.hy_lo + 1) // 2, (self.hy_hi - 1) // 2 + 1)
        roof_qy = range((self.hy_lo - 1) // 2, (self.hy_hi + 1) // 2 + 1)
        return qx, floor_qy, roof_qy

    def _lay_floor(self):
        if self.floor is None:
            return
        names = FLOORS[self.floor]
        qx, qy, _ = self.squares()
        for y in qy:
            for x in qx:
                self.m.set_floor(x, y, self.rng.choice(names))

    def _lay_roof(self):
        if self.roof is None:
            return
        style = ROOF_TIN if self.roof == "tin" else ROOF_PLANK
        qx, _, qy = self.squares()
        rng = self.rng
        grid = {}
        for y in qy:
            for x in qx:
                i = x - qx[0]
                if y == qy[0]:
                    name = style["trim"][i & 1]
                elif y == qy[-1]:
                    name = style["eave_end"] if i == 0 else style["eave"][i & 1]
                elif self.roof == "tin":
                    name = style["field"][(x + y) & 1]
                else:
                    name = rng.choice(style["field"])
                grid[(x, y)] = name
        # A patched panel or two, never on the outer ring.
        patch = style["patch"]
        rows, cols = len(patch), len(patch[0])
        inner_w, inner_h = len(qx) - 2, len(qy) - 4
        tries = max(1, (inner_w * inner_h) // 18)
        used = set()
        for _ in range(tries):
            if inner_w < cols or inner_h < rows:
                break
            x0 = qx[0] + 1 + rng.randrange(inner_w - cols + 1)
            y0 = qy[0] + 2 + rng.randrange(inner_h - rows + 1)
            cells = {(x0 + c, y0 + r) for r in range(rows) for c in range(cols)}
            if any((x + dx, y + dy) in used for x, y in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            used |= cells
            for r in range(rows):
                for c in range(cols):
                    grid[(x0 + cols - 1 - c, y0 + r)] = patch[r][c]      # patch columns are listed left to right
        if "single" in style and inner_w > 2 and inner_h > 2:
            for _ in range(max(1, tries // 2)):
                spot = (qx[0] + 1 + rng.randrange(inner_w), qy[0] + 2 + rng.randrange(inner_h))
                if spot not in used:
                    grid[spot] = style["single"]
        for (x, y), name in grid.items():
            self.m.set_roof(x, y, name)
            self.roof_squares.add((x, y))

    # ---------------------------------------------------------------- queries
    def interior(self):
        """Hexes inside the outer walls (including partition and blocker hexes)."""
        return {(hx, hy) for hx in range(self.hx_lo + 1, self.hx_hi) for hy in range(self.hy_lo + 1, self.hy_hi)}

    def door_hex(self, side, pos):
        if side == "front":
            return (pos, self.hy_hi)
        if side == "back":
            return (pos, self.hy_lo)
        if side == "left":
            return (self.hx_hi, pos)
        if side == "right":
            return (self.hx_lo, pos)
        kind, where = side
        return (where, pos) if kind == "ns" else (pos, where)


# ----------------------------------------------------------------------- stockade
def stockade(m, corners, rng, gates=(), gaps=()):
    """A closed fence of corrugated sheet along a rectilinear outline.

    corners  [(hx, hy), ...] in drawing order; consecutive corners share hx or hy,
             the last joins the first.
    gates    [(hx, hy)]: door hexes of double gates in east-west runs (hx even).
             The gate picture covers hx - 3 .. hx + 2. The door object is made
             MULTIHEX: shut, it blocks its own hex and the six around it; open
             (the engine sets NO_BLOCK) it blocks nothing, so the passage is
             three hexes wide (hx - 1 .. hx + 1) and one NPC standing in it
             cannot cork the town. The three outer hexes, where the open
             leaves rest, hold invisible blockers for good.
    gaps     {(hx, hy)} hexes of the outline left empty (something else stands there).

    Returns (fence hexes as a set, {gate hex: door object}).
    """
    gaps = set(gaps)
    hexes = set()
    gate_objects = {}
    gate_cover = {}
    for ghx, ghy in gates:
        if ghx & 1:
            raise KitError("a gate door stands on an even hx")
        for hx in range(ghx + GATE_SPAN[0], ghx + GATE_SPAN[1] + 1):
            gate_cover[(hx, ghy)] = (ghx, ghy)
    n = len(corners)
    corner_set = set(corners)
    under = []                      # (hy, hx) rows needing blockers below
    for i, (ax, ay) in enumerate(corners):
        bx, by = corners[(i + 1) % n]
        px, py = corners[i - 1]
        if (ax == bx) == (ay == by):
            raise KitError(f"stockade: corners {i} and {i + 1} are not on one row or column")
        # The piece on the corner hex itself, chosen from the two directions that meet there.
        arms = set()
        for ox, oy in ((px, py), (bx, by)):
            if oy == ay:
                arms.add("left" if ox > ax else "right")
            else:
                arms.add("up" if oy < ay else "down")
        shape = {frozenset(("right", "down")): "W", frozenset(("left", "down")): "N",
                 frozenset(("left", "up")): "E", frozenset(("right", "up")): "S"}.get(frozenset(arms))
        if shape is None:
            raise KitError(f"stockade: corner {i} at ({ax}, {ay}) is not a right angle")
        if (ax, ay) not in gaps:
            put(m, FENCE_CORNER[shape], ax, ay)
            hexes.add((ax, ay))
        # The run towards the next corner.
        if ay == by:
            step = 1 if bx > ax else -1
            for hx in range(ax + step, bx, step):
                if (hx, ay) in gaps or (hx, ay) in corner_set:
                    continue
                hexes.add((hx, ay))
                if (hx, ay) in gate_cover:
                    door = gate_cover[(hx, ay)]
                    if (hx, ay) == door:
                        gate = put(m, GATE, hx, ay)
                        gate.flags |= OBJECT_MULTIHEX
                        gate_objects[door] = gate
                    elif abs(hx - door[0]) > 1:
                        put(m, SECRET_BLOCK, hx, ay)
                    continue
                if hx & 1:
                    put(m, rng.choice(FENCE_EW_ODD), hx, ay)
                else:
                    put(m, rng.choice(FENCE_EW_EVEN), hx, ay)
                if hx & 1:
                    under.append((hx, ay + 1))
        else:
            step = 1 if by > ay else -1
            count = 0
            for hy in range(ay + step, by, step):
                if (ax, hy) in gaps or (ax, hy) in corner_set:
                    continue
                hexes.add((ax, hy))
                count += 1
                if count % 6 == 3:
                    put(m, rng.choice(FENCE_NS_POST), ax, hy)
                else:
                    put(m, rng.choice(FENCE_NS), ax, hy)
    for hx, hy in under:
        if (hx, hy) not in hexes and (hx, hy - 1) not in gate_cover:
            if not any(o.obj_type in (2, 3) for o in m.objects_at(tile(hx, hy))):
                put(m, BLOCK_CLEAR, hx, hy)
                hexes.add((hx, hy))
    return hexes, gate_objects
