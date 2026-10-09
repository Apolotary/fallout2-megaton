# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Cast of the main quest: who and what the "core" scripts need on the map.

    python3 -m cast            (from mod/megaton/) lists every entry with its spot

Protos (looks, stats and weapon animations come from the vanilla proto; checked
with tools/contact_sheet.py and `python3 -m f2lib proto <pid>`):

  Deputy Weld   Robobrain (maroboaa): the nearest thing Fallout 2 has to an
                upright greeter robot. Unarmed; "deterrence hardware: not fitted".
  Lucas Simms   NCR Guard (nmcoppaa): blue police coat and cap, the only lawman
                sprite. It has rifle animations, so his rifle shows and fires. A HUNTING
                rifle: with the assault rifle of the brief his first burst killed a
                level-1 character outright, and the weapon lay on his body for whoever
                stood by while Burke shot him (mgsimms.ssl: lose_his_things).
  Mister Burke  Mobster (nmboncaa): blue suit, pale hat, red tie. This sprite has
                ONLY rifle-class animations: a pistol would leave him fighting
                bare-handed, hence the sawed-off shotgun. It is in his pack, not
                in his hand: he looks unarmed until mgburke.ssl (or the combat
                AI) has him draw it.
  Harden Simms  Child (Male).
  Hired guns    the three "Weak ... Guard" protos in leather (43 to 46 hit points,
                poor shots): an ambush a low-level character can survive this
                close to Arroyo. The leader (on HITMAN1) carries the contract and
                the money. mghitman.ssl keeps all three hidden until megaton.ssl
                sets MG_F_HIT_SQUAD_DONE; they wait at the caravan camp and walk in.

Nobody has an `hp=` override: anything below the proto's maximum makes the
engine add "He looks: Wounded" to the description of a man nobody has touched.

Things the ARCHITECT must provide (attach entries): a door object on GATE (the
main gate; mggate.ssl locks it until Weld has greeted the player, then opens it
for good) and a door object on HOUSE_DOOR (the Empty House; mghouse.ssl). If the
gate is built from more than one door object, add an attach line per leaf.

The bomb is placed here (PID_MGA_BOMB on BOMB: the custom three-state sprite of
mod/megaton-art, one object whose frame mgbomb.ssl sets from GVAR_MG_BOMB)
because its script is the quest. The layout dresses it (goo, pool, the sprite's
blockers: layout/art.py) but must not put a second bomb on that hex.
"""
from cast import *

CAST = [
    # --- outside the gate
    critter("WELD", PID_CR_ROBOBRAIN_75, script="mgweld", ai=AI_MG_ROBOT),

    # --- the sheriff and his son
    critter("SIMMS", PID_CR_NCR_GUARD_137, script="mgsimms", ai=AI_MG_GUARD,
            items=[(PID_HUNTING_RIFLE, 1, "right"), (PID_223_FMJ, 2), (PID_STIMPAK, 2),
                   (PID_MG_HOUSE_KEY, 1), (PID_MONEY, 40)]),
    critter("HARDEN", PID_CR_CHILD_MALE, script="mgharden", ai=AI_MG_CHILD),

    # --- the man in the corner of the saloon; nobody in town is on his team
    critter("BURKE", PID_CR_MOBSTER, script="mgburke", team=TEAM_MG_BURKE, ai=AI_MG_BURKE,
            items=[(PID_SAWED_OFF_SHOTGUN, 1), (PID_12_GA_SHOTGUN_SHELLS, 1),
                   (PID_MG_PULSE_CHARGE, 1), (PID_MONEY, 120)]),

    # --- the bomb, and the radiation around it
    thing("BOMB", PID_MGA_BOMB, script="mgbomb"),
    spatial("BOMB", radius=4, script="mgsprad"),

    # --- arrival
    spatial("ARRIVAL", radius=5, script="mgspgate"),
    spatial("SIMMS_GREET", radius=4, script="mgspsims"),
    attach("GATE", "door", script="mggate"),

    # --- the reward
    attach("HOUSE_DOOR", "door", script="mghouse"),

    # --- Burke's hired guns (hidden until due)
    critter("HITMAN1", PID_CR_WEAK_GUN_GUARD_71, script="mghitman", team=TEAM_MG_HIRED, ai=AI_MG_HIRED_GUN,
            items=[(PID_10MM_PISTOL, 1, "right"), (PID_10MM_JHP, 1), (PID_STIMPAK, 1),
                   (PID_MG_CONTRACT, 1), (PID_MONEY, 150)]),
    critter("HITMAN2", PID_CR_WEAK_MELEE_GUARD_69, script="mghitman", team=TEAM_MG_HIRED, ai=AI_MG_HIRED_GUN,
            items=[(PID_SPEAR, 1, "right")]),
    critter("HITMAN3", PID_CR_WEAK_GUN_GUARD_72, script="mghitman", team=TEAM_MG_HIRED, ai=AI_MG_HIRED_GUN,
            items=[(PID_PIPE_RIFLE, 1, "right"), (PID_10MM_JHP, 1)]),
]
