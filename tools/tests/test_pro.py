# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Prototypes: every retail proto parses and re-serialises byte-identically."""
import collections
import hashlib

import _env
from f2lib import ids
from f2lib.pro import Proto

EXPECTED_SIZES = {
    ("item", "armor"): 129, ("item", "container"): 65, ("item", "drug"): 125, ("item", "weapon"): 122,
    ("item", "ammo"): 81, ("item", "misc"): 69, ("item", "key"): 61,
    ("scenery", "door"): 49, ("scenery", "stairs"): 49, ("scenery", "elevator"): 49,
    ("scenery", "ladder_up"): 45, ("scenery", "ladder_down"): 45, ("scenery", "generic"): 45,
    ("wall", ""): 36, ("tile", ""): 28, ("misc", ""): 28,
}


def test_all_protos_round_trip():
    db = _env.gf().protos
    kinds = collections.Counter()
    for obj_type in range(ids.PROTO_TYPE_COUNT):
        for pid in db.pids(obj_type):
            raw = db.raw(pid)
            proto = Proto.from_bytes(raw)
            assert proto.to_bytes() == raw, f"0x{pid:08X} does not round-trip"
            assert proto.pid == pid, f"proto file of 0x{pid:08X} holds pid 0x{proto.pid:08X}"
            assert proto.obj_type == obj_type
            key = (proto.kind, proto.subtype_name)
            kinds[key] += 1
            if proto.kind == "critter":
                assert len(raw) in (412, 416)
            else:
                assert len(raw) == EXPECTED_SIZES[key], (hex(pid), len(raw))
    assert sum(kinds.values()) == 7650
    assert kinds[("item", "weapon")] == 110 and kinds[("scenery", "door")] == 98 and kinds[("critter", "")] == 483
    # every item and scenery sub-type occurs, so every branch of the parser ran
    assert {k[1] for k in kinds if k[0] == "item"} == set(ids.ITEM_TYPES)
    assert {k[1] for k in kinds if k[0] == "scenery"} == set(ids.SCENERY_TYPES)


def test_named_fields_and_texts():
    db = _env.gf().protos
    door = db.get(0x02000002)
    assert (door.kind, door.subtype_name, door.fid, door.material, door.sound_id) == ("scenery", "door", 0x0200006D, 3, ord("D"))
    assert hashlib.sha256(db.name(0x02000002).encode()).hexdigest() == "ea4cce18c3a73a9383b791b30f5cf52f342bcb57f4b4980185680b6cf0a032b1" and hashlib.sha256(db.description(0x02000002).encode()).hexdigest() == "071a5abe91641764ea00dab53add68a82b216223af91ff37c684f89c855d7caa"
    assert db.path(0x02000002) == "proto/scenery/00000002.pro" and db.subtype(0x02000002) == 0
    assert db.subtype(0x03000001) is None

    pistol = db.get(0x00000008)
    assert (pistol.subtype_name, pistol.min_damage, pistol.max_damage, pistol.ammo_capacity, pistol.ammo_type_pid) == ("weapon", 5, 12, 12, 29)
    assert hashlib.sha256(db.name(0x00000008).encode()).hexdigest() == "efa5e8563c2c145d5659b1b934926273ade8e8a3168fcff12e95ababbab3daad"

    villager = db.get(0x01000003)
    assert villager.max_hp == 50 and villager.sid == -1 and len(villager.base_stats) == 35 and len(villager.skills) == 18
    assert db.get(0x04000002).fields() == ["pid", "message_id", "fid", "flags", "flags_ext", "sid", "material"]
    assert "light_distance" in db.get(0x05000010).fields() and "sid" not in db.get(0x05000010).fields()

    assert not db.exists(0x02FFFFFF) and db.path(0x02FFFFFF) is None
    assert (0x02000002, "Wooden Door") in db.search("wooden door", ids.OBJ_TYPE_SCENERY)
    try:
        door.no_such_field
    except AttributeError:
        pass
    else:
        raise AssertionError("unknown field did not raise")


def test_copy_makes_a_new_proto():
    db = _env.gf().protos
    wall = db.get(0x03000001)
    clone = wall.copy(pid=ids.make_pid(ids.OBJ_TYPE_WALL, 1634), fid=ids.make_fid(ids.OBJ_TYPE_WALL, 1690), message_id=163400)
    data = clone.to_bytes()
    again = Proto.from_bytes(data)
    assert len(data) == 36 and again.pid == 0x03000662 and again.fid == 0x0300069A and again.material == wall.material
    assert wall.pid == 0x03000001, "the original must not change"
    critter = db.get(0x01000003).copy()
    critter.base_stats[7] = 99
    assert db.get(0x01000003).base_stats[7] != 99, "copy() must not share lists"


def test_object_flags_follow_engine_rule():
    db = _env.gf().protos
    assert db.get(0x00000080).object_flags() & 0xFFFFFFFF == 0xA0009000      # footlocker
    assert db.get(0x05000010).object_flags() & 0xFFFFFFFF == 0xA0008018      # exit grid
    assert db.get(0x0500000C).object_flags() & 0xFFFFFFFF == 0xA0000018      # scroll blocker
    assert db.get(0x03000001).object_flags() == 0
