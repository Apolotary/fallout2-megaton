# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Rendered passes of one piece -> palette sprites cut into engine parts (system Python side).

    result = process("build/render/mgt_crate", palette)
    result["parts"]      list of parts, each with pixels, FRM shift, anchor hex, proto flags
    result["blockers"]   footprint hexes that carry no sprite part (need an invisible blocker)
    result["report"]     numbers for the build log (ramps used, reassembly check, reach problems)

A part is one FRM + one proto. Layers:
    main     the piece itself, cut per hex (pipeline/slicer.py)
    shadow   the soft ground shadow as a 1-bit dither, FLAT (painted with the floor, under
             every critter); with shadow="baked" it is merged into the main parts instead
    halo     pool of light on the ground: FLAT + TRANS_ENERGY (tints the floor yellow)
    glow     same blend but not flat: tints whatever was painted before it (the lamp itself,
             the wall behind it); one part on the piece's light hex
"""
import json
import os

import numpy as np

from . import convert, slicer
from . import proj as P

FLAT = 0x08
NO_BLOCK = 0x10
TRANS_NONE = 0x8000
TRANS_ENERGY = 0x80000
LIGHT_THRU = 0x20000000
SHOOT_THRU = 0x80000000
EXT_LOOK = 0x2000
EXT_USE = 0x0800                   # proto "can be used" (proto_instance.cc _proto_action_can_use): spec use=True
EXT_WALL_EW = 0x08000000          # the engine's "wall along a hex row" rule for the see-through egg and for light

MATERIALS = ("glass", "metal", "plastic", "wood", "dirt", "stone", "cement", "leather")
ANIMATE_SCRIPT = "animfrvr"       # stock scripts.lst entry 511: reg_anim_animate_forever(self_obj, ANIM_stand)


def _frame_paths(render_dir, layer, frames):
    paths = []
    for frame in range(frames):
        path = os.path.join(render_dir, f"{layer}_f{frame:03d}.png")
        if not os.path.exists(path):
            if frame == 0:
                raise FileNotFoundError(path)
            break
        paths.append(path)
    return paths


def process(render_dir, palette):
    with open(os.path.join(render_dir, "meta.json")) as f:
        meta = json.load(f)
    spec = meta["spec"]
    name = meta["name"]
    ss = meta["ss"]
    opts = convert.options(spec.get("convert"))
    quantiser = convert.Quantiser(palette, opts)
    canvas = tuple(meta["canvases"]["main"])
    footprint = [tuple(h) for h in meta["footprint"]]
    frame_count = int(spec["frames"])
    report = {"name": name, "warnings": []}

    # ---- main layer: frames -> indices
    frames, mask, alpha0 = [], None, None
    fx_pixels = {}
    for number, path in enumerate(_frame_paths(render_dir, "main", frame_count)):
        indices, mask, rgb, alpha = convert.convert_frame(convert.load_rgba(path), ss, quantiser, opts, mask)
        for fx in meta.get("fx", ()):
            fx_path = os.path.join(render_dir, f"fx_{fx}_f{number:03d}.png")
            if os.path.exists(fx_path):
                _, fx_alpha = convert.downsample(convert.load_rgba(fx_path), ss)
                fx_pixels[fx] = max(fx_pixels.get(fx, 0), convert.apply_fx(indices, rgb, mask, fx_alpha, fx))
        frames.append(indices)
        if alpha0 is None:
            alpha0 = alpha
    xyz, valid = convert.load_positions(os.path.join(render_dir, "pos.png"), meta["position"], ss)
    valid &= mask

    # ---- ground shadow
    shadow = None
    shadow_path = os.path.join(render_dir, "shadow.png")
    if spec["shadow"] != "none" and os.path.exists(shadow_path):
        _, total_alpha = convert.downsample(convert.load_rgba(shadow_path), ss)
        shadow, _ = convert.shadow_mask(total_alpha, alpha0, opts, origin=(canvas[0], canvas[1]))
        shadow &= ~mask
    if shadow is not None and spec["shadow"] == "baked" and shadow.any():
        # shadow pixels join the main sprite; their ground point is the pixel itself
        ys, xs = np.nonzero(shadow)
        gx, gy = xs + canvas[0] + 0.5, ys + canvas[1] + 0.5
        a = (P.SQ_V_PX[1] * gx - P.SQ_V_PX[0] * gy) / P._DET
        b = (P.SQ_U_PX[0] * gy - P.SQ_U_PX[1] * gx) / P._DET
        xyz[ys, xs] = np.stack([a * P.SQ_U_M, b * P.SQ_V_M, np.zeros(len(ys))], axis=1)
        valid[ys, xs] = True
        mask = mask | shadow
        for indices in frames:
            indices[ys, xs] = convert.BLACK
        shadow = None

    # ---- cut the main layer
    owner, hexes, info = slicer.assign(mask, canvas, xyz, valid, footprint, spec["anchors"], spec["overhang"])
    main_parts = slicer.cut(frames, owner, hexes, canvas)
    for index in range(len(frames)):
        if not np.array_equal(slicer.assemble(main_parts, canvas, index), frames[index]):
            raise AssertionError(f"{name}: the cut parts do not reproduce frame {index}")
    report["reassembly"] = "exact"
    report["assign"] = info
    report["warnings"] += slicer.reach_problems(main_parts)
    report["ramps"] = convert.ramp_histogram(frames[0])
    report["fx_pixels"] = fx_pixels
    for fx, count in fx_pixels.items():
        if count == 0:
            report["warnings"].append(f"objects tagged fx={fx!r} cover no whole pixel: make them thicker")
    luma = palette.rgb[frames[0][frames[0] > 0]].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    report["mean_luminance"] = round(float(luma.mean()), 1) if len(luma) else 0.0
    report["luminance_p5_p50_p95"] = [int(round(float(np.percentile(luma, q)))) for q in (5, 50, 95)] if len(luma) else []
    report["size"] = [canvas[2] - canvas[0], canvas[3] - canvas[1]]

    kind = spec["kind"]
    see_through = spec["see_through"]
    sight_through = spec["sight"] == "through"
    light = spec.get("light")
    light_hex = tuple(spec.get("light_hex") or (0, 0))
    material = MATERIALS.index(spec["material"])
    animated = len(frames) > 1
    parts = []
    part_hexes = [part["hex"] for part in main_parts]
    light_owner = None
    if light and part_hexes:
        lx, ly = P.hex_px(*light_hex)
        light_owner = min(part_hexes, key=lambda h: (P.hex_px(*h)[0] - lx) ** 2 + ((P.hex_px(*h)[1] - ly) / P.SIN_E) ** 2)
    for part in main_parts:
        blocking = part["hex"] in footprint
        flags = 0 if blocking else NO_BLOCK
        if sight_through or not blocking:
            flags |= LIGHT_THRU | SHOOT_THRU
        ext = EXT_LOOK | (EXT_USE if spec.get("use") else 0)
        if see_through:
            rule = see_through if see_through in ("u", "v") else slicer.orientation(
                owner, hexes.index(part["hex"]), canvas, xyz, valid)
            if rule == "u":
                ext |= EXT_WALL_EW
        else:
            flags |= TRANS_NONE
        record = dict(part, layer="main", type=kind, flags=flags, flags_ext=ext, material=material,
                      light=[0, 0], script=ANIMATE_SCRIPT if animated else None, fps=spec["fps"], blocking=blocking)
        if light and part["hex"] == light_owner:
            record["light"] = [int(light[0]), int(round(65536 * light[1] / 100.0))]
        parts.append(record)

    # ---- flat shadow layer
    if shadow is not None and shadow.any():
        shadow_frames = [np.where(shadow, convert.BLACK, 0).astype(np.uint8)]
        s_owner, s_hexes = slicer.assign_flat(shadow, canvas)
        for part in slicer.cut(shadow_frames, s_owner, s_hexes, canvas):
            if part["pixels"] < 12:
                continue
            parts.append(dict(part, layer="shadow", type="scenery", flags=FLAT | NO_BLOCK | LIGHT_THRU | SHOOT_THRU | TRANS_NONE,
                              flags_ext=0, material=4, light=[0, 0], script=None, fps=10, blocking=False))
        report["shadow_pixels"] = int(shadow.sum())

    # ---- light layers
    for layer in meta["layers"]:
        if layer == "main":
            continue
        if layer not in ("halo", "glow"):
            report["warnings"].append(f"layer {layer!r} is not known (main, halo, glow): ignored")
            continue
        l_canvas = tuple(meta["canvases"][layer])
        l_frames = []
        for path in _frame_paths(render_dir, layer, frame_count):
            rgb, alpha = convert.downsample(convert.load_rgba(path), ss)
            l_frames.append(convert.halo_indices(rgb, alpha, palette, opts, origin=(l_canvas[0], l_canvas[1])))
        any_pixels = np.zeros(l_frames[0].shape, bool)
        for frame in l_frames:
            any_pixels |= frame > 0
        if not any_pixels.any():
            report["warnings"].append(f"layer {layer!r} is too faint to show (raise its strength)")
            continue
        if layer == "halo":
            l_owner, l_hexes = slicer.assign_flat(any_pixels, l_canvas)
            flags = FLAT | NO_BLOCK | LIGHT_THRU | SHOOT_THRU | TRANS_ENERGY
        else:
            l_owner = np.where(any_pixels, 0, -1).astype(np.int32)
            l_hexes = [light_owner or light_hex]
            flags = NO_BLOCK | LIGHT_THRU | SHOOT_THRU | TRANS_ENERGY
        l_parts = slicer.cut(l_frames, l_owner, l_hexes, l_canvas)
        report["warnings"] += slicer.reach_problems(l_parts)
        for part in l_parts:
            parts.append(dict(part, layer=layer, type="scenery", flags=flags, flags_ext=0, material=0, light=[0, 0],
                              script=ANIMATE_SCRIPT if len(l_frames) > 1 else None, fps=spec["fps"], blocking=False))

    blockers = [list(h) for h in footprint if h not in part_hexes]
    return {"name": name, "spec": spec, "meta": meta, "canvas": canvas, "footprint": [list(h) for h in footprint],
            "parts": parts, "blockers": blockers, "report": report, "frames": frames, "mask": mask}


def part_frm(part):
    """f2lib Frm of one part (single stored direction, all frames the same size)."""
    from f2lib.frm import Frame, Frm
    frm = Frm()
    frm.fps = int(part.get("fps", 10)) if len(part["frames"]) > 1 else 0
    frm.x_offsets = [part["shift"][0]] * 6
    frm.y_offsets = [part["shift"][1]] * 6
    frm.stored = [[Frame(pixels.shape[1], pixels.shape[0], pixels.tobytes()) for pixels in part["frames"]]]
    frm.direction_map = [0] * 6
    return frm


def composite(result, palette, frame=0, background=None, layers=("shadow", "main")):
    """RGBA picture of the assembled piece (for previews): parts painted in engine order."""
    canvas = list(result["canvas"])
    for part in result["parts"]:
        hx, hy = P.hex_px(*part["hex"])
        left, right, up, down = part["reach"]
        canvas = [min(canvas[0], hx - left), min(canvas[1], hy - up), max(canvas[2], hx + right), max(canvas[3], hy + down)]
    width, height = canvas[2] - canvas[0], canvas[3] - canvas[1]
    out = np.zeros((height, width), np.uint8)
    for layer in layers:
        subset = [p for p in result["parts"] if p["layer"] == layer]
        painted = slicer.assemble(subset, canvas, min(frame, max(len(p["frames"]) for p in subset) - 1) if subset else 0)
        np.copyto(out, painted, where=painted > 0)
    return palette.rgba[out], tuple(canvas)
