"""``.msg`` message files: ``{id}{audio}{text}`` triples.

Rules mirrored from message.cc:205-286 and 474-522: everything outside braces
is ignored (comments), line breaks inside a field are dropped, a stray ``}``
outside a field is an error, a field holds at most 1023 bytes, and a repeated
id replaces the earlier entry. Text is single-byte (cp1252 for English).

To change a vanilla file for a mod, prefer `append_entries`: it keeps the
original bytes (comments included) and relies on the "last id wins" rule.
"""

FIELD_MAX = 1023
ENCODING = "cp1252"


def parse(data):
    """bytes -> {id: (audio, text)} as byte strings decoded with cp1252, in file order."""
    entries = {}
    fields = []
    i, n = 0, len(data)
    while True:
        while i < n and data[i] != 0x7B:            # skip to '{'
            if data[i] == 0x7D:
                raise ValueError(f"mismatched delimiters at offset {i}")
            i += 1
        if i >= n:
            break
        end = data.find(b"}", i + 1)
        if end < 0:
            raise ValueError(f"unterminated field at offset {i}")
        field = data[i + 1:end].replace(b"\r\n", b"").replace(b"\n", b"")
        if len(field) > FIELD_MAX:
            raise ValueError(f"field longer than {FIELD_MAX} bytes at offset {i}")
        fields.append(field)
        i = end + 1
        if len(fields) == 3:
            number = int(fields[0].decode("ascii").strip())
            entries.pop(number, None)
            entries[number] = (fields[1].decode(ENCODING), fields[2].decode(ENCODING))
            fields = []
    if fields:
        raise ValueError("incomplete entry at end of file")
    return entries


def format_entry(number, text, audio=""):
    line = f"{{{number}}}{{{audio}}}{{{text}}}"
    for part in (audio, text):
        if "{" in part or "}" in part:
            raise ValueError(f"braces are not allowed in message {number}")
        if len(part.encode(ENCODING)) > FIELD_MAX:
            raise ValueError(f"message {number} is longer than {FIELD_MAX} bytes")
    return line


def serialise(entries):
    """{id: text | (audio, text)} -> bytes, one entry per CRLF line, sorted by id."""
    lines = []
    for number in sorted(entries):
        value = entries[number]
        audio, text = ("", value) if isinstance(value, str) else value
        lines.append(format_entry(number, text, audio))
    return ("\r\n".join(lines) + "\r\n").encode(ENCODING)


def append_entries(data, entries):
    """Original file bytes + new/overriding entries appended at the end."""
    out = bytearray(data)
    if out and not out.endswith(b"\n"):
        out += b"\r\n"
    return bytes(out) + serialise(entries)


class MsgFile:
    """Parsed message file with id lookup."""

    def __init__(self, entries=None):
        self.entries = dict(entries or {})

    @classmethod
    def from_bytes(cls, data):
        return cls(parse(data))

    def __len__(self):
        return len(self.entries)

    def __contains__(self, number):
        return number in self.entries

    def text(self, number, default=None):
        entry = self.entries.get(number)
        return entry[1] if entry is not None else default

    def audio(self, number, default=None):
        entry = self.entries.get(number)
        return entry[0] if entry is not None else default

    def set(self, number, text, audio=""):
        self.entries[number] = (audio, text)

    def to_bytes(self):
        return serialise(self.entries)
