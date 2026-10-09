# SPDX-License-Identifier: MIT
"""The town's buildings for sheet and piece scripts: read from the last snapshot (town/snapshot/town.json),
so a roof sheet is always sized for the building as the town builds it today. Pure Python.

    from kit import sheet, town
    S = town.shack("saloon")                 # pipeline.tilegeo.Shack: size, first square, wall lines, door()
    @sheet("rf_saloon", kind="roof", size=S.size)
    def rf_saloon(ctx): ...

    town.box("clinic")        (hx_lo, hy_lo, hx_hi, hy_hi)
    town.buildings()          the names: saloon craterside billy church common plant lucy clinic lantern sheriff house
    town.doors("clinic")      [(side, position, name)] of its outer doors
    town.facts()              the whole of town.json (plan, spots, reserved hexes, click targets)
"""
import json
import os

from pipeline import tilegeo as T

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "town", "snapshot", "town.json")
_cache = {}


def facts():
    if "facts" not in _cache:
        if not os.path.exists(_PATH):
            raise FileNotFoundError("no town snapshot: run python3 mod/megaton-art/town/snapshot.py")
        with open(_PATH) as f:
            _cache["facts"] = json.load(f)
    return _cache["facts"]


def buildings():
    return list(facts()["plan"]["buildings"])


def box(name):
    try:
        return tuple(facts()["plan"]["buildings"][name]["box"])
    except KeyError:
        raise KeyError(f"no building {name!r} in the town (has: {', '.join(buildings())})") from None


def shack(name):
    return T.Shack(box(name))


def doors(name):
    return [tuple(d) for d in facts()["plan"]["buildings"][name]["doors"]]
