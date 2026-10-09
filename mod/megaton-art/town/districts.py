# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The town cut into districts, and the camera positions used to look at them. Pure data + geometry.

Coordinates are hexes of the town plan (mod/megaton/layout/plan.py): rising hx goes LEFT on
screen, rising hy goes DOWN-RIGHT; the gate is at the bottom (hy 127), the saloon at the back.

VIEWS       {name: (hx, hy)} view centres: what a 1280 x 960 window shows with the view centred there
            (town/mock.py shoots every one of them; a mock may add its own)
DISTRICTS   the eight areas of density.json, each a list of hex boxes (hx_lo, hy_lo, hx_hi, hy_hi);
            a hex belongs to the FIRST district of DISTRICT_ORDER one of whose boxes holds it
            ("perimeter" is not a box: every hex within PERIMETER_DEPTH of the outer wall)
"""

VIEWS = {
    "apron": (100, 134),            # arrival apron: caravan camp, Weld, the gate from outside
    "gate": (100, 124),             # the gate set and the yard just inside
    "gate-inside": (100, 114),      # the track between the sheriff's and the empty house
    "crater": (100, 96),            # the bomb, the pool and its ring
    "plaza": (102, 80),             # between the pool and the saloon
    "saloon": (102, 66),            # the saloon and the strip behind it
    "craterside": (76, 72),         # Craterside Supply and the north-east corner
    "east-lane": (80, 94),          # church, clinic and the lane to the water plant
    "plant": (64, 94),              # water plant and its yard, the east wall
    "sheriff": (80, 116),           # sheriff's house and the south-east corner
    "billy": (124, 70),             # Billy Creel's and the north-west corner
    "west-lane": (122, 92),         # common house, Lucy's, the lane between them
    "lantern": (120, 108),          # the Brass Lantern and the empty house
    "west-corner": (134, 112),      # the south-west corner behind the empty house
}
PHONE_VIEWS = ["apron", "gate", "crater", "plaza", "saloon", "east-lane", "lantern"]

PERIMETER_DEPTH = 3                 # hexes from the outer wall that count as "perimeter"
DISTRICT_ORDER = ["apron", "perimeter", "crater", "gate", "street", "saloon", "shops", "houses"]
DISTRICTS = {
    "apron": {"title": "arrival apron (outside the gate)", "boxes": [(56, 128, 144, 140)]},
    "perimeter": {"title": "perimeter (the strip along the inside of the outer wall)", "boxes": []},
    "crater": {"title": "crater ring (the pool and the ground round it)", "boxes": [(89, 83, 111, 107)]},
    "gate": {"title": "gate approach (the track from the gate to the pool, the yard inside the gate)",
             "boxes": [(89, 108, 111, 127)]},
    "street": {"title": "main street (the plaza in front of the saloon and the two lanes off the pool)",
               "boxes": [(83, 76, 117, 82), (71, 92, 88, 96), (112, 92, 129, 96)]},
    "saloon": {"title": "saloon side (the saloon, the strip behind it)", "boxes": [(83, 57, 117, 75)]},
    "shops": {"title": "shop side (screen right: Craterside, church, clinic, water plant, sheriff)",
              "boxes": [(56, 57, 88, 127)]},
    "houses": {"title": "house side (screen left: Billy's, common house, Lucy's, Brass Lantern, empty house)",
               "boxes": [(112, 57, 144, 127)]},
}
BUILDING_DISTRICT = {
    "saloon": "saloon", "craterside": "shops", "church": "shops", "plant": "shops", "clinic": "shops", "sheriff": "shops",
    "billy": "houses", "common": "houses", "lucy": "houses", "lantern": "houses", "house": "houses",
}


def in_box(hx, hy, box):
    return box[0] <= hx <= box[2] and box[1] <= hy <= box[3]


def district_of(hx, hy, wall_distance=None):
    """Name of the district hex (hx, hy) belongs to, or None. wall_distance: hexes to the nearest
    hex of the outer wall for a hex inside it (None = unknown / outside)."""
    if in_box(hx, hy, DISTRICTS["apron"]["boxes"][0]):
        return "apron"
    if wall_distance is not None and wall_distance <= PERIMETER_DEPTH:
        return "perimeter"
    for name in DISTRICT_ORDER:
        if name in ("apron", "perimeter"):
            continue
        if any(in_box(hx, hy, box) for box in DISTRICTS[name]["boxes"]):
            return name
    return None
