"""Fallout 2 DAT2 archives: reader and writer.

Layout (little-endian), per fallout2-ce src/dfile.cc dbaseOpen()::

    [member payloads ...][tree][u32 treeSize][u32 archiveSize]
    tree = u32 count, then per member:
        u32 nameLength, name bytes (backslashes, no NUL), u8 compressed,
        u32 realSize, u32 packedSize, u32 offset (relative to fileSize - archiveSize)

Compressed members are zlib streams. The engine finds members with a
case-insensitive binary search, so the tree must be sorted by lower-cased
name; `write_dat2` does that and uses zlib level 9, which reproduces the GOG
``patch000.dat`` byte for byte (tools/tests/test_dat2.py).

The reader mirrors tools/dat2.py (same keys: lower-case, forward slashes).
"""
import fnmatch
import os
import struct
import zlib
from collections import namedtuple

Dat2Entry = namedtuple("Dat2Entry", "name compressed real_size packed_size offset")


def _key(name):
    return name.replace("\\", "/").lower()


class Dat2:
    """Read-only view of a DAT2 archive.

    `entries` maps the normalised key (lower-case, '/') to a `Dat2Entry` whose
    `name` is the path exactly as stored; `order` lists keys in archive order.
    """

    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        try:
            self.f.seek(0, os.SEEK_END)
            size = self.f.tell()
            self.f.seek(size - 8)
            tree_size, archive_size = struct.unpack("<II", self.f.read(8))
            self.data_offset = size - archive_size
            self.f.seek(size - tree_size - 8)
            tree = self.f.read(tree_size)
            (count,) = struct.unpack_from("<I", tree, 0)
            pos = 4
            self.entries = {}
            self.order = []
            for _ in range(count):
                (n,) = struct.unpack_from("<I", tree, pos)
                pos += 4
                name = tree[pos:pos + n].decode("latin-1")
                pos += n
                compressed, real, packed, offset = struct.unpack_from("<BIII", tree, pos)
                pos += 13
                key = _key(name)
                self.entries[key] = Dat2Entry(name, compressed, real, packed, offset)
                self.order.append(key)
        except BaseException:
            self.f.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self.f.close()

    def names(self):
        return list(self.order)

    def has(self, name):
        return _key(name) in self.entries

    def read(self, name):
        entry = self.entries[_key(name)]
        self.f.seek(self.data_offset + entry.offset)
        raw = self.f.read(entry.packed_size)
        if entry.compressed:
            raw = zlib.decompress(raw) if entry.real_size else b""
        if len(raw) != entry.real_size:
            raise ValueError(f"{name}: got {len(raw)} bytes, directory says {entry.real_size}")
        return raw

    def read_all(self, original_names=False):
        """{key: bytes} for every member; keys are the stored names when original_names is set."""
        return {(self.entries[k].name if original_names else k): self.read(k) for k in self.order}

    def extract(self, outdir, lower=True, globs=()):
        """Write members under outdir; returns the number of files written."""
        globs = [g.lower() for g in globs]
        count = 0
        for key in self.order:
            if globs and not any(fnmatch.fnmatch(key, g) for g in globs):
                continue
            rel = key if lower else self.entries[key].name.replace("\\", "/")
            dst = os.path.join(outdir, rel)
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            with open(dst, "wb") as out:
                out.write(self.read(key))
            count += 1
        return count


def write_dat2(files, out, compress=True):
    """Write a DAT2 archive.

    files     {member path: bytes}; '/' and '\\' are both accepted, the case of
              the path is stored as given (lookups are case-insensitive).
    out       output file name.
    compress  zlib level 9 for every non-empty member (what the retail
              archives use); False stores everything.

    Returns the number of members written.
    """
    names = {}
    for name in files:
        stored = name.replace("/", "\\")
        if stored.lower() in names:
            raise ValueError(f"duplicate member (case-insensitive): {name}")
        names[stored.lower()] = (stored, name)

    tree = bytearray(struct.pack("<I", len(names)))
    with open(out, "wb") as f:
        offset = 0
        for lowered in sorted(names):
            stored, original = names[lowered]
            data = bytes(files[original])
            compressed = 1 if (compress and data) else 0
            packed = zlib.compress(data, 9) if compressed else data
            encoded = stored.encode("latin-1")
            f.write(packed)
            tree += struct.pack("<I", len(encoded)) + encoded
            tree += struct.pack("<BIII", compressed, len(data), len(packed), offset)
            offset += len(packed)
        f.write(tree)
        f.write(struct.pack("<II", len(tree), offset + len(tree) + 8))
    return len(names)


def pack_dir(directory, out, compress=True):
    """Pack every file below `directory` (paths relative to it) into a DAT2 archive."""
    files = {}
    for root, dirs, names in os.walk(directory):
        dirs.sort()
        for name in sorted(names):
            if name.startswith("."):
                continue
            full = os.path.join(root, name)
            with open(full, "rb") as f:
                files[os.path.relpath(full, directory).replace(os.sep, "\\")] = f.read()
    return write_dat2(files, out, compress=compress)
