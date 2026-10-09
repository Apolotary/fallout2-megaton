# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Map files: byte-identical round trip of every vanilla map, construction API, validation."""
import os
import tempfile

import numpy as np

import _env
from f2lib import Dat2, GameFiles, MapFile, geometry as g, ids, mapstxt
from f2lib import map as fmap


def _registered_tree(tmp, name="testmap", gam_vars=None):
    """Overlay in which `name` is registered as the next map of maps.txt."""
    os.makedirs(os.path.join(tmp, "data"), exist_ok=True)
    data, index = mapstxt.append_map(_env.gf().read("data/maps.txt"), "Test Map", name, saved=True, automap=True)
    with open(os.path.join(tmp, "data", "maps.txt"), "wb") as f:
        f.write(data)
    if gam_vars is not None:
        from f2lib import gam
        os.makedirs(os.path.join(tmp, "maps"), exist_ok=True)
        with open(os.path.join(tmp, "maps", name + ".gam"), "wb") as f:
            f.write(gam.serialise(gam_vars))
    return GameFiles(overlay=tmp), index


def _errors(m):
    return [p for p in m.validate() if p.startswith("error")]


def test_all_vanilla_maps_round_trip():
    gf = _env.gf()
    names = gf.glob("maps/*.map")
    assert len(names) == 155
    top = nested = scripts = 0
    for path in names:
        data = gf.read(path)
        m = MapFile.from_bytes(data, gf)
        assert m.to_bytes() == data, f"{path} does not round-trip"
        assert m.name.lower() == path.split("/")[1], path
        top += sum(len(block) for block in m.objects)
        nested += sum(1 for _ in m.all_objects(nested=True))
        scripts += len(m.scripts())
    assert top == 300464 and nested - top == 5234 and scripts == 4319


def test_master_dat_maps_shadowed_by_patch000_round_trip():
    """patch000.dat replaces 15 maps; the originals only exist inside master.dat."""
    gf = _env.gf()
    with Dat2(_env.archive("patch000.dat")) as patch, Dat2(_env.archive("master.dat")) as master:
        shadowed = [k for k in patch.order if k.startswith("maps/") and k.endswith(".map") and master.has(k)]
        assert len(shadowed) == 15
        different = 0
        for key in shadowed:
            data = master.read(key)
            different += data != patch.read(key)
            assert MapFile.from_bytes(data, gf).to_bytes() == data, f"master.dat {key} does not round-trip"
        assert different == 14, "only newr2.map is unchanged by the patch"


def test_known_vanilla_content():
    gf = _env.gf()
    m = MapFile.load("arvillag", gf)
    assert (m.name, m.version, m.script_index) == ("ARVILLAG.MAP", 20, 27)
    assert gf.scripts.name(m.script_index - 1).lower() == "arvillag"
    assert m.base_name == "arvillag" and m.file_name == "arvillag.map"
    assert g.can_center(m.entering_tile) and not m.script_lists[ids.SCRIPT_TYPE_SYSTEM].count
    item_script = next(s for s in m.scripts(ids.SCRIPT_TYPE_ITEM) if s.sid == 0x03000079)
    assert (item_script.index, item_script.owner_id, item_script.local_vars_offset, item_script.next) == (751, 66, -1, -1)
    owner = next(o for o in m.all_objects() if o.sid == 0x03000079)
    assert owner.id == 66 and m.find_script(owner.sid) is item_script

    bridge = MapFile.load("arbridge.map", gf)
    carrier = next(o for o in bridge.all_objects() if o.pid == 0x01000004 and o.inventory)
    quantity, spear = carrier.inventory[0]
    assert carrier.inv_capacity == 10 and quantity == 1 and spear.pid == 0x00000007 and spear.tile == -1
    assert spear.flags == 0x02000008 and spear["ammo_type_pid"] == -1 and spear.kind == "item"
    exit_grid = next(o for o in bridge.all_objects() if ids.is_exit_grid(o.pid) and o["dest_map"] > 0)
    assert exit_grid.data_names == ("data_flags", "dest_map", "dest_tile", "dest_elevation", "dest_rotation")

    caves = MapFile.load("arcaves", gf)
    spatial = caves.scripts(ids.SCRIPT_TYPE_SPATIAL)[0]
    assert (spatial.sid, spatial.tile, spatial.elevation, spatial.radius, spatial.index) == (0x01000000, 27895, 1, 10, 30)
    assert sorted(caves.tiles) == [0, 1, 2] and len(caves.objects[1]) > 0

    # two retail maps have elevation 0 absent
    assert sorted(MapFile.load("newr1a", gf).tiles) == [1, 2]


def test_build_new_map_and_reparse():
    with tempfile.TemporaryDirectory() as tmp:
        gf, index = _registered_tree(tmp, gam_vars=[("MVAR_A", 1), ("MVAR_B", 0)])
        assert index == 151
        m = MapFile.new("testmap", gf)
        assert m.name == "TESTMAP.MAP" and sorted(m.tiles) == [0] and m.sort_on_write
        m.global_vars = [1, 0]

        m.fill_floor(45, 45, 54, 54, "edg5000.frm")
        m.set_floor(50, 50, 192)
        m.fill_roof(48, 48, 49, 49, lambda x, y: "plk1000.frm" if (x + y) & 1 else None)
        assert m.floor(50, 50) == 192 and m.floor(45, 45) == 191 and m.floor(44, 45) == fmap.NO_TILE
        assert m.roof(48, 49) == gf.art_list(ids.OBJ_TYPE_TILE).index("plk1000.frm") and m.roof(48, 48) == fmap.NO_TILE

        door = m.add_object(0x02000002, g.tile_at(101, 96), open_flags=fmap.LOCKED)
        wall = m.add_object(0x03000081, g.tile_at(103, 96))
        guard = m.add_object(0x01000003, g.tile_at(105, 101), rotation=3, script="acklint")
        spear = m.add_item(guard, 0x00000007, equipped="right")
        m.add_item(guard, 0x00000028, quantity=4)
        locker = m.add_object(0x00000080, g.tile_at(96, 100), script=gf.scripts.index("zilocker"))
        pistol = m.add_item(locker, 0x00000008)
        ammo = m.add_item(locker, 0x0000001D, quantity=2)
        lamp = m.add_object(0x0200008D, g.tile_at(100, 98))                     # "Light Source"
        exit_world = m.add_exit_grid(g.tile_at(100, 110))
        exit_map = m.add_exit_grid(g.tile_at(101, 110), dest_map=4, dest_tile=20100, dest_elevation=0, dest_rotation=2, shape=1)
        blocker = m.add_scroll_blocker(g.tile_at(100, 120))
        ladder = m.add_object(0x020000C5, g.tile_at(98, 98))
        extra = [m.add_object(0x02000005, g.tile_at(90 + i, 104), script="acklint") for i in range(18)]
        spatial = m.add_spatial_script("acklint", g.tile_at(100, 105), radius=3)
        m.set_map_script("arvillag")
        m.set_entrance(g.tile_at(100, 100), rotation=2)

        # defaults taken from the protos
        assert door.fid == 0x0200006D and door.flags == 0 and door["open_flags"] == fmap.LOCKED and door.data == [0, fmap.LOCKED]
        assert wall.data == [0] and wall.sid == -1 and wall.script_index == -1 and wall.cid == -1
        assert guard.data == [0, 0, 0, gf.protos.get(0x01000003).max_ap, 0, 1, 1, -1, 50, 0, 0]
        assert guard.flags == 0x20000000 and guard.rotation == 3 and guard.inv_capacity == 10
        assert spear.flags & fmap.OBJECT_IN_RIGHT_HAND and spear.tile == -1 and spear.elevation == 0
        assert pistol.data == [0, 12, 29] and ammo["quantity"] == gf.protos.get(0x0000001D).quantity
        assert lamp.light_intensity == 0x10000 and lamp.light_distance == 8 and lamp.flags & fmap.OBJECT_LIGHTING
        assert exit_world.fid == 0x05000021 and exit_world.data == [0, -2, -1, 0, 0] and exit_world.flags & 0xFFFFFFFF == 0xA0008018
        assert exit_map.fid == 0x05000012 and exit_map.data == [0, 4, 20100, 0, 2]
        assert blocker.fid == 0x05000001 and blocker.flags & 0xFFFFFFFF == 0xA0000018
        assert ladder.data_names == ("data_flags", "dest_map", "dest_built_tile") and ladder["dest_built_tile"] == -1
        # both are legal but suspicious until dealt with (test_map_audit.py covers the helpers)
        assert sorted(p.split(": ", 2)[2][:24] for p in m.validate()) == ["locked door without a sc", "no destination set, usin"]
        m.attach_script(door, "ziwoddor")
        m.set_destination(ladder, g.tile_at(98, 100))
        ids_seen = [o.id for o in m.all_objects(nested=True)]
        assert len(ids_seen) == len(set(ids_seen)) and all(0 < i < 18000 for i in ids_seen)

        # script bookkeeping
        assert m.script_index == gf.scripts.index("arvillag") + 1
        critter_scripts = m.scripts(ids.SCRIPT_TYPE_CRITTER)
        item_scripts = m.scripts(ids.SCRIPT_TYPE_ITEM)
        assert len(critter_scripts) == 1 and len(item_scripts) == 20
        record = m.find_script(guard.sid)
        assert record is critter_scripts[0] and ids.sid_type(guard.sid) == ids.SCRIPT_TYPE_CRITTER
        assert (record.index, record.owner_id, guard.script_index) == (gf.scripts.index("acklint"), guard.id, gf.scripts.index("acklint"))
        assert ids.sid_type(locker.sid) == ids.SCRIPT_TYPE_ITEM and len({s.sid for s in item_scripts}) == 20
        item_list = m.script_lists[ids.SCRIPT_TYPE_ITEM]
        assert item_list.count == 20 and [e.length for e in item_list.extents] == [16, 4]
        assert (spatial.tile, spatial.elevation, spatial.radius) == (g.tile_at(100, 105), 0, 3)
        try:
            m.attach_script(guard, "acklint")
        except ValueError:
            pass
        else:
            raise AssertionError("second script on one object was accepted")

        assert m.validate() == [], m.validate()

        data = m.to_bytes()
        assert data == m.to_bytes()
        back = MapFile.from_bytes(data, gf)
        assert back.to_bytes() == data
        assert back.flags == 0xC and back.name == "TESTMAP.MAP" and back.entering_tile == 20100 and back.entering_rotation == 2
        assert back.global_vars == [1, 0] and back.local_vars == [] and back.darkness == 1 and back.index == -1
        assert (back.tiles[0] == m.tiles[0]).all() and back.tiles[0].dtype == np.uint32
        tiles_in_file = [o.tile for o in back.objects[0]]
        assert tiles_in_file == sorted(tiles_in_file), "objects are written in tile order like the game's own saver"
        assert len(back.objects[0]) == len(m.objects[0]) and not back.objects[1] and not back.objects[2]
        guard_back = next(o for o in back.all_objects() if o.id == guard.id)
        assert [(q, i.pid) for q, i in guard_back.inventory] == [(1, 0x00000007), (4, 0x00000028)]
        assert guard_back.data == guard.data and guard_back.sid == guard.sid
        assert len(back.scripts(ids.SCRIPT_TYPE_ITEM)) == 20 and back.validate() == []
        # unused script slots are all-zero 64-byte records
        tail = back.script_lists[ids.SCRIPT_TYPE_ITEM].extents[1].slots[4:]
        assert all(s.sid == 0 and s.index == 0 and s.next == 0 for s in tail)
        # header, 2 globals, 1 square block, 5 list counts, extents (spatial: one live 72-byte record and
        # 15 unused 64-byte slots; item: 2 extents; critter: 1), object counts, records, 4 inventory quantities
        expected_size = (0xEC + 8 + 40000 + 5 * 4 + (72 + 15 * 64 + 8) + 2 * (16 * 64 + 8) + (16 * 64 + 8)
                         + 4 + 3 * 4 + sum(84 + 4 * len(o.data) for o in m.all_objects(nested=True)) + 4 * 4)
        assert len(data) == expected_size

        m.remove_object(extra[0])
        assert len(m.scripts(ids.SCRIPT_TYPE_ITEM)) == 19 and m.validate() == []


def test_edit_vanilla_map_in_place():
    gf = _env.gf()
    original = gf.read("maps/arvillag.map")
    m = MapFile.from_bytes(original, gf)
    before = len(m.objects[0])
    script_count = m.script_lists[ids.SCRIPT_TYPE_ITEM].count
    barrel = m.add_object(0x02000005, m.entering_tile + 3, script="acklint")
    assert barrel.id not in {o.id for o in m.all_objects(nested=True) if o is not barrel}
    back = MapFile.from_bytes(m.to_bytes(), gf)
    assert len(back.objects[0]) == before + 1 and back.script_lists[ids.SCRIPT_TYPE_ITEM].count == script_count + 1
    assert back.find_script(barrel.sid).index == gf.scripts.index("acklint")
    assert not _errors(back)
    assert MapFile.from_bytes(original, gf).to_bytes() == original


def test_validation_catches_each_invariant():
    with tempfile.TemporaryDirectory() as tmp:
        gf, _ = _registered_tree(tmp, gam_vars=[("MVAR_A", 0), ("MVAR_B", 0)])

        def fresh():
            m = MapFile.new("testmap", gf)
            m.global_vars = [0, 0]
            m.fill_floor(48, 48, 52, 52, "edg5000.frm")
            m.add_object(0x02000005, g.tile_at(102, 100))
            return m

        def expect(m, fragment, severity="error"):
            problems = m.validate()
            assert any(p.startswith(severity) and fragment in p for p in problems), (fragment, problems)

        assert fresh().validate() == []

        m = fresh(); m.version = 21; expect(m, "version")
        m = fresh(); m.entering_tile = g.tile_at(30, 100); expect(m, "cannot be a view centre")
        m = fresh(); m.entering_tile = 40000; expect(m, "outside 0..39999")
        m = fresh(); m.entering_elevation = 3; expect(m, "entering elevation")
        m = fresh(); m.entering_elevation = 1; expect(m, "has no squares", "warning")
        m = fresh(); m.name_raw = b"X" * 16; expect(m, "NUL-terminated")
        m = fresh(); m.name = "other"; expect(m, "not registered")
        m = fresh(); m.flags |= 1; expect(m, "saved game", "warning")
        m = fresh(); m.global_vars = [0]; expect(m, "declares 2 variables")
        m = fresh(); m.tiles[0][5] = 4000; expect(m, "beyond art/tiles/tiles.lst")
        m = fresh(); m.tiles[0] = m.tiles[0][:50]; expect(m, "square block")

        m = fresh(); m.script_index = 5000; expect(m, "beyond scripts.lst")
        m = fresh(); m.attach_script(m.objects[0][0], 5000); expect(m, "outside scripts.lst")
        m = fresh(); m.objects[0][0].sid = 0x03000005; expect(m, "no script record", "warning")
        m = fresh(); m.objects[0][0].sid = 0x09000000; expect(m, "invalid script type")
        m = fresh(); m.attach_script(m.objects[0][0], "acklint"); m.objects[0][0].sid = -1; expect(m, "not referenced", "warning")
        m = fresh()
        a = m.add_object(0x02000005, g.tile_at(104, 100), script="acklint")
        b = m.add_object(0x02000005, g.tile_at(106, 100), script="acklint")
        m.find_script(b.sid).sid = a.sid
        expect(m, "used twice")
        m = fresh(); m.attach_script(m.objects[0][0], "acklint"); m.script_lists[3].count = 2; expect(m, "extent lengths sum")
        m = fresh(); m.attach_script(m.objects[0][0], "acklint"); m.script_lists[3].count = 20; expect(m, "extents for count")
        m = fresh(); m.add_spatial_script("acklint", 40001); expect(m, "bad position")

        m = fresh(); m.objects[0].clear(); m.add_object(0x03000081, g.tile_at(103, 96)); expect(m, "every top-level object is a wall")
        m = fresh(); m.objects[0][0].tile = 40000; expect(m, "outside 0..39999")
        m = fresh(); m.objects[0][0].pid = 0x02FFFFFF; expect(m, "prototype does not exist")
        m = fresh(); m.objects[0][0].data.append(0); expect(m, "data words")
        m = fresh(); m.objects[0][0].fid = 0x02000FFF; expect(m, "no art file", "warning")
        m = fresh(); m.objects[0][0].light_intensity = 0x10000; expect(m, "LIGHTING flag", "warning")
        m = fresh(); m.objects[0][0].id = 18000; expect(m, "party range", "warning")
        m = fresh(); m.add_object(0x02000005, g.tile_at(104, 100)).id = m.objects[0][0].id; expect(m, "more than one object", "warning")
        m = fresh(); m.objects[0][0].elevation = 2; expect(m, "differs from its block", "warning")
        m = fresh(); m.add_object(0x02000005, g.tile_at(100, 100), elevation=1); expect(m, "no squares", "warning")
        m = fresh(); m.add_object(0x02000005, m.entering_tile); expect(m, "blocks the entering tile", "warning")

        m = fresh()
        chest = m.add_object(0x00000080, g.tile_at(98, 100))
        item = m.add_item(chest, 0x00000028)
        chest.inv_capacity = 0
        expect(m, "inventory capacity")
        chest.inv_capacity = 10
        item.fid = 0x00000FFF
        expect(m, "no art file")                    # an error for inventory items (dangling pointer in the engine)
        try:
            m.add_item(chest, 0x02000005)
        except ValueError:
            pass
        else:
            raise AssertionError("scenery was accepted as an inventory item")

        m = fresh(); m.add_exit_grid(m.entering_tile); expect(m, "exit grid on the entering tile")
        m = fresh(); m.add_exit_grid(g.tile_at(100, 104), dest_map=400); expect(m, "exit grid leads to map 400")
        m = fresh(); m.add_exit_grid(g.tile_at(100, 104), dest_map=4, dest_tile=50000); expect(m, "destination tile")

        for bad in (lambda m: m.set_floor(100, 0, 191), lambda m: m.set_floor(0, 0, 5000), lambda m: m.set_floor(0, 0, "nosuch.frm"),
                    lambda m: m.set_roof(0, 0, 191, elevation=1), lambda m: m.add_object(0x02000005, 100, elevation=3),
                    lambda m: m.add_object(0x02000005, 100, no_such_field=1), lambda m: m.set_map_script("nosuchscript")):
            try:
                bad(fresh())
            except (ValueError, KeyError, TypeError):
                continue
            raise AssertionError("invalid construction call was accepted")


def test_new_elevations_and_version_19_ladders():
    gf = _env.gf()
    m = MapFile.new("x", gf)
    m.add_elevation(2)
    m.set_floor(1, 1, 191, elevation=2)
    back = MapFile.from_bytes(m.to_bytes(), gf)
    assert back.flags == 0x4 and sorted(back.tiles) == [0, 2] and back.floor(1, 1, 2) == 191
    assert len(m.to_bytes()) == 0xEC + 2 * 40000 + 20 + 16
    assert fmap.data_layout(0x020000C5, gf.protos.subtype(0x020000C5), version=19) == ("data_flags", "dest_built_tile")
    assert fmap.data_layout(0x05000010, None) == ("data_flags", "dest_map", "dest_tile", "dest_elevation", "dest_rotation")
    assert fmap.data_layout(0x0500000C, None) == ("data_flags",) and len(fmap.data_layout(0x01000003, None)) == 11
