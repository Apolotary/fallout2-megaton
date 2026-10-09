# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Synthetic helper checks; no game builds or source writes."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(os.environ.get('MEGATON_TEST_ROOT', Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(SOURCE/'tools'), str(SOURCE/'mod/megaton-art')]
import pipeline
from f2lib.frm import Frm, Frame
from pipeline.tiles import stock_mask
import numpy as np

candidate = Path(__file__).with_name('clone_assets.py')
if not candidate.is_file():
    candidate = SOURCE/'mod/megaton-art/pipeline/clone_assets.py'
spec = importlib.util.spec_from_file_location('pipeline.clone_assets_candidate', candidate)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    return {
        'pieces': {'box': {'parts': [{'type':'scenery','slot':0,'layer':'main','hex':[0,0],
                                    'frm':'mgs0000.frm','frames':1,'shift':[0,0],'size':[2,2]}]}},
        'slots': {'scenery':[{'key':'box/main/0,0'}], 'wall':[]},
        'tiles': {'first_index':3,
                  'slots':[{'key':'blank'},{'key':'roof/0,0'},{'key':'paint/0,0@ground'},{'key':'paint/1,0@mgt0002'}],
                  'sheets':{'roof':{'decal':False,'size':[1,1],'grid':[[4]]},
                            'paint':{'decal':True,'size':[2,1],'cells':[[0,0],[1,0]]}}},
    }


def form(width, height, pixels):
    frm = Frm(); frm.stored = [[Frame(width,height,pixels)]]
    return frm.to_bytes()


class CloneAssetChecks(unittest.TestCase):
    def make_tree(self):
        art=Path(tempfile.mkdtemp(prefix='own-art-check-'))
        manifest=fixture(); raw=(json.dumps(manifest)+'\n').encode()
        (art/'manifest.json').write_bytes(raw)
        own, _=module.expected_assets(manifest)
        rows=[]
        for name,(kind,desc) in own.items():
            if kind=='part': blob=form(2,2,b'\x01\x02\x03\x04')
            else:
                pixels=np.zeros((36,80),np.uint8); pixels[18,40]=11
                blob=form(80,36,pixels.tobytes())
            path=art/'sprites'/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(blob)
            rows.append({'path':name,'size':len(blob),'sha256':module.digest(blob)})
        inventory={'version':1,'recipe':'indexed_cells_v1','source_manifest_sha256':module.digest(raw),'files':rows}
        (art/'sprites/manifest.json').write_text(json.dumps(inventory))
        return art,manifest,raw,inventory

    def test_exact_own_set(self):
        art,manifest,raw,_=self.make_tree()
        assets,composites=module.load_assets(art,raw,manifest)
        self.assertEqual(len(assets),4);self.assertEqual(len(composites),2)
        self.assertEqual(module.dependency_order(manifest['tiles']['slots'],composites),[2,3])

    def test_retired_live_part(self):
        m=fixture();m['slots']['scenery'][0]['retired']=True
        with self.assertRaises(module.AssetError):module.expected_assets(m)

    def test_duplicate_live_part(self):
        m=fixture();m['pieces']['box']['parts']*=2
        with self.assertRaises(module.AssetError):module.expected_assets(m)

    def test_wrong_slot_filename(self):
        m=fixture();m['pieces']['box']['parts'][0]['frm']='mgw0000.frm'
        with self.assertRaises(module.AssetError):module.expected_assets(m)

    def test_undeclared_decal(self):
        m=fixture();m['tiles']['sheets']['paint']['cells']=[[0,0]]
        with self.assertRaises(module.AssetError):module.expected_assets(m)

    def test_cycle(self):
        m=fixture();m['tiles']['slots'][2]['key']='paint/0,0@mgt0003'
        _,c=module.expected_assets(m)
        with self.assertRaises(module.AssetError):module.dependency_order(m['tiles']['slots'],c)

    def test_missing_dependency(self):
        m=fixture();m['tiles']['slots'][2]['key']='paint/0,0@mgt9999'
        _,c=module.expected_assets(m)
        with self.assertRaises(module.AssetError):module.dependency_order(m['tiles']['slots'],c)

    def test_manifest_change_refused(self):
        art,m,raw,_=self.make_tree()
        with self.assertRaises(module.AssetError):module.load_assets(art,raw+b' ',m)

    def test_corrupt_sprite(self):
        art,m,raw,_=self.make_tree();path=art/'sprites/scenery/mgs0000.frm';path.write_bytes(path.read_bytes()+b'bad')
        with self.assertRaises(module.AssetError):module.load_assets(art,raw,m)

    def test_extra_file_refused(self):
        art,m,raw,_=self.make_tree();(art/'sprites/extra.frm').write_bytes(b'not reviewed')
        with self.assertRaises(module.AssetError):module.load_assets(art,raw,m)

    def test_symlink_refused(self):
        art,m,raw,_=self.make_tree();(art/'sprites/alias.frm').symlink_to('scenery/mgs0000.frm')
        with self.assertRaises(module.AssetError):module.load_assets(art,raw,m)

    def test_reviewed_but_invalid_cell_refused(self):
        art,m,raw,inventory=self.make_tree();name='decals/paint/0-0.frm'
        path=art/'sprites'/name;frm=Frm.from_bytes(path.read_bytes());pixels=bytearray(frm.frame().pixels);pixels[0]=9;frm.frame().pixels=bytes(pixels);blob=frm.to_bytes();path.write_bytes(blob)
        row=next(x for x in inventory['files'] if x['path']==name);row.update(size=len(blob),sha256=module.digest(blob))
        (art/'sprites/manifest.json').write_text(json.dumps(inventory))
        with self.assertRaises(module.AssetError):module.load_assets(art,raw,m)


if __name__=='__main__': unittest.main()
