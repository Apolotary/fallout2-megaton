#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Synthetic-only tests. No compiler, Node, game, engine or network is invoked."""
import copy,importlib.util,json,pathlib,shutil,struct,tempfile,unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stdout, redirect_stderr
from types import SimpleNamespace
import io
BASE=pathlib.Path(__file__).resolve().parent
REPO=BASE.parent if BASE.name=='tests' else pathlib.Path.cwd()
TARGET=REPO/'mod/megaton/prebuilt.py' if BASE.name=='tests' else BASE/'prebuilt.py'
spec=importlib.util.spec_from_file_location('candidate',TARGET);pb=importlib.util.module_from_spec(spec);spec.loader.exec_module(pb)
EVIDENCE=pathlib.Path(tempfile.mkdtemp(prefix='megaton-prebuilt-synthetic-')).resolve()
REAL=REPO

def minimal_int(last=0x8010):
 head=bytes.fromhex('8002c00100000012800dc001')
 tail=bytes.fromhex('80048010801a8020801a8021801a8022801a8023802480258026')
 entries=struct.pack('>H',2)+b'.\0'+struct.pack('>H',6)+b'start\0'
 ident=struct.pack('>i',len(entries))+entries+b'\xff'*4
 start=46+48+len(ident)+4
 return head+struct.pack('>i',start)+tail+struct.pack('>i',2)+struct.pack('>6i',6,0,0,0,start,0)+struct.pack('>6i',10,0,0,0,start,0)+ident+b'\xff'*4+struct.pack('>H',last)
BLOB=minimal_int()

class TestPrebuilt(unittest.TestCase):
 def setUp(self):
  self.root=EVIDENCE/self.id().split('.')[-1];self.root.mkdir()
  def put(path,text):
   p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
  rows=[(f's{i:02d}','','') for i in range(40)]
  put('mod/megaton/registry.py','SCRIPTS = '+repr(rows)+'\nLOCAL_VARS = 0\n')
  put(pb.SCRIPTS+'/ids.h',''.join(f'#define SCRIPT_S{i:02d} ({1304+i})\n' for i in range(40)))
  put(pb.SCRIPTS+'/megaton.h','\n'.join('#include "'+n+'"' for n in ['ids.h','tiles.h','mgcore.h','mgflav.h','mgmerch.h','fo2.h'])+'\n')
  for n in ['tiles.h','mgcore.h','mgflav.h','mgmerch.h']:put(pb.SCRIPTS+'/'+n,'// synthetic header\n')
  put(pb.HEADERS+'/fo2.h','#include "pids.h"\n#include "gvars.h"\n')
  for n in ['pids.h','gvars.h']:put(pb.HEADERS+'/'+n,'// synthetic generated header\n')
  for stem,_,_ in rows:put(pb.SCRIPTS+'/'+stem+'.ssl','#include "megaton.h"\nprocedure start;\nprocedure start begin end\n')
  put('tools/ssl.py','# synthetic wrapper identity only\n')
  shutil.copyfile(REAL/'tools/intfile.py',self.root/'tools/intfile.py')
  for n in ['sslc.mjs','sslc.wasm']:put('tools/sslc/build/bin/'+n,'synthetic runtime\n')
  put('tools/sslc/CMakeLists.txt','# synthetic compiler checkout\n')
  self.contract=pb.fingerprint(self.root)
  self.manifest={**self.contract,'compiler_artifacts':{n:'1'*64 for n in ['sslc.mjs','sslc.wasm']},'outputs':[]}
  for script in self.contract['scripts']:
   path=pb.PREBUILT+'/scripts/'+script['stem']+'.int';p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(BLOB)
   self.manifest['outputs'].append({'path':path,'size':len(BLOB),'sha256':pb.sha(BLOB),'source':script['source']})
  self.save()
 def save(self):
  (self.root/pb.PREBUILT/'manifest.json').write_text(json.dumps(self.manifest)+'\n')
 def validate(self,**args):return pb.validate(self.root,**args)
 def bad(self):
  with self.assertRaises(pb.PrebuiltError):self.validate()
 def fake_compile(self,root,contract):
  folder=self.root/'build/fresh-synthetic';folder.mkdir(parents=True)
  for s in contract['scripts']:(folder/(s['stem']+'.int')).write_bytes(BLOB)
  return folder,{'sslc.mjs':'2'*64,'sslc.wasm':'3'*64}
 def test_40_roots_49_closure_no_node(self):
  with patch.object(pb.shutil,'which',return_value=None):
   self.assertEqual(len(self.validate()['inputs']),49)
   out=self.root/'output/scripts';self.assertEqual(pb.copy_verified(self.root,out),40)
   self.assertEqual(len(list(out.iterdir())),40)
   self.assertEqual(pb.copy_verified(self.root,out),40)
 def test_changed_ssl(self):
  with (self.root/pb.SCRIPTS/'s00.ssl').open('a') as f:f.write('// changed\n')
  self.bad()
 def test_changed_own_header(self):
  (self.root/pb.SCRIPTS/'mgcore.h').write_text('// changed\n');self.bad()
 def test_changed_generated_header(self):
  (self.root/pb.HEADERS/'pids.h').write_text('// changed\n');self.bad()
 def test_new_include_dependency(self):
  (self.root/pb.SCRIPTS/'new.h').write_text('// new\n')
  with (self.root/pb.SCRIPTS/'mgcore.h').open('a') as f:f.write('#include "new.h"\n')
  self.assertEqual(len(pb.fingerprint(self.root)['inputs']),50);self.bad()
 def test_inactive_branch_include_discovered(self):
  (self.root/pb.SCRIPTS/'new.h').write_text('// new\n')
  (self.root/pb.SCRIPTS/'mgcore.h').write_text('#if 0\n#include "new.h"\n#endif\n')
  self.assertEqual(len(pb.fingerprint(self.root)['inputs']),50)
 def test_commented_include_ignored(self):
  (self.root/pb.SCRIPTS/'mgcore.h').write_text('/*\n#include "missing.h"\n*/\n// #include "no.h"\n')
  self.assertEqual(len(pb.fingerprint(self.root)['inputs']),49)
 def test_dynamic_include_refused(self):
  (self.root/pb.SCRIPTS/'mgcore.h').write_text('#include HEADER\n');self.bad()
 def test_angle_include_refused(self):
  (self.root/pb.SCRIPTS/'mgcore.h').write_text('#include <pids.h>\n');self.bad()
 def test_alternate_preprocessor_refused(self):
  (self.root/pb.SCRIPTS/'mgcore.h').write_text('%:include "new.h"\n');self.bad()
 def test_continuation_include_is_found(self):
  (self.root/pb.SCRIPTS/'new.h').write_text('// new\n')
  (self.root/pb.SCRIPTS/'mgcore.h').write_text('#inc\\\nlude "new.h"\n')
  self.assertEqual(len(pb.fingerprint(self.root)['inputs']),50)
 def test_ambiguous_header_refused(self):
  (self.root/pb.SCRIPTS/'pids.h').write_text('// shadow\n');self.bad()
 def test_outside_include_refused(self):
  (self.root/pb.SCRIPTS/'mgcore.h').write_text('#include "../registry.py"\n');self.bad()
 def test_crlf_header_refused(self):
  (self.root/pb.HEADERS/'pids.h').write_bytes(b'// generated\r\n');self.bad()
 def test_machine_macro_refused(self):
  (self.root/pb.SCRIPTS/'mgcore.h').write_text('#define BAD __FILE__\n');self.bad()
 def test_missing_header_refused(self):
  p=self.root/pb.HEADERS/'pids.h';p.rename(p.with_suffix('.preserved'));self.bad()
 def test_source_symlink_refused(self):
  p=self.root/pb.SCRIPTS/'s00.ssl';q=p.with_suffix('.preserved');p.rename(q);p.symlink_to(q.name);self.bad()
 def test_parent_symlink_refused(self):
  p=self.root/pb.HEADERS;q=p.with_name('headers-preserved');p.rename(q);p.symlink_to(q.name);self.bad()
 def test_stage_defines_only_source_guards(self):
  for args in ({'stage':'stage.py'},{'defines':['X=1']},{'only':[]},{'source_dirs':[self.root/'elsewhere']}):
   with self.subTest(args=args),self.assertRaises(pb.PrebuiltError):self.validate(**args)
  self.validate(source_dirs=[self.root/pb.SCRIPTS])
 def test_registry_reorder_refused(self):
  p=self.root/'mod/megaton/registry.py';p.write_text(p.read_text().replace("'s00'","'swap'").replace("'s01'","'s00'").replace("'swap'","'s01'"));self.bad()
 def test_registry_local_vars_change(self):
  p=self.root/'mod/megaton/registry.py';p.write_text(p.read_text().replace('LOCAL_VARS = 0','LOCAL_VARS = 1'));self.bad()
 def test_profile_change(self):
  self.manifest['profile']['flags'][-1]='-s';self.save();self.bad()
 def test_private_path_rejection_survives_pattern_refactor(self):
  reader=SimpleNamespace(IntError=ValueError)
  values=[b'/'+name+b'/fixture' for name in (b'Users',b'home',b'Volumes',b'private')]
  values += [b'Q:'+bytes([92])+b'fixture', b'file'+b'://fixture', b'10.'+b'1.2.3', b'fixture'+b'@example.invalid']
  for value in values:
   reader.IntFile=lambda data,name:SimpleNamespace(lint=lambda:[],local_vars_needed=lambda:0,identifiers={},strings={0:data.decode('ascii')})
   with self.subTest(sample_hash=pb.sha(value)), patch.object(pb,'load_module',return_value=reader), self.assertRaises(pb.PrebuiltError):
    pb.check_bytecode(self.root,value,'synthetic.int',0)
  with patch.object(pb,'load_module',return_value=reader):
   pb.check_bytecode(self.root,b'ordinary local text','synthetic.int',0)
 def test_wrapper_change(self):
  (self.root/'tools/ssl.py').write_text('# changed wrapper\n');self.bad()
 def test_source_hash_tamper(self):
  self.manifest['source_sha256']='0'*64;self.save();self.bad()
 def test_output_corruption(self):
  (self.root/pb.PREBUILT/'scripts/s00.int').write_bytes(b'broken');self.bad()
 def test_missing_output(self):
  p=self.root/pb.PREBUILT/'scripts/s00.int';p.rename(self.root/'saved.int');self.bad()
 def test_extra_output(self):
  (self.root/pb.PREBUILT/'scripts/extra.int').write_bytes(BLOB);self.bad()
 def test_duplicate_output_record(self):
  self.manifest['outputs'][-1]=copy.deepcopy(self.manifest['outputs'][0]);self.save();self.bad()
 def test_manifest_duplicate_key(self):
  p=self.root/pb.PREBUILT/'manifest.json';p.write_text(p.read_text().replace('{','{"schema":1,',1));self.bad()
 def test_output_symlink(self):
  p=self.root/pb.PREBUILT/'scripts/s00.int';q=self.root/'saved.int';p.rename(q);p.symlink_to(q);self.bad()
 def test_all_validate_before_any_copy(self):
  (self.root/pb.PREBUILT/'scripts/s39.int').write_bytes(b'broken');out=self.root/'new-output'
  with self.assertRaises(pb.PrebuiltError):pb.copy_verified(self.root,out)
  self.assertFalse(out.exists())
 def test_destination_conflict_preserved(self):
  out=self.root/'output';out.mkdir();p=out/'s00.int';p.write_bytes(b'previous')
  with self.assertRaises(pb.PrebuiltError):pb.copy_verified(self.root,out)
  self.assertEqual(p.read_bytes(),b'previous');self.assertEqual(len(list(out.iterdir())),1)
 def test_verify_fresh_equal_never_writes_prebuilt(self):
  before=(self.root/pb.PREBUILT/'manifest.json').read_bytes()
  with patch.object(pb,'compile_all',side_effect=self.fake_compile):self.assertEqual(pb.verify(self.root)['scripts'],40)
  self.assertEqual(before,(self.root/pb.PREBUILT/'manifest.json').read_bytes())
 def test_verify_fresh_mismatch(self):
  data=minimal_int(0x8011);p=self.root/pb.PREBUILT/'scripts/s00.int';p.write_bytes(data)
  self.manifest['outputs'][0].update(size=len(data),sha256=pb.sha(data));self.save()
  with patch.object(pb,'compile_all',side_effect=self.fake_compile),self.assertRaises(pb.PrebuiltError):pb.verify(self.root)
  self.assertEqual(p.read_bytes(),data)
 def test_verify_compiler_failure_no_fallback(self):
  with patch.object(pb,'compile_all',side_effect=pb.PrebuiltError('compiler unavailable')),self.assertRaises(pb.PrebuiltError):pb.verify(self.root)
 def test_write_preserves_previous(self):
  old=(self.root/pb.PREBUILT/'manifest.json').read_bytes()
  with patch.object(pb,'compile_all',side_effect=self.fake_compile):self.assertEqual(pb.write(self.root)['scripts'],40)
  saved=list((self.root/'build/prebuilt-history').glob('*/manifest.json'))
  self.assertEqual(len(saved),1);self.assertEqual(saved[0].read_bytes(),old)
 def test_write_compare_failure_preserves_current(self):
  old=(self.root/pb.PREBUILT/'manifest.json').read_bytes()
  with patch.object(pb,'compile_all',side_effect=self.fake_compile),self.assertRaises(pb.PrebuiltError):pb.write(self.root,self.root/'no-frozen-copy')
  self.assertEqual((self.root/pb.PREBUILT/'manifest.json').read_bytes(),old)
 def test_compiler_pin_mismatch_refused_without_launch(self):
  with patch.object(pb.shutil,'which',return_value='/synthetic/node'),patch.object(pb.subprocess,'run',return_value=type('P',(),{'stdout':'wrong\n'})()),self.assertRaises(pb.PrebuiltError):pb.compiler_identity(self.root)
 def test_compiler_dirty_refused_without_launch(self):
  values=iter([pb.PIN,pb.PIN,' M changed.c'])
  with patch.object(pb.shutil,'which',return_value='/synthetic/node'),patch.object(pb.subprocess,'run',side_effect=lambda *a,**k:type('P',(),{'stdout':next(values)})()),self.assertRaises(pb.PrebuiltError):pb.compiler_identity(self.root)
 def test_compiler_clean_pin_runtime_hashes(self):
  values=iter([pb.PIN,pb.PIN,''])
  with patch.object(pb.shutil,'which',return_value='/synthetic/node'),patch.object(pb.subprocess,'run',side_effect=lambda *a,**k:type('P',(),{'stdout':next(values)})()):
   self.assertEqual(set(pb.compiler_identity(self.root)),{'sslc.mjs','sslc.wasm'})

class TestPriorityPortability(unittest.TestCase):
 def invoke(self, platform_os):
  output, error = io.StringIO(), io.StringIO()
  with patch.object(pb, 'os', platform_os), patch.object(pb.sys, 'argv', ['prebuilt.py', 'verify']), patch.object(pb, 'verify', return_value={'scripts': 40}) as verify, redirect_stdout(output), redirect_stderr(error):
   result = pb.main()
  return result, verify.call_count, error.getvalue()
 def test_absent_priority_api_still_runs_explicit_command(self):
  for platform_os in (SimpleNamespace(), SimpleNamespace(PRIO_PROCESS=0), SimpleNamespace(setpriority=Mock())):
   with self.subTest(attributes=vars(platform_os)):
    self.assertEqual(self.invoke(platform_os), (0, 1, ''))
    if hasattr(platform_os, 'setpriority'):
     platform_os.setpriority.assert_not_called()
 def test_available_priority_api_is_used(self):
  priority = Mock()
  self.assertEqual(self.invoke(SimpleNamespace(setpriority=priority, PRIO_PROCESS=7)), (0, 1, ''))
  priority.assert_called_once_with(7, 0, 15)
 def test_real_priority_failure_is_not_suppressed(self):
  priority = Mock(side_effect=PermissionError('synthetic priority failure'))
  status, calls, error = self.invoke(SimpleNamespace(setpriority=priority, PRIO_PROCESS=7))
  self.assertEqual((status, calls), (2, 0))
  self.assertIn('Filesystem or priority operation failed', error)

if __name__=='__main__':
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case) for case in (TestPrebuilt, TestPriorityPortability))
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 report={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'status':'PASS' if result.wasSuccessful() else 'FAIL','scope':'Synthetic source/header/INT fixtures only; compile and Git/Node calls mocked; no real compilation or stage/live mutation.','evidence_directory':EVIDENCE.name}
 destination=EVIDENCE/'synthetic-results.json' if BASE.name=='tests' else BASE/'synthetic-results.json'
 destination.write_text(json.dumps(report,indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
