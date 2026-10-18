import json
import tempfile
import threading
import time
import unittest
import uuid
import wave
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
from http.server import ThreadingHTTPServer
from vibelton import samples


class SampleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.library = root / 'loops'
        self.library.mkdir()
        self.wav = self.library / 'Break_170.wav'
        with wave.open(str(self.wav), 'wb') as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(8000)
            stream.writeframes(b'\0\0' * 8000)
        for name,value in [('SAMPLE_ROOT',self.library),('ROOT',root/'jobs'),('REGIONS',root/'regions')]:
            p = patch.object(samples,name,value); p.start(); self.addCleanup(p.stop)
        self.extra = root/'Shadow library'; self.extra.mkdir()
        p = patch.object(samples,'EXTRA_SAMPLE_ROOTS',(self.extra,)); p.start(); self.addCleanup(p.stop)
        p = patch.object(samples.queue,'QUEUE_DIR',root/'queue'); p.start(); self.addCleanup(p.stop)
        self.state = {'connected':True,'updated_at':time.time(),'capabilities':['audio_import_v1'],
                      'session_id':'session','set_path':'/sets/Working.als','arrangement_readable':True,
                      'arrangement_end':16,'scene_count':1,
                      'production':{'arrangement_readable':True,'revision':'before',
                                    'tracks':[{'id':'audio','name':'Break','type':'audio','audio_import_supported':True}]}}
        p = patch.object(samples.queue,'current_state',side_effect=lambda:self.state); p.start(); self.addCleanup(p.stop)
        self.commands = []
        def enqueue(actions,source):
            self.commands.extend(actions); return {'id':'command'}
        p = patch.object(samples.queue,'enqueue',side_effect=enqueue); p.start(); self.addCleanup(p.stop)
        self.payload = {'session_id':'session','source_revision':'before','expected_set_path':'/sets/Working.als',
                        'working_copy_confirmed':True,'path':str(self.wav),'track_id':'audio',
                        'scene_index':1,'name':'Prototype break','settings':{'warping':True},'arrangement_beat':24,'source_bpm':170}

    def test_catalogue_filters_paginates_and_never_follows_outside_symlinks(self):
        outside = self.library.parent/'outside.wav'; outside.write_bytes(b'not audio')
        (self.library/'escape.wav').symlink_to(outside)
        result = samples.catalogue('break',0,1)
        self.assertEqual(1,result['total']); self.assertEqual(str(self.wav.resolve()),result['files'][0]['path'])
        self.assertEqual(1,samples.catalogue()['total'])
        with self.assertRaises(ValueError): samples.source_path(outside)

    def test_metadata_has_evidence_and_labels_filename_bpm_as_hint(self):
        result = samples.metadata(str(self.wav))
        self.assertEqual(1,result['channels']); self.assertAlmostEqual(1,result['duration_seconds'])
        self.assertEqual([170],result['filename_bpm_hints']); self.assertFalse(result['bpm_measured'])
        self.assertEqual(64,len(result['sha256'])); self.assertFalse(result['audio_auditioned'])

    def test_extra_library_catalogue_and_byte_identical_guarded_staging(self):
        external = self.extra/'Modern_170.wav'; external.write_bytes(self.wav.read_bytes())
        result = samples.catalogue('Shadow library')
        self.assertEqual([str(external.resolve())], [item['path'] for item in result['files']])
        job = samples.apply({**self.payload,'path':str(external)})
        staged = Path(job['action']['path'])
        self.assertTrue(staged.resolve().is_relative_to(self.library.resolve()))
        self.assertEqual(external.read_bytes(),staged.read_bytes())
        self.assertEqual(str(external.resolve()),job['source']['path'])
        self.assertEqual(2,samples.catalogue()['total'])
        self.assertEqual(str(staged),samples.bridge_source(job['source']))
        staged.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Staged sample'):
            samples.bridge_source(job['source'])

    def test_extra_library_escape_and_bad_import_do_not_stage(self):
        outside=self.extra.parent/'escape.wav';outside.write_bytes(self.wav.read_bytes())
        (self.extra/'escape.wav').symlink_to(outside)
        self.assertEqual(0,samples.catalogue('Shadow library')['total'])
        with self.assertRaises(ValueError):samples.source_path(outside)
        external=self.extra/'Modern.wav';external.write_bytes(self.wav.read_bytes())
        with self.assertRaises(ValueError):samples.apply({**self.payload,'path':str(external),'session_id':'stale'})
        self.assertFalse((self.library/'.vibelton-imports').exists())

    def test_guarded_job_enqueues_once_and_tracks_interruption(self):
        job = samples.apply(self.payload)
        self.assertEqual(1,len(self.commands)); self.assertEqual('Queued',samples.job_status(job['id'])['status'])
        with self.assertRaisesRegex(ValueError,'pending'): samples.apply(self.payload)
        self.state['session_id'] = 'new'
        self.assertEqual('Interrupted',samples.job_status(job['id'])['status'])

    def test_bad_session_revision_copy_range_and_target_never_enqueue(self):
        for key,value in [('session_id','stale'),('source_revision','stale'),('expected_set_path','/sets/Original.als'),
                          ('working_copy_confirmed',False),('scene_index',0),('arrangement_beat',8),('track_id','unknown')]:
            with self.subTest(key=key):
                with self.assertRaises(ValueError): samples.apply({**self.payload,key:value})
        self.assertEqual([],self.commands)

    def test_unreadable_arrangement_and_unsupported_bridge_never_enqueue(self):
        self.state['arrangement_readable'] = False
        with self.assertRaisesRegex(ValueError,'readback'): samples.apply(self.payload)
        self.state['arrangement_readable'] = True; self.state['capabilities'] = []
        with self.assertRaisesRegex(ValueError,'bridge'): samples.apply(self.payload)
        self.assertEqual([],self.commands)

    def test_invalid_settings_rejected(self):
        for settings in [{'gain':float('nan')},{'pitch_coarse':2.5},{'gain':True},{'warp_mode':2.5},
                         {'start_marker':4,'end_marker':2},{'warping':False,'looping':True},{'unknown':1}]:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError): samples.validate_settings(settings)

    def test_unwarped_arrangement_rejected_before_queue(self):
        with self.assertRaisesRegex(ValueError,'Session-only'):
            samples.apply({**self.payload,'settings':{'warping':False}})
        self.assertEqual([],self.commands)

    def test_marker_past_source_is_rejected_before_queue(self):
        with self.assertRaisesRegex(ValueError,'source duration'):
            samples.apply({**self.payload,'settings':{'warping':True,'end_marker':999}})
        self.assertEqual([],self.commands)

    def test_reserved_range_allows_layers_after_arrangement_end_advances(self):
        region=samples.reserve_region({**self.payload,'start_beat':24,'length_beats':64})
        self.assertEqual([],self.commands)
        self.state['arrangement_end']=88
        job=samples.apply({**self.payload,'region_id':region['id']})
        self.assertEqual(region,job['action']['region'])

    def test_region_rejects_original_range_and_stale_session(self):
        with self.assertRaisesRegex(ValueError,'original Arrangement'):
            samples.reserve_region({**self.payload,'start_beat':0,'length_beats':64})
        region=samples.reserve_region({**self.payload,'start_beat':24,'length_beats':64})
        self.state['session_id']='changed'
        with self.assertRaises(ValueError):
            samples.apply({**self.payload,'session_id':'changed','region_id':region['id']})
        self.assertEqual([],self.commands)

    def test_partial_execution_is_reported_without_replay(self):
        job = samples.apply(self.payload)
        path = samples.queue.QUEUE_DIR/'sample-executions'/(job['id']+'.json')
        path.parent.mkdir(parents=True); path.write_text(json.dumps({'status':'Partial failure','readback_verified':False}))
        self.assertEqual('Partial failure',samples.job_status(job['id'])['status'])
        self.assertEqual(1,len(self.commands))

    def test_http_catalogue_metadata_and_audio_ranges(self):
        from vibelton.server import Handler
        class QuietHandler(Handler):
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        def close():
            server.shutdown(); server.server_close(); thread.join()
        self.addCleanup(close)
        base='http://127.0.0.1:%s/api/samples' % server.server_port
        with urlopen(base+'?query=break') as response:
            self.assertEqual(1,json.load(response)['total'])
        query=urlencode({'path':str(self.wav)})
        with urlopen(base+'/metadata?'+query) as response:
            self.assertEqual([170],json.load(response)['filename_bpm_hints'])
        with urlopen(Request(base+'/audio?'+query,headers={'Range':'bytes=0-3'})) as response:
            self.assertEqual(206,response.status); self.assertEqual(b'RIFF',response.read())
            self.assertEqual('bytes 0-3/%d' % self.wav.stat().st_size,response.headers['Content-Range'])
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(base+'/audio?'+query,headers={'Range':'bytes=999999-'}))
        self.assertEqual(416,error.exception.code)
        error.exception.close()
        with self.assertRaises(HTTPError) as error:
            urlopen(base+'/audio?'+urlencode({'path':str(self.library.parent/'outside.wav')}))
        self.assertEqual(400,error.exception.code)
        error.exception.close()

    def test_import_shuffled_slot_auto_tunes_and_auto_selects_empty_audio_track(self):
        import math, struct
        pitched_wav = self.library / 'Bass_120.wav'
        sr = 8000
        # 223 Hz is slightly sharp of A3 (220 Hz); transpose to G (196 Hz -> -2 st)
        samples_pcm = [int(16000 * math.sin(2 * math.pi * 223.0 * i / sr)) for i in range(sr)]
        with wave.open(str(pitched_wav), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(sr)
            stream.writeframes(struct.pack('<' + 'h' * len(samples_pcm), *samples_pcm))

        self.state['production']['tracks'] = [
            {'id': 'busy-audio', 'name': '1-Busy Audio', 'type': 'audio', 'audio_import_supported': True, 'session_clips': [{'scene_index': 0, 'name': 'Existing'}]},
            {'id': 'empty-audio', 'name': '5-Audio', 'type': 'audio', 'audio_import_supported': True, 'session_clips': [], 'arrangement_clips': []},
        ]
        job = samples.import_shuffled_slot({
            'relative_path': 'Bass_120.wav',
            'track_id': 'auto',
            'target_key': 'G',
            'auto_tune': True,
            'working_copy_confirmed': True,
        })
        self.assertEqual(job['status'], 'Queued')
        action = job['action']
        self.assertEqual(action['track_id'], 'empty-audio')
        self.assertEqual(action['target_name'], '5-Audio')
        self.assertEqual(len(action['sha256']), 64)
        self.assertAlmostEqual(action['duration_seconds'], 1.0, places=2)
        self.assertEqual(action['source_bpm'], 120.0)
        self.assertTrue(action['settings']['warping'])
        self.assertTrue(action['settings']['looping'])
        self.assertEqual(action['settings']['pitch_coarse'], -2)
        self.assertNotEqual(action['settings']['pitch_fine'], 0.0)
        self.assertAlmostEqual(action['settings']['gain'], 0.85)

        # Verify calculate_smart_tuning directly
        smart = samples.calculate_smart_tuning('A', 'G', cents_offset=18.0)
        self.assertEqual(-2, smart['pitch_coarse'])
        self.assertEqual(-18, smart['pitch_fine'])

        # Verify target_track_id validation rejects group or unsupported tracks BEFORE calling metadata()
        self.state['production']['tracks'].append({
            'id': 'group-audio', 'name': 'Drums Group', 'type': 'audio',
            'is_group': True, 'audio_import_supported': True,
        })
        self.state['production']['tracks'].append({
            'id': 'frozen-audio', 'name': 'Frozen Audio', 'type': 'audio',
            'is_group': False, 'audio_import_supported': False,
        })
        with patch.object(samples, 'metadata', side_effect=AssertionError('metadata() should not be called before track validation')):
            with self.assertRaisesRegex(ValueError, 'non-group audio track'):
                samples.import_shuffled_slot({
                    'relative_path': 'Bass_120.wav',
                    'target_track_id': 'group-audio',
                    'working_copy_confirmed': True,
                })
            with self.assertRaisesRegex(ValueError, 'non-group audio track'):
                samples.import_shuffled_slot({
                    'relative_path': 'Bass_120.wav',
                    'target_track_id': 'frozen-audio',
                    'working_copy_confirmed': True,
                })

        # Verify audio_to_midi and slice_transients validate target MIDI track and working_copy_confirmed before queuing composition_apply
        self.state['capabilities'] = ['audio_import_v1', 'composition_v1', 'production_v1']
        self.state['production']['tracks'].append({
            'id': 'midi-bass', 'name': '2-MIDI Bass', 'type': 'midi', 'is_group': False,
        })
        self.state['production']['tracks'].append({
            'id': 'midi-group', 'name': 'Synth Group', 'type': 'midi', 'is_group': True,
        })
        with self.assertRaisesRegex(ValueError, 'working copy'):
            samples.audio_to_midi({
                'path': str(pitched_wav),
                'target_track_id': 'midi-bass',
                'working_copy_confirmed': False,
            })
        with self.assertRaisesRegex(ValueError, 'MIDI track'):
            samples.audio_to_midi({
                'path': str(pitched_wav),
                'target_track_id': 'empty-audio',
                'working_copy_confirmed': True,
            })
        with self.assertRaisesRegex(ValueError, 'non-group MIDI track'):
            samples.audio_to_midi({
                'path': str(pitched_wav),
                'target_track_id': 'midi-group',
                'working_copy_confirmed': True,
            })
        queued_midi = samples.audio_to_midi({
            'path': str(pitched_wav),
            'target_track_id': 'midi-bass',
            'working_copy_confirmed': True,
        })
        self.assertTrue(queued_midi.get('queued'))
        self.assertEqual('midi-bass', queued_midi['target_track_id'])
        self.assertEqual('command', queued_midi['command_id'])
        self.assertEqual('composition_apply', self.commands[-1]['type'])

        with self.assertRaisesRegex(ValueError, 'working copy'):
            samples.slice_transients({
                'path': str(pitched_wav),
                'target_track_id': 'midi-bass',
                'working_copy_confirmed': False,
            })
        queued_slices = samples.slice_transients({
            'path': str(pitched_wav),
            'target_track_id': 'midi-bass',
            'working_copy_confirmed': True,
        })
        self.assertTrue(queued_slices.get('queued'))
        self.assertEqual('midi-bass', queued_slices['target_track_id'])
        self.assertEqual('command', queued_slices['command_id'])
        self.assertEqual('composition_apply', self.commands[-1]['type'])

    def test_http_samples_imports_job_status_alias(self):
        from vibelton.server import Handler
        class QuietHandler(Handler):
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join()))
        job = samples.apply(self.payload)
        base = f'http://127.0.0.1:{server.server_port}/api/samples'
        with urlopen(f'{base}/imports/{job["id"]}') as resp:
            data = json.load(resp)
            self.assertEqual(job['id'], data['id'])
            self.assertEqual('Queued', data['status'])
        with urlopen(f'{base}/status/{job["id"]}') as resp:
            data2 = json.load(resp)
            self.assertEqual(job['id'], data2['id'])

    def test_midi_placement_preflight_gap_overlap_and_job_status(self):
        import math, struct
        pitched_wav = self.library / 'Lead_120.wav'
        sr = 8000
        samples_pcm = [int(16000 * math.sin(2 * math.pi * 220.0 * i / sr)) for i in range(sr)]
        with wave.open(str(pitched_wav), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(sr)
            stream.writeframes(struct.pack('<' + 'h' * len(samples_pcm), *samples_pcm))

        self.state['capabilities'] = ['audio_import_v1', 'composition_v1', 'production_v1']
        self.state['arrangement_end'] = 16.0
        self.state['production']['tracks'] = [
            {
                'id': 'midi-lead', 'name': 'Lead MIDI', 'type': 'midi', 'is_group': False,
                'arrangement_clips': [{'name': 'Intro Clip', 'start_beat': 8.0, 'end_beat': 16.0, 'length': 8.0}],
            }
        ]

        # 1. Default start_beat adds +4 beat safety gap past arrangement_end (16.0 -> 20.0)
        queued = samples.audio_to_midi({
            'path': str(pitched_wav),
            'target_track_id': 'midi-lead',
            'working_copy_confirmed': True,
        })
        self.assertEqual(20.0, queued['start_beat'])
        job_id = queued['job_id']
        self.assertEqual('Queued', samples.job_status(job_id)['status'])

        # 2. job_status reads execution status from composition-executions/<job_id>.json
        comp_exec = samples.queue.QUEUE_DIR / 'composition-executions' / (job_id + '.json')
        comp_exec.parent.mkdir(parents=True, exist_ok=True)
        comp_exec.write_text(json.dumps({'status': 'Failed', 'error': 'Bridge rejected clip'}))
        status_after = samples.job_status(job_id)
        self.assertEqual('Failed', status_after['status'])
        self.assertEqual('Bridge rejected clip', status_after['error'])

        # 3. Rejects explicit start_beat that overlaps existing Arrangement clip [8.0, 16.0)
        with self.assertRaisesRegex(ValueError, 'Arrangement range is occupied'):
            samples.audio_to_midi({
                'path': str(pitched_wav),
                'target_track_id': 'midi-lead',
                'start_beat': 12.0,
                'working_copy_confirmed': True,
            })

        # 4. Rejects placement when Arrangement readback is unreadable
        self.state['arrangement_readable'] = False
        self.state['production']['arrangement_readable'] = False
        with self.assertRaisesRegex(ValueError, 'Resolve Arrangement readback errors'):
            samples.audio_to_midi({
                'path': str(pitched_wav),
                'target_track_id': 'midi-lead',
                'working_copy_confirmed': True,
            })

    def test_import_shuffled_slot_fx_oneshot_and_settings_override(self):
        self.state['production']['tracks'] = [
            {'id': 'fx-audio', 'name': 'FX Audio', 'type': 'audio', 'audio_import_supported': True, 'session_clips': [], 'arrangement_clips': []},
        ]
        # FX slot defaults looping to False
        fx_job = samples.import_shuffled_slot({
            'relative_path': 'Break_170.wav',
            'track_id': 'fx-audio',
            'slot_id': 'fx',
            'working_copy_confirmed': True,
        })
        self.assertFalse(fx_job['action']['settings']['looping'])
        exec_path = samples.queue.QUEUE_DIR / 'sample-executions' / (fx_job['id'] + '.json')
        exec_path.parent.mkdir(parents=True, exist_ok=True)
        exec_path.write_text(json.dumps({'status': 'Applied', 'readback_verified': True}))

        # Caller can explicitly override looping and settings on any slot
        self.state['scene_count'] = 2
        custom_job = samples.import_shuffled_slot({
            'relative_path': 'Break_170.wav',
            'track_id': 'fx-audio',
            'slot_id': 'drums',
            'looping': False,
            'settings': {'gain': 0.5},
            'working_copy_confirmed': True,
        })
        self.assertFalse(custom_job['action']['settings']['looping'])
        self.assertAlmostEqual(0.5, custom_job['action']['settings']['gain'])
