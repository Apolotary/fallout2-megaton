#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Proof that the Blender camera lands on the game's grid.

    python3 mod/megaton-art/pipeline/calibrate.py            # offline (pixel-exact map renderer)
    python3 mod/megaton-art/pipeline/calibrate.py --engine   # + a screenshot from the real engine

What it does
  1. Blender renders a checkerboard of floor squares, posts one wall height
     (96 px) tall and posts one person (1.80 m = 65 px) tall
     (pipeline/calibrate_scene.py).
  2. A small map is built with the same checkerboard out of two stock floor
     tiles, stock shack walls and villagers on the posts' hexes.
  3. The Blender picture is laid over the game's picture at the position the
     projection predicts - no fitting - and three numbers are measured:
       floor    share of floor pixels where "is this an even square" agrees between
                Blender and the game's own tile painting (the game's tile art overlaps
                its neighbours by 1-2 px, so 100 % is not reachable; a shift of one
                pixel in any direction costs 4-6 %, see the table it prints)
       wall     Blender post top vs. the top of the stock wall on the same hex
       person   Blender post top vs. the top of the stock villager sprite
  Results: build/calib/calibration.json, build/calib/overlay-*.png (4x crops).

    python3 mod/megaton-art/pipeline/calibrate.py --light    # the stock sprites the light rig was read from
  writes build/calib/light-study.png: ten stock sprites at 4x with their luminance numbers and
  what each one says about the original artists' light (summarised in pipeline/bscene.py).
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)

from f2lib import GameFiles, MapFile, geometry as g, ids, mapstxt, write_dat2   # noqa: E402
from render_map import KIND_FLOOR, MapRenderer                                   # noqa: E402
from pipeline import proj as P                                                   # noqa: E402

BLENDER = os.environ.get("BLENDER", "blender")
OUT = os.path.join(ART, "build", "calib")
ORIGIN = g.tile_at(100, 100)
TILE_EVEN, TILE_ODD = "VCRB047.FRM", "holb060.frm"      # bright / dark, same outline
PID_WALL_U_EVEN, PID_WALL_U_ODD = 0x03000082, 0x03000081     # jas1001 / jas1000: wall along a hex row
PID_WALL_V = 0x03000078                                 # jbs1000: wall along a hex column
PID_VILLAGER = 0x01000003


def box_down(rgba, ss):
    h, w = rgba.shape[0] // ss, rgba.shape[1] // ss
    return rgba[:h * ss, :w * ss].reshape(h, ss, w, ss, -1).astype(np.float32).mean(axis=(1, 3))


def run_blender():
    subprocess.run([BLENDER, "-b", "--threads", "4", "--python", os.path.join(HERE, "calibrate_scene.py"), "--", OUT],
                   check=True, stdout=subprocess.DEVNULL)


def square_of_origin():
    """Logical floor square of the origin hex (even hx, even hy)."""
    hx, hy = g.tile_xy(ORIGIN)
    return hx // 2, hy // 2


def build_map(gf, calib):
    m = MapFile.new("mgcalib", gf)
    sqx0, sqy0 = square_of_origin()
    lo, hi = calib["squares"]
    for qy in range(lo - 6, hi + 6):
        for qx in range(lo - 6, hi + 6):
            inside = lo <= qx < hi and lo <= qy < hi
            name = (TILE_EVEN if (qx + qy) % 2 == 0 else TILE_ODD) if inside else "edg5000.frm"
            m.set_floor(sqx0 + qx, sqy0 + qy, name)
    hx0, hy0 = g.tile_xy(ORIGIN)
    walls = []
    for dhx, dhy in calib["wall_posts"]:
        if (dhx, dhy) == (0, 0):
            continue
        if dhy == 0 or (dhx, dhy) == (3, 3):
            pid = PID_WALL_U_ODD if dhx & 1 else PID_WALL_U_EVEN
        else:
            pid = PID_WALL_V
        m.add_object(pid, g.tile_at(hx0 + dhx, hy0 + dhy))
        walls.append((dhx, dhy, pid))
    for dhx, dhy in calib["human_posts"]:
        m.add_object(PID_VILLAGER, g.tile_at(hx0 + dhx, hy0 + dhy), rotation=g.SE)
    m.set_entrance(g.tile_at(hx0 + 1, hy0 + 8), elevation=0, rotation=g.NE)
    return m, walls


def game_parity(gf, calib, world_rect):
    """Per pixel: 1 where the game shows an even square, 0 odd, -1 elsewhere - by the game's own
    painting rule (squares in ascending sqy, sqx; each tile's mask overwrites what is below)."""
    x0, y0, x1, y1 = world_rect
    parity = np.full((y1 - y0, x1 - x0), -1, np.int8)
    mask = gf.art.load(gf.art.fid(ids.OBJ_TYPE_TILE, TILE_EVEN)).frame(0, 0).array() > 0
    sqx0, sqy0 = square_of_origin()
    lo, hi = calib["squares"]
    for qy in range(lo, hi):
        for qx in range(lo, hi):
            wx, wy = g.square_world(g.square_at(sqx0 + qx, sqy0 + qy))
            px, py = wx - x0, wy - y0
            if px < 0 or py < 0 or px + 80 > parity.shape[1] or py + 36 > parity.shape[0]:
                continue
            parity[py:py + 36, px:px + 80][mask] = 1 if (qx + qy) % 2 == 0 else 0
    return parity


def measure(engine=False):
    if not os.path.exists(os.path.join(OUT, "calib.json")) or "--render" in sys.argv:
        run_blender()
    with open(os.path.join(OUT, "calib.json")) as f:
        calib = json.load(f)
    ss = calib["ss"]
    cx0, cy0, cx1, cy1 = calib["canvas"]
    gf = GameFiles()
    ox, oy = g.hex_center(ORIGIN)
    ox, oy = ox + P.ANCHOR_SHIFT[0], oy + P.ANCHOR_SHIFT[1]
    world_rect = (ox + cx0, oy + cy0, ox + cx1, oy + cy1)

    checker = box_down(np.asarray(Image.open(os.path.join(OUT, "checker.png")).convert("RGBA")), ss)
    posts = box_down(np.asarray(Image.open(os.path.join(OUT, "posts.png")).convert("RGBA")), ss)
    m, walls = build_map(gf, calib)
    scene = MapRenderer(gf).render(m, 0, world_rect=world_rect, kinds=True)
    game = scene.rgb()
    floor_pixels = scene.kinds == KIND_FLOOR

    # ---- floor: agreement of square parity, also for the Blender picture shifted by a pixel
    parity = game_parity(gf, calib, world_rect)
    lo, hi = calib["squares"]
    # judge only squares whose four neighbours are part of the board
    interior = np.zeros(parity.shape, bool)
    sqx0, sqy0 = square_of_origin()
    tile_mask = gf.art.load(gf.art.fid(ids.OBJ_TYPE_TILE, TILE_EVEN)).frame(0, 0).array() > 0
    for qy in range(lo + 1, hi - 1):
        for qx in range(lo + 1, hi - 1):
            wx, wy = g.square_world(g.square_at(sqx0 + qx, sqy0 + qy))
            interior[wy - world_rect[1]:wy - world_rect[1] + 36, wx - world_rect[0]:wx - world_rect[0] + 80] |= tile_mask
    ours = checker[:, :, 3] >= 127.5
    table = {}
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            shifted = np.roll(np.roll(ours, dy, axis=0), dx, axis=1)
            agree = (shifted == (parity == 1))[interior]
            table[(dx, dy)] = float(agree.mean())
    floor = {"agreement_unshifted": table[(0, 0)],
             "best_shift": max(table, key=table.get), "best_agreement": max(table.values()),
             "shift_table": {f"{dx},{dy}": round(v, 4) for (dx, dy), v in table.items()}}

    # ---- posts vs. stock walls and villagers
    def post_top(dhx, dhy, channel):
        px, py = P.hex_px(dhx, dhy)
        col = int(px - cx0)
        strip = posts[:, col - 2:col + 2, :]
        rows = np.flatnonzero((strip[:, :, 3] > 127).any(axis=1) & (strip[:, :, channel].max(axis=1) > 80)
                              & (np.arange(posts.shape[0]) <= py - cy0 + 1))
        # keep the run that ends at the hex centre
        rows = rows[rows > py - cy0 - 130]
        # relative to the anchor pixel row of the hex
        return int(rows.min()) + cy0 - py + P.ANCHOR_SHIFT[1], int(rows.max()) + cy0 - py + P.ANCHOR_SHIFT[1]

    def sprite_rows(pid, dhx, dhy, rotation=0):
        proto = gf.protos.get(pid)
        frm = gf.art.load(proto.fid)
        left, top, width, height = frm.placement(rotation, 0)
        pixels = frm.frame(rotation, 0).array()
        return left, top, pixels

    wall_results = []
    for dhx, dhy, pid in walls:
        left, top, pixels = sprite_rows(pid, dhx, dhy)
        # column of the sprite under the hex centre: the wall's top edge there
        column = min(max(-left, 0), pixels.shape[1] - 1)
        opaque = np.flatnonzero(pixels[:, column])
        stock_top = top + int(opaque.min())
        stock_bottom = top + int(opaque.max())
        ours_top, ours_bottom = post_top(dhx, dhy, 2)
        wall_results.append({"hex": [dhx, dhy], "art": gf.art.name(proto_fid(gf, pid)),
                             "stock_top_px": stock_top, "stock_bottom_px": stock_bottom,
                             "post_top_px": ours_top, "post_bottom_px": ours_bottom,
                             "stock_height_px": stock_bottom - stock_top + 1})
    human_results = []
    for dhx, dhy in calib["human_posts"]:
        left, top, pixels = sprite_rows(PID_VILLAGER, dhx, dhy, rotation=g.SE)
        rows = np.flatnonzero(pixels.any(axis=1))
        ours_top, ours_bottom = post_top(dhx, dhy, 1)
        human_results.append({"hex": [dhx, dhy], "stock_top_px": top + int(rows.min()),
                              "stock_bottom_px": top + int(rows.max()),
                              "post_top_px": ours_top, "post_bottom_px": ours_bottom})

    result = {"proj": calib["proj"], "floor": floor, "walls": wall_results, "humans": human_results}

    # ---- pictures
    overlay = game.astype(np.float32)
    edge = np.zeros(ours.shape, bool)
    edge[:-1] |= ours[:-1] != ours[1:]
    edge[:, :-1] |= ours[:, :-1] != ours[:, 1:]
    overlay[edge] = (255, 255, 0)
    alpha = posts[:, :, 3:4] / 255.0 * 0.85
    overlay = overlay * (1 - alpha) + posts[:, :, :3] * alpha
    image = Image.fromarray(overlay.clip(0, 255).astype(np.uint8))
    image.save(os.path.join(OUT, "overlay-full.png"))
    for name, (dhx, dhy) in (("origin", (0, 0)), ("wall-u", (4, 0)), ("wall-v", (0, 4)), ("human", (2, 2))):
        px, py = P.hex_px(dhx, dhy)
        box = (int(px - cx0) - 70, int(py - cy0) - 125, int(px - cx0) + 70, int(py - cy0) + 35)
        crop = image.crop(box).resize((560, 640), Image.NEAREST)
        draw = ImageDraw.Draw(crop)
        draw.text((4, 4), f"{name}: hex ({dhx},{dhy})  yellow = Blender square edges, blue/green = Blender posts", fill=(255, 255, 255))
        crop.save(os.path.join(OUT, f"overlay-{name}.png"))

    if engine:
        result["engine"] = engine_check(gf, m, calib, checker, posts, floor_pixels & interior)
    with open(os.path.join(OUT, "calibration.json"), "w") as f:
        json.dump(result, f, indent=1)
    return result


def proto_fid(gf, pid):
    return gf.protos.get(pid).fid


def engine_check(gf, m, calib, checker, posts, floor_pixels):
    """Run the map in the real engine and compare its screenshot with the offline render + overlay."""
    stage = os.path.join(OUT, "stage")
    os.makedirs(stage, exist_ok=True)
    maps_txt, index = mapstxt.append_map(gf.read("data/maps.txt"), "MG Calibration", "mgcalib",
                                         saved=False, automap=False)
    m.index = index if hasattr(m, "index") else index
    patch = os.path.join(stage, "patch-calib.dat")
    write_dat2({"maps\\mgcalib.map": m.to_bytes(), "data\\maps.txt": maps_txt}, patch)
    width, height = 1280, 960
    view = g.View(ORIGIN, width, height - 100)
    steps = os.path.join(stage, "steps.txt")
    with open(steps, "w") as f:
        f.write(f"center {ORIGIN}\nwait 600\nshot shots/calib.ppm\n")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "f2test.py"), "--name", "art-calib", "--fresh",
                    "--map", "mgcalib.map", "--patch", patch, "--res", f"{width}x{height}", "--steps", steps],
                   check=True, stdout=subprocess.DEVNULL)
    shot = np.asarray(Image.open(os.path.join(ROOT, "run", "art-calib", "shots", "calib.png")).convert("RGB"))
    sx, sy = view.hex_center(ORIGIN)
    sx, sy = sx + P.ANCHOR_SHIFT[0], sy + P.ANCHOR_SHIFT[1]
    cx0, cy0, cx1, cy1 = calib["canvas"]
    x0, y0 = sx + cx0, sy + cy0
    region = shot[max(y0, 0):y0 + checker.shape[0], max(x0, 0):x0 + checker.shape[1]].astype(np.float32)
    ch = checker[max(-y0, 0):max(-y0, 0) + region.shape[0], max(-x0, 0):max(-x0, 0) + region.shape[1]]
    po = posts[max(-y0, 0):max(-y0, 0) + region.shape[0], max(-x0, 0):max(-x0, 0) + region.shape[1]]
    ours = ch[:, :, 3] >= 127.5
    # in the engine the bright tile is the even square: compare by brightness
    bright = region.sum(axis=2) > 300
    dark = region.sum(axis=2) < 120
    # only floor that nothing stands on (walls, villagers and the board's rim are left out),
    # and not the mouse cursor or the player, which the offline picture does not have
    floor = floor_pixels[max(-y0, 0):max(-y0, 0) + region.shape[0], max(-x0, 0):max(-x0, 0) + region.shape[1]]
    judged = (bright | dark) & floor
    agreement = float((ours == bright)[judged].mean())
    edge = np.zeros(ours.shape, bool)
    edge[:-1] |= ours[:-1] != ours[1:]
    edge[:, :-1] |= ours[:, :-1] != ours[:, 1:]
    over = region.copy()
    over[edge] = (255, 255, 0)
    alpha = po[:, :, 3:4] / 255.0 * 0.85
    over = over * (1 - alpha) + po[:, :, :3] * alpha
    Image.fromarray(over.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "overlay-engine.png"))
    px, py = P.hex_px(4, 0)
    centre = (int(px - cx0) - max(-x0, 0), int(py - cy0) - max(-y0, 0))
    Image.fromarray(over.clip(0, 255).astype(np.uint8)).crop(
        (centre[0] - 150, centre[1] - 130, centre[0] + 130, centre[1] + 60)).resize((1120, 760), Image.NEAREST).save(
        os.path.join(OUT, "overlay-engine-4x.png"))
    return {"screenshot": "run/art-calib/shots/calib.png", "floor_agreement": agreement,
            "floor_pixels_judged": int(judged.sum())}


STUDY = [  # (art type, file, what it shows)
    (2, "brl1000.frm", "drum: brightest a third in from the LEFT edge, dark right flank, shadow sliver bottom right"),
    (2, "barrel4.frm", "two drums: same, shadow to the right is short"),
    (2, "box04.frm", "crate: top 1.3-1.4x the sides, bevels catch light, right / bottom outline nearly black"),
    (2, "boxes1.frm", "plank crates: warm brown, highlights 95, crevices 20"),
    (2, "tirs000.frm", "tyres: near black with a grey sheen on top"),
    (2, "car1.frm", "car wreck: dithered (stippled) shadow under and to the right"),
    (2, "watrtank.frm", "tank: left-lit cylinder, rust streaks, dark base"),
    (2, "flamp1.frm", "lamp post: shadow blob to the right of the base"),
    (3, "jas1001.frm", "wall along a hex row (faces screen right-front)"),
    (3, "jbs1000.frm", "wall along a hex column (faces screen left-front): about 8 % brighter"),
]


def light_study():
    """Sheet of the stock sprites the light rig was measured on, 4x, with their luminance numbers."""
    gf = GameFiles()
    zoom = 4
    cells = []
    for art_type, name, note in STUDY:
        frm = gf.art.load(gf.art.fid(art_type, name))
        pixels = frm.frame(0, 0).array()
        rgb = gf.palette.rgb[pixels][pixels > 0].astype(np.float32)
        luma = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        numbers = (f"mean {luma.mean():.0f}  5/50/95 %: {np.percentile(luma, 5):.0f} / {np.percentile(luma, 50):.0f} / "
                   f"{np.percentile(luma, 95):.0f}")
        image = frm.image(gf.palette, 0)
        cells.append((image.resize((image.width * zoom, image.height * zoom), Image.NEAREST), name, numbers, note))
        print(f"{name:13s} {numbers}   {note}")
    width = 1800
    x = y = 10
    row = 0
    places = []
    for image, name, numbers, note in cells:
        cell_width = max(image.width, 330)
        if x + cell_width + 10 > width:
            x, y, row = 10, y + row + 60, 0
        places.append((x, y))
        x += cell_width + 20
        row = max(row, image.height)
    sheet = Image.new("RGB", (width, y + row + 70), (131, 112, 88))
    draw = ImageDraw.Draw(sheet)
    for (image, name, numbers, note), (x, y) in zip(cells, places):
        sheet.paste(image, (x, y), image)
        draw.text((x, y + image.height + 4), f"{name}  {numbers}", fill=(255, 255, 255))
        draw.text((x, y + image.height + 18), note[:60], fill=(230, 230, 200))
        draw.text((x, y + image.height + 32), note[60:], fill=(230, 230, 200))
    os.makedirs(OUT, exist_ok=True)
    sheet.save(os.path.join(OUT, "light-study.png"))
    print("wrote", os.path.relpath(os.path.join(OUT, "light-study.png"), ROOT))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", action="store_true", help="also run the real engine")
    ap.add_argument("--light", action="store_true", help="only write the stock-art light study sheet")
    ap.add_argument("--render", action="store_true", help="re-run Blender even if the renders exist")
    args = ap.parse_args()
    if args.light:
        light_study()
        return
    result = measure(args.engine)
    floor = result["floor"]
    print(f"floor: agreement {floor['agreement_unshifted'] * 100:.2f} % unshifted; best shift {floor['best_shift']} "
          f"-> {floor['best_agreement'] * 100:.2f} %")
    for dy in (-2, -1, 0, 1, 2):
        print("   " + "  ".join(f"{floor['shift_table'][f'{dx},{dy}'] * 100:6.2f}" for dx in (-2, -1, 0, 1, 2)) + f"   dy={dy}")
    for wall in result["walls"]:
        print(f"wall  {wall['art']:12s} hex {wall['hex']}: stock top {wall['stock_top_px']}, bottom {wall['stock_bottom_px']}; "
              f"Blender 96 px post top {wall['post_top_px']}, bottom {wall['post_bottom_px']}")
    for human in result["humans"]:
        print(f"human hex {human['hex']}: stock top {human['stock_top_px']}, bottom {human['stock_bottom_px']}; "
              f"Blender 1.80 m post top {human['post_top_px']}, bottom {human['post_bottom_px']}")
    if "engine" in result:
        print(f"engine: floor agreement {result['engine']['floor_agreement'] * 100:.2f} %  ({result['engine']['screenshot']})")


if __name__ == "__main__":
    main()
