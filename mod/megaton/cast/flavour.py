# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Cast of the flavour group: the townsfolk who are not part of any quest, and the armory.

    cd mod/megaton && python3 -m cast        lists every entry with its spot

Who is who (protos chosen with tools/contact_sheet.py and f2lib ProtoDB; a
critter's look, SPECIAL and skills come from its proto, only hp / team / AI are
set here):

    CROMWELL   Holy Man (narobe robes, 47 hp). Stands in the pool beside the bomb
               and preaches; mgcrom.ssl never moves him. Non-fighter.
    MAYA       Holy Woman (same robes, 45 hp), inside the church. Non-fighter.
    STOCKHOLM  Weak Gun Guard (hmlthr leather armour, 43 hp) with a hunting rifle:
               the sniper post beside the gate, outside the wall.
    MICKY      Weak Peasant (nmbpea, bald and ragged), down to 12 of his 30 hp:
               the beggar slumped against the wall outside. Owns nothing.
    BILLY      Trapper (nmlthr leather jacket, 50 hp), 10mm pistol: in his house.
    MAGGIE     Child (Female) (nachld, 25 hp): plays outside Billy's house.
    NATHAN     McGee (nmoldd, the old man in a waistcoat, 40 hp): by the wrecked tanker truck.
    SETTLER1,2 the congregation at the pool's edge; SETTLER3, SETTLER4 walk
               about town. All four run mgsettlr.ssl, which tells them apart by
               the spot they start on (a settler placed anywhere else just
               stands where he was put and chats).
    ARMORY_DOOR    the architect's door between the Sheriff's living room and
                   the armory closet gets mgarmory.ssl (it locks itself).
    ARMORY_LOCKER  the weapons locker behind that door. Not scripted and not
                   locked: the door is the lock. Contents are a mid-game
                   payoff for a hard Lockpick check, see mgarmory.ssl.

Everyone is on the town team. Cromwell, Maya, Micky and Maggie have no weapon
and never attack; their AI packets (coward / child) make them run from a fight.
"""
from cast import *

CAST = [
    # Children of Atom
    critter("CROMWELL", PID_CR_HOLY_MAN, script="mgcrom", ai=AI_MG_COWARD,
            items=[(PID_MONEY, 14)]),
    critter("MAYA", PID_CR_HOLY_WOMAN, script="mgmaya", ai=AI_MG_COWARD,
            items=[(PID_WATER_FLASK, 1), (PID_MONEY, 9)]),

    # Outside the gate
    critter("STOCKHOLM", PID_CR_WEAK_GUN_GUARD_71, script="mgstock", ai=AI_MG_GUARD,
            items=[(PID_HUNTING_RIFLE, 1, "right"), (PID_223_FMJ, 1), (PID_STIMPAK, 1), (PID_MONEY, 3)]),
    critter("MICKY", PID_CR_WEAK_PEASANT_63, script="mgmicky", ai=AI_MG_COWARD, hp=12),

    # Residents
    critter("BILLY", PID_CR_TRAPPER_95, script="mgbilly", ai=AI_MG_TOUGH_CITIZEN,
            items=[(PID_10MM_PISTOL, 1, "right"), (PID_10MM_JHP, 1), (PID_BEER, 1), (PID_MONEY, 35)]),
    critter("MAGGIE", PID_CR_CHILD_FEMALE, script="mgmaggie", ai=AI_MG_CHILD),
    critter("NATHAN", PID_CR_MCGEE, script="mgnathan", ai=AI_MG_CITIZEN,
            items=[(PID_RADIO, 1), (PID_MONEY, 11)]),

    # Settlers (mgsettlr.ssl: roles by starting spot)
    critter("SETTLER1", PID_CR_AVERAGE_PEASANT_66, script="mgsettlr",
            items=[(PID_MONEY, 6)]),
    critter("SETTLER2", PID_CR_STRONG_PEASANT_67, script="mgsettlr",
            items=[(PID_KNIFE, 1), (PID_MONEY, 8)]),
    critter("SETTLER3", PID_CR_AVERAGE_PEASANT_65, script="mgsettlr",
            items=[(PID_MEAT_JERKY, 1), (PID_MONEY, 12)]),
    critter("SETTLER4", PID_CR_STRONG_PEASANT_68, script="mgsettlr",
            items=[(PID_FRUIT, 2), (PID_MONEY, 5)]),

    # The Sheriff's armory closet
    attach("ARMORY_DOOR", "door", script="mgarmory"),
    thing("ARMORY_LOCKER", PID_LOCKER_132,
          items=[(PID_10MM_SMG, 1), (PID_10MM_JHP, 4), (PID_HUNTING_RIFLE, 1), (PID_223_FMJ, 2),
                 (PID_SHOTGUN, 1), (PID_12_GA_SHOTGUN_SHELLS, 3), (PID_LEATHER_ARMOR, 1),
                 (PID_COMBAT_KNIFE, 1), (PID_STIMPAK, 3), (PID_SHERIFFS_BADGE, 1)]),
]
