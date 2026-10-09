// SPDX-License-Identifier: LicenseRef-Sustainable-Use
/*
 * mgmerch.h - shared by the merchants group's scripts: the shops and services
 * of Megaton (mgmoira, mgmerc, mggob, mgdoc, mgjenny, mgtrade, mgnova).
 *
 *     #include "mgmerch.h"                    // pulls in megaton.h
 *     #define NAME                    SCRIPT_MGMOIRA
 *
 * It holds what those scripts must agree on: who is dead, the theft alarm of
 * Craterside Supply, how stock is kept and refilled, and when a shopkeeper
 * forgives. Everything is a macro (a header cannot hold procedures, megaton.h
 * explains why). Macros marked "statement" are safe bare after then / else.
 *
 * STOCK. A merchant's goods live in his own inventory, where the barter screen
 * shows them. Each merchant script lists them ONCE, in a procedure of
 * mg_stock() lines, and cast/merchants.py gives them nothing:
 *
 *     procedure restock begin
 *        mg_stock(PID_STIMPAK, 3);            // top up to three, never beyond
 *        mg_stock_cash(350);
 *     end
 *     procedure map_enter_p_proc begin
 *        if (self_is_alive and (is_loading_game == 0)) then mg_check_stock(LVAR_STOCKED, restock);
 *     end
 *     procedure talk_p_proc begin ... mg_check_stock(LVAR_STOCKED, restock); ... end
 *
 * The town has one delivery day, GVAR_MG_RESTOCK_DAY: it moves to today once
 * MG_RESTOCK_DAYS days have passed (megaton.ssl does the same on every entry;
 * whoever notices first moves it). A merchant restocks when the day stored in
 * his own local variable is not that day, so nothing is added twice however
 * often the map is entered, and a first visit always finds the shelves full.
 * create_object() fails while a save is loading, hence no check in a
 * map_enter that runs for a load; talk_p_proc catches up.
 *
 * GRUDGES. megaton.h makes a shopkeeper the player's personal enemy when he
 * is caught stealing twice (or hurts her). Left alone that would close a shop
 * for good, so every merchant calls mg_merch_note_grudge() in critter_p_proc
 * and mg_merch_cool_off() in map_enter_p_proc: the grudge is dropped at a map
 * entry when the town itself has forgiven (megaton.ssl counts amnesties in
 * GVAR_MG_AMNESTY), or, while the town is at peace, once MG_GRUDGE_DAYS days
 * have passed since it began.
 */
#ifndef MGMERCH_H
#define MGMERCH_H

#include "megaton.h"

/* ------------------------------------------------------------ who is dead */

/* Bits of GVAR_MG_MERCH_DEAD (registry.py). Each script sets its own bit in
   destroy_p_proc, whoever did the killing; other scripts read them to change
   what they say and to offer fallbacks (Moira takes Lucy's letter when the
   caravan trader is dead; mglucy.ssl reads that bit too). */
#define MG_DEAD_MOIRA           (1)
#define MG_DEAD_MERC            (2)
#define MG_DEAD_GOB             (4)
#define MG_DEAD_DOC             (8)
#define MG_DEAD_JENNY           (16)
#define MG_DEAD_TRADER          (32)
#define MG_DEAD_NOVA            (64)

#define mg_merch_is_dead(bit)   ((global_var(GVAR_MG_MERCH_DEAD) bwand (bit)) != 0)                        // true once that one has died
#define mg_merch_died(bit)      set_global_var(GVAR_MG_MERCH_DEAD, global_var(GVAR_MG_MERCH_DEAD) bwor (bit))  // in destroy_p_proc

/* ------------------------------------------- Craterside Supply's theft alarm */

/* GVAR_MG_SHOP_ALARM (registry.py). mgmoira.ssl raises it from pickup_p_proc,
   mgmerc.ssl answers it from critter_p_proc. */
#define MG_ALARM_CALM           (0)
#define MG_ALARM_CAUGHT         (1)       // Moira caught the player once; her guard has not spoken yet
#define MG_ALARM_WARNED         (2)       // the guard gave his one warning
#define MG_ALARM_SHOOT          (3)       // caught again: the guard turns on the player

/* ------------------------------------------------------------------ stock */

#define MG_RESTOCK_DAYS         (3)       // deliveries reach the town this often (design brief 5.5)

// statement: top a line of stock up to n pieces (never beyond; sold-out lines are refilled)
#define mg_stock(pid, n)        one_statement(if (obj_is_carrying_obj_pid(self_obj, pid) < (n)) then \
                                   add_mult_objs_to_inven(self_obj, create_object_sid(pid, 0, 0, -1), (n) - obj_is_carrying_obj_pid(self_obj, pid)))
// statement: top the purse up to n dollars (a richer purse is left alone)
#define mg_stock_cash(n)        one_statement(if (item_caps_total(self_obj) < (n)) then item_caps_adjust(self_obj, (n) - item_caps_total(self_obj)))
// statement: move the town's delivery day on when it is due, and call `restock_proc` when self has
// not restocked for that day yet. lv = a local variable of the script (delivery day + 1; 0 = never).
#define mg_check_stock(lv, restock_proc)  mg_block( \
                                   if (mg_days_since(global_var(GVAR_MG_RESTOCK_DAY)) >= MG_RESTOCK_DAYS) then set_global_var(GVAR_MG_RESTOCK_DAY, mg_day); \
                                   if (local_var(lv) != global_var(GVAR_MG_RESTOCK_DAY) + 1) then begin \
                                      set_local_var(lv, global_var(GVAR_MG_RESTOCK_DAY) + 1); \
                                      call restock_proc; \
                                   end)

/* ---------------------------------------------------------------- grudges */

#define MG_GRUDGE_DAYS          (3)       // a robbed shopkeeper's own grudge lasts this long

// statement, in critter_p_proc (cheap): remember the day a personal grudge began. lv_day as below.
#define mg_merch_note_grudge(lv_day)  mg_block(if (local_var(MG_LVAR_HOSTILE) == 1) then begin \
                                   if (local_var(lv_day) == 0) then set_local_var(lv_day, mg_day + 1); \
                                end)

// statement, in map_enter_p_proc: drop self's personal grudge when it has run its course.
// lv_amnesty, lv_day = two local variables of the script (last GVAR_MG_AMNESTY seen; day + 1 on
// which the grudge began or was first found at a map entry, 0 = none).
#define mg_merch_cool_off(lv_amnesty, lv_day)  mg_block( \
                                   if (local_var(lv_amnesty) != global_var(GVAR_MG_AMNESTY)) then begin \
                                      set_local_var(lv_amnesty, global_var(GVAR_MG_AMNESTY)); \
                                      set_local_var(lv_day, 0); \
                                      mg_forgive; \
                                   end else if (local_var(MG_LVAR_HOSTILE) != 1) then begin \
                                      set_local_var(lv_day, 0); \
                                   end else if (mg_town_is_hostile == 0) then begin \
                                      if (local_var(lv_day) == 0) then begin \
                                         set_local_var(lv_day, mg_day + 1); \
                                      end else if (mg_days_since(local_var(lv_day) - 1) >= MG_GRUDGE_DAYS) then begin \
                                         set_local_var(lv_day, 0); \
                                         mg_forgive; \
                                      end \
                                   end)

#endif /* MGMERCH_H */
