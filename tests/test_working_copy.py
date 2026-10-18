from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import production, working_copy


class WorkingCopyRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        env = patch.dict(os.environ, {'VIBELTON_HOME': str(self.root / 'home')})
        env.start()
        self.addCleanup(env.stop)
        for target, value in (('vibelton.production.ROOT', self.root / 'production'),
                              ('vibelton.queue.QUEUE_DIR', self.root / 'queue')):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.state = {
            'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1'], 'session_id': 's',
            'production': {'session_id': 's', 'revision': 'r1', 'set_path': '/Sets/song vibelton-working-copy.als',
                           'tracks': [{'id': 't', 'name': 'Bass', 'type': 'midi',
                                       'mixer': {'volume': .6, 'pan': 0.0, 'sends': []}, 'devices': [],
                                       'routing': 'Main', 'arrangement_clips': []}]}}
        self.enqueued: list = []
        for name, effect in (('current_state', lambda: self.state),
                             ('enqueue', lambda actions, source: (self.enqueued.append(actions) or {'id': 'c'}))):
            patcher = patch.object(production.queue, name, side_effect=effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def plan(self) -> dict:
        return production.create_plan({'intent': 'Pan', 'snapshot_name': 'Before pan', 'actions': [
            {'type': 'set_track_mixer', 'target_track_id': 't', 'values': {'pan': .25}}]})

    def set_path(self, value) -> None:
        self.state['production']['set_path'] = value

    def test_working_copy_name_is_allowed(self) -> None:
        job = production.execute({'plan_id': self.plan()['id'], 'working_copy_confirmed': True})
        self.assertEqual('Queued', job['status'])

    def test_original_looking_name_is_blocked_and_nothing_queued(self) -> None:
        plan = self.plan()
        self.set_path('/Sets/My Great Song.als')
        with self.assertRaisesRegex(ValueError, 'does not look like a working copy'):
            production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        self.assertEqual([], self.enqueued)

    def test_untitled_set_is_blocked_with_save_as_hint(self) -> None:
        plan = self.plan()
        self.set_path('')
        with self.assertRaisesRegex(ValueError, 'Save Live Set As'):
            production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})

    def test_confirmation_checkbox_alone_cannot_override_the_gate(self) -> None:
        plan = self.plan()
        self.set_path('/Sets/original.als')
        with self.assertRaises(ValueError):
            production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})

    def test_scaffold_plan_is_blocked_on_original_set(self) -> None:
        self.set_path('/Sets/original.als')
        with self.assertRaisesRegex(ValueError, 'working copy'):
            production.create_scaffold_plan({'genre': 'House'})

    def test_pattern_match_is_case_insensitive_on_file_name_only(self) -> None:
        self.assertTrue(working_copy.check('/a/b/Song VIBELTON-WORKING-COPY .als')['allowed'])
        # A matching *folder* must not make an original Set look like a copy.
        self.assertFalse(working_copy.check('/vibelton-working-copy/Original.als')['allowed'])

    def test_pattern_is_configurable(self) -> None:
        home = self.root / 'home'
        home.mkdir()
        (home / 'config.json').write_text(json.dumps({'working_copy_pattern': 'scratch-copy'}))
        self.assertTrue(working_copy.check('/Sets/track scratch-copy 1.als')['allowed'])
        self.assertFalse(working_copy.check('/Sets/x vibelton-working-copy.als')['allowed'])

    def test_weak_patterns_cannot_loosen_the_rule(self) -> None:
        home = self.root / 'home'
        home.mkdir()
        for weak in ('', '   ', 'copy', 'a', '.als', 'backup', '12345678', '-working-', 5, ['x'], None):
            with self.subTest(pattern=weak):
                (home / 'config.json').write_text(json.dumps({'working_copy_pattern': weak}))
                self.assertEqual(working_copy.DEFAULT_PATTERN, working_copy.pattern())
                self.assertFalse(working_copy.check('/Sets/My song.als')['allowed'])
                self.assertFalse(working_copy.check('/Sets/copy of my song.als')['allowed'])

    def test_the_ignored_pattern_is_explained_to_the_user(self) -> None:
        home = self.root / 'home'
        home.mkdir()
        (home / 'config.json').write_text(json.dumps({'working_copy_pattern': 'copy'}))
        verdict = working_copy.check('/Sets/My song.als')
        self.assertIn('Ignoring working_copy_pattern', verdict['pattern_warning'])
        self.assertIn('shorter than', verdict['pattern_warning'])

    def test_a_reasonable_custom_pattern_has_no_warning(self) -> None:
        home = self.root / 'home'
        home.mkdir()
        (home / 'config.json').write_text(json.dumps({'working_copy_pattern': 'my-sandbox-copy'}))
        self.assertNotIn('pattern_warning', working_copy.check('/Sets/a my-sandbox-copy.als'))

    def test_rollback_is_blocked_on_original_and_on_a_different_set(self) -> None:
        job = production.execute({'plan_id': self.plan()['id'], 'working_copy_confirmed': True})
        production._write(self.root / 'queue' / 'production-executions' / (job['id'] + '.json'),
                          {'status': 'Applied', 'post_revision': 'r1'})
        self.set_path('/Sets/original.als')
        with self.assertRaisesRegex(ValueError, 'working copy'):
            production.rollback({'job_id': job['id'], 'working_copy_confirmed': True})
        self.set_path('/Sets/another vibelton-working-copy.als')
        with self.assertRaisesRegex(ValueError, 'different Live Set'):
            production.rollback({'job_id': job['id'], 'working_copy_confirmed': True})

    def test_job_and_snapshot_record_the_set(self) -> None:
        job = production.execute({'plan_id': self.plan()['id'], 'working_copy_confirmed': True})
        snapshot = production._read(self.root / 'production' / 'snapshots' / (job['snapshot_id'] + '.json'))
        self.assertEqual('/Sets/song vibelton-working-copy.als', job['set_path'])
        self.assertEqual(job['set_path'], snapshot['set_path'])

    def test_status_endpoint_payload(self) -> None:
        self.assertTrue(production.working_copy_status()['allowed'])
        self.set_path('/Sets/original.als')
        status = production.working_copy_status()
        self.assertEqual(('original_set', False), (status['reason'], status['allowed']))


if __name__ == '__main__':
    unittest.main()
