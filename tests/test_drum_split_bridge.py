"""Bridge coverage for splitting a Drum Rack track into one lane per drum role."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

_spec = importlib.util.spec_from_file_location('drum_split_fixtures', Path(__file__).resolve().parent / 'test_production_bridge.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

module = base.module


class DrumClip:
    def __init__(self, notes, start=0.0, length=16.0, name='Beat'):
        self.name, self.start_time, self.length = name, float(start), float(length)
        self.end_time = self.start_time + self.length
        self.is_midi_clip = True
        self.loop_start, self.loop_end = 0.0, self.length
        self.signature_numerator, self.signature_denominator = 4, 4
        self.notes = list(notes)

    def get_notes(self, *_args):
        return list(self.notes)

    def remove_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        self.notes = [n for n in self.notes
                      if not (from_pitch <= n[0] < from_pitch + pitch_span and from_time <= n[1] < from_time + time_span)]


class Slot:
    def __init__(self, clip=None):
        self.clip = clip

    @property
    def has_clip(self):
        return self.clip is not None


class DrumRack:
    class_name = 'DrumGroupDevice'
    can_have_drum_pads = True
    has_drum_pads = True

    def __init__(self, names):
        self.name = 'Swang Bap Kit'
        self.parameters = []
        self.drum_pads = [NS(note=n, name=names.get(n, ''), chains=[1] if n in names else []) for n in range(128)]


class DrumTrack(base.Track):
    def __init__(self, name='Beats'):
        super().__init__()
        self.name = name
        self.devices = [DrumRack({36: 'Kick 808', 38: 'Snare Tight', 42: 'Hat Closed', 46: 'Hat Open', 60: ''})]
        beat = [(36, 0.0, .25, 110, False), (42, .5, .25, 80, False), (38, 1.0, .25, 100, False),
                (46, 1.5, .25, 70, False), (36, 2.0, .25, 110, False), (60, 3.5, .25, 90, False)]
        self.clip_slots = [Slot(DrumClip(beat)), Slot()]
        self.arrangement_clips = [DrumClip(beat, start=0.0)]


class DrumSong(base.Song):
    def __init__(self):
        super().__init__()
        self.tracks = [DrumTrack(), base.Track()]
        self.scenes = [NS(name='One'), NS(name='Two')]
        self.cue_points = []

    def duplicate_track(self, index):
        self.tracks.insert(index + 1, copy.deepcopy(self.tracks[index]))

    def delete_track(self, index):
        self.tracks.pop(index)


class DrumSplitBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = patch.object(module.os.path, 'expanduser', return_value=self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.song = DrumSong()
        self.bridge = module.CompositionBridge()
        self.bridge._composition_init()
        self.bridge.song = lambda: self.song
        self.bridge._log = lambda *args: None
        self.drums = self.song.tracks[0]
        self.drum_id = self.bridge._composition_track_id(self.drums)

    def job(self, actions):
        action = {'type': 'production_apply', 'job_id': str(uuid.uuid4()), 'session_id': self.bridge._composition_session,
                  'source_revision': self.bridge._production_state()['revision'], 'actions': actions}
        self.bridge._production_apply(action)
        path = Path(self.tmp.name) / '.vibelton' / 'production-executions' / (action['job_id'] + '.json')
        return json.loads(path.read_text())

    def lanes(self):
        return [{'name': 'Beats · Kick', 'role': 'Kick', 'notes': [36]},
                {'name': 'Beats · Snare / Clap', 'role': 'Snare / Clap', 'notes': [38]},
                {'name': 'Beats · Hats', 'role': 'Hats', 'notes': [42, 46]},
                {'name': 'Beats · Percussion', 'role': 'Percussion', 'notes': [60]}]

    def test_state_reports_the_pads_the_clips_play(self):
        track = next(t for t in self.bridge._production_state()['tracks'] if t['id'] == self.drum_id)
        self.assertEqual('Swang Bap Kit', track['drum_rack']['device_name'])
        self.assertEqual([(36, 'Kick 808'), (38, 'Snare Tight'), (42, 'Hat Closed'), (46, 'Hat Open'), (60, '')],
                         [(p['note'], p['name']) for p in track['drum_rack']['pads']])
        plain = [t for t in self.bridge._production_state()['tracks'] if t['id'] != self.drum_id][0]
        self.assertNotIn('drum_rack', plain)

    def test_split_makes_lanes_in_role_order_and_leaves_the_original(self):
        before = self.bridge._composition_clip_snapshot(self.drums.clip_slots[0].clip)
        result = self.job([{'type': 'split_drum_track', 'track_id': self.drum_id, 'lanes': self.lanes()}])
        self.assertEqual('Applied', result['status'])
        self.assertEqual(['Beats', 'Beats · Kick', 'Beats · Snare / Clap', 'Beats · Hats', 'Beats · Percussion', 'Bass'],
                         [t.name for t in self.song.tracks])
        hats = self.song.tracks[3]
        self.assertEqual({42, 46}, {n[0] for n in hats.clip_slots[0].clip.notes})
        self.assertEqual({42, 46}, {n[0] for n in hats.arrangement_clips[0].notes})
        self.assertEqual(before, self.bridge._composition_clip_snapshot(self.drums.clip_slots[0].clip))
        self.assertEqual(['Kick', 'Snare / Clap', 'Hats', 'Percussion'], [r['role'] for r in result['created_tracks']])
        # The original is muted so its existing clips don't double the lanes; the lanes stay audible.
        self.assertTrue(self.drums.mute)
        self.assertTrue(result['muted_source'])
        self.assertFalse(any(getattr(t, 'mute', False) for t in self.song.tracks[1:5]))

    def test_undo_deletes_exactly_the_lanes(self):
        observable = self.bridge._production_observable_rollback_revision()
        applied = self.job([{'type': 'split_drum_track', 'track_id': self.drum_id, 'lanes': self.lanes()}])
        undo = self.job([{'type': 'rollback_split_drum_track', 'created_tracks': applied['created_tracks'],
                          'expected_post_rollback_observable_revision': observable,
                          'source_track_id': self.drum_id, 'unmute_source': True}])
        self.assertEqual('Applied', undo['status'])
        self.assertEqual(['Beats', 'Bass'], [t.name for t in self.song.tracks])
        self.assertFalse(self.drums.mute)

    def test_a_track_you_had_muted_stays_muted_after_undo(self):
        self.drums.mute = True
        observable = self.bridge._production_observable_rollback_revision()
        applied = self.job([{'type': 'split_drum_track', 'track_id': self.drum_id, 'lanes': self.lanes()}])
        self.assertNotIn('muted_source', applied)
        self.job([{'type': 'rollback_split_drum_track', 'created_tracks': applied['created_tracks'],
                   'expected_post_rollback_observable_revision': observable,
                   'source_track_id': self.drum_id, 'unmute_source': False}])
        self.assertTrue(self.drums.mute)

    def test_undo_refuses_an_edited_lane(self):
        observable = self.bridge._production_observable_rollback_revision()
        applied = self.job([{'type': 'split_drum_track', 'track_id': self.drum_id, 'lanes': self.lanes()}])
        self.song.tracks[1].clip_slots[0].clip.notes.append((36, 3.0, .25, 127, False))
        undo = self.job([{'type': 'rollback_split_drum_track', 'created_tracks': applied['created_tracks'],
                          'expected_post_rollback_observable_revision': observable}])
        self.assertEqual('Failed', undo['status'])
        self.assertIn('edited', undo['error'])
        self.assertEqual(6, len(self.song.tracks))

    def test_overlapping_lanes_are_refused_before_anything_changes(self):
        lanes = self.lanes()
        lanes[1]['notes'] = [36, 38]
        with self.assertRaises(RuntimeError):
            self.job([{'type': 'split_drum_track', 'track_id': self.drum_id, 'lanes': lanes}])
        self.assertEqual(2, len(self.song.tracks))


if __name__ == '__main__':
    unittest.main()
