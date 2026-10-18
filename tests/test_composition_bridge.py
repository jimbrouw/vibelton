"""Contract tests against the real executor with a minimal in-memory Live host."""
import copy
import importlib.util
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'ableton_remote_script/Vibelton/composition_bridge.py'
spec=importlib.util.spec_from_file_location('composition_bridge_test',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class Clip:
    def __init__(self,length=4):
        self.name='Original';self.length=length;self.loop_start=0;self.loop_end=length
        self.signature_numerator=4;self.signature_denominator=4;self.is_midi_clip=True
        self.notes=[(60,0.,1.,90,False)];self.start_time=0;self.end_time=length
    def get_notes(self,*args):return self.notes
    def set_notes(self,notes):self.notes=list(notes)


class Slot:
    def __init__(self,clip=None):self.clip=clip
    @property
    def has_clip(self):return self.clip is not None
    def create_clip(self,length):
        if self.has_clip:raise RuntimeError('Cannot overwrite')
        self.clip=Clip(length)


class Track:
    def __init__(self):
        self.name='My synth';self.has_midi_input=True;self.clip_slots=[Slot(Clip())]
        self.devices=[NS(name='User synth',class_name='Plugin',parameters=[NS(name='Cutoff',value=.3)])]
        self.mixer_device=NS(volume=NS(value=.6),panning=NS(value=.2),sends=[NS(value=.1)])
        self.arrangement_clips=[Clip()];self.fail_copy=False
    def duplicate_clip_to_arrangement(self,clip,start):
        if self.fail_copy:raise RuntimeError('Simulated copy failure')
        new=copy.deepcopy(clip);new.start_time=start;new.end_time=start+new.length;self.arrangement_clips.append(new)


class Song:
    def __init__(self):
        self.tracks=[Track()];self.scenes=[NS(name='User scene')];self.tempo=135;self.is_playing=False
        self.signature_numerator=4;self.signature_denominator=4
        self.master_track=NS(mixer_device=NS(song_tempo=NS(automation_state=0)))
    def create_scene(self,index):
        self.scenes.append(NS(name=''));[t.clip_slots.append(Slot()) for t in self.tracks]
    def stop_playing(self):self.is_playing=False
    def start_playing(self):self.is_playing=True
    def stop_all_clips(self):pass


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        p=patch.object(module.os.path,'expanduser',return_value=self.tmp.name);p.start();self.addCleanup(p.stop)
        self.song=Song();self.bridge=module.CompositionBridge();self.bridge._composition_init()
        self.bridge.song=lambda:self.song;self.bridge._log=lambda *args:None
        self.bridge.application=lambda:NS(view=NS(show_view=lambda *args:None))
        trackid=self.bridge._composition_track_id(self.song.tracks[0])
        self.action={'type':'composition_apply','job_id':str(uuid.uuid4()),'session_id':self.bridge._composition_session,
                     'scene_count':1,'tracks':[{'id':trackid,'name':'My synth'}], 'bpm':168,'start_beat':8.,'total_beats':7.,'preview':False,
                     'clips':[{'track_id':trackid,'scene_index':1,'name':'CL test','start_beat':8.,'length_beats':7.,'metre':[7,8],
                               'notes':[{'pitch':60,'start':0.,'duration':.25,'velocity':90}]}]}
    def result(self):return json.loads((Path(self.tmp.name)/'.vibelton/composition-executions'/(self.action['job_id']+'.json')).read_text())

    def test_apply_fills_section_preserves_original_and_stays_stopped(self):
        original=self.bridge._composition_clip_snapshot(self.song.tracks[0].clip_slots[0].clip)
        self.bridge._composition_apply(self.action)
        result=self.result();self.assertEqual('Applied',result['status']);self.assertTrue(result['readback_verified'])
        self.assertTrue(result['markers_pending']);self.assertEqual(1,result['completed_clips'])
        self.assertFalse(self.song.is_playing)
        clip=self.song.tracks[0].arrangement_clips[-1]
        self.assertEqual((8,15,7,8),(clip.start_time,clip.end_time,clip.signature_numerator,clip.signature_denominator))
        self.assertEqual(original,self.bridge._composition_clip_snapshot(self.song.tracks[0].clip_slots[0].clip))

    def test_duplicate_never_replays(self):
        self.bridge._composition_apply(self.action)
        with self.assertRaisesRegex(RuntimeError,'already attempted'):self.bridge._composition_apply(self.action)
        self.assertEqual(2,len(self.song.tracks[0].arrangement_clips))
        self.assertEqual('Applied',self.result()['status'])

    def test_reject_occupied_range_before_mutation(self):
        self.action['start_beat']=0
        with self.assertRaisesRegex(RuntimeError,'occupied'):self.bridge._composition_apply(self.action)
        self.assertEqual(1,len(self.song.scenes));self.assertEqual(135,self.song.tempo)
        self.assertEqual('Failed',self.result()['status'])

    def test_missing_track_or_changed_session_rejected(self):
        self.song.tracks[0].name='Renamed'
        with self.assertRaisesRegex(RuntimeError,'missing or changed'):self.bridge._composition_apply(self.action)
        self.assertEqual('Failed',self.result()['status'])
        self.action['job_id']=str(uuid.uuid4());self.action['session_id']='stale'
        with self.assertRaisesRegex(RuntimeError,'session changed'):self.bridge._composition_apply(self.action)

    def test_occupied_session_slot_rejected(self):
        self.action['clips'][0]['scene_index']=0
        with self.assertRaisesRegex(RuntimeError,'new Session scenes'):self.bridge._composition_apply(self.action)
        self.assertEqual('Original',self.song.tracks[0].clip_slots[0].clip.name)

    def test_partial_failure_is_durable_without_retry(self):
        self.song.tracks[0].fail_copy=True
        with self.assertRaisesRegex(RuntimeError,'Simulated copy failure'):self.bridge._composition_apply(self.action)
        result=self.result();self.assertEqual('Partial failure',result['status']);self.assertFalse(result['readback_verified'])
        self.assertEqual(0,result['action_index'])
        with self.assertRaisesRegex(RuntimeError,'already attempted'):self.bridge._composition_apply(self.action)

    def test_preview_loops_only_selected_range(self):
        self.action['preview']=True;self.bridge._composition_apply(self.action)
        self.assertTrue(self.song.is_playing);self.assertEqual(8,self.song.loop_start);self.assertEqual(7,self.song.loop_length)

    def test_full_build_after_preview_disables_short_loop(self):
        self.action['preview']=True;self.bridge._composition_apply(self.action)
        self.action['job_id']=str(uuid.uuid4());self.action['scene_count']=2
        self.action['preview']=False;self.action['start_beat']=24
        self.action['clips'][0]['scene_index']=2;self.action['clips'][0]['start_beat']=24
        self.bridge._composition_apply(self.action)
        self.assertFalse(self.song.loop);self.assertFalse(self.song.is_playing)
        self.assertEqual(24,self.song.current_song_time)

    def test_note_out_of_bounds_rejected_before_mutation(self):
        self.action['clips'][0]['notes'][0]['duration']=100
        with self.assertRaisesRegex(RuntimeError,'Invalid MIDI'):self.bridge._composition_apply(self.action)
        self.assertEqual(1,len(self.song.scenes))

    def test_tempo_automation_is_not_silently_overridden(self):
        self.song.master_track.mixer_device.song_tempo.automation_state=1
        with self.assertRaisesRegex(RuntimeError,'Tempo automation'):self.bridge._composition_apply(self.action)
        self.assertEqual(135,self.song.tempo);self.assertEqual(1,len(self.song.scenes))

    def test_clip_musical_summary_and_scale_state_exposed(self):
        self.song.root_note = 8
        self.song.scale_name = 'Minor'
        state = self.bridge._composition_state()
        self.assertEqual(8, state['root_note'])
        self.assertEqual('Minor', state['scale_name'])
        clip_summary = state['composition_tracks'][0]['arrangement_clips'][0]['summary']
        self.assertEqual('midi', clip_summary['kind'])
        self.assertEqual(1, clip_summary['note_count'])
        self.assertEqual(60, clip_summary['pitch_min'])
        self.assertEqual([0], clip_summary['pitch_classes'])

    def test_live12_add_new_notes_probability_and_velocity_deviation(self):
        added_payloads = []
        orig_create = Slot.create_clip

        def create_live12_clip(slot_self, length):
            orig_create(slot_self, length)
            def add_new_notes(payload):
                added_payloads.append(payload)
                notes_list = payload['notes'] if isinstance(payload, dict) else payload
                slot_self.clip.notes = [
                    (int(n['pitch']), float(n['start_time']), float(n['duration']), int(n['velocity']), bool(n.get('mute', False)))
                    for n in notes_list
                ]
            slot_self.clip.add_new_notes = add_new_notes

        with patch.object(Slot, 'create_clip', create_live12_clip):
            self.action['clips'][0]['notes'] = [
                {'pitch': 36, 'start': 0.0, 'duration': 0.25, 'velocity': 108, 'probability': 1.0, 'velocity_deviation': 4},
                {'pitch': 38, 'start': 1.75, 'duration': 0.12, 'velocity': 64, 'probability': 0.78, 'velocity_deviation': 10},
            ]
            self.bridge._composition_apply(self.action)
        self.assertEqual('Applied', self.result()['status'])
        self.assertEqual(1, len(added_payloads))
        written = added_payloads[0]['notes']
        self.assertEqual(0.78, written[1]['probability'])
        self.assertEqual(10.0, written[1]['velocity_deviation'])

    def test_live12_add_new_notes_runtime_fallback_and_preflight_validation(self):
        # 1. Invalid probability (> 1.0) rejected in preflight before mutating Live
        self.action['clips'][0]['notes'] = [
            {'pitch': 36, 'start': 0.0, 'duration': 0.25, 'velocity': 108, 'probability': 1.5, 'velocity_deviation': 0},
        ]
        with self.assertRaisesRegex(RuntimeError, 'Invalid MIDI note probability'):
            self.bridge._composition_apply(self.action)
        self.assertEqual(1, len(self.song.scenes))

        # 2. If add_new_notes({'notes': ...}) raises RuntimeError, falls back to tuple(extended_notes)
        self.action['job_id'] = str(uuid.uuid4())
        tuple_calls = []
        orig_create = Slot.create_clip

        def create_tuple_only_clip(slot_self, length):
            orig_create(slot_self, length)
            def add_new_notes(payload):
                if isinstance(payload, dict):
                    raise RuntimeError('Dict format not supported in this Live 11 build')
                tuple_calls.append(payload)
                slot_self.clip.notes = [
                    (int(n['pitch']), float(n['start_time']), float(n['duration']), int(n['velocity']), bool(n.get('mute', False)))
                    for n in payload
                ]
            slot_self.clip.add_new_notes = add_new_notes

        with patch.object(Slot, 'create_clip', create_tuple_only_clip):
            self.action['clips'][0]['notes'] = [
                {'pitch': 42, 'start': 0.5, 'duration': 0.125, 'velocity': 76, 'probability': 0.92, 'velocity_deviation': 6},
            ]
            self.bridge._composition_apply(self.action)
        self.assertEqual('Applied', self.result()['status'])
        self.assertEqual(1, len(tuple_calls))
        self.assertEqual(0.92, tuple_calls[0][0]['probability'])

        # 3. If dict and tuple-of-dicts raise TypeError, tries Live.Clip.MidiNoteSpecification(**nd) before set_notes
        self.action['job_id'] = str(uuid.uuid4())
        self.action['scene_count'] = len(self.song.scenes)
        self.action['start_beat'] = 48
        self.action['clips'][0]['scene_index'] = 3
        self.action['clips'][0]['start_beat'] = 48

        class FakeMidiNoteSpec:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        spec_calls = []
        def create_spec_clip(slot_self, length):
            orig_create(slot_self, length)
            def spec_only_add_new_notes(payload):
                if isinstance(payload, tuple) and payload and isinstance(payload[0], FakeMidiNoteSpec):
                    spec_calls.append(payload)
                    slot_self.clip.notes = tuple(
                        (item.kwargs['pitch'], item.kwargs['start_time'], item.kwargs['duration'], item.kwargs['velocity'], item.kwargs['mute'])
                        for item in payload
                    )
                    return
                raise TypeError('MidiNoteSpecification required')
            slot_self.clip.add_new_notes = spec_only_add_new_notes

        with patch.object(self.bridge, '_midi_note_specification_cls', return_value=FakeMidiNoteSpec):
            with patch.object(Slot, 'create_clip', create_spec_clip):
                self.bridge._composition_apply(self.action)
        self.assertEqual('Applied', self.result()['status'])
        self.assertEqual(1, len(spec_calls))
        self.assertEqual(0.92, spec_calls[0][0].kwargs['probability'])
        self.assertNotIn('extended_notes_degraded', self.result())

        # 4. If all add_new_notes paths raise TypeError, falls back to clip.set_notes(raw) and records extended_notes_degraded=True
        self.action['job_id'] = str(uuid.uuid4())
        self.action['scene_count'] = len(self.song.scenes)
        self.action['start_beat'] = 64
        self.action['clips'][0]['scene_index'] = 4
        self.action['clips'][0]['start_beat'] = 64

        def create_set_notes_fallback_clip(slot_self, length):
            orig_create(slot_self, length)
            def broken_add_new_notes(_payload):
                raise TypeError('MidiNoteSpecification required')
            slot_self.clip.add_new_notes = broken_add_new_notes

        with patch.object(Slot, 'create_clip', create_set_notes_fallback_clip):
            self.bridge._composition_apply(self.action)
        self.assertEqual('Applied', self.result()['status'])
        self.assertTrue(self.result()['readback_verified'])
        self.assertTrue(self.result().get('extended_notes_degraded'))

if __name__=='__main__':unittest.main()
