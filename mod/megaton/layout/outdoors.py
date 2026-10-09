# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Everything under the sky: signs, lamps, junk, the pool's furniture, the yards, the apron.

Read dressing.py first. Places are named as in the design brief (section 4.6);
coordinates are hexes of plan.py. What is where, clockwise from the gate:

    gate (inside)   signboard, lamp posts, a wreck and crates against the wall
    plant yard      two tanks, the pipe along the church wall, the water sign
    east nook       brahmin, hay, a cart (between Craterside and the plant)
    alley           the outhouse between Craterside and the saloon
    plaza           lamp posts, a fire barrel, the plank ramp down to the pool
    west nook       a car wreck and scrap (between Billy's and Lucy's)
    bus yard        Nathan and Manya's wrecked truck, the second outhouse
    pool            podium, banners, incense, the warning sign
    apron           Weld's mat, the sniper's booth, Micky's corner, the caravan
                    camp with its fire, wagons and brahmin, Silver's lean-to

Lights: lamp posts and fire barrels carry their own light (dressing.lamp),
so the town reads at night from visible sources; the architect's invisible
lights (buildings.add_lights) fill in rooms and doorsteps.
"""
from . import spots
from .interiors import (ARMCHAIR, ATOM_FLAG, BARREL, BUCKET, CRATES, INCENSE, LANTERN, MATTRESS, METAL_CRATE,
                        PIPE_TEE, PODIUM, POT, SMALL_CRATE, SPOOL_TABLE,
                        JERKY, JUNK, ROPE, ROT_GUT, WATER_FLASK, FIREWOOD, LINT)

SIGN_BAR, SIGN_STORE, SIGN_SHERIFF, SIGN_CLINIC = 0x02000236, 0x02000256, 0x0200058C, 0x0200067D
SIGN_WANTED, SIGN_WATER, SIGN_RADIATION, SIGN_MOTEL = 0x020004CC, 0x0200036D, 0x020004A3, 0x02000377
BULLETIN_BOARD = 0x02000254
LAMP_POST = 0x02000376               # "Lamp Post", junklit1: a pole with a salvaged lamp
FIRE_BARREL = 0x02000001             # "Burning Metal Barrel"
FIRE_PIT = 0x02000264
OUTHOUSE = 0x020003E3
GUARD_SHACK = 0x02000255
TRUCK = 0x02000144
CARS = (0x020000E0, 0x020000E1, 0x020000E2, 0x020000E3, 0x020000E4)
WAGONS = (0x0200020F, 0x02000210, 0x02000213)
CART = 0x02000170
TANKS = (0x02000494, 0x020004A6)
GROUND_PIPE = 0x02000493             # "Pipes", gekpipe1: eight hexes of pipe with an elbow, along a row
TIRES, TIRE = 0x02000007, 0x02000065
JUNK_HEAPS = (0x0200006A, 0x0200006B, 0x0200006D, 0x0200010F, 0x02000110, 0x02000112)
SCRAP = (0x020000FC, 0x020000FD, 0x020000FE, 0x020000FF, 0x02000100)
TRASH = (0x02000137, 0x02000138, 0x02000139, 0x0200013A)
BARREL_STACK = (0x0200018E, 0x0200018F)
TOXIC_BARREL = (0x02000227, 0x02000228)
ROCKS = (0x020001AC, 0x020001AD, 0x020001AE, 0x020001AF, 0x020001B0, 0x020001B1)
PLANK = 0x02000719                   # a plank ramp; the picture runs seven rows down from its hex
MAT = 0x02000215
HAY = (0x020004E0, 0x020004E1, 0x020004E3)
POLE = (0x02000181, 0x02000182)
TUB = 0x02000145
BONES = (0x02000052, 0x02000053)
BRAHMIN, DOG = 0x0100000A, 0x01000009


def signs(d):
    """Signs hang where the retail maps hang the same art: the BAR and GENERAL STORE signs one
    row in front of a front wall, the Sheriff, Clinic and Wanted signs on a wall's own hex."""
    d.at("signs")
    d.flat(SIGN_BAR, 107, 76)
    d.flat(SIGN_STORE, 79, 76)
    d.flat(SIGN_SHERIFF, 88, 118)
    d.flat(SIGN_CLINIC, 84, 107)
    d.flat(SIGN_WANTED, 83, 121)
    d.flat(SIGN_MOTEL, 119, 92)
    d.prop(SIGN_WATER, 70, 103, block=None)
    d.prop(BULLETIN_BOARD, 95, 123)


def lamps(d):
    d.at("street lamps")
    for hx, hy in ((96, 120), (104, 120),            # inside the gate
                   (95, 78), (111, 80),              # plaza
                   (90, 99), (110, 99),              # the track at the pool, by the clinic and the Brass Lantern
                   (72, 90), (128, 93),              # plant door, the lane to Lucy's
                   (74, 77), (126, 76)):             # Craterside, Billy's
        d.lamp(LAMP_POST, hx, hy, radius=5, percent=75, block=None)
    d.at("fire barrels")
    for hx, hy in ((102, 81), (133, 108), (66, 82), (88, 131), (107, 132)):
        d.lamp(FIRE_BARREL, hx, hy, radius=4, percent=85, block=None)


def pool(d):
    """The Confessor's side of the pool: he preaches from the slime beside the bomb, his
    podium, banners and incense stand on the bank towards the track."""
    d.at("pool")
    d.prop(PODIUM, 105, 98, block=None)
    d.prop(ATOM_FLAG[0], 107, 97, block=None)
    d.prop(ATOM_FLAG[1], 104, 100, block=None)
    d.prop(INCENSE, 106, 99, block=None)
    d.prop(SIGN_RADIATION, 95, 101, block=None)
    d.lamp(LANTERN, 103, 99, radius=3, percent=70, block=None)
    d.at("church yard")
    d.prop(ATOM_FLAG[2], 90, 83, block=None)          # the "atom" on a pole
    d.prop(PIPE_TEE, 89, 91, block=None)


def yards(d):
    d.at("inside the gate")
    d.prop(CARS[1], 80, 124)
    # in the lane right of the track, in plain sight: behind the gate's bus wall nobody would find it
    d.box(SMALL_CRATE, 95, 116, [(JUNK, 1)], block=None, note="scrap for Walter's pipes")
    d.prop(TIRES, 86, 125, block=None)
    d.prop(CRATES[0], 92, 125, block=None)
    d.prop(METAL_CRATE[1], 91, 124, block=None)
    d.prop(JUNK_HEAPS[3], 108, 124)
    d.prop(TIRE, 106, 125, block=None)
    d.prop(BARREL[2], 109, 125, block=None)
    d.prop(PIPE_TEE, spots.SPOTS["LEAK1"][0] + 1, spots.SPOTS["LEAK1"][1] + 1, block=None)     # beside Walter's first leak
    d.prop(TIRES, 71, 124, block=None)
    d.prop(BARREL_STACK[0], 70, 118, block=None)
    d.prop(TOXIC_BARREL[0], 71, 119, block=None)
    d.prop(JUNK_HEAPS[0], 65, 117)
    d.prop(JUNK_HEAPS[1], 129, 122)
    d.prop(TIRES, 130, 118, block=None)
    d.prop(BARREL[0], 128, 124, block=None)

    d.at("plant yard")
    d.prop(TANKS[0], 66, 106)
    d.prop(TANKS[1], 61, 108)
    d.prop(GROUND_PIPE, 67, 112)
    d.prop(BARREL[1], 69, 110, block=None)

    d.at("east nook")
    d.flat(HAY[0], 63, 75)
    d.flat(HAY[2], 66, 78)
    d.critter(BRAHMIN, 61, 77, rotation=2)
    d.critter(BRAHMIN, 65, 74, rotation=4)
    d.prop(CART, 66, 80)
    d.prop(TUB, 59, 80, block=None)
    d.prop(BARREL_STACK[1], 60, 72, block=None)
    d.prop(BUCKET, 64, 79, block=None)

    d.at("Craterside's doorstep")
    d.prop(CRATES[1], 72, 77, block=None)
    d.prop(BARREL[1], 71, 78, block=None)
    d.prop(METAL_CRATE[0], 73, 79, block=None)

    d.at("alley")
    d.prop(OUTHOUSE, 84, 67)
    d.prop(BARREL[3], 86, 63, block=None)
    d.prop(CRATES[2], 84, 62, block=None)
    d.flat(TRASH[0], 85, 70)

    d.at("plaza")
    d.flat(PLANK, 105, 76)
    d.flat(PLANK, 100, 105)
    for hx, hy, i in ((96, 109, 0), (94, 110, 1), (93, 111, 2), (104, 109, 3), (107, 110, 4), (109, 111, 5)):
        d.prop(ROCKS[i], hx, hy, block=None)
    d.critter(DOG, 115, 79, rotation=2)

    d.at("west nook")
    d.prop(CARS[3], 137, 78)
    d.prop(JUNK_HEAPS[4], 141, 73)
    d.box(SMALL_CRATE, 133, 81, [(JUNK, 1), (ROPE, 1)], block=None, note="scrap for Walter's pipes")
    d.prop(TIRES, 131, 72, block=None)
    d.prop(BARREL[0], 140, 84, block=None)
    d.prop(SCRAP[2], 134, 83, block=None)

    d.at("bus yard")
    d.prop(TRUCK, 137, 106)
    d.prop(OUTHOUSE, 131, 100)
    d.prop(ARMCHAIR[0], 131, 105, block=None)
    d.prop(SPOOL_TABLE, 132, 104, block=None)
    d.prop(TIRES, 141, 111, block=None)
    d.prop(JUNK_HEAPS[2], 141, 101)
    d.prop(PIPE_TEE, 111, 90, block=None)


def apron(d):
    d.at("apron: gate")
    d.flat(MAT, *spots.SPOTS["WELD"][:2])
    d.prop(GUARD_SHACK, 111, 134)
    d.prop(TIRES, 104, 131, block=None)
    d.prop(METAL_CRATE[0], 106, 133, block=None)
    d.flat(MATTRESS[3], 91, 130)
    d.flat(TRASH[1], 89, 130)
    d.prop(BUCKET, 92, 129, block=None)

    d.at("apron: caravan camp")
    d.lamp(FIRE_PIT, 81, 134, radius=5, percent=90, block=None)
    d.prop(WAGONS[2], 76, 132)
    d.prop(WAGONS[0], 86, 136)
    d.critter(BRAHMIN, 78, 135, rotation=1)
    d.critter(BRAHMIN, 74, 136, rotation=3)
    d.prop(CRATES[3], 79, 130, block=None)
    d.box(SMALL_CRATE, 80, 130, [(JERKY, 2), (FIREWOOD, 1)], block=None)
    d.flat(MATTRESS[2], 84, 132)

    d.at("apron: Silver's lean-to")
    d.prop(POLE[0], 126, 131, block=None)
    d.prop(POLE[1], 122, 132, block=None)
    d.flat(HAY[1], 125, 134)
    d.prop(ROCKS[2], 121, 135, block=None)
    d.flat(BONES[0], 122, 136)
    d.prop(POT, 123, 135, block=None)
    d.box(SMALL_CRATE, 126, 134, [(ROT_GUT, 1), (WATER_FLASK, 1), (LINT, 1)], block=None)


def dress(d):
    signs(d)
    lamps(d)
    pool(d)
    yards(d)
    apron(d)
