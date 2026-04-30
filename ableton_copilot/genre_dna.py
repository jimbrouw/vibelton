"""Genre DNA profiles for the Vibelton music brain.

Each genre defines distinct rhythm patterns, pitch ranges, and articulation
so that House, UK Garage, DnB etc. sound genuinely different.

Bass pattern entry: (beat_pos, semitone_interval, duration, velocity)
Lead phrase entry:  (beat_pos, scale_degree_idx, duration, velocity)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# Type aliases for readability
BassPattern = list[tuple[float, int, float, int]]
LeadPhrase = list[tuple[float, int, float, int]]


@dataclass(frozen=True)
class GenreDNA:
    name: str
    bpm_default: int
    bpm_range: tuple[int, int]
    swing: float  # 0.0 = straight, 0.5 = full shuffle

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
    bpm_default=124, bpm_range=(120, 128), swing=0.0,

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
    bpm_default=132, bpm_range=(128, 136), swing=0.12,

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
    bpm_default=174, bpm_range=(170, 180), swing=0.0,

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
    bpm_default=168, bpm_range=(160, 175), swing=0.05,

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
    bpm_default=132, bpm_range=(125, 140), swing=0.0,

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
    bpm_default=138, bpm_range=(136, 142), swing=0.0,

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
    bpm_default=140, bpm_range=(130, 150), swing=0.0,

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
    bpm_default=90, bpm_range=(80, 100), swing=0.08,

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
    bpm_default=96, bpm_range=(88, 100), swing=0.0,

    kick_patterns=(
        [0.0, 1.5, 2.5],                # dembow
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
    bpm_default=92, bpm_range=(80, 100), swing=0.06,

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
    bpm_default=78, bpm_range=(60, 90), swing=0.0,

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
    bpm_default=104, bpm_range=(96, 120), swing=0.0,

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
    bpm_default=108, bpm_range=(100, 115), swing=0.0,

    kick_patterns=(
        [0.0, 0.75, 2.0, 2.75],         # syncopated "clave" feel
        [0.0, 1.0, 2.0, 3.0],           # four-on-the-floor
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
    bpm_default=113, bpm_range=(110, 115), swing=0.05,

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


def lookup_genre(name: str) -> GenreDNA:
    """Return the GenreDNA for a genre name, falling back to House."""
    return GENRE_REGISTRY.get(name.lower().strip(), DEFAULT_DNA)


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
