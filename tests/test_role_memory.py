from __future__ import annotations

import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import production, role_maps, role_memory

ROLES = role_maps.ROLES


def track(tid, name, index, ttype='midi', **extra):
    return {'id': tid, 'name': name, 'index': index, 'type': ttype, 'is_group': False, **extra}


def entry(tid, name, index, role, ttype='midi'):
    return {'track_id': tid, 'track_name': name, 'track_index': index, 'track_type': ttype, 'role': role}


class MatchingTests(unittest.TestCase):
    def test_same_id_survives_a_rename(self) -> None:
        match = role_memory.resolve([entry('a', 'Kick', 0, 'Kick')], [track('a', 'Thump', 0)])['matches']['a']
        self.assertEqual(('Kick', 'id', 'Kick'), (match['role'], match['matched_by'], match['renamed_from']))
        self.assertFalse(match['needs_review'])

    def test_reopened_set_new_ids_match_by_unique_name(self) -> None:
        result = role_memory.resolve([entry('old1', 'Kick', 0, 'Kick'), entry('old2', 'Bass', 1, 'Bass')],
                                     [track('n2', 'Bass', 1), track('n1', 'Kick', 0)])
        self.assertEqual({'n1': 'name', 'n2': 'name'}, {t: m['matched_by'] for t, m in result['matches'].items()})
        self.assertEqual('Bass', result['matches']['n2']['role'])

    def test_duplicate_names_fall_back_to_position_and_ask_for_review(self) -> None:
        entries = [entry('o1', 'Serum 2', 5, 'Bass'), entry('o2', 'Serum 2', 7, 'Chords')]
        result = role_memory.resolve(entries, [track('n1', 'Serum 2', 5), track('n2', 'Serum 2', 7)])
        self.assertEqual({'n1': 'position', 'n2': 'position'}, {t: m['matched_by'] for t, m in result['matches'].items()})
        self.assertTrue(all(m['needs_review'] for m in result['matches'].values()))
        self.assertEqual('Bass', result['matches']['n1']['role'])

    def test_renamed_after_reload_is_matched_by_position_for_review(self) -> None:
        result = role_memory.resolve([entry('o1', 'Kick', 0, 'Kick')], [track('n1', 'Four on floor', 0)])
        self.assertEqual(('position', True), (result['matches']['n1']['matched_by'], result['matches']['n1']['needs_review']))

    def test_a_removed_track_is_orphaned_and_a_new_one_has_no_role(self) -> None:
        result = role_memory.resolve([entry('a', 'Kick', 0, 'Kick'), entry('b', 'Lead', 1, 'Lead')],
                                     [track('a', 'Kick', 0), track('c', 'Pad', 2)])
        self.assertEqual(['Lead'], [e['track_name'] for e in result['orphaned']])
        self.assertEqual(['c'], result['new_tracks'])
        self.assertNotIn('c', result['matches'])

    def test_undoing_a_deletion_restores_the_role(self) -> None:
        memory = [entry('b', 'Lead', 1, 'Lead')]
        self.assertEqual(['Lead'], [e['track_name'] for e in role_memory.resolve(memory, [])['orphaned']])
        self.assertEqual('Lead', role_memory.resolve(memory, [track('z', 'Lead', 1)])['matches']['z']['role'])

    def test_ambiguity_never_guesses(self) -> None:
        # Two remembered tracks could both be the one renamed track: leave it unmatched.
        entries = [entry('o1', 'A', 3, 'Kick'), entry('o2', 'B', 3, 'Bass')]
        result = role_memory.resolve(entries, [track('n1', 'C', 3)])
        self.assertEqual({}, result['matches'])
        self.assertEqual(2, len(result['orphaned']))

    def test_group_tracks_never_take_a_role(self) -> None:
        result = role_memory.resolve([entry('g', 'Drums', 0, 'Kick')], [{**track('g', 'Drums', 0), 'is_group': True}])
        self.assertEqual({}, result['matches'])

    def test_ignored_is_remembered_as_none(self) -> None:
        merged = role_memory.merge([], [track('a', 'Foo', 0)], {'a': 'Ignore / Unknown'}, ROLES)
        self.assertIsNone(merged[0]['role'])
        self.assertIn('a', role_memory.remembered_roles(merged, [track('a', 'Foo', 0)]))


class MergeTests(unittest.TestCase):
    def test_saving_refreshes_the_identity_of_matched_entries(self) -> None:
        old = [entry('old', 'Kick', 0, 'Kick'), entry('o2', 'Bass', 1, 'Bass')]
        tracks = [track('new', 'Kick', 0), track('n2', 'Bass', 1)]
        merged = role_memory.merge(old, tracks, {'new': 'Kick'}, ROLES)
        self.assertEqual({'new', 'n2'}, {e['track_id'] for e in merged})  # both re-stamped to the live ids

    def test_an_unreviewed_position_guess_is_not_stamped_until_confirmed(self) -> None:
        old = [entry('o1', 'Kick', 0, 'Kick')]
        tracks = [track('n1', 'Renamed', 0)]
        untouched = role_memory.merge(old, tracks, {}, ROLES)
        self.assertEqual('Kick', untouched[0]['track_name'])
        confirmed = role_memory.merge(old, tracks, {'n1': 'Kick'}, ROLES)
        self.assertEqual('Renamed', confirmed[0]['track_name'])

    def test_orphans_survive_a_save(self) -> None:
        merged = role_memory.merge([entry('gone', 'Lead', 4, 'Lead')], [track('a', 'Kick', 0)], {'a': 'Kick'}, ROLES)
        self.assertEqual({'Lead', 'Kick'}, {e['track_name'] for e in merged})

    def test_unknown_roles_and_tracks_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unsupported track role'):
            role_memory.merge([], [track('a', 'x', 0)], {'a': 'Flugelhorn'}, ROLES)
        with self.assertRaisesRegex(ValueError, 'not in the open Set'):
            role_memory.merge([], [track('a', 'x', 0)], {'zzz': 'Kick'}, ROLES)


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for target, value in (('vibelton.production.ROOT', root / 'production'), ('vibelton.queue.QUEUE_DIR', root / 'queue')):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        fixture = json.loads((Path(__file__).resolve().parent / 'fixtures' / 'arranger-mixed-audio-midi.json').read_text())
        self.production = fixture['production']
        self.production.update(session_id='s', revision='r1')
        # Meaningless names: heuristics cannot identify these stems.
        for i, t in enumerate(self.production['tracks']):
            t['name'] = 'Track %s' % 'ABCD'[i]
            t['index'] = i
            for c in t['arrangement_clips']:
                c['name'] = 'Loop'
        self.state = {'connected': True, 'updated_at': time.time(), 'capabilities': ['production_v1', 'arrangement_copy_v2'],
                      'session_id': 's', 'tempo': 124.0, 'metre': [4, 4], 'production': self.production}
        patcher = patch.object(production.queue, 'current_state', side_effect=lambda: self.state)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ids = [t['id'] for t in self.production['tracks']]

    def plan_sources(self, **extra) -> set[str]:
        plan = production.create_scaffold_plan({'genre': 'House', 'variant_id': 'club-version', **extra})
        return {c['source_track_id'] for c in plan['actions'][0]['copies']}

    def test_unidentifiable_names_scaffold_nothing_until_roles_are_remembered(self) -> None:
        with self.assertRaisesRegex(ValueError, 'No fingerprinted'):
            self.plan_sources()

    def test_remembered_roles_drive_planning_and_survive_a_restart(self) -> None:
        production.save_role_memory({'roles': dict(zip(self.ids, ['Kick', 'Bass', 'Hats', 'Chords']))})
        status = production.role_memory_status()
        self.assertEqual({'Kick', 'Bass', 'Hats', 'Chords'}, {v['role'] for v in status['remembered'].values()})
        self.assertEqual(set(self.ids), self.plan_sources())

    def test_reopened_set_with_new_ids_still_gets_its_roles(self) -> None:
        production.save_role_memory({'roles': dict(zip(self.ids, ['Kick', 'Bass', 'Hats', 'Chords']))})
        for t in self.production['tracks']:
            t['id'] = 'new-' + t['id']
        self.production['revision'] = 'r2'
        status = production.role_memory_status()
        self.assertEqual({'name'}, {v['matched_by'] for v in status['remembered'].values()})
        self.assertEqual({'new-' + i for i in self.ids}, self.plan_sources())

    def test_an_ignored_stem_is_left_out_even_if_its_name_would_have_matched(self) -> None:
        self.production['tracks'][0]['name'] = 'Kick'  # heuristics would pick this up...
        production.save_role_memory({'roles': {self.ids[0]: 'Ignore / Unknown'}})  # ...but you said ignore it
        with self.assertRaises(ValueError):  # nothing else is identifiable, so no sources at all
            self.plan_sources()

    def test_an_explicit_choice_in_the_request_beats_memory(self) -> None:
        production.save_role_memory({'roles': dict(zip(self.ids, ['Kick', 'Bass', 'Hats', 'Chords']))})
        sources = self.plan_sources(roles={self.ids[0]: 'Ignore / Unknown'})
        self.assertNotIn(self.ids[0], sources)

    def test_removed_and_added_tracks_are_reported_not_fatal(self) -> None:
        production.save_role_memory({'roles': dict(zip(self.ids, ['Kick', 'Bass', 'Hats', 'Chords']))})
        removed = self.production['tracks'].pop(3)
        self.production['tracks'].append(track('fresh', 'Brand new', 9, ttype='midi',
                                               mixer={'volume': .8, 'pan': 0, 'sends': []}, devices=[], routing='Main',
                                               arrangement_clips=[], session_clips=[]))
        self.production['revision'] = 'r3'
        status = production.role_memory_status()
        self.assertEqual(['Chords'], [o['role'] for o in status['orphaned']])
        self.assertEqual(['fresh'], status['new_tracks'])
        self.production['tracks'].pop()
        self.production['tracks'].append(removed)  # deletion undone: the role comes back
        self.assertEqual('Chords', production.role_memory_status()['remembered'][removed['id']]['role'])

    def test_an_unsaved_set_cannot_remember_and_says_why(self) -> None:
        self.production['set_path'] = ''
        status = production.role_memory_status()
        self.assertEqual('unsaved', status['reason'])
        with self.assertRaisesRegex(ValueError, 'Save the Live Set first'):
            production.save_role_memory({'roles': {self.ids[0]: 'Kick'}})

    def test_memory_is_per_set(self) -> None:
        production.save_role_memory({'roles': {self.ids[0]: 'Kick'}})
        self.production['set_path'] = '/Sets/another vibelton-working-copy.als'
        self.assertEqual({}, production.role_memory_status()['remembered'])

    def test_clear_forgets_everything(self) -> None:
        production.save_role_memory({'roles': {self.ids[0]: 'Kick'}})
        self.assertEqual({}, production.save_role_memory({'clear': True})['remembered'])

    def test_bad_payloads_are_rejected(self) -> None:
        for payload in ({}, {'roles': {}, 'clear': True}, {'roles': 'x'}, {'roles': {self.ids[0]: 'Nope'}}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                production.save_role_memory(payload)


if __name__ == '__main__':
    unittest.main()
