#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Offline regression checks for door-click log parsing; no game files needed."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('art_runner_under_test', Path(__file__).with_name('run_all.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

DOOR = 0x02000352
OTHER_DOOR = 0x02000196
PIPE = 0x02000AE1
PROTOS = {DOOR: SimpleNamespace(subtype_name='door'), OTHER_DOOR: SimpleNamespace(subtype_name='door'),
          PIPE: SimpleNamespace(subtype_name='generic')}


def obj(number, frame=0, flags=0, tile=18470):
    return (f'[autotest] obj tile={tile} pid=0x{number:08X} fid=0x02000000 '
            f'flags=0x{flags:08X} sid=-1 rot=0 frame={frame} x=0 y=0 name=Synthetic')


def samples(before, after):
    return ['[autotest] CLICK door-plant BEFORE', *before,
            '[autotest] CLICK door-plant AFTER', *after]


class ClickOutcomeTests(unittest.TestCase):
    def parse(self, before, after, protos=PROTOS):
        return runner.click_outcomes(samples(before, after), protos)['door-plant']

    def test_observed_overhead_order_swap_does_not_hide_opening(self):
        # Reproduces the failed comparison: the pipe was last BEFORE and first AFTER.
        closed = obj(DOOR)
        pipe = obj(PIPE, flags=0xA0008010)
        opened = obj(DOOR, frame=7, flags=0xA0000010)
        self.assertEqual(self.parse([closed, pipe], [pipe, opened]), 'worked')

    def test_order_and_unrelated_animated_scenery_do_not_matter(self):
        for reverse_before in (False, True):
            for reverse_after in (False, True):
                before = [obj(DOOR), obj(PIPE, frame=1, flags=0xA0008010)]
                after = [obj(DOOR, frame=7, flags=0xA0000010), obj(PIPE, frame=2, flags=0xA0008010)]
                if reverse_before:
                    before.reverse()
                if reverse_after:
                    after.reverse()
                self.assertEqual(self.parse(before, after), 'worked')

    def test_foreign_scenery_changes_cannot_create_false_success(self):
        self.assertEqual(self.parse([obj(DOOR), obj(PIPE)], [obj(DOOR), obj(PIPE, frame=1, flags=0xA0008010)]), 'nothing')

    def test_mid_swing_frame_is_an_opening_even_before_flag_change(self):
        self.assertEqual(self.parse([obj(DOOR)], [obj(DOOR, frame=1)]), 'worked')

    def test_absent_door_fails_closed(self):
        self.assertEqual(self.parse([obj(PIPE)], [obj(PIPE)]), 'invalid')

    def test_ambiguous_or_duplicate_doors_fail_closed(self):
        for before in ([obj(DOOR), obj(OTHER_DOOR)], [obj(DOOR), obj(DOOR)]):
            self.assertEqual(self.parse(before, [obj(DOOR, frame=7)]), 'invalid')

    def test_door_identity_must_match_in_both_phases(self):
        self.assertEqual(self.parse([obj(DOOR)], [obj(OTHER_DOOR, frame=7)]), 'invalid')
        self.assertEqual(self.parse([obj(DOOR)], [obj(DOOR, frame=7, tile=18471)]), 'invalid')

    def test_missing_phase_fails_closed(self):
        lines = ['[autotest] CLICK door-plant BEFORE', obj(DOOR)]
        self.assertEqual(runner.click_outcomes(lines, PROTOS)['door-plant'], 'invalid')

    def test_unknown_scenery_prototype_fails_closed(self):
        self.assertEqual(self.parse([obj(0x02009999)], [obj(0x02009999, frame=7)]), 'invalid')

    def test_dialogue_target_still_uses_dialog_state(self):
        lines = ['[autotest] CLICK talk-synthetic BEFORE', '[autotest] state map=X dialog=0',
                 '[autotest] CLICK talk-synthetic AFTER', '[autotest] state map=X dialog=1']
        self.assertEqual(runner.click_outcomes(lines, PROTOS), {'talk-synthetic': 'worked'})


if __name__ == '__main__':
    unittest.main()
