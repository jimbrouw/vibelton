"""Guarded audio imports. Never edits an existing clip or replaces a slot."""
import hashlib
import json
import math
import os
import time
import uuid


def audio_snapshot(clip):
    data = {'file_path': str(clip.file_path), 'warping': bool(clip.warping),
            'looping': bool(clip.looping), 'start_marker': float(clip.start_marker),
            'end_marker': float(clip.end_marker), 'loop_start': float(clip.loop_start),
            'loop_end': float(clip.loop_end), 'pitch_coarse': int(clip.pitch_coarse),
            'pitch_fine': float(clip.pitch_fine), 'gain': float(clip.gain),
            'warp_mode': int(clip.warp_mode)}
    if data['warping']:
        markers = clip.warp_markers
        if isinstance(markers, dict):
            markers = markers['warp_markers']
        data['warp_markers'] = [{'beat_time': float(m['beat_time'] if isinstance(m, dict) else m.beat_time),
                                 'sample_time': float(m['sample_time'] if isinstance(m, dict) else m.sample_time)}
                                for m in markers]
    return data


class AudioBridge:
    def _audio_import(self, action):
        job_id = str(uuid.UUID(action['job_id']))
        directory = os.path.join(os.path.expanduser('~'), '.vibelton', 'sample-executions')
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, job_id + '.json')
        if os.path.exists(path):
            raise RuntimeError('Audio job already attempted; automatic replay rejected')
        result = {'job_id': job_id, 'status': 'Queued', 'readback_verified': False,
                  'session_id': self._composition_session, 'created_at': time.time(), 'created_clips': []}
        def persist():
            with open(path + '.tmp', 'w') as stream:
                json.dump(result, stream, allow_nan=False)
            os.replace(path + '.tmp', path)
        persist()
        mutated = False
        try:
            song = self.song()
            project = self._production_state()
            if action.get('session_id') != self._composition_session or action.get('source_revision') != project['revision']:
                raise RuntimeError('Live session or material changed before audio import')
            if not project['arrangement_readable']:
                raise RuntimeError('Arrangement readback is incomplete')
            if action.get('working_copy_confirmed') is not True or not action.get('expected_set_path') or action['expected_set_path'] != str(getattr(song, 'file_path', '')):
                raise RuntimeError('Active working copy does not match')
            source = os.path.realpath(action['path'])
            root = os.path.realpath(os.path.join(os.path.expanduser('~'), 'Music', 'LOOP PACKS'))
            if os.path.commonpath([root, source]) != root or not os.path.isfile(source):
                raise RuntimeError('Audio source is outside the loop library')
            digest = hashlib.sha256()
            with open(source, 'rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() != action['sha256']:
                raise RuntimeError('Audio source changed before import')
            scene = action['scene_index']
            if type(scene) is not int or scene != len(song.scenes):
                raise RuntimeError('Audio import must append a fresh scene')
            tracks = {self._composition_track_id(t): t for t in song.tracks}
            track = tracks.get(action['track_id'])
            if track is None or track.name != action['target_name'] or bool(getattr(track, 'is_foldable', False)) or bool(track.has_midi_input) or bool(getattr(track, 'is_frozen', False)):
                raise RuntimeError('Audio target is missing, changed, grouped or frozen')
            if not track.clip_slots or not callable(getattr(track.clip_slots[0], 'create_audio_clip', None)):
                raise RuntimeError('Live does not expose audio import on this track')
            settings = action['settings']
            allowed = {'warping', 'looping', 'start_marker', 'end_marker', 'loop_start', 'loop_end', 'pitch_coarse', 'pitch_fine', 'gain', 'warp_mode'}
            if not isinstance(settings, dict) or set(settings) - allowed:
                raise RuntimeError('Unknown audio clip setting')
            if 'warping' not in settings:
                raise RuntimeError('Specify warping explicitly so marker units are unambiguous')
            bounds = {'start_marker': (0,1576800), 'end_marker': (.001,1576800),
                      'loop_start': (0,1576800), 'loop_end': (.001,1576800),
                      'pitch_coarse': (-48,48), 'pitch_fine': (-50,49), 'gain': (0,1), 'warp_mode': (0,10)}
            for key, value in settings.items():
                if key in ('warping', 'looping'):
                    if type(value) is not bool:
                        raise RuntimeError('Invalid audio boolean')
                elif isinstance(value, bool) or not isinstance(value, (float,int)) or not math.isfinite(value) or not bounds[key][0] <= value <= bounds[key][1]:
                    raise RuntimeError('Invalid audio setting')
                if key in ('pitch_coarse','warp_mode') and type(value) is not int:
                    raise RuntimeError('Invalid audio integer')
            for left,right in (('start_marker','end_marker'),('loop_start','loop_end')):
                if left in settings and right in settings and settings[left] >= settings[right]:
                    raise RuntimeError('Invalid audio range')
            if settings.get('warping') is False and settings.get('looping'):
                raise RuntimeError('Unwarped audio cannot loop')
            duration = action.get('duration_seconds')
            if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration <= 0:
                raise RuntimeError('Invalid measured source duration')
            source_bpm = action.get('source_bpm')
            if settings.get('warping') is True:
                if isinstance(source_bpm,bool) or not isinstance(source_bpm,(int,float)) or not math.isfinite(source_bpm) or not 40 <= source_bpm <= 240:
                    raise RuntimeError('Confirm source BPM before importing warped audio')
            if 'warping' in settings:
                maximum = duration * (source_bpm / 60 if settings['warping'] else 1)
                if any(settings.get(key,0) > maximum + .001 for key in ('start_marker','end_marker','loop_start','loop_end')):
                    raise RuntimeError('Audio marker exceeds measured source duration')
            beat = action.get('arrangement_beat')
            region = action.get('region')
            if beat is not None:
                if settings.get('warping') is not True:
                    raise RuntimeError('Arrangement imports require explicit warping=true')
                if isinstance(beat,bool) or not isinstance(beat,(float,int)) or not math.isfinite(beat) or not 0 <= beat <= 1576800:
                    raise RuntimeError('Audio Arrangement destination is not a fresh range')
                if region is not None:
                    region_id = str(uuid.UUID(region['id']))
                    region_path = os.path.join(os.path.expanduser('~'), '.vibelton', 'sample-regions', region_id + '.json')
                    with open(region_path) as stream:
                        recorded = json.load(stream)
                    if recorded != region or region['session_id'] != self._composition_session or region['set_path'] != str(song.file_path):
                        raise RuntimeError('Reserved prototype range changed or belongs to another Set')
                    if not region['start_beat'] <= beat < region['start_beat'] + region['length_beats']:
                        raise RuntimeError('Audio destination is outside the reserved prototype range')
                elif beat < project['arrangement_end'] + 4:
                    raise RuntimeError('Audio Arrangement destination is not a fresh range')
                if not callable(getattr(track, 'duplicate_clip_to_arrangement', None)):
                    raise RuntimeError('Audio Arrangement copy is unavailable')
            # Capture content, positions, track count and sounds before any mutation.
            originals = [(slot.clip, self._composition_clip_snapshot(slot.clip))
                         for t in song.tracks for slot in t.clip_slots if slot.has_clip]
            arrangement = [(c, self._composition_clip_snapshot(c), float(c.start_time), float(c.end_time))
                           for t in song.tracks if not bool(getattr(t, 'is_foldable', False))
                           for c in t.arrangement_clips]
            sounds = {key: self._composition_sound_snapshot(t) for key,t in tracks.items()}
            scene_names = [str(s.name) for s in song.scenes]
            tempo = float(song.tempo)
            mutated = True
            song.create_scene(-1)
            song.scenes[-1].name = 'DnB sample · ' + job_id[:8]
            result['created_scene_index'] = scene
            persist()
            slot = track.clip_slots[scene]
            if slot.has_clip:
                raise RuntimeError('New sample slot became occupied')
            slot.create_audio_clip(source)
            clip = slot.clip
            result['created_clips'].append({'track_id': action['track_id'], 'scene_index': scene})
            persist()
            if clip is None or not clip.is_audio_clip:
                raise RuntimeError('Audio import did not create an audio clip')
            clip.name = action['name']
            # Inspect all required properties before configuring the new clip.
            audio_snapshot(clip)
            if 'warping' in settings:
                clip.warping = settings['warping']
            if clip.warping:
                if source_bpm is None:
                    raise RuntimeError('Imported audio is warped; confirm source BPM explicitly')
                markers = audio_snapshot(clip)['warp_markers']
                if len(markers) < 2:
                    raise RuntimeError('Warp timing readback is insufficient')
                markers = sorted(markers,key=lambda m:m['sample_time'])
                # Check the actual source-to-beat mapping, not Live's Warp checkbox.
                for marker in markers:
                    if abs(marker['beat_time'] - marker['sample_time'] * source_bpm / 60) > .01:
                        raise RuntimeError('Imported warp timing does not match confirmed source BPM; no Arrangement copy made')
            if settings.get('looping') and not clip.warping:
                raise RuntimeError('Looping requires a warped clip')
            # Extend upper bounds first; then move lower bounds, then final upper bounds.
            for left,right in (('start_marker','end_marker'),('loop_start','loop_end')):
                if right in settings and settings[right] > float(getattr(clip,right)):
                    setattr(clip,right,settings[right])
                if left in settings:
                    setattr(clip,left,settings[left])
                if right in settings:
                    setattr(clip,right,settings[right])
            for key in ('warp_mode','pitch_coarse','pitch_fine','gain','looping'):
                if key in settings:
                    setattr(clip,key,settings[key])
            actual = audio_snapshot(clip)
            for key,value in settings.items():
                if isinstance(value,bool):
                    matches = actual[key] is value
                else:
                    matches = abs(float(actual[key]) - value) <= .0001
                if not matches:
                    raise RuntimeError('Audio setting readback failed: ' + key)
            if os.path.realpath(actual['file_path']) != source:
                raise RuntimeError('Audio source path readback failed')
            fingerprint = self._composition_clip_snapshot(clip)
            result['clip_readback'] = {'name':str(clip.name), 'length':float(clip.length), 'audio':actual}
            if beat is not None:
                if not actual['warping']:
                    raise RuntimeError('Unwarped audio cannot use beat-based Arrangement copy')
                length = float(clip.length)
                if not math.isfinite(length) or length <= 0:
                    raise RuntimeError('Invalid audio clip length')
                # Recheck all tracks immediately before Arrangement mutation.
                if region is not None and beat + length > region['start_beat'] + region['length_beats'] + .0001:
                    raise RuntimeError('Imported clip exceeds the reserved prototype range')
                check_tracks = [track] if region is not None else song.tracks
                if any(c.start_time < beat + length and c.end_time > beat
                       for t in check_tracks if not bool(getattr(t, 'is_foldable', False))
                       for c in t.arrangement_clips):
                    raise RuntimeError('Audio Arrangement range became occupied')
                track.duplicate_clip_to_arrangement(clip, float(beat))
                result['arrangement_requested_beat'] = beat
                persist()
                copies = [c for c in track.arrangement_clips if abs(float(c.start_time)-beat) < .0001]
                if len(copies) != 1 or abs(float(copies[0].end_time)-beat-length) > .0001 or self._composition_clip_snapshot(copies[0]) != fingerprint:
                    raise RuntimeError('Audio Arrangement readback failed')
                result['arrangement_readback'] = {'start_beat':float(copies[0].start_time),'end_beat':float(copies[0].end_time)}
            if any(self._composition_clip_snapshot(c) != fp for c,fp in originals):
                raise RuntimeError('Original Session audio or MIDI changed')
            if any(self._composition_clip_snapshot(c) != fp or float(c.start_time) != start or float(c.end_time) != end for c,fp,start,end in arrangement):
                raise RuntimeError('Original Arrangement audio or MIDI changed')
            if list(tracks) != [self._composition_track_id(t) for t in song.tracks] or any(self._composition_sound_snapshot(tracks[key]) != value for key,value in sounds.items()):
                raise RuntimeError('Original tracks, instruments or mixers changed')
            if [str(s.name) for s in song.scenes[:scene]] != scene_names or len(song.scenes) != scene + 1 or float(song.tempo) != tempo:
                raise RuntimeError('Original scenes or tempo changed')
            result.update(status='Applied', readback_verified=True, preserved_originals=True, finished_at=time.time())
            persist()
            self._log('audio_import_applied','Audio import and settings readback passed',{'job_id':job_id})
        except Exception as exc:
            result.update(status='Partial failure' if mutated else 'Failed', error=str(exc), finished_at=time.time())
            persist()
            raise
