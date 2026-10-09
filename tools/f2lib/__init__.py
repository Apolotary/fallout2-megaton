"""f2lib - offline tooling for Fallout 2 game data (fallout2-ce compatible).

Modules (each is small and usable on its own):

    ids        PID / FID / SID bit packing and the object-type table
    dat2       DAT2 archive reader and writer (``patchNNN.dat``)
    gamefiles  read-only virtual game tree (unpacked data + mod overlay)
    lst        ``.lst`` index <-> name helpers
    msg        ``.msg`` parse / serialise
    pro        prototype (``.pro``) parser / serialiser and lookup database
    pal        ``color.pal`` -> RGB, RGB -> palette index
    frm        FRM / FR0-5 decode to RGBA, encode from RGBA, art lookup by FID
    geometry   hex / square grid maths matching the engine
    map        ``.map`` parse / serialise / construct / validate
    mapstxt    ``data/maps.txt``: read the map table, append a map
    gam        ``.gam`` variable files
    cli        the ``python3 -m f2lib`` command line

Quick start::

    from f2lib import GameFiles, MapFile, write_dat2
    gf = GameFiles(overlay="mod/mymod/data") # the selected game with the mod's files on top
    m = MapFile.new("mymap", gf)
    m.set_floor(50, 50, "edg5000.frm")
    m.add_object(0x02000002, tile=20100)     # wooden door, defaults from proto
    problems = m.validate()                  # [] when the engine will accept the map
    write_dat2({"maps\\mymap.map": m.to_bytes()}, "patch001.dat")

Run ``python3 -m f2lib -h`` (from ``tools/``) for the command line.
"""
from .dat2 import Dat2, write_dat2
from .gamefiles import GameFiles
from .map import MapFile

__all__ = ["Dat2", "write_dat2", "GameFiles", "MapFile"]
