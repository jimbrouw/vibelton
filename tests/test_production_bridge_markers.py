"""Remote Script marker support: the probe and exact-readback arrangement cues."""
from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

try:
    import test_production_bridge as base
except ImportError:  # run as tests.test_production_bridge_markers
    from tests import test_production_bridge as base

Cue, module = base.Cue, base.module


class ProbeSong(base.ArrangementSong):
    song_length = 64.0


class DriftingSong(ProbeSong):
    """Models the Live 12.3.2 failure mode: the cue does not land where requested."""

    def set_or_delete_cue(self) -> None:
        for index, cue in enumerate(self.cue_points):
            if abs(cue.time - self.current_song_time) < .00001:   # deleting what is under the playhead works
                self.cue_points.pop(index)
                return
        self.cue_points.append(Cue(self.current_song_time + 1.0))


class StickyDeleteSong(ProbeSong):
    """Setting a cue works, but removing one is ignored for the first ``refusals`` attempts."""

    refusals = 10 ** 6

    def set_or_delete_cue(self) -> None:
        if any(abs(c.time - self.current_song_time) < .00001 for c in self.cue_points):
            if self.refusals <= 0:
                return super().set_or_delete_cue()
            self.refusals -= 1
            return None
        return super().set_or_delete_cue()


class BridgeMarkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = patch.object(module.os.path, 'expanduser', return_value=self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.song = ProbeSong()
        self.bridge = module.CompositionBridge()
        self.bridge._composition_init()
        self.bridge.song = lambda: self.song
        self.bridge._log = lambda *args: None

    def action(self, actions, revision=None) -> dict:
        return {'type': 'production_apply', 'job_id': str(uuid.uuid4()),
                'session_id': self.bridge._composition_session,
                'source_revision': revision or self.bridge._production_state()['revision'], 'actions': actions}

    def result(self, action) -> dict:
        return json.loads((Path(self.tmp.name) / '.vibelton' / 'production-executions' / (action['job_id'] + '.json')).read_text())

    def capability(self) -> bool:
        return self.bridge._production_state()['template_capabilities']['arrangement_locator_readback']

    def run_probe(self) -> dict:
        action = self.action([{'type': 'probe_arrangement_locators'}])
        try:
            self.bridge._production_apply(action)
        except RuntimeError:
            pass
        return self.result(action)

    # -- probe ----------------------------------------------------------

    def test_capability_is_off_until_a_probe_passes(self) -> None:
        self.assertFalse(self.capability())

    def test_passing_probe_enables_markers_and_leaves_the_cue_list_unchanged(self) -> None:
        keep = Cue(8.0)
        keep.name = 'User marker'
        self.song.cue_points = [keep]
        result = self.run_probe()
        self.assertEqual('Applied', result['status'], result.get('error'))
        self.assertTrue(result['locator_probe']['passed'])
        self.assertEqual([('User marker', 8.0)], [(c.name, c.time) for c in self.song.cue_points])
        self.assertTrue(self.capability())

    def test_probe_works_through_the_real_asynchronous_path_too(self) -> None:
        self.bridge.schedule_message = lambda _ticks, callback: callback()
        self.assertEqual('Applied', self.run_probe()['status'])
        self.assertTrue(self.capability())

    def test_a_cue_that_does_not_land_exactly_fails_the_probe_and_reports_it(self) -> None:
        self.song = DriftingSong()
        result = self.run_probe()
        self.assertEqual('Failed', result['status'])
        self.assertFalse(result['locator_probe']['passed'])
        self.assertEqual([], result['locator_probe']['leftover_cues'])   # the drifted cue was cleaned up
        self.assertFalse(self.capability())

    def test_set_ok_but_delete_fails_reports_the_leftover_cue(self) -> None:
        self.song = StickyDeleteSong()
        result = self.run_probe()
        probe = result['locator_probe']
        self.assertEqual('Failed', result['status'])
        self.assertFalse(probe['passed'])
        self.assertTrue(probe['cleanup_attempted'])
        self.assertEqual(['VIBELTON_PROBE'], [c['name'] for c in probe['leftover_cues']])
        self.assertFalse(self.capability())

    def test_cleanup_that_succeeds_leaves_no_leftover_cue(self) -> None:
        self.song = StickyDeleteSong()
        self.song.refusals = 1   # the probe's own delete is ignored; the cleanup delete works
        result = self.run_probe()
        probe = result['locator_probe']
        self.assertEqual('Failed', result['status'])
        self.assertTrue(probe['cleanup_attempted'])
        self.assertEqual([], probe['leftover_cues'])
        self.assertEqual([], self.song.cue_points)

    def test_cleanup_also_works_through_the_asynchronous_path(self) -> None:
        self.bridge.schedule_message = lambda _ticks, callback: callback()
        self.song = StickyDeleteSong()
        self.song.refusals = 1
        probe = self.run_probe()['locator_probe']
        self.assertTrue(probe['cleanup_attempted'])
        self.assertEqual([], probe['leftover_cues'])

    def test_drifted_cue_is_cleaned_up_but_the_users_own_cues_are_not(self) -> None:
        self.song = DriftingSong()
        mine = Cue(8.0)
        mine.name = 'Drop'
        self.song.cue_points = [mine]
        probe = self.run_probe()['locator_probe']
        self.assertTrue(probe['cleanup_attempted'])
        self.assertEqual([], probe['leftover_cues'])
        self.assertEqual([('Drop', 8.0)], [(c.name, c.time) for c in self.song.cue_points])

    def test_probe_on_a_set_too_short_to_seek_into_fails_cleanly(self) -> None:
        self.song.song_length = 0.0
        result = self.run_probe()
        self.assertEqual('Failed', result['status'])
        self.assertIn('too short', result['error'])
        self.assertEqual([], self.song.cue_points)

    def test_failed_probe_after_a_pass_turns_the_capability_back_off(self) -> None:
        self.run_probe()
        self.assertTrue(self.capability())
        self.song = DriftingSong()
        self.run_probe()
        self.assertFalse(self.capability())

    def test_probe_rejects_extra_parameters(self) -> None:
        action = self.action([{'type': 'probe_arrangement_locators', 'time': 4.0}])
        with self.assertRaises(RuntimeError):
            self.bridge._production_apply(action)

    # -- arrangement apply with markers ----------------------------------

    def copy_action(self, track, fingerprint, markers, deferred=False) -> dict:
        definitions = [{'time': float(t), 'name': 'S%d' % i} for i, t in enumerate((64.0, 80.0, 96.0, 112.0, 128.0, 144.0, 160.0))]
        return self.action([{
            'type': 'apply_arrangement_copies', 'expected_end_beat': 128.0, 'locators_deferred': deferred,
            'copies': [{'source_track_id': self.bridge._composition_track_id(track), 'source_start_beat': 0.0,
                        'source_fingerprint': fingerprint, 'destination_beat': 64.0}],
            'locators': [] if deferred else markers, 'locator_definitions': definitions}])

    def prepared_song(self):
        self.song = ProbeSong()
        track = self.song.tracks[0]
        return track, self.bridge._composition_clip_snapshot(track.arrangement_clips[0])

    def test_markers_are_refused_until_the_capability_is_proven(self) -> None:
        track, fingerprint = self.prepared_song()
        action = self.copy_action(track, fingerprint, [{'time': 64.0, 'name': 'INTRO'}])
        with self.assertRaisesRegex(RuntimeError, 'cannot create deterministic'):
            self.bridge._production_apply(action)
        self.assertEqual(1, len(track.arrangement_clips))

    def test_markers_are_created_alongside_the_users_own_cues_and_removed_exactly(self) -> None:
        track, fingerprint = self.prepared_song()
        user = Cue(8.0)
        user.name = 'My marker'
        self.song.cue_points = [user]
        self.assertEqual('Applied', self.run_probe()['status'])
        self.bridge.schedule_message = lambda _ticks, callback: callback()
        before = self.bridge._production_observable_rollback_revision()
        marker = {'time': 64.0, 'name': 'INTRO'}
        apply = self.copy_action(track, fingerprint, [marker])
        self.bridge._production_apply(apply)
        applied = self.result(apply)
        self.assertEqual('Applied', applied['status'], applied.get('error'))
        self.assertEqual(['My marker', 'INTRO'], sorted((c.name for c in self.song.cue_points), key=['My marker', 'INTRO'].index))
        self.assertEqual([marker], applied['created_locators'])
        self.song.song_length = 128.0
        rollback = self.action([{'type': 'rollback_arrangement_copies', 'copies': applied['created_copies'],
                                 'locators': applied['created_locators'],
                                 'expected_post_rollback_observable_revision': before}])
        self.bridge._production_apply(rollback)
        done = self.result(rollback)
        self.assertEqual('Applied', done['status'], done.get('error'))
        self.assertEqual([('My marker', 8.0)], [(c.name, c.time) for c in self.song.cue_points])

    def test_a_marker_on_top_of_an_existing_cue_is_refused_before_anything_changes(self) -> None:
        track, fingerprint = self.prepared_song()
        self.run_probe()
        clash = Cue(64.0)
        clash.name = 'Already here'
        self.song.cue_points = [clash]
        action = self.copy_action(track, fingerprint, [{'time': 64.0, 'name': 'INTRO'}])
        with self.assertRaisesRegex(RuntimeError, 'already exists'):
            self.bridge._production_apply(action)
        self.assertEqual(1, len(track.arrangement_clips))

    def test_deferred_markers_still_never_touch_existing_cues(self) -> None:
        track, fingerprint = self.prepared_song()
        user = Cue(8.0)
        user.name = 'My marker'
        self.song.cue_points = [user]
        action = self.copy_action(track, fingerprint, [], deferred=True)
        self.bridge._production_apply(action)
        self.assertEqual('Applied', self.result(action)['status'])
        self.assertEqual([('My marker', 8.0)], [(c.name, c.time) for c in self.song.cue_points])


if __name__ == '__main__':
    unittest.main()
