"""Section markers (Live locators): created with the scaffold, removed again by rollback."""
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
except ImportError:
    from tests.fake_live import FakeLive

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'arranger-mixed-audio-midi.json'
SCOPE = {'genre': 'House', 'variant_id': 'club-version'}
NAMES = ['INTRO', 'GROOVE', 'MAIN GROOVE', 'TENSION', 'BREAKDOWN', 'DROP', 'OUTRO']


class MarkerTests(unittest.TestCase):
    capability = True

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
        prod.update(session_id='live-1', revision='',
                    template_capabilities={'arrangement_locator_readback': self.capability})
        self.state = {'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1', 'arrangement_copy_v2'],
                      'session_id': 'live-1', 'tempo': 124.0, 'metre': [4, 4], 'production': prod}
        self.live = FakeLive(self)
        self.live.seal()
        self.original = json.loads(json.dumps(prod))
        self.enqueued: list[dict] = []
        for name, effect in (('current_state', lambda: self.state),
                             ('enqueue', lambda actions, source: (self.enqueued.append({'actions': actions}) or {'id': 'c%d' % len(self.enqueued)}))):
            patcher = patch.object(production.queue, name, side_effect=effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def plan(self, section=None) -> dict:
        return production.create_scaffold_plan({**SCOPE, **({'section': section} if section else {})})

    def apply(self, plan) -> dict:
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        result = self.live.process(len(self.enqueued) - 1)
        self.assertEqual('Applied', result['status'], result.get('error'))
        return job

    def rollback(self, **payload) -> dict:
        job = production.rollback({'working_copy_confirmed': True, **SCOPE, **payload})
        result = self.live.process(len(self.enqueued) - 1)
        self.assertEqual('Applied', result['status'], result.get('error'))
        return production.job_status(job['id'])

    def cue_names(self):
        return [c['name'] for c in self.state['production']['locators']]


class MarkerCreationTests(MarkerTests):
    def test_full_scaffold_creates_one_named_marker_per_section_and_rollback_removes_them(self) -> None:
        plan = self.plan()
        self.assertFalse(plan['locators_deferred'])
        self.assertEqual(NAMES, [l['name'] for l in plan['actions'][0]['locators']])
        job = self.apply(plan)
        cues = self.state['production']['locators']
        self.assertEqual(NAMES, [c['name'] for c in cues])
        base = (plan['start_bar'] - 1) * 4.0
        starts = [base + 4.0 * sec['start_bar'] for sec in plan['variant']['sections']]
        self.assertEqual(starts, [c['time'] for c in cues])
        result = self.rollback(job_id=job['id'])
        self.assertEqual([], self.cue_names())
        self.assertEqual(self.original['tracks'], self.state['production']['tracks'])
        self.assertIn('Removed 7 section markers.', result['message'])

    def test_a_single_section_gets_only_its_own_marker(self) -> None:
        plan = self.plan('Breakdown')
        self.assertEqual(['BREAKDOWN'], [l['name'] for l in plan['actions'][0]['locators']])
        self.apply(plan)
        self.assertEqual(['BREAKDOWN'], self.cue_names())

    def test_section_rollback_removes_only_that_sections_marker(self) -> None:
        job = self.apply(self.plan())
        result = self.rollback(job_id=job['id'], section='Breakdown')
        self.assertNotIn('BREAKDOWN', self.cue_names())
        self.assertEqual([n for n in NAMES if n != 'BREAKDOWN'], self.cue_names())
        self.assertIn('Removed 1 section marker.', result['message'])
        # The whole-job rollback afterwards removes the rest and does not trip over the missing one.
        final = self.rollback(job_id=job['id'])
        self.assertEqual([], self.cue_names())
        self.assertIn('Removed 6 section markers.', final['message'])
        self.assertEqual(self.original['tracks'], self.state['production']['tracks'])

    def test_sections_scaffolded_one_by_one_each_keep_their_marker(self) -> None:
        self.apply(self.plan('Intro'))
        self.apply(self.plan('Groove'))
        self.assertEqual(['INTRO', 'GROOVE'], self.cue_names())
        self.rollback(section='Intro')
        self.assertEqual(['GROOVE'], self.cue_names())

    def test_users_own_cue_points_are_left_alone(self) -> None:
        self.state['production']['locators'] = [{'time': 8.0, 'name': 'My marker'}]
        self.live.seal()
        original = json.loads(json.dumps(self.state['production']['locators']))
        job = self.apply(self.plan())
        self.assertEqual(['My marker'] + NAMES, self.cue_names())
        self.rollback(job_id=job['id'])
        self.assertEqual(original, self.state['production']['locators'])

    def test_dry_run_reports_markers_and_changes_nothing(self) -> None:
        job = self.apply(self.plan())
        queued, cues = len(self.enqueued), self.cue_names()
        report = production.rollback({'job_id': job['id'], 'working_copy_confirmed': True, 'dry_run': True})
        self.assertEqual(7, len(report['locators_to_remove']))
        self.assertIn('Would remove 7 section markers.', report['summary'])
        self.assertEqual((queued, cues), (len(self.enqueued), self.cue_names()))

    def test_a_marker_the_user_deleted_is_reported_missing_not_an_error(self) -> None:
        job = self.apply(self.plan())
        self.state['production']['locators'] = [c for c in self.state['production']['locators'] if c['name'] != 'TENSION']
        self.live.seal()
        report = production.rollback({'job_id': job['id'], 'working_copy_confirmed': True, 'dry_run': True})
        self.assertEqual(['TENSION'], [l['name'] for l in report['locators_missing']])
        self.rollback(job_id=job['id'])
        self.assertEqual([], self.cue_names())


class MarkersNotProvenTests(MarkerTests):
    capability = False

    def test_without_the_capability_markers_are_plan_only(self) -> None:
        plan = self.plan()
        self.assertTrue(plan['locators_deferred'])
        self.assertEqual([], plan['actions'][0]['locators'])
        self.assertEqual(NAMES, [l['name'] for l in plan['locator_definitions']])
        self.assertTrue(any('not created in Live' in w for w in plan['warnings']), plan['warnings'])
        self.apply(plan)
        self.assertEqual([], self.cue_names())


class ProbeServerTests(MarkerTests):
    capability = False

    def test_probe_queues_a_single_parameterless_action_after_confirmation(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Confirm the working copy'):
            production.probe_locators({'working_copy_confirmed': False})
        job = production.probe_locators({'working_copy_confirmed': True})
        self.assertEqual('Queued', job['status'])
        self.assertEqual([{'type': 'probe_arrangement_locators'}], self.enqueued[-1]['actions'][0]['actions'])

    def test_probe_is_blocked_on_an_original_set(self) -> None:
        self.state['production']['set_path'] = '/Sets/My song.als'
        with self.assertRaisesRegex(ValueError, 'working copy'):
            production.probe_locators({'working_copy_confirmed': True})
        self.assertEqual([], self.enqueued)

    def test_a_probe_job_cannot_be_rolled_back(self) -> None:
        job = production.probe_locators({'working_copy_confirmed': True})
        production._write(self.root / 'queue' / 'production-executions' / (job['id'] + '.json'),
                          {'status': 'Applied', 'post_revision': 'x'})
        with self.assertRaisesRegex(ValueError, 'nothing to roll back'):
            production.rollback({'job_id': job['id'], 'working_copy_confirmed': True})

    def test_once_the_bridge_advertises_the_capability_plans_create_markers(self) -> None:
        self.assertTrue(self.plan()['locators_deferred'])
        self.state['production']['template_capabilities']['arrangement_locator_readback'] = True
        self.live.seal()
        self.assertFalse(self.plan()['locators_deferred'])


if __name__ == '__main__':
    unittest.main()
