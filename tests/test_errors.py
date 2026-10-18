from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import errors, production

try:
    from fake_live import FakeLive
except ImportError:
    from tests.fake_live import FakeLive

# Raw messages exactly as the server and Remote Script raise them today.
KNOWN = {
    'live_disconnected': 'Ableton is disconnected or its heartbeat is stale',
    'bridge_outdated': 'Install the Phase 1 Vibelton bridge and restart Live before using Production plans',
    'session_expired': 'Missing or invalid session token',
    'blocked_origin': 'Forbidden origin',
    'working_copy': '“shape.als” does not look like a working copy (its name must contain “vibelton-working-copy”).',
    'other_set': 'This job was applied to a different Live Set; open that Set to roll it back',
    'undo_unsafe': 'Live project state changed after this job; rollback is no longer safe',
    'stale_plan': 'Live project state changed; create a new production plan',
    'no_sources': 'No fingerprinted 4-bar to 16-bar source loops found in the Set to scaffold from',
    'outro_uncovered': 'Choose a source for the final section so the arrangement reaches its outro',
    'bad_source_clip': 'Choose a fingerprinted, whole-bar Arrangement clip of at most 16 bars',
    'section_occupied': 'Section Intro already has clips on 1-Kick where it would be placed. Undo that section first.',
    'unknown_section': "Unknown section 'Nope'. Sections: Intro, Groove",
    'not_4_4': 'Arrangement scaffolding currently requires a 4/4 Live Set',
    'destination_occupied': 'Arrangement copy destination is already occupied',
    'source_changed': 'Expected arrangement copy is missing or changed',
    'readback_mismatch': 'Arrangement copy readback did not match',
    'rollback_inexact': 'Arrangement rollback did not restore the exact original state',
    'replay': 'Production command already attempted; automatic replay rejected',
    'interrupted': 'Live restarted before the production job was acknowledged. It will not be retried automatically.',
    'nothing_to_undo': 'Nothing to roll back. Removed 0 of 4 clips.',
}


class CatalogueTests(unittest.TestCase):
    def test_every_known_message_maps_to_its_code(self) -> None:
        for code, raw in KNOWN.items():
            with self.subTest(code=code):
                result = errors.explain(raw)
                self.assertEqual(code, result['code'])
                self.assertEqual(raw[:2000], result['raw'])
                self.assertTrue(result['message'] and result['title'] and result['next_step'])

    def test_plain_text_never_leaks_code_or_paths(self) -> None:
        for raw in KNOWN.values():
            shown = ' '.join(errors.explain(raw)[k] for k in ('title', 'message', 'next_step'))
            for bad in ('Traceback', 'File "', '.py', 'RuntimeError', 'Exception', 'KeyError'):
                self.assertNotIn(bad, shown)

    def test_unknown_errors_are_generic_but_keep_the_raw_text_for_details(self) -> None:
        result = errors.explain("KeyError: 'target_track_id' at /Users/x/vibelton/production.py:123")
        self.assertEqual('unexpected', result['code'])
        self.assertNotIn('/Users', result['message'])
        self.assertIn('target_track_id', result['raw'])

    def test_placed_counts_lead_the_message_and_mention_undo(self) -> None:
        result = errors.explain('Arrangement copy readback did not match', {'placed': 3, 'planned': 22})
        self.assertTrue(result['message'].startswith('3 of 22 clips placed.'))
        self.assertTrue(result['undo_available'])
        self.assertIn('Undo is available', result['next_step'])

    def test_nothing_placed_says_so_plainly(self) -> None:
        result = errors.explain('Arrangement copy destination is already occupied', {'placed': 0, 'planned': 22})
        self.assertTrue(result['message'].startswith('Nothing was placed in Live.'))
        self.assertFalse(result['undo_available'])

    def test_the_home_directory_is_removed_from_the_details(self) -> None:
        from pathlib import Path as _P
        result = errors.explain("[Errno 2] No such file: %s/Music/secret/x.wav" % _P.home())
        self.assertNotIn(str(_P.home()), result['raw'])
        self.assertIn('~/Music/secret/x.wav', result['raw'])

    def test_an_empty_error_does_not_crash(self) -> None:
        self.assertEqual('unexpected', errors.explain(None)['code'])


class JobExplanationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for target, value in (('vibelton.production.ROOT', self.root / 'production'), ('vibelton.queue.QUEUE_DIR', self.root / 'queue')):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        prod = json.loads((Path(__file__).resolve().parent / 'fixtures' / 'arranger-mixed-audio-midi.json').read_text())['production']
        prod.update(session_id='s', revision='')
        self.state = {'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1', 'arrangement_copy_v2'],
                      'session_id': 's', 'tempo': 124.0, 'metre': [4, 4], 'production': prod}
        self.live = FakeLive(self)
        self.live.seal()
        self.enqueued: list[dict] = []
        for name, effect in (('current_state', lambda: self.state),
                             ('enqueue', lambda actions, source: (self.enqueued.append({'actions': actions}) or {'id': 'c'}))):
            patcher = patch.object(production.queue, name, side_effect=effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def scaffold(self):
        plan = production.create_scaffold_plan({'genre': 'House', 'variant_id': 'club-version'})
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        self.live.process(0)
        return plan, production.job_status(job['id'])

    def test_a_partial_scaffold_says_how_much_was_placed_and_offers_undo(self) -> None:
        self.live.fail_after = 3
        plan, job = self.scaffold()
        planned = len(plan['actions'][0]['copies'])
        explanation = job['explanation']
        self.assertEqual('Partial failure', job['status'])
        self.assertTrue(explanation['message'].startswith('3 of %d clips placed.' % planned), explanation['message'])
        self.assertTrue(explanation['undo_available'])
        self.assertEqual('simulated failure', explanation['raw'])
        self.assertNotIn('Traceback', json.dumps(explanation))

    def test_a_clean_job_has_no_explanation(self) -> None:
        _, job = self.scaffold()
        self.assertEqual('Applied', job['status'])
        self.assertNotIn('explanation', job)


if __name__ == '__main__':
    unittest.main()
