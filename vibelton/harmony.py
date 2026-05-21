from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any


SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
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

PROGRESSION_MODELS: dict[str, dict[str, dict[str, list[tuple[str, int]]]]] = {
    "default": {
        "major": {
            "neutral": [("I", 5), ("V", 4), ("vi", 4), ("IV", 4), ("ii", 1)],
            "moody": [("vi", 5), ("IV", 4), ("I", 3), ("V", 3), ("ii", 1)],
            "cinematic": [("I", 4), ("vi", 3), ("IV", 4), ("bVII", 2), ("V", 3)],
            "jazzy": [("I", 4), ("iii", 2), ("vi", 3), ("ii", 3), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 5), ("VI", 4), ("III", 4), ("VII", 4), ("iv", 2)],
            "moody": [("i", 5), ("iv", 4), ("VI", 4), ("VII", 3), ("v", 2)],
            "cinematic": [("i", 5), ("VI", 4), ("iv", 4), ("bII", 2), ("V", 3)],
            "jazzy": [("i", 4), ("iv", 4), ("VII", 3), ("III", 3), ("V", 2)],
        },
    },
    "house": {
        "major": {
            "neutral": [("I", 4), ("V", 3), ("IV", 4), ("vi", 3), ("ii", 2)],
            "moody": [("vi", 4), ("IV", 3), ("I", 3), ("V", 2)],
            "cinematic": [("I", 4), ("vi", 3), ("bVII", 2), ("IV", 3)],
            "jazzy": [("I", 4), ("vi", 3), ("ii", 3), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 5), ("VI", 4), ("III", 3), ("VII", 4), ("iv", 2)],
            "moody": [("i", 5), ("iv", 4), ("VI", 3), ("VII", 3)],
            "cinematic": [("i", 4), ("VI", 4), ("iv", 3), ("bVII", 2), ("V", 2)],
            "jazzy": [("i", 3), ("iv", 3), ("VII", 3), ("III", 2), ("ii", 2)],
        }
    },
    "uk garage": {
        "major": {
            "neutral": [("I", 4), ("ii", 4), ("V", 4), ("vi", 3), ("IV", 3)],
            "moody": [("vi", 5), ("ii", 3), ("IV", 3), ("V", 3)],
            "cinematic": [("I", 3), ("vi", 3), ("bVII", 2), ("IV", 3), ("V", 2)],
            "jazzy": [("I", 3), ("iii", 3), ("vi", 3), ("ii", 4), ("V", 4)],
        },
        "minor": {
            "neutral": [("i", 4), ("iv", 4), ("VII", 3), ("III", 3)],
            "moody": [("i", 5), ("VI", 3), ("VII", 3), ("v", 2)],
            "cinematic": [("i", 4), ("VI", 4), ("bII", 2), ("V", 2)],
            "jazzy": [("i", 3), ("iv", 3), ("v", 2), ("bVII", 2)],
        }
    },
    "drum n bass": {
        "major": {
            "neutral": [("I", 5), ("vi", 4), ("IV", 3), ("V", 3)],
            "moody": [("vi", 5), ("ii", 3), ("V", 3), ("I", 2)],
            "cinematic": [("I", 4), ("bVII", 3), ("vi", 3), ("IV", 2)],
            "jazzy": [("I", 3), ("iii", 3), ("vi", 3), ("ii", 3), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 6), ("VI", 4), ("VII", 3), ("iv", 2)],
            "moody": [("i", 7), ("VI", 3), ("v", 3), ("iv", 2)],
            "cinematic": [("i", 5), ("VI", 4), ("bII", 2), ("V", 3)],
            "jazzy": [("i", 4), ("iv", 4), ("VII", 3), ("v", 2)],
        }
    },
    "jungle": {
        "major": {
            "neutral": [("I", 4), ("IV", 3), ("vi", 3), ("V", 2)],
            "moody": [("vi", 5), ("IV", 4), ("ii", 3), ("V", 2)],
            "cinematic": [("I", 4), ("bVII", 2), ("IV", 3), ("vi", 2)],
            "jazzy": [("I", 3), ("vi", 3), ("ii", 4), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 6), ("bVII", 3), ("iv", 3), ("VI", 2)],
            "moody": [("i", 7), ("v", 3), ("VI", 3), ("iv", 2)],
            "cinematic": [("i", 5), ("VI", 4), ("bII", 2), ("v", 2)],
            "jazzy": [("i", 4), ("iv", 4), ("VII", 3), ("v", 2)],
        }
    },
    "techno": {
        "major": {
            "neutral": [("I", 6), ("IV", 3), ("V", 3), ("vi", 2)],
            "moody": [("vi", 6), ("IV", 4), ("ii", 2), ("V", 2)],
            "cinematic": [("I", 5), ("vi", 3), ("bVII", 2), ("IV", 3)],
            "jazzy": [("I", 4), ("vi", 3), ("ii", 3), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 7), ("VII", 3), ("VI", 2), ("iv", 2), ("v", 2)],
            "moody": [("i", 7), ("v", 4), ("VI", 3), ("iv", 2)],
            "cinematic": [("i", 5), ("VI", 3), ("iv", 3), ("bII", 2), ("V", 2)],
            "jazzy": [("i", 4), ("iv", 3), ("VII", 3), ("ii", 2), ("V", 2)],
        }
    },
    "trance": {
        "major": {
            "neutral": [("I", 5), ("V", 4), ("vi", 4), ("IV", 4)],
            "moody": [("vi", 5), ("IV", 4), ("I", 3), ("V", 3)],
            "cinematic": [("I", 5), ("vi", 4), ("IV", 4), ("bVII", 3), ("V", 3)],
            "jazzy": [("I", 4), ("iii", 3), ("vi", 3), ("ii", 3), ("V", 2)],
        },
        "minor": {
            "neutral": [("i", 5), ("VI", 4), ("III", 4), ("VII", 4)],
            "moody": [("i", 5), ("iv", 4), ("VI", 4), ("VII", 3)],
            "cinematic": [("i", 5), ("VI", 4), ("iv", 4), ("VII", 3), ("V", 3)],
            "jazzy": [("i", 4), ("iv", 4), ("VII", 3), ("III", 3), ("v", 2)],
        }
    },
    "trap": {
        "major": {
            "neutral": [("I", 5), ("vi", 4), ("IV", 3), ("ii", 2)],
            "moody": [("vi", 6), ("ii", 3), ("IV", 3), ("V", 2)],
            "cinematic": [("I", 5), ("bVII", 2), ("vi", 3), ("IV", 3)],
            "jazzy": [("I", 4), ("vi", 3), ("ii", 3), ("V", 2)],
        },
        "minor": {
            "neutral": [("i", 6), ("VI", 3), ("v", 3), ("VII", 2), ("iv", 2)],
            "moody": [("i", 7), ("bII", 2), ("VI", 3), ("v", 4), ("iv", 2)],
            "cinematic": [("i", 5), ("VI", 4), ("bII", 2), ("V", 3), ("iv", 2)],
            "jazzy": [("i", 4), ("iv", 3), ("VI", 3), ("VII", 2), ("V", 2)],
        }
    },
    "hip hop": {
        "major": {
            "neutral": [("I", 4), ("vi", 4), ("ii", 3), ("V", 3)],
            "moody": [("vi", 5), ("IV", 3), ("ii", 3), ("V", 2)],
            "cinematic": [("I", 4), ("vi", 3), ("bVII", 2), ("IV", 3)],
            "jazzy": [("I", 3), ("vi", 3), ("ii", 4), ("V", 4)],
        },
        "minor": {
            "neutral": [("i", 5), ("VI", 4), ("iv", 3), ("VII", 3), ("III", 2)],
            "moody": [("i", 5), ("iv", 5), ("VI", 3), ("v", 2)],
            "cinematic": [("i", 4), ("bII", 2), ("VI", 4), ("iv", 4), ("V", 2)],
            "jazzy": [("i", 3), ("iv", 4), ("VII", 3), ("III", 3), ("ii", 2)],
        }
    },
    "reggaeton": {
        "major": {
            "neutral": [("I", 5), ("V", 4), ("vi", 4), ("IV", 4)],
            "moody": [("vi", 5), ("IV", 4), ("I", 3), ("V", 3)],
            "cinematic": [("I", 4), ("vi", 4), ("IV", 3), ("V", 3)],
            "jazzy": [("I", 4), ("vi", 3), ("ii", 3), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 5), ("VII", 4), ("VI", 4), ("v", 3), ("iv", 2)],
            "moody": [("i", 5), ("VI", 4), ("v", 3), ("VII", 3)],
            "cinematic": [("i", 4), ("VI", 4), ("iv", 3), ("bII", 2), ("V", 2)],
            "jazzy": [("i", 4), ("iv", 3), ("VII", 3), ("III", 2), ("V", 2)],
        }
    },
    "downtempo": {
        "major": {
            "neutral": [("I", 4), ("IV", 4), ("vi", 3), ("ii", 3), ("V", 2)],
            "moody": [("vi", 5), ("ii", 3), ("IV", 3), ("I", 2), ("V", 1)],
            "cinematic": [("I", 4), ("bVII", 3), ("IV", 4), ("vi", 3), ("V", 2)],
            "jazzy": [("I", 3), ("vi", 3), ("ii", 4), ("V", 4), ("IV", 2)],
        },
        "minor": {
            "neutral": [("i", 4), ("iv", 4), ("VII", 3), ("III", 3), ("VI", 2)],
            "moody": [("i", 5), ("VI", 4), ("iv", 4), ("v", 2), ("bII", 2)],
            "cinematic": [("i", 4), ("VI", 4), ("bII", 2), ("V", 2), ("iv", 3)],
            "jazzy": [("i", 3), ("iv", 4), ("VII", 3), ("III", 3), ("ii", 3)],
        }
    },
    "ambient": {
        "major": {
            "neutral": [("I", 5), ("IV", 4), ("vi", 4), ("ii", 3), ("V", 1)],
            "moody": [("vi", 5), ("IV", 4), ("ii", 3), ("I", 2), ("V", 1)],
            "cinematic": [("I", 5), ("bVII", 3), ("IV", 5), ("vi", 3), ("ii", 2)],
            "jazzy": [("I", 4), ("iii", 3), ("ii", 4), ("vi", 3), ("V", 1)],
        },
        "minor": {
            "neutral": [("i", 4), ("VI", 5), ("iv", 4), ("VII", 2), ("v", 1)],
            "moody": [("i", 5), ("VI", 4), ("iv", 5), ("bII", 2), ("v", 1)],
            "cinematic": [("i", 5), ("bII", 3), ("VI", 4), ("iv", 4), ("V", 2)],
            "jazzy": [("i", 3), ("iv", 4), ("VII", 3), ("III", 3), ("ii", 2)],
        },
    },
    "pop": {
        "major": {
            "neutral": [("I", 5), ("V", 4), ("vi", 4), ("IV", 4)],
            "moody": [("vi", 5), ("IV", 4), ("I", 3), ("V", 3)],
            "cinematic": [("I", 5), ("vi", 3), ("IV", 4), ("V", 3)],
            "jazzy": [("I", 4), ("vi", 3), ("ii", 3), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 5), ("VI", 4), ("III", 4), ("VII", 4)],
            "moody": [("i", 5), ("iv", 4), ("VI", 4), ("VII", 3)],
            "cinematic": [("i", 5), ("VI", 4), ("III", 3), ("VII", 4)],
            "jazzy": [("i", 4), ("iv", 4), ("VII", 3), ("III", 3), ("v", 2)],
        }
    },
    "afrobeats": {
        "major": {
            "neutral": [("I", 4), ("IV", 4), ("V", 3), ("vi", 3)],
            "moody": [("vi", 4), ("IV", 4), ("I", 3), ("V", 3)],
            "cinematic": [("I", 4), ("vi", 3), ("IV", 3), ("bVII", 2)],
            "jazzy": [("I", 3), ("IV", 4), ("ii", 3), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 4), ("VII", 4), ("v", 3), ("VI", 3)],
            "moody": [("i", 5), ("VI", 4), ("v", 3), ("VII", 3)],
            "cinematic": [("i", 4), ("VI", 4), ("iv", 3), ("V", 2)],
            "jazzy": [("i", 3), ("iv", 4), ("v", 3), ("bVII", 2)],
        }
    },
    "amapiano": {
        "major": {
            "neutral": [("I", 4), ("IV", 4), ("vi", 3), ("ii", 3)],
            "moody": [("vi", 5), ("IV", 4), ("ii", 3), ("V", 2)],
            "cinematic": [("I", 4), ("vi", 3), ("IV", 3), ("V", 2)],
            "jazzy": [("I", 3), ("IV", 4), ("ii", 4), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 4), ("iv", 4), ("VII", 3), ("III", 3)],
            "moody": [("i", 5), ("VI", 4), ("v", 3), ("VII", 3)],
            "cinematic": [("i", 4), ("VI", 4), ("iv", 3), ("v", 2)],
            "jazzy": [("i", 3), ("iv", 4), ("v", 3), ("VII", 3)],
        }
    },
    "hyperpop": {
        "major": {
            "neutral": [("I", 5), ("IV", 5), ("V", 4), ("vi", 3)],
            "moody": [("vi", 5), ("IV", 4), ("ii", 4), ("V", 3)],
            "cinematic": [("I", 5), ("vi", 4), ("IV", 4), ("V", 4)],
            "jazzy": [("I", 4), ("IV", 3), ("ii", 3), ("V", 3)],
        },
        "minor": {
            "neutral": [("i", 5), ("VI", 5), ("VII", 4), ("III", 3)],
            "moody": [("i", 5), ("VI", 4), ("iv", 4), ("VII", 3)],
            "cinematic": [("i", 5), ("VI", 4), ("iv", 4), ("v", 3)],
            "jazzy": [("i", 4), ("iv", 4), ("VII", 3), ("v", 3)],
        }
    },
}


@dataclass(frozen=True)
class HarmonyPlan:
    degrees: list[str]
    voiced_chords: list[list[int]]
    colour: str
    used_music21: bool = False


def detect_colour(text: str) -> str:
    lowered = text.lower()
    if "jazzy" in lowered or "jazz" in lowered:
        return "jazzy"
    if "cinematic" in lowered or "epic" in lowered:
        return "cinematic"
    if "moody" in lowered or "dark" in lowered or "sad" in lowered:
        return "moody"
    return "neutral"


@lru_cache(maxsize=1)
def optional_music21() -> Any | None:
    try:
        import music21  # type: ignore
    except Exception:
        return None
    return music21


def weighted_progression(style: str, mode: str, colour: str, bars: int, seed: int) -> list[str]:
    style_model = PROGRESSION_MODELS.get(style, {})
    mode_model = style_model.get(mode) or PROGRESSION_MODELS["default"][mode]
    weighted = mode_model.get(colour) or mode_model["neutral"]
    bag = [degree for degree, weight in weighted for _ in range(max(1, weight))]
    result = []
    index = seed % len(bag)
    step = max(1, (seed % 5) + 1)
    for bar in range(bars):
        degree = bag[(index + bar * step) % len(bag)]
        if bar == 0 and degree.lower() not in {"i", "I".lower()}:
            degree = "i" if mode == "minor" else "I"
        result.append(degree)
    return result


def plan_harmony(
    root_midi: int,
    mode: str,
    style: str,
    colour: str,
    bars: int,
    octave: int,
    seed: int,
    extensions: tuple[int, ...] = (),
    parallel_motion: bool = False,
) -> HarmonyPlan:
    degrees = weighted_progression(style, mode, colour, bars, seed)
    raw = [chord_from_degree(root_midi, mode, degree, octave, extensions, colour) for degree in degrees]
    if parallel_motion and raw:
        first_voiced = sorted(raw[0])
        first_root = raw[0][0]
        intervals = [pitch - first_root for pitch in first_voiced]
        voiced = []
        for raw_chord in raw:
            current_root = raw_chord[0]
            voiced.append([current_root + interval for interval in intervals])
    else:
        voiced = voice_lead(raw)
    return HarmonyPlan(degrees=degrees, voiced_chords=voiced, colour=colour, used_music21=False)


def chord_from_degree(
    root_midi: int,
    mode: str,
    degree: str,
    octave: int,
    extensions: tuple[int, ...],
    colour: str,
) -> list[int]:
    scale = SCALES.get(mode, SCALES["minor"])
    root = root_midi + (octave - 4) * 12
    normalized = degree.replace("b", "").lower()
    degree_index = ROMAN_DEGREES.get(normalized, 0)
    accidental = -1 if degree.startswith("b") else 0
    base = root + scale[degree_index] + accidental
    if degree_index >= 5:
        base -= 12

    third = root + scale[(degree_index + 2) % 7]
    fifth = root + scale[(degree_index + 4) % 7]
    while third <= base:
        third += 12
    while fifth <= third:
        fifth += 12
    pitches = [base, third, fifth]

    for ext in extensions:
        pitches.append(base + ext)
    if colour == "jazzy" and len(pitches) < 4:
        pitches.append(base + 10)
    if colour == "cinematic" and len(pitches) < 4:
        pitches.append(base + 14)
    return pitches


def voice_lead(chords: list[list[int]]) -> list[list[int]]:
    if not chords:
        return []
    voiced = [sorted(chords[0])]
    for chord in chords[1:]:
        voiced.append(best_inversion(voiced[-1], chord))
    return voiced


def best_inversion(previous: list[int], chord: list[int]) -> list[int]:
    candidates = []
    for shift in range(-2, 3):
        shifted = [pitch + shift * 12 for pitch in chord]
        for rotation in range(len(shifted)):
            candidate = shifted[rotation:] + [pitch + 12 for pitch in shifted[:rotation]]
            candidate = sorted(candidate)
            distance = sum(abs(a - b) for a, b in zip(previous, candidate[: len(previous)]))
            candidates.append((distance, max(candidate) - min(candidate), candidate))
    return min(candidates, key=lambda item: (item[0], item[1]))[2]
