from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .genre_dna import lookup_genre, pick_pattern, GenreDNA, DEFAULT_DNA, GrooveProfile
from .harmony import detect_colour, plan_harmony
from .midi_library import seeded_rng, stable_seed


NOTE_NAMES = {
    "c": 0,
    "c#": 1,
    "db": 1,
    "d": 2,
    "d#": 3,
    "eb": 3,
    "e": 4,
    "f": 5,
    "f#": 6,
    "gb": 6,
    "g": 7,
    "g#": 8,
    "ab": 8,
    "a": 9,
    "a#": 10,
    "bb": 10,
    "b": 11,
}

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
}

COMMON_PROGRESSIONS = {
    "major": ["I", "V", "vi", "IV"],
    "minor": ["i", "VI", "III", "VII"],
}

ROMAN_DEGREES = {
    "i": 0,
    "ii": 1,
    "iii": 2,
    "iv": 3,
    "v": 4,
    "vi": 5,
    "vii": 6,
}


@dataclass(frozen=True)
class MelodyRule:
    contour: tuple[int, ...]
    rest_density: float
    ending_degree: int
    ending_duration: float


MELODY_RULES: dict[str, MelodyRule] = {
    "house": MelodyRule(contour=(0, 2, 4, 2), rest_density=0.08, ending_degree=4, ending_duration=0.55),
    "uk garage": MelodyRule(contour=(0, 0, 2, -1), rest_density=0.16, ending_degree=2, ending_duration=0.45),
    "drum n bass": MelodyRule(contour=(0, 7, 12, 7), rest_density=0.04, ending_degree=6, ending_duration=0.32),
    "jungle": MelodyRule(contour=(0, 5, 7, 12), rest_density=0.1, ending_degree=4, ending_duration=0.4),
    "techno": MelodyRule(contour=(0, 0, 0, 2), rest_density=0.02, ending_degree=0, ending_duration=0.24),
    "trance": MelodyRule(contour=(0, 4, 7, 12), rest_density=0.04, ending_degree=4, ending_duration=0.45),
    "trap": MelodyRule(contour=(0, -2, -5, -7), rest_density=0.34, ending_degree=0, ending_duration=0.72),
    "hip hop": MelodyRule(contour=(0, -2, 0, 2), rest_density=0.24, ending_degree=0, ending_duration=0.58),
    "reggaeton": MelodyRule(contour=(0, 2, 4, 7), rest_density=0.12, ending_degree=4, ending_duration=0.42),
    "ambient": MelodyRule(contour=(0, 0, 7, 12), rest_density=0.46, ending_degree=4, ending_duration=1.4),
    "pop": MelodyRule(contour=(0, 2, 4, 7), rest_density=0.1, ending_degree=0, ending_duration=0.55),
    "afrobeats": MelodyRule(contour=(0, 2, 5, 7), rest_density=0.14, ending_degree=4, ending_duration=0.4),
    "amapiano": MelodyRule(contour=(0, 0, 2, 5), rest_density=0.12, ending_degree=0, ending_duration=0.32),
}


@dataclass(frozen=True)
class Note:
    pitch: int
    start: float
    duration: float
    velocity: int = 92
    mute: bool = False

    def to_live(self) -> dict[str, Any]:
        return {
            "pitch": self.pitch,
            "start": round(self.start, 4),
            "duration": round(self.duration, 4),
            "velocity": self.velocity,
            "mute": self.mute,
        }


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def note_number(name: str, octave: int = 4) -> int:
    clean = name.strip().lower().replace("♯", "#").replace("♭", "b")
    if clean not in NOTE_NAMES:
        clean = "c"
    return 12 * (octave + 1) + NOTE_NAMES[clean]


DEFAULT_GENRE_KEYS = {
    "house": [("a", "minor"), ("c", "minor"), ("g", "minor"), ("d", "minor")],
    "uk garage": [("a", "minor"), ("b", "minor"), ("d", "minor"), ("e", "minor")],
    "drum n bass": [("f", "minor"), ("f#", "minor"), ("g", "minor"), ("e", "minor")],
    "jungle": [("f", "minor"), ("f#", "minor"), ("g", "minor"), ("eb", "minor")],
    "techno": [("a", "minor"), ("c", "minor"), ("f#", "minor"), ("b", "minor")],
    "trance": [("g", "minor"), ("a", "minor"), ("b", "minor"), ("f#", "minor")],
    "trap": [("c#", "minor"), ("d", "minor"), ("f", "minor"), ("a", "minor")],
    "hip hop": [("c", "minor"), ("f", "minor"), ("g", "minor"), ("a", "minor")],
    "reggaeton": [("g", "minor"), ("c", "minor"), ("d", "minor"), ("a", "minor")],
    "downtempo": [("a", "minor"), ("d", "minor"), ("g", "minor"), ("e", "minor")],
    "ambient": [("c", "major"), ("f", "major"), ("g", "major"), ("a", "minor")],
    "pop": [("c", "major"), ("g", "major"), ("f", "major"), ("a", "minor")],
    "afrobeats": [("a", "minor"), ("b", "minor"), ("e", "minor"), ("g", "major")],
    "amapiano": [("e", "minor"), ("a", "minor"), ("b", "minor"), ("c", "major")],
    "hyperpop": [("c", "major"), ("f", "major"), ("g", "major"), ("d", "major")],
}


def infer_key(text: str, genre: str = "") -> tuple[str, str]:
    import re
    from .genre_dna import detect_style_from_text
    lowered = text.lower().replace("♯", "#").replace("♭", "b")
    
    # 1. Check Camelot Wheel codes
    camelot_match = re.search(r"\b(1[0-2]|[1-9])\s*([ab])\b", lowered)
    if camelot_match:
        code = f"{camelot_match.group(1)}{camelot_match.group(2)}"
        camelot_map = {
            "1a": ("ab", "minor"), "2a": ("eb", "minor"), "3a": ("bb", "minor"), "4a": ("f", "minor"),
            "5a": ("c", "minor"), "6a": ("g", "minor"), "7a": ("d", "minor"), "8a": ("a", "minor"),
            "9a": ("e", "minor"), "10a": ("b", "minor"), "11a": ("f#", "minor"), "12a": ("c#", "minor"),
            "1b": ("b", "major"), "2b": ("f#", "major"), "3b": ("db", "major"), "4b": ("ab", "major"),
            "5b": ("eb", "major"), "6b": ("bb", "major"), "7b": ("f", "major"), "8b": ("c", "major"),
            "9b": ("g", "major"), "10b": ("d", "major"), "11b": ("a", "major"), "12b": ("e", "major"),
        }
        if code in camelot_map:
            return camelot_map[code]

    # 2. Check for explicit root and mode in the text
    mode_explicit = None
    if "minor" in lowered or "dark" in lowered:
        mode_explicit = "minor"
    elif "major" in lowered:
        mode_explicit = "major"
        
    explicit_root = None
    for name in sorted(NOTE_NAMES, key=len, reverse=True):
        if f"{name} major" in lowered or f"{name} minor" in lowered or f"in {name}" in lowered:
            explicit_root = name
            break
            
    if not explicit_root:
        if "am" in lowered or "a minor" in lowered:
            explicit_root = "a"
            mode_explicit = "minor"

    # If we have an explicit root, pair it with mode_explicit
    if explicit_root:
        resolved_mode = mode_explicit or ("minor" if "minor" in lowered or "dark" in lowered else "major")
        return explicit_root, resolved_mode

    # 3. No explicit root was specified. Fallback to genre-specific defaults.
    target_genre = genre
    if not target_genre:
        target_genre = detect_style_from_text(text)

    target_genre = target_genre.strip().lower() if target_genre else ""

    pool = DEFAULT_GENRE_KEYS.get(target_genre)
    if pool:
        if mode_explicit:
            filtered_pool = [k for k in pool if k[1] == mode_explicit]
            if filtered_pool:
                pool = filtered_pool
        seed = sum(ord(c) for c in text)
        return pool[seed % len(pool)]

    # 4. Ultimate fallback if no genre key pool is found
    resolved_mode = mode_explicit or ("minor" if "minor" in lowered or "dark" in lowered else "major")
    return ("a", "minor") if resolved_mode == "minor" else ("c", "major")


def chord_pitches(root: str, mode: str, degree: str, octave: int = 3) -> list[int]:
    scale = SCALES.get(mode, SCALES["minor"])
    root_midi = note_number(root, octave)
    degree_index = ROMAN_DEGREES.get(degree.lower(), 0)
    base = root_midi + scale[degree_index]
    if degree_index >= 5:
        base -= 12

    third = scale[(degree_index + 2) % 7]
    fifth = scale[(degree_index + 4) % 7]
    third_pitch = root_midi + third
    fifth_pitch = root_midi + fifth
    while third_pitch <= base:
        third_pitch += 12
    while fifth_pitch <= third_pitch:
        fifth_pitch += 12
    return [base, third_pitch, fifth_pitch]


def generate_chords(text: str, bars: int = 4, _bypass_genre: bool = False) -> list[dict[str, Any]]:
    if not _bypass_genre:
        from .genre_dna import detect_style_from_text
        style = detect_style_from_text(text)
        if style:
            return genre_chords(text, bars=bars, genre=style)
            
    root, mode = infer_key(text)
    degrees = COMMON_PROGRESSIONS[mode]
    notes: list[Note] = []
    for bar in range(bars):
        degree = degrees[bar % len(degrees)]
        for pitch in chord_pitches(root, mode, degree):
            notes.append(Note(pitch=pitch, start=bar * 4.0, duration=3.75, velocity=86))
    return [note.to_live() for note in notes]


def generate_bassline(text: str, bars: int = 4, _bypass_genre: bool = False) -> list[dict[str, Any]]:
    if not _bypass_genre:
        from .genre_dna import detect_style_from_text
        style = detect_style_from_text(text)
        if style:
            return genre_bassline(text, bars=bars, genre=style)
            
    root, mode = infer_key(text)
    degrees = COMMON_PROGRESSIONS[mode]
    notes: list[Note] = []
    for bar in range(bars):
        root_pitch = chord_pitches(root, mode, degrees[bar % len(degrees)], octave=2)[0]
        pattern = [0.0, 1.5, 2.0, 3.0]
        for offset in pattern:
            pitch = root_pitch + (12 if math.isclose(offset, 3.0) else 0)
            notes.append(Note(pitch=pitch, start=bar * 4.0 + offset, duration=0.45, velocity=96))
    return [note.to_live() for note in notes]


def generate_melody(text: str, bars: int = 4) -> list[dict[str, Any]]:
    root, mode = infer_key(text)
    scale = SCALES[mode]
    base = note_number(root, 4)
    pattern = [0, 2, 4, 7, 9, 7, 4, 2]
    notes: list[Note] = []
    step = 0.5
    total_steps = bars * 8
    for index in range(total_steps):
        degree = pattern[index % len(pattern)] % len(scale)
        octave_shift = 12 if pattern[index % len(pattern)] >= 7 else 0
        pitch = base + scale[degree] + octave_shift
        velocity = 84 + (index % 3) * 6
        notes.append(Note(pitch=pitch, start=index * step, duration=0.42, velocity=velocity))
    return [note.to_live() for note in notes]


def generate_drums(bars: int = 4) -> list[dict[str, Any]]:
    notes: list[Note] = []
    for bar in range(bars):
        start = bar * 4.0
        for beat in range(4):
            notes.append(Note(pitch=36, start=start + beat, duration=0.18, velocity=110))
        for beat in [1, 3]:
            notes.append(Note(pitch=38, start=start + beat, duration=0.18, velocity=104))
        for eighth in range(8):
            notes.append(Note(pitch=42, start=start + eighth * 0.5, duration=0.12, velocity=70 + (eighth % 2) * 12))
    return [note.to_live() for note in notes]


def generate_edm_chords(text: str, bars: int = 4, energy: str = "main") -> list[dict[str, Any]]:
    root, mode = infer_key(text)
    degrees = COMMON_PROGRESSIONS[mode]
    notes: list[Note] = []
    for bar in range(bars):
        pitches = chord_pitches(root, mode, degrees[bar % len(degrees)])
        voicing = [pitches[1], pitches[2], pitches[0] + 12, pitches[1] + 12]
        if energy == "intro":
            starts = [0.0, 2.0]
            duration = 1.75
            velocity = 72
        elif energy == "break":
            starts = [0.0, 1.5, 3.0]
            duration = 0.9
            velocity = 78
        else:
            starts = [0.0, 0.75, 1.5, 2.5, 3.25]
            duration = 0.46
            velocity = 88
        for start in starts:
            for index, pitch in enumerate(voicing):
                notes.append(Note(pitch=pitch, start=bar * 4.0 + start, duration=duration, velocity=velocity - index * 4))
    return [note.to_live() for note in notes]


def generate_edm_bassline(text: str, bars: int = 4, energy: str = "main") -> list[dict[str, Any]]:
    root, mode = infer_key(text)
    degrees = COMMON_PROGRESSIONS[mode]
    notes: list[Note] = []
    for bar in range(bars):
        root_pitch = chord_pitches(root, mode, degrees[bar % len(degrees)], octave=2)[0]
        if energy == "build":
            pattern = [(0.0, 0, 0.35), (1.5, 0, 0.35), (2.0, 12, 0.25), (2.5, 7, 0.25), (3.0, 12, 0.35), (3.5, 14, 0.2)]
        else:
            pattern = [(0.0, 0, 0.38), (0.75, 12, 0.2), (1.5, 0, 0.34), (2.0, 7, 0.24), (2.5, 0, 0.34), (3.0, 12, 0.3), (3.5, 10, 0.18)]
        for index, (offset, interval, duration) in enumerate(pattern):
            velocity = 94 + (index % 3) * 7
            notes.append(Note(pitch=root_pitch + interval, start=bar * 4.0 + offset, duration=duration, velocity=velocity))
    return [note.to_live() for note in notes]


def generate_edm_lead(text: str, bars: int = 4, energy: str = "main") -> list[dict[str, Any]]:
    root, mode = infer_key(text)
    scale = SCALES[mode]
    base = note_number(root, 5)
    phrases = {
        "build": [(0.0, 0), (0.5, 2), (1.0, 4), (1.5, 5), (2.0, 7), (2.5, 5), (3.0, 4), (3.5, 2)],
        "break": [(0.0, 7), (1.0, 5), (1.75, 4), (3.0, 2)],
        "main": [(0.0, 7), (0.25, 9), (0.75, 7), (1.25, 5), (1.5, 4), (2.0, 7), (2.5, 11), (3.25, 9), (3.5, 7)],
    }
    phrase = phrases.get(energy, phrases["main"])
    notes: list[Note] = []
    for bar in range(bars):
        for index, (offset, degree_value) in enumerate(phrase):
            degree = degree_value % len(scale)
            octave_shift = 12 if degree_value >= 7 else 0
            if bar % 4 == 3 and index >= len(phrase) - 2:
                octave_shift += 12
            velocity = 82 + ((bar + index) % 4) * 8
            notes.append(Note(pitch=base + scale[degree] + octave_shift, start=bar * 4.0 + offset, duration=0.22 if energy == "main" else 0.38, velocity=velocity))
    return [note.to_live() for note in notes]


def generate_edm_drums(bars: int = 4, energy: str = "main") -> list[dict[str, Any]]:
    notes: list[Note] = []
    for bar in range(bars):
        start = bar * 4.0
        for beat in range(4):
            notes.append(Note(pitch=36, start=start + beat, duration=0.16, velocity=116))
        if energy != "hats":
            for beat in [1, 3]:
                notes.append(Note(pitch=38, start=start + beat, duration=0.16, velocity=104))
                notes.append(Note(pitch=39, start=start + beat + 0.03, duration=0.1, velocity=76))
        hat_step = 0.25 if energy in {"main", "drop"} else 0.5
        hat_count = int(4 / hat_step)
        for tick in range(hat_count):
            offset = tick * hat_step
            velocity = 58 + (tick % 4) * 10
            notes.append(Note(pitch=42, start=start + offset, duration=0.08, velocity=velocity))
        for offset in [0.5, 1.5, 2.5, 3.5]:
            if energy in {"main", "drop", "build"}:
                notes.append(Note(pitch=46, start=start + offset, duration=0.18, velocity=74))
        if energy in {"main", "drop"} and bar % 4 == 3:
            for step in range(8):
                notes.append(Note(pitch=38, start=start + 3.0 + step * 0.125, duration=0.08, velocity=72 + step * 5))
            notes.append(Note(pitch=49, start=start, duration=0.35, velocity=86))
        if energy == "build" and bar >= max(0, bars - 2):
            for step in range(16):
                notes.append(Note(pitch=38, start=start + step * 0.25, duration=0.08, velocity=54 + step * 4))
    return [note.to_live() for note in notes]


def transpose_notes(notes: list[dict[str, Any]], semitones: int) -> list[dict[str, Any]]:
    shifted = []
    for note in notes:
        copy = dict(note)
        copy["pitch"] = int(clamp(copy["pitch"] + semitones, 0, 127))
        shifted.append(copy)
    return shifted


def filter_drums(notes: list[dict[str, Any]], keep: set[int]) -> list[dict[str, Any]]:
    return [note for note in notes if int(note["pitch"]) in keep]


def clip_action(track_name: str, clip_name: str, notes: list[dict[str, Any]], bars: int = 4) -> dict[str, Any]:
    return {
        "type": "create_midi_clip",
        "track_name": track_name,
        "clip_name": clip_name,
        "scene_index": 0,
        "length_beats": bars * 4,
        "notes": notes,
    }


def finisher_mutation(track_name: str, new_clip_name: str, notes: list[dict[str, Any]], bars: int = 4) -> list[dict[str, Any]]:
    """
    Enforces the Duplicate-and-Mute pattern for all Finisher-related commands.
    Duplicates the track, mutes the original, and creates the mutated clip on the copy.
    """
    return [
        {"type": "duplicate_track", "track_name": track_name},
        {"type": "mute_track", "track_name": track_name},
        clip_action(f"{track_name} Copy", new_clip_name, notes, bars),
    ]


# ── Genre-Aware Generators ───────────────────────────────────────────
# These use GenreDNA profiles to produce musically distinct output.
# They replace the old generate_edm_* functions when a genre is known.


def _pattern_seed(text: str, energy: str, bars: int, salt: str = "") -> int:
    """Deterministic seed from prompt context for pattern selection."""
    return sum(ord(c) for c in f"{text.lower()}:{energy}:{bars}:{salt}")


def _groove_note(note: dict[str, Any], profile: GrooveProfile, bpm: int, seed: int | str, role: str) -> dict[str, Any]:
    copy = dict(note)
    start = float(copy.get("start", 0.0))
    duration = float(copy.get("duration", 0.25))
    velocity = int(copy.get("velocity", 96))
    beat_ms = 60000.0 / max(20, bpm)
    rng = seeded_rng({"seed": seed, "role": role, "note": copy})

    subdivision = int(round((start % 1.0) / 0.25)) % 4
    push = profile.push_pull_per_subdivision[subdivision % len(profile.push_pull_per_subdivision)]
    jitter_beats = rng.uniform(-profile.position_jitter_ms, profile.position_jitter_ms) / beat_ms
    length_jitter = rng.uniform(-profile.length_jitter, profile.length_jitter)
    curve = profile.weak_beat_curve[subdivision % len(profile.weak_beat_curve)]
    velocity_jitter = rng.randint(-profile.velocity_jitter, profile.velocity_jitter)

    if role == "kick":
        curve = max(curve, 0.94)
    elif role in {"hat", "percussion"}:
        curve *= 0.94
    elif role in {"chord", "pad"}:
        jitter_beats *= 0.35
        length_jitter *= 0.35

    copy["start"] = round(max(0.0, start + push + jitter_beats), 4)
    copy["duration"] = round(max(0.0312, duration + length_jitter), 4)
    copy["velocity"] = int(clamp(round(velocity * curve) + velocity_jitter, 1, 127))
    return copy


def apply_groove(
    notes: list[dict[str, Any]],
    dna: GenreDNA,
    seed: int | str,
    role: str,
) -> list[dict[str, Any]]:
    grooved = [_groove_note(note, dna.groove_profile, dna.bpm_default, seed, role) for note in notes]
    return sorted(grooved, key=lambda item: (float(item["start"]), int(item["pitch"])))


def drum_role_for_pitch(pitch: int) -> str:
    if pitch == 36:
        return "kick"
    if pitch in {38, 39}:
        return "snare"
    if pitch in {42, 46, 49}:
        return "hat"
    return "percussion"


def genre_bassline(text: str, bars: int = 4, energy: str = "main", genre: str = "") -> list[dict[str, Any]]:
    """Generate a bassline using the GenreDNA profile for the given genre."""
    root, mode = infer_key(text, genre=genre)
    dna = lookup_genre(genre)
    seed = _pattern_seed(text, energy, bars, "bass")
    pattern = pick_pattern(dna.bass_patterns, seed)
    if not pattern:
        return generate_bassline(text, bars)

    base_pitch = note_number(root, dna.bass_octave)
    scale = SCALES.get(mode, SCALES["minor"])
    degrees = COMMON_PROGRESSIONS[mode]
    notes: list[dict[str, Any]] = []

    for bar in range(bars):
        degree = degrees[bar % len(degrees)]
        chord_root = chord_pitches(root, mode, degree, octave=dna.bass_octave)[0]

        for beat, interval, duration, velocity in pattern:
            # Adjust for energy
            if energy == "intro":
                velocity = max(40, velocity - 20)
                duration = duration * 1.5
            elif energy == "build":
                velocity = min(127, velocity + (bar % 4) * 3)
            elif energy == "break":
                velocity = max(40, velocity - 15)
                duration = duration * 1.3

            pitch = chord_root + interval
            # Keep bass in a sane range (MIDI 24-55)
            while pitch > 55:
                pitch -= 12
            while pitch < 24:
                pitch += 12

            notes.append({
                "pitch": pitch,
                "start": round(bar * 4.0 + beat, 4),
                "duration": round(max(0.08, duration), 4),
                "velocity": clamp(velocity, 1, 127),
                "mute": False,
            })

    grooved = apply_groove(notes, dna, seed, "bass")
    if dna.name == "trap" and len(grooved) > 1:
        for i in range(len(grooved) - 1):
            curr_note = grooved[i]
            next_note = grooved[i + 1]
            gap = float(next_note["start"]) - (float(curr_note["start"]) + float(curr_note["duration"]))
            if gap < 0.25:
                curr_note["duration"] = round(float(next_note["start"]) - float(curr_note["start"]) + 0.1, 4)
                next_note["velocity"] = int(clamp(max(110, int(next_note["velocity"]) + 15), 1, 127))
                next_note["pitch"] = int(clamp(int(next_note["pitch"]) + 12, 0, 127))
    return grooved


def genre_lead(text: str, bars: int = 4, energy: str = "main", genre: str = "") -> list[dict[str, Any]]:
    """Generate a lead/hook using the GenreDNA profile for the given genre."""
    root, mode = infer_key(text, genre=genre)
    dna = lookup_genre(genre)
    seed = _pattern_seed(text, energy, bars, "lead")
    phrase = pick_pattern(dna.lead_phrases, seed)
    if not phrase:
        return generate_melody(text, bars)

    scale = SCALES.get(mode, SCALES["minor"])
    base = note_number(root, dna.lead_octave)
    notes: list[dict[str, Any]] = []

    for bar in range(bars):
        for beat, degree, duration, velocity in phrase:
            # Map scale degree to pitch
            octave_shift = 0
            effective_degree = degree
            while effective_degree >= len(scale):
                effective_degree -= len(scale)
                octave_shift += 12

            pitch = base + scale[effective_degree] + octave_shift

            # Energy adjustments
            if energy == "intro":
                velocity = max(40, velocity - 18)
                duration = duration * 1.4
            elif energy == "build":
                velocity = min(127, velocity + (bar % 4) * 4)
            elif energy == "break":
                velocity = max(40, velocity - 12)
                duration = duration * 1.6

            # Add variation: every 4th bar, shift last notes up
            if bar % 4 == 3 and beat >= 3.0:
                pitch += 12

            notes.append({
                "pitch": int(clamp(pitch, 0, 127)),
                "start": round(bar * 4.0 + beat, 4),
                "duration": round(max(0.08, duration), 4),
                "velocity": int(clamp(velocity, 1, 127)),
                "mute": False,
            })

    notes = shape_melody(notes, dna.name, seed, scale, base, energy)
    return apply_groove(notes, dna, seed, "lead")


def shape_melody(
    notes: list[dict[str, Any]],
    style: str,
    seed: int,
    scale: list[int],
    base: int,
    energy: str,
) -> list[dict[str, Any]]:
    rule = MELODY_RULES.get(style, MELODY_RULES["house"])
    phrase_bars = 2 if energy == "break" else 4
    shaped: list[dict[str, Any]] = []

    for index, note in enumerate(notes):
        start = float(note["start"])
        bar = int(start // 4)
        local_beat = start - bar * 4
        is_phrase_late = (bar + 1) % phrase_bars == 0 and local_beat >= 2.5
        rest_score = stable_seed({"seed": seed, "style": style, "index": index, "bar": bar}) % 1000 / 1000
        if local_beat > 0.25 and not is_phrase_late and rest_score < rule.rest_density:
            continue

        copy = dict(note)
        contour = rule.contour[bar % len(rule.contour)]
        copy["pitch"] = int(clamp(int(copy["pitch"]) + contour, 0, 127))
        if energy == "intro":
            copy["velocity"] = int(clamp(int(copy["velocity"]) - 8, 1, 127))
        shaped.append(copy)

    if not shaped:
        return notes

    phrase_last_indexes: dict[int, int] = {}
    for index, note in enumerate(shaped):
        phrase = int(float(note["start"]) // (phrase_bars * 4))
        if phrase not in phrase_last_indexes or float(note["start"]) >= float(shaped[phrase_last_indexes[phrase]]["start"]):
            phrase_last_indexes[phrase] = index

    target_class = scale[rule.ending_degree % len(scale)]
    ending_candidates = [base + target_class + octave * 12 for octave in range(-2, 3)]
    for index in phrase_last_indexes.values():
        note = shaped[index]
        note["pitch"] = int(clamp(nearest_pitch(int(note["pitch"]), ending_candidates), 0, 127))
        note["duration"] = round(max(float(note["duration"]), rule.ending_duration), 4)
        note["velocity"] = int(clamp(int(note["velocity"]) + 4, 1, 127))

    return shaped


def nearest_pitch(current: int, candidates: list[int]) -> int:
    return min(candidates, key=lambda pitch: abs(pitch - current))


def genre_chords(text: str, bars: int = 4, energy: str = "main", genre: str = "", parallel_motion: bool = False) -> list[dict[str, Any]]:
    """Generate chords using the GenreDNA profile for the given genre."""
    root, mode = infer_key(text, genre=genre)
    dna = lookup_genre(genre)
    seed = _pattern_seed(text, energy, bars, "chords")
    rhythm = pick_pattern(dna.chord_rhythms, seed)
    if not rhythm:
        return generate_chords(text, bars)

    lowered_text = text.lower()
    if "parallel" in lowered_text or "sampling" in lowered_text or "lock chord" in lowered_text:
        parallel_motion = True

    colour = detect_colour(text)
    harmony = plan_harmony(
        root_midi=note_number(root, 4),
        mode=mode,
        style=dna.name,
        colour=colour,
        bars=bars,
        octave=dna.chord_octave,
        seed=seed,
        extensions=dna.chord_extensions,
        parallel_motion=parallel_motion,
    )
    notes: list[dict[str, Any]] = []

    for bar in range(bars):
        pitches = harmony.voiced_chords[bar % len(harmony.voiced_chords)]

        # Determine duration based on style
        if dna.chord_style == "pad":
            dur = 3.75 if energy in ("intro", "break") else dna.chord_duration
        else:
            dur = dna.chord_duration

        # Velocity based on energy
        base_vel = 72 if energy in ("intro", "break") else 86

        for beat_pos in rhythm:
            for i, pitch in enumerate(pitches):
                vel = base_vel - i * 3  # lower voices slightly quieter
                notes.append({
                    "pitch": int(clamp(pitch, 0, 127)),
                    "start": round(bar * 4.0 + beat_pos, 4),
                    "duration": round(dur, 4),
                    "velocity": int(clamp(vel, 1, 127)),
                    "mute": False,
                })

    return apply_groove(notes, dna, seed, "chord")


def genre_drums(bars: int = 4, energy: str = "main", genre: str = "") -> list[dict[str, Any]]:
    """Generate a drum pattern using the GenreDNA profile as fallback.

    This is used when the MIDI library has no match. Instead of the old
    generic four-on-the-floor, it uses the genre's actual kick/snare/hat
    patterns.
    """
    dna = lookup_genre(genre)
    seed = _pattern_seed(genre, energy, bars, "drums")
    kick_pat = pick_pattern(dna.kick_patterns, seed)
    snare_pat = pick_pattern(dna.snare_patterns, seed)
    hat_pat = pick_pattern(dna.hat_patterns, seed + 1)
    mutation_rng = seeded_rng({"seed": seed, "kind": "bar_to_bar_drum_mutation"})

    notes: list[dict[str, Any]] = []

    for bar in range(bars):
        start = bar * 4.0

        # Kicks
        for beat in kick_pat:
            if energy == "intro" and beat not in (0.0,):
                continue  # sparse intro kick
            vel = 110 if beat == 0.0 else 100
            notes.append({
                "pitch": 36, "start": round(start + beat, 4),
                "duration": 0.16, "velocity": vel, "mute": False,
            })

        # Snares / Claps
        if energy != "intro" or bar % 2 == 1:
            for beat in snare_pat:
                notes.append({
                    "pitch": 38, "start": round(start + beat, 4),
                    "duration": 0.16, "velocity": 104, "mute": False,
                })

        # Hats
        for i, beat in enumerate(hat_pat):
            if energy in {"main", "build"}:
                phase = bar % 4
                keep_probability = 0.9 if phase == 1 else (0.7 if phase == 2 else 1.0)
                if mutation_rng.random() > keep_probability:
                    continue
            vel = 58 + (i % 4) * 8
            if energy == "build":
                vel = min(127, vel + (bar % 4) * 3)
            hat_pitch = 46 if (i % 4 == 2 and energy in ("main", "build")) else 42
            notes.append({
                "pitch": hat_pitch, "start": round(start + beat, 4),
                "duration": 0.08, "velocity": vel, "mute": False,
            })

        # Fill on last bar of every 4
        if energy in ("main", "build") and bar % 4 == 3:
            for step in range(8):
                notes.append({
                    "pitch": 38, "start": round(start + 3.0 + step * 0.125, 4),
                    "duration": 0.08,
                    "velocity": 72 + step * 5,
                    "mute": False,
                })

    grooved = [
        _groove_note(note, dna.groove_profile, dna.bpm_default, {"seed": seed, "index": index}, drum_role_for_pitch(int(note["pitch"])))
        for index, note in enumerate(notes)
    ]
    return sorted(grooved, key=lambda item: (float(item["start"]), int(item["pitch"])))
