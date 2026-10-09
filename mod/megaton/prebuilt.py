#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Verified production-only Megaton bytecode; no compiler is needed to validate/copy.

Developer commands: prebuilt.py verify | write [--compare-dir FROZEN_SCRIPTS].
No compiler download, engine execution, or normal output-tree mutation occurs.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import uuid

sys.dont_write_bytecode = True
SCHEMA = 1
COUNT = 40
PIN = '3991207639c133bd14948fae6c18df59310b5287'
TAG = '2026-09-17-13-26-18'
SCRIPTS = 'mod/megaton/scripts'
HEADERS = 'mod/scripts_src/headers'
PREBUILT = 'mod/megaton/prebuilt'
INCLUDE_DIRS = [HEADERS, SCRIPTS]


class PrebuiltError(RuntimeError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def safe_file(root, relative):
    """Reject traversal, symlinks (including parent dirs), and wrong-case paths."""
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise PrebuiltError('Invalid relative prebuilt path')
    parts = PurePosixPath(relative).parts
    if PurePosixPath(relative).is_absolute() or any(p in ('.', '..') for p in parts) or '/'.join(parts) != relative:
        raise PrebuiltError('Invalid relative prebuilt path')
    current = Path(root).resolve()
    for part in parts:
        if not current.is_dir() or part not in {p.name for p in current.iterdir()}:
            raise PrebuiltError('Missing or wrong-case input: ' + relative)
        current = current/part
        if current.is_symlink():
            raise PrebuiltError('Symlink input is not permitted: ' + relative)
    if not current.is_file():
        raise PrebuiltError('Ordinary file required: ' + relative)
    return current


def read_source(root, relative):
    data = safe_file(root, relative).read_bytes()
    if b'\r' in data:
        raise PrebuiltError('LF-only source required; rerun setup for generated headers: ' + relative)
    if b'\0' in data:
        raise PrebuiltError('NUL byte in source: ' + relative)
    try:
        return data, data.decode('utf-8')
    except UnicodeDecodeError as error:
        raise PrebuiltError('UTF-8 source required: ' + relative) from error


def without_comments(text):
    # Join preprocessor continuation lines before recognizing comments/directives.
    text = text.replace('\\\n', '')
    pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/'
    return re.sub(pattern, lambda m: re.sub(r'[^\n]', ' ', m[0]) if m[0].startswith(('//', '/*')) else m[0], text)


def production_scripts(root):
    _, source = read_source(root, 'mod/megaton/registry.py')
    values = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('SCRIPTS', 'LOCAL_VARS'):
                    if target.id in values:
                        raise PrebuiltError('Duplicate script registry assignment')
                    try:
                        values[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError) as error:
                        raise PrebuiltError('Script registry must use literal production values') from error
    rows, local_vars = values.get('SCRIPTS'), values.get('LOCAL_VARS')
    if not isinstance(rows, list) or len(rows) != COUNT or type(local_vars) is not int or local_vars < 0:
        raise PrebuiltError('Exactly 40 registered production scripts and a local-var count are required')
    stems = []
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) != 3 or not isinstance(row[0], str) or not re.fullmatch('[a-z][a-z0-9_]{0,7}', row[0]):
            raise PrebuiltError('Invalid production script registry')
        stems.append(row[0])
    if len(set(stems)) != COUNT:
        raise PrebuiltError('Duplicate production script stem')
    _, ids = read_source(root, SCRIPTS+'/ids.h')
    found = re.findall(r'^\s*#\s*define\s+SCRIPT_([A-Z0-9_]+)\s+\((\d+)\)\s*$', without_comments(ids), re.M)
    numbers = {stem.lower():int(number) for stem, number in found}
    if len(found) != len(numbers) or set(numbers) != set(stems):
        raise PrebuiltError('Generated script IDs do not match the registry; rerun setup')
    ordered = [numbers[stem] for stem in stems]
    if ordered[0] < 1 or ordered != list(range(ordered[0], ordered[0]+COUNT)):
        raise PrebuiltError('Generated script IDs are not in registry order')
    return [{'stem':stem, 'number':numbers[stem], 'local_vars':local_vars, 'source':SCRIPTS+'/'+stem+'.ssl'} for stem in stems]


def discover_inputs(root, scripts):
    """Visit literal includes in every branch, rejecting ambiguity and dynamic includes."""
    pending = [s['source'] for s in scripts]
    visited = {}
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        if not any(relative.startswith(prefix+'/') for prefix in (SCRIPTS, HEADERS)):
            raise PrebuiltError('Compiler dependency outside permitted source roots')
        data, text = read_source(root, relative)
        clean = without_comments(text)
        if re.search(r'\b__(?:FILE|DATE|TIME|TIMESTAMP)__\b', clean):
            raise PrebuiltError('Machine-dependent compiler macro: ' + relative)
        if '??' in clean or re.search(r'^\s*%:',clean,re.M):
            raise PrebuiltError('Alternate preprocessor spellings are unsupported: ' + relative)
        visited[relative] = {'path':relative, 'size':len(data), 'sha256':sha(data)}
        for line in clean.splitlines():
            directive = re.match(r'^\s*#\s*(include\w*|import)\b(.*)$', line)
            if not directive:
                continue
            match = re.fullmatch(r'\s*"([^"\n]+)"\s*', directive[2])
            if directive[1] != 'include' or not match:
                raise PrebuiltError('Only literal quoted includes are supported: ' + relative)
            name = match[1]
            if PurePosixPath(name).is_absolute() or '\\' in name or any(p in ('.','..') for p in PurePosixPath(name).parts):
                raise PrebuiltError('Unsafe include path: ' + relative)
            candidates = []
            for directory in [str(PurePosixPath(relative).parent)]+INCLUDE_DIRS:
                candidate = directory+'/'+name
                if candidate in candidates:
                    continue
                path = Path(root)/candidate
                if path.exists() or path.is_symlink():
                    safe_file(root, candidate)
                    candidates.append(candidate)
            if len(candidates) != 1:
                raise PrebuiltError('Missing or ambiguous include in: ' + relative)
            pending.append(candidates[0])
    return [visited[p] for p in sorted(visited)]


def fingerprint(root):
    scripts = production_scripts(root)
    profile = {'compiler':{'url':'https://github.com/sfall-team/sslc', 'tag':TAG, 'commit':PIN},
               'flags':['-q','-l','-p','-F','-O2','-n'], 'defines':[], 'include_dirs':INCLUDE_DIRS,
               'wrapper_sha256':sha(safe_file(root, 'tools/ssl.py').read_bytes())}
    core = {'schema':SCHEMA, 'profile':profile, 'scripts':scripts, 'inputs':discover_inputs(root, scripts)}
    return {**core, 'source_sha256':sha(canonical(core))}


def production_only(root, *, stage=None, defines=(), source_dirs=None, only=None):
    if stage is not None or defines or only is not None:
        raise PrebuiltError('Production prebuilts cannot be used for stage, define or partial-script overrides')
    if source_dirs is not None and list(map(lambda p:Path(p).absolute(), source_dirs)) != [Path(root).absolute()/SCRIPTS]:
        raise PrebuiltError('Production prebuilts cannot use source-directory overrides')


def unique_object(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise PrebuiltError('Duplicate key in prebuilt manifest')
        result[key] = value
    return result


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_bytecode(root, data, name, local_vars):
    reader = load_module('megaton_prebuilt_intfile', safe_file(root, 'tools/intfile.py'))
    try:
        script = reader.IntFile(data, name)
        warnings = script.lint()
        if warnings or script.local_vars_needed() > local_vars:
            raise PrebuiltError('Compiled script fails VM/local-var validation: ' + name)
    except (ValueError, struct.error, reader.IntError) as error:
        raise PrebuiltError('Unreadable compiled script: ' + name) from error
    # Scan raw bytes and decoded tables. Full release privacy scanning remains separate.
    values = [data]+[s.encode('utf-8') for table in (script.identifiers, script.strings) for s in table.values()]
    private = rb'(?i)(?:/' + rb'(?:Users|home|Volumes|private)/|file://|[a-z]:[\\/]|192\.168\.\d{1,3}\.|10\.\d{1,3}\.\d{1,3}\.|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})'
    if any(re.search(private, value) for value in values):
        raise PrebuiltError('Compiled script contains a machine-path/private-address pattern: ' + name)


def _validated(root, **guards):
    production_only(root, **guards)
    root = Path(root).resolve()
    current = fingerprint(root)
    try:
        manifest = json.loads(safe_file(root, PREBUILT+'/manifest.json').read_text(), object_pairs_hook=unique_object)
    except json.JSONDecodeError as error:
        raise PrebuiltError('Invalid prebuilt manifest JSON') from error
    expected_keys = set(current)|{'outputs','compiler_artifacts'}
    if not isinstance(manifest,dict) or set(manifest) != expected_keys or any(manifest.get(k) != v for k,v in current.items()):
        raise PrebuiltError('Prebuilt scripts do not match these sources; install the script compiler and rebuild')
    artifacts=manifest['compiler_artifacts']
    if not isinstance(artifacts,dict) or set(artifacts)!={'sslc.mjs','sslc.wasm'} or any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in artifacts.values()):
        raise PrebuiltError('Invalid compiler provenance hashes')
    expected = {PREBUILT+'/scripts/'+s['stem']+'.int':s for s in current['scripts']}
    records = manifest.get('outputs')
    if not isinstance(records, list) or len(records) != COUNT:
        raise PrebuiltError('Prebuilt manifest must contain exactly 40 outputs')
    if any(not isinstance(r,dict) or set(r)!={'path','size','sha256','source'} or
           not isinstance(r['path'],str) or not isinstance(r['source'],str) or not isinstance(r['sha256'],str) for r in records):
        raise PrebuiltError('Invalid prebuilt output record')
    if {r['path'] for r in records} != set(expected):
        raise PrebuiltError('Prebuilt output set is missing, extra or duplicated')
    directory = root/PREBUILT/'scripts'
    if directory.is_symlink() or not directory.is_dir() or {p.name for p in directory.iterdir()} != {Path(p).name for p in expected}:
        raise PrebuiltError('Prebuilt scripts directory must contain exactly the 40 expected files')
    payloads = {}
    for record in records:
        relative=record['path']; script=expected[relative]
        data=safe_file(root, relative).read_bytes()
        if record['source']!=script['source'] or type(record['size']) is not int or record['size']!=len(data) or record['sha256']!=sha(data):
            raise PrebuiltError('Prebuilt output hash/source mismatch: '+relative)
        check_bytecode(root,data,relative,script['local_vars'])
        payloads[script['stem']+'.int']=data
    return manifest,payloads


def validate(root, **guards):
    """Validate all source/profile/registry/output bytes; requires no Node/compiler."""
    return _validated(root, **guards)[0]


def copy_verified(root, destination, **guards):
    """Validate all40 first. Never overwrite a different existing destination file."""
    manifest,payloads=_validated(root, **guards)
    destination=Path(destination).absolute()
    for path in [destination]+list(destination.parents):
        if path.is_symlink():
            raise PrebuiltError('Destination cannot contain symlinks')
    for name,data in payloads.items():
        target=destination/name
        if target.exists() and (not target.is_file() or target.read_bytes()!=data):
            raise PrebuiltError('Use a clean build output; differing destination exists: '+name)
    destination.mkdir(parents=True,exist_ok=True)
    for name,data in payloads.items():
        target=destination/name
        if not target.exists():
            with target.open('xb') as stream:
                stream.write(data)
    return len(payloads)


def compiler_identity(root):
    """Verify checkout pin/clean tracked files; record, do not claim provenance of, runtime hashes."""
    root=Path(root).resolve()
    if not shutil.which('node'):
        raise PrebuiltError('Pinned script compiler requires Node on PATH')
    checkout=root/'tools/sslc'
    if checkout.is_symlink():
        raise PrebuiltError('Compiler checkout cannot be a symlink')
    safe_file(root,'tools/sslc/CMakeLists.txt')
    try:
        run=lambda *args:subprocess.run(['git','-C',str(checkout),*args],check=True,capture_output=True,text=True).stdout.strip()
        if run('rev-parse','HEAD')!=PIN or run('rev-parse','refs/tags/'+TAG+'^{commit}') != PIN:
            raise PrebuiltError('Script compiler checkout/tag does not match the pinned commit')
        if run('status','--porcelain','--untracked-files=no'):
            raise PrebuiltError('Script compiler checkout has tracked modifications')
    except (subprocess.CalledProcessError,FileNotFoundError) as error:
        raise PrebuiltError('Pinned script compiler checkout is unavailable') from error
    return {name:sha(safe_file(root,'tools/sslc/build/bin/'+name).read_bytes()) for name in ('sslc.mjs','sslc.wasm')}


def compile_all(root, contract):
    """Called only by explicit verify/write; preserves scratch evidence in ignored build/."""
    root=Path(root).resolve()
    identity=compiler_identity(root)
    if fingerprint(root)!=contract:
        raise PrebuiltError('Compilation inputs changed before compilation')
    folder=root/'build'/('prebuilt-check-'+uuid.uuid4().hex)
    folder.mkdir(parents=True)
    oldpath=list(sys.path)
    try:
        sys.path.insert(0,str(root/'tools'))
        wrapper=load_module('megaton_prebuilt_ssl',safe_file(root,'tools/ssl.py'))
        for script in contract['scripts']:
            target=folder/(script['stem']+'.int')
            try:
                parsed,diagnostics=wrapper.compile_ssl(str(root/script['source']),str(target),
                    include_dirs=[str(root/p) for p in INCLUDE_DIRS],defines=(),optimize=2,short_circuit=False,warnings=False)
            except Exception as error:
                # Keep the compiler's exact diagnostic outside the proposed repository.
                # The manifest and public-facing error contain no machine path.
                with tempfile.NamedTemporaryFile(prefix='megaton-prebuilt-compile-',suffix='.log',mode='w',delete=False) as log:
                    log.write(str(error)+'\n')
                raise PrebuiltError('Fresh compilation failed: '+script['source']+'; local diagnostic '+Path(log.name).name) from error
            if diagnostics:
                with tempfile.NamedTemporaryFile(prefix='megaton-prebuilt-diagnostics-',suffix='.log',mode='w',delete=False) as log:
                    log.write('\n'.join(diagnostics)+'\n')
            check_bytecode(root,target.read_bytes(),script['stem']+'.int',script['local_vars'])
    finally:
        sys.path[:]=oldpath
    if fingerprint(root)!=contract or compiler_identity(root)!=identity:
        raise PrebuiltError('Source/compiler changed during compilation')
    return folder,identity


def verify(root):
    manifest,payloads=_validated(root)
    contract={k:manifest[k] for k in ('schema','profile','scripts','inputs','source_sha256')}
    folder,_=compile_all(root,contract)
    for name,expected in payloads.items():
        if (folder/name).read_bytes()!=expected:
            raise PrebuiltError('Fresh compilation differs from prebuilt: '+name)
    return {'scripts':len(payloads),'inputs':len(contract['inputs']),'source_sha256':contract['source_sha256']}


def write(root, compare_dir=None):
    root=Path(root).resolve(); contract=fingerprint(root)
    folder,identity=compile_all(root,contract)
    records=[]
    for script in contract['scripts']:
        name=script['stem']+'.int'; data=(folder/name).read_bytes()
        if compare_dir is not None:
            expected=Path(compare_dir)/name
            if expected.is_symlink() or not expected.is_file() or expected.read_bytes()!=data:
                raise PrebuiltError('Fresh output differs from frozen production output: '+name)
        records.append({'path':PREBUILT+'/scripts/'+name,'size':len(data),'sha256':sha(data),'source':script['source']})
    manifest={**contract,'outputs':records,'compiler_artifacts':identity}
    staged=folder/'prebuilt'; (staged/'scripts').mkdir(parents=True)
    for record in records:
        shutil.copyfile(folder/Path(record['path']).name,staged/'scripts'/Path(record['path']).name)
    (staged/'manifest.json').write_bytes(json.dumps(manifest,indent=2,sort_keys=True).encode('ascii')+b'\n')
    target=root/PREBUILT
    if fingerprint(root)!=contract:
        raise PrebuiltError('Compilation inputs changed before recording prebuilts')
    if target.is_symlink():raise PrebuiltError('Prebuilt destination cannot be a symlink')
    for parent in target.parents:
        if parent.is_symlink():raise PrebuiltError('Prebuilt destination parent cannot be a symlink')
    if target.exists():
        history=root/'build/prebuilt-history'/uuid.uuid4().hex; history.parent.mkdir(parents=True,exist_ok=True)
        target.rename(history)
    staged.rename(target)
    validate(root)
    return {'scripts':len(records),'inputs':len(contract['inputs']),'source_sha256':contract['source_sha256']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['verify','write'])
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--compare-dir',type=Path,help='write only: require byte equality with frozen own production INTs')
    args=parser.parse_args()
    if args.command=='verify' and args.compare_dir is not None:parser.error('--compare-dir is for write only')
    try:
        if hasattr(os, 'setpriority') and hasattr(os, 'PRIO_PROCESS'):
            os.setpriority(os.PRIO_PROCESS,0,15)
        result=verify(args.root) if args.command=='verify' else write(args.root,args.compare_dir)
        print(json.dumps(result,sort_keys=True))
        return 0
    except (PrebuiltError,OSError) as error:
        print('prebuilt: '+(str(error) if isinstance(error,PrebuiltError) else 'Filesystem or priority operation failed'),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
