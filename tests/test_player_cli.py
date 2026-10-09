#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Synthetic safety tests. Retain fixtures; never select an actual game as target."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout

CLI = Path(__file__).with_name('megaton.py')
if not CLI.is_file():
    CLI = Path(__file__).resolve().parents[1] / 'megaton.py'
SPEC = importlib.util.spec_from_file_location('megaton_candidate', CLI)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
m.library()  # Resolve the repository's unchanged vendored library before fixture roots.


class Safety(unittest.TestCase):
    def setUp(self):
        self.container = Path(tempfile.mkdtemp(prefix='megaton-cli-synthetic-')).resolve()
        self.root = self.container / 'repo'
        self.root.mkdir()
        self.target = self.container / 'game-copy'
        self.target.mkdir()
        self.tree = self.container / 'extracted-copy'
        self.tree.mkdir()
        self.env = mock.patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.root_patch = mock.patch.object(m, 'ROOT', self.root)
        self.root_patch.start()
        m.library()
        from f2lib.dat2 import write_dat2
        self.data = {'color.pal': b'synthetic palette', 'font1.aaf': b'synthetic font',
                     'data/maps.txt': b'[Map 000]\n', 'art/tiles/tiles.lst': b'synthetic.frm\n',
                     'text/english/game/proto.msg': b'synthetic own message',
                     'scripts/scripts.lst': b'synthetic.int\n'}
        for kind in ('items', 'critters', 'scenery'):
            self.data['proto/' + kind + '/' + kind + '.lst'] = b'example.pro\n'
            self.data['proto/' + kind + '/example.pro'] = b'synthetic ' + kind.encode()
        for name, data in self.data.items():
            path = self.tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        base = dict(self.data, **{'scripts/scripts.lst': b'old.int\n'})
        write_dat2(base, self.target / 'master.dat')
        write_dat2({}, self.target / 'critter.dat')
        write_dat2({'scripts/scripts.lst': self.data['scripts/scripts.lst']}, self.target / 'patch000.dat')
        (self.target / 'ddraw.ini').write_text('[Misc]\nStartingMap=megaton.map\n')
        profile = {'schema_version': 1, 'id': 'synthetic-test-profile', 'files': []}
        with m.InputView(self.tree) as view:
            for name, data in sorted(self.data.items()):
                item = {'path': name, 'size': len(data), 'sha256': m.hashlib.sha256(data).hexdigest()}
                if name.endswith('.lst'):
                    item['count'] = {'kind': 'lines', 'value': 1}
                if name == 'data/maps.txt':
                    item['count'] = {'kind': 'Map', 'value': 1}
                profile['files'].append(item)
            kinds = ['items', 'critters', 'scenery']
            profile['header_prototypes'] = {'scheme': 'megaton-header-prototypes-v1', 'kinds': kinds,
                                            **m.prototype_signature(view, kinds)}
        (self.root / 'game-profile.json').write_text(json.dumps(profile))
        archive = self.root / 'mod/megaton/out/patch001.dat'
        archive.parent.mkdir(parents=True)
        archive.write_bytes(b'own synthetic mod v1')
        self.build_record()

    def tearDown(self):
        self.root_patch.stop()
        self.env.stop()

    def build_record(self):
        archive = self.root / 'mod/megaton/out/patch001.dat'
        m.write_json(m.state_path('.megaton-build.json'), {'schema_version': 1,
            'archive': 'mod/megaton/out/patch001.dat', 'sha256': m.sha(archive), 'build_inputs': m.source_fingerprint()})

    def target_snapshot(self):
        return {p.name: m.sha(p) for p in self.target.iterdir() if p.is_file() and not p.is_symlink()}

    def test_profile_tree_and_archive_overlay(self):
        self.assertEqual(m.preflight(self.tree)['kind'], 'tree')
        self.assertEqual(m.preflight(self.target)['kind'], 'archives')
        with m.InputView(self.target) as view:
            self.assertEqual(view.read('scripts/scripts.lst'), b'synthetic.int\n')

    def test_unsupported_profile_precedes_all_setup_writes(self):
        (self.tree / 'scripts/scripts.lst').write_bytes(b'unsupported\nextra\n')
        before = {p.relative_to(self.root).as_posix() for p in self.root.rglob('*')}
        with mock.patch.object(m, 'child') as child, mock.patch.object(m, 'generate_prefabs') as prefabs:
            with self.assertRaises(m.UserError):
                m.setup(str(self.tree))
            child.assert_not_called()
            prefabs.assert_not_called()
        self.assertEqual(before, {p.relative_to(self.root).as_posix() for p in self.root.rglob('*')})

    def test_case_ambiguity_is_rejected(self):
        with mock.patch.object(Path, 'iterdir', return_value=iter([self.target / 'patch001.dat', self.target / 'PATCH001.DAT'])):
            with self.assertRaises(m.UserError):
                m.patch_at(self.target)

    def test_selection_order_and_cache_refusal(self):
        m.write_json(m.state_path('.source.json'), {'version': 1, 'source': str(self.tree), 'kind': 'tree'})
        self.assertEqual(m.select_source(), self.tree)
        with mock.patch.dict(os.environ, {'FALLOUT2_DIR': str(self.target)}):
            self.assertEqual(m.select_source(), self.target)
            self.assertEqual(m.select_source(str(self.tree)), self.tree)
        m.state_path('.source.json').write_text('invalid json')
        self.assertEqual(m.select_source(str(self.tree)), self.tree)
        with self.assertRaises(m.UserError):
            m.select_source(str(self.root / 'game'))

    def setup_mocks(self, crlf=False):
        def child(arguments, source):
            for relative in m.GENERATED:
                if relative.endswith('.h'):
                    path = self.root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'own synthetic header\r\n' if crlf else b'own synthetic header\n')
        def prefabs(base):
            for relative in m.GENERATED:
                if relative.endswith('.json'):
                    path = self.root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('{"synthetic": true}\n')
        return child, prefabs

    def test_setup_separate_commands_and_original_source(self):
        child, prefabs = self.setup_mocks()
        with mock.patch.object(m, 'child', side_effect=child) as calls, mock.patch.object(m, 'generate_prefabs', side_effect=prefabs):
            m.setup(str(self.target))
            first = [call.args for call in calls.call_args_list]
            m.setup(str(self.target))
        self.assertEqual([args[0][0] for args in first], ['tools/gen_pid_header.py', 'mod/megaton-art/build.py', 'mod/megaton/build.py'])
        self.assertEqual(first[1][0], ['mod/megaton-art/build.py', 'clone-data'])
        self.assertEqual(first[2][0], ['mod/megaton/build.py', 'ids'])
        self.assertTrue(all(args[1] == self.target for args in first))
        self.assertEqual(m.read_json(m.state_path('.source.json'))['source'], str(self.target))
        self.assertEqual(m.require_setup()[0], self.target)
        self.assertFalse(list((self.root / 'mod/reference').rglob('*.png')))

    def test_child_environment_overrides_inherited_source(self):
        with mock.patch.dict(os.environ, {'FALLOUT2_DIR': 'wrong-source'}), \
             mock.patch.object(m.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)) as run:
            m.child(['mod/megaton-art/build.py', 'clone-data'], self.target)
        self.assertEqual(run.call_args.kwargs['env']['FALLOUT2_DIR'], str(self.target))
        self.assertEqual(run.call_args.args[0][:2], [m.sys.executable, '-B'])
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_crlf_setup_never_records_success(self):
        child, prefabs = self.setup_mocks(crlf=True)
        with mock.patch.object(m, 'child', side_effect=child), mock.patch.object(m, 'generate_prefabs', side_effect=prefabs):
            with self.assertRaises(m.UserError):
                m.setup(str(self.tree))
        self.assertFalse(m.state_path('.megaton-setup.json').exists())

    def test_build_delegates_prebuilt_and_normal_build(self):
        def generate(arguments, source):
            if arguments == ['mod/megaton/build.py']:
                archive = self.root / 'mod/megaton/out/patch001.dat'
                archive.parent.mkdir(parents=True)
                archive.write_bytes(b'own synthetic successful build')
        with mock.patch.object(m, 'require_setup', return_value=(self.target, {'profile': 'synthetic'})), \
             mock.patch.object(m, 'child', side_effect=generate) as child:
            m.build(prebuilt='verify')
        self.assertEqual([call.args[0] for call in child.call_args_list],
                         [['mod/megaton/prebuilt.py', 'verify'], ['mod/megaton/build.py']])

    def test_install_idempotent_uninstall_preserves(self):
        before = self.target_snapshot()
        source_state = {'version': 1, 'source': str(self.target), 'kind': 'archives'}
        m.write_json(m.state_path('.source.json'), source_state)
        self.assertIn('installed', m.install())
        path = self.target / 'patch001.dat'
        stamp = path.stat()
        state_bytes = m.state_path('.megaton-install.json').read_bytes()
        self.assertIn('already installed', m.install(str(self.target)))
        self.assertEqual(path.stat().st_ino, stamp.st_ino)
        self.assertEqual(m.state_path('.megaton-install.json').read_bytes(), state_bytes)
        self.assertEqual(json.loads(m.status())['installed'], 'unchanged')
        self.assertIn('uninstalled', m.uninstall())
        self.assertEqual(before, self.target_snapshot())
        self.assertEqual(m.read_json(m.state_path('.source.json')), source_state)
        self.assertTrue(list((self.root / 'game/retained').rglob('previous.dat')))
        self.assertIn('not installed', m.uninstall())

    def test_foreign_equal_bytes_are_not_ownership(self):
        archive = self.root / 'mod/megaton/out/patch001.dat'
        (self.target / 'patch001.dat').write_bytes(archive.read_bytes())
        before = self.target_snapshot()
        with self.assertRaises(m.UserError):
            m.install(str(self.target))
        self.assertEqual(before, self.target_snapshot())

    def test_modified_owned_archive_refuses_both_operations(self):
        m.install(str(self.target))
        (self.target / 'patch001.dat').write_bytes(b'user modification')
        for action in (lambda: m.install(str(self.target)), m.uninstall):
            with self.assertRaises(m.UserError):
                action()
        self.assertEqual((self.target / 'patch001.dat').read_bytes(), b'user modification')
        self.assertEqual(json.loads(m.status())['installed'], 'modified')

    def test_foreign_case_and_symlink_refusal(self):
        foreign = self.target / 'PATCH001.DAT'
        foreign.write_bytes(b'foreign patch')
        with self.assertRaises(m.UserError):
            m.install(str(self.target))
        foreign.rename(self.container / 'preserved-foreign.dat')
        foreign = self.target / 'patch001.dat'
        foreign.symlink_to(self.container / 'preserved-foreign.dat')
        with self.assertRaises(m.UserError):
            m.install(str(self.target))
        self.assertEqual((self.container / 'preserved-foreign.dat').read_bytes(), b'foreign patch')

    def test_update_preserves_previous_owned_bytes(self):
        m.install(str(self.target))
        archive = self.root / 'mod/megaton/out/patch001.dat'
        archive.write_bytes(b'own synthetic mod v2')
        self.build_record()
        m.install(str(self.target))
        self.assertEqual((self.target / 'patch001.dat').read_bytes(), archive.read_bytes())
        saved = list((self.root / 'game/retained').rglob('previous.dat'))
        self.assertTrue(any(path.read_bytes() == b'own synthetic mod v1' for path in saved))

    def test_lost_state_never_claims_existing_patch(self):
        m.install(str(self.target))
        m.state_path('.megaton-install.json').rename(self.root / 'preserved-state.json')
        with self.assertRaises(m.UserError):
            m.install(str(self.target))
        self.assertIn('not installed', m.uninstall())
        self.assertTrue((self.target / 'patch001.dat').exists())

    def test_interrupted_link_adopted_only_by_shared_inode(self):
        real_save = m.save_install
        count = 0
        def save(state):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('synthetic interruption after no-replace link')
            real_save(state)
        with mock.patch.object(m, 'save_install', side_effect=save):
            with self.assertRaises(OSError):
                m.install(str(self.target))
        self.assertTrue(m.install_state()['pending'])
        self.assertTrue((self.target / 'patch001.dat').is_file())
        m.install(str(self.target))
        self.assertFalse(m.install_state()['pending'])
        self.assertEqual(json.loads(m.status())['installed'], 'unchanged')

    def test_foreign_creation_race_never_overwrites(self):
        real_link = m.os.link
        def link(source, destination):
            if Path(destination) == self.target / 'patch001.dat':
                Path(destination).write_bytes(b'foreign appeared')
            return real_link(source, destination)
        with mock.patch.object(m.os, 'link', side_effect=link):
            with self.assertRaises(FileExistsError):
                m.install(str(self.target))
        self.assertEqual((self.target / 'patch001.dat').read_bytes(), b'foreign appeared')
        with self.assertRaises(m.UserError):
            m.install(str(self.target))

    def test_state_failure_occurs_before_target_mutation(self):
        before = self.target_snapshot()
        with mock.patch.object(m, 'save_install', side_effect=PermissionError('synthetic read-only state')):
            with self.assertRaises(PermissionError):
                m.install(str(self.target))
        self.assertEqual(before, self.target_snapshot())

    def test_status_is_read_only_and_lock_blocks_mutations(self):
        before = {p.relative_to(self.root).as_posix(): m.sha(p) for p in self.root.rglob('*') if p.is_file()}
        m.status()
        after = {p.relative_to(self.root).as_posix(): m.sha(p) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        lock = m.state_path('.megaton.lock')
        lock.mkdir()
        with self.assertRaises(m.UserError):
            m.install(str(self.target))
        self.assertTrue(lock.exists())

    def test_extracted_source_needs_explicit_install_target(self):
        m.write_json(m.state_path('.source.json'), {'version': 1, 'source': str(self.tree), 'kind': 'tree'})
        with self.assertRaises(m.UserError):
            m.install()
        m.install(str(self.target))

    def test_bad_state_cli_error_has_no_traceback(self):
        m.state_path('.megaton-install.json').write_text('{')
        output = io.StringIO()
        with redirect_stderr(output), redirect_stdout(io.StringIO()):
            self.assertEqual(m.main(['status']), 1)
        self.assertNotIn('Traceback', output.getvalue())

    def test_interruption_after_staging_preserved_recovers(self):
        real_save = m.save_install
        count = 0
        def save(state):
            nonlocal count
            count += 1
            if count == 3:
                raise OSError('synthetic interruption before final ownership commit')
            real_save(state)
        with mock.patch.object(m, 'save_install', side_effect=save):
            with self.assertRaises(OSError):
                m.install(str(self.target))
        self.assertTrue(m.install_state()['pending']['linked_identity'])
        self.assertFalse(list(self.target.glob('.megaton-stage-*')))
        m.install(str(self.target))
        self.assertFalse(m.install_state()['pending'])
        m.uninstall()
        self.assertFalse(list(self.target.glob('.megaton-*')))

    def test_interrupted_uninstall_recovers_preserved_bytes(self):
        m.install(str(self.target))
        real_save = m.save_install
        count = 0
        def save(state):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('synthetic interruption after preservation')
            real_save(state)
        with mock.patch.object(m, 'save_install', side_effect=save):
            with self.assertRaises(OSError):
                m.uninstall()
        self.assertFalse((self.target / 'patch001.dat').exists())
        m.uninstall()
        self.assertIsNone(m.install_state()['installed'])

    def test_cross_volume_preservation_keeps_exact_bytes(self):
        source = self.container / 'owned-synthetic.dat'
        target = self.root / 'game/retained/cross-volume.dat'
        source.write_bytes(b'own synthetic bytes')
        expected = m.sha(source)
        with mock.patch.object(m.os, 'link', side_effect=OSError(m.errno.EXDEV, 'synthetic different filesystem')):
            m.move_verified(source, target, expected)
        self.assertFalse(source.exists())
        self.assertEqual(m.sha(target), expected)

    def test_unsupported_hardlinks_keep_old_install_intact(self):
        m.install(str(self.target))
        old = (self.target / 'patch001.dat').read_bytes()
        (self.root / 'mod/megaton/out/patch001.dat').write_bytes(b'own synthetic mod v2')
        self.build_record()
        with mock.patch.object(m.os, 'link', side_effect=OSError(m.errno.ENOTSUP, 'synthetic link failure')):
            with self.assertRaises(OSError):
                m.install(str(self.target))
        self.assertEqual((self.target / 'patch001.dat').read_bytes(), old)

    def test_exact_two_prefabs_no_preview_api(self):
        calls = []
        class Prefab:
            @staticmethod
            def extract(game_map, low, high, **kwargs):
                calls.append((low, high, kwargs))
                return types.SimpleNamespace(save=lambda path: Path(path).write_text('{"synthetic":true}\n'))
        fake = types.SimpleNamespace(GameFiles=lambda **kwargs: kwargs, MapFile=types.SimpleNamespace(load=lambda *args: 'synthetic-map'),
                                     geometry=types.SimpleNamespace(tile_at=lambda x, y: (x, y)))
        with mock.patch.object(m, 'library', return_value=fake), \
             mock.patch.dict(m.sys.modules, {'map_kit': types.SimpleNamespace(Prefab=Prefab)}):
            m.generate_prefabs(self.tree)
        self.assertEqual([(low, high) for low, high, _ in calls], [((132, 83), (140, 106)), ((143, 135), (168, 139))])
        self.assertTrue(all(kwargs['elevation'] == 0 and kwargs['critters'] == 'none' for _, _, kwargs in calls))
        files = list((self.root / 'mod/reference/prefabs').iterdir())
        self.assertEqual({path.name for path in files}, {'carwall-den-a.json', 'carwall-den-b.json'})

    def test_failed_rebuild_preserves_old_output_but_disarms_install(self):
        old = (self.root / 'mod/megaton/out/patch001.dat').read_bytes()
        with mock.patch.object(m, 'require_setup', return_value=(self.target, {'profile': 'synthetic'})), \
             mock.patch.object(m, 'child', side_effect=m.UserError('synthetic failed compiler')):
            with self.assertRaises(m.UserError):
                m.build()
        self.assertFalse(m.state_path('.megaton-build.json').exists())
        self.assertFalse((self.root / 'mod/megaton/out').exists())
        copies = list((self.root / 'game/build-history').rglob('patch001.dat'))
        self.assertEqual([path.read_bytes() for path in copies], [old])
        self.assertTrue(list((self.root / 'game/build-history').rglob('previous-build.json')))
        with self.assertRaises(m.UserError):
            m.install(str(self.target))

    def test_changed_build_source_or_art_inventory_refuses_install(self):
        source = self.root / 'mod/megaton/registry.py'
        source.write_text('# synthetic source\n')
        with self.assertRaises(m.UserError):
            m.install(str(self.target))
        self.build_record()
        art = self.root / 'mod/megaton-art/out/art/scenery/example.frm'
        art.parent.mkdir(parents=True)
        art.write_bytes(b'synthetic prepared art')
        with self.assertRaises(m.UserError):
            m.install(str(self.target))

    def test_source_change_during_build_never_records_success(self):
        def generate(arguments, source):
            archive = self.root / 'mod/megaton/out/patch001.dat'
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b'synthetic new output')
            (self.root / 'mod/megaton/registry.py').write_text('# unexpected source change\n')
        with mock.patch.object(m, 'require_setup', return_value=(self.target, {'profile': 'synthetic'})), \
             mock.patch.object(m, 'child', side_effect=generate):
            with self.assertRaises(m.UserError):
                m.build()
        self.assertFalse(m.state_path('.megaton-build.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
