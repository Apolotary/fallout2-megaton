#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Build Megaton from user-owned Fallout 2 data and manage one owned installation."""
import argparse
from contextlib import contextmanager, ExitStack
import errno
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys
import uuid
import zlib

ROOT = Path(__file__).resolve().parent
ARCHIVES = ('master.dat', 'critter.dat', 'patch000.dat')
TREE_REQUIRED = ('color.pal', 'data/maps.txt', 'art/tiles/tiles.lst', 'text/english/game/proto.msg')
GENERATED = ('mod/scripts_src/headers/pids.h', 'mod/scripts_src/headers/gvars.h',
             'mod/megaton/scripts/ids.h', 'mod/megaton/scripts/tiles.h',
             'mod/reference/prefabs/carwall-den-a.json', 'mod/reference/prefabs/carwall-den-b.json')
PREFABS = (('carwall-den-a', (132, 83), (140, 106)), ('carwall-den-b', (143, 135), (168, 139)))


class UserError(RuntimeError):
    pass


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def library():
    tools = str(ROOT / 'tools')
    if tools not in sys.path:
        sys.path.insert(0, tools)
    try:
        return importlib.import_module('f2lib')
    except ImportError as exc:
        raise UserError('Install the dependencies from requirements.txt before running setup or build.') from exc


def no_links(path):
    path = Path(os.path.abspath(path))
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise UserError('Symbolic links are not allowed for generated state or installation targets.')
    return path


def find_case(root, relative):
    path = Path(root)
    parts = relative.replace('\\', '/').split('/')
    if any(not part or part in {'.', '..'} or ':' in part or '\0' in part for part in parts):
        raise UserError('An input contains an unsafe relative path.')
    for part in parts:
        try:
            matches = [entry for entry in path.iterdir() if entry.name.lower() == part.lower()]
        except (FileNotFoundError, NotADirectoryError):
            return None
        if len(matches) > 1:
            raise UserError('Game data contains ambiguous names differing only in letter case.')
        if not matches:
            return None
        path = matches[0]
    return path


def state_path(name):
    return no_links(ROOT / 'game' / name)


def read_json(path, default=None):
    path = no_links(path)
    if not path.exists():
        return default
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise UserError('A local state file is invalid; preserve it and restore its last valid copy.') from exc
    if not isinstance(value, dict):
        raise UserError('A local state file must contain a JSON object.')
    return value


def write_json(path, value):
    path = no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '-' + uuid.uuid4().hex + '.tmp')
    with temp.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    no_links(path)
    os.replace(temp, path)


@contextmanager
def operation_lock():
    folder = state_path('.megaton.lock')
    folder.parent.mkdir(parents=True, exist_ok=True)
    try:
        folder.mkdir()
    except FileExistsError:
        raise UserError('Another Megaton operation may be running. If interrupted, first stop every Megaton command, then move game/.megaton.lock aside and retry.') from None
    try:
        yield
    finally:
        folder.rmdir()


def select_source(explicit=None):
    choice = explicit or os.environ.get('FALLOUT2_DIR')
    if not choice:
        choice = read_json(state_path('.source.json'), {}).get('source')
    if not choice:
        raise UserError('Select your English Fallout 2 data with --game DIR or FALLOUT2_DIR.')
    source = Path(choice).expanduser().resolve()
    cache = ROOT / 'game'
    if not source.is_dir():
        raise UserError('The selected game folder does not exist.')
    if source == ROOT or source in cache.parents or source == cache or cache in source.parents:
        raise UserError('Keep game input outside this project and its generated game directory.')
    return source


class InputView:
    """Read-only preflight; shared f2lib performs extraction only after approval."""
    def __init__(self, source):
        self.source = Path(source)
        self.stack = ExitStack()
        self.archives = []

    def __enter__(self):
        try:
            if all((path := find_case(self.source, name)) is not None and path.is_file() for name in TREE_REQUIRED):
                self.kind = 'tree'
                # GameFiles' general lookup caches names; detect ambiguity first.
                for directory, dirs, files in os.walk(self.source, followlinks=False):
                    names = dirs + files
                    if len({name.lower() for name in names}) != len(names):
                        raise UserError('The extracted game tree contains ambiguous letter-case names.')
                    if any((Path(directory) / name).is_symlink() for name in names):
                        raise UserError('Use a regular extracted data tree without symbolic links.')
            else:
                self.kind = 'archives'
                library()
                from f2lib.dat2 import Dat2
                for name in ARCHIVES:
                    path = find_case(self.source, name)
                    if path is None or not path.is_file() or path.is_symlink():
                        raise UserError('Select an English extracted tree or a folder with master.dat, critter.dat and patch000.dat.')
                    archive = self.stack.enter_context(Dat2(path))
                    if len(archive.order) != len(set(archive.order)):
                        raise UserError('A game archive contains duplicate case-insensitive member names.')
                    for member in archive.order:
                        parts = member.replace('\\', '/').split('/')
                        if any(not part or part in {'.', '..'} or ':' in part or '\0' in part for part in parts):
                            raise UserError('A game archive contains an unsafe member path.')
                    self.archives.append(archive)
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *exc):
        self.stack.close()

    def read(self, name):
        if self.kind == 'tree':
            path = find_case(self.source, name)
            if path is not None and path.is_file():
                return path.read_bytes()
        else:
            for archive in reversed(self.archives):
                if archive.has(name):
                    return archive.read(name)
        raise FileNotFoundError(name)


def count_input(data, rule):
    if rule['kind'] == 'lines':
        lines = data.decode('latin-1').split('\n')
        return len(lines) - int(bool(lines) and lines[-1] == '')
    prefix = re.escape(rule['kind'])
    numbers = [int(value) for value in re.findall(r'^\[' + prefix + r'\s+(\d+)\]', data.decode('latin-1'), re.M | re.I)]
    if numbers != list(range(rule['value'])):
        return -1
    return len(numbers)


def prototype_signature(view, kinds):
    h = hashlib.sha256(b'megaton-header-prototypes-v1\0')
    count = missing = 0
    for kind in kinds:
        for filename in view.read('proto/' + kind + '/' + kind + '.lst').decode('latin-1').split():
            name = 'proto/' + kind + '/' + filename.lower()
            encoded = name.encode('utf-8')
            h.update(struct.pack('>I', len(encoded)))
            h.update(encoded)
            try:
                data = view.read(name)
            except FileNotFoundError:
                h.update(b'M')
                missing += 1
            else:
                h.update(b'P')
                h.update(struct.pack('>Q', len(data)))
                h.update(hashlib.sha256(data).digest())
            count += 1
    return {'count': count, 'missing': missing, 'sha256': h.hexdigest()}


def preflight(source):
    profile = read_json(ROOT / 'game-profile.json')
    if not profile or profile.get('schema_version') != 1:
        raise UserError('The supported game profile is missing or invalid.')
    with InputView(source) as view:
        for item in profile['files']:
            try:
                data = view.read(item['path'])
            except FileNotFoundError:
                raise UserError('Missing ' + item['path'] + '; only the tested English GOG profile is supported.') from None
            if ('count' in item and count_input(data, item['count']) != item['count']['value']) or (
                    len(data) != item['size'] or hashlib.sha256(data).hexdigest() != item['sha256']):
                raise UserError('Unsupported ' + item['path'] + '; only the tested English GOG profile is supported.')
        expected = profile['header_prototypes']
        actual = prototype_signature(view, expected['kinds'])
        if any(actual[key] != expected[key] for key in ('count', 'missing', 'sha256')):
            raise UserError('Unsupported prototype inputs; only the tested English GOG profile is supported.')
        return {'source': str(source), 'kind': view.kind, 'profile': profile['id'],
                'profile_sha256': sha(ROOT / 'game-profile.json')}


def child(arguments, source):
    env = dict(os.environ, FALLOUT2_DIR=str(source), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-B', *arguments], cwd=ROOT, env=env)
    if result.returncode:
        raise UserError('Command failed: ' + ' '.join(arguments) + '. Inspect its message above; setup/build is not marked complete.')


def generate_prefabs(base):
    f2 = library()
    from map_kit import Prefab
    game = f2.GameFiles(base=base)
    game_map = f2.MapFile.load('denbus1', game)
    target = no_links(ROOT / 'mod/reference/prefabs')
    target.mkdir(parents=True, exist_ok=True)
    for name, low, high in PREFABS:
        path = no_links(target / (name + '.json'))
        Prefab.extract(game_map, f2.geometry.tile_at(*low), f2.geometry.tile_at(*high),
                       elevation=0, critters='none', name=name).save(str(path))


def setup(game=None):
    source = select_source(game)
    selected = preflight(source)  # No generated directory or extraction writes before this point.
    library()
    from f2lib.gamepath import resolve_game
    with operation_lock():
        base = resolve_game(str(source), root=ROOT)
        child(['tools/gen_pid_header.py', '--data', str(base), '--out', 'mod/scripts_src/headers'], source)
        generate_prefabs(base)
        child(['mod/megaton-art/build.py', 'clone-data'], source)
        child(['mod/megaton/build.py', 'ids'], source)
        files = {}
        for relative in GENERATED:
            path = no_links(ROOT / relative)
            if not path.is_file() or (relative.endswith('.h') and b'\r' in path.read_bytes()):
                raise UserError('Generated inputs are missing or headers are not LF: ' + relative)
            files[relative] = sha(path)
        write_json(state_path('.megaton-setup.json'), {'schema_version': 1, **selected, 'generated_sha256': files})
    return 'Setup complete. Run python megaton.py build.'


def require_setup(game=None):
    source = select_source(game)
    selected = preflight(source)
    saved = read_json(state_path('.megaton-setup.json'), {})
    if saved.get('schema_version') != 1 or any(saved.get(key) != value for key, value in selected.items()):
        raise UserError('Run python megaton.py setup for this selected game first.')
    for name in GENERATED:
        path = no_links(ROOT / name)
        if not path.is_file() or sha(path) != saved.get('generated_sha256', {}).get(name):
            raise UserError('Generated inputs changed or are missing; run setup again.')
    return source, selected


def source_fingerprint():
    """Hash the build-input inventory, including prepared art and prebuilt INTs."""
    roots = ('mod/megaton', 'mod/megaton-art', 'mod/scripts_src/headers',
             'mod/reference/prefabs', 'tools')
    suffixes = {'.py', '.json', '.h', '.ssl', '.msg', '.int', '.frm', '.lst', '.pro', '.dat', '.txt', '.steps'}
    paths = {ROOT / name for name in ('megaton.py', 'game-profile.json', 'requirements.txt', '.gitattributes')
             if (ROOT / name).is_file()}
    for relative in roots:
        base = ROOT / relative
        for directory, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = sorted(name for name in dirs if name not in {'__pycache__', '.git', 'node_modules', 'sslc'}
                             and not (Path(directory) == ROOT / 'mod/megaton' and name.startswith('out')))
            if any((Path(directory) / name).is_symlink() for name in dirs):
                raise UserError('Build inputs must not contain symbolic-link directories.')
            paths.update(Path(directory) / name for name in files if Path(name).suffix.lower() in suffixes)
    h = hashlib.sha256(b'megaton-build-inputs-v1\0')
    for path in sorted(paths):
        no_links(path)
        name = path.relative_to(ROOT).as_posix().encode('utf-8')
        h.update(struct.pack('>I', len(name)))
        h.update(name)
        h.update(bytes.fromhex(sha(path)))
    return {'scheme': 'megaton-build-inputs-v1', 'files': len(paths), 'sha256': h.hexdigest()}


def build(game=None, prebuilt=None):
    with operation_lock():
        source, selected = require_setup(game)
        history = state_path('build-history') / uuid.uuid4().hex
        history.mkdir(parents=True)
        record = state_path('.megaton-build.json')
        output = no_links(ROOT / 'mod/megaton/out')
        if record.exists():
            record.rename(history / 'previous-build.json')
        if output.exists():
            if not output.is_dir():
                raise UserError('The build output path must be a regular directory.')
            output.rename(history / 'previous-out')
        if prebuilt:
            child(['mod/megaton/prebuilt.py', prebuilt], source)
        fingerprint = source_fingerprint()
        child(['mod/megaton/build.py'], source)
        archive = no_links(ROOT / 'mod/megaton/out/patch001.dat')
        if not archive.is_file():
            raise UserError('The build did not produce patch001.dat.')
        if source_fingerprint() != fingerprint:
            raise UserError('Build inputs changed during the build. No install-ready build was recorded; inspect the changes and run setup again.')
        write_json(state_path('.megaton-build.json'), {'schema_version': 1, **selected,
                   'archive': 'mod/megaton/out/patch001.dat', 'sha256': sha(archive),
                   'build_inputs': fingerprint})
    return 'Build complete: mod/megaton/out/patch001.dat.'


def install_state():
    value = read_json(state_path('.megaton-install.json'),
                      {'schema_version': 1, 'installed': None, 'pending': None, 'history': []})
    if value.get('schema_version') != 1 or not isinstance(value.get('history'), list):
        raise UserError('Installation ownership state is invalid; no game files were changed.')
    installed = value.get('installed')
    if installed is not None and (not isinstance(installed, dict)
            or not isinstance(installed.get('target'), str) or installed.get('filename') != 'patch001.dat'
            or not re.fullmatch(r'[0-9a-f]{64}', str(installed.get('sha256', '')))):
        raise UserError('Installation ownership record is invalid; no game files were changed.')
    if value.get('pending') is not None and not isinstance(value['pending'], dict):
        raise UserError('Pending installation state is invalid; no game files were changed.')
    return value


def save_install(value):
    write_json(state_path('.megaton-install.json'), value)


def patch_at(target):
    path = find_case(target, 'patch001.dat')
    if path is not None and (path.is_symlink() or not path.is_file()):
        raise UserError('patch001.dat must be a regular file, not a symbolic link or directory.')
    return path


def file_stamp(path):
    no_links(path)
    st = path.stat()
    if not stat.S_ISREG(st.st_mode):
        raise UserError('Expected a regular owned file.')
    value = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
    value_hash = sha(path)
    after = path.stat()
    if value != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise UserError('A file changed while it was checked; retry after other programs stop writing it.')
    return value, value_hash


def copy_exclusive(source, target, expected):
    target = no_links(target)
    with Path(source).open('rb') as stream, target.open('xb') as output:
        shutil.copyfileobj(stream, output)
        output.flush()
        os.fsync(output.fileno())
    if sha(target) != expected:
        raise UserError('A copied archive failed verification; the pending transaction was retained.')


def move_verified(source, target, expected):
    """Move owned bytes aside; a cross-volume move keeps a verified retained copy."""
    source, target = no_links(source), no_links(target)
    stamp, actual = file_stamp(source)
    if actual != expected:
        raise UserError('Owned archive changed before preservation.')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not target.is_file() or sha(target) != expected:
            raise UserError('An interrupted preservation copy differs; both files were retained.')
    else:
        try:
            # Link-before-unlink is an atomic no-replace move on one filesystem.
            os.link(source, target)
        except OSError as exc:
            if exc.errno not in {errno.EXDEV, errno.ENOTSUP, errno.EPERM}:
                raise
            copy_exclusive(source, target, expected)
    if file_stamp(source) != (stamp, expected) or sha(target) != expected:
        raise UserError('A file changed during preservation; both copies were retained.')
    source.unlink()  # The verified retained file already owns these exact bytes.


def validate_target(target):
    target = no_links(Path(target).expanduser())
    if not target.is_dir():
        raise UserError('The installation target must be an existing game folder.')
    if target == ROOT or ROOT in target.parents or target in ROOT.parents:
        raise UserError('Use an installation folder separate from this project.')
    for name in ARCHIVES:
        path = find_case(target, name)
        if path is None or not path.is_file() or path.is_symlink():
            raise UserError('The installation target needs regular master.dat, critter.dat and patch000.dat files.')
    preflight(target)
    return target


def choose_target(explicit, state):
    if explicit:
        return validate_target(explicit)
    if state.get('installed'):
        return validate_target(state['installed']['target'])
    source = select_source()
    if not all((path := find_case(source, name)) is not None and path.is_file() for name in ARCHIVES):
        raise UserError('An extracted tree is not an installation. Use install --target DIR for a game folder.')
    return validate_target(source)


def owned_patch(target, installed):
    path = patch_at(target)
    if installed is None:
        if path is not None:
            raise UserError('A foreign patch001.dat already exists. Preserve it yourself before installing Megaton.')
        return None
    if installed.get('target') != str(target) or installed.get('filename') != 'patch001.dat':
        raise UserError('Another installation is already owned. Uninstall it before choosing a new target.')
    if path is not None and (path.name != installed['filename'] or file_stamp(path)[1] != installed.get('sha256')):
        raise UserError('The owned patch was renamed or modified. Refusing to replace or remove it.')
    return path


def pending_paths(pending):
    token = pending.get('id', '')
    if not re.fullmatch(r'[0-9a-f]{32}', token) or pending.get('operation') not in {'install', 'uninstall'}:
        raise UserError('Pending install state is invalid; preserve it for manual recovery.')
    target = no_links(Path(pending['target']))
    retained = state_path('retained') / token
    return target, target / ('.megaton-stage-' + token + '.dat'), retained


def resume_pending(state):
    pending = state.get('pending')
    if not pending:
        return
    target, staged, retained = pending_paths(pending)
    old = pending.get('previous')
    path = patch_at(target)
    old_saved = retained / 'previous.dat'
    if pending['operation'] == 'uninstall':
        if path is not None:
            owned_patch(target, old)
            move_verified(path, old_saved, old['sha256'])
        elif not old_saved.is_file() or sha(old_saved) != old['sha256']:
            raise UserError('Interrupted uninstall has no matching preserved archive; inspect the ownership state.')
        state['installed'] = None
    else:
        retained_new = retained / 'installed.dat'
        linked_identity = pending.get('linked_identity')
        if not staged.exists() and linked_identity:
            if (path is None or path.name != 'patch001.dat' or list(file_stamp(path)[0]) != linked_identity
                    or sha(path) != pending['sha256'] or not retained_new.is_file()
                    or sha(retained_new) != pending['sha256']):
                raise UserError('Interrupted installation no longer matches its recorded file identity; nothing was replaced.')
            if old and (not old_saved.is_file() or sha(old_saved) != old['sha256']):
                raise UserError('The preserved previous archive changed; installation stopped.')
            state['installed'] = {'target': str(target), 'filename': 'patch001.dat', 'sha256': pending['sha256']}
            state['history'].append(dict(pending, completed=True))
            state['pending'] = None
            save_install(state)
            return
        if not staged.is_file() or staged.is_symlink() or sha(staged) != pending['sha256']:
            raise UserError('Interrupted install has incomplete staging. Preserve its named staging file, then restore the prior ownership state.')
        if path is not None and os.path.samestat(path.stat(), staged.stat()):
            if old and (not old_saved.is_file() or sha(old_saved) != old['sha256']):
                raise UserError('The preserved previous archive changed; installation stopped.')
        else:
            if old and path is not None:
                owned_patch(target, old)
                # Check no-replace linking before moving the working old patch.
                probe = staged.with_name(staged.name + '.link-test')
                if not probe.exists():
                    os.link(staged, probe)
                elif probe.is_symlink() or not os.path.samestat(probe.stat(), staged.stat()):
                    raise UserError('A foreign link-test file exists; it was not changed.')
                probe.unlink()  # Only the extra link is removed; staged retains all bytes.
                move_verified(path, old_saved, old['sha256'])
                path = None
            elif path is not None:
                raise UserError('A foreign patch appeared during installation; it was not changed.')
            elif old and not old_saved.is_file():
                raise UserError('The prior owned patch disappeared during installation; inspect the pending state.')
            if old_saved.exists() and (not old or sha(old_saved) != old['sha256']):
                raise UserError('The preserved previous archive changed; installation stopped.')
            # This primitive never overwrites a file another process created.
            os.link(staged, target / 'patch001.dat')
        if patch_at(target).name != 'patch001.dat' or sha(target / 'patch001.dat') != pending['sha256']:
            raise UserError('The new installation changed before ownership could be recorded.')
        pending['linked_identity'] = list(file_stamp(target / 'patch001.dat')[0])
        save_install(state)
        # Preserve staging before declaring completion. Its recorded inode lets
        # an interrupted move be reconciled without claiming a foreign file.
        move_verified(staged, retained_new, pending['sha256'])
        state['installed'] = {'target': str(target), 'filename': 'patch001.dat', 'sha256': pending['sha256']}
    state['history'].append(dict(pending, completed=True))
    state['pending'] = None
    save_install(state)


def starting_map(target):
    path = find_case(target, 'ddraw.ini')
    if path is None or not path.is_file() or path.is_symlink():
        return False
    for line in path.read_text(errors='replace').splitlines():
        line = re.split(r'[;#]', line, maxsplit=1)[0].strip()
        if re.fullmatch(r'StartingMap\s*=\s*megaton\.map', line, re.I):
            return True
    return False


def install(target=None):
    with operation_lock():
        state = install_state()
        built = read_json(state_path('.megaton-build.json'), {})
        archive = no_links(ROOT / 'mod/megaton/out/patch001.dat')
        if built.get('schema_version') != 1 or not archive.is_file() or sha(archive) != built.get('sha256'):
            raise UserError('No verified local build is available. Run python megaton.py build first.')
        if built.get('build_inputs') != source_fingerprint():
            raise UserError('Build inputs changed since the last successful build. Run python megaton.py build before installing.')
        expected = built['sha256']
        if state.get('pending'):
            if target and no_links(Path(target).expanduser()) != Path(state['pending']['target']):
                raise UserError('Finish the pending operation on its original target first.')
            if state['pending']['operation'] == 'install' and state['pending'].get('sha256') != expected:
                raise UserError('The pending installation belongs to another build; resolve it before installing this build.')
            resume_pending(state)
        destination = choose_target(target, state)
        previous = state.get('installed')
        existing = owned_patch(destination, previous)
        if existing is not None and previous['sha256'] == expected:
            return 'Megaton is already installed and unchanged.'
        if previous and existing is None:
            raise UserError('The owned patch is missing. Run uninstall to clear that ownership before installing again.')
        token = uuid.uuid4().hex
        pending = {'id': token, 'operation': 'install', 'target': str(destination),
                   'sha256': expected, 'previous': previous}
        # Persist a writable journal before changing the game folder.
        state['pending'] = pending
        save_install(state)
        staged = destination / ('.megaton-stage-' + token + '.dat')
        copy_exclusive(archive, staged, expected)
        resume_pending(state)
        reminder = ' StartingMap=megaton.map is active; ddraw.ini was not changed.' if starting_map(destination) else ''
        return 'Megaton installed.' + reminder


def uninstall(target=None):
    with operation_lock():
        state = install_state()
        if state.get('pending'):
            if target and no_links(Path(target).expanduser()) != Path(state['pending']['target']):
                raise UserError('Finish the pending operation on its original target first.')
            resume_pending(state)
        previous = state.get('installed')
        if previous is None:
            return 'Megaton is not installed by this project.'
        destination = no_links(Path(previous['target']))
        if target and no_links(Path(target).expanduser()) != destination:
            raise UserError('The requested target does not match the owned installation.')
        existing = owned_patch(destination, previous)
        if existing is None:
            state['history'].append({'operation': 'already-absent', 'previous': previous})
            state['installed'] = None
            save_install(state)
            return 'Owned patch already absent; ownership cleared.'
        state['pending'] = {'id': uuid.uuid4().hex, 'operation': 'uninstall',
                            'target': str(destination), 'previous': previous}
        save_install(state)
        resume_pending(state)
        reminder = ' StartingMap=megaton.map remains active; adjust ddraw.ini before starting a normal game.' if starting_map(destination) else ''
        return 'Megaton uninstalled; its archive was moved into game/retained/.' + reminder


def status(game=None):
    state = install_state()
    try:
        source = str(select_source(game))
    except UserError as exc:
        source = str(exc)
    record = state.get('installed')
    result = {'source': source, 'installed': 'not owned', 'pending': state.get('pending')}
    if record:
        target = no_links(Path(record['target']))
        path = patch_at(target)
        result.update(target=str(target), installed='missing' if path is None else
                      'unchanged' if path.name == record['filename'] and sha(path) == record['sha256'] else 'modified',
                      starting_map_megaton=starting_map(target))
    return json.dumps(result, indent=2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('setup', 'build', 'status'):
        command = commands.add_parser(name)
        command.add_argument('--game', metavar='DIR')
        if name == 'build':
            flags = command.add_mutually_exclusive_group()
            flags.add_argument('--verify-prebuilt', action='store_true', help='require a pinned compiler and verify committed INTs before building')
            flags.add_argument('--write-prebuilt', action='store_true', help='maintainer: regenerate the prebuilt manifest/INTs with a pinned compiler')
    for name in ('install', 'uninstall'):
        commands.add_parser(name).add_argument('--target', metavar='DIR')
    args = parser.parse_args(argv)
    try:
        if args.command == 'setup':
            message = setup(args.game)
        elif args.command == 'build':
            message = build(args.game, 'verify' if args.verify_prebuilt else 'write' if args.write_prebuilt else None)
        elif args.command == 'install':
            message = install(args.target)
        elif args.command == 'uninstall':
            message = uninstall(args.target)
        else:
            message = status(args.game)
    except (RuntimeError, OSError, ValueError, TypeError, KeyError, EOFError, struct.error, zlib.error) as exc:
        print('Megaton: ' + str(exc), file=sys.stderr)
        return 1
    print(message)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
