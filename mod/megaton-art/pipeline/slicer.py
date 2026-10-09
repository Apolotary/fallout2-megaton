# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Cut a rendered set piece into engine-correct sprites.

HOW THE ENGINE SORTS (object.cc:761-859, research/04 section 12)
  Non-flat objects are painted hex by hex in ascending tile number (hy * 200 + hx): row after
  row away-to-near, each row from screen right to left. A sprite is sorted by the hex it is
  anchored on and nothing else - not by its size, not by where its pixels are. A critter is one
  such sprite. So a big picture sorts correctly against a walking critter only if every pixel
  belongs to a sprite anchored on the hex that pixel's piece of the world stands on.
  Stock art does exactly this: a shack wall is one 16 px or 32 px strip per hex (jas1000 on odd
  hx, jas1001 on even hx), a wall along a column one 16 px strip per hex (jbs1000 / jbs1002);
  the Den car wall and the tanker are cut the same way.
  Two more rules come from the same loop: an object is only repainted when its hex is within
  320 x 240 px of the dirty rectangle (so a part must not reach further than that from its
  hex: proj.MAX_REACH_*), and a part is lit by the light level of its own hex.

WHAT THIS MODULE DOES
  assign()  gives every opaque pixel an anchor hex, using the world position of the surface
            the pixel shows (the position pass): the nearest blocked hex at or behind the point
            on the ground under it. Pixels hanging further than `overhang` from any blocked hex
            (an awning, a sign over a gateway) get the nearest hex at or in front of that point
            as an extra, non-blocking anchor, so a critter walking beneath is painted before /
            after them as it should. For a thin wall this reproduces the stock vertical strips;
            for a deep structure it gives one column of picture per hex of floor it stands on.
  cut()     crops one sprite per anchor and computes the FRM shift that puts it back in place.
  assemble() repaints the parts with the engine's own placement formula; build.py asserts the
            result equals the uncut picture pixel for pixel.
"""
import numpy as np

from . import proj as P

MIN_PART_PIXELS = 24        # parts with fewer pixels are merged into a neighbour
MIN_PART_WIDTH = 4          # ... and so are parts narrower than this (slivers on a cut line)
FLAT_GRID = 6               # flat layers (shadow, halo) are cut on a lattice of every 6th hex


def hex_px_array(hexes):
    return np.array([P.hex_px(dhx, dhy) for dhx, dhy in hexes], np.float32).reshape(-1, 2)


def ground_px(xyz):
    """World points (n, 3) -> screen px of the ground point under them (n, 2)."""
    a = xyz[:, 0] / P.SQ_U_M
    b = xyz[:, 1] / P.SQ_V_M
    return np.stack([a * P.SQ_U_PX[0] + b * P.SQ_V_PX[0], a * P.SQ_U_PX[1] + b * P.SQ_V_PX[1]], axis=1)


def nearest_of(points_px, hexes):
    """For ground points given as screen px (n, 2): index of the nearest hex and the true
    ground distance to its centre in metres."""
    centres = hex_px_array(hexes)
    best = np.zeros(len(points_px), np.int32)
    best_d = np.full(len(points_px), np.inf, np.float32)
    for start in range(0, len(points_px), 16384):
        chunk = points_px[start:start + 16384]
        dx = chunk[:, None, 0] - centres[None, :, 0]
        dy = (chunk[:, None, 1] - centres[None, :, 1]) / P.SIN_E
        d = dx * dx + dy * dy
        best[start:start + 16384] = d.argmin(axis=1)
        best_d[start:start + 16384] = d.min(axis=1)
    return best, np.sqrt(best_d) / P.PX_PER_M


def own_hex(points_px):
    """Vectorised proj.nearest_hex_px: (n, 2) screen px of ground points -> (n, 2) int (dhx, dhy)."""
    px, py = points_px[:, 0], points_px[:, 1]
    dhx0 = np.rint((12.0 * px - 16.0 * py) / -384.0).astype(np.int32)
    dhy0 = np.rint((-24.0 * py - 6.0 * px) / -384.0).astype(np.int32)
    best = np.full(len(px), np.inf, np.float32)
    out = np.zeros((len(px), 2), np.int32)
    for ddy in range(-2, 3):
        for ddx in range(-2, 3):
            dhx, dhy = dhx0 + ddx, dhy0 + ddy
            a = 1 - dhx
            hx_px = 48 * (a >> 1) + 32 * (a & 1) - 32 + 16 * dhy
            hy_px = -12 * (a >> 1) + 12 * dhy
            d = (hx_px - px) ** 2 + ((hy_px - py) / P.SIN_E) ** 2
            better = d < best
            best[better] = d[better]
            out[better, 0] = dhx[better]
            out[better, 1] = dhy[better]
    return out


def pixel_ground(mask, canvas, xyz=None, valid=None):
    """Screen px of the ground point under every masked pixel -> (ys, xs, points (n, 2)).

    With a position pass the point is the foot of the surface the pixel shows; pixels the pass
    missed (edge pixels) borrow from the nearest pixel that has one. Without a pass (flat
    layers) the pixel is its own ground point.
    """
    ys, xs = np.nonzero(mask)
    if xyz is None:
        return ys, xs, np.stack([xs + canvas[0] + 0.5, ys + canvas[1] + 0.5], axis=1).astype(np.float32)
    usable = valid & mask
    if not usable.any():
        return ys, xs, np.stack([xs + canvas[0] + 0.5, ys + canvas[1] + 0.5], axis=1).astype(np.float32)
    # nearest pixel that has a position (OpenCV labels every pixel with its nearest zero pixel)
    import cv2
    _, labels = cv2.distanceTransformWithLabels((~usable).astype(np.uint8), cv2.DIST_L2, 5,
                                                labelType=cv2.DIST_LABEL_PIXEL)
    uy, ux = np.nonzero(usable)
    lookup = np.zeros((int(labels.max()) + 1, 2), np.int32)
    lookup[labels[uy, ux]] = np.stack([uy, ux], axis=1)
    near = lookup[labels[ys, xs]]
    source = xyz[near[:, 0], near[:, 1]]
    return ys, xs, ground_px(source)


def nearest_constrained(points_px, hexes, side, tolerance=1.5):
    """Like nearest_of, but only hexes on one side of the point count:
    side = "behind": hex centre at or behind the point (further up the screen, <= point y + tolerance)
    side = "front":  hex centre at or in front of it (>= point y - tolerance)
    Points with no hex on that side fall back to the plain nearest."""
    centres = hex_px_array(hexes)
    best = np.zeros(len(points_px), np.int32)
    best_d = np.full(len(points_px), np.inf, np.float32)
    for start in range(0, len(points_px), 16384):
        chunk = points_px[start:start + 16384]
        dx = chunk[:, None, 0] - centres[None, :, 0]
        dy = chunk[:, None, 1] - centres[None, :, 1]            # > 0: the hex is behind the point
        d = dx * dx + (dy / P.SIN_E) ** 2
        allowed = dy >= -tolerance if side == "behind" else dy <= tolerance
        constrained = np.where(allowed, d, np.inf)
        none = ~allowed.any(axis=1)
        constrained[none] = d[none]
        best[start:start + 16384] = constrained.argmin(axis=1)
        best_d[start:start + 16384] = constrained.min(axis=1)
    return best, np.sqrt(best_d) / P.PX_PER_M


def own_hex_in_front(points_px, tolerance=1.5):
    """(n, 2) hexes: for each ground point the nearest hex whose centre is at or in front of it."""
    px, py = points_px[:, 0], points_px[:, 1]
    dhx0 = np.rint((12.0 * px - 16.0 * py) / -384.0).astype(np.int32)
    dhy0 = np.rint((-24.0 * py - 6.0 * px) / -384.0).astype(np.int32)
    best = np.full(len(px), np.inf, np.float32)
    out = np.stack([dhx0, dhy0], axis=1)
    for ddy in range(-2, 3):
        for ddx in range(-2, 3):
            dhx, dhy = dhx0 + ddx, dhy0 + ddy
            a = 1 - dhx
            hx_px = 48 * (a >> 1) + 32 * (a & 1) - 32 + 16 * dhy
            hy_px = -12 * (a >> 1) + 12 * dhy
            d = (hx_px - px) ** 2 + ((hy_px - py) / P.SIN_E) ** 2
            better = (d < best) & (hy_px >= py - tolerance)
            best[better] = d[better]
            out[better, 0] = dhx[better]
            out[better, 1] = dhy[better]
    return out


def assign(mask, canvas, xyz, valid, footprint, anchors="auto", overhang=1.0, min_pixels=MIN_PART_PIXELS):
    """-> (owner (h, w) int32: index into the returned hex list or -1, hexes [(dhx, dhy)], info).

    footprint  the hexes the piece blocks [(dhx, dhy)]
    anchors    "auto", or an explicit list of hexes to cut on (every pixel goes to the nearest)

    auto, for a pixel showing a surface whose foot is the ground point G:
      1. it goes to the nearest BLOCKED hex whose centre is at or behind G. Nobody can ever stand
         on that hex, everybody in front of the surface stands on a later hex and is painted
         after it, everybody behind it on an earlier one. This is the stock wall scheme: a wall
         along a hex row is cut into strips on that row's hexes, and the half-offset hexes in
         front of it are blocked but carry no picture.
      2. if no blocked hex is within `overhang` metres (an awning, a sign over a gateway), it
         goes to the nearest hex at or IN FRONT of G instead, as a part that does not block:
         someone standing under it is painted after it, someone further back before it.
      3. anchors that end up with fewer than `min_pixels` pixels, or with a sliver under
         MIN_PART_WIDTH px wide, are dissolved into their neighbours.
    """
    footprint = [tuple(h) for h in footprint]
    owner = np.full(mask.shape, -1, np.int32)
    ys, xs, points = pixel_ground(mask, canvas, xyz, valid)
    info = {"pixels": int(len(ys)), "overhang_parts": 0, "dissolved_parts": 0}
    if not len(ys):
        return owner, [], info
    if anchors != "auto":
        hexes = [tuple(h) for h in anchors]
        index, _ = nearest_of(points, hexes)
    else:
        hexes = list(footprint)
        if hexes:
            index, distance = nearest_constrained(points, hexes, "behind")
            far = distance > overhang
        else:
            index = np.zeros(len(ys), np.int32)
            far = np.ones(len(ys), bool)
        if far.any():
            own = own_hex_in_front(points[far])
            keys, inverse = np.unique(own, axis=0, return_inverse=True)
            inverse = inverse.reshape(-1)
            lookup = np.zeros(len(keys), np.int32)
            for k, key in enumerate(keys):
                key = (int(key[0]), int(key[1]))
                if key not in hexes:
                    hexes.append(key)
                    info["overhang_parts"] += 1
                lookup[k] = hexes.index(key)
            index = index.copy()
            index[far] = lookup[inverse]
        # dissolve anchors that got next to nothing or only a sliver (never the last one)
        while True:
            counts = np.bincount(index, minlength=len(hexes))
            used = np.flatnonzero(counts)
            if len(used) == 1:
                break
            widths = {int(k): int(xs[index == k].max() - xs[index == k].min() + 1) for k in used}
            small = [int(k) for k in used if counts[k] < min_pixels or widths[int(k)] < MIN_PART_WIDTH]
            if not small:
                break
            victim = min(small, key=lambda k: counts[k])
            keep = [int(k) for k in used if k != victim]
            moved = index == victim
            nearest, _ = nearest_of(points[moved], [hexes[k] for k in keep])
            index[moved] = np.array(keep, np.int32)[nearest]
            info["dissolved_parts"] += 1
    used = sorted(set(int(i) for i in np.unique(index)))
    remap = np.full(max(used) + 1, -1, np.int32)
    remap[used] = np.arange(len(used), dtype=np.int32)
    owner[ys, xs] = remap[index]
    hexes = [hexes[i] for i in used]
    info["overhang_parts"] = sum(1 for h in hexes if h not in footprint)
    return owner, hexes, info


def assign_flat(mask, canvas, grid=FLAT_GRID):
    """Owner map for a flat layer (shadow, halo). Flat sprites are all painted before anything
    that stands, so the cut does not matter for sorting - only the engine's repaint reach does.
    One part on the (even, even) hex nearest to the layer's middle if everything is within
    reach of it; otherwise the pixel's own hex snapped to a lattice of every `grid`-th hex."""
    owner = np.full(mask.shape, -1, np.int32)
    ys, xs, points = pixel_ground(mask, canvas)
    if not len(ys):
        return owner, []
    middle = np.array([[(points[:, 0].min() + points[:, 0].max()) / 2.0, (points[:, 1].min() + points[:, 1].max()) / 2.0]],
                      np.float32)
    centre = own_hex(middle)[0]
    centre = (int(round(centre[0] / 2.0)) * 2, int(round(centre[1] / 2.0)) * 2)
    cx, cy = P.hex_px(*centre)
    reach_x = max(points[:, 0].max() - cx, cx - points[:, 0].min())
    reach_y = max(points[:, 1].max() - cy, cy - points[:, 1].min())
    if reach_x <= P.MAX_REACH_X * 0.8 and reach_y <= P.MAX_REACH_DOWN * 0.8:
        owner[ys, xs] = 0
        return owner, [centre]
    own = own_hex(points)
    snapped = (np.rint(own / float(grid)) * grid).astype(np.int32)
    keys, inverse = np.unique(snapped, axis=0, return_inverse=True)
    owner[ys, xs] = inverse.reshape(-1)
    return owner, [(int(k[0]), int(k[1])) for k in keys]


def cut(frames, owner, hexes, canvas):
    """Crop one part per anchor hex.

    frames  list of (h, w) uint8 index images of one layer (same canvas)
    -> list of parts: {"hex": (dhx, dhy), "shift": (x, y), "size": (w, h), "frames": [arrays],
                       "reach": (left, right, up, down) px from the hex centre}
    The crop box is the union over all frames, so every frame of a part has the same size.
    """
    parts = []
    any_frame = np.zeros(owner.shape, bool)
    for frame in frames:
        any_frame |= frame > 0
    for k, (dhx, dhy) in enumerate(hexes):
        selected = (owner == k) & any_frame
        if not selected.any():
            continue
        ys, xs = np.nonzero(selected)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        hx_px, hy_px = P.hex_px(dhx, dhy)
        rel_left = canvas[0] + x0 - hx_px
        rel_bottom = canvas[1] + y1 - 1 - hy_px
        width, height = x1 - x0, y1 - y0
        cropped = []
        for frame in frames:
            piece = np.where(owner[y0:y1, x0:x1] == k, frame[y0:y1, x0:x1], 0).astype(np.uint8)
            cropped.append(piece)
        parts.append({
            "hex": (dhx, dhy),
            "shift": (int(rel_left + width // 2 + P.ANCHOR_SHIFT[0]), int(rel_bottom + P.ANCHOR_SHIFT[1])),
            "size": (width, height),
            "frames": cropped,
            "reach": (int(-rel_left), int(rel_left + width), int(-(rel_bottom - height + 1)), int(rel_bottom + 1)),
            "pixels": int(selected.sum()),
        })
    parts.sort(key=lambda part: P.tile_order_key(*part["hex"]))
    return parts


def reach_problems(parts):
    """Parts that stick out further from their hex than the engine repaints reliably."""
    problems = []
    for part in parts:
        left, right, up, down = part["reach"]
        if left > P.MAX_REACH_X or right > P.MAX_REACH_X or up > P.MAX_REACH_UP or down > P.MAX_REACH_DOWN:
            problems.append(f"part on hex {part['hex']} reaches {left} px left, {right} right, {up} up, {down} down "
                            f"of its hex (limits {P.MAX_REACH_X} / {P.MAX_REACH_X} / {P.MAX_REACH_UP} / {P.MAX_REACH_DOWN})")
    return problems


def assemble(parts, canvas, frame=0):
    """Repaint parts the way the engine places sprites (object.cc:4881-4923) -> (h, w) uint8."""
    width, height = canvas[2] - canvas[0], canvas[3] - canvas[1]
    out = np.zeros((height, width), np.uint8)
    for part in parts:                                   # already in engine paint order
        pixels = part["frames"][frame]
        h, w = pixels.shape
        hx_px, hy_px = P.hex_px(*part["hex"])
        anchor_x = hx_px + part["shift"][0]              # relative to the origin hex's anchor pixel
        anchor_y = hy_px + part["shift"][1]
        left = anchor_x - w // 2 - P.ANCHOR_SHIFT[0] - canvas[0]
        top = anchor_y - (h - 1) - P.ANCHOR_SHIFT[1] - canvas[1]
        target = out[top:top + h, left:left + w]
        np.copyto(target, pixels, where=pixels > 0)
    return out


def orientation(owner, k, canvas, xyz, valid):
    """'u' or 'v': the ground direction a part mostly runs along (for the see-through rule)."""
    selected = (owner == k) & valid
    if selected.sum() < 8:
        return "u"
    points = xyz[selected]
    spread_x = float(points[:, 0].std())
    spread_y = float(points[:, 1].std())
    return "u" if spread_x >= spread_y else "v"
