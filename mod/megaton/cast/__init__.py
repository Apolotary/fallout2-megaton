# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The cast: who and what stands where on the Megaton map.

This package is the contract between the people who write scripts and the
people who build the map. A script group lists its characters and scripted
objects in ONE file of this package, by spot name; the real town layout
(layout/) and the test stages (stagekit.py) both call `place_cast`, so the
script writer never touches a map builder and the architect never has to know
which proto, inventory or script an NPC needs.

    cast/core.py         main quest: Weld, Simms, Burke, the bomb, Harden, gate
    cast/merchants.py    Moira, Gob, Doc Church, Jenny, the caravan, Nova
    cast/sidequests.py   Moriarty, Silver, terminal, Walter, leaks, Lucy
    cast/flavour.py      everybody else

Each file defines ``CAST``, a list of entries made with the four functions
below (a missing file is simply an empty group)::

    from cast import *

    CAST = [
        # A critter: spot name (layout/spots.py), vanilla critter proto (look + stats),
        # then what differs from the defaults.
        critter("SIMMS", 0x0100008A, script="mgsimms", ai=AI_MG_GUARD, hp=90,
                items=[(PID_ASSAULT_RIFLE, 1, "right"), (PID_5MM_JHP, 2), (PID_STIMPAK, 2)]),
        critter("MOIRA", 0x0100003D, script="mgmoira", ai=AI_MG_MERCHANT, barter=True,
                items=[(PID_STIMPAK, 3), (PID_MONEY, 350)]),

        # A scripted object the cast brings along itself (scenery or a container item).
        thing("BOMB", PID_MGA_BOMB, script="mgbomb"),
        thing("STRONGBOX", PID_FOOTLOCKER_128, script="mgstrong", locked=True,
              items=[(PID_MONEY, 180)]),

        # A script for something the ARCHITECT places at that spot: a door, the gate.
        # kind is checked against what is found there.
        attach("HOUSE_DOOR", "door", script="mghouse"),

        # A spatial trigger: spatial_p_proc fires for every critter stepping within `radius`.
        spatial("ENTRY", radius=5, script="mgspgate"),
    ]

Rules
  - `spot` is a name of layout/spots.py (append new ones there; scripts get
    them as TILE_<NAME> / ROT_<NAME>). Coordinates belong to the architect.
  - `pid`: critters 0x01000000 + critters.lst line (the bare line number works
    too), scenery 0x02000000 + line, items the bare line number. All PID_*
    names of the stock game (headers/pids.h) and of the mod (registry.ITEMS)
    are available as constants of this module, e.g. PID_STIMPAK, PID_MG_HOUSE_KEY,
    PID_CR_VILLAGER_3 (critters), PID_SC_... (scenery).
    A critter's look, stats, skills and barter flag come from its proto: pick
    one with `python3 tools/contact_sheet.py critters --name ... --directions`
    and `python3 -m f2lib proto <pid>` (run from tools/).
  - `script`: stem from registry.SCRIPTS. Several entries may share a script.
  - `items`: (pid, quantity) or (pid, quantity, "right" | "left" | "worn").
    A weapon in the right hand is the one an NPC fights with. Cash is
    PID_MONEY (41): that is what barter and item_caps_total() count.
    PID_BOTTLE_CAPS (519) is a worthless souvenir.
  - `hp`: starting hit points, at most the proto's maximum (that maximum, like
    every other stat, cannot be changed per object).
  - `team` / `ai`: TEAM_MG_* / AI_MG_* of scripts/megaton.h, read from that
    header so the map and the scripts cannot disagree. Defaults: the town
    team and the plain citizen packet.
  - `barter=True` makes the build fail unless the proto has the barter flag
    (without it the engine answers every barter attempt with a refusal).
  - `attach` kinds: "door", "container", "scenery", "item", "critter", "any".
    `stand_in` is the PID a test stage puts there when nobody has built the
    real thing; the defaults are a wooden door, a footlocker and a signpost.

place_cast(map, gamefiles, groups=None, strict=False, spots=None, extra=())
does the placing. With strict=False an entry whose script has not been
compiled into the staging tree is still placed, without the script (critters
then just stand there), so one group's map does not wait for another group's
scripts. The integration build uses strict=True: every script must exist and
every `attach` must find its object.
"""
import importlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(MOD))
for _path in (MOD, os.path.join(ROOT, "tools")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import registry  # noqa: E402
from f2lib import geometry, ids  # noqa: E402
from layout import spots as _spots  # noqa: E402

GROUPS = ("core", "merchants", "sidequests", "flavour")

MEGATON_H = os.path.join(MOD, "scripts", "megaton.h")
PIDS_H = os.path.join(ROOT, "mod", "scripts_src", "headers", "pids.h")

CRITTER_BARTER_FLAG = 0x02            # critter_flags bit (proto_types.h CRITTER_BARTER)

# What a test stage puts on an `attach` spot when the architect's object is not there.
STAND_INS = {
    "door": 0x02000350,               # wooden door that fits the "jad" doorway walls
    "container": 0x00000080,          # footlocker
    "scenery": 0x020000C9,            # signpost: one hex, easy to see
    "item": 0x00000080,
    "any": 0x020000C9,
}
KINDS = ("door", "container", "scenery", "item", "critter", "any")


def _defines(path, pattern):
    """{NAME: int} of `#define NAME (number)` lines whose name matches `pattern`."""
    found = {}
    with open(path, encoding="latin-1") as f:
        for line in f:
            match = re.match(r"#define\s+(%s)\s+\((-?\d+|0x[0-9A-Fa-f]+)\)" % pattern, line)
            if match:
                found[match.group(1)] = int(match.group(2), 0)
    return found


# TEAM_MG_* and AI_MG_* come from megaton.h, PID_* from the generated pids.h and the registry.
CONSTANTS = {}
CONSTANTS.update(_defines(PIDS_H, r"PID_\w+"))
CONSTANTS.update(_defines(MEGATON_H, r"(?:TEAM|AI)_MG_\w+"))
CONSTANTS.update({define: pid for define, pid, _, _, _ in registry.ITEMS})
CONSTANTS.update(registry.art_pids())                       # PID_MGA_*: custom art (registry.ART_NAMES)
globals().update(CONSTANTS)


class CastError(Exception):
    pass


# ------------------------------------------------------------------ entries

def critter(spot, pid, script=None, rotation=None, items=(), hp=None,
            team=CONSTANTS["TEAM_MG_TOWN"], ai=CONSTANTS["AI_MG_CITIZEN"], barter=False):
    """An NPC standing on `spot`. See the module docstring for every field."""
    if pid < 0x01000000:
        pid |= 0x01000000
    return dict(type="critter", spot=spot, pid=pid, script=script, rotation=rotation, items=list(items),
                hp=hp, team=team, ai=ai, barter=barter)


def thing(spot, pid, script=None, rotation=None, items=(), locked=False):
    """A scenery object or container the cast creates on `spot` (optionally scripted, locked, filled)."""
    return dict(type="thing", spot=spot, pid=pid, script=script, rotation=rotation, items=list(items), locked=locked)


def attach(spot, kind, script, stand_in=None):
    """A script for an object of `kind` the architect placed on `spot`."""
    if kind not in KINDS:
        raise CastError(f"attach({spot!r}): kind must be one of {KINDS}")
    return dict(type="attach", spot=spot, kind=kind, script=script, stand_in=stand_in)


def spatial(spot, radius, script):
    """A spatial script centred on `spot`."""
    return dict(type="spatial", spot=spot, radius=radius, script=script)


__all__ = ["critter", "thing", "attach", "spatial"] + sorted(CONSTANTS)


# ------------------------------------------------------------------- loading

def load(groups=None):
    """Entries of the given groups (default: all), each tagged with its group name.

    A group whose file does not exist yet contributes nothing."""
    entries = []
    for group in (GROUPS if groups is None else groups):
        if not os.path.exists(os.path.join(HERE, group + ".py")):
            if group not in GROUPS:
                raise CastError(f"no cast group {group!r} (cast/{group}.py)")
            continue
        module = importlib.import_module("cast." + group)
        for entry in module.CAST:
            entries.append(dict(entry, group=group))
    return entries


def spot_position(spot, spots=None):
    """(hx, hy, rotation) of a spot name, or of an explicit (hx, hy[, rotation]) tuple (tests only)."""
    if isinstance(spot, str):
        table = spots if spots is not None and spot in spots else _spots.SPOTS
        if spot not in table:
            raise CastError(f"unknown spot {spot!r}: add it to layout/spots.py")
        return tuple(table[spot])
    return (spot[0], spot[1], spot[2] if len(spot) > 2 else 0)


def describe(entry):
    return f"{entry.get('group', '?')}: {entry['type']} at {entry['spot']}"


# ------------------------------------------------------------------- placing

def _kind_of(gf, obj):
    """The `attach` kinds an existing map object satisfies."""
    kinds = {"any"}
    if obj.obj_type == ids.OBJ_TYPE_CRITTER:
        kinds.add("critter")
    elif obj.obj_type == ids.OBJ_TYPE_SCENERY:
        kinds.add("scenery")
        if gf.protos.get(obj.pid).subtype_name == "door":
            kinds.add("door")
    elif obj.obj_type == ids.OBJ_TYPE_ITEM:
        kinds.add("item")
        if gf.protos.get(obj.pid).subtype_name == "container":
            kinds.add("container")
    return kinds


def _script_ready(gf, stem):
    """True when the compiled script is in the tree the engine will read."""
    return gf.exists(f"scripts/{stem}.int")


def _fill(m, owner, items, what):
    for item in items:
        pid, quantity = item[0], item[1] if len(item) > 1 else 1
        equipped = item[2] if len(item) > 2 else None
        if equipped not in (None, "left", "right", "worn"):
            raise CastError(f"{what}: item slot {equipped!r} is not left / right / worn")
        if not m.gf.protos.exists(pid):
            raise CastError(f"{what}: item PID {pid} does not exist")
        m.add_item(owner, pid, quantity=quantity, equipped=equipped)


def place_cast(m, gf, groups=None, strict=False, spots=None, extra=(), elevation=0, log=print):
    """Put the cast on map `m` (an f2lib MapFile). Returns [(entry, object or script record)].

    groups   group names to place (default: all four)
    strict   True: a missing script or a missing `attach` target is an error.
             False: the object is placed without the script / the entry is
             skipped, and a line says so.
    spots    {name: (hx, hy, rotation)} replacing layout/spots.py positions
             (a compacted test stage); names not in it keep their real place
    extra    more entries (tests), placed after the groups'
    """
    entries = load(groups) + [dict(entry, group=entry.get("group", "extra")) for entry in extra]
    placed = []
    occupied = {}
    for entry in entries:
        what = describe(entry)
        hx, hy, spot_rotation = spot_position(entry["spot"], spots)
        tile = geometry.tile_at(hx, hy)
        if tile < 0:
            raise CastError(f"{what}: ({hx}, {hy}) is outside the map")
        script = entry.get("script")
        if script is not None:
            if gf.scripts.find(script) is None:
                raise CastError(f"{what}: script {script!r} is not in scripts.lst (registry.SCRIPTS)")
            if not _script_ready(gf, script):
                if strict:
                    raise CastError(f"{what}: script {script}.ssl has not been compiled")
                log(f"cast: {what}: {script}.ssl not built yet, placed without a script")
                script = None

        kind = entry["type"]
        if kind == "spatial":
            if script is not None:
                placed.append((entry, m.add_spatial_script(script, tile, elevation, radius=entry["radius"])))
            continue

        if kind == "attach":
            candidates = [obj for obj in m.objects_at(tile, elevation) if entry["kind"] in _kind_of(gf, obj)]
            if not candidates:
                if strict:
                    raise CastError(f"{what}: no {entry['kind']} on tile {tile} to attach {entry['script']} to")
                log(f"cast: {what}: no {entry['kind']} on tile {tile}, {entry['script']} not attached")
                continue
            target = candidates[0]
            if script is not None:
                if target.sid != -1:
                    raise CastError(f"{what}: the {entry['kind']} on tile {tile} already has a script")
                m.attach_script(target, script)
            placed.append((entry, target))
            continue

        pid = entry["pid"]
        if not gf.protos.exists(pid):
            raise CastError(f"{what}: PID 0x{pid:08X} does not exist")
        proto = gf.protos.get(pid)
        rotation = spot_rotation if entry.get("rotation") is None else entry["rotation"]
        if kind == "critter":
            if proto.obj_type != ids.OBJ_TYPE_CRITTER:
                raise CastError(f"{what}: PID 0x{pid:08X} is not a critter")
            if entry["barter"] and not proto.critter_flags & CRITTER_BARTER_FLAG:
                raise CastError(f"{what}: proto 0x{pid:08X} ({gf.protos.name(pid)}) has no barter flag; "
                                "pick a proto of the same art that has it (python3 -m f2lib proto <pid>, critter_flags bit 2)")
            if tile in occupied:
                raise CastError(f"{what}: tile {tile} is already taken by {occupied[tile]}")
            occupied[tile] = what
            obj = m.add_object(pid, tile, elevation, rotation=rotation, script=script)
            obj["team"] = entry["team"]
            obj["ai_packet"] = entry["ai"]
            if entry["hp"] is not None:
                if not 0 < entry["hp"] <= proto.max_hp:
                    raise CastError(f"{what}: hp {entry['hp']} is outside 1..{proto.max_hp}, the proto's maximum")
                obj["hp"] = entry["hp"]
            _fill(m, obj, entry["items"], what)
        else:
            if proto.obj_type not in (ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_ITEM):
                raise CastError(f"{what}: a thing must be scenery or an item, not 0x{pid:08X}")
            obj = m.add_object(pid, tile, elevation, rotation=rotation, script=script)
            if entry["items"]:
                if proto.subtype_name != "container":
                    raise CastError(f"{what}: only containers can hold items")
                _fill(m, obj, entry["items"], what)
            if entry["locked"]:
                m.lock(obj)
        placed.append((entry, obj))
    return placed


def summary(groups=None):
    """One line per entry, for build logs and for people looking for a spot."""
    lines = []
    for entry in load(groups):
        hx, hy, _ = spot_position(entry["spot"])
        pid = f" pid=0x{entry['pid']:08X}" if "pid" in entry else ""
        lines.append(f"{entry['group']:<10} {entry['type']:<8} {str(entry['spot']):<18} ({hx:3d},{hy:3d})"
                     f"{pid} script={entry.get('script')}")
    return lines


if __name__ == "__main__":
    print("\n".join(summary()) or "the cast is empty")
