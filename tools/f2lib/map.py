"""Fallout 2 ``.map`` files (version 19/20): parse, serialise, build, validate.

Everything is big-endian int32. Layout (mapLoad, map.cc:850-911)::

    header 0xEC bytes | global vars | local vars | 40000 bytes of squares per
    PRESENT elevation | 5 script lists | total object count | 3 object blocks

`MapFile.from_bytes(...).to_bytes()` reproduces every vanilla map byte for
byte (tools/tests/test_map.py), including the garbage the original tools left
in unused script slots, so any map can be edited in place.

Building a map from nothing::

    gf = GameFiles(overlay="mod/megaton/data")
    m = MapFile.new("megaton", gf)                 # 1 elevation, MEGATON.MAP
    m.fill_floor(40, 40, 60, 60, "edg5000.frm")    # squares x 40..60, y 40..60
    door = m.add_object(0x02000002, tile=20100, rotation=0)
    m.lock(door)                                   # see `lock` for what the engine enforces
    guard = m.add_object(0x01000004, tile=20305, script="acguard")
    m.add_item(guard, 0x00000007, equipped="right")
    ladder = m.add_object(0x0200008B, tile=20110)
    m.set_destination(ladder, tile=20112, elevation=1)
    m.add_exit_grid(22500)                         # to the world map
    m.set_map_script("megaton")                    # scripts.lst name
    m.set_entrance(20100, rotation=2)
    assert not m.validate()
    m.save("mod/megaton/data/maps/megaton.map")

Index bases: `MapFile.script_index` (map script) is 1-based, `Script.index`
and `MapObject.script_index` are 0-based lines of scripts.lst; tile ids are
0-based lines of art/tiles/tiles.lst and id 1 means "no tile".

What the engine does with each field, and why the validation rules exist, is
documented in research/04-fo2-map-format.md (sections 3-10 and 15).
"""
import struct

import numpy as np

from . import gam, geometry, ids, mapstxt

VERSION = 20
HEADER_SIZE = 0xEC
ELEVATION_COUNT = 3
ELEVATION_ABSENT = (0x2, 0x4, 0x8)           # header flag: elevation has no square block
FLAG_SAVEGAME = 0x1
NO_TILE = 1                                  # tiles.lst index of the transparent "nothing" tile
EMPTY_SQUARE = (NO_TILE << 16) | NO_TILE
EXTENT_SIZE = 16
PLAYER_ID = 18000                            # object ids from here up belong to the party

# Object flags (obj_types.h:45-90).
OBJECT_HIDDEN = 0x01
OBJECT_FLAT = 0x08
OBJECT_NO_BLOCK = 0x10
OBJECT_LIGHTING = 0x20
OBJECT_MULTIHEX = 0x800
OBJECT_IN_LEFT_HAND = 0x01000000
OBJECT_IN_RIGHT_HAND = 0x02000000
OBJECT_WORN = 0x04000000
OBJECT_LIGHT_THRU = 0x20000000
OBJECT_SHOOT_THRU = 0x80000000
OBJECT_OPEN_DOOR = OBJECT_NO_BLOCK | OBJECT_LIGHT_THRU | OBJECT_SHOOT_THRU    # what an open door gains
# data_flags of containers / open_flags of doors.
DOOR_OPEN = 0x01
LOCKED = 0x02000000
JAMMED = 0x04000000

OBJECT_FIELDS = ("id", "tile", "x", "y", "sx", "sy", "frame", "rotation", "fid", "flags", "elevation",
                 "pid", "cid", "light_distance", "light_intensity", "outline", "sid", "script_index")
CRITTER_DATA = ("reaction", "damage_last_turn", "maneuver", "ap", "results", "ai_packet", "team",
                "who_hit_me", "hp", "radiation", "poison")
ITEM_DATA = {3: ("ammo_quantity", "ammo_type_pid"), 4: ("quantity",), 5: ("charges",), 6: ("key_code",)}
SCENERY_DATA = {0: ("open_flags",), 1: ("dest_built_tile", "dest_map"), 2: ("elevator_type", "elevator_level"),
                3: ("dest_map", "dest_built_tile"), 4: ("dest_map", "dest_built_tile")}
EXIT_GRID_DATA = ("dest_map", "dest_tile", "dest_elevation", "dest_rotation")

SCRIPT_TAIL = ("flags", "index", "program", "owner_id", "local_vars_offset", "local_vars_count",
               "return_value", "action", "fixed_param", "action_being_used", "script_overrides",
               "field_48", "how_much", "field_50")

_OBJECT_HEAD = struct.Struct(">21i")
_SCRIPT_TAIL = struct.Struct(">14i")
_EQUIP_FLAGS = {None: 0, "left": OBJECT_IN_LEFT_HAND, "right": OBJECT_IN_RIGHT_HAND, "worn": OBJECT_WORN}


def data_layout(pid, subtype, version=VERSION):
    """Names of the int32 words that follow an object's 0x54-byte common part.

    subtype is the proto's item / scenery sub-type (ignored for other types).
    Non-critters start with `data_flags` (objectDataRead, proto.cc:565-645).
    """
    obj_type = ids.pid_type(pid)
    if obj_type == ids.OBJ_TYPE_CRITTER:
        return CRITTER_DATA
    if obj_type == ids.OBJ_TYPE_ITEM:
        return ("data_flags",) + ITEM_DATA.get(subtype, ())
    if obj_type == ids.OBJ_TYPE_SCENERY:
        if subtype in (3, 4) and version == 19:
            return ("data_flags", "dest_built_tile")
        return ("data_flags",) + SCENERY_DATA.get(subtype, ())
    if ids.is_exit_grid(pid):
        return ("data_flags",) + EXIT_GRID_DATA
    return ("data_flags",)


class MapObject:
    """One object record.

    The 18 common fields are attributes (`OBJECT_FIELDS`). Type-specific words
    live in `data` and are reached by name: ``door["open_flags"]``,
    ``critter["hp"] = 30`` (names in `data_names`). `inventory` is a list of
    ``[quantity, MapObject]`` pairs.
    """

    __slots__ = OBJECT_FIELDS + ("inv_capacity", "inv_ptr", "data", "data_names", "inventory")

    def __repr__(self):
        return f"<MapObject id={self.id} pid=0x{self.pid & 0xFFFFFFFF:08X} tile={self.tile} elev={self.elevation}>"

    def __getitem__(self, name):
        try:
            return self.data[self.data_names.index(name)]
        except ValueError:
            raise KeyError(f"{self.kind} object has no data field {name!r} (has {self.data_names})") from None

    def __setitem__(self, name, value):
        try:
            self.data[self.data_names.index(name)] = value
        except ValueError:
            raise KeyError(f"{self.kind} object has no data field {name!r} (has {self.data_names})") from None

    def get(self, name, default=None):
        return self.data[self.data_names.index(name)] if name in self.data_names else default

    @property
    def obj_type(self):
        return ids.pid_type(self.pid)

    @property
    def kind(self):
        return ids.TYPE_NAMES[self.obj_type] if self.obj_type < len(ids.TYPE_NAMES) else "unknown"

    def items(self):
        """Inventory objects (without quantities)."""
        return [item for _, item in self.inventory]

    def walk(self):
        """This object and everything nested in its inventory."""
        yield self
        for _, item in self.inventory:
            yield from item.walk()


class Script:
    """One script record (scripts.cc:1956-2004).

    `built_tile` / `radius` exist only on spatial records, `time` only on timed
    ones; which one a record is depends on its own `sid`, also for the unused
    slots of an extent.
    """

    __slots__ = ("sid", "next", "built_tile", "radius", "time") + SCRIPT_TAIL

    def __init__(self, sid=0, index=0, owner_id=0, live=False):
        self.sid = sid
        self.next = -1 if live else 0
        self.built_tile = self.radius = self.time = 0
        for name in SCRIPT_TAIL:
            setattr(self, name, 0)
        self.index = index
        self.owner_id = owner_id
        if live:                                     # scriptAdd defaults = every vanilla live record
            self.local_vars_offset = -1
            self.action_being_used = -1

    def __repr__(self):
        return f"<Script sid=0x{self.sid & 0xFFFFFFFF:08X} index={self.index} owner={self.owner_id}>"

    @property
    def type(self):
        return ids.sid_type(self.sid)

    @property
    def tile(self):
        """Spatial scripts: trigger hex."""
        return ids.built_tile_parts(self.built_tile)[0]

    @property
    def elevation(self):
        return ids.built_tile_parts(self.built_tile)[1]

    @classmethod
    def _read(cls, data, pos):
        self = cls.__new__(cls)
        self.sid, self.next = struct.unpack_from(">2i", data, pos)
        pos += 8
        self.built_tile = self.radius = self.time = 0
        script_type = ids.sid_type(self.sid)
        if script_type == ids.SCRIPT_TYPE_SPATIAL:
            self.built_tile, self.radius = struct.unpack_from(">2i", data, pos)
            pos += 8
        elif script_type == ids.SCRIPT_TYPE_TIMED:
            (self.time,) = struct.unpack_from(">i", data, pos)
            pos += 4
        for name, value in zip(SCRIPT_TAIL, _SCRIPT_TAIL.unpack_from(data, pos)):
            setattr(self, name, value)
        return self, pos + _SCRIPT_TAIL.size

    def _write(self, out):
        s32 = ids.s32
        out.append(struct.pack(">2i", s32(self.sid), s32(self.next)))
        script_type = ids.sid_type(self.sid)
        if script_type == ids.SCRIPT_TYPE_SPATIAL:
            out.append(struct.pack(">2i", s32(self.built_tile), s32(self.radius)))
        elif script_type == ids.SCRIPT_TYPE_TIMED:
            out.append(struct.pack(">i", s32(self.time)))
        out.append(_SCRIPT_TAIL.pack(*(s32(getattr(self, name)) for name in SCRIPT_TAIL)))


class ScriptExtent:
    """16 script slots of which the first `length` are live."""

    __slots__ = ("slots", "length", "next")

    def __init__(self):
        self.slots = [Script() for _ in range(EXTENT_SIZE)]
        self.length = 0
        self.next = 0


class ScriptList:
    """All scripts of one type: `count` live records spread over extents of 16."""

    __slots__ = ("count", "extents")

    def __init__(self):
        self.count = 0
        self.extents = []

    def live(self):
        return [slot for extent in self.extents for slot in extent.slots[:max(0, min(extent.length, EXTENT_SIZE))]]

    def _set_live(self, scripts):
        self.extents = []
        self.count = len(scripts)
        for start in range(0, len(scripts), EXTENT_SIZE):
            extent = ScriptExtent()
            chunk = scripts[start:start + EXTENT_SIZE]
            extent.slots[:len(chunk)] = chunk
            extent.length = len(chunk)
            self.extents.append(extent)


class MapFile:
    """A map: header fields, map variables, squares, scripts and objects.

    Attributes
        version, entering_tile, entering_elevation, entering_rotation,
        script_index (map script, 1-based, 0 = none), flags, darkness, index,
        last_visit_time, reserved (44 ints)
        name            header file name, e.g. 'ARVILLAG.MAP' (`name_raw`: the 16 bytes)
        global_vars     map variables (MVARs); local_vars: script local pool
        tiles           {elevation: (10000,) uint32 array}; a missing key means
                        the elevation has no squares (header flag bits 2/4/8)
        script_lists    5 `ScriptList` (system, spatial, timed, item, critter)
        objects         3 lists of top-level `MapObject`, one per elevation
        sort_on_write   order objects by tile when serialising, as the game's
                        own saver does (True for new maps, False for parsed ones)
    """

    def __init__(self, gamefiles=None):
        self.gf = gamefiles
        self.version = VERSION
        self.name_raw = bytes(16)
        self.entering_tile = 20100
        self.entering_elevation = 0
        self.entering_rotation = 0
        self.script_index = 0
        self.flags = 0
        self.darkness = 1
        self.index = -1
        self.last_visit_time = 0
        self.reserved = [0] * 44
        self.global_vars = []
        self.local_vars = []
        self.tiles = {}
        self.script_lists = [ScriptList() for _ in range(5)]
        self.objects = [[] for _ in range(ELEVATION_COUNT)]
        self.sort_on_write = False
        self._raw_counts = (0, 0)
        self._layouts = {}
        self._used_ids = None
        self._next_id = 0

    # ------------------------------------------------------------------ names
    @property
    def name(self):
        return self.name_raw.split(b"\0", 1)[0].decode("latin-1")

    @name.setter
    def name(self, value):
        value = value.upper()
        if not value.endswith(".MAP"):
            value += ".MAP"
        encoded = value.encode("latin-1")
        if len(encoded) > 12:
            raise ValueError(f"map name {value!r} does not fit 8.3")
        self.name_raw = encoded.ljust(16, b"\0")

    @property
    def base_name(self):
        """Lower-case name without extension, as written in maps.txt (map_name=)."""
        return self.name.lower().split(".", 1)[0]

    @property
    def file_name(self):
        return self.base_name + ".map"

    # --------------------------------------------------------------- creation
    @classmethod
    def new(cls, name, gamefiles):
        """Empty single-elevation map (elevations 1 and 2 flagged absent)."""
        self = cls(gamefiles)
        self.name = name
        self.tiles[0] = np.full(geometry.SQUARE_COUNT, EMPTY_SQUARE, dtype=np.uint32)
        self.sort_on_write = True
        return self

    @classmethod
    def load(cls, name, gamefiles):
        """Parse maps/<name> from the game tree."""
        file_name = name if "." in name else name + ".map"
        return cls.from_bytes(gamefiles.read("maps/" + file_name), gamefiles)

    def add_elevation(self, elevation):
        """Give an elevation a (blank) square block."""
        if elevation not in self.tiles:
            self.tiles[elevation] = np.full(geometry.SQUARE_COUNT, EMPTY_SQUARE, dtype=np.uint32)

    # ---------------------------------------------------------------- parsing
    def _layout(self, pid):
        layout = self._layouts.get(pid)
        if layout is None:
            subtype = None
            if ids.pid_type(pid) in (ids.OBJ_TYPE_ITEM, ids.OBJ_TYPE_SCENERY):
                if self.gf is None:
                    raise ValueError("a GameFiles tree is needed to size item and scenery objects")
                subtype = self.gf.protos.subtype(pid)
            layout = self._layouts[pid] = data_layout(pid, subtype, self.version)
        return layout

    def _read_object(self, data, pos):
        obj = MapObject()
        values = _OBJECT_HEAD.unpack_from(data, pos)
        pos += _OBJECT_HEAD.size
        (obj.id, obj.tile, obj.x, obj.y, obj.sx, obj.sy, obj.frame, obj.rotation, obj.fid, obj.flags,
         obj.elevation, obj.pid, obj.cid, obj.light_distance, obj.light_intensity, obj.outline, obj.sid,
         obj.script_index, inv_length, obj.inv_capacity, obj.inv_ptr) = values
        obj.data_names = names = self._layout(obj.pid)
        obj.data = list(struct.unpack_from(f">{len(names)}i", data, pos))
        pos += 4 * len(names)
        obj.inventory = []
        for _ in range(inv_length):
            (quantity,) = struct.unpack_from(">i", data, pos)
            item, pos = self._read_object(data, pos + 4)
            obj.inventory.append([quantity, item])
        return obj, pos

    @classmethod
    def from_bytes(cls, data, gamefiles):
        """Parse a map. `gamefiles` supplies the protos that size item / scenery records."""
        self = cls(gamefiles)
        (self.version,) = struct.unpack_from(">i", data, 0)
        if self.version not in (19, 20):
            raise ValueError(f"unsupported map version {self.version}")
        self.name_raw = bytes(data[4:20])
        (self.entering_tile, self.entering_elevation, self.entering_rotation, local_count, self.script_index,
         self.flags, self.darkness, global_count, self.index) = struct.unpack_from(">9i", data, 0x14)
        (self.last_visit_time,) = struct.unpack_from(">I", data, 0x38)
        self.reserved = list(struct.unpack_from(">44i", data, 0x3C))
        self._raw_counts = (global_count, local_count)
        pos = HEADER_SIZE
        self.global_vars = list(struct.unpack_from(f">{max(global_count, 0)}i", data, pos))
        pos += 4 * len(self.global_vars)
        self.local_vars = list(struct.unpack_from(f">{max(local_count, 0)}i", data, pos))
        pos += 4 * len(self.local_vars)

        for elevation in range(ELEVATION_COUNT):
            if not self.flags & ELEVATION_ABSENT[elevation]:
                block = np.frombuffer(data, dtype=">u4", count=geometry.SQUARE_COUNT, offset=pos)
                self.tiles[elevation] = block.astype(np.uint32)
                pos += 4 * geometry.SQUARE_COUNT

        for script_list in self.script_lists:
            (script_list.count,) = struct.unpack_from(">i", data, pos)
            pos += 4
            for _ in range((script_list.count + EXTENT_SIZE - 1) // EXTENT_SIZE if script_list.count > 0 else 0):
                extent = ScriptExtent()
                for slot in range(EXTENT_SIZE):
                    extent.slots[slot], pos = Script._read(data, pos)
                extent.length, extent.next = struct.unpack_from(">2i", data, pos)
                pos += 8
                script_list.extents.append(extent)

        (total,) = struct.unpack_from(">i", data, pos)
        pos += 4
        for elevation in range(ELEVATION_COUNT):
            (count,) = struct.unpack_from(">i", data, pos)
            pos += 4
            block = self.objects[elevation]
            for _ in range(count):
                obj, pos = self._read_object(data, pos)
                block.append(obj)
        if total != sum(len(block) for block in self.objects):
            raise ValueError("object total does not match the per-elevation counts")
        if pos != len(data):
            raise ValueError(f"{len(data) - pos} trailing bytes after the object section")
        return self

    # ------------------------------------------------------------ serialising
    def _write_object(self, obj, out):
        s32 = ids.s32
        out.append(_OBJECT_HEAD.pack(
            s32(obj.id), s32(obj.tile), s32(obj.x), s32(obj.y), s32(obj.sx), s32(obj.sy), s32(obj.frame),
            s32(obj.rotation), s32(obj.fid), s32(obj.flags), s32(obj.elevation), s32(obj.pid), s32(obj.cid),
            s32(obj.light_distance), s32(obj.light_intensity), s32(obj.outline), s32(obj.sid),
            s32(obj.script_index), len(obj.inventory), s32(obj.inv_capacity), s32(obj.inv_ptr)))
        out.append(struct.pack(f">{len(obj.data)}i", *(s32(v) for v in obj.data)))
        for quantity, item in obj.inventory:
            out.append(struct.pack(">i", quantity))
            self._write_object(item, out)

    def to_bytes(self):
        global_count, local_count = self._raw_counts
        if global_count >= 0:
            global_count = len(self.global_vars)
        if local_count >= 0:
            local_count = len(self.local_vars)
        flags = self.flags & ~sum(ELEVATION_ABSENT)
        for elevation in range(ELEVATION_COUNT):
            if elevation not in self.tiles:
                flags |= ELEVATION_ABSENT[elevation]

        s32 = ids.s32
        out = [struct.pack(">i", self.version), self.name_raw,
               struct.pack(">9i", self.entering_tile, self.entering_elevation, self.entering_rotation, local_count,
                           self.script_index, s32(flags), self.darkness, global_count, self.index),
               struct.pack(">I", self.last_visit_time & 0xFFFFFFFF),
               struct.pack(">44i", *(s32(v) for v in self.reserved)),
               struct.pack(f">{len(self.global_vars)}i", *(s32(v) for v in self.global_vars)),
               struct.pack(f">{len(self.local_vars)}i", *(s32(v) for v in self.local_vars))]
        for elevation in range(ELEVATION_COUNT):
            if elevation in self.tiles:
                squares = np.asarray(self.tiles[elevation])
                if squares.shape != (geometry.SQUARE_COUNT,):
                    raise ValueError(f"elevation {elevation}: expected {geometry.SQUARE_COUNT} squares")
                out.append(squares.astype(">u4").tobytes())
        for script_list in self.script_lists:
            out.append(struct.pack(">i", script_list.count))
            for extent in script_list.extents:
                for slot in extent.slots:
                    slot._write(out)
                out.append(struct.pack(">2i", extent.length, s32(extent.next)))
        out.append(struct.pack(">i", sum(len(block) for block in self.objects)))
        for block in self.objects:
            if self.sort_on_write:
                block = sorted(block, key=lambda obj: obj.tile)
            out.append(struct.pack(">i", len(block)))
            for obj in block:
                self._write_object(obj, out)
        return b"".join(out)

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self.to_bytes())

    # ----------------------------------------------------------------- squares
    def tile_id(self, tile):
        """Accepts a tiles.lst index or an art file name ('edg5000.frm')."""
        if isinstance(tile, str):
            tile = self.gf.art_list(ids.OBJ_TYPE_TILE).index(tile)
        if not 0 <= tile <= 0xFFF:
            raise ValueError(f"tile id {tile} does not fit 12 bits")
        return tile

    def _square(self, x, y, elevation):
        if not (0 <= x < geometry.SQUARE_WIDTH and 0 <= y < geometry.SQUARE_HEIGHT):
            raise ValueError(f"square ({x}, {y}) is outside the 100x100 grid")
        if elevation not in self.tiles:
            raise ValueError(f"elevation {elevation} has no squares (use add_elevation)")
        return y * geometry.SQUARE_WIDTH + x

    def floor(self, x, y, elevation=0):
        return int(self.tiles[elevation][self._square(x, y, elevation)]) & 0xFFF

    def roof(self, x, y, elevation=0):
        return (int(self.tiles[elevation][self._square(x, y, elevation)]) >> 16) & 0xFFF

    def set_floor(self, x, y, tile, elevation=0):
        """Floor of square (x, y); x grows to the screen left, y down-right."""
        square = self._square(x, y, elevation)
        word = int(self.tiles[elevation][square])
        self.tiles[elevation][square] = (word & 0xFFFF0000) | self.tile_id(tile)

    def set_roof(self, x, y, tile, elevation=0):
        square = self._square(x, y, elevation)
        word = int(self.tiles[elevation][square])
        self.tiles[elevation][square] = (word & 0x0000FFFF) | (self.tile_id(tile) << 16)

    def _fill(self, setter, x0, y0, x1, y1, tile, elevation):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                chosen = tile(x, y) if callable(tile) else tile
                if chosen is not None:
                    setter(x, y, chosen, elevation)

    def fill_floor(self, x0, y0, x1, y1, tile, elevation=0):
        """Set every floor square of the inclusive box; `tile` may be f(x, y) -> id | name | None."""
        self._fill(self.set_floor, x0, y0, x1, y1, tile, elevation)

    def fill_roof(self, x0, y0, x1, y1, tile, elevation=0):
        self._fill(self.set_roof, x0, y0, x1, y1, tile, elevation)

    # ----------------------------------------------------------------- objects
    def all_objects(self, elevation=None, nested=False):
        """Top-level objects (of one elevation or all); nested=True adds inventory contents."""
        blocks = self.objects if elevation is None else [self.objects[elevation]]
        for block in blocks:
            for obj in block:
                if nested:
                    yield from obj.walk()
                else:
                    yield obj

    def objects_at(self, tile, elevation=0):
        return [obj for obj in self.objects[elevation] if obj.tile == tile]

    def new_object_id(self):
        """An object id no object of this map uses, below the party range.

        Unique ids matter: the engine finds the owner of a saved timer event by id.
        """
        if self._used_ids is None:
            self._used_ids = {obj.id for obj in self.all_objects(nested=True)}
        value = self._next_id
        for _ in range(PLAYER_ID - 1):
            value = value % (PLAYER_ID - 1) + 1          # cycles through 1 .. PLAYER_ID - 1
            if value not in self._used_ids:
                self._used_ids.add(value)
                self._next_id = value
                return value
        raise ValueError("no free object id below the party range")

    def _make_object(self, pid, tile, elevation, rotation, fields):
        if self.gf is None:
            raise ValueError("a GameFiles tree is needed to create objects")
        proto = self.gf.protos.get(pid)
        obj = MapObject()
        obj.id = self.new_object_id()
        obj.tile = tile
        obj.x = obj.y = obj.sx = obj.sy = obj.frame = 0
        obj.rotation = rotation
        obj.fid = proto.fid
        obj.elevation = elevation
        obj.pid = pid
        obj.cid = -1
        obj.outline = 0
        obj.sid = obj.script_index = -1
        obj.inv_capacity = obj.inv_ptr = 0
        obj.inventory = []
        if proto.obj_type == ids.OBJ_TYPE_TILE:
            obj.light_distance = obj.light_intensity = 0
        else:
            # objectSetLight: distance capped at 8, no light without intensity.
            obj.light_intensity = max(proto.light_intensity, 0)
            obj.light_distance = min(proto.light_distance, 8) if obj.light_intensity else 0
        obj.flags = proto.object_flags() | (OBJECT_LIGHTING if obj.light_intensity else 0)

        obj.data_names = names = self._layout(pid)
        obj.data = [0] * len(names)
        if proto.obj_type == ids.OBJ_TYPE_CRITTER:
            obj["ap"] = proto.max_ap
            obj["hp"] = proto.max_hp
            obj["ai_packet"] = proto.ai_packet
            obj["team"] = proto.team
            obj["who_hit_me"] = -1
        elif proto.obj_type == ids.OBJ_TYPE_ITEM:
            sub = proto.subtype_name
            if sub == "weapon":
                obj["ammo_quantity"] = proto.ammo_capacity
                obj["ammo_type_pid"] = proto.ammo_type_pid
            elif sub == "ammo":
                obj["quantity"] = proto.quantity
            elif sub == "misc":
                obj["charges"] = proto.charges
            elif sub == "key":
                obj["key_code"] = proto.key_code
        elif proto.obj_type == ids.OBJ_TYPE_SCENERY:
            sub = proto.subtype_name
            if sub == "door":
                obj["open_flags"] = proto.open_flags
            elif sub == "stairs":
                obj["dest_built_tile"] = proto.dest_built_tile
                obj["dest_map"] = proto.dest_map
            elif sub == "elevator":
                obj["elevator_type"] = proto.elevator_type
                obj["elevator_level"] = proto.elevator_level
            elif sub in ("ladder_up", "ladder_down"):
                # Not the proto's value: every retail ladder proto holds -1 there, and a ladder with a
                # non-zero map leaves the map (-1 = town map) instead of moving the user within it.
                obj["dest_map"] = 0
                obj["dest_built_tile"] = -1              # unusable until a destination is set
        elif ids.is_exit_grid(pid):
            obj["dest_map"] = -2                         # world map
            obj["dest_tile"] = -1

        for name, value in fields.items():
            if name in OBJECT_FIELDS:
                setattr(obj, name, value)
            elif name in names:
                obj[name] = value
            else:
                raise TypeError(f"{obj.kind} objects have no field {name!r}")
        if obj.light_intensity > 0:
            obj.flags |= OBJECT_LIGHTING
        if ids.is_exit_grid(pid) and obj["dest_map"] <= 0 and "fid" not in fields and (obj.fid & 0xFFF) < 33:
            obj.fid += 16                                # world-map exits use the green art (object.cc:442-447)
        obj.flags = ids.s32(obj.flags)                   # signed like every parsed field, so built == re-read
        return obj

    def add_object(self, pid, tile, elevation=0, rotation=0, script=None, **fields):
        """Place an object built from its proto and return it.

        Defaults follow the engine's own object creation: fid, flags and light
        from the proto; critters at full hit / action points with the proto's
        AI packet and team; weapons loaded, ammo / misc items with the proto's
        quantity / charges; doors with the proto's open flags; exit grids
        leading to the world map; stairs and ladders without a destination
        (`set_destination`). Override any common field (`OBJECT_FIELDS`)
        or data word (`MapObject.data_names`) by keyword, e.g. ``frame=1``,
        ``flags=...``, ``open_flags=LOCKED``, ``dest_map=4``. `script` attaches
        a script by scripts.lst name or 0-based index.
        """
        if not 0 <= elevation < ELEVATION_COUNT:
            raise ValueError(f"elevation {elevation} is out of range")
        obj = self._make_object(pid, tile, elevation, rotation, fields)
        self.objects[elevation].append(obj)
        if script is not None:
            self.attach_script(obj, script)
        return obj

    def add_item(self, owner, pid, quantity=1, equipped=None, **fields):
        """Put an item into `owner`'s inventory (critter or container); returns the item object.

        `owner` may itself be a carried container (a bag inside a chest).
        equipped: None, 'left', 'right' (hands) or 'worn' (armor) for critters.
        The right hand is the one a non-player critter fights with: a weapon
        put there also switches the critter to its armed standing art (the
        weapon bits of the FID), as in the retail maps - otherwise it is
        drawn unarmed and has no attack animation for that weapon.
        """
        if ids.pid_type(pid) != ids.OBJ_TYPE_ITEM:
            raise ValueError("only items can be carried")
        item = self._make_object(pid, -1, owner.elevation, 0, fields)
        item.flags |= _EQUIP_FLAGS[equipped]
        owner.inventory.append([quantity, item])
        owner.inv_capacity = max(owner.inv_capacity, 10, len(owner.inventory))
        if equipped == "right" and owner.obj_type == ids.OBJ_TYPE_CRITTER:
            self._wield(owner, item)
        return item

    def _wield(self, critter, item):
        """FID change of _invenWieldFunc (inventory.cc:3269): only for a critter standing unarmed
        and only when its art has frames for the weapon's animation code."""
        proto = self.gf.protos.get(item.pid)
        if proto.subtype_name != "weapon" or not proto.anim_code:
            return
        if ids.fid_anim(critter.fid) or ids.fid_weapon(critter.fid) or ids.fid_rotation(critter.fid):
            return
        armed = ids.make_fid(ids.OBJ_TYPE_CRITTER, ids.fid_index(critter.fid), weapon=proto.anim_code)
        if self.gf.art.exists(armed):
            critter.fid = armed

    def add_exit_grid(self, tile, dest_map=-2, dest_tile=-1, dest_elevation=0, dest_rotation=0, elevation=0, shape=0):
        """Exit grid hex. dest_map: maps.txt index, -2 world map, -1 town map; shape 0..7 picks the art.

        With dest_tile -1 the destination map's own entering tile is used.
        """
        return self.add_object(ids.EXIT_GRID_FIRST_PID + shape, tile, elevation, dest_map=dest_map,
                               dest_tile=dest_tile, dest_elevation=dest_elevation, dest_rotation=dest_rotation)

    def add_scroll_blocker(self, tile, elevation=0):
        """Invisible marker the view centre cannot move onto."""
        return self.add_object(ids.SCROLL_BLOCKER_PID, tile, elevation)

    def set_destination(self, obj, tile, elevation=0, rotation=0, dest_map=None):
        """Where stairs or a ladder take their user (hides their different word order).

        dest_map None stays on this map (`elevation` is then the elevation to
        go to); otherwise it is the maps.txt index of another map. `rotation`
        is the direction the player faces after a map change.
        """
        sub = self.gf.protos.get(obj.pid).subtype_name if obj.obj_type == ids.OBJ_TYPE_SCENERY else ""
        if sub not in ("stairs", "ladder_up", "ladder_down"):
            raise ValueError(f"{obj!r} is neither stairs nor a ladder")
        if dest_map is None:
            # "same map" is spelt differently: stairs change map when dest_map > 0, ladders
            # when it is non-zero (proto_instance.cc:1510-1609); these are the retail values.
            dest_map = -1 if sub == "stairs" else 0
        elif dest_map <= 0:
            raise ValueError("dest_map must be a positive maps.txt index (None = this map)")
        obj["dest_map"] = dest_map
        obj["dest_built_tile"] = ids.built_tile(tile, elevation, rotation)

    def lock(self, obj, locked=True):
        """Set or clear the lock flag of a door or container (it lives in a different word for each).

        What the engine does with it: a locked container refuses to open ("It
        is locked."). A locked door only plays the locked sound and opens all
        the same unless its script overrides the use (both checked in the
        running game, tools/tests/test_engine.py). The stock door scripts such
        as ZIWodDor do override it, but they also force their own compiled-in
        lock state whenever the map is entered, and nothing in the engine
        picks a lock - that is always the object's script
        (use_skill_on_p_proc; proto_instance.cc:1710, skill.cc:837).
        """
        proto = self.gf.protos.get(obj.pid)
        if proto.subtype_name == "door":
            name = "open_flags"
        elif proto.subtype_name == "container":
            name = "data_flags"
        else:
            raise ValueError(f"{obj!r} is neither a door nor a container")
        obj[name] = ids.s32((obj[name] | LOCKED) if locked else (obj[name] & ~LOCKED))

    def open_door(self, door):
        """Make a door stand open, exactly as the game saves one it has opened: open bit, last
        animation frame, passable and transparent to light and shots, and the object's x / y moved
        by the offsets of the frames played (closing the door subtracts them again)."""
        if self.gf.protos.get(door.pid).subtype_name != "door":
            raise ValueError(f"{door!r} is not a door")
        frames = self.gf.art.load(door.fid).frames(door.rotation)
        for frame in frames[door.frame + 1:]:
            door.x += frame.x
            door.y += frame.y
        door.frame = len(frames) - 1
        door["open_flags"] |= DOOR_OPEN
        door.flags = ids.s32(door.flags | OBJECT_OPEN_DOOR)

    def remove_object(self, obj):
        """Remove a top-level object together with its script record."""
        self.objects[obj.elevation].remove(obj)
        if obj.sid != -1 and ids.sid_type(obj.sid) < len(self.script_lists):
            script_list = self.script_lists[ids.sid_type(obj.sid)]
            script_list._set_live([s for s in script_list.live() if s.sid != obj.sid])

    # ----------------------------------------------------------------- scripts
    def script_number(self, script):
        """0-based scripts.lst index from a name ('acguard', 'acguard.int') or an index."""
        if isinstance(script, str):
            return self.gf.scripts.index(script)
        return script

    def scripts(self, script_type=None):
        """Live script records of one type, or of all types."""
        lists = self.script_lists if script_type is None else [self.script_lists[script_type]]
        return [script for script_list in lists for script in script_list.live()]

    def find_script(self, sid):
        if sid == -1 or not 0 <= ids.sid_type(sid) < len(self.script_lists):
            return None
        for script in self.script_lists[ids.sid_type(sid)].live():
            if script.sid == sid:
                return script
        return None

    def _add_script(self, script_type, index, owner_id):
        script_list = self.script_lists[script_type]
        used = {script.sid & 0xFFFFFF for script in script_list.live()}
        number = next(n for n in range(len(used) + 1) if n not in used)
        script = Script(ids.make_sid(script_type, number), index, owner_id, live=True)
        script_list._set_live(script_list.live() + [script])
        return script

    def attach_script(self, obj, script):
        """Give a top-level object a script (list: critter for critters, item for everything else).

        The loader only links scripts that have a record in the map file - a
        script named in the proto is NOT attached automatically.
        """
        if obj.sid != -1:
            raise ValueError(f"{obj!r} already has a script")
        index = self.script_number(script)
        script_type = ids.SCRIPT_TYPE_CRITTER if obj.obj_type == ids.OBJ_TYPE_CRITTER else ids.SCRIPT_TYPE_ITEM
        record = self._add_script(script_type, index, obj.id)
        obj.sid = record.sid
        obj.script_index = index
        return record

    def add_spatial_script(self, script, tile, elevation=0, radius=0):
        """Script whose spatial_p_proc fires when something walks within `radius` hexes of `tile`."""
        record = self._add_script(ids.SCRIPT_TYPE_SPATIAL, self.script_number(script), -1)
        record.built_tile = ids.built_tile(tile, elevation)
        record.radius = radius
        return record

    def set_map_script(self, script):
        """Map script by scripts.lst name or 0-based index; None removes it."""
        self.script_index = 0 if script is None else self.script_number(script) + 1

    def set_entrance(self, tile, elevation=0, rotation=0):
        """Where the player appears when no explicit destination is given."""
        self.entering_tile = tile
        self.entering_elevation = elevation
        self.entering_rotation = rotation

    # -------------------------------------------------------------- validation
    def _check_destination(self, obj, where, is_ladder, map_count, error, warning):
        """Stairs / ladder destination (useStairs, useLadderUp, useLadderDown in proto_instance.cc)."""
        dest_map = obj["dest_map"]
        if obj["dest_built_tile"] == -1:
            warning(f"{where}: no destination set, using it does nothing (see MapFile.set_destination)")
            return
        tile, dest_elevation, _ = ids.built_tile_parts(obj["dest_built_tile"])
        if not geometry.is_valid(tile) or dest_elevation >= ELEVATION_COUNT:
            error(f"{where}: destination tile {tile} / elevation {dest_elevation} is invalid")
        elif dest_map > 0:
            if map_count is not None and dest_map >= map_count:
                error(f"{where}: leads to map {dest_map}, maps.txt has {map_count} maps")
        elif is_ladder and dest_map != 0:
            # Ladders (unlike stairs) treat every non-zero map as a map change; -1 and -2 are the map screens.
            warning(f"{where}: ladder with destination map {dest_map} leaves the map for the "
                    f"{'town' if dest_map == -1 else 'world'} map; use 0 to stay on this map")
        elif dest_elevation not in self.tiles:
            warning(f"{where}: leads to elevation {dest_elevation}, which has no squares")

    def validate(self):
        """Check everything the engine assumes but does not verify.

        Returns a list of strings, each starting with ``error:`` (the map can
        fail to load, crash the engine or corrupt memory) or ``warning:``
        (legal but almost certainly not intended). Checks that need game data
        (protos, art, scripts.lst, maps.txt, .gam) run when the map has a
        `GameFiles` tree.
        """
        problems = []
        error = lambda text: problems.append("error: " + text)
        warning = lambda text: problems.append("warning: " + text)
        gf = self.gf

        # --- header
        if self.version not in (19, 20):
            error(f"version {self.version} is not 19 or 20")
        raw_name = self.name_raw
        if len(raw_name) != 16 or b"\0" not in raw_name:
            error("header name is not a NUL-terminated 16-byte field")
        name = self.name
        if not name.upper().endswith(".MAP") and not name.upper().endswith(".SAV"):
            error(f"header name {name!r} has no .MAP extension (the engine derives the .GAM path and map index from it)")
        if len(self.base_name) > 8 or not self.base_name:
            error(f"map base name {self.base_name!r} must be 1..8 characters")
        if self.flags & FLAG_SAVEGAME:
            warning("header flag 0x1 (saved game) is set: script locals are kept and the .GAM is not loaded")
        if not 0 <= self.entering_elevation < ELEVATION_COUNT:
            error(f"entering elevation {self.entering_elevation} is outside 0..2")
        elif self.entering_elevation not in self.tiles:
            warning(f"entering elevation {self.entering_elevation} has no squares")
        if not geometry.is_valid(self.entering_tile):
            error(f"entering tile {self.entering_tile} is outside 0..39999")
        elif not geometry.can_center(self.entering_tile):
            hx, hy = geometry.tile_xy(self.entering_tile)
            error(f"entering tile {self.entering_tile} (hx {hx}, hy {hy}) cannot be a view centre: need "
                  f"{geometry.CENTER_HX[0]} <= hx <= {geometry.CENTER_HX[1]} and "
                  f"{geometry.CENTER_HY[0]} <= hy <= {geometry.CENTER_HY[1]} (map load fails)")
        if not 0 <= self.entering_rotation < 6:
            warning(f"entering rotation {self.entering_rotation} is outside 0..5")
        if not self.tiles:
            warning("no elevation has squares")

        # --- map variables
        global_count, local_count = self._raw_counts
        if global_count < 0 or local_count < 0:
            warning("negative variable count in the header")
        if gf is not None:
            gam_path = f"maps/{self.base_name}.gam"
            if gf.exists(gam_path):
                declared = len(gam.parse(gf.read(gam_path)))
                if declared > len(self.global_vars):
                    error(f"{gam_path} declares {declared} variables but the map has {len(self.global_vars)} "
                          "global vars (out-of-bounds access in fallout2-ce)")
            maps_txt = "data/maps.txt"
            if gf.exists(maps_txt):
                registered = mapstxt.map_names(gf.read(maps_txt))
                if self.base_name not in registered:
                    error(f"map_name={self.base_name} is not registered in {maps_txt}: the map index becomes -1 "
                          "and the engine indexes its map table out of bounds")
                elif registered.index(self.base_name) >= mapstxt.AUTOMAP_MAP_COUNT:
                    error(f"maps.txt index {registered.index(self.base_name)} exceeds the automap table (160 maps)")
                map_count = len(registered)
            else:
                map_count = None
            script_count = len(gf.scripts) if gf.exists("scripts/scripts.lst") else None
            tile_count = len(gf.art_list(ids.OBJ_TYPE_TILE))
        else:
            map_count = script_count = tile_count = None

        # --- squares
        for elevation, squares in sorted(self.tiles.items()):
            squares = np.asarray(squares)
            if squares.shape != (geometry.SQUARE_COUNT,):
                error(f"elevation {elevation}: square block has shape {squares.shape}, expected (10000,)")
                continue
            floors = squares & 0xFFF
            roofs = (squares >> 16) & 0xFFF
            if (squares & 0xF000F000).any():
                warning(f"elevation {elevation}: {int(((squares & 0xF000F000) != 0).sum())} squares carry flag bits")
            if (floors == 0).any() or (roofs == 0).any():
                warning(f"elevation {elevation}: tile id 0 (reserved.frm) is used; the empty tile is id {NO_TILE}")
            if tile_count is not None:
                top = int(max(floors.max(), roofs.max()))
                if top >= tile_count:
                    error(f"elevation {elevation}: tile id {top} is beyond art/tiles/tiles.lst ({tile_count} entries)")
                else:
                    for tile in sorted(set(np.unique(floors).tolist()) | set(np.unique(roofs).tolist())):
                        if not gf.art.exists(ids.make_fid(ids.OBJ_TYPE_TILE, tile)):
                            warning(f"elevation {elevation}: tile id {tile} has no art file")

        # --- scripts
        if script_count is not None and self.script_index > script_count:
            error(f"map script index {self.script_index} is beyond scripts.lst ({script_count} lines)")
        if self.script_index < 0:
            warning(f"map script index {self.script_index} is negative (treated as none)")
        for script_type, script_list in enumerate(self.script_lists):
            label = ids.SCRIPT_TYPE_NAMES[script_type]
            lengths = [extent.length for extent in script_list.extents]
            expected = (script_list.count + EXTENT_SIZE - 1) // EXTENT_SIZE if script_list.count > 0 else 0
            if len(script_list.extents) != expected:
                error(f"{label} scripts: {len(script_list.extents)} extents for count {script_list.count}")
            if any(not 0 <= length <= EXTENT_SIZE for length in lengths):
                error(f"{label} scripts: extent length outside 0..16")
                continue
            if sum(lengths) != script_list.count:
                error(f"{label} scripts: extent lengths sum to {sum(lengths)}, count says {script_list.count}")
            if any(length != EXTENT_SIZE for length in lengths[:-1]):
                error(f"{label} scripts: only the last extent may be partly filled")
            if lengths and lengths[-1] == 0:
                error(f"{label} scripts: last extent is empty")
            seen = set()
            for script in script_list.live():
                if script.type != script_type:
                    error(f"{label} scripts: record sid 0x{script.sid & 0xFFFFFFFF:08X} has type {script.type}")
                if script.sid in seen:
                    error(f"{label} scripts: sid 0x{script.sid & 0xFFFFFFFF:08X} is used twice")
                seen.add(script.sid)
                if script.index < 0 or (script_count is not None and script.index >= script_count):
                    error(f"{label} script 0x{script.sid & 0xFFFFFFFF:08X}: index {script.index} is outside scripts.lst")
                if script.local_vars_offset != -1 and not self.flags & FLAG_SAVEGAME \
                        and script.local_vars_offset + script.local_vars_count > len(self.local_vars):
                    warning(f"{label} script 0x{script.sid & 0xFFFFFFFF:08X}: local vars beyond the map's local pool")
                if script_type == ids.SCRIPT_TYPE_SPATIAL:
                    tile, elevation, _ = ids.built_tile_parts(script.built_tile)
                    if not geometry.is_valid(tile) or elevation >= ELEVATION_COUNT:
                        error(f"spatial script 0x{script.sid & 0xFFFFFFFF:08X}: bad position (tile {tile}, elevation {elevation})")
                    elif tile < 10:
                        warning(f"spatial script 0x{script.sid & 0xFFFFFFFF:08X}: tiles below 10 never trigger")

        # --- objects
        top_level = list(self.all_objects())
        if top_level and all(ids.fid_type(obj.fid) == ids.OBJ_TYPE_WALL for obj in top_level):
            error("every top-level object is a wall: the art preloader scans past the start of its table")
        owners = {}
        seen_ids = {}
        protos = gf.protos if gf is not None else None
        art = gf.art if gf is not None else None
        for elevation, block in enumerate(self.objects):
            if block and elevation not in self.tiles:
                warning(f"elevation {elevation} has {len(block)} objects but no squares")
            for top in block:
                if top.elevation != elevation:
                    warning(f"{top!r}: elevation field {top.elevation} differs from its block {elevation}")
                if not geometry.is_valid(top.tile):
                    error(f"{top!r}: tile {top.tile} is outside 0..39999")
                for obj in top.walk():
                    nested = obj is not top
                    where = f"{obj!r}" + (f" (inside {top!r})" if nested else "")
                    seen_ids.setdefault(obj.id, []).append(obj)
                    if obj.id >= PLAYER_ID:
                        warning(f"{where}: id is in the party range (>= {PLAYER_ID})")
                    obj_type = obj.obj_type
                    if obj.pid == -1:
                        # The engine's own hidden helpers (owners of spatial scripts) in saved maps.
                        warning(f"{where}: no prototype (PID -1); only the engine creates such objects")
                        continue
                    if obj_type >= ids.PROTO_TYPE_COUNT:
                        error(f"{where}: PID type {obj_type} has no prototypes")
                        continue
                    if protos is not None:
                        if not protos.exists(obj.pid):
                            error(f"{where}: prototype does not exist" + (" (map load fails)" if obj_type in (0, 2) else ""))
                            continue
                        expected_names = self._layout(obj.pid)
                        if len(obj.data) != len(expected_names):
                            error(f"{where}: {len(obj.data)} data words, the proto requires {len(expected_names)}")
                    if ids.fid_type(obj.fid) != obj_type:
                        warning(f"{where}: FID type {ids.fid_type(obj.fid)} differs from PID type {obj_type}")
                    if art is not None and not art.exists(obj.fid):
                        (error if nested else warning)(f"{where}: FID 0x{obj.fid & 0xFFFFFFFF:08X} has no art file")
                    if not 0 <= obj.rotation < 6:
                        warning(f"{where}: rotation {obj.rotation} is outside 0..5")
                    if obj.light_intensity > 0 and not obj.flags & OBJECT_LIGHTING and not nested:
                        warning(f"{where}: has light intensity but not the LIGHTING flag (0x20), so it emits nothing")
                    if len(obj.inventory) > 0 and obj.inv_capacity < len(obj.inventory):
                        error(f"{where}: inventory capacity {obj.inv_capacity} < {len(obj.inventory)} items (heap overflow)")
                    if nested:
                        if obj_type != ids.OBJ_TYPE_ITEM:
                            warning(f"{where}: inventory entry is not an item")
                        if obj.tile != -1:
                            warning(f"{where}: inventory item has tile {obj.tile} instead of -1")
                    if obj.sid != -1:
                        if not 0 <= ids.sid_type(obj.sid) < len(self.script_lists):
                            error(f"{where}: sid 0x{obj.sid & 0xFFFFFFFF:08X} has an invalid script type")
                        else:
                            script = self.find_script(obj.sid)
                            if script is None:
                                warning(f"{where}: sid 0x{obj.sid & 0xFFFFFFFF:08X} has no script record (script is dropped)")
                            else:
                                owners.setdefault(obj.sid, []).append(obj)
                                if not nested and obj.script_index != script.index:
                                    warning(f"{where}: script_index {obj.script_index} differs from its record ({script.index})")
                    if ids.is_exit_grid(obj.pid) and not nested and len(obj.data) == 5:
                        if obj.tile == self.entering_tile and elevation == self.entering_elevation:
                            error(f"{where}: exit grid on the entering tile (the player would leave immediately)")
                        dest_map = obj["dest_map"]
                        if dest_map > 0 and map_count is not None and dest_map >= map_count:
                            error(f"{where}: exit grid leads to map {dest_map}, maps.txt has {map_count} maps")
                        if dest_map > 0 and obj["dest_tile"] not in (-1, 0):
                            if not geometry.is_valid(obj["dest_tile"]):
                                error(f"{where}: exit grid destination tile {obj['dest_tile']} is invalid")
                            elif not 0 <= obj["dest_elevation"] < ELEVATION_COUNT:
                                warning(f"{where}: exit grid destination elevation {obj['dest_elevation']} is outside 0..2, "
                                        "so its destination tile is ignored")
                    names = obj.data_names
                    if names[1:] == ITEM_DATA[3] and len(obj.data) == 3 and protos is not None \
                            and not self.flags & FLAG_SAVEGAME and obj["ammo_quantity"] != protos.get(obj.pid).ammo_capacity:
                        warning(f"{where}: weapon holds {obj['ammo_quantity']} rounds, its proto's capacity is "
                                f"{protos.get(obj.pid).ammo_capacity}: the engine refills (or empties) it when the map is first loaded")
                    if "dest_built_tile" in names and "dest_map" in names and len(obj.data) == len(names) and not nested:
                        self._check_destination(obj, where, names.index("dest_map") == 1, map_count, error, warning)
                    if names[:2] == ("data_flags", "open_flags") and len(obj.data) == 2 and obj["open_flags"] & LOCKED \
                            and obj.sid == -1:
                        warning(f"{where}: locked door without a script: the engine opens it all the same (see MapFile.lock)")
        duplicates = sorted(object_id for object_id, objs in seen_ids.items() if len(objs) > 1)
        if duplicates:
            warning(f"{len(duplicates)} object ids are used by more than one object (first: {duplicates[0]}); "
                    "saved timer events find their object by id")
        for sid, objs in owners.items():
            if len(objs) > 1:
                warning(f"script 0x{sid & 0xFFFFFFFF:08X} is referenced by {len(objs)} objects")
        for script_type in (ids.SCRIPT_TYPE_ITEM, ids.SCRIPT_TYPE_CRITTER):
            for script in self.script_lists[script_type].live():
                if script.sid not in owners:
                    warning(f"{ids.SCRIPT_TYPE_NAMES[script_type]} script 0x{script.sid & 0xFFFFFFFF:08X} "
                            f"(index {script.index}) is not referenced by any object")

        if geometry.is_valid(self.entering_tile) and 0 <= self.entering_elevation < ELEVATION_COUNT:
            for obj in self.objects_at(self.entering_tile, self.entering_elevation):
                if obj.obj_type in (ids.OBJ_TYPE_CRITTER, ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_WALL) \
                        and not obj.flags & (OBJECT_NO_BLOCK | OBJECT_HIDDEN):
                    warning(f"{obj!r} blocks the entering tile")
        return problems
