"""Strict Composition Lab executor, deliberately separate from legacy actions."""
import hashlib
import json
import math
import os
import time
import uuid

try:
    from .audio_bridge import audio_snapshot
except ImportError:
    # This module is also loaded standalone by the contract tests.
    import importlib.util
    _audio_spec = importlib.util.spec_from_file_location('vibelton_audio_snapshot', os.path.join(os.path.dirname(__file__), 'audio_bridge.py'))
    _audio_module = importlib.util.module_from_spec(_audio_spec)
    _audio_spec.loader.exec_module(_audio_module)
    audio_snapshot = _audio_module.audio_snapshot


_CLASSIC_HOUSE_TEMPLATE = 'classic-house-124-club-mix/v1'
_CLASSIC_HOUSE_GROUPS = (
    ('DRUMS', 3, (('Kick', 'midi'), ('Snare / Clap', 'midi'), ('Hats', 'midi'), ('Percussion', 'midi'))),
    ('BASS', 11, (('Bass', 'midi'),)),
    ('MUSIC', 43, (('Chords', 'midi'), ('Lead', 'midi'), ('Hook', 'midi'), ('Atmosphere', 'midi'))),
    ('VOCALS', 49, (('Vocal', 'audio'),)),
    ('FX', 58, (('FX / Risers', 'audio'),)),
    ('REFERENCE', 62, (('Reference', 'audio'),)),
)
_CLASSIC_HOUSE_LOCATORS = (
    (0.0, 'INTRO · 16 bars'), (64.0, 'GROOVE · 16 bars'), (128.0, 'MAIN GROOVE · 32 bars'),
    (256.0, 'TENSION · 16 bars'), (320.0, 'BREAKDOWN · 16 bars'),
    (384.0, 'MAIN SECTION · 32 bars'), (512.0, 'DJ OUTRO · 16 bars'),
)


try:
    import Live  # type: ignore
except ImportError:
    Live = None


# Live ticks to wait for current_song_time to read back as requested before a cue toggle is refused.
_LOCATOR_SEEK_ATTEMPTS = 8


def _cue_summary(cues):
    return '[%s]' % ', '.join('%r at beat %g' % (cue['name'], cue['time']) for cue in cues) if cues else 'nothing'


def _production_complete_callback(finish, complete, failed):
    try:
        finish()
    except Exception as exc:
        failed(exc)
    else:
        complete()


class CompositionBridge:
    def _midi_note_specification_cls(self):
        live_mod = Live
        if live_mod is None:
            try:
                import Live as _live_mod  # type: ignore
                live_mod = _live_mod
            except ImportError:
                live_mod = None
        return getattr(getattr(live_mod, 'Clip', None), 'MidiNoteSpecification', None)

    def _phase3b_arrangement_spike(self, action):
        """One disposable native copy/readback/delete probe; never a production action."""
        if set(action) != {'type', 'spike_id', 'session_id', 'source_track_id', 'source_start_beat', 'destination_beat'}:
            raise RuntimeError('Invalid Phase 3B spike action')
        if action['session_id'] != self._composition_session:
            raise RuntimeError('Live session changed')
        destination = float(action['destination_beat'])
        source_start = float(action['source_start_beat'])
        tracks = {self._composition_track_id(track): track for track in self.song().tracks}
        track = tracks.get(action['source_track_id'])
        if track is None or not callable(getattr(track, 'duplicate_clip_to_arrangement', None)) or not callable(getattr(track, 'delete_clip', None)):
            raise RuntimeError('Native arrangement copy/delete is unavailable')
        matches = [clip for clip in self._track_arrangement_clips(track) if abs(float(clip.start_time) - source_start) < .00001]
        if len(matches) != 1:
            raise RuntimeError('Source arrangement clip is not unique')
        source = matches[0]
        fingerprint = self._composition_clip_snapshot(source)
        before = [(self._composition_track_id(item), self._composition_clip_snapshot(clip), float(clip.start_time), float(clip.end_time))
                  for item in self.song().tracks for clip in self._track_arrangement_clips(item)]
        track.duplicate_clip_to_arrangement(source, destination)
        copies = [clip for clip in self._track_arrangement_clips(track) if abs(float(clip.start_time) - destination) < .00001 and
                  self._composition_clip_snapshot(clip) == fingerprint]
        if len(copies) != 1 or self._composition_clip_snapshot(source) != fingerprint:
            raise RuntimeError('Native arrangement copy readback is ambiguous')
        copied = copies[0]
        track.delete_clip(copied)
        after = [(self._composition_track_id(item), self._composition_clip_snapshot(clip), float(clip.start_time), float(clip.end_time))
                 for item in self.song().tracks for clip in self._track_arrangement_clips(item)]
        if before != after or self._composition_clip_snapshot(source) != fingerprint:
            raise RuntimeError('Native arrangement delete did not restore the observable Set state')
        directory = os.path.join(os.path.expanduser('~'), '.vibelton', 'phase3b-spikes')
        os.makedirs(directory, exist_ok=True)
        result = {'id': action['spike_id'], 'status': 'Passed', 'track_id': action['source_track_id'],
                  'source_start_beat': source_start, 'destination_beat': destination, 'fingerprint': fingerprint,
                  'before': before, 'after': after}
        with open(os.path.join(directory, action['spike_id'] + '.json'), 'w') as handle:
            json.dump(result, handle)
        self._log('phase3b_spike_passed', 'Native arrangement copy/readback/delete passed', {'spike_id': action['spike_id']})
    def _composition_init(self):
        self._composition_session = str(uuid.uuid4())
        self._composition_track_ids = {}

    def _composition_track_id(self, track):
        # Live objects expose stable pointers; retain objects if the host does not.
        pointer = str(getattr(track, '_live_ptr', id(track)))
        if pointer not in self._composition_track_ids:
            self._composition_track_ids[pointer] = str(uuid.uuid4())
        return self._composition_track_ids[pointer]

    def _track_arrangement_clips(self, track):
        if bool(getattr(track, 'is_foldable', False)):
            return ()
        return track.arrangement_clips

    def _device_parameters(self, device):
        params = getattr(device, 'parameters', None) or ()
        out = []
        for idx, p in enumerate(list(params)[:16]):
            out.append({
                'index': idx,
                'name': str(getattr(p, 'name', 'Param %d' % idx)),
                'value': float(getattr(p, 'value', 0.0)),
                'min': float(getattr(p, 'min', 0.0)),
                'max': float(getattr(p, 'max', 1.0)),
                'is_quantized': bool(getattr(p, 'is_quantized', False)),
            })
        return out

    def _composition_devices(self, track):
        result = []
        for d in track.devices:
            item = {'name': str(d.name), 'class_name': str(getattr(d, 'class_name', ''))}
            params = self._device_parameters(d)
            if params:
                item['parameters'] = params
            result.append(item)
        return result

    def _composition_arrangement(self, track):
        return [{'name': str(c.name), 'start_beat': float(c.start_time), 'end_beat': float(c.end_time),
                 'length': float(c.length), 'metre': [int(c.signature_numerator), int(c.signature_denominator)],
                 'summary': self._clip_musical_summary(c)}
                for c in self._track_arrangement_clips(track)]

    def _composition_state(self):
        tracks, readable, end, errors = [], True, 0.0, []
        for track in self.song().tracks:
            try:
                clips = self._composition_arrangement(track)
                end = max([end] + [c['end_beat'] for c in clips])
            except Exception as exc:
                clips, readable = [], False
                errors.append({'track_id': self._composition_track_id(track), 'track_name': str(track.name),
                               'is_group': bool(getattr(track, 'is_foldable', False)),
                               'stage': 'arrangement_metadata', 'error': str(exc)[:500]})
            session_summaries = {}
            for scene_index, slot in enumerate(getattr(track, 'clip_slots', [])):
                if getattr(slot, 'has_clip', False):
                    try:
                        clip = slot.clip
                        if clip is not None:
                            summary = self._clip_musical_summary(clip)
                            if summary is not None:
                                session_summaries[str(scene_index)] = summary
                    except Exception:
                        pass
            tracks.append({'id': self._composition_track_id(track), 'devices': self._composition_devices(track),
                           'has_audio_output': bool(getattr(track, 'has_audio_output', False)),
                           'arrangement_clips': clips,
                           'session_clip_summaries': session_summaries,
                           'routed_to': str(getattr(getattr(track, 'output_routing_type', None), 'display_name', ''))})
        song = self.song()
        root_note = getattr(song, 'root_note', None)
        scale_name = getattr(song, 'scale_name', None)
        return {'session_id': self._composition_session, 'capabilities': ['composition_v1'],
                'arrangement_readable': readable, 'arrangement_end': end,
                'metre': [int(song.signature_numerator), int(song.signature_denominator)],
                'root_note': int(root_note) if isinstance(root_note, (int, float)) else None,
                'scale_name': str(scale_name) if scale_name is not None else None,
                'composition_tracks': tracks, 'arrangement_errors': errors,
                'set_path': str(getattr(song, 'file_path', ''))}

    # Production v1 is intentionally narrow.  It shares Composition Lab's
    # session-scoped IDs but has its own versioned state and executor so the
    # legacy chat actions keep their current behaviour.
    def _production_mixer_state(self, track):
        mixer = track.mixer_device
        return {'volume': float(mixer.volume.value), 'pan': float(mixer.panning.value),
                'sends': [float(send.value) for send in mixer.sends]}

    def _production_locators(self):
        return [{'time': float(cue.time), 'name': str(cue.name)} for cue in getattr(self.song(), 'cue_points', [])]

    def _production_template_capabilities(self):
        song = self.song()
        tracks = list(song.tracks)
        locator_end = max(time_value for time_value, _name in _CLASSIC_HOUSE_LOCATORS)
        return {
            'group_creation': callable(getattr(song, 'create_group_track', None)),
            'locators': callable(getattr(song, 'set_or_delete_cue', None)),
            # Live 12.3.2 exposes cue mutation, but its Remote Script API does
            # not preserve the requested cue position/name for deterministic
            # readback.  Do not advertise it for production arrangements.
            # True only after a probe_arrangement_locators job created, read back and deleted a cue
            # with the exact requested time and name in THIS Live session.
            'arrangement_locator_readback': bool(getattr(self, '_locator_probe_passed', False)),
            # Live refuses to seek beyond an empty Set's song length.  Do not
            # advertise a seven-locator template unless its final beat is
            # already reachable without adding clips or using the UI.
            'locator_range': float(getattr(song, 'song_length', 0.0)) >= locator_end,
            'track_colours': all(hasattr(track, 'color_index') for track in tracks),
        }

    def _production_is_pristine_default_set(self, tracks, locators):
        expected = (('1-MIDI', 'midi'), ('2-MIDI', 'midi'), ('3-Audio', 'audio'), ('4-Audio', 'audio'))
        if locators or len(tracks) != len(expected):
            return False
        for track, (name, kind) in zip(tracks, expected):
            actual = 'midi' if bool(getattr(track, 'has_midi_input', False)) else 'audio'
            if str(track.name) != name or actual != kind or list(track.devices) or list(self._track_arrangement_clips(track)):
                return False
            if any(getattr(slot, 'has_clip', False) for slot in track.clip_slots):
                return False
        return True

    def _production_state(self):
        tracks, arrangement_readable, arrangement_end, errors = [], True, 0.0, []
        song_tracks = list(self.song().tracks)
        for index, track in enumerate(song_tracks):
            if bool(getattr(track, 'is_foldable', False)):
                arrangement = []
            else:
                try:
                    arrangement = [{'name': str(clip.name), 'start_beat': float(clip.start_time),
                                    'end_beat': float(clip.end_time), 'length': float(clip.length),
                                    'metre': [int(clip.signature_numerator), int(clip.signature_denominator)],
                                    'fingerprint': self._composition_clip_snapshot(clip)}
                                   for clip in self._track_arrangement_clips(track)]
                    arrangement_end = max([arrangement_end] + [clip['end_beat'] for clip in arrangement])
                except Exception as exc:
                    arrangement, arrangement_readable = [], False
                    errors.append({'track_id': self._composition_track_id(track), 'track_name': str(track.name),
                                   'is_group': bool(getattr(track, 'is_foldable', False)),
                                   'stage': 'arrangement_metadata_and_fingerprint', 'error': str(exc)[:500]})
            session_clips = []
            for scene_index, slot in enumerate(getattr(track, 'clip_slots', [])):
                if slot.has_clip:
                    try:
                        clip = slot.clip
                        session_clips.append({'scene_index': scene_index, 'name': str(clip.name),
                                              'length': float(clip.length),
                                              'fingerprint': self._composition_clip_snapshot(clip)})
                    except Exception:
                        session_clips.append({'scene_index': scene_index, 'name': 'Unreadable clip',
                                              'length': None, 'fingerprint': None})
            tracks.append({
                'id': self._composition_track_id(track),
                'index': index,
                'name': str(track.name),
                'type': 'midi' if bool(getattr(track, 'has_midi_input', False)) else 'audio',
                'color_index': int(getattr(track, 'color_index', -1)),
                'is_group': bool(getattr(track, 'is_foldable', False)),
                'audio_import_supported': (not bool(getattr(track, 'is_foldable', False))
                                           and not bool(getattr(track, 'has_midi_input', False))
                                           and not bool(getattr(track, 'is_frozen', False))
                                           and bool(getattr(track, 'clip_slots', []))
                                           and callable(getattr(track.clip_slots[0], 'create_audio_clip', None))),
                'group_track_id': (self._composition_track_id(track.group_track)
                                   if getattr(track, 'group_track', None) is not None else None),
                'mixer': self._production_mixer_state(track),
                'devices': self._composition_devices(track),
                'routing': str(getattr(getattr(track, 'output_routing_type', None), 'display_name', '')),
                'arrangement_clips': arrangement,
                'session_clips': session_clips,
            })
        state = {
            'schema_version': 'vibelton.production-project-state/v1',
            'session_id': self._composition_session,
            'tempo': float(self.song().tempo),
            'metre': [int(self.song().signature_numerator), int(self.song().signature_denominator)],
            'arrangement_readable': arrangement_readable,
            'arrangement_errors': errors,
            'set_path': str(getattr(self.song(), 'file_path', '')),
            'arrangement_end': arrangement_end,
            'scene_names': [str(scene.name) for scene in getattr(self.song(), 'scenes', [])],
            'tracks': tracks,
            'locators': self._production_locators(),
            'template_capabilities': self._production_template_capabilities(),
            'is_pristine_default_set': self._production_is_pristine_default_set(song_tracks, self._production_locators()),
        }
        state['revision'] = hashlib.sha256(json.dumps(state, allow_nan=False, sort_keys=True,
                                                       separators=(',', ':')).encode()).hexdigest()
        return state

    def _production_observable_rollback_revision(self):
        """Return the stable Set-state hash used after copy deletion.

        Live retains song length after Arrangement clips are removed.  The
        resulting locator-range capability is runtime bookkeeping, not a
        remaining Set mutation, so exclude only that field here.  The normal
        production revision continues to protect the pre-mutation preflight.
        """
        state = self._production_state()
        state.pop('revision', None)
        capabilities = state.get('template_capabilities')
        if isinstance(capabilities, dict):
            capabilities.pop('locator_range', None)
        return hashlib.sha256(json.dumps(state, allow_nan=False, sort_keys=True,
                                         separators=(',', ':')).encode()).hexdigest()

    def _production_preflight(self, action):
        if action.get('session_id') != self._composition_session:
            raise RuntimeError('Live session changed; refresh the production plan')
        state = self._production_state()
        if action.get('source_revision') != state['revision']:
            raise RuntimeError('Live project state changed; create a new production plan')
        actions = action.get('actions')
        if not isinstance(actions, list) or not 1 <= len(actions) <= 20:
            raise RuntimeError('Invalid production action batch')
        tracks = {self._composition_track_id(track): track for track in self.song().tracks}
        prepared = []
        for item in actions:
            if not isinstance(item, dict):
                raise RuntimeError('Invalid production action schema')
            if item.get('type') == 'apply_session_scene_map':
                if set(item) != {'type', 'source_scene_count', 'scenes'} or len(self.song().scenes) != item['source_scene_count']:
                    raise RuntimeError('Session scenes changed; draft a fresh plan')
                if not isinstance(item['scenes'], list) or len(item['scenes']) != 7:
                    raise RuntimeError('Session plan requires seven scenes')
                prepared_scenes = []
                for scene in item['scenes']:
                    if set(scene) != {'name', 'bar_count', 'copies'} or not isinstance(scene['copies'], list):
                        raise RuntimeError('Invalid Session scene plan')
                    seen_tracks, prepared_copies = set(), []
                    for spec in scene['copies']:
                        if set(spec) != {'track_id', 'source_scene_index', 'source_fingerprint'}:
                            raise RuntimeError('Invalid Session source')
                        track = tracks.get(spec['track_id'])
                        index = spec['source_scene_index']
                        if (track is None or spec['track_id'] in seen_tracks or type(index) is not int or
                                not 0 <= index < item['source_scene_count'] or index >= len(track.clip_slots) or
                                not track.clip_slots[index].has_clip or
                                self._composition_clip_snapshot(track.clip_slots[index].clip) != spec['source_fingerprint'] or
                                not callable(getattr(track.clip_slots[index], 'duplicate_clip_to', None))):
                            raise RuntimeError('Session source is missing, changed, or cannot be copied')
                        seen_tracks.add(spec['track_id'])
                        prepared_copies.append((track, track.clip_slots[index], spec))
                    prepared_scenes.append((scene, prepared_copies))
                prepared.append(('session_apply', (item['source_scene_count'], prepared_scenes)))
                continue
            if item.get('type') == 'rollback_session_scene_map':
                if set(item) != {'type', 'source_scene_count', 'created_scenes', 'expected_post_rollback_observable_revision'}:
                    raise RuntimeError('Invalid Session rollback plan')
                prepared.append(('session_rollback', item))
                continue
            if item.get('type') == 'apply_song_sketch_template':
                if (set(item) != {'type', 'preset_id', 'layout_mode', 'locator_range'} or
                        item.get('preset_id') != _CLASSIC_HOUSE_TEMPLATE or
                        item.get('layout_mode') not in ('grouped', 'flat') or
                        not isinstance(item.get('locator_range'), bool)):
                    raise RuntimeError('Invalid Song Sketch template action')
                capabilities = state['template_capabilities']
                if not capabilities.get('track_colours'):
                    raise RuntimeError('This Live build lacks a required deterministic template capability')
                if item['layout_mode'] == 'grouped' and not capabilities.get('group_creation'):
                    raise RuntimeError('This Live build does not expose deterministic group-track creation')
                if item['layout_mode'] == 'flat' and capabilities.get('group_creation'):
                    raise RuntimeError('Flat template action does not match current bridge capability')
                if not state['is_pristine_default_set']:
                    raise RuntimeError('Classic House template requires an untouched new default Live Set')
                if item['locator_range'] != bool(capabilities.get('locator_range')):
                    raise RuntimeError('Song Sketch locator capability changed; create a new production plan')
                if item['locator_range'] and not capabilities.get('locators'):
                    raise RuntimeError('This Live build cannot create the requested deterministic locator range')
                prepared.append(('template', (item['layout_mode'], item['locator_range'])))
                continue
            if item.get('type') == 'rollback_song_sketch_template':
                required = {'type', 'preset_id', 'created_track_ids', 'created_locators', 'restore_tempo', 'restore_metre', 'restore_tracks'}
                if set(item) != required or item.get('preset_id') != _CLASSIC_HOUSE_TEMPLATE:
                    raise RuntimeError('Invalid Song Sketch template rollback action')
                prepared.append(('template_rollback', item))
                continue
            if item.get('type') == 'apply_arrangement_copies':
                required = {'type', 'copies', 'locators', 'locator_definitions', 'locators_deferred', 'expected_end_beat'}
                if (set(item) != required or not isinstance(item['copies'], list) or not item['copies'] or
                        not isinstance(item['locators'], list) or not isinstance(item['locator_definitions'], list) or
                        len(item['locator_definitions']) != 7 or not isinstance(item['locators_deferred'], bool)):
                    raise RuntimeError('Invalid arrangement-copy action')
                if item['locators_deferred']:
                    if item['locators']:
                        raise RuntimeError('Deferred arrangement locators must not mutate Live')
                elif (not 1 <= len(item['locators']) <= 7 or
                      not state['template_capabilities'].get('arrangement_locator_readback')):
                    raise RuntimeError('This Live build cannot create deterministic arrangement locators')
                elif any(not isinstance(cue, dict) or set(cue) != {'time', 'name'} or
                         not isinstance(cue['time'], (int, float)) or not isinstance(cue['name'], str)
                         for cue in item['locators']):
                    raise RuntimeError('Invalid arrangement locator')
                copies, destinations = [], set()
                for spec in item['copies']:
                    required_copy = {'source_track_id', 'source_start_beat', 'source_fingerprint', 'destination_beat'}
                    target = (spec.get('source_track_id'), spec.get('destination_beat'))
                    if set(spec) != required_copy or spec['source_track_id'] not in tracks or target in destinations:
                        raise RuntimeError('Invalid arrangement copy source')
                    if not isinstance(spec['source_fingerprint'], str) or len(spec['source_fingerprint']) != 64:
                        raise RuntimeError('Invalid arrangement source fingerprint')
                    track = tracks[spec['source_track_id']]
                    matches = [clip for clip in self._track_arrangement_clips(track)
                               if abs(float(clip.start_time) - float(spec['source_start_beat'])) < .00001]
                    if len(matches) != 1 or self._composition_clip_snapshot(matches[0]) != spec['source_fingerprint']:
                        raise RuntimeError('Arrangement source is missing, ambiguous, or changed')
                    if not callable(getattr(track, 'duplicate_clip_to_arrangement', None)):
                        raise RuntimeError('Native arrangement copy is unavailable')
                    destinations.add(target)
                    copies.append((track, matches[0], spec))
                if any(not isinstance(spec.get('time'), (int, float)) or not isinstance(spec.get('name'), str) for spec in item['locator_definitions']):
                    raise RuntimeError('Invalid arrangement locator')
                if not item['locators_deferred']:
                    taken = [cue for cue in item['locators']
                             if any(abs(float(existing['time']) - float(cue['time'])) < .00001
                                    for existing in self._production_locators())]
                    if taken:
                        raise RuntimeError('A locator already exists at a requested section start')
                prepared.append(('arrangement_apply', (copies, item['locators'], item['locator_definitions'],
                                                       item['locators_deferred'], float(item['expected_end_beat']))))
                continue
            if item.get('type') == 'probe_arrangement_locators':
                if set(item) != {'type'}:
                    raise RuntimeError('Invalid locator probe action')
                prepared.append(('locator_probe', None))
                continue
            if item.get('type') == 'rollback_arrangement_copies':
                required = {'type', 'copies', 'locators', 'expected_post_rollback_observable_revision'}
                if (set(item) != required or not isinstance(item['copies'], list) or
                        not isinstance(item['locators'], list) or
                        not isinstance(item['expected_post_rollback_observable_revision'], str) or
                        len(item['expected_post_rollback_observable_revision']) != 64):
                    raise RuntimeError('Invalid arrangement-copy rollback action')
                prepared.append(('arrangement_rollback', item))
                continue
            if item.get('type') == 'apply_session_to_arrangement_copies':
                if (set(item) not in ({'type', 'copies'}, {'type', 'copies', 'expected_end_beat'}) or
                        not isinstance(item.get('copies'), list) or not item['copies']):
                    raise RuntimeError('Invalid session-to-arrangement copy action')
                expected_end = item.get('expected_end_beat')
                if expected_end is not None and (isinstance(expected_end, bool) or not isinstance(expected_end, (int, float)) or float(expected_end) <= 0.0):
                    raise RuntimeError('Invalid expected_end_beat for session-to-arrangement copy action')
                copies, destinations = [], set()
                for spec in item['copies']:
                    required_copy = {'track_id', 'source_scene_index', 'source_fingerprint', 'destination_beat'}
                    if not isinstance(spec, dict) or set(spec) != required_copy or spec['track_id'] not in tracks:
                        raise RuntimeError('Invalid session-to-arrangement copy source')
                    s_idx = spec['source_scene_index']
                    dest_beat = spec['destination_beat']
                    fp = spec['source_fingerprint']
                    if (type(s_idx) is not int or s_idx < 0 or
                            isinstance(dest_beat, bool) or not isinstance(dest_beat, (int, float)) or float(dest_beat) < 0.0 or
                            not isinstance(fp, str) or len(fp) != 64):
                        raise RuntimeError('Invalid session-to-arrangement copy parameters')
                    target = (spec['track_id'], float(dest_beat))
                    if target in destinations:
                        raise RuntimeError('Duplicate session-to-arrangement copy destination')
                    track = tracks[spec['track_id']]
                    if (s_idx >= len(track.clip_slots) or not track.clip_slots[s_idx].has_clip or
                            self._composition_clip_snapshot(track.clip_slots[s_idx].clip) != fp or
                            not callable(getattr(track, 'duplicate_clip_to_arrangement', None))):
                        raise RuntimeError('Session source clip is missing, changed, or cannot be copied to arrangement')
                    destinations.add(target)
                    copies.append((track, track.clip_slots[s_idx].clip, spec))
                prepared.append(('session_to_arrangement_apply', (copies, float(expected_end) if expected_end is not None else None)))
                continue
            if item.get('type') == 'rollback_session_to_arrangement_copies':
                required = {'type', 'copies', 'expected_post_rollback_observable_revision'}
                if (set(item) != required or not isinstance(item.get('copies'), list) or not item['copies'] or
                        not isinstance(item.get('expected_post_rollback_observable_revision'), str) or
                        len(item['expected_post_rollback_observable_revision']) != 64):
                    raise RuntimeError('Invalid session-to-arrangement rollback action')
                prepared.append(('session_to_arrangement_rollback', item))
                continue
            if item.get('type') == 'set_device_parameter':
                tid = item.get('target_track_id') or item.get('track_id')
                dev_idx = item.get('device_index')
                param_idx = item.get('parameter_index')
                val = item.get('value')
                allowed_keys = {'type', 'target_track_id', 'track_id', 'device_index', 'parameter_index', 'value'}
                if not set(item).issubset(allowed_keys) or tid not in tracks:
                    raise RuntimeError('Invalid device parameter action target')
                track = tracks[tid]
                if type(dev_idx) is not int or not 0 <= dev_idx < len(track.devices):
                    raise RuntimeError('Invalid device_index for set_device_parameter')
                device = track.devices[dev_idx]
                params = list(getattr(device, 'parameters', ()) or ())
                if type(param_idx) is not int or not 0 <= param_idx < len(params):
                    raise RuntimeError('Invalid parameter_index for set_device_parameter')
                param = params[param_idx]
                p_min = float(getattr(param, 'min', 0.0))
                p_max = float(getattr(param, 'max', 1.0))
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not p_min <= float(val) <= p_max:
                    raise RuntimeError('Invalid device parameter value')
                prepared.append(('device_parameter', (track, dev_idx, param_idx, param, float(val))))
                continue
            if set(item) != {'type', 'target_track_id', 'values'} or item.get('type') != 'set_track_mixer':
                raise RuntimeError('Unsupported production action')
            track = tracks.get(item.get('target_track_id'))
            values = item.get('values')
            allowed_mixer = {'volume', 'pan', 'send_0', 'send_1', 'sends'}
            if track is None or not isinstance(values, dict) or not values or set(values) - allowed_mixer:
                raise RuntimeError('Invalid production mixer target or values')
            sends_list = list(getattr(track.mixer_device, 'sends', ()) or ())
            normalized = {}
            for key, low, high in (('volume', 0.0, 1.0), ('pan', -1.0, 1.0), ('send_0', 0.0, 1.0), ('send_1', 0.0, 1.0)):
                if key not in values:
                    continue
                if key == 'send_0' and len(sends_list) < 1:
                    raise RuntimeError('Track has no send_0 available')
                if key == 'send_1' and len(sends_list) < 2:
                    raise RuntimeError('Track has no send_1 available')
                value = values[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                    raise RuntimeError('Invalid production mixer value')
                normalized[key] = float(value)
            if 'sends' in values:
                raw_sends = values['sends']
                if not isinstance(raw_sends, list) or not raw_sends or len(raw_sends) > len(sends_list):
                    raise RuntimeError('Invalid production mixer sends list')
                norm_sends = []
                for sv in raw_sends:
                    if isinstance(sv, bool) or not isinstance(sv, (int, float)) or not math.isfinite(sv) or not 0.0 <= float(sv) <= 1.0:
                        raise RuntimeError('Invalid production mixer send value')
                    norm_sends.append(float(sv))
                normalized['sends'] = norm_sends
            prepared.append(('mixer', (track, normalized)))
        special_kinds = (
            'template', 'template_rollback', 'arrangement_apply', 'arrangement_rollback',
            'session_apply', 'session_rollback', 'session_to_arrangement_apply', 'session_to_arrangement_rollback',
        )
        if any(kind in special_kinds for kind, _payload in prepared):
            kinds = [kind for kind, _payload in prepared]
            if len(kinds) != 1 or kinds[0] not in special_kinds:
                raise RuntimeError('Special production actions must run alone')
        return prepared

    def _production_set_color(self, track, color_index):
        track.color_index = int(color_index)
        if int(getattr(track, 'color_index', -1)) != int(color_index):
            raise RuntimeError('Track colour readback did not match')

    def _production_create_track(self, track_type, name, color_index):
        song = self.song()
        before = len(song.tracks)
        if track_type == 'midi':
            song.create_midi_track(-1)
        elif track_type == 'audio':
            song.create_audio_track(-1)
        else:
            raise RuntimeError('Unsupported template track type')
        if len(song.tracks) != before + 1:
            raise RuntimeError('Track creation did not add exactly one track')
        track = song.tracks[-1]
        track.name = name
        self._production_set_color(track, color_index)
        if str(track.name) != name:
            raise RuntimeError('Track name readback did not match')
        return track

    def _production_set_locator(self, time_value, name):
        self._production_locators_sync([(time_value, name)], 'set')

    def _production_delete_locator(self, time_value, name):
        self._production_locators_sync([(time_value, name)], 'delete')

    def _production_locators_sync(self, locators, operation, trace=None):
        """The cue engine without schedule_message: every step runs immediately."""
        errors = []
        self._production_locators_async(locators, operation, lambda: None, errors.append, trace, immediate=True)
        if errors:
            raise errors[0]

    def _production_locators_async(self, locators, operation, complete, failed, trace=None, immediate=False):
        """Create or delete cues one at a time, letting Live settle between steps.

        ``set_or_delete_cue`` toggles a cue at the playhead, so each step first
        confirms that Live really moved the playhead to the requested beat and
        then checks the whole cue list: exactly one cue added (or removed) at
        that beat, and nothing else changed.  ``trace`` collects what was seen.
        """
        song = self.song()
        eps = .00001
        log = trace if trace is not None else []
        if immediate or not callable(getattr(self, 'schedule_message', None)):
            defer = lambda callback: callback()
        else:
            defer = lambda callback: self.schedule_message(1, callback)
        original_time = float(song.current_song_time)
        index = [0]
        attempts = [0]

        def restore():
            # Live refuses to seek behind the song length, and the user's playhead may be parked past the end.
            try:
                target = max(0.0, min(original_time, float(getattr(song, 'song_length', original_time))))
                if abs(float(song.current_song_time) - target) > eps:
                    song.current_song_time = target
            except Exception as exc:
                log.append({'op': 'restore', 'error': str(exc)})

        def fail(exc):
            restore()
            failed(exc)

        def begin():
            try:
                if getattr(song, 'is_playing', False):
                    raise RuntimeError('Stop playback first: Live places cues at the moving playhead while it plays')
                time_value = float(locators[index[0]][0])
                length = float(getattr(song, 'song_length', time_value))
                if time_value > length + eps:
                    raise RuntimeError('Locator at beat %g is beyond the song length (beat %g)' % (time_value, length))
                attempts[0] = 0
                song.current_song_time = time_value
                defer(mutate)
            except Exception as exc:
                fail(exc)

        def mutate():
            try:
                time_value, name = float(locators[index[0]][0]), locators[index[0]][1]
                observed = float(song.current_song_time)
                if abs(observed - time_value) >= eps:
                    attempts[0] += 1
                    if attempts[0] < _LOCATOR_SEEK_ATTEMPTS:
                        # Wait for a slow seek to land; re-issue it once in case Live dropped it.
                        if attempts[0] == _LOCATOR_SEEK_ATTEMPTS // 2:
                            song.current_song_time = time_value
                        defer(mutate)
                        return
                    log.append({'op': operation, 'time': time_value, 'name': name, 'song_time': observed,
                                'seek_ticks': attempts[0], 'toggled': False})
                    raise RuntimeError('Live did not move the playhead to beat %g (it reads %g); no cue was changed'
                                       % (time_value, observed))
                before = self._production_locators()
                matches = [cue for cue in before if abs(cue['time'] - time_value) < eps]
                if operation == 'set':
                    if matches:
                        raise RuntimeError('A locator already exists at the requested time')
                elif len([cue for cue in matches if cue['name'] == name]) != 1:
                    raise RuntimeError('Expected template locator is missing or changed')
                step = {'op': operation, 'time': time_value, 'name': name, 'song_time': observed,
                        'seek_ticks': attempts[0], 'cues_before': before, 'toggled': True}
                log.append(step)
                song.set_or_delete_cue()
                defer(lambda: verify(step))
            except Exception as exc:
                fail(exc)

        def verify(step):
            try:
                time_value, name = step['time'], step['name']
                before = step['cues_before']
                after = self._production_locators()
                step['cues_after'] = after
                step['song_time_after'] = float(song.current_song_time)
                added = [cue for cue in after if cue not in before]
                removed = [cue for cue in before if cue not in after]
                if operation == 'set':
                    if removed or len(added) != 1 or abs(added[0]['time'] - time_value) >= eps:
                        raise RuntimeError('Locator creation readback did not match: asked for beat %g, Live added %s '
                                           'and removed %s' % (time_value, _cue_summary(added), _cue_summary(removed)))
                    cue = [item for item in song.cue_points
                           if abs(float(item.time) - time_value) < eps and str(item.name) == added[0]['name']][0]
                    cue.name = name
                    if str(cue.name) != name:
                        raise RuntimeError('Locator name readback did not match')
                elif (added or len(removed) != 1 or abs(removed[0]['time'] - time_value) >= eps or
                      removed[0]['name'] != name):
                    raise RuntimeError('Locator deletion readback did not match: asked to remove beat %g, Live added %s '
                                       'and removed %s' % (time_value, _cue_summary(added), _cue_summary(removed)))
                index[0] += 1
                if index[0] == len(locators):
                    restore()
                    complete()
                else:
                    begin()
            except Exception as exc:
                fail(exc)

        begin()

    def _production_probe_locators(self, result, complete, failed):
        """Create, read back and delete one cue; only an exact round trip enables arrangement markers."""
        song = self.song()
        self._locator_probe_passed = False
        name = 'VIBELTON_PROBE'
        original = self._production_locators()
        trace = []
        cues = list(getattr(song, 'cue_points', []))
        diagnostics = {
            'path': 'async' if callable(getattr(self, 'schedule_message', None)) else 'sync',
            'song_length': float(getattr(song, 'song_length', 0.0)),
            'is_playing': bool(getattr(song, 'is_playing', False)),
            'start_song_time': float(song.current_song_time),
            'cues_at_start': original,
            # What this Live build exposes, to look for a better cue API than the playhead toggle.
            'api': {'song': sorted(attr for attr in dir(song) if 'cue' in attr.lower()),
                    'cue_point': sorted(attr for attr in dir(cues[0]) if not attr.startswith('_')) if cues else []},
            'trace': trace,
        }
        if not callable(getattr(song, 'set_or_delete_cue', None)):
            failed(RuntimeError('This Live build has no cue API'))
            return
        length = diagnostics['song_length']
        taken = [float(cue['time']) for cue in original]
        free = [t for t in (4.0, 8.0, 12.0, 16.0, 32.0)
                if t <= length and all(abs(t - other) > .00001 for other in taken)]
        if not free:
            failed(RuntimeError('The Set is too short (or beats 4-32 already hold cues) to probe cue support'))
            return
        probe_time = free[0]

        def run(operation, done, fail):
            self._production_locators_async([(probe_time, name)], operation, done, fail, trace)

        def fail(exc):
            self._locator_probe_passed = False

            def report(cleanup_error=None):
                # What the Set holds now that was not there before the probe (empty = nothing stray).
                leftover = [cue for cue in self._production_locators() if cue not in original]
                probe = dict(diagnostics, passed=False, time=probe_time, error=str(exc), leftover_cues=leftover,
                             cleanup_attempted=bool(stray), end_song_time=float(song.current_song_time))
                if cleanup_error is not None:
                    probe['cleanup_error'] = str(cleanup_error)
                result.update(locator_probe=probe)
                failed(exc)

            # One best-effort delete of any cue the probe left behind: named VIBELTON_PROBE, or created but never
            # named because it landed off target (Live leaves those blank or numbered "1", "2"...). Cues you named
            # yourself are never touched.
            stray = [cue for cue in self._production_locators()
                     if cue not in original and (cue['name'] in (name, '') or cue['name'].isdigit())]
            if not stray:
                report()
                return
            specs = [(float(cue['time']), cue['name']) for cue in stray]
            try:
                self._production_locators_async(specs, 'delete', report, report, trace)
            except Exception as cleanup_exc:
                report(cleanup_exc)

        def deleted():
            try:
                if self._production_locators() != original:
                    raise RuntimeError('The cue list differs from the original after the probe cleaned up')
                self._locator_probe_passed = True
                result.update(locator_probe=dict(diagnostics, passed=True, time=probe_time, name=name,
                                                 end_song_time=float(song.current_song_time)))
                complete()
            except Exception as exc:
                fail(exc)

        run('set', lambda: run('delete', deleted, fail), fail)

    def _production_apply_template(self, layout_mode, locator_range, result, complete=None, failed=None):
        song = self.song()
        restore_tracks = []
        for index, track in enumerate(list(song.tracks)):
            restore_tracks.append({'index': index, 'name': str(track.name),
                                   'track_type': 'midi' if bool(getattr(track, 'has_midi_input', False)) else 'audio',
                                   'color_index': int(getattr(track, 'color_index', -1))})
        source_track_ids = [self._composition_track_id(track) for track in song.tracks]
        created_ids = []
        if layout_mode == 'grouped':
            for group_name, color_index, children in _CLASSIC_HOUSE_GROUPS:
                before = len(song.tracks)
                song.create_group_track(-1)
                if len(song.tracks) != before + 1:
                    raise RuntimeError('Group creation did not add exactly one track')
                group = song.tracks[-1]
                group.name = group_name
                self._production_set_color(group, color_index)
                if not bool(getattr(group, 'is_foldable', False)) or str(group.name) != group_name:
                    raise RuntimeError('Group readback did not match')
                created_ids.append(self._composition_track_id(group))
                for name, track_type in children:
                    track = self._production_create_track(track_type, name, color_index)
                    if getattr(track, 'group_track', None) is not group:
                        raise RuntimeError('Created track is not grouped as requested')
                    created_ids.append(self._composition_track_id(track))
        else:
            # This is intentionally flat.  The intended group is reported by
            # the plan/result, but no Live group relationship is fabricated.
            for _group_name, color_index, children in _CLASSIC_HOUSE_GROUPS:
                for name, track_type in children:
                    track = self._production_create_track(track_type, name, color_index)
                    if getattr(track, 'group_track', None) is not None:
                        raise RuntimeError('Flat template unexpectedly created a group relationship')
                    created_ids.append(self._composition_track_id(track))
        # Live refuses to delete its final track.  Build and verify every
        # template track first, then remove only the original default tracks.
        # This preserves a real track throughout and leaves no defaults in the
        # completed template.
        def finish():
            tracks = {self._composition_track_id(track): (index, track) for index, track in enumerate(song.tracks)}
            if set(source_track_ids) - set(tracks) or set(created_ids) - set(tracks):
                raise RuntimeError('Template track identity changed before default-track removal')
            for index in sorted((tracks[track_id][0] for track_id in source_track_ids), reverse=True):
                song.delete_track(index)
            if len(song.tracks) != len(created_ids):
                raise RuntimeError('Default-track removal did not complete')
            if locator_range and len(self._production_locators()) != len(_CLASSIC_HOUSE_LOCATORS):
                raise RuntimeError('Locator persistence readback did not match')
            if not locator_range and self._production_locators():
                raise RuntimeError('Blank-set template unexpectedly created locators')
            song.tempo = 124.0
            song.signature_numerator, song.signature_denominator = 4, 4
            if abs(float(song.tempo) - 124.0) > .00001 or (int(song.signature_numerator), int(song.signature_denominator)) != (4, 4):
                raise RuntimeError('Song timing readback did not match')
            warnings = []
            if layout_mode == 'flat':
                warnings.append('Groups were not created because this Ableton Live Remote Script cannot create group tracks deterministically.')
            if not locator_range:
                warnings.append('Arrangement locators were deferred: Ableton cannot create the full locator range until arrangement content establishes sufficient song length.')
            result.update(layout_mode=layout_mode, warning=warnings[0] if warnings else None, warnings=warnings,
                          locator_range=locator_range, locators_deferred=not locator_range,
                          locator_definitions=[{'time': time_value, 'name': name} for time_value, name in _CLASSIC_HOUSE_LOCATORS],
                          created_track_ids=created_ids,
                          created_locators=([{'time': time_value, 'name': name} for time_value, name in _CLASSIC_HOUSE_LOCATORS]
                                            if locator_range else []),
                          restore_tracks=restore_tracks)

        if locator_range and callable(getattr(self, 'schedule_message', None)) and complete is not None and failed is not None:
            self._production_locators_async(_CLASSIC_HOUSE_LOCATORS, 'set',
                                            lambda: self.schedule_message(
                                                1, lambda: _production_complete_callback(finish, complete, failed)), failed)
            return True
        if locator_range:
            for time_value, name in _CLASSIC_HOUSE_LOCATORS:
                self._production_set_locator(time_value, name)
        finish()
        # Live may report the old project state until the next control-surface
        # tick after tracks are removed or song timing changes.  Do not record
        # an immediately stale revision: it would make the exact rollback
        # guard reject an otherwise untouched template.
        if callable(getattr(self, 'schedule_message', None)) and complete is not None and failed is not None:
            self.schedule_message(1, complete)
            return True
        return False

    def _production_rollback_template(self, item, result, complete=None, failed=None):
        song = self.song()
        tracks = {self._composition_track_id(track): (index, track) for index, track in enumerate(song.tracks)}
        if set(item['created_track_ids']) - set(tracks):
            raise RuntimeError('Expected template tracks are missing or changed')
        for track_id in item['created_track_ids']:
            if tracks[track_id][1].devices or self._track_arrangement_clips(tracks[track_id][1]):
                raise RuntimeError('Template track contains material; rollback is no longer safe')
        # Restore defaults before deleting the template.  As in application,
        # this never asks Live to delete its final track.
        for spec in sorted(item['restore_tracks'], key=lambda value: value['index']):
            track = self._production_create_track(spec['track_type'], spec['name'], spec['color_index'])
            if str(track.name) != spec['name']:
                raise RuntimeError('Default-track restoration readback did not match')
        tracks = {self._composition_track_id(track): (index, track) for index, track in enumerate(song.tracks)}
        for index in sorted((tracks[track_id][0] for track_id in item['created_track_ids']), reverse=True):
            song.delete_track(index)
        if len(song.tracks) != len(item['restore_tracks']):
            raise RuntimeError('Template-track removal did not complete')
        def finish():
            song.tempo = float(item['restore_tempo'])
            song.signature_numerator, song.signature_denominator = item['restore_metre']
            result.update(restored_template=True)

        locator_specs = [(locator['time'], locator['name']) for locator in item['created_locators']]
        if locator_specs and callable(getattr(self, 'schedule_message', None)) and complete is not None and failed is not None:
            self._production_locators_async(locator_specs, 'delete',
                                            lambda: self.schedule_message(
                                                1, lambda: _production_complete_callback(finish, complete, failed)), failed)
            return True
        for locator in item['created_locators']:
            self._production_delete_locator(locator['time'], locator['name'])
        finish()
        # See the matching template-apply path: record rollback completion
        # only after Live has published the restored track/timing state.
        if callable(getattr(self, 'schedule_message', None)) and complete is not None and failed is not None:
            self.schedule_message(1, complete)
            return True
        return False

    def _production_apply_arrangement_copies(self, copies, locators, locator_definitions, locators_deferred, expected_end, result, complete, failed):
        """Copy only preflighted Arrangement clips, then create post-length cues."""
        song = self.song()
        created = []
        original_locators = self._production_locators()
        try:
            # Check every destination before changing anything.  A retry or a
            # manual addition therefore fails before mutation rather than
            # layering an indistinguishable duplicate clip.
            occupied = {}
            for track, source, spec in copies:
                start = float(spec['destination_beat'])
                end = start + float(source.end_time) - float(source.start_time)
                if end <= start or any(start < float(clip.end_time) - .00001 and end > float(clip.start_time) + .00001
                                      for clip in self._track_arrangement_clips(track)):
                    raise RuntimeError('Arrangement copy destination is already occupied')
                track_key = self._composition_track_id(track)
                if any(start < prior_end - .00001 and end > prior_start + .00001
                       for prior_start, prior_end in occupied.get(track_key, [])):
                    raise RuntimeError('Arrangement copies overlap each other')
                occupied.setdefault(track_key, []).append((start, end))
            for track, source, spec in copies:
                track.duplicate_clip_to_arrangement(source, float(spec['destination_beat']))
                matches = [clip for clip in self._track_arrangement_clips(track)
                           if abs(float(clip.start_time) - float(spec['destination_beat'])) < .00001 and
                           self._composition_clip_snapshot(clip) == spec['source_fingerprint']]
                if len(matches) != 1 or self._composition_clip_snapshot(source) != spec['source_fingerprint']:
                    raise RuntimeError('Arrangement copy readback did not match')
                created.append({'source_track_id': self._composition_track_id(track),
                                'source_start_beat': float(spec['source_start_beat']),
                                'source_fingerprint': spec['source_fingerprint'],
                                'destination_beat': float(spec['destination_beat'])})
                result.update(created_copies=created, completed_actions=len(created))
            if abs(max([0.0] + [float(clip.end_time) for track in song.tracks for clip in self._track_arrangement_clips(track)]) - expected_end) > .00001:
                raise RuntimeError('Arrangement copy length readback did not reach the approved end')
        except Exception as exc:
            failed(exc)
            return True

        def finish():
            try:
                for spec in created:
                    track = {self._composition_track_id(item): item for item in song.tracks}[spec['source_track_id']]
                    matches = [clip for clip in self._track_arrangement_clips(track)
                               if abs(float(clip.start_time) - spec['destination_beat']) < .00001]
                    if len(matches) != 1 or self._composition_clip_snapshot(matches[0]) != spec['source_fingerprint']:
                        raise RuntimeError('Arrangement copy fingerprint changed after placement')
                observed = self._production_locators()
                if locators_deferred:
                    if observed != original_locators:
                        raise RuntimeError('Existing arrangement locators changed during copy')
                    result.update(created_copies=created, created_locators=[], locator_definitions=locator_definitions,
                                  locators_deferred=True,
                                  locator_warning='Arrangement locators were not created because this Ableton Live Remote Script cannot read them back deterministically.',
                                  expected_end_beat=expected_end, arrangement_verified=True)
                else:
                    new_cues = [{'time': float(item['time']), 'name': str(item['name'])} for item in locators]
                    order = lambda cue: (cue['time'], cue['name'])
                    if sorted(observed, key=order) != sorted(original_locators + new_cues, key=order):
                        raise RuntimeError('Arrangement locator readback did not match')
                    result.update(created_copies=created, created_locators=new_cues, locator_definitions=locator_definitions,
                                  locators_deferred=False, expected_end_beat=expected_end, arrangement_verified=True)
                complete()
            except Exception as exc:
                failed(exc)

        if locators_deferred:
            finish()
            return True
        specs = [(float(item['time']), str(item['name'])) for item in locators]
        if callable(getattr(self, 'schedule_message', None)):
            self._production_locators_async(specs, 'set', finish, failed)
            return True
        try:
            for time_value, name in specs:
                self._production_set_locator(time_value, name)
            finish()
        except Exception as exc:
            failed(exc)
        return True

    def _production_rollback_arrangement_copies(self, item, result, complete, failed):
        song = self.song()
        tracks = {self._composition_track_id(track): track for track in song.tracks}
        targets = []
        try:
            for spec in item['copies']:
                track = tracks.get(spec.get('source_track_id'))
                if track is None or not callable(getattr(track, 'delete_clip', None)):
                    raise RuntimeError('Arrangement rollback target track is unavailable')
                sources = [clip for clip in self._track_arrangement_clips(track)
                           if abs(float(clip.start_time) - float(spec['source_start_beat'])) < .00001]
                matches = [clip for clip in self._track_arrangement_clips(track)
                           if abs(float(clip.start_time) - float(spec['destination_beat'])) < .00001 and
                           self._composition_clip_snapshot(clip) == spec['source_fingerprint']]
                if len(sources) != 1 or self._composition_clip_snapshot(sources[0]) != spec['source_fingerprint'] or len(matches) != 1:
                    raise RuntimeError('Expected arrangement copy is missing or changed')
                targets.append((track, matches[0], spec))
            if item['locators'] and not all(locator in self._production_locators() for locator in item['locators']):
                raise RuntimeError('Arrangement locators are missing or changed')
        except Exception as exc:
            failed(exc)
            return True

        def finish():
            try:
                for track, clip, _spec in targets:
                    track.delete_clip(clip)
                    if clip in self._track_arrangement_clips(track):
                        raise RuntimeError('Arrangement copy deletion readback did not match')
                if (self._production_observable_rollback_revision() !=
                        item['expected_post_rollback_observable_revision']):
                    raise RuntimeError('Arrangement rollback did not restore the exact original state')
                result.update(deleted_copies=len(targets), deleted_locators=item['locators'], arrangement_rollback_verified=True)
                complete()
            except Exception as exc:
                failed(exc)

        specs = [(float(locator['time']), str(locator['name'])) for locator in item['locators']]
        # Deferred-locator executions intentionally have no native cue
        # targets.  Do not pass an empty sequence into the asynchronous cue
        # helper, which expects at least one element.
        if not specs:
            finish()
            return True
        if callable(getattr(self, 'schedule_message', None)):
            self._production_locators_async(specs, 'delete', finish, failed)
            return True
        try:
            for time_value, name in specs:
                self._production_delete_locator(time_value, name)
            finish()
        except Exception as exc:
            failed(exc)
        return True

    def _production_apply_session_scenes(self, source_count, scenes, result, complete, failed):
        song = self.song()
        created = []
        try:
            if len(song.scenes) != source_count:
                raise RuntimeError('Session scenes changed before placement')
            for scene_spec, copies in scenes:
                index = len(song.scenes)
                song.create_scene(-1)
                song.scenes[index].name = scene_spec['name']
                record = {'index': index, 'name': scene_spec['name'], 'copies': []}
                created.append(record)
                result['created_scenes'] = created
                if str(song.scenes[index].name) != scene_spec['name']:
                    raise RuntimeError('Session scene name readback did not match')
                for track, source_slot, spec in copies:
                    target = track.clip_slots[index]
                    if target.has_clip:
                        raise RuntimeError('New Session slot is unexpectedly occupied')
                    source_slot.duplicate_clip_to(target)
                    if (not target.has_clip or
                            self._composition_clip_snapshot(target.clip) != spec['source_fingerprint'] or
                            self._composition_clip_snapshot(source_slot.clip) != spec['source_fingerprint']):
                        raise RuntimeError('Session clip copy readback did not match')
                    record['copies'].append(spec)
            result.update(created_scenes=created, completed_actions=1, session_verified=True)
            complete()
        except Exception as exc:
            result['created_scenes'] = created
            failed(exc)
        return True

    def _production_rollback_session_scenes(self, item, result, complete, failed):
        song = self.song()
        scenes = item['created_scenes']
        try:
            if not scenes or len(song.scenes) != item['source_scene_count'] + len(scenes):
                raise RuntimeError('Session scene count changed; rollback is unsafe')
            tracks = {self._composition_track_id(track): track for track in song.tracks}
            for offset, record in enumerate(scenes):
                index = item['source_scene_count'] + offset
                if record['index'] != index or str(song.scenes[index].name) != record['name']:
                    raise RuntimeError('A generated Session scene was changed')
                for spec in record['copies']:
                    track = tracks.get(spec['track_id'])
                    if (track is None or not track.clip_slots[index].has_clip or
                            self._composition_clip_snapshot(track.clip_slots[index].clip) != spec['source_fingerprint']):
                        raise RuntimeError('A generated Session clip was changed')
                if any(track.clip_slots[index].has_clip for track in song.tracks
                       if self._composition_track_id(track) not in {spec['track_id'] for spec in record['copies']}):
                    raise RuntimeError('A generated Session scene contains a new clip')
            for record in reversed(scenes):
                song.delete_scene(record['index'])
            if self._production_observable_rollback_revision() != item['expected_post_rollback_observable_revision']:
                raise RuntimeError('Session rollback did not restore the original observable Set')
            result.update(deleted_scenes=len(scenes), session_rollback_verified=True)
            complete()
        except Exception as exc:
            failed(exc)
        return True

    def _production_apply_session_to_arrangement_copies(self, copies, expected_end, result, complete, failed):
        song = self.song()
        created = []
        try:
            occupied = {}
            for track, source, spec in copies:
                start = float(spec['destination_beat'])
                length = float(getattr(source, 'length', 0.0) or (float(getattr(source, 'end_time', 0.0)) - float(getattr(source, 'start_time', 0.0))))
                end = start + length
                if end <= start or any(start < float(clip.end_time) - .00001 and end > float(clip.start_time) + .00001
                                      for clip in self._track_arrangement_clips(track)):
                    raise RuntimeError('Arrangement copy destination is already occupied')
                track_key = self._composition_track_id(track)
                if any(start < prior_end - .00001 and end > prior_start + .00001
                       for prior_start, prior_end in occupied.get(track_key, [])):
                    raise RuntimeError('Session-to-arrangement copies overlap each other')
                occupied.setdefault(track_key, []).append((start, end))
            for track, source, spec in copies:
                track.duplicate_clip_to_arrangement(source, float(spec['destination_beat']))
                matches = [clip for clip in self._track_arrangement_clips(track)
                           if abs(float(clip.start_time) - float(spec['destination_beat'])) < .00001 and
                           self._composition_clip_snapshot(clip) == spec['source_fingerprint']]
                if len(matches) != 1 or self._composition_clip_snapshot(source) != spec['source_fingerprint']:
                    raise RuntimeError('Session-to-arrangement copy readback did not match')
                created.append({'track_id': self._composition_track_id(track),
                                'source_scene_index': int(spec['source_scene_index']),
                                'source_fingerprint': spec['source_fingerprint'],
                                'destination_beat': float(spec['destination_beat'])})
                result.update(created_copies=created, completed_actions=len(created))
            if expected_end is not None:
                actual_end = max([0.0] + [float(clip.end_time) for track in song.tracks for clip in self._track_arrangement_clips(track)])
                if abs(actual_end - float(expected_end)) > .00001:
                    raise RuntimeError('Session-to-arrangement copy length readback did not reach the approved end')
            result.update(created_copies=created, session_to_arrangement_verified=True)
            complete()
        except Exception as exc:
            result['created_copies'] = created
            failed(exc)
        return True

    def _production_rollback_session_to_arrangement_copies(self, item, result, complete, failed):
        song = self.song()
        tracks = {self._composition_track_id(track): track for track in song.tracks}
        targets = []
        try:
            for spec in item['copies']:
                track = tracks.get(spec.get('track_id'))
                if track is None or not callable(getattr(track, 'delete_clip', None)):
                    raise RuntimeError('Session-to-arrangement rollback target track is unavailable')
                s_idx = int(spec['source_scene_index'])
                if (s_idx < 0 or s_idx >= len(track.clip_slots) or not track.clip_slots[s_idx].has_clip or
                        self._composition_clip_snapshot(track.clip_slots[s_idx].clip) != spec['source_fingerprint']):
                    raise RuntimeError('Expected Session source clip is missing or changed')
                matches = [clip for clip in self._track_arrangement_clips(track)
                           if abs(float(clip.start_time) - float(spec['destination_beat'])) < .00001 and
                           self._composition_clip_snapshot(clip) == spec['source_fingerprint']]
                if len(matches) != 1:
                    raise RuntimeError('Expected session-to-arrangement copy is missing or changed')
                targets.append((track, matches[0], spec))
            for track, clip, _spec in targets:
                track.delete_clip(clip)
                if clip in self._track_arrangement_clips(track):
                    raise RuntimeError('Session-to-arrangement copy deletion readback did not match')
            if self._production_observable_rollback_revision() != item['expected_post_rollback_observable_revision']:
                raise RuntimeError('Session-to-arrangement rollback did not restore the exact original state')
            result.update(deleted_copies=len(targets), session_to_arrangement_rollback_verified=True)
            complete()
        except Exception as exc:
            failed(exc)
        return True

    def _production_apply(self, action):
        job_id = str(uuid.UUID(action['job_id']))
        directory = os.path.join(os.path.expanduser('~'), '.vibelton', 'production-executions')
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, job_id + '.json')
        if os.path.exists(path):
            raise RuntimeError('Production command already attempted; automatic replay rejected')
        result = {'job_id': job_id, 'status': 'Queued', 'completed_actions': 0,
                  'session_id': self._composition_session, 'started_at': time.time()}

        def persist():
            with open(path + '.tmp', 'w') as handle:
                json.dump(result, handle)
            os.replace(path + '.tmp', path)

        persist()
        mutated = False
        try:
            prepared = self._production_preflight(action)
            before, after = [], []
            for index, (kind, payload) in enumerate(prepared):
                if kind in ('session_apply', 'session_rollback'):
                    def complete_session():
                        result.update(action_index=index, completed_actions=1, status='Applied', before=before, after=after,
                                      post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()
                        self._log('production_applied', 'Session scenes changed and read back', {'job_id': job_id})

                    def fail_session(exc):
                        result.update(status='Partial failure' if result.get('created_scenes') else 'Failed',
                                      error=str(exc), post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()

                    if kind == 'session_apply':
                        self._production_apply_session_scenes(payload[0], payload[1], result, complete_session, fail_session)
                    else:
                        self._production_rollback_session_scenes(payload, result, complete_session, fail_session)
                    return
                if kind in ('session_to_arrangement_apply', 'session_to_arrangement_rollback'):
                    def complete_s2a():
                        result.update(action_index=index, completed_actions=1, status='Applied', before=before, after=after,
                                      post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()
                        self._log('production_applied', 'Session-to-arrangement copies changed and read back', {'job_id': job_id})

                    def fail_s2a(exc):
                        result.update(status='Partial failure' if result.get('created_copies') else 'Failed',
                                      error=str(exc), post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()

                    if kind == 'session_to_arrangement_apply':
                        self._production_apply_session_to_arrangement_copies(payload[0], payload[1], result, complete_s2a, fail_s2a)
                    else:
                        self._production_rollback_session_to_arrangement_copies(payload, result, complete_s2a, fail_s2a)
                    return
                if kind == 'arrangement_apply':
                    def complete_arrangement():
                        result.update(action_index=index, completed_actions=1, status='Applied', before=before, after=after,
                                      post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()
                        self._log('production_applied', 'Arrangement copies and locators applied and read back', {'job_id': job_id})

                    def fail_arrangement(exc):
                        result.update(status='Partial failure', error=str(exc),
                                      post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()

                    self._production_apply_arrangement_copies(payload[0], payload[1], payload[2], payload[3], payload[4], result,
                                                              complete_arrangement, fail_arrangement)
                    return
                if kind == 'locator_probe':
                    def complete_probe():
                        result.update(action_index=index, completed_actions=1, status='Applied', before=before, after=after,
                                      post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()
                        self._log('production_applied', 'Locator probe passed: cue readback is exact', {'job_id': job_id})

                    def fail_probe(exc):
                        result.update(status='Failed', error=str(exc), finished_at=time.time())
                        persist()

                    self._production_probe_locators(result, complete_probe, fail_probe)
                    return
                if kind == 'arrangement_rollback':
                    def complete_arrangement_rollback():
                        result.update(action_index=index, completed_actions=1, status='Applied', before=before, after=after,
                                      post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()
                        self._log('production_applied', 'Arrangement copies and locators rolled back and read back', {'job_id': job_id})

                    def fail_arrangement_rollback(exc):
                        result.update(status='Partial failure', error=str(exc), finished_at=time.time())
                        persist()

                    self._production_rollback_arrangement_copies(payload, result, complete_arrangement_rollback,
                                                                  fail_arrangement_rollback)
                    return
                if kind == 'template':
                    def complete_template():
                        result.update(action_index=index, completed_actions=1, status='Applied', before=before, after=after,
                                      post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()
                        self._log('production_applied', 'Production actions applied and read back', {'job_id': job_id})

                    def fail_template(exc):
                        result.update(status='Partial failure', error=str(exc), finished_at=time.time())
                        persist()

                    if self._production_apply_template(payload[0], payload[1], result, complete_template, fail_template):
                        return
                    mutated = True
                    result['action_index'] = index
                    result['completed_actions'] += 1
                    persist()
                    continue
                if kind == 'template_rollback':
                    def complete_rollback():
                        result.update(action_index=index, completed_actions=1, status='Applied', before=before, after=after,
                                      post_revision=self._production_state()['revision'], finished_at=time.time())
                        persist()
                        self._log('production_applied', 'Production actions applied and read back', {'job_id': job_id})

                    def fail_rollback(exc):
                        result.update(status='Partial failure', error=str(exc), finished_at=time.time())
                        persist()

                    if self._production_rollback_template(payload, result, complete_rollback, fail_rollback):
                        return
                    mutated = True
                    result['action_index'] = index
                    result['completed_actions'] += 1
                    persist()
                    continue
                if kind == 'device_parameter':
                    track, dev_idx, param_idx, param, target_val = payload
                    tid = self._composition_track_id(track)
                    orig_val = float(param.value)
                    before.append({'type': 'set_device_parameter', 'target_track_id': tid,
                                   'device_index': dev_idx, 'parameter_index': param_idx, 'value': orig_val})
                    param.value = target_val
                    obs_val = float(param.value)
                    if abs(obs_val - target_val) > 0.000001:
                        raise RuntimeError('Production device parameter readback did not match')
                    after.append({'type': 'set_device_parameter', 'target_track_id': tid,
                                  'device_index': dev_idx, 'parameter_index': param_idx, 'value': obs_val})
                    mutated = True
                    result['action_index'] = index
                    result['completed_actions'] += 1
                    persist()
                    continue
                track, values = payload
                mixer = track.mixer_device
                sends_list = list(getattr(mixer, 'sends', ()) or ())

                def _read_mixer_key(k):
                    if k == 'volume':
                        return float(mixer.volume.value)
                    if k == 'pan':
                        return float(mixer.panning.value)
                    if k == 'send_0':
                        return float(sends_list[0].value)
                    if k == 'send_1':
                        return float(sends_list[1].value)
                    if k == 'sends':
                        return [float(sends_list[i].value) for i in range(len(values['sends']))]
                    raise RuntimeError('Unsupported mixer key')

                original = {key: _read_mixer_key(key) for key in values}
                before.append({'target_track_id': self._composition_track_id(track), 'values': original})
                if 'volume' in values:
                    mixer.volume.value = values['volume']
                if 'pan' in values:
                    mixer.panning.value = values['pan']
                if 'send_0' in values:
                    sends_list[0].value = values['send_0']
                if 'send_1' in values:
                    sends_list[1].value = values['send_1']
                if 'sends' in values:
                    for s_idx, s_val in enumerate(values['sends']):
                        sends_list[s_idx].value = s_val
                observed = {key: _read_mixer_key(key) for key in values}
                # Live parameters are represented as floating point values and
                # may quantize a requested value by a few ULPs.  Treat this as
                # successful readback while still rejecting a material mismatch.
                for key in values:
                    if key == 'sends':
                        if any(abs(observed['sends'][i] - values['sends'][i]) > 0.000001 for i in range(len(values['sends']))):
                            raise RuntimeError('Production mixer readback did not match')
                    elif abs(observed[key] - values[key]) > 0.000001:
                        raise RuntimeError('Production mixer readback did not match')
                after.append({'target_track_id': self._composition_track_id(track), 'values': observed})
                mutated = True
                result['action_index'] = index
                result['completed_actions'] += 1
                persist()
            result.update(status='Applied', before=before, after=after,
                          post_revision=self._production_state()['revision'], finished_at=time.time())
            persist()
            self._log('production_applied', 'Production actions applied and read back', {'job_id': job_id})
        except Exception as exc:
            result.update(status='Partial failure' if mutated else 'Failed', error=str(exc), finished_at=time.time())
            persist()
            raise

    def _composition_read_notes(self, clip):
        if not clip.is_midi_clip:
            return None
        if hasattr(clip, 'get_notes_extended'):
            notes = clip.get_notes_extended(0, 128, 0.0, float(clip.length))
            return sorted((int(n.pitch), round(float(n.start_time), 4), round(float(n.duration), 4),
                           round(float(n.velocity)), bool(n.mute)) for n in notes)
        return sorted((int(n[0]), round(float(n[1]), 4), round(float(n[2]), 4), int(n[3]), bool(n[4]))
                      for n in clip.get_notes(0.0, 0, float(clip.length), 128))

    def _clip_musical_summary(self, clip):
        if bool(getattr(clip, 'is_midi_clip', False)):
            notes = self._composition_read_notes(clip) or []
            pitches = [n[0] for n in notes]
            return {
                'kind': 'midi',
                'note_count': len(notes),
                'pitch_min': min(pitches) if pitches else None,
                'pitch_max': max(pitches) if pitches else None,
                'pitch_classes': sorted({p % 12 for p in pitches}),
                'notes_preview': [
                    {'pitch': n[0], 'start': n[1], 'duration': n[2], 'velocity': n[3], 'mute': n[4]}
                    for n in notes[:128]
                ],
            }
        if bool(getattr(clip, 'is_audio_clip', False)):
            snap = audio_snapshot(clip)
            return {
                'kind': 'audio',
                'file_path': snap.get('file_path', ''),
                'warping': snap.get('warping', False),
                'looping': snap.get('looping', False),
                'pitch_coarse': snap.get('pitch_coarse', 0),
                'pitch_fine': snap.get('pitch_fine', 0.0),
                'gain': snap.get('gain', 0.0),
            }
        return None

    def _composition_clip_snapshot(self, clip):
        data = {'name': str(clip.name), 'length': float(clip.length),
                'loop_start': float(clip.loop_start), 'loop_end': float(clip.loop_end),
                'metre': [int(clip.signature_numerator), int(clip.signature_denominator)],
                'notes': self._composition_read_notes(clip)}
        if bool(getattr(clip, 'is_audio_clip', False)):
            data['audio'] = audio_snapshot(clip)
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def _composition_sound_snapshot(self, track):
        def device_state(device):
            return {'name': str(device.name), 'class': str(getattr(device, 'class_name', '')),
                    'parameters': [(str(p.name), float(p.value)) for p in device.parameters],
                    'chains': [[device_state(d) for d in chain.devices] for chain in getattr(device, 'chains', [])]}
        mixer = track.mixer_device
        return {'devices': [device_state(d) for d in track.devices],
                'volume': float(mixer.volume.value), 'pan': float(mixer.panning.value),
                'sends': [float(p.value) for p in mixer.sends],
                'routing': str(getattr(getattr(track, 'output_routing_type', None), 'display_name', ''))}

    def _composition_preflight(self, action):
        song = self.song()
        if action.get('session_id') != self._composition_session:
            raise RuntimeError('Live session changed; refresh track assignments')
        if action.get('scene_count') != len(song.scenes):
            raise RuntimeError('Session scenes changed since compilation')
        bpm = action.get('bpm')
        if not isinstance(bpm, (int, float)) or not math.isfinite(bpm) or not 40 <= bpm <= 240:
            raise RuntimeError('Invalid composition tempo')
        start, length = action.get('start_beat'), action.get('total_beats')
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in (start, length)) or start < 0 or not 0 < length <= 3600:
            raise RuntimeError('Invalid arrangement range')
        tracks = {self._composition_track_id(t): t for t in song.tracks}
        for ref in action['tracks']:
            track = tracks.get(ref['id'])
            if track is None or track.name != ref['name'] or not track.has_midi_input:
                raise RuntimeError('A target MIDI track is missing or changed')
        # Full-song range is empty across ALL tracks, including audio.
        for track in song.tracks:
            for clip in self._track_arrangement_clips(track):
                if clip.start_time < start + length and clip.end_time > start:
                    raise RuntimeError('Arrangement range is occupied')
        pairs, allowed = set(), {ref['id'] for ref in action['tracks']}
        if not action['clips']:
            raise RuntimeError('No clips to apply')
        for clip in action['clips']:
            track = tracks.get(clip['track_id'])
            if track is None or clip['track_id'] not in allowed or not hasattr(track, 'duplicate_clip_to_arrangement'):
                raise RuntimeError('Target cannot receive arrangement clips')
            slot = clip['scene_index']
            if type(slot) is not int or not len(song.scenes) <= slot < len(song.scenes) + 64:
                raise RuntimeError('Composition must use new Session scenes')
            pair = (clip['track_id'], slot)
            if pair in pairs:
                raise RuntimeError('Multiple clips target the same slot')
            pairs.add(pair)
            if slot < len(track.clip_slots) and track.clip_slots[slot].has_clip:
                raise RuntimeError('Target slot is occupied')
            if tuple(clip['metre']) not in ((4, 4), (3, 4), (5, 4), (7, 8), (9, 8)):
                raise RuntimeError('Unsupported metre')
            at, size = clip['start_beat'], clip['length_beats']
            if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in (at, size)) or size <= 0 or at < start or at + size > start + length + .00001:
                raise RuntimeError('Clip outside composition range')
            if not isinstance(clip['notes'], list) or len(clip['notes']) > 150000:
                raise RuntimeError('Too many notes')
            for n in clip['notes']:
                for key in ('start', 'duration', 'pitch', 'velocity'):
                    if not isinstance(n[key], (int, float)) or not math.isfinite(n[key]):
                        raise RuntimeError('Invalid note value')
                if n['start'] < 0 or n['duration'] < .001 or n['start'] + n['duration'] > size + .00001 or not 0 <= n['pitch'] <= 127 or not 1 <= n['velocity'] <= 127:
                    raise RuntimeError('Invalid MIDI note')
                if 'probability' in n and n['probability'] is not None:
                    prob = n['probability']
                    if isinstance(prob, bool) or not isinstance(prob, (int, float)) or not math.isfinite(prob) or not 0.0 < prob <= 1.0:
                        raise RuntimeError('Invalid MIDI note probability')
                if 'velocity_deviation' in n and n['velocity_deviation'] is not None:
                    vdev = n['velocity_deviation']
                    if isinstance(vdev, bool) or not isinstance(vdev, (int, float)) or not math.isfinite(vdev) or not -127 <= vdev <= 127:
                        raise RuntimeError('Invalid MIDI note velocity_deviation')
        return tracks

    def _composition_apply(self, action):
        job_id = str(uuid.UUID(action['job_id']))
        directory = os.path.join(os.path.expanduser('~'), '.vibelton', 'composition-executions')
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, job_id + '.json')
        if os.path.exists(path):
            raise RuntimeError('Composition command already attempted; automatic replay rejected')
        result = {'job_id': job_id, 'status': 'Queued', 'completed_clips': 0, 'readback_verified': False,
                  'session_id': self._composition_session, 'started_at': time.time()}

        def persist():
            with open(path + '.tmp', 'w') as handle:
                json.dump(result, handle)
            os.replace(path + '.tmp', path)

        persist()
        mutated = False
        try:
            tracks = self._composition_preflight(action)
            song = self.song()
            song.stop_playing()
            sounds = {key: self._composition_sound_snapshot(track) for key, track in tracks.items()}
            originals = [(slot.clip, self._composition_clip_snapshot(slot.clip)) for track in song.tracks
                         for slot in track.clip_slots if slot.has_clip]
            original_arrangement = [(c, self._composition_clip_snapshot(c), float(c.start_time), float(c.end_time))
                                    for track in song.tracks for c in self._track_arrangement_clips(track)]
            # Reject existing tempo automation rather than silently defeating steady tempo.
            tempo_parameter = song.master_track.mixer_device.song_tempo
            if int(getattr(tempo_parameter, 'automation_state', 0)) != 0:
                raise RuntimeError('Tempo automation is present. Use a working copy with steady tempo before applying.')
            mutated = True
            song.tempo = float(action['bpm'])
            max_scene = max(c['scene_index'] for c in action['clips'])
            while len(song.scenes) <= max_scene:
                song.create_scene(-1)
                song.scenes[-1].name = 'Composition Lab · ' + job_id[:8]
            expected = []
            for index, spec in enumerate(action['clips']):
                result['action_index'] = index
                track = tracks[spec['track_id']]
                slot = track.clip_slots[spec['scene_index']]
                if slot.has_clip:
                    raise RuntimeError('Target slot became occupied; stopped without overwriting')
                slot.create_clip(float(spec['length_beats']))
                clip = slot.clip
                clip.name = spec['name']
                clip.signature_numerator, clip.signature_denominator = spec['metre']
                clip.loop_start = 0.0
                clip.loop_end = float(spec['length_beats'])
                clip.start_marker = 0.0
                clip.end_marker = float(spec['length_beats'])
                clip.looping = True
                has_extended = any(
                    ('probability' in n and n['probability'] is not None) or ('velocity_deviation' in n and n['velocity_deviation'] is not None)
                    for n in spec['notes']
                )
                raw = tuple((int(n['pitch']), float(n['start']), float(n['duration']), int(n['velocity']), bool(n.get('mute', False))) for n in spec['notes'])
                if has_extended and hasattr(clip, 'add_new_notes'):
                    extended_notes = []
                    for n in spec['notes']:
                        nd = {
                            'pitch': int(n['pitch']),
                            'start_time': float(n['start']),
                            'duration': float(n['duration']),
                            'velocity': int(n['velocity']),
                            'mute': bool(n.get('mute', False)),
                        }
                        if 'probability' in n and n['probability'] is not None:
                            nd['probability'] = float(n['probability'])
                        if 'velocity_deviation' in n and n['velocity_deviation'] is not None:
                            nd['velocity_deviation'] = float(n['velocity_deviation'])
                        extended_notes.append(nd)
                    try:
                        clip.add_new_notes({'notes': extended_notes})
                    except (TypeError, ValueError, RuntimeError):
                        try:
                            clip.add_new_notes(tuple(extended_notes))
                        except (TypeError, ValueError, RuntimeError):
                            spec_cls = self._midi_note_specification_cls()
                            if callable(spec_cls):
                                try:
                                    clip.add_new_notes(tuple(spec_cls(**nd) for nd in extended_notes))
                                except (TypeError, ValueError, RuntimeError):
                                    if hasattr(clip, 'set_notes'):
                                        clip.set_notes(raw)
                                        result['extended_notes_degraded'] = True
                                    else:
                                        raise
                            elif hasattr(clip, 'set_notes'):
                                clip.set_notes(raw)
                                result['extended_notes_degraded'] = True
                            else:
                                raise
                elif hasattr(clip, 'set_notes'):
                    # Legacy _write_notes clamps duration; preserve this score's validated durations.
                    clip.set_notes(raw)
                elif hasattr(clip, 'add_new_notes'):
                    basic_notes = tuple({
                        'pitch': int(n['pitch']),
                        'start_time': float(n['start']),
                        'duration': float(n['duration']),
                        'velocity': int(n['velocity']),
                        'mute': bool(n.get('mute', False)),
                    } for n in spec['notes'])
                    try:
                        clip.add_new_notes({'notes': list(basic_notes)})
                    except (TypeError, ValueError, RuntimeError):
                        clip.add_new_notes(basic_notes)
                else:
                    raise RuntimeError('Clip does not expose set_notes or add_new_notes')

                track.duplicate_clip_to_arrangement(clip, float(spec['start_beat']))
                expected.append((track, spec, self._composition_clip_snapshot(clip)))
                result['completed_clips'] += 1
                persist()
            readback = []
            for track, spec, fingerprint in expected:
                matches = [c for c in self._track_arrangement_clips(track) if c.name == spec['name'] and abs(c.start_time - spec['start_beat']) < .0001]
                if len(matches) != 1:
                    raise RuntimeError('Arrangement clip readback did not match')
                clip = matches[0]
                if abs(clip.end_time - spec['start_beat'] - spec['length_beats']) > .0001 or self._composition_clip_snapshot(clip) != fingerprint:
                    raise RuntimeError('Arrangement length, notes or metre did not match')
                readback.append({'name': clip.name, 'start_beat': float(clip.start_time), 'end_beat': float(clip.end_time), 'metre': spec['metre']})
            if any(self._composition_clip_snapshot(c) != fingerprint for c, fingerprint in originals):
                raise RuntimeError('Original Session clip preservation check failed')
            if any(self._composition_clip_snapshot(c) != fp or c.start_time != start or c.end_time != end for c, fp, start, end in original_arrangement):
                raise RuntimeError('Original Arrangement preservation check failed')
            if any(self._composition_sound_snapshot(tracks[key]) != snapshot for key, snapshot in sounds.items()):
                raise RuntimeError('Instrument or mixer preservation check failed')
            result.update(status='Applied', readback_verified=True, preserved_originals=True, clips=readback,
                          finished_at=time.time(), markers_pending=True)
            persist()
            try:
                self.application().view.show_view('Arranger')
                song.current_song_time = float(action['start_beat'])
                song.loop_start = float(action['start_beat'])
                song.loop_length = float(action['total_beats'])
                song.loop = bool(action['preview'])
                if action['preview']:
                    song.stop_all_clips()
                    song.back_to_arranger = False
                    song.start_playing()
            except Exception as exc:
                result['preview_error'] = str(exc)
                persist()
            self._log('composition_applied', 'Composition clips verified; Arrangement metre markers pending', {'job_id': job_id})
        except Exception as exc:
            result.update(status='Partial failure' if mutated else 'Failed', error=str(exc), finished_at=time.time())
            persist()
            raise
