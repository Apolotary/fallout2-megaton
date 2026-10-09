# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Cast of the side quests: who and what the sidequests script group puts on the map.

    Moriarty's information   Colin Moriarty, Silver, the office door, his terminal,
                             the password cabinet and the wage strongbox (brief 5.7)
    Walter's leaks           Walter and three leaking pipes (brief 5.6)
    Lucy West's letter       Lucy West (brief 5.8)
    and Jericho, who sells the tip about the strongbox (brief 6.11)

What the architect has to provide
  OFFICE_DOOR   a real door in the wall between the saloon hall and the office;
                mgoffice.ssl is attached to it and locks it on the first visit.
                The office (TERMINAL, CABINET, STRONGBOX) must have no other way in.
  LEAK1..3      hexes against the wall of the empty house, the common house and
                the church, each with a free hex beside it to work from. Each gets
                TWO objects on the same hex, a pipe and a plume of steam, both
                running mgleak.ssl; the script tells the leaks apart by comparing
                its own tile with TILE_LEAK1..3, so they must stand exactly on those
                spots. The pipe removes the steam when the leak is closed. The pipe
                blocks its hex. Neither proto has the "use" action: a leak is closed
                with the Repair skill or by using Junk / a tool on it (mgleak.ssl).
  SILVER        outside the wall, out of sight of the gate; a lean-to and a dead
                camp fire are dressing only.
  Everybody else stands on the spot named after them. Jericho is cast here because
  this group wrote his script, although registry.py lists mgjeri under "Flavour".

Looks (vanilla protos; only team, AI and inventory are ours)
  Moriarty   nmfatt, the heavyset barkeep in a waistcoat ("Generic Bartender 1", 45 HP)
  Jericho    nmlthr, bald man in leather armour ("Raider", 60 HP), hunting rifle
  Lucy West  nfpeas, plainly dressed young woman ("Strong Peasant", 31 HP)
  Walter     nmpeas, working man in a cap and vest ("Davin", 35 HP)
  Silver     nftrmp, ragged skirt ("Generic Slut 1", 45 HP); her own team, so a fight
             with her never involves the town
Everybody starts at the proto's full hit points on purpose: a critter placed below its
maximum is described as wounded when looked at. The protos were picked for their hit
points as much as for their art (several with the same sprite have 75 to 130).
"""
from cast import *

# Moriarty's key (PID_MG_OFFICE_KEY) is on him: Steal gets it, and so does his corpse.
# Silver carries the $300 she took; mgsilvr.ssl hands it over from her inventory.
# Walter's $200 reward is paid out of his own purse, so his corpse still pays for the job.
# The $180 of wages in the strongbox is NOT an item: mgstrong.ssl hands it out and remembers.
CAST = [
    critter("MORIARTY", PID_CR_GENERIC_BARTENDER_1, script="mgmoriar", ai=AI_MG_TOUGH_CITIZEN,
            items=[(PID_10MM_PISTOL, 1, "right"), (PID_10MM_JHP, 1), (PID_MG_OFFICE_KEY, 1),
                   (PID_MONEY, 120), (PID_BOOZE, 1)]),
    critter("JERICHO", PID_CR_RAIDER_238, script="mgjeri", ai=AI_MG_GUARD,
            items=[(PID_HUNTING_RIFLE, 1, "right"), (PID_223_FMJ, 2), (PID_BOOZE, 2), (PID_MONEY, 35)]),
    critter("LUCY", PID_CR_STRONG_PEASANT_68, script="mglucy", ai=AI_MG_CITIZEN,
            items=[(PID_MONEY, 40), (PID_NUKA_COLA, 2)]),
    critter("WALTER", PID_CR_DAVIN, script="mgwalter", ai=AI_MG_CITIZEN,
            items=[(PID_WRENCH, 1, "right"), (PID_MONEY, 230), (PID_JUNK, 1)]),
    critter("SILVER", PID_CR_GENERIC_SLUT_1, script="mgsilvr", team=TEAM_MG_SILVER, ai=AI_MG_TOUGH_CITIZEN,
            items=[(PID_KNIFE, 1, "right"), (PID_MONEY, 300), (PID_JET, 2), (PID_ROT_GUT, 1)]),

    attach("OFFICE_DOOR", "door", script="mgoffice"),
    thing("TERMINAL", PID_SC_TERMINAL_632, script="mgterm"),
    thing("CABINET", PID_LOCKER_188, script="mgcabin", locked=True,
          items=[(PID_BOOZE, 2), (PID_MENTATS, 1), (PID_MONEY, 35)]),
    thing("STRONGBOX", PID_FOOTLOCKER_128, script="mgstrong", locked=True),

    thing("LEAK1", PID_SC_PIPE_415, script="mgleak"),
    thing("LEAK1", PID_SC_STEAM_1851, script="mgleak"),
    thing("LEAK2", PID_SC_PIPE_415, script="mgleak"),
    thing("LEAK2", PID_SC_STEAM_1851, script="mgleak"),
    thing("LEAK3", PID_SC_PIPE_415, script="mgleak"),
    thing("LEAK3", PID_SC_STEAM_1851, script="mgleak"),
]
