"""A4: per-clip rollback for Session-to-Arrangement copy jobs (fake bridge enforcing the same checks)."""
from __future__ import annotations

import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import production

try:
    from fake_live import FakeLive, clip
except ImportError:
    from tests.fake_live import FakeLive, clip

FP = {'kick-id': 'k' * 64, 'bass-id': 'b' * 64}


class SessionToArrangementRollbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for target, value in (('vibelton.production.ROOT', self.root / 'production'),
                              ('vibelton.queue.QUEUE_DIR', self.root / 'queue')):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.state = {
            'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1', 'arrangement_copy_v2'],
            'session_id': 'live-1',
            'production': {
                'schema_version': 'x', 'session_id': 'live-1', 'revision': '', 'tempo': 124, 'metre': [4, 4],
                'set_path': '/sets/s2a vibelton-working-copy.als', 'locators': [], 'arrangement_end': 0,
                'tracks': [{'id': tid, 'index': i, 'name': name, 'type': 'midi', 'mixer': {'volume': .8, 'pan': 0, 'sends': []},
                            'devices': [], 'routing': 'Main', 'arrangement_clips': [],
                            'session_clips': [{'scene_index': 0, 'name': name + ' loop', 'length': 16.0, 'fingerprint': FP[tid]}]}
                           for i, (tid, name) in enumerate([('kick-id', 'Kick'), ('bass-id', 'Bass')])]}}
        self.live = FakeLive(self)
        self.live.seal()
        self.original_tracks = copy.deepcopy(self.state['production']['tracks'])
        self.enqueued: list[dict] = []
        for target, effect in (('current_state', lambda: self.state),
                               ('enqueue', lambda actions, source: (self.enqueued.append({'actions': actions}) or {'id': 'c%d' % len(self.enqueued)}))):
            patcher = patch.object(production.queue, target, side_effect=effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def place(self, destinations=(0.0, 16.0)) -> dict:
        copies = [{'track_id': tid, 'source_scene_index': 0, 'source_fingerprint': FP[tid], 'destination_beat': dest}
                  for tid in FP for dest in destinations]
        plan = production.create_plan({'intent': 'Place', 'snapshot_name': 'Before place',
                                       'actions': [{'type': 'apply_session_to_arrangement_copies', 'copies': copies}]})
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        result = self.live.process(len(self.enqueued) - 1)
        self.assertEqual('Applied', result['status'], result.get('error'))
        return job

    def rollback(self, job, **extra) -> dict:
        return production.rollback({'job_id': job['id'], 'working_copy_confirmed': True, **extra})

    def track(self, tid):
        return next(t for t in self.state['production']['tracks'] if t['id'] == tid)

    def test_clean_rollback_restores_original_state(self) -> None:
        job = self.place()
        self.assertEqual(4, len(production.job_status(job['id'])['placements']))
        rb = self.rollback(job)
        self.assertEqual('Applied', self.live.process(len(self.enqueued) - 1)['status'])
        self.assertEqual(self.original_tracks, self.state['production']['tracks'])
        self.assertEqual('Removed 4 of 4 clips.', production.job_status(rb['id'])['message'])

    def test_partial_placement_rolls_back_only_what_exists(self) -> None:
        self.live.fail_after = 2
        copies = [{'track_id': tid, 'source_scene_index': 0, 'source_fingerprint': FP[tid], 'destination_beat': d}
                  for tid in FP for d in (0.0, 16.0)]
        plan = production.create_plan({'intent': 'Place', 'snapshot_name': 'x', 'actions': [
            {'type': 'apply_session_to_arrangement_copies', 'copies': copies}]})
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        self.assertEqual('Partial failure', self.live.process(len(self.enqueued) - 1)['status'])
        self.rollback(job)
        self.assertEqual('Applied', self.live.process(len(self.enqueued) - 1)['status'])
        self.assertEqual(self.original_tracks, self.state['production']['tracks'])

    def test_edited_clip_is_skipped_and_kept(self) -> None:
        job = self.place()
        edited = next(c for c in self.track('kick-id')['arrangement_clips'] if c['start_beat'] == 16.0)
        edited['fingerprint'] = 'e' * 64
        rb = self.rollback(job)
        self.assertEqual('Applied', self.live.process(len(self.enqueued) - 1)['status'])
        self.assertEqual([16.0], [c['start_beat'] for c in self.track('kick-id')['arrangement_clips']])
        self.assertEqual([], self.track('bass-id')['arrangement_clips'])
        message = production.job_status(rb['id'])['message']
        self.assertIn('Removed 3 of 4 clips', message)
        self.assertIn('you edited them', message)

    def test_user_added_clip_is_untouched(self) -> None:
        job = self.place()
        self.track('kick-id')['arrangement_clips'].append(clip(64.0, 72.0, 'u' * 64, 'Mine'))
        self.live.seal()
        self.rollback(job)
        self.assertEqual('Applied', self.live.process(len(self.enqueued) - 1)['status'])
        self.assertEqual([64.0], [c['start_beat'] for c in self.track('kick-id')['arrangement_clips']])

    def test_dry_run_changes_nothing(self) -> None:
        job = self.place()
        before = (len(self.enqueued), copy.deepcopy(self.state['production']['tracks']))
        report = production.rollback({'job_id': job['id'], 'working_copy_confirmed': True, 'dry_run': True})
        self.assertTrue(report['dry_run'])
        self.assertEqual(4, report['removable_count'])
        self.assertTrue(report['summary'].startswith('Would remove 4 of 4'))
        self.assertEqual(before, (len(self.enqueued), self.state['production']['tracks']))

    def test_section_without_recorded_sections_is_refused(self) -> None:
        job = self.place()
        with self.assertRaises(ValueError):
            self.rollback(job, section='Drop')

    def test_changed_session_source_is_skipped(self) -> None:
        job = self.place()
        self.track('kick-id')['session_clips'][0]['fingerprint'] = 'z' * 64
        rb = self.rollback(job)
        self.assertEqual('Applied', self.live.process(len(self.enqueued) - 1)['status'])
        self.assertEqual(2, len(self.track('kick-id')['arrangement_clips']))   # kept: their source changed
        self.assertEqual([], self.track('bass-id')['arrangement_clips'])
        self.assertIn('source loop changed', production.job_status(rb['id'])['message'])


if __name__ == '__main__':
    unittest.main()
