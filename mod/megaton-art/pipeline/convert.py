# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Render (RGBA, supersampled) -> 8-bit sprite pixels in the game's fixed palette.

What the engine gives us (research/05 section 9, object.cc:2756-2783):
  - 256 colours, index 0 transparent: 1-bit alpha, so every edge pixel is either in or out.
  - indices 1..228 are fixed colours; a sprite is darkened at night by mapping each of them to
    a darker palette entry.
  - indices 229..254 are rewritten by the palette-cycling ticker AND are skipped by the night
    darkening (`if (color < 0xE5)`): they are the game's only self-lit colours. They are never
    used by the quantiser. A piece gets them only on surfaces it tags by name
    (kit.geo.set_fx -> a coverage mask per range -> apply_fx below), never by colour matching.

Pipeline for one frame (convert_frame):
  1. box-filter the supersampled render down in linear light, premultiplied - edge pixels keep
     the object's own colour, never a blend with a background, so there is no fringe to clean;
  2. grade (optional exposure / contrast / saturation; the scene template is already calibrated);
  3. alpha >= alpha_threshold is kept, everything else is transparent; single stray pixels go;
  4. silhouette pixels are darkened like the hand-touched edges of stock sprites: more on the
     side away from the light (right, bottom) than towards it (left, top);
  5. nearest palette colour in Oklab with extra weight on hue/chroma error (a grey-brown never
     turns greenish to gain a little lightness accuracy), ordered dithering in lightness at low
     strength so gradients do not band and frames of an animation do not shimmer.

Palette facts worth knowing when choosing material colours (measured by `palette_report`):
  warm browns are rich: tan 117-125, orange 141-155, sand 156-168, rust 169-181, flesh 182-195,
  earth 221-227 - over 70 entries between cream and black-brown, so rust, wood, dirt and
  tarnished metal grade smoothly; greys have 19 steps; olive / khaki / sage about 30.
  Poor: saturated blue (the steel ramp 101-111 tops out at a dusty (64,108,140)), cyan (none),
  purple (8 entries), and anything light AND saturated except yellow 56-58, red 126-133,
  orange 141-148, green 196/215. A neon tube must therefore be red, orange, yellow or green.
  Night: the engine darkens every fixed colour, so baked glow dims with the map unless the
  piece is a lamp (its own hex is lit) or the surface uses an animated range (FX).
"""
import numpy as np

# ---------------------------------------------------------------- palette map
RAMPS = {
    "grey": list(range(1, 16)) + [202, 207, 208, 220, 228],
    "rose": list(range(16, 32)),
    "bluegrey": list(range(32, 48)),
    "purple": list(range(48, 56)),
    "yellow": list(range(56, 69)),
    "lime": list(range(69, 76)),
    "khaki": list(range(76, 85)),
    "sage": list(range(85, 89)),
    "teal": list(range(89, 96)),
    "forest": list(range(96, 101)),
    "steel": list(range(101, 117)),
    "tan": list(range(117, 126)),
    "red": list(range(126, 141)),
    "orange": list(range(141, 156)),
    "sand": list(range(156, 169)),
    "rust": list(range(169, 182)),
    "flesh": list(range(182, 196)),
    "green": [196, 197, 198, 200] + list(range(215, 220)),
    "olivegrey": [199, 201] + list(range(209, 215)),
    "earth": [203, 204, 205, 206] + list(range(221, 228)),
}
# Animated ranges (cycle.cc:25-75). Never darkened at night. Rest colours in palette order.
FX = {
    "slime": (229, [(0, 108, 0), (11, 115, 7), (27, 123, 15), (43, 131, 27)]),            # shimmers, 200 ms: reads as a steady green glow
    "monitors": (233, [(107, 107, 111), (99, 103, 127), (87, 107, 143), (0, 147, 163), (107, 187, 255)]),  # 100 ms blue flicker
    "fire": (238, [(255, 0, 0), (215, 0, 0), (147, 43, 11), (255, 119, 0), (255, 59, 0)]),  # 200 ms red/orange flicker
    "embers": (243, [(71, 0, 0), (123, 0, 0), (179, 0, 0), (123, 0, 0), (71, 0, 0)]),       # 142 ms dark red pulse
    "shore": (248, [(83, 63, 43), (75, 59, 43), (67, 55, 39), (63, 51, 39), (55, 47, 35), (51, 43, 35)]),
    "alarm": (254, [(240, 0, 0)]),                                                        # one index ramping black <-> red: a blinking lamp
}
BLACK = 228               # opaque black (index 0 is the transparent one)

DEFAULTS = {
    "alpha_threshold": 0.5,
    "despeckle": True,          # drop opaque pixels with no opaque 4-neighbour, fill 1-pixel holes
    "dither": "ordered",        # "ordered" | "fs" (error diffusion; stills only) | "none"
    "dither_strength": 0.35,    # 0..1; 0.35 hides banding without visible pattern
    "chroma_weight": 2.2,       # weight of hue/chroma error against lightness error
    "outline": 0.40,            # darkening of silhouette pixels facing away from the light (0 = off)
    "outline_lit": 0.12,        # ... facing the light
    "exposure": 0.0,            # stops, applied after rendering
    "contrast": 1.2,            # power curve in linear light around `pivot`; stock art is contrasty:
                                # its darkest 5 % sit near luminance 12-25, its brightest 5 % near 84-95
    "pivot": 0.04,              # linear value that contrast leaves alone (sRGB 56: the stock median)
    "saturation": 1.1,
    "allow": None,              # list of ramp names: only these may be used
    "forbid": (),               # ramp names never to use, e.g. ("purple", "green")
    "shadow_gain": 1.0,         # density of the dithered ground shadow
    "shadow_max": 0.56,         # densest allowed: 0.5 = checkerboard, 1 = solid black
    "shadow_floor": 0.30,       # weaker than this is dropped: keeps the sun's shadow, drops the faint
                                # sky occlusion all round the base, which only reads as stray dots
    "halo_levels": 3,           # strongest tint step a halo may use (1..6: 1/7 .. 6/7 yellow)
}

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16.0 + 1.0 / 32.0
BAYER8 = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
                   [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
                   [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                   [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]], np.float32) / 64.0 + 1.0 / 128.0


def options(overrides=None):
    merged = dict(DEFAULTS)
    for key, value in (overrides or {}).items():
        if key not in DEFAULTS:
            raise KeyError(f"unknown convert option {key!r} (known: {', '.join(sorted(DEFAULTS))})")
        merged[key] = value
    return merged


# -------------------------------------------------------------- colour maths
def srgb_to_linear(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0.0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def linear_to_oklab(rgb):
    rgb = np.asarray(rgb, np.float32)
    l = 0.4122214708 * rgb[..., 0] + 0.5363325363 * rgb[..., 1] + 0.0514459929 * rgb[..., 2]
    m = 0.2119034982 * rgb[..., 0] + 0.6806995451 * rgb[..., 1] + 0.1073969566 * rgb[..., 2]
    s = 0.0883024619 * rgb[..., 0] + 0.2817188376 * rgb[..., 1] + 0.6299787005 * rgb[..., 2]
    l, m, s = np.cbrt(np.maximum(l, 0)), np.cbrt(np.maximum(m, 0)), np.cbrt(np.maximum(s, 0))
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], axis=-1)


# -------------------------------------------------------------------- loading
def load_rgba(path):
    """PNG -> float32 (h, w, 4), sRGB-encoded straight alpha, 0..1."""
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGBA"), np.float32) / 255.0


def downsample(rgba, ss):
    """Box filter in linear light with premultiplied alpha -> (rgb linear straight (h, w, 3), alpha (h, w))."""
    h, w = rgba.shape[0] // ss, rgba.shape[1] // ss
    rgba = rgba[:h * ss, :w * ss]
    alpha = rgba[..., 3]
    premultiplied = srgb_to_linear(rgba[..., :3]) * alpha[..., None]
    premultiplied = premultiplied.reshape(h, ss, w, ss, 3).mean(axis=(1, 3))
    alpha = alpha.reshape(h, ss, w, ss).mean(axis=(1, 3))
    rgb = premultiplied / np.maximum(alpha, 1e-6)[..., None]
    return rgb, alpha


def load_positions(path, position_meta, ss):
    """pos.png -> (xyz (h, w, 3) float32, valid (h, w) bool) at sprite resolution.

    Every sprite pixel takes the position of its sub-sample nearest to the camera: at a
    silhouette that is the surface in front, which is the one the pixel will show.
    """
    import cv2
    from . import proj as P
    raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if raw is None or raw.dtype != np.uint16 or raw.shape[2] != 4:
        raise ValueError(f"{path}: expected a 16-bit RGBA PNG")
    values = raw[..., [2, 1, 0]].astype(np.float32) / 65535.0
    hit = raw[..., 3] > 32767
    rng = position_meta["range"]
    xyz = np.stack([values[..., 0] * rng - rng / 2.0, values[..., 1] * rng - rng / 2.0,
                    values[..., 2] * position_meta["zrange"] + position_meta["z0"]], axis=-1)
    h, w = raw.shape[0] // ss, raw.shape[1] // ss
    xyz = xyz[:h * ss, :w * ss].reshape(h, ss, w, ss, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, ss * ss, 3)
    hit = hit[:h * ss, :w * ss].reshape(h, ss, w, ss).transpose(0, 2, 1, 3).reshape(h, w, ss * ss)
    depth = xyz @ np.asarray(P.VIEW_DIR, np.float32)
    depth = np.where(hit, depth, np.inf)
    nearest = depth.argmin(axis=2)
    rows, cols = np.indices((h, w))
    return xyz[rows, cols, nearest], hit.any(axis=2)


# -------------------------------------------------------------------- palette
class Quantiser:
    """Nearest palette colour in Oklab among the indices a piece may use."""

    def __init__(self, palette, opts):
        self.opts = opts
        allowed = np.zeros(256, bool)
        ramps = opts["allow"] if opts["allow"] else list(RAMPS)
        for name in ramps:
            allowed[RAMPS[name]] = True
        for name in opts["forbid"]:
            allowed[RAMPS[name]] = False
        allowed &= palette.static                   # 1..228 only: the animated ranges are never candidates here
        rgb = palette.rgb.astype(np.float32)
        self.indices = np.flatnonzero(allowed)
        if len(self.indices) < 2:
            raise ValueError("the allow / forbid lists leave fewer than two colours")
        self.rgb = rgb
        self.lab = linear_to_oklab(srgb_to_linear(rgb[self.indices] / 255.0))
        self.weights = np.array([1.0, opts["chroma_weight"], opts["chroma_weight"]], np.float32)

    def nearest(self, lab):
        """(n, 3) Oklab -> palette indices (n,)."""
        out = np.empty(len(lab), np.uint8)
        candidates = self.lab * self.weights
        for start in range(0, len(lab), 8192):
            chunk = lab[start:start + 8192] * self.weights
            distance = ((chunk[:, None, :] - candidates[None, :, :]) ** 2).sum(axis=2)
            out[start:start + 8192] = self.indices[distance.argmin(axis=1)]
        return out

    def quantise(self, rgb_linear, mask):
        """(h, w, 3) linear RGB + (h, w) bool -> (h, w) uint8 indices, 0 outside the mask."""
        opts = self.opts
        h, w = mask.shape
        out = np.zeros((h, w), np.uint8)
        ys, xs = np.nonzero(mask)
        if not len(ys):
            return out
        lab = linear_to_oklab(rgb_linear[ys, xs])
        if opts["dither"] == "ordered" and opts["dither_strength"] > 0:
            threshold = BAYER4[ys % 4, xs % 4] - 0.5
            lab = lab.copy()
            lab[:, 0] += threshold * 0.055 * opts["dither_strength"]
            out[ys, xs] = self.nearest(lab)
        elif opts["dither"] == "fs" and opts["dither_strength"] > 0:
            out[:] = self._diffuse(linear_to_oklab(rgb_linear), mask, opts["dither_strength"])
        else:
            out[ys, xs] = self.nearest(lab)
        return out

    def _diffuse(self, lab, mask, strength):
        """Floyd-Steinberg in Oklab, error scaled by `strength`, never carried across transparency."""
        h, w = mask.shape
        work = lab.astype(np.float32).copy()
        out = np.zeros((h, w), np.uint8)
        table = self.lab
        candidates = table * self.weights
        for y in range(h):
            for x in range(w):
                if not mask[y, x]:
                    continue
                value = work[y, x]
                distance = (((value * self.weights) - candidates) ** 2).sum(axis=1)
                best = int(distance.argmin())
                out[y, x] = self.indices[best]
                error = (value - table[best]) * strength
                error = np.clip(error, -0.08, 0.08)
                for dx, dy, share in ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and ny < h and mask[ny, nx]:
                        work[ny, nx] += error * share
        return out


# ---------------------------------------------------------------------- steps
def grade(rgb_linear, opts):
    rgb = rgb_linear
    if opts["exposure"]:
        rgb = rgb * (2.0 ** opts["exposure"])
    if opts["contrast"] != 1.0:
        luma = (rgb * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(axis=-1, keepdims=True)
        luma = np.maximum(luma, 1e-6)
        rgb = rgb * (opts["pivot"] * np.power(luma / opts["pivot"], opts["contrast"]) / luma)
    if opts["saturation"] != 1.0:
        luma = (rgb * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(axis=-1, keepdims=True)
        rgb = luma + (rgb - luma) * opts["saturation"]
    return np.clip(rgb, 0.0, 1.0)


def alpha_mask(alpha, opts):
    mask = alpha >= opts["alpha_threshold"]
    if opts["despeckle"]:
        padded = np.pad(mask, 1)
        neighbours = (padded[:-2, 1:-1].astype(np.int8) + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:])
        mask = (mask & (neighbours > 0)) | (~mask & (neighbours == 4) & (alpha >= opts["alpha_threshold"] * 0.5))
    return mask


def darken_outline(rgb_linear, mask, opts):
    """Darken silhouette pixels: `outline` where the neighbour to the right or below is empty
    (the side away from the key light), `outline_lit` where the one to the left or above is."""
    if not (opts["outline"] or opts["outline_lit"]):
        return rgb_linear
    padded = np.pad(mask, 1)
    shade_side = ~padded[1:-1, 2:] | ~padded[2:, 1:-1]
    lit_side = ~padded[1:-1, :-2] | ~padded[:-2, 1:-1]
    factor = np.ones(mask.shape, np.float32)
    factor[mask & lit_side] = 1.0 - opts["outline_lit"]
    factor[mask & shade_side] = 1.0 - opts["outline"]
    return rgb_linear * factor[..., None]


def convert_frame(rgba_ss, ss, quantiser, opts, mask=None):
    """One supersampled RGBA frame -> (indices (h, w) uint8, mask, graded linear rgb, alpha)."""
    rgb, alpha = downsample(rgba_ss, ss)
    rgb = grade(rgb, opts)
    if mask is None:
        mask = alpha_mask(alpha, opts)
    edged = darken_outline(rgb, mask, opts)
    return quantiser.quantise(edged, mask), mask, rgb, alpha


def shadow_mask(total_alpha, object_alpha, opts, origin=(0, 0)):
    """Ground shadow as a 1-bit dither. total_alpha: alpha of the shadow-catcher render,
    object_alpha: alpha of the beauty render (both at sprite resolution).
    origin: canvas position of pixel (0, 0), so the dither pattern is fixed to the map, not the sprite."""
    strength = np.clip((total_alpha - object_alpha) / np.maximum(1.0 - object_alpha, 1e-3), 0.0, 1.0)
    strength[object_alpha > 0.98] = 0.0
    density = np.clip(strength * opts["shadow_gain"], 0.0, opts["shadow_max"])
    density[strength < opts["shadow_floor"]] = 0.0
    h, w = density.shape
    ys, xs = np.indices((h, w))
    threshold = BAYER4[(ys + origin[1]) % 4, (xs + origin[0]) % 4]
    return density > threshold, strength


def gray_level_indices(palette):
    """Palette index to use for each tint level 0..13 of a translucent (halo) sprite.

    The engine blends by the sprite pixel's GREY LEVEL (object.cc:3461: ((b + 3r + 6g) / 10) >> 2
    on 6-bit components), not by its colour: level k in 1..7 mixes k/7 of the blend colour into
    what is underneath (color.cc _buildBlendTable).
    """
    six = palette.rgb.astype(np.int32) >> 2
    level = ((six[:, 2] + 3 * six[:, 0] + 6 * six[:, 1]) // 10) >> 2
    chosen = {}
    for wanted in range(1, 14):
        best = None
        for index in RAMPS["grey"]:
            if level[index] == wanted and (best is None or index > best):
                best = index
        if best is None:                    # no pure grey at that level: any static colour will do
            matches = [i for i in range(1, 229) if palette.static[i] and level[i] == wanted]
            best = matches[0] if matches else None
        chosen[wanted] = best
    return chosen


def halo_indices(rgb_linear, alpha, palette, opts, origin=(0, 0)):
    """Light pool render -> indices whose grey levels give a dithered 0..halo_levels tint."""
    levels = gray_level_indices(palette)
    top = int(opts["halo_levels"])
    luma = (rgb_linear * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(axis=-1) * alpha
    value = np.clip(luma, 0.0, 1.0) * top
    h, w = value.shape
    ys, xs = np.indices((h, w))
    threshold = BAYER8[(ys + origin[1]) % 8, (xs + origin[0]) % 8]
    stepped = np.floor(value + threshold).astype(np.int32).clip(0, top)
    out = np.zeros((h, w), np.uint8)
    for level in range(1, top + 1):
        out[stepped == level] = levels[level]
    return out


def apply_fx(indices, rgb_linear, mask, fx_alpha, name):
    """Repaint the pixels covered by an fx mask with the nearest colour of that animated range.
    fx_alpha: coverage (h, w) 0..1 of the tagged objects at sprite resolution."""
    start, colours = FX[name]
    chosen = mask & (fx_alpha >= 0.5)
    if not chosen.any():
        return 0
    table = linear_to_oklab(srgb_to_linear(np.array(colours, np.float32) / 255.0))
    lab = linear_to_oklab(rgb_linear[chosen])
    distance = ((lab[:, None, :] - table[None, :, :]) ** 2).sum(axis=2)
    indices[chosen] = (start + distance.argmin(axis=1)).astype(np.uint8)
    return int(chosen.sum())


# -------------------------------------------------------------------- reports
def ramp_histogram(indices):
    """{ramp or fx name: pixel count} of a converted sprite - a quick check for stray colours."""
    owner = {}
    for name, members in RAMPS.items():
        for index in members:
            owner[index] = name
    for name, (start, colours) in FX.items():
        for offset in range(len(colours)):
            owner[start + offset] = "fx:" + name
    counts = {}
    values, numbers = np.unique(indices[indices > 0], return_counts=True)
    for value, number in zip(values, numbers):
        name = owner.get(int(value), "other")
        counts[name] = counts.get(name, 0) + int(number)
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


def palette_report(palette):
    """Per ramp: number of entries and its lightest / darkest colour."""
    lines = []
    for name, members in RAMPS.items():
        members = [i for i in members if palette.static[i]]
        colours = palette.rgb[members].astype(int)
        luma = colours @ np.array([0.299, 0.587, 0.114])
        lightest = tuple(int(c) for c in colours[luma.argmax()])
        darkest = tuple(int(c) for c in colours[luma.argmin()])
        chroma = (colours.max(axis=1) - colours.min(axis=1)).max()
        lines.append(f"{name:10s} {len(members):2d} entries  lightest {lightest}  darkest {darkest}  "
                     f"strongest colour difference within an entry {int(chroma)}")
    return "\n".join(lines)
