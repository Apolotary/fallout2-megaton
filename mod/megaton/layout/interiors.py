# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Interiors of the eleven buildings: furniture, containers with their loot, lamps.

One function per building, coordinates in hexes (hx, hy) of plan.BUILDINGS.
Read dressing.py first (how sprites, blockers and draw order work). The
conventions used throughout:

  back wall   row hy_lo + 1; its odd-hx hexes lie under the wall picture, which is
              where retail maps tuck lockers and bookcases (flush with the wall)
  right wall  column hx_lo + 1
  "back" / "right" pieces: the same furniture drawn for one wall or the other; the
              tables below say which is which (counted over all retail maps)

Loot is small on purpose: food, drink, a little cash, tools of the trade.
Nothing here is worth more than about $150 unless it sits behind a lock.
"""
from f2lib import geometry as g

from . import plan

# --- scenery ---------------------------------------------------------------------------------
KEG_SHELF = 0x0200005E            # "Bar": the shelf of kegs and coils behind a counter (back wall)
STILL = 0x020003E8
SPOOL_TABLE, ROUND_TABLE = 0x02000003, 0x02000004        # cable-drum table, round wooden table
RED_TABLE, GREY_TABLE = 0x02000293, 0x02000294           # rectangular tables (ss101, ss102)
STOOLS = (0x020000EA, 0x020000EB, 0x020000EC, 0x020000ED)   # chair6..9: small swivel stools
CHAIR_BACK = (0x0200029A, 0x0200029B)    # ss108, ss109: wooden chairs seen from the front (stand below a table)
CHAIR_RIGHT = (0x0200029E, 0x020002A0)   # ss112, ss114
CHAIR_LEFT = (0x02000296, 0x02000297)    # ss104, ss105
CHAIR_FRONT = (0x020002A4, 0x020002A5)   # ss118, ss119: seen from behind (stand above a table)
ARMCHAIR = (0x020000E5, 0x020000E6, 0x020000E7, 0x020000E8)
COUCH = (0x02000063, 0x02000064)
BED_RIGHT, BED_BACK = 0x020000D2, 0x020000D5             # iron beds: head to the right wall / to the back wall
BED_SIDE, BED_NARROW = 0x020000D3, 0x020000D4
COT_BACK, COT_RIGHT = 0x020003B4, 0x020003B5             # rope cots (aybed1, aybed2)
CHILD_BED = (0x02000273, 0x02000274)
BUNK_BACK, BUNK_SIDE = 0x02000275, 0x02000276            # steel bunk beds
MATTRESS = (0x020000CE, 0x020000CF, 0x020000D0, 0x020000D1)   # flat, walkable
MEDICAL_BED = 0x02000387
RUGS = (0x02000178, 0x02000179, 0x0200017A)
WALL_LAMP_BACK, WALL_LAMP_RIGHT = 0x0200014E, 0x02000150     # stand one hex in front of the wall they hang on
POSTER = (0x02000382, 0x02000383)
SHELVES_BACK, SHELVES_RIGHT = (0x02000239, 0x0200023B), (0x0200023A, 0x0200023C)   # open shelving (bigshlf)
GOODS_BACK = (0x02000722, 0x02000723, 0x02000724, 0x02000725)     # rows of goods drawn on SHELVES_BACK, same hex
GOODS_RIGHT = (0x02000726, 0x02000727, 0x02000728, 0x02000729)    # ... on SHELVES_RIGHT
LONG_TABLE_EW, LONG_TABLE_NS = (0x020001ED, 0x020001EE), (0x020001F0, 0x020001F2)
STOVE = 0x020002AB
SINK_BACK, SINK_RIGHT = 0x0200011B, 0x0200011D
POT, BUCKET, BOWL = 0x02000174, 0x0200016D, 0x0200016B
BRAHMIN_MEAT = (0x02000513, 0x02000514, 0x02000515)
MED_TABLE = (0x0200028B, 0x0200028C, 0x02000355)
EYE_CHART = 0x020006D5
PEW = (0x02000106, 0x02000107, 0x02000108, 0x0200015B, 0x0200020D, 0x020000C8)
PULPIT, PODIUM = 0x020000C7, 0x0200020E
ATOM_FLAG = (0x0200027A, 0x0200027B, 0x0200027C)         # red banners with the trefoil
INCENSE = 0x02000645
LANTERN = 0x0200056A                                      # "Light": a lantern standing on the floor
WATER_PUMP, GENERATOR = 0x02000388, 0x02000290
MACHINERY = (0x02000249, 0x0200024A, 0x0200024B, 0x0200024C, 0x0200024D)
CONTROL_CABINET = (0x0200048F, 0x02000490)
SMALL_MACHINE = (0x02000343, 0x02000344)
PIPE_UPRIGHT, PIPE_TEE = 0x0200019F, 0x020001A6
COMPUTER = 0x02000009
DEAD_ROBOT = 0x020004CE
CRATES = (0x020000DC, 0x020000DD, 0x020000DE, 0x020000DF)
METAL_CRATE = (0x020000B4, 0x020000C1)
BARREL = (0x02000005, 0x02000006, 0x0200018C, 0x0200018D)

# --- wall-type pieces: bar counters (bar001 .. bar010 make one L-shaped counter) ---------------
def bar_piece(n):
    return 0x030001D2 + n


# --- containers (items) ----------------------------------------------------------------------
FRIDGE, ICE_CHEST = 42, 43
BOOKCASE_BACK, BOOKCASE_RIGHT = (60, 61, 62), (63, 64, 65)
DESK_BACK, DESK_RIGHT = 66, 67
DRESSER_RIGHT, DRESSER_BACK = 68, 70
FOOTLOCKER = (128, 129, 130, 131)
LOCKER_BACK, LOCKER_RIGHT = (132, 133, 188), (134, 135, 189)
BOOKSHELF_BACK, BOOKSHELF_RIGHT = (145, 146), (147, 149)
WOOD_SHELVES_BACK, WOOD_SHELVES_RIGHT = (151, 152), (153, 155)
WORKBENCH, TOOL_BOARD = 157, 158
FOOD_TABLE = (166, 167)
CLUTTER_EW, CLUTTER_NS = (168, 169, 172, 176, 177), (170, 171, 178, 179)   # table-top clutter for LONG_TABLE_*
SMALL_CRATE = 180
STEEL_DESK_BACK, STEEL_DESK_RIGHT = (185, 186), 187
STEEL_BOX = (199, 200, 203, 204)
CHEST = 245
AMMO_CRATE = (367, 369)
WALL_SAFE, FLOOR_SAFE, POOR_BOX = 501, 502, 521

# --- loot ------------------------------------------------------------------------------------
MONEY, BOTTLE_CAPS = 41, 519
STIMPAK, HEALING_POWDER, ANTIDOTE, FIRST_AID_KIT, RAD_X, MENTATS, JET = 40, 273, 49, 47, 109, 53, 259
EMPTY_HYPO, BROC, XANDER = 318, 271, 272
NUKA, BEER, BOOZE, GAMMA_GULP, RUM, ROT_GUT = 106, 124, 125, 310, 311, 469
JERKY, IGUANA, FRUIT, NOODLES, POOFS = 284, 103, 71, 226, 295
JUNK, TOOL, WRENCH, CROWBAR, OIL_CAN, ROPE, FLARE, LIGHTER, FLINT = 98, 75, 384, 20, 412, 127, 79, 101, 278
SHOVEL, METAL_POLE, FIREWOOD, WATER_FLASK = 289, 297, 286, 126
KNIFE, CLUB, SHIV, SPEAR, BRASS_KNUCKLES = 4, 5, 383, 7, 21
AMMO_10MM, SHELLS, BBS, BB_GUN = 29, 95, 163, 161
CATS_PAW, CARDS, DICE, EIGHT_BALL, SHADES, COSMETICS, SPECTACLES = 225, 436, 325, 328, 433, 317, 415
CONDOM, FLOWER, ROBES, LINT, DOG_TAGS, RADIO, SCOUT_BOOK = 314, 117, 113, 439, 56, 100, 86


def goods(d, shelf, hx, hy, rows):
    """An open shelf with goods on it (retail: New Reno's shops). rows = pieces of GOODS_* to stack."""
    d.prop(shelf, hx, hy)
    for pid in rows:
        d.flat(pid, hx, hy)


# ================================================================================= saloon
def saloon(d):
    """Hall 99..113 x 62..74, office 89..97 x 62..66, rented room 89..97 x 68..74.

    The counter is the retail L-shaped bar (Redding's Malamute, Modoc's inn): a
    corner piece, an arm up to the back wall and a run to the right, drawn on
    the even hexes of its row and the odd hexes of the row below. Behind it
    the keg shelves stand against the back wall, Gob and Moriarty in the lane
    between. The lane ends at Moriarty's office door: whoever wants in there
    walks the length of the bar under his eyes.
    """
    d.at("Moriarty's Saloon: hall")
    for hx in (106, 102):
        d.prop(KEG_SHELF, hx, 62, block=None)
    for hx in range(101, 111):
        d.close(hx, 63, "keg shelf")
    for hx in range(102, 111, 2):
        d.close(hx, 62, "keg shelf")
    d.prop(STILL, 100, 62)

    cx, cy = 111, 66
    d.wall(bar_piece(5), cx, cy)
    for n, hy in ((4, cy - 1), (3, cy - 2), (2, cy - 3), (1, cy - 4)):
        d.wall(bar_piece(n), cx, hy)
    run = [6, 7, 6, 7, 6, 7, 8, 9, 10]
    for i, n in enumerate(run):
        hx = cx - 1 - i
        d.wall(bar_piece(n), hx, cy + (hx & 1))
    end = cx - len(run)
    for hx in range(end + 1, cx, 2):               # the odd hexes between the pieces of the upper row
        d.close(hx, cy, "bar counter")
    d.close(end - 1, cy + 1, "bar counter")
    d.box(ICE_CHEST, 110, 64, [(BEER, 3), (GAMMA_GULP, 2), (NUKA, 2)], note="behind the bar")

    for hx, stool in zip((110, 108, 106, 104), STOOLS):
        d.prop(stool, hx, 68, block=None)
    # Burke's corner table, a second table for the regulars, Jericho's end of the bar.
    d.prop(SPOOL_TABLE, 100, 71, block=None)
    d.prop(ROUND_TABLE, 110, 71, block=None)
    d.prop(CHAIR_FRONT[0], 110, 70, block=None)
    d.prop(CHAIR_RIGHT[0], 111, 71, block=None)
    d.prop(CHAIR_LEFT[0], 109, 72, block=None)
    d.prop(BARREL[0], 113, 64, block=None)
    d.prop(CRATES[1], 112, 62, block=None)
    d.flat(WALL_LAMP_BACK, 112, 62)

    d.at("Moriarty's Saloon: office")
    d.box(DESK_BACK, 93, 62, [(MONEY, 22), (CARDS, 1), (BOTTLE_CAPS, 6)], note="under the terminal")
    d.box(BOOKCASE_RIGHT[0], 89, 64, [(CATS_PAW, 2), (ROT_GUT, 1)])
    d.prop(BED_SIDE, 97, 65)

    d.at("Moriarty's Saloon: rented room")
    d.prop(BED_BACK, 94, 69)
    d.box(DRESSER_BACK, 90, 68, [(CONDOM, 2), (COSMETICS, 1), (EMPTY_HYPO, 1), (MONEY, 6)])
    d.flat(RUGS[0], 93, 72)
    d.flat(WALL_LAMP_BACK, 96, 68)


# ================================================================================= craterside
def craterside(d):
    """Shop 71..81 x 64..74. Moira behind a counter of planks, goods on open shelves behind
    her and down the right wall, the workbench with its tool board in the back-left corner,
    her cot in the back-right one."""
    d.at("Craterside Supply")
    d.box(WORKBENCH, 79, 64, [(WRENCH, 1), (FLINT, 1), (METAL_POLE, 1)])
    d.box(TOOL_BOARD, 79, 64, [(CROWBAR, 1), (ROPE, 1)], block=None)
    goods(d, SHELVES_BACK[0], 74, 64, GOODS_BACK[:3])
    d.prop(COT_RIGHT, 72, 66)
    goods(d, SHELVES_RIGHT[0], 72, 70, GOODS_RIGHT[:3])
    d.box(LOCKER_RIGHT[0], 71, 72, [(FLARE, 2), (HEALING_POWDER, 1)])
    d.box(LOCKER_RIGHT[0], 71, 74, [(WATER_FLASK, 1), (NOODLES, 2)])
    d.prop(LONG_TABLE_EW[0], 76, 70)
    d.box(CLUTTER_EW[1], 76, 70, [(POOFS, 1)], block=None, note="odds and ends on the counter")
    d.prop(METAL_CRATE[0], 81, 67, block=None)
    d.prop(CRATES[0], 80, 73, block=None)


# ================================================================================= billy creel
def billy(d):
    """One room 119..127 x 64..72 for Billy and Maggie."""
    d.at("Billy Creel's House")
    d.prop(BED_RIGHT, 120, 66)
    d.prop(CHILD_BED[0], 126, 65)
    d.box(FOOTLOCKER[0], 124, 64, [(MONEY, 45), (AMMO_10MM, 1), (DOG_TAGS, 1), (BRASS_KNUCKLES, 1)],
          locked=True, note="his caravan years", tag="STASH_BILLY")
    d.box(BOOKCASE_RIGHT[0], 119, 69, [(BBS, 1), (CARDS, 1), (FRUIT, 2)])
    d.prop(ROUND_TABLE, 122, 70, block=None)
    d.prop(CHAIR_RIGHT[0], 123, 70, block=None)
    d.flat(RUGS[0], 124, 68)


# ================================================================================= church
def church(d):
    """Chapel 75..87 x 82..90, entered from the pool side. The pulpit and the banners stand
    at the far (right) wall, pews across the room with an aisle on the door's row."""
    d.at("Church of the Children of Atom")
    d.prop(PULPIT, 77, 86, block=None)
    d.prop(ATOM_FLAG[0], 76, 84, block=None)
    d.prop(ATOM_FLAG[1], 76, 88, block=None)
    d.prop(INCENSE, 78, 84, block=None)
    d.prop(INCENSE, 78, 88, block=None)
    for hx in (80, 83):
        d.prop(PEW[3], hx, 84)
        d.prop(PEW[3], hx, 88)
    d.box(POOR_BOX, 86, 84, [(MONEY, 7), (BOTTLE_CAPS, 3)], note="donations")
    d.box(BOOKSHELF_BACK[0], 85, 82, [(ROBES, 1), (FLOWER, 2), (WATER_FLASK, 1)])
    d.flat(MATTRESS[2], 78, 83)
    d.flat(MATTRESS[3], 76, 90)


# ================================================================================= common house
def common(d):
    """Bunkroom 113..125 x 82..90: beds for whoever has none. The mattress on COMMON_BED is the
    architect's and carries mgbed; the rest is here to be slept beside."""
    d.at("Common House")
    d.prop(BUNK_BACK, 117, 83)
    d.prop(COT_BACK, 124, 83)
    d.flat(MATTRESS[0], 116, 87)
    d.flat(MATTRESS[1], 120, 88)
    d.box(FOOTLOCKER[0], 120, 82, [(JERKY, 1), (FLINT, 1)])
    d.box(FOOTLOCKER[0], 114, 82, [(CATS_PAW, 1), (BEER, 1), (LINT, 1)])
    d.box(LOCKER_RIGHT[0], 113, 89, [(WATER_FLASK, 1), (KNIFE, 1)])
    d.prop(RED_TABLE, 123, 88)
    d.prop(CHAIR_FRONT[0], 123, 86, block=None)


# ================================================================================= water plant
def plant(d):
    """Machine hall 59..69 x 86..94 (the twin pump and the generator fill its back half),
    back room 59..69 x 96..100 behind the door in the cross wall."""
    d.at("Water Processing Plant: machine hall")
    d.prop(WATER_PUMP, 62, 89)
    d.prop(GENERATOR, 67, 88)
    d.prop(CONTROL_CABINET[0], 59, 92, block=None)
    d.prop(PIPE_UPRIGHT, 60, 94, block=None)
    d.prop(SMALL_MACHINE[0], 68, 91, block=None)
    d.at("Water Processing Plant: back room")
    d.box(STEEL_DESK_BACK[0], 62, 96, [(JET, 2), (MENTATS, 1), (STIMPAK, 1), (MONEY, 40)], locked=True,
          note="somebody's stash, and not Walter's", tag="STASH_PLANT")
    d.prop(COT_RIGHT, 60, 98)
    d.box(LOCKER_BACK[0], 67, 96, [(WRENCH, 1), (WATER_FLASK, 2), (OIL_CAN, 1)])


# ================================================================================= lucy west
def lucy(d):
    """One room 131..139 x 88..96; the door is in the right wall."""
    d.at("Lucy West's House")
    d.prop(BED_BACK, 137, 89)
    d.box(DRESSER_BACK, 132, 88, [(FLOWER, 1), (MONEY, 8), (COSMETICS, 1)])
    d.prop(ROUND_TABLE, 135, 93, block=None)
    d.prop(CHAIR_FRONT[0], 135, 92, block=None)
    d.box(BOOKCASE_RIGHT[0], 131, 95, [(FRUIT, 2), (NOODLES, 1)])
    d.flat(RUGS[2], 135, 91)


# ================================================================================= clinic
def clinic(d):
    """Ward 75..87 x 98..106: two beds with their monitors at the back wall, the steel table,
    the locked medicine locker, Doc Church's desk at the right wall."""
    d.at("Megaton Clinic")
    d.prop(MEDICAL_BED, 86, 98)
    d.prop(MEDICAL_BED, 82, 98)
    d.box(LOCKER_BACK[2], 77, 98, [(STIMPAK, 2), (ANTIDOTE, 2), (HEALING_POWDER, 2), (FIRST_AID_KIT, 1)],
          locked=True, note="the medicine locker", tag="STASH_CLINIC")
    d.prop(MED_TABLE[0], 78, 101)
    d.box(STEEL_DESK_RIGHT, 75, 104, [(EMPTY_HYPO, 2), (MONEY, 12), (SPECTACLES, 1)])
    d.flat(EYE_CHART, 80, 97)


# ================================================================================= brass lantern
def lantern(d):
    """Kitchen 113..125 x 98..102 and the open stall in front of it (113..125 x 104..108,
    the architect's counter on hx 117..121, hy 106..108)."""
    d.at("The Brass Lantern: kitchen")
    d.box(WOOD_SHELVES_BACK[0], 121, 98, [(FRUIT, 2), (NOODLES, 1), (POOFS, 1)])
    d.prop(STOVE, 118, 98)
    d.box(FRIDGE, 115, 98, [(IGUANA, 2), (JERKY, 2), (NUKA, 2)])
    d.box(FLOOR_SAFE, 113, 100, [(MONEY, 60), (BOTTLE_CAPS, 12)], locked=True, note="the takings",
          tag="STASH_LANTERN")
    d.flat(BRAHMIN_MEAT[0], 116, 100)
    d.prop(POT, 124, 100, block=None)
    d.at("The Brass Lantern: stall")
    for obj in d.m.objects_at(g.tile_at(*plan.LANTERN_BAR)):       # the architect's counter: the same back bar
        if obj.pid == KEG_SHELF:
            d.scripted(obj)
    d.box(FOOD_TABLE[0], 124, 105, [(JERKY, 1), (FRUIT, 1)])
    d.lamp(LANTERN, 114, 106, radius=4, percent=80, block=None)      # the lantern the place is named for
    for hx, stool in zip((116, 118, 122), STOOLS):
        d.prop(stool, hx, 110, block=None)
    d.prop(ROUND_TABLE, 124, 111, block=None)
    d.prop(CHAIR_FRONT[0], 124, 110, block=None)


# ================================================================================= sheriff
def sheriff(d):
    """Living room 79..87 x 114..120, armory closet 75..77 x 114..120 behind mgarmory's door.
    The weapons locker itself is the cast's (ARMORY_LOCKER)."""
    d.at("Sheriff's House: living room")
    d.box(DESK_BACK, 85, 114, [(SHADES, 1), (AMMO_10MM, 1), (MONEY, 15)])
    d.prop(BED_BACK, 82, 115)
    d.prop(COT_RIGHT, 79, 119)
    d.prop(ROUND_TABLE, 85, 118, block=None)
    d.prop(CHAIR_FRONT[0], 85, 117, block=None)
    d.at("Sheriff's House: armory")
    d.prop(DEAD_ROBOT, 76, 119, block=None)
    d.prop(COMPUTER, 75, 117, block=None)
    d.box(AMMO_CRATE[0], 76, 117, [(FLARE, 3), (SHELLS, 1)], block=None)


# ================================================================================= the empty house
def house(d):
    """Room 113..125 x 114..120. Bare until the sheriff hands over the key: a mattress (the
    architect's, with mgbed), empty lockers for the new owner's things, a table."""
    d.at("Empty House")
    d.box(LOCKER_BACK[0], 117, 114, note="storage, empty")
    d.box(LOCKER_BACK[0], 119, 114, note="storage, empty")
    d.box(FOOTLOCKER[0], 124, 114, note="storage, empty")
    d.prop(SPOOL_TABLE, 116, 118, block=None)
    d.prop(CHAIR_RIGHT[0], 117, 118, block=None)
    d.flat(RUGS[1], 120, 118)


def dress(d):
    saloon(d)
    craterside(d)
    billy(d)
    church(d)
    common(d)
    plant(d)
    lucy(d)
    clinic(d)
    lantern(d)
    sheriff(d)
    house(d)
