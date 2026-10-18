"""Shared fake Remote Script for rollback/section tests.

Mimics the bridge's apply/rollback strictness on ``test.state['production']`` and writes the
execution result file the server reads back.
"""
from __future__ import annotations

import copy
import hashlib
import json

from vibelton import production


def clip(start, end, fp, name='Loop'):
    return {'name': name, 'start_beat': float(start), 'end_beat': float(end), 'length': float(end - start),
            'metre': [4, 4], 'fingerprint': fp}


class FakeLive:
    """Mimics the Remote Script's apply/rollback strictness on a production state."""

    def __init__(self, test: object) -> None:
        self.t = test
        self.fail_after: int | None = None

    def seal(self) -> None:
        prod = self.t.state['production']
        prod['arrangement_end'] = max([0.0] + [c['end_beat'] for t in prod['tracks'] for c in t['arrangement_clips']])
        body = {k: v for k, v in prod.items() if k != 'revision'}
        prod['revision'] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()

    def process(self, command_index: int) -> dict:
        action = self.t.enqueued[command_index]['actions'][0]
        job_id, result = action['job_id'], {'job_id': action['job_id']}
        prod = self.t.state['production']
        tracks = {t['id']: t for t in prod['tracks']}
        try:
            for item in action['actions']:
                if item['type'] == 'apply_arrangement_copies':
                    created = []
                    for spec in item['copies']:
                        if self.fail_after is not None and len(created) >= self.fail_after:
                            raise RuntimeError('simulated failure')
                        track = tracks[spec['source_track_id']]
                        source = next(c for c in track['arrangement_clips']
                                      if c['start_beat'] == spec['source_start_beat'])
                        length = source['end_beat'] - source['start_beat']
                        track['arrangement_clips'].append(clip(spec['destination_beat'], spec['destination_beat'] + length,
                                                               spec['source_fingerprint'], source['name']))
                        created.append(dict(spec))
                        result.update(created_copies=copy.deepcopy(created))
                    # Native cues (only requested when the capability was advertised).
                    for cue in item.get('locators', []):
                        if any(abs(l['time'] - cue['time']) < 1e-5 for l in prod['locators']):
                            raise RuntimeError('A locator already exists at the requested time')
                    prod['locators'] = sorted(prod['locators'] + [dict(c) for c in item.get('locators', [])],
                                              key=lambda l: l['time'])
                    result.update(created_locators=copy.deepcopy(item.get('locators', [])))
                elif item['type'] == 'apply_session_to_arrangement_copies':
                    created = []
                    for spec in item['copies']:
                        if self.fail_after is not None and len(created) >= self.fail_after:
                            raise RuntimeError('simulated failure')
                        track = tracks[spec['track_id']]
                        source = next(c for c in track['session_clips'] if c['scene_index'] == spec['source_scene_index'])
                        if source['fingerprint'] != spec['source_fingerprint']:
                            raise RuntimeError('Session source clip is missing, changed, or cannot be copied to arrangement')
                        track['arrangement_clips'].append(clip(spec['destination_beat'], spec['destination_beat'] + source['length'],
                                                               spec['source_fingerprint'], source['name']))
                        created.append(dict(spec))
                        result.update(created_copies=copy.deepcopy(created))
                elif item['type'] == 'rollback_session_to_arrangement_copies':
                    targets = []
                    for spec in item['copies']:
                        track = tracks[spec['track_id']]
                        source = [c for c in track['session_clips'] if c['scene_index'] == spec['source_scene_index']]
                        found = [c for c in track['arrangement_clips'] if c['start_beat'] == spec['destination_beat']
                                 and c['fingerprint'] == spec['source_fingerprint']]
                        if len(source) != 1 or source[0]['fingerprint'] != spec['source_fingerprint']:
                            raise RuntimeError('Expected Session source clip is missing or changed')
                        if len(found) != 1:
                            raise RuntimeError('Expected session-to-arrangement copy is missing or changed')
                        targets.append((track, found[0]))
                    for track, found in targets:
                        track['arrangement_clips'].remove(found)
                    self.seal()
                    if production._observable_rollback_revision(prod) != item['expected_post_rollback_observable_revision']:
                        raise RuntimeError('Session-to-arrangement rollback did not restore the exact original state')
                    result.update(deleted_copies=len(targets))
                elif item['type'] == 'rollback_arrangement_copies':
                    targets = []
                    for spec in item['copies']:
                        track = tracks[spec['source_track_id']]
                        found = [c for c in track['arrangement_clips'] if c['start_beat'] == spec['destination_beat']
                                 and c['fingerprint'] == spec['source_fingerprint']]
                        sources = [c for c in track['arrangement_clips'] if c['start_beat'] == spec['source_start_beat']]
                        if len(found) != 1 or len(sources) != 1 or sources[0]['fingerprint'] != spec['source_fingerprint']:
                            raise RuntimeError('Expected arrangement copy is missing or changed')
                        targets.append((track, found[0]))
                    for cue in item['locators']:
                        if cue not in prod['locators']:
                            raise RuntimeError('Arrangement locators are missing or changed')
                    for track, found in targets:
                        track['arrangement_clips'].remove(found)
                    prod['locators'] = [l for l in prod['locators'] if l not in item['locators']]
                    self.seal()
                    if production._observable_rollback_revision(prod) != item['expected_post_rollback_observable_revision']:
                        raise RuntimeError('Arrangement rollback did not restore the exact original state')
                    result.update(deleted_copies=len(targets))
            result['status'] = 'Applied'
        except Exception as exc:
            result.update(status='Partial failure' if result.get('created_copies') else 'Failed', error=str(exc))
        self.seal()
        result['post_revision'] = prod['revision']
        path = self.t.root / 'queue' / 'production-executions' / (job_id + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result))
        return result
