#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Build the mod into a private staging dir and run one scripted scenario in the real engine.

    python3 mod/megaton/test.py --group core --stage tests/core/stage.py --steps tests/core/simms.txt
    python3 mod/megaton/test.py --group core --steps tests/core/arrival.txt --res 1280x960     (real town)

What it does
  1. Wipes mod/megaton/out-<group>/ and runs build.py there (ids data protos art scripts
     maps lint pack) with --stage / --only as given. Without --stage the real town
     (layout/) is built: that is the integration case.
  2. Runs tools/f2test.py: a new game that starts on megaton.map with that
     patch001.dat mounted, debug.log on, script debug_msg() output logged. The run
     directory is run/mg-<group>-<steps file stem>/; the native runner preserves the
     previous run before its --fresh setup.
     A game that starts at the gate begins with the Vault-suit movie (megaton.ssl,
     starting kit); it is dismissed before the first step (--skip-movies).
  3. Prints the autotest log, every debug.log line containing ERROR / Error, the
     verdict of every `expect`, and the screenshot paths (PNG: open them and LOOK).

Exit status is non-zero when the build fails, the engine times out or exits with
an error, debug.log reports an error, or an `expect` does not hold.

Step files
  One autotest command per line, '#' starts a comment (tools/f2test.py -h lists the
  commands; the optional engine patch is documented in engine/README.md). The steps start
  in the game, on the map, about five seconds after it loaded. On top of the raw
  commands this script understands:

    @NAME            tile of a spot (layout/spots.py; on a stage: where the stage put
                     it, including the stage props @PROP_CHEST, @PROP_LOCKED_CHEST, @PROP_DOOR)
    @NAME/D          the hex next to it in direction D (0 NE, 1 E, 2 SE, 3 SW, 4 W, 5 NW)
    @NAME/D/N        N hexes away in direction D
    $NAME            number of a #define from scripts/ids.h or scripts/megaton.h
                     ($GVAR_MG_BOMB, $MG_BOMB_DISARMED, $MG_F_HOUSE_OWNED, $PID_MG_HOUSE_KEY)
    shot NAME        short for `shot shots/NAME.ppm`
    expect gvar N V            global variable N must be V now
    expect state k=v [k=v...]  the `state` line must contain these (map= mapIndex= elev=
                               dudeTile= center= time= combat= dialog=); k!=v, k>n and k<n
                               also work (time>302500: the clock has moved on)
    expect obj TILE R TEXT     some object within R hexes of TILE has TEXT in its
                               `objects` line (e.g. pid=0x00000214, name=Footlocker)
    expect noobj TILE R TEXT   ... no object has
    expect msg TEXT            the run's debug.log contains TEXT somewhere: a line of the message
                               window (display_msg, combat lines, "You see ...") as printed. Judged
                               at the end over the WHOLE run, wherever the line stands in the file
    expect nomsg TEXT          ... does not contain it

  Typical lines:  dude @SIMMS/3      (teleport next to Simms)
                  talk @SIMMS        (open his dialogue; then `key 1`, `key 2` pick options)
                  setgvar $GVAR_MG_BOMB $MG_BOMB_DISARMED
                  expect gvar $GVAR_MG_Q_SIMMS $MG_Q_SIMMS_DISARMED
                  shot 03-reward
  Waits are real milliseconds: give dialogue 1500-2500 ms to open, a walk about
  250 ms per hex, a map change 6000-8000 ms.

  Driving the interface (coordinates are screen pixels, so keep such tests at the
  default 640x480; tests/foundation/*.txt are worked examples):
    key 1 .. key 9       pick a dialogue option; key i inventory, key p Pip-Boy, key tab automap
    key 318 / 319        F4 save screen / F5 load screen (key enter confirms)
    key 500 / 501        Pip-Boy STATUS / AUTOMAPS; key 507, 508, ... = its first, second, ... line
    click 360 440        the active-item button: attack cursor, or "use on" cursor for a key in hand
    movetile T, rclick, clicktile T 0 -8     open the container on tile T (rclick again afterwards)
    move X Y, press 1, wait 1200, move X Y+40, press 0     hold the button: action menu, second entry
    click 237 181        on the world map: the party marker while it stands on Megaton (enters the town)
  `key esc` in the game itself opens the options menu and pauses everything: only use
  it to close a screen you know is open. `key a` starts combat.

Conventions for a group's tests: tests/<group>/stage.py (optional stage),
tests/<group>/<scenario>.txt (step files), tests/<group>/scripts/ (optional
stand-ins, named by the stage file's SCRIPTS_DIR).
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

BUILD_STEPS = ["ids", "data", "protos", "art", "scripts", "maps", "lint", "pack"]
SPOTS_FILE = ".spots.json"
DEFINE = re.compile(r"#define\s+(\w+)\s+\((-?\d+|0x[0-9A-Fa-f]+)(?:\s*\+\s*(\d+))?\)")


def find(path):
    """A path as given, or relative to mod/megaton/."""
    for candidate in (path, os.path.join(HERE, path)):
        if os.path.exists(candidate):
            return os.path.abspath(candidate)
    raise SystemExit(f"test: no such file: {path}")


def load_defines():
    """{NAME: int} from the generated ids.h and the numeric defines of megaton.h."""
    values = {}
    for name in ("ids.h", "megaton.h"):
        with open(os.path.join(HERE, "scripts", name)) as f:
            for line in f:
                match = DEFINE.match(line)
                if match:
                    values[match.group(1)] = int(match.group(2), 0) + int(match.group(3) or 0)
    return values


def load_spots(out_dir):
    """{NAME: tile}: what the stage wrote, else the town's own spots."""
    path = os.path.join(out_dir, SPOTS_FILE)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    from layout import spots

    return {name: hy * 200 + hx for name, (hx, hy, _) in spots.SPOTS.items()}


def translate(text, spots, defines):
    """Step file text -> (autotest script, [expectation dicts])."""
    from f2lib import geometry

    def spot(match):
        name = match.group(1)
        if name not in spots:
            raise SystemExit(f"test: unknown spot @{name}")
        tile = spots[name]
        if match.group(2) is not None:
            tile = geometry.tile_in_direction(tile, int(match.group(2)), int(match.group(3) or 1))
        return str(tile)

    def define(match):
        if match.group(1) not in defines:
            raise SystemExit(f"test: unknown name ${match.group(1)} (not in ids.h / megaton.h)")
        return str(defines[match.group(1)])

    lines = []
    expectations = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        words = line.split()
        if words[:2] in (["expect", "msg"], ["expect", "nomsg"]) and len(words) > 2:
            # literal text, before any name is looked up: "$300" or "@" in it mean themselves
            expectations.append(dict(kind=words[1], want=line.split(None, 2)[2], line=number, text=raw.strip()))
            continue
        line = re.sub(r"@(\w+)(?:/([0-5])(?:/(\d+))?)?", spot, line)
        line = re.sub(r"\$(\w+)", define, line)
        words = line.split()
        if words[0] == "shot" and len(words) == 2 and "/" not in words[1] and "." not in words[1]:
            line = f"shot shots/{words[1]}.ppm"
        elif words[0] == "expect":
            kind = words[1] if len(words) > 1 else ""
            index = len(expectations)
            if kind == "gvar" and len(words) == 4:
                probe = f"gvar {words[2]}"
                want = words[3]
            elif kind == "state" and len(words) > 2:
                probe = "state"
                want = words[2:]
            elif kind in ("obj", "noobj") and len(words) >= 5:
                probe = f"objects {words[2]} {words[3]}"
                want = " ".join(words[4:])
            else:
                raise SystemExit(f"test: line {number}: cannot parse `{raw.strip()}`")
            expectations.append(dict(kind=kind, want=want, line=number, text=raw.strip()))
            lines += [f"log EXPECT {index} BEGIN", probe, f"log EXPECT {index} END"]
            continue
        lines.append(line)
    return "\n".join(lines) + "\n", expectations


def _state_key(want):
    return re.split(r"!=|>|<|=", want, maxsplit=1)[0]


def _state_holds(fields, want):
    """One `expect state` term: key=value, key!=value, key>number or key<number."""
    match = re.fullmatch(r"(\w+)(!=|>|<|=)(.*)", want)
    if not match:
        return False
    key, how, value = match.groups()
    got = fields.get(key)
    if how == "=":
        return got == value
    if how == "!=":
        return got is not None and got != value
    try:
        return int(got) > int(value) if how == ">" else int(got) < int(value)
    except (TypeError, ValueError):
        return False


def check(expectations, log_lines, messages=""):
    """Compare the probes' output with what the step file expected; returns [(ok, message)].
    `messages` is the text of the run's debug.log (for `expect msg` / `expect nomsg`)."""
    results = []
    for index, expectation in enumerate(expectations):
        if expectation["kind"] in ("msg", "nomsg"):
            found = expectation["want"] in messages
            ok = found == (expectation["kind"] == "msg")
            results.append((ok, f"line {expectation['line']}: {expectation['text']}  -> {'printed' if found else 'not printed'}"))
            continue
        try:
            begin = log_lines.index(f"[autotest] EXPECT {index} BEGIN")
            end = log_lines.index(f"[autotest] EXPECT {index} END")
        except ValueError:
            results.append((False, f"line {expectation['line']}: {expectation['text']}  -> never reached"))
            continue
        output = log_lines[begin + 1:end]
        kind, want = expectation["kind"], expectation["want"]
        if kind == "gvar":
            got = output[0].rsplit("=", 1)[-1].strip() if output else "?"
            ok = got == want
            seen = f"is {got}"
        elif kind == "state":
            fields = dict(part.split("=", 1) for part in " ".join(output).split() if "=" in part)
            missing = [w for w in want if not _state_holds(fields, w)]
            ok = not missing
            seen = " ".join(f"{_state_key(w)}={fields.get(_state_key(w))}" for w in want)
        else:
            hits = [line for line in output if want in line]
            ok = bool(hits) == (kind == "obj")
            seen = f"{len(hits)} of {len(output)} objects match"
        results.append((ok, f"line {expectation['line']}: {expectation['text']}  -> {seen}"))
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", required=True, help="who is testing: names the staging dir out-<group> and the run mg-<group>-...")
    ap.add_argument("--steps", required=True, help="step file (path, or relative to mod/megaton/)")
    ap.add_argument("--stage", help="stage file with build_maps(out_dir); without it the real town is built")
    ap.add_argument("--only", help="comma-separated script stems: compile only these (list megaton too if the map script is needed)")
    ap.add_argument("--res", default="640x480", help="game resolution WxH (default 640x480)")
    ap.add_argument("--art-cache-size", type=int, default=24, metavar="MB",
                    help="run-local art cache, 1..64 MB (default: 24 for Megaton's custom art)")
    ap.add_argument("--ddraw", action="append", default=[], help="extra ddraw.ini [Misc] line, e.g. PipBoyAvailableAtGameStart=1")
    ap.add_argument("--map", default="megaton.map", help="starting map; `default` = a normal new game (Temple of Trials)")
    ap.add_argument("--timeout", type=int, default=240, help="seconds before the engine is killed (default 240)")
    ap.add_argument("--load-wait", type=int, default=5000, help="ms between starting the game and the first step")
    ap.add_argument("--skip-movies", type=int, default=None,
                    help="movies to dismiss before the first step (default: 1 when the game starts on megaton.map, where "
                         "megaton.ssl plays the Vault-suit movie before it hands out the starting kit; else 0)")
    ap.add_argument("--no-build", action="store_true", help="reuse out-<group>/patch001.dat as it is")
    ap.add_argument("--allow-errors", action="store_true", help="do not fail on ERROR lines in debug.log (still printed)")
    args = ap.parse_args()
    if not 1 <= args.art_cache_size <= 64:
        ap.error("--art-cache-size must be from 1 to 64 MB")

    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args.group):
        raise SystemExit("test: --group must be a plain lower-case name (it becomes a directory name)")
    out_dir = os.path.join(HERE, f"out-{args.group}")
    steps_path = find(args.steps)
    run_name = f"mg-{args.group}-{os.path.splitext(os.path.basename(steps_path))[0]}"
    run_dir = os.path.join(ROOT, "run", run_name)

    if not args.no_build:
        shutil.rmtree(out_dir, ignore_errors=True)
        command = [sys.executable, os.path.join(HERE, "build.py"), "--out", out_dir]
        if args.stage:
            command += ["--stage", find(args.stage)]
        if args.only:
            command += ["--only", args.only]
        print("== build:", " ".join(os.path.relpath(c, ROOT) if os.path.isabs(c) else c for c in command[1:] + BUILD_STEPS), flush=True)
        status = subprocess.run(command + BUILD_STEPS, cwd=ROOT).returncode
        if status != 0:
            print(f"== RESULT: FAIL (build failed with status {status})")
            return status
    patch = os.path.join(out_dir, "patch001.dat")
    if not os.path.exists(patch):
        print(f"== RESULT: FAIL ({os.path.relpath(patch, ROOT)} does not exist)")
        return 1

    with open(steps_path) as f:
        script, expectations = translate(f.read(), load_spots(out_dir), load_defines())
    os.makedirs(out_dir, exist_ok=True)
    translated = os.path.join(out_dir, ".steps.txt")
    with open(translated, "w") as f:
        f.write(script)

    command = [sys.executable, os.path.join(ROOT, "tools", "f2test.py"), "--name", run_name, "--fresh",
               "--patch", patch, "--res", args.res, "--debug-log", "--script-messages",
               "--art-cache-size", str(args.art_cache_size),
               "--timeout", str(args.timeout), "--load-wait", str(args.load_wait), "--steps", translated]
    if args.map != "default":
        command += ["--map", args.map]
    skip_movies = args.skip_movies if args.skip_movies is not None else (1 if args.map == "megaton.map" else 0)
    if skip_movies:
        command += ["--skip-movies", str(skip_movies)]
    for line in args.ddraw:
        command += ["--ddraw", line]
    print(f"== run: {run_name} ({os.path.relpath(steps_path, ROOT)}, {args.res}"
          + (f", ddraw {' '.join(args.ddraw)}" if args.ddraw else "") + ")", flush=True)
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    log_lines = result.stdout.splitlines()

    print("== autotest log")
    for line in log_lines:
        if line.startswith("[autotest]") and " EXPECT " not in line:
            print("  " + line)

    failures = []
    if result.returncode == 124:
        failures.append(f"engine timed out after {args.timeout}s")
    elif result.returncode != 0:
        failures.append(f"engine exit code {result.returncode}")
    other = [line for line in log_lines if not line.startswith("[autotest]") and not line.startswith("[f2test]")]
    if other:
        print("== engine output")
        for line in other:
            print("  " + line)

    debug_log = os.path.join(run_dir, "debug.log")
    errors = []
    messages = ""
    if os.path.exists(debug_log):
        with open(debug_log, errors="replace") as f:
            messages = f.read().replace("\r", "\n")
        errors = [line.strip() for line in messages.split("\n") if "ERROR" in line or "Error" in line]
    print(f"== debug.log errors: {len(errors)}  ({os.path.relpath(debug_log, ROOT)})")
    for line in errors:
        print("  " + line)
    if errors and not args.allow_errors:
        failures.append(f"{len(errors)} error line(s) in debug.log")

    if expectations:
        print("== expectations")
        for ok, message in check(expectations, log_lines, messages):
            print(f"  {'ok  ' if ok else 'FAIL'} {message}")
            if not ok:
                failures.append(message)

    shots = sorted(glob.glob(os.path.join(run_dir, "shots", "*.png")))
    print(f"== screenshots: {len(shots)}")
    for shot in shots:
        print("  " + shot)

    if failures:
        print("== RESULT: FAIL")
        for failure in failures:
            print("  " + failure)
        return result.returncode or 1
    print("== RESULT: PASS" + (f" ({len(expectations)} expectations)" if expectations else " (no expectations: look at the screenshots)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
