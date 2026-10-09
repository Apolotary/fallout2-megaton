# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The custom pre-rendered art in the town, including the reviewed density pass.

    layout.build() -> decorate() -> dressing.dress() -> art.apply() -> seal pockets -> cast

The sprites come from the Blender pipeline in mod/megaton-art (staged by `build.py art`). WHERE
each piece stands, and which stock object of the town it replaces, is the art director's plan in
mod/megaton-art/placement.py. This module is the only place that plan meets the map:

  1. placement.resolve(town=m) checks the original plan against the map as it has just been built
     (bones and stock dressing, no cast yet): every object a piece replaces must be there, no
     footprint may land on a blocking object or a named spot, the hexes a piece promises to keep
     free must be free, and every spot and doorway that could be reached before must still be
     reachable. Any problem stops the build (ArtError): the layout moved, so move the placement.
  2. The replaced stock objects are taken off the map: fence sheets and their blockers where the
     gate set and the junk walls stand, lamp posts and invisible lights where a piece brings its
     own lamp, the signs, the Brass Lantern's bar, the pool's furniture.
  3. The pieces are placed. how="placer": pipeline.place.Placer (parts in paint order, invisible
     blockers on footprint hexes without a picture, the stock "animfrvr" script on animated
     parts). how="any": a one-hex piece, its parts on the hex itself. how="object": the bomb -
     the CAST creates that one object (cast/core.py, PID_MGA_BOMB with mgbomb.ssl); only its
     blockers are added here.
  4. Hooks:
       gate     the town's own door object (kit.GATE on plan.GATE, MULTIHEX, mggate.ssl) keeps its
                proto and wears the five-frame door FRM (frame 0 shut .. 4 open). The engine plays
                the frames when the door is opened or closed and keeps the last one, so the script
                needs no art code and a shut gate still blocks its seven hexes.
       decor    the pieces that replace furniture mgdecor.ssl describes (podium, banners, signs,
                the bar) carry mgdecor.ssl themselves; it knows them by PID (ids.h PID_MGA_*).
       lamps    a part whose proto has a light is a lamp by being placed; the dressing's record of
                lights (tests/layout: enough lamps, a light near every door) follows the swap.
  5. density.apply() validates placement-v2.json against the complete manifest, removes exact
     objects, applies frozen roof/floor indices and places density pieces through the same
     decor/animation path. It merges the final placement and lamp summaries before the town
     closes trim rows, seals pockets or places the cast. It never imports the mock or allocates tiles.

The stock dressing code (outdoors.py, buildings.py, perimeter.py) still places what is replaced:
the town can be built without the art (layout.build(art=False): the plan's "before" picture and
the base the plan is checked against), and nothing here depends on how those modules order
their work. Read "replaced by the art" in their comments as: removed again in step 2.
"""
import os
import sys

from f2lib import geometry as g, ids

import registry

from . import density, kit, plan, spots

ART_DIR = registry.art_dir()
DECOR_SCRIPT = "mgdecor"
ORDER = {"shadow": 0, "halo": 1, "main": 2, "glow": 3}
OBJECT_FLAT = 0x08


class ArtError(Exception):
    pass


def decor_pids():
    """PIDs of the art pieces that carry mgdecor.ssl (every named piece but the bomb)."""
    return {pid for name, pid in registry.art_pids().items() if name != "PID_MGA_BOMB"}


def bomb_pid():
    return registry.art_pids().get("PID_MGA_BOMB")


def staged(gf):
    """True when the art's protos are in the tree the map is built from (`build.py art` ran)."""
    pid = bomb_pid()
    return pid is not None and gf.protos.exists(pid)


def _art_modules():
    """(placement module, Placer class) of mod/megaton-art."""
    if ART_DIR not in sys.path:
        sys.path.insert(0, ART_DIR)
    import placement                      # mod/megaton-art/placement.py
    from pipeline.place import Placer     # mod/megaton-art/pipeline/place.py

    return placement, Placer


def resolve(m, gf):
    """The plan checked against map `m` (the town before the art and before the cast).

    Returns (document, placer). Raises ArtError listing every problem."""
    placement, Placer = _art_modules()
    manifest = registry.art_manifest()
    problems = []
    for key, want in (("GATE", plan.GATE), ("BOMB", plan.BOMB), ("LANTERN_BAR", plan.LANTERN_BAR)):
        if tuple(placement.PLAN[key]) != tuple(want):
            problems.append(f"placement.PLAN[{key!r}] is {placement.PLAN[key]}, layout/plan.py says {want}")
    base_manifest = density.base_manifest(manifest, density.load())
    document, found = placement.resolve(base_manifest, town=m, gf=gf,
                                        spots={name: (hx, hy) for name, (hx, hy, _) in spots.SPOTS.items()})
    problems += found
    if problems:
        raise ArtError("the art placement plan (mod/megaton-art/placement.py) does not fit the town:\n  "
                       + "\n  ".join(problems))
    return document, Placer(manifest)


def apply(m, gf, info, log=print):
    """Steps 1 to 4 of the module docstring on map `m`. Returns the summary stored in info["art"]."""
    document, placer = resolve(m, gf)
    record = info.get("dressing")
    decor = decor_pids()
    script_ready = gf.scripts.find(DECOR_SCRIPT) is not None and gf.exists(f"scripts/{DECOR_SCRIPT}.int")

    # 2. the stock objects the pieces replace
    removed = []
    for place in document["placements"]:
        for item in place["remove"]:
            pid = int(item["pid"], 16)
            found = [obj for obj in m.objects_at(item["tile"]) if obj.pid == pid]
            if not found:
                raise ArtError(f"{place['piece']}: {item['pid']} is no longer on {item['hex']}")
            m.remove_object(found[0])
            removed.append((tuple(item["hex"]), pid, item["pid"], place["piece"]))
    if record:
        gone = {(hx, hy) for (hx, hy), pid, _, _ in removed}
        gone_pids = {((hx, hy), pid) for (hx, hy), pid, _, _ in removed}
        record["lights"] = [light for light in record["lights"] if (light[2], light[3]) not in gone]
        record["objects"] = [entry for entry in record["objects"] if ((entry[3], entry[4]), entry[2]) not in gone_pids]
        record["scripted"] = [entry for entry in record["scripted"] if tuple(entry[2]) not in gone
                              or any(o.sid != -1 for o in m.objects_at(g.tile_at(*entry[2])))]

    # 3. the pieces
    def place_rows(rows):
        placed, lamps, scripted = [], [], []
        for place in rows:
            name, tile, how = place["piece"], place["tile"], place["how"]
            piece = placer.piece(name)
            if how == "placer":
                created = placer.place(m, name, tile)
            elif how == "any":
                created = [m.add_object(int(part["pid"], 16), tile, script=part["script"])
                           for part in sorted(piece["parts"], key=lambda p: ORDER[p["layer"]])]
            elif how == "object":
                if int(next(p["pid"] for p in piece["parts"] if p["layer"] == "main"), 16) != bomb_pid():
                    raise ArtError(f"{name}: how='object' is the bomb's; the cast has no entry for this piece")
                created = [m.add_object(int(piece["blocker_pid"], 16), g.tile_at(hx, hy)) for hx, hy in place["blockers"]]
                info["bomb_blocked"] = {tuple(h) for h in place["blockers"]}
            else:
                raise ArtError(f"{name}: unknown how {how!r}")
            for obj in created:
                if obj.pid in decor and script_ready and obj.sid == -1:
                    m.attach_script(obj, DECOR_SCRIPT)
                    scripted.append((name, g.tile_xy(obj.tile)))
                    if record:
                        record["scripted"].append(("art: " + place["group"], piece["title"], g.tile_xy(obj.tile)))
            for part in place["parts"]:
                if part["light"] and how != "object":
                    hx, hy = part["hex"]
                    percent = round(part["light"][1] * 100 / 65536)
                    lamps.append((name, hx, hy, part["light"][0], percent))
                    if record:
                        record["lights"].append(("art: " + place["group"], piece["title"], hx, hy, part["light"][0], percent))
            placed.append((name, tuple(place["origin"]), how, len(created)))
        return placed, lamps, scripted

    placed, lamps, scripted = place_rows(document["placements"])

    # 4. the gate's door wears the five-frame door FRM
    door = document["hooks"]["gate_door"]
    gate = info.get("gate")
    if gate is None or g.tile_xy(gate.tile) != tuple(plan.GATE) or gate.pid != int(door["object"]["proto"], 16):
        raise ArtError("the town's gate door object is not the stock gate on plan.GATE")
    fid = int(door["set"]["fid"], 16)
    if gf.art.load(fid).frame_count != door["frames"] or door["frames"] < 2:
        raise ArtError(f"the gate's door FRM {door['set']['frm']} does not hold {door['frames']} frames: rebuild the art")
    gate.fid = fid

    summary = {"placed": placed, "removed": removed, "lamps": lamps, "scripted": scripted,
               "gate_fid": fid, "document": document}
    summary = density.apply(m, gf, info, summary, placer, place_rows)
    placement, _ = _art_modules()
    summary["document"]["hooks"] = placement.hooks(placer.manifest)
    placed, removed, lamps, scripted = (summary[k] for k in ("placed", "removed", "lamps", "scripted"))
    info["art"] = summary
    log(f"art: {len(placed)} placements of {len({name for name, _, _, _ in placed})} pieces, {len(removed)} stock objects "
        f"replaced, {len(lamps)} lamps, {len(scripted)} pieces with {DECOR_SCRIPT}")
    return summary


def report(info, out=print):
    """What stands where, group by group (cd mod/megaton && python3 -m layout.art [staging dir])."""
    summary = info["art"]
    for group in dict.fromkeys(p["group"] for p in summary["document"]["placements"]):
        out(f"== {group}")
        for place in summary["document"]["placements"]:
            if place["group"] != group:
                continue
            gone = ", ".join(f"{item['pid']} {tuple(item['hex'])}" for item in place["remove"]
                             if int(item["pid"], 16) != 0x02000043)
            out(f"   {place['piece']:<18} {str(tuple(place['origin'])):<11} {place['how']:<7}"
                + (f" replaces {gone}" if gone else ""))


if __name__ == "__main__":             # cd mod/megaton && python3 -m layout.art [staging dir]
    import layout
    from f2lib import GameFiles

    staging = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(layout.HERE), "out")
    _, built = layout.build(GameFiles(overlay=staging), log=lambda *a: None)
    if "art" in built:
        report(built)
    else:
        print(f"{staging} holds no custom art: run the build's `art` step there first")
