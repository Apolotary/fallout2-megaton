# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Megaton map generation: build_maps(out_dir) writes maps/megaton.map.

    python3 mod/megaton/build.py --out mod/megaton/out-layout ids data protos art scripts maps
    python3 mod/megaton/layout/preview.py            # overview and per-building crops
    python3 mod/megaton/tests/layout/test_layout.py  # validate, roofs, reachability, spots

The modules, in the order build() uses them:

    plan.py       every coordinate: wall outline, gate, bomb, buildings, apron, paths
    spots.py      named places for NPCs and scripted objects (the contract with scripts)
    kit.py        how wall pieces go together: the tin / wood shack kit and the stockade
    terrain.py    floor tiles: desert, cracked crater floor, paths, the slime pool
    perimeter.py  the outer wall with its gate, junk heaps against it
    buildings.py  the eleven shells, the Brass Lantern's counter, the bomb's cradle, lights
    apron.py      exit grids, the invisible fence behind them, scroll blockers
    walk.py       where one can walk (the engine's blocking rule); used by the tests
    dressing.py   the decorator's tool box: furniture with its blockers, containers, lamps
    interiors.py  what stands in each of the eleven buildings
    outdoors.py   signs, lamps, junk, the yards, the pool's furniture, the apron
    art.py        the custom pre-rendered art (mod/megaton-art): gate set, bomb, signs, string
                  lights, crater dressing - placed from the art director's plan, in place of
                  the stock objects it replaces

The cast (cast/) is placed last, on the spots, so NPCs and scripted objects
appear as the script groups deliver them. The decorator adds furniture and
dressing afterwards through decorate() - see its docstring for the rules.
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(MOD))
for _path in (MOD, os.path.join(ROOT, "tools")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from f2lib import GameFiles, MapFile, geometry as g  # noqa: E402

from . import apron, buildings, kit, perimeter, plan, spots, terrain  # noqa: E402

MAP_NAME = "megaton"
MAP_SCRIPT = "megaton"
SEED = 2241                      # the year; every random choice of the builder comes from this
SPOTS_FILE = ".spots.json"       # read by test.py for @NAME (hidden files are not packed)


class LayoutError(Exception):
    pass


def build(gf, groups=None, strict=False, with_cast=True, log=print, art=None):
    """Build the town on a new MapFile and return (map, info).

    art   True: with the custom art (layout/art.py; `build.py art` must have staged it).
          False: the stock town the art plan starts from. None (default): with the art when it
          is staged; a strict build insists on it.
    info: {"shacks": {key: kit.Shack}, "fence": set of hexes, "gate": door object,
           "exits": set of hexes, "pool": set of hexes, "placed": cast placements,
           "dressing": the decorator's books, "art": what layout/art.py placed and replaced}
    """
    from . import art as art_module

    if art is None:
        art = art_module.staged(gf)
        if strict and not art:
            raise LayoutError("the custom art is not staged (proto/scenery/mgs*.pro): run the build's `art` step")
    rng = random.Random(SEED)
    m = MapFile.new(MAP_NAME, gf)

    ground = terrain.lay(m, random.Random(rng.random()))
    shacks = buildings.build_shacks(m, random.Random(rng.random()))
    stall = buildings.build_lantern_stall(m, random.Random(rng.random()))
    beds = buildings.build_beds(m)
    fence, gate = perimeter.build(m, random.Random(rng.random()))
    bomb_blocked = buildings.build_bomb(m, random.Random(rng.random()), ground["pool"])
    exits = apron.build(m, fence)
    frame, blockers = apron.scroll_frame(m)
    lights = buildings.add_lights(m, shacks)

    ex, ey, rotation = spots.SPOTS["ENTRY"]
    entrance = g.tile_at(ex, ey)
    if not g.can_center(entrance):
        raise LayoutError(f"ENTRY ({ex}, {ey}) cannot be a view centre")
    m.set_entrance(entrance, elevation=0, rotation=rotation)

    info = {"shacks": shacks, "fence": fence, "gate": gate, "exits": exits,
            "pool": ground["pool"], "stall": stall, "bomb_blocked": bomb_blocked,
            "frame": frame, "lights": lights, "beds": beds, "placed": []}
    decorate(m, gf, info, log=log, art=art)

    if with_cast:
        import cast

        info["placed"] = cast.place_cast(m, gf, groups=groups, strict=strict, log=log)
        if "dressing" in info:
            from . import dressing

            dressing.after_cast(m, gf, info)
    buildings.ensure_bomb(m, art=art)

    if gf.exists(f"scripts/{MAP_SCRIPT}.int"):
        m.set_map_script(MAP_SCRIPT)
    else:
        log(f"layout: {MAP_SCRIPT}.ssl is not compiled, the map has no map script")
    log(f"layout: {len(m.objects[0])} objects, {len(shacks)} buildings, {len(fence)} wall hexes, "
        f"{len(exits)} exit hexes, {blockers} scroll blockers, {len(info['placed'])} cast entries")
    return m, info


def decorate(m, gf, info, log=print, art=False):
    """Furniture, signs, junk, the apron's dressing, then the custom art over it.

    Called after the bones are built and BEFORE the cast is placed, so a
    careless object cannot land on top of an NPC unnoticed: the tests in
    tests/layout fail if a spot is blocked or cut off. Order: dressing.dress()
    (interiors.py, outdoors.py), art.apply() (replaces part of that dressing by
    the pre-rendered pieces and checks its plan against this very map), then
    the blockers on the row behind every back wall (dressing.close_trim_rows:
    under the roof's trim, where standing would take that roof off), and last
    the blockers on hexes that all of it has cut off from the town.
    """
    from . import art as art_module, dressing

    from . import density

    # Preserve the exact deterministic stock town used for the reviewed mock.
    # New reservations govern the final town after the declared replacements.
    with density.reservations(False):
        dresser = dressing.dress(m, gf, info)
    with density.reservations(art):
        # Exact stock replacements have now been staged. Reserve the full final
        # walk-under contract for art validation and subsequent pocket sealing.
        dresser.reserved = keep_free()
        dresser.hard = {h for h, why in dresser.reserved.items() if not why.startswith(("access", "doorstep"))}
        if art:
            art_module.apply(m, gf, info, log=log)
        dressing.close_trim_rows(dresser)
        dressing.seal_pockets(dresser)


def keep_free():
    """{(hx, hy): reason}: hexes furniture and dressing must leave walkable.

    The decorator's contract, checked by tests/layout/test_layout.py (keep_free):
      - every spot an NPC stands on or walks to;
      - one hex in front of every scripted object (terminal, cabinet, strongbox,
        locker, leaking pipes, beds): the hexes around it, of which the test
        demands at least one stays free and reachable, are listed as "access";
      - each doorway with the hexes just inside and outside it, the three hexes
        of the gateway and the rows before and behind it;
      - the middle line of the paths of plan.PATHS (the track from the exit grid
        to the pool, and the lanes from the pool to the saloon, the water plant,
        Lucy's, Craterside and Billy's);
      - the cradle's front lip, from where the bomb is worked on.
    Hexes marked "access" may be blocked as long as one per object stays free.
    """
    import cast

    free = {}
    held = {}                                # spot name -> kinds of cast entries on it
    for entry in cast.load():
        if isinstance(entry["spot"], str):
            held.setdefault(entry["spot"], set()).add(entry["type"])
    door_tiles = {pos for _, _, pos, _ in plan.all_doors()} | {plan.GATE}
    for name, (hx, hy, _) in spots.SPOTS.items():
        if (hx, hy) in door_tiles or name == "BOMB":
            continue
        if held.get(name, set()) & {"thing", "attach"}:
            for n in g.neighbors(g.tile_at(hx, hy)):
                free.setdefault(g.tile_xy(n), f"access to {name}")
        else:
            free[(hx, hy)] = f"spot {name}"
    for key, name, (hx, hy), _ in plan.all_doors():
        free[(hx, hy)] = f"door {key} / {name}"
        for n in g.neighbors(g.tile_at(hx, hy)):
            free.setdefault(g.tile_xy(n), f"doorstep {key} / {name}")
    gx, gy = plan.GATE
    for dx in (-1, 0, 1):
        for dy in (-2, -1, 0, 1, 2):
            free[(gx + dx, gy + dy)] = "gateway"
    for (ax, ay), (bx, by), _ in plan.PATHS:
        for tile in g.line(g.tile_at(ax, ay), g.tile_at(bx, by)):
            free.setdefault(g.tile_xy(tile), "path")
    for dx, dy in buildings.BOMB_ACCESS:
        free[(plan.BOMB[0] + dx, plan.BOMB[1] + dy)] = "bomb access"
        free[(plan.BOMB[0] + dx, plan.BOMB[1] + dy + 1)] = "bomb access"
    from . import density
    for hex_, reason in density.keep_free().items():
        free.setdefault(hex_, reason)
    return free


def test_names(m, info=None):
    """{NAME: tile} for step files (test.py's @NAME): every spot, plus names for the plan.

        @STASH_BILLY, _CLINIC, _PLANT, _LANTERN   the locked containers of layout/interiors.py
        @DOOR_<BUILDING>_<DOOR>   a door hex, e.g. @DOOR_SALOON_OFFICE, @DOOR_CLINIC_CLINIC
        @IN_<BUILDING>_<ROOM>     a free hex in the middle of a room, e.g. @IN_SALOON_HALL
        @POOL, @PLAZA, @TRACK     open ground: beside the bomb, in front of the saloon, inside the gate
    """
    from . import walk

    blocked, doors, exits = walk.survey(m)
    names = {name: hy * 200 + hx for name, (hx, hy, _) in spots.SPOTS.items()}

    def label(*parts):
        return "_".join(part.upper().replace(" ", "_").replace("'", "") for part in parts)

    for key, name, (hx, hy), _ in plan.all_doors():
        names[label("DOOR", key, name)] = g.tile_at(hx, hy)
    for key, spec in plan.BUILDINGS.items():
        for room, (lo_x, lo_y, hi_x, hi_y) in spec["rooms"].items():
            centre = g.tile_at((lo_x + hi_x) // 2, (lo_y + hi_y) // 2)
            inside = [g.tile_at(hx, hy) for hx in range(lo_x, hi_x + 1) for hy in range(lo_y, hi_y + 1)]
            free = [t for t in inside if t not in blocked and t not in doors
                    and not any(obj.obj_type == 1 for obj in m.objects_at(t))]
            names[label("IN", key, room)] = min(free, key=lambda t: g.distance(t, centre))
    for box in (info or {}).get("dressing", {}).get("containers", ()):
        if box.get("tag"):
            names[box["tag"]] = g.tile_at(*box["hex"])
    names["POOL"] = g.tile_at(plan.BOMB[0] + 3, plan.BOMB[1] + 4)
    names["PLAZA"] = g.tile_at(plan.BOMB[0], plan.BOMB[1] - 14)
    names["TRACK"] = g.tile_at(plan.GATE[0], plan.GATE[1] - 6)
    return names


def build_maps(out_dir, strict=False, log=print, art=None):
    """build.py entry point: write maps/megaton.map into the staging tree `out_dir`.
    art: see build() (False = the stock town without the custom art, for comparisons)."""
    gf = GameFiles(overlay=out_dir)
    m, info = build(gf, strict=strict, log=log, art=art)
    problems = [p for p in m.validate() if "locked door without a script" not in p]
    for problem in problems:
        log("layout: " + problem)
    if any(p.startswith("error") for p in problems):
        raise LayoutError("the map has errors")
    os.makedirs(os.path.join(out_dir, "maps"), exist_ok=True)
    m.save(os.path.join(out_dir, "maps", m.file_name))
    with open(os.path.join(out_dir, SPOTS_FILE), "w") as f:
        json.dump(test_names(m, info), f, indent=1, sort_keys=True)
    log(f"maps: {m.file_name} written")
    return m, info
