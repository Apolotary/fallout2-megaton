# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Shared setup for the f2lib tests: import path, project paths, cached game tree."""
import functools
import os
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(TESTS)
ROOT = os.path.dirname(TOOLS)

if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from f2lib import GameFiles  # noqa: E402


@functools.lru_cache(maxsize=None)
def gf():
    """The selected read-only vanilla game tree."""
    return GameFiles()


@functools.lru_cache(maxsize=None)
def retail_map(path):
    """Parsed retail map by game path ('maps/arvillag.map'); shared between tests, so read-only."""
    from f2lib import MapFile
    return MapFile.from_bytes(gf().read(path), gf())


def retail_maps():
    """Every retail map, parsed once per test run."""
    return [retail_map(path) for path in gf().glob("maps/*.map")]


class Skip(Exception):
    """Raised by a test that cannot run here; run_all.py reports it as skipped."""


def skip(reason):
    if os.environ.get("PYTEST_CURRENT_TEST"):
        import pytest
        pytest.skip(reason)
    raise Skip(reason)


def archive(name):
    """Optional original archive; extracted-only fixtures skip archive-specific tests."""
    import json
    from pathlib import Path
    from f2lib.gamepath import _find
    state = Path(ROOT)/"game"/".source.json"
    remembered = json.loads(state.read_text()) if state.is_file() else {}
    source = os.environ.get("FALLOUT2_DIR") or remembered.get("source")
    path = _find(Path(source), name) if source else None
    if path is None:
        skip("This test needs original game archives; the selected input is an extracted tree.")
    return str(path)
