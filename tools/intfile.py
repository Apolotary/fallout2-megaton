#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Fallout 2 compiled script (.int) reader, disassembler and lint.

Layout as fallout2-ce loads it (src/interpreter.cc programCreateByPath), all
values big-endian:

    0x00  42 bytes  startup code, identical in every script except the int32
                    address of "main" at 0x0C
    0x2A  int32     procedure count N; procedure 0 is a dummy ("..............")
    0x2E  N x 24    nameOffset, flags, time, conditionOffset, bodyOffset, argCount
          table     identifiers: int32 size, entries, FF FF FF FF
          table     strings: int32 size, entries, FF FF FF FF (only the marker
                    when the script has no strings)
          code      main (script variable initialisers, jump to `start`), then
                    the procedure bodies up to EOF

A table entry is uint16 length + NUL padded text. Offsets used by the bytecode
and by nameOffset point at the text and are relative to the table's size field
(first entry: 6). Instructions are 16-bit words with bit 15 set; only the push
opcodes (C001 int, A001 float, 9001 string/identifier) have a 4-byte operand.

    intfile.py <file.int> [...]     disassemble
"""
import struct
import sys

HEADER_HEAD = bytes.fromhex("8002c00100000012800dc001")
HEADER_TAIL = bytes.fromhex("80048010801a8020801a8021801a8022801a8023802480258026")
PUSH_INT, PUSH_FLOAT, PUSH_STRING = 0xC001, 0xA001, 0x9001

PROC_FLAGS = ((0x01, "timed"), (0x02, "conditional"), (0x04, "imported"), (0x08, "exported"), (0x10, "critical"))

# Procedures the engine looks up by name (gScriptProcNames, src/scripts.cc).
ENGINE_PROCS = (
    "start", "spatial_p_proc", "description_p_proc", "pickup_p_proc", "drop_p_proc", "use_p_proc",
    "use_obj_on_p_proc", "use_skill_on_p_proc", "talk_p_proc", "critter_p_proc", "combat_p_proc",
    "damage_p_proc", "map_enter_p_proc", "map_exit_p_proc", "create_p_proc", "destroy_p_proc",
    "look_at_p_proc", "timed_event_p_proc", "map_update_p_proc", "push_p_proc", "is_dropping_p_proc",
    "combat_is_starting_p_proc", "combat_is_over_p_proc",
)

# Opcode names in opcode order starting at 0x8000: the SSL keyword where one
# exists, otherwise the sslc enum name (opcodes.h, oplib.h, opextra.h).
_NAMES = """
noop push critical_start critical_done jump call call_at call_condition callstart exec spawn fork
a_to_d d_to_a exit detach exit_prog stop_prog fetch_global store_global fetch_external
store_external export_var export_proc swap swapa pop dup pop_return pop_exit pop_address pop_flags
pop_flags_return pop_flags_exit pop_flags_return_extern pop_flags_exit_extern
pop_flags_return_val_extern pop_flags_return_val_exit pop_flags_return_val_exit_extern
check_arg_count lookup_string_proc pop_base pop_to_base push_base set_global fetch_proc_address
dump if while store fetch equal not_equal less_equal greater_equal less greater add sub mul div
mod and or bwand bwor bwxor bwnot floor not negate wait cancel cancelall startcritical endcritical

sayquit sayend saystart saystartpos sayreplytitle saygotoreply sayreply sayoption saymessage
sayreplywindow sayoptionwindow sayborder sayscrollup sayscrolldown saysetspacing sayoptioncolor
sayreplycolor sayrestart saygetlastpos sayreplyflags sayoptionflags saymessagetimeout createwin
deletewin selectwin resizewin scalewin showwin fillwin fillrect fillwin3x3 display displaygfx
displayraw loadpalettetable fadein fadeout gotoxy print format printrect setfont settextflags
settextcolor sethighlightcolor stopmovie playmovie movieflags playmovierect playmoviealpha
playmoviealpharect addregion addregionflag addregionproc addregionrightproc deleteregion
activateregion checkregion addbutton addbuttontext addbuttonflag addbuttongfx addbuttonproc
addbuttonrightproc deletebutton hidemouse showmouse mouseshape refreshmouse setglobalmousefunc
addnamedevent addnamedhandler clearnamed signalnamed addkey deletekey soundplay soundpause
soundresume soundstop soundrewind sounddelete setoneoptpause selectfilelist tokenize

give_exp_points scr_return play_sfx obj_name sfx_build_open_name get_pc_stat tile_contains_pid_obj
set_map_start override_map_start has_skill using_skill roll_vs_skill skill_contest do_check
is_success is_critical how_much mark_area_known reaction_influence random roll_dice move_to
create_object_sid display_msg script_overrides obj_is_carrying_obj_pid tile_contains_obj_pid
self_obj source_obj target_obj dude_obj obj_being_used_with local_var set_local_var map_var
set_map_var global_var set_global_var script_action obj_type obj_item_subtype get_critter_stat
set_critter_stat animate_stand_obj animate_stand_reverse_obj animate_move_obj_to_tile
tile_in_tile_rect attack_complex make_daytime tile_distance tile_distance_objs tile_num
tile_num_in_direction pickup_obj drop_obj add_obj_to_inven rm_obj_from_inven wield_obj_critter
use_obj obj_can_see_obj attack start_gdialog end_dialogue dialogue_reaction metarule3 set_map_music
set_obj_visibility load_map wm_area_set_pos set_exit_grids anim_busy critter_heal set_light_level
game_time game_time_in_seconds elevation kill_critter kill_critter_type critter_dmg add_timer_event
rm_timer_event game_ticks has_trait destroy_object obj_can_hear_obj game_time_hour fixed_param
tile_is_visible dialogue_system_enter action_being_used critter_state game_time_advance
radiation_inc radiation_dec critter_attempt_placement obj_pid cur_map_index critter_add_trait
critter_rm_trait proto_data message_str critter_inven_obj obj_set_light_level world_map inven_cmds
float_msg metarule anim obj_carrying_pid_obj reg_anim_func reg_anim_animate
reg_anim_animate_reverse reg_anim_obj_move_to_obj reg_anim_obj_run_to_obj
reg_anim_obj_move_to_tile reg_anim_obj_run_to_tile play_gmovie add_mult_objs_to_inven
rm_mult_objs_from_inven get_month get_day explosion days_since_visited gsay_start gsay_end
gsay_reply gsay_option gsay_message giq_option poison get_poison party_add party_remove
reg_anim_animate_forever critter_injure combat_is_initialized gdialog_mod_barter difficulty_level
running_burning_guy inven_unwield obj_is_locked obj_lock obj_unlock obj_is_open obj_open obj_close
game_ui_disable game_ui_enable game_ui_is_disabled gfade_out gfade_in item_caps_total
item_caps_adjust anim_action_frame reg_anim_play_sfx critter_mod_skill sfx_build_char_name
sfx_build_ambient_name sfx_build_interface_name sfx_build_item_name sfx_build_weapon_name
sfx_build_scenery_name attack_setup destroy_mult_objs use_obj_on_obj endgame_slideshow
move_obj_inven_to_obj endgame_movie obj_art_fid art_anim party_member_obj rotation_to_tile jam_lock
gdialog_set_barter_mod combat_difficulty obj_on_screen critter_is_fleeing critter_set_flee_state
terminate_combat debug_msg critter_stop_attacking

read_byte read_short read_int read_string set_pc_base_stat set_pc_extra_stat get_pc_base_stat
get_pc_extra_stat set_critter_base_stat set_critter_extra_stat get_critter_base_stat
get_critter_extra_stat tap_key get_year game_loaded graphics_funcs_available load_shader free_shader
activate_shader deactivate_shader set_global_script_repeat input_funcs_available key_pressed
set_shader_int set_shader_float set_shader_vector in_world_map force_encounter set_world_map_pos
get_world_map_x_pos get_world_map_y_pos set_dm_model set_df_model set_movie_path set_perk_image
set_perk_ranks set_perk_level set_perk_stat set_perk_stat_mag set_perk_skill1 set_perk_skill1_mag
set_perk_type set_perk_skill2 set_perk_skill2_mag set_perk_str set_perk_per set_perk_end
set_perk_chr set_perk_int set_perk_agl set_perk_lck set_perk_name set_perk_desc set_pipboy_available
get_kill_counter mod_kill_counter get_perk_owed set_perk_owed get_perk_available
get_critter_current_ap set_critter_current_ap active_hand toggle_active_hand set_weapon_knockback
set_target_knockback set_attacker_knockback remove_weapon_knockback remove_target_knockback
remove_attacker_knockback set_global_script_type available_global_script_types set_sfall_global
get_sfall_global_int get_sfall_global_float set_pickpocket_max set_hit_chance_max set_skill_max
eax_available set_eax_environment inc_npc_level get_viewport_x get_viewport_y set_viewport_x
set_viewport_y set_xp_mod set_perk_level_mod get_ini_setting get_shader_version set_shader_mode
get_game_mode force_graphics_refresh get_shader_texture set_shader_texture get_uptime set_stat_max
set_stat_min set_car_current_town set_pc_stat_max set_pc_stat_min set_npc_stat_max set_npc_stat_min
set_fake_perk set_fake_trait set_selectable_perk set_perkbox_title hide_real_perks show_real_perks
has_fake_perk has_fake_trait perk_add_mode clear_selectable_perks set_critter_hit_chance_mod
set_base_hit_chance_mod set_critter_skill_mod set_base_skill_mod set_critter_pickpocket_mod
set_base_pickpocket_mod set_pyromaniac_mod apply_heaveho_fix set_swiftlearner_mod
set_hp_per_level_mod write_byte write_short write_int call_offset_v0 call_offset_v1 call_offset_v2
call_offset_v3 call_offset_v4 call_offset_r0 call_offset_r1 call_offset_r2 call_offset_r3
call_offset_r4 show_iface_tag hide_iface_tag is_iface_tag_active get_bodypart_hit_modifier
set_bodypart_hit_modifier set_critical_table get_critical_table reset_critical_table get_sfall_arg
set_sfall_return set_unspent_ap_bonus get_unspent_ap_bonus set_unspent_ap_perk_bonus
get_unspent_ap_perk_bonus init_hook get_ini_string sqrt abs sin cos tan arctan set_palette
remove_script set_script get_script nb_create_char fs_create fs_copy fs_find fs_write_byte
fs_write_short fs_write_int fs_write_float fs_write_string fs_delete fs_size fs_pos fs_seek
fs_resize get_proto_data set_proto_data set_self register_hook fs_write_bstring fs_read_byte
fs_read_short fs_read_int fs_read_float list_begin list_next list_end sfall_ver_major
sfall_ver_minor sfall_ver_build hero_select_win set_hero_race set_hero_style
set_critter_burst_disable get_weapon_ammo_pid set_weapon_ammo_pid get_weapon_ammo_count
set_weapon_ammo_count write_string get_mouse_x get_mouse_y get_mouse_buttons get_window_under_mouse
get_screen_width get_screen_height stop_game resume_game create_message_window remove_trait
get_light_level refresh_pc_art get_attack_type force_encounter_with_flags set_map_time_multi
play_sfall_sound stop_sfall_sound create_array set_array get_array free_array len_array resize_array
temp_array fix_array string_split list_as_array atoi atof scan_array get_tile_fid modified_ini
get_sfall_args set_sfall_arg force_aimed_shots disable_aimed_shots mark_movie_played get_npc_level
set_critter_skill_points get_critter_skill_points set_available_skill_points
get_available_skill_points mod_skill_points_per_level set_perk_freq get_last_attacker
get_last_target block_combat tile_under_cursor gdialog_get_barter_mod set_inven_ap_cost substr
strlen sprintf charcode reservd2 typeof save_array load_array array_key arrayexpr reservd3 reservd4
reg_anim_destroy reg_anim_animate_and_hide reg_anim_combat_check reg_anim_light reg_anim_change_fid
reg_anim_take_out reg_anim_turn_towards metarule2_explosions register_hook_proc pow log exponent
ceil round reservd5 reservd6 reservd7 message_str_game sneak_success tile_light obj_blocking_line
obj_blocking_tile tile_get_objs party_member_list path_find_to create_spatial art_exists
obj_is_carrying_obj sfall_func0 sfall_func1 sfall_func2 sfall_func3 sfall_func4 sfall_func5
sfall_func6 register_hook_proc_spec reg_anim_callback div sfall_func7 sfall_func8
"""
OPCODE_NAMES = {0x8000 + i: name for i, name in enumerate(_NAMES.split())}
OPCODE_NAMES.update({PUSH_INT: "push", PUSH_FLOAT: "pushf", PUSH_STRING: "pushs"})
OPCODES = {name: code for code, name in OPCODE_NAMES.items()}

# Opcodes fallout2-ce registers a handler for (interpreterRegisterOpcode calls in
# interpreter.cc, interpreter_lib.cc, interpreter_extra.cc, sfall_opcodes.cc).
# Anything else is fatal for the running script instance.
_CE = ("8000-807C 807F-8156 815A-815D 8162-8164 816A 816C 8170-8172 8193 819B 819D-819E 81AC 81AF 81B3 "
       "81B6 81DF-81E0 81EB-81ED 81F5 8204-8206 820D-8212 8217-821A 821C-821E 8220-8221 8224 8228-8229 "
       "822D-8239 824B 824E-824F 8253 8256-8257 8261 8263 8267 826B 826E-826F 8271 8274 8276-827C 827F")
CE_OPCODES = {PUSH_INT, PUSH_FLOAT, PUSH_STRING}
for _part in _CE.split():
    _lo, _, _hi = _part.partition("-")
    CE_OPCODES.update(range(int(_lo, 16), int(_hi or _lo, 16) + 1))

# Builtins that leave a value on the stack, by argument count (sslc: extra.c
# writeExtraExpression, parselib.c writeLibExpression and the sfall_opcodes table).
# Together with the operators below this is everything an argument expression can
# be compiled to, which is what lets _expression_start find where one begins.
_EXPRESSIONS = {
    0: """saygetlastpos self_obj source_obj target_obj dude_obj obj_being_used_with script_action
        game_time game_time_in_seconds game_time_hour fixed_param action_being_used cur_map_index
        get_month get_day days_since_visited combat_is_initialized difficulty_level running_burning_guy
        game_ui_is_disabled endgame_slideshow endgame_movie combat_difficulty get_year game_loaded
        graphics_funcs_available input_funcs_available in_world_map get_world_map_x_pos
        get_world_map_y_pos get_perk_owed active_hand available_global_script_types eax_available
        get_viewport_x get_viewport_y get_shader_version get_game_mode get_uptime get_sfall_arg
        get_unspent_ap_bonus get_unspent_ap_perk_bonus init_hook nb_create_char sfall_ver_major
        sfall_ver_minor sfall_ver_build get_mouse_x get_mouse_y get_mouse_buttons get_window_under_mouse
        get_screen_width get_screen_height get_light_level get_attack_type modified_ini get_sfall_args
        get_available_skill_points tile_under_cursor gdialog_get_barter_mod sneak_success""",
    1: """checkregion obj_name get_pc_stat is_success is_critical how_much local_var map_var global_var
        obj_type obj_item_subtype tile_num anim_busy elevation game_ticks tile_is_visible critter_state
        obj_pid get_poison obj_is_locked obj_is_open item_caps_total sfx_build_ambient_name
        sfx_build_interface_name sfx_build_item_name obj_art_fid art_anim party_member_obj obj_on_screen
        critter_is_fleeing read_byte read_short read_int read_string get_pc_base_stat get_pc_extra_stat
        load_shader key_pressed get_kill_counter get_perk_available get_critter_current_ap
        get_sfall_global_int get_sfall_global_float get_ini_setting has_fake_perk has_fake_trait
        call_offset_r0 is_iface_tag_active get_bodypart_hit_modifier get_ini_string sqrt abs sin cos tan
        get_script fs_find fs_size fs_pos fs_read_byte fs_read_short fs_read_int fs_read_float
        list_begin list_next get_weapon_ammo_pid get_weapon_ammo_count len_array list_as_array atoi atof
        get_tile_fid get_npc_level get_last_attacker get_last_target strlen charcode typeof load_array
        reservd3 reservd4 log exponent ceil round party_member_list art_exists sfall_func0""",
    2: """soundplay selectfilelist sfx_build_open_name has_skill using_skill random roll_dice
        obj_is_carrying_obj_pid get_critter_stat tile_distance tile_distance_objs obj_can_see_obj
        critter_heal obj_can_hear_obj proto_data message_str critter_inven_obj metarule
        obj_carrying_pid_obj item_caps_adjust anim_action_frame destroy_mult_objs rotation_to_tile
        get_critter_base_stat get_critter_extra_stat get_shader_texture call_offset_r1 arctan fs_create
        fs_copy get_proto_data play_sfall_sound create_array get_array temp_array string_split
        scan_array get_critter_skill_points sprintf array_key arrayexpr message_str_game tile_light
        tile_get_objs obj_is_carrying_obj sfall_func1""",
    3: """tokenize tile_contains_pid_obj roll_vs_skill skill_contest do_check reaction_influence move_to
        tile_contains_obj_pid set_critter_stat tile_num_in_direction has_trait critter_attempt_placement
        inven_cmds rm_mult_objs_from_inven sfx_build_char_name sfx_build_scenery_name call_offset_r2
        substr metarule2_explosions obj_blocking_line obj_blocking_tile path_find_to sfall_func2""",
    4: """create_object_sid metarule3 critter_add_trait critter_rm_trait sfx_build_weapon_name
        call_offset_r3 get_critical_table create_spatial sfall_func3""",
    5: """tile_in_tile_rect call_offset_r4 sfall_func4""",
    6: """sfall_func5""",
    7: """sfall_func6""",
    8: """sfall_func7""",
    9: """sfall_func8""",
}
# opcode -> values taken off the stack; each of these puts one back
_VALUE_OPS = {OPCODES[name]: count for count, names in _EXPRESSIONS.items() for name in names.split()}
_VALUE_OPS.update({code: 2 for code in range(0x8033, 0x8043)})      # equal .. bwxor
_VALUE_OPS.update({code: 1 for code in range(0x8043, 0x8047)})      # bwnot, floor, not, negate
_VALUE_OPS.update({0x8012: 1, 0x8014: 1, 0x8032: 1,                 # fetch_global, fetch_external, fetch
                   0x8263: 2, 0x827F: 2})                           # sfall operators: pow, unsigned div

_EXTERNAL_OPS = (OPCODES["fetch_external"], OPCODES["store_external"], OPCODES["export_var"])
_OPTION_OPS = (OPCODES["gsay_option"], OPCODES["giq_option"])
_PUSHES = (PUSH_INT, PUSH_FLOAT, PUSH_STRING)


class IntError(ValueError):
    """The file is not a well-formed .int script."""


class Procedure:
    __slots__ = ("index", "name", "flags", "time", "condition", "body", "argc")

    def __init__(self, index, name, flags, time, condition, body, argc):
        self.index, self.name, self.flags, self.time = index, name, flags, time
        self.condition, self.body, self.argc = condition, body, argc


class Instruction:
    __slots__ = ("offset", "opcode", "operand")

    def __init__(self, offset, opcode, operand=None):
        self.offset, self.opcode, self.operand = offset, opcode, operand

    @property
    def name(self):
        return OPCODE_NAMES.get(self.opcode, "op_%04X" % self.opcode)


def _read_table(data, pos, what):
    """Returns ({offset: text}, position after the table's FF FF FF FF marker)."""
    if pos + 4 > len(data):
        raise IntError("%s table is truncated" % what)
    (size,) = struct.unpack_from(">i", data, pos)
    entries = {}
    if size == -1:
        return entries, pos + 4
    end = pos + 4 + size
    if size < 0 or end + 4 > len(data):
        raise IntError("%s table size %d runs past the end of the file" % (what, size))
    cursor = pos + 4
    while cursor < end:
        (length,) = struct.unpack_from(">H", data, cursor)
        text = data[cursor + 2:cursor + 2 + length]
        if cursor + 2 + length > end or length == 0:
            raise IntError("%s table entry at 0x%X is malformed" % (what, cursor))
        entries[cursor + 2 - pos] = text.split(b"\0", 1)[0].decode("cp1252", "replace")
        cursor += 2 + length
    if data[end:end + 4] != b"\xff\xff\xff\xff":
        raise IntError("%s table is not terminated by FF FF FF FF" % what)
    return entries, end + 4


class IntFile:
    """Parsed .int file: procedures, identifiers, strings and instructions."""

    def __init__(self, data, name=""):
        self.data, self.name = data, name
        if len(data) < 46 or data[:12] != HEADER_HEAD or data[16:42] != HEADER_TAIL:
            raise IntError("not an .int file (startup code does not match)")
        (self.main,) = struct.unpack_from(">i", data, 12)
        (count,) = struct.unpack_from(">i", data, 42)
        ident_pos = 46 + 24 * count
        if count < 1 or ident_pos > len(data):
            raise IntError("bad procedure count %d" % count)
        self.identifiers, string_pos = _read_table(data, ident_pos, "identifier")
        self.strings, self.code_start = _read_table(data, string_pos, "string")
        if self.main != self.code_start:
            raise IntError("main address 0x%X is not the start of the code (0x%X)" % (self.main, self.code_start))

        self.procedures = []
        for index in range(count):
            name_off, flags, time, condition, body, argc = struct.unpack_from(">6i", data, 46 + 24 * index)
            if name_off not in self.identifiers:
                raise IntError("procedure %d: bad name offset %d" % (index, name_off))
            # body 0 = declared but never defined (vanilla surf.int has 68 of them)
            if body != 0 and not self.code_start <= body <= len(data):
                raise IntError("procedure %d: body offset 0x%X outside the code" % (index, body))
            self.procedures.append(Procedure(index, self.identifiers[name_off], flags, time, condition, body, argc))

        self.instructions = []
        pos = self.code_start
        while pos < len(data):
            if pos + 2 > len(data):
                raise IntError("truncated instruction at 0x%X" % pos)
            (opcode,) = struct.unpack_from(">H", data, pos)
            if not opcode & 0x8000:
                raise IntError("bad opcode %04X at 0x%X" % (opcode, pos))
            if opcode in _PUSHES:
                if pos + 6 > len(data):
                    raise IntError("truncated push at 0x%X" % pos)
                fmt = ">f" if opcode == PUSH_FLOAT else ">i"
                self.instructions.append(Instruction(pos, opcode, struct.unpack_from(fmt, data, pos + 2)[0]))
                pos += 6
            else:
                self.instructions.append(Instruction(pos, opcode))
                pos += 2

        starts = {ins.offset for ins in self.instructions} | {0, len(data)}
        for proc in self.procedures:
            if proc.body not in starts:
                raise IntError("procedure %s: body 0x%X is not on an instruction boundary" % (proc.name, proc.body))

    # ---------------------------------------------------------------- queries
    def procedure_names(self):
        """Real procedures (the dummy entry 0 excluded), in table order."""
        return [p.name for p in self.procedures[1:]]

    def handlers(self):
        """Engine event procedures this script defines."""
        have = {n.lower() for n in self.procedure_names()}
        return [n for n in ENGINE_PROCS if n in have]

    def _expression_start(self, end):
        """Index of the first instruction of the expression whose value is on top of the stack
        just before instruction `end`; None when the code is not a plain expression (a
        conditional expression, a call through a variable, ...)."""
        needed = 1
        i = end
        while needed > 0:
            i -= 1
            if i < 0:
                return None
            opcode = self.instructions[i].opcode
            if opcode in _PUSHES:
                needed -= 1
            elif opcode in _VALUE_OPS:
                needed += _VALUE_OPS[opcode] - 1
            elif opcode == OPCODES["call"] and i >= 2 and self.instructions[i - 2].opcode == PUSH_INT \
                    and self.instructions[i - 1].opcode == PUSH_INT:
                # push <return address>; d_to_a; arguments; push argc; push procedure; call
                # One result for: procedure, argc, the arguments and the d_to_a in front of them.
                needed += self.instructions[i - 2].operand + 2
            elif opcode != OPCODES["d_to_a"]:    # d_to_a: gives the call its mark, takes the return address
                return None
        return i

    def local_var_indexes(self):
        """(constant LVAR indexes this script reads or writes, offsets of local_var /
        set_local_var calls whose index could not be evaluated)."""
        constants, unknown = [], []
        for i, ins in enumerate(self.instructions):
            if ins.opcode == OPCODES["local_var"]:
                end = i
            elif ins.opcode == OPCODES["set_local_var"]:
                end = self._expression_start(i)      # skip the value: the index was pushed before it
            else:
                continue
            start = self._expression_start(end) if end is not None else None
            if start is not None and end - start == 1 and self.instructions[start].opcode == PUSH_INT:
                constants.append(self.instructions[start].operand)
            else:
                unknown.append(ins.offset)
        return constants, unknown

    def local_vars_needed(self):
        """`# local_vars=N` this script needs in scripts.lst: highest constant LVAR index + 1.
        Too low only if lint() reports an index it could not evaluate."""
        constants = self.local_var_indexes()[0]
        return max(constants) + 1 if constants else 0

    def lint(self):
        """Warnings about things that compile fine but misbehave in fallout2-ce."""
        out = []
        names = self.procedure_names()
        if names and names[0].lower() != "start":
            out.append("procedure #1 is '%s', not 'start': the engine runs procedure #1 for every event "
                       "this script has no handler for" % names[0])
        unknown = sorted({ins.opcode for ins in self.instructions if ins.opcode not in CE_OPCODES})
        for opcode in unknown:
            out.append("opcode %04X (%s) is not implemented by fallout2-ce: fatal script error when executed"
                       % (opcode, OPCODE_NAMES.get(opcode, "?")))
        for proc in self.procedures[1:]:
            if proc.flags & 0x04:
                out.append("procedure '%s' is imported: calling imported procedures does nothing in fallout2-ce"
                           % proc.name)
        for i, ins in enumerate(self.instructions):
            if ins.opcode in _OPTION_OPS and i >= 2 and self.instructions[i - 2].opcode == PUSH_STRING:
                out.append("0x%04X: %s target is a string; the engine only accepts a procedure reference"
                           % (ins.offset, ins.name))
        for offset in self.local_var_indexes()[1]:
            out.append("0x%04X: local variable index is not a constant; `local_vars needed` does not count it" % offset)
        return out

    # ----------------------------------------------------------- disassembly
    def _comment(self, i):
        ins = self.instructions[i]
        nxt = self.instructions[i + 1] if i + 1 < len(self.instructions) else None
        if ins.opcode == PUSH_STRING:
            table = self.identifiers if nxt is not None and nxt.opcode in _EXTERNAL_OPS else self.strings
            text = table.get(ins.operand)
            return "?? bad offset" if text is None else '"%s"' % text.replace("\n", "\\n")
        if ins.opcode != PUSH_INT or nxt is None:
            return ""
        value = ins.operand
        named = 1 <= value < len(self.procedures)
        if nxt.opcode == OPCODES["call"] and named:
            return "procedure %s" % self.procedures[value].name
        if nxt.opcode == OPCODES["jump"]:
            return "-> 0x%04X" % value
        if nxt.opcode == OPCODES["d_to_a"] and value >= self.code_start:
            return "return address 0x%04X" % value
        if nxt.opcode == PUSH_INT and i + 2 < len(self.instructions) and named \
                and self.instructions[i + 2].opcode in _OPTION_OPS:
            return "procedure %s" % self.procedures[value].name
        return ""

    def disassemble(self):
        lines = ["; %s: %d bytes, %d procedures, %d strings, code 0x%04X..0x%04X"
                 % (self.name or "<script>", len(self.data), len(self.procedures) - 1, len(self.strings),
                    self.code_start, len(self.data))]
        lines.append("; procedures (index, body, args, flags, name)")
        for proc in self.procedures:
            flags = ",".join(text for bit, text in PROC_FLAGS if proc.flags & bit) or "-"
            extra = ""
            if proc.flags & 0x01:
                extra += " time=%d" % proc.time
            if proc.flags & 0x02:
                extra += " condition=0x%04X" % proc.condition
            lines.append(";   %3d  0x%04X  %d  %-8s %s%s" % (proc.index, proc.body, proc.argc, flags, proc.name, extra))
        names = self.procedure_names()
        lines.append("; engine handlers: %s" % (", ".join(self.handlers()) or "none"))
        if names:
            lines.append("; fallback for unhandled events (procedure #1): %s" % names[0])
        lines.append("; local_vars needed (constant indexes seen): %d" % self.local_vars_needed())
        variables = sorted(set(self.identifiers.values()) - {p.name for p in self.procedures})
        if variables:
            lines.append("; other identifiers: %s" % ", ".join(variables))
        lines.append("; strings")
        for offset in sorted(self.strings):
            lines.append(';   %5d  "%s"' % (offset, self.strings[offset].replace("\n", "\\n")))
        for warning in self.lint():
            lines.append("; WARNING: %s" % warning)

        bodies = {}
        for proc in self.procedures[1:]:
            bodies.setdefault(proc.body, []).append(proc.name)
        lines.append("")
        lines.append("main:")
        for i, ins in enumerate(self.instructions):
            for name in bodies.get(ins.offset, ()):
                lines.append("")
                lines.append("procedure %s:" % name)
            if ins.operand is None:
                text = "%04X: %04X           %s" % (ins.offset, ins.opcode, ins.name)
            else:
                raw = struct.unpack_from(">I", self.data, ins.offset + 2)[0]
                shown = repr(ins.operand) if ins.opcode == PUSH_FLOAT else str(ins.operand)
                text = "%04X: %04X %08X  %s %s" % (ins.offset, ins.opcode, raw, ins.name, shown)
            comment = self._comment(i)
            lines.append("  %-44s; %s" % (text, comment) if comment else "  " + text)
        return "\n".join(lines) + "\n"


def load(path):
    with open(path, "rb") as f:
        return IntFile(f.read(), path)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    status = 0
    for path in argv[1:]:
        try:
            sys.stdout.write(load(path).disassemble())
        except (OSError, IntError) as error:
            print("%s: %s" % (path, error), file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
