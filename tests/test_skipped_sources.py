"""A2: planning says *why* each track/clip was not used as a source."""
from __future__ import annotations

import copy
import unittest

from tests import test_arranger_edge_cases as _edge
from vibelton import errors, production, role_memory


def reasons(plan_or_exc) -> dict:
    items = plan_or_exc if isinstance(plan_or_exc, list) else plan_or_exc.skipped_sources
    return {(i['track_name'], i['clip_name']): i['reason'] for i in items}


class SkippedSourceTests(unittest.TestCase):
    # Borrow the fixture helpers without inheriting (and re-running) the edge-case tests.
    setUp = _edge.ArrangerEdgeCaseTests.setUp
    load = _edge.ArrangerEdgeCaseTests.load
    scaffold = _edge.ArrangerEdgeCaseTests.scaffold

    def test_looped_extended_and_good_clips(self) -> None:
        fixture = self.load('looped-clips')
        plan = self.scaffold()
        found = reasons(plan['skipped_sources'])
        self.assertEqual('looped_or_extended', found[('1-Kick', 'Kick looped to fill 72 beats')])
        self.assertEqual('looped_or_extended', found[('2-Bass', 'Bass looped to fill 64 beats')])
        self.assertNotIn(('1-Kick', 'Kick 16 bars'), found)
        entry = next(i for i in plan['skipped_sources'] if i['track_name'] == '1-Kick')
        self.assertEqual({'track_name', 'clip_name', 'start_bar', 'reason'}, set(entry))
        self.assertEqual(1, entry['start_bar'])
        self.assertTrue(any('not used' in w.lower() and 'looped' in w.lower() for w in plan['warnings']))

    def test_not_whole_bar_fails_with_reason(self) -> None:
        self.load('2p5-bar-loop')
        with self.assertRaises(production.ScaffoldPlanError) as ctx:
            self.scaffold()
        self.assertEqual({'not_whole_bar'}, set(reasons(ctx.exception).values()))
        explained = errors.explain(str(ctx.exception), {'skipped_sources': ctx.exception.skipped_sources})
        self.assertIn('whole', explained['message'].lower())
        self.assertNotIn('/', explained['message'])
        self.assertTrue(explained['details'])

    def test_longer_than_16_bars_and_no_fingerprint(self) -> None:
        fixture = self.load('12-bar-loop')
        prod = self.state['production']
        for track in prod['tracks']:
            clip = track['arrangement_clips'][0]
            if track['id'] == 'kick':
                clip.update(end_beat=80.0, length=80.0)
            else:
                clip.pop('fingerprint')
        with self.assertRaises(production.ScaffoldPlanError) as ctx:
            self.scaffold()
        found = reasons(ctx.exception)
        self.assertEqual('longer_than_16_bars', found[('1-Kick', 'Kick')])
        self.assertEqual('no_fingerprint', found[('2-Bass', 'Bass')])

    def test_group_track_and_unknown_role(self) -> None:
        self.load('clip-on-group-track')
        prod = self.state['production']
        mystery = {**copy.deepcopy(prod['tracks'][1]), 'id': 'mystery', 'name': 'Zzz Thing'}
        mystery['arrangement_clips'][0]['name'] = 'Zzz'
        prod['tracks'].append(mystery)
        plan = self.scaffold()
        found = reasons(plan['skipped_sources'])
        self.assertEqual('group_track', found[('Drums', 'Stray group clip')])
        self.assertEqual('no_role', found[('Zzz Thing', 'Zzz')])

    def test_two_tracks_with_the_same_role_layer_towards_the_peak(self) -> None:
        # A second track of the same role is used too: it joins in the higher-energy sections only.
        self.load('12-bar-loop')
        prod = self.state['production']
        twin = {**copy.deepcopy(prod['tracks'][0]), 'id': 'kick2', 'name': '5-Kick'}
        prod['tracks'].append(twin)
        plan = self.scaffold()
        used = {c['source_track_id'] for c in plan['actions'][0]['copies']}
        self.assertEqual({'kick', 'kick2'}, used & {'kick', 'kick2'})
        sections = {track: {c['section'] for c in plan['source_coverage'] if c['track_name'] == track}
                    for track in ('1-Kick', '5-Kick')}
        self.assertLess(sections['5-Kick'], sections['1-Kick'])   # a strict subset: fewer sections
        energy = {sec['name']: sec['energy_level'] for sec in plan['variant']['sections']}
        peak = max(energy[name] for name in sections['1-Kick'])
        self.assertTrue(any(energy[name] == peak for name in sections['5-Kick']))
        self.assertNotIn('role_already_used', {i['reason'] for i in plan.get('skipped_sources', [])})

    def test_role_ignored(self) -> None:
        self.load('12-bar-loop')
        plan = production.create_scaffold_plan({'genre': 'House', 'variant_id': 'club-version',
                                                'roles': {'chords': role_memory.IGNORE}})
        self.assertEqual('role_ignored', reasons(plan['skipped_sources'])[('4-Chords', 'Chords')])

    def test_error_names_top_reason_in_plain_language(self) -> None:
        skipped = [{'track_name': 'Kick', 'clip_name': 'a', 'start_bar': 1, 'reason': 'looped_or_extended'}] * 14 + \
                  [{'track_name': 'Pad', 'clip_name': 'b', 'start_bar': 1, 'reason': 'no_role'}]
        explained = errors.explain('No fingerprinted 4-bar to 16-bar source loops found', {'skipped_sources': skipped})
        self.assertIn('14 clips were looped or stretched', explained['message'])
        self.assertIn('Cmd+J', explained['message'])
        self.assertEqual(15, len(explained['details']))


if __name__ == '__main__':
    unittest.main()
