"""PID / FID / SID bit packing and the object-type table.

All three ids keep an object or script *type* in bits 24+ and an index below:

    PID  (type << 24) | index      index = 1-based line of proto/<type>/<type>.lst
    FID  (type << 24) | index      index = 0-based line of art/<type>/<type>.lst
                                   critters add weapon (bits 12-15), animation
                                   (bits 16-23) and rotation+1 (bits 28-30)
    SID  (type << 24) | n          script type and per-list serial number

Sources: fallout2-ce obj_types.h:17-34, art.cc:1009-1012, scripts.h:40-47.
"""

OBJ_TYPE_ITEM = 0
OBJ_TYPE_CRITTER = 1
OBJ_TYPE_SCENERY = 2
OBJ_TYPE_WALL = 3
OBJ_TYPE_TILE = 4
OBJ_TYPE_MISC = 5
OBJ_TYPE_INTERFACE = 6
OBJ_TYPE_INVENTORY = 7
OBJ_TYPE_HEAD = 8
OBJ_TYPE_BACKGROUND = 9
OBJ_TYPE_SKILLDEX = 10

# Directory name under art/ (all 11) and proto/ (first 6).
TYPE_DIRS = ("items", "critters", "scenery", "walls", "tiles", "misc",
             "intrface", "inven", "heads", "backgrnd", "skilldex")
PROTO_TYPE_COUNT = 6
# Singular names used in messages and by the CLI.
TYPE_NAMES = ("item", "critter", "scenery", "wall", "tile", "misc",
              "interface", "inventory", "head", "background", "skilldex")

ITEM_TYPES = ("armor", "container", "drug", "weapon", "ammo", "misc", "key")
SCENERY_TYPES = ("door", "stairs", "elevator", "ladder_up", "ladder_down", "generic")

SCRIPT_TYPE_SYSTEM = 0
SCRIPT_TYPE_SPATIAL = 1
SCRIPT_TYPE_TIMED = 2
SCRIPT_TYPE_ITEM = 3
SCRIPT_TYPE_CRITTER = 4
SCRIPT_TYPE_NAMES = ("system", "spatial", "timed", "item", "critter")

EXIT_GRID_FIRST_PID = 0x5000010
EXIT_GRID_LAST_PID = 0x5000017
SCROLL_BLOCKER_PID = 0x500000C


def s32(value):
    """Wrap an integer into the signed 32-bit range (accepts 0xA0000018-style values)."""
    return (value + 0x80000000) % 0x100000000 - 0x80000000


def u32(value):
    """Unsigned 32-bit view of an integer."""
    return value & 0xFFFFFFFF


def make_pid(obj_type, index):
    """index is the 1-based proto list line."""
    return (obj_type << 24) | index


def pid_type(pid):
    return (pid >> 24) & 0xFF


def pid_index(pid):
    return pid & 0xFFFFFF


def is_exit_grid(pid):
    return EXIT_GRID_FIRST_PID <= pid <= EXIT_GRID_LAST_PID


def make_fid(obj_type, index, anim=0, weapon=0, rotation_plus_1=0):
    """index is the 0-based art list line; the last three arguments are for critters."""
    return ((rotation_plus_1 & 7) << 28) | (obj_type << 24) | ((anim & 0xFF) << 16) | ((weapon & 0xF) << 12) | (index & 0xFFF)


def fid_type(fid):
    return (fid >> 24) & 0xF


def fid_index(fid):
    return fid & 0xFFF


def fid_anim(fid):
    return (fid >> 16) & 0xFF


def fid_weapon(fid):
    return (fid >> 12) & 0xF


def fid_rotation(fid):
    """0 = plain .frm, 1..6 = .fr0 .. .fr5"""
    return (fid >> 28) & 7


def make_sid(script_type, number):
    return (script_type << 24) | number


def sid_type(sid):
    return (sid >> 24) & 0xFF


def built_tile(tile, elevation=0, rotation=0):
    """tile | rotation << 26 | elevation << 29 (obj_types.h:295-314)."""
    return s32((tile & 0x3FFFFFF) | ((rotation & 7) << 26) | ((elevation & 7) << 29))


def built_tile_parts(value):
    """-> (tile, elevation, rotation)"""
    value = u32(value)
    return value & 0x3FFFFFF, (value >> 29) & 7, (value >> 26) & 7
