"""Local persistence and command boundary for Composition Lab."""
from __future__ import annotations

import copy
import json
import os
import threading
import time
import uuid
from pathlib import Path
from . import composition as score
from . import queue

ROOT = Path.home() / '.vibelton' / 'compositions'
LOCK = threading.RLock()


def read(path, default=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, allow_nan=False))
    os.replace(tmp, path)


def revisions():
    return sorted((ROOT / 'revisions').glob('*.json'))


def get_revision(revision=None):
    paths = revisions()
    if revision is None:
        return read(paths[-1]) if paths else {'revision': 0, 'composition': score.prepare(score.default_document()), 'created_at': None}
    if type(revision) is not int or revision < 1:
        raise ValueError('Invalid revision')
    result = read(ROOT / 'revisions' / ('%06d.json' % revision))
    if result is None:
        raise ValueError('Revision not found')
    return result


def overview():
    latest = get_revision()
    job_files = sorted((ROOT / 'jobs').glob('*.json'), key=lambda p: read(p)['created_at'])
    return {**latest, 'history': [{'revision': x['revision'], 'title': x['composition']['title'], 'created_at': x['created_at']} for x in (read(p) for p in revisions())],
            'live': queue.current_state(), 'jobs': [job_status(p.stem) for p in job_files[-30:]]}


def save(payload):
    with LOCK:
        latest = get_revision()
        if payload.get('base_revision') != latest['revision']:
            raise ValueError('This draft changed elsewhere. Reload before saving your edits.')
        doc = payload['composition']
        if payload.get('fit_duration'):
            doc = score.fit_duration(doc)
        doc = score.prepare(doc, latest['composition'] if latest['revision'] else None, payload.get('regenerate'))
        result = {'revision': latest['revision'] + 1, 'composition': doc, 'created_at': time.time()}
        write(ROOT / 'revisions' / ('%06d.json' % result['revision']), result)
        return {**result, 'compiled': score.compile_score(doc)}


def compile_revision(payload):
    result = get_revision(payload['revision'])
    return {'revision': result['revision'], **score.compile_score(result['composition'], payload.get('section_id'))}


def create_from_project(payload=None):
    payload = dict(payload or {})
    with LOCK:
        state = queue.current_state() or {}
        doc = score.project_document(state, payload)
        if payload.get('save_revision') is False:
            return {'revision': get_revision()['revision'], 'composition': doc, 'compiled': score.compile_score(doc)}
        latest = get_revision()
        result = {'revision': latest['revision'] + 1, 'composition': doc, 'created_at': time.time()}
        write(ROOT / 'revisions' / ('%06d.json' % result['revision']), result)
        return {**result, 'compiled': score.compile_score(doc)}


def generate_bass_companion_revision(payload=None):
    payload = dict(payload or {})
    with LOCK:
        latest = get_revision()
        base_doc = copy.deepcopy(payload.get('composition') or latest['composition'])
        target_sec_id = payload.get('section_id')
        bc_params = {
            'key': payload.get('key', base_doc.get('root_midi', 56)),
            'scale': str(payload.get('scale') or base_doc.get('mode') or 'minor'),
            'swing': float(payload.get('swing', base_doc.get('expression', {}).get('swing', 0.15))),
            'density': str(payload.get('density') or 'medium').lower(),
            'movement': str(payload.get('movement') or 'syncopated_hook').lower(),
            'lock_to_kick': payload.get('lock_to_kick', True) is not False,
        }
        if payload.get('lock_to_kick_beats') is not None:
            bc_params['lock_to_kick_beats'] = list(payload['lock_to_kick_beats'])
        elif base_doc.get('lock_to_kick_beats'):
            bc_params['lock_to_kick_beats'] = list(base_doc['lock_to_kick_beats'])

        updated_sections = []
        for s in base_doc['sections']:
            if target_sec_id and s['id'] != target_sec_id:
                continue
            if s.get('locked'):
                continue
            part = s.get('parts', {}).get('bass')
            if part and part.get('locked'):
                continue
            if 'bass' not in s.get('active_parts', []):
                s['active_parts'].append('bass')
            s['bass_companion'] = dict(bc_params)
            updated_sections.append(s['id'])

        if not updated_sections:
            raise ValueError('No unlocked bass parts available to update in the selected scope')

        doc = score.prepare(base_doc, latest['composition'] if latest['revision'] else None, {
            'sections': updated_sections,
            'roles': ['bass'],
        })
        if payload.get('save_revision') is False:
            return {'revision': latest['revision'], 'composition': doc, 'compiled': score.compile_score(doc), 'updated_sections': updated_sections}
        result = {'revision': latest['revision'] + 1, 'composition': doc, 'created_at': time.time()}
        write(ROOT / 'revisions' / ('%06d.json' % result['revision']), result)
        return {**result, 'compiled': score.compile_score(doc), 'updated_sections': updated_sections}


def live_ready():
    state = queue.current_state()
    if not state.get('connected') or time.time() - state.get('updated_at', 0) > 10:
        raise ValueError('Ableton is disconnected or its heartbeat is stale')
    if 'composition_v1' not in state.get('capabilities', []):
        raise ValueError('Install the updated Vibelton bridge and restart Live before applying compositions')
    errors = state.get('arrangement_errors') or (state.get('production') or {}).get('arrangement_errors')
    group_only_errors = isinstance(errors, list) and bool(errors) and all(
        isinstance(err, dict) and err.get('is_group') is True for err in errors
    )
    if not state.get('arrangement_readable') and not group_only_errors:
        raise ValueError('This Live version does not expose Arrangement clips for safe placement and verification')
    return state


def apply(payload):
    with LOCK:
        if payload.get('working_copy_confirmed') is not True:
            raise ValueError('Save a working copy of your Live Set, then confirm it before applying')
        result = get_revision(payload['revision'])
        doc = result['composition']
        compiled = score.compile_score(doc, payload.get('section_id'))
        state = live_ready()
        key = '%s:%s' % (result['revision'], payload.get('section_id') or 'full')
        for p in (ROOT / 'jobs').glob('*.json'):
            previous = read(p)
            if previous['application_key'] == key:
                raise ValueError('This revision/section has already been submitted. Check its result; save a new revision for another version.')
            status = job_status(p.stem)
            if status['status'] == 'Queued' and previous.get('session_id') == state['session_id']:
                raise ValueError('Wait for the queued composition to finish before submitting another')
        live_tracks = {t['id']: t for t in state['tracks']}
        selected = {s['id']: s for s in doc['sections']}
        start = float(state['arrangement_end'])
        start = 0 if start == 0 else (int(start / 4) + 2) * 4
        if payload.get('region_id'):
            from . import samples
            region_id = str(uuid.UUID(payload['region_id']))
            region = read(samples.REGIONS / (region_id + '.json'))
            if not region or region['session_id'] != state['session_id'] or region['set_path'] != state.get('set_path'):
                raise ValueError('Reserved prototype range belongs to another Set or session')
            if compiled['total_beats'] > region['length_beats']:
                raise ValueError('Composition exceeds the reserved prototype range')
            start = region['start_beat']
            # The bridge repeats the all-track collision check before writing.
            if any(c['start_beat'] < start + compiled['total_beats'] and c['end_beat'] > start
                   for t in state['tracks'] for c in t.get('arrangement_clips', [])):
                raise ValueError('Reserved prototype range is occupied; MIDI must be written before layering audio')
        clips, refs = [], {}
        for i, section in enumerate(compiled['sections']):
            source = selected[section['id']]
            by_track = {}
            for role in source['active_parts']:
                ref = doc['assignments'][role]
                if not ref:
                    raise ValueError('Assign an existing MIDI instrument to %s before applying' % role)
                track = live_tracks.get(ref['id'])
                if ref['session_id'] != state['session_id'] or not track or track['name'] != ref['name'] or track['type'] != 'midi':
                    raise ValueError('Track assignment changed for %s; refresh and reassign it' % role)
                routed_to = track.get('routed_to', '').strip()
                if not track.get('has_audio_output') and routed_to in ('', 'No Output', 'None', 'Main', 'Master'):
                    raise ValueError('%s needs an instrument or MIDI output routing' % track['name'])
                refs[ref['id']] = ref
                if role not in source['parts']:
                    raise ValueError('Save generated material for %s first' % role)
                by_track.setdefault(ref['id'], []).extend(source['parts'][role]['notes'])
            for track_id, notes in by_track.items():
                clips.append({'track_id': track_id, 'scene_index': state['scene_count'] + i,
                              'name': 'CL r%d · %s' % (result['revision'], section['name']),
                              'notes': sorted(notes, key=lambda n: (n['start'], n['pitch'])),
                              'metre': section['metre'], 'length_beats': section['length_beats'],
                              'start_beat': start + section['start_beat']})
        job_id = str(uuid.uuid4())
        action = {'type': 'composition_apply', 'job_id': job_id, 'session_id': state['session_id'],
                  'tracks': list(refs.values()), 'clips': clips, 'bpm': doc['bpm'],
                  'start_beat': start, 'total_beats': compiled['total_beats'],
                  'scene_count': state['scene_count'], 'preview': bool(payload.get('section_id'))}
        markers = [{'beat': start + s['start_beat'], 'metre': s['metre'], 'section': s['name']} for s in compiled['sections']]
        # Reserve before enqueue; uncertain failures must never silently resubmit.
        job = {'id': job_id, 'revision': result['revision'], 'application_key': key, 'status': 'Queued',
               'session_id': state['session_id'], 'created_at': time.time(), 'markers': markers,
               'markers_verified': False, 'compiled': compiled, 'start_beat': start, 'preview': action['preview']}
        write(ROOT / 'jobs' / (job_id + '.json'), job)
        try:
            command = queue.enqueue([action], source='composition')
            job['command_id'] = command['id']
            write(ROOT / 'jobs' / (job_id + '.json'), job)
        except Exception:
            job['status'] = 'Failed'
            job['error'] = 'Queue submission uncertain; inspect bridge results before creating a new revision.'
            write(ROOT / 'jobs' / (job_id + '.json'), job)
            raise
        return job


def job_status(job_id):
    try:
        uuid.UUID(job_id)
    except (ValueError, TypeError):
        raise ValueError('Invalid execution ID')
    job = read(ROOT / 'jobs' / (job_id + '.json'))
    if not job:
        raise ValueError('Execution not found')
    execution = read(queue.QUEUE_DIR / 'composition-executions' / (job_id + '.json'))
    if execution:
        job['execution'] = execution
        if execution['status'] == 'Applied':
            job['status'] = 'Verified' if job['markers_verified'] and execution.get('readback_verified') else 'Applied'
        else:
            job['status'] = execution['status']
    state = queue.current_state()
    if job['status'] == 'Queued' and state.get('session_id') and job['session_id'] != state['session_id']:
        job['status'] = 'Interrupted'
        job['error'] = 'Live restarted before execution was acknowledged. This command will not be retried automatically.'
    return job


def verify_markers(payload):
    with LOCK:
        job = job_status(payload['job_id'])
        if job['status'] not in ('Applied', 'Verified') or not job.get('execution', {}).get('readback_verified'):
            raise ValueError('Clip readback must pass before verifying metre markers')
        if payload.get('markers') != job['markers'] or not str(payload.get('evidence', '')).strip():
            raise ValueError('Provide the exact marker list and an Ableton UI verification note')
        state = live_ready()
        if state['session_id'] != job['session_id']:
            raise ValueError('Live session changed; marker verification belongs to the original session')
        job['markers_verified'] = True
        job['marker_evidence'] = str(payload['evidence'])[:4000]
        job['verified_at'] = time.time()
        write(ROOT / 'jobs' / (job['id'] + '.json'), job)
        return job_status(job['id'])
