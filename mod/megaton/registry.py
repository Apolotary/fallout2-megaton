# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Every number the Megaton mod claims in Fallout 2's global tables.

Scripts, maps and data files all refer to these ids; keeping them in one place
is what stops two parts of the mod from picking the same slot. The values are
chosen so the mod works on an unmodified fallout2-ce (and vanilla saves stay
loadable): nothing vanilla is renumbered, only free or cut-content slots are
used. Design reference: research/09-megaton-design-brief.md section 5.1.
"""

# --- maps.txt -----------------------------------------------------------------
# Vanilla ends at [Map 150]; the automap tables allow indices up to 159.
MAPS = [
    # (index, lookup_name, file stem (<= 8 chars), music, map.msg elevation names)
    (151, "Megaton", "megaton", "12junktn", ["Megaton", "Megaton Crater", "Megaton"]),
]

# --- city.txt -----------------------------------------------------------------
# The engine insists on exactly 49 areas, so a new town has to take over one of
# the three cut-content areas. Area 18 ("Primitive Tribe") is never referenced
# by a vanilla script.
AREA = 18
AREA_NAME = "Megaton"
# Top-left of the world-map circle in window space. Inside the 3x3 block of
# sub-tiles that is revealed around Arroyo at the start of the game, so the
# town can be seen on the very first visit to the world map.
AREA_WORLD_POS = (225, 169)
AREA_SIZE = "Medium"
# Where leaving the map puts the party on the world map (circle centre).
WORLD_MAP_EXIT_POS = (215, 160)

MAP_MSG_AREA_NAME_ID = 1500 + AREA  # map.msg id used for the town's name

# --- art/intrface/intrface.lst ------------------------------------------------------
# One picture is appended to the interface art list (vanilla has 469 lines, so it gets
# index 469): the "MEGATON" plate of the world map's destination list, which city.txt
# names by its index (townmap_label_art_idx). worldmap_art.py draws it. Append only.
INTERFACE_ART = [
    # (file name (8.3), comment)
    ("wm_megat.frm", "Worldmap Megaton TownMarker (Megaton mod)"),
]

# --- global variables -----------------------------------------------------------
# GVAR_RESERVED_VAR1..59 (634..692) are unused by vanilla scripts and tables.
# Appending new GVARs instead would break every existing save.
GVARS = {
    # 0 dormant, 1 disarmed, 2 rigged (pulse charge fitted), 3 detonated.
    "GVAR_MG_BOMB": 634,
    # Pip-Boy "Disarm the bomb": 0 none, 1 active, 2 disarmed (unreported), 3 rewarded.
    "GVAR_MG_Q_SIMMS": 635,
    # Pip-Boy "Rig the bomb": 0 none, 1 heard the pitch, 2 accepted (holding the
    # charge), 3 charge planted, 4 detonated and paid.
    "GVAR_MG_Q_BURKE": 636,
    # Burke: 0 in the saloon, 1 left town alive, 2 shot Simms and fled, 3 dead,
    # 4 waiting at the rendezvous outside, 5 gone after the blast.
    "GVAR_MG_BURKE": 637,
    # Simms: 0 alive, 1 told about Burke (scene pending), 2 survived the scene, 3 dead.
    "GVAR_MG_SIMMS": 638,
    # Pip-Boy "Fix Walter's pipes": 0 none, 1 accepted, 2 all fixed, 3 paid.
    "GVAR_MG_Q_WATER": 639,
    # Pip-Boy "Moriarty's information": 0 none, 1 price quoted, 2 on the Silver job, 3 obtained.
    "GVAR_MG_Q_INFO": 640,
    # Pip-Boy "Lucy West's letter": 0 none, 1 carrying it, 2 posted, 3 Lucy told.
    "GVAR_MG_Q_LETTER": 641,
    # Bit field, see FLAGS below.
    "GVAR_MG_FLAGS": 642,
    # Game day on which Burke's hired guns become due.
    "GVAR_MG_HIT_DAY": 643,
    # Set once the starting kit has been handed out (new game begun at the gate).
    "GVAR_MG_KIT_GIVEN": 644,
    # Everyone in town is hostile (the player attacked townsfolk or announced the plan).
    "GVAR_MG_TOWN_HOSTILE": 645,
    # Number of Walter's leaks fixed so far (0..3) and which (bits 1, 2, 4 in LEAK_BITS).
    "GVAR_MG_LEAK_BITS": 646,
    # Day the merchants were last restocked.
    "GVAR_MG_RESTOCK_DAY": 647,
    # Step of the saloon confrontation scene (0 idle).
    "GVAR_MG_SCENE": 648,
    # Free slots, handed out in blocks so parallel work cannot collide:
    # 649-656 main quest, 657-662 merchants, 663-670 side quests, 671-676 flavour,
    # 677-692 unassigned. Add a named entry here when you take one.
    # Merchants: Craterside Supply theft alarm. 0 calm, 1 Moira caught the player stealing (her guard
    # has yet to say so), 2 the guard gave his one warning, 3 caught again: the guard opens fire.
    "GVAR_MG_SHOP_ALARM": 657,
    # Merchants: bit field of shopkeepers who are dead. 1 Moira, 2 her mercenary, 4 Gob, 8 Doc Church,
    # 16 Jenny Stahl, 32 the caravan trader, 64 Nova. Each one's script sets its bit in destroy_p_proc.
    "GVAR_MG_MERCH_DEAD": 658,
    # Flavour: pulse Cromwell raises with every sermon line; the congregation answers it (0..999).
    "GVAR_MG_SERMON": 671,
    # Flavour: armory door in the Sheriff's house. 0 locked, 1 the player was caught at the lock
    # once (warned), 2 picked open. Caught a second time: GVAR_MG_TOWN_HOSTILE (mgarmory.ssl).
    "GVAR_MG_ARMORY": 672,
    # Flavour: how many times the player has given Micky something clean to drink (mgmicky.ssl).
    "GVAR_MG_MICKY": 673,
    # Side quests: Moriarty's errand to collect from Silver. 0 never offered, 1 open, 2 closed without
    # the money (he was told she is gone or dead; the price of his information stands). mgmoriar.ssl.
    "GVAR_MG_SILVER_JOB": 663,
    # Side quests: the deal Silver offers. 0 none, 1 the player took her $100 to say she is gone,
    # 2 the player agreed to say so for nothing (mgsilvr.ssl sets it).
    "GVAR_MG_SILVER_DEAL": 664,
    # Side quests: 1 once Walter is dead; mgleak.ssl then closes the pipe job itself (mgwalter.ssl sets it).
    "GVAR_MG_WALTER_DEAD": 665,
    # Side quests: 1 once Moriarty is dead; Silver then owes nobody (mgmoriar.ssl sets it).
    "GVAR_MG_MORIARTY_DEAD": 666,
    # Main quest: game tick at which the current step of the saloon scene began (mgsimms.ssl drives it).
    "GVAR_MG_SCENE_TICK": 649,
    # Main quest: day + 1 on which the town turned hostile; megaton.ssl stamps it and forgives after a week away (0 not hostile).
    "GVAR_MG_HOSTILE_DAY": 650,
    # Main quest: how many times the town has forgiven the player (megaton.ssl); NPCs compare it with a local copy to drop personal grudges.
    "GVAR_MG_AMNESTY": 651,
    # Main quest: Harden Simms. 0 fine, 1 dead, 2 knows the player killed his father (he will never pay the reward).
    "GVAR_MG_HARDEN": 652,
    # Main quest: game tick at which the town's present alarm began: when it turned hostile, and again each time
    # a hostile town sees the player walk in. For MG_GRACE_TICKS after it the town shouts instead of shooting (megaton.h).
    "GVAR_MG_HOSTILE_TICK": 653,
    # Main quest: day + 1 on which somebody in town last took a PERSONAL grudge against the player (mg_make_hostile:
    # a second theft, the shop alarm, an insult), 0 none. megaton.ssl lets such grudges lapse a week later, as it
    # does the town's: without it a sheriff robbed twice shot on sight for the rest of the game.
    "GVAR_MG_GRUDGE_DAY": 654,
}

# Bits of GVAR_MG_FLAGS.
FLAGS = {
    "MG_F_WELD_GREETED": 1,
    "MG_F_GOB_FRIEND": 2,
    "MG_F_GOB_INSULTED": 4,
    "MG_F_MOIRA_NOTES": 8,
    "MG_F_HOUSE_OWNED": 16,
    "MG_F_KNOWS_TERMINAL": 32,
    "MG_F_HAS_PASSWORD": 64,
    "MG_F_PRICE_300": 128,
    "MG_F_SIMMS_BONUS": 256,
    "MG_F_SIMMS_PRO_BONO": 512,
    "MG_F_BURKE_BONUS": 1024,
    "MG_F_BURKE_ADVANCE": 2048,
    "MG_F_SIMMS_WARNED": 4096,
    "MG_F_HIT_SQUAD_DONE": 8192,
    "MG_F_SILVER_PAID": 16384,
    "MG_F_SILVER_DEAD": 32768,
    "MG_F_HAS_CHARGE": 65536,
    "MG_F_HAS_LETTER": 131072,
    "MG_F_SIMMS_MET": 262144,
    "MG_F_INFO_FROM_TERMINAL": 524288,
    # Free bits: 1<<20..22 main quest, 1<<23..25 merchants, 1<<26..28 side quests,
    # 1<<29..30 flavour. Add a named entry here when you take one.
    # Merchants (1<<23): the player handed Gob the $180 of back pay (mggob.ssl sets it; Nova reads it).
    "MG_F_WAGES_RETURNED": 8388608,
    # Flavour (1<<29): Mother Maya passed on the rumour that the sheriff wants the bomb made safe
    # (mgmaya.ssl sets it; Simms may read it to let the player bring the subject up).
    "MG_F_MAYA_RUMOUR": 536870912,
    # Flavour (1<<30): the player settled Stockholm's eight-dollar tab (mgstock.ssl sets it).
    "MG_F_STOCKHOLM_PAID": 1073741824,
    # Side quests (1<<26): the player took the $180 of staff wages out of Moriarty's strongbox
    # (mgstrong.ssl sets it, with -5 karma). mggob.ssl may offer "this is yours" while it is set
    # and MG_F_WAGES_RETURNED is not.
    "MG_F_WAGES_TAKEN": 67108864,
    # Merchants (1<<24): the bomb has refused the player although he had Moira's notes (mgbomb.ssl sets it on
    # such a failure; mgmoira.ssl then offers "your notes got me close, not close enough" and lends her tools).
    "MG_F_BOMB_TRIED": 16777216,
    # Main quest: the player confessed to Simms that he fitted Burke's charge (reward is the base amount only).
    "MG_F_SIMMS_KNOWS_RIG": 1 << 20,
    # Main quest: Simms knows about Burke but agreed to let the player handle him (no saloon scene).
    "MG_F_SIMMS_STANDS_DOWN": 1 << 21,
    # Main quest: the player walked into town before meeting Simms; he comes over to give his one warning (mgspsims.ssl).
    "MG_F_SIMMS_SUMMONED": 1 << 22,
}

# Vanilla variable reused: town reputation slot that belongs to Area 18.
VANILLA_GVARS = {
    "GVAR_PLAYER_REPUTATION": 0,
    "GVAR_TOWN_REP_MEGATON": 65,
}

# --- new item protos ---------------------------------------------------------------
# Vanilla has 531 items; ours are appended to proto/items/items.lst in this order
# (never reorder: PIDs are stored in maps and saves).
# (define name, PID, name shown in game, description, vanilla PID to clone)
ITEMS = [
    ("PID_MG_PULSE_CHARGE", 532, "Fusion Pulse Charge",
     "A fist-sized charge of pre-War make. A tag wired to it reads: FIT TO SOCKET. WALK AWAY.", 59),
    ("PID_MG_HOUSE_KEY", 533, "Megaton House Key",
     "A brass key on a loop of wire. It opens the empty house by the gate in Megaton.", 82),
    ("PID_MG_LUCY_LETTER", 534, "Lucy West's Letter",
     "A folded letter, sealed with candle wax and addressed to the West family homestead.", 476),
    ("PID_MG_MOIRA_NOTES", 535, "Moira's Bomb Notes",
     "Cheerful, closely written notes and a wiring diagram titled 'Things Not To Touch (probably)'.", 487),
    ("PID_MG_CONTRACT", 536, "Contract",
     "A short note: 'One meddler, last seen near Megaton. Half now, half on proof. - B.'", 487),
    ("PID_MG_OFFICE_KEY", 537, "Moriarty's Key",
     "A heavy iron key that smells of cheap whiskey.", 105),
]

# --- custom art (mod/megaton-art) -----------------------------------------------------
# The pre-rendered scenery and wall pieces come from the Blender pipeline in mod/megaton-art
# (its manifest.json numbers every sprite); `build.py art` stages them into this mod's tree.
# Each sprite is one "slot": a proto and an art-list line. Slot i of a kind is
#     PID      (type << 24) | (ART_FIRST_PID[kind] + i)     proto/<kind>/<prefix><i:04d>.pro
#     art line ART_FIRST_ART[kind] + i                      art/<kind>/<prefix><i:04d>.frm
# Proto lists are padded with "mgpad.pro" lines from the end of the stock list up to
# ART_FIRST_PID - 1: those lines (scenery 1852..1899, walls 1634..1699) are the only free
# numbers left for other new scenery / wall protos. Art lines directly follow the stock ones,
# so nothing else may append to art/scenery/scenery.lst or art/walls/walls.lst.
#
# Maps and saves store these PIDs and FIDs, so slots are append-only. The ledger
# art_ids.json (beside this file) lists every slot ever shipped, in order; `build.py ids`
# refuses a manifest in which a recorded slot moved or vanished, and appends new ones.
ART_FIRST_PID = {"scenery": 1900, "wall": 1700}
ART_FIRST_ART = {"scenery": 1863, "wall": 1690}      # = number of lines of the stock art lists
ART_PREFIX = {"scenery": "mgs", "wall": "mgw"}
ART_LEDGER = "art_ids.json"

# Sprites that scripts or the cast name: (define written to ids.h, piece in the art manifest).
# The define is the PID of the piece's main part (each of these pieces has exactly one).
ART_NAMES = [
    ("PID_MGA_BOMB", "mgb_bomb_states"),          # the bomb: ONE object, its frame is the quest state
    ("PID_MGA_LECTERN", "mgb_lectern"),           # Cromwell's lectern (was the stock podium)
    ("PID_MGA_BANNER_RED", "mgb_banner"),         # banners of the Children of Atom at the pool
    ("PID_MGA_BANNER_YELLOW", "mgb_banner_b"),
    ("PID_MGA_ATOM_SIGN", "sg_atom"),             # the welded atom by the church door
    ("PID_MGA_WATER_TANK", "sg_water"),           # WATER tank in the plant yard
    ("PID_MGA_DANGER_SIGN", "mgb_sign"),          # warning sign at the pool
    ("PID_MGA_NOODLE_BAR", "sg_noodle_bar"),      # the Brass Lantern's counter
]
# Frames of PID_MGA_BOMB (mod/megaton-art/pieces/bomb/mgb_bomb.py renders them in this order).
ART_BOMB_FRAMES = {"MGA_BOMB_FRAME_DORMANT": 0, "MGA_BOMB_FRAME_RIGGED": 1, "MGA_BOMB_FRAME_DISARMED": 2}
# The gate: the stock double-gate door proto keeps its place, flags and script and wears this
# piece's five-frame FRM (frame 0 shut .. 4 open; the engine plays it when the door is used).
ART_GATE_DOOR = "mg_gate_door"

# --- quests.txt / quests.msg ------------------------------------------------------
# (quests.msg id, text, gvar name, value at which it is listed, value at which it is done)
QUESTS = [
    (4000, "Disarm the atomic bomb in the middle of Megaton.", "GVAR_MG_Q_SIMMS", 1, 3),
    (4001, "Rig the Megaton bomb for Mister Burke.", "GVAR_MG_Q_BURKE", 2, 4),
    (4002, "Fix the three leaking pipes for Walter.", "GVAR_MG_Q_WATER", 1, 3),
    (4003, "Get Moriarty's information.", "GVAR_MG_Q_INFO", 1, 3),
    (4004, "Mail Lucy West's letter.", "GVAR_MG_Q_LETTER", 1, 3),
]

# --- scripts.lst / scrname.msg ------------------------------------------------------
# Vanilla (patched) scripts.lst has 1303 lines; ours are appended in this order,
# so entries may be added at the END but never reordered or removed once saves
# exist. local_vars is deliberately generous: local_var() silently fails beyond
# the declared count. A registered script without a .ssl file is simply not
# built (its slot stays reserved).
# (file stem (<= 8 chars), display name shown when looking at the object, comment)
LOCAL_VARS = 16
SCRIPTS = [
    ("megaton", "", "Megaton map script"),
    # Main quest
    ("mgweld", "Deputy Weld", "Megaton gate greeter robot"),
    ("mgsimms", "Lucas Simms", "Megaton sheriff"),
    ("mgburke", "Mister Burke", "Megaton saloon stranger"),
    ("mgbomb", "Bomb", "Megaton atomic bomb"),
    ("mgharden", "Harden Simms", "Megaton sheriff's son"),
    # Merchants and services
    ("mgmoira", "Moira Brown", "Megaton Craterside Supply"),
    ("mggob", "Gob", "Megaton saloon bartender"),
    ("mgdoc", "Doc Church", "Megaton clinic"),
    ("mgjenny", "Jenny Stahl", "Megaton Brass Lantern"),
    ("mgtrade", "Lucky Harith", "Megaton caravan outside the gate"),
    ("mgnova", "Nova", "Megaton saloon"),
    # Side quests
    ("mgmoriar", "Colin Moriarty", "Megaton saloon owner"),
    ("mgsilvr", "Silver", "Megaton runaway outside the walls"),
    ("mgterm", "Terminal", "Megaton Moriarty's terminal"),
    ("mgwalter", "Walter", "Megaton water plant"),
    ("mgleak", "Leaking Pipe", "Megaton leaking pipe"),
    ("mglucy", "Lucy West", "Megaton saloon patron"),
    # Flavour
    ("mgcrom", "Confessor Cromwell", "Megaton Children of Atom"),
    ("mgmaya", "Mother Maya", "Megaton Children of Atom"),
    ("mgstock", "Stockholm", "Megaton gate sniper"),
    ("mgmicky", "Micky", "Megaton beggar"),
    ("mgjeri", "Jericho", "Megaton ex-raider"),
    ("mgbilly", "Billy Creel", "Megaton resident"),
    ("mgmaggie", "Maggie", "Megaton child"),
    ("mgnathan", "Nathan Vargas", "Megaton resident"),
    ("mgsettlr", "Settler", "Megaton generic settler"),
    ("mgmerc", "Mercenary", "Megaton Moira's guard"),
    ("mghitman", "Hired Gun", "Megaton Burke's hired guns"),
    # Spatial triggers
    ("mgspgate", "", "Megaton spatial: arrival at the gate"),
    ("mgspsims", "", "Megaton spatial: Simms greets the player"),
    ("mgsprad", "", "Megaton spatial: radiation at the pool"),
    # Doors, containers, furniture
    ("mggate", "Gate", "Megaton main gate"),
    ("mghouse", "Door", "Megaton player house door"),
    ("mgoffice", "Door", "Megaton Moriarty's office door"),
    ("mgarmory", "Door", "Megaton armory door"),
    ("mgstrong", "Strongbox", "Megaton wage strongbox"),
    ("mgcabin", "Cabinet", "Megaton password cabinet"),
    ("mgbed", "Bed", "Megaton bed the player may rest in"),
    ("mgdecor", "", "Megaton furniture: descriptions, locked stashes"),
]


# --- helpers for the custom art ---------------------------------------------------------
def art_dir():
    """mod/megaton-art: the pipeline's manifest.json, its built out/ tree and placement.py."""
    import os

    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "megaton-art")


def art_manifest():
    """The art pipeline's manifest.json (every sprite, piece by piece), or None if it is not there."""
    import json
    import os

    path = os.path.join(art_dir(), "manifest.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def art_pids(manifest=None):
    """{define: PID} for ART_NAMES, read from the manifest ({} without one)."""
    manifest = manifest or art_manifest()
    if manifest is None:
        return {}
    found = {}
    for define, piece in ART_NAMES:
        main = [part for part in manifest["pieces"][piece]["parts"] if part["layer"] == "main"]
        if len(main) != 1:
            raise ValueError(f"art piece {piece} has {len(main)} main parts; ART_NAMES needs exactly one")
        found[define] = int(main[0]["pid"], 16)
    return found
