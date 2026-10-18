"""A3: a loop longer than a section is a reported gap, never a hard error or a partial clip."""
from __future__ import annotations

import unittest

from tests import test_arranger_edge_cases as _edge
from vibelton import arrangements, production


class SectionGapTests(unittest.TestCase):
    setUp = _edge.ArrangerEdgeCaseTests.setUp
    load = _edge.ArrangerEdgeCaseTests.load

    def long_loop_set(self, bars: int = 16, tempo: float = 119.0) -> None:
        self.load('12-bar-loop')
        prod = self.state['production']
        prod['tempo'] = self.state['tempo'] = tempo
        for track in prod['tracks']:
            track['arrangement_clips'][0].update(end_beat=bars * 4.0, length=bars * 4.0)
        prod['arrangement_end'] = self.state['arrangement_end'] = bars * 4.0

    def plan(self, variant: str) -> dict:
        return production.create_scaffold_plan({'genre': 'House', 'variant_id': variant})

    def check(self, plan: dict) -> None:
        action = plan['actions'][0]
        lengths = {}
        prod = self.state['production']
        for track in prod['tracks']:
            lengths[track['id']] = track['arrangement_clips'][0]['length']
        real_end = max(c['destination_beat'] + lengths[c['source_track_id']] for c in action['copies'])
        self.assertEqual(real_end, action['expected_end_beat'], 'expected_end_beat must equal the real maximum end')
        for copy_spec in action['copies']:   # no partial clips: every copy ends inside its planned span
            self.assertLessEqual(copy_spec['destination_beat'] + lengths[copy_spec['source_track_id']],
                                 plan['scaffold_scope']['base_beat'] + 4 * plan['variant']['total_bars'] + 1e-6)
        self.assertIsInstance(plan['section_gaps'], list)
        for gap in plan['section_gaps']:
            self.assertTrue({'section', 'section_bars', 'max_unfilled_bars', 'empty', 'roles'} <= set(gap))
            self.assertGreater(gap['max_unfilled_bars'], 0)

    def test_16_bar_loop_at_119_bpm_plans_every_variant(self) -> None:
        self.long_loop_set()
        for variant in arrangements.GENRE_VARIANTS['House']:
            with self.subTest(variant=variant):
                self.check(self.plan(variant))

    def test_final_section_without_fitting_source_is_a_gap_and_warning(self) -> None:
        self.long_loop_set()
        plan = self.plan('dj-extended-mix')
        outro = plan['variant']['sections'][-1]['name']
        self.assertTrue(any(g['section'] == outro and g['empty'] for g in plan['section_gaps']))
        self.assertTrue(any('ends' in w.lower() and outro.lower() in w.lower() for w in plan['warnings']))
        self.assertTrue(any(outro in g for g in plan['gaps']))

    def test_6_and_12_bar_loops_report_gaps_per_section(self) -> None:
        for name in ('6-bar-loop', '12-bar-loop'):
            with self.subTest(fixture=name):
                self.load(name)
                plan = self.plan('club-version')
                self.assertTrue(plan['section_gaps'], 'loops that do not divide sections leave reported gaps')
                self.assertEqual(plan['actions'][0]['expected_end_beat'],
                                 max(c['destination_beat'] + 4 * (6 if name.startswith('6') else 12)
                                     for c in plan['actions'][0]['copies']))


if __name__ == '__main__':
    unittest.main()
