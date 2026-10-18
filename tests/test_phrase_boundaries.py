"""Phrase-safe section boundaries and bar-line stem entries/exits."""
from __future__ import annotations

import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import arrangements, production

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def options_for(genre: str, bpm: float) -> dict:
    return arrangements.build_options(genre, {'tempo': bpm}, {'tempo': float(bpm), 'tracks': [], 'metre': [4, 4]}, None)


class PhraseMathTests(unittest.TestCase):
    def test_every_genre_variant_and_tempo_snaps_to_whole_phrases(self) -> None:
        for genre in arrangements.SUPPORTED_GENRES:
            for bpm in range(60, 201, 2):
                with self.subTest(genre=genre, bpm=bpm):
                    options = options_for(genre, bpm)
                    arrangements.validate_options(options)
                    for variant in options['variants']:
                        phrase = variant['phrase_bars']
                        self.assertIn(phrase, (4, 8))
                        for section in variant['sections']:
                            self.assertEqual(0, section['start_bar'] % phrase)
                            self.assertEqual(0, section['end_bar'] % phrase)
                            self.assertGreaterEqual(section['bar_count'], phrase)
                        self.assertEqual(0, variant['total_bars'] % phrase)

    def test_total_length_stays_within_one_phrase_of_the_duration_target(self) -> None:
        for bpm in (90, 119, 124, 128, 140, 174):
            options = options_for('House', bpm)
            for variant in options['variants']:
                ideal = variant['target_duration_seconds'] * bpm / 240.0
                self.assertLessEqual(abs(variant['total_bars'] - ideal), variant['phrase_bars'] * 1.5 + 0.5,
                                     (bpm, variant['id']))

    def test_eight_bar_phrases_are_used_when_the_arrangement_is_long_enough(self) -> None:
        self.assertEqual(8, arrangements.phrase_unit(144, 7))
        self.assertEqual(4, arrangements.phrase_unit(64, 7))
        self.assertEqual(4, arrangements.phrase_unit(100, 14))  # not enough room for 8-bar minimums

    def test_proportions_survive_the_snapping(self) -> None:
        sections = options_for('House', 124)['variants'][1]['sections']  # club version: 16/16/32/16/16/32/16
        self.assertEqual([16, 16, 32, 16, 16, 32, 16], [s['bar_count'] for s in sections])

    def test_off_phrase_boundaries_fail_closed(self) -> None:
        options = options_for('House', 119)
        arrangements.validate_options(options)
        tampered = copy.deepcopy(options)
        first, second = tampered['variants'][0]['sections'][:2]
        first['end_bar'] -= 1
        first['bar_count'] -= 1
        second['start_bar'] -= 1
        second['bar_count'] += 1
        with self.assertRaisesRegex(ValueError, 'phrases'):
            arrangements.validate_options(tampered)

    def test_missing_phrase_declaration_fails_closed(self) -> None:
        options = options_for('Techno', 126)
        del options['variants'][0]['phrase_bars']
        with self.assertRaisesRegex(ValueError, 'phrase length'):
            arrangements.validate_options(options)


class StemBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for target, value in (('vibelton.production.ROOT', root / 'production'), ('vibelton.queue.QUEUE_DIR', root / 'queue')):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.state: dict = {}
        patcher = patch.object(production.queue, 'current_state', side_effect=lambda: self.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def plan_for(self, fixture: str, **extra) -> dict:
        prod = json.loads((FIXTURES / f'arranger-{fixture}.json').read_text())['production']
        prod.update(session_id='s', revision='r-' + fixture)
        self.state = {'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1', 'arrangement_copy_v2'],
                      'session_id': 's', 'tempo': prod['tempo'], 'metre': prod['metre'], 'production': prod}
        return production.create_scaffold_plan({'genre': 'House', 'variant_id': 'club-version', **extra})

    def test_every_entry_and_exit_is_listed_and_sits_on_a_bar_line(self) -> None:
        plan = self.plan_for('mixed-audio-midi')
        self.assertTrue(plan['boundaries'])
        self.assertEqual(8, plan['phrase_bars'])
        for item in plan['boundaries']:
            self.assertTrue(item['on_bar_line'])
            self.assertEqual('bar_line', item['handling'])
            if item['edge_beat'] is not None:
                self.assertEqual(0.0, item['edge_beat'] % 4)
        enters = [b for b in plan['boundaries'] if b['event'] == 'enter']
        self.assertTrue(enters)
        # an entering stem's first clip starts exactly at the section boundary
        base = (plan['start_bar'] - 1) * 4.0
        for item in enters:
            self.assertEqual(base + 4.0 * (item['bar'] - plan['start_bar']), item['edge_beat'])

    def test_audio_boundaries_carry_a_fade_warning_and_midi_only_sets_do_not(self) -> None:
        audio = self.plan_for('mixed-audio-midi')
        self.assertTrue(any(b['audio'] for b in audio['boundaries']))
        self.assertTrue(any('clip fades' in w for w in audio['warnings']), audio['warnings'])
        midi = self.plan_for('nested-groups')
        self.assertFalse(any(b['audio'] for b in midi['boundaries']))
        self.assertFalse(any('clip fades' in w for w in midi['warnings']))

    def test_exits_use_the_real_clip_end_even_when_a_loop_leaves_a_gap(self) -> None:
        plan = self.plan_for('6-bar-loop')
        exits = [b for b in plan['boundaries'] if b['event'] == 'exit' and b['edge_beat'] is not None]
        self.assertTrue(exits)
        for item in exits:
            boundary_beat = (plan['start_bar'] - 1) * 4.0 + 4.0 * (item['bar'] - plan['start_bar'])
            self.assertLessEqual(item['edge_beat'], boundary_beat)
            self.assertEqual(0.0, item['edge_beat'] % 4)

    def test_section_plans_only_report_their_own_boundaries(self) -> None:
        plan = self.plan_for('mixed-audio-midi', section='Breakdown')
        self.assertTrue(plan['boundaries'])
        self.assertTrue(all('Breakdown' in (b['from'], b['to']) for b in plan['boundaries']))

    def test_summary_text_is_readable(self) -> None:
        plan = self.plan_for('mixed-audio-midi')
        self.assertRegex(plan['boundary_summary'], r'^\d+ stem entries and \d+ exits')

    def test_a_clip_edge_inside_a_bar_is_refused(self) -> None:
        sections = [{'name': 'A', 'start_bar': 0, 'end_bar': 4, 'active_track_roles': ['Kick']},
                    {'name': 'B', 'start_bar': 4, 'end_bar': 8, 'active_track_roles': []}]
        chosen = {'Kick': ('t', {}, 10.0)}
        copies = [{'source_track_id': 't', 'destination_beat': 0.0}]
        with self.assertRaisesRegex(ValueError, 'inside a bar'):
            production._stem_boundaries(sections, chosen, copies, {'t': 10.0}, {'t': {'name': 'T', 'type': 'audio'}}, 0.0, None)


if __name__ == '__main__':
    unittest.main()
