/*
 * sample.h - ids shared by the sample scripts; the kind of header a mod keeps
 * for its own script numbers, variables and tuning values.
 *
 * Every value can be overridden from the command line (tools/ssl.py -D), which
 * is how mod/t3/build.py installs the samples over stock Arroyo scripts.
 */
#ifndef SAMPLE_H
#define SAMPLE_H

#include "fo2.h"

/* 1-based lines in scripts/scripts.lst. The stock list has 1303 lines, so the
   first script a mod appends is 1304. */
#ifndef SCRIPT_SMPMAP
#define SCRIPT_SMPMAP           (1304)
#endif
#ifndef SCRIPT_SMPNPC
#define SCRIPT_SMPNPC           (1305)
#endif
#ifndef SCRIPT_SMPOBJ
#define SCRIPT_SMPOBJ           (1306)
#endif
#ifndef SCRIPT_SMPTRIG
#define SCRIPT_SMPTRIG          (1307)
#endif
#ifndef SCRIPT_SMPLOCK
#define SCRIPT_SMPLOCK          (1308)
#endif

/* Global variables: slots of the stock game's unused reserved block, so no
   vault13.gam change is needed and old saves stay compatible. */
#define GVAR_SMP_MAP_VISITS     (GVAR_MOD_FIRST)        // times the sample map was entered
#define GVAR_SMP_MAP_UPDATES    (GVAR_MOD_FIRST + 1)    // times its map_update_p_proc ran
#define GVAR_SMP_NPC            (GVAR_MOD_FIRST + 2)    // NPC_* state below
#define GVAR_SMP_PUMP           (GVAR_MOD_FIRST + 3)    // PUMP_* state below
#define GVAR_SMP_TRIGGER        (GVAR_MOD_FIRST + 4)    // times the spatial trigger fired
#define GVAR_SMP_LOCK           (GVAR_MOD_FIRST + 5)    // LOCK_* state of the last lock touched
#define GVAR_SMP_MAP_EXITS      (GVAR_MOD_FIRST + 6)    // times the sample map was left

#define NPC_UNKNOWN             (0)
#define NPC_MET                 (1)
#define NPC_GAVE_KEY            (2)

#define PUMP_BROKEN             (0)
#define PUMP_FIXED              (1)

#define LOCK_LOCKED             (0)
#define LOCK_OPENED_WITH_KEY    (1)
#define LOCK_PICKED             (2)

/* Map variables: lines of maps/<map>.gam, counted from 0. The map file's header
   must declare at least as many (see smpmap.ssl). */
#ifndef MVAR_SMP_VISITS
#define MVAR_SMP_VISITS         (0)
#endif
#ifndef MVAR_SMP_PUMP_FIXED
#define MVAR_SMP_PUMP_FIXED     (1)
#endif

/* The key that opens the sample lock and that the sample NPC hands out. */
#ifndef SMP_KEY_PID
#define SMP_KEY_PID             PID_KEY_82
#endif

#endif /* SAMPLE_H */
