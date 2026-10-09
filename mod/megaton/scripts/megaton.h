// SPDX-License-Identifier: LicenseRef-Sustainable-Use
/*
 * megaton.h - the one header every Megaton script includes.
 *
 *     #include "megaton.h"
 *     #define NAME                    SCRIPT_MGSIMMS      // this script's own number (ids.h)
 *
 * It pulls in fo2.h (engine constants and the dialogue / text / skill macros),
 * ids.h (generated from registry.py: SCRIPT_*, GVAR_MG_*, MG_F_*, PID_MG_*,
 * MAP_MEGATON, AREA_MEGATON) and tiles.h (generated from layout/spots.py:
 * TILE_<SPOT>, ROT_<SPOT>). Scripts never write raw tile numbers, GVAR numbers
 * or PIDs of mod content.
 *
 * Everything below is a macro: a header cannot hold procedures, because the
 * engine runs procedure #1 for every event a script does not handle and that
 * slot must stay the script's own empty `start`. Macros marked "statement" are
 * complete statements that are safe bare after then / else; write them with a
 * ';' like any call.
 * `and` / `or` are NOT short-circuit in this language: both sides always run,
 * which is why the macros nest `if`s instead of chaining conditions.
 *
 * Local variables: scripts.lst gives every Megaton script 16 (registry.LOCAL_VARS).
 * 0..11 belong to the script, 12..15 to this header (MG_LVAR_*).
 *
 * Shared text lives in megaton.msg, the map script's message file, ids 900..999
 * (MG_MSG_*); any script reads it with message_str(SCRIPT_MEGATON, id).
 *
 * The reference NPC that uses the whole townsperson block, and that the engine
 * test tests/foundation/townsfolk.txt drives, is tests/foundation/scripts/mgsettlr.ssl.
 */
#ifndef MEGATON_H
#define MEGATON_H

#include "fo2.h"
#include "ids.h"
#include "tiles.h"

/* Like fo2.h's one_statement(), for a body that ends with `end`: the language
   allows no ';' after a block, and one_statement() would put one there. */
#define mg_block(body)          if (true) then begin body end else return

/* ---------------------------------------------------------------- flag field */

/* GVAR_MG_FLAGS is a bit field; the bits are the MG_F_* constants of ids.h. */
#define mg_flag(F)              ((global_var(GVAR_MG_FLAGS) bwand (F)) != 0)                             // true when flag F is set
#define mg_set_flag(F)          set_global_var(GVAR_MG_FLAGS, global_var(GVAR_MG_FLAGS) bwor (F))        // set flag F
#define mg_clear_flag(F)        set_global_var(GVAR_MG_FLAGS, (global_var(GVAR_MG_FLAGS) bwor (F)) - (F))  // clear flag F

/* ------------------------------------------------------------- quest states */

/* Values of the state GVARs (design brief 5.1). Read with gvar(), write with
   set_gvar() or, for the Pip-Boy quests, mg_advance() so a quest never runs
   backwards and a finished one cannot be reopened by a stale dialogue option. */

/* GVAR_MG_BOMB */
#define MG_BOMB_DORMANT         (0)       // ticking faintly, as it has for a century
#define MG_BOMB_DISARMED        (1)       // made safe for good
#define MG_BOMB_RIGGED          (2)       // Burke's pulse charge is fitted
#define MG_BOMB_DETONATED       (3)       // the town is gone

/* GVAR_MG_Q_SIMMS - Pip-Boy "Disarm the atomic bomb" (listed at 1, crossed out at 3) */
#define MG_Q_SIMMS_NONE         (0)
#define MG_Q_SIMMS_ACTIVE       (1)       // Simms made his offer
#define MG_Q_SIMMS_DISARMED     (2)       // bomb is dead, nobody has told him
#define MG_Q_SIMMS_REWARDED     (3)       // paid, house handed over

/* GVAR_MG_Q_BURKE - Pip-Boy "Rig the Megaton bomb" (listed at 2, crossed out at 4) */
#define MG_Q_BURKE_NONE         (0)
#define MG_Q_BURKE_HEARD        (1)       // heard the pitch (not listed yet)
#define MG_Q_BURKE_ACCEPTED     (2)       // carrying the pulse charge
#define MG_Q_BURKE_PLANTED      (3)       // charge fitted to the bomb
#define MG_Q_BURKE_DONE         (4)       // detonated and paid

/* GVAR_MG_BURKE - where the man himself is */
#define MG_BURKE_IN_SALOON      (0)
#define MG_BURKE_LEFT           (1)       // walked out alive; his hired guns will follow
#define MG_BURKE_SHOT_SIMMS     (2)       // killed the sheriff and fled
#define MG_BURKE_DEAD           (3)
#define MG_BURKE_RENDEZVOUS     (4)       // waiting by the caravan fire for the word
#define MG_BURKE_GONE           (5)       // left after the blast

/* GVAR_MG_SIMMS */
#define MG_SIMMS_ALIVE          (0)
#define MG_SIMMS_TOLD           (1)       // knows about Burke; the saloon scene is pending
#define MG_SIMMS_SURVIVED       (2)       // alive after the scene
#define MG_SIMMS_DEAD           (3)

/* GVAR_MG_Q_WATER - Pip-Boy "Fix the three leaking pipes" (listed at 1, crossed out at 3) */
#define MG_Q_WATER_NONE         (0)
#define MG_Q_WATER_ACCEPTED     (1)
#define MG_Q_WATER_FIXED        (2)       // all three leaks closed, not yet reported
#define MG_Q_WATER_PAID         (3)

/* GVAR_MG_Q_INFO - Pip-Boy "Get Moriarty's information" (listed at 1, crossed out at 3) */
#define MG_Q_INFO_NONE          (0)
#define MG_Q_INFO_QUOTED        (1)       // he named his price
#define MG_Q_INFO_SILVER        (2)       // working it off: the Silver job
#define MG_Q_INFO_OBTAINED      (3)

/* GVAR_MG_Q_LETTER - Pip-Boy "Post Lucy West's letter" (listed at 1, crossed out at 3) */
#define MG_Q_LETTER_NONE        (0)
#define MG_Q_LETTER_CARRYING    (1)
#define MG_Q_LETTER_POSTED      (2)       // the caravan has it, Lucy does not know yet
#define MG_Q_LETTER_DONE        (3)

/* GVAR_MG_KIT_GIVEN - decided once, on the first entry to the map (megaton.ssl) */
#define MG_KIT_UNDECIDED        (0)
#define MG_KIT_GIVEN            (1)       // the game began at the gate: starting kit handed out
#define MG_KIT_NOT_DUE          (2)       // the player walked here from somewhere else

/* GVAR_MG_LEAK_BITS - which of Walter's leaks are fixed */
#define MG_LEAK_1               (1)       // by the empty house (TILE_LEAK1)
#define MG_LEAK_2               (2)       // by the common house (TILE_LEAK2)
#define MG_LEAK_3               (4)       // on the church wall (TILE_LEAK3)
#define MG_LEAK_ALL             (7)

/* GVAR_MG_SCENE - step of the saloon confrontation; the main-quest scripts name the other steps */
#define MG_SCENE_IDLE           (0)
#define MG_SCENE_ENDED          (7)       // = MG_SCENE_DONE of mgcore.h
#define MG_HUSH_TICKS           (300)     // thirty seconds
// true while Simms and Burke are having it out in the saloon and for half a minute afterwards:
// nobody in there chatters about drinks and room prices over an arrest or a body (the saloon's
// regulars test it before their idle floats; GVAR_MG_SCENE_TICK is when the current step began)
#define mg_saloon_hush          ((global_var(GVAR_MG_SCENE) != MG_SCENE_IDLE) and \
                                 ((global_var(GVAR_MG_SCENE) != MG_SCENE_ENDED) or ((game_time - global_var(GVAR_MG_SCENE_TICK)) < MG_HUSH_TICKS)))

/* GVAR_MG_TOWN_HOSTILE */
#define MG_TOWN_PEACEFUL        (0)
#define MG_TOWN_IS_HOSTILE      (1)       // every townsperson attacks the player on sight, until megaton.ssl forgives (a week away)

// statement: raise a state GVAR to `value` unless it is already there or beyond (states never go back)
#define mg_advance(var, value)  one_statement(if (global_var(var) < (value)) then set_global_var(var, value))

/* ------------------------------------------------- karma, reputation, rewards */

#define mg_karma                global_var(GVAR_PLAYER_REPUTATION)                                       // the player's karma
// statement: change karma by n (may be negative) and say so in the message window ("You gain 10 karma.").
// The stock game changes karma silently and fallout2-ce only reports it with DisplayKarmaChanges=1 in
// ddraw.ini, which the browser build does not set; a player who does set it sees both lines.
// n is expanded three times: pass a constant or a plain variable.
// true when the engine itself announces every karma change (ddraw.ini [Misc] DisplayKarmaChanges=1): then the mod's own
// line would be a second one for the same change. get_ini_setting is an sfall function fallout2-ce implements; it
// answers -1 when the file or the key is missing.
#define mg_engine_prints_karma  (get_ini_setting("ddraw.ini|Misc|DisplayKarmaChanges") == 1)
#define mg_add_karma(n)         one_statement(set_global_var(GVAR_PLAYER_REPUTATION, global_var(GVAR_PLAYER_REPUTATION) + (n)); \
                                   if (((n) > 0) and (mg_engine_prints_karma == false)) then display_msg(message_str(SCRIPT_MEGATON, MG_MSG_KARMA_GAIN) + (n) + message_str(SCRIPT_MEGATON, MG_MSG_KARMA_AFTER)); \
                                   else if (((n) < 0) and (mg_engine_prints_karma == false)) then display_msg(message_str(SCRIPT_MEGATON, MG_MSG_KARMA_LOSS) + (0 - (n)) + message_str(SCRIPT_MEGATON, MG_MSG_KARMA_AFTER)))
#define mg_town_rep             global_var(GVAR_TOWN_REP_MEGATON)                                        // standing in Megaton (character screen)
#define mg_add_town_rep(n)      set_global_var(GVAR_TOWN_REP_MEGATON, global_var(GVAR_TOWN_REP_MEGATON) + (n))     // change town reputation by n
// statement: award experience and say so in the message window ("You gain 100 experience points.")
#define mg_give_xp(n)           one_statement(give_exp_points(n); display_msg(message_str(SCRIPT_MEGATON, MG_MSG_XP_BEFORE) + (n) + message_str(SCRIPT_MEGATON, MG_MSG_XP_AFTER)))
// statement: the usual end of a quest step: experience (announced), karma and town reputation in one go
#define mg_reward(xp, karma, rep)   one_statement(mg_give_xp(xp); mg_add_karma(karma); mg_add_town_rep(rep))

/* ------------------------------------------------------------------- money */

#define mg_dude_caps            item_caps_total(dude_obj)                      // money the player carries
#define mg_dude_has_caps(n)     (item_caps_total(dude_obj) >= (n))             // true when the player can pay n
#define mg_take_caps(n)         item_caps_adjust(dude_obj, 0 - (n))            // remove n from the player (does nothing if he has less: test first)
#define mg_give_caps(n)         item_caps_adjust(dude_obj, n)                  // hand the player n (created; no purse is debited)
// statement: the player pays n into who's purse (a merchant's barter money grows by it); test mg_dude_has_caps first
#define mg_pay(who, n)          one_statement(item_caps_adjust(dude_obj, 0 - (n)); item_caps_adjust(who, n))

/* -------------------------------------------------------------------- time */

#define mg_day                  (game_time / TICKS_PER_DAY)                    // whole game days since the game began (0 on the first day)
#define mg_days_since(day)      ((game_time / TICKS_PER_DAY) - (day))          // days passed since a stored mg_day value
#define mg_hour                 (game_time_hour / 100)                         // hour of the day, 0..23
// a new game starts at tick 302400 (08:24 of day 0, scripts.cc); the map script's first map_enter
// before this tick means the game began in Megaton, not at the Temple of Trials
#define MG_NEW_GAME_TICKS       (302400 + 3000)

/* ---------------------------------------------------------- teams and AI */

/* Combat teams. The engine makes a critter go after whoever hit it, hit one of
   its team, or was hit by one of its team (combat_ai.cc): one team for the whole
   town means citizens never fight each other and always back each other up.
   The player's party is team 0. Stock scripts assign teams 0..210 (scan of all
   .int files), so these numbers belong to nobody a companion could bring along. */
#define TEAM_MG_TOWN            (230)     // every resident, the guards, the robot, the caravan outside
#define TEAM_MG_BURKE           (231)     // Mister Burke: nobody in town takes his side
#define TEAM_MG_HIRED           (232)     // Burke's hired guns
#define TEAM_MG_SILVER          (233)     // Silver, alone beyond the wall
#define TEAM_MG_ANIMAL          (234)     // brahmin and other livestock

/* AI packets (packet_num in data/ai.txt, all vanilla). */
#define AI_MG_CITIZEN           (14)      // "Peasants": fights back half-heartedly, runs when bleeding
#define AI_MG_TOUGH_CITIZEN     (24)      // "Tough Citizen": stands his ground, uses stimpaks
#define AI_MG_COWARD            (33)      // "Coward": runs at the first scratch (beggars, drunks, Gob)
#define AI_MG_CHILD             (15)      // "Child": never fights
#define AI_MG_MERCHANT          (17)      // "Store Owner"
#define AI_MG_DOCTOR            (19)      // "Doctor"
#define AI_MG_GUARD             (12)      // "Generic Guards": ranged first, careful with bursts (Simms, Stockholm, the mercenary)
#define AI_MG_ROBOT             (31)      // "Security Bot": never retreats (Deputy Weld)
#define AI_MG_BURKE             (128)     // "Mobsters"
#define AI_MG_HIRED_GUN         (136)     // "Merc Raider"
#define AI_MG_ANIMAL            (6)       // "Brahmin"

// statement: put self on a team with an AI packet. The map (cast/) already does this for placed
// critters; call it in map_enter_p_proc only for critters a script creates at run time.
#define mg_set_team_ai(team, ai)    one_statement(critter_add_trait(self_obj, TRAIT_OBJECT, OBJECT_TEAM_NUM, team); critter_add_trait(self_obj, TRAIT_OBJECT, OBJECT_AI_PACKET, ai))

/* ------------------------------------------------- the townsperson block */

/*
 * Standard behaviour of everybody who lives in Megaton. A script gets it by
 * calling one macro from each handler (it may do more in the same handler):
 *
 *     procedure critter_p_proc begin   mg_townsperson_critter;   end
 *     procedure combat_p_proc begin    mg_townsperson_combat;    end
 *     procedure damage_p_proc begin    mg_townsperson_damage;    end
 *     procedure destroy_p_proc begin   mg_townsperson_destroy;   end
 *     procedure pickup_p_proc begin    mg_townsperson_pickup;    end
 *     procedure talk_p_proc begin
 *        if (mg_is_hostile) then mg_hostile_bark;
 *        else talk(Node001);
 *     end
 *
 * Rules it implements:
 *   - The player wounding or killing a townsperson sets GVAR_MG_TOWN_HOSTILE:
 *     from then on everyone with the critter macro attacks on sight, after the
 *     warning described at mg_in_grace below. megaton.ssl lifts it on the first
 *     entry a week or more later and counts that amnesty in GVAR_MG_AMNESTY.
 *   - mg_make_hostile turns just this one person against the player (an insult,
 *     a second theft, a blow). Such a grudge lapses with the town's amnesty, or,
 *     in a town that stayed at peace, on the first entry a week after the last
 *     one began (megaton.ssl, GVAR_MG_GRUDGE_DAY). It may be called from a dialogue node:
 *     attack_complex() does nothing while a conversation is open, so the fight
 *     starts from the next critter_p_proc tick, after the dialogue has closed.
 *   - A personal grudge lapses with the town's. It is stamped with the number of
 *     amnesties so far (MG_LVAR_GRUDGE_ERA) and only counts while that number
 *     stands: otherwise the one settler the player once hit would open fire the
 *     moment a forgiven player walked back in, the player would defend himself,
 *     and the town would be hostile again for another week, every time.
 *     (Scripts that keep a grudge of their own read MG_LVAR_HOSTILE directly:
 *     Burke and Silver, who are not townspeople and never forgive.)
 *   - Caught stealing: a warning the first time, a fight the second.
 * Non-fighters (children, the beggar) leave out mg_townsperson_critter; their
 * AI packet makes them run once somebody else has started the fight.
 */
#define MG_LVAR_FREE            (12)      // script-owned local variables are 0 .. MG_LVAR_FREE - 1
#define MG_LVAR_GRUDGE_ERA      (12)      // GVAR_MG_AMNESTY when self's personal grudge began (mg_make_hostile)
#define MG_LVAR_SETUP           (13)      // 1 once the object's one-time setup is done (mg_needs_setup / mg_setup_done)
#define MG_LVAR_CAUGHT          (14)      // 1 once the player was caught stealing from self
#define MG_LVAR_HOSTILE         (15)      // 1 = self is the player's personal enemy

#define MG_KARMA_KILLED_CITIZEN (-15)     // karma for killing someone who lives here

#define mg_town_is_hostile      (global_var(GVAR_MG_TOWN_HOSTILE) != MG_TOWN_PEACEFUL)                    // true once the town has turned on the player
// statement: the whole town turns on the player (megaton.ssl forgives after a week away). The first time, the alarm's
// clock starts: for MG_GRACE_TICKS the town shouts before it shoots (below).
#define mg_town_turns_hostile   one_statement(if (global_var(GVAR_MG_TOWN_HOSTILE) == MG_TOWN_PEACEFUL) then set_global_var(GVAR_MG_HOSTILE_TICK, game_time); \
                                   set_global_var(GVAR_MG_TOWN_HOSTILE, MG_TOWN_IS_HOSTILE))
/* The warning. A hostile town used to open fire the instant it saw the player, and the sheriff's rifle
   killed a new arrival before his first turn. Now an alarm has a beginning, GVAR_MG_HOSTILE_TICK: the
   moment the town turned (mg_town_turns_hostile), and again every time the player walks into a town
   that is hostile already (megaton.ssl). For MG_GRACE_TICKS after it
     - outside combat, townspeople who see the player shout at him instead of attacking (mg_townsperson_critter);
     - in combat, a townsperson lets his turn pass (mg_townsperson_combat, in combat_p_proc).
   The grace is over at once for somebody the player has hurt himself (a personal grudge), and for the
   whole town with a second blow or a death (mg_end_grace). A variable set by hand in a test has no
   alarm tick and therefore no grace. */
#define MG_GRACE_TICKS          (105)     // ten seconds. In combat the clock moves five seconds at the top of every round:
                                          // the round of the first blow and the two after it are free, so the player
                                          // has two whole turns to get out of sight before anybody fires
#define mg_in_grace             ((game_time - global_var(GVAR_MG_HOSTILE_TICK)) < MG_GRACE_TICKS)
#define mg_start_grace          set_global_var(GVAR_MG_HOSTILE_TICK, game_time)                           // the alarm begins (again): megaton.ssl, on entering a hostile town
#define mg_end_grace            set_global_var(GVAR_MG_HOSTILE_TICK, game_time - MG_GRACE_TICKS)         // no more warnings
// true while self holds a personal grudge that no amnesty has wiped out since
#define mg_has_grudge           ((local_var(MG_LVAR_HOSTILE) == 1) and (local_var(MG_LVAR_GRUDGE_ERA) == global_var(GVAR_MG_AMNESTY)))
#define mg_is_hostile           ((global_var(GVAR_MG_TOWN_HOSTILE) != MG_TOWN_PEACEFUL) or mg_has_grudge)   // true when self wants the player dead
// statement: self alone turns on the player (safe inside dialogue)
#define mg_make_hostile         one_statement(set_local_var(MG_LVAR_HOSTILE, 1); set_local_var(MG_LVAR_GRUDGE_ERA, global_var(GVAR_MG_AMNESTY)); \
                                   set_global_var(GVAR_MG_GRUDGE_DAY, mg_day + 1))
#define mg_forgive              set_local_var(MG_LVAR_HOSTILE, 0)                                         // self drops a personal grudge (not the town's)
// statement, in critter_p_proc: attack the player when hostile and able to see him; while the alarm is young, shout
// instead (one of the MG_MSG_WARN lines, picked by where self stands so a crowd does not speak in chorus; only in
// the alarm's first three seconds, so the line is not written over itself for the whole grace)
#define mg_townsperson_critter  mg_block(if (mg_is_hostile) then begin if (obj_can_see_obj(self_obj, dude_obj)) then begin \
                                    if (mg_has_grudge or (mg_in_grace == false)) then attack_complex(dude_obj, 0, 1, 0, 0, 30000, 0, 0); \
                                    else if ((game_time - global_var(GVAR_MG_HOSTILE_TICK)) < 30) then \
                                       float_msg(self_obj, message_str(SCRIPT_MEGATON, MG_MSG_WARN_FIRST + ((tile_num(self_obj) + global_var(GVAR_MG_HOSTILE_TICK)) % MG_MSG_WARN_COUNT)), FLOAT_MSG_RED); \
                                 end end)
// statement, in combat_p_proc: while the alarm is young self lets the turn pass,
// unless the player has hurt him personally (script_overrides in a combat turn = the engine skips the AI)
#define mg_townsperson_combat   mg_block(if (fixed_param == COMBAT_SUBTYPE_TURN) then begin \
                                    if (mg_town_is_hostile and mg_in_grace and (mg_has_grudge == false)) then script_overrides; \
                                 end)
// statement, in damage_p_proc: hurt by the player -> personal enemy and the town turns hostile; a blow struck at a
// town that is hostile already ends its patience
#define mg_townsperson_damage   mg_block(if (source_obj == dude_obj) then begin mg_make_hostile; \
                                    if (mg_town_is_hostile) then mg_end_grace; else mg_town_turns_hostile; end)
// statement, in destroy_p_proc: killed by the player -> town hostile, no warnings, karma loss
#define mg_townsperson_destroy  mg_block(if (source_obj == dude_obj) then begin mg_town_turns_hostile; mg_end_grace; mg_add_karma(MG_KARMA_KILLED_CITIZEN); end)
// statement, in pickup_p_proc: caught stealing by a living self -> warning float and -2 reputation once, then a fight.
// (pickup_p_proc also runs when a corpse is looted, hence the nested test for self being alive.)
#define mg_townsperson_pickup   mg_block(if (source_obj == dude_obj) then begin if (self_is_alive) then begin \
                                    if (local_var(MG_LVAR_CAUGHT) != 1) then begin \
                                       set_local_var(MG_LVAR_CAUGHT, 1); \
                                       mg_add_town_rep(-2); \
                                       float_msg(self_obj, message_str(SCRIPT_MEGATON, random(MG_MSG_THIEF_FIRST, MG_MSG_THIEF_LAST)), FLOAT_MSG_RED); \
                                    end else mg_make_hostile; \
                                 end end)
// statement: what a hostile townsperson shouts instead of talking (use in talk_p_proc)
#define mg_hostile_bark         float_msg(self_obj, message_str(SCRIPT_MEGATON, random(MG_MSG_HOSTILE_FIRST, MG_MSG_HOSTILE_LAST)), FLOAT_MSG_RED)
// One-time setup of an object (map_enter_p_proc runs on every visit and after every load):
//     if (mg_needs_setup) then begin mg_setup_done; ... end
#define mg_needs_setup          (local_var(MG_LVAR_SETUP) != 1)               // true until mg_setup_done ran for this object
#define mg_setup_done           set_local_var(MG_LVAR_SETUP, 1)               // remember that the one-time setup happened

/* ------------------------------------------------------------- world map */

// put the party marker on Megaton's circle (the party starts on Arroyo's when a new game begins here)
#define mg_fix_world_position   set_world_map_pos(MEGATON_WORLD_X, MEGATON_WORLD_Y)
// statement: make sure the town shows on the world map with its name (never downgrades "visited")
#define mg_reveal_megaton       one_statement(if (metarule(METARULE_AREA_KNOWN, AREA_MEGATON) == 0) then mark_area_known(MARK_TYPE_TOWN, AREA_MEGATON, MARK_STATE_KNOWN))
// remove the town from the world map for good (after the blast)
#define mg_erase_megaton        mark_area_known(MARK_TYPE_TOWN, AREA_MEGATON, MARK_STATE_INVISIBLE)

/* ------------------------------------------------- shared lines (megaton.msg) */

#define MG_MSG_XP_BEFORE        (900)     // "You gain "
#define MG_MSG_XP_AFTER         (901)     // " experience points."
#define MG_MSG_KARMA_GAIN       (902)     // "You gain "            (mg_add_karma)
#define MG_MSG_KARMA_LOSS       (903)     // "You lose "
#define MG_MSG_KARMA_AFTER      (904)     // " karma."
#define MG_MSG_THIEF_FIRST      (910)     // 910..914: floats of someone who caught the player stealing
#define MG_MSG_THIEF_LAST       (914)
#define MG_MSG_HOSTILE_FIRST    (920)     // 920..924: shouts of a hostile townsperson
#define MG_MSG_HOSTILE_LAST     (924)
#define MG_MSG_WARN_FIRST       (930)     // 930..934: what a hostile town shouts before it shoots (mg_townsperson_critter)
#define MG_MSG_WARN_COUNT       (5)

#endif /* MEGATON_H */
