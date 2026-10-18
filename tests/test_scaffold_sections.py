"""Scaffold / re-scaffold / roll back a single arrangement section."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import production

try:
    from fake_live import FakeLive
except ImportError:  # run as tests.test_scaffold_sections
    from tests.fake_live import FakeLive

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'arranger-mixed-audio-midi.json'


class ScaffoldSectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for target, value in (('vibelton.production.ROOT', self.root / 'production'),
                              ('vibelton.queue.QUEUE_DIR', self.root / 'queue')):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        prod = json.loads(FIXTURE.read_text())['production']
        prod.update(session_id='live-1', revision='')
        self.state = {'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1', 'arrangement_copy_v2'],
                      'session_id': 'live-1', 'tempo': 124.0, 'metre': [4, 4], 'production': prod}
        self.live = FakeLive(self)
        self.live.seal()
        self.original_tracks = json.loads(json.dumps(prod['tracks']))
        self.enqueued: list[dict] = []
        for name, effect in (('current_state', lambda: self.state),
                             ('enqueue', lambda actions, source: (self.enqueued.append({'actions': actions}) or {'id': 'c%d' % len(self.enqueued)}))):
            patcher = patch.object(production.queue, name, side_effect=effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    SCOPE = {'genre': 'House', 'variant_id': 'club-version'}

    def plan(self, section=None) -> dict:
        payload = {'genre': 'House', 'variant_id': 'club-version'}
        if section:
            payload['section'] = section
        return production.create_scaffold_plan(payload)

    def apply(self, plan) -> dict:
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        result = self.live.process(len(self.enqueued) - 1)
        self.assertEqual('Applied', result['status'], result.get('error'))
        return job

    def rollback(self, **payload) -> dict:
        job = production.rollback({'working_copy_confirmed': True, **self.SCOPE, **payload})
        self.assertEqual('Applied', self.live.process(len(self.enqueued) - 1)['status'])
        return production.job_status(job['id'])

    def section_range(self, plan, name):
        base = (plan['start_bar'] - 1) * 4.0
        sec = next(s for s in plan['variant']['sections'] if s['name'] == name)
        return base + 4 * sec['start_bar'], base + 4 * sec['end_bar']

    def placed(self):
        return sorted((t['id'], c['start_beat']) for t in self.state['production']['tracks']
                      for c in t['arrangement_clips'] if c['start_beat'] >= 64)

    # ------------------------------------------------------------------

    def test_a_section_plan_contains_only_that_section(self) -> None:
        plan = self.plan('Intro')
        start, end = self.section_range(plan, 'Intro')
        copies = plan['actions'][0]['copies']
        self.assertTrue(copies)
        self.assertTrue(all(start <= c['destination_beat'] < end for c in copies))
        self.assertEqual({'Intro'}, {c['section'] for c in plan['source_coverage']})
        self.assertEqual('Intro', plan['scaffold_scope']['section'])

    def test_sections_land_exactly_where_the_full_scaffold_would_put_them(self) -> None:
        full = self.plan()
        full_by_section = {}
        for c in full['actions'][0]['copies']:
            for name in ('Intro', 'Groove'):
                start, end = self.section_range(full, name)
                if start <= c['destination_beat'] < end:
                    full_by_section.setdefault(name, []).append((c['source_track_id'], c['destination_beat']))
        intro = self.plan('Intro')
        self.apply(intro)
        groove = self.plan('Groove')  # planned AFTER Intro changed the arrangement end
        self.assertEqual(sorted(full_by_section['Intro']),
                         sorted((c['source_track_id'], c['destination_beat']) for c in intro['actions'][0]['copies']))
        self.assertEqual(sorted(full_by_section['Groove']),
                         sorted((c['source_track_id'], c['destination_beat']) for c in groove['actions'][0]['copies']))
        self.assertEqual(intro['start_bar'], groove['start_bar'])

    def test_expected_end_never_lowers_the_sets_end(self) -> None:
        full = self.plan()
        self.apply(full)
        end_before = self.state['production']['arrangement_end']
        self.rollback(section='Intro')
        plan = self.plan('Intro')  # later sections still exist, so the Set still ends where it did
        self.assertGreaterEqual(plan['actions'][0]['expected_end_beat'], end_before)

    def test_placing_an_already_scaffolded_section_is_refused_with_guidance(self) -> None:
        self.apply(self.plan('Intro'))
        with self.assertRaisesRegex(ValueError, 'Undo that section first'):
            self.plan('Intro')

    def test_rescaffold_is_rollback_then_scaffold_and_restores_cleanly(self) -> None:
        self.apply(self.plan('Intro'))
        removed = self.rollback(section='Intro')
        self.assertTrue(removed['message'].startswith('Removed '))
        self.assertEqual([], self.placed())
        self.apply(self.plan('Intro'))
        self.assertTrue(self.placed())

    def test_rolling_back_one_section_of_a_full_scaffold_leaves_the_rest(self) -> None:
        full = self.plan()
        job = self.apply(full)
        all_placed = self.placed()
        start, end = self.section_range(full, 'Breakdown')
        in_breakdown = [p for p in all_placed if start <= p[1] < end]
        self.assertTrue(in_breakdown)
        result = self.rollback(job_id=job['id'], section='Breakdown')
        self.assertEqual(sorted(set(all_placed) - set(in_breakdown)), self.placed())
        self.assertIn('Removed %d of %d clips' % (len(in_breakdown), len(in_breakdown)), result['message'])
        # A later whole-job rollback only has the remaining clips and reports no phantom losses.
        final = self.rollback(job_id=job['id'])
        self.assertEqual([], self.placed())
        self.assertEqual(self.original_tracks, self.state['production']['tracks'])
        self.assertNotIn('skipped', final['message'])
        remaining = len(all_placed) - len(in_breakdown)
        self.assertEqual('Removed %d of %d clips.' % (remaining, remaining), final['message'])

    def test_section_rollback_targets_the_newest_scaffold_when_older_ones_remain(self) -> None:
        # Live 12.3.2: earlier smoke-test scaffolds were still in the Set, and section Undo refused with
        # "scaffolded more than once" instead of undoing the scaffold the panel was showing.
        old = self.apply(self.plan())
        old_placed = self.placed()
        newer_plan = self.plan()
        self.assertGreater(newer_plan['start_bar'], 1)
        new = self.apply(newer_plan)
        start, end = self.section_range(newer_plan, 'Groove')
        new_groove = [p for p in self.placed() if start <= p[1] < end and p not in old_placed]
        self.assertTrue(new_groove)
        result = self.rollback(section='Groove')
        self.assertEqual(new['id'], result['rollback_of'])
        self.assertTrue(set(old_placed) <= set(self.placed()))
        self.assertFalse(set(new_groove) & set(self.placed()))
        self.assertNotEqual(old['id'], result['rollback_of'])

    def test_section_dry_run_changes_nothing(self) -> None:
        self.apply(self.plan('Intro'))
        queued = len(self.enqueued)
        report = production.rollback({'working_copy_confirmed': True, 'dry_run': True, 'section': 'Intro', **self.SCOPE})
        self.assertTrue(report['dry_run'])
        self.assertEqual('Intro', report['section'])
        self.assertEqual(queued, len(self.enqueued))
        self.assertTrue(self.placed())

    def test_other_section_rollback_does_not_touch_this_one(self) -> None:
        self.apply(self.plan('Intro'))
        self.apply(self.plan('Groove'))
        before = self.placed()
        self.rollback(section='Groove')
        intro_start, intro_end = self.section_range(self.plan('Groove'), 'Intro')
        self.assertTrue(self.placed())
        self.assertTrue(all(intro_start <= p[1] < intro_end for p in self.placed()))
        self.assertLess(len(self.placed()), len(before))

    def test_unknown_section_and_unscaffolded_section_errors(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unknown section'):
            self.plan('Nope')
        with self.assertRaisesRegex(ValueError, 'No scaffolded clips'):
            production.rollback({'working_copy_confirmed': True, 'section': 'Intro', **self.SCOPE})

    def test_section_status_reports_what_is_in_the_set(self) -> None:
        self.apply(self.plan('Intro'))
        sections = production.scaffold_sections('House', 'club-version')['sections']
        self.assertEqual(['Intro'], list(sections))
        self.assertGreater(sections['Intro']['clips'], 0)
        self.rollback(section='Intro')
        self.assertEqual({}, production.scaffold_sections('House', 'club-version')['sections'])

    def test_user_edited_clip_in_a_section_survives_that_sections_rollback(self) -> None:
        self.apply(self.plan('Intro'))
        victim = next(c for t in self.state['production']['tracks'] for c in t['arrangement_clips'] if c['start_beat'] >= 64)
        victim['fingerprint'] = 'e' * 64
        self.live.seal()
        result = self.rollback(section='Intro')
        self.assertIn('skipped because you edited them', result['message'])
        self.assertEqual(1, len(self.placed()))


if __name__ == '__main__':
    unittest.main()
