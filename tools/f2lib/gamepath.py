"""Locate user-owned Fallout 2 data and keep any generated copy under game/.

Selection order: an explicit directory, FALLOUT2_DIR, then game/.source.json.
An installation needs master.dat, critter.dat and patch000.dat. An extracted
tree is used in place. Source directories are opened read-only.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import struct
import zlib
import tempfile

from .dat2 import Dat2

ROOT = Path(__file__).resolve().parents[2]
ARCHIVES = ("master.dat", "critter.dat", "patch000.dat")
REQUIRED = ("color.pal", "data/maps.txt", "art/tiles/tiles.lst", "text/english/game/proto.msg")


class GamePathError(RuntimeError):
    """A game selection or extraction error suitable for a CLI message."""


def _find(root, relative):
    current = Path(root)
    for part in relative.split("/"):
        try:
            matches = [p for p in current.iterdir() if p.name.lower() == part.lower()]
        except (FileNotFoundError, NotADirectoryError):
            return None
        if len(matches) > 1:
            raise GamePathError("Game data contains ambiguous names differing only in letter case.")
        if not matches:
            return None
        current = matches[0]
    return current if current.is_file() else None


def _is_tree(path):
    return all(_find(path, name) is not None for name in REQUIRED)


def _state(cache):
    if (cache / ".source.json").is_symlink():
        raise GamePathError("The game settings file must not be a symbolic link.")
    try:
        value = json.loads((cache / ".source.json").read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def _save(cache, state):
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / ".source.json"
    if target.is_symlink():
        raise GamePathError("The game settings file must not be a symbolic link.")
    with tempfile.NamedTemporaryFile("w", dir=cache, prefix=".source-", delete=False,
                                     encoding="utf-8") as out:
        json.dump(state, out, indent=2)
        out.write("\n")
        temp = out.name
    os.replace(temp, target)


def _member_path(root, name):
    name = name.replace("\\", "/").lower()
    parts = name.split("/")
    if any(not part or part in {".", ".."} or ":" in part or "\0" in part for part in parts):
        raise GamePathError("A game archive contains an unsafe member path.")
    return root.joinpath(*parts)


@contextmanager
def _exclusive(cache):
    cache.mkdir(parents=True, exist_ok=True)
    lock = cache / ".setup.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        raise GamePathError("Game setup is already running; if it was interrupted, remove game/.setup.lock only after every exporter has stopped.") from None
    try:
        yield
    finally:
        lock.rmdir()


def resolve_game(game=None, *, root=None):
    """Return an extracted data Path; root is the repository root (test override).

    Archive extraction is staged separately and the old cache is retained if
    extraction fails. Only the three base-game archives are imported: loose
    mods and additional patches are not part of this viewer's setup.
    """
    repo = Path(root).resolve() if root is not None else ROOT
    cache = repo / "game"
    if cache.is_symlink():
        raise GamePathError("The generated game directory must not be a symbolic link.")
    state = _state(cache)
    choice = game or os.environ.get("FALLOUT2_DIR") or state.get("source")
    if not choice:
        raise GamePathError("Select your Fallout 2 folder with --game DIR or FALLOUT2_DIR.")
    source = Path(choice).expanduser().resolve()
    if not source.is_dir():
        raise GamePathError("The selected game folder does not exist; use --game DIR or FALLOUT2_DIR.")
    if source == repo or source in cache.parents or source == cache or cache in source.parents:
        raise GamePathError("Keep the selected game outside this project's generated game directory and do not put the project inside the selected game.")
    if _is_tree(source):
        with _exclusive(cache):
            _save(cache, {"version": 1, "source": str(source), "kind": "tree"})
        return source
    archives = [_find(source, name) for name in ARCHIVES]
    if not all(archives):
        raise GamePathError("Use --game DIR or FALLOUT2_DIR for an English extracted tree or a folder containing master.dat, critter.dat and patch000.dat.")
    with _exclusive(cache):
        return _prepare_archives(cache, source, archives)


def _prepare_archives(cache, source, archives):
    state = _state(cache)
    signature = [{"name": name, "size": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns}
                 for name, p in zip(ARCHIVES, archives)]
    target = cache / "data"
    if target.is_symlink():
        raise GamePathError("The extracted game cache must not be a symbolic link.")
    if (state.get("source") == str(source) and state.get("archives") == signature
            and state.get("kind") == "archives" and _is_tree(target)):
        return target
    cache.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".extract-", dir=cache))
    backup = cache / ".previous-data"
    try:
        for archive_path in archives:
            with Dat2(archive_path) as archive:
                for key in archive.order:
                    dest = _member_path(temporary, key)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(archive.read(key))
        if not _is_tree(temporary):
            raise GamePathError("The archives do not contain the required English Fallout 2 data.")
        if backup.exists() or backup.is_symlink():
            raise GamePathError("An earlier extraction backup exists in game/; preserve it before retrying setup.")
        had_old = target.exists()
        if had_old:
            target.rename(backup)
        try:
            temporary.rename(target)
            _save(cache, {"version": 1, "source": str(source), "kind": "archives", "archives": signature})
        except BaseException:
            if target.exists():
                shutil.rmtree(target)
            if had_old:
                backup.rename(target)
            raise
        if had_old:
            shutil.rmtree(backup)
        return target
    except GamePathError:
        raise
    except (OSError, ValueError, EOFError, struct.error, zlib.error) as exc:
        raise GamePathError("Could not read or extract the selected game; check its archives and free disk space.") from exc
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
