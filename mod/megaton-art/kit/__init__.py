# SPDX-License-Identifier: MIT
"""Megaton art kit: what a piece script imports.

    from kit import piece, geo, mat, G

    @piece("mg_crate", title="Crate", desc="A supply crate, nailed shut.")
    def mg_crate(ctx):
        geo.crate(at=(0, 0, 0))

`piece` registers a builder; `pipeline/blender_piece.py` (run by build.py) calls it in a fresh
scene per frame, renders the passes and writes the piece's meta data. The builder only creates
objects: camera, light, ground, rendering and sprite cutting are not its business.

ctx.frame   animation frame being built (0 for stills)
ctx.frames  number of frames
ctx.rng     random.Random seeded from the piece name (use it, never the global random)

OPTIONS of @piece (all optional except the name)
  title, desc      proto name and description shown by the game ("You see: ...")
  kind             "scenery" (default) or "wall" (blocks light and sight by the engine's wall rules;
                   use for runs of perimeter / building wall only)
  footprint        the hexes the piece BLOCKS. "auto" (default): worked out from the geometry,
                   object by object (kit.geo, "BLOCK"): props block the hex they stand on, wall
                   runs block like stock walls. Or a list of (dhx, dhy); [] = nothing blocks.
                   Always check the red hexes in the preview.
  also_block       hexes blocked in addition to the footprint, [(dhx, dhy)]; default: the piece's row in
                   kit/also_block.json (written by pipeline/sortfix.py from the draw-order test)
  block_radius     None (default): every object's own radius. A number overrides them all.
  block_height     1.5 m: things above head height never block
  anchors          the hexes the picture is CUT on (one sprite part per hex). "auto" (default):
                   every pixel goes to the nearest blocked hex at or behind the surface it shows
                   (pipeline/slicer.py explains why that sorts correctly); anything that hangs
                   more than `overhang` m away from every blocked hex (an awning, a sign over a
                   gateway) is cut onto the walkable hexes under it as parts that do not block.
                   Or a list of (dhx, dhy) to force the cut.
  overhang         1.0 m
  shadow           "flat" (default): soft ground shadow as its own flat sprite under everything;
                   "baked": inside the sprite like stock props (small props only); "none"
  see_through      False (default): solid, never fades. True, "u" or "v": fades in a circle around
                   the player when he is hidden by it, like stock walls - set it on anything tall
                   the player can walk behind. "u" = the piece runs along a hex row, "v" = along
                   a hex column; True picks per part from its shape. (The engine has exactly these
                   two rules; a part that runs both ways should be two pieces.)
  sight            "through" (default for scenery) or "blocks" (default for walls): light and line
                   of sight; "blocks" also stops bullets.
  light            (distance_hexes 1..8, intensity_percent): the piece is a lamp. The engine lights
                   the hexes around `light_hex` (default (0, 0)) and the part on it stays bright at
                   night. White light only; add geo.halo() for the warm pool.
  frames, fps      animation (scenery only): the builder is called once per frame with ctx.frame,
                   every part becomes a multi-frame FRM, and placing the piece attaches the stock
                   script "animfrvr" (animate for ever) - scenery never animates by itself. Change
                   materials / emitters between frames, not the outline: all frames share one cut.
  material         what it sounds like when hit: "metal" (default), "wood", "stone", "cement",
                   "glass", "dirt", "leather", "plastic"
  convert          dict of palette conversion options (pipeline/convert.py DEFAULTS), e.g.
                   {"dither": "none"} or {"forbid": ["purple", "green"]}
  samples, ss      render quality overrides
"""
import random
import zlib

from pipeline import proj as G      # noqa: F401  (re-exported)

REGISTRY = {}


def _also_block():
    import json
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "also_block.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {name: hexes for name, hexes in json.load(f).items() if not name.startswith("_")}


ALSO_BLOCK = _also_block()

DEFAULT_SPEC = {
    "title": None, "desc": None, "kind": "scenery",
    "footprint": "auto", "block_radius": None, "block_height": 1.5,
    # also_block: hexes blocked IN ADDITION to the automatic footprint (kit/also_block.json holds a table by piece
    # name: the hexes on which the draw-order test, `build.py sort`, found a critter painted over something that
    # stands in front of him - the same job the "Wall s.t." blockers do in front of every stock wall)
    "also_block": None,
    "anchors": "auto", "overhang": 1.0,
    "shadow": "flat", "see_through": False, "sight": None,
    "light": None, "light_hex": (0, 0),
    # use=True: the player can USE the piece (hand cursor, "use" in the action menu): its protos get the
    # engine's use-action flag. Without it a click only examines, and a script's use_p_proc is never
    # reached from the mouse. For pieces that carry a script with use_p_proc (the bomb).
    "use": False,
    "frames": 1, "fps": 10, "material": "metal",
    "convert": {}, "samples": None, "ss": None,
}


class Context:
    def __init__(self, name, frame=0, frames=1):
        self.name = name
        self.frame = frame
        self.frames = frames
        self.rng = random.Random(zlib.crc32(name.encode()))


def piece(name, **options):
    """Decorator: register `function(ctx)` as the builder of piece `name` (a-z, 0-9, _; max 24)."""
    if not name.replace("_", "").isalnum() or name != name.lower() or len(name) > 24:
        raise ValueError(f"piece name {name!r}: use lower-case letters, digits and '_' (at most 24)")
    unknown = set(options) - set(DEFAULT_SPEC)
    if unknown:
        raise TypeError(f"piece {name!r}: unknown option(s) {sorted(unknown)}")
    spec = dict(DEFAULT_SPEC)
    spec.update(options)
    spec["name"] = name
    if spec["also_block"] is None:
        spec["also_block"] = [list(h) for h in ALSO_BLOCK.get(name, [])]
    if spec["title"] is None:
        spec["title"] = name.replace("_", " ").title()
    if spec["desc"] is None:
        spec["desc"] = ""
    if spec["sight"] is None:
        spec["sight"] = "blocks" if spec["kind"] == "wall" else "through"
    if spec["kind"] not in ("scenery", "wall"):
        raise ValueError(f"piece {name!r}: kind must be 'scenery' or 'wall'")
    if spec["kind"] == "wall" and int(spec["frames"]) > 1:
        raise ValueError(f"piece {name!r}: walls cannot be animated; make the moving part a scenery piece")
    if spec["see_through"] not in (False, True, "u", "v"):
        raise ValueError(f"piece {name!r}: see_through must be False, True, 'u' or 'v'")
    if spec["shadow"] not in ("flat", "baked", "none"):
        raise ValueError(f"piece {name!r}: shadow must be 'flat', 'baked' or 'none'")
    if spec["light"] is not None and not (1 <= spec["light"][0] <= 8 and 0 < spec["light"][1] <= 100):
        raise ValueError(f"piece {name!r}: light is (distance 1..8 hexes, intensity 1..100 percent)")

    def register(function):
        if name in REGISTRY:
            raise ValueError(f"piece {name!r} is defined twice")
        REGISTRY[name] = (spec, function)
        return function
    return register


# ----------------------------------------------------------------------- tile sheets
from pipeline import tilegeo as T   # noqa: E402,F401  (re-exported: T.Shack, T.hex_xy, T.SQ_U ...)

SHEETS = {}

DEFAULT_SHEET = {
    "kind": "roof",             # "roof" | "floor"
    "size": (1, 1),             # (N, M) squares: N along +x (qx), M along +y (qy)
    "wrap": False,              # True: the sheet repeats seamlessly (its geometry is rendered with eight
                                # copies of itself around it); paint it over any area, any size
    "decal": False,             # floors only. False: every pixel of every tile must be painted (a floor
                                # tile's holes show BLACK). True: junk, stains, planks lying on whatever
                                # ground is there - the build lays each tile over the floor tile it lands on
    "eave_shadow": None,        # roofs: px of stippled shadow under the roof's lower edge, as on the stock
                                # eaves (None = 9 for roofs; 0 = none)
    "shadow": None,             # decals: None / True = things lying on the ground throw a stippled shadow
    "title": None,
    "convert": {}, "samples": None, "ss": None,
}


class SheetContext:
    """What a sheet builder gets: sizes and the same seeded rng as a piece.

    ctx.n, ctx.m     squares along +x / +y;  ctx.w, ctx.h  the same in metres
    ctx.kind         "roof" or "floor";  ctx.rng  random.Random seeded from the sheet's name
    ctx.square(i, j) (x, y) of the far corner of square (i, j);  ctx.hex(dhx, dhy)  see T.hex_xy
    """

    def __init__(self, name, spec):
        self.name = name
        self.spec = spec
        self.kind = spec["kind"]
        self.n, self.m = spec["size"]
        self.w, self.h = T.size_m(self.n, self.m)
        self.frame, self.frames = 0, 1
        self.rng = random.Random(zlib.crc32(name.encode()))

    square = staticmethod(T.square_xy)
    hex = staticmethod(T.hex_xy)


def sheet(name, **options):
    """Decorator: register `function(ctx)` as the builder of tile sheet `name` (a-z, 0-9, _; max 24).

        @sheet("rf_saloon", kind="roof", size=T.Shack(BOX).size)
        def rf_saloon(ctx):
            ...create objects with kit.geo / kit.mat, in SHEET coordinates (pipeline/tilegeo.py):
               x 0..ctx.w, y 0..ctx.h, z = height above the roof plane (roofs) or the ground (floors)
    """
    if not name.replace("_", "").isalnum() or name != name.lower() or len(name) > 24:
        raise ValueError(f"sheet name {name!r}: use lower-case letters, digits and '_' (at most 24)")
    unknown = set(options) - set(DEFAULT_SHEET)
    if unknown:
        raise TypeError(f"sheet {name!r}: unknown option(s) {sorted(unknown)}")
    spec = dict(DEFAULT_SHEET)
    spec.update(options)
    spec["name"] = name
    spec["size"] = tuple(int(v) for v in spec["size"])
    if spec["kind"] not in ("roof", "floor"):
        raise ValueError(f"sheet {name!r}: kind must be 'roof' or 'floor'")
    if len(spec["size"]) != 2 or min(spec["size"]) < 1 or max(spec["size"]) > 24:
        raise ValueError(f"sheet {name!r}: size is (N, M) squares, each 1..24")
    if spec["decal"] and spec["kind"] != "floor":
        raise ValueError(f"sheet {name!r}: only floors can be decals (a roof's holes are simply transparent)")
    if spec["eave_shadow"] is None:
        spec["eave_shadow"] = 9 if spec["kind"] == "roof" and not spec["wrap"] else 0
    if spec["shadow"] is None:
        spec["shadow"] = bool(spec["decal"])
    if spec["title"] is None:
        spec["title"] = name.replace("_", " ").title()

    def register(function):
        if name in SHEETS or name in REGISTRY:
            raise ValueError(f"{name!r} is defined twice")
        SHEETS[name] = (spec, function)
        return function
    return register


try:                                    # the rest needs Blender; `piece` and G work anywhere
    from . import geo, mat              # noqa: E402,F401
except ImportError:                     # pragma: no cover - outside Blender
    geo = mat = None
