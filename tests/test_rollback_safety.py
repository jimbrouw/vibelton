from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import production, rollback_safety

try:
    from fake_live import FakeLive, clip
except ImportError:  # run as tests.test_rollback_safety
    from tests.fake_live import FakeLive, clip

SRC_FP = {'kick': 'k' * 64, 'bass': 'b' * 64, 'hats': 'h' * 64}


class RollbackSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for target, value in (('vibelton.production.ROOT', self.root / 'production'),
                              ('vibelton.queue.QUEUE_DIR', self.root / 'queue')):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        names = [('kick-id', 'Kick', 'kick'), ('bass-id', 'Bass', 'bass'), ('hats-id', 'Hats', 'hats')]
        self.state = {
            'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1', 'arrangement_copy_v2'],
            'session_id': 'live-1',
            'production': {
                'schema_version': 'x', 'session_id': 'live-1', 'revision': '', 'tempo': 124, 'metre': [4, 4],
                'set_path': '/sets/shape vibelton-working-copy.als', 'locators': [], 'arrangement_end': 0,
                'tracks': [{'id': tid, 'index': i, 'name': name, 'type': 'audio', 'mixer': {'volume': .8, 'pan': 0, 'sends': []},
                            'devices': [], 'routing': 'Main', 'arrangement_clips': [clip(0, 64, SRC_FP[key], name)]}
                           for i, (tid, name, key) in enumerate(names)]}}
        self.live = FakeLive(self)
        self.live.seal()
        self.original_tracks = copy.deepcopy(self.state['production']['tracks'])
        self.enqueued: list[dict] = []
        for target, effect in (('current_state', lambda: self.state),
                               ('enqueue', lambda actions, source: (self.enqueued.append({'actions': actions}) or {'id': 'c%d' % len(self.enqueued)}))):
            patcher = patch.object(production.queue, target, side_effect=effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def scaffold(self, destinations=(64.0, 128.0)) -> dict:
        copies = [{'source_track_id': tid, 'source_start_beat': 0.0, 'source_fingerprint': SRC_FP[key],
                   'destination_beat': dest}
                  for tid, key in (('kick-id', 'kick'), ('bass-id', 'bass')) for dest in destinations]
        locators = [{'time': float(i), 'name': 'S%d' % i} for i in range(7)]
        plan = production.create_plan({'intent': 'Scaffold', 'snapshot_name': 'Before scaffold', 'actions': [{
            'type': 'apply_arrangement_copies', 'copies': copies, 'locators': [], 'locator_definitions': locators,
            'locators_deferred': True, 'expected_end_beat': max(destinations) + 64.0}]})
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        self.live.process(len(self.enqueued) - 1)
        return job

    def rollback(self, job, **extra) -> dict:
        return production.rollback({'job_id': job['id'], 'working_copy_confirmed': True, **extra})

    def clips(self, track_id):
        return {c['start_beat']: c for t in self.state['production']['tracks'] if t['id'] == track_id
                for c in t['arrangement_clips']}

    # -- tests ---------------------------------------------------------

    def test_rolling_back_an_older_job_never_deletes_a_newer_jobs_clip_at_the_same_spot(self) -> None:
        old = self.scaffold(destinations=(64.0,))
        # You move the old copies away; the old job still remembers where it put them.
        for track in self.state['production']['tracks']:
            track['arrangement_clips'] = [c for c in track['arrangement_clips'] if c['start_beat'] == 0]
        self.live.seal()
        production.job_status(old['id'])
        stored = self.root / 'production' / 'placements' / (old['id'] + '.json')
        data = json.loads(stored.read_text())
        for record in data['records']:      # Live regenerated the track ids since the first scaffold
            record['track_id'] += '-old'
            record['key'] = production.rollback_safety.record_key(record)
        stored.write_text(json.dumps(data))
        new = self.scaffold(destinations=(64.0,))     # same tracks, same bars, same content
        self.assertEqual(2, len(production.job_status(new['id'])['placements']))
        with self.assertRaisesRegex(ValueError, 'no reversible changes'):   # nothing left that is the old job's to undo
            production.rollback({'job_id': old['id'], 'working_copy_confirmed': True, 'dry_run': True})
        dry = production.rollback({'job_id': new['id'], 'working_copy_confirmed': True, 'dry_run': True})
        self.assertEqual(2, dry['removable_count'])

    def test_clean_rollback_removes_only_scaffold_clips_and_restores_state(self) -> None:
        job = self.scaffold()
        self.assertEqual(4, len(production.job_status(job['id'])['placements']))
        rb = self.rollback(job)
        result = self.live.process(len(self.enqueued) - 1)
        self.assertEqual('Applied', result['status'], result.get('error'))
        self.assertEqual(self.original_tracks, self.state['production']['tracks'])
        self.assertEqual('Removed 4 of 4 clips.', production.job_status(rb['id'])['message'])

    def test_rollback_after_partial_scaffold_undoes_just_those(self) -> None:
        self.live.fail_after = 3
        job = self.scaffold()
        status = production.job_status(job['id'])
        self.assertEqual('Partial failure', status['status'])
        self.assertEqual(3, len(status['placements']))
        self.rollback(job)
        self.assertEqual('Applied', self.live.process(len(self.enqueued) - 1)['status'])
        self.assertEqual(self.original_tracks, self.state['production']['tracks'])

    def test_user_edited_clip_is_skipped_and_reported(self) -> None:
        job = self.scaffold()
        edited = self.clips('kick-id')[64.0]
        edited['fingerprint'] = 'e' * 64  # user changed the notes
        rb = self.rollback(job)
        result = self.live.process(len(self.enqueued) - 1)
        self.assertEqual('Applied', result['status'], result.get('error'))
        self.assertIn(64.0, self.clips('kick-id'))      # edited clip survived
        self.assertNotIn(128.0, self.clips('kick-id'))  # untouched copy removed
        self.assertNotIn(64.0, self.clips('bass-id'))
        message = production.job_status(rb['id'])['message']
        self.assertEqual('Removed 3 of 4 clips. 1 skipped because you edited them: Kick bar 17.', message)

    def test_moved_clip_and_user_added_clips_survive(self) -> None:
        job = self.scaffold()
        self.clips('bass-id')[128.0]['start_beat'] = 130.0
        self.clips('bass-id')[130.0]['end_beat'] = 194.0
        user_clip = clip(300, 332, 'u' * 64, 'My new clip')
        next(t for t in self.state['production']['tracks'] if t['id'] == 'hats-id')['arrangement_clips'].append(user_clip)
        self.live.seal()
        self.rollback(job)
        result = self.live.process(len(self.enqueued) - 1)
        self.assertEqual('Applied', result['status'], result.get('error'))
        self.assertIn(130.0, self.clips('bass-id'))
        self.assertIn(300.0, self.clips('hats-id'))
        self.assertEqual({0.0, 130.0}, set(self.clips('bass-id')))
        self.assertEqual({0.0}, set(self.clips('kick-id')))

    def test_user_clip_overlapping_a_placed_clip_blocks_its_removal(self) -> None:
        job = self.scaffold()
        track = next(t for t in self.state['production']['tracks'] if t['id'] == 'kick-id')
        track['arrangement_clips'].append(clip(100, 120, 'u' * 64))  # overlaps the 64-128 copy
        self.live.seal()
        report = self.rollback(job, dry_run=True)
        reasons = {s['record']['destination_beat']: s['reason'] for s in report['skipped']}
        self.assertEqual('overlapped', reasons[64.0])

    def test_rollback_after_server_restart_uses_disk_records(self) -> None:
        job = self.scaffold()
        production.job_status(job['id'])  # the UI poll that records placements
        placements = self.root / 'production' / 'placements' / (job['id'] + '.json')
        self.assertTrue(placements.is_file())
        self.assertTrue((self.root / 'production' / 'snapshots' / (job['snapshot_id'] + '.json')).is_file())
        # A restarted server keeps nothing in memory: everything must come from ROOT.
        # Even a lost placement file can be rebuilt from the snapshot + bridge result.
        placements.unlink()
        self.rollback(job)
        self.assertEqual('Applied', self.live.process(len(self.enqueued) - 1)['status'])
        self.assertEqual(self.original_tracks, self.state['production']['tracks'])

    def test_rollback_after_live_reloads_the_set_remaps_tracks_by_name(self) -> None:
        job = self.scaffold()
        self.state['session_id'] = 'live-2'
        prod = self.state['production']
        prod['session_id'] = 'live-2'
        for track in prod['tracks']:
            track['id'] = 'new-' + track['id']  # Live regenerated the ids
        self.live.seal()
        self.rollback(job)
        result = self.live.process(len(self.enqueued) - 1)
        self.assertEqual('Applied', result['status'], result.get('error'))
        self.assertEqual({0.0}, set(self.clips('new-kick-id')))

    def test_dry_run_changes_nothing(self) -> None:
        job = self.scaffold()
        self.clips('kick-id')[64.0]['fingerprint'] = 'e' * 64
        self.live.seal()
        before = copy.deepcopy(self.state)
        queued, jobs = len(self.enqueued), sorted(p.name for p in (self.root / 'production' / 'jobs').glob('*'))
        plans = sorted(p.name for p in (self.root / 'production' / 'plans').glob('*'))
        report = self.rollback(job, dry_run=True)
        self.assertTrue(report['dry_run'])
        self.assertEqual(3, report['removable_count'])
        self.assertEqual(4, report['total'])
        self.assertTrue(report['summary'].startswith('Would remove 3 of 4 clips.'))
        self.assertEqual(queued, len(self.enqueued))
        self.assertEqual(before, self.state)
        self.assertEqual(jobs, sorted(p.name for p in (self.root / 'production' / 'jobs').glob('*')))
        self.assertEqual(plans, sorted(p.name for p in (self.root / 'production' / 'plans').glob('*')))

    def test_refuses_rollback_onto_a_different_set(self) -> None:
        job = self.scaffold()
        self.state['production']['set_path'] = '/sets/other vibelton-working-copy.als'
        with self.assertRaisesRegex(ValueError, 'different Live Set'):
            self.rollback(job)

    def test_nothing_removable_is_an_error_not_a_silent_success(self) -> None:
        job = self.scaffold()
        for track in self.state['production']['tracks']:
            for c in track['arrangement_clips']:
                if c['start_beat'] != 0.0:
                    c['fingerprint'] = 'e' * 64
        with self.assertRaisesRegex(ValueError, 'Nothing to roll back'):
            self.rollback(job)

    def test_a_recorded_clip_that_is_a_source_loop_is_never_removable(self) -> None:
        record = {'track_id': 'kick-id', 'track_name': 'Kick', 'track_index': 0, 'destination_beat': 0.0,
                  'end_beat': 64.0, 'source_start_beat': 0.0, 'source_fingerprint': SRC_FP['kick']}
        verdict = rollback_safety.classify([record], self.state['production'])
        self.assertEqual([], verdict['removable'])
        self.assertEqual('is_source', verdict['skipped'][0]['reason'])


if __name__ == '__main__':
    unittest.main()
