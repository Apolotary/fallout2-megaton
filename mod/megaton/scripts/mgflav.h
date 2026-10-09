// SPDX-License-Identifier: LicenseRef-Sustainable-Use
/*
 * mgflav.h - shared by the flavour group's scripts: the townsfolk who make
 * Megaton feel inhabited (mgcrom, mgmaya, mgstock, mgmicky, mgbilly, mgmaggie,
 * mgnathan, mgsettlr) and the armory door (mgarmory).
 *
 *     #include "megaton.h"
 *     #define NAME                    SCRIPT_MGSTOCK
 *     #include "mgflav.h"
 *
 * Timed chatter. A townsperson says a floating line every so often while the
 * player is close, instead of on every critter tick:
 *
 *     variable chatter_pending := 0;                  // script-level: not saved
 *
 *     procedure map_enter_p_proc begin   chatter_pending := 0;   ... end
 *     procedure critter_p_proc begin
 *        mg_townsperson_critter;
 *        flav_arm_chatter(chatter_pending, 9, 18, 30);      // range in hexes, delay in seconds
 *     end
 *     procedure timed_event_p_proc begin
 *        if (fixed_param == FLAV_TIMER_CHATTER) then begin
 *           chatter_pending := 0;
 *           if (flav_may_chatter(9)) then call chatter;
 *        end
 *     end
 *
 * Why it is built this way (read in the engine source, confirmed in runs):
 *   - critter_p_proc runs for ONE critter script per frame, in turn, and not at
 *     all during combat or dialogue; timed events do not fire then either.
 *   - Timed events are saved with the game but script-level variables are not.
 *     flav_arm_chatter therefore cancels any event of the same kind before it
 *     queues one (restart_timer): a save made while an event was pending can
 *     never leave two chains of chatter running.
 *   - An event can find its critter in no state to talk: knocked out, turned
 *     hostile since it was queued, or waiting for a fight to end (events are
 *     held back during combat and all fire when it is over). flav_can_chat is
 *     what stops those. (A killed critter is not the worry: the engine removes
 *     its script, events and all, in critterKill.)
 *   - obj_can_see_obj() needs a clear line (walls, closed doors and other
 *     critters block it), the target inside the viewer's perception range, and
 *     is cut short by sneaking. Asking it both ways keeps a townsperson who
 *     happens to face the other way from going mute.
 *   - tile_distance_objs() ignores elevations, hence the explicit test.
 */
#ifndef MGFLAV_H
#define MGFLAV_H

#define FLAV_TIMER_CHATTER      (1)       // fixed_param of the chatter event; scripts number their own from 2

/* list_begin() type of the sfall object lists fallout2-ce implements. */
#define LIST_CRITTERS           (0)

// true when the player stands on self's elevation, at most n hexes away
#define flav_dude_within(n)     ((elevation(self_obj) == elevation(dude_obj)) and (tile_distance_objs(self_obj, dude_obj) <= (n)))
// true when self and the player have each other in view (see above)
#define flav_in_sight           (obj_can_see_obj(self_obj, dude_obj) or obj_can_see_obj(dude_obj, self_obj))
// true when self is in a state to say anything friendly
#define flav_can_chat           (self_is_alive and (mg_is_hostile == false) and (combat_is_initialized == 0) and ((critter_state(self_obj) bwand CRITTER_IS_PRONE) == 0))
// true when a floating line would be seen and makes sense now
#define flav_may_chatter(range) (flav_can_chat and flav_dude_within(range) and flav_in_sight)

// statement, in critter_p_proc: queue the next chatter event, `lo`..`hi` seconds from now,
// when none is pending and the player is within `range` hexes
#define flav_arm_chatter(pending, range, lo, hi) \
                                mg_block(if ((pending) == 0) then begin if (flav_dude_within(range)) then begin \
                                   pending := 1; \
                                   restart_timer(seconds(random(lo, hi)), FLAV_TIMER_CHATTER); \
                                end end)

// statement: var := a line id in first..last, never `previous` (the line said last time) when
// the range holds more than one line: on a repeat the next line is taken instead
#define flav_pick(var, first, last, previous) \
                                mg_block(var := random(first, last); \
                                   if (var == (previous)) then begin \
                                      var := var + 1; \
                                      if (var > (last)) then var := (first); \
                                   end)

// statement, in pickup_p_proc of somebody who never fights (the Confessor, Maya, Micky, Maggie):
// megaton.h's rule for the first theft (a warning, reputation -2). megaton.h answers the second
// with a personal grudge, which only a fighter can act on: one of these would just refuse to speak
// for the rest of the game. Instead the grudge is dropped and every further theft that is noticed
// costs the town's good opinion again.
#define flav_meek_pickup        mg_block(mg_townsperson_pickup; \
                                   if (local_var(MG_LVAR_HOSTILE) == 1) then begin \
                                      if (global_var(GVAR_MG_TOWN_HOSTILE) == MG_TOWN_PEACEFUL) then begin \
                                         mg_forgive; \
                                         mg_add_town_rep(-2); \
                                         float_msg(self_obj, message_str(SCRIPT_MEGATON, random(MG_MSG_THIEF_FIRST, MG_MSG_THIEF_LAST)), FLOAT_MSG_RED); \
                                      end \
                                   end)

#endif /* MGFLAV_H */
