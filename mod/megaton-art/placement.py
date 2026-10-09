#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Where every piece of the art mod goes in Megaton: the plan the town is built from.

    python3 mod/megaton-art/placement.py            check against manifest.json and the town as
                                                    mod/megaton/layout builds it today (without art),
                                                    write mod/megaton-art/placement.json
    python3 mod/megaton-art/placement.py --check    the same without writing (exit code 1 on problems)

THE TOWN USES THIS FILE DIRECTLY: mod/megaton/layout/art.py imports the original-piece plan, resolves it against the
map it has just built (resolve(town=...)) and applies the result, so every town build re-checks
every removal, footprint, free hex and reachability against the layout of the moment, and a
problem stops the build. The reviewed density additions and exact tile operations are frozen in
placement-v2.json and validated by layout/density.py. placement.json is the combined plan
written out for people and for the review stage (stage/town/build_stage.py builds its map from it).

Coordinates are hexes (hx, hy) of mod/megaton/layout/plan.py: tile = hy * 200 + hx, rising hx
goes screen-LEFT, rising hy goes down-right. PLAN below copies the handful of plan constants
the placements hang on; if the town moves one of them, the pieces of that group move with it.

An entry (`put`) is one piece on one or more origins:
    piece     name in manifest.json
    at        origin hexes. how="placer": pipeline.place.Placer.place (origin EVEN hx, EVEN hy; adds
              the parts in paint order, invisible blockers on footprint hexes without a picture, and the
              stock script "animfrvr" on animated parts). how="any": the piece is one hex big, its
              parts' PIDs go on the hex directly, in the order shadow, halo, main, glow (any parity).
              how="object": the town's cast creates the ONE main part itself (it carries a script).
    remove    stock objects of the town that the piece replaces: (hx, hy, pid). The check below
              fails when one is no longer there (the layout moved: move the placement with it). reach=N also drops the invisible "Secret Blocking
              Hex" objects within N hexes of each removed object (the blockers of its picture).
    free      hexes that must stay walkable next to the piece (doorways, access hexes)
    note      where and why, for a person

VERDICTS (the art director's judgement after the engine review; see the docstring of
stage/town/build_stage.py for how it was made):
    "upgrade"     clearly better than the stock object it replaces / adds something the town lacked
    "acceptable"  usable; flaws listed in "flaws"
    "cut"         do not use: worse than stock, or no place in the town. The piece stays in the
                  manifest (its ids are claimed for good) but is not placed.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "placement.json")

PLAN = {
    "source": "mod/megaton/layout/plan.py and spots.py, read 2026-10-09",
    "GATE": (100, 127),             # door hex of the gate, on the front wall (hy 127)
    "BOMB": (100, 94),
    "ENTRY": (101, 136),
    "LANTERN_BAR": (117, 108),
}
GATE, BOMB = PLAN["GATE"], PLAN["BOMB"]

# stock PIDs named in removals
FENCE = None                        # any wall object on the hex (the stockade's sheets differ per hex)
SECRET_BLOCK = 0x02000043
WALL_BLOCK = 0x0300026E             # "Wall s.t.": the stockade's invisible blocker on row hy + 1
LIGHT_SOURCE = 0x0200008D
LAMP_POST = 0x02000376
BURNING_BARREL = 0x02000001
STOCK_GATE_DOOR = 0x0200071A

RULES = [
    "Mount mod/megaton-art/out/patch-art.dat beside the town patch; build the map with "
    "GameFiles(overlay=[..., 'mod/megaton-art/out']). The patch holds art, protos and the pro_scen / pro_wall "
    "message files only.",
    "how='placer': pipeline.place.Placer().place(map, piece, tile_of_origin). Origin hexes have EVEN hx and EVEN hy.",
    "how='any': one-hex pieces. Add the parts' PIDs (manifest.json pieces[name].parts, order shadow, halo, main, "
    "glow) on the hex itself; attach parts[i].script where it is not null.",
    "how='object': the cast creates the main part's PID with its own script (see hooks).",
    "Remove every object listed under 'remove' first; 'free' hexes must stay walkable.",
    "EAVE RULE. Roof tiles are painted after all objects, and a stock shack roof overhangs its FRONT wall "
    "(row hy) by 1.7 m: whatever stands d metres in front of that wall is cut off above 1.85 m + 0.48 * d "
    "(row hy+1: 2.2 m, hy+3: 3.0 m, hy+5: 3.8 m). A LEFT wall has no overhang. Behind a BACK wall the roof "
    "hides everything below 2.6 m on row hy-2. The roofline pieces (sg_roof_*, sg_moriarty) are built for row hy-3.",
    "A lamp piece (a part with 'light' in the manifest) replaces the invisible Light Source 0x0200008D beside it: "
    "do not keep both, or the spot is lit twice.",
    "Halo parts (layer 'halo') tint the ground yellow by day as well as by night; that is how the engine's "
    "'energy' translucency works. It is faint by day. A map script may hide them until dusk; none does here.",
    "Pieces marked verdict 'cut' are not placed. Their protos exist (ids are never reused) but nothing refers to them.",
    "CLICK RULE. The engine gives a click to the LAST opaque thing painted under the cursor (hexes in tile order: "
    "row by row down the screen), and nothing at all under a roof. A piece that stands between the camera and a "
    "door, a person's post or a container - on a later hex, with pixels over it - takes the clicks meant for it, "
    "however right it looks. tests/layout/test_layout.py (clickable) measures every door, cast member, scripted "
    "object and container against the town without the art; a placement that hides one fails the test.",
]

GROUPS = {
    "gate": [
        "The junk prefab 'carwall-den-b' (perimeter.JUNK, stamped at (104, 126)) STAYS in front of mg_wall_hull and "
        "mg_wall_boxes: wrecks in front, fuselage and containers behind and above them is the layered look wanted. "
        "Only the fence sheets and wall blockers listed under each piece's 'remove' go.",
        "Small windows. In a 1040x480 window (380 px of map) the view reaches 190 px above the player. From the arrival "
        "hex (101, 136) the gate's foot is 108 px up: the leaves with their MEGA | TON stencil (to 158 px) are on "
        "screen, the sign's letters (237..281 px) are not; they are whole only from the two rows at the gate's foot, "
        "and again from anywhere on the track INSIDE the town within 27 rows of the gate. In a 1280x960 window the "
        "sign is on screen on arrival. Moving plan ENTRY nearer than row 130 is the only way to show the sign "
        "on arrival in a small window.",
        "Night. mg_gate_sign is the gate's lamp (8 hexes, 100 %): the two invisible lights the town has outside the "
        "gate ((96, 131), (104, 131)) are removed; mg_pole (106, 120) replaces the lamp post on (104, 120) and the "
        "invisible light on (105, 123); sg_worklamp (96, 120) replaces the lamp post there and the light on (95, 123).",
        "The door: see hooks.gate_door. Keep kit.stockade(..., gates=[plan.GATE]) with the door object, its MULTIHEX "
        "flag and script; pass every hex under 'remove' of the gate-group pieces as `gaps`.",
    ],
    "street": [
        "Roofs decide what shows. A stock roof is painted after every object: it hides whatever stands behind the "
        "building (lower than 2.6 m two rows behind its back wall, 0.4 m less per further row) and its eave cuts off "
        "whatever stands in front (see rules). Every placement here was looked at with roofs on; move a piece and "
        "look again (stage/town/build_stage.py renders the offline pictures in seconds).",
        "Several stock objects that pieces replace carry a script of the town (flags, signs, the bar, the podium): "
        "'remove' entries say scripted=true. Attach that script to the new piece's main part.",
        "The burning barrels stay stock (sg_fire_barrel is cut).",
        "Small windows: lettering under 0.4 m (14 px) is an icon, not text, at phone size. The cross, the star, the "
        "atom, the trefoil and the lantern carry their signs; MEGATON, MORIARTY'S and SALOON are big enough to read.",
    ],
    "crater": [
        "The ring was designed on open ground; in the town the common house, the Brass Lantern kitchen (both hx 112), "
        "the church and the clinic (hx 88) stand 12 hexes from the bomb, so the flanks are left to the buildings and "
        "nothing stands within a hex of a door.",
        "The bomb: see hooks.bomb. Two invisible pool lights of layout/buildings.py add_lights may stay.",
        "Do not stand tall things between the gate and the bomb on hx 104..108 south of row 104: from the track they "
        "cut across the bomb's lettering (a pole on (106, 100) did).",
    ],
}

ENTRIES = []
VERDICTS = {}


def put(piece, at, how="placer", group="", remove=(), reach=0, free=(), note=""):
    origins = [tuple(at)] if isinstance(at[0], int) else [tuple(a) for a in at]
    ENTRIES.append(dict(piece=piece, origins=origins, how=how, group=group, remove=[tuple(r) for r in remove],
                        reach=reach, free=[tuple(f) for f in free], note=note))


def verdict(piece, value, why, flaws=()):
    VERDICTS[piece] = dict(verdict=value, why=why, flaws=list(flaws))


def off(base, *offsets):
    return [(base[0] + dx, base[1] + dy) for dx, dy in offsets]


# ======================================================================================== GATE
gx, gy = GATE[0], GATE[1] - 1                 # origin of the gate set: (100, 126)

put("mg_gate", (gx, gy), group="gate",
    remove=[(96, 127, FENCE), (103, 127, FENCE), (104, 127, FENCE),
            (97, 127, SECRET_BLOCK), (98, 127, SECRET_BLOCK), (102, 127, SECRET_BLOCK), (103, 128, WALL_BLOCK)],
    free=[(99, 127), (100, 127), (101, 127), (99, 128), (100, 128), (101, 128), (99, 126), (100, 126), (101, 126)],
    note="Stands in the gate opening: the piece's hex (0, 1) is plan.GATE. It replaces the stockade sheets on "
         "(96, 127), (103, 127), (104, 127), the three secret blockers beside the door and the wall blocker on "
         "(103, 128); it blocks all of those itself, plus (96, 128) and (104, 128). The passage (99..101, 127) "
         "stays the door's. perimeter.build: pass these hexes as kit.stockade gaps.")
put("mg_gate_sign", (gx, gy), group="gate",
    remove=[(96, 131, LIGHT_SOURCE), (104, 131, LIGHT_SOURCE)],
    note="Same origin as mg_gate. One part on (100, 128) that does not block: MEGATON, the bulb string, two "
         "floodlights. It is the gate's lamp (8 hexes, 100 %), so the two invisible lights outside the gate go.")
put("mg_wire_gate", (gx, gy), group="gate",
    note="Cables from the sign's upright to the pole on (106, 120). Three parts that do not block.")
put("mg_wall_bus", (88, 126), group="gate",
    remove=[(hx, 127, FENCE) for hx in range(88, 96)] + [(hx, 128, WALL_BLOCK) for hx in (89, 91, 93, 95)],
    note="Right of the gate on screen, wall hexes (88..95, 127): the open apron side, seen whole.")
put("mg_wall_cars", (82, 126), group="gate",
    remove=[(hx, 127, FENCE) for hx in range(82, 88)] + [(hx, 128, WALL_BLOCK) for hx in (83, 85, 87)],
    note="Right again, wall hexes (82..87, 127).")
put("mg_wall_hull", (104, 126), group="gate",
    remove=[(hx, 127, FENCE) for hx in range(105, 109)] + [(hx, 128, WALL_BLOCK) for hx in (105, 107)],
    note="Left of the gate, wall hexes (105..108, 127): the fuselage barrel carries on from the gate's left bay.")
put("mg_wall_boxes", (108, 126), group="gate",
    remove=[(hx, 127, FENCE) for hx in range(109, 117)] + [(hx, 128, WALL_BLOCK) for hx in (109, 111, 113, 115)],
    note="Left again, wall hexes (109..116, 127): the container stack, 5.2 m tall.")
put("mg_nest", (86, 124), group="gate",
    remove=[(86, 125, 0x02000007)],
    note="Watch platform inside the wall, where the bus meets the car-door wall: posts on (86, 124), (88, 124), "
         "(86, 126), (88, 126), ladder foot on (89, 125), in front of the sheriff's house's windowless front wall. "
         "The town's tyre stack on (86, 125) goes. Planned on (92, 124), where it stood between the camera and the "
         "sheriff's door (88, 116) and left a sixth of the door to click.")
put("mg_pole", [(106, 120), (106, 110)], group="gate",
    remove=[(104, 120, LAMP_POST), (105, 123, LIGHT_SOURCE)],
    note="Utility poles up the left side of the track; each is a lamp (5 hexes, 80 %). (106, 120) is the pole the "
         "gate's cables end on; it replaces the stock lamp post on (104, 120) and the invisible light on (105, 123). "
         "Do NOT carry the line on to (106, 100): from the gate that pole and its cables stand across the bomb.")
put("mg_wire_v", (106, 110), group="gate",
    note="Cables down a hex column: far pole on the origin, near pole on (0, +10).")

# ====================================================================================== STREET
put("sg_moriarty", (96, 58), group="street",
    note="Behind the saloon: legs on (96, 58) and (104, 58), between its back wall (hy 61) and the town wall. The "
         "board rises over the far edge of the saloon roof. The stock BAR neon on (107, 76) stays as the door sign.")
put("sg_roof_stack", [(110, 58), (122, 110)], group="street",
    note="Roofline (origin on row hy_back - 3): saloon left end; the empty house (back wall hy 113).")
put("sg_roof_vent", [(92, 58), (62, 82)], group="street",
    note="Roofline: saloon right end; water plant (back wall hy 85). Animated fan.")
put("sg_roof_tank", (122, 60), group="street", note="Roofline: Billy Creel's house (back wall hy 63).")
put("sg_roof_antenna", (76, 60), group="street", note="Roofline: Craterside Supply (back wall hy 63).")
put("sg_roof_patch", (78, 110), group="street", note="Roofline: the sheriff's house (back wall hy 113).")

put("sg_awning_u", [(112, 104)], group="street",
    note="Against a FRONT wall on row hy: origin on row hy + 1, posts on (0, 1) and (4, 1). BESIDE a door, never "
         "over it: the roof of this piece is the last thing painted there, so a click on a door under it lands on "
         "the awning (planned over the Brass Lantern's kitchen door on (116, 104), 26 % of the door stayed "
         "clickable). It stands over the right end of the Brass Lantern's stall, posts on (112, 105) and (116, 105). "
         "NOT at the saloon: over the door (104, 76) it left 30 % of the door; beside it, on (100, 76), its roof "
         "was painted over the front right corner of the hall whenever the saloon's own roof was off, across "
         "Burke's table and whoever stood or lay there (a tap on Lucy West, or on the sheriff's body, picked the "
         "awning). NOT at Craterside's door (planned on (76, 76)): its left post would stand on (80, 77), the "
         "middle of the lane from Craterside to the plaza, which the town keeps free (layout.keep_free, plan.PATHS).")
put("sg_awning_v", (72, 86), group="street",
    remove=[(72, 90, LAMP_POST), (72, 92, LIGHT_SOURCE)],
    note="Against a LEFT wall on column hx: origin = far post (hx + 2, hy), near post on (0, +4). On the FAR side of "
         "the water plant's door (70, 92), posts on (72, 86) and (72, 90): painted before the door, it cannot take a "
         "click meant for it (planned over the door on (72, 90), half the door was covered). Its lamp hangs on the "
         "near post, where the stock lamp post stood: that post and the doorstep light go.")
put("sg_awning_v", (90, 106), group="street",
    note="The clinic's lean-to, on the gate side of its door (88, 102): posts on (90, 106) and (90, 110), where the "
         "town's idler stands. Planned over the door on (90, 100): awning and clinic sign together left 5 pixels of "
         "the door to click. North of the door the intake pipe is in the way, so it stands south of it and covers a "
         "twelfth of the door. The stock lamp post and doorstep light at the door stay (this lamp is too far away).")
put("sg_walllamp_u", [(108, 76), (80, 76), (126, 74), (122, 104), (126, 92), (138, 98)], group="street",
    remove=[(105, 77, LIGHT_SOURCE), (77, 77, LIGHT_SOURCE), (123, 75, LIGHT_SOURCE), (119, 105, LIGHT_SOURCE),
            (123, 93, LIGHT_SOURCE), (135, 99, LIGHT_SOURCE)],
    note="Beside a door in a FRONT wall: door (hx, hy) -> origin (hx + 3, hy + 1). Saloon, Craterside, Billy's, "
         "Brass Lantern kitchen, and the two doors that moved out from under their roofs: the common house "
         "(123, 91) and Lucy West's (135, 97).")
put("sg_walllamp_v", [(90, 88), (90, 118), (128, 118)], group="street",
    remove=[(90, 86, LIGHT_SOURCE), (90, 116, LIGHT_SOURCE), (128, 116, LIGHT_SOURCE)],
    note="Over a door in a LEFT wall: door (hx, hy) -> origin (hx + 2, hy + 2). Church, sheriff, and the player's "
         "house (126, 116): its door is round the corner from the Brass Lantern, and the lamp is what the "
         "sheriff's directions name.")

put("sg_craterside", (64, 78), group="street",
    remove=[(79, 76, 0x02000256), (74, 77, LAMP_POST)],
    note="At Craterside's front right corner, feet on (64, 78), (66, 78), (68, 78); its arrow points left at the "
         "door (77, 75). NOT in the yard in front of the door (hx 70..84): the church's roof stands in front of "
         "that yard and hides everything lower than 2.2 m there. Replaces the GENERAL STORE sign and the lamp post "
         "(the sign has its own lamp; sg_walllamp_u and the awning light the doorstep).")
put("sg_crates", (66, 76), group="street", note="Beside Craterside's front right corner, behind the sign.")
put("sg_clinic", (94, 108), group="street", remove=[(84, 107, 0x0200067D)],
    note="In the lane between the clinic and the track, feet on (94, 108) and (96, 108), facing the gate. Replaces "
         "the stock CLINIC sign. Planned on (90, 106), where the board stood between the camera and the clinic's "
         "door (88, 102) and took every click meant for the door.")
put("sg_sheriff", (90, 114), group="street", remove=[(88, 118, 0x0200058C)],
    note="Beside the sheriff's door (88, 116). Replaces the stock Sheriff sign.")
put("sg_atom", (90, 84), group="street", remove=[(90, 83, 0x0200027C)],
    note="Beside the church door (88, 86), facing the pool. Replaces the stock flag (it carries the script "
         "of the town's decor: move the script to this piece's part).")
put("sg_water", (60, 102), group="street", remove=[(70, 103, 0x0200036D)],
    note="Plant yard, against the water plant's front wall (hy 101). Replaces the WATER sign (scripted: "
         "move its script).")
put("sg_brass_lantern", (126, 108), group="street",
    note="Front left corner of the Brass Lantern stall; board and lantern hang to the screen right over the stall.")
put("sg_noodle_bar", (118, 108), group="street", reach=5, remove=[(117, 108, 0x0200005E)],
    free=[(119, 105), (119, 111)],
    note="The Brass Lantern's counter, on the hexes of the stock Bar (buildings.BAR_BLOCKED) plus three stools on "
         "(117, 109), (119, 109), (121, 109). The stock bar carries a script: put it on this piece's part.")
put("sg_bench", (122, 108), group="street", note="In the Brass Lantern stall under the hanging sign.")
put("sg_bench_plank", (118, 74), group="street", note="In front of Billy Creel's house, right of the door.")
put("sg_laundry", (132, 102), group="street",
    note="In front of Lucy West's house: poles on (132, 102) and (138, 102); the four hexes under it are blocked.")
put("sg_cart", (66, 80), group="street", reach=2, remove=[(66, 80, 0x02000170)],
    note="East nook between Craterside and the water plant. Replaces the stock cart.")
put("sg_tires", [(130, 118), (130, 72)], group="street", reach=1,
    remove=[(130, 118, 0x02000007), (131, 72, 0x02000007)],
    note="Yard corners. Replaces two stock tyre stacks.")
put("sg_barrels", [(68, 110), (70, 118)], group="street", reach=1,
    remove=[(69, 110, 0x02000006), (70, 118, 0x0200018E), (71, 119, 0x02000227)],
    note="Plant yard; inside the wall right of the gate. Replaces stock drums.")

put("sg_string_u5", [(96, 80), (110, 112)], group="street",
    note="Bulb string along a hex row: hooks on the origin and on (+10, 0). Across the saloon's approach; over "
         "the customers' side of the Brass Lantern.")
put("sg_string_u3", (106, 80), group="street", note="Hooks on the origin and (+6, 0): continues the plaza run.")
put("sg_string_v5", (94, 104), group="street",
    note="Bulb string down a hex column: hooks on the origin and (0, +10). Right side of the track, pool to gate.")
put("sg_string_v3", (92, 86), group="street", note="Hooks on the origin and (0, +6): church door towards the clinic.")
put("sg_pole", [(96, 80), (106, 80), (112, 80), (110, 112), (120, 112), (94, 104), (94, 114), (92, 86), (92, 92)],
    group="street", remove=[(95, 78, LAMP_POST), (111, 80, LAMP_POST)],
    note="One under every hook of a string run. Replaces the lamp posts of the plaza.")
put("sg_worklamp", (96, 120), group="street",
    remove=[(96, 120, LAMP_POST), (95, 123, LIGHT_SOURCE)],
    note="Work lamp right of the track inside the gate, on the stock lamp post's hex.")
put("sg_worklamp", (128, 93), how="any", group="street",
    remove=[(128, 93, LAMP_POST)],
    note="Work lamp in the lane to Lucy's, on the stock lamp post's own hex (odd row, hence how='any': the "
         "piece is one hex). It was planned on (128, 94), which is the middle of the lane from the pool to "
         "Lucy's house (plan.PATHS) and has to stay free. (The invisible light it used to replace on (128, 92) "
         "was the doorstep light of Lucy's old door in the right wall; that door is in the front wall now.)")
put("sg_bomb_notice", (94, 100), group="street",
    note="On the bank at the gate side of the pool, facing the gate.")

# ====================================================================================== CRATER
bx, by = BOMB

put("mgb_bomb_states", (bx, by), how="object", group="crater", reach=3,
    remove=[(bx, by - 1, 0x02000301)],
    free=off(BOMB, (-1, 1), (0, 1), (1, 1)),
    note="THE bomb: one object on plan.BOMB with the bomb script, its frame is the quest state (hooks.bomb). "
         "The town's cast creates it (cast/core.py, PID_MGA_BOMB), so there is no stock Bomb to remove; the "
         "Support Base and the BOMB_BLOCKED blockers go: the blockers are the piece's 'blockers' list in the "
         "manifest. BOMB_ACCESS (-1, 1) (0, 1) (1, 1) stays free.")
put("mgb_bomb_shade", (bx, by), group="crater",
    note="Companion on the bomb's hex: the tail's ground shadow and three stones (no part on the bomb's own hex).")
RING = ("Ring round the pool, offsets from plan.BOMB. Where the common house and the Brass Lantern kitchen stand (hx 112) "
        "and in front of the clinic door the buildings themselves close the crater: no pieces there. Gaps: dx -2..2 at "
        "dy 8..10 (track from the gate), dx 4..6 at dy -10 (path from the saloon), the lanes to Lucy's and to the "
        "water plant (dy -2..3).")
for name, spots in (
        ("mgb_rim_v", [(-8, -4)]), ("mgb_rim_h", [(-8, -6), (-4, -8)]), ("mgb_rim_u", [(0, -10)]),
        ("mgb_rim_w", [(8, -10)]), ("mgb_rail_h", [(4, 8)]), ("mgb_rail_u", [(-6, 8)]),
        ("mgb_flagline", [(-2, 10)]), ("mgb_pipe_intake", [(-10, 2)]), ("mgb_pipe_u", [(-14, 2)])):
    put(name, off(BOMB, *spots), group="crater", note=RING)
put("mgb_step_u", off(BOMB, (5, -10), (5, -9), (5, -8), (0, 8), (0, 9), (0, 10)), how="any", group="crater",
    remove=[(100, 105, 0x02000719)],
    note="Plank steps across the two ways into the crater that run up the screen. Replace the stock plank ramp "
         "on the track (100, 105).")
for name, spots in (
        ("mgb_rim_end", [(-8, -5)]),
        ("mgb_sandbags", [(7, -11), (3, 9), (-7, 8)]), ("mgb_sandbags_b", [(4, -11), (8, 6)]),
        ("mgb_step_v", [(11, 0), (12, 0), (13, 0), (-8, 0), (-9, 0), (-10, 0)]),
        ("mgb_boards_v", [(0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7)]),
        ("mgb_shore_a", [(2, -7), (-4, -6)]), ("mgb_shore_b", [(6, -3)]), ("mgb_shore_c", [(-6, 4), (6, 5)]),
        ("mgb_mat", [(4, 5), (2, 5)])):
    put(name, off(BOMB, *spots), how="any", group="crater", note="Crater dressing, offsets from plan.BOMB.")
put("mgb_lectern", off(BOMB, (3, 3)), how="any", group="crater", remove=[(105, 98, 0x0200020E)],
    note="One hex in front of CROMWELL (103, 96): he is painted first and the stand hides his legs. Replaces the "
         "stock Podium (scripted: move its script).")
put("mgb_candles", off(BOMB, (5, 3)), how="any", group="crater", remove=[(106, 99, 0x02000645)],
    note="Replaces the incense burner. A light of 3 hexes, 70 %.")
put("mgb_candles_b", off(BOMB, (1, 3)), how="any", group="crater", remove=[(103, 99, 0x0200056A)],
    note="Replaces the lantern. Not on the bomb's access hexes.")
put("mgb_banner", off(BOMB, (7, 3)), how="any", group="crater", remove=[(107, 97, 0x0200027A)],
    note="Faces the camera, cloth to the screen-right of its mast. Replaces a stock flag (scripted: move its script).")
put("mgb_banner_b", off(BOMB, (-4, 4)), how="any", group="crater", remove=[(104, 100, 0x0200027B)],
    note="Cloth to the screen-left of its mast. Replaces the other stock flag (scripted: move its script).")
put("mgb_sign", off(BOMB, (4, 10)), how="any", group="crater", remove=[(95, 101, 0x020004A3)],
    note="Beside the track where it enters the crater, outside the railing. Replaces the stock radiation sign "
         "(scripted: move its script).")

# ==================================================================================== VERDICTS
U, A, C = "upgrade", "acceptable", "cut"
for _name, _value, _why, _flaws in (
    # ---- gate
    ("mg_gate", U, "The landmark the entrance lacked: wing lintel, engine, plated bays, hazard posts; sits in the stock "
     "fence and next to the stock car-wreck wall without looking pasted in after the regrade.",
     ["the wing reads by its taper, red tip and engine more than by its top surface",
      "the engine's fan face is nearly black", "a critter under the engine pod can show a few px of hair over it"]),
    ("mg_gate_sign", U, "MEGATON in seven mismatched letters, floodlit, readable at 1:1 by day and at night; the gate's lamp.",
     ["in a 1040x480 window it is above the top of the screen from the arrival hex (101, 136) and comes into view "
      "three rows from the gate: the stencil on the leaves covers the arrival"]),
    ("mg_gate_door", U, "Five-frame sliding door with MEGA | TON stencilled across the leaves, worn by the town's own door object.", []),
    ("mg_gate_shut", A, "Fallback for a town without the door FRM.", []),
    ("mg_gate_ajar", A, "Fallback for a town without the door FRM.", []),
    ("mg_gate_open", A, "Fallback for a town without the door FRM.", []),
    ("mg_wire_gate", A, "Cables from the sign to the first pole.", ["1-2 px lines"]),
    ("mg_wall_bus", U, "A school bus as eight hexes of wall; reads at a glance.", ["at night the per-hex light steps show on its side"]),
    ("mg_wall_boxes", U, "Container stack, 5.2 m: shows above the stock car heap in front of it.", []),
    ("mg_wall_hull", A, "Fuselage barrel beside the gate.", ["cleaner than the stock wrecks around it",
                                                          "its lower half is behind the car heap"]),
    ("mg_wall_cars", A, "Car-door wall.", ["reads as coloured panels with window holes more than as car doors"]),
    ("mg_nest", A, "Watch platform behind the bus: the one tall thing inside the wall at the gate.",
     ["the deck interior is dark; nobody and no gun up there"]),
    ("mg_pole", U, "Utility pole with transformer can and lamp: replaces a generic lamp post, carries the cables.", []),
    ("mg_wire_v", A, "Cables between two poles down a column.", ["1-2 px lines"]),
    ("mg_wire_u", A, "Cables between two poles along a row.", ["1-2 px lines"]),
    # ---- street
    ("sg_moriarty", U, "Billboard over the saloon roof, cream letters and red neon.",
     ["only on screen from the plaza in a 960 px high window; in a 380 px window it shows from behind the saloon or "
      "from inside it: the stock BAR neon stays as the door sign"]),
    ("sg_craterside", U, "Brushed board with junk nailed round it; replaces the stock GENERAL STORE sign.", []),
    ("sg_brass_lantern", U, "Hanging board and a lit brass lantern.", ["its lettering is 7 px: an icon at phone size, not text"]),
    ("sg_clinic", U, "White cross on a green panel: readable from the gate.", ["the MEGATON line is 5 px tall"]),
    ("sg_atom", U, "Welded atom with a green self-lit nucleus.", []),
    ("sg_sheriff", U, "Star on a shield over a name board.", []),
    ("sg_water", A, "Boiler-shell tank with a stencil.", ["plain shell"]),
    ("sg_bomb_notice", U, "DAYS WITHOUT / A DETONATION / ALL OF THEM on the board beside the bomb.", []),
    ("sg_string_u3", U, "Bulb string: the warm points of light the street lacked.", ["bulbs are 2 px"]),
    ("sg_string_u5", U, "Bulb string.", ["bulbs are 2 px"]),
    ("sg_string_v3", U, "Bulb string.", ["bulbs are 2 px"]),
    ("sg_string_v5", U, "Bulb string.", ["bulbs are 2 px"]),
    ("sg_pole", A, "String pole on a tyre foot.", []),
    ("sg_worklamp", A, "Work lamp on a post with a warm pool.", ["generic"]),
    ("sg_fire_barrel", C, "The stock Burning Metal Barrel has a frame-animated flame; this one has static cones that only "
     "change colour. Keep the stock barrels.", ["flames are crude cones"]),
    ("sg_walllamp_u", A, "Lamp beside a door in a front wall.", ["small; can overlap the shoulder of somebody right under it"]),
    ("sg_walllamp_v", A, "Lamp over a door in a left wall.", ["small; can overlap the shoulder of somebody right under it"]),
    ("sg_awning_u", U, "Junk awning over a door in a front wall.", ["the same picture three times in town: tyres in the same place"]),
    ("sg_awning_v", U, "Lean-to awning over a door in a left wall (two parts since the review).", []),
    ("sg_tires", A, "Tyre pile.", ["darker than the stock tyre stack; no better than it, only different"]),
    ("sg_crates", A, "Crates, sacks, a jerry can.", []),
    ("sg_barrels", A, "Drums on a pallet.", ["more saturated than stock drums"]),
    ("sg_noodle_bar", U, "The Brass Lantern's counter: wok, stove pipe, shelves, stools.", []),
    ("sg_bench", A, "Car-seat bench.", ["reads as a red block at 1:1"]),
    ("sg_bench_plank", A, "Plank bench.", []),
    ("sg_cart", A, "Handcart.", ["no better than the stock cart it replaces, only more junk on it"]),
    ("sg_laundry", U, "Washing line: the first sign in town that people live here.", []),
    ("sg_roof_stack", A, "Stove pipes on the roofline.", []),
    ("sg_roof_tank", U, "Water tank on a lattice tower over the roofline.", []),
    ("sg_roof_antenna", U, "Mast with dish and a blinking red beacon.", []),
    ("sg_roof_patch", A, "Scrap hoarding on the roofline.", []),
    ("sg_roof_vent", A, "Animated extractor fan on the roofline.", []),
    # ---- crater
    ("mgb_bomb_states", U, "The centrepiece: bigger and far more readable than the stock bomb, MEGATON on its side, three "
     "quest states in one sprite.", ["the tail unit is the weakest part", "one sprite: the hex at its nose is blocked so nobody can vanish behind it"]),
    ("mgb_bomb", A, "Dormant state only.", []),
    ("mgb_bomb_rigged", A, "Rigged state only.", []),
    ("mgb_bomb_safe", A, "Disarmed state only.", []),
    ("mgb_bomb_shade", A, "The tail's ground shadow and three stones.", []),
    ("mgb_lectern", U, "Lectern with the atom on its cloth, in place of the stock podium.", []),
    ("mgb_candles", A, "Candles.", ["the yellow pool hardly shows on the green floor"]),
    ("mgb_candles_b", A, "Candles on a crate.", ["as mgb_candles"]),
    ("mgb_banner", U, "Red atom banner on a mast.", []),
    ("mgb_banner_b", A, "Yellow atom banner.", []),
    ("mgb_flagline", U, "Prayer flags over the way into the crater.", []),
    ("mgb_mat", A, "Prayer mat.", []),
    ("mgb_rim_u", A, "Retaining wall of scrap and sandbags.", ["reads as a low scrap wall; the higher ground behind it is only hinted"]),
    ("mgb_rim_u2", A, "Second look of mgb_rim_u.", []),
    ("mgb_rim_h", A, "Retaining wall, level run.", []),
    ("mgb_rim_v", A, "Retaining wall, down a column.", []),
    ("mgb_rim_w", A, "Retaining wall, coming forward.", []),
    ("mgb_rim_end", A, "End post with a tyre.", []),
    ("mgb_sandbags", A, "Sandbags.", []),
    ("mgb_sandbags_b", A, "Sandbags, taller.", []),
    ("mgb_rail_u", U, "Pipe railing along the lip of the crater.", []),
    ("mgb_rail_h", U, "Pipe railing, level run.", []),
    ("mgb_rail_v", A, "Pipe railing down a column.", []),
    ("mgb_step_u", A, "Plank steps.", ["plain planks"]),
    ("mgb_step_v", A, "Plank steps.", ["plain planks"]),
    ("mgb_boards_u", A, "Duckboards.", ["dark"]),
    ("mgb_boards_v", A, "Duckboards.", ["dark"]),
    ("mgb_shore_a", A, "Shore debris: tyre in the mud.", []),
    ("mgb_shore_b", A, "Shore debris: drum.", []),
    ("mgb_shore_c", A, "Shore debris.", ["the rib-cage is a few pixels"]),
    ("mgb_pipe_u", A, "The water plant's intake pipe.", ["the clinic's roof hides most of a run behind the clinic"]),
    ("mgb_pipe_intake", A, "Pipe end with valve wheel in the pool.", []),
    ("mgb_sign", U, "DANGER trefoil sign; toned down from the first build.", []),
    # ---- pipeline demos
    ("mgt_crate", C, "Pipeline demo. No better than the stock crates.", []),
    ("mgt_wall_u", C, "Pipeline demo. The stock corrugated fence is better drawn.", []),
    ("mgt_stall", C, "Pipeline demo. Superseded by sg_awning_u / sg_noodle_bar.", []),
    ("mgt_lamp", C, "Pipeline demo. Superseded by mg_pole / sg_worklamp.", []),
    ("mgt_sign", C, "Pipeline demo. Superseded by mg_gate_sign.", []),
    ("mgt_fence", C, "Pipeline demo. Stock chain-link walls exist.", []),
    ("mgt_junk", C, "Pipeline demo. Superseded by sg_barrels / sg_tires; its front hex sorts wrongly.", []),
    ("mgt_hull", C, "Pipeline demo. Superseded by mg_wall_hull.", []),
):
    verdict(_name, _value, _why, _flaws)

# ==================================================================================== OPTIONAL
# Pieces that are fit for use but stand nowhere in the reviewed scene: {piece: when to use it}.
OPTIONAL = {
    "mg_gate_door": "Not placed as an object: its art slot holds the five-frame door FRM that the town's own gate "
                    "door object wears (hooks.gate_door).",
    "mg_gate_shut": "Fallback only, if the town does not use the door FRM: the leaves as plain scenery on the gate "
                    "origin; a script would show one of shut / ajar / open.",
    "mg_gate_ajar": "See mg_gate_shut.",
    "mg_gate_open": "See mg_gate_shut.",
    "mg_wire_u": "Cables along a hex row: right pole (mg_pole) on the origin, left pole on (+12, 0). Not in the reviewed "
                 "scene: its only run ended on a pole among the Brass Lantern's chairs.",
    "mgb_rail_v": "Railing down a hex column, hexes (0, 0) (0, 1). The crater's flanks are closed by buildings in this "
                  "town, so the scene needs none.",
    "mgb_rim_u2": "Second look of mgb_rim_u for the same run; alternate them on a longer back wall.",
    "mgb_boards_u": "Duckboards along a hex row (two hexes); the scene only has a walkway down a column (mgb_boards_v).",
    "mgb_bomb": "Single-state alternative to mgb_bomb_states (dormant). Same footprint and placement.",
    "mgb_bomb_rigged": "Single-state alternative (charge fitted).",
    "mgb_bomb_safe": "Single-state alternative (disarmed).",
}


# ======================================================================================= HOOKS
def hooks(manifest):
    """Script and object hooks the town needs, with the ids filled in from the manifest."""
    pieces = manifest["pieces"]

    def pid(name, layer="main"):
        return next((p["pid"] for p in pieces.get(name, {}).get("parts", ()) if p["layer"] == layer), None)

    door = pieces.get("mg_gate_door", {}).get("parts", [{}])[0]
    door_frames = int(pieces.get("mg_gate_door", {}).get("frames", 1))      # gate_door.py records the real count
    door_fps = int(pieces.get("mg_gate_door", {}).get("fps", 8))
    result = {
        "gate_door": {
            "what": "The gate opens and closes with the town's existing door object: keep the stock proto "
                    f"0x{STOCK_GATE_DOOR:08X} on plan.GATE with its MULTIHEX flag and its script, and give the object "
                    "this art. Frame 0 is shut, the last frame open; the engine plays the frames forwards when the "
                    "door is used and backwards when it closes. Nothing else changes.",
            "object": {"hex": list(GATE), "proto": f"0x{STOCK_GATE_DOOR:08X}"},
            "set": {"fid": door.get("fid"), "frm": door.get("frm")},
            "frames": door_frames, "fps": door_fps,
            "states": {"shut": 0, "open": door_frames - 1},
            "built_by": "pieces/gate/gate_door.py (run by build.py after every build of the gate pieces)",
        },
        "bomb": {
            "what": "mgb_bomb_states is ONE sprite whose frames are the quest states. The cast creates its part's PID "
                    "on plan.BOMB with the bomb script (never through Placer: that would attach 'animfrvr' and spin "
                    "the states), then adds the invisible blockers of placements[mgb_bomb_states].blockers.",
            "pid": pid("mgb_bomb_states"),
            "frames": {"dormant": 0, "rigged": 1, "disarmed": 2},
            "script": "set_frame(self_obj, n) (fo2.h: anim(self_obj, ANIMATE_SET_FRAME, n)) in map_enter_p_proc from "
                      "GVAR_MG_BOMB and whenever the state changes. Object, script and local variables stay. "
                      "Proven on the review stage by stage/town/mgbstate.ssl.",
            "light": "the sprite is a lamp (5 hexes, 85 %); frame 1 has a red lamp on the animated 'alarm' palette "
                     "colour, which blinks by itself and stays bright at night",
        },
        "lamps": {
            "what": "Parts whose proto carries a light: placing the object is enough (f2lib sets the object's light "
                    "from the proto). White light only; the warm pool is the piece's halo part.",
            "pieces": {name: {"pid": p["pid"], "hex": p["hex"], "distance": p["light"][0],
                              "intensity_percent": round(p["light"][1] * 100 / 65536)}
                       for name, piece in pieces.items() for p in piece["parts"] if p["light"] != [0, 0]},
        },
        "animated": {
            "what": "Frame-animated parts only move when a script starts them: attach the stock script 'animfrvr' "
                    "(scripts.lst entry 511, animate for ever). Placer.place does it. NOT for mgb_bomb_states.",
            "pieces": {name: sorted({p["pid"] for p in piece["parts"] if p["script"]})
                       for name, piece in pieces.items()
                       if any(p["script"] for p in piece["parts"]) and name != "mgb_bomb_states"},
        },
        "palette_animation": {
            "what": "Pixels on the engine's animated palette ranges: they flicker / blink by themselves and are not "
                    "darkened at night. No script needed.",
            "pieces": {name: sorted(piece["report"]["fx_pixels"]) for name, piece in pieces.items()
                       if piece["report"].get("fx_pixels")},
        },
    }
    return result



# ===================================================================== check + placement.json
ORDER ={"shadow": 0, "halo": 1, "main": 2, "glow": 3}
NO_BLOCK = 0x10
SPOT_OBJECTS = {"BOMB", "GATE", "TERMINAL", "CABINET", "STRONGBOX", "NOVA_BED", "HOUSE_BED", "COMMON_BED", "ARMORY_LOCKER",
                "LEAK1", "LEAK2", "LEAK3", "OFFICE_DOOR", "ARMORY_DOOR", "HOUSE_DOOR"}      # spots that ARE an object


def load_town():
    """The town as mod/megaton/layout builds it today WITHOUT the art (the stock dressing the plan
    replaces is all there), with mod/megaton/out as the overlay for compiled scripts and protos."""
    town_mod = os.path.join(ROOT, "mod", "megaton")
    if town_mod not in sys.path:
        sys.path.insert(0, town_mod)
    from f2lib import GameFiles
    import layout
    gf = GameFiles(overlay=[os.path.join(town_mod, "out"), os.path.join(HERE, "out")])
    town, _ = layout.build(gf, art=False, with_cast=False, log=lambda *a: None)
    for obj in list(town.objects_at(BOMB[1] * 200 + BOMB[0])):      # the cast's bomb is the art's: no stock one stays
        if obj.pid == 0x02000300:
            town.remove_object(obj)
    return gf, town


def town_spots():
    town_mod = os.path.join(ROOT, "mod", "megaton")
    if town_mod not in sys.path:
        sys.path.insert(0, town_mod)
    from layout import spots
    return {name: (hx, hy) for name, (hx, hy, _) in spots.SPOTS.items()}


def blocks(gf, obj):
    """Does a stock object of the town keep a critter off its hex?"""
    from f2lib import ids
    if obj.obj_type == ids.OBJ_TYPE_WALL or obj.obj_type == ids.OBJ_TYPE_CRITTER:
        return True
    if obj.obj_type in (ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_ITEM):
        return not obj.flags & NO_BLOCK
    return False


def resolve(manifest=None, town=None, gf=None, spots=None):
    """-> (original-piece document, [problems]).

    layout.art passes the original manifest subset, then validates and applies density.
    The CLI below writes the combined final document when density is installed.

    town   the map to check against: a MapFile holding the town WITHOUT the art (layout/art.py passes
           the map it is building, before the cast stands on it); default: built here from layout
    gf     the GameFiles that map was built with
    spots  {name: (hx, hy)}; default layout/spots.py
    """
    from f2lib import geometry as g, ids
    if manifest is None:
        with open(os.path.join(HERE, "manifest.json")) as f:
            manifest = json.load(f)
    if town is None:
        gf, town = load_town()
    if spots is None:
        spots = town_spots()
    pieces = manifest["pieces"]
    problems = []
    removed = {}                      # (hx, hy, pid) -> entry that removes it
    removed_ids = set()
    placements = []
    for entry in ENTRIES:
        name = entry["piece"]
        if name not in pieces:
            problems.append(f"{name}: not in manifest.json")
            continue
        piece = pieces[name]
        if VERDICTS.get(name, {}).get("verdict") == "cut":
            problems.append(f"{name}: placed although its verdict is 'cut'")
        removal = []
        for hx, hy, pid in entry["remove"]:
            found = [obj for obj in town.objects_at(g.tile_at(hx, hy))
                     if (pid is None and obj.obj_type == ids.OBJ_TYPE_WALL) or obj.pid == pid]
            found = [obj for obj in found if id(obj) not in removed_ids]
            if not found:
                what = "a wall" if pid is None else f"0x{pid:08X}"
                problems.append(f"{name}: the town has no {what} on ({hx}, {hy}) to remove")
                continue
            for obj in found[:1]:
                removed_ids.add(id(obj))
                removal.append({"hex": [hx, hy], "tile": obj.tile, "pid": f"0x{obj.pid:08X}",
                                "scripted": obj.sid != -1})
                if entry["reach"]:
                    centre = g.tile_at(hx, hy)
                    for other in town.all_objects(0):
                        if other.pid == SECRET_BLOCK and id(other) not in removed_ids \
                                and g.distance(other.tile, centre) <= entry["reach"]:
                            removed_ids.add(id(other))
                            ox, oy = g.tile_xy(other.tile)
                            removal.append({"hex": [ox, oy], "tile": other.tile, "pid": f"0x{SECRET_BLOCK:08X}",
                                            "scripted": False})
        for index, (hx, hy) in enumerate(entry["origins"]):
            how = entry["how"]
            if how == "placer" and (hx & 1 or hy & 1):
                problems.append(f"{name} at ({hx}, {hy}): a placer origin needs even hx and even hy")
            if how == "any" and (piece["blockers"] or any(part["hex"] != [0, 0] for part in piece["parts"])):
                problems.append(f"{name}: how='any' needs a piece with every part on its own hex and no extra blockers")
            parts = sorted(piece["parts"], key=lambda p: (ORDER[p["layer"]], p["hex"][1] * 200 + p["hex"][0]))
            placements.append({
                "piece": name, "group": entry["group"], "how": how, "origin": [hx, hy], "tile": g.tile_at(hx, hy),
                "blocks": [[hx + dx, hy + dy] for dx, dy in piece["footprint"]],
                "parts": [{"layer": p["layer"], "hex": [hx + p["hex"][0], hy + p["hex"][1]], "pid": p["pid"],
                           "script": p["script"], "light": p["light"] if p["light"] != [0, 0] else None} for p in parts],
                "blockers": [[hx + dx, hy + dy] for dx, dy in piece["blockers"]],
                "remove": removal if index == 0 else [],
                "free": [list(h) for h in entry["free"]] if index == 0 else [],
                "note": entry["note"],
            })

    # ---- what the placements collide with
    town_block = {}
    for obj in town.all_objects(0):
        if id(obj) in removed_ids or not blocks(gf, obj):
            continue
        town_block.setdefault(g.tile_xy(obj.tile), []).append(obj)
    claimed = {}
    for place in placements:
        label = f"{place['piece']} at ({place['origin'][0]}, {place['origin'][1]})"
        for hx, hy in place["blocks"]:
            for obj in town_block.get((hx, hy), ()):
                if obj.pid in (SECRET_BLOCK, WALL_BLOCK):
                    continue
                problems.append(f"{label}: its hex ({hx}, {hy}) holds town object 0x{obj.pid:08X}")
            for spot, where in spots.items():
                if where == (hx, hy) and spot not in SPOT_OBJECTS:
                    problems.append(f"{label}: blocks the town spot {spot} on ({hx}, {hy})")
            if (hx, hy) in claimed and claimed[(hx, hy)] != label:
                problems.append(f"{label}: hex ({hx}, {hy}) is also blocked by {claimed[(hx, hy)]}")
            claimed[(hx, hy)] = label
    for place in placements:
        for hx, hy in place["free"]:
            if (hx, hy) in claimed:
                problems.append(f"{place['piece']}: hex ({hx}, {hy}) must stay free but {claimed[(hx, hy)]} blocks it")

    # ---- can everybody still get everywhere? (flood fill from the entry, before and after)
    def reachable(blocked):
        start = g.tile_at(*PLAN["ENTRY"])
        seen, todo = {start}, [start]
        while todo:
            tile = todo.pop()
            for nxt in g.ring(tile, 1):
                if nxt in seen or nxt < 0 or g.tile_xy(nxt) in blocked:
                    continue
                seen.add(nxt)
                todo.append(nxt)
        return seen

    doors = {g.tile_xy(obj.tile) for obj in town.all_objects(0)
             if obj.obj_type == ids.OBJ_TYPE_SCENERY and gf.protos.get(obj.pid).subtype_name == "door"}
    before_block = {g.tile_xy(obj.tile) for obj in town.all_objects(0) if blocks(gf, obj)
                    and obj.obj_type != ids.OBJ_TYPE_CRITTER} - doors
    gate_passage = {(GATE[0] + dx, GATE[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    after_block = ({hex_ for hex_, objs in town_block.items() if any(o.obj_type != ids.OBJ_TYPE_CRITTER for o in objs)}
                   | set(claimed)) - doors
    before, after = reachable(before_block - gate_passage), reachable(after_block - gate_passage)
    for spot, where in sorted(spots.items()):
        tile = g.tile_at(*where)
        near_before = any(t in before for t in [tile] + list(g.ring(tile, 1)))
        near_after = any(t in after for t in [tile] + list(g.ring(tile, 1)))
        if near_before and not near_after:
            problems.append(f"the town spot {spot} on {where} can no longer be reached from the entry")
    for door in sorted(doors):
        tile = g.tile_at(*door)
        open_before = sum(1 for t in g.ring(tile, 1) if t in before)
        open_after = sum(1 for t in g.ring(tile, 1) if t in after)
        if open_after < open_before:
            lost = [g.tile_xy(t) for t in g.ring(tile, 1) if t in before and t not in after]
            problems.append(f"the doorway on {door} loses free neighbour hex(es) {lost}")

    # ---- verdicts: every piece of the manifest has one; pieces in use are placed, cut ones are not
    used = {}
    for place in placements:
        used[place["piece"]] = used.get(place["piece"], 0) + 1
    if int(pieces.get("mg_gate_door", {}).get("frames", 0)) < 2:
        problems.append("mg_gate_door holds one frame: the door FRM was not built (run build.py data)")
    piece_table = {}
    for name, piece in pieces.items():
        v = VERDICTS.get(name)
        if v is None:
            problems.append(f"{name}: no verdict")
            v = {"verdict": "unreviewed", "why": "", "flaws": []}
        if v["verdict"] != "cut" and name not in used and name not in OPTIONAL:
            problems.append(f"{name}: verdict {v['verdict']!r} but not placed anywhere (list it in OPTIONAL if that is meant)")
        piece_table[name] = {
            "verdict": v["verdict"], "why": v["why"], "flaws": v["flaws"], "placed": used.get(name, 0),
            "optional": OPTIONAL.get(name), "kind": piece["kind"], "script": piece["script"],
            "pids": sorted({part["pid"] for part in piece["parts"]}),
            "lamp": next(({"hex": p["hex"], "distance": p["light"][0], "intensity_percent": round(p["light"][1] * 100 / 65536)}
                          for p in piece["parts"] if p["light"] != [0, 0]), None),
            "animated": any(p["script"] for p in piece["parts"]),
            "palette_animation": sorted(piece["report"].get("fx_pixels", {})),
            "halo": any(p["layer"] == "halo" for p in piece["parts"]),
        }
    document = {
        "about": "Megaton art mod: where every piece goes in the town, what it replaces and which script hooks it needs. "
                 "Generated by mod/megaton-art/placement.py from its own tables, manifest.json and the town as "
                 "mod/megaton/layout builds it; edit placement.py, not this file. The town build resolves placement.py "
                 "itself (mod/megaton/layout/art.py); the review stage map is built from this file.",
        "plan": {key: (list(value) if isinstance(value, tuple) else value) for key, value in PLAN.items()},
        "rules": RULES,
        "groups": GROUPS,
        "hooks": hooks(manifest),
        "pieces": piece_table,
        "placements": placements,
    }
    return document, problems


def sync_verdicts(manifest):
    """Update verdict metadata from the original plan and reviewed density document.

    Used by art build.finish(); no files, IDs, geometry, or tiles are changed here.
    """
    from collections import Counter

    table = {name: dict(row) for name, row in VERDICTS.items()}
    path = os.path.join(HERE, "placement-v2.json")
    document = None
    if os.path.exists(path):
        with open(path) as stream:
            document = json.load(stream)
        for name, row in document["pieces"].items():
            table[name] = {"verdict": row["verdict"], "why": row["why"], "flaws": []}
        usage = Counter(e["piece"] for e in ENTRIES for _ in e["origins"])
        for row in document["removed"]:
            if row["kind"] == "piece":
                usage[row["piece"]] -= 1
        usage.update(p["piece"] for p in document["placements"])
        for row in document["removed"]:
            if row["kind"] == "piece" and not usage[row["piece"]]:
                table[row["piece"]] = {"verdict": "cut", "why": "Removed by the reviewed density plan; IDs remain reserved.", "flaws": []}
    missing = set(manifest["pieces"]) - set(table)
    if missing:
        raise ValueError("missing reviewed piece verdicts: " + ", ".join(sorted(missing)))
    for name, entry in manifest["pieces"].items():
        value = table[name]["verdict"]
        if value not in ("upgrade", "acceptable", "cut"):
            raise ValueError(f"{name}: invalid reviewed verdict {value!r}")
        entry["verdict"] = value
    if document is not None:
        for name, entry in manifest.get("tiles", {}).get("sheets", {}).items():
            value = document["sheets"].get(name, {}).get("verdict")
            if value not in ("upgrade", "acceptable", "cut"):
                raise ValueError(f"{name}: missing reviewed sheet verdict")
            entry["verdict"] = value


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    # The executable exports the complete town plan; resolve() remains the base
    # resolver used by layout.art before its reviewed density operations.
    town_mod = os.path.join(ROOT, "mod", "megaton")
    if town_mod not in sys.path:
        sys.path.insert(0, town_mod)
    from layout import density
    if density.load() is None:
        document, problems = resolve()
    else:
        from f2lib import GameFiles
        import layout
        # New art lists must win over an older town staging tree during a merge.
        gf = GameFiles(overlay=[os.path.join(HERE, "out"), os.path.join(town_mod, "out")])
        _, info = layout.build(gf, art=True, with_cast=False, log=lambda *a: None)
        document, problems = info["art"]["document"], []
    for line in problems:
        print(f"[placement] PROBLEM {line}")
    counts = {}
    for piece in document["pieces"].values():
        counts[piece["verdict"]] = counts.get(piece["verdict"], 0) + 1
    print(f"[placement] {len(document['placements'])} placements of {sum(1 for p in document['pieces'].values() if p['placed'])} "
          f"pieces; verdicts {counts}; {sum(len(p['remove']) for p in document['placements'])} stock objects removed; "
          f"{len(problems)} problem(s)")
    if not args.check:
        with open(OUT, "w") as f:
            json.dump(document, f, indent=1)
            f.write("\n")
        print(f"[placement] wrote {os.path.relpath(OUT, ROOT)}")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
