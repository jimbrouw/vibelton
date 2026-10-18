from __future__ import annotations

import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from vibelton import production
from vibelton import song_sketch


class ProductionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patcher = patch('vibelton.production.ROOT', self.root / 'production')
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('vibelton.queue.QUEUE_DIR', self.root / 'queue')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.state = {
            'connected': True,
            'updated_at': time.time(),
            'capabilities': ['composition_v1', 'production_v1'],
            'session_id': 'live-session',
            'tempo': 124,
            'metre': [4, 4],
            'arrangement_readable': True,
            'arrangement_end': 64,
            'production': {
                'schema_version': 'vibelton.production-project-state/v1',
                'session_id': 'live-session',
                'revision': 'before',
                'set_path': '/Sets/shape vibelton-working-copy.als',
                'tracks': [{
                    'id': 'bass-id', 'name': 'Bass', 'type': 'midi',
                    'mixer': {'volume': .6, 'pan': 0.0, 'sends': [.1]},
                    'devices': [], 'routing': 'Main', 'arrangement_clips': [],
                }],
            },
        }
        patcher = patch.object(production.queue, 'current_state', side_effect=lambda: self.state)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.enqueued: list[dict] = []

        def enqueue(actions, source):
            self.enqueued.append({'actions': actions, 'source': source})
            return {'id': 'command-%d' % len(self.enqueued)}

        patcher = patch.object(production.queue, 'enqueue', side_effect=enqueue)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_plan(self) -> dict:
        return production.create_plan({
            'intent': 'Create a reversible pan check',
            'snapshot_name': 'Before pan check',
            'actions': [{'type': 'set_track_mixer', 'target_track_id': 'bass-id', 'values': {'pan': .25}}],
        })

    def test_analysis_is_versioned_and_qualified(self) -> None:
        result = production.analyse()
        self.assertEqual(production.PROJECT_ANALYSIS_SCHEMA, result['schema_version'])
        self.assertEqual('before', result['source_revision'])
        self.assertIn('audio_render', result['missing_measurements'])
        self.assertEqual('Bass', result['tracks'][0]['name'])
        comparison = production.comparison_contract()
        self.assertEqual(production.COMPARISON_SCHEMA, comparison['schema_version'])
        self.assertEqual('render_not_supported', comparison['status'])
        self.assertTrue(comparison['same_range_required'])

    def test_plan_is_strict_and_does_not_queue(self) -> None:
        plan = self.make_plan()
        self.assertEqual('Draft', plan['status'])
        self.assertEqual('before', plan['source_revision'])
        self.assertEqual([], self.enqueued)
        with self.assertRaisesRegex(ValueError, 'Unsupported production action'):
            production.create_plan({
                'intent': 'Unsafe', 'snapshot_name': 'Before unsafe',
                'actions': [{'type': 'add_device', 'target_track_id': 'bass-id', 'values': {'pan': 0}}],
            })

    def test_execute_captures_inverse_and_rejects_stale_state(self) -> None:
        plan = self.make_plan()
        with self.assertRaisesRegex(ValueError, 'working copy'):
            production.execute({'plan_id': plan['id'], 'working_copy_confirmed': False})
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        self.assertEqual('Queued', job['status'])
        self.assertEqual('production', self.enqueued[0]['source'])
        bridge_action = self.enqueued[0]['actions'][0]
        self.assertEqual('production_apply', bridge_action['type'])
        snapshot = production._read(self.root / 'production' / 'snapshots' / (job['snapshot_id'] + '.json'))
        self.assertEqual(0.0, snapshot['inverse_actions'][0]['values']['pan'])
        self.assertEqual('Queued', production.get_plan(plan['id'])['status'])
        self.state['production']['revision'] = 'changed'
        newer = self.make_plan()
        self.state['production']['revision'] = 'changed-again'
        with self.assertRaisesRegex(ValueError, 'state changed'):
            production.execute({'plan_id': newer['id'], 'working_copy_confirmed': True})

    def test_applied_fixture_can_queue_exact_rollback(self) -> None:
        plan = self.make_plan()
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        execution_path = self.root / 'queue' / 'production-executions' / (job['id'] + '.json')
        production._write(execution_path, {'status': 'Applied', 'post_revision': 'after'})
        self.state['production']['revision'] = 'after'
        self.state['production']['tracks'][0]['mixer']['pan'] = .25
        self.assertEqual('Applied', production.job_status(job['id'])['status'])
        rollback = production.rollback({'job_id': job['id'], 'working_copy_confirmed': True})
        self.assertEqual(job['id'], rollback['rollback_of'])
        self.assertEqual('set_track_mixer', self.enqueued[1]['actions'][0]['actions'][0]['type'])
        self.assertEqual(0.0, self.enqueued[1]['actions'][0]['actions'][0]['values']['pan'])

    def test_dry_run_rollback_of_a_mixer_job_queues_nothing(self) -> None:
        plan = self.make_plan()
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        production._write(self.root / 'queue' / 'production-executions' / (job['id'] + '.json'),
                          {'status': 'Applied', 'post_revision': 'after'})
        self.state['production']['revision'] = 'after'
        report = production.rollback({'job_id': job['id'], 'working_copy_confirmed': True, 'dry_run': True})
        self.assertTrue(report['dry_run'])
        self.assertEqual(1, len(self.enqueued))  # only the original apply

    def test_cleanup_proposal_is_persisted_and_never_queues(self) -> None:
        self.state['production']['tracks'] = [
            {'id': 'kick', 'name': 'Audio 1 Kick', 'type': 'audio', 'mixer': {'volume': .6, 'pan': 0, 'sends': []},
             'devices': [], 'routing': 'Main', 'arrangement_clips': []},
            {'id': 'unknown', 'name': 'Thing', 'type': 'midi', 'mixer': {'volume': .6, 'pan': 0, 'sends': []},
             'devices': [], 'routing': 'Main', 'arrangement_clips': []},
        ]
        proposal = production.create_cleanup_proposal({})
        self.assertEqual('Proposal', proposal['status'])
        self.assertFalse(proposal['apply_available'])
        self.assertEqual('Kick', proposal['tracks'][0]['suggested_name'])
        self.assertTrue(proposal['tracks'][1]['requires_choice'])
        self.assertEqual([], self.enqueued)
        self.assertEqual(proposal['id'], production._read(self.root / 'production' / 'cleanup-proposals' / (proposal['id'] + '.json'))['id'])

    def test_classic_house_template_is_a_draft_for_a_pristine_capable_set(self) -> None:
        defaults = []
        for index, (name, track_type) in enumerate((('1-MIDI', 'midi'), ('2-MIDI', 'midi'), ('3-Audio', 'audio'), ('4-Audio', 'audio'))):
            defaults.append({'id': 'default-%d' % index, 'name': name, 'type': track_type,
                             'mixer': {'volume': .85, 'pan': 0, 'sends': []}, 'devices': [], 'routing': 'Main',
                             'arrangement_clips': [], 'color_index': 0, 'is_group': False, 'group_track_id': None})
        self.state['production'].update(tracks=defaults, tempo=120.0, metre=[4, 4], locators=[],
                                        template_capabilities={'group_creation': True, 'locators': True, 'locator_range': True, 'track_colours': True},
                                        is_pristine_default_set=True)
        plan = production.create_classic_house_template({'snapshot_name': 'Before Classic House template'})
        self.assertEqual('Draft', plan['status'])
        self.assertEqual('grouped', plan['layout_mode'])
        self.assertEqual([{'type': 'apply_song_sketch_template', 'preset_id': song_sketch.CLASSIC_HOUSE_CLUB_MIX_ID,
                           'layout_mode': 'grouped', 'locator_range': True}], plan['actions'])
        self.assertEqual([], self.enqueued)

    def test_classic_house_template_falls_back_to_explicit_flat_layout(self) -> None:
        defaults = []
        for index, (name, track_type) in enumerate((('1-MIDI', 'midi'), ('2-MIDI', 'midi'), ('3-Audio', 'audio'), ('4-Audio', 'audio'))):
            defaults.append({'id': 'default-%d' % index, 'name': name, 'type': track_type,
                             'mixer': {'volume': .85, 'pan': 0, 'sends': []}, 'devices': [], 'routing': 'Main',
                             'arrangement_clips': [], 'color_index': 0, 'is_group': False, 'group_track_id': None})
        self.state['production'].update(tracks=defaults, tempo=120.0, metre=[4, 4], locators=[],
                                        template_capabilities={'group_creation': False, 'locators': True, 'locator_range': True, 'track_colours': True},
                                        is_pristine_default_set=True)
        plan = production.create_classic_house_template({'snapshot_name': 'Before flat Classic House template'})
        self.assertEqual('flat', plan['layout_mode'])
        self.assertEqual('Groups were not created because this Ableton Live Remote Script cannot create group tracks deterministically.',
                         plan['warnings'][0])
        self.assertEqual('flat', plan['actions'][0]['layout_mode'])
        self.assertTrue(plan['actions'][0]['locator_range'])

    def test_flat_template_defers_locators_when_blank_set_has_no_locator_range(self) -> None:
        self.state['production'].update(
            template_capabilities={'group_creation': False, 'locators': True, 'locator_range': False, 'track_colours': True},
            is_pristine_default_set=True,
        )
        plan = production.create_classic_house_template({'snapshot_name': 'Blank Set with deferred locators'})
        self.assertEqual([{'type': 'apply_song_sketch_template', 'preset_id': song_sketch.CLASSIC_HOUSE_CLUB_MIX_ID,
                           'layout_mode': 'flat', 'locator_range': False}], plan['actions'])
        self.assertTrue(plan['locators_deferred'])
        self.assertEqual(song_sketch.classic_house_preset()['locators'], plan['locator_definitions'])
        self.assertIn('Arrangement locators were deferred', plan['warnings'][-1])
        self.assertEqual([], self.enqueued)

    def test_arrangement_options_are_persisted_retry_safe_and_never_queue(self) -> None:
        tracks = []
        for index, (_group, role, kind) in enumerate(song_sketch.TRACKS):
            tracks.append({'id': 'role-%d' % index, 'name': role, 'type': kind,
                           'mixer': {'volume': .6, 'pan': 0, 'sends': []}, 'devices': [], 'routing': 'Main',
                           'arrangement_clips': ([{'name': '16-bar loop', 'start_time': 0, 'length': 64}] if role == 'Kick' else [])})
        self.state['production'].update(tempo=124.0, metre=[4, 4], tracks=tracks)
        self.state['tracks'] = [{'id': track['id'], 'name': track['name'], 'type': track['type'], 'clips': []} for track in tracks]
        request_id = str(uuid.uuid4())
        proposal = production.create_house_arrangement_options({'request_id': request_id})
        self.assertEqual(production.ARRANGEMENT_PLAN_SCHEMA, proposal['schema_version'])
        self.assertEqual('Options', proposal['status'])
        self.assertEqual([104, 144, 184], [variant['total_bars'] for variant in proposal['variants']])
        self.assertEqual(proposal['id'], production.create_house_arrangement_options({'request_id': request_id})['id'])
        self.assertEqual([], self.enqueued)
        selection_request_id = str(uuid.uuid4())
        selection = production.select_house_arrangement({
            'proposal_id': proposal['id'], 'variant_id': 'club-version', 'approved': True,
            'request_id': selection_request_id, 'phase_3b_benchmark': {'bpm': 124, 'total_bars': 144},
        })
        self.assertEqual('Selected', selection['status'])
        self.assertEqual('club-version', selection['variant']['id'])
        self.assertTrue(selection['execution_available'])
        self.assertEqual(selection['id'], production.select_house_arrangement({
            'proposal_id': proposal['id'], 'variant_id': 'club-version', 'approved': True,
            'request_id': selection_request_id, 'phase_3b_benchmark': {'bpm': 124, 'total_bars': 144},
        })['id'])

    def test_club_execution_plan_is_copy_only_and_rejects_ambiguous_sources(self) -> None:
        source = {'name': 'loop', 'start_beat': 0.0, 'end_beat': 64.0, 'length': 64.0,
                  'metre': [4, 4], 'fingerprint': 'a' * 64}
        self.state['production'].update(
            tempo=124.0, metre=[4, 4],
            template_capabilities={'locators': True},
            tracks=[{'id': 'source', 'name': 'Kick', 'type': 'midi', 'mixer': {'volume': .6, 'pan': 0, 'sends': []},
                     'devices': [], 'routing': 'Main', 'arrangement_clips': [source]}],
        )
        selection_id = str(uuid.uuid4())
        selection = {'id': selection_id, 'status': 'Selected', 'session_id': 'live-session', 'source_revision': 'before',
                     'variant': {'id': 'club-version', 'intended_locators': [
                         {'time': beat, 'name': 'L%d' % index} for index, beat in enumerate((0, 64, 128, 256, 320, 384, 512))]},
                     'assumptions': []}
        production._write(self.root / 'production' / 'arrangement-selections' / (selection_id + '.json'), selection)
        plan = production.create_house_arrangement_execution_plan(
            {'selection_id': selection_id, 'snapshot_name': 'Before Club copy', 'approved': True})
        self.assertEqual('apply_arrangement_copies', plan['actions'][0]['type'])
        self.assertEqual(8, len(plan['actions'][0]['copies']))
        self.assertEqual(576.0, plan['actions'][0]['expected_end_beat'])
        self.assertEqual([], self.enqueued)
        self.state['production']['tracks'][0]['arrangement_clips'].append(dict(source))
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            production.create_house_arrangement_execution_plan(
                {'selection_id': selection_id, 'snapshot_name': 'Ambiguous', 'approved': True})

    def test_drum_and_bass_proposal_needs_sources_before_live_execution(self) -> None:
        self.state['tempo'] = 170.0
        self.state['production'].update(tempo=170.0, metre=[4, 4])
        proposal = production.create_house_arrangement_options({
            'request_id': str(uuid.uuid4()), 'genre': 'Drum & Bass'})
        self.assertEqual('Drum & Bass', proposal['genre'])
        selection = production.select_house_arrangement({
            'proposal_id': proposal['id'], 'variant_id': 'dnb-rolling-club',
            'approved': True, 'request_id': str(uuid.uuid4())})
        self.assertEqual('Drum & Bass', selection['genre'])
        self.assertTrue(selection['execution_available'])
        self.assertEqual([], self.enqueued)
        with self.assertRaisesRegex(ValueError, 'Club version'):
            production.create_house_arrangement_execution_plan({
                'selection_id': selection['id'], 'snapshot_name': 'Not executable', 'approved': True})
        with self.assertRaisesRegex(ValueError, 'does not belong'):
            production.select_house_arrangement({
                'proposal_id': proposal['id'], 'variant_id': 'club-version',
                'approved': True, 'request_id': str(uuid.uuid4())})

    def test_additional_genre_selection_does_not_mutate_live(self) -> None:
        for genre, variant in (("Techno", "techno-peak-time"), ("UK Garage", "ukg-vocal-club"),
                               ("Hip Hop", "hiphop-verse-hook"), ("Disco / Nu-disco", "disco-club-lift")):
            with self.subTest(genre=genre):
                proposal = production.create_house_arrangement_options({
                    'request_id': str(uuid.uuid4()), 'genre': genre})
                selection = production.select_house_arrangement({
                    'proposal_id': proposal['id'], 'variant_id': variant,
                    'approved': True, 'request_id': str(uuid.uuid4())})
                self.assertEqual(genre, selection['genre'])
                self.assertTrue(selection['execution_available'])
                self.assertEqual([], self.enqueued)

    def test_dnb_execution_draft_places_confirmed_source_after_existing_song(self) -> None:
        self.state['tempo'] = 170.0
        self.state['production'].update(tempo=170.0, metre=[4, 4], arrangement_end=1152.0,
                                        locators=[{'time': 0.0, 'name': 'Existing'}])
        self.state['production']['tracks'][0]['name'] = 'Kick'
        self.state['production']['tracks'][0]['arrangement_clips'] = [{
            'name': 'Drum phrase', 'start_beat': 0.0, 'end_beat': 16.0, 'length': 16.0,
            'fingerprint': 'a' * 64, 'metre': [4, 4]}]
        proposal = production.create_house_arrangement_options({
            'request_id': str(uuid.uuid4()), 'genre': 'Drum & Bass'})
        selection = production.select_house_arrangement({
            'proposal_id': proposal['id'], 'variant_id': 'dnb-rolling-club',
            'approved': True, 'request_id': str(uuid.uuid4())})
        plan = production.create_house_arrangement_execution_plan({
            'selection_id': selection['id'], 'snapshot_name': 'Working copy before rolling club',
            'approved': True, 'sources': [{'role': 'Kick', 'track_id': 'bass-id', 'source_start_beat': 0.0}]})
        action = plan['actions'][0]
        self.assertEqual('apply_arrangement_copies', action['type'])
        self.assertTrue(all(item['destination_beat'] >= 1152 for item in action['copies']))
        self.assertEqual([], action['locators'])
        self.assertTrue(plan['source_coverage'])
        self.assertTrue(plan['gaps'])
        self.assertEqual([], self.enqueued)
        with self.assertRaisesRegex(ValueError, 'Restart Ableton Live'):
            production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        self.state['capabilities'].append('arrangement_copy_v2')
        queued = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        self.assertEqual('Queued', queued['status'])
        self.assertEqual(1, len(self.enqueued))

    def test_session_scene_plan_uses_existing_session_clips_and_new_scenes(self) -> None:
        self.state['tempo'] = 170.0
        self.state['capabilities'].append('session_scene_v1')
        self.state['production'].update(tempo=170.0, metre=[4, 4], scene_names=['Ideas', 'Breaks'])
        self.state['production']['tracks'][0]['session_clips'] = [{
            'scene_index': 0, 'name': 'Existing beat', 'length': 16.0, 'fingerprint': 'a' * 64}]
        proposal = production.create_house_arrangement_options({
            'request_id': str(uuid.uuid4()), 'genre': 'Drum & Bass'})
        selection = production.select_house_arrangement({
            'proposal_id': proposal['id'], 'variant_id': 'dnb-rolling-club',
            'approved': True, 'request_id': str(uuid.uuid4())})
        plan = production.create_house_arrangement_execution_plan({
            'selection_id': selection['id'], 'snapshot_name': 'Before Session scene test',
            'approved': True, 'view': 'session',
            'sources': [{'role': 'Kick', 'track_id': 'bass-id', 'source_scene_index': 0}]})
        self.assertEqual('session', plan['view'])
        self.assertEqual(3, plan['first_new_scene'])
        self.assertEqual(7, len(plan['actions'][0]['scenes']))
        self.assertEqual('apply_session_scene_map', plan['actions'][0]['type'])
        self.assertEqual([], self.enqueued)
        queued = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        self.assertEqual('Queued', queued['status'])
        self.assertEqual(1, len(self.enqueued))

    def test_group_track_arrangement_error_treated_as_readable(self) -> None:
        self.state['arrangement_readable'] = False
        self.state['arrangement_errors'] = [{'track_id': 'grp', 'track_name': '15-Group', 'is_group': True,
                                             'error': 'Main, Group and Return Tracks have no arrangement clips'}]
        self.state['production']['arrangement_readable'] = False
        self.state['production']['arrangement_errors'] = self.state['arrangement_errors']
        self.state['production']['tracks'].append({
            'id': 'grp', 'name': '15-Group', 'type': 'audio', 'is_group': True,
            'mixer': {'volume': .85, 'pan': 0.0, 'sends': []},
            'devices': [], 'routing': 'Main', 'arrangement_clips': [],
        })
        result = production.analyse()
        self.assertTrue(result['project']['arrangement_readable'])

    def test_mix_balance_proposal_balances_active_roles_and_skips_empty_tracks(self) -> None:
        self.state['production']['tracks'] = [
            {
                'id': 'vocal', 'name': '1-Audio', 'type': 'audio',
                'mixer': {'volume': .85, 'pan': 0.0, 'sends': [.1]},
                'devices': [], 'routing': 'Main',
                'arrangement_clips': [{'name': 'VOCAL', 'start_beat': 0.0, 'end_beat': 64.0, 'length': 64.0}],
                'session_clips': [],
            },
            {
                'id': 'moog', 'name': '22-moog short 5 A flat1', 'type': 'audio',
                'mixer': {'volume': .85, 'pan': 0.0, 'sends': [.1]},
                'devices': [], 'routing': 'Main',
                'arrangement_clips': [{'name': 'moog short 5 A flat1', 'start_beat': 0.0, 'end_beat': 64.0, 'length': 64.0}],
                'session_clips': [],
            },
            {
                'id': 'shaker', 'name': '10-Shaker 1-96 bpm', 'type': 'audio',
                'mixer': {'volume': .85, 'pan': 0.0, 'sends': [.1]},
                'devices': [], 'routing': 'Main',
                'arrangement_clips': [{'name': 'Shaker 1-96 bpm', 'start_beat': 0.0, 'end_beat': 64.0, 'length': 64.0}],
                'session_clips': [],
            },
            {
                'id': 'empty', 'name': '5-Audio', 'type': 'audio',
                'mixer': {'volume': .85, 'pan': 0.0, 'sends': [.1]},
                'devices': [], 'routing': 'Main', 'arrangement_clips': [], 'session_clips': [],
            },
        ]
        plan = production.create_mix_balance_proposal({})
        self.assertEqual('Draft', plan['status'])
        self.assertEqual(3, len(plan['actions']))
        self.assertEqual(['empty'], [item['track_id'] for item in plan['skipped_empty_tracks']])
        by_target = {a['target_track_id']: a['values'] for a in plan['actions']}
        self.assertAlmostEqual(0.69, by_target['vocal']['volume'])
        self.assertAlmostEqual(0.66, by_target['moog']['volume'])
        self.assertAlmostEqual(0.52, by_target['shaker']['volume'])
        self.assertAlmostEqual(0.22, by_target['shaker']['pan'])
        self.assertEqual([], self.enqueued)

    def test_sends_and_device_parameter_actions_validate_and_capture_rollback_snapshot(self) -> None:
        self.state['production']['tracks'][0]['mixer']['sends'] = [0.1, 0.2]
        self.state['production']['tracks'][0]['devices'] = [{
            'name': 'Auto Filter', 'class_name': 'AutoFilter',
            'parameters': [{'index': 0, 'name': 'Device On', 'value': 1.0, 'min': 0.0, 'max': 1.0, 'is_quantized': True},
                           {'index': 1, 'name': 'Frequency', 'value': 0.35, 'min': 0.0, 'max': 1.0, 'is_quantized': False}],
        }]
        plan = production.create_plan({
            'intent': 'Open filter and send to reverb',
            'snapshot_name': 'Before filter + send',
            'actions': [
                {'type': 'set_track_mixer', 'target_track_id': 'bass-id', 'values': {'send_0': 0.45, 'send_1': 0.6}},
                {'type': 'set_device_parameter', 'target_track_id': 'bass-id', 'device_index': 0, 'parameter_index': 1, 'value': 0.8},
            ],
        })
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        snapshot = production._read(self.root / 'production' / 'snapshots' / (job['snapshot_id'] + '.json'))
        self.assertEqual({'send_0': 0.1, 'send_1': 0.2}, snapshot['inverse_actions'][0]['values'])
        self.assertEqual('set_device_parameter', snapshot['inverse_actions'][1]['type'])
        self.assertAlmostEqual(0.35, snapshot['inverse_actions'][1]['value'])

    def test_compare_reference_renders_validates_and_records_operation(self) -> None:
        import array, math, wave
        sr = 22050
        def make_wav(path: Path, freq: float, amp: float) -> Path:
            pcm = array.array('h')
            for i in range(sr // 2):
                val = amp * math.sin(2.0 * math.pi * freq * (i / sr))
                pcm.append(int(val * 32767))
            with wave.open(str(path), 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(pcm.tobytes())
            return path

        ref = make_wav(self.root / 'ref.wav', 100.0, 0.7)
        cand = make_wav(self.root / 'cand.wav', 2000.0, 0.3)
        res = production.compare_reference_renders({'reference_path': str(ref), 'candidate_path': str(cand)})
        self.assertEqual('compared', res['status'])
        self.assertEqual('vibelton.render-comparison/v1', res['schema_version'])
        self.assertIn('deltas', res)

    def test_check_low_end_clash_diagnoses_and_records_operation(self) -> None:
        import array, math, wave
        sr = 22050
        def make_wav(path: Path, freq: float, phase: float) -> Path:
            pcm = array.array('h')
            for i in range(sr // 2):
                val = 0.8 * math.sin(2.0 * math.pi * freq * (i / sr) + phase)
                pcm.append(int(val * 32767))
            with wave.open(str(path), 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(pcm.tobytes())
            return path

        kick = make_wav(self.root / 'kick.wav', 60.0, 0.0)
        bass = make_wav(self.root / 'bass.wav', 60.0, math.pi)
        res = production.check_low_end_clash({'kick_path': str(kick), 'bass_path': str(bass)})
        self.assertTrue(res['clash_detected'])
        self.assertTrue(res['phase_cancellation_detected'])

    def test_create_session_to_arrangement_plan_and_rollback(self) -> None:
        import json
        fp1 = 'a' * 64
        fp2 = 'b' * 64
        self.state['production']['tracks'].append({
            'id': 'serum-id', 'name': '6-Serum 2', 'type': 'midi',
            'mixer': {'volume': .75, 'pan': 0.0, 'sends': [.1, .1]},
            'devices': [{'name': 'Serum 2', 'class_name': 'PluginDevice'}],
            'routing': 'Main',
            'arrangement_clips': [],
            'session_clips': [
                {'scene_index': 0, 'name': 'Serum Hook A', 'length': 16.0, 'fingerprint': fp1},
                {'scene_index': 1, 'name': 'Serum Hook B', 'length': 16.0, 'fingerprint': fp2},
            ],
        })
        self.state['production']['revision'] = 'rev-s2a-1'

        plan = production.create_session_to_arrangement_plan({})
        self.assertEqual('Draft', plan['status'])
        self.assertEqual('session_to_arrangement', plan['workflow'])
        self.assertEqual(1, len(plan['actions']))
        copies = plan['actions'][0]['copies']
        self.assertEqual(2, len(copies))
        self.assertEqual(0.0, copies[0]['destination_beat'])
        self.assertEqual(16.0, copies[1]['destination_beat'])

        expected_obs = production._observable_rollback_revision(self.state['production'])
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})

        # Simulate bridge execution
        self.state['production']['tracks'][-1]['arrangement_clips'] = [
            {'name': 'Serum Hook A', 'start_beat': 0.0, 'end_beat': 16.0, 'length': 16.0, 'metre': [4, 4], 'fingerprint': fp1},
            {'name': 'Serum Hook B', 'start_beat': 16.0, 'end_beat': 32.0, 'length': 16.0, 'metre': [4, 4], 'fingerprint': fp2},
        ]
        self.state['production']['revision'] = 'rev-s2a-2'
        exec_dir = self.root / 'queue' / 'production-executions'
        exec_dir.mkdir(parents=True, exist_ok=True)
        (exec_dir / (job['id'] + '.json')).write_text(json.dumps({
            'job_id': job['id'], 'status': 'Applied', 'completed_actions': 2,
            'created_copies': copies, 'post_revision': 'rev-s2a-2',
        }), encoding='utf-8')

        rb_job = production.rollback({'job_id': job['id'], 'working_copy_confirmed': True})
        rb_plan = production.get_plan(rb_job['plan_id'])
        self.assertEqual('rollback_session_to_arrangement_copies', rb_plan['actions'][0]['type'])
        self.assertEqual(expected_obs, rb_plan['actions'][0]['expected_post_rollback_observable_revision'])

    def test_mix_balance_proposal_sets_dry_sends_on_kick_bass_and_spatial_sends_on_vocal_chords(self) -> None:
        self.state['production']['tracks'] = [
            {
                'id': 'kick', 'name': 'Kick', 'type': 'audio',
                'mixer': {'volume': .85, 'pan': 0.0, 'sends': [.25, .25]},
                'devices': [], 'routing': 'Main',
                'arrangement_clips': [{'name': 'Kick Loop', 'start_beat': 0.0, 'end_beat': 16.0, 'length': 16.0}],
                'session_clips': [],
            },
            {
                'id': 'bass', 'name': 'Sub Bass', 'type': 'midi',
                'mixer': {'volume': .85, 'pan': 0.0, 'sends': [.2, .2]},
                'devices': [], 'routing': 'Main',
                'arrangement_clips': [{'name': 'Bass Loop', 'start_beat': 0.0, 'end_beat': 16.0, 'length': 16.0}],
                'session_clips': [],
            },
            {
                'id': 'vocal', 'name': 'Lead Vocal', 'type': 'audio',
                'mixer': {'volume': .85, 'pan': 0.0, 'sends': [0.0, 0.0]},
                'devices': [], 'routing': 'Main',
                'arrangement_clips': [{'name': 'Vox', 'start_beat': 0.0, 'end_beat': 16.0, 'length': 16.0}],
                'session_clips': [],
            },
            {
                'id': 'chords', 'name': 'Rhodes Chords', 'type': 'midi',
                'mixer': {'volume': .85, 'pan': 0.0, 'sends': [0.0, 0.0]},
                'devices': [], 'routing': 'Main',
                'arrangement_clips': [{'name': 'Chords', 'start_beat': 0.0, 'end_beat': 16.0, 'length': 16.0}],
                'session_clips': [],
            },
        ]
        plan = production.create_mix_balance_proposal({})
        by_target = {a['target_track_id']: a['values'] for a in plan['actions']}
        self.assertAlmostEqual(0.0, by_target['kick']['send_0'])
        self.assertAlmostEqual(0.0, by_target['kick']['send_1'])
        self.assertAlmostEqual(0.0, by_target['bass']['send_0'])
        self.assertAlmostEqual(0.0, by_target['bass']['send_1'])
        self.assertAlmostEqual(0.28, by_target['vocal']['send_0'])
        self.assertAlmostEqual(0.18, by_target['vocal']['send_1'])
        self.assertAlmostEqual(0.35, by_target['chords']['send_0'])
        self.assertAlmostEqual(0.24, by_target['chords']['send_1'])

    def test_create_device_parameter_plan_creates_reversible_plan(self) -> None:
        self.state['production']['tracks'][0]['devices'] = [{
            'name': 'Serum 2', 'class_name': 'PluginDevice',
            'parameters': [
                {'index': 0, 'name': 'Device On', 'value': 1.0, 'min': 0.0, 'max': 1.0, 'is_quantized': True},
                {'index': 1, 'name': 'Macro 1 Cutoff', 'value': 0.35, 'min': 0.0, 'max': 1.0, 'is_quantized': False},
            ],
        }]
        plan = production.create_device_parameter_plan({
            'changes': [{'target_track_id': 'bass-id', 'device_index': 0, 'parameter_index': 1, 'value': 0.78}],
        })
        self.assertEqual('Draft', plan['status'])
        self.assertEqual('device_parameters', plan['workflow'])
        self.assertEqual(1, len(plan['before_actions']))
        self.assertAlmostEqual(0.35, plan['before_actions'][0]['value'])
        with self.assertRaisesRegex(ValueError, 'parameter value'):
            production.create_device_parameter_plan({
                'changes': [{'target_track_id': 'bass-id', 'device_index': 0, 'parameter_index': 1, 'value': 1.5}],
            })
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        snapshot = production._read(self.root / 'production' / 'snapshots' / (job['snapshot_id'] + '.json'))
        self.assertEqual('set_device_parameter', snapshot['inverse_actions'][0]['type'])
        self.assertAlmostEqual(0.35, snapshot['inverse_actions'][0]['value'])

        # Positional fallback when parameter dicts omit explicit "index"
        self.state['production']['tracks'][0]['devices'] = [{
            'name': 'Serum 2', 'class_name': 'PluginDevice',
            'parameters': [
                {'name': 'Device On', 'value': 1.0, 'min': 0.0, 'max': 1.0, 'is_quantized': True},
                {'name': 'Macro 1 Cutoff', 'value': 0.42, 'min': 0.0, 'max': 1.0, 'is_quantized': False},
            ],
        }]
        plan_pos = production.create_device_parameter_plan({
            'changes': [{'target_track_id': 'bass-id', 'device_index': 0, 'parameter_index': 1, 'value': 0.65}],
        })
        self.assertEqual(1, len(plan_pos['before_actions']))
        self.assertAlmostEqual(0.42, plan_pos['before_actions'][0]['value'])

        # Missing value in parameter snapshot raises ValueError instead of silently skipping before_actions
        self.state['production']['tracks'][0]['devices'][0]['parameters'][1] = {'name': 'Macro 1 Cutoff', 'min': 0.0, 'max': 1.0}
        with self.assertRaisesRegex(ValueError, 'before_actions snapshot'):
            production.create_device_parameter_plan({
                'changes': [{'target_track_id': 'bass-id', 'device_index': 0, 'parameter_index': 1, 'value': 0.65}],
            })

    def test_production_js_polls_midi_jobs_and_guards_focus(self) -> None:
        js_path = Path(__file__).resolve().parent.parent / 'web' / 'production.js'
        content = js_path.read_text(encoding='utf-8')
        self.assertIn('pollInFlight', content)
        self.assertIn('hasFocusedInput', content)
        self.assertIn('for (const report of [transcribeReport, sliceReport])', content)


if __name__ == '__main__':
    unittest.main()
