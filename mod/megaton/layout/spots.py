# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Named places on the Megaton map.

Scripts never hard-code tile numbers: build.py turns this table into
scripts/tiles.h (TILE_<NAME>), and the map builder places every NPC and
scripted object from the same table, so the two cannot drift apart.

Coordinates are hexes (hx, hy); tile = hy * 200 + hx. Rotation 0..5 is the
facing for NPCs (0 = north-east, clockwise). The names are a contract with
the scripts and must stay; the coordinates belong to the map builder and may
move as the layout is refined. They are positions on the town of plan.py:
tests/layout/test_layout.py fails if a spot is blocked, cut off from the
entrance, or outside the room / side of town it belongs to (its PLACES table),
so add a line there when you append a spot that has to be somewhere specific.

WHERE PEOPLE STAND. The camera looks from the bottom of the screen: a building's FRONT wall
(its highest hy) and LEFT wall (its highest hx) stand between it and the room, and every roof
is painted 96 pixels above its floor, over whatever lies up-screen of the building. Somebody
who stands within five rows of his room's front wall, within three hexes of its left wall, or
in a lane behind another building, cannot be seen and cannot be clicked or tapped except from
the next hex. tests/layout/test_layout.py (seen) measures every cast member and standing post
(layout/sight.py: `cd mod/megaton && python3 -m layout.sight --seen out`); a new spot has to
pass it.
"""

SPOTS = {
    # Arrival
    "ENTRY": (101, 136, 0),            # player start, outside the gate
    "GATE": (100, 127, 0),              # the gate object
    "SIMMS_GREET": (100, 117, 2),       # where Simms meets a newcomer, just inside
    "GATE_EXIT": (100, 138, 2),        # where fleeing NPCs leave the map
    # Main cast
    "WELD": (97, 130, 2),
    "SIMMS": (99, 113, 2),               # two hexes right of the track's middle: the power pole on (106, 120) is not between him and the camera
    "HARDEN": (83, 115, 3),              # at the back of the living room: a boy four rows behind the front wall is hidden by it
    "BURKE": (100, 70, 2),
    "BURKE_TABLE": (101, 71, 0),        # Simms stands here for the confrontation
    "BURKE_RENDEZVOUS": (83, 134, 0),  # Burke waits here once the charge is planted
    "BOMB": (100, 94, 0),
    "CROMWELL": (103, 96, 2),
    "MAYA": (81, 86, 3),
    # Saloon
    "MORIARTY": (103, 64, 2),
    "GOB": (109, 64, 2),
    "NOVA": (107, 69, 2),
    "JERICHO": (110, 67, 1),             # at the bar's end, four hexes clear of the left wall that hid him
    "LUCY": (105, 69, 2),               # by the bar stools, facing the saloon door: she watches who comes in. Six rows behind the front wall, which hid her completely when she stood two rows behind it
    "OFFICE_DOOR": (98, 64, 0),
    "TERMINAL": (94, 62, 2),
    "CABINET": (90, 62, 2),
    "STRONGBOX": (90, 65, 2),
    "NOVA_BED": (92, 71, 0),
    # Shops and services
    "MOIRA": (76, 68, 2),
    "MERC": (78, 70, 2),                 # at the left end of Moira's counter, facing the customers. Four rows behind the front wall on (80, 71) he was hidden by it; by the workbench on (78, 67) he could be seen, but the counter's blocked hexes stood between him and every customer, and he guarded nothing (obj_can_see_obj stops at any blocked hex)
    "DOC": (81, 101, 3),
    "JENNY": (119, 105, 2),
    "WALTER": (64, 90, 2),
    "LEAK1": (108, 114, 0),              # in the lane beside the empty house, clear of the container stack at the gate
    "LEAK2": (110, 89, 0),
    "LEAK3": (90, 90, 0),
    # Houses
    "HOUSE_DOOR": (126, 116, 0),         # in the house's LEFT wall, round the corner from the Brass Lantern: a door facing the track would be hidden under the roof
    "HOUSE_BED": (121, 116, 0),
    "COMMON_BED": (121, 84, 0),
    "ARMORY_DOOR": (78, 116, 0),
    "BILLY": (123, 68, 2),
    "MAGGIE": (116, 74, 2),              # beside the bench in front of Billy's house; further down the plaza she was under the common house's roof
    "NATHAN": (129, 103, 2),
    # Townsfolk
    "SETTLER1": (106, 103, 0),
    "SETTLER2": (96, 103, 5),
    "SETTLER3": (100, 79, 2),
    # Outside the walls
    "STOCKHOLM": (105, 130, 2),
    "MICKY": (90, 129, 2),
    "TRADER": (81, 132, 1),
    "SILVER": (124, 133, 2),
    # Burke's hired guns wait at the caravan camp, about sixteen hexes from ENTRY and to one side of it:
    # the returning player sees them get up and has the road behind him (they stood 3, 5 and 8 hexes from
    # ENTRY, around it, and a visit began with half his hit points gone). mghitman.ssl walks them in.
    "HITMAN1": (86, 132, 1),
    "HITMAN2": (87, 130, 1),
    "HITMAN3": (84, 133, 1),
    # Flavour group: a fourth settler, the places settlers walk to (open ground, never
    # in a doorway; mgsettlr.ssl explains who goes where and when), the weapons locker.
    "SETTLER4": (91, 109, 3),          # idler beside the clinic, watching the gate road
    "LOITER_SALOON": (108, 78, 5),     # in front of the saloon, clear of its door (evenings)
    "LOITER_LANTERN": (115, 107, 5),   # at the right end of the Brass Lantern's counter, under its awning (the stools' side is under the house's roof)
    "LOITER_COMMON": (111, 91, 0),     # beside the common house, at its pool-side corner (nights)
    "LOITER_GATE": (104, 114, 2),      # inside the gate, off the track, where the gate's container stack does not hide him
    "LOITER_WATER": (73, 91, 1),       # by the water plant, clear of its door and of the clinic's roof
    "ARMORY_LOCKER": (76, 114, 2),     # weapons locker at the back of the armory closet, behind ARMORY_DOOR
    # Main quest group: the arrival trigger across the track (mgspgate.ssl), and where Simms
    # stands on his evening round, 18:00 to 22:00, at the pool's edge on the entry path (mgsimms.ssl).
    "ARRIVAL": (101, 132, 0),
    "SIMMS_POOL": (100, 104, 5),
    # Main quest group: waypoints of the walk between the saloon and the gate (Simms going to arrest
    # Burke and back, Burke leaving town). The engine's pathfinder gives up on walks much longer than
    # twenty hexes, so mgcore.h's mg_way_body sends a walker from one of these to the next, in order
    # of hy: GATE_EXIT, WAY_APRON, WAY_GATE, SIMMS_POOL, WAY_POOL, WAY_SALOON, the saloon. Each must be
    # open ground no more than about eighteen walkable hexes from its neighbours in that list.
    "WAY_APRON": (100, 131, 0),        # on the track outside the gate
    "WAY_GATE": (100, 122, 0),         # on the track inside the gate
    "WAY_POOL": (111, 95, 0),          # east of the pool, clear of the goo
    "WAY_SALOON": (107, 79, 0),        # in front of the saloon door
    # Where megaton.ssl centres the view when the player arrives from outside (frame_arrival): just
    # inside the gate, right of the track, so that a 380-pixel-high window (the phone) shows the whole
    # MEGATON sign over the gate at its top and the newcomer on ENTRY at its foot. Nobody stands here.
    "ARRIVAL_VIEW": (98, 124, 0),
}


def tile(name):
    hx, hy, _ = SPOTS[name]
    return hy * 200 + hx
