#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Every script's text, checked without the engine (about a second).

    python3 mod/megaton/tests/integration/check_text.py

Uses the machinery of tests/core/check_text.py on ALL scripts of registry.SCRIPTS:
  - a reply (entries 200..899 of a .msg) must fit the four lines the conversation
    window shows, or the game pages it after ten seconds, which nobody expects;
  - every line number a script uses with a literal (Reply, the option macros, show,
    floater..., mstr, giq_option) must exist in its .msg: the engine prints "Error"
    in place of a missing line;
  - no entry may be empty, hold a placeholder (TODO, TBD, FIXME, XXX, lorem) or a
    doubled space, and the file must not contain a stray brace.
Lines a script never mentions by number are NOT reported here: several scripts pick
theirs through ranges and header macros (mgflav.h).

Exit status 1 when something is flagged.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, MOD)
sys.path.insert(0, os.path.join(MOD, "tests", "core"))

import check_text as core  # noqa: E402  (tests/core/check_text.py)
import registry  # noqa: E402

PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME|XXX|lorem|placeholder)\b", re.I)


def main():
    font = core.Font(core.FONT)
    fit = core.REPLY_HEIGHT // font.line_height
    flagged = 0
    entries_checked = 0
    for stem, _, _ in registry.SCRIPTS:
        source = os.path.join(MOD, "scripts", stem + ".ssl")
        path = os.path.join(MOD, "scripts", stem + ".msg")
        if not os.path.exists(source):
            print(f"{stem}: registered but there is no {stem}.ssl")
            flagged += 1
            continue
        if not os.path.exists(path):
            continue
        with open(path, encoding="latin-1") as f:
            raw = f.read()
        body = "\n".join(line for line in raw.splitlines() if not line.startswith("#"))
        if body.count("{") != body.count("}") or body.count("{") % 3:
            print(f"{stem}.msg: unbalanced braces")
            flagged += 1
        found, allowed = core.entries(path)
        numbers = [number for number, _ in found]
        for number in sorted({n for n in numbers if numbers.count(n) > 1}):
            print(f"{stem}.msg {{{number}}}: defined twice")
            flagged += 1
        for number, text in found:
            entries_checked += 1
            if not text.strip() or PLACEHOLDER.search(text) or "  " in text:
                print(f"{stem}.msg {{{number}}}: empty, placeholder or doubled space: {text!r}")
                flagged += 1
            if 200 <= number < 900 and number not in allowed:
                lines = font.wrap(text, core.REPLY_WIDTH)
                if len(lines) > fit:
                    print(f"{stem}.msg {{{number}}}: {len(lines)} lines in the reply window (it shows {fit})")
                    flagged += 1
        missing, _ = core.references(stem)
        if missing:
            print(f"{stem}.ssl uses lines its .msg lacks: {missing}")
            flagged += 1
    print(f"{entries_checked} entries of {len(registry.SCRIPTS)} scripts checked: " + ("ok" if not flagged else f"{flagged} problem(s)"))
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
