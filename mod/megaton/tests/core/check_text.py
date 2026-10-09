#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Measure dialogue text the way the engine lays it out, and flag what will not fit.

    python3 mod/megaton/tests/core/check_text.py                    (the core scripts' .msg files)
    python3 mod/megaton/tests/core/check_text.py scripts/mgmoira.msg ...

The conversation screen is the same 640x480 picture at every resolution. An
NPC's reply is wrapped to 369 pixels in the game's dialogue font (font1.aaf)
and the window shows the lines that fit into 48 pixels; a longer reply is
paged (it moves on after ten seconds, or when the reply box is clicked), which
a player on a phone will not guess. An option is wrapped to 379 pixels after
its bullet; the option window holds what fits into 107 pixels.

This script wraps every entry numbered 200 and up (the conversation text, by
this mod's convention) exactly like word_wrap.cc does and prints the entries
that need more lines than the reply window shows (four). It cannot know which
entries are replies and which are options or message-window text, so read its
output with the script in hand; entries listed in a file's own
`# long-ok: 340 341 ...` comment line are skipped (text that is only ever
shown in the message window).

For the core scripts it also compares the line numbers each .ssl uses
(Reply, the option macros, show, floater..., mstr, giq_option with NAME) with
its .msg: a number used but missing is an error (the engine prints "Error"
in its place), a line nobody uses is reported too.

Exit status 1 when something is flagged.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(MOD))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from f2lib import GameFiles
FONT = None

REPLY_WIDTH = 369
REPLY_HEIGHT = 48
CORE = ["megaton", "mgweld", "mgsimms", "mgburke", "mgbomb", "mgharden", "mghitman",
        "mgspgate", "mgsprad", "mggate", "mghouse"]


class Font:
    def __init__(self, path):
        if path is None:
            data = GameFiles().read("font1.aaf")
        else:
            with open(path, "rb") as f:
                data = f.read()
        assert data[:4] == b"AAFF", "not an AAF font"
        self.max_height, self.gap, self.space, self.line_gap = struct.unpack(">4H", data[4:12])
        self.widths = [struct.unpack(">H", data[12 + 8 * i:14 + 8 * i])[0] for i in range(256)]
        self.widths[32] = self.space
        self.line_height = self.max_height + self.line_gap

    def char(self, c):
        return self.widths[ord(c) & 0xFF] + self.gap

    def width(self, text):
        return sum(self.char(c) for c in text)

    def wrap(self, text, width):
        """Lines as word_wrap.cc breaks them."""
        if self.width(text) < width:
            return [text]
        lines = []
        start = 0
        accum = 0
        last_break = None
        i = 0
        while i < len(text):
            accum += self.char(text[i])
            if accum <= width:
                if text[i].isspace() or text[i] == "-":
                    last_break = i
            else:
                if last_break is not None:
                    lines.append(text[start:last_break + 1])
                    start = last_break + 1
                    i = last_break
                else:
                    lines.append(text[start:i])
                    start = i
                    i -= 1
                last_break = None
                accum = 0
            i += 1
        lines.append(text[start:])
        return lines


def entries(path):
    with open(path, encoding="latin-1") as f:
        text = f.read()
    allowed = set()
    for line in text.splitlines():
        if line.startswith("#") and "long-ok:" in line:
            allowed.update(int(n) for n in re.findall(r"\d+", line.split("long-ok:", 1)[1]))
    found = [(int(m.group(1)), m.group(2)) for m in re.finditer(r"^\{(\d+)\}\{[^}]*\}\{([^}]*)\}", text, re.M)]
    return found, allowed


USES = re.compile(r"\b(Reply|NOption|GOption|BOption|NLowOption|GLowOption|BLowOption|EndOption|NMessage|GMessage|BMessage|"
                  r"show|floater|floater_color|floater_random|mstr|Act)\(\s*(\d+)(?:\s*,\s*(\d+))?")
GIQ = re.compile(r"giq_option\(\s*-?\d+\s*,\s*NAME\s*,\s*(\d+)")
RANDOM = re.compile(r"random\(\s*(\d{3})\s*,\s*(\d{3})\s*\)")


def references(stem):
    """(numbers the script uses but the .msg lacks, .msg lines below 900 the script never uses)."""
    with open(os.path.join(MOD, "scripts", stem + ".ssl"), encoding="latin-1") as f:
        source = re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", f.read(), flags=re.S))
    used = set()
    for match in USES.finditer(source):
        used.add(int(match.group(2)))
        if match.group(1) == "floater_random" and match.group(3):
            used.update(range(int(match.group(2)), int(match.group(3)) + 1))
    used.update(int(match.group(1)) for match in GIQ.finditer(source))
    for match in RANDOM.finditer(source):
        first, last = int(match.group(1)), int(match.group(2))
        if 100 <= first < last < 900:
            used.update(range(first, last + 1))
    path = os.path.join(MOD, "scripts", stem + ".msg")
    have = {number for number, _ in entries(path)[0]} if os.path.exists(path) else set()
    return sorted(used - have), sorted(number for number in have - used if number < 900)


def main():
    font = Font(FONT)
    fit = REPLY_HEIGHT // font.line_height
    paths = sys.argv[1:] or [os.path.join(MOD, "scripts", stem + ".msg") for stem in CORE]
    flagged = 0
    longest = 0
    for path in paths:
        if not os.path.exists(path):
            path = os.path.join(MOD, path)
        found, allowed = entries(path)
        for number, text in found:
            if number < 200 or number >= 900 or number in allowed:
                continue
            lines = font.wrap(text, REPLY_WIDTH)
            longest = max(longest, len(lines))
            if len(lines) > fit:
                flagged += 1
                print(f"{os.path.basename(path)} {{{number}}}: {len(lines)} lines, {len(text)} characters")
                for line in lines:
                    print("    | " + line)
    print(f"font line height {font.line_height} px: a reply shows {fit} lines; longest entry checked: {longest} lines; "
          f"{flagged} entr{'y' if flagged == 1 else 'ies'} too long")
    if not sys.argv[1:]:
        for stem in CORE + ["mgspsims"]:
            missing, unused = references(stem)
            if missing or unused:
                flagged += 1
                print(f"{stem}: used but not in the .msg: {missing}; in the .msg but never used: {unused}")
        print("message numbers: every line a core script uses exists" if not flagged else "message numbers: see above")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
