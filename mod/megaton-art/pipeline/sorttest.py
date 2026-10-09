# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Draw-order test: a critter on EVERY free hex round every piece, checked pixel by pixel.

    python3 mod/megaton-art/build.py sort [NAME ...]     -> a table, and build/preview/sort-NAME.png for
                                                           every piece that fails

The engine paints a sprite before or after a critter by tile number alone (pipeline/slicer.py).
Whether that is RIGHT for a pixel is geometry: under the game's camera two things that share a
screen pixel are ordered by the screen height of the ground points under them - the lower foot
is nearer. The position pass gives the foot of the surface every pixel shows; a standing critter's
foot is the centre of his hex. So for a critter on hex H and a part anchored on hex A:

    the engine paints the critter over the part   iff  tile(H) >= tile(A)
    the critter really is in front of a pixel     iff  foot_y(H) > foot_y(pixel)

and every pixel of the part inside the critter's silhouette where the two disagree is a pixel
drawn wrongly. Two kinds, counted apart:
    OVER    the piece is painted over a critter who stands in front of it (the bad one: he vanishes)
    UNDER   the critter is painted over something that stands in front of him
A band of +-`TOLERANCE` px of foot height is not counted: at equal depth either order is right.
The silhouette is a standing human: 26 px wide, 64 px tall, feet on the hex centre.

This tests each piece alone, on every hex its footprint leaves free - far more positions than a
walk in the engine can visit. The walk (stage/town/walk.py) then shows the same thing in the game.
"""
import json
import os

import numpy as np

from . import convert, piece as piece_module, slicer
from . import proj as P

# Hexes nobody can stand on although the piece's own footprint leaves them free: the leaves of the gate
# stand in the passage, which the town's door object blocks while they are not fully open.
ASSUME_BLOCKED = {name: [(-1, 1), (0, 1), (1, 1)] for name in ("mg_gate_shut", "mg_gate_ajar", "mg_gate_door",
                                                              "mg_gate_f25", "mg_gate_f75")}
# Things that lie on the ground and are walked on: a critter standing on them is always painted over them,
# which is right, although the feet-on-the-ground comparison calls the plank's near edge "in front".
WALKED_ON = ("mgb_step_u", "mgb_step_v", "mgb_boards_u", "mgb_boards_v", "mgb_mat",
             "gr_pipe_ramp_u", "gr_pipe_ramp_v")      # the plank ramps over a pipe: people cross on them

TOLERANCE = 3.0             # px of foot height treated as "same depth"
BODY_W, BODY_H = 26, 64
FAIL_PIXELS = 64            # a hex with more wrongly ordered pixels than this fails the piece: 4 % of a standing
                            # figure, a hand's width where he brushes an edge. Stock props do no better.


def _silhouette():
    """Boolean (BODY_H, BODY_W): a capsule, narrower at head and feet."""
    ys, xs = np.mgrid[0:BODY_H, 0:BODY_W]
    half = np.where(ys < 12, 6.0, np.where(ys < 40, 12.0, 8.0))
    return np.abs(xs - (BODY_W - 1) / 2.0) <= half


def check(render_dir, palette):
    """-> dict(name, worst_over, worst_under, over_hex, under_hex, hexes, picture inputs)."""
    result = piece_module.process(render_dir, palette)
    with open(os.path.join(render_dir, "meta.json")) as f:
        meta = json.load(f)
    canvas = result["canvas"]
    mask = result["mask"]
    xyz, valid = convert.load_positions(os.path.join(render_dir, "pos.png"), meta["position"], meta["ss"])
    valid &= mask
    ys, xs, points = slicer.pixel_ground(mask, canvas, xyz, valid)
    foot = np.full(mask.shape, np.nan, np.float32)
    foot[ys, xs] = points[:, 1]
    main = [part for part in result["parts"] if part["layer"] == "main"]
    owner = np.full(mask.shape, -1, np.int32)
    for k, part in enumerate(main):
        pixels = part["frames"][0]
        h, w = pixels.shape
        hx_px, hy_px = P.hex_px(*part["hex"])
        left = hx_px + part["shift"][0] - w // 2 - P.ANCHOR_SHIFT[0] - canvas[0]
        top = hy_px + part["shift"][1] - (h - 1) - P.ANCHOR_SHIFT[1] - canvas[1]
        any_frame = np.zeros(pixels.shape, bool)
        for frame in part["frames"]:
            any_frame |= frame > 0
        owner[top:top + h, left:left + w][any_frame] = k
    order = np.array([P.tile_order_key(*part["hex"]) for part in main], np.int64)
    blocked = {tuple(h) for h in result["footprint"]} | set(ASSUME_BLOCKED.get(result["name"], ()))
    lying = result["name"] in WALKED_ON
    failing = {"over": [], "under": []}
    body = _silhouette()
    # every hex whose critter could touch the sprite
    corners = [P.nearest_hex_px(canvas[0] - BODY_W, canvas[1] - 4), P.nearest_hex_px(canvas[2] + BODY_W, canvas[1] - 4),
               P.nearest_hex_px(canvas[0] - BODY_W, canvas[3] + BODY_H + 4), P.nearest_hex_px(canvas[2] + BODY_W, canvas[3] + BODY_H + 4)]
    lo_x, hi_x = min(c[0] for c in corners) - 1, max(c[0] for c in corners) + 1
    lo_y, hi_y = min(c[1] for c in corners) - 1, max(c[1] for c in corners) + 1
    worst = {"over": (0, None), "under": (0, None)}
    wrong_over = np.zeros(mask.shape, np.int32)
    wrong_under = np.zeros(mask.shape, np.int32)
    tested = 0
    for dhy in range(lo_y, hi_y + 1):
        for dhx in range(lo_x, hi_x + 1):
            if (dhx, dhy) in blocked:
                continue
            cx, cy = P.hex_px(dhx, dhy)
            x0, y0 = int(cx - BODY_W // 2 - canvas[0]), int(cy + 2 - BODY_H - canvas[1])
            ax0, ay0 = max(x0, 0), max(y0, 0)
            ax1, ay1 = min(x0 + BODY_W, mask.shape[1]), min(y0 + BODY_H, mask.shape[0])
            if ax0 >= ax1 or ay0 >= ay1:
                continue
            window = (slice(ay0, ay1), slice(ax0, ax1))
            inside = body[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] & (owner[window] >= 0)
            if not inside.any():
                continue
            tested += 1
            critter_after = P.tile_order_key(dhx, dhy) >= order[np.maximum(owner[window], 0)]
            in_front = cy > foot[window] + TOLERANCE
            behind = cy < foot[window] - TOLERANCE
            over = inside & ~critter_after & in_front
            under = inside & critter_after & behind & (not lying)
            for key, wrong, store in (("over", over, wrong_over), ("under", under, wrong_under)):
                count = int(wrong.sum())
                if count > FAIL_PIXELS:
                    failing[key].append(((dhx, dhy), count))
                if count:
                    store[window][wrong] += 1
                if count > worst[key][0]:
                    worst[key] = (count, (dhx, dhy))
    return {"name": result["name"], "over": worst["over"][0], "over_hex": worst["over"][1],
            "under": worst["under"][0], "under_hex": worst["under"][1], "hexes": tested, "parts": len(main),
            "failing": failing,
            "_picture": (result, wrong_over, wrong_under)}


def picture(report, palette, path, zoom=2):
    """The piece with its wrongly ordered pixels marked: red = painted over somebody in front,
    blue = somebody behind painted over it; the worst hexes get a ring."""
    from PIL import Image, ImageDraw
    result, wrong_over, wrong_under = report["_picture"]
    canvas = result["canvas"]
    main = [part for part in result["parts"] if part["layer"] == "main"]
    indices = slicer.assemble(main, canvas)
    rgb = palette.rgb[indices].astype(np.float32)
    rgb[indices == 0] = (131, 112, 88)
    rgb[wrong_over > 0] = rgb[wrong_over > 0] * 0.3 + np.array([255, 30, 30], np.float32) * 0.7
    rgb[(wrong_under > 0) & (wrong_over == 0)] = rgb[(wrong_under > 0) & (wrong_over == 0)] * 0.3 + np.array([40, 90, 255], np.float32) * 0.7
    image = Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).resize((indices.shape[1] * zoom, indices.shape[0] * zoom), Image.NEAREST)
    draw = ImageDraw.Draw(image)
    for part in main:
        px, py = P.hex_px(*part["hex"])
        x, y = (px - canvas[0]) * zoom, (py - canvas[1]) * zoom
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 255, 255))
    for key, colour in (("over_hex", (255, 0, 0)), ("under_hex", (0, 80, 255))):
        if report[key]:
            px, py = P.hex_px(*report[key])
            x, y = (px - canvas[0]) * zoom, (py - canvas[1]) * zoom
            draw.ellipse((x - 9, y - 6, x + 9, y + 6), outline=colour, width=2)
    image.save(path)


def run(names, render_root, palette, out_dir):
    rows = []
    os.makedirs(out_dir, exist_ok=True)
    for name in names:
        render_dir = os.path.join(render_root, name)
        if not os.path.exists(os.path.join(render_dir, "pos.png")):
            rows.append({"name": name, "missing": True})
            continue
        report = check(render_dir, palette)
        report["fails"] = report["over"] > FAIL_PIXELS or report["under"] > FAIL_PIXELS
        if report["fails"]:
            picture(report, palette, os.path.join(out_dir, f"sort-{name}.png"))
        report.pop("_picture")
        rows.append(report)
    return rows
