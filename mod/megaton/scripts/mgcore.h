// SPDX-License-Identifier: LicenseRef-Sustainable-Use
/*
 * mgcore.h - shared by the main-quest scripts: megaton (the map script), mgsimms,
 * mgburke, mgbomb, mgharden, mghitman, mgweld, mggate, mghouse and the three
 * spatial triggers.
 *
 *     #include "mgcore.h"                     // pulls in megaton.h
 *     #define NAME                    SCRIPT_MGSIMMS
 *
 * It names the steps of the saloon confrontation (GVAR_MG_SCENE), the states of
 * GVAR_MG_HARDEN, the numbers the main quest pays out, and a few animation and
 * sound helpers. Who writes which variable:
 *
 *   megaton.ssl   the rules that hold when nobody is watching: what the scene's
 *                 outcome is if the player walked away from it, Burke leaving a
 *                 town whose bomb is dead, the hired guns falling due, the town's
 *                 grudge lapsing, a quest that has nobody left to close it.
 *   mgsimms.ssl   drives the scene while the player is on the map (he walks to the
 *                 table, speaks, and the moment is decided in his script).
 *   mgburke.ssl   Burke's side of it, and the detonation.
 *   mgbomb.ssl    GVAR_MG_BOMB and the quest steps that follow from it.
 *
 * Two object pointers are exported by megaton.ssl and filled in by the two men
 * themselves on every map_enter (exported variables are not saved):
 *
 *     import variable mg_simms_obj;           // 0 while he is not on the map
 *     import variable mg_burke_obj;
 *
 * A script that imports them only works on a map whose map script is megaton.ssl.
 * Always test a pointer against 0 and the critter for being alive before use.
 */
#ifndef MGCORE_H
#define MGCORE_H

#include "megaton.h"

/* ------------------------------------------- the saloon confrontation */

/*
 * GVAR_MG_SCENE. The step is a global so a save made in the middle of the scene
 * carries on where it stopped; GVAR_MG_SCENE_TICK is the game tick at which the
 * current step began, and every wait is measured against it (script timers do
 * not survive leaving the map and script variables do not survive a load).
 *
 *   IDLE         nothing going on
 *   WALK         Simms is on his way to Burke's table
 *   ARREST       Simms has spoken; Burke answers
 *   DRAW         Burke's hand is inside his jacket: the player, if he is there,
 *                gets one forced conversation with Simms to decide it
 *   FIGHT        the player stepped in: Burke is hostile, Simms fights him
 *   SIMMS_FALLS  Burke fires; Simms dies a moment later
 *   BURKE_FALLS  Simms fired first; Burke dies a moment later
 *   DONE         over, for good
 */
#define MG_SCENE_WALK           (1)
#define MG_SCENE_ARREST         (2)
#define MG_SCENE_DRAW           (3)
#define MG_SCENE_FIGHT          (4)
#define MG_SCENE_SIMMS_FALLS    (5)
#define MG_SCENE_BURKE_FALLS    (6)
#define MG_SCENE_DONE           (7)

#define mg_scene                global_var(GVAR_MG_SCENE)
// true while the scene is somewhere between its first and its last step
#define mg_scene_running        ((global_var(GVAR_MG_SCENE) != MG_SCENE_IDLE) and (global_var(GVAR_MG_SCENE) != MG_SCENE_DONE))
// statement: enter a step and start its clock
#define mg_scene_step(step)     one_statement(set_global_var(GVAR_MG_SCENE, step); set_global_var(GVAR_MG_SCENE_TICK, game_time))
// game ticks spent in the current step
#define mg_scene_ticks          (game_time - global_var(GVAR_MG_SCENE_TICK))

#define MG_SCENE_WATCH_RANGE    (8)       // hexes: the player counts as present inside this distance

/* GVAR_MG_HARDEN */
#define MG_HARDEN_FINE          (0)
#define MG_HARDEN_DEAD          (1)
#define MG_HARDEN_ORPHANED      (2)       // the player killed his father: he pays nothing, ever

/* ------------------------------------------------- what the quest pays */

#define MG_PAY_SIMMS            (300)     // Simms for a dead bomb
#define MG_PAY_SIMMS_BONUS      (600)     // ... after haggling (MG_F_SIMMS_BONUS)
#define MG_PAY_BOUNTY           (100)     // Simms for Burke
#define MG_PAY_BURKE            (1000)    // Burke for a crater
#define MG_PAY_BURKE_BONUS      (1500)    // ... after haggling (MG_F_BURKE_BONUS)
#define MG_PAY_BURKE_ADVANCE    (250)     // paid up front and deducted (MG_F_BURKE_ADVANCE)

#define MG_XP_DISARM            (100)     // the act of disarming, or of pulling the charge
#define MG_XP_RIG               (100)     // the act of fitting the charge
#define MG_XP_REPORT            (600)     // telling Simms (or Harden) the bomb is dead
#define MG_XP_EXPOSE            (100)     // telling Simms about Burke
#define MG_XP_SCENE             (150)     // Simms alive at the end of the scene
#define MG_XP_TALKED_OUT        (150)     // Burke talked into leaving
#define MG_XP_DETONATE          (600)
#define MG_KARMA_DETONATE       (-300)

#define MG_HIT_DELAY_DAYS       (3)       // Burke's hired guns come this many days after he leaves
// statement: Burke is gone and wants the player dead; the first cause sets the day
#define mg_schedule_hit         one_statement(if (global_var(GVAR_MG_HIT_DAY) == 0) then set_global_var(GVAR_MG_HIT_DAY, mg_day + MG_HIT_DELAY_DAYS))

/* The bomb: effective score = Traps + the bonuses below (design brief 5.2). */
#define MG_BOMB_NEED            (40)      // to disarm a dormant bomb, or to fit the charge
#define MG_BOMB_NEED_PULL       (50)      // to take a fitted charge out again
#define MG_BOMB_NEAR            (15)      // this far below the mark is a near miss, further is hopeless
#define MG_BOMB_BONUS_NOTES     (20)      // read Moira's notes (MG_F_MOIRA_NOTES, or carrying them). The brief says 15, on the
                                          // assumption that nobody starts below Traps 20; the first premade character has 14
                                          // (Gifted takes ten points off every skill) and ended one point short with the notes
                                          // and a Mentat. With 20, the notes and ONE more help are enough from Traps 10 up.
#define MG_BOMB_BONUS_TOOL      (10)      // carrying a Tool or a Super Tool Kit
#define MG_BOMB_BONUS_MENTATS   (10)      // took a Mentat at the access plate, this visit
#define MG_BOMB_BONUS_TRACED    (5)       // traced the firing circuit with Science

/* ----------------------------------------------------- small helpers */

// the player is close enough to self, on the same level, to count as a witness
#define mg_dude_watching        ((elevation(self_obj) == elevation(dude_obj)) and (tile_distance_objs(self_obj, dude_obj) <= MG_SCENE_WATCH_RANGE))
// True when nobody can be watching obj, so a script may move or remove it without the player
// seeing a man vanish. The engine's obj_on_screen() tests a fixed 640 x 480 rectangle whatever
// the game's resolution: on a wider screen (the browser build is 480 high and up to 1280 wide)
// somebody in the right-hand part of the picture counts as "off screen", and Burke was seen to
// disappear from his table in full view at 1280 x 960. Hence the second test: his place on a
// screen centred on the player (the view follows the player), at the size the game really runs
// at (sfall's get_screen_width / get_screen_height, which fallout2-ce has), must be outside the
// picture: beyond a side edge, with his feet above the top edge, or a sprite's height below the
// bottom one (the map view ends 100 pixels above the bottom of the screen, at the interface bar).
// One hex of hx is 24 pixels to the left and 6 down, one of hy 16 to the right and 12 down
// (research/04, section 11.2; checked against tools/f2lib geometry.hex_world: good to the 8 pixel
// stagger of odd and even hexes, which the margins swallow).
// Not covered: a player who has scrolled the view away from himself on a screen wider than 640.
#define mg_px_right(obj)        ((16 * ((tile_num(obj) / 200) - (tile_num(dude_obj) / 200))) - (24 * ((tile_num(obj) % 200) - (tile_num(dude_obj) % 200))))
#define mg_px_down(obj)         ((12 * ((tile_num(obj) / 200) - (tile_num(dude_obj) / 200))) + (6 * ((tile_num(obj) % 200) - (tile_num(dude_obj) % 200))))
#define mg_view_half_width      ((get_screen_width / 2) + 48)
#define mg_view_half_height     ((get_screen_height - 100) / 2)
#define mg_out_of_view(obj)     ((mg_px_right(obj) > mg_view_half_width) or (mg_px_right(obj) < (0 - mg_view_half_width)) or \
                                 (mg_px_down(obj) > (mg_view_half_height + 96)) or (mg_px_down(obj) < (0 - (mg_view_half_height + 24))))
#define mg_unseen(obj)          ((obj_on_screen(obj) == 0) and mg_out_of_view(obj))
// true when obj is a critter pointer that can still be used
#define mg_alive(obj)           ((critter_state(obj) bwand CRITTER_IS_DEAD) == 0)

/* Weapon animations (animation.h) and the firing sounds of the cast's weapons
   (sound/sfx/WA<code>1XXX1.ACM, code = the weapon proto's sound letter). */
#define ANIM_POINT              (43)
#define ANIM_UNPOINT            (44)
#define ANIM_FIRE_SINGLE        (45)
#define SFX_RIFLE_SHOT          "WAH1XXX1"     // assault rifle (Simms)
#define SFX_SHOTGUN_SHOT        "WAR1XXX1"     // sawed-off shotgun (Burke)
#define SFX_EXPLOSION           "WHN1XXX1"     // the engine's own explosion sound
#define SFX_GEIGER              "GEIGER"

// statement: who raises his weapon, fires once (no bullet, no damage: the script decides
// what the shot does) and lowers it again
#define mg_fire_weapon(who, sfx) \
                                one_statement(reg_anim_func(REG_ANIM_CLEAR, who); \
                                   reg_anim_func(REG_ANIM_BEGIN, ANIM_SEQ_UNRESERVED); \
                                   reg_anim_animate(who, ANIM_POINT, -1); \
                                   reg_anim_play_sfx(who, sfx, 0); \
                                   reg_anim_animate(who, ANIM_FIRE_SINGLE, -1); \
                                   reg_anim_animate(who, ANIM_UNPOINT, -1); \
                                   reg_anim_func(REG_ANIM_END, 0))

// statement: self runs up to another object and stops beside it (a walking critter
// covers about a hex a second and would never catch a player who keeps moving)
#define mg_run_to_obj(target)   one_statement(reg_anim_func(REG_ANIM_CLEAR, self_obj); \
                                   reg_anim_func(REG_ANIM_BEGIN, ANIM_SEQ_UNRESERVED); \
                                   reg_anim_obj_run_to_obj(self_obj, target, -1); \
                                   reg_anim_func(REG_ANIM_END, 0))

/* ------------------------------------------------------- long walks */

/*
 * The engine's pathfinder gives up after 2000 nodes, which in open country is a
 * walk of little more than twenty hexes (seen in the real town: Simms, told to
 * walk the 46 hexes from his post to Burke's table, did not move). Anybody who
 * crosses the town therefore goes from waypoint to waypoint. The waypoints lie
 * along the track from the exit to the saloon and are ordered by hy
 * (layout/spots.py): WAY_APRON, WAY_GATE, SIMMS_POOL, WAY_POOL, WAY_SALOON.
 *
 * A script that needs it declares `procedure way_to(variable target);` and
 * defines it with this body; way_to(tile) is then the hex to walk to NOW on
 * the way to `tile`: the nearest waypoint that still lies ahead (more than two
 * rows ahead, so the walker turns for the next one before he has stopped), or
 * the destination itself. mg_walk_on() gives the walk order.
 *
 *     procedure way_to(variable target) begin
 *        mg_way_body
 *     end
 */
#define mg_way_row(tile)        ((tile) / 200)
#define mg_way_north(spot)      if ((mg_way_row(spot) < (here - 2)) and (mg_way_row(spot) > there)) then return (spot)
#define mg_way_south(spot)      if ((mg_way_row(spot) > (here + 2)) and (mg_way_row(spot) < there)) then return (spot)
#define mg_way_body             variable here; \
                                variable there; \
                                here := mg_way_row(self_tile); \
                                there := mg_way_row(target); \
                                if (there < here) then begin \
                                   mg_way_north(TILE_WAY_APRON); \
                                   mg_way_north(TILE_WAY_GATE); \
                                   mg_way_north(TILE_SIMMS_POOL); \
                                   mg_way_north(TILE_WAY_POOL); \
                                   mg_way_north(TILE_WAY_SALOON); \
                                end else begin \
                                   mg_way_south(TILE_WAY_SALOON); \
                                   mg_way_south(TILE_WAY_POOL); \
                                   mg_way_south(TILE_SIMMS_POOL); \
                                   mg_way_south(TILE_WAY_GATE); \
                                   mg_way_south(TILE_WAY_APRON); \
                                end \
                                return target;

/*
 * statement: keep self walking (hurry 0) or running (hurry 1) to `target` by way of the waypoints.
 * Call it from critter_p_proc on every tick. `goal` and `again` are script-level variables of the
 * caller: the hex of the last order, and the game tick before which an unchanged order is not
 * repeated. A new order is given at once when the next waypoint changes (dropping the walk in
 * progress, hence the 16), otherwise only when he stands still and three seconds have passed.
 */
#define mg_walk_on(target, hurry, goal, again) \
                                mg_block(if (way_to(target) != (goal)) then begin \
                                   goal := way_to(target); \
                                   again := game_time + 30; \
                                   animate_move_obj_to_tile(self_obj, goal, (hurry) + 16); \
                                end else if (game_time >= (again)) then begin \
                                   again := game_time + 30; \
                                   if (anim_busy(self_obj) == 0) then animate_move_obj_to_tile(self_obj, goal, hurry); \
                                end)

/* Personal grudges lapse with the town's (megaton.ssl counts amnesties in
   GVAR_MG_AMNESTY). In map_enter_p_proc, with a local variable of the script's own:
       mg_honour_amnesty(LVAR_AMNESTY);                                            */
#define mg_honour_amnesty(lv)   mg_block(if (local_var(lv) != global_var(GVAR_MG_AMNESTY)) then begin \
                                   set_local_var(lv, global_var(GVAR_MG_AMNESTY)); \
                                   mg_forgive; \
                                end)

#endif /* MGCORE_H */
