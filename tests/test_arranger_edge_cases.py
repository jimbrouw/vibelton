"""Scaffold planning against edge-case Sets (fixtures under tests/fixtures/arranger-*.json).

Documented planning rules these tests pin down:

* Source clips must be fingerprinted, whole-bar and 1-16 bars long. Anything else
  (e.g. a 2.5-bar loop) is never used as a source - the planner never trims a user clip.
* A source is repeated as whole copies only. A section that is not an exact multiple of
  the loop length keeps its leftover bars empty and reports them in ``gaps``.
* Every destination, section edge and locator sits on a bar line (multiple of 4 beats).
* New copies start at the current arrangement end rounded up to a 16-bar boundary, so
  existing clips are never overlapped, moved or trimmed.
* Group tracks are never a source and never receive copies; stems inside (nested) groups are used.
* Arrangement track automation is not read, copied or extended.
"""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from vibelton import production

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


class ArrangerEdgeCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for target, value in (('vibelton.production.ROOT', root / 'production'),
                              ('vibelton.queue.QUEUE_DIR', root / 'queue')):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.state: dict = {}
        patcher = patch.object(production.queue, 'current_state', side_effect=lambda: self.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def load(self, name: str) -> dict:
        fixture = json.loads((FIXTURES / f'arranger-{name}.json').read_text())
        prod = fixture['production']
        prod.update(session_id='edge-session', revision='edge-rev-' + name)
        self.state = {'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1', 'arrangement_copy_v2'],
                      'session_id': 'edge-session', 'tempo': prod['tempo'], 'metre': prod['metre'],
                      'arrangement_end': prod['arrangement_end'], 'set_path': prod['set_path'], 'production': prod}
        return fixture

    def scaffold(self, genre='House') -> dict:
        return production.create_scaffold_plan({'genre': genre, 'variant_id': 'club-version' if genre == 'House' else None})

    def assert_universal_invariants(self, plan: dict, fixture: dict) -> list[dict]:
        prod = fixture['production']
        tracks = {t['id']: t for t in prod['tracks']}
        action = plan['actions'][0]
        self.assertEqual('apply_arrangement_copies', action['type'])
        by_track = defaultdict(list)
        for copy_spec in action['copies']:
            source_track = tracks[copy_spec['source_track_id']]
            self.assertFalse(source_track['is_group'], 'group tracks must never be sources')
            source = next(c for c in source_track['arrangement_clips'] if c['start_beat'] == copy_spec['source_start_beat'])
            self.assertEqual(0.0, copy_spec['destination_beat'] % 4, 'destination must sit on a bar line')
            self.assertEqual(0.0, source['length'] % 4, 'only whole-bar sources')
            self.assertGreaterEqual(copy_spec['destination_beat'], prod['arrangement_end'], 'must not overlap existing material')
            by_track[copy_spec['source_track_id']].append((copy_spec['destination_beat'], copy_spec['destination_beat'] + source['length']))
        for track_id, spans in by_track.items():
            spans.sort()
            for (_, prev_end), (next_start, _) in zip(spans, spans[1:]):
                self.assertLessEqual(prev_end, next_start + 1e-9, f'copies overlap on {track_id}')
        for locator in plan['locator_definitions']:
            self.assertEqual(0.0, locator['time'] % 4)
        for section in plan['variant']['sections']:
            self.assertEqual(section['start_bar'], int(section['start_bar']))
            self.assertEqual(section['end_bar'], int(section['end_bar']))
        # every copy lies inside the planned arrangement span
        start_beat = (plan['start_bar'] - 1) * 4
        for spans in by_track.values():
            for begin, end in spans:
                self.assertGreaterEqual(begin, start_beat)
                self.assertLessEqual(end, plan['actual_end_bar'] * 4 + 1e-9)
        return action['copies']

    def test_6_and_12_bar_loops_are_tiled_whole_with_gaps_reported(self) -> None:
        for name, loop in (('6-bar-loop', 24.0), ('12-bar-loop', 48.0)):
            with self.subTest(name):
                fixture = self.load(name)
                plan = self.scaffold()
                copies = self.assert_universal_invariants(plan, fixture)
                self.assertTrue(copies)
                for copy_spec in copies:
                    self.assertEqual(0.0, (copy_spec['destination_beat'] - (plan['start_bar'] - 1) * 4) % 4)
                # whole copies only: no copy extends past its section end
                sections = plan['variant']['sections']
                base = (plan['start_bar'] - 1) * 4
                for copy_spec in copies:
                    ends = [base + 4 * s['end_bar'] for s in sections if base + 4 * s['start_bar'] <= copy_spec['destination_beat'] < base + 4 * s['end_bar']]
                    self.assertEqual(1, len(ends))
                    self.assertLessEqual(copy_spec['destination_beat'] + loop, ends[0] + 1e-9)
                # a loop that does not divide a section leaves reported gaps, never trimmed clips
                self.assertTrue(any('unfilled' in gap for gap in plan['gaps']), plan['gaps'])

    def test_2p5_bar_loops_are_never_used_as_sources(self) -> None:
        self.load('2p5-bar-loop')
        with self.assertRaisesRegex(ValueError, 'No fingerprinted'):
            self.scaffold()

    def test_nested_groups_are_skipped_but_their_stems_are_used(self) -> None:
        fixture = self.load('nested-groups')
        plan = self.scaffold()
        copies = self.assert_universal_invariants(plan, fixture)
        used = {c['source_track_id'] for c in copies}
        self.assertTrue({'kick', 'hats'} & used, 'stems inside groups must still be used')
        self.assertFalse(used & {'g-drums', 'g-perc'})

    def test_clip_reported_on_a_group_track_is_ignored(self) -> None:
        fixture = self.load('clip-on-group-track')
        plan = self.scaffold()
        copies = self.assert_universal_invariants(plan, fixture)
        self.assertNotIn('g-drums', {c['source_track_id'] for c in copies})

    def test_track_automation_is_ignored_and_called_out(self) -> None:
        fixture = self.load('track-automation')
        self.assertIn('arrangement_automation', next(t for t in fixture['production']['tracks'] if t['id'] == 'kick'))
        plan = self.scaffold()
        self.assert_universal_invariants(plan, fixture)
        self.assertTrue(any('automation' in w.lower() for w in plan['warnings']), plan['warnings'])

    def test_mixed_audio_and_midi_stems_are_both_scaffolded(self) -> None:
        fixture = self.load('mixed-audio-midi')
        plan = self.scaffold()
        copies = self.assert_universal_invariants(plan, fixture)
        types = {next(t for t in fixture['production']['tracks'] if t['id'] == c['source_track_id'])['type'] for c in copies}
        self.assertEqual({'audio', 'midi'}, types)

    def test_warped_audio_is_planned_in_beats_not_seconds(self) -> None:
        fixture = self.load('warped-audio-other-tempo')
        plan = self.scaffold()
        copies = self.assert_universal_invariants(plan, fixture)
        hats = sorted(c['destination_beat'] for c in copies if c['source_track_id'] == 'hats')
        self.assertTrue(hats)
        for first, second in zip(hats, hats[1:]):
            self.assertIn(second - first, (32.0, 64.0, 96.0, 128.0, 192.0, 256.0), 'steps follow the 32-beat clip, not the 100 BPM tempo')

    def test_planning_never_sends_anything_to_the_bridge(self) -> None:
        """The preview step: a draft plan must exist without any queued Live command."""
        self.load('mixed-audio-midi')
        with patch.object(production.queue, 'enqueue') as enqueue:
            plan = self.scaffold()
        enqueue.assert_not_called()
        self.assertEqual('Draft', plan['status'])
        self.assertTrue(plan['source_coverage'] and plan['variant']['sections'], 'preview needs coverage and sections')

    def test_looped_clips_are_never_chosen_as_sources(self) -> None:
        fixture = self.load('looped-clips')
        plan = self.scaffold()
        copies = self.assert_universal_invariants(plan, fixture)
        chosen = {(c['source_track_id'], c['source_start_beat']) for c in copies}
        self.assertIn(('kick', 72.0), chosen)     # the genuine 16-bar clip is used
        self.assertNotIn(('kick', 0.0), chosen)   # looped to 72 beats: skipped
        self.assertFalse([k for k in chosen if k[0] == 'bass'], 'bass has only a looped clip')

    def test_partly_filled_arrangement_is_never_overlapped(self) -> None:
        fixture = self.load('partly-filled-arrangement')
        plan = self.scaffold()
        copies = self.assert_universal_invariants(plan, fixture)
        self.assertEqual(33, plan['start_bar'])  # ceil(100 / 64) * 64 = 128 beats = bar 33
        self.assertTrue(all(c['destination_beat'] >= 128.0 for c in copies))


if __name__ == '__main__':
    unittest.main()
