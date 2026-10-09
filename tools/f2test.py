#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Run an explicitly selected native fallout2-ce test build headlessly with a scripted test.

Creates an isolated run directory under run/<name>/ (game archives are
symlinked, everything else is private to the run), starts a new game on the
requested map, executes autotest steps (see engine/README.md)
and converts screenshots to PNG.

    tools/f2test.py --name smoke --map artemple.map --steps steps.txt
    tools/f2test.py --name megaton --map megaton.map --patch mod/out/patch001.dat \
        --res 1280x960 --steps mod/tests/walkaround.txt

Step files contain autotest commands; paths in `shot` commands are relative to
the run directory (use shots/NAME.ppm; a PNG is written next to each PPM).
Unless --raw is given, the steps run after the standard "new game, take the
first premade character, skip the intro movie" prologue, i.e. in-game. For maps
that start with a movie of their own, --skip-movies N appends N extra
"key space, wait 1500" pairs to the prologue (one per movie to skip; default 0).

Autotest commands (one per line, '#' comments):
    wait <ms> | key <char|esc|enter|space|tab|code> | move <x> <y>
    click <x> <y> | rclick [<x> <y>] | clicktile <tile> [dx dy] | movetile <tile>
    shot <file.ppm> | center <tile> | dude <tile> | state | objects <tile> <radius>
    talk <tile> | use <tile> | skill <skill#> <tile> | gvar <n> | setgvar <n> <v>
    log <text> | quit [code]
"""
import argparse
import glob
import json
from pathlib import Path
import re
import uuid
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# An embedding caller may set ENGINE; the CLI requires F2_ENGINE.
ENGINE = None
ARCHIVES = ("master.dat", "critter.dat", "patch000.dat")


def select_engine():
    choice = os.environ.get("F2_ENGINE") if "F2_ENGINE" in os.environ else ENGINE
    if not choice or not str(choice).strip():
        raise ValueError("Set F2_ENGINE to the executable built with engine/fallout2-ce-autotest.patch.")
    path = Path(choice).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("F2_ENGINE must identify an existing executable file.")
    return path


def selected_source(explicit=None):
    choice = explicit or os.environ.get("FALLOUT2_DIR")
    if not choice:
        state = Path(ROOT) / "game/.source.json"
        if state.is_symlink():
            raise ValueError("The remembered game settings must not be a symbolic link.")
        try:
            value = json.loads(state.read_text(encoding="utf-8"))
            choice = value.get("source") if isinstance(value, dict) else None
        except FileNotFoundError:
            pass
    if not isinstance(choice, str) or not choice.strip():
        raise ValueError("Select the original archive folder with --game, FALLOUT2_DIR or megaton.py setup.")
    path = Path(choice).expanduser().resolve()
    if not path.is_dir():
        raise ValueError("The selected original archive folder does not exist.")
    return path


def case_child(directory, name, *, kind="file", required=True):
    matches = [p for p in Path(directory).iterdir() if p.name.casefold() == name.casefold()]
    if len(matches) > 1:
        raise ValueError("Game input contains ambiguous names differing only in letter case.")
    if not matches:
        if required:
            raise ValueError("Native tests need the original archives and fallout2.cfg; an extracted-only tree is insufficient.")
        return None
    path = matches[0]
    if path.is_symlink() or not (path.is_dir() if kind == "dir" else path.is_file()):
        raise ValueError("Game inputs must have the expected type and must not be symbolic links.")
    return path


def tree_files(directory):
    result = []
    if directory is None:
        return result
    for parent, dirs, files in os.walk(directory, followlinks=False):
        names = dirs + files
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError("Input folder contains ambiguous names differing only in letter case.")
        for name in names:
            path = Path(parent) / name
            if path.is_symlink() or (name in files and not path.is_file()):
                raise ValueError("Input folders must not contain symbolic links or special files.")
        result.extend((Path(parent) / name) for name in files)
    return result


def prepare_inputs(args):
    source = selected_source(getattr(args, "game", None))
    archives = [case_child(source, name) for name in ARCHIVES]
    config = case_child(source, "fallout2.cfg")
    sound = case_child(source, "sound", kind="dir", required=False)
    sounds = tree_files(sound)
    patches = [Path(p).expanduser().resolve() for p in args.patch]
    if len(patches) > 9 or any(not p.is_file() for p in patches):
        raise ValueError("Use at most nine existing mod patch files.")
    overlay = Path(args.overlay).expanduser().resolve() if args.overlay else None
    if overlay is not None and not overlay.is_dir():
        raise ValueError("The overlay folder does not exist.")
    tree_files(overlay)
    if not re.fullmatch(r"[1-9][0-9]{1,4}x[1-9][0-9]{1,4}", args.res):
        raise ValueError("Resolution must be WIDTHxHEIGHT.")
    with config.open(encoding="latin-1", newline="") as stream:
        cfg = stream.read()
    return source, archives, sound, sounds, patches, overlay, cfg


def no_output_links(path):
    path = Path(os.path.abspath(path))
    for item in [path, *path.parents]:
        if item.is_symlink():
            raise ValueError("Run output paths must not be symbolic links.")
    return path


def retained(path):
    path = no_output_links(path)
    if path.exists():
        target = path.with_name(path.name + ".previous-" + uuid.uuid4().hex)
        path.rename(target)
        return target
    return None


def configure_run(cfg, args):
    # Keep every writable loose-data path inside the run, even when the source
    # config was installed with absolute paths or platform-specific casing.
    updates = {"system": {"master_dat": "master.dat", "critter_dat": "critter.dat",
                           "master_patches": "data", "critter_patches": "data"},
               "sound": {"music_path1": "sound/music/", "music_path2": "sound/music/"}}
    if args.debug_log or args.script_messages:
        updates["debug"] = {"mode": "log"}
    if args.script_messages:
        updates["debug"]["show_script_messages"] = "1"
    newline = "\r\n" if "\r\n" in cfg else "\n"
    rows, section, seen_sections = [], "", set()
    def flush():
        if section in updates:
            if rows and not rows[-1].endswith("\n"):
                rows[-1] += newline
            rows.extend(f"{k}={v}{newline}" for k, v in updates[section].items())
            updates[section].clear()
    for line in cfg.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and "]" in stripped:
            flush()
            section = stripped[1:stripped.index("]")].strip().lower()
            if section in seen_sections and section in updates:
                raise ValueError("Game configuration contains duplicate managed sections.")
            seen_sections.add(section)
        key = stripped.split("=", 1)[0].strip().lower() if "=" in stripped else None
        if key is not None and section in updates and key in updates[section]:
            continue
        rows.append(line)
    flush()
    for section_name, values in updates.items():
        if values:
            if rows and not rows[-1].endswith("\n"):
                rows[-1] += newline
            rows.append(f"[{section_name}]{newline}")
            rows.extend(f"{k}={v}{newline}" for k, v in values.items())
    return configure_art_cache("".join(rows), getattr(args, "art_cache_size", None))


PROLOGUE = """\
wait 3000
key n
wait 2500
key t
wait 2500
key esc
wait {load_wait}
"""

# One more movie to skip: space dismisses it, then give the next screen time.
SKIP_MOVIE = """\
key space
wait 1500
"""


def art_cache_mb(value):
    """Bound an explicit run-local cache override in megabytes."""
    try:
        size = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("art cache must be an integer from 1 to 64 MB") from None
    if not 1 <= size <= 64:
        raise argparse.ArgumentTypeError("art cache must be from 1 to 64 MB")
    return size


def configure_art_cache(cfg, size):
    """Change only [system] in the run's copy, preserving other sections and line endings."""
    if size is None:
        return cfg
    newline = "\r\n" if "\r\n" in cfg else "\n"
    rows, section, found, had_system = [], "", False, False
    for line in cfg.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and "]" in stripped:
            if section == "system" and not found:
                if rows and not rows[-1].endswith("\n"):
                    rows[-1] += newline
                rows.append(f"art_cache_size={size}{newline}")
                found = True
            section = stripped[1:stripped.index("]")].strip().lower()
            had_system |= section == "system"
        if section == "system" and stripped.split("=", 1)[0].strip().lower() == "art_cache_size":
            if not found:
                rows.append(f"art_cache_size={size}{newline}")
                found = True
            continue
        rows.append(line)
    if not found:
        if rows and not rows[-1].endswith("\n"):
            rows[-1] += newline
        if not had_system:
            rows.append(f"[system]{newline}")
        rows.append(f"art_cache_size={size}{newline}")
    return "".join(rows)


def setup(run_dir, args):
    source, archives, sound, sounds, patches, overlay, cfg = prepare_inputs(args)
    run = no_output_links(run_dir)
    if run == source or source in run.parents or run in source.parents:
        raise ValueError("Keep the isolated run folder separate from the original game folder.")
    cfg = configure_run(cfg, args)
    for name in ("shots", "data", "sound", "fallout2.cfg", "f2_res.ini", "ddraw.ini"):
        no_output_links(run / name)
    # Replacing an earlier sound mirror preserves all run-local cached files.
    retained(run / "sound")
    (run / "shots").mkdir(parents=True, exist_ok=True)
    (run / "data").mkdir(parents=True, exist_ok=True)
    (run / "sound/music").mkdir(parents=True, exist_ok=True)
    for name, archive in zip(ARCHIVES, archives):
        link = run / name
        if link.is_symlink():
            if link.resolve() != archive:
                link.rename(run / (name + ".previous-" + uuid.uuid4().hex))
            else:
                continue
        elif link.exists():
            retained(link)
        link.symlink_to(archive)
    for item in sounds:
        relative = item.relative_to(sound)
        link = run / "sound" / str(relative).lower()
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(item)
    for stale in run.iterdir():
        if re.fullmatch(r"patch00[1-9]\.dat", stale.name, flags=re.I):
            stale.rename(run / (stale.name + ".previous-" + uuid.uuid4().hex))
    for index, patch in enumerate(patches, start=1):
        (run / f"patch{index:03d}.dat").symlink_to(patch)
    if overlay:
        # Refuse an existing symlink anywhere the overlay could write through.
        for parent, dirs, files in os.walk(run / "data", followlinks=False):
            for name in dirs + files:
                no_output_links(Path(parent) / name)
        shutil.copytree(overlay, run / "data", dirs_exist_ok=True)
    for name in ("fallout2.cfg", "f2_res.ini", "ddraw.ini"):
        retained(run / name)
    (run / "fallout2.cfg").write_text(cfg, encoding="latin-1", newline="")
    width, height = args.res.split("x")
    (run / "f2_res.ini").write_text(f"[MAIN]\nSCR_WIDTH={width}\nSCR_HEIGHT={height}\nWINDOWED=1\nSCALE_2X=0\n")
    ddraw = "[Misc]\nSkipOpeningMovies=1\n"
    if args.map:
        ddraw += f"StartingMap={args.map}\n"
    ddraw += "".join(line + "\n" for line in args.ddraw)
    (run / "ddraw.ini").write_text(ddraw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="run directory name under run/")
    ap.add_argument("--game", help="original game archive folder (else FALLOUT2_DIR or remembered setup)")
    ap.add_argument("--map", default="", help="starting map file name (e.g. artemple.map)")
    ap.add_argument("--steps", required=True, help="autotest step file")
    ap.add_argument("--patch", action="append", default=[], help="DAT archive mounted as patch001.dat, patch002.dat, ...")
    ap.add_argument("--overlay", help="directory copied into the run's loose data/ folder")
    ap.add_argument("--res", default="640x480", help="game resolution WxH (default 640x480)")
    ap.add_argument("--art-cache-size", type=art_cache_mb, metavar="MB",
                    help="run-local art cache, 1..64 MB (default: preserve the game configuration)")
    ap.add_argument("--raw", action="store_true", help="do not prepend the new-game prologue")
    ap.add_argument("--load-wait", type=int, default=5000, help="ms to wait for the first map after the prologue")
    ap.add_argument("--skip-movies", type=int, default=0, metavar="N", help="append N extra 'key space / wait 1500' pairs to the prologue, for maps that start with a movie (default 0)")
    ap.add_argument("--timeout", type=int, default=120, help="kill the engine after this many seconds")
    ap.add_argument("--ddraw", action="append", default=[], help="extra line for ddraw.ini [Misc]")
    ap.add_argument("--debug-log", action="store_true", help="write the engine's debug.log into the run dir")
    ap.add_argument("--script-messages", action="store_true", help="log scripts' debug_msg() output (implies a debug.log)")
    ap.add_argument("--fresh", action="store_true", help="preserve the previous run directory and start a fresh one")
    args = ap.parse_args()
    if args.skip_movies < 0:
        ap.error("--skip-movies must be >= 0")
    if args.skip_movies and args.raw:
        ap.error("--skip-movies extends the prologue, which --raw omits")

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.name) or args.name in {".", ".."}:
        ap.error("--name must be a single folder name")
    if args.timeout <= 0:
        ap.error("--timeout must be positive")
    selected_engine = select_engine()
    prepared = prepare_inputs(args)
    configure_run(prepared[-1], args)
    with open(args.steps) as f:
        steps = f.read()
    if args.script_messages:
        args.debug_log = True
    run_dir = no_output_links(Path(ROOT) / "run" / args.name)
    source = prepared[0]
    if run_dir == source or source in run_dir.parents or run_dir in source.parents:
        raise ValueError("Keep the isolated run folder separate from the original game folder.")
    if args.fresh:
        retained(run_dir)
    for name in ("autotest.txt", "fallout2-ce", "run.log", "debug.log"):
        no_output_links(run_dir / name)
    setup(run_dir, args)
    for name in ("autotest.txt", "fallout2-ce", "run.log", "debug.log"):
        retained(run_dir / name)
    if not args.raw:
        steps = PROLOGUE.format(load_wait=args.load_wait) + SKIP_MOVIE * args.skip_movies + steps
    if "quit" not in steps.split():
        steps += "\nquit 0\n"
    script_path = os.path.join(run_dir, "autotest.txt")
    with open(script_path, "w") as f:
        f.write(steps)

    for old in glob.glob(os.path.join(run_dir, "shots", "*.p[pn][mg]")):
        retained(old)

    # The engine changes directory to wherever its executable lives (the
    # folder containing the .app when run from a bundle), so run a bare copy
    # from inside the run directory.
    engine = os.path.join(run_dir, "fallout2-ce")
    shutil.copy2(selected_engine, engine)

    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", F2_AUTOTEST=script_path)
    log_path = os.path.join(run_dir, "run.log")
    with open(log_path, "w") as log:
        proc = subprocess.Popen([engine], cwd=run_dir, env=env, stdout=log, stderr=subprocess.STDOUT)
        deadline = time.time() + args.timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.2)
        timed_out = proc.poll() is None
        if timed_out:
            proc.kill()
            proc.wait()

    with open(log_path, errors="replace") as log:
        sys.stdout.write(log.read())

    try:
        from PIL import Image

        for ppm in sorted(glob.glob(os.path.join(run_dir, "shots", "*.ppm"))):
            png = ppm[:-4] + ".png"
            Image.open(ppm).save(png)
            print(f"[f2test] {os.path.relpath(png, ROOT)}")
    except ImportError:
        print("[f2test] PIL not available; screenshots left as .ppm")

    if timed_out:
        print(f"[f2test] TIMEOUT after {args.timeout}s (engine killed)")
        return 124
    print(f"[f2test] engine exit code {proc.returncode}")
    return proc.returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(f"[f2test] {exc}", file=sys.stderr)
        sys.exit(2)
