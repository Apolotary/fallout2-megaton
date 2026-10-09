#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Draw-order walk: the player walks (mouse clicks, the engine's own path finding) in front of,
behind and through every multi-part structure of the review stage, with a screenshot at every stop.

    python3 mod/megaton-art/stage/town/walk.py            build the step files, run the engine, check arrivals
    python3 mod/megaton-art/stage/town/walk.py --dry      only check that every stop is a free hex of the map

Needs the stage built (build_stage.py). Three engine runs, run/art-review-walk-gate, -crater,
-street; pictures land in stage/town/shots/walk-<leg>-<n>.png (n = 0 at the start hex).

A LEG: the player is put on its first hex, the view is centred on the structure, then he is
sent to each further hex by a click on it; after each click the script waits, logs where he is
and takes a picture. A stop he did not reach is reported: either something blocks that should
not, or the hex is one the piece blocks (then the leg is wrong, not the piece).
`pipeline/sorttest.py` (build.py sort) checks every free hex round every piece by arithmetic;
this walk shows the important ones in the real game, lit and animated, player sprite and all.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(ART))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ART)
sys.path.insert(0, HERE)

from f2lib import GameFiles, MapFile, geometry as g, ids      # noqa: E402

from pipeline import data                                     # noqa: E402
import build_stage                                            # noqa: E402

# run -> [(leg, centre hex, [stops ...], what it shows)]
LEGS = {
    "gate": [
        ("gate-front", (100, 126), [(103, 129), (101, 129), (99, 129), (98, 129), (95, 129)],
         "along the apron side of the shut gate: left bay, door, under the engine, right bay"),
        ("gate-behind", (100, 125), [(104, 125), (102, 125), (100, 125), (98, 125), (96, 125)],
         "along the town side: behind the left bay, the door, the right bay"),
        ("bus-front", (90, 126), [(95, 130), (93, 129), (88, 129), (85, 129), (83, 129)],
         "in front of the bus and the car-door wall"),
        ("bus-behind", (90, 125), [(96, 124), (90, 123), (90, 126), (88, 126), (86, 126)],
         "behind the nest, then between nest and bus, behind the bus and the car doors"),
        ("nest", (93, 124), [(96, 124), (96, 126), (95, 122), (93, 122), (91, 123), (91, 125)],
         "round the watch platform: ladder side, behind it, its right side"),
        ("hull-behind", (110, 125), [(104, 124), (105, 125), (107, 125), (110, 124), (113, 125), (116, 125)],
         "behind the fuselage and the container stack"),
        ("wires", (106, 116), [(105, 122), (106, 122), (107, 119), (106, 117), (106, 115), (105, 113), (107, 111), (106, 109)],
         "under the gate cables and the pole line, on and beside the cable parts' own hexes"),
        ("gate-open", (100, 126), "open", [(100, 127), (100, 125), (101, 127), (99, 127), (100, 129)],
         "the gate opened: into the gateway, through it, both passage hexes, back out"),
    ],
    "crater": [
        ("bomb-front", (100, 94), [(104, 96), (102, 95), (100, 95), (98, 95), (96, 95), (95, 94)],
         "along the bomb's near side, access hexes, to the tail end"),
        ("bomb-behind", (100, 93), [(95, 92), (96, 91), (99, 91), (102, 91), (104, 92), (105, 94)],
         "round the tail, along the far side, to the nose"),
        ("rim-far", (100, 85), [(106, 83), (103, 83), (101, 83), (99, 84), (97, 85), (95, 86), (93, 87), (91, 88), (91, 90)],
         "outside the retaining wall: behind rim_u, both rim_h, round the corner, beside rim_v"),
        ("rim-inside", (100, 87), [(104, 86), (102, 85), (100, 86), (98, 87), (97, 88), (94, 89), (93, 90)],
         "inside the wall, at its foot"),
        ("rim-left", (108, 85), [(106, 86), (108, 86), (110, 86), (111, 85), (110, 84), (108, 83)],
         "rim_w from inside, past its end, behind it"),
        ("rail-near", (100, 102), [(108, 102), (106, 102), (104, 103), (102, 103), (100, 104), (98, 103), (96, 104), (93, 103)],
         "outside the railing, under the prayer flags, past the notice"),
        ("rail-inside", (100, 100), [(106, 100), (104, 101), (100, 100), (96, 101), (94, 101)],
         "inside the railing, on the duckboards"),
        ("pipes", (89, 96), [(93, 97), (91, 97), (89, 97), (93, 95), (91, 95), (88, 95)],
         "in front of and behind the intake pipe"),
    ],
    "street": [
        ("saloon-awning", (106, 77), [(110, 79), (106, 79), (106, 78), (106, 77), (105, 76), (106, 76), (109, 77)],
         "to the saloon door: in front of, under and behind the awning, past its post and the wall lamp"),
        ("plaza-string", (102, 80), [(105, 82), (103, 81), (102, 80), (101, 79), (99, 79), (97, 81), (95, 80)],
         "under the plaza bulb strings, on the string part's own hex, round a pole"),
        ("clinic", (90, 103), [(93, 105), (91, 107), (91, 105), (91, 103), (89, 102), (89, 100), (91, 99)],
         "clinic sign front and behind, then under the lean-to awning to the door and out past its far post"),
        ("church", (91, 86), [(93, 85), (91, 85), (90, 86), (89, 86), (91, 87), (93, 86)],
         "atom sign, church door, wall lamp, string pole"),
        ("sheriff", (90, 115), [(93, 116), (91, 115), (89, 115), (89, 113), (91, 113), (89, 117)],
         "sheriff's sign and wall lamp"),
        ("lantern", (119, 108), [(123, 110), (120, 110), (118, 109), (116, 109), (115, 107), (116, 106), (118, 106)],
         "Brass Lantern: customers' side, between the stools, round the counter's end, behind it, under the awning"),
        ("lantern-sign", (124, 108), [(127, 110), (125, 109), (123, 109), (125, 107), (127, 107)],
         "round the hanging sign and the bench"),
        ("laundry", (135, 102), [(139, 103), (135, 103), (131, 103), (131, 102), (133, 101), (136, 101), (135, 102)],
         "in front of, round and behind the washing line, then under it"),
        ("craterside", (68, 78), [(70, 80), (67, 79), (65, 79), (63, 78), (65, 77), (67, 77), (69, 77)],
         "Craterside's sign, front and behind, the crates"),
    ],
}
NO_BLOCK = 0x10
GATE = (100, 127)


def blocked_hexes(gf, m):
    """Hexes of the stage map a critter cannot enter (the shut gate's passage counts as free)."""
    blocked = set()
    for obj in m.all_objects(0):
        hx, hy = g.tile_xy(obj.tile)
        if obj.obj_type in (ids.OBJ_TYPE_WALL, ids.OBJ_TYPE_CRITTER):
            blocked.add((hx, hy))
        elif obj.obj_type in (ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_ITEM) and not obj.flags & NO_BLOCK:
            if gf.protos.get(obj.pid).subtype_name != "door" or (hx, hy) != GATE:
                blocked.add((hx, hy))
    return blocked


def legs_of(run):
    for leg in LEGS[run]:
        if leg[2] == "open":
            yield leg[0], leg[1], leg[3], True, leg[4]
        else:
            yield leg[0], leg[1], leg[2], False, leg[3]


def check_stops():
    gf = GameFiles(overlay=[build_stage.OVERLAY, data.OUT])
    m = MapFile.load(build_stage.DAY, gf)
    blocked = blocked_hexes(gf, m)
    bad = []
    for run in LEGS:
        for label, _, stops, _, _ in legs_of(run):
            for stop in stops:
                if stop in blocked:
                    bad.append(f"{label}: stop {stop} is blocked in the stage map")
    return bad


def steps(run):
    t = lambda h: g.tile_at(*h)                                    # noqa: E731
    lines = [f"# generated by stage/town/walk.py ({run})", "wait 1200"]
    for label, centre, stops, opened, _ in legs_of(run):
        if opened:
            lines += [f"dude {t((100, 129))}", "wait 300", f"center {t((100, 124))}", "wait 300", f"use {t(GATE)}", "wait 3000"]
        lines += [f"dude {t(stops[0])}", "wait 700", f"dude {t(stops[0])}", "wait 300", f"center {t(centre)}", "wait 450",
                  f"log leg {label} 0", "state",
                  f"shot shots/walk-{label}-0.ppm"]
        for index, (before, stop) in enumerate(zip(stops, stops[1:]), start=1):
            reach = g.distance(t(before), t(stop))
            lines += [f"clicktile {t(stop)}", f"wait {800 + reach * 650}", f"log leg {label} {index}", "state",
                      f"shot shots/walk-{label}-{index}.ppm"]
    lines += ["quit 0", ""]
    return "\n".join(lines)


def run_one(run):
    path = os.path.join(HERE, f"steps-walk-{run}.txt")
    with open(path, "w") as f:
        f.write(steps(run))
    output = build_stage.run_engine(f"walk-{run}", build_stage.DAY, "1280x960", steps_path=path, timeout=600)
    tiles = [int(line.split("dudeTile=")[1].split()[0]) for line in output.splitlines() if "dudeTile=" in line]
    expected = [(label, index, stop) for label, _, stops, _, _ in legs_of(run) for index, stop in enumerate(stops)]
    missed = []
    if len(tiles) != len(expected):
        missed.append(f"{run}: {len(tiles)} positions reported, {len(expected)} expected (the run stopped early?)")
    for (label, index, stop), tile in zip(expected, tiles):
        if tile != g.tile_at(*stop):
            missed.append(f"{label} stop {index}: sent to {stop}, stands on {g.tile_xy(tile)}")
    return len(expected), missed


def run(only=None):
    bad = check_stops()
    for line in bad:
        print(f"[walk] {line}")
    if bad:
        raise SystemExit("the walk has stops on blocked hexes: fix LEGS")
    total, missed = 0, []
    for name in LEGS:
        if only and name != only:
            continue
        count, lost = run_one(name)
        total += count
        missed += lost
    for line in missed:
        print(f"[walk] NOT REACHED {line}")
    print(f"[walk] {total - len(missed)} of {total} stops reached; pictures: stage/town/shots/walk-*.png")
    return missed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", choices=sorted(LEGS))
    args = ap.parse_args()
    if args.dry:
        bad = check_stops()
        for line in bad:
            print(f"[walk] {line}")
        print(f"[walk] {sum(len(l[3] if l[2] == 'open' else l[2]) for legs in LEGS.values() for l in legs)} stops, {len(bad)} on blocked hexes")
        return
    run(args.only)


if __name__ == "__main__":
    main()
