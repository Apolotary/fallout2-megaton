#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The custom art in the real town, in the real engine (run names mg-art-*).

    python3 mod/megaton/tests/art/run_all.py                 arrival, states, clicks, reach (about 7 minutes)
    python3 mod/megaton/tests/art/run_all.py arrival clicks  only these
    python3 mod/megaton/tests/art/run_all.py looks           the picture tours (no assertions: open them)
    python3 mod/megaton/tests/art/run_all.py --publish       no engine: copy the tours' best pictures to
                                                             mod/megaton/out-preview/art-*.png

    arrival   1040x480 (the phone's window): the view on arrival shows the whole MEGATON sign and
              the newcomer; the shut gate lets nobody through; Weld greets, the gate slides open
              (frame 0 -> 4), the player walks through it
    states    the bomb's frame follows GVAR_MG_BOMB (0 dormant, 1 charge fitted, 2 disarmed); gate
              and bomb keep their pictures through leaving for the world map, a save and a load
    clicks    mouse clicks on every outer door, on Jenny, Cromwell and the bomb, on the town with
              the art and on the same town without it (stage_stock.py): what worked without the
              art must work with it, and the bomb's menu must open from a click on its casing
    reach     what a click reaches in absolute terms: the three doors that stood under their own
              roofs (common house, Lucy West's, the player's house) open from three hexes away, and
              Lucy West, Jericho, Moira's mercenary, Harden Simms and Maggie, who stood behind walls
              and roofs, answer a click on the body from across the room
    looks     every district by day and at night at 1280x960 (run/mg-art-big-looks) and at
              1040x480 (run/mg-art-phone-looks), on the integration stage (its rig moves the clock)

Staging dirs: mod/megaton/out-art, out-art-stock, out-art-big, out-art-phone. One engine at a time.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(MOD))
INT_STAGE = os.path.join("tests", "integration", "stage.py")


def test(group, steps, *options):
    """Run one scenario through test.py; returns (passed, the run's autotest log lines)."""
    command = [sys.executable, os.path.join(MOD, "test.py"), "--group", group,
               "--steps", os.path.join("tests", "art", steps + ".txt")] + list(options)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, errors="replace")
    tail = result.stdout[result.stdout.find("== debug.log"):]
    print(f"--- {group}: {steps}\n{tail}", flush=True)
    return result.returncode == 0, result.stdout.splitlines()


def click_outcomes(lines, protos):
    """Classify actual door prototypes, matching one stable (tile, PID) across phases.

    Other scenery may share a door hex and carry the same translucency flags as
    an open door. Missing, duplicate, or ambiguous door evidence fails closed.
    """
    seen = {}
    target = phase = None
    for line in lines:
        match = re.search(r"\[autotest\] CLICK (\S+) (BEFORE|AFTER)", line)
        if match:
            target, phase = match.groups()
            phases = seen.setdefault(target, {})
            if phase in phases:
                phases[phase]["invalid"] = True
            else:
                phases[phase] = {"doors": {}, "invalid": False, "dialog": None}
            continue
        if target is None:
            continue
        sample = seen[target][phase]
        obj = re.search(r"\[autotest\] obj tile=(\d+) pid=(0x[0-9A-Fa-f]+).*flags=(0x[0-9A-Fa-f]+).*frame=(\d+)", line)
        state = re.search(r"\[autotest\] state .*dialog=(\d)", line)
        if target.startswith("door-") and obj:
            tile, number, flags, frame = (int(obj.group(1)), int(obj.group(2), 16),
                                          int(obj.group(3), 16), int(obj.group(4)))
            if number >> 24 != 2:     # only scenery prototypes can be doors
                continue
            try:
                proto = protos.get(number)
                if proto is None:
                    raise KeyError(number)
                is_door = proto.subtype_name == "door"
            except (KeyError, ValueError, IndexError, FileNotFoundError):
                sample["invalid"] = True
                continue
            if not is_door:
                continue
            key = (tile, number)
            if key in sample["doors"]:
                sample["invalid"] = True
            # Frame > 0 includes a leaf caught in mid-swing before flags change.
            sample["doors"][key] = frame > 0 or flags & 0xA0000010 == 0xA0000010
        elif not target.startswith("door-") and state:
            sample["dialog"] = state.group(1) == "1"
    outcomes = {}
    for name, pair in seen.items():
        if set(pair) != {"BEFORE", "AFTER"} or any(s["invalid"] for s in pair.values()):
            outcomes[name] = "invalid"
            continue
        before, after = pair["BEFORE"], pair["AFTER"]
        if name.startswith("door-"):
            if len(before["doors"]) != 1 or set(before["doors"]) != set(after["doors"]):
                outcomes[name] = "invalid"
                continue
            key = next(iter(before["doors"]))
            changed = before["doors"][key] != after["doors"][key]
        else:
            if before["dialog"] is None or after["dialog"] is None:
                outcomes[name] = "invalid"
                continue
            changed = before["dialog"] != after["dialog"]
        outcomes[name] = "worked" if changed else "nothing"
    return outcomes


def run_clicks():
    ok_art, art = test("art", "clicks", "--res", "1280x960", "--timeout", "420")
    ok_stock, stock = test("art-stock", "clicks", "--stage", os.path.join("tests", "art", "stage_stock.py"),
                           "--res", "1280x960", "--timeout", "420")
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from f2lib import GameFiles

    with_art = click_outcomes(art, GameFiles(overlay=os.path.join(MOD, "out-art")).protos)
    without = click_outcomes(stock, GameFiles(overlay=os.path.join(MOD, "out-art-stock")).protos)
    failed = (not (ok_art and ok_stock) or not with_art or set(with_art) != set(without)
              or "invalid" in with_art.values() or "invalid" in without.values())
    print("--- clicks: target, without the art, with the art")
    for name in sorted(without):
        verdict = "ok"
        if without[name] == "worked" and with_art.get(name) != "worked":
            verdict = "FAIL: the art took the click"
            failed = True
        if name == "use-bomb" and with_art.get(name) != "worked":
            verdict = "FAIL: the bomb's menu did not open"
            failed = True
        if name.startswith("door-") and with_art.get(name) != "worked":
            verdict = "FAIL: a click does not open this door"
            failed = True
        if without[name] == "invalid" or with_art.get(name) == "invalid":
            verdict = "FAIL: missing, unknown, or ambiguous click evidence"
        print(f"    {name:<18} {without[name]:<8} {with_art.get(name, '?'):<8} {verdict}")
    return not failed


# out-preview name: (looks run, shot). Day and night, the desktop window (1280x960) and the phone's (1040x480).
PUBLISH = {
    "art-arrival-phone.png": ("phone", "d-00-arrival"), "art-arrival-phone-night.png": ("phone", "n-00-arrival"),
    "art-arrival.png": ("big", "d-00-arrival"), "art-arrival-night.png": ("big", "n-00-arrival"),
    "art-gate-shut.png": ("big", "d-01-gate-shut"), "art-gate-open.png": ("big", "d-03-gate-open"),
    "art-gate-shut-night.png": ("big", "n-01-gate-shut"), "art-gate-open-night.png": ("big", "n-03-gate-open"),
    "art-gate-open-phone.png": ("phone", "d-03-gate-open"),
    "art-street.png": ("big", "d-inside-gate"), "art-street-night.png": ("big", "n-inside-gate"),
    "art-street-phone.png": ("phone", "d-inside-gate"), "art-street-phone-night.png": ("phone", "n-inside-gate"),
    "art-crater-dormant.png": ("big", "d-bomb-dormant"), "art-crater-rigged.png": ("big", "d-bomb-rigged"),
    "art-crater-disarmed.png": ("big", "d-bomb-disarmed"), "art-crater-rigged-night.png": ("big", "n-bomb-rigged"),
    "art-crater-dormant-night.png": ("big", "n-bomb-dormant"), "art-crater-disarmed-night.png": ("big", "n-bomb-disarmed"),
    "art-crater-phone.png": ("phone", "d-bomb-dormant"), "art-crater-phone-night.png": ("phone", "n-bomb-rigged"),
    "art-saloon.png": ("big", "d-saloon"), "art-saloon-night.png": ("big", "n-saloon"),
    "art-saloon-front-phone.png": ("phone", "d-plaza"), "art-saloon-front-phone-night.png": ("phone", "n-plaza"),
    "art-brass-lantern.png": ("big", "d-lantern"), "art-brass-lantern-night.png": ("big", "n-lantern"),
    "art-brass-lantern-phone.png": ("phone", "d-lantern"),
    "art-clinic-sheriff.png": ("big", "d-clinic-sheriff"), "art-clinic-sheriff-night.png": ("big", "n-clinic-sheriff"),
    "art-clinic-sheriff-phone.png": ("phone", "d-clinic-sheriff"), "art-clinic-sheriff-phone-night.png": ("phone", "n-clinic-sheriff"),
}


def publish():
    import shutil

    target = os.path.join(MOD, "out-preview")
    os.makedirs(target, exist_ok=True)
    missing = 0
    for name, (run, shot) in PUBLISH.items():
        source = os.path.join(ROOT, "run", f"mg-art-{run}-looks", "shots", shot + ".png")
        if os.path.exists(source):
            shutil.copyfile(source, os.path.join(target, name))
        else:
            print(f"missing: {os.path.relpath(source, ROOT)} (run `run_all.py looks` first)")
            missing += 1
    print(f"{len(PUBLISH) - missing} pictures copied to {os.path.relpath(target, ROOT)}")
    return 1 if missing else 0


SCENARIOS = {
    "arrival": lambda: test("art", "arrival", "--res", "1040x480", "--timeout", "300")[0],
    "states": lambda: test("art", "states", "--timeout", "400")[0],
    "clicks": run_clicks,
    "reach": lambda: test("art", "reach", "--res", "1280x960", "--timeout", "300")[0],
    "looks": lambda: all([test("art-big", "looks", "--stage", INT_STAGE, "--res", "1280x960", "--timeout", "480")[0],
                          test("art-phone", "looks", "--stage", INT_STAGE, "--res", "1040x480", "--timeout", "480")[0]]),
}
DEFAULT = ["arrival", "states", "clicks", "reach"]


def main(argv):
    if argv[1:] == ["--publish"]:
        return publish()
    names = argv[1:] or DEFAULT
    unknown = [name for name in names if name not in SCENARIOS]
    if unknown:
        print(__doc__)
        return 2
    failed = [name for name in names if not SCENARIOS[name]()]
    print("art tests: " + ("FAILED: " + ", ".join(failed) if failed else "all passed"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
