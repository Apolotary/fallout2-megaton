"""``.gam`` variable files (``maps/<map>.gam``, ``data/vault13.gam``).

Grammar as implemented by globalVarsRead (game.cc:1044-1100): lines are
skipped until one starting with the section tag (``MAP_GLOBAL_VARS:`` or
``GAME_GLOBAL_VARS:``); every following line that is not empty and does not
start with ``//`` declares one variable; text after ``;`` is dropped and the
value is the integer after the first ``=`` (0 when there is none). Retail
files write ``NAME   :=value;``.

For a pristine map the engine replaces the map's global variables by the
.gam contents, so the map header must hold at least as many variables.
"""
import re

MAP_SECTION = "MAP_GLOBAL_VARS:"
GAME_SECTION = "GAME_GLOBAL_VARS:"


def parse(data, section=MAP_SECTION):
    """bytes -> [(name, value)] in file order."""
    variables = []
    inside = False
    for line in data.decode("latin-1").split("\n"):
        line = line.rstrip("\r")
        if not inside:
            inside = line.startswith(section)
            continue
        if line == "" or line.startswith("//"):
            continue
        line = line.split(";", 1)[0]
        name, equals, value = line.partition("=")
        number = re.match(r"\s*[+-]?\d+", value) if equals else None
        variables.append((name.rstrip(" \t:"), int(number.group()) if number else 0))
    return variables


def serialise(variables, section=MAP_SECTION):
    """[(name, value)] -> bytes in the retail layout."""
    lines = [section, ""]
    lines += [f"{name:<24}:={value};" for name, value in variables]
    return ("\r\n".join(lines) + "\r\n").encode("latin-1")
