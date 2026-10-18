"""Local loop catalogue and durable, session-bound audio import jobs."""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path
from . import queue
from .composition_service import read, write

SAMPLE_ROOT = Path.home() / 'Music' / 'LOOP PACKS'
def _configured_sample_roots():
    """Extra approved sample folders from ~/.vibelton/config.json ("extra_sample_roots")."""
    try:
        config = json.loads((Path.home() / '.vibelton' / 'config.json').read_text(encoding='utf-8'))
        items = config.get('extra_sample_roots', []) if isinstance(config, dict) else []
    except (OSError, ValueError):
        items = []
    return tuple(Path(item).expanduser() for item in items if isinstance(item, str) and item.strip())


EXTRA_SAMPLE_ROOTS = (Path.home() / 'Music' / 'Shadow Samples - UK Bass Vol. 1', *_configured_sample_roots())
ROOT = Path.home() / '.vibelton' / 'sample-jobs'
REGIONS = Path.home() / '.vibelton' / 'sample-regions'
EXTENSIONS = {'.wav', '.aif', '.aiff', '.flac', '.mp3', '.ogg', '.m4a'}
LOCK = threading.RLock()


def approved_roots():
    """Folders audio may be read from: the loop-pack root, the built-in extra root and any configured ones."""
    return [SAMPLE_ROOT, *EXTRA_SAMPLE_ROOTS]


def source_path(value):
    path = Path(value).expanduser().resolve(strict=True)
    if not any(path.is_relative_to(root.resolve()) for root in (SAMPLE_ROOT, *EXTRA_SAMPLE_ROOTS)) or not path.is_file() or path.suffix.lower() not in EXTENSIONS:
        raise ValueError('Choose an audio file inside an approved sample library')
    return path


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def catalogue(query='', offset=0, limit=100):
    if not 0 <= offset or not 1 <= limit <= 500:
        raise ValueError('Invalid catalogue page')
    files, errors = [], []
    def on_error(exc):
        errors.append(str(exc))
    import os
    for root in (SAMPLE_ROOT, *EXTRA_SAMPLE_ROOTS):
        if not root.exists():
            continue
        for directory, dirs, names in os.walk(root, onerror=on_error, followlinks=False):
            dirs[:] = [name for name in dirs if name != '.vibelton-imports']
            for name in names:
                path = Path(directory) / name
                relative = str(path.relative_to(root))
                label = relative if root == SAMPLE_ROOT else root.name + '/' + relative
                if path.suffix.lower() not in EXTENSIONS or query.lower() not in label.lower():
                    continue
                try:
                    path = source_path(path)
                    # Do not follow aliases from one catalogue root to another.
                    if not path.is_relative_to(root.resolve()):
                        continue
                    files.append({'path': str(path), 'relative_path': label,
                                  'bytes': path.stat().st_size})
                except (ValueError, OSError):
                    continue
    files.sort(key=lambda item: item['relative_path'].casefold())
    return {'root': str(SAMPLE_ROOT), 'roots': [str(root) for root in (SAMPLE_ROOT, *EXTRA_SAMPLE_ROOTS)], 'total': len(files), 'offset': offset,
            'files': files[offset:offset + limit], 'errors': errors,
            'audio_auditioned': False}


def bridge_source(info):
    """Stage an identical copy for the loaded bridge's existing library guard."""
    source = source_path(info['path'])
    if source.is_relative_to(SAMPLE_ROOT.resolve()):
        return str(source)
    directory = SAMPLE_ROOT / '.vibelton-imports'
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.resolve().is_relative_to(SAMPLE_ROOT.resolve()):
        raise ValueError('Sample staging directory is outside the bridge library')
    destination = directory / (info['sha256'] + source.suffix.lower())
    if destination.exists():
        if destination.is_symlink() or fingerprint(destination) != info['sha256']:
            raise ValueError('Staged sample does not match the approved source')
    else:
        import shutil
        temporary = directory / (str(uuid.uuid4()) + '.tmp')
        try:
            shutil.copyfile(source, temporary)
            if fingerprint(temporary) != info['sha256']:
                raise ValueError('Sample changed while staging')
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return str(destination)


def _ffprobe_bin() -> str:
    import os
    import shutil
    found = shutil.which('ffprobe')
    if found:
        return found
    for candidate in ('/opt/homebrew/bin/ffprobe', '/usr/local/bin/ffprobe'):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return 'ffprobe'


def _arrangement_readable(state: dict) -> bool:
    prod = state.get('production') or {}
    if state.get('arrangement_readable') and prod.get('arrangement_readable'):
        return True
    errors = state.get('arrangement_errors') or prod.get('arrangement_errors')
    return isinstance(errors, list) and bool(errors) and all(
        isinstance(err, dict) and err.get('is_group') is True for err in errors
    )


def metadata(value, target_key=None):
    from . import audio_intelligence
    path = source_path(value)
    result = subprocess.run([_ffprobe_bin(), '-v', 'error', '-show_entries',
                             'format=duration:stream=codec_type,codec_name,sample_rate,channels,duration',
                             '-of', 'json', str(path)], capture_output=True, text=True, timeout=15, check=True)
    data = json.loads(result.stdout)
    audio = next((stream for stream in data.get('streams', []) if stream.get('codec_type') == 'audio'), None)
    if audio is None:
        raise ValueError('File has no audio stream')
    duration = float(audio.get('duration', data.get('format', {}).get('duration', 0)))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('File has no finite positive duration')
    hints = [int(n) for n in re.findall(r'(?<!\d)([7-9]\d|1\d\d|200)(?!\d)', path.stem)]
    sha = fingerprint(path)
    intel = audio_intelligence.analyse_audio_file(path, target_key=target_key, sha256=sha)
    return {'path': str(path), 'sha256': sha, 'duration_seconds': duration,
            'sample_rate': int(audio['sample_rate']), 'channels': int(audio['channels']),
            'codec': audio['codec_name'], 'filename_bpm_hints': hints,
            'bpm_measured': False, 'audio_auditioned': False,
            'spectral_bands': intel['spectral_bands'],
            'band_energy': intel['band_energy'],
            'onset_density': intel['onset_density'],
            'pitch_analysis': intel['pitch_analysis'],
            'audio_intelligence': intel}


def _infer_project_context(payload: dict | None = None) -> tuple[float, str | None, list[str]]:
    payload = payload or {}
    state = queue.current_state() or {}
    target_bpm = float(payload.get('target_bpm') or state.get('tempo') or 119.0)
    target_key = payload.get('target_key')
    occupied_bands = list(payload.get('occupied_bands') or [])

    prod_tracks = (state.get('production') or {}).get('tracks') or []
    if not target_key or not occupied_bands:
        try:
            from . import song_sketch
            sketch = song_sketch.infer(state)
            if not target_key:
                for tr in sketch.get('tracks', []):
                    if tr.get('key_hint'):
                        target_key = tr['key_hint']
                        break
            if not occupied_bands:
                roles_active = {
                    tr.get('suggested_role')
                    for tr in sketch.get('tracks', [])
                    if (tr.get('arrangement_clip_count', 0) > 0 or tr.get('session_clip_count', 0) > 0)
                }
                if 'Bass' in roles_active or 'Kick' in roles_active:
                    occupied_bands.append('low')
                if 'Chords' in roles_active or 'Vocal' in roles_active or 'Percussion' in roles_active:
                    occupied_bands.append('low_mid')
                if 'Vocal' in roles_active or 'Lead' in roles_active:
                    occupied_bands.append('mid')
        except Exception:
            if prod_tracks and not occupied_bands:
                occupied_bands = ['low_mid']
    return target_bpm, target_key, occupied_bands


def recommend_samples(payload: dict | None = None) -> dict:
    from . import audio_intelligence
    payload = dict(payload or {})
    role = str(payload.get('role') or 'percussion').strip()
    query = str(payload.get('query') or '').strip()
    limit = max(1, min(50, int(payload.get('limit') or 10)))
    max_candidates = max(limit, min(60, int(payload.get('max_candidates') or 25)))
    target_bpm, target_key, occupied_bands = _infer_project_context(payload)

    candidate_paths = payload.get('candidate_paths')
    if isinstance(candidate_paths, list) and candidate_paths:
        raw_files = [{'path': str(source_path(p)), 'relative_path': Path(p).name} for p in candidate_paths]
    else:
        cat = catalogue(query=query, offset=0, limit=500)
        raw_files = cat.get('files', [])
        if not query and len(raw_files) > max_candidates:
            role_kw_map = {
                'bass': ('bass', 'sub', '808', 'moog', 'reese'),
                'top_loop': ('top', 'drum', 'drmlp', 'break', 'hat', 'loop'),
                'percussion': ('shaker', 'perc', 'top', 'hat', 'drum', 'drmlp', 'loop'),
                'vocal': ('vox', 'vocal', 'voice', 'chop'),
                'fx': ('fx', 'riser', 'impact', 'atmos', 'sweep', 'tex'),
                'chords': ('chord', 'synth', 'stab', 'pad', 'keys', 'electro'),
            }
            kws = role_kw_map.get(role.lower(), ())
            if kws:
                prioritized = [f for f in raw_files if any(k in f['relative_path'].lower() for k in kws)]
                others = [f for f in raw_files if f not in prioritized]
                raw_files = (prioritized + others)[:max_candidates]
            else:
                raw_files = raw_files[:max_candidates]
        else:
            raw_files = raw_files[:max_candidates]

    recommendations = []
    for item in raw_files:
        try:
            meta = metadata(item['path'], target_key=target_key)
            score_info = audio_intelligence.score_sample_candidate(
                meta,
                role=role,
                target_bpm=target_bpm,
                target_key=target_key,
                occupied_bands=occupied_bands,
            )
            recommendations.append({
                'path': meta['path'],
                'relative_path': item.get('relative_path') or Path(meta['path']).name,
                'duration_seconds': meta['duration_seconds'],
                'filename_bpm_hints': meta['filename_bpm_hints'],
                'spectral_bands': meta['spectral_bands'],
                'onset_density': meta['onset_density'],
                'pitch_analysis': meta['pitch_analysis'],
                'score': score_info['total_score'],
                'score_breakdown': score_info,
                'tuning_plan': score_info['tuning_plan'],
            })
        except Exception:
            continue

    recommendations.sort(key=lambda r: (-r['score'], r['relative_path'].casefold()))
    return {
        'role': role,
        'target_bpm': target_bpm,
        'target_key': target_key,
        'occupied_bands': occupied_bands,
        'total_evaluated': len(recommendations),
        'recommendations': recommendations[:limit],
    }


def quick_shuffle(payload: dict | None = None) -> dict:
    payload = dict(payload or {})
    target_bpm, target_key, occupied_bands = _infer_project_context(payload)
    locked_slots = dict(payload.get('locked_slots') or {})
    variation_index = int(payload.get('variation_index') or payload.get('seed') or 0)
    candidate_paths = payload.get('candidate_paths')

    slot_specs = payload.get('slots') or [
        {'slot_id': 'top_loop', 'label': 'Drum / Top Loop', 'role': 'top_loop'},
        {'slot_id': 'percussion', 'label': 'Percussion / Shaker', 'role': 'percussion'},
        {'slot_id': 'bass_synth', 'label': 'Bass / Synth', 'role': 'bass'},
        {'slot_id': 'texture_fx', 'label': 'Texture / FX', 'role': 'fx'},
    ]

    used_paths: set[str] = set()
    running_occupied = list(occupied_bands)

    # First register any locked slots so unlocked slots avoid clashing with them
    resolved_locked: dict[str, dict] = {}
    for slot_id, locked_val in locked_slots.items():
        if not locked_val:
            continue
        locked_path = locked_val.get('path') if isinstance(locked_val, dict) else str(locked_val)
        if not locked_path:
            continue
        try:
            meta = metadata(locked_path, target_key=target_key)
            used_paths.add(meta['path'])
            dom = (meta.get('spectral_bands') or {}).get('dominant_band')
            if dom and dom not in running_occupied:
                running_occupied.append(dom)
            resolved_locked[slot_id] = {
                'path': meta['path'],
                'relative_path': Path(meta['path']).name,
                'duration_seconds': meta['duration_seconds'],
                'filename_bpm_hints': meta['filename_bpm_hints'],
                'spectral_bands': meta['spectral_bands'],
                'onset_density': meta['onset_density'],
                'pitch_analysis': meta['pitch_analysis'],
                'locked': True,
            }
        except Exception:
            continue

    slots_out = []
    for idx, spec in enumerate(slot_specs):
        slot_id = spec.get('slot_id') or f'slot_{idx}'
        role = spec.get('role') or 'percussion'
        label = spec.get('label') or role.title()
        if slot_id in resolved_locked:
            slots_out.append({
                'slot_id': slot_id,
                'label': label,
                'role': role,
                'locked': True,
                'selected': resolved_locked[slot_id],
            })
            continue

        rec = recommend_samples({
            'role': role,
            'target_bpm': target_bpm,
            'target_key': target_key,
            'occupied_bands': running_occupied,
            'limit': 15,
            'max_candidates': 30,
            **({'candidate_paths': candidate_paths} if candidate_paths else {}),
        })
        pool = [c for c in rec.get('recommendations', []) if c['path'] not in used_paths]
        if not pool:
            pool = rec.get('recommendations', [])
        selected = None
        if pool:
            pick_idx = (variation_index + idx) % min(len(pool), max(1, min(4, len(pool))))
            selected = pool[pick_idx]
            used_paths.add(selected['path'])
            dom = (selected.get('spectral_bands') or {}).get('dominant_band')
            if dom and dom not in running_occupied:
                running_occupied.append(dom)
        slots_out.append({
            'slot_id': slot_id,
            'label': label,
            'role': role,
            'locked': False,
            'selected': selected,
        })

    return {
        'target_bpm': target_bpm,
        'target_key': target_key,
        'occupied_bands': running_occupied,
        'slots': slots_out,
    }



def finite(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid ' + label)
    return value


def validate_settings(settings):
    allowed = {'warping', 'looping', 'start_marker', 'end_marker', 'loop_start', 'loop_end',
               'pitch_coarse', 'pitch_fine', 'gain', 'warp_mode'}
    if not isinstance(settings, dict) or set(settings) - allowed:
        raise ValueError('Unknown audio clip setting')
    for key in ('warping', 'looping'):
        if key in settings and type(settings[key]) is not bool:
            raise ValueError('Invalid ' + key)
    for key, bounds in {'start_marker': (0, 1576800), 'end_marker': (.001, 1576800),
                        'loop_start': (0, 1576800), 'loop_end': (.001, 1576800),
                        'pitch_coarse': (-48, 48), 'pitch_fine': (-50, 49), 'gain': (0, 1),
                        'warp_mode': (0, 10)}.items():
        if key in settings:
            finite(settings[key], *bounds, key)
    for key in ('pitch_coarse', 'warp_mode'):
        if key in settings and type(settings[key]) is not int:
            raise ValueError('Invalid ' + key)
    for left, right in (('start_marker', 'end_marker'), ('loop_start', 'loop_end')):
        if left in settings and right in settings and settings[left] >= settings[right]:
            raise ValueError(left + ' must precede ' + right)
    if settings.get('warping') is False and settings.get('looping'):
        raise ValueError('Unwarped audio cannot loop')
    return dict(settings)


def reserve_region(payload):
    """Reserve a fresh, initially empty prototype range without mutating Live."""
    with LOCK:
        state = queue.current_state()
        if not state.get('connected') or time.time() - (state.get('updated_at') or 0) > 10:
            raise ValueError('Live heartbeat is stale or disconnected')
        if not _arrangement_readable(state):
            raise ValueError('Resolve Arrangement readback before reserving a range')
        if payload.get('working_copy_confirmed') is not True or not payload.get('expected_set_path') or payload['expected_set_path'] != state.get('set_path'):
            raise ValueError('Confirm the active named working copy')
        if payload.get('session_id') != state['session_id'] or payload.get('source_revision') != state['production']['revision']:
            raise ValueError('Session or material changed; inspect again')
        start = finite(payload.get('start_beat'), 0, 1576800, 'range start')
        length = finite(payload.get('length_beats'), .001, 3600, 'range length')
        if start < state.get('arrangement_end', 0) + 4 or start + length > 1576800:
            raise ValueError('Prototype range must be beyond the original Arrangement')
        region = {'id':str(uuid.uuid4()),'session_id':state['session_id'], 'set_path':state['set_path'],
                  'start_beat':start,'length_beats':length,'original_end':state['arrangement_end'],
                  'created_at':time.time(),'source_revision':state['production']['revision']}
        write(REGIONS / (region['id'] + '.json'),region)
        return region


def apply(payload):
    with LOCK:
        allowed = {'session_id', 'source_revision', 'expected_set_path', 'working_copy_confirmed',
                   'path', 'track_id', 'scene_index', 'name', 'settings', 'arrangement_beat', 'source_bpm', 'region_id'}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise ValueError('Unknown sample import field')
        state = queue.current_state()
        if not state.get('connected') or time.time() - (state.get('updated_at') or 0) > 10:
            raise ValueError('Live heartbeat is stale or disconnected')
        if 'audio_import_v1' not in state.get('capabilities', []):
            raise ValueError('Updated audio bridge must be loaded before importing')
        if not _arrangement_readable(state):
            raise ValueError('Resolve Arrangement readback errors before importing')
        if payload.get('working_copy_confirmed') is not True:
            raise ValueError('Confirm a separate named working copy first')
        if not payload.get('expected_set_path') or payload['expected_set_path'] != state.get('set_path'):
            raise ValueError('Active Set path does not match the working copy')
        project = state['production']
        if payload.get('session_id') != state['session_id'] or payload.get('source_revision') != project['revision']:
            raise ValueError('Live session or material changed; inspect again')
        target = next((t for t in project['tracks'] if t['id'] == payload.get('track_id')), None)
        if not target or target['type'] != 'audio' or target.get('is_group') or not target.get('audio_import_supported'):
            raise ValueError('Choose a non-group audio track with audio import support')
        scene = payload.get('scene_index')
        if type(scene) is not int or scene != state['scene_count']:
            raise ValueError('Import must append exactly one new scene')
        name = payload.get('name')
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError('Supply a short clip name')
        settings = validate_settings(payload.get('settings', {}))
        if 'warping' not in settings:
            raise ValueError('Specify warping explicitly so marker units are unambiguous')
        region = None
        if 'arrangement_beat' in payload:
            if settings.get('warping') is not True:
                raise ValueError('Arrangement imports require explicit warping=true; unwarped imports are Session-only')
            beat = finite(payload['arrangement_beat'], 0, 1576800, 'Arrangement position')
            if payload.get('region_id'):
                region_id = str(uuid.UUID(payload['region_id']))
                region = read(REGIONS / (region_id + '.json'))
                if not region or region['session_id'] != state['session_id'] or region['set_path'] != state['set_path']:
                    raise ValueError('Prototype range belongs to another Set or session')
                if not region['start_beat'] <= beat < region['start_beat'] + region['length_beats']:
                    raise ValueError('Audio destination is outside the prototype range')
            elif beat < state.get('arrangement_end', 0) + 4:
                raise ValueError('Choose a fresh range or reserve a prototype range first')
        if settings.get('warping') is True:
            finite(payload.get('source_bpm'), 40, 240, 'confirmed source BPM')
        info = metadata(payload['path'])
        maximum = info['duration_seconds'] * (payload['source_bpm'] / 60 if settings.get('warping') else 1)
        if settings.get('warping') in (True, False):
            if any(settings.get(key, 0) > maximum + .001 for key in ('start_marker','end_marker','loop_start','loop_end')):
                raise ValueError('Audio marker exceeds the measured source duration')
        for path in ROOT.glob('*.json'):
            if job_status(path.stem)['status'] == 'Queued':
                raise ValueError('Wait for the pending sample job')
        job_id = str(uuid.uuid4())
        action = {**payload, 'type': 'audio_import', 'job_id': job_id, 'path': bridge_source(info),
                  'sha256': info['sha256'], 'duration_seconds': info['duration_seconds'],
                  'settings': settings, 'target_name': target['name'], 'region':region}
        job = {'id': job_id, 'status': 'Queued', 'session_id': state['session_id'],
               'created_at': time.time(), 'action': action, 'source': info}
        write(ROOT / (job_id + '.json'), job)
        try:
            job['command_id'] = queue.enqueue([action], source='samples')['id']
            write(ROOT / (job_id + '.json'), job)
        except Exception:
            job['status'] = 'Failed'
            job['error'] = 'Queue submission uncertain; inspect execution before resubmitting.'
            write(ROOT / (job_id + '.json'), job)
            raise
        return job


def _resolve_sample_path(raw_val: str) -> Path:
    if not raw_val or not str(raw_val).strip():
        raise ValueError('Provide a path or relative_path to import')
    raw_str = str(raw_val).strip()
    p = Path(raw_str).expanduser()
    if p.is_absolute() and p.exists():
        return source_path(p)
    for root in (SAMPLE_ROOT, *EXTRA_SAMPLE_ROOTS):
        cand = root / raw_str
        if cand.exists():
            return source_path(cand)
        if raw_str.startswith(root.name + '/'):
            sub = raw_str[len(root.name) + 1:]
            cand2 = root / sub
            if cand2.exists():
                return source_path(cand2)
    return source_path(raw_str)


def calculate_smart_tuning(
    sample_key: str | int | dict | None,
    target_key: str | None,
    cents_offset: float = 0.0,
) -> dict[str, int]:
    from . import audio_intelligence
    return audio_intelligence.calculate_smart_tuning(sample_key, target_key, cents_offset=cents_offset)


def import_shuffled_slot(payload: dict) -> dict:
    """Smart 1-click import for a Loop Finder slot with auto-track selection and KeyScope cent tuning."""
    with LOCK:
        payload = dict(payload or {})
        state = queue.current_state() or {}
        if not state.get('connected') or time.time() - (state.get('updated_at') or 0) > 10:
            raise ValueError('Live heartbeat is stale or disconnected')
        if payload.get('working_copy_confirmed') is not True:
            raise ValueError('Confirm a separate named working copy first')

        project = state.get('production') or {}
        tracks = project.get('tracks') or []
        track_id = payload.get('track_id') or payload.get('target_track_id')
        if not track_id or track_id == 'auto':
            audio_tracks = [
                t for t in tracks
                if t.get('type') == 'audio' and not t.get('is_group') and t.get('audio_import_supported')
            ]
            empty_audio = [
                t for t in audio_tracks
                if not t.get('arrangement_clips') and not t.get('session_clips') and not t.get('clips')
            ]
            chosen_track = empty_audio[0] if empty_audio else (audio_tracks[0] if audio_tracks else None)
            if not chosen_track:
                raise ValueError('No compatible audio track with audio_import_supported found in the open Set')
            track_id = chosen_track['id']
        else:
            chosen_track = next((t for t in tracks if t.get('id') == track_id), None)
            if not chosen_track or chosen_track.get('type') != 'audio' or chosen_track.get('is_group') or not chosen_track.get('audio_import_supported'):
                raise ValueError('Choose a non-group audio track with audio import support')

        raw_path = payload.get('path') or payload.get('relative_path')
        resolved_path = _resolve_sample_path(raw_path)

        target_key = payload.get('target_key')
        if not target_key:
            _, target_key, _ = _infer_project_context(payload)
        auto_tune = payload.get('auto_tune', True) is not False

        info = metadata(str(resolved_path), target_key=target_key)
        pitch_info = info.get('pitch_analysis') or {}

        hints = info.get('filename_bpm_hints') or []
        intel_bpm = (info.get('audio_intelligence') or {}).get('tempo_estimate_bpm')
        raw_bpm = payload.get('source_bpm') or (hints[0] if hints else None) or intel_bpm or state.get('tempo') or 120.0
        source_bpm = max(40.0, min(240.0, float(raw_bpm)))

        if auto_tune:
            sample_key_source = pitch_info if pitch_info.get('detected') else (payload.get('sample_key') or payload.get('key') or pitch_info)
            smart = calculate_smart_tuning(
                sample_key_source,
                target_key,
                cents_offset=float(pitch_info.get('cents_offset') or 0.0),
            )
            coarse = int(pitch_info.get('recommended_pitch_coarse') if pitch_info.get('recommended_pitch_coarse') is not None else smart['pitch_coarse'])
            fine = float(pitch_info.get('recommended_pitch_fine') if pitch_info.get('recommended_pitch_fine') is not None else smart['pitch_fine'])
        else:
            coarse = 0
            fine = 0.0
        coarse = max(-48, min(48, coarse))
        fine = max(-50.0, min(49.0, fine))

        slot_role = str(payload.get('slot_id') or payload.get('role') or payload.get('category') or '').lower()
        is_fx_oneshot = slot_role in ('fx', 'texture_fx', 'oneshot', 'one_shot') or 'fx' in slot_role
        default_looping = not is_fx_oneshot
        if 'looping' in payload and payload['looping'] is not None:
            default_looping = bool(payload['looping'])
        settings = {
            'warping': True,
            'looping': default_looping,
            'pitch_coarse': coarse,
            'pitch_fine': fine,
            'gain': float(payload.get('gain', 0.85)),
        }
        if isinstance(payload.get('settings'), dict):
            extra_settings = validate_settings({**settings, **payload['settings']})
            settings.update(extra_settings)
        clip_name = str(payload.get('name') or resolved_path.stem)[:200]
        apply_payload = {
            'session_id': payload.get('session_id') or state.get('session_id'),
            'source_revision': payload.get('source_revision') or project.get('revision'),
            'expected_set_path': payload.get('expected_set_path') or state.get('set_path'),
            'working_copy_confirmed': True,
            'path': str(resolved_path),
            'track_id': track_id,
            'scene_index': int(payload.get('scene_index') if payload.get('scene_index') is not None else state.get('scene_count', 0)),
            'name': clip_name,
            'settings': settings,
            'source_bpm': source_bpm,
        }
        if 'arrangement_beat' in payload and payload['arrangement_beat'] is not None:
            apply_payload['arrangement_beat'] = payload['arrangement_beat']
        if payload.get('region_id'):
            apply_payload['region_id'] = payload['region_id']
        return apply(apply_payload)


def job_status(job_id):
    job_id = str(uuid.UUID(job_id))
    job = read(ROOT / (job_id + '.json'))
    if not job:
        raise ValueError('Sample job not found')
    execution = (
        read(queue.QUEUE_DIR / 'sample-executions' / (job_id + '.json'))
        or read(queue.QUEUE_DIR / 'composition-executions' / (job_id + '.json'))
        or read(Path.home() / '.vibelton' / 'composition-executions' / (job_id + '.json'))
    )
    if execution:
        job.update(status=execution['status'], execution=execution)
        if execution.get('error') and not job.get('error'):
            job['error'] = execution['error']
    state = queue.current_state()
    if job['status'] == 'Queued' and state.get('session_id') != job['session_id']:
        job.update(status='Interrupted', error='Live session changed; this job will not replay.')
    return job


def _resolve_analysis_audio_path(raw_val: str) -> Path:
    if not raw_val or not str(raw_val).strip():
        raise ValueError('Provide an audio file path to analyse')
    raw_str = str(raw_val).strip()
    try:
        return _resolve_sample_path(raw_str)
    except Exception:
        p = Path(raw_str).expanduser().resolve(strict=True)
        if not p.is_file() or p.suffix.lower() not in EXTENSIONS:
            raise ValueError('Choose an existing audio file')
        return p


def _maybe_queue_midi_to_live(
    payload: dict,
    notes: list[dict],
    default_clip_name: str,
    bpm: float,
) -> dict | None:
    target_track_id = payload.get('target_track_id') or payload.get('track_id')
    wants_live = bool(target_track_id or payload.get('apply_to_live') or payload.get('queue_to_live'))
    if not wants_live and 'working_copy_confirmed' not in payload:
        return None
    if payload.get('working_copy_confirmed') is not True:
        raise ValueError('Confirm in the UI that Ableton is open on a working copy before sending MIDI to Live.')
    if not wants_live:
        return None

    state = queue.current_state() or {}
    if not state.get('connected') or time.time() - (state.get('updated_at') or 0) > 10:
        raise ValueError('Live heartbeat is stale or disconnected')
    if 'composition_v1' not in (state.get('capabilities') or []):
        raise ValueError('Updated composition bridge must be loaded before placing MIDI clips')
    if not _arrangement_readable(state):
        raise ValueError('Resolve Arrangement readback errors before placing MIDI clips')

    project = state.get('production') or {}
    all_tracks = (project.get('tracks') or []) or (state.get('tracks') or [])
    if target_track_id == 'auto' or not target_track_id:
        midi_tracks = [t for t in all_tracks if t.get('type') == 'midi' and not t.get('is_group')]
        empty_midi = [
            t for t in midi_tracks
            if not t.get('arrangement_clips') and not t.get('session_clips') and not t.get('clips')
        ]
        target = empty_midi[0] if empty_midi else (midi_tracks[0] if midi_tracks else None)
    else:
        target = next((t for t in all_tracks if t.get('id') == target_track_id), None)

    if not target or target.get('type') != 'midi' or target.get('is_group'):
        raise ValueError('Choose a non-group MIDI track to receive transcribed MIDI notes')
    if not notes:
        raise ValueError('No MIDI notes were detected in the audio source to place into Live')

    max_note_end = max((float(n.get('start', 0.0)) + float(n.get('duration', 0.25)) for n in notes), default=4.0)
    length_beats = max(4.0, float(math.ceil(max_note_end / 4.0) * 4.0))
    arr_end = float(state.get('arrangement_end') or 0.0)
    default_start = float(math.ceil(max(0.0, arr_end + (4.0 if arr_end > 0 else 0.0)) / 4.0) * 4.0)
    start_beat = float(payload.get('start_beat') if payload.get('start_beat') is not None else default_start)
    for t in all_tracks:
        for c in (t.get('arrangement_clips') or []):
            c_start = float(c.get('start_beat', c.get('start_time', 0.0)))
            c_end = float(c.get('end_beat', c.get('end_time', c_start + float(c.get('length', 0.0)))))
            if c_start < start_beat + length_beats and c_end > start_beat:
                raise ValueError('Arrangement range is occupied; choose a fresh start_beat beyond existing clips')
    scene_count = int(state.get('scene_count') or 0)
    job_id = str(uuid.uuid4())
    clip_name = str(payload.get('name') or default_clip_name)[:120]

    clean_notes = []
    for n in notes:
        st = max(0.0, float(n.get('start', 0.0)))
        if st >= length_beats:
            continue
        dur = max(0.0312, min(float(n.get('duration', 0.25)), length_beats - st))
        clean_notes.append({
            'pitch': max(0, min(127, int(n.get('pitch', 60)))),
            'start': round(st, 4),
            'duration': round(dur, 4),
            'velocity': max(1, min(127, int(n.get('velocity', 90)))),
            'mute': bool(n.get('mute', False)),
        })

    action = {
        'type': 'composition_apply',
        'job_id': job_id,
        'session_id': state.get('session_id'),
        'scene_count': scene_count,
        'bpm': max(40.0, min(240.0, float(bpm or state.get('tempo') or 120.0))),
        'start_beat': start_beat,
        'total_beats': length_beats,
        'preview': bool(payload.get('preview', False)),
        'tracks': [{'id': target['id'], 'name': target['name']}],
        'clips': [{
            'track_id': target['id'],
            'scene_index': scene_count,
            'name': clip_name,
            'start_beat': start_beat,
            'length_beats': length_beats,
            'metre': [4, 4],
            'notes': clean_notes,
        }],
    }
    job = {
        'id': job_id,
        'status': 'Queued',
        'session_id': state.get('session_id'),
        'created_at': time.time(),
        'action': action,
    }
    write(ROOT / (job_id + '.json'), job)
    try:
        cmd = queue.enqueue([action], source='samples')
        job['command_id'] = cmd.get('id')
        write(ROOT / (job_id + '.json'), job)
    except Exception:
        job['status'] = 'Failed'
        job['error'] = 'Queue submission uncertain; inspect execution before resubmitting.'
        write(ROOT / (job_id + '.json'), job)
        raise
    return {
        'job_id': job_id,
        'command_id': cmd.get('id'),
        'status': 'Queued',
        'target_track_name': target['name'],
        'target_track_id': target['id'],
        'scene_index': scene_count,
        'start_beat': start_beat,
        'length_beats': length_beats,
    }


def audio_to_midi(payload: dict) -> dict:
    from . import audio_intelligence
    payload = dict(payload or {})
    if payload.get('working_copy_confirmed') is False:
        raise ValueError('Confirm in the UI that Ableton is open on a working copy before sending MIDI to Live.')
    raw_path = payload.get('path') or payload.get('relative_path')
    path = _resolve_analysis_audio_path(raw_path)
    state = queue.current_state() or {}
    bpm = float(payload.get('bpm') or state.get('tempo') or 120.0)
    max_seconds = float(payload.get('max_seconds') or 16.0)
    quantize_grid = float(payload.get('quantize_grid') or 0.25)
    result = audio_intelligence.transcribe_audio_to_midi(
        path,
        bpm=bpm,
        max_seconds=max_seconds,
        quantize_grid=quantize_grid,
    )
    queued_info = _maybe_queue_midi_to_live(
        payload,
        result.get('notes') or [],
        f"Audio2MIDI · {path.stem}",
        bpm,
    )
    if queued_info:
        result = {**result, **queued_info, 'queued': True}
    return result


def slice_transients(payload: dict) -> dict:
    from . import audio_intelligence
    payload = dict(payload or {})
    if payload.get('working_copy_confirmed') is False:
        raise ValueError('Confirm in the UI that Ableton is open on a working copy before sending MIDI to Live.')
    raw_path = payload.get('path') or payload.get('relative_path')
    path = _resolve_analysis_audio_path(raw_path)
    state = queue.current_state() or {}
    bpm = float(payload.get('bpm') or state.get('tempo') or 120.0)
    max_slices = int(payload.get('max_slices') or 16)
    max_seconds = float(payload.get('max_seconds') or 30.0)
    result = audio_intelligence.slice_loop_transients(
        path,
        max_slices=max_slices,
        bpm=bpm,
        max_seconds=max_seconds,
    )
    queued_info = _maybe_queue_midi_to_live(
        payload,
        result.get('midi_notes') or [],
        f"Slices · {path.stem}",
        bpm,
    )
    if queued_info:
        result = {**result, **queued_info, 'queued': True}
    return result



