"""Read-only virtual game tree.

`GameFiles` answers "what would the engine read for this path": it looks in
the overlay directories first (our mod output, highest priority first) and
then in the selected game tree (see gamepath.resolve_game).

Paths are engine-style and case-insensitive; both ``art\\tiles\\tiles.lst`` and
``art/tiles/TILES.LST`` work. Nothing is ever written through this class.
Directory listings are cached: after adding files to an overlay, create a new
instance or call `refresh()`.

Parsed views are cached on the instance and built on demand:

    gf.art_list(type)      names of art/<type>/<type>.lst      (lst.NameList, 0-based)
    gf.proto_list(type)    names of proto/<type>/<type>.lst    (lst.NameList, 1-based)
    gf.scripts             scripts/scripts.lst                 (lst.ScriptList)
    gf.msg(path)           text/english/<path>                 (msg.MsgFile)
    gf.protos              pro.ProtoDB
    gf.art                 frm.ArtDB
    gf.palette             pal.Palette
"""
import fnmatch
import os

from . import ids

from .gamepath import resolve_game


def norm(path):
    """Engine path -> lookup key: forward slashes, lower case, no leading './'."""
    path = path.replace("\\", "/").lower()
    while path.startswith("./"):
        path = path[2:]
    return path.strip("/")


class _Tree:
    """One directory root with case-insensitive lookup (directory listings are cached)."""

    def __init__(self, root):
        self.root = root
        self._dirs = {}

    def _listing(self, real_dir):
        listing = self._dirs.get(real_dir)
        if listing is None:
            try:
                listing = {name.lower(): name for name in os.listdir(real_dir)}
            except (FileNotFoundError, NotADirectoryError):
                listing = {}
            self._dirs[real_dir] = listing
        return listing

    def resolve(self, key):
        """key (normalised) -> real path or None"""
        real = self.root
        if not key:
            return real if os.path.isdir(real) else None
        for part in key.split("/"):
            name = self._listing(real).get(part)
            if name is None:
                return None
            real = os.path.join(real, name)
        return real

    def listdir(self, key):
        real = self.resolve(key)
        if real is None or not os.path.isdir(real):
            return []
        return list(self._listing(real))


class GameFiles:
    def __init__(self, base=None, overlay=None):
        """base: extracted game tree (default: the selected user-owned game).
        overlay: a directory, or a list of directories with the highest priority first."""
        if overlay is None:
            overlays = []
        elif isinstance(overlay, (str, os.PathLike)):
            overlays = [overlay]
        else:
            overlays = list(overlay)
        self.base = os.fspath(base) if base is not None else os.fspath(resolve_game())
        self.overlays = [os.fspath(o) for o in overlays]
        if not os.path.isdir(self.base):
            raise FileNotFoundError(f"game tree not found: {self.base}")
        self._trees = [_Tree(o) for o in self.overlays] + [_Tree(self.base)]
        self._cache = {}

    def refresh(self):
        """Forget cached directory listings and parsed views (call after writing into an overlay)."""
        self._trees = [_Tree(o) for o in self.overlays] + [_Tree(self.base)]
        self._cache = {}

    # ------------------------------------------------------------------ files
    def find(self, path):
        """Real file-system path of the winning copy, or None."""
        key = norm(path)
        for tree in self._trees:
            real = tree.resolve(key)
            if real is not None and os.path.isfile(real):
                return real
        return None

    def exists(self, path):
        return self.find(path) is not None

    def read(self, path):
        real = self.find(path)
        if real is None:
            raise FileNotFoundError(f"not in game tree: {path}")
        with open(real, "rb") as f:
            return f.read()

    def text(self, path, encoding="cp1252"):
        return self.read(path).decode(encoding)

    def listdir(self, path=""):
        """Sorted lower-case names (files and directories) merged over all roots."""
        key = norm(path)
        names = set()
        for tree in self._trees:
            names.update(tree.listdir(key))
        return sorted(names)

    def glob(self, pattern):
        """Files matching a glob such as 'maps/*.map' (the directory part is literal)."""
        directory, _, name_pattern = norm(pattern).rpartition("/")
        prefix = directory + "/" if directory else ""
        return [prefix + n for n in self.listdir(directory)
                if fnmatch.fnmatchcase(n, name_pattern) and self.exists(prefix + n)]

    def is_overridden(self, path):
        """True when the winning copy comes from an overlay."""
        real = self.find(path)
        return real is not None and not os.path.abspath(real).startswith(os.path.abspath(self.base) + os.sep)

    # ----------------------------------------------------------- parsed views
    def _cached(self, key, build):
        if key not in self._cache:
            self._cache[key] = build()
        return self._cache[key]

    def art_list(self, obj_type):
        from . import lst
        d = ids.TYPE_DIRS[obj_type]
        return self._cached(("art_list", obj_type),
                            lambda: lst.NameList(lst.art_names(self.read(f"art/{d}/{d}.lst")), base=0))

    def proto_list(self, obj_type):
        from . import lst
        d = ids.TYPE_DIRS[obj_type]
        return self._cached(("proto_list", obj_type),
                            lambda: lst.NameList(lst.proto_names(self.read(f"proto/{d}/{d}.lst")), base=1))

    @property
    def scripts(self):
        from . import lst
        return self._cached("scripts", lambda: lst.ScriptList(self.read("scripts/scripts.lst")))

    def msg(self, path, language="english"):
        """path relative to text/<language>/, e.g. 'game/pro_item.msg'."""
        from . import msg
        full = f"text/{language}/{norm(path)}"
        return self._cached(("msg", full), lambda: msg.MsgFile.from_bytes(self.read(full)))

    @property
    def protos(self):
        from . import pro
        return self._cached("protos", lambda: pro.ProtoDB(self))

    @property
    def art(self):
        from . import frm
        return self._cached("art", lambda: frm.ArtDB(self))

    @property
    def palette(self):
        from . import pal
        return self._cached("palette", lambda: pal.Palette(self.read("color.pal")))
