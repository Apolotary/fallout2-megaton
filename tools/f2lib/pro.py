"""Prototype (``.pro``) files: parse, serialise, look up.

All fields are big-endian int32 except the single-byte `sound_id` (items,
scenery) and `weapon_sound_code` (weapons). On-disk order follows protoRead
(proto.cc:1663-1736), which differs from the engine's in-memory structs.
`Proto.to_bytes()` reproduces every retail proto byte for byte
(tools/tests/test_pro.py); the engine's own protoWrite is buggy and must not
be used as a reference.

    db = GameFiles().protos                  # ProtoDB
    door = db.get(0x02000002)
    door.kind, door.subtype_name             # 'scenery', 'door'
    db.name(door.pid)                        # 'Wooden Door'
    new = door.copy(pid=0x0200073C, fid=0x0200074A).to_bytes()
"""
import struct

from . import ids

COMMON = ("pid", "message_id", "fid", "light_distance", "light_intensity", "flags", "flags_ext")
TILE = ("pid", "message_id", "fid", "flags", "flags_ext", "sid", "material")
ITEM_FIXED = ("sub_type", "material", "size", "weight", "cost", "inv_fid")
CRITTER_HEAD = ("head_fid", "ai_packet", "team", "critter_flags")
CRITTER_TAIL = ("body_type", "experience", "kill_type")

ITEM_SUB = {
    0: ("ac",) + tuple(f"dr_{n}" for n in ("normal", "laser", "fire", "plasma", "electrical", "emp", "explosion"))
       + tuple(f"dt_{n}" for n in ("normal", "laser", "fire", "plasma", "electrical", "emp", "explosion"))
       + ("perk", "male_fid", "female_fid"),
    1: ("max_size", "open_flags"),
    2: ("stat_0", "stat_1", "stat_2", "amount_0", "amount_1", "amount_2",
        "duration_1", "amount1_0", "amount1_1", "amount1_2",
        "duration_2", "amount2_0", "amount2_1", "amount2_2",
        "addiction_chance", "withdrawal_effect", "withdrawal_onset"),
    3: ("anim_code", "min_damage", "max_damage", "damage_type", "max_range_1", "max_range_2",
        "projectile_pid", "min_strength", "ap_cost_1", "ap_cost_2", "crit_fail_table", "perk",
        "burst_rounds", "caliber", "ammo_type_pid", "ammo_capacity"),      # + u8 weapon_sound_code
    4: ("caliber", "quantity", "ac_modifier", "dr_modifier", "damage_multiplier", "damage_divisor"),
    5: ("power_type_pid", "power_type", "charges"),
    6: ("key_code",),
}
SCENERY_SUB = {
    0: ("open_flags", "key_code"),
    1: ("dest_built_tile", "dest_map"),
    2: ("elevator_type", "elevator_level"),
    3: ("ladder_dest",),
    4: ("ladder_dest",),
    5: ("unused",),
}

STAT_NAMES = ("strength", "perception", "endurance", "charisma", "intelligence", "agility", "luck",
              "max_hp", "max_ap", "armor_class", "unarmed_damage", "melee_damage", "carry_weight",
              "sequence", "healing_rate", "critical_chance", "better_criticals",
              "dt_normal", "dt_laser", "dt_fire", "dt_plasma", "dt_electrical", "dt_emp", "dt_explosion",
              "dr_normal", "dr_laser", "dr_fire", "dr_plasma", "dr_electrical", "dr_emp", "dr_explosion",
              "radiation_resistance", "poison_resistance", "age", "gender")
SKILL_NAMES = ("small_guns", "big_guns", "energy_weapons", "unarmed", "melee", "throwing", "first_aid",
               "doctor", "sneak", "lockpick", "steal", "traps", "science", "repair", "speech", "barter",
               "gambling", "outdoorsman")
MATERIAL_NAMES = ("glass", "metal", "plastic", "wood", "dirt", "stone", "cement", "leather")

MSG_FILES = ("game/pro_item.msg", "game/pro_crit.msg", "game/pro_scen.msg",
             "game/pro_wall.msg", "game/pro_tile.msg", "game/pro_misc.msg")

# Object flags a proto hands to a new object (objectCreateWithFidPid, object.cc:931-973).
_TRANS_PRIORITY = (0x8000, 0x10000, 0x20000, 0x40000, 0x80000, 0x4000)
_COPIED_FLAGS = 0x08 | 0x10 | 0x800 | 0x1000 | 0x10000000 | 0x20000000 | 0x80000000


class Proto:
    """One prototype; fields are attributes in on-disk order (see `fields()`)."""

    def __init__(self, fields):
        object.__setattr__(self, "_f", dict(fields))

    def __getattr__(self, name):
        if name == "_f":
            raise AttributeError(name)
        try:
            return self._f[name]
        except KeyError:
            raise AttributeError(f"{self.kind} proto has no field {name!r}") from None

    def __setattr__(self, name, value):
        if name not in self._f:
            raise AttributeError(f"{self.kind} proto has no field {name!r}")
        self._f[name] = value

    def __repr__(self):
        return f"<Proto 0x{self.pid:08X} {self.kind}{'/' + self.subtype_name if self.subtype_name else ''}>"

    def fields(self):
        return list(self._f)

    def as_dict(self):
        return dict(self._f)

    def copy(self, **changes):
        """Deep copy with some fields replaced."""
        fields = {k: (list(v) if isinstance(v, list) else v) for k, v in self._f.items()}
        for name, value in changes.items():
            if name not in fields:
                raise AttributeError(f"{self.kind} proto has no field {name!r}")
            fields[name] = value
        return Proto(fields)

    # --------------------------------------------------------------- classify
    @property
    def obj_type(self):
        return ids.pid_type(self._f["pid"])

    @property
    def kind(self):
        return ids.TYPE_NAMES[self.obj_type]

    @property
    def subtype_name(self):
        """'weapon', 'door', ... for items and scenery, else ''."""
        if self.obj_type == ids.OBJ_TYPE_ITEM:
            return ids.ITEM_TYPES[self._f["sub_type"]]
        if self.obj_type == ids.OBJ_TYPE_SCENERY:
            return ids.SCENERY_TYPES[self._f["sub_type"]]
        return ""

    # ---------------------------------------------------------------- derived
    @property
    def max_hp(self):
        return self.base_stats[7] + self.bonus_stats[7]

    @property
    def max_ap(self):
        return self.base_stats[8] + self.bonus_stats[8]

    def object_flags(self):
        """Flags a freshly created object of this proto carries."""
        flags = self._f["flags"] & _COPIED_FLAGS
        for bit in _TRANS_PRIORITY:
            if self._f["flags"] & bit:
                flags |= bit
                break
        return flags

    # -------------------------------------------------------------- serialise
    @classmethod
    def from_bytes(cls, data):
        f = {}
        pos = 0

        def ints(names):
            nonlocal pos
            f.update(zip(names, struct.unpack_from(f">{len(names)}i", data, pos)))
            pos += 4 * len(names)

        def byte(name):
            nonlocal pos
            f[name] = data[pos]
            pos += 1

        def array(name, count):
            nonlocal pos
            f[name] = list(struct.unpack_from(f">{count}i", data, pos))
            pos += 4 * count

        obj_type = (struct.unpack_from(">i", data, 0)[0] >> 24) & 0xFF
        if obj_type == ids.OBJ_TYPE_TILE:
            ints(TILE)
        elif obj_type == ids.OBJ_TYPE_MISC:
            ints(COMMON)
        elif obj_type in (ids.OBJ_TYPE_ITEM, ids.OBJ_TYPE_CRITTER, ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_WALL):
            ints(COMMON + ("sid",))
            if obj_type == ids.OBJ_TYPE_ITEM:
                ints(ITEM_FIXED)
                byte("sound_id")
                ints(ITEM_SUB[f["sub_type"]])
                if f["sub_type"] == 3:
                    byte("weapon_sound_code")
            elif obj_type == ids.OBJ_TYPE_CRITTER:
                ints(CRITTER_HEAD)
                array("base_stats", 35)
                array("bonus_stats", 35)
                array("skills", 18)
                ints(CRITTER_TAIL)
                if pos + 4 <= len(data):         # optional: two retail protos stop before it
                    ints(("damage_type",))
            elif obj_type == ids.OBJ_TYPE_SCENERY:
                ints(("sub_type", "material"))
                byte("sound_id")
                ints(SCENERY_SUB[f["sub_type"]])
            else:
                ints(("material",))
        else:
            raise ValueError(f"not a prototype: object type {obj_type}")
        if pos != len(data):
            raise ValueError(f"proto 0x{f['pid']:08X}: {len(data) - pos} trailing bytes")
        return cls(f)

    def to_bytes(self):
        out = bytearray()
        for name, value in self._f.items():
            if name in ("sound_id", "weapon_sound_code"):
                out.append(value)
            elif isinstance(value, list):
                out += struct.pack(f">{len(value)}i", *(ids.s32(v) for v in value))
            else:
                out += struct.pack(">i", ids.s32(value))
        return bytes(out)


class ProtoDB:
    """Prototype lookup over a `GameFiles` tree (parsed protos are cached)."""

    def __init__(self, gamefiles):
        self.gf = gamefiles
        self._protos = {}
        self._subtypes = {}

    def path(self, pid):
        """Game-tree path of the proto file, or None for an index beyond the list."""
        obj_type = ids.pid_type(pid)
        if obj_type >= ids.PROTO_TYPE_COUNT:
            return None
        name = self.gf.proto_list(obj_type).name(ids.pid_index(pid))
        return f"proto/{ids.TYPE_DIRS[obj_type]}/{name.lower()}" if name else None

    def exists(self, pid):
        path = self.path(pid)
        return path is not None and self.gf.exists(path)

    def raw(self, pid):
        path = self.path(pid)
        if path is None:
            raise KeyError(f"no proto list entry for PID 0x{pid:08X}")
        return self.gf.read(path)

    def get(self, pid):
        proto = self._protos.get(pid)
        if proto is None:
            proto = self._protos[pid] = Proto.from_bytes(self.raw(pid))
        return proto

    def subtype(self, pid):
        """Item / scenery sub-type number (the int32 at 0x20), None for other types."""
        if ids.pid_type(pid) not in (ids.OBJ_TYPE_ITEM, ids.OBJ_TYPE_SCENERY):
            return None
        value = self._subtypes.get(pid)
        if value is None:
            value = self._subtypes[pid] = struct.unpack_from(">i", self.raw(pid), 0x20)[0]
        return value

    def count(self, obj_type):
        return len(self.gf.proto_list(obj_type))

    def pids(self, obj_type):
        """Every PID of a type, in list order."""
        return [ids.make_pid(obj_type, i) for i in self.gf.proto_list(obj_type).indices()]

    # ------------------------------------------------------------------ texts
    def _text(self, pid, offset):
        obj_type = ids.pid_type(pid)
        if obj_type >= ids.PROTO_TYPE_COUNT or not self.exists(pid):
            return None
        return self.gf.msg(MSG_FILES[obj_type]).text(self.get(pid).message_id + offset)

    def name(self, pid):
        """Display name from pro_<type>.msg, or None."""
        return self._text(pid, 0)

    def description(self, pid):
        return self._text(pid, 1)

    def search(self, text, obj_type=None):
        """[(pid, name)] of protos whose name contains `text` (case-insensitive)."""
        needle = text.lower()
        found = []
        types = range(ids.PROTO_TYPE_COUNT) if obj_type is None else (obj_type,)
        for t in types:
            for pid in self.pids(t):
                name = self.name(pid)
                if name and needle in name.lower():
                    found.append((pid, name))
        return found
