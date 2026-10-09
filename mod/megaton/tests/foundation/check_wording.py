#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Check live dialogue and art sources for retired wording, without building.

    python3 mod/megaton/tests/foundation/check_wording.py

Includes comments and metadata. Generated art, snapshots, and historical renders
are excluded; their pixels are checked separately after the signs are rendered.
Also joins literal sx.letters calls so separate sign rows cannot hide a phrase.
"""
import ast
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[4]
TEXT_SUFFIXES = {".py", ".json", ".msg", ".ssl", ".h", ".md", ".txt"}
GENERATED_DIRS = {"build", "out", "__pycache__", "snapshot", "data"}
RETIRED = (("retired bomb reassurance", "perfectlysafe"),
           ("retired promise", "wepromise"))
WELCOME = "Howdy, traveller. Megaton welcomes you. Please be advised: the bomb has not gone off."
BOARD_ROWS = ["DAYS WITHOUT", "A DETONATION", "ALL OF THEM"]


def phrase_hits(text):
    """Return category and source line; punctuation and syllable breaks do not count."""
    # Preserve character positions when removing escaped line breaks in source.
    plain = re.sub(r"\\(?:[nrt]|x(?:0a|0d|09))", lambda m: " " * len(m[0]), text.lower())
    letters = list(re.finditer(r"[a-z]", plain))
    compact = "".join(m[0] for m in letters)
    hits = []
    for label, phrase in RETIRED:
        for match in re.finditer(phrase, compact):
            offset = letters[match.start()].start()
            hits.append((label, text.count("\n", 0, offset) + 1))
    return hits


def sources(folder):
    for directory, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in GENERATED_DIRS
                         and not d.startswith(".") and not Path(directory, d).is_symlink())
        for name in sorted(files):
            path = Path(directory, name)
            if path.suffix.lower() in TEXT_SUFFIXES and not path.is_symlink():
                yield path


def lettering(source):
    """Function name -> literal sign rows in source order, plus their line numbers."""
    tree = ast.parse(source)
    found = {}
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls = sorted((node for node in ast.walk(function)
                        if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "sx" and node.func.attr == "letters"),
                       key=lambda node: (node.lineno, node.col_offset))
        if calls:
            found[function.name] = [
                (node.args[0].value if node.args and isinstance(node.args[0], ast.Constant)
                 and isinstance(node.args[0].value, str) else None, node.lineno)
                for node in calls]
    return found


def check(root=ROOT):
    failures = []
    checked = 0
    script_dir = root / "mod/megaton/scripts"
    art_dirs = [root / "mod/megaton-art"]
    for folder in [script_dir] + art_dirs:
        if not folder.is_dir():
            failures.append(f"{folder.relative_to(root)}: missing source directory")
            continue
        for path in sources(folder):
            relative = path.relative_to(root)
            raw = path.read_bytes()
            try:
                source = raw.decode("utf-8")
            except UnicodeDecodeError:
                source = raw.decode("latin-1")
            checked += 1
            failures.extend(f"{relative}:{line}: {label}" for label, line in phrase_hits(source))
            if path.suffix == ".py" and folder in art_dirs:
                try:
                    signs = lettering(source)
                except SyntaxError as exc:
                    failures.append(f"{relative}:{exc.lineno}: invalid Python art source")
                    continue
                for name, rows in signs.items():
                    text = " ".join(value or "" for value, _ in rows)
                    failures.extend(f"{relative}:{rows[0][1]}: {label} in {name} lettering"
                                    for label, _ in phrase_hits(text))
                    if name == "sg_bomb_notice" and [value for value, _ in rows] != BOARD_ROWS:
                        failures.append(f"{relative}:{rows[0][1]}: bomb notice rows differ from approved wording")
        sign_path = folder / "pieces/signs/sg_signs.py"
        if folder in art_dirs and sign_path.is_file():
            try:
                if "sg_bomb_notice" not in lettering(sign_path.read_text(encoding="utf-8")):
                    failures.append(f"{sign_path.relative_to(root)}: bomb notice lettering is missing")
            except (UnicodeDecodeError, SyntaxError):
                pass  # Reported with the other art source checks above.
        elif folder in art_dirs:
            failures.append(f"{sign_path.relative_to(root)}: bomb notice source is missing")

    weld = script_dir / "mgweld.msg"
    if weld.is_file():
        entries = dict((int(m[1]), m[2]) for m in re.finditer(
            r"^\{(\d+)\}\{[^}]*\}\{([^}]*)\}", weld.read_text(encoding="latin-1"), re.M))
        for number in (110, 200):
            if entries.get(number) != WELCOME:
                failures.append(f"mod/megaton/scripts/mgweld.msg {{{number}}}: approved greeting differs")
        for number in (111, 115, 201, 233):
            if "the bomb has been disarmed" not in entries.get(number, "").lower():
                failures.append(f"mod/megaton/scripts/mgweld.msg {{{number}}}: missing disarmed state")
    else:
        failures.append("mod/megaton/scripts/mgweld.msg: missing greeting source")
    return checked, failures


def main():
    checked, failures = check()
    for failure in failures:
        print(failure)
    print(f"Wording: {checked} source files checked; {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
