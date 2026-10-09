# SPDX-License-Identifier: LicenseRef-Sustainable-Use
""".lst index bases and .msg parsing."""
import hashlib

import _env
from f2lib import gam, ids, lst, mapstxt, msg


def test_art_lists_are_zero_based():
    gf = _env.gf()
    tiles = gf.art_list(ids.OBJ_TYPE_TILE)
    assert len(tiles) == 3102
    assert (tiles.name(0), tiles.name(1), tiles.name(2)) == ("reserved.frm", "grid000.frm", "brick01.frm")
    assert tiles.index("GRID000.FRM") == 1 and tiles.find("nosuch.frm") is None and tiles.next_index == 3102
    assert gf.art_list(ids.OBJ_TYPE_CRITTER).name(62) == "hmwarr", "critter lines are cut at the comma"
    assert gf.art_list(ids.OBJ_TYPE_INTERFACE).name(0) == "blank.frm", "cut at space / semicolon"
    assert len(gf.art_list(ids.OBJ_TYPE_WALL)) == 1690 and len(gf.art_list(ids.OBJ_TYPE_SCENERY)) == 1863


def test_proto_lists_are_one_based():
    gf = _env.gf()
    scenery = gf.proto_list(ids.OBJ_TYPE_SCENERY)
    assert len(scenery) == 1851 and scenery.name(1) == "00000024.pro" and scenery.name(0) is None
    assert scenery.name(1851) is not None and scenery.name(1852) is None
    assert gf.proto_list(ids.OBJ_TYPE_ITEM).name(1) == "00000003.pro"
    assert [len(gf.proto_list(t)) for t in range(6)] == [531, 483, 1851, 1633, 3102, 50]


def test_scripts_list():
    scripts = _env.gf().scripts
    assert len(scripts) == 1303
    assert scripts.name(0) == "obj_dude" and scripts.entries[0].local_vars == 5
    # arvillag.map's header says 27 (1-based) and scripts.lst line 27 is ArVillag.int.
    assert scripts.index("arvillag") == 26 == scripts.index("ArVillag.int")
    assert scripts.find("nosuchscript") is None
    for bad in (("megaton_guard1",), ("",), ("my guard",), ("megaton", "x" * 240), ("megaton", "has # local_vars=9")):
        try:
            lst.ScriptList.format_line(*bad)
        except ValueError:
            continue
        raise AssertionError(f"format_line accepted {bad!r}")
    assert lst.ScriptList.format_line("megatonguar.int", "x" * 200).startswith("megatonguar.int ; xxx")
    line = lst.ScriptList.format_line("megaton", "Megaton map script", 3)
    parsed = lst.ScriptList((line + "\r\n").encode())
    assert parsed.entries[0].name == "megaton" and parsed.entries[0].local_vars == 3


def test_append_lines_keeps_newline_style():
    data = _env.gf().read("art/tiles/tiles.lst")
    grown = lst.append_lines(data, ["mytile01.frm", "mytile02.frm"])
    names = lst.art_names(grown)
    assert names[:3102] == lst.art_names(data) and names[3102:] == ["mytile01.frm", "mytile02.frm"]
    assert grown.endswith(b"mytile02.frm\r\n")
    assert lst.art_names(lst.append_lines(b"a.frm", ["b.frm"])) == ["a.frm", "b.frm"]


def test_msg_parse_and_serialise():
    gf = _env.gf()
    items = gf.msg("game/pro_item.msg")
    assert hashlib.sha256(items.text(100).encode()).hexdigest() == "883177524590266e875bed587fbc42b858774dd83eeee0aafd73ac5e81af2b96"
    assert hashlib.sha256(items.text(101)[:22].encode()).hexdigest() == "d37f32a8b89f31c56e45ebb0f59a3cd8e89be3d4431ddabcd9173a771c6379d1"
    assert [len(gf.msg(f"game/pro_{n}.msg")) for n in ("item", "crit", "scen", "wall", "tile", "misc")] == [1023, 502, 2765, 1647, 813, 54]

    entries = {5: ("", "five"), 1: ("snd01", "one"), 300: ("", "multi word, with punctuation!")}
    assert msg.parse(msg.serialise(entries)) == {k: entries[k] for k in sorted(entries)}
    assert msg.parse(b"# comment\n{10}{}{split\nline}\n{10}{}{replaced}\n{11}{a}{b}") == {10: ("", "replaced"), 11: ("a", "b")}

    original = gf.read("text/english/game/map.msg")
    grown = msg.append_entries(original, {653: "Megaton", 1518: "Megaton"})
    parsed = msg.parse(grown)
    assert grown.startswith(original) and parsed[653][1] == "Megaton" and parsed[1518][1] == "Megaton"
    assert len(parsed) == len(msg.parse(original)) + 1

    for bad in (b"{1}{}{unterminated", b"stray } brace", b"{1}{}"):
        try:
            msg.parse(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad!r}")


def test_maps_txt():
    data = _env.gf().read("data/maps.txt")
    table = mapstxt.maps(data)
    assert len(table) == 151 and table[150]["map_name"] == "rndbess" and hashlib.sha256(table[4]["lookup_name"].encode()).hexdigest() == "942bbe5fc7ff9e75129ffa6ef7a320a5468520783bc0c58578223a028f12772c"
    assert mapstxt.map_names(data).index("arvillag") == 4
    grown, index = mapstxt.append_map(data, "Megaton", "megaton", music="12junktn", saved=True,
                                      can_rest_here=(True, False, False), automap=True)
    assert index == 151 and grown.startswith(data)
    added = mapstxt.maps(grown)[151]
    assert added == {"lookup_name": "Megaton", "map_name": "megaton", "music": "12junktn", "saved": "Yes",
                     "can_rest_here": "Yes,No,No", "automap": "Yes"}
    for bad in (("Megaton", "toolongname"), ("Me,gaton", "megaton"), ("Arroyo", "arvillag")):
        try:
            mapstxt.append_map(data, *bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad}")


def test_gam():
    variables = gam.parse(_env.gf().read("maps/arvillag.gam"))
    assert len(variables) >= 1 and all(isinstance(v, int) for _, v in variables)
    assert len(gam.parse(_env.gf().read("data/vault13.gam"), gam.GAME_SECTION)) == 696
    sample = [("MVAR_Bomb_Armed", 0), ("MVAR_Visits", 3), ("MVAR_Negative", -2)]
    assert gam.parse(gam.serialise(sample)) == sample
