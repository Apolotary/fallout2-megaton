# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Virtual game tree: case-insensitive lookup and overlay precedence."""
import os
import tempfile

import _env
from f2lib import GameFiles


def test_case_and_separator_insensitive():
    gf = _env.gf()
    a = gf.read("art/tiles/tiles.lst")
    assert a == gf.read("ART\\TILES\\Tiles.LST") == gf.read("./art/tiles/tiles.lst")
    assert gf.exists("COLOR.PAL") and not gf.exists("art/tiles") and not gf.exists("no/such.file")
    assert "tiles.lst" in gf.listdir("art/tiles")
    assert len(gf.glob("maps/*.map")) == 155
    try:
        gf.read("maps/nosuch.map")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing file did not raise")


def test_overlay_wins_and_adds():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "Data"))
        os.makedirs(os.path.join(tmp, "maps"))
        with open(os.path.join(tmp, "Data", "MAPS.TXT"), "wb") as f:
            f.write(b"; replaced\r\n")
        with open(os.path.join(tmp, "maps", "newmap.map"), "wb") as f:
            f.write(b"x")
        gf = GameFiles(overlay=tmp)
        assert gf.read("data/maps.txt") == b"; replaced\r\n"
        assert gf.is_overridden("data/maps.txt") and not gf.is_overridden("data/city.txt")
        assert gf.read("data/city.txt") == _env.gf().read("data/city.txt")
        assert gf.exists("maps/NEWMAP.MAP") and "newmap.map" in gf.listdir("maps")
        assert len(gf.glob("maps/*.map")) == 156
        assert len(_env.gf().glob("maps/*.map")) == 155, "the base tree must stay untouched"


def test_overlay_priority_order():
    with tempfile.TemporaryDirectory() as high, tempfile.TemporaryDirectory() as low:
        for root, text in ((high, b"high"), (low, b"low")):
            with open(os.path.join(root, "color.pal"), "wb") as f:
                f.write(text)
        with open(os.path.join(low, "only_low.txt"), "wb") as f:
            f.write(b"low")
        gf = GameFiles(overlay=[high, low])
        assert gf.read("color.pal") == b"high"
        assert gf.read("only_low.txt") == b"low"


def test_parsed_views_are_cached():
    gf = _env.gf()
    assert gf.art_list(4) is gf.art_list(4)
    assert gf.protos is gf.protos and gf.palette is gf.palette and gf.scripts is gf.scripts
