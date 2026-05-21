"""Genre DNA profiles for the Vibelton music brain.

Each genre defines distinct rhythm patterns, pitch ranges, and articulation
so that House, UK Garage, DnB etc. sound genuinely different.

Bass pattern entry: (beat_pos, semitone_interval, duration, velocity)
Lead phrase entry:  (beat_pos, scale_degree_idx, duration, velocity)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

# Type aliases for readability
BassPattern = list[tuple[float, int, float, int]]
LeadPhrase = list[tuple[float, int, float, int]]


@dataclass(frozen=True)
class CuratedGenreDNA:
    name: str
    bpm_range: tuple[int, int]
    swing_percent: tuple[int, int]
    bar_grid: str
    structure: tuple[str, ...]
    kick_pattern: str
    bass_pattern: str
    hi_hat_pattern: str
    energy_arc: str
    rules: tuple[str, ...]
    rule_breakers: tuple[str, ...]
    blends_with: tuple[str, ...]
    vibe_words: tuple[str, ...]


@dataclass(frozen=True)
class GrooveProfile:
    name: str
    position_jitter_ms: float
    velocity_jitter: int
    length_jitter: float
    weak_beat_curve: tuple[float, float, float, float]
    push_pull_per_subdivision: tuple[float, ...]

    @classmethod
    def from_swing(cls, swing: float, name: str = "straight") -> "GrooveProfile":
        shuffle = max(0.0, min(0.5, swing))
        return cls(
            name=name,
            position_jitter_ms=round(4.0 + shuffle * 40.0, 3),
            velocity_jitter=max(2, int(4 + shuffle * 40)),
            length_jitter=round(0.01 + shuffle * 0.08, 4),
            weak_beat_curve=(1.0, 0.82, 0.92, 0.78),
            push_pull_per_subdivision=(0.0, shuffle * 0.08, 0.0, shuffle * 0.04),
        )


GROOVE_TEMPLATES: dict[str, GrooveProfile] = {
    "straight": GrooveProfile.from_swing(0.0, "straight"),
    "mpc_58": GrooveProfile(
        name="mpc_58",
        position_jitter_ms=8.0,
        velocity_jitter=8,
        length_jitter=0.018,
        weak_beat_curve=(1.0, 0.78, 0.9, 0.72),
        push_pull_per_subdivision=(0.0, 0.0667, 0.0, 0.0667),
    ),
    "mpc_62": GrooveProfile(
        name="mpc_62",
        position_jitter_ms=10.0,
        velocity_jitter=10,
        length_jitter=0.022,
        weak_beat_curve=(1.0, 0.74, 0.88, 0.7),
        push_pull_per_subdivision=(0.0, 0.0667, 0.0, 0.0667),
    ),
    "dnb_tight": GrooveProfile(
        name="dnb_tight",
        position_jitter_ms=3.5,
        velocity_jitter=5,
        length_jitter=0.008,
        weak_beat_curve=(1.0, 0.86, 0.94, 0.82),
        push_pull_per_subdivision=(0.0, -0.004, 0.0, -0.006),
    ),
    "ukg_shuffle": GrooveProfile(
        name="ukg_shuffle",
        position_jitter_ms=7.0,
        velocity_jitter=9,
        length_jitter=0.018,
        weak_beat_curve=(1.0, 0.65, 0.9, 0.9),
        push_pull_per_subdivision=(0.0, 0.0417, 0.0, 0.0417),
    ),
    "dembow": GrooveProfile(
        name="dembow",
        position_jitter_ms=5.0,
        velocity_jitter=7,
        length_jitter=0.012,
        weak_beat_curve=(1.0, 0.65, 0.95, 0.95),
        push_pull_per_subdivision=(0.0, 0.006, 0.0, -0.004),
    ),
    "trap_triplet": GrooveProfile(
        name="trap_triplet",
        position_jitter_ms=4.0,
        velocity_jitter=12,
        length_jitter=0.01,
        weak_beat_curve=(1.0, 0.7, 0.86, 0.68),
        push_pull_per_subdivision=(0.0, 0.0, 0.0, 0.0),
    ),
}


@dataclass(frozen=True)
class GenreDNA:
    name: str
    bpm_default: int
    bpm_range: tuple[int, int]
    groove_profile: GrooveProfile

    # Drum beat positions within a 4-beat bar
    kick_patterns: tuple[list[float], ...]
    snare_patterns: tuple[list[float], ...]
    hat_patterns: tuple[list[float], ...]
    hat_style: str  # "8ths", "16ths", "triplets"

    # Bass
    bass_octave: int
    bass_patterns: tuple[BassPattern, ...]

    # Chords
    chord_octave: int
    chord_style: str  # "stab", "pad", "offbeat"
    chord_rhythms: tuple[list[float], ...]
    chord_duration: float
    chord_extensions: tuple[int, ...]  # extra semitones above triad

    # Lead
    lead_octave: int
    lead_phrases: tuple[LeadPhrase, ...]


# ── House ────────────────────────────────────────────────────────────
HOUSE = GenreDNA(
    name="house",
    bpm_default=124, bpm_range=(120, 128), groove_profile=GROOVE_TEMPLATES["straight"],

    kick_patterns=(
        [0.0, 1.0, 2.0, 3.0],
    ),
    snare_patterns=(
        [1.0, 3.0],
    ),
    hat_patterns=(
        [0.5, 1.5, 2.5, 3.5],                          # offbeat 8ths
        [i * 0.5 for i in range(8)],                    # straight 8ths
    ),
    hat_style="8ths",

    bass_octave=1,
    bass_patterns=(
        # Rolling 8ths on root and 5th
        [(0.0, 0, 0.4, 100), (0.5, 0, 0.4, 90), (1.0, 0, 0.4, 100),
         (1.5, 7, 0.4, 90), (2.0, 0, 0.4, 100), (2.5, 0, 0.4, 90),
         (3.0, 7, 0.4, 100), (3.5, 0, 0.4, 90)],
        # Quarter-note root pump
        [(0.0, 0, 0.7, 100), (1.0, 0, 0.7, 96),
         (2.0, 7, 0.7, 100), (3.0, 0, 0.7, 96)],
        # Disco-style octave bounce
        [(0.0, 0, 0.35, 100), (0.5, 12, 0.3, 80),
         (1.0, 0, 0.35, 100), (1.5, 12, 0.3, 80),
         (2.0, 0, 0.35, 100), (2.5, 12, 0.3, 80),
         (3.0, 7, 0.35, 100), (3.5, 12, 0.3, 80)],
    ),

    chord_octave=4, chord_style="stab",
    chord_rhythms=(
        [0.0, 1.0, 2.0, 3.0],
        [0.5, 1.5, 2.5, 3.5],          # offbeat stabs
    ),
    chord_duration=0.4,
    chord_extensions=(),                 # plain triads

    lead_octave=4,
    lead_phrases=(
        # Sparse, soulful
        [(0.0, 4, 0.5, 82), (1.0, 3, 0.4, 78), (2.0, 4, 0.6, 84),
         (3.0, 2, 0.5, 80)],
        # Funky riff
        [(0.0, 0, 0.3, 80), (0.5, 2, 0.3, 76), (1.5, 4, 0.4, 84),
         (2.0, 3, 0.3, 78), (3.0, 4, 0.5, 82), (3.5, 2, 0.3, 76)],
    ),
)

# ── UK Garage ────────────────────────────────────────────────────────
UK_GARAGE = GenreDNA(
    name="uk garage",
    bpm_default=132, bpm_range=(128, 136), groove_profile=GROOVE_TEMPLATES["ukg_shuffle"],

    kick_patterns=(
        [0.0, 2.5],                      # classic 2-step
        [0.0, 1.75, 2.5],                # busier 2-step
        [0.0, 0.75, 2.5, 3.25],          # skippy
    ),
    snare_patterns=(
        [1.0, 3.0],
        [1.0, 2.75, 3.0],               # ghost snare
    ),
    hat_patterns=(
        [i * 0.25 for i in range(16)],  # fast 16ths
    ),
    hat_style="16ths",

    bass_octave=2,
    bass_patterns=(
        # Syncopated staccato — stays on root and 5th
        [(0.0, 0, 0.3, 100), (1.75, 0, 0.25, 88),
         (2.5, 7, 0.3, 96)],
        # Bouncy offbeat
        [(0.0, 0, 0.3, 100), (0.75, 0, 0.2, 84),
         (2.0, 7, 0.25, 92), (3.25, 0, 0.2, 88)],
        # Skippy 2-step bass
        [(0.0, 0, 0.35, 100), (1.25, 5, 0.2, 84),
         (2.5, 0, 0.3, 96), (3.5, 7, 0.2, 88)],
    ),

    chord_octave=4, chord_style="stab",
    chord_rhythms=(
        [0.0, 1.5, 3.0],               # syncopated stabs
        [0.75, 1.5, 2.75, 3.5],        # offbeat stabs
    ),
    chord_duration=0.35,
    chord_extensions=(10, 14),           # 7ths and 9ths — jazzy

    lead_octave=4,
    lead_phrases=(
        # Soulful, stepwise
        [(0.0, 4, 0.5, 80), (0.75, 3, 0.4, 76), (1.5, 4, 0.6, 84),
         (2.5, 2, 0.5, 78), (3.25, 3, 0.4, 80)],
        # Call and response
        [(0.0, 0, 0.4, 82), (0.5, 2, 0.4, 78), (1.5, 4, 0.75, 84),
         (3.0, 3, 0.4, 80), (3.5, 2, 0.4, 76)],
        # Vocal-style
        [(0.0, 4, 0.6, 82), (1.0, 3, 0.5, 78),
         (2.0, 2, 0.4, 76), (2.5, 4, 0.6, 84), (3.5, 3, 0.35, 78)],
    ),
)

# ── Drum & Bass ──────────────────────────────────────────────────────
DNB = GenreDNA(
    name="drum n bass",
    bpm_default=174, bpm_range=(170, 180), groove_profile=GROOVE_TEMPLATES["dnb_tight"],

    kick_patterns=(
        [0.0, 2.5],                      # half-time feel
        [0.0, 1.75, 2.5],
    ),
    snare_patterns=(
        [1.0, 3.0],                      # amen-style backbeat
        [1.0, 2.75, 3.0, 3.5],          # with ghost notes
    ),
    hat_patterns=(
        [i * 0.25 for i in range(16)],  # fast 16ths (ride)
    ),
    hat_style="16ths",

    bass_octave=1,
    bass_patterns=(
        # Reese — sustained root
        [(0.0, 0, 1.8, 100), (2.0, 7, 1.8, 96)],
        # Rolling sub
        [(0.0, 0, 0.4, 100), (0.5, 0, 0.4, 90),
         (1.0, 7, 0.6, 96), (2.0, 0, 0.4, 100),
         (2.5, 5, 0.4, 88), (3.0, 0, 0.8, 96)],
        # Tearing bass
        [(0.0, 0, 0.3, 110), (0.25, 0, 0.2, 90),
         (0.75, 7, 0.3, 100), (1.5, 0, 0.3, 110),
         (2.0, 0, 0.8, 96), (3.0, 5, 0.4, 92), (3.5, 7, 0.4, 96)],
    ),

    chord_octave=4, chord_style="pad",
    chord_rhythms=(
        [0.0],                           # sustained pad
    ),
    chord_duration=3.75,
    chord_extensions=(10,),              # minor 7ths

    lead_octave=4,
    lead_phrases=(
        # Fast arp
        [(i * 0.25, (i * 2) % 7, 0.2, 86 + (i % 3) * 6) for i in range(16)],
        # Sparse melodic
        [(0.0, 4, 0.8, 84), (1.5, 3, 0.5, 78),
         (2.5, 4, 0.6, 86), (3.5, 6, 0.4, 80)],
    ),
)

# ── Jungle ───────────────────────────────────────────────────────────
JUNGLE = GenreDNA(
    name="jungle",
    bpm_default=168, bpm_range=(160, 175), groove_profile=GROOVE_TEMPLATES["dnb_tight"],

    kick_patterns=(
        [0.0, 2.5],
        [0.0, 1.5, 2.5, 3.5],           # busy breakbeat kick
    ),
    snare_patterns=(
        [1.0, 2.0, 3.0, 3.5],           # chopped break snare
        [0.5, 1.0, 2.5, 3.0, 3.25, 3.5],
    ),
    hat_patterns=(
        [i * 0.25 for i in range(16)],
    ),
    hat_style="16ths",

    bass_octave=1,
    bass_patterns=(
        [(0.0, 0, 1.5, 100), (2.0, 7, 1.5, 96)],
        [(0.0, 0, 0.8, 100), (1.0, 0, 0.4, 88),
         (2.0, 7, 0.8, 96), (3.0, 5, 0.4, 90)],
    ),

    chord_octave=4, chord_style="stab",
    chord_rhythms=([0.0, 2.0],),
    chord_duration=1.5,
    chord_extensions=(10,),

    lead_octave=4,
    lead_phrases=(
        [(0.0, 4, 0.6, 82), (1.0, 3, 0.4, 78), (2.0, 4, 0.5, 84),
         (3.0, 6, 0.4, 80)],
    ),
)

# ── Techno ───────────────────────────────────────────────────────────
TECHNO = GenreDNA(
    name="techno",
    bpm_default=132, bpm_range=(125, 140), groove_profile=GROOVE_TEMPLATES["straight"],

    kick_patterns=(
        [0.0, 1.0, 2.0, 3.0],
    ),
    snare_patterns=(
        [1.0, 3.0],
        [2.0],                           # sparse clap
    ),
    hat_patterns=(
        [i * 0.25 for i in range(16)],  # driving 16ths
        [0.5, 1.5, 2.5, 3.5],           # offbeat
    ),
    hat_style="16ths",

    bass_octave=1,
    bass_patterns=(
        # Driving 16th-note root
        [(i * 0.25, 0, 0.2, 96 if i % 4 == 0 else 78)
         for i in range(16)],
        # Acid-style root + octave
        [(0.0, 0, 0.2, 100), (0.25, 12, 0.15, 80),
         (0.5, 0, 0.2, 96), (0.75, 0, 0.2, 84),
         (1.0, 0, 0.2, 100), (1.25, 12, 0.15, 80),
         (1.5, 7, 0.2, 92), (1.75, 0, 0.2, 84),
         (2.0, 0, 0.2, 100), (2.25, 12, 0.15, 80),
         (2.5, 0, 0.2, 96), (2.75, 5, 0.2, 84),
         (3.0, 0, 0.2, 100), (3.25, 12, 0.15, 80),
         (3.5, 7, 0.2, 92), (3.75, 0, 0.15, 78)],
        # Minimal pulse
        [(0.0, 0, 0.5, 100), (1.0, 0, 0.5, 92),
         (2.0, 0, 0.5, 100), (3.0, 7, 0.5, 88)],
    ),

    chord_octave=4, chord_style="pad",
    chord_rhythms=([0.0],),
    chord_duration=3.5,
    chord_extensions=(),

    lead_octave=4,
    lead_phrases=(
        # Hypnotic repetition
        [(i * 0.5, 0 if i % 4 != 3 else 2, 0.2, 78 + (i % 4) * 6)
         for i in range(8)],
        # Minimal stab
        [(0.0, 4, 0.3, 80), (1.5, 4, 0.3, 76),
         (2.5, 3, 0.3, 80), (3.5, 4, 0.3, 76)],
    ),
)

# ── Trance ───────────────────────────────────────────────────────────
TRANCE = GenreDNA(
    name="trance",
    bpm_default=138, bpm_range=(136, 142), groove_profile=GROOVE_TEMPLATES["straight"],

    kick_patterns=([0.0, 1.0, 2.0, 3.0],),
    snare_patterns=([1.0, 3.0],),
    hat_patterns=([0.5, 1.5, 2.5, 3.5],),
    hat_style="8ths",

    bass_octave=1,
    bass_patterns=(
        [(0.0, 0, 0.4, 100), (0.5, 0, 0.35, 88),
         (1.0, 0, 0.4, 100), (1.5, 0, 0.35, 88),
         (2.0, 0, 0.4, 100), (2.5, 7, 0.35, 88),
         (3.0, 0, 0.4, 100), (3.5, 0, 0.35, 88)],
    ),

    chord_octave=4, chord_style="pad",
    chord_rhythms=([0.0],),
    chord_duration=3.75,
    chord_extensions=(10,),

    lead_octave=4,
    lead_phrases=(
        # Uplifting arp
        [(0.0, 0, 0.2, 80), (0.25, 2, 0.2, 76), (0.5, 4, 0.2, 82),
         (0.75, 7, 0.2, 78), (1.0, 4, 0.2, 82), (1.25, 2, 0.2, 76),
         (1.5, 0, 0.2, 80), (1.75, 2, 0.2, 76),
         (2.0, 4, 0.2, 82), (2.25, 7, 0.2, 78),
         (2.5, 9, 0.2, 86), (2.75, 7, 0.2, 78),
         (3.0, 4, 0.2, 82), (3.25, 2, 0.2, 76),
         (3.5, 0, 0.4, 84)],
    ),
)

# ── Trap ─────────────────────────────────────────────────────────────
TRAP = GenreDNA(
    name="trap",
    bpm_default=140, bpm_range=(130, 150), groove_profile=GROOVE_TEMPLATES["trap_triplet"],

    kick_patterns=(
        [0.0, 0.75, 2.5],               # sparse bounce
        [0.0, 2.0],                      # minimal
        [0.0, 0.5, 2.5, 3.0],           # busier
    ),
    snare_patterns=(
        [2.0],                           # half-time on beat 3
        [2.0, 3.75],                     # with pickup
    ),
    hat_patterns=(
        # Triplet rolls
        [i * (1/3) for i in range(12)],
        # Mixed 16ths with rolls
        [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75,
         2.0, 2.17, 2.33, 2.5, 2.67, 2.83,  # triplet roll
         3.0, 3.25, 3.5, 3.75],
    ),
    hat_style="triplets",

    bass_octave=1,
    bass_patterns=(
        # 808 long sustain
        [(0.0, 0, 3.5, 110)],
        # 808 with movement
        [(0.0, 0, 1.75, 110), (2.0, 7, 1.75, 100)],
        # Sliding 808
        [(0.0, 0, 1.0, 110), (1.0, 5, 0.8, 96),
         (2.0, 0, 1.5, 110)],
    ),

    chord_octave=4, chord_style="pad",
    chord_rhythms=([0.0],),
    chord_duration=3.5,
    chord_extensions=(10,),

    lead_octave=4,
    lead_phrases=(
        # Dark, spacious
        [(0.0, 4, 0.8, 78), (1.5, 3, 0.5, 72), (3.0, 0, 0.8, 82)],
        # Pentatonic
        [(0.0, 0, 0.5, 80), (1.0, 2, 0.4, 76),
         (2.0, 4, 0.6, 82), (3.5, 2, 0.4, 76)],
    ),
)

# ── Hip Hop ──────────────────────────────────────────────────────────
HIP_HOP = GenreDNA(
    name="hip hop",
    bpm_default=90, bpm_range=(80, 100), groove_profile=GROOVE_TEMPLATES["mpc_58"],

    kick_patterns=(
        [0.0, 2.5],                      # boom bap
        [0.0, 0.75, 2.5, 3.25],
    ),
    snare_patterns=(
        [1.0, 3.0],                      # classic backbeat
    ),
    hat_patterns=(
        [i * 0.5 for i in range(8)],    # 8th notes
    ),
    hat_style="8ths",

    bass_octave=1,
    bass_patterns=(
        [(0.0, 0, 0.8, 100), (1.0, 0, 0.4, 88),
         (2.0, 7, 0.8, 96), (3.0, 5, 0.4, 88)],
        [(0.0, 0, 1.5, 100), (2.0, 0, 1.5, 96)],
    ),

    chord_octave=4, chord_style="pad",
    chord_rhythms=([0.0],),
    chord_duration=3.5,
    chord_extensions=(10, 14),

    lead_octave=4,
    lead_phrases=(
        [(0.0, 4, 0.6, 78), (1.5, 3, 0.5, 74),
         (2.5, 2, 0.5, 76), (3.5, 0, 0.5, 80)],
    ),
)

# ── Reggaeton ────────────────────────────────────────────────────────
REGGAETON = GenreDNA(
    name="reggaeton",
    bpm_default=96, bpm_range=(88, 100), groove_profile=GROOVE_TEMPLATES["dembow"],

    kick_patterns=(
        [0.0, 1.5, 2.5],                # dembow
        [0.0, 0.75, 1.5, 2.0, 2.75, 3.5], # 3-3-2 linear clave
    ),
    snare_patterns=(
        [0.75, 1.75, 2.75, 3.75],       # dembow snare
    ),
    hat_patterns=(
        [i * 0.25 for i in range(16)],
    ),
    hat_style="16ths",

    bass_octave=1,
    bass_patterns=(
        [(0.0, 0, 0.6, 100), (1.5, 7, 0.4, 92),
         (2.5, 0, 0.6, 100)],
    ),

    chord_octave=4, chord_style="stab",
    chord_rhythms=([0.0, 1.5, 2.5],),
    chord_duration=0.4,
    chord_extensions=(),

    lead_octave=4,
    lead_phrases=(
        [(0.0, 4, 0.4, 80), (0.75, 3, 0.3, 76),
         (1.5, 4, 0.5, 82), (2.5, 2, 0.4, 78), (3.25, 4, 0.4, 80)],
    ),
)

# ── Downtempo ────────────────────────────────────────────────────────
DOWNTEMPO = GenreDNA(
    name="downtempo",
    bpm_default=92, bpm_range=(80, 100), groove_profile=GROOVE_TEMPLATES["mpc_58"],

    kick_patterns=([0.0, 2.0],),
    snare_patterns=([1.0, 3.0],),
    hat_patterns=([i * 0.5 for i in range(8)],),
    hat_style="8ths",

    bass_octave=2,
    bass_patterns=(
        [(0.0, 0, 1.0, 90), (2.0, 7, 1.0, 86)],
    ),

    chord_octave=4, chord_style="pad",
    chord_rhythms=([0.0],),
    chord_duration=3.75,
    chord_extensions=(10, 14),

    lead_octave=4,
    lead_phrases=(
        [(0.0, 4, 0.8, 72), (2.0, 3, 0.6, 68), (3.0, 2, 0.8, 70)],
    ),
)

# ── Ambient ──────────────────────────────────────────────────────────
AMBIENT = GenreDNA(
    name="ambient",
    bpm_default=78, bpm_range=(60, 90), groove_profile=GROOVE_TEMPLATES["straight"],

    kick_patterns=([],),                 # no kick
    snare_patterns=([],),                # no snare
    hat_patterns=([],),
    hat_style="8ths",

    bass_octave=2,
    bass_patterns=(
        [(0.0, 0, 3.5, 70)],            # one long drone note
    ),

    chord_octave=4, chord_style="pad",
    chord_rhythms=([0.0],),
    chord_duration=3.75,
    chord_extensions=(10, 14),

    lead_octave=4,
    lead_phrases=(
        [(0.0, 4, 1.5, 60), (2.0, 7, 1.5, 56)],
    ),
)

# ── Pop ──────────────────────────────────────────────────────────────
POP = GenreDNA(
    name="pop",
    bpm_default=104, bpm_range=(96, 120), groove_profile=GROOVE_TEMPLATES["straight"],

    kick_patterns=([0.0, 1.0, 2.0, 3.0],),
    snare_patterns=([1.0, 3.0],),
    hat_patterns=([i * 0.5 for i in range(8)],),
    hat_style="8ths",

    bass_octave=2,
    bass_patterns=(
        [(0.0, 0, 0.7, 96), (1.0, 0, 0.7, 90),
         (2.0, 7, 0.7, 96), (3.0, 0, 0.7, 90)],
    ),

    chord_octave=3, chord_style="stab",
    chord_rhythms=([0.0, 1.0, 2.0, 3.0],),
    chord_duration=0.8,
    chord_extensions=(),

    lead_octave=4,
    lead_phrases=(
        [(0.0, 0, 0.5, 82), (0.5, 2, 0.4, 78), (1.0, 4, 0.5, 84),
         (2.0, 3, 0.4, 80), (2.5, 2, 0.4, 78), (3.0, 0, 0.6, 82)],
    ),
)

# ── Afrobeats ────────────────────────────────────────────────────────
AFROBEATS = GenreDNA(
    name="afrobeats",
    bpm_default=108, bpm_range=(100, 115), groove_profile=GROOVE_TEMPLATES["dembow"],

    kick_patterns=(
        [0.0, 0.75, 2.0, 2.75],         # syncopated "clave" feel
        [0.0, 1.0, 2.0, 3.0],           # four-on-the-floor
        [0.0, 0.75, 1.5, 2.0, 2.75, 3.5], # 3-3-2 linear clave
    ),
    snare_patterns=(
        [0.75, 1.75, 2.75, 3.75],       # dembow-adjacent rim stabs
        [1.0, 3.0],                      # standard backbeat
    ),
    hat_patterns=(
        [i * 0.25 for i in range(16)],  # 16ths
        [0.25, 0.5, 1.25, 1.5, 2.25, 2.5, 3.25, 3.5], # syncopated
    ),
    hat_style="16ths",

    bass_octave=1,
    bass_patterns=(
        # Melodic, following kick
        [(0.0, 0, 0.4, 100), (0.75, 0, 0.3, 90),
         (2.0, 5, 0.4, 96), (2.75, 0, 0.3, 88)],
        # Bouncy groove
        [(0.0, 0, 0.5, 100), (1.5, 7, 0.4, 92),
         (2.5, 0, 0.5, 96), (3.5, 5, 0.3, 88)],
    ),

    chord_octave=4, chord_style="stab",
    chord_rhythms=([0.0, 0.75, 1.5, 2.25, 3.0],),
    chord_duration=0.3,
    chord_extensions=(10, 14),

    lead_octave=4,
    lead_phrases=(
        # Pentatonic, repeating
        [(0.0, 4, 0.4, 80), (0.5, 2, 0.3, 76), (1.0, 0, 0.5, 84),
         (1.5, 2, 0.3, 78), (2.0, 4, 0.5, 80)],
    ),
)

# ── Amapiano ─────────────────────────────────────────────────────────
AMAPIANO = GenreDNA(
    name="amapiano",
    bpm_default=113, bpm_range=(110, 115), groove_profile=GROOVE_TEMPLATES["ukg_shuffle"],

    kick_patterns=(
        [0.0, 1.0, 2.0, 3.0],
    ),
    snare_patterns=(
        [1.5, 3.5],                     # late snare
        [1.0, 1.5, 3.0, 3.5],           # shaker-heavy feel
    ),
    hat_patterns=(
        [i * 0.25 for i in range(16)],  # constant 16th shakers
    ),
    hat_style="16ths",

    bass_octave=1,
    bass_patterns=(
        # "Log Drum" roll
        [(0.0, 0, 0.2, 110), (0.125, 0, 0.15, 96), (0.25, 0, 0.2, 100),
         (1.5, 7, 0.3, 110), (2.5, 0, 0.4, 100), (3.75, 0, 0.15, 88)],
        # Deep house bounce
        [(0.0, 0, 0.6, 100), (1.5, 0, 0.4, 92),
         (2.75, 5, 0.3, 96), (3.5, 0, 0.4, 88)],
    ),

    chord_octave=3, chord_style="pad",
    chord_rhythms=([0.0],),
    chord_duration=3.75,
    chord_extensions=(10, 14),

    lead_octave=4,
    lead_phrases=(
        # Percussive synth hook
        [(0.0, 0, 0.2, 84), (0.5, 0, 0.2, 78), (1.0, 4, 0.3, 86),
         (1.5, 0, 0.2, 80), (2.5, 2, 0.2, 82), (3.0, 0, 0.3, 76)],
    ),
)


# ── Lookup ───────────────────────────────────────────────────────────

GENRE_REGISTRY: dict[str, GenreDNA] = {
    "house": HOUSE,
    "uk garage": UK_GARAGE,
    "drum n bass": DNB,
    "dnb": DNB,
    "jungle": JUNGLE,
    "techno": TECHNO,
    "trance": TRANCE,
    "trap": TRAP,
    "grime": TRAP,
    "dubstep": TRAP,
    "hip hop": HIP_HOP,
    "hip-hop": HIP_HOP,
    "reggaeton": REGGAETON,
    "downtempo": DOWNTEMPO,
    "ambient": AMBIENT,
    "pop": POP,
    "hyperpop": TRAP,   # similar rhythm profile
    "dance and mainstage": HOUSE,
    "reggae": REGGAETON,  # dembow-adjacent
    "dancehall": REGGAETON,
    "modern pop": POP,
    "rock and country": POP,
    "afrobeats": AFROBEATS,
    "amapiano": AMAPIANO,
}

DEFAULT_DNA = HOUSE


CURATED_GENRES: dict[str, CuratedGenreDNA] = {
    "uk garage": CuratedGenreDNA(
        name="UK Garage",
        bpm_range=(130, 136),
        swing_percent=(58, 65),
        bar_grid="4/4 8-bar phrases",
        structure=("intro 8", "build 16", "drop 16", "break 8", "drop 2 16", "outro 8"),
        kick_pattern="Skippy two-step kick: starts on beat 1, then jumps to the late offbeat before beat 4.",
        bass_pattern="Sub bass ducks around the kick with syncopated offbeat stabs and short melodic slides.",
        hi_hat_pattern="Swung 16th-note hats with soft ghost hits and a clear bounce.",
        energy_arc="tension-release",
        rules=(
            "Kick avoids a straight four-on-the-floor pulse.",
            "Snare or clap lands on 2 and 4.",
            "Pitched-up soulful vocal chops are a signature sound.",
            "Sub bass breathes around the kick instead of sitting underneath every beat.",
            "Filtered Rhodes, organ, or pluck stabs work well on offbeats.",
        ),
        rule_breakers=(
            "Drop the kick for 4 bars and let bass plus snare carry the groove.",
            "Triple-time the hi-hat for a bar before the drop.",
            "Use a half-time snare in the break for breathing room.",
        ),
        blends_with=("afrobeats", "amapiano", "house", "grime", "drum n bass"),
        vibe_words=("skippy", "bouncy", "swung", "soulful", "london", "2-step", "vocal chop", "sunday club"),
    ),
    "house": CuratedGenreDNA(
        name="House",
        bpm_range=(120, 128),
        swing_percent=(50, 55),
        bar_grid="4/4 16-bar phrases",
        structure=("intro 16", "build A 16", "drop 32", "breakdown 16", "drop 2 32", "outro 16"),
        kick_pattern="Four-on-the-floor kick on every beat.",
        bass_pattern="Rolling bass locks tightly with the kick, often repeating one or two notes.",
        hi_hat_pattern="Open hat on the offbeat between every kick.",
        energy_arc="sustained",
        rules=(
            "Kick stays on every beat.",
            "Clap or snare lands on 2 and 4.",
            "Open hats create the lift between kicks.",
            "Bass and kick should feel glued together.",
            "Long intros and outros keep it DJ-friendly.",
        ),
        rule_breakers=(
            "Drop the kick for 4 bars while bass and clap continue.",
            "Pitch-bend a vocal sample before the drop.",
            "Use a 3-bar phrase in the breakdown before snapping back to 4.",
        ),
        blends_with=("uk garage", "techno", "afrobeats", "amapiano"),
        vibe_words=("four on the floor", "pumping", "club", "classic", "driving", "groove", "disco"),
    ),
    "techno": CuratedGenreDNA(
        name="Techno",
        bpm_range=(125, 135),
        swing_percent=(50, 52),
        bar_grid="4/4 16-bar phrases",
        structure=("intro 16", "build 32", "peak 32", "reduction 16", "peak 2 32", "outro 16"),
        kick_pattern="Relentless four-on-the-floor kick with minimal variation.",
        bass_pattern="Repetitive single-note bass with movement from filter and tone changes, not many notes.",
        hi_hat_pattern="Straight offbeat hats with small texture changes over time.",
        energy_arc="meditative",
        rules=(
            "Repeat patterns for long stretches.",
            "Use texture and filter movement instead of obvious melody.",
            "Keep the pulse steady and machine-like.",
            "Let small changes carry the arrangement.",
            "Use empty space as part of the groove.",
        ),
        rule_breakers=(
            "Introduce one vocal or melodic phrase only once in the whole track.",
            "Layer a percussion rhythm that cycles against the main groove.",
            "Drop everything for 8 bars and return without warning.",
        ),
        blends_with=("house", "drum n bass", "dubstep"),
        vibe_words=("driving", "hypnotic", "minimal", "industrial", "dark", "berlin", "pulse", "machine"),
    ),
    "drum n bass": CuratedGenreDNA(
        name="Drum & Bass",
        bpm_range=(165, 180),
        swing_percent=(50, 55),
        bar_grid="4/4 16-bar phrases",
        structure=("intro 16", "build 16", "drop 32", "break 16", "drop 2 32", "outro 16"),
        kick_pattern="Fast broken kick pattern with the main hit on beat 1 and another strong hit around beat 3.",
        bass_pattern="Rolling sub or Reese bass acts as the lead instrument with tone movement carrying the energy.",
        hi_hat_pattern="Busy 8th or 16th-note hats that keep the track racing forward.",
        energy_arc="tension-release",
        rules=(
            "Fast breakbeat rhythm is central.",
            "Sub bass below the obvious low end needs real weight.",
            "Drops are usually large 32-bar sections.",
            "Breaks create contrast before the next impact.",
            "Bass design matters more than note count.",
        ),
        rule_breakers=(
            "Half-time the snare for a bar before the drop.",
            "Use a detuned vocal as the lead instead of a synth.",
            "Use triplet hats for 2 bars in a build.",
        ),
        blends_with=("jungle", "uk garage", "techno"),
        vibe_words=("fast", "rolling", "sub bass", "liquid", "neurofunk", "breakbeat", "jungle"),
    ),
    "jungle": CuratedGenreDNA(
        name="Jungle",
        bpm_range=(160, 180),
        swing_percent=(50, 55),
        bar_grid="4/4 8-bar phrases",
        structure=("intro 8", "build 16", "drop 32", "break 16", "drop 2 32", "outro 8"),
        kick_pattern="Chopped breakbeat kicks with ghost hits and edits that keep surprising the ear.",
        bass_pattern="Dub-influenced sub bass plays riffs and melodies rather than only long single notes.",
        hi_hat_pattern="Fast breakbeat hats with edits, shuffle, and crunchy sample movement.",
        energy_arc="wave",
        rules=(
            "Chopped breakbeats define the movement.",
            "Ragga or reggae vocal samples fit naturally.",
            "Bass can carry melody.",
            "Dub delay and reverb work well on vocal stabs.",
            "Energy comes from drum edits as much as tempo.",
        ),
        rule_breakers=(
            "Drop the entire mix for half a bar of vocal.",
            "Reverse the break for 2 bars in the build.",
            "Pitch the whole track down slightly for the last 8 bars.",
        ),
        blends_with=("drum n bass", "dubstep", "grime"),
        vibe_words=("chopped", "ragga", "amen break", "dub", "rough", "sub", "90s", "breakneck"),
    ),
    "grime": CuratedGenreDNA(
        name="Grime",
        bpm_range=(138, 142),
        swing_percent=(50, 55),
        bar_grid="4/4 8-bar phrases",
        structure=("intro 8", "verse 1 16", "bridge 8", "verse 2 16", "drop switch 16", "outro 8"),
        kick_pattern="Sparse 140 BPM kick pattern with lots of room for the MC.",
        bass_pattern="Square, sine, or 808-style bass plays short raw riffs and sharp stabs.",
        hi_hat_pattern="Simple hats, often steady, leaving the main space open for vocal rhythm.",
        energy_arc="tension-release",
        rules=(
            "Sparse percussion is part of the identity.",
            "Snare usually lands on beat 3 for a half-time feel.",
            "Square-wave and sine bass tones should feel direct and raw.",
            "Short icy melodic stabs are useful.",
            "Leave room for an MC at the front.",
        ),
        rule_breakers=(
            "Drop into double-time for 4 bars, then return to half-time.",
            "Use a violin or string sample as the lead.",
            "Add a full bar of silence in the middle of a verse.",
        ),
        blends_with=("uk garage", "dubstep", "drum n bass", "trap"),
        vibe_words=("square wave", "eski", "mc", "140", "east london", "sparse", "riddim", "dark"),
    ),
    "dubstep": CuratedGenreDNA(
        name="Dubstep",
        bpm_range=(138, 142),
        swing_percent=(50, 55),
        bar_grid="4/4 16-bar phrases",
        structure=("intro 16", "build 16", "drop 16", "break 16", "drop 2 16", "outro 16"),
        kick_pattern="Half-time boom-clap pattern with kick on beat 1 and snare on beat 3.",
        bass_pattern="Wobble or growl bass plays phrases and fills the midrange, with sub underneath.",
        hi_hat_pattern="Sparse offbeat hats that leave room for bass movement.",
        energy_arc="tension-release",
        rules=(
            "Half-time feel at around 140 BPM is central.",
            "Bass design carries the song.",
            "Leave big spaces between drum hits.",
            "Sub bass supports the wobble or growl.",
            "Build tension before the drop with restraint.",
        ),
        rule_breakers=(
            "Use 2 silent bars before the drop.",
            "Switch to triplet bass for one bar.",
            "Drop with no kick on beat 1, only bass and snare.",
        ),
        blends_with=("grime", "drum n bass", "trap"),
        vibe_words=("wobble", "half-time", "drop", "sub", "growl", "bass music", "riddim"),
    ),
    "afrobeats": CuratedGenreDNA(
        name="Afrobeats",
        bpm_range=(96, 115),
        swing_percent=(52, 58),
        bar_grid="4/4 8-bar phrases",
        structure=("intro 8", "verse 1 16", "pre-chorus 4", "chorus 8", "verse 2 16", "bridge 8", "final chorus 16", "outro 8"),
        kick_pattern="Syncopated kick pattern that dances around the vocal instead of pounding every beat.",
        bass_pattern="Melodic bass often anticipates the next bar and leaves gaps on the obvious downbeats.",
        hi_hat_pattern="Shaker-led 16th-note motion with a shuffled, human feel.",
        energy_arc="sustained",
        rules=(
            "Layer percussion parts with different rhythms.",
            "Shaker motion carries the groove.",
            "Bass often lands before beat 1.",
            "Talking drum or log drum gives the track identity.",
            "Keep the vocal melody clear.",
        ),
        rule_breakers=(
            "Drop everything except the shaker for 4 bars.",
            "Use a 3-bar phrase in the bridge.",
            "Pitch the talking drum melodically and make it the lead.",
        ),
        blends_with=("amapiano", "uk garage", "house", "trap"),
        vibe_words=("groove", "percussion", "shaker", "talking drum", "polyrhythm", "naija", "lagos", "feel-good"),
    ),
    "amapiano": CuratedGenreDNA(
        name="Amapiano",
        bpm_range=(110, 115),
        swing_percent=(55, 62),
        bar_grid="4/4 16-bar phrases",
        structure=("intro 16", "build 16", "groove A 32", "break 16", "groove B 32", "outro 16"),
        kick_pattern="Slow swung four-on-the-floor kick with a relaxed, patient feel.",
        bass_pattern="Log drum acts as the bass, playing deep wooden melodic riffs with pitch slides.",
        hi_hat_pattern="Layered shakers and soft hats create a busy but low-pressure top end.",
        energy_arc="meditative",
        rules=(
            "Log drum bass is the core sound.",
            "Jazzy piano or Rhodes chords fit the feel.",
            "The groove should feel slow and swung.",
            "Percussion can be busy, but not harsh.",
            "Long sections let the track hypnotize.",
        ),
        rule_breakers=(
            "Use a 3-over-4 percussion rhythm against the main groove.",
            "Drop the piano for an entire section.",
            "Pitch-shift the log drum down an octave for the final section.",
        ),
        blends_with=("afrobeats", "house", "uk garage"),
        vibe_words=("log drum", "jazzy", "south africa", "rhodes", "lazy", "soulful", "piano", "shaker"),
    ),
    "trap": CuratedGenreDNA(
        name="Trap",
        bpm_range=(130, 150),
        swing_percent=(50, 55),
        bar_grid="4/4 8-bar phrases",
        structure=("intro 8", "verse 1 16", "chorus hook 8", "verse 2 16", "bridge 8", "final hook 16", "outro 8"),
        kick_pattern="Half-time kick pattern with sparse hits that leave room for the 808.",
        bass_pattern="808 bass is long, tuned, sliding, and usually acts as both bass and weight.",
        hi_hat_pattern="Fast hats with 16th, 32nd, and triplet rolls.",
        energy_arc="wave",
        rules=(
            "Snare usually lands on beat 3 for a half-time feel.",
            "808 is the only bass voice.",
            "Hi-hat rolls create most of the motion.",
            "Keep the middle of the mix open.",
            "Use a simple atmospheric melody loop.",
        ),
        rule_breakers=(
            "Switch triplet hats back to straight 16ths mid-bar.",
            "Pitch-bend the 808 down at the end of a phrase.",
            "Drop everything but the 808 for half a bar before the hook.",
        ),
        blends_with=("grime", "dubstep", "afrobeats"),
        vibe_words=("808", "hi-hat roll", "half-time", "atlanta", "drill", "spacey", "melodic", "dark"),
    ),
}

CURATED_ALIASES: dict[str, str] = {
    "ukg": "uk garage",
    "garage": "uk garage",
    "2-step": "uk garage",
    "2step": "uk garage",
    "dnb": "drum n bass",
    "drum and bass": "drum n bass",
    "drum & bass": "drum n bass",
    "afrobeat": "afrobeats",
}


def lookup_genre(name: str) -> GenreDNA:
    """Return the GenreDNA for a genre name, falling back to House."""
    return GENRE_REGISTRY.get(name.lower().strip(), DEFAULT_DNA)


def normalize_curated_genre_id(name: str) -> str:
    key = name.lower().strip()
    return CURATED_ALIASES.get(key, key)


def lookup_curated_genre(name: str) -> CuratedGenreDNA | None:
    """Return the curated prompt grammar for a genre name, if one exists."""
    return CURATED_GENRES.get(normalize_curated_genre_id(name))


def find_curated_genres_by_vibe(words: list[str]) -> list[CuratedGenreDNA]:
    """Rank curated genres by natural-language vibe words."""
    lowered = [word.lower() for word in words]
    ranked: list[tuple[int, CuratedGenreDNA]] = []
    for genre in CURATED_GENRES.values():
        score = sum(
            1
            for vibe_word in genre.vibe_words
            if any(_vibe_word_matches(word, vibe_word) for word in lowered)
        )
        if score:
            ranked.append((score, genre))
    return [genre for _score, genre in sorted(ranked, key=lambda item: item[0], reverse=True)]


def _vibe_word_matches(word: str, vibe_word: str) -> bool:
    if not word or not vibe_word:
        return False
    if " " in vibe_word:
        return word == vibe_word
    return word == vibe_word or word.rstrip("s") == vibe_word.rstrip("s")


def build_curated_prompt_context(genre_name: str) -> str:
    """Build prompt context from the curated genre grammar."""
    genre = lookup_curated_genre(genre_name)
    if not genre:
        return ""
    return f"""
GENRE: {genre.name}
TEMPO: {genre.bpm_range[0]}-{genre.bpm_range[1]} BPM
SWING: {genre.swing_percent[0]}-{genre.swing_percent[1]}% (50 = straight, 75 = heavy swing)
BAR GRID: {genre.bar_grid}
ENERGY ARC: {genre.energy_arc}

STRUCTURE:
{chr(10).join(f"  - {section}" for section in genre.structure)}

KICK: {genre.kick_pattern}
BASS: {genre.bass_pattern}
HI-HAT: {genre.hi_hat_pattern}

RULES:
{chr(10).join(f"  - {rule}" for rule in genre.rules)}

CREATIVE RULE-BREAKERS:
{chr(10).join(f"  - {rule}" for rule in genre.rule_breakers)}
""".strip()


def build_curated_blend_prompt_context(genre_a_name: str, genre_b_name: str, bias: float = 0.5) -> str:
    genre_a = lookup_curated_genre(genre_a_name)
    genre_b = lookup_curated_genre(genre_b_name)
    if not genre_a or not genre_b:
        return ""
    clamped_bias = max(0.0, min(1.0, bias))
    bpm_a = sum(genre_a.bpm_range) / 2
    bpm_b = sum(genre_b.bpm_range) / 2
    swing_a = sum(genre_a.swing_percent) / 2
    swing_b = sum(genre_b.swing_percent) / 2
    bpm = round(bpm_a * (1 - clamped_bias) + bpm_b * clamped_bias)
    swing = round(swing_a * (1 - clamped_bias) + swing_b * clamped_bias)
    dominant = genre_a if clamped_bias < 0.5 else genre_b
    flavour = genre_b if clamped_bias < 0.5 else genre_a
    return f"""
BLEND: {genre_a.name} x {genre_b.name}
BIAS: {round((1 - clamped_bias) * 100)}% {genre_a.name} / {round(clamped_bias * 100)}% {genre_b.name}
TARGET TEMPO: {bpm} BPM
TARGET SWING: {swing}%

STRUCTURE:
Use {dominant.name}'s arrangement:
{chr(10).join(f"  - {section}" for section in dominant.structure)}

RHYTHMIC FLAVOUR:
Borrow from {flavour.name}:
  - KICK: {flavour.kick_pattern}
  - BASS: {flavour.bass_pattern}
  - HI-HAT: {flavour.hi_hat_pattern}

COMBINED RULES:
{chr(10).join(f"  - [{dominant.name}] {rule}" for rule in dominant.rules[:3])}
{chr(10).join(f"  - [{flavour.name}] {rule}" for rule in flavour.rules[:2])}
""".strip()


def find_curated_genres_by_tempo(bpm: int, tolerance: int = 5) -> list[CuratedGenreDNA]:
    return [
        genre
        for genre in CURATED_GENRES.values()
        if genre.bpm_range[0] - tolerance <= bpm <= genre.bpm_range[1] + tolerance
    ]


def get_curated_blend_suggestions(genre_name: str) -> list[CuratedGenreDNA]:
    genre = lookup_curated_genre(genre_name)
    if not genre:
        return []
    return [
        partner
        for partner_id in genre.blends_with[:3]
        if (partner := lookup_curated_genre(partner_id)) is not None
    ]


def curated_sections_for_genre(genre_name: str) -> list[tuple[str, int, str]]:
    genre = lookup_curated_genre(genre_name)
    if not genre:
        return []
    sections: list[tuple[str, int, str]] = []
    for section in genre.structure:
        name, bars_text = section.rsplit(" ", 1)
        try:
            bars = int(bars_text)
        except ValueError:
            continue
        lowered_name = name.lower()
        if any(word in lowered_name for word in ["intro", "outro", "texture"]):
            energy = "intro"
        elif any(word in lowered_name for word in ["build", "verse", "pre", "bridge", "groove"]):
            energy = "build"
        elif any(word in lowered_name for word in ["break", "reduction", "drift"]):
            energy = "break"
        else:
            energy = "main"
        sections.append((name.title(), bars, energy))
    return sections


def curated_default_bpm(genre_name: str) -> int | None:
    genre = lookup_curated_genre(genre_name)
    if not genre:
        return None
    return round(sum(genre.bpm_range) / 2)


def detect_style_from_text(text: str) -> str:
    """Identify the genre from a string (prompt or path)."""
    lowered = text.lower()
    
    # Priority matches
    if any(word in lowered for word in ["drum n bass", "dnb"]):
        return "drum n bass"
    if any(word in lowered for word in ["90s jungle", "jungle"]):
        return "jungle"
    if any(word in lowered for word in ["uk garage", "ukg", "2-step", "2step", "garage"]):
        return "uk garage"
    if "grime" in lowered:
        return "grime"
    if "dubstep" in lowered:
        return "dubstep"
    if any(word in lowered for word in ["reggae", "dance hall", "dancehall"]):
        return "reggaeton"
    if "ambient" in lowered or "cinematic" in lowered:
        return "ambient"
    if "trance" in lowered:
        return "trance"
    if "techno" in lowered:
        return "techno"
    if "trap" in lowered:
        return "trap"
    if "hip hop" in lowered or "hip-hop" in lowered or "rap" in lowered:
        return "hip hop"
    if "pop" in lowered:
        return "pop"
    if "afrobeats" in lowered or "afrobeat" in lowered:
        return "afrobeats"
    if "amapiano" in lowered:
        return "amapiano"
    vibe_matches = find_curated_genres_by_vibe(lowered.replace("/", " ").replace("-", " ").split())
    if vibe_matches:
        for genre_id, genre in CURATED_GENRES.items():
            if genre is vibe_matches[0]:
                return genre_id
    
    # Check registry aliases
    for style_name in GENRE_REGISTRY:
        if style_name in lowered:
            return style_name
            
    # Default fallback
    if "edm" in lowered or "electronic" in lowered:
        return "house"
        
    return "house"  # Universal fallback


def pick_pattern(patterns: tuple | list, seed: int) -> list:
    """Deterministically pick a pattern variant from a list using a seed."""
    if not patterns:
        return []
    return patterns[seed % len(patterns)]
