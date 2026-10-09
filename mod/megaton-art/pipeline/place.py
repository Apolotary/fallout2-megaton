# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Put a built piece on a map (f2lib MapFile). This is what a town layout script calls.

    from pipeline.place import Placer
    placer = Placer()                               # reads manifest.json; needs out/ built
    gf = GameFiles(overlay=[..., placer.overlay])   # the map must see the art mod's protos
    placer.place(m, "mg_gate", g.tile_at(100, 96))  # origin hex: EVEN hx and EVEN hy

place() adds, in this order: the flat parts (shadow, halo), the main parts in engine paint
order, glow parts, and one stock invisible blocker ("Secret Blocking Hex", 0x02000043) on every
footprint hex that carries no part. Animated parts get the stock script "animfrvr" attached
(scenery only animates when a script starts it: there is no engine-side idle animation for
scenery, see animation.cc / scripts; the stock casino signs and the NCR flag work the same way).
Lamps need nothing: the part's proto carries light distance / intensity and f2lib sets the
object's LIGHTING flag from it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from f2lib import geometry as g      # noqa: E402

from . import data                    # noqa: E402

LAYER_ORDER = {"shadow": 0, "halo": 1, "main": 2, "glow": 3}


class Placer:
    def __init__(self, manifest=None):
        self.manifest = manifest or data.load_manifest()
        self.overlay = data.OUT

    def names(self):
        return list(self.manifest["pieces"])

    def piece(self, name):
        try:
            return self.manifest["pieces"][name]
        except KeyError:
            raise KeyError(f"no piece {name!r} in manifest.json (has: {', '.join(self.names())})") from None

    def hexes(self, name, tile, what="footprint"):
        """Tiles of a piece's footprint (or 'parts') when its origin is on `tile`."""
        hx, hy = g.tile_xy(tile)
        piece = self.piece(name)
        offsets = piece["footprint"] if what == "footprint" else [part["hex"] for part in piece["parts"]]
        return [g.tile_at(hx + dhx, hy + dhy) for dhx, dhy in offsets]

    def place(self, m, name, tile, elevation=0, blockers=True):
        """Add piece `name` with its origin hex on `tile`; returns the objects created."""
        hx, hy = g.tile_xy(tile)
        if hx & 1 or hy & 1:
            raise ValueError(f"piece {name!r}: origin hex ({hx}, {hy}) must have even hx and even hy")
        piece = self.piece(name)
        created = []
        parts = sorted(piece["parts"], key=lambda part: (LAYER_ORDER.get(part["layer"], 2),
                                                         part["hex"][1] * 200 + part["hex"][0]))
        for part in parts:
            target = g.tile_at(hx + part["hex"][0], hy + part["hex"][1])
            if target < 0:
                raise ValueError(f"piece {name!r} leaves the map at hex {part['hex']}")
            created.append(m.add_object(int(part["pid"], 16), target, elevation=elevation, script=part["script"]))
        if blockers:
            for dhx, dhy in piece["blockers"]:
                created.append(m.add_object(int(piece["blocker_pid"], 16), g.tile_at(hx + dhx, hy + dhy),
                                            elevation=elevation))
        return created
