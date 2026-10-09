# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Cast of the "merchants" script group: the shops and services of Megaton.

    MOIRA        Moira Brown, Craterside Supply          mgmoira   barter
    MERC         her hired mercenary, at the counter's end   mgmerc
    GOB          Gob, behind Moriarty's bar              mggob     barter
    DOC          Doc Church, the clinic                  mgdoc     barter + healing
    JENNY        Jenny Stahl, Brass Lantern counter      mgjenny   barter
    TRADER       "Lucky" Harith, the caravan outside     mgtrade   barter + Lucy's letter
    NOVA         Nova, saloon floor                      mgnova    room rental, password
    HOUSE_BED    bed of the player's house               mgbed     (attached to the architect's bed)
    COMMON_BED   a cot in the Common House               mgbed     (attached to the architect's bed)

Stock is NOT listed here on purpose. Every merchant script keeps its own list
in its `restock` procedure and fills the critter's inventory itself (first
visit, then every three days, topping up to the listed quantities and to the
listed cash), so there is one table per shop and nothing to keep in step.
Only what a character wears or wields is given here.

Protos were picked for their look and for the barter flag in the proto (a
script cannot add it): python3 tools/contact_sheet.py critters --name '...'
and python3 -m f2lib proto <pid>. The name shown in the game comes from
registry.SCRIPTS, not from the proto.

Placement notes for the architect
  - MOIRA stands behind her counter and MERC within about five hexes of the
    customer side with a clear view of it: he warns thieves by sight.
  - GOB behind the bar, NOVA on the saloon floor; nothing depends on distance.
  - TRADER camps by the fire outside the gate; BURKE_RENDEZVOUS is that fire.
  - HOUSE_BED / COMMON_BED must be bed scenery standing exactly on the spot
    (the script tells the two apart by TILE_HOUSE_BED), with a free hex
    within three hexes of it: the rest menu opens when the player EXAMINES
    the bed from that close (no stock bed has the "use" action; mgbed.ssl
    explains). More beds in the Common House may carry mgbed too: add
    attach() lines with new spots.
  - NOVA_BED (the rented room) gets no script: the night there is sold by Nova.
"""
from cast import *

CAST = [
    # Fair-haired woman in tan work clothes. Proto "Average Merchant": 46 hp, barter flag.
    critter("MOIRA", PID_CR_AVERAGE_MERCHANT_59, script="mgmoira", ai=AI_MG_MERCHANT),

    # Leather armor and a shotgun. Proto "Mercenary": 60 hp, Small Guns 56 %. (The brief's assault rifle
    # did 31 points in one burst to a 44-point character: a shop guard, not a firing squad.)
    critter("MERC", PID_CR_MERCENARY_359, script="mgmerc", ai=AI_MG_GUARD,
            items=[(PID_SHOTGUN, 1, "right"), (PID_LEATHER_ARMOR, 1, "worn"), (PID_12_GA_SHOTGUN_SHELLS, 1),
                   (PID_STIMPAK, 1), (PID_MONEY, 35)]),

    # Proto "Generic Ghoul": 53 hp, barter flag. He runs rather than fights.
    critter("GOB", PID_CR_GENERIC_GHOUL_159, script="mggob", ai=AI_MG_COWARD),

    # White coat. Proto "Doc Jones": 55 hp, barter flag.
    critter("DOC", PID_CR_DOC_JONES, script="mgdoc", ai=AI_MG_DOCTOR),

    # Proto "Master Trader" (female): 42 hp, barter flag.
    critter("JENNY", PID_CR_MASTER_TRADER_61, script="mgjenny", ai=AI_MG_MERCHANT),

    # Weathered man in a red shirt. Proto "Prospector": 67 hp, barter flag; he stands his ground.
    critter("TRADER", PID_CR_PROSPECTOR_236, script="mgtrade", ai=AI_MG_TOUGH_CITIZEN),

    # 45 hp; no barter (she rents the room through her dialogue).
    critter("NOVA", PID_CR_GENERIC_SLUT_1, script="mgnova", ai=AI_MG_CITIZEN,
            items=[(PID_MONEY, 12), (PID_JET, 1)]),

    # Beds the architect places (layout/buildings.py: a flat mattress); a test stage puts the same one there.
    attach("HOUSE_BED", "scenery", script="mgbed", stand_in=PID_SC_BED_208),
    attach("COMMON_BED", "scenery", script="mgbed", stand_in=PID_SC_BED_208),
]
