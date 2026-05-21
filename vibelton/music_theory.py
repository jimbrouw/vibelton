from __future__ import annotations

from dataclasses import dataclass
from typing import Any


NOTE_NAMES_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
NOTE_NAMES_FLAT = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")

NOTE_TO_PC = {
    "c": 0,
    "b#": 0,
    "c#": 1,
    "db": 1,
    "d": 2,
    "d#": 3,
    "eb": 3,
    "e": 4,
    "fb": 4,
    "e#": 5,
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
    "cb": 11,
}

SCALE_INTERVALS = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "natural minor": (0, 2, 3, 5, 7, 8, 10),
    "harmonic minor": (0, 2, 3, 5, 7, 8, 11),
    "melodic minor": (0, 2, 3, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "minor pentatonic": (0, 3, 5, 7, 10),
    "major pentatonic": (0, 2, 4, 7, 9),
}

MAJOR_DIATONIC_QUALITIES = ("major", "minor", "minor", "major", "major", "minor", "diminished")
MINOR_DIATONIC_QUALITIES = ("minor", "diminished", "major", "minor", "minor", "major", "major")
ROMAN_MAJOR = ("I", "ii", "iii", "IV", "V", "vi", "vii°")
ROMAN_MINOR = ("i", "ii°", "III", "iv", "v", "VI", "VII")

FLAT_KEYS = {5, 10, 3, 8, 1, 6, 11}
ORDER_OF_SHARPS = ("F", "C", "G", "D", "A", "E", "B")
ORDER_OF_FLATS = ("B", "E", "A", "D", "G", "C", "F")


@dataclass(frozen=True)
class ScaleBrain:
    root: str
    mode: str
    notes: tuple[str, ...]
    relative_key: str
    diatonic_chords: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class RhythmFeel:
    name: str
    grid: str
    primary_hits: tuple[float, ...]
    offbeats: tuple[float, ...]
    description: str


@dataclass(frozen=True)
class VoiceRole:
    name: str
    midi_range: tuple[int, int]
    producer_role: str
    motion_advice: str


@dataclass(frozen=True)
class ProgressionRecipe:
    vibe: str
    mode: str
    degrees: tuple[str, ...]
    description: str


VOICE_ROLES = (
    VoiceRole("bass", (24, 48), "low rhythm and root motion", "Use stable motion; contrary motion against melody adds push and pull."),
    VoiceRole("tenor", (48, 60), "main melody support or low hook", "Keep it singable and avoid crowding the bass."),
    VoiceRole("alto", (55, 72), "counter melody and inner movement", "Use stepwise motion to connect chords."),
    VoiceRole("soprano", (67, 84), "lead pattern and top-line identity", "Use clear contour and repetition so the hook reads quickly."),
)

RHYTHM_FEELS = {
    "downbeat": RhythmFeel(
        name="downbeat",
        grid="4/4 quarter-note anchors",
        primary_hits=(0.0, 1.0, 2.0, 3.0),
        offbeats=(0.5, 1.5, 2.5, 3.5),
        description="Strong count-based rhythm. Good for weight, clarity, kicks, and simple hooks.",
    ),
    "upbeat": RhythmFeel(
        name="upbeat",
        grid="4/4 eighth-note offbeats",
        primary_hits=(0.5, 1.5, 2.5, 3.5),
        offbeats=(0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75),
        description="Offbeat rhythm. Good for lift, bounce, hats, stabs, and dance momentum.",
    ),
    "syncopated": RhythmFeel(
        name="syncopated",
        grid="16th-note grid with displaced accents",
        primary_hits=(0.0, 0.75, 1.5, 2.5, 3.25),
        offbeats=(0.25, 1.25, 2.25, 3.75),
        description="Accents avoid obvious counts. Good for groove, tension, and call-and-response.",
    ),
}

PROGRESSION_RECIPES = (
    ProgressionRecipe("romantic", "minor", ("i", "III", "VI", "iv"), "Sentimental minor color with a lifted relative-major center."),
    ProgressionRecipe("sentimental", "minor", ("i", "III", "VI", "iv"), "Stable emotional loop with soft resolution."),
    ProgressionRecipe("sad", "minor", ("i", "VI", "III", "VII"), "Common producer-friendly minor loop with immediate mood."),
    ProgressionRecipe("dark", "minor", ("i", "VI", "iv", "V"), "Darker minor movement with stronger dominant pull."),
    ProgressionRecipe("uplifting", "major", ("I", "V", "vi", "IV"), "Broad major-pop lift with familiar resolution."),
    ProgressionRecipe("hopeful", "major", ("I", "V", "vi", "IV"), "Clear major-center loop with emotional lift."),
    ProgressionRecipe("jazzy", "major", ("Imaj7", "iii7", "vi7", "ii7", "V7"), "Extended harmony for smoother color and motion."),
    ProgressionRecipe("club", "minor", ("i", "VII", "VI", "VII"), "Loopable minor movement for dance arrangements."),
)


def normalize_note_name(note: str) -> str:
    clean = note.strip().lower().replace("♯", "#").replace("♭", "b")
    if clean not in NOTE_TO_PC:
        raise ValueError(f"Unknown note name: {note}")
    return NOTE_NAMES_SHARP[NOTE_TO_PC[clean]]


def pitch_class(note: str) -> int:
    clean = note.strip().lower().replace("♯", "#").replace("♭", "b")
    if clean not in NOTE_TO_PC:
        raise ValueError(f"Unknown note name: {note}")
    return NOTE_TO_PC[clean]


def note_name(pc: int, prefer_flats: bool = False) -> str:
    names = NOTE_NAMES_FLAT if prefer_flats else NOTE_NAMES_SHARP
    return names[pc % 12]


def scale_notes(root: str, mode: str = "major") -> tuple[str, ...]:
    normalized_mode = mode.lower().strip()
    intervals = SCALE_INTERVALS.get(normalized_mode)
    if intervals is None:
        raise ValueError(f"Unsupported scale mode: {mode}")
    root_pc = pitch_class(root)
    prefer_flats = root_pc in FLAT_KEYS
    return tuple(note_name(root_pc + interval, prefer_flats=prefer_flats) for interval in intervals)


def relative_key(root: str, mode: str = "major") -> str:
    normalized_mode = "minor" if "minor" in mode.lower() else "major"
    notes = scale_notes(root, normalized_mode)
    if normalized_mode == "major":
        return f"{notes[5]} minor"
    return f"{notes[2]} major"


def diatonic_chords(root: str, mode: str = "major") -> tuple[dict[str, str], ...]:
    normalized_mode = "minor" if "minor" in mode.lower() else "major"
    notes = scale_notes(root, normalized_mode)
    qualities = MINOR_DIATONIC_QUALITIES if normalized_mode == "minor" else MAJOR_DIATONIC_QUALITIES
    romans = ROMAN_MINOR if normalized_mode == "minor" else ROMAN_MAJOR
    return tuple(
        {
            "degree": str(index + 1),
            "roman": romans[index],
            "root": notes[index],
            "quality": qualities[index],
            "chord": format_chord(notes[index], qualities[index]),
        }
        for index in range(7)
    )


def format_chord(root: str, quality: str) -> str:
    if quality == "major":
        return root
    if quality == "minor":
        return f"{root}m"
    if quality == "diminished":
        return f"{root}dim"
    if quality == "augmented":
        return f"{root}aug"
    return f"{root} {quality}"


def scale_brain(root: str, mode: str = "major") -> ScaleBrain:
    normalized_mode = "minor" if "minor" in mode.lower() else "major"
    return ScaleBrain(
        root=normalize_note_name(root),
        mode=normalized_mode,
        notes=scale_notes(root, normalized_mode),
        relative_key=relative_key(root, normalized_mode),
        diatonic_chords=diatonic_chords(root, normalized_mode),
    )


def chord_quality_from_intervals(intervals: tuple[int, ...]) -> str:
    normalized = tuple(sorted(interval % 12 for interval in intervals))
    if normalized[:3] == (0, 4, 7):
        return "major"
    if normalized[:3] == (0, 3, 7):
        return "minor"
    if normalized[:3] == (0, 3, 6):
        return "diminished"
    if normalized[:3] == (0, 4, 8):
        return "augmented"
    if len(normalized) >= 4 and normalized[:4] == (0, 4, 7, 11):
        return "major seventh"
    if len(normalized) >= 4 and normalized[:4] == (0, 3, 7, 10):
        return "minor seventh"
    if len(normalized) >= 4 and normalized[:4] == (0, 4, 7, 10):
        return "dominant seventh"
    return "unknown"


def chord_tones(root: str, quality: str = "major") -> tuple[str, ...]:
    intervals_by_quality = {
        "major": (0, 4, 7),
        "minor": (0, 3, 7),
        "diminished": (0, 3, 6),
        "augmented": (0, 4, 8),
        "major seventh": (0, 4, 7, 11),
        "minor seventh": (0, 3, 7, 10),
        "dominant seventh": (0, 4, 7, 10),
    }
    intervals = intervals_by_quality.get(quality.lower().strip())
    if intervals is None:
        raise ValueError(f"Unsupported chord quality: {quality}")
    root_pc = pitch_class(root)
    prefer_flats = root_pc in FLAT_KEYS
    return tuple(note_name(root_pc + interval, prefer_flats=prefer_flats) for interval in intervals)


def circle_of_fifths() -> dict[str, tuple[str, ...]]:
    return {
        "sharps": ORDER_OF_SHARPS,
        "flats": ORDER_OF_FLATS,
        "memory_shortcut": tuple(reversed(ORDER_OF_FLATS)),
    }


def rhythm_feel(name: str) -> RhythmFeel:
    return RHYTHM_FEELS.get(name.lower().strip(), RHYTHM_FEELS["downbeat"])


def recommend_progression(vibe: str, mode: str | None = None) -> ProgressionRecipe:
    lowered = vibe.lower()
    candidates = [recipe for recipe in PROGRESSION_RECIPES if recipe.vibe in lowered]
    if mode:
        normalized_mode = "minor" if "minor" in mode.lower() else "major"
        candidates = [recipe for recipe in candidates if recipe.mode == normalized_mode] or candidates
    if candidates:
        return candidates[0]
    if mode and "major" in mode.lower():
        return next(recipe for recipe in PROGRESSION_RECIPES if recipe.vibe == "uplifting")
    return next(recipe for recipe in PROGRESSION_RECIPES if recipe.vibe == "sad")


def progression_chords(root: str, mode: str, degrees: tuple[str, ...]) -> tuple[str, ...]:
    chord_map = {entry["roman"].replace("°", ""): entry["chord"] for entry in diatonic_chords(root, mode)}
    chord_map.update({entry["roman"].lower().replace("°", ""): entry["chord"] for entry in diatonic_chords(root, mode)})
    result = []
    for degree in degrees:
        clean = degree.replace("maj7", "").replace("7", "").replace("°", "")
        base = chord_map.get(clean) or chord_map.get(clean.lower()) or chord_map.get(clean.upper())
        if base is None:
            base = degree
        if "maj7" in degree:
            base = base.replace("m", "") + "maj7"
        elif degree.endswith("7") and not base.endswith("7"):
            base = f"{base}7"
        result.append(base)
    return tuple(result)


def producer_theory_card(root: str, mode: str, vibe: str = "") -> dict[str, Any]:
    brain = scale_brain(root, mode)
    recipe = recommend_progression(vibe or mode, brain.mode)
    return {
        "key": f"{brain.root} {brain.mode}",
        "notes": brain.notes,
        "relative_key": brain.relative_key,
        "diatonic_chords": brain.diatonic_chords,
        "circle_of_fifths": circle_of_fifths(),
        "voices": tuple(role.__dict__ for role in VOICE_ROLES),
        "rhythm_feels": {name: feel.__dict__ for name, feel in RHYTHM_FEELS.items()},
        "recommended_progression": {
            "vibe": recipe.vibe,
            "degrees": recipe.degrees,
            "chords": progression_chords(brain.root, brain.mode, recipe.degrees),
            "description": recipe.description,
        },
    }
