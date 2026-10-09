#!/usr/bin/env python3
"""Regenerate the shanty-town asset survey in this directory.

    python3 mod/reference/build_survey.py            # everything (about 20 s)
    python3 mod/reference/build_survey.py prefabs    # only one part: sheets, maps, regions, prefabs

Output: contact sheets of protos (sheets/), overview renders of six retail
maps (maps/), full-size crops of the most reusable spots (regions/), ready
made prefabs with previews (prefabs/) and index.txt, which lists every file.
Everything is derived from the retail data with tools/contact_sheet.py,
tools/render_map.py and tools/map_kit.py; edit the tables below and re-run.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from f2lib import GameFiles, MapFile, geometry as g, ids  # noqa: E402
import contact_sheet  # noqa: E402
import map_kit  # noqa: E402
from render_map import MapRenderer, Overlay, save_png  # noqa: E402

T = contact_sheet.TYPES

# (file prefix, type, name regex, options, what it shows)
SHEETS = [
    ("walls-shack-tin-wood", "walls", r"^(jc|jd|jb|ja|cn|cor)", {"zoom": 2},
     "tin / wooden shack walls, the 'junktown' kit: straight pieces, corners, doorways, windows"),
    ("walls-corrugated-warehouse", "walls", r"^(ware|scwall)", {"zoom": 2},
     "dark red corrugated warehouse walls: 4 corners, NS / EW runs, doorways (Klamath, New Reno)"),
    ("walls-car-wrecks", "walls", r"^(carw|cargt|poptr)", {},
     "walls made of stacked car wrecks (The Den) and the rusty truck: 16 px slices of big pictures, "
     "only usable in their original arrangement - take them as prefabs"),
    ("walls-fences-gates", "walls", r"^(fence|tfenc|fen\d|fnc|fns|vgat)", {"zoom": 2},
     "chain-link fences, wooden fences (brahmin pens) and the Vault City gate arch (vgat)"),
    ("walls-tents-tank", "walls", r"^(ybk|ylf|yrt|yar|btnk)", {"zoom": 2},
     "canvas tent (ybk back / ylf left / yrt right), Arroyo hide tent (yar), round water tank (btnk)"),
    ("scenery-junk", "scenery", r"junk|stuff|tire|trash|rubble|crate|boxes|\bcart\b|pile of|debris", {},
     "junk heaps, tires, trash, crates, rubble"),
    ("scenery-cars-barrels", "scenery", r"\b(car|truck|barrels?)\b|^shorcar|^carspec", {},
     "wrecked cars, trucks, barrels (0x02000001 is the burning barrel)"),
    ("scenery-signs", "scenery", r"sign|poster|bulletin|billboard", {},
     "every sign: Sheriff 0200058C, Clinic 0200067D, Doc Johnson 0200058B, saloons 0200058D / 020006CB / "
     "020004F2, stores, wanted poster ..."),
    ("scenery-bomb-pools-water", "scenery",
     r"^(abomb|slimpol|goop|slimeis|water0|cavwater|polewatr|watrtank|pumpnec|well)|warhead", {},
     "the Bomb (02000300) and its Support Base (02000301), slime pools, radioactive goo, water, wells, "
     "pump, water tank; 'Nuclear Warhead' 020001C1 only has the placeholder art reserved.frm"),
    ("scenery-goo", "scenery", r"^mstr", {}, "flat green 'Goo' puddles and streaks (mstr01..)"),
    ("scenery-gates-doors", "scenery", r"gate|guard shack|door", {},
     "gates and every door; the door sub-type is in the flag line"),
    ("scenery-lights-fires", "scenery", r"lamp|light|fire|torch|brazier|campfire|stove", {},
     "lamp posts, lights, fires"),
    ("critters-brahmin-ghoul-robot", "critters", r"brahmin|ghoul|glow|robo|\bbot\b|handy|turret",
     {"unique_art": True, "directions": True},
     "brahmin, ghouls, glowing ones, robots: one row per art, all six directions"),
    ("tiles-desert-dirt", "tiles", r"^(edg|edgs|foot|gar|grass)", {"zoom": 2},
     "desert ground (edg5000..5007 is the plain filler of every map here), dirt edges, footpaths, garden, grass"),
    ("tiles-shack-floors-metal", "tiles", r"^(cmt|capb|brn|crbm|plt|rst|stlflr|grt|mstrflr|shipflr)", {"zoom": 2},
     "floors inside the shacks (cmt, capb, brn, crbm wood) and metal: plates (plt, rst), steel floor, grates"),
    ("tiles-slime", "tiles", r"^slime", {"zoom": 2},
     "green slime pond floor tiles with banks (28 pieces; animated palette, they pulse in the game)"),
    ("tiles-roofs", "tiles", r"^(plk|ruf|jrt|wroof|crtp|yrf|arrf|tp)", {},
     "shack roofs: plk sheets, ruf corrugated strips and edges, jrt trim (every Gecko / Vault City / Modoc "
     "shack); wroof warehouse; crtp tarps; yrf canvas tent; arrf Arroyo tent; tp rusted roofs and floors of "
     "Klamath and The Den"),
]

# Retail maps with the best shanty-town material: (map, what is on it)
MAPS = [
    ("denbus1", "The Den, east side: Smitty's junkyard walled with car wrecks, wooden shack, chain-link fences"),
    ("geckjunk", "Gecko junkyard: rows of tin / wood shacks, brahmin pens, garage, car wrecks, reactor ruin"),
    ("gecksetl", "Gecko settlement: free-standing shacks, bar, brahmin pen, garden plots"),
    ("vctyctyd", "Vault City courtyard: shacks, canvas tents, brahmin pen, fenced perimeter with turrets and the gate"),
    ("klamall", "Klamath, Trapper Town: corrugated shack, warehouses, car wrecks, fences"),
    ("modmain", "Modoc: scattered shacks, brahmin pen, round water tank, outhouse"),
]

# Full-size crops: (file, map, elevation, centre tile, radius, what to look at)
REGIONS = [
    ("den-junkyard", "denbus1", 0, g.tile_at(150, 114), 17, "car-wreck walls, wrecks and the shack of Smitty's yard"),
    ("gecko-junkyard-shacks", "geckjunk", 0, g.tile_at(92, 112), 17, "shack row and pens"),
    ("gecko-settlement-shacks", "gecksetl", 0, g.tile_at(104, 92), 17, "shacks around the square"),
    ("vaultcity-gate", "vctyctyd", 0, g.tile_at(106, 133), 11, "gate arch, perimeter fence, turrets"),
    ("vaultcity-tents", "vctyctyd", 0, g.tile_at(94, 92), 11, "canvas tent and shacks"),
    ("klamath-shack", "klamall", 0, g.tile_at(142, 110), 12, "corrugated shack next to the warehouse"),
    ("modoc-water-tank", "modmain", 0, g.tile_at(134, 84), 9, "round water tank"),
    ("enclave-bomb", "encpres", 0, g.tile_at(122, 74), 6, "the only 'Bomb' scenery in the game, on its support base"),
    ("klamath-slime-pools", "klatoxcv", 1, g.tile_at(105, 107), 11, "slime pool scenery in the toxic caves"),
    ("toxic-dump-ponds", "rndtoxic", 0, g.tile_at(112, 100), 17,
     "ponds made of the slime floor tiles (the only map using them) ringed with waste barrels"),
]

# Prefabs: (name, map, elevation, corner (hx, hy), opposite corner (hx, hy), what it is)
PREFABS = [
    ("gate-vaultcity", "vctyctyd", 0, (97, 133), (114, 137), "gate arch with the fence posts beside it"),
    ("tent-canvas", "vctyctyd", 0, (89, 89), (98, 100), "canvas tent with its furniture"),
    ("tent-arroyo", "arvillag", 0, (96, 95), (104, 104), "hide tent"),
    ("watertank-modoc", "modmain", 0, (130, 80), (138, 86), "round water tank"),
    ("bomb-enclave", "encpres", 0, (120, 71), (124, 76), "bomb on its support base"),
    ("shack-klamath", "klamall", 0, (134, 100), (153, 124), "corrugated two-room shack"),
    ("shack-den", "denbus1", 0, (133, 106), (143, 116), "small wooden shack"),
    ("shack-gecko-a", "gecksetl", 0, (117, 100), (131, 118), "tin / wood shack"),
    ("shack-gecko-b", "geckjunk", 0, (57, 106), (71, 118), "tin / wood shack"),
    ("shed-gecko", "gecksetl", 0, (121, 84), (127, 90), "one-room shed"),
    ("carwall-den-a", "denbus1", 0, (132, 83), (140, 106), "car-wreck wall, north-south run"),
    ("carwall-den-b", "denbus1", 0, (143, 135), (168, 139), "car-wreck wall, east-west run"),
    ("carwall-denres", "denres1", 0, (41, 62), (74, 86), "long car-wreck wall with a corner"),
    ("warehouse-klamath", "klamall", 0, (135, 78), (151, 98), "corrugated warehouse"),
    ("slimepool-klamath", "klatoxcv", 1, (100, 103), (110, 111), "slime pool scenery between cave walls"),
    ("slimepond-toxic", "rndtoxic", 0, (100, 82), (125, 101), "pond of slime floor tiles ringed with waste barrels"),
]

MAP_USAGE_TOP = 18

FOOTER = """
GOING ON FROM HERE (run from the project root)

  another crop, with hex grid and blocked hexes:
      python3 tools/render_map.py geckjunk --crop 22492 10 --grid --blockers --tile-numbers 2 -o crop.png
  where a proto from a sheet stands on the retail maps / what a map is made of:
      python3 tools/map_kit.py where 0x02000300
      python3 tools/map_kit.py usage gecksetl --type walls --top 40
  outline a proto on a map picture:
      python3 tools/render_map.py vctyctyd --mark 0300050B --fit 1500 -o marked.png
  cut another prefab (two opposite corner tiles of the hex box) and look at it:
      python3 tools/map_kit.py extract gecksetl 14298 18316 -o bar.json --show bar-src.png
      python3 tools/map_kit.py preview bar.json --roofs -o bar.png
  more sheets:
      python3 tools/contact_sheet.py walls --used-in gecksetl --zoom 2 -o gecko-walls
Other maps worth a look: newrcs (New Reno chop shop: a field of car wrecks), denres1 (more car-wreck walls),
kladwtwn, redment, broken1 (brahmin pens, water tank), rndtoxic (slime ponds), arvillag (hide tents).
"""


def build_sheets(gf, out, index):
    os.makedirs(out, exist_ok=True)
    index.append("\nCONTACT SHEETS (sheets/)  -  cell: PID or tile id, art file and size, proto name, flags;")
    index.append("the same rows as text in sheets/<name>.txt\n")
    for prefix, kind, pattern, options, text in SHEETS:
        options = dict(options)
        entries = contact_sheet.collect(gf, T[kind], name=pattern, unique_art=options.pop("unique_art", False))
        files = contact_sheet.make_sheets(gf, entries, os.path.join(out, prefix),
                                          f"{kind}  /{pattern}/  ({len(entries)} entries)  -  {text}", **options)
        pages = f"-01..{len(files):02d}.png" if len(files) > 1 else "-01.png"
        index.append(f"  sheets/{prefix}{pages}  {len(entries)} {kind}: {text}")


def build_maps(gf, out, index):
    os.makedirs(out, exist_ok=True)
    renderer = MapRenderer(gf)
    index.append("\nMAP OVERVIEWS (maps/)  -  the area holding objects, scaled to 1540 px, tile number every 10 hexes;")
    index.append("<map>.png without roofs (wall layout), <map>-roofs.png as the game shows it\n")
    usage = []
    for name, text in MAPS:
        game_map = MapFile.load(name, gf)
        for roofs in (False, True):
            scene = renderer.render(game_map, 0, roofs=roofs)
            path = os.path.join(out, f"{name}{'-roofs' if roofs else ''}.png")
            save_png(Overlay(scene, min(1.0, 1540 / max(scene.size))).tile_numbers(10).image, path, colours=256)
        index.append(f"  maps/{name}.png, maps/{name}-roofs.png  {text}")
        usage.append(f"{name}: {text}")
        for obj_type in (ids.OBJ_TYPE_WALL, ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_TILE):
            rows = map_kit.proto_usage(gf, [game_map], obj_type)
            usage.append(f"  most used {('tiles (F floor, R roof)' if obj_type == ids.OBJ_TYPE_TILE else contact_sheet_name(obj_type))}:")
            for count, key, art, proto_name, info in rows[:MAP_USAGE_TOP]:
                shown = f"tile {key:<5}" if obj_type == ids.OBJ_TYPE_TILE else f"{key:08X}"
                usage.append(f"    {map_kit._count(count):>9}  {shown}  {art:<13} {proto_name:<24} {info}")
        usage.append("")
    with open(os.path.join(out, "usage.txt"), "w") as f:
        f.write("\n".join(usage))
    index.append("  maps/usage.txt  the most used wall / scenery protos and tile ids of each of these maps")


def contact_sheet_name(obj_type):
    return next(label for label, value in T.items() if value == obj_type)


def build_regions(gf, out, index):
    os.makedirs(out, exist_ok=True)
    renderer = MapRenderer(gf)
    index.append("\nREGIONS (regions/)  -  full-size crops, tile number every 5 hexes; <name>.png without roofs,")
    index.append("<name>-roofs.png with; reproduce or move with: render_map.py MAP -e ELEV --crop TILE RADIUS\n")
    for name, map_name, elevation, center, radius, text in REGIONS:
        game_map = MapFile.load(map_name, gf)
        for roofs in (False, True):
            scene = renderer.render(game_map, elevation, roofs=roofs, crop=(center, radius))
            save_png(Overlay(scene).tile_numbers(5).image, os.path.join(out, f"{name}{'-roofs' if roofs else ''}.png"), colours=256)
        index.append(f"  regions/{name}.png  {map_name} e{elevation} --crop {center} {radius}: {text}")


def build_prefabs(gf, out, index):
    os.makedirs(out, exist_ok=True)
    index.append("\nPREFABS (prefabs/)  -  cut with map_kit.py, stamp with map_kit.Prefab.load(path).stamp(map, at=tile)")
    index.append("(tile with even hx and hy); no critters, scripts not attached; prefabs/overview-NN.png shows them\n")
    prefabs = []
    for name, map_name, elevation, low, high, text in PREFABS:
        prefab = map_kit.Prefab.extract(MapFile.load(map_name, gf), g.tile_at(*low), g.tile_at(*high), elevation,
                                        critters="none", name=name)
        prefab.save(os.path.join(out, name + ".json"))
        prefabs.append(prefab)
        index.append(f"  prefabs/{name}.json  {prefab.size[0]}x{prefab.size[1]} hexes, {len(prefab.objects)} objects, "
                     f"from {map_name} e{elevation} tiles {g.tile_at(*low)}..{g.tile_at(*high)}: {text}")
    files = map_kit.preview_sheet(gf, prefabs, os.path.join(out, "overview"))
    index.append(f"  prefabs/overview-01..{len(files):02d}.png  thumbnails of all prefabs")


PARTS = {"sheets": build_sheets, "maps": build_maps, "regions": build_regions, "prefabs": build_prefabs}


def clean(directory):
    """Remove what an earlier run generated there, so renamed entries leave nothing stale behind."""
    if os.path.isdir(directory):
        for name in os.listdir(directory):
            if name.endswith((".png", ".txt", ".json")):
                os.remove(os.path.join(directory, name))


def main(argv):
    gf = GameFiles()
    wanted = argv or list(PARTS)
    index = ["Shanty-town asset survey for the Megaton map. Generated by mod/reference/build_survey.py from the",
             "retail Fallout 2 data; do not edit by hand. PIDs are hexadecimal, tile ids decimal."]
    for part in PARTS:
        if part in wanted:
            clean(os.path.join(HERE, part))
            PARTS[part](gf, os.path.join(HERE, part), index)
    if wanted == list(PARTS):
        with open(os.path.join(HERE, "index.txt"), "w") as f:
            f.write("\n".join(index) + "\n" + FOOTER)
    print("\n".join(index))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
