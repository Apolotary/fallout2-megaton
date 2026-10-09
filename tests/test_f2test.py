# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Synthetic runner tests: no game, compiler, build or engine subprocess runs."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RUNNER = HERE / 'f2test.py' if (HERE / 'f2test.py').is_file() else HERE.parent / 'tools/f2test.py'
spec=importlib.util.spec_from_file_location('runner_candidate',RUNNER)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.base=Path(tempfile.mkdtemp(prefix='megaton-f2test-fixture-')).resolve()
        self.root=self.base/'repo'; self.root.mkdir()
        self.game=self.base/'owned-copy'; self.game.mkdir()
        for name in m.ARCHIVES: (self.game/name.upper()).write_bytes(('synthetic '+name).encode())
        (self.game/'Fallout2.CFG').write_bytes(b'[SYSTEM]\r\nmaster_dat=foreign.dat\r\nMASTER_PATCHES=outside\r\ncritter_dat=foreign2.dat\r\ncritter_patches=outside2\r\nart_cache_size=8\r\n[debug]\r\nmode=environment\r\nshow_script_messages=0\r\n[sound]\r\nmusic_path1=outside3\r\nmusic_path2=outside4\r\n')
        (self.game/'Sound/Music').mkdir(parents=True)
        (self.game/'Sound/Music/THEME.ACM').write_bytes(b'synthetic sound')
        self.engine=self.base/'fake-executable'; self.engine.write_text('never run'); self.engine.chmod(0o755)
        self.steps=self.base/'steps.txt'; self.steps.write_text('log sentinel\n')
        self.args=SimpleNamespace(patch=[],overlay=None,debug_log=True,script_messages=True,res='640x480',map='fixture.map',ddraw=[])
        self.saved=patch.multiple(m,ROOT=str(self.root),ENGINE=None); self.saved.start(); self.addCleanup(self.saved.stop)
        self.env=patch.dict(os.environ,{'FALLOUT2_DIR':str(self.game),'F2_ENGINE':str(self.engine)},clear=True); self.env.start(); self.addCleanup(self.env.stop)
        self.original=self.snapshot(self.game)
    def snapshot(self,root):
        return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    def tearDown(self):
        # Every fixture is synthetic and intentionally retained for diagnosis.
        self.assertEqual(self.original,self.snapshot(self.game))
    def main(self,*args):
        argv=['f2test','--name','smoke','--steps',str(self.steps),*args]
        proc=SimpleNamespace(returncode=0,poll=lambda:0)
        with patch.object(sys,'argv',argv),patch.object(m.subprocess,'Popen',return_value=proc) as launch,contextlib.redirect_stdout(io.StringIO()):
            result=m.main()
        return result,launch
    def test_explicit_engine_is_absolute_and_missing_override_never_falls_back(self):
        self.assertEqual(m.select_engine(),self.engine)
        m.ENGINE=str(self.engine)
        for choice in ['',str(self.base/'missing'),str(self.game)]:
            os.environ['F2_ENGINE']=choice
            with self.assertRaises(ValueError): m.select_engine()
    def test_non_executable_refused(self):
        self.engine.chmod(0o644)
        with self.assertRaises(ValueError): m.select_engine()
    def test_relative_engine_resolves_before_run(self):
        os.environ['F2_ENGINE']=os.path.relpath(self.engine,Path.cwd())
        self.assertEqual(m.select_engine(),self.engine)
    def test_remembered_original_and_explicit_precedence(self):
        (self.root/'game').mkdir(); (self.root/'game/.source.json').write_text(json.dumps({'source':str(self.game),'kind':'archives'}))
        del os.environ['FALLOUT2_DIR']
        self.assertEqual(m.selected_source(),self.game)
        (self.root/'game/.source.json').write_text('invalid')
        self.assertEqual(m.selected_source(str(self.game)),self.game)
        os.environ['FALLOUT2_DIR']=str(self.game)
        self.assertEqual(m.selected_source(),self.game)
    def test_case_insensitive_inputs_simple_namespace_compatibility(self):
        run=self.root/'run/test'; m.setup(run,self.args)
        for name in m.ARCHIVES: self.assertEqual((run/name).resolve(),self.game/name.upper())
        self.assertEqual((run/'sound/music/theme.acm').read_bytes(),b'synthetic sound')
        self.assertFalse((run/'sound').is_symlink())
        cfg=(run/'fallout2.cfg').read_text()
        self.assertIn('master_patches=data',cfg); self.assertIn('critter_patches=data',cfg)
        self.assertIn('music_path1=sound/music/',cfg); self.assertNotIn('outside',cfg)
        self.assertIn('[debug]\nmode=log\nshow_script_messages=1',cfg)
        self.assertIn('art_cache_size=8',cfg)
        self.assertIn(b'\r\n',(run/'fallout2.cfg').read_bytes())
    def test_override_cache_stays_in_system(self):
        self.args.art_cache_size=24; run=self.root/'run/test'; m.setup(run,self.args)
        cfg=(run/'fallout2.cfg').read_text(); self.assertIn('art_cache_size=24',cfg); self.assertNotIn('art_cache_size=8',cfg)
    def test_fresh_preserves_entire_previous_run(self):
        run=self.root/'run/smoke'; run.mkdir(parents=True); (run/'evidence').write_text('old')
        result,launch=self.main('--fresh')
        self.assertEqual(result,0); self.assertEqual(launch.call_count,1)
        prior=list(run.parent.glob('smoke.previous-*')); self.assertEqual(len(prior),1); self.assertEqual((prior[0]/'evidence').read_text(),'old')
        call=launch.call_args; self.assertEqual(call.kwargs['cwd'],run)
        self.assertTrue(call.kwargs['env']['F2_AUTOTEST'].endswith('autotest.txt'))
        self.assertIn('quit 0',(run/'autotest.txt').read_text())
        self.assertEqual((run/'fallout2-ce').read_text(),'never run')
    def test_repeated_run_preserves_logs_config_and_shots(self):
        self.main(); run=self.root/'run/smoke'; (run/'run.log').write_text('old log'); (run/'shots/old.png').write_text('synthetic image')
        self.main()
        self.assertEqual([p.read_text() for p in run.glob('run.log.previous-*')],['old log'])
        self.assertEqual([p.read_text() for p in (run/'shots').glob('old.png.previous-*')],['synthetic image'])
        self.assertEqual(len(list(run.glob('fallout2.cfg.previous-*'))),1)
    def test_extracted_only_fails_before_fresh_run_mutation(self):
        extracted=self.base/'extracted'; extracted.mkdir(); (extracted/'color.pal').write_text('fixture'); os.environ['FALLOUT2_DIR']=str(extracted)
        run=self.root/'run/smoke'; run.mkdir(parents=True); (run/'evidence').write_text('unchanged')
        with self.assertRaisesRegex(ValueError,'extracted-only'): self.main('--fresh')
        self.assertEqual((run/'evidence').read_text(),'unchanged'); self.assertEqual(len(list(run.parent.iterdir())),1)
    def test_missing_steps_fails_before_fresh_run_mutation(self):
        run=self.root/'run/smoke'; run.mkdir(parents=True); (run/'evidence').write_text('old'); self.steps=self.base/'absent'
        with self.assertRaises(FileNotFoundError): self.main('--fresh')
        self.assertEqual((run/'evidence').read_text(),'old')
    def test_engine_refusal_before_any_run_write(self):
        os.environ['F2_ENGINE']=''
        with self.assertRaises(ValueError): self.main('--fresh')
        self.assertFalse((self.root/'run').exists())
    def test_ambiguous_archive_fails_before_run_write(self):
        # Native case-sensitive filesystems can create both names; this temp host cannot.
        original_iterdir=Path.iterdir
        def listing(path):
            result=list(original_iterdir(path))
            if path==self.game: result.append(self.game/'master.dat')
            return iter(result)
        with patch.object(Path,'iterdir',listing):
            with self.assertRaisesRegex(ValueError,'ambiguous'): m.setup(self.root/'run/test',self.args)
        self.assertFalse((self.root/'run').exists())
    def test_duplicate_sound_name_refused(self):
        original_walk=os.walk
        def walking(path,**kwargs):
            if Path(path)==self.game/'Sound': return iter([(str(path),[],['a','A'])])
            return original_walk(path,**kwargs)
        with patch.object(m.os,'walk',walking):
            with self.assertRaisesRegex(ValueError,'ambiguous'): m.prepare_inputs(self.args)
    def test_output_symlink_refuses_original_write(self):
        (self.root/'run').symlink_to(self.game,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symbolic'): m.setup(self.root/'run/test',self.args)
    def test_original_run_overlap_refused(self):
        with self.assertRaisesRegex(ValueError,'separate'): m.setup(self.game/'test',self.args)
        self.assertFalse((self.game/'test').exists())
    def test_source_input_symlink_refused(self):
        alternate=self.base/'alternate'; alternate.mkdir()
        for name in m.ARCHIVES: (alternate/name).symlink_to(self.game/name.upper())
        os.environ['FALLOUT2_DIR']=str(alternate)
        with self.assertRaisesRegex(ValueError,'symbolic'): m.prepare_inputs(self.args)
    def test_duplicate_managed_config_section_precedes_run_write(self):
        cfg='[system]\nmaster_dat=a\n[SYSTEM]\nmaster_dat=b\n'
        with patch.object(m,'prepare_inputs',return_value=(self.game,[],None,[],[],None,cfg)):
            with self.assertRaisesRegex(ValueError,'duplicate'): m.setup(self.root/'run/test',self.args)
        self.assertFalse((self.root/'run').exists())
    def test_patch_change_retains_previous_link(self):
        patch1=self.base/'first.dat'; patch1.write_text('first'); patch2=self.base/'second.dat'; patch2.write_text('second')
        self.args.patch=[str(patch1)]; run=self.root/'run/test'; m.setup(run,self.args)
        self.args.patch=[str(patch2)]; m.setup(run,self.args)
        self.assertEqual((run/'patch001.dat').resolve(),patch2)
        self.assertEqual([p.resolve() for p in run.glob('patch001.dat.previous-*')],[patch1])
    def test_unsafe_run_name_refused_without_process(self):
        with self.assertRaises(SystemExit),contextlib.redirect_stderr(io.StringIO()): self.main('--name','../escape')
        self.assertFalse((self.root/'run').exists())

if __name__=='__main__': unittest.main(verbosity=2)
