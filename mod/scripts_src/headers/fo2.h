// SPDX-License-Identifier: LicenseRef-Sustainable-Use
/*
 * fo2.h - constants and helper macros for Fallout 2 scripts run by fallout2-ce.
 *
 * Values and behaviour are taken from fallout2-ce's source. Identifier names
 * follow the conventional names of Fallout 2 script headers, so that scripts
 * stay portable. Engine references: scripts.h, obj_types.h, proto_types.h,
 * stat_defs.h, skill_defs.h, perk_defs.h, trait_defs.h, animation.h, random.h,
 * interpreter_extra.cc.
 * Prototype ids (pids.h) and global variable names (gvars.h) are generated from
 * the game data by tools/gen_pid_header.py. Compile with tools/ssl.py, which
 * puts this directory on the include path.
 *
 * A script that uses the text or dialogue macros must define its own 1-based
 * line number in scripts/scripts.lst:
 *     #define NAME (1304)
 * The macros then read text/english/dialog/<scripts.lst name>.msg.
 *
 * Engine rules that shape every script (verified in fallout2-ce, see samples/):
 *   - Declare `procedure start;` before any other procedure and keep its body
 *     empty. The engine calls procedure #1 for EVERY event the script has no
 *     handler for (e.g. every critter tick of an NPC without critter_p_proc) and
 *     calls `start` itself twice when a script is first loaded with the map.
 *     Do one-time setup in map_enter_p_proc, guarded by a local variable.
 *   - Dialogue option targets must be procedure names (compiled to procedure
 *     numbers); a string is silently ignored. 0 (DIALOG_END) ends the talk.
 *   - local_var() returns -1 and set_local_var() does nothing unless the script's
 *     scripts.lst line says `# local_vars=N` with N > highest index used. Map
 *     scripts cannot use local variables at all: use map_var(), and keep the
 *     number of map variables equal in the .map header and maps/<map>.gam.
 *   - Reading an `import variable` nobody exported is a fatal script error; the
 *     map script (loaded first) is the place to export.
 *   - A function that returns nothing useful may still not be usable as an
 *     expression, and vice versa (destroy_mult_objs is expression-only,
 *     critter_mod_skill statement-only); the compiler says which.
 *   - Script-level `variable`s are not saved and are reset whenever the script
 *     is reloaded; anything that must survive goes into local/map/global vars.
 *   - set_critter_stat() ADDS its value and, like critter_mod_skill(), only
 *     works on dude_obj. create_object_sid() takes a 1-based script number.
 *   - Opcodes fallout2-ce does not implement kill the script instance
 *     (tools/ssl.py warns about them).
 */
#ifndef FO2_H
#define FO2_H

#include "pids.h"
#include "gvars.h"

/* ------------------------------------------------------------------ basics */

/* `true` and `false` are built into the compiler. */
#define NO_SCRIPT               (-1)      // create_object_sid(): attach no script

/*
 * Several statements as ONE statement. A macro that expands to `a; b` breaks
 * silently after `then`, `else` or `do` (only `a` becomes conditional), and the
 * language has no `begin ... end;`. The else branch is never taken: it only
 * absorbs the semicolon the caller writes after the macro. -O2 removes the test.
 */
#define one_statement(statements)   if (true) then begin statements; end else return

/* script_action values = the event being handled (ScriptProc, src/scripts.h). */
#define ACTION_START            (1)
#define ACTION_SPATIAL          (2)
#define ACTION_DESCRIPTION      (3)
#define ACTION_PICKUP           (4)
#define ACTION_DROP             (5)
#define ACTION_USE              (6)
#define ACTION_USE_OBJ_ON       (7)
#define ACTION_USE_SKILL_ON     (8)
#define ACTION_TALK             (11)
#define ACTION_CRITTER          (12)
#define ACTION_COMBAT           (13)
#define ACTION_DAMAGE           (14)
#define ACTION_MAP_ENTER        (15)
#define ACTION_MAP_EXIT         (16)
#define ACTION_DESTROY          (18)
#define ACTION_LOOK_AT          (21)
#define ACTION_TIMED_EVENT      (22)
#define ACTION_MAP_UPDATE       (23)
#define ACTION_PUSH             (24)
#define ACTION_IS_DROPPING      (25)

/* Game time. The unit of game_time and add_timer_event() is the tick (1/10 s). */
#define TICKS_PER_SECOND        (10)
#define TICKS_PER_MINUTE        (600)
#define TICKS_PER_HOUR          (36000)
#define TICKS_PER_DAY           (864000)
#define seconds(n)              ((n) * TICKS_PER_SECOND)   // n game seconds in ticks
#define minutes(n)              ((n) * TICKS_PER_MINUTE)   // n game minutes in ticks
#define hours(n)                ((n) * TICKS_PER_HOUR)     // n game hours in ticks
#define days(n)                 ((n) * TICKS_PER_DAY)      // n game days in ticks
// game_time_hour is the clock as HHMM (e.g. 1430); these test the time of day
#define is_night                ((game_time_hour >= 1900) or (game_time_hour < 600))
#define is_day                  ((game_time_hour >= 600) and (game_time_hour < 1900))

/* Hex grid: tile = y * 200 + x, six directions for tile_num_in_direction() / rotation. */
#define DIR_NE                  (0)
#define DIR_E                   (1)
#define DIR_SE                  (2)
#define DIR_SW                  (3)
#define DIR_W                   (4)
#define DIR_NW                  (5)

/* ----------------------------------------------------------------- objects */

/* obj_type(obj) (also the high byte of a PID). */
#define OBJ_TYPE_ITEM           (0)
#define OBJ_TYPE_CRITTER        (1)
#define OBJ_TYPE_SCENERY        (2)
#define OBJ_TYPE_WALL           (3)
#define OBJ_TYPE_TILE           (4)
#define OBJ_TYPE_MISC           (5)

/* obj_item_subtype(obj) for items. */
#define ITEM_TYPE_ARMOR         (0)
#define ITEM_TYPE_CONTAINER     (1)
#define ITEM_TYPE_DRUG          (2)
#define ITEM_TYPE_WEAPON        (3)
#define ITEM_TYPE_AMMO          (4)
#define ITEM_TYPE_MISC          (5)
#define ITEM_TYPE_KEY           (6)

/* obj_item_subtype(obj) for scenery. */
#define SCENERY_TYPE_DOOR       (0)
#define SCENERY_TYPE_STAIRS     (1)
#define SCENERY_TYPE_ELEVATOR   (2)
#define SCENERY_TYPE_LADDER_UP  (3)
#define SCENERY_TYPE_LADDER_DOWN (4)
#define SCENERY_TYPE_GENERIC    (5)

#define self_tile               tile_num(self_obj)             // hex the script's object stands on
#define self_elevation          elevation(self_obj)            // its elevation (0..2)
#define self_pid                obj_pid(self_obj)              // its prototype id
#define self_name               obj_name(self_obj)             // its display name
#define dude_tile               tile_num(dude_obj)             // hex of the player
#define dude_elevation          elevation(dude_obj)            // elevation of the player
#define is_dude(obj)            ((obj) == dude_obj)            // true when obj is the player
#define is_critter(obj)         (obj_type(obj) == OBJ_TYPE_CRITTER)
#define is_item(obj)            (obj_type(obj) == OBJ_TYPE_ITEM)
#define distance_to_dude        tile_distance_objs(self_obj, dude_obj)   // hexes between self and the player
#define sees_dude               obj_can_see_obj(self_obj, dude_obj)      // line of sight + perception check

#define create_object(pid, tile, elev)        create_object_sid(pid, tile, elev, NO_SCRIPT)  // spawn an unscripted object
#define hide_object(obj)        set_obj_visibility(obj, 1)     // make invisible and passable
#define show_object(obj)        set_obj_visibility(obj, 0)     // make visible again
#define face_dude               anim(self_obj, ANIMATE_ROTATION, rotation_to_tile(self_tile, dude_tile))  // turn self towards the player
#define face_direction(obj, dir) anim(obj, ANIMATE_ROTATION, dir)   // set an object's rotation (DIR_*)
#define set_frame(obj, frame)   anim(obj, ANIMATE_SET_FRAME, frame) // show a fixed frame of the object's art

/* Doors and containers. obj_lock/obj_unlock/obj_open/obj_close work on both. */
#define is_locked(obj)          obj_is_locked(obj)
#define is_open(obj)            obj_is_open(obj)
#define self_is_locked          obj_is_locked(self_obj)
#define self_is_open            obj_is_open(self_obj)

/* --------------------------------------------------------------- inventory */

/* critter_inven_obj(who, slot). */
#define INVEN_TYPE_WORN         (0)
#define INVEN_TYPE_RIGHT_HAND   (1)
#define INVEN_TYPE_LEFT_HAND    (2)
#define INVEN_TYPE_INV_COUNT    (-2)

#define armor_of(who)           critter_inven_obj(who, INVEN_TYPE_WORN)        // worn armor object or 0
#define right_hand_of(who)      critter_inven_obj(who, INVEN_TYPE_RIGHT_HAND)  // item in the right hand or 0
#define left_hand_of(who)       critter_inven_obj(who, INVEN_TYPE_LEFT_HAND)   // item in the left hand or 0
#define inven_count(who)        critter_inven_obj(who, INVEN_TYPE_INV_COUNT)   // number of inventory stacks
#define inven_item(who, index)  inven_cmds(who, 13, index)                     // inventory stack by index (0..count-1)

#define has_item(who, pid)      (obj_is_carrying_obj_pid(who, pid) > 0)        // true when who carries at least one
#define item_count(who, pid)    obj_is_carrying_obj_pid(who, pid)              // how many of pid who carries
#define item_of(who, pid)       obj_carrying_pid_obj(who, pid)                 // the carried object of that pid or 0
#define give_item(who, pid)     add_obj_to_inven(who, create_object(pid, 0, 0))                  // put one new pid into who's inventory
#define give_items(who, pid, n) add_mult_objs_to_inven(who, create_object(pid, 0, 0), n)         // put n new pids into who's inventory
// expression: destroy up to n of pid in who's inventory and return how many went (who must carry at least one):
//    if (has_item(dude_obj, PID_ROPE)) then gone := take_items(dude_obj, PID_ROPE, 1);
#define take_items(who, pid, n) destroy_mult_objs(obj_carrying_pid_obj(who, pid), n)
// statement: destroy the whole stack of pid in who's inventory; does nothing when who has none
#define take_all(who, pid)      one_statement(if (has_item(who, pid)) then destroy_object(obj_carrying_pid_obj(who, pid)))
#define caps_of(who)            item_caps_total(who)                           // money carried
#define give_caps(who, n)       item_caps_adjust(who, n)                       // add (or with negative n remove) money
#define give_xp(n)              give_exp_points(n)                             // award experience to the player

/* ------------------------------------------------------- stats and skills */

/* get_critter_stat(who, stat) / do_check(who, stat, mod); do_check only takes the first seven. */
#define STAT_STRENGTH           (0)
#define STAT_PERCEPTION         (1)
#define STAT_ENDURANCE          (2)
#define STAT_CHARISMA           (3)
#define STAT_INTELLIGENCE       (4)
#define STAT_AGILITY            (5)
#define STAT_LUCK               (6)
#define STAT_MAX_HP             (7)
#define STAT_MAX_AP             (8)
#define STAT_ARMOR_CLASS        (9)
#define STAT_UNARMED_DAMAGE     (10)
#define STAT_MELEE_DAMAGE       (11)
#define STAT_CARRY_WEIGHT       (12)
#define STAT_SEQUENCE           (13)
#define STAT_HEALING_RATE       (14)
#define STAT_CRITICAL_CHANCE    (15)
#define STAT_BETTER_CRITICALS   (16)
#define STAT_DT_NORMAL          (17)      // damage thresholds 17..23 in DMG_* order
#define STAT_DR_NORMAL          (24)      // damage resistances 24..30 in DMG_* order
#define STAT_RADIATION_RESIST   (31)
#define STAT_POISON_RESIST      (32)
#define STAT_AGE                (33)
#define STAT_GENDER             (34)      // GENDER_*
#define STAT_CURRENT_HP         (35)
#define STAT_CURRENT_POISON     (36)
#define STAT_CURRENT_RADIATION  (37)

#define GENDER_MALE             (0)
#define GENDER_FEMALE           (1)

/* get_pc_stat(pcstat). */
#define PCSTAT_UNSPENT_SKILL_POINTS (0)
#define PCSTAT_LEVEL            (1)
#define PCSTAT_EXPERIENCE       (2)
#define PCSTAT_REPUTATION       (3)
#define PCSTAT_KARMA            (4)

/* has_skill(who, skill) / roll_vs_skill(who, skill, mod) / action_being_used. */
#define SKILL_SMALL_GUNS        (0)
#define SKILL_BIG_GUNS          (1)
#define SKILL_ENERGY_WEAPONS    (2)
#define SKILL_UNARMED           (3)
#define SKILL_MELEE_WEAPONS     (4)
#define SKILL_THROWING          (5)
#define SKILL_FIRST_AID         (6)
#define SKILL_DOCTOR            (7)
#define SKILL_SNEAK             (8)
#define SKILL_LOCKPICK          (9)
#define SKILL_STEAL             (10)
#define SKILL_TRAPS             (11)
#define SKILL_SCIENCE           (12)
#define SKILL_REPAIR            (13)
#define SKILL_SPEECH            (14)
#define SKILL_BARTER            (15)
#define SKILL_GAMBLING          (16)
#define SKILL_OUTDOORSMAN       (17)

/* Results of roll_vs_skill() and do_check(); test them with is_success() / is_critical().
   The engine only upgrades a roll to a critical from the second game day on (random.cc),
   so on day one a critical-failure branch never runs. */
#define ROLL_CRITICAL_FAILURE   (0)
#define ROLL_FAILURE            (1)
#define ROLL_SUCCESS            (2)
#define ROLL_CRITICAL_SUCCESS   (3)

#define stat_of(who, stat)      get_critter_stat(who, stat)                    // current value of a STAT_*
#define dude_stat(stat)         get_critter_stat(dude_obj, stat)
#define dude_iq                 get_critter_stat(dude_obj, STAT_INTELLIGENCE)
#define dude_is_male            (get_critter_stat(dude_obj, STAT_GENDER) == GENDER_MALE)
#define dude_level              get_pc_stat(PCSTAT_LEVEL)
#define skill_of(who, skill)    has_skill(who, skill)                          // skill level in percent
// d100 roll against skill + bonus (the best party member's skill counts for the player): true on success
#define skill_check(who, skill, bonus)      is_success(roll_vs_skill(who, skill, bonus))
#define dude_skill_check(skill, bonus)      is_success(roll_vs_skill(dude_obj, skill, bonus))
// d10 roll against a primary stat + bonus: true on success
#define stat_check(who, stat, bonus)        is_success(do_check(who, stat, bonus))
#define dude_stat_check(stat, bonus)        is_success(do_check(dude_obj, stat, bonus))
#define skill_is_tagged(skill)  metarule(METARULE_SKILL_CHECK_TAG, skill)      // true when the player tagged the skill
#define dude_is_sneaking        using_skill(dude_obj, SKILL_SNEAK)             // only this combination is implemented

/* has_trait(type, who, id) / critter_add_trait(who, type, id, value). */
#define TRAIT_PERK              (0)       // id = PERK_*, value = rank
#define TRAIT_OBJECT            (1)       // id = OBJECT_* below
#define TRAIT_TRAIT             (2)       // id = TRAIT_* (player only, read only)
#define OBJECT_AI_PACKET        (5)
#define OBJECT_TEAM_NUM         (6)
#define OBJECT_CUR_ROT          (10)
#define OBJECT_VISIBILITY       (666)     // 1 when the object is visible
#define OBJECT_CUR_WEIGHT       (669)     // weight of the carried inventory

#define has_perk(who, perk)     has_trait(TRAIT_PERK, who, perk)               // rank of a PERK_* (0 = none)
#define dude_has_trait(trait)   has_trait(TRAIT_TRAIT, dude_obj, trait)        // true when the player picked a TRAIT_*
#define team_of(who)            has_trait(TRAIT_OBJECT, who, OBJECT_TEAM_NUM)  // combat team number
#define ai_of(who)              has_trait(TRAIT_OBJECT, who, OBJECT_AI_PACKET) // AI packet number (data/ai.txt)
#define rotation_of(obj)        has_trait(TRAIT_OBJECT, obj, OBJECT_CUR_ROT)   // facing, DIR_*
#define is_visible(obj)         has_trait(TRAIT_OBJECT, obj, OBJECT_VISIBILITY)
#define set_team(who, team)     critter_add_trait(who, TRAIT_OBJECT, OBJECT_TEAM_NUM, team)   // change combat team
#define set_ai(who, packet)     critter_add_trait(who, TRAIT_OBJECT, OBJECT_AI_PACKET, packet) // change AI packet
#define TEAM_PLAYER             (0)       // the player's team; other numbers are per-map conventions

/* Perks (perk_defs.h) most likely to matter in dialogue and checks. */
#define PERK_AWARENESS          (0)
#define PERK_PRESENCE           (10)
#define PERK_EDUCATED           (18)
#define PERK_HEALER             (19)
#define PERK_EMPATHY            (22)
#define PERK_MR_FIXIT           (31)
#define PERK_MEDIC              (32)
#define PERK_MASTER_THIEF       (33)
#define PERK_SPEAKER            (34)
#define PERK_CULT_OF_PERSONALITY (39)
#define PERK_SCROUNGER          (40)
#define PERK_ANIMAL_FRIEND      (44)
#define PERK_SMOOTH_TALKER      (49)      // each rank counts as +1 INT for dialogue options
#define PERK_DEMOLITION_EXPERT  (82)
#define PERK_HARMLESS           (91)
#define PERK_KARMA_BEACON       (95)
#define PERK_MAGNETIC_PERSONALITY (98)
#define PERK_NEGOTIATOR         (99)
#define PERK_SALESMAN           (103)
#define PERK_THIEF              (105)

/* Traits (trait_defs.h). */
#define TRAIT_FAST_METABOLISM   (0)
#define TRAIT_BRUISER           (1)
#define TRAIT_SMALL_FRAME       (2)
#define TRAIT_ONE_HANDER        (3)
#define TRAIT_FINESSE           (4)
#define TRAIT_KAMIKAZE          (5)
#define TRAIT_HEAVY_HANDED      (6)
#define TRAIT_FAST_SHOT         (7)
#define TRAIT_BLOODY_MESS       (8)
#define TRAIT_JINXED            (9)
#define TRAIT_GOOD_NATURED      (10)
#define TRAIT_CHEM_RELIANT      (11)
#define TRAIT_CHEM_RESISTANT    (12)
#define TRAIT_SEX_APPEAL        (13)
#define TRAIT_SKILLED           (14)
#define TRAIT_GIFTED            (15)

/* ------------------------------------------------- critters and combat */

/* critter_state(who): 0 normal, bit 0 dead, bit 1 knocked out/prone; DAM_CRIP_* bits may be set too. */
#define CRITTER_IS_NORMAL       (0)
#define CRITTER_IS_DEAD         (1)
#define CRITTER_IS_PRONE        (2)
#define is_dead(who)            ((critter_state(who) bwand CRITTER_IS_DEAD) != 0)
#define is_knocked_out(who)     ((critter_state(who) bwand CRITTER_IS_PRONE) != 0)
#define self_is_alive           ((critter_state(self_obj) bwand CRITTER_IS_DEAD) == 0)

/* Damage types for critter_dmg(who, amount, type); OR in the flags. */
#define DMG_NORMAL              (0)
#define DMG_LASER               (1)
#define DMG_FIRE                (2)
#define DMG_PLASMA              (3)
#define DMG_ELECTRICAL          (4)
#define DMG_EMP                 (5)
#define DMG_EXPLOSION           (6)
#define DMG_BYPASS_ARMOR        (256)     // flag: ignore armor
#define DMG_NO_ANIMATE          (512)     // flag: no hit animation

/* Injury bits for critter_injure(who, bits) and the result arguments of attack_complex(). */
#define DAM_KNOCKED_OUT         (1)
#define DAM_KNOCKED_DOWN        (2)
#define DAM_CRIP_LEG_LEFT       (4)
#define DAM_CRIP_LEG_RIGHT      (8)
#define DAM_CRIP_ARM_LEFT       (16)
#define DAM_CRIP_ARM_RIGHT      (32)
#define DAM_BLIND               (64)
#define DAM_DEAD                (128)
#define DAM_PERFORM_REVERSE     (8388608) // critter_injure(): clear the given bits instead of setting them

// make self attack who; only valid in the attacker's own script. Silently ignored while a
// conversation is open, i.e. anywhere in talk_p_proc and its nodes: set a flag there and
// attack from critter_p_proc (samples: tests/tvquest.ssl)
#define start_attack(who)       attack_complex(who, 0, 1, 0, 0, 30000, 0, 0)
#define heal(who, amount)       critter_heal(who, amount)
#define kill(who)               kill_critter(who, ANIM_FALL_BACK_SF)           // kill with the plain fall-back corpse

/* fixed_param in combat_p_proc (the values fallout2-ce actually sends). */
#define COMBAT_SUBTYPE_HIT_SUCCEEDED (2)  // self has just hit its target
#define COMBAT_SUBTYPE_TURN     (4)       // self's turn in the combat sequence begins
#define COMBAT_SUBTYPE_NONCOM_TURN (5)    // turn of a critter that is not fighting

/* -------------------------------------------------------------- animation */

/* anim(obj, anim, arg) and reg_anim_animate(obj, anim, delay) (AnimationType, src/animation.h). */
#define ANIM_STAND              (0)
#define ANIM_WALK               (1)
#define ANIM_CLIMB_LADDER       (4)
#define ANIM_MAGIC_HANDS_GROUND (10)
#define ANIM_MAGIC_HANDS_MIDDLE (11)
#define ANIM_MAGIC_HANDS_UP     (12)
#define ANIM_DODGE              (13)
#define ANIM_HIT_FROM_FRONT     (14)
#define ANIM_HIT_FROM_BACK      (15)
#define ANIM_THROW_PUNCH        (16)
#define ANIM_KICK_LEG           (17)
#define ANIM_THROW              (18)
#define ANIM_RUNNING            (19)
#define ANIM_FALL_BACK          (20)
#define ANIM_FALL_FRONT         (21)
#define ANIM_PRONE_TO_STANDING  (36)
#define ANIM_BACK_TO_STANDING   (37)
#define ANIM_FALL_BACK_SF       (48)      // single frame: lying on the back
#define ANIM_FALL_FRONT_SF      (49)      // single frame: lying face down
#define ANIM_FALL_BACK_BLOOD_SF (62)
#define ANIM_FALL_FRONT_BLOOD_SF (63)
#define ANIMATE_ROTATION        (1000)    // anim(): arg = DIR_*, turns the object
#define ANIMATE_SET_FRAME       (1010)    // anim(): arg = frame number

/* reg_anim_func(cmd, arg) brackets a sequence of reg_anim_* calls. */
#define REG_ANIM_BEGIN          (1)
#define REG_ANIM_CLEAR          (2)       // arg = object whose pending animations are dropped
#define REG_ANIM_END            (3)
#define ANIM_SEQ_UNRESERVED     (1)       // arg of REG_ANIM_BEGIN: may be interrupted
#define ANIM_SEQ_RESERVED       (2)       // arg of REG_ANIM_BEGIN: may not be interrupted

#define anim_begin              reg_anim_func(REG_ANIM_BEGIN, ANIM_SEQ_UNRESERVED)
#define anim_end                reg_anim_func(REG_ANIM_END, 0)
#define anim_clear(obj)         reg_anim_func(REG_ANIM_CLEAR, obj)
// walk / run self to a hex (animate_move_obj_to_tile: flag 0 walk, 1 run; +16 = drop queued animations first)
#define walk_to(tile)           animate_move_obj_to_tile(self_obj, tile, 0)
#define run_to(tile)            animate_move_obj_to_tile(self_obj, tile, 1)

/* ------------------------------------------------------------------- text */

/* float_msg(who, text, color). */
#define FLOAT_MSG_WARNING       (-2)      // big red text, also recentres the view on the player
#define FLOAT_MSG_SEQUENTIAL    (-1)      // cycles through the colors
#define FLOAT_MSG_NORMAL        (0)       // yellow
#define FLOAT_MSG_BLACK         (1)
#define FLOAT_MSG_RED           (2)
#define FLOAT_MSG_GREEN         (3)
#define FLOAT_MSG_BLUE          (4)
#define FLOAT_MSG_PURPLE        (5)
#define FLOAT_MSG_NEAR_WHITE    (6)
#define FLOAT_MSG_LIGHT_RED     (7)
#define FLOAT_MSG_YELLOW        (8)
#define FLOAT_MSG_WHITE         (9)
#define FLOAT_MSG_GREY          (10)
#define FLOAT_MSG_DARK_GREY     (11)
#define FLOAT_MSG_LIGHT_GREY    (12)

#define mstr(id)                message_str(NAME, id)                          // line {id} of this script's .msg file
#define mstr_of(script, id)     message_str(script, id)                        // line {id} of another script's .msg file
#define show(id)                display_msg(message_str(NAME, id))             // print line {id} in the message window
#define show_text(text)         display_msg(text)                              // print any string in the message window
#define floater(id)             float_msg(self_obj, message_str(NAME, id), FLOAT_MSG_NORMAL)       // line {id} floats over self
#define floater_color(id, color) float_msg(self_obj, message_str(NAME, id), color)                 // ... in a FLOAT_MSG_* color
#define floater_on(who, id, color) float_msg(who, message_str(NAME, id), color)                    // ... over another object
#define floater_random(first, last) float_msg(self_obj, message_str(NAME, random(first, last)), FLOAT_MSG_NORMAL)  // one of lines first..last
#define float_text(who, text)   float_msg(who, text, FLOAT_MSG_NORMAL)         // any string floats over who
#define clear_floater(who)      float_msg(who, "", FLOAT_MSG_NORMAL)           // remove who's floating text
#define debug(text)             debug_msg("" + text + "\n")                    // line in debug.log ([debug] mode=log)

/* --------------------------------------------------------------- dialogue */

/* Reaction an option causes (also drives the Empathy perk colors). */
#define REACTION_GOOD           (49)
#define REACTION_NEUTRAL        (50)
#define REACTION_BAD            (51)

#define LOW_IQ                  (-3)      // giq_option: negative iq = only shown when INT <= -iq
#define DIALOG_END              (0)       // option target that just ends the conversation
#define MOOD_NEUTRAL            (4)       // start_gdialog mood; only matters for talking heads

/*
 * Run a conversation from talk_p_proc, starting at procedure `node`. Each node
 * calls Reply() once and adds options; picking an option calls its procedure. A
 * node that adds no option ends the conversation. Statement macro: `talk(Node1);`
 */
#define talk(node)              one_statement(start_gdialog(NAME, self_obj, MOOD_NEUTRAL, -1, -1); gsay_start; call node; gsay_end; end_dialogue)
// same with a talking head: head = line number in art/heads/heads.lst, background = art/backgrnd line
#define talk_head(node, head, background)  one_statement(start_gdialog(NAME, self_obj, MOOD_NEUTRAL, head, background); gsay_start; call node; gsay_end; end_dialogue)

#define Reply(id)               gsay_reply(NAME, id)                           // NPC says line {id}
#define ReplyText(text)         gsay_reply(NAME, text)                         // NPC says a computed string
// player option {id} leading to `node`, shown when INT >= iq (NOption neutral, GOption good, BOption bad reaction)
#define NOption(id, node, iq)   giq_option(iq, NAME, id, node, REACTION_NEUTRAL)
#define GOption(id, node, iq)   giq_option(iq, NAME, id, node, REACTION_GOOD)
#define BOption(id, node, iq)   giq_option(iq, NAME, id, node, REACTION_BAD)
// option only a low-intelligence player (INT <= 3) gets
#define NLowOption(id, node)    giq_option(LOW_IQ, NAME, id, node, REACTION_NEUTRAL)
#define GLowOption(id, node)    giq_option(LOW_IQ, NAME, id, node, REACTION_GOOD)
#define BLowOption(id, node)    giq_option(LOW_IQ, NAME, id, node, REACTION_BAD)
// option with a computed string as its text
#define NOptionText(text, node, iq) giq_option(iq, NAME, text, node, REACTION_NEUTRAL)
// option {id} that ends the conversation
#define EndOption(id, iq)       giq_option(iq, NAME, id, DIALOG_END, REACTION_NEUTRAL)
// NPC says line {id}; the player can only acknowledge it, then the node continues
#define NMessage(id)            gsay_message(NAME, id, REACTION_NEUTRAL)
#define GMessage(id)            gsay_message(NAME, id, REACTION_GOOD)
#define BMessage(id)            gsay_message(NAME, id, REACTION_BAD)
#define barter                  gdialog_mod_barter(0)                          // open the barter screen from a node (critter needs the barter flag)

/* -------------------------------------------------------------- variables */

#define lvar(index)             local_var(index)
#define set_lvar(index, value)  set_local_var(index, value)
#define mvar(index)             map_var(index)
#define set_mvar(index, value)  set_map_var(index, value)
#define gvar(index)             global_var(index)
#define set_gvar(index, value)  set_global_var(index, value)
#define inc_lvar(index)         set_local_var(index, local_var(index) + 1)
#define inc_mvar(index)         set_map_var(index, map_var(index) + 1)
#define inc_gvar(index)         set_global_var(index, global_var(index) + 1)
// GVAR 634..692 are unused "reserved" slots of the stock game: free for mods without touching vault13.gam
#define GVAR_MOD_FIRST          (634)
#define GVAR_MOD_LAST           (692)

/* ------------------------------------------------------------ timed events */

// timed_event_p_proc runs after `ticks` with fixed_param == param
#define timer(ticks, param)         add_timer_event(self_obj, ticks, param)
#define cancel_timers               rm_timer_event(self_obj)                   // drop all pending events of self
#define cancel_timer(param)         metarule3(METARULE3_CLR_FIXED_TIMED_EVENTS, self_obj, param, 0)  // drop the events with this param
#define restart_timer(ticks, param) one_statement(cancel_timer(param); timer(ticks, param))   // statement macro: at most one pending event per param

/* ----------------------------------------------------------- map and world */

/* metarule(rule, arg). */
#define METARULE_SIGNAL_END_GAME    (13)
#define METARULE_FIRST_RUN          (14)
#define METARULE_ELEVATOR           (15)
#define METARULE_PARTY_COUNT        (16)
#define METARULE_AREA_KNOWN         (17)
#define METARULE_WHO_ON_DRUGS       (18)
#define METARULE_MAP_KNOWN          (19)
#define METARULE_IS_LOADGAME        (22)
#define METARULE_CAR_CURRENT_TOWN   (30)
#define METARULE_SKILL_CHECK_TAG    (40)
#define METARULE_DROP_ALL_INVEN     (42)
#define METARULE_INVEN_UNWIELD_WHO  (43)
#define METARULE_GET_WORLDMAP_XPOS  (44)
#define METARULE_GET_WORLDMAP_YPOS  (45)
#define METARULE_CURRENT_TOWN       (46)
#define METARULE_VIOLENCE_FILTER    (48)
#define METARULE_WEAPON_DAMAGE_TYPE (49)
#define METARULE_CRITTER_BARTERS    (50)
#define METARULE_CRITTER_KILL_TYPE  (51)

/* metarule3(rule, a, b, c). */
#define METARULE3_CLR_FIXED_TIMED_EVENTS (100)
#define METARULE3_MARK_SUBTILE      (101)
#define METARULE3_GET_KILL_COUNT    (103)
#define METARULE3_MARK_MAP_ENTRANCE (104)
#define METARULE3_TILE_GET_NEXT_CRITTER (106)
#define METARULE3_ART_SET_BASE_FID_NUM (107)
#define METARULE3_TILE_SET_CENTER   (108)

#define map_first_run           metarule(METARULE_FIRST_RUN, 0)                // true until the map has been saved once (first visit)
#define is_loading_game         metarule(METARULE_IS_LOADGAME, 0)              // true while a savegame is being loaded
#define party_size              metarule(METARULE_PARTY_COUNT, 0)              // party members including the player
#define can_barter(who)         metarule(METARULE_CRITTER_BARTERS, who)        // true when the critter's proto has the barter flag
#define center_view(tile)       metarule3(METARULE3_TILE_SET_CENTER, tile, 0, 0)   // scroll the view to a hex
#define next_critter_on(tile, elev, after) metarule3(METARULE3_TILE_GET_NEXT_CRITTER, tile, elev, after)  // iterate critters on a hex (after = 0 first)

/* set_light_level(percent): ambient light, 100 = full daylight, 50 = cave, below 40 = night. */
#define LIGHT_DAY               (100)
#define LIGHT_DUSK              (70)
#define LIGHT_CAVE              (50)
#define LIGHT_NIGHT             (40)
// ambient light for the current time of day: night until 06:00, ramps up to 07:00, day, ramps down 18:00-19:00
// (game_time_hour is HHMM, so within one hour the difference is the minutes 0..59, hence / 60)
#define daylight_level          (LIGHT_NIGHT if (game_time_hour < 600 or game_time_hour >= 1900) else \
                                 ((LIGHT_NIGHT + (game_time_hour - 600) * (LIGHT_DAY - LIGHT_NIGHT) / 60) if (game_time_hour < 700) else \
                                 ((LIGHT_DAY - (game_time_hour - 1800) * (LIGHT_DAY - LIGHT_NIGHT) / 60) if (game_time_hour >= 1800) else LIGHT_DAY)))
#define apply_daylight          set_light_level(daylight_level)                // call from map_enter_p_proc and map_update_p_proc of outdoor maps
// light radius (hexes, 0..8) and intensity (percent) of an object such as a lamp
#define set_object_light(obj, radius, percent)  obj_set_light_level(obj, percent, radius)

/* mark_area_known(type, id, state). */
#define MARK_TYPE_TOWN          (0)       // id = area number in data/city.txt
#define MARK_TYPE_MAP           (1)       // id = map number in data/maps.txt
#define MARK_STATE_UNKNOWN      (0)
#define MARK_STATE_KNOWN        (1)
#define MARK_STATE_VISITED      (2)
#define MARK_STATE_INVISIBLE    (-66)     // towns only: remove from the world map
#define reveal_town(area)       mark_area_known(MARK_TYPE_TOWN, area, MARK_STATE_KNOWN)   // show a town on the world map

/* load_map(map, start): map = file name string or number in data/maps.txt; start position slot. */
#define goto_map(map)           load_map(map, 0)
#define goto_world_map          world_map

#endif /* FO2_H */
