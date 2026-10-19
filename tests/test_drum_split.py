"""Server coverage for planning, applying, undoing and scaffolding around a Drum Rack split."""
from __future__ import annotations

import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import production, queue


def drum_track(track_id='trk-beats', name='8-Swang Bap Kit', pads=None):
    pads = pads if pads is not None else [{'note': 36, 'name': 'Kick 808'}, {'note': 38, 'name': 'Snare Tight'},
                                          {'note': 42, 'name': ''}, {'note': 46, 'name': 'Hat Open'},
                                          {'note': 50, 'name': 'Conga Hi'}]
    return {'id': track_id, 'name': name, 'type': 'midi', 'mixer': {'volume': .8, 'pan': 0.0, 'sends': []},
            'devices': [{'name': 'Swang Bap Kit', 'class_name': 'DrumGroupDevice'}], 'routing': 'Main',
            'arrangement_clips': [],
            'session_clips': [{'scene_index': 0, 'name': 'Beat', 'length': 16.0, 'fingerprint': 'd' * 64}],
            'drum_rack': {'device_name': 'Swang Bap Kit', 'pads': pads}}


class DrumSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for target, value in (('vibelton.production.ROOT', self.root / 'production'), ('vibelton.queue.QUEUE_DIR', self.root / 'queue')):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(production.queue, 'enqueue', side_effect=lambda actions, source: {'id': 'cmd'})
        patcher.start()
        self.addCleanup(patcher.stop)
        bass = {'id': 'trk-bass', 'name': 'Reese Bass', 'type': 'midi', 'mixer': {'volume': .8, 'pan': 0.0, 'sends': []},
                'devices': [], 'routing': 'Main', 'arrangement_clips': [],
                'session_clips': [{'scene_index': 0, 'name': 'Bass', 'length': 16.0, 'fingerprint': 'b' * 64}]}
        self.state = {'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1', 'arrangement_copy_v2'],
                      'session_id': 'drum-session', 'tempo': 90.0, 'metre': [4, 4], 'arrangement_readable': True,
                      'arrangement_end': 0.0, 'set_path': '/Sets/beat vibelton-working-copy.als',
                      'production': {'schema_version': 'vibelton.production-project-state/v1', 'session_id': 'drum-session',
                                     'revision': 'rev-1', 'set_path': '/Sets/beat vibelton-working-copy.als',
                                     'tempo': 90.0, 'metre': [4, 4], 'arrangement_end': 0.0, 'scene_names': ['A'],
                                     'tracks': [drum_track(), bass], 'locators': []}}
        patcher = patch.object(production.queue, 'current_state', side_effect=lambda: self.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_pads_group_by_name_then_by_note(self):
        lanes = production.drum_split_preview(drum_track())
        self.assertEqual(['Kick', 'Snare / Clap', 'Hats', 'Percussion'], [lane['role'] for lane in lanes])
        hats = lanes[2]
        self.assertEqual([42, 46], hats['notes'])   # 42 has no name: General MIDI closed hat
        self.assertEqual(['note 42', 'pad "Hat Open"'], [p['matched_by'] for p in hats['pads']])
        self.assertEqual('8-Swang Bap Kit · Hats', hats['name'])

    def test_one_role_only_has_nothing_to_split(self):
        self.assertIsNone(production.drum_split_preview(drum_track(pads=[{'note': 36, 'name': 'Kick A'}, {'note': 35, 'name': 'Kick B'}])))
        self.state['production']['tracks'][0] = drum_track(pads=[{'note': 36, 'name': 'Kick A'}])
        with self.assertRaisesRegex(ValueError, 'nothing to split'):
            production.create_drum_split_plan({'track_id': 'trk-beats'})

    def test_plan_and_undo_use_the_recorded_lanes(self):
        plan = production.create_drum_split_plan({'track_id': 'trk-beats'})
        self.assertEqual('split_drum_track', plan['actions'][0]['type'])
        self.assertEqual(4, len(plan['actions'][0]['lanes']))
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        created = [{'track_id': 'lane-%d' % n, 'name': lane['name'], 'role': lane['role'], 'notes': lane['notes'],
                    'clip_fingerprints': {'s0': '%064x' % n}} for n, lane in enumerate(plan['actions'][0]['lanes'])]
        exec_dir = self.root / 'queue' / 'production-executions'
        exec_dir.mkdir(parents=True, exist_ok=True)
        (exec_dir / (job['id'] + '.json')).write_text(json.dumps({
            'job_id': job['id'], 'status': 'Applied', 'completed_actions': 1, 'created_tracks': created,
            'muted_source': True, 'post_revision': 'rev-2'}), encoding='utf-8')
        self.state['production']['revision'] = 'rev-2'
        tracks = self.state['production']['tracks']
        for n, record in enumerate(created):
            tracks.insert(1 + n, dict(copy.deepcopy(tracks[0]), id=record['track_id'], name=record['name']))
        preview = production.rollback({'job_id': job['id'], 'working_copy_confirmed': True, 'dry_run': True})
        self.assertIn('Would delete the 4 drum lanes', preview['summary'])
        undo = production.rollback({'job_id': job['id'], 'working_copy_confirmed': True})
        action = production.get_plan(undo['plan_id'])['actions'][0]
        self.assertEqual('rollback_split_drum_track', action['type'])
        self.assertEqual(created, action['created_tracks'])
        self.assertEqual(('trk-beats', True), (action['source_track_id'], action['unmute_source']))
        self.assertIn('unmuted', preview['summary'])

    def test_a_split_track_is_left_to_its_lanes(self):
        tracks = self.state['production']['tracks']
        for role in ('Kick', 'Hats'):
            lane = dict(copy.deepcopy(tracks[0]), id='lane-' + role, name='8-Swang Bap Kit · ' + role)
            lane['session_clips'] = [{'scene_index': 0, 'name': 'Beat', 'length': 16.0, 'fingerprint': role[0].lower() * 64}]
            tracks.append(lane)
        analysis = {t['id']: t for t in production.analyse()['tracks']}
        self.assertEqual(2, analysis['trk-beats']['split_into_lanes'])
        self.assertNotIn('drum_split_preview', analysis['trk-beats'])
        with self.assertRaisesRegex(ValueError, 'already split'):
            production.create_drum_split_plan({'track_id': 'trk-beats'})
        plan = production.create_scaffold_plan({'genre': 'Boom Bap', 'variant_id': 'boombap-two-verses',
                                                'roles': {'trk-beats': 'Percussion'}})
        used = {c['track_name'] for c in plan['source_coverage']}
        self.assertNotIn('8-Swang Bap Kit', used)
        self.assertTrue({'8-Swang Bap Kit · Kick', '8-Swang Bap Kit · Hats'} <= used)

    def test_unsplit_drum_track_offers_a_preview(self):
        track = {t['id']: t for t in production.analyse()['tracks']}['trk-beats']
        self.assertEqual(['Kick', 'Snare / Clap', 'Hats', 'Percussion'], [l['role'] for l in track['drum_split_preview']])


if __name__ == '__main__':
    unittest.main()
