# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""FRM decode / encode and the palette."""
import os

import numpy as np

import _env
from f2lib import ids
from f2lib.frm import Frm, critter_suffix

# Every Nth art file is decoded; F2LIB_FULL=1 checks all of them (about a minute).
STRIDE = 1 if os.environ.get("F2LIB_FULL") else 9


def test_palette():
    pal = _env.gf().palette
    assert pal.rgb.shape == (256, 3) and pal.rgba.shape == (256, 4)
    assert pal.rgba[0].tolist() == [0, 0, 0, 0] and pal.rgba[1, 3] == 255
    assert int(pal.static.sum()) == 228 and not pal.static[0] and not pal.static[229:].any()
    assert pal.rgb[229].tolist() == [0, 108, 0], "animated ranges get their first colour"
    assert int(pal.rgb.max()) <= 252
    # the engine's own RGB555 table never yields transparent or animated indices
    assert pal.static[np.unique(pal.lut)].all()
    # quantising a palette colour gives a palette entry with that very colour
    for exact in (True, False):
        indices = pal.quantise(pal.rgb[1:229], exact=exact)
        assert pal.static[indices].all()
        if exact:
            assert (pal.rgb[indices] == pal.rgb[1:229]).all()


def test_decode_sample_of_every_art_type():
    gf = _env.gf()
    pal = gf.palette
    decoded = 0
    for obj_type, directory in enumerate(ids.TYPE_DIRS):
        files = [n for n in gf.listdir(f"art/{directory}") if n.endswith(".frm") or n[-4:-1] == ".fr"]
        assert files, directory
        for name in files[::STRIDE]:
            data = gf.read(f"art/{directory}/{name}")
            frm = Frm.from_bytes(data)
            assert frm.frame_count >= 1 and frm.direction_count in (1, 6), name
            assert frm.to_bytes() == data, f"art/{directory}/{name} does not round-trip"
            if not name.endswith(".frm"):
                assert frm.direction_count == 1, "a .fr0-.fr5 file holds one direction"
            for direction in (0, 3, 5):
                width, height = frm.size(direction)
                rgba = frm.rgba(pal, direction)
                assert rgba.shape == (height, width, 4) and rgba.dtype == np.uint8
                left, top, w, h = frm.placement(direction)
                assert (w, h) == (width, height) and left == frm.shift(direction)[0] - width // 2
            decoded += 1
    assert decoded > 1000


def test_known_art():
    gf = _env.gf()
    tile = gf.art.load(gf.art.fid(ids.OBJ_TYPE_TILE, "brick01.frm"))
    assert tile.size() == (80, 36) and tile.direction_count == 1 and tile.frame_count == 1 and tile.shift() == (0, 0)
    assert gf.art.path(0x040000BF) == "art/tiles/edg5000.frm"
    exit_grid = gf.art.load(0x05000011)
    assert exit_grid.size() == (96, 24) and exit_grid.shift(0) == (-32, 11)
    # critter: stand animation, six stored directions that differ
    warrior = gf.art.load(0x0100003E)
    assert gf.art.path(0x0100003E) == "art/critters/hmwarraa.frm" and warrior.direction_count == 6
    assert warrior.frame(0).pixels != warrior.frame(3).pixels
    image = warrior.image(gf.palette, direction=2)
    assert image.mode == "RGBA" and image.size == warrior.size(2)
    assert gf.art.exists(0x0100003E) and not gf.art.exists(ids.make_fid(ids.OBJ_TYPE_TILE, 4000))


def test_critter_file_suffixes():
    assert critter_suffix(0, 0) == "aa" and critter_suffix(1, 0) == "ab"
    assert critter_suffix(0, 5) == "ha" and critter_suffix(1, 1) == "db"       # pistol stand, knife walk
    assert critter_suffix(20, 0) == "ba" and critter_suffix(48, 0) == "ra" and critter_suffix(63, 3) == "rp"
    assert critter_suffix(38, 5) == "hc" and critter_suffix(38, 0) is None     # take out needs a weapon
    assert critter_suffix(36, 0) == "ch" and critter_suffix(37, 0) == "cj" and critter_suffix(64, 0) == "na"
    assert critter_suffix(18, 1) == "dm" and critter_suffix(18, 4) == "gm" and critter_suffix(18, 0) == "as"
    assert critter_suffix(13, 0) == "an" and critter_suffix(13, 5) == "he"
    gf = _env.gf()
    assert gf.art.path(ids.make_fid(ids.OBJ_TYPE_CRITTER, 62, anim=20)) == "art/critters/hmwarrba.frm"
    split = ids.make_fid(ids.OBJ_TYPE_CRITTER, 1, anim=20, rotation_plus_1=1)       # power armor, fall back, NE
    assert gf.art.path(split) == "art/critters/hapowrba.fr0" and gf.art.load(split).direction_count == 1


def test_encode_decode_round_trip():
    gf = _env.gf()
    pal = gf.palette
    rng = np.random.default_rng(7)
    static = np.flatnonzero(pal.static)

    # 1. synthetic image made of palette colours with a transparent border
    indices = static[rng.integers(0, len(static), size=(36, 80))]
    rgba = pal.rgba[indices].copy()
    rgba[:4, :] = 0
    rgba[:, :6] = (10, 20, 30, 0)
    frm = Frm.from_rgba([rgba], pal, shift=(3, -5), fps=10)
    back = Frm.from_bytes(frm.to_bytes())
    assert back.size() == (80, 36) and back.shift(4) == (3, -5) and back.fps == 10 and back.direction_count == 1
    expected = rgba.copy()
    expected[rgba[:, :, 3] == 0] = 0
    assert (back.rgba(pal) == expected).all()
    assert not np.isin(back.frame().array(), np.arange(229, 256)).any(), "encoder used an animated index"

    # 2. real art: decode -> encode -> decode gives the same picture
    for fid in (0x040000BF, 0x02000001, 0x0300006C, 0x0100003E):
        source = gf.art.load(fid)
        picture = source.rgba(pal, 2)
        again = Frm.from_bytes(Frm.from_rgba([picture], pal, shift=source.shift(2)).to_bytes())
        assert (again.rgba(pal) == picture).all(), hex(fid)
        assert again.placement() == source.placement(2)

    # 3. six directions, two frames each, arbitrary colours (quantised, never transparent by accident)
    photos = [[rng.integers(0, 256, size=(20, 12, 4), dtype=np.uint8) for _ in range(2)] for _ in range(6)]
    six = Frm.from_bytes(Frm.from_rgba(photos, pal, shift=[(d, -d) for d in range(6)]).to_bytes())
    assert six.direction_count == 6 and six.frame_count == 2 and six.shift(5) == (5, -5)
    for d in range(6):
        for i in range(2):
            opaque = photos[d][i][:, :, 3] >= 128
            assert ((six.frame(d, i).array() != 0) == opaque).all()
            assert pal.static[six.frame(d, i).array()[opaque]].all()
    # PIL images are accepted too
    from PIL import Image
    pil = Frm.from_rgba([Image.fromarray(photos[0][0], "RGBA")], pal)
    assert pil.frame().pixels == six.frame(0, 0).pixels
