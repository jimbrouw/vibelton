"""Composition Lab: editable scores compiled into deterministic, sound-safe MIDI.

All times are quarter-note beats. This module never talks to Live or the queue.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import random
from pathlib import Path
from .harmony import plan_harmony

ROLES = ('drums', 'percussion', 'bass', 'chords', 'motif', 'counterline')
METRES = ((4, 4), (3, 4), (5, 4), (7, 8), (9, 8))
EXPRESSIONS = ('density', 'syncopation', 'swing', 'timing', 'tension', 'space')
INGREDIENTS = ('interlocking', 'angular', 'spacious', 'jungle', 'uk_bass', 'sparse')


def number(value, low, high, label, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('%s must be a finite number' % label)
    if not low <= value <= high or (integer and int(value) != value):
        raise ValueError('%s must be between %s and %s%s' % (label, low, high, ' (whole numbers)' if integer else ''))
    return value


def beats_per_bar(metre):
    if not isinstance(metre, list) or len(metre) != 2 or tuple(metre) not in METRES:
        raise ValueError('Choose 4/4, 3/4, 5/4, 7/8 or 9/8')
    return metre[0] * 4 / metre[1]


def default_document():
    sections = []
    rows = [('Opening signal', [7, 8], 16, .3, ['percussion', 'motif'], 'original'),
            ('First groove', [7, 8], 32, .65, ['drums', 'percussion', 'bass', 'motif'], 'displace'),
            ('Fracture', [5, 4], 24, .8, ['drums', 'bass', 'chords', 'motif'], 'fragment'),
            ('Open space', [3, 4], 32, .25, ['chords', 'motif', 'counterline'], 'stretch'),
            ('Collision', [7, 8], 64, .95, list(ROLES), 'return')]
    for pair in range(8):
        for metre in ([7, 8], [9, 8]):
            rows.append(('Exit %d · %d/%d' % (pair + 1, *metre), metre, 1,
                         max(.15, .6 - pair * .06), ['percussion', 'bass', 'motif'], 'fragment'))
    for i, (name, metre, bars, energy, roles, transform) in enumerate(rows):
        sections.append({'id': 'section-%02d' % (i + 1), 'name': name, 'metre': metre,
                         'grouping': {3: [3], 5: [3, 2], 7: [2, 2, 3], 9: [2, 2, 2, 3]}[metre[0]],
                         'bars': bars, 'energy': energy, 'active_parts': roles, 'locked': False,
                         'motif_transform': transform, 'motif_id': 'signal', 'parts': {}})
    return {'title': 'Signals from elsewhere', 'brief': 'Interlocking percussion, angular phrases and broken beats. A recurring signal becomes fractured, opens into space, then returns.',
            'mood': 'Expressive, restless, spacious', 'bpm': 168, 'target_seconds': 240, 'seed': 1687,
            'root_midi': 57, 'mode': 'minor', 'motif': [0, 3, 7, 2, 10],
            'ingredients': {'rhythm': ['interlocking', 'jungle', 'uk_bass'], 'harmony': ['spacious'],
                            'phrasing': ['angular', 'sparse'], 'structure': ['spacious', 'angular']},
            'expression': {'density': .6, 'syncopation': .6, 'swing': .15, 'timing': .15, 'tension': .4, 'space': .3},
            'assignments': {role: None for role in ROLES}, 'sound_locks': {role: True for role in ROLES},
            'drum_notes': {'kick': 36, 'snare': 38, 'hat': 42, 'percussion': 60}, 'sections': sections}


def validate(doc):
    if not isinstance(doc, dict):
        raise ValueError('Composition must be an object')
    number(doc['bpm'], 40, 240, 'Tempo')
    number(doc['target_seconds'], 10, 900, 'Target duration')
    number(doc['seed'], 0, 2147483647, 'Seed', True)
    number(doc['root_midi'], 24, 84, 'Root note', True)
    if doc['mode'] not in ('minor', 'major'):
        raise ValueError('Mode must be minor or major')
    if not isinstance(doc['motif'], list) or not 1 <= len(doc['motif']) <= 32:
        raise ValueError('Motif needs 1–32 intervals')
    for interval in doc['motif']:
        number(interval, -24, 24, 'Motif interval', True)
    for field in ('title', 'brief', 'mood'):
        if not isinstance(doc[field], str) or len(doc[field]) > 4000:
            raise ValueError('Invalid %s' % field)
    for key in EXPRESSIONS:
        number(doc['expression'][key], 0, 1, key)
    for values in doc['ingredients'].values():
        if not isinstance(values, list) or any(v not in INGREDIENTS for v in values):
            raise ValueError('Unknown musical ingredient')
    for key in ('kick', 'snare', 'hat', 'percussion'):
        number(doc['drum_notes'][key], 0, 127, 'Drum note', True)
    for role in ROLES:
        ref = doc['assignments'][role]
        if ref is not None and (not isinstance(ref, dict) or not all(isinstance(ref.get(k), str) and ref[k] for k in ('id', 'name', 'session_id'))):
            raise ValueError('Invalid track assignment for %s' % role)
        if doc['sound_locks'].get(role) is not True:
            raise ValueError('Sounds remain locked in Composition Lab v1; choose sounds in Ableton')
    if not isinstance(doc['sections'], list) or not 1 <= len(doc['sections']) <= 64:
        raise ValueError('Use 1–64 sections')
    ids, note_count = set(), 0
    for s in doc['sections']:
        if not isinstance(s['id'], str) or not s['id'] or s['id'] in ids:
            raise ValueError('Section IDs must be unique')
        ids.add(s['id'])
        if not isinstance(s['name'], str) or not s['name'].strip() or len(s['name']) > 100:
            raise ValueError('Section needs a name of up to 100 characters')
        length = beats_per_bar(s['metre']) * number(s['bars'], 1, 256, 'Bars', True)
        grouping = s['grouping']
        if not isinstance(grouping, list) or not grouping or any(type(g) is not int or g < 1 for g in grouping) or sum(grouping) != s['metre'][0]:
            raise ValueError('Accent grouping must add up to the metre numerator')
        number(s['energy'], 0, 1, 'Energy')
        if not isinstance(s['locked'], bool):
            raise ValueError('Section lock must be true or false')
        if not isinstance(s['active_parts'], list) or not s['active_parts'] or len(set(s['active_parts'])) != len(s['active_parts']) or any(r not in ROLES for r in s['active_parts']):
            raise ValueError('Select unique musical parts for each section')
        if s['motif_transform'] not in ('original', 'displace', 'fragment', 'stretch', 'return'):
            raise ValueError('Unknown motif transformation')
        if any(r not in ROLES for r in s['parts']):
            raise ValueError('Unknown part role')
        for role, part in s['parts'].items():
            if not isinstance(part.get('locked'), bool) or not isinstance(part.get('notes'), list):
                raise ValueError('Invalid part')
            note_count += len(part['notes'])
            for n in part['notes']:
                number(n['pitch'], 0, 127, 'Pitch', True)
                number(n['velocity'], 1, 127, 'Velocity', True)
                number(n['start'], 0, length, 'Note start')
                number(n['duration'], .001, length, 'Note duration')
                if 'probability' in n and n['probability'] is not None:
                    number(n['probability'], 0.01, 1.0, 'Note probability')
                if 'velocity_deviation' in n and n['velocity_deviation'] is not None:
                    number(n['velocity_deviation'], -127, 127, 'Note velocity deviation')
                if n['start'] + n['duration'] > length + .00001:
                    raise ValueError('Notes must stay inside their section')
    if note_count > 150000 or sum(beats_per_bar(s['metre']) * s['bars'] for s in doc['sections']) > 3600:
        raise ValueError('Composition is too large')
    return doc


def seed_for(*values):
    return int(hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()[:12], 16)


def _phrase_variant_for_bar(bar_idx: int, total_bars: int = 4) -> str:
    mod4 = bar_idx % 4
    if mod4 == 0:
        return 'statement'
    if mod4 == 1:
        return 'continuation'
    if mod4 == 2:
        return 'development'
    if bar_idx % 8 == 7 or bar_idx == total_bars - 1:
        return 'turnaround_B'
    return 'turnaround_A'


def _infer_section_energy_role(section: dict) -> str:
    name = str(section.get('name', '')).lower()
    energy = float(section.get('energy', 0.5))
    if any(k in name for k in ('drop', 'main', 'collision', 'peak')) or energy >= 0.85:
        return 'drop'
    if any(k in name for k in ('break', 'open', 'space', 'bridge')) or energy <= 0.32:
        return 'breakdown'
    if any(k in name for k in ('build', 'fracture', 'riser', 'tension')):
        return 'build'
    if any(k in name for k in ('intro', 'opening')):
        return 'intro'
    return 'main'


def _resolve_bass_root_midi(key: str | int) -> int:
    if isinstance(key, int) and not isinstance(key, bool):
        root = int(key)
        while root >= 48:
            root -= 12
        while root < 33:
            root += 12
        return root
    pitch_map = {
        'C': 36, 'C#': 37, 'DB': 37, 'D': 38, 'D#': 39, 'EB': 39,
        'E': 40, 'F': 41, 'F#': 42, 'GB': 42, 'G': 43, 'G#': 44,
        'AB': 44, 'A': 45, 'A#': 46, 'BB': 46, 'B': 47,
    }
    token = str(key or 'Ab').strip().split()[0]
    if token.endswith('m') and len(token) >= 2 and token[:-1].upper() in pitch_map:
        token = token[:-1]
    return pitch_map.get(token.upper(), 44)


def generate_bass_companion(
    *,
    key: str | int = 'Ab',
    scale: str = 'minor',
    swing: float = 0.0,
    density: str = 'medium',
    movement: str = 'syncopated_hook',
    lock_to_kick_beats: list[float] | None = None,
    bars: int = 4,
    metre: list[int] | tuple[int, int] = (4, 4),
    seed: int = 119,
) -> list[dict]:
    root_midi = _resolve_bass_root_midi(key)
    swing_clamped = max(0.0, min(0.35, float(swing)))
    bar_length = beats_per_bar(list(metre))
    total_length = bar_length * max(1, int(bars))

    raw_kicks = lock_to_kick_beats if lock_to_kick_beats else [0.0, round(bar_length * 0.625, 4)]
    kick_in_bar = sorted({round(float(k) % bar_length, 4) for k in raw_kicks if 0.0 <= float(k) % bar_length < bar_length})
    if not kick_in_bar:
        kick_in_bar = [0.0]

    minor_third = 3 if 'minor' in str(scale).lower() else 4
    if movement == 'pedal':
        intervals = (0, 0, 0, 7)
    elif movement == 'octave_jump':
        intervals = (0, 12, 0, 12)
    elif movement == 'fifth_glide':
        intervals = (0, 7, minor_third, 7)
    else:  # syncopated_hook
        intervals = (0, minor_third, 5, 10)

    # Candidate offbeat rest slots in a bar (16th grid) that avoid colliding with kick hits
    grid_16th = [round(step * 0.25, 4) for step in range(1, int(bar_length * 4))]
    rest_slots = [pos for pos in grid_16th if all(abs(pos - k) >= 0.24 for k in kick_in_bar)]
    if not rest_slots:
        rest_slots = [round(bar_length * 0.5, 4)]

    density_key = str(density or 'medium').lower()
    if density_key == 'sparse':
        locked_kicks = kick_in_bar[:1]
        answer_count = 1
    elif density_key == 'rolling':
        locked_kicks = kick_in_bar
        answer_count = min(len(rest_slots), 4)
    else:  # medium
        locked_kicks = kick_in_bar[:2]
        answer_count = min(len(rest_slots), 2)

    rng = random.Random(seed_for('bass_companion', root_midi, scale, density_key, movement, seed))
    cell_answers_even = sorted(rest_slots[:answer_count])
    cell_answers_odd = sorted(rest_slots[-answer_count:]) if len(rest_slots) >= answer_count else cell_answers_even

    notes: list[dict] = []

    def _emit(pitch: int, start_beat: float, dur: float, vel: int, probability: float = 1.0, velocity_deviation: int = 4) -> None:
        pos = start_beat
        # Apply swing to odd 16th subdivisions
        if int(round(pos * 4.0)) % 2 == 1 and swing_clamped > 0.0:
            pos = min(total_length - 0.01, pos + swing_clamped * 0.25)
        pos = round(max(0.0, min(total_length - 0.01, pos)), 5)
        dur_clamped = round(max(0.001, min(dur, total_length - pos - 0.0001)), 5)
        if pos + dur_clamped > total_length:
            dur_clamped = round(max(0.001, total_length - pos), 5)
        notes.append({
            'pitch': max(0, min(127, int(pitch))),
            'start': pos,
            'duration': dur_clamped,
            'velocity': max(1, min(127, int(vel))),
            'probability': round(max(0.01, min(1.0, float(probability))), 3),
            'velocity_deviation': max(-127, min(127, int(velocity_deviation))),
        })

    for bar in range(int(bars)):
        base = bar * bar_length
        variant = _phrase_variant_for_bar(bar, int(bars))
        # 1. Locked kick hits (always anchoring downbeat/kick pulse)
        for k_idx, k_pos in enumerate(locked_kicks):
            pitch = root_midi if k_idx == 0 else root_midi + intervals[k_idx % len(intervals)]
            dur = 0.45 if density_key != 'rolling' else 0.22
            _emit(pitch, base + k_pos, dur, 98 if k_idx == 0 else 88, probability=1.0, velocity_deviation=4)

        # 2. 2-bar rhythmic cell answers in the gaps between kicks
        answers = cell_answers_even if (bar % 2 == 0) else cell_answers_odd
        for a_idx, a_pos in enumerate(answers):
            if variant in ('turnaround_A', 'turnaround_B') and a_pos >= bar_length - 0.75:
                continue
            interval = intervals[(a_idx + 1 + (bar % 2)) % len(intervals)]
            if variant == 'development' and a_idx == len(answers) - 1:
                interval = 12 if movement == 'octave_jump' else 7
            _emit(root_midi + interval, base + a_pos, 0.24, 82 + (a_idx % 2) * 6, probability=0.9, velocity_deviation=6)

        # 3. Distinct AAAB turnaround / octave pickup on bar 4 / bar 8
        if variant in ('turnaround_A', 'turnaround_B'):
            turn_pos_1 = max(0.25, bar_length - 0.75)
            turn_pos_2 = max(0.5, bar_length - 0.25)
            turn_pitch_1 = root_midi + (12 if movement != 'pedal' else 7)
            turn_pitch_2 = root_midi + (7 if variant == 'turnaround_A' else 10)
            _emit(turn_pitch_1, base + turn_pos_1, 0.22, 92, probability=0.88, velocity_deviation=8)
            _emit(turn_pitch_2, base + turn_pos_2, 0.20, 96, probability=0.92, velocity_deviation=8)

    return sorted(notes, key=lambda n: (n['start'], n['pitch']))


def generate_part(doc, section, role, variation=0):
    rng = random.Random(seed_for(doc['seed'], section['id'], role, variation))
    e = doc['expression']
    area = 'rhythm' if role in ('drums', 'percussion', 'bass') else 'harmony' if role == 'chords' else 'phrasing'
    ingredients = set(doc['ingredients'].get(area, [])) | set(doc['ingredients'].get('structure', []))
    bar_length = beats_per_bar(section['metre'])
    length = bar_length * section['bars']
    unit = 4 / section['metre'][1]
    accents, offset = [], 0
    for group in section['grouping']:
        accents.append(offset * unit)
        offset += group
    energy = section['energy']
    density = min(.98, .25 + e['density'] * .55 + energy * .25 - e['space'] * .3)
    root = doc['root_midi']
    section_kind = _infer_section_energy_role(section)
    harmony = plan_harmony(
        root,
        doc['mode'],
        'default',
        'jazzy' if e['tension'] > .3 else 'neutral',
        section['bars'],
        4,
        doc['seed'],
        extensions=(7,) if e['tension'] > .5 else (),
        energy=section_kind,
    )
    notes = []
    default_vel_dev = int(round(max(4.0, min(12.0, 4.0 + e['timing'] * 24.0))))

    def add(pitch, start, duration, velocity, probability=1.0, velocity_deviation=None):
        start = max(0, min(length - .002, start + rng.uniform(-.035, .035) * e['timing']))
        if int(round(start * 4)) % 2:
            start = min(length - .002, start + e['swing'] * .12)
        duration = min(duration, length - start)
        vdev = default_vel_dev if velocity_deviation is None else int(velocity_deviation)
        notes.append({'pitch': max(0, min(127, int(pitch))), 'start': round(start, 5),
                      'duration': round(max(.001, duration), 5),
                      'velocity': max(1, min(127, int(velocity + rng.uniform(-8, 8) * e['timing']))),
                      'probability': round(max(0.01, min(1.0, float(probability))), 3),
                      'velocity_deviation': max(-127, min(127, vdev))})

    total_bars = section['bars']
    for bar in range(total_bars):
        base = bar * bar_length
        chord = harmony.voiced_chords[bar]
        variant = _phrase_variant_for_bar(bar, total_bars)
        is_turnaround = variant in ('turnaround_A', 'turnaround_B')
        is_final_transition = (bar == total_bars - 1 and total_bars >= 2)

        if role == 'drums':
            dropout_start = bar_length * 0.5 if (is_turnaround or is_final_transition) else bar_length + 1.0
            for step in range(int(bar_length * 4)):
                at = step / 4
                accent = any(abs(at - a) < .01 for a in accents)
                # Strip kicks in the turnaround / pre-drop transition window
                if at < dropout_start:
                    if accent and (step == 0 or rng.random() < density):
                        add(doc['drum_notes']['kick'], base + at, .12, 86 + energy * 25, probability=1.0, velocity_deviation=4)
                    elif variant == 'development' and abs(at - (accents[0] + unit * 0.5)) < .01:
                        add(doc['drum_notes']['kick'], base + at, .11, 80 + energy * 20, probability=0.92, velocity_deviation=6)
                if abs(at - accents[-1]) < .01 and not is_turnaround:
                    add(doc['drum_notes']['snare'], base + at, .12, 82 + energy * 24, probability=1.0, velocity_deviation=5)
                elif 'jungle' in ingredients and step % 2 and rng.random() < e['syncopation'] * energy * .24:
                    add(doc['drum_notes']['snare'], base + at, .07, 48 + energy * 15, probability=0.78, velocity_deviation=10)
                elif variant == 'continuation' and step == int(bar_length * 4) - 1:
                    add(doc['drum_notes']['snare'], base + at, .07, 54 + energy * 18, probability=0.82, velocity_deviation=9)
                if step % 2 == 0 and rng.random() < density and not (is_turnaround and at >= dropout_start):
                    add(doc['drum_notes']['hat'], base + at, .06, 55 + energy * 25, probability=0.88 if step % 4 == 2 else 0.96, velocity_deviation=8)
            # Turnaround / transition accelerating snare fill in second half of bar
            if is_turnaround or is_final_transition:
                fill_start = max(0.5, bar_length * 0.5)
                fill_mid = max(fill_start + 0.25, bar_length * 0.75)
                pos = fill_start
                idx_fill = 0
                while pos < bar_length - 0.05:
                    step_size = 0.5 if pos < fill_mid else 0.25
                    vel = min(124, int(72 + idx_fill * 7 + energy * 20))
                    add(doc['drum_notes']['snare'], base + pos, min(0.11, step_size * 0.8), vel, probability=0.92, velocity_deviation=7)
                    pos += step_size
                    idx_fill += 1
        elif role == 'percussion':
            for step in range(int(bar_length * 4)):
                at = step / 4
                if is_turnaround and at >= bar_length * 0.5:
                    if step % 2 == 1:
                        add(doc['drum_notes']['percussion'] + 2, base + at, .08, 68 + energy * 26, probability=0.84, velocity_deviation=9)
                elif step % 3 == (bar % 3 if 'interlocking' in ingredients else 0) and rng.random() < density:
                    add(doc['drum_notes']['percussion'], base + at, .09, 58 + energy * 28, probability=0.88, velocity_deviation=8)
        elif role == 'bass':
            bc = dict(doc.get('bass_companion') or {})
            bc.update(section.get('bass_companion') or {})
            if bc:
                drum_notes = (section.get('parts') or {}).get('drums', {}).get('notes') or []
                kick_pitch = int(doc.get('drum_notes', {}).get('kick', 36))
                kicks_in_sec = [n['start'] for n in drum_notes if n.get('pitch') == kick_pitch]
                lock_kicks = (
                    bc.get('lock_to_kick_beats')
                    or bc.get('kick_beats')
                    or section.get('lock_to_kick_beats')
                    or doc.get('lock_to_kick_beats')
                    or kicks_in_sec
                    or [0.0, round(bar_length * 0.625, 4)]
                )
                if bc.get('lock_to_kick') is False:
                    lock_kicks = [0.0]
                bc['kick_beats'] = lock_kicks
                return generate_bass_companion(
                    key=bc.get('key', doc.get('root_midi', 56)),
                    scale=bc.get('scale', doc.get('mode', 'minor')),
                    swing=float(bc.get('swing', e.get('swing', 0.0))),
                    density=str(bc.get('density', 'medium')),
                    movement=str(bc.get('movement', 'syncopated_hook')),
                    lock_to_kick_beats=lock_kicks,
                    bars=total_bars,
                    metre=section['metre'],
                    seed=seed_for(doc['seed'], section['id'], role, variation),
                )
            bass_root = max(28, chord[0] - 24)
            drum_notes = (section.get('parts') or {}).get('drums', {}).get('notes') or []
            kick_pitch = int(doc.get('drum_notes', {}).get('kick', 36))
            bar_kicks = sorted({
                round(float(n['start']) - base, 4)
                for n in drum_notes
                if n.get('pitch') == kick_pitch and base - 0.01 <= float(n['start']) < base + bar_length - 0.01
            })
            if not bar_kicks and (section.get('lock_to_kick_beats') or doc.get('lock_to_kick_beats')):
                raw_lock = section.get('lock_to_kick_beats') or doc.get('lock_to_kick_beats') or []
                bar_kicks = sorted({round(float(b) % bar_length, 4) for b in raw_lock if isinstance(b, (int, float))})
            pulse_positions = bar_kicks if bar_kicks else accents

            # Lock downbeat and accent hits to actual kick grid
            for index, at in enumerate(pulse_positions):
                if is_turnaround and at >= bar_length * 0.65:
                    continue
                if index == 0 or rng.random() < density:
                    displacement = .25 if (not bar_kicks and index and ('uk_bass' in ingredients or variant == 'development') and rng.random() < max(0.35, e['syncopation'])) else 0
                    pitch = bass_root + (7 if (variant == 'development' and index == len(pulse_positions) - 1) else 0)
                    add(pitch, base + at + displacement, min(.6, unit * .7), 84 + energy * 20)
            # Syncopated answer in gap between kick accents
            gap_pos = min(bar_length - 0.5, (pulse_positions[0] if pulse_positions else 0.0) + unit * 0.5)
            if any(abs(gap_pos - kp) < 0.15 for kp in pulse_positions):
                gap_pos = min(bar_length - 0.5, gap_pos + 0.25)
            if variant in ('statement', 'continuation') and gap_pos > 0:
                ans_interval = 3 if doc['mode'] == 'minor' else 4
                add(bass_root + (0 if variant == 'statement' else ans_interval), base + gap_pos, min(.35, unit * .45), 76 + energy * 18)
            elif is_turnaround:
                # AAAB bar-4 turnaround octave jump & pickup into beat 1.0 of next bar/section
                pickup_1 = max(0.25, bar_length - min(1.0, unit))
                pickup_2 = max(pickup_1 + 0.20, bar_length - min(0.5, unit * 0.5))
                add(bass_root + 12, base + pickup_1, min(.35, pickup_2 - pickup_1), 88 + energy * 18)
                add(bass_root + 7, base + pickup_2, min(.35, bar_length - pickup_2), 92 + energy * 18)
        elif role == 'chords':
            if variant == 'statement':
                for pitch in chord:
                    add(pitch, base, bar_length * (.7 if 'spacious' in ingredients else .42), 54 + energy * 28)
            elif variant == 'continuation':
                off = unit * 0.5 if 'angular' in ingredients else 0.0
                for pitch in chord:
                    add(pitch, base + off, (bar_length - off) * (.55 if 'spacious' in ingredients else .35), 50 + energy * 26)
            elif variant == 'development':
                off = min(bar_length * 0.5, unit * 0.5)
                for pitch in chord:
                    add(pitch, base + off, (bar_length - off) * .45, 56 + energy * 28)
            else:  # turnaround_A / turnaround_B: two-part cadential stab with top-voice extension
                first_dur = bar_length * 0.45
                second_at = bar_length * 0.625
                for pitch in chord:
                    add(pitch, base, first_dur, 56 + energy * 28)
                turn_chord = list(chord[:-1]) + [chord[-1] + 12] if chord else [root + 12]
                for pitch in turn_chord:
                    add(pitch, base + second_at, max(0.15, (bar_length - second_at) * 0.8), 62 + energy * 30)
        else:
            # motif / lead / counterline with Cross-Track Call-and-Response gap locking
            motif = list(doc['motif'])
            transform = section['motif_transform']
            if transform == 'fragment':
                motif = motif[:2 + bar % max(1, len(motif) - 1)]
            if role == 'counterline':
                motif = list(reversed(motif))[:3]

            # Place call-and-response phrases in the rhythmic gap after chord downbeats
            gap_offset = bar_length * 0.375 if ('chords' in section.get('active_parts', []) or 'bass' in section.get('active_parts', [])) else 0.0
            span = max(0.5, bar_length - gap_offset)
            step = span / (len(motif) + 1)

            if variant in ('statement', 'development'):
                for i, interval in enumerate(motif):
                    at = gap_offset + i * step
                    if transform == 'displace' or variant == 'development':
                        at = gap_offset + ((i * step + unit * 0.5) % span)
                    if transform == 'stretch' and i % 2:
                        continue
                    if 'sparse' in ingredients and i > 1 and rng.random() < e['space'] * .5:
                        continue
                    pitch = root + interval + (12 if role == 'counterline' else 0)
                    if (transform == 'fragment' and 'angular' in ingredients and i % 2) or (variant == 'development' and i == len(motif) - 1):
                        pitch += 12
                    add(pitch, base + at, min(step * (.85 if transform == 'stretch' else .55), bar_length - at), 66 + energy * 24)
            elif variant == 'continuation':
                # Sparse echo in the late gap of bar 2
                echo_motif = motif[:max(1, len(motif) // 2)]
                for i, interval in enumerate(echo_motif):
                    at = min(bar_length - 0.25, bar_length * 0.5 + i * step)
                    pitch = root + interval + (12 if role == 'counterline' else 0)
                    add(pitch, base + at, min(step * .5, bar_length - at), 58 + energy * 20)
            else:
                # turnaround_A / turnaround_B: resolving cadential answer in bar 4
                ans_intervals = list(reversed(motif[:3])) + [12 if variant == 'turnaround_B' else 7]
                ans_step = (bar_length * 0.75) / max(1, len(ans_intervals))
                for i, interval in enumerate(ans_intervals):
                    at = min(bar_length - 0.15, bar_length * 0.20 + i * ans_step)
                    pitch = root + interval + (12 if role == 'counterline' else 0)
                    add(pitch, base + at, min(ans_step * 0.75, bar_length - at), 72 + energy * 25)
    return sorted(notes, key=lambda n: (n['start'], n['pitch']))


def enforce_locks(old, new):
    if old is None:
        return
    new_sections = {s['id']: s for s in new['sections']}
    for index, s in enumerate(old['sections']):
        other = new_sections.get(s['id'])
        if s['locked']:
            if other is None or new['sections'].index(other) != index or {k: v for k, v in s.items() if k != 'locked'} != {k: v for k, v in other.items() if k != 'locked'}:
                raise ValueError('Unlock section "%s" in a separate saved revision before editing it' % s['name'])
        for role, part in s['parts'].items():
            if part['locked']:
                candidate = (other or {}).get('parts', {}).get(role)
                if candidate is None or {k: v for k, v in candidate.items() if k != 'locked'} != {k: v for k, v in part.items() if k != 'locked'}:
                    raise ValueError('Unlock %s in "%s" before changing its notes' % (role, s['name']))
                if any(other[k] != s[k] for k in ('metre', 'bars', 'grouping')) or (role in other['active_parts']) != (role in s['active_parts']):
                    raise ValueError('Locked parts preserve their length, metre and active state')


def prepare(doc, old=None, regenerate=None):
    doc = copy.deepcopy(doc)
    enforce_locks(old, doc)
    old_sections = {s['id']: s for s in (old or {}).get('sections', [])}
    # Resize untouched generated parts before validating bounds. Explicit note edits
    # and all locked parts still have to fit their declared section.
    for s in doc['sections']:
        prev = old_sections.get(s['id'])
        if prev and not s['locked'] and any(s[k] != prev[k] for k in ('metre', 'bars')):
            for role, part in list(s['parts'].items()):
                if not part['locked'] and part['notes'] == prev.get('parts', {}).get(role, {}).get('notes'):
                    del s['parts'][role]
    validate(doc)
    global_keys = ('seed', 'root_midi', 'mode', 'motif', 'expression', 'ingredients', 'drum_notes', 'bass_companion', 'lock_to_kick_beats')
    global_change = old is not None and any(doc.get(k) != old.get(k) for k in global_keys)
    role_priority = {r: idx for idx, r in enumerate(ROLES)}
    for s in doc['sections']:
        prev = old_sections.get(s['id'])
        section_change = prev is not None and any(s.get(k) != prev.get(k) for k in ('metre', 'bars', 'grouping', 'energy', 'motif_transform', 'bass_companion', 'lock_to_kick_beats'))

        ordered_roles = sorted(s['active_parts'], key=lambda r: role_priority.get(r, 99))
        for role in ordered_roles:
            part = s['parts'].get(role)
            selected = regenerate and s['id'] in regenerate.get('sections', []) and role in regenerate.get('roles', ROLES)
            if s['locked'] or (part and part['locked']):
                continue
            # Explicit Codex note edits win over automatic regeneration.
            explicit = part is not None and (prev is None or part.get('notes') != prev.get('parts', {}).get(role, {}).get('notes'))
            if part is None or selected or ((global_change or section_change) and not explicit):
                variation = (part or {}).get('variation', 0) + (1 if selected else 0)
                s['parts'][role] = {'locked': False, 'variation': variation, 'notes': generate_part(doc, s, role, variation)}
    validate(doc)
    return doc


def compile_score(doc, section_id=None):
    validate(doc)
    sections, beat = [], 0.0
    chosen = [s for s in doc['sections'] if section_id is None or s['id'] == section_id]
    if not chosen:
        raise ValueError('Section does not exist')
    for s in chosen:
        length = beats_per_bar(s['metre']) * s['bars']
        sections.append({'id': s['id'], 'name': s['name'], 'metre': s['metre'], 'grouping': s['grouping'],
                         'bars': s['bars'], 'start_beat': beat, 'length_beats': length,
                         'seconds': length * 60 / doc['bpm'], 'active_parts': s['active_parts']})
        beat += length
    return {'sections': sections, 'total_beats': beat, 'seconds': beat * 60 / doc['bpm'],
            'target_seconds': doc['target_seconds'], 'difference_seconds': beat * 60 / doc['bpm'] - doc['target_seconds']}


def fit_duration(doc):
    """Closest whole-bar fit via bounded knapsack; tie-break by least bar edits."""
    doc = copy.deepcopy(doc)
    validate(doc)
    fixed = 0
    editable = []
    for s in doc['sections']:
        unit = int(beats_per_bar(s['metre']) * 2)
        if s['locked'] or any(p['locked'] for p in s['parts'].values()):
            fixed += unit * s['bars']
        else:
            editable.append((s, unit))
    target = doc['target_seconds'] * doc['bpm'] / 30
    if not editable:
        return doc
    # All lengths are half-beat multiples. Keep a sufficient overshoot window.
    cap = min(7200, max(sum(u for _, u in editable), int(target - fixed) + 20))
    states = {0: (0, ())}
    for s, unit in editable:
        next_states = {}
        for total, (cost, bars) in states.items():
            for count in range(1, min(256, (cap - total) // unit) + 1):
                end = total + unit * count
                candidate = (cost + abs(count - s['bars']), bars + (count,))
                if end not in next_states or candidate < next_states[end]:
                    next_states[end] = candidate
        states = next_states
    if states:
        best = min(states, key=lambda x: (abs(x + fixed - target), states[x][0], x))
        for (s, _), count in zip(editable, states[best][1]):
            if count != s['bars']:
                s['bars'] = count
                s['parts'] = {}
    return doc


def _extract_project_midi_intelligence(tracks: list[dict]) -> dict:
    """Scan arrangement and session clips for summary.notes_preview to extract motif, root/mode, and kick pulses."""
    midi_clips: list[dict] = []
    source_clips_used: list[dict] = []
    pc_counts: dict[int, int] = {}

    for tr in tracks:
        tr_name = str(tr.get('name') or '')
        tr_id = str(tr.get('id') or '')
        sess_summaries = tr.get('session_clip_summaries') or {}
        all_clips = []
        for c in tr.get('arrangement_clips') or []:
            if isinstance(c, dict):
                all_clips.append((c, c.get('summary')))
        for c in tr.get('session_clips') or tr.get('clips') or []:
            if isinstance(c, dict):
                s_idx = str(c.get('scene_index'))
                summary = c.get('summary') or sess_summaries.get(s_idx)
                all_clips.append((c, summary))

        for clip, summary in all_clips:
            if not isinstance(summary, dict) or summary.get('kind') != 'midi':
                continue
            notes = summary.get('notes_preview') or []
            if not notes:
                continue
            active_notes = [n for n in notes if isinstance(n, dict) and not n.get('mute')]
            if not active_notes:
                continue
            pitches = [int(n['pitch']) for n in active_notes if 'pitch' in n]
            if not pitches:
                continue
            for p in pitches:
                pc = p % 12
                pc_counts[pc] = pc_counts.get(pc, 0) + 1
            avg_pitch = sum(pitches) / len(pitches)
            clip_entry = {
                'track_id': tr_id,
                'track_name': tr_name,
                'clip_name': str(clip.get('name') or ''),
                'note_count': len(active_notes),
                'avg_pitch': avg_pitch,
                'notes': sorted(active_notes, key=lambda n: (float(n.get('start', 0.0)), int(n.get('pitch', 60)))),
            }
            midi_clips.append(clip_entry)
            source_clips_used.append({
                'track_id': tr_id,
                'track_name': tr_name,
                'clip_name': clip_entry['clip_name'],
                'note_count': len(active_notes),
            })

    extracted_motif: list[int] | None = None
    extracted_root_pc: int | None = None
    extracted_mode: str | None = None
    kick_beats: list[float] = []

    if pc_counts:
        minor_template = (0, 2, 3, 5, 7, 8, 10)
        major_template = (0, 2, 4, 5, 7, 9, 11)
        best_score = -1.0
        for root_pc in range(12):
            for mode_name, tmpl in (('minor', minor_template), ('major', major_template)):
                in_scale = sum(pc_counts.get((root_pc + iv) % 12, 0) for iv in tmpl)
                tonic_bonus = pc_counts.get(root_pc, 0) * 0.5 + pc_counts.get((root_pc + 7) % 12, 0) * 0.25
                score_val = in_scale + tonic_bonus
                if score_val > best_score:
                    best_score = score_val
                    extracted_root_pc = root_pc
                    extracted_mode = mode_name

    # Extract motif intervals from most active mid/high register MIDI clip
    melodic_candidates = [c for c in midi_clips if c['avg_pitch'] >= 48] or midi_clips
    if melodic_candidates:
        melodic_candidates.sort(key=lambda c: (-c['note_count'], -c['avg_pitch']))
        top_clip = melodic_candidates[0]
        # Take distinct onset time top-notes for the motif
        by_time: dict[float, int] = {}
        for n in top_clip['notes']:
            st = round(float(n.get('start', 0.0)), 3)
            by_time[st] = max(by_time.get(st, -1), int(n['pitch']))
        ordered_pitches = [by_time[k] for k in sorted(by_time)[:8]]
        if len(ordered_pitches) >= 2:
            base_pitch = ordered_pitches[0]
            extracted_motif = [max(-24, min(24, int(p - base_pitch))) for p in ordered_pitches[:6]]
            if extracted_root_pc is None:
                extracted_root_pc = base_pitch % 12

    # Extract rhythmic low-note / kick attacks
    low_clips = [c for c in midi_clips if c['avg_pitch'] < 52 or any(int(n['pitch']) <= 48 for n in c['notes'])]
    for lc in low_clips:
        for n in lc['notes']:
            if int(n['pitch']) <= 48:
                beat_pos = round(float(n.get('start', 0.0)) % 4.0, 4)
                if beat_pos not in kick_beats:
                    kick_beats.append(beat_pos)
    kick_beats = sorted(kick_beats)[:8]

    return {
        'motif': extracted_motif,
        'root_pc': extracted_root_pc,
        'mode': extracted_mode,
        'lock_to_kick_beats': kick_beats,
        'source_clips_used': source_clips_used,
    }


def project_document(state: dict | None = None, payload: dict | None = None) -> dict:
    """Seed a Composition Lab score from the open Ableton Set (e.g. shape change .als at 119 BPM in Ab/Fm)."""
    state = dict(state or {})
    payload = dict(payload or {})
    bpm = float(payload.get('bpm') or state.get('tempo') or 119.0)
    bpm = max(40.0, min(240.0, bpm))
    session_id = str(state.get('session_id') or 'project-session')

    tracks = list(state.get('tracks') or (state.get('production') or {}).get('tracks') or [])
    midi_intel = _extract_project_midi_intelligence(tracks)

    detected_key = payload.get('key')
    if not detected_key:
        try:
            from . import song_sketch
            for tr in tracks:
                kh = song_sketch.detect_key_hint(tr)
                if kh and kh.get('key'):
                    detected_key = kh['key']
                    break
        except Exception:
            pass
    pc_names = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B')
    if not detected_key and midi_intel.get('root_pc') is not None:
        detected_key = pc_names[int(midi_intel['root_pc']) % 12]
    detected_key = str(detected_key or 'Ab')
    pitch_to_midi_oct3 = {
        'C': 48, 'C#': 49, 'DB': 49, 'D': 50, 'D#': 51, 'EB': 51,
        'E': 52, 'F': 53, 'F#': 54, 'GB': 54, 'G': 55, 'G#': 56,
        'AB': 56, 'A': 57, 'A#': 58, 'BB': 58, 'B': 59,
    }
    key_token = detected_key.strip().split()[0]
    if key_token.endswith('m') and len(key_token) >= 2 and key_token[:-1].upper() in pitch_to_midi_oct3:
        key_token = key_token[:-1]
    default_root = (48 + int(midi_intel['root_pc'])) if midi_intel.get('root_pc') is not None and not payload.get('key') and key_token.upper() not in pitch_to_midi_oct3 else pitch_to_midi_oct3.get(key_token.upper(), 56)
    if midi_intel.get('root_pc') is not None and not payload.get('key') and not any(
        tr.get('name', '').lower().find('flat') >= 0 or tr.get('name', '').lower().find('min') >= 0 for tr in tracks
    ):
        default_root = 48 + int(midi_intel['root_pc'])
        detected_key = pc_names[int(midi_intel['root_pc']) % 12]
    root_midi = int(payload.get('root_midi') or default_root)
    mode = str(payload.get('mode') or midi_intel.get('mode') or ('major' if 'major' in detected_key.lower() else 'minor'))
    if mode not in ('minor', 'major'):
        mode = 'minor'

    # Discover available MIDI instrument tracks (e.g. 6-Serum 2, 8-Serum 2, 12-Serum 2, 3-THE_INSTRUMENT)
    midi_synths = [
        t for t in tracks
        if t.get('type') == 'midi'
        and not t.get('is_group')
        and (t.get('devices') or t.get('has_audio_output'))
    ]
    preferred = sorted(
        midi_synths,
        key=lambda t: (
            0 if any(k in str(t.get('name', '')).lower() for k in ('serum', 'instrument', 'synth', 'moog', 'bass')) else 1,
            int(t.get('index', 999)) if str(t.get('index', '')).isdigit() else 999,
        ),
    )

    assignments: dict[str, dict | None] = {role: None for role in ROLES}
    synth_roles = ('bass', 'chords', 'motif', 'counterline')
    if preferred and state.get('session_id'):
        for idx, role in enumerate(synth_roles):
            chosen_track = preferred[min(idx, len(preferred) - 1)]
            if chosen_track.get('id') and chosen_track.get('name'):
                assignments[role] = {
                    'id': str(chosen_track['id']),
                    'name': str(chosen_track['name']),
                    'session_id': session_id,
                }
        if payload.get('assign_all_roles'):
            first_tr = preferred[0]
            for r in ('drums', 'percussion'):
                assignments[r] = {
                    'id': str(first_tr['id']),
                    'name': str(first_tr['name']),
                    'session_id': session_id,
                }

    rows = [
        ('Intro groove', [4, 4], [2, 2], 4, 0.42, ['drums', 'percussion', 'bass', 'chords'], 'original'),
        ('Build & vocal space', [4, 4], [2, 2], 4, 0.76, ['drums', 'percussion', 'bass', 'chords', 'motif'], 'displace'),
        ('Main drop', [4, 4], [2, 2], 8, 0.92, ['drums', 'percussion', 'bass', 'chords', 'motif'], 'original'),
        ('Breakdown answer', [4, 4], [2, 2], 4, 0.30, ['chords', 'motif', 'counterline'], 'stretch'),
    ]
    sections = []
    for i, (name, metre, grouping, bars, energy, roles, transform) in enumerate(rows):
        sections.append({
            'id': 'section-%02d' % (i + 1),
            'name': name,
            'metre': metre,
            'grouping': grouping,
            'bars': bars,
            'energy': energy,
            'active_parts': roles,
            'locked': False,
            'motif_transform': transform,
            'motif_id': 'shape-change',
            'parts': {},
        })

    total_beats = sum(beats_per_bar(s['metre']) * s['bars'] for s in sections)
    target_seconds = round(total_beats * 60.0 / bpm, 2)
    set_name = Path(str(state.get('set_path') or 'shape change.als')).stem.strip() or 'shape change'
    motif_intervals = list(payload.get('motif') or midi_intel.get('motif') or [0, 3, 7, 10, 7])

    doc = {
        'title': str(payload.get('title') or f'{set_name} · {int(round(bpm))} BPM ({detected_key})'),
        'brief': str(payload.get('brief') or f'Project-seeded 4/4 groove at {bpm:.1f} BPM in {detected_key} {mode} with AAAB phrasing, Bass Companion lock, and call-and-response synth answers.'),
        'mood': str(payload.get('mood') or 'Hypnotic, groovy, warm low-end'),
        'bpm': bpm,
        'target_seconds': max(10.0, min(900.0, target_seconds)),
        'seed': int(payload.get('seed') or 1190),
        'root_midi': root_midi,
        'mode': mode,
        'motif': motif_intervals,
        'source_clips_used': midi_intel.get('source_clips_used', []),
        'ingredients': {
            'rhythm': ['interlocking', 'uk_bass'],
            'harmony': ['spacious'],
            'phrasing': ['interlocking', 'sparse'],
            'structure': ['spacious'],
        },
        'expression': {
            'density': 0.58,
            'syncopation': 0.62,
            'swing': 0.16,
            'timing': 0.08,
            'tension': 0.42,
            'space': 0.32,
        },
        'assignments': assignments,
        'sound_locks': {role: True for role in ROLES},
        'drum_notes': {'kick': 36, 'snare': 38, 'hat': 42, 'percussion': 60},
        'sections': sections,
    }
    if midi_intel.get('lock_to_kick_beats'):
        doc['lock_to_kick_beats'] = midi_intel['lock_to_kick_beats']
    return prepare(doc)

