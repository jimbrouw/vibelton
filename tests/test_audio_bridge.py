import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


ROOT=Path(__file__).resolve().parents[1]
fixtures=load('audio_test_fixtures',ROOT/'tests/test_composition_bridge.py')
audio=load('audio_test_bridge',ROOT/'ableton_remote_script/Vibelton/audio_bridge.py')


class Clip(fixtures.Clip):
    def __init__(self,path):
        super().__init__()
        self.is_audio_clip=True; self.is_midi_clip=False; self.file_path=path
        self.warping=True; self.looping=True; self.start_marker=0; self.end_marker=4
        self.pitch_coarse=0; self.pitch_fine=0; self.gain=.7; self.warp_mode=0
        self.warp_markers=[NS(beat_time=0,sample_time=0),NS(beat_time=4,sample_time=4*60/170)]


class Slot(fixtures.Slot):
    def create_audio_clip(self,path):
        if self.has_clip: raise RuntimeError('Cannot overwrite')
        self.clip=Clip(path)


class Host(audio.AudioBridge,fixtures.module.CompositionBridge):
    pass


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        p=patch.object(audio.os.path,'expanduser',return_value=str(root)); p.start(); self.addCleanup(p.stop)
        self.source=root/'Music/LOOP PACKS/Break.wav'; self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b'test audio')
        self.song=fixtures.Song(); self.song.file_path='/sets/Working.als'
        t=self.song.tracks[0]; t.name='Audio'; t.has_midi_input=False; t.clip_slots=[Slot()]
        # Use MIDI originals to verify preservation independently of the new imported audio.
        self.song.create_scene=lambda index:(self.song.scenes.append(NS(name='')),[t.clip_slots.append(Slot()) for t in self.song.tracks])
        self.bridge=Host(); self.bridge._composition_init(); self.bridge.song=lambda:self.song
        self.bridge._log=lambda *args:None
        self.action={'type':'audio_import','job_id':str(uuid.uuid4()),'session_id':self.bridge._composition_session,
                     'source_revision':self.bridge._production_state()['revision'],'expected_set_path':self.song.file_path,
                     'working_copy_confirmed':True,'path':str(self.source),'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest(),
                     'source_bpm':170,'duration_seconds':4*60/170,
                     'track_id':self.bridge._composition_track_id(t),'target_name':'Audio','scene_index':1,
                     'name':'Edited break','settings':{'warping':True,'gain':.5,'pitch_coarse':-2,'start_marker':1,'end_marker':3},
                     'arrangement_beat':8}
    def result(self):
        return json.loads((Path(self.tmp.name)/'.vibelton/sample-executions'/(self.action['job_id']+'.json')).read_text())

    def test_import_edits_and_copies_with_readback_and_preservation(self):
        original=copy.deepcopy(self.song.tracks[0].arrangement_clips[0].__dict__)
        self.bridge._audio_import(self.action)
        result=self.result(); self.assertEqual('Applied',result['status']); self.assertTrue(result['readback_verified'])
        self.assertTrue(result['preserved_originals']); self.assertEqual(.5,result['clip_readback']['audio']['gain'])
        self.assertEqual(original,self.song.tracks[0].arrangement_clips[0].__dict__)
        self.assertEqual(135,self.song.tempo); self.assertFalse(self.song.is_playing)

    def test_same_job_never_replays(self):
        self.bridge._audio_import(self.action)
        with self.assertRaisesRegex(RuntimeError,'already attempted'): self.bridge._audio_import(self.action)
        self.assertEqual(2,len(self.song.scenes))

    def test_unwarped_arrangement_rejected_before_mutation(self):
        self.action['settings']={'warping':False}
        with self.assertRaisesRegex(RuntimeError,'warping=true'): self.bridge._audio_import(self.action)
        self.assertEqual(1,len(self.song.scenes)); self.assertEqual('Failed',self.result()['status'])

    def test_wrong_warp_mapping_stops_before_arrangement_copy(self):
        original = Slot.create_audio_clip
        def import_wrong(slot,path):
            original(slot,path); slot.clip.warp_markers[-1].sample_time=2
        with patch.object(Slot,'create_audio_clip',import_wrong):
            with self.assertRaisesRegex(RuntimeError,'warp timing'): self.bridge._audio_import(self.action)
        self.assertEqual(1,len(self.song.tracks[0].arrangement_clips))
        self.assertEqual('Partial failure',self.result()['status'])

    def test_unwarped_default_is_explicitly_warped_then_checked(self):
        original = Slot.create_audio_clip
        def import_unwarped(slot,path):
            original(slot,path); slot.clip.warping=False; slot.clip.looping=False
        with patch.object(Slot,'create_audio_clip',import_unwarped): self.bridge._audio_import(self.action)
        self.assertEqual('Applied',self.result()['status'])

    def test_stale_revision_and_changed_source_fail_before_mutation(self):
        self.source.write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError,'source changed'): self.bridge._audio_import(self.action)
        self.assertEqual('Failed',self.result()['status']); self.assertEqual(1,len(self.song.scenes))

    def test_partial_failure_records_created_scene_and_clip(self):
        self.song.tracks[0].fail_copy=True
        with self.assertRaisesRegex(RuntimeError,'Simulated copy failure'): self.bridge._audio_import(self.action)
        result=self.result(); self.assertEqual('Partial failure',result['status'])
        self.assertFalse(result['readback_verified']); self.assertEqual(1,result['created_scene_index'])
        self.assertEqual(1,len(result['created_clips']))

    def test_audio_fingerprint_changes_when_source_or_settings_change(self):
        c=Clip(str(self.source)); before=self.bridge._composition_clip_snapshot(c)
        for key,value in [('file_path','elsewhere.wav'),('gain',.2),('pitch_coarse',3),('start_marker',1)]:
            d=copy.deepcopy(c); setattr(d,key,value)
            self.assertNotEqual(before,self.bridge._composition_clip_snapshot(d))
        c.warp_markers[1].sample_time=1.3
        self.assertNotEqual(before,self.bridge._composition_clip_snapshot(c))

    def test_real_read_failure_stays_blocked_and_is_diagnosed(self):
        self.song.tracks[0].arrangement_clips=[NS(name='Unreadable')]
        state=self.bridge._composition_state(); project=self.bridge._production_state()
        self.assertFalse(state['arrangement_readable']); self.assertFalse(project['arrangement_readable'])
        self.assertEqual('Audio',state['arrangement_errors'][0]['track_name'])
        self.action['source_revision']=project['revision']
        with self.assertRaisesRegex(RuntimeError,'readback'): self.bridge._audio_import(self.action)
        self.assertEqual(1,len(self.song.scenes))

    def test_wrong_copy_scene_and_occupied_destination_fail_without_mutation(self):
        for key,value in [('expected_set_path','/sets/Original.als'),('scene_index',0),('arrangement_beat',0)]:
            with self.subTest(key=key):
                action={**self.action,key:value,'job_id':str(uuid.uuid4())}
                with self.assertRaises(RuntimeError): self.bridge._audio_import(action)
        self.assertEqual(1,len(self.song.scenes))

    def test_four_four_midi_preflight_supported(self):
        self.song.tracks[0].has_midi_input=True
        action={'session_id':self.bridge._composition_session,'scene_count':1,'bpm':170,'start_beat':8,'total_beats':4,
                'tracks':[{'id':self.action['track_id'],'name':'Audio'}],
                'clips':[{'track_id':self.action['track_id'],'scene_index':1,'metre':[4,4],
                          'start_beat':8,'length_beats':4,'notes':[]}]}
        self.assertIn(self.action['track_id'],self.bridge._composition_preflight(action))

    def reserve(self,length=64):
        region={'id':str(uuid.uuid4()),'session_id':self.bridge._composition_session,'set_path':self.song.file_path,
                'start_beat':8,'length_beats':length,'original_end':4,'source_revision':self.action['source_revision']}
        path=Path(self.tmp.name)/'.vibelton/sample-regions'/(region['id']+'.json')
        path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(region))
        self.action['region']=region
        return path

    def test_reserved_range_layers_against_other_tracks_without_replacing_them(self):
        self.reserve()
        other=fixtures.Track(); c=other.arrangement_clips[0]; c.start_time=8; c.end_time=72
        self.song.tracks.append(other)
        before=copy.deepcopy(c.__dict__)
        self.action['source_revision']=self.bridge._production_state()['revision']
        self.bridge._audio_import(self.action)
        self.assertEqual('Applied',self.result()['status']); self.assertEqual(before,c.__dict__)

    def test_reserved_range_rejects_tampering_before_mutation(self):
        self.reserve(); self.action['region']['length_beats']=999
        with self.assertRaisesRegex(RuntimeError,'range changed'): self.bridge._audio_import(self.action)
        self.assertEqual(1,len(self.song.scenes))

    def test_reserved_range_checks_target_collision_and_upper_boundary(self):
        self.reserve(length=1)
        with self.assertRaisesRegex(RuntimeError,'exceeds'): self.bridge._audio_import(self.action)
        self.assertEqual(1,len(self.song.tracks[0].arrangement_clips))

    def test_foldable_group_track_does_not_break_arrangement_readback_or_import(self):
        class GroupTrack:
            is_foldable = True
            has_midi_input = False
            name = '15-Group'
            devices = []
            mixer_device = NS(volume=NS(value=.6), panning=NS(value=0.0), sends=[NS(value=.1)])
            def __init__(self):
                self.clip_slots = [Slot()]
            @property
            def arrangement_clips(self):
                raise RuntimeError('Main, Group and Return Tracks have no arrangement clips')
        group = GroupTrack()
        self.song.tracks.append(group)
        comp_state = self.bridge._composition_state()
        prod_state = self.bridge._production_state()
        self.assertTrue(comp_state['arrangement_readable'])
        self.assertTrue(prod_state['arrangement_readable'])
        self.assertEqual([], comp_state['arrangement_errors'])
        self.assertEqual([], prod_state['arrangement_errors'])
        self.action['source_revision'] = prod_state['revision']
        self.bridge._audio_import(self.action)
        self.assertEqual('Applied', self.result()['status'])

