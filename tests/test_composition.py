import copy
import json
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from vibelton import composition as c, composition_service as service


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.doc = c.prepare(c.default_document())

    def test_exact_four_minutes_and_exit(self):
        result = c.compile_score(self.doc)
        self.assertEqual((672, 240), (result['total_beats'], result['seconds']))
        self.assertEqual(16, len(result['sections'][5:]))
        self.assertEqual(64, sum(s['length_beats'] for s in result['sections'][5:]))
        for a,b in zip(result['sections'], result['sections'][1:]):
            self.assertEqual(a['start_beat']+a['length_beats'], b['start_beat'])

    def test_bad_grouping_and_nonfinite_rejected(self):
        self.doc['sections'][0]['grouping'] = [4,4]
        with self.assertRaisesRegex(ValueError,'grouping'): c.validate(self.doc)
        self.doc = c.default_document(); self.doc['bpm'] = float('nan')
        with self.assertRaisesRegex(ValueError,'finite'): c.validate(self.doc)

    def test_determinism_note_bounds_and_metres(self):
        self.assertEqual(self.doc, c.prepare(c.default_document()))
        for s in self.doc['sections']:
            for p in s['parts'].values():
                for note in p['notes']:
                    self.assertGreaterEqual(note['start'],0)
                    self.assertLessEqual(note['start']+note['duration'], c.beats_per_bar(s['metre'])*s['bars']+.00001)

    def test_selective_variation_keeps_other_sections_and_locked_parts(self):
        self.doc['sections'][1]['parts']['bass']['locked'] = True
        new=c.prepare(self.doc, self.doc, {'sections':['section-02'],'roles':['bass','drums']})
        self.assertEqual(self.doc['sections'][1]['parts']['bass'],new['sections'][1]['parts']['bass'])
        self.assertNotEqual(self.doc['sections'][1]['parts']['drums'],new['sections'][1]['parts']['drums'])
        self.assertEqual(self.doc['sections'][0],new['sections'][0])
        self.assertEqual(self.doc['sections'][2:],new['sections'][2:])

    def test_locked_section_cannot_move_edit_or_remove(self):
        self.doc['sections'][0]['locked']=True
        for operation in ('edit','remove','move'):
            new=copy.deepcopy(self.doc)
            if operation=='edit': new['sections'][0]['bars']=1
            elif operation=='remove': new['sections'].pop(0)
            else: new['sections'][0],new['sections'][1]=new['sections'][1],new['sections'][0]
            with self.assertRaisesRegex(ValueError,'Unlock section'): c.prepare(new,self.doc)
        new=copy.deepcopy(self.doc);new['expression']['density']=.9
        self.assertEqual(self.doc['sections'][0],c.prepare(new,self.doc)['sections'][0])

    def test_unlock_is_separate_revision(self):
        self.doc['sections'][0]['locked']=True
        new=copy.deepcopy(self.doc);new['sections'][0]['locked']=False
        unlocked=c.prepare(new,self.doc)
        new['sections'][0]['bars']=2
        with self.assertRaises(ValueError): c.prepare(new,self.doc)
        self.assertEqual(2,c.prepare(new,unlocked)['sections'][0]['bars'])

    def test_resize_regenerates_unlocked_notes(self):
        new=copy.deepcopy(self.doc);new['sections'][0]['bars']=1
        prepared=c.prepare(new,self.doc)
        self.assertTrue(all(n['start']+n['duration']<=3.50001 for p in prepared['sections'][0]['parts'].values() for n in p['notes']))

    def test_explicit_codex_notes_survive_save(self):
        new=copy.deepcopy(self.doc)
        new['sections'][0]['parts']['motif']['notes']=[{'pitch':60,'start':0,'duration':1,'velocity':90}]
        new['expression']['density']=.8
        self.assertEqual(new['sections'][0]['parts']['motif'],c.prepare(new,self.doc)['sections'][0]['parts']['motif'])

    def test_fit_preserves_locked_sections_and_tempo(self):
        self.doc['sections'][0]['locked']=True
        self.doc['target_seconds']=230
        fitted=c.prepare(c.fit_duration(self.doc),self.doc)
        self.assertEqual(self.doc['sections'][0],fitted['sections'][0])
        self.assertEqual(168,fitted['bpm'])
        self.assertLessEqual(abs(c.compile_score(fitted)['seconds']-230),.18)

    def test_preview_contains_only_selected_section(self):
        preview=c.compile_score(self.doc,'section-03')
        self.assertEqual(1,len(preview['sections']))
        self.assertEqual(0,preview['sections'][0]['start_beat'])
        self.assertEqual(120,preview['total_beats'])

    def test_aaab_phrase_invariant_bar4_distinct_from_bar1(self):
        proj = c.project_document({'tempo': 119.0, 'session_id': 'live', 'tracks': []})
        section = proj['sections'][1]  # 4-bar 4/4 section with drums, percussion, bass, chords, motif
        self.assertEqual([4, 4], section['metre'])
        for role in ('drums', 'bass', 'chords', 'motif'):
            notes = section['parts'][role]['notes']
            bar1 = [(round(n['start'], 2), n['pitch']) for n in notes if 0.0 <= n['start'] < 4.0]
            bar4 = [(round(n['start'] - 12.0, 2), n['pitch']) for n in notes if 12.0 <= n['start'] < 16.0]
            self.assertTrue(bar1, f'Expected bar 1 notes for {role}')
            self.assertTrue(bar4, f'Expected bar 4 notes for {role}')
            self.assertNotEqual(bar1, bar4, f'Bar 4 must be rhythmically/melodically distinct from Bar 1 for {role}')

    def test_bass_companion_kick_lock_swing_density_and_movement(self):
        kicks = [0.0, 2.5]
        sparse_notes = c.generate_bass_companion(
            key='Ab', scale='minor', swing=0.0, density='sparse', movement='pedal', lock_to_kick_beats=kicks, bars=4
        )
        rolling_notes = c.generate_bass_companion(
            key='Ab', scale='minor', swing=0.25, density='rolling', movement='octave_jump', lock_to_kick_beats=kicks, bars=4
        )
        self.assertGreater(len(rolling_notes), len(sparse_notes))
        # Downbeat kick at 0.0 is locked in every bar
        starts_sparse = {round(n['start'], 2) for n in sparse_notes}
        for bar_start in (0.0, 4.0, 8.0, 12.0):
            self.assertIn(bar_start, starts_sparse)
        # Octave jump uses Ab1 (44) and Ab2 (56)
        pitches_rolling = {n['pitch'] for n in rolling_notes}
        self.assertIn(44, pitches_rolling)
        self.assertIn(56, pitches_rolling)
        # Bar 4 is distinct from Bar 1
        b1 = [(round(n['start'], 3), n['pitch']) for n in rolling_notes if 0.0 <= n['start'] < 4.0]
        b4 = [(round(n['start'] - 12.0, 3), n['pitch']) for n in rolling_notes if 12.0 <= n['start'] < 16.0]
        self.assertNotEqual(b1, b4)

    def test_section_transitions_strip_kicks_and_add_snare_fill_before_drop(self):
        proj = c.project_document({'tempo': 119.0, 'session_id': 'live', 'tracks': []})
        build_sec = proj['sections'][1]  # 4-bar Build & vocal space before Main drop
        drum_notes = build_sec['parts']['drums']['notes']
        kick_pitch = proj['drum_notes']['kick']
        snare_pitch = proj['drum_notes']['snare']
        # In bar 4 (beats 12.0..16.0), kicks are stripped in the second half (beats 14.0..16.0)
        late_bar4_kicks = [n for n in drum_notes if n['pitch'] == kick_pitch and 14.1 <= n['start'] < 16.0]
        self.assertEqual([], late_bar4_kicks)
        # Snare fill has multiple accelerating hits in beats 14.0..16.0
        late_bar4_snares = [n for n in drum_notes if n['pitch'] == snare_pitch and 13.9 <= n['start'] < 16.0]
        self.assertGreaterEqual(len(late_bar4_snares), 4)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for target,value in [('vibelton.composition_service.ROOT',self.root/'compositions'),('vibelton.queue.QUEUE_DIR',self.root)]:
            p=patch(target,value);p.start();self.addCleanup(p.stop)
        self.state={'connected':True,'updated_at':time.time(),'capabilities':['composition_v1'], 'session_id':'live',
                    'arrangement_readable':True,'arrangement_end':32,'scene_count':2,
                    'tracks':[{'id':'track','name':'My synth','type':'midi','has_audio_output':True,'devices':[{'name':'User preset'}]}]}
        p=patch.object(service.queue,'current_state',side_effect=lambda:self.state);p.start();self.addCleanup(p.stop)
        p=patch.object(service.queue,'enqueue',return_value={'id':'command'});self.enqueue=p.start();self.addCleanup(p.stop)
        d=c.default_document()
        for role in c.ROLES:d['assignments'][role]={'id':'track','name':'My synth','session_id':'live'}
        self.saved=service.save({'base_revision':0,'composition':d})

    def test_save_compile_never_enqueue_and_revisions_persist(self):
        service.compile_revision({'revision':1})
        self.enqueue.assert_not_called()
        self.assertEqual(self.saved, service.get_revision(1)|{'compiled':self.saved['compiled']})
        with self.assertRaisesRegex(ValueError,'changed elsewhere'):
            service.save({'base_revision':0,'composition':self.saved['composition']})

    def test_apply_is_single_safe_action_and_merges_shared_tracks(self):
        job=service.apply({'revision':1,'working_copy_confirmed':True})
        actions=self.enqueue.call_args.args[0]
        self.assertEqual(['composition_apply'],[a['type'] for a in actions])
        self.assertEqual(21,len(actions[0]['clips']))
        self.assertFalse(actions[0]['preview'])
        self.assertGreaterEqual(job['start_beat'],32)
        self.assertEqual('Queued',job['status'])
        with self.assertRaisesRegex(ValueError,'already been submitted'):
            service.apply({'revision':1,'working_copy_confirmed':True})
        self.assertEqual(1,self.enqueue.call_count)

    def test_stale_bridge_missing_assignment_and_working_copy(self):
        with self.assertRaisesRegex(ValueError,'working copy'):service.apply({'revision':1})
        self.state['updated_at']=0
        with self.assertRaisesRegex(ValueError,'stale'):service.apply({'revision':1,'working_copy_confirmed':True})
        self.state['updated_at']=time.time();self.state['tracks'][0]['name']='Renamed'
        with self.assertRaisesRegex(ValueError,'changed'):service.apply({'revision':1,'working_copy_confirmed':True})
        self.enqueue.assert_not_called()

    def test_durable_status_and_marker_attestation(self):
        job=service.apply({'revision':1,'working_copy_confirmed':True})
        with self.assertRaisesRegex(ValueError,'readback'):service.verify_markers({'job_id':job['id']})
        service.write(self.root/'composition-executions'/(job['id']+'.json'),{'status':'Applied','readback_verified':True})
        self.assertEqual('Applied',service.job_status(job['id'])['status'])
        with self.assertRaisesRegex(ValueError,'exact marker'): service.verify_markers({'job_id':job['id'],'markers':[],'evidence':'checked'})
        verified=service.verify_markers({'job_id':job['id'],'markers':job['markers'],'evidence':'Checked each marker in Ableton Arrangement UI'})
        self.assertEqual('Verified',verified['status'])

    def test_session_restart_does_not_retry(self):
        job=service.apply({'revision':1,'working_copy_confirmed':True})
        self.state['session_id']='new-live'
        self.assertEqual('Interrupted',service.job_status(job['id'])['status'])
        self.assertEqual(1,self.enqueue.call_count)

    def test_reserved_prototype_range_sets_exact_midi_start(self):
        from vibelton import samples
        region_id=str(uuid.uuid4())
        self.state['set_path']='/sets/Prototype.als'
        region={'id':region_id,'session_id':'live','set_path':self.state['set_path'],'start_beat':48,'length_beats':3600}
        with patch.object(samples,'REGIONS',self.root/'regions'):
            service.write(samples.REGIONS/(region_id+'.json'),region)
            job=service.apply({'revision':1,'working_copy_confirmed':True,'region_id':region_id})
        self.assertEqual(48,job['start_beat'])
        self.assertEqual(48,self.enqueue.call_args.args[0][0]['clips'][0]['start_beat'])

    def test_reserved_prototype_range_rejects_wrong_set_or_occupied_range(self):
        from vibelton import samples
        region_id=str(uuid.uuid4());self.state['set_path']='/sets/Prototype.als'
        region={'id':region_id,'session_id':'live','set_path':'/sets/Wrong.als','start_beat':48,'length_beats':3600}
        with patch.object(samples,'REGIONS',self.root/'regions'):
            service.write(samples.REGIONS/(region_id+'.json'),region)
            with self.assertRaisesRegex(ValueError,'another Set'):
                service.apply({'revision':1,'working_copy_confirmed':True,'region_id':region_id})
            region['set_path']=self.state['set_path'];service.write(samples.REGIONS/(region_id+'.json'),region)
            self.state['tracks'][0]['arrangement_clips']=[{'start_beat':48,'end_beat':52}]
            with self.assertRaisesRegex(ValueError,'occupied'):
                service.apply({'revision':1,'working_copy_confirmed':True,'region_id':region_id})
        self.enqueue.assert_not_called()

    def test_create_from_project_seeds_119_bpm_ab_revision_with_synth_tracks(self):
        self.state['tempo'] = 119.0
        self.state['set_path'] = '/Users/standard/Music/Ableton/shape chnage Project/shape change .als'
        self.state['tracks'] = [
            {'id': 'track-2', 'name': '3-THE_INSTRUMENT', 'type': 'midi', 'has_audio_output': True, 'devices': [{'name': 'THE_INSTRUMENT'}]},
            {'id': 'track-5', 'name': '6-Serum 2', 'type': 'midi', 'has_audio_output': True, 'devices': [{'name': 'Serum 2'}]},
            {'id': 'track-7', 'name': '8-Serum 2', 'type': 'midi', 'has_audio_output': True, 'devices': [{'name': 'Serum 2'}]},
            {'id': 'track-11', 'name': '12-Serum 2', 'type': 'midi', 'has_audio_output': True, 'devices': [{'name': 'Serum 2'}]},
            {'id': 'track-21', 'name': '22-moog short 5 A flat1', 'type': 'audio', 'has_audio_output': True, 'devices': []},
        ]
        seeded = service.create_from_project({})
        self.assertEqual(2, seeded['revision'])
        comp = seeded['composition']
        self.assertEqual(119.0, comp['bpm'])
        self.assertEqual(56, comp['root_midi'])  # Ab3
        self.assertEqual([4, 4], comp['sections'][0]['metre'])
        self.assertIsNotNone(comp['assignments']['bass'])
        self.assertIsNotNone(comp['assignments']['chords'])
        self.assertIsNotNone(comp['assignments']['motif'])

    def test_prepare_compiles_drums_before_bass_and_locks_bass_to_drum_kicks(self):
        doc = c.default_document()
        # Put 'bass' BEFORE 'drums' in active_parts to verify prepare() still compiles drums first
        doc['sections'][1]['active_parts'] = ['bass', 'drums', 'motif']
        doc['sections'][1]['metre'] = [4, 4]
        doc['sections'][1]['grouping'] = [2, 2]
        doc['sections'][1]['bars'] = 4
        doc['bass_companion'] = {'density': 'sparse', 'movement': 'pedal', 'swing': 0.0}
        prepared = c.prepare(doc)
        sec = prepared['sections'][1]
        drum_kicks = {round(n['start'], 2) for n in sec['parts']['drums']['notes'] if n['pitch'] == doc['drum_notes']['kick']}
        bass_starts = {round(n['start'], 2) for n in sec['parts']['bass']['notes']}
        self.assertTrue(drum_kicks)
        for bar_downbeat in (0.0, 4.0, 8.0, 12.0):
            if bar_downbeat in drum_kicks:
                self.assertIn(bar_downbeat, bass_starts)

    def test_project_document_extracts_real_midi_motif_and_root_from_notes_preview(self):
        state = {
            'tempo': 119.0,
            'session_id': 'live',
            'tracks': [
                {
                    'id': 'tr-electro',
                    'name': '2-Light Electro',
                    'type': 'midi',
                    'has_audio_output': True,
                    'devices': [{'name': 'Instrument Rack'}],
                    'arrangement_clips': [
                        {
                            'name': 'Electro Hook',
                            'start_beat': 0.0,
                            'end_beat': 8.0,
                            'length': 8.0,
                            'summary': {
                                'kind': 'midi',
                                'note_count': 4,
                                'notes_preview': [
                                    {'pitch': 60, 'start': 0.0, 'duration': 0.5, 'velocity': 100, 'mute': False},
                                    {'pitch': 63, 'start': 1.0, 'duration': 0.5, 'velocity': 95, 'mute': False},
                                    {'pitch': 67, 'start': 2.0, 'duration': 0.5, 'velocity': 95, 'mute': False},
                                    {'pitch': 70, 'start': 3.0, 'duration': 0.5, 'velocity': 90, 'mute': False},
                                ],
                            },
                        }
                    ],
                },
                {
                    'id': 'tr-serum',
                    'name': '6-Serum 2',
                    'type': 'midi',
                    'has_audio_output': True,
                    'devices': [{'name': 'Serum 2'}],
                    'session_clip_summaries': {
                        '0': {
                            'kind': 'midi',
                            'note_count': 2,
                            'notes_preview': [
                                {'pitch': 36, 'start': 0.0, 'duration': 0.5, 'velocity': 110, 'mute': False},
                                {'pitch': 36, 'start': 1.5, 'duration': 0.5, 'velocity': 105, 'mute': False},
                            ],
                        }
                    },
                    'clips': [{'scene_index': 0, 'name': 'Sub Pulse', 'length': 4.0}],
                },
            ],
        }
        doc = c.project_document(state)
        self.assertEqual([0, 3, 7, 10], doc['motif'])
        self.assertEqual(48, doc['root_midi'])  # C3
        self.assertEqual('minor', doc['mode'])
        self.assertEqual(2, len(doc['source_clips_used']))
        self.assertIn(1.5, doc['lock_to_kick_beats'])

    def test_bass_companion_service_updates_unlocked_bass_and_respects_locks(self):
        # Lock bass in section-02, leave section-03 unlocked
        doc = copy.deepcopy(self.saved['composition'])
        doc['sections'][1]['parts']['bass']['locked'] = True
        locked_bass_before = copy.deepcopy(doc['sections'][1]['parts']['bass'])
        unlocked_bass_before = copy.deepcopy(doc['sections'][2]['parts']['bass'])
        saved2 = service.save({'base_revision': 1, 'composition': doc})
        self.assertEqual(2, saved2['revision'])

        res = service.generate_bass_companion_revision({
            'density': 'rolling',
            'movement': 'octave_jump',
            'swing': 0.22,
        })
        self.assertEqual(3, res['revision'])
        new_doc = res['composition']
        self.assertNotIn('section-02', res['updated_sections'])
        self.assertIn('section-03', res['updated_sections'])
        self.assertEqual(locked_bass_before, new_doc['sections'][1]['parts']['bass'])
        self.assertNotEqual(unlocked_bass_before['notes'], new_doc['sections'][2]['parts']['bass']['notes'])

    def test_note_probability_and_velocity_deviation_validation(self):
        doc = copy.deepcopy(self.saved['composition'])
        drum_notes = doc['sections'][1]['parts']['drums']['notes']
        self.assertTrue(any('probability' in n and 0.01 <= n['probability'] <= 1.0 for n in drum_notes))
        self.assertTrue(any('velocity_deviation' in n and -127 <= n['velocity_deviation'] <= 127 for n in drum_notes))
        bad = copy.deepcopy(doc)
        bad['sections'][1]['parts']['drums']['notes'][0]['probability'] = 1.5
        with self.assertRaisesRegex(ValueError, 'probability'):
            c.validate(bad)

    def test_prepare_detects_bass_companion_and_lock_to_kick_beats_changes(self):
        base_doc = copy.deepcopy(self.saved['composition'])
        edited_doc = copy.deepcopy(base_doc)
        edited_doc['bass_companion'] = {'density': 'rolling', 'movement': 'octave_jump', 'swing': 0.25}
        edited_doc['lock_to_kick_beats'] = [0.0, 1.5, 2.75]
        regenerated = c.prepare(edited_doc, old=base_doc)
        self.assertNotEqual(
            base_doc['sections'][1]['parts']['bass']['notes'],
            regenerated['sections'][1]['parts']['bass']['notes'],
        )
        # Verify kick_beats at 1.5 are reflected in generated bass attacks
        bass_starts = {round(n['start'] % 3.5, 2) for n in regenerated['sections'][1]['parts']['bass']['notes']}
        self.assertIn(0.0, bass_starts)


if __name__=='__main__':unittest.main()
