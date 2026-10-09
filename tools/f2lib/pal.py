"""``color.pal``: the game palette.

File layout (color.cc:294-366): 256 x (R, G, B) with 6-bit components, then a
32768-byte RGB555 -> palette index table. Entry 0 is the transparent colour.
Entries 229..254 are rewritten at run time by the colour-cycling ticker
(cycle.cc:25-75) and are "unmapped" (0xFF) in the file, so a static renderer
needs substitutes: `Palette` uses the first colour of each cycle.

New art must only use indices 1..228; `Palette.quantise` guarantees that.
"""
import numpy as np

# First index and 8-bit colours of each animated range, in palette order at rest.
ANIMATED_RANGES = {
    "slime": (229, [(0, 108, 0), (11, 115, 7), (27, 123, 15), (43, 131, 27)]),
    "monitors": (233, [(107, 107, 111), (99, 103, 127), (87, 107, 143), (0, 147, 163), (107, 187, 255)]),
    "fire_slow": (238, [(255, 0, 0), (215, 0, 0), (147, 43, 11), (255, 119, 0), (255, 59, 0)]),
    "fire_fast": (243, [(71, 0, 0), (123, 0, 0), (179, 0, 0), (123, 0, 0), (71, 0, 0)]),
    "shoreline": (248, [(83, 63, 43), (75, 59, 43), (67, 55, 39), (63, 51, 39), (55, 47, 35), (51, 43, 35)]),
}
ALARM_INDEX = 254                 # red ramps 0..240, shown here at full brightness
FIRST_ANIMATED = 229


class Palette:
    """Palette with numpy views.

    rgb      (256, 3) uint8   8-bit colours, animated ranges substituted
    rgba     (256, 4) uint8   same with alpha: 0 for index 0, 255 otherwise
    static   (256,) bool      True for indices new art may use (1..228, mapped)
    lut      (32768,) uint8   the engine's own RGB555 -> index table
    """

    def __init__(self, data, static_cycle=True):
        if len(data) < 768 + 32768:
            raise ValueError("color.pal is too short")
        self.raw = bytes(data)
        six_bit = np.frombuffer(self.raw, dtype=np.uint8, count=768).reshape(256, 3)
        mapped = (six_bit <= 63).all(axis=1)
        self.rgb = np.where(mapped[:, None], six_bit * 4, 0).astype(np.uint8)
        if static_cycle:
            for start, colours in ANIMATED_RANGES.values():
                for offset, colour in enumerate(colours):
                    self.rgb[start + offset] = [(c >> 2) << 2 for c in colour]
            self.rgb[ALARM_INDEX] = (240, 0, 0)
        self.rgba = np.concatenate([self.rgb, np.full((256, 1), 255, np.uint8)], axis=1)
        self.rgba[0] = 0
        self.static = mapped.copy()
        self.static[0] = False
        self.static[FIRST_ANIMATED:] = False
        self.lut = np.frombuffer(self.raw, dtype=np.uint8, count=32768, offset=768)
        self._static_indices = np.flatnonzero(self.static)

    def quantise(self, rgb, exact=True):
        """(..., 3) uint8 colours -> palette indices of the same leading shape.

        exact=True picks the nearest static colour (Euclidean RGB, lowest index
        on ties); exact=False uses the engine's RGB555 table (faster, coarser).
        Neither ever returns 0 or an animated index.
        """
        rgb = np.asarray(rgb, dtype=np.uint8)
        flat = rgb.reshape(-1, 3)
        if not exact:
            packed = ((flat[:, 0].astype(np.int32) >> 3) << 10) | ((flat[:, 1].astype(np.int32) >> 3) << 5) | (flat[:, 2] >> 3)
            return self.lut[packed].reshape(rgb.shape[:-1])
        packed = (flat[:, 0].astype(np.int32) << 16) | (flat[:, 1].astype(np.int32) << 8) | flat[:, 2]
        unique, inverse = np.unique(packed, return_inverse=True)
        colours = np.stack([(unique >> 16) & 255, (unique >> 8) & 255, unique & 255], axis=1).astype(np.int32)
        candidates = self.rgb[self._static_indices].astype(np.int32)
        best = np.empty(len(colours), dtype=np.uint8)
        for start in range(0, len(colours), 4096):
            chunk = colours[start:start + 4096]
            distance = ((chunk[:, None, :] - candidates[None, :, :]) ** 2).sum(axis=2)
            best[start:start + 4096] = self._static_indices[distance.argmin(axis=1)]
        return best[inverse].reshape(rgb.shape[:-1])
