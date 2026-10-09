"""``.lst`` files: line number <-> name.

Index bases differ and are easy to get wrong (all verified against the engine
and the retail data, research/05 section 7):

    art/<type>/<type>.lst       FID index   0-based   art.cc:671-710
    proto/<type>/<type>.lst     PID index   1-based   proto.cc:201-248
    scripts/scripts.lst         Script.index and proto sid: 0-based;
                                MapHeader.scriptIndex and script opcodes: 1-based

The engine replaces a list as a whole file, so a mod ships the complete
vanilla list plus appended lines (`append_lines`); never insert or reorder.
"""
import re
from collections import namedtuple


def split_lines(data):
    """Lines as the engine reads them: a final newline does not add an empty entry."""
    lines = data.decode("latin-1").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line.rstrip("\r") for line in lines]


def art_names(data):
    """art list -> file names; a line is cut at the first of ' ,;\\t' and 12 characters are kept."""
    names = []
    for line in split_lines(data):
        for separator in " ,;\t":
            line = line.split(separator)[0]
        names.append(line[:12])
    return names


def proto_names(data):
    """proto list -> file names (cut at the first space)."""
    return [line.split(" ")[0] for line in split_lines(data)]


def append_lines(data, lines):
    """Return list bytes with `lines` appended, keeping the file's newline style."""
    newline = b"\r\n" if b"\r\n" in data or not data else b"\n"
    out = bytearray(data)
    if out and not out.endswith(b"\n"):
        out += newline
    for line in lines:
        out += line.encode("latin-1") + newline
    return bytes(out)


class NameList:
    """Names of one list with its index base (0 for art, 1 for protos)."""

    def __init__(self, names, base):
        self.names = list(names)
        self.base = base
        self._index = {}
        for i, name in enumerate(self.names):
            self._index.setdefault(name.lower(), i + base)

    def __len__(self):
        return len(self.names)

    def __iter__(self):
        return iter(self.names)

    def indices(self):
        return range(self.base, self.base + len(self.names))

    def name(self, index):
        """Name at `index`, or None when out of range."""
        i = index - self.base
        return self.names[i] if 0 <= i < len(self.names) else None

    def index(self, name):
        """First index of `name` (case-insensitive); raises KeyError when absent."""
        try:
            return self._index[name.lower()]
        except KeyError:
            raise KeyError(f"{name!r} is not in the list") from None

    def find(self, name):
        return self._index.get(name.lower())

    @property
    def next_index(self):
        """Index a newly appended line would get."""
        return self.base + len(self.names)


ScriptEntry = namedtuple("ScriptEntry", "name local_vars line")


class ScriptList:
    """scripts/scripts.lst: ``name.int  ; comment  # local_vars=N`` (scripts.cc:1374-1420).

    `index(name)` is 0-based (Script.index, Object.scriptIndex, proto sid);
    add 1 for MapHeader.scriptIndex and for script source constants.
    """

    def __init__(self, data):
        self.entries = []
        for line in split_lines(data):
            cut = line.find(".int")
            name = line[:cut] if cut >= 0 else ""
            local_vars = 0
            if "#" in line and "local_vars=" in line:
                number = re.match(r"\s*[+-]?\d+", line.split("local_vars=", 1)[1])
                local_vars = int(number.group()) if number else 0
            self.entries.append(ScriptEntry(name, local_vars, line))
        self._index = {}
        for i, entry in enumerate(self.entries):
            self._index.setdefault(entry.name.lower(), i)

    def __len__(self):
        return len(self.entries)

    def name(self, index):
        return self.entries[index].name if 0 <= index < len(self.entries) else None

    def index(self, name):
        key = name.lower()
        if key.endswith(".int"):
            key = key[:-4]
        try:
            return self._index[key]
        except KeyError:
            raise KeyError(f"script {name!r} is not in scripts.lst") from None

    def find(self, name):
        try:
            return self.index(name)
        except KeyError:
            return None

    @staticmethod
    def format_line(name, comment="", local_vars=0):
        """One list line in the retail column layout.

        Refuses what the engine cannot take: a name that does not fit its
        ``char[16]`` file-name buffer together with ".int" (11 characters; a
        name over 13 makes the whole list fail to load), a line over 259
        bytes (it would be read as two entries and shift every later index)
        and a comment that the local_vars scan would trip over.
        """
        if name.lower().endswith(".int"):
            name = name[:-4]
        if not 1 <= len(name) <= 11 or any(c in name for c in " \t.;#"):
            raise ValueError(f"script name {name!r} must be 1..11 characters without spaces, '.', ';' or '#'")
        if "local_vars=" in comment or "#" in comment or "\n" in comment or "\r" in comment:
            raise ValueError("the comment must not contain '#', 'local_vars=' or line breaks")
        line = f"{name + '.int':<16}; {comment:<46}# local_vars={int(local_vars)}"
        if len(line.encode("latin-1")) > 257:
            raise ValueError("scripts.lst line longer than 257 bytes")
        return line
