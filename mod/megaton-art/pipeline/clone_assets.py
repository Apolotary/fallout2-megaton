# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Restore reviewed own sprites and compose tiles from the player's game.

The player path never renders, claims IDs, or changes a tracked ledger. The
sprite inventory binds each committed byte to the complete art manifest.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import uuid


class AssetError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(root, relative):
    """Read a regular file within a trusted root without following symlinks."""
    parts = relative.split('/')
    if not parts or any(part in ('', '.', '..') for part in parts):
        raise AssetError('Invalid sprite inventory path.')
    path = Path(root)
    if path.is_symlink():
        raise AssetError('Sprite roots must not be symlinks.')
    for part in parts:
        path = path/part
        if path.is_symlink():
            raise AssetError('Sprite paths must not contain symlinks.')
    if not path.is_file():
        raise AssetError('A required sprite input is missing.')
    return path.read_bytes()


def cell_key(key):
    match = re.fullmatch(r'([a-zA-Z0-9_-]+)/([0-9]+),([0-9]+)(?:@([a-zA-Z0-9_-]+))?', key)
    if not match:
        raise AssetError('Malformed tile slot key.')
    return match[1], int(match[2]), int(match[3]), match[4]


def expected_assets(manifest):
    """Return exact own-FRM inputs and frozen composite recipes from a ledger."""
    owned, composite = {}, {}
    seen_parts = set()
    for piece_name, piece in manifest['pieces'].items():
        for part in piece['parts']:
            kind, slot = part['type'], part['slot']
            if kind not in ('scenery', 'wall') or type(slot) is not int:
                raise AssetError('Invalid live part kind or slot.')
            ledger = manifest['slots'][kind]
            if not 0 <= slot < len(ledger):
                raise AssetError('Live part is outside its ledger.')
            row = ledger[slot]
            key = f"{piece_name}/{part['layer']}/{part['hex'][0]},{part['hex'][1]}"
            if row['key'] != key or row.get('retired') or row.get('reserved') or (kind, slot) in seen_parts:
                raise AssetError('Live part does not own a unique active slot.')
            seen_parts.add((kind, slot))
            prefix, folder = ('mgs', 'scenery') if kind == 'scenery' else ('mgw', 'walls')
            if part['frm'] != f'{prefix}{slot:04d}.frm':
                raise AssetError('Live part filename disagrees with its slot.')
            owned[folder+'/'+part['frm']] = ('part', part)
    for kind, ledger in manifest['slots'].items():
        for slot, row in enumerate(ledger):
            if not row.get('reserved') and not row.get('retired') and (kind, slot) not in seen_parts:
                raise AssetError('Active part slot has no owning piece.')
    tile_section = manifest['tiles']
    slots, sheets = tile_section['slots'], tile_section['sheets']
    if (not slots or slots[0]['key'] != 'blank' or tile_section['first_index'] + len(slots) > 4096
            or len({row['key'] for row in slots}) != len(slots)):
        raise AssetError('Invalid frozen tile ledger.')
    for slot, row in enumerate(slots):
        if row.get('retired') or row['key'] == 'blank':
            continue
        name, i, j, base = cell_key(row['key'])
        if name not in sheets:
            raise AssetError('Tile names an unknown sheet.')
        sheet = sheets[name]
        if not 0 <= i < sheet['size'][0] or not 0 <= j < sheet['size'][1]:
            raise AssetError('Tile cell is outside its sheet.')
        if bool(base) != bool(sheet['decal']):
            raise AssetError('Tile composition disagrees with its sheet class.')
        if base:
            if [i, j] not in sheet['cells']:
                raise AssetError('Composite references an unpainted decal cell.')
            composite[slot] = (name, i, j, base)
        else:
            if sheet['grid'][j][i] != tile_section['first_index'] + slot:
                raise AssetError('Own tile slot disagrees with its sheet grid.')
            owned[f'tiles/mgt{slot:04d}.frm'] = ('tile', {'slot':slot})
    for name, sheet in sheets.items():
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', name):
            raise AssetError('Invalid sheet name.')
        if sheet['decal']:
            seen_cells = set()
            for i, j in sheet['cells']:
                if ((i, j) in seen_cells or not 0 <= i < sheet['size'][0]
                        or not 0 <= j < sheet['size'][1]):
                    raise AssetError('Invalid or duplicate decal cell.')
                seen_cells.add((i, j))
                owned[f'decals/{name}/{i}-{j}.frm'] = ('decal', {'sheet':name, 'i':i, 'j':j})
    return owned, composite


def dependency_order(slots, composite):
    """Topological order for all frozen composite slots; reject missing/cyclic bases."""
    visiting, complete, order = set(), set(), []

    def visit(slot):
        if slot in complete:
            return
        if slot in visiting:
            raise AssetError('The composite tile graph contains a cycle.')
        visiting.add(slot)
        base = composite[slot][3]
        if base.startswith('mgt'):
            match = re.fullmatch(r'mgt([0-9]{4})', base)
            if not match:
                raise AssetError('Malformed custom tile base.')
            dependency = int(match[1])
            if (not 0 <= dependency < len(slots) or slots[dependency].get('retired')
                    or slots[dependency]['key'] == 'blank'):
                raise AssetError('Composite references a missing or retired custom tile.')
            if dependency in composite:
                visit(dependency)
        visiting.remove(slot)
        complete.add(slot)
        order.append(slot)

    for slot in sorted(composite):
        visit(slot)
    return order


def load_assets(art, manifest_bytes, manifest):
    from f2lib.frm import Frm
    from .tiles import stock_mask
    import numpy as np

    owned, composites = expected_assets(manifest)
    root = art/'sprites'
    inventory = json.loads(read_regular(root, 'manifest.json'))
    if (inventory.get('version') != 1 or inventory.get('recipe') != 'indexed_cells_v1'
            or inventory.get('source_manifest_sha256') != digest(manifest_bytes)):
        raise AssetError('Committed sprites do not match the art manifest; refresh them with the author tools.')
    records = {}
    for row in inventory['files']:
        if row['path'] in records:
            raise AssetError('Duplicate sprite inventory entry.')
        records[row['path']] = row
    if set(records) != set(owned):
        raise AssetError('Sprite inventory differs from the live own-art set.')
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise AssetError('Committed sprite tree contains a symlink.')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(owned) | {'manifest.json'}:
        raise AssetError('Committed sprite tree has missing or extra files.')
    loaded = {}
    mask = stock_mask()
    for name, (kind, descriptor) in owned.items():
        data = read_regular(root, name)
        record = records[name]
        if len(data) != record['size'] or digest(data) != record['sha256']:
            raise AssetError('A committed sprite differs from its reviewed bytes.')
        frm = Frm.from_bytes(data)
        if frm.version != 4 or frm.to_bytes() != data or len(frm.stored) != 1:
            raise AssetError('A committed sprite has an unsupported FRM structure.')
        if kind == 'part':
            if (frm.frame_count != descriptor['frames'] or list(frm.shift()) != descriptor['shift']
                    or list(frm.size()) != descriptor['size']):
                raise AssetError('A live sprite disagrees with its part metadata.')
        else:
            if (frm.frame_count != 1 or frm.size() != (80, 36) or any(frm.x_offsets)
                    or any(frm.y_offsets) or frm.frame().x or frm.frame().y
                    or np.any(frm.frame().array()[~mask])):
                raise AssetError('An own tile cell has invalid dimensions, offsets or pixels.')
        loaded[name] = (data, frm)
    return loaded, composites


def build(art=None):
    """Build privately, verify, then activate; preserve every previous output tree."""
    import numpy as np
    from f2lib import GameFiles, ids
    from f2lib.frm import Frm
    from . import data, tiles

    art = Path(art) if art else Path(__file__).resolve().parents[1]
    manifest_bytes = read_regular(art, 'manifest.json')
    manifest = json.loads(manifest_bytes)
    snapshot = json.dumps(manifest, sort_keys=True)
    assets, composites = load_assets(art, manifest_bytes, manifest)
    order = dependency_order(manifest['tiles']['slots'], composites)
    stock = GameFiles()
    names = stock.art_list(ids.OBJ_TYPE_TILE)
    if len(names) != manifest['tiles']['first_index']:
        raise AssetError('The selected game tile table is unsupported.')
    stock_bases = {}
    for _, _, _, base in composites.values():
        if not base.startswith('mgt'):
            try:
                stock_bases[base] = names.index(base+'.frm')
            except (ValueError, KeyError):
                raise AssetError('A required source tile is absent from the selected game.') from None
    staging = art/('out.clone-'+uuid.uuid4().hex)
    staging.mkdir()
    for name, (blob, _) in assets.items():
        if name.startswith('decals/'):
            continue
        data._write(str(staging), 'art/'+name, blob)
    data.write_data(manifest, str(staging))
    tiles.write_data(manifest, str(staging))
    for slot in order:
        sheet, i, j, base = composites[slot]
        over = assets[f'decals/{sheet}/{i}-{j}.frm'][1].frame().array()
        if base.startswith('mgt'):
            under = Frm.from_bytes(read_regular(staging, 'art/tiles/'+base+'.frm')).frame().array()
        else:
            under = tiles.base_pixels(stock, stock_bases[base])
        data._write(str(staging), f'art/tiles/mgt{slot:04d}.frm', tiles.tile_frm(np.where(over > 0, over, under)))
    problems = data.verify(manifest, str(staging)) + tiles.verify(manifest, str(staging))
    if problems:
        raise AssetError('Generated art verification failed; the prior output was preserved.')
    data.pack(str(staging), str(staging/'patch-art.dat'))
    if snapshot != json.dumps(manifest, sort_keys=True) or read_regular(art, 'manifest.json') != manifest_bytes:
        raise AssetError('The art manifest changed during clone-data; the prior output was preserved.')
    # Recheck inputs after generation before activating a new output tree.
    load_assets(art, manifest_bytes, manifest)
    destination = art/'out'
    if destination.is_symlink():
        raise AssetError('Art output must not be a symlink.')
    backup = None
    if destination.exists():
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup = art/('out.previous-'+stamp+'-'+uuid.uuid4().hex[:8])
        destination.rename(backup)
    try:
        staging.rename(destination)
    except OSError:
        if backup is not None and not destination.exists():
            backup.rename(destination)
        raise
    print(f'art: restored {len(assets)} own sprite inputs; composed {len(composites)} tiles from your game')
    return destination
