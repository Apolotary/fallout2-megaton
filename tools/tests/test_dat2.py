# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""DAT2 reader / writer."""
import os
import tempfile

import _env
from f2lib import Dat2, write_dat2
from f2lib.dat2 import pack_dir

def patch000():
    return _env.archive("patch000.dat")


def test_patch000_rebuild_is_byte_identical():
    """Extract every member of the GOG patch000.dat and pack it again: same bytes."""
    with Dat2(patch000()) as archive:
        files = archive.read_all(original_names=True)
        assert len(files) == 489
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "rebuilt.dat")
        assert write_dat2(files, out) == 489
        with open(out, "rb") as a, open(patch000(), "rb") as b:
            assert a.read() == b.read()


def test_reader_matches_unpacked_tree():
    """Members read through Dat2 equal the files of the merged extraction."""
    with Dat2(patch000()) as archive:
        assert archive.has("Data\\MAPS.TXT") and archive.has("data/maps.txt")
        for key in ("data/maps.txt", "scripts/scripts.lst", "maps/ncr1.map"):
            assert archive.read(key) == _env.gf().read(key), key
        entry = archive.entries["art/intrface/helpscrn.frm"]
        assert (entry.name, entry.compressed, entry.real_size) == ("Art\\intrface\\HELPSCRN.FRM", 1, 307274)


def test_write_read_round_trip():
    files = {"maps/B.MAP": b"\x01" * 5000, "Data\\a.txt": b"hello", "text/empty.msg": b"", "art/tiles/z_9.frm": bytes(range(256))}
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "patch001.dat")
        write_dat2(files, out)
        with Dat2(out) as archive:
            stored = [archive.entries[k].name for k in archive.order]
            assert stored == sorted(stored, key=str.lower), "tree must be sorted case-insensitively"
            assert "\\" in stored[0] and "/" not in "".join(stored)
            assert archive.read("MAPS\\b.map") == files["maps/B.MAP"]
            assert archive.read("data/A.TXT") == b"hello"
            assert archive.read("text/empty.msg") == b""
            assert archive.entries["text/empty.msg"].compressed == 0
            assert archive.entries["maps/b.map"].packed_size < 100

        stored_out = os.path.join(tmp, "stored.dat")
        write_dat2(files, stored_out, compress=False)
        with Dat2(stored_out) as archive:
            assert all(archive.entries[k].compressed == 0 for k in archive.order)
            assert archive.read_all() == {k.replace("\\", "/").lower(): v for k, v in files.items()}


def test_duplicate_names_are_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            write_dat2({"maps/a.map": b"1", "MAPS\\A.MAP": b"2"}, os.path.join(tmp, "x.dat"))
        except ValueError:
            return
    raise AssertionError("case-insensitive duplicate was accepted")


def test_pack_dir_and_extract():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src")
        os.makedirs(os.path.join(src, "maps"))
        with open(os.path.join(src, "maps", "x.map"), "wb") as f:
            f.write(b"map")
        with open(os.path.join(src, "top.txt"), "wb") as f:
            f.write(b"top")
        out = os.path.join(tmp, "p.dat")
        assert pack_dir(src, out) == 2
        with Dat2(out) as archive:
            assert archive.names() == ["maps/x.map", "top.txt"]
            assert archive.entries["maps/x.map"].name == "maps\\x.map"
            assert archive.extract(os.path.join(tmp, "dst"), globs=["maps/*"]) == 1
        with open(os.path.join(tmp, "dst", "maps", "x.map"), "rb") as f:
            assert f.read() == b"map"
