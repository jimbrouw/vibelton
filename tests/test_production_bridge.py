"""Fixture coverage for the narrowly-scoped Phase 1 bridge executor."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch


path = Path(__file__).resolve().parents[1] / 'ableton_remote_script/Vibelton/composition_bridge.py'
spec = importlib.util.spec_from_file_location('production_bridge_test', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Track:
    def __init__(self) -> None:
        self.name = 'Bass'
        self.has_midi_input = True
        self.devices = []
        self.arrangement_clips = []
        self.output_routing_type = NS(display_name='Main')
        self.mixer_device = NS(volume=NS(value=.6), panning=QuantizedParameter(0.0), sends=[])


class QuantizedParameter:
    """Model Live returning a value within float precision of the write."""
    def __init__(self, value: float) -> None:
        self._value = value

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        self._value = float(value) + (0.000000001 if value else 0.0)


class Song:
    def __init__(self) -> None:
        self.tracks = [Track()]
        self.tempo = 124
        self.signature_numerator = 4
        self.signature_denominator = 4


class ArrangementClip:
    def __init__(self, start: float, length: float = 64.0, name: str = 'source') -> None:
        self.name, self.start_time, self.length = name, float(start), float(length)
        self.end_time = self.start_time + self.length
        self.is_midi_clip = True
        self.loop_start, self.loop_end = 0.0, self.length
        self.signature_numerator, self.signature_denominator = 4, 4
        self.notes = [(60, 0.0, 1.0, 100, False)]

    def get_notes(self, *_args):
        return self.notes


class ArrangementTrack(Track):
    def __init__(self, *, fail_after: int | None = None) -> None:
        super().__init__()
        self.arrangement_clips = [ArrangementClip(0.0)]
        self.fail_after = fail_after
        self.copy_count = 0

    def duplicate_clip_to_arrangement(self, source, destination: float) -> None:
        self.copy_count += 1
        if self.fail_after is not None and self.copy_count > self.fail_after:
            raise RuntimeError('fixture copy failure')
        self.arrangement_clips.append(ArrangementClip(destination, source.length, source.name))

    def delete_clip(self, clip) -> None:
        self.arrangement_clips.remove(clip)


class ArrangementSong(Song):
    def __init__(self, *, fail_after: int | None = None) -> None:
        super().__init__()
        self.tracks = [ArrangementTrack(fail_after=fail_after)]
        self.cue_points = []
        self.current_song_time = 0.0

    def set_or_delete_cue(self) -> None:
        for index, cue in enumerate(self.cue_points):
            if abs(cue.time - self.current_song_time) < .00001:
                self.cue_points.pop(index)
                return
        self.cue_points.append(Cue(self.current_song_time))


class SessionSlot:
    def __init__(self, clip=None) -> None:
        self.clip = clip

    @property
    def has_clip(self):
        return self.clip is not None

    def duplicate_clip_to(self, target) -> None:
        target.clip = ArrangementClip(0.0, self.clip.length, self.clip.name)


class SessionTrack(ArrangementTrack):
    def __init__(self) -> None:
        super().__init__()
        self.clip_slots = [SessionSlot(ArrangementClip(0.0, 16.0, 'Session groove')),
                           SessionSlot()]


class SessionSong(ArrangementSong):
    def __init__(self) -> None:
        super().__init__()
        self.tracks = [SessionTrack()]
        self.scenes = [NS(name='Original one'), NS(name='Original two')]

    def create_scene(self, _index) -> None:
        self.scenes.append(NS(name=''))
        for track in self.tracks:
            track.clip_slots.append(SessionSlot())

    def delete_scene(self, index) -> None:
        self.scenes.pop(index)
        for track in self.tracks:
            track.clip_slots.pop(index)


class Cue:
    def __init__(self, time_value: float) -> None:
        self.time = time_value
        self.name = ''


class TemplateTrack(Track):
    def __init__(self, name: str, track_type: str, *, group: bool = False) -> None:
        super().__init__()
        self.name = name
        self.has_midi_input = track_type == 'midi'
        self.color_index = 0
        self.is_foldable = group
        self.group_track = None
        self.clip_slots = []

    def create_midi_clip(self, start_time, length):
        clip = NS(name='', length=float(length), start_time=float(start_time), end_time=float(start_time) + float(length),
                  is_midi_clip=True, notes=[], loop_start=0.0, loop_end=float(length), signature_numerator=4,
                  signature_denominator=4)
        clip.get_notes = lambda *_args: clip.notes
        self.arrangement_clips.append(clip)
        return clip

    def delete_clip(self, clip):
        self.arrangement_clips.remove(clip)


class TemplateSong:
    def __init__(self) -> None:
        self.tracks = [TemplateTrack(name, kind) for name, kind in
                       (('1-MIDI', 'midi'), ('2-MIDI', 'midi'), ('3-Audio', 'audio'), ('4-Audio', 'audio'))]
        self.tempo = 120.0
        self.signature_numerator = 4
        self.signature_denominator = 4
        self.cue_points = []
        self.current_song_time = 0.0
        self.song_length = 1024.0
        self._current_group = None

    def delete_track(self, index: int) -> None:
        if len(self.tracks) == 1:
            raise RuntimeError("Couldn't delete track.")
        self.tracks.pop(index)
        if not self.tracks:
            self._current_group = None

    def create_group_track(self, _index: int) -> None:
        group = TemplateTrack('', 'audio', group=True)
        self.tracks.append(group)
        self._current_group = group

    def create_midi_track(self, _index: int) -> None:
        track = TemplateTrack('', 'midi')
        track.group_track = self._current_group
        self.tracks.append(track)

    def create_audio_track(self, _index: int) -> None:
        track = TemplateTrack('', 'audio')
        track.group_track = self._current_group
        self.tracks.append(track)

    def set_or_delete_cue(self) -> None:
        for index, cue in enumerate(self.cue_points):
            if abs(cue.time - self.current_song_time) < .00001:
                self.cue_points.pop(index)
                return
        self.cue_points.append(Cue(self.current_song_time))


class FlatTemplateSong(TemplateSong):
    # Models the installed Live bridge: it can create tracks/locators/colours,
    # but has no native group-track constructor.
    create_group_track = None

    def __init__(self) -> None:
        super().__init__()
        self.song_length = 0.0


class ProductionBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = patch.object(module.os.path, 'expanduser', return_value=self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.song = Song()
        self.bridge = module.CompositionBridge()
        self.bridge._composition_init()
        self.bridge.song = lambda: self.song
        self.bridge._log = lambda *args: None
        self.track_id = self.bridge._composition_track_id(self.song.tracks[0])

    def action(self, revision: str, pan: float) -> dict:
        return {
            'type': 'production_apply', 'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session, 'source_revision': revision,
            'actions': [{'type': 'set_track_mixer', 'target_track_id': self.track_id, 'values': {'pan': pan}}],
        }

    def result(self, action: dict) -> dict:
        file = Path(self.tmp.name) / '.vibelton' / 'production-executions' / (action['job_id'] + '.json')
        return json.loads(file.read_text())

    def test_apply_readback_and_explicit_inverse_restore_fixture(self) -> None:
        first = self.action(self.bridge._production_state()['revision'], .25)
        self.bridge._production_apply(first)
        self.assertAlmostEqual(.25, self.song.tracks[0].mixer_device.panning.value)
        applied = self.result(first)
        self.assertEqual('Applied', applied['status'])
        self.assertEqual(0.0, applied['before'][0]['values']['pan'])
        second = self.action(applied['post_revision'], 0.0)
        self.bridge._production_apply(second)
        self.assertEqual(0.0, self.song.tracks[0].mixer_device.panning.value)
        self.assertEqual('Applied', self.result(second)['status'])

    def test_stale_state_is_rejected_before_mutation(self) -> None:
        action = self.action('stale', .25)
        with self.assertRaisesRegex(RuntimeError, 'state changed'):
            self.bridge._production_apply(action)
        self.assertEqual(0.0, self.song.tracks[0].mixer_device.panning.value)
        self.assertEqual('Failed', self.result(action)['status'])

    def test_arrangement_copy_readback_and_exact_inverse_fixture(self) -> None:
        self.song = ArrangementSong()
        track = self.song.tracks[0]
        source = track.arrangement_clips[0]
        fingerprint = self.bridge._composition_clip_snapshot(source)
        action = {
            'type': 'production_apply', 'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session, 'source_revision': self.bridge._production_state()['revision'],
            'actions': [{'type': 'apply_arrangement_copies', 'expected_end_beat': 576.0, 'locators_deferred': True,
                         'copies': [{'source_track_id': self.bridge._composition_track_id(track), 'source_start_beat': 0.0,
                                     'source_fingerprint': fingerprint, 'destination_beat': beat}
                                    for beat in (64.0, 128.0, 192.0, 256.0, 320.0, 384.0, 448.0, 512.0)],
                         'locators': [], 'locator_definitions': [{'time': beat, 'name': 'L%d' % index}
                                      for index, beat in enumerate((0.0, 64.0, 128.0, 256.0, 320.0, 384.0, 512.0))]}],
        }
        before_observable_revision = self.bridge._production_observable_rollback_revision()
        self.bridge._production_apply(action)
        applied = self.result(action)
        self.assertEqual('Applied', applied['status'])
        self.assertEqual(9, len(track.arrangement_clips))
        self.assertEqual([], self.song.cue_points)

        # Live retains the extended song length after deletion.  It must not
        # invalidate exact observable rollback of the editable Set contents.
        self.song.song_length = 576.0
        self.assertEqual(fingerprint, self.bridge._composition_clip_snapshot(track.arrangement_clips[0]))
        rollback = {
            'type': 'production_apply', 'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session,
            # The full revision remains the preflight guard.  After Live
            # retains the extended song length, draft rollback from that
            # actual current revision.
            'source_revision': self.bridge._production_state()['revision'],
            'actions': [{'type': 'rollback_arrangement_copies', 'copies': applied['created_copies'],
                         'locators': applied['created_locators'],
                         'expected_post_rollback_observable_revision': before_observable_revision}],
        }
        # Match the real Control Surface, where schedule_message exists even
        # though this deferred-locator rollback has no cue targets.
        self.bridge.schedule_message = lambda _ticks, callback: callback()
        self.bridge._production_apply(rollback)
        self.assertEqual('Applied', self.result(rollback)['status'])
        self.assertEqual(1, len(track.arrangement_clips))
        self.assertEqual([], self.song.cue_points)

    def test_multitrack_copies_preserve_existing_locators(self) -> None:
        self.song = ArrangementSong()
        self.song.tracks.append(ArrangementTrack())
        cue = Cue(0.0)
        cue.name = 'Original marker'
        self.song.cue_points = [cue]
        before = self.bridge._production_observable_rollback_revision()
        copies = []
        for track in self.song.tracks:
            copies.append({'source_track_id': self.bridge._composition_track_id(track),
                           'source_start_beat': 0.0,
                           'source_fingerprint': self.bridge._composition_clip_snapshot(track.arrangement_clips[0]),
                           'destination_beat': 64.0})
        action = {'type': 'production_apply', 'job_id': str(uuid.uuid4()),
                  'session_id': self.bridge._composition_session,
                  'source_revision': self.bridge._production_state()['revision'],
                  'actions': [{'type': 'apply_arrangement_copies', 'expected_end_beat': 128.0,
                               'copies': copies, 'locators': [], 'locators_deferred': True,
                               'locator_definitions': [{'time': float(i * 16), 'name': 'Section %d' % i}
                                                       for i in range(7)]}]}
        self.bridge._production_apply(action)
        result = self.result(action)
        self.assertEqual('Applied', result['status'])
        self.assertEqual(2, len(result['created_copies']))
        self.assertEqual('Original marker', self.song.cue_points[0].name)
        rollback = {'type': 'production_apply', 'job_id': str(uuid.uuid4()),
                    'session_id': self.bridge._composition_session,
                    'source_revision': self.bridge._production_state()['revision'],
                    'actions': [{'type': 'rollback_arrangement_copies',
                                 'copies': result['created_copies'], 'locators': [],
                                 'expected_post_rollback_observable_revision': before}]}
        self.bridge._production_apply(rollback)
        self.assertEqual('Applied', self.result(rollback)['status'])
        self.assertEqual([1, 1], [len(track.arrangement_clips) for track in self.song.tracks])
        self.assertEqual('Original marker', self.song.cue_points[0].name)

    def test_session_scenes_copy_and_exact_rollback(self) -> None:
        self.song = SessionSong()
        track = self.song.tracks[0]
        track_id = self.bridge._composition_track_id(track)
        fingerprint = self.bridge._composition_clip_snapshot(track.clip_slots[0].clip)
        before = self.bridge._production_observable_rollback_revision()
        action = {'type': 'production_apply', 'job_id': str(uuid.uuid4()),
                  'session_id': self.bridge._composition_session,
                  'source_revision': self.bridge._production_state()['revision'],
                  'actions': [{'type': 'apply_session_scene_map', 'source_scene_count': 2,
                               'scenes': [{'name': 'Vibelton section %d' % i, 'bar_count': 8,
                                           'copies': [{'track_id': track_id, 'source_scene_index': 0,
                                                       'source_fingerprint': fingerprint}]}
                                          for i in range(7)]}]}
        self.bridge._production_apply(action)
        applied = self.result(action)
        self.assertEqual('Applied', applied['status'])
        self.assertEqual(9, len(self.song.scenes))
        self.assertEqual(9, len(track.clip_slots))
        self.assertEqual('Session groove', track.clip_slots[0].clip.name)
        rollback = {'type': 'production_apply', 'job_id': str(uuid.uuid4()),
                    'session_id': self.bridge._composition_session,
                    'source_revision': self.bridge._production_state()['revision'],
                    'actions': [{'type': 'rollback_session_scene_map', 'source_scene_count': 2,
                                 'created_scenes': applied['created_scenes'],
                                 'expected_post_rollback_observable_revision': before}]}
        self.bridge._production_apply(rollback)
        self.assertEqual('Applied', self.result(rollback)['status'])
        self.assertEqual(['Original one', 'Original two'], [scene.name for scene in self.song.scenes])

    def test_arrangement_source_checks_and_partial_failure_are_safe(self) -> None:
        self.song = ArrangementSong(fail_after=1)
        track = self.song.tracks[0]
        fingerprint = self.bridge._composition_clip_snapshot(track.arrangement_clips[0])
        source_id = self.bridge._composition_track_id(track)
        action = {'type': 'production_apply', 'job_id': str(uuid.uuid4()), 'session_id': self.bridge._composition_session,
                  'source_revision': self.bridge._production_state()['revision'], 'actions': [
                      {'type': 'apply_arrangement_copies', 'expected_end_beat': 128.0, 'locators_deferred': True,
                       'copies': [{'source_track_id': source_id, 'source_start_beat': 0.0,
                                   'source_fingerprint': fingerprint, 'destination_beat': 64.0},
                                  {'source_track_id': source_id, 'source_start_beat': 0.0,
                                   'source_fingerprint': fingerprint, 'destination_beat': 128.0}],
                       'locators': [], 'locator_definitions': [{'time': beat, 'name': 'L%d' % index}
                                    for index, beat in enumerate((0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0))]},
                  ]}
        self.bridge._production_apply(action)
        self.assertEqual('Partial failure', self.result(action)['status'])
        self.assertEqual(2, len(track.arrangement_clips))
        # Replaying the same job cannot create another copy.
        with self.assertRaisesRegex(RuntimeError, 'already attempted'):
            self.bridge._production_apply(action)
        self.assertEqual(2, len(track.arrangement_clips))

    def test_arrangement_fingerprint_mismatch_rejects_before_mutation(self) -> None:
        self.song = ArrangementSong()
        track = self.song.tracks[0]
        action = {'type': 'production_apply', 'job_id': str(uuid.uuid4()), 'session_id': self.bridge._composition_session,
                  'source_revision': self.bridge._production_state()['revision'], 'actions': [
                      {'type': 'apply_arrangement_copies', 'expected_end_beat': 64.0, 'locators_deferred': True,
                       'copies': [{'source_track_id': self.bridge._composition_track_id(track), 'source_start_beat': 0.0,
                                   'source_fingerprint': 'b' * 64, 'destination_beat': 64.0}],
                       'locators': [], 'locator_definitions': [{'time': beat, 'name': 'L%d' % index}
                                    for index, beat in enumerate((0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0))]},
                  ]}
        with self.assertRaisesRegex(RuntimeError, 'source is missing, ambiguous, or changed'):
            self.bridge._production_apply(action)
        self.assertEqual(1, len(track.arrangement_clips))
        self.assertEqual('Failed', self.result(action)['status'])

    def test_duplicate_job_never_replays(self) -> None:
        action = self.action(self.bridge._production_state()['revision'], .25)
        self.bridge._production_apply(action)
        with self.assertRaisesRegex(RuntimeError, 'already attempted'):
            self.bridge._production_apply(action)
        self.assertAlmostEqual(.25, self.song.tracks[0].mixer_device.panning.value)

    def test_classic_house_template_and_recorded_rollback_fixture(self) -> None:
        self.song = TemplateSong()
        original_tracks = [(track.name, track.has_midi_input, track.color_index)
                           for track in self.song.tracks]
        first = {
            'type': 'production_apply', 'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session, 'source_revision': self.bridge._production_state()['revision'],
            'actions': [{'type': 'apply_song_sketch_template', 'preset_id': 'classic-house-124-club-mix/v1',
                         'layout_mode': 'grouped', 'locator_range': True}],
        }
        self.bridge._production_apply(first)
        applied = self.result(first)
        self.assertEqual('Applied', applied['status'])
        self.assertEqual(18, len(self.song.tracks))
        self.assertEqual(124.0, self.song.tempo)
        self.assertEqual(7, len(self.song.cue_points))
        self.assertTrue(all(track.color_index >= 0 for track in self.song.tracks))
        children = [track for track in self.song.tracks if not track.is_foldable]
        self.assertEqual(12, len(children))
        self.assertTrue(all(track.group_track is not None for track in children))
        second = {
            'type': 'production_apply', 'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session, 'source_revision': applied['post_revision'],
            'actions': [{'type': 'rollback_song_sketch_template', 'preset_id': 'classic-house-124-club-mix/v1',
                         'created_track_ids': applied['created_track_ids'], 'created_locators': applied['created_locators'],
                         'restore_tempo': 120.0, 'restore_metre': [4, 4], 'restore_tracks': applied['restore_tracks']}],
        }
        self.bridge._production_apply(second)
        self.assertEqual('Applied', self.result(second)['status'])
        self.assertEqual(['1-MIDI', '2-MIDI', '3-Audio', '4-Audio'], [track.name for track in self.song.tracks])
        self.assertEqual(original_tracks, [(track.name, track.has_midi_input, track.color_index)
                                           for track in self.song.tracks])
        self.assertEqual(120.0, self.song.tempo)
        self.assertEqual([], self.song.cue_points)

    def test_flat_classic_house_template_and_recorded_rollback_fixture(self) -> None:
        self.song = FlatTemplateSong()
        # The live bridge waits for cue-point selection/readback on later ticks.
        self.bridge.schedule_message = lambda _ticks, callback: callback()
        original_tracks = [(track.name, track.has_midi_input, track.color_index)
                           for track in self.song.tracks]
        first = {
            'type': 'production_apply', 'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session, 'source_revision': self.bridge._production_state()['revision'],
            'actions': [{'type': 'apply_song_sketch_template', 'preset_id': 'classic-house-124-club-mix/v1',
                         'layout_mode': 'flat', 'locator_range': False}],
        }
        self.bridge._production_apply(first)
        applied = self.result(first)
        self.assertEqual('Applied', applied['status'])
        self.assertEqual('flat', applied['layout_mode'])
        self.assertIn('Groups were not created', applied['warning'])
        self.assertEqual(['Kick', 'Snare / Clap', 'Hats', 'Percussion', 'Bass', 'Chords', 'Lead', 'Hook',
                          'Atmosphere', 'Vocal', 'FX / Risers', 'Reference'], [track.name for track in self.song.tracks])
        self.assertTrue(all(track.group_track is None for track in self.song.tracks))
        self.assertEqual(124.0, self.song.tempo)
        self.assertEqual([], self.song.cue_points)
        self.assertTrue(applied['locators_deferred'])
        self.assertIn('Arrangement locators were deferred', applied['warnings'][-1])
        self.assertEqual(7, len(applied['locator_definitions']))
        second = {
            'type': 'production_apply', 'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session, 'source_revision': applied['post_revision'],
            'actions': [{'type': 'rollback_song_sketch_template', 'preset_id': 'classic-house-124-club-mix/v1',
                         'created_track_ids': applied['created_track_ids'], 'created_locators': applied['created_locators'],
                         'restore_tempo': 120.0, 'restore_metre': [4, 4], 'restore_tracks': applied['restore_tracks']}],
        }
        self.bridge._production_apply(second)
        self.assertEqual('Applied', self.result(second)['status'])
        self.assertEqual(['1-MIDI', '2-MIDI', '3-Audio', '4-Audio'], [track.name for track in self.song.tracks])
        self.assertEqual(original_tracks, [(track.name, track.has_midi_input, track.color_index)
                                           for track in self.song.tracks])
        self.assertEqual([], self.song.cue_points)

    def test_template_rejects_a_stale_locator_capability_before_mutating(self) -> None:
        self.song = FlatTemplateSong()
        action = {'type': 'production_apply', 'job_id': str(uuid.uuid4()), 'session_id': self.bridge._composition_session,
                  'source_revision': self.bridge._production_state()['revision'], 'actions': [
                      {'type': 'apply_song_sketch_template', 'preset_id': 'classic-house-124-club-mix/v1',
                       'layout_mode': 'flat', 'locator_range': True},
                  ]}
        with self.assertRaisesRegex(RuntimeError, 'locator capability changed'):
            self.bridge._production_apply(action)
        self.assertEqual(['1-MIDI', '2-MIDI', '3-Audio', '4-Audio'], [track.name for track in self.song.tracks])

    def test_sends_and_device_parameter_apply_and_readback(self) -> None:
        track = self.song.tracks[0]
        track.mixer_device.sends = [QuantizedParameter(0.1), QuantizedParameter(0.2)]
        param_cutoff = QuantizedParameter(0.35)
        param_cutoff.name = 'Frequency'
        param_cutoff.min = 0.0
        param_cutoff.max = 1.0
        param_cutoff.is_quantized = False
        track.devices = [NS(name='Auto Filter', class_name='AutoFilter', parameters=[param_cutoff])]

        state = self.bridge._production_state()
        self.assertEqual(1, len(state['tracks'][0]['devices'][0]['parameters']))
        first = {
            'type': 'production_apply', 'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session, 'source_revision': state['revision'],
            'actions': [
                {'type': 'set_track_mixer', 'target_track_id': self.track_id, 'values': {'send_0': 0.55, 'send_1': 0.75}},
                {'type': 'set_device_parameter', 'target_track_id': self.track_id, 'device_index': 0, 'parameter_index': 0, 'value': 0.82},
            ],
        }
        self.bridge._production_apply(first)
        applied = self.result(first)
        self.assertEqual('Applied', applied['status'])
        self.assertAlmostEqual(0.55, track.mixer_device.sends[0].value)
        self.assertAlmostEqual(0.75, track.mixer_device.sends[1].value)
        self.assertAlmostEqual(0.82, param_cutoff.value)
        self.assertAlmostEqual(0.1, applied['before'][0]['values']['send_0'])
        self.assertAlmostEqual(0.35, applied['before'][1]['value'])

    def test_session_to_arrangement_copies_and_recorded_rollback_fixture(self) -> None:
        self.song = SessionSong()
        track = self.song.tracks[0]
        track_id = self.bridge._composition_track_id(track)
        fingerprint = self.bridge._composition_clip_snapshot(track.clip_slots[0].clip)
        before_obs = self.bridge._production_observable_rollback_revision()
        action = {
            'type': 'production_apply',
            'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session,
            'source_revision': self.bridge._production_state()['revision'],
            'actions': [{
                'type': 'apply_session_to_arrangement_copies',
                'copies': [{
                    'track_id': track_id,
                    'source_scene_index': 0,
                    'source_fingerprint': fingerprint,
                    'destination_beat': 64.0,
                }],
            }],
        }
        self.bridge._production_apply(action)
        applied = self.result(action)
        self.assertEqual('Applied', applied['status'])
        self.assertTrue(applied['session_to_arrangement_verified'])
        self.assertEqual(2, len(track.arrangement_clips))
        self.assertEqual(64.0, track.arrangement_clips[-1].start_time)

        rollback = {
            'type': 'production_apply',
            'job_id': str(uuid.uuid4()),
            'session_id': self.bridge._composition_session,
            'source_revision': self.bridge._production_state()['revision'],
            'actions': [{
                'type': 'rollback_session_to_arrangement_copies',
                'copies': applied['created_copies'],
                'expected_post_rollback_observable_revision': before_obs,
            }],
        }
        self.bridge._production_apply(rollback)
        rb_res = self.result(rollback)
        self.assertEqual('Applied', rb_res['status'])
        self.assertTrue(rb_res['session_to_arrangement_rollback_verified'])
        self.assertEqual(1, len(track.arrangement_clips))


if __name__ == '__main__':
    unittest.main()

