# Phase 1: House Sub-Genre Expansion - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `vibelton/genre_dna.py` | model | transform | `vibelton/genre_dna.py` (existing `HOUSE`, `TECHNO` constants) | exact — same file, same data-entry pattern |
| `vibelton/harmony.py` | service | transform | `vibelton/harmony.py` (existing `_EDM_STYLES` set) | exact — one-line set extension |
| `vibelton/planner.py` | service | event-driven | `vibelton/planner.py` (existing `expanded_song_sketch_plan`, `genre_words`, `STYLE_PALETTES`) | exact — same file, same branching pattern |
| `lib/genreDNA.ts` | model | transform | `lib/genreDNA.ts` (existing `house`, `techno` entries in `GENRES`) | exact — same file, same object literal pattern |
| `app/page.tsx` | component | request-response | `lib/genreDNA.ts` + `web/styles.css` `.prompt-button` / `.vst-settings details` | role-match — first real component in app/ |
| `app/layout.tsx` | config | request-response | `app/layout.tsx` (existing bare layout) | exact — one-line import addition |
| `tests/test_genre_dna.py` | test | batch | `tests/test_genre_dna.py` (existing test class) | exact — same file, same `unittest.TestCase` pattern |
| `LISTENING_NOTES.md` | config | — | none | no analog — new template document |

---

## Pattern Assignments

### `vibelton/genre_dna.py` — 5 sub-tasks (model, transform)

**Analog:** `vibelton/genre_dna.py` — existing `HOUSE`, `TECHNO`, `CURATED_GENRES`, `GROOVE_TEMPLATES`, `detect_style_from_text`

---

#### Sub-task A: Add `parent` field to `GenreDNA`

**Core pattern** (lines 111–138 — existing `GenreDNA` dataclass):
```python
@dataclass(frozen=True)
class GenreDNA:
    name: str
    bpm_default: int
    bpm_range: tuple[int, int]
    groove_profile: GrooveProfile

    kick_patterns: tuple[list[float], ...]
    snare_patterns: tuple[list[float], ...]
    hat_patterns: tuple[list[float], ...]
    hat_style: str

    bass_octave: int
    bass_patterns: tuple[BassPattern, ...]

    chord_octave: int
    chord_style: str
    chord_rhythms: tuple[list[float], ...]
    chord_duration: float
    chord_extensions: tuple[int, ...]

    lead_octave: int
    lead_phrases: tuple[LeadPhrase, ...]
```

**Add at end of dataclass** — new field with default so all existing callsites are unaffected:
```python
    parent: str | None = None  # key into GENRE_REGISTRY, e.g. "house"
```

---

#### Sub-task B: Add `"laid_back"` and `"push"` to `GROOVE_TEMPLATES`

**Core pattern** (lines 58–108 — existing `GROOVE_TEMPLATES` dict):
```python
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
    "dnb_tight": GrooveProfile(
        name="dnb_tight",
        position_jitter_ms=3.5,
        velocity_jitter=5,
        length_jitter=0.008,
        weak_beat_curve=(1.0, 0.86, 0.94, 0.82),
        push_pull_per_subdivision=(0.0, -0.004, 0.0, -0.006),
    ),
    ...
}
```

**`from_swing()` factory** (lines 45–55 — use for `"laid_back"`):
```python
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
```

**Add after line 108** (end of `GROOVE_TEMPLATES` dict):
```python
GROOVE_TEMPLATES["laid_back"] = GrooveProfile.from_swing(0.62, "laid_back")
# position_jitter_ms≈28.8, velocity_jitter≈28, length_jitter≈0.06

GROOVE_TEMPLATES["push"] = GrooveProfile(
    name="push",
    position_jitter_ms=3.0,
    velocity_jitter=4,
    length_jitter=0.007,
    weak_beat_curve=(1.0, 0.88, 0.96, 0.84),
    push_pull_per_subdivision=(-0.005, 0.0, -0.003, 0.0),
)
```

---

#### Sub-task C: Add `DEEP_HOUSE` and `TECH_HOUSE` `GenreDNA` constants + registry entries

**Core pattern** — existing `HOUSE` constant (lines 140–190) and `UK_GARAGE` constant (lines 192–244). Follow identical frozen dataclass instantiation:
```python
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
        [0.5, 1.5, 2.5, 3.5],
        [i * 0.5 for i in range(8)],
    ),
    hat_style="8ths",
    bass_octave=1,
    bass_patterns=(
        [(0.0, 0, 0.4, 100), (0.5, 0, 0.4, 90), ...],
        [(0.0, 0, 0.7, 100), (1.0, 0, 0.7, 96), ...],
        [(0.0, 0, 0.35, 100), (0.5, 12, 0.3, 80), ...],
    ),
    chord_octave=4, chord_style="stab",
    chord_rhythms=(...),
    chord_duration=0.4,
    chord_extensions=(),
    lead_octave=4,
    lead_phrases=(...),
)
```

**`GENRE_REGISTRY` extension pattern** (lines 708–733 — flat dict mapping):
```python
GENRE_REGISTRY: dict[str, GenreDNA] = {
    "house": HOUSE,
    "uk garage": UK_GARAGE,
    "techno": TECHNO,
    # sub-genres: add below existing keys
    "deep_house": DEEP_HOUSE,
    "tech_house": TECH_HOUSE,
}
```

**`_resolve_genre()` + `_RESOLVED_GENRE_REGISTRY` infrastructure** — new function, place after `GENRE_REGISTRY` definition. Requires `import dataclasses` at top of file (already imported via `from dataclasses import dataclass`; use `dataclasses.replace()`):
```python
import dataclasses  # add to top-level imports

def _resolve_genre(key: str, registry: dict[str, "GenreDNA"]) -> "GenreDNA":
    child = registry[key]
    if child.parent is None:
        return child
    if child.parent not in registry:
        return child
    if child.parent == key:
        raise ValueError(f"Circular parent: {key!r} points to itself")
    parent = registry[child.parent]
    return dataclasses.replace(
        child,
        bass_patterns=parent.bass_patterns + child.bass_patterns,
        lead_phrases=parent.lead_phrases + child.lead_phrases,
    )

_RESOLVED_GENRE_REGISTRY: dict[str, GenreDNA] = {
    key: _resolve_genre(key, GENRE_REGISTRY)
    for key in GENRE_REGISTRY
}

# Public alias for AC-4 test import
RESOLVED_GENRE_REGISTRY = _RESOLVED_GENRE_REGISTRY
```

**`lookup_genre()` update** (line 1003–1005 — existing):
```python
def lookup_genre(name: str) -> GenreDNA:
    """Return the GenreDNA for a genre name, falling back to House."""
    return GENRE_REGISTRY.get(name.lower().strip(), DEFAULT_DNA)
```
Change to:
```python
def lookup_genre(name: str) -> GenreDNA:
    """Return the resolved GenreDNA for a genre name, falling back to House."""
    return _RESOLVED_GENRE_REGISTRY.get(name.lower().strip(), DEFAULT_DNA)
```

---

#### Sub-task D: Add `CURATED_GENRES` entries for Deep House and Tech House

**Core pattern** (lines 738–813 — existing `"house"` and `"techno"` entries):
```python
CURATED_GENRES: dict[str, CuratedGenreDNA] = {
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
            ...
        ),
        rule_breakers=(...),
        blends_with=("uk garage", "techno", "afrobeats", "amapiano"),
        vibe_words=("four on the floor", "pumping", "club", "classic", "driving", "groove", "disco"),
    ),
    "techno": CuratedGenreDNA(
        name="Techno",
        bpm_range=(125, 135),
        swing_percent=(50, 52),
        bar_grid="4/4 16-bar phrases",
        structure=("intro 16", "build 32", "peak 32", "reduction 16", "peak 2 32", "outro 16"),
        ...
    ),
```

**Add new entries** (after existing `"house"` and `"techno"` entries, D-05 and D-06 section structures are locked):
```python
    "deep_house": CuratedGenreDNA(
        name="Deep House",
        bpm_range=(120, 124),
        swing_percent=(60, 65),
        bar_grid="4/4 16-bar phrases",
        structure=(
            "intro 32", "build 16", "main 32", "break 16", "main 2 32", "outro 32"
        ),  # D-05: 160 bars total
        ...
        vibe_words=("deep", "soulful", "late-night", "rhodes", "warm", "hypnotic", "jazzy"),
    ),
    "tech_house": CuratedGenreDNA(
        name="Tech House",
        bpm_range=(127, 132),
        swing_percent=(50, 52),
        bar_grid="4/4 16-bar phrases",
        structure=(
            "intro 16", "build 32", "peak 32", "reduction 16", "peak 2 32", "outro 16"
        ),  # D-06: 144 bars total
        ...
        vibe_words=("dark", "industrial", "techno-edge", "rolling", "minimal", "peak-hour", "pressure"),
    ),
```

Also add `CURATED_ALIASES` entries after line 999 (existing aliases section):
```python
CURATED_ALIASES: dict[str, str] = {
    ...
    "deep house": "deep_house",   # ADD
    "tech house": "tech_house",   # ADD
}
```

---

#### Sub-task E: Extend `detect_style_from_text()`

**Core pattern** (lines 1154–1202 — existing `if/elif` priority chain):
```python
def detect_style_from_text(text: str) -> str:
    lowered = text.lower()
    # Priority matches — order is decisive
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
    ...
    if "techno" in lowered:                # <-- sub-genre checks MUST precede this line (line 1175)
        return "techno"
    ...
```

**Insert before the `"techno"` check at line 1175**:
```python
    # Sub-genre checks — MUST precede the "techno" catch-all
    if any(word in lowered for word in [
        "deep house", "soulful house", "late-night house", "rhodes house"
    ]):
        return "deep_house"
    if any(word in lowered for word in [
        "tech house", "techno house", "dark house", "industrial house", "peak-hour house"
    ]):
        return "tech_house"
    # existing "techno" check follows:
    if "techno" in lowered:
        return "techno"
```

---

### `vibelton/harmony.py` — 1 sub-task (service, transform)

**Analog:** `vibelton/harmony.py` — existing `_EDM_STYLES` set (lines 295–300)

**Core pattern** (lines 295–300):
```python
# Genres where the main/drop section traditionally reduces to 1-2 chords.
_EDM_STYLES = {
    "house", "uk garage", "techno", "trance",
    "drum n bass", "jungle", "dubstep", "grime",
    "trap",
}
```

**Extend** (add two entries to the set literal):
```python
_EDM_STYLES = {
    "house", "uk garage", "techno", "trance",
    "drum n bass", "jungle", "dubstep", "grime",
    "trap",
    "deep_house",   # ADD
    "tech_house",   # ADD
}
```

---

### `vibelton/planner.py` — 3 sub-tasks (service, event-driven)

**Analog:** `vibelton/planner.py` — existing `genre_words()`, `STYLE_PALETTES`, `expanded_song_sketch_plan()`

---

#### Sub-task A: Add sub-genre words to `genre_words()`

**Core pattern** (lines 1253–1279):
```python
def genre_words() -> list[str]:
    return [
        "dance and mainstage",
        "downtempo",
        "drum n bass",
        "dnb",
        "dubstep",
        "grime",
        "hip hop",
        "hip-hop",
        "house",
        "90s jungle",
        "jungle",
        ...
        "techno",
        ...
    ]
```

**Add before `"house"`** (so sub-genre words match first):
```python
        "deep house",    # ADD — before "house"
        "tech house",    # ADD — before "techno"
        "house",
        ...
        "techno",
```

---

#### Sub-task B: Add `STYLE_PALETTES` entries for `deep_house` and `tech_house`

**Core pattern** (lines 1296–1404 — existing per-style dicts):
```python
STYLE_PALETTES: dict[str, dict[str, list[str]]] = {
    "house": {
        "chords": ["Electric", "Analog", "Wavetable", "Meld"],
        "pad": ["Warm House Pad", "Analog", "Meld", "Wavetable"],
        "riff": ["Bouncy Riff", "Drift", "Wavetable", "Operator"],
        "hook": ["House Lead", "Wavetable", "Drift", "Electric"],
        "bass": ["Bouncy Bass", "Analog", "Drift", "Operator"],
        "bd": ["909 Core Kit", "808 Core Kit"],
        "hats": ["909 Core Kit", "808 Core Kit"],
    },
    "techno": {
        "chords": ["Analog", "Drift", "Wavetable", "Operator"],
        "pad": ["Dark Pad", "Meld", "Wavetable", "Analog"],
        "riff": ["Hypnotic Riff", "Drift", "Operator", "Wavetable"],
        "hook": ["Minimal Hook", "Operator", "Drift", "Meld"],
        "bass": ["Driving Bass", "Operator", "Drift", "Analog"],
        "bd": ["909 Core Kit", "808 Core Kit"],
    },
```

**Add after existing `"house"` entry** (deep_house blends house + jazzy instruments; tech_house blends techno + rolling textures):
```python
    "deep_house": {
        "chords": ["Rhodes", "Electric", "Analog", "Meld"],
        "pad": ["Warm House Pad", "Warm Pad", "Meld", "Analog"],
        "riff": ["Soulful Riff", "Electric", "Drift", "Wavetable"],
        "hook": ["House Lead", "Electric", "Drift", "Wavetable"],
        "bass": ["Sub Bass", "Analog", "Drift", "Operator"],
        "bd": ["909 Core Kit", "808 Core Kit"],
        "hats": ["909 Core Kit", "808 Core Kit"],
    },
    "tech_house": {
        "chords": ["Analog", "Drift", "Wavetable", "Operator"],
        "pad": ["Dark Pad", "Tension", "Meld", "Wavetable"],
        "riff": ["Hypnotic Riff", "Acid Riff", "Drift", "Operator"],
        "hook": ["Minimal Hook", "Operator", "Drift", "Meld"],
        "bass": ["Rolling Bass", "Driving Bass", "Operator", "Drift"],
        "bd": ["909 Core Kit", "808 Core Kit"],
        "hats": ["909 Core Kit", "808 Core Kit"],
    },
```

---

#### Sub-task C: D-07 Randomised Intro Strategy in `expanded_song_sketch_plan()`

**Extension point** (lines 1150–1176 — existing section loop):
```python
for scene_index, (section, bars, energy) in enumerate(sections):
    actions.append({"type": "set_scene_name", "scene_index": scene_index, "name": section})
    if "Chords" in track_names:
        actions.append(scene_clip("Chords", ...))
    if "Pad" in track_names:
        actions.append(scene_clip("Pad", ...))
    if "Bass" in track_names and energy != "intro":
        actions.append(scene_clip("Bass", ...))
    if "Riff" in track_names and energy in {"build", "main"}:
        actions.append(scene_clip("Riff", ...))
    if "Hook" in track_names and energy in {"main", "break"}:
        actions.append(scene_clip("Hook", ...))
    if "Hh / Sh / Rd" in track_names:
        actions.append(scene_clip("Hh / Sh / Rd", ...))
    ...
    if energy != "break":
        if "Bd" in track_names:
            actions.append(scene_clip("Bd", ...))
        if "Snare / Clap" in track_names:
            actions.append(scene_clip("Snare / Clap", ...))
    ...
```

**Seed pattern** — existing `_pattern_seed()` approach already used in `genre_dna.py` `pick_pattern()` and referenced throughout planner. Apply same deterministic seed derivation before the section loop:

```python
# D-07: Randomised intro strategy (before the section loop)
_INTRO_STRATEGIES = {0: "drums_reveal", 1: "atmosphere", 2: "filtered"}
intro_seed = sum(ord(c) for c in message) % 3
intro_style = _INTRO_STRATEGIES[intro_seed] if style in ("deep_house", "tech_house") else None

for scene_index, (section, bars, energy) in enumerate(sections):
    # ... existing scene_name action ...

    # D-07 gating for deep_house and tech_house intro sections
    if energy == "intro" and intro_style == "atmosphere":
        # Only Chords, Pad, Ambience — skip drums and bass
        _intro_drums = False
        _intro_bass = False
    elif energy == "intro" and intro_style == "drums_reveal":
        # Only Bd, Hh/Sh/Rd — skip Chords, Pad, Bass, Hook, Riff
        _intro_drums = True
        _intro_bass = False
    else:
        # "filtered" (all tracks at reduced velocity, handled by energy="intro" in genre_*())
        # or non-deep_house/tech_house genres
        _intro_drums = True
        _intro_bass = False  # existing behavior: Bass already skipped when energy == "intro"

    # Then use _intro_drums / _intro_bass flags to gate clip generation below
```

**Allowed-tracks branching for deep_house and tech_house** — add alongside existing style branches (lines 962–988):
```python
elif "deep_house" in style_key:
    allowed_tracks = {
        "Chords", "Pad", "Bass", "Riff", "Hook",
        "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Drum Instrument", "Ambience"
    }
elif "tech_house" in style_key:
    allowed_tracks = {
        "Bass", "Pad", "Riff",
        "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Drum Instrument", "Ambience"
    }
```

---

### `lib/genreDNA.ts` — model, transform

**Analog:** `lib/genreDNA.ts` — existing `house` and `techno` entries (lines 44–93)

**Core pattern** (lines 44–68, existing `house` entry):
```typescript
export const GENRES: Record<string, GenreDNA> = {
  ukGarage: {
    name: 'UK Garage',
    bpmRange: [130, 136],
    swingPercent: [58, 65],
    barGrid: '4/4 8-bar phrases',
    structure: ['intro 8', 'build 16', 'drop 16', 'break 8', 'drop 2 16', 'outro 8'],
    kickPattern: '...',
    bassPattern: '...',
    hiHatPattern: '...',
    energyArc: 'tension-release',
    rules: [...],
    ruleBreakers: [...],
    blendsWith: ['afrobeats', 'amapiano', 'house', 'grime', 'drumAndBass'],
    vibeWords: [...],
  },

  house: {
    name: 'House',
    bpmRange: [120, 128],
    ...
    blendsWith: ['ukGarage', 'techno', 'afrobeats', 'amapiano'],
    vibeWords: ['four on the floor', 'pumping', 'club', 'classic', 'driving', 'groove', 'disco'],
  },
```

**Add after `house` entry** — camelCase keys match existing convention; `blendsWith` values use camelCase partner keys:
```typescript
  deepHouse: {
    name: 'Deep House',
    bpmRange: [120, 124],
    swingPercent: [60, 65],
    barGrid: '4/4 16-bar phrases',
    structure: ['intro 32', 'build 16', 'main 32', 'break 16', 'main 2 32', 'outro 32'],
    kickPattern: 'Patient four-on-the-floor with a soft ghost on beat 3. No double kicks.',
    bassPattern: 'Sub-bass focused. Octave drops on bar 3 give forward pull.',
    hiHatPattern: 'Open hat on upbeats or closed 8th-note drive.',
    energyArc: 'sustained',
    rules: [
      'Kick is patient — four-on-the-floor, nothing busier.',
      'Whole-bar chords let the harmony breathe.',
      'Long intro and outro for DJ mixing.',
      'Rhodes or warm pad leads are slow and stepwise.',
      'Bass and kick are glued but the bass has space to move.',
    ],
    ruleBreakers: [
      'Add a #11 voicing to the chord for one section.',
      'Drop the kick for 4 bars and let bass carry.',
    ],
    blendsWith: ['house', 'amapiano', 'ukGarage'],
    vibeWords: ['deep', 'soulful', 'late-night', 'rhodes', 'warm', 'hypnotic', 'jazzy'],
  },

  techHouse: {
    name: 'Tech House',
    bpmRange: [127, 132],
    swingPercent: [50, 52],
    barGrid: '4/4 16-bar phrases',
    structure: ['intro 16', 'build 32', 'peak 32', 'reduction 16', 'peak 2 32', 'outro 16'],
    kickPattern: 'Relentless four-on-the-floor at full velocity. No variation, no mercy.',
    bassPattern: 'Rolling 16th-note riff. Tight and industrial. Bass is texture as much as groove.',
    hiHatPattern: '16th-note closed hats, high velocity, or alternating open/closed 16ths.',
    energyArc: 'meditative',
    rules: [
      'Kick never rests.',
      'Bass rolls in continuous 16ths.',
      '8th-note chord stabs alternate chord and silence.',
      'Short staccato lead phrases.',
      'Builds are long — tension accumulates across 32 bars.',
    ],
    ruleBreakers: [
      'Strip everything except kick and bass for 8 bars.',
      'Add a pitched LFO stab on every beat.',
    ],
    blendsWith: ['techno', 'house', 'ukGarage'],
    vibeWords: ['dark', 'industrial', 'techno-edge', 'rolling', 'minimal', 'peak-hour', 'pressure'],
  },
```

**`genreId` key convention** — `route.ts` line 436 validates `GENRES[body.genreId]`. Genre card `data-genreId` must be `"deepHouse"` / `"techHouse"` (camelCase) to pass validation.

---

### `app/page.tsx` — component, request-response

**Analog:** `web/styles.css` `.prompt-button` + `.vst-settings details` + `lib/genreDNA.ts` card-click routing pattern

**No direct code analog exists** — `app/page.tsx` is currently 8 lines (lines 1–8):
```tsx
export default function Home() {
  return (
    <main>
      <h1>Vibleton</h1>
      <p>The Finisher API is available at /api/finisher.</p>
    </main>
  )
}
```

**React state pattern for card click routing** (from RESEARCH.md Pattern 6 + route.ts FinisherRequest type):
```tsx
'use client'
import { useState } from 'react'

export default function Home() {
  const [userInput, setUserInput] = useState('')
  const [genreId, setGenreId] = useState('house')

  function handleCardClick(promptTemplate: string, cardGenreId: string) {
    setUserInput(promptTemplate)
    setGenreId(cardGenreId)  // must be camelCase: "deepHouse" | "techHouse"
  }

  // POST to /api/finisher with { genreId, userInput }
}
```

**HTML element pattern for expandable parent card** — copy from `.vst-settings details` CSS class (lines 637–665 of `web/styles.css`):
```tsx
<details className="genre-parent-card">
  <summary>
    <h2>House <small>Deep House · Tech House</small></h2>
  </summary>
  <div className="genre-sub-cards">
    {/* sub-genre buttons here */}
  </div>
</details>
```

**HTML element pattern for sub-genre and direct-click cards** — copy `.prompt-button` class (lines 331–364 of `web/styles.css`):
```tsx
<button
  className="prompt-button genre-sub-card"
  onClick={() => handleCardClick(DEEP_HOUSE_PROMPT, 'deepHouse')}
>
  <span>Deep House</span>
  <small className="genre-subline">120–124 BPM · Soulful · Late-night</small>
  <p className="genre-description">Slow, soulful, Rhodes-driven House...</p>
</button>
```

**Prompt template constants** (from UI-SPEC §Copywriting Contract — copy verbatim):
```tsx
const DEEP_HOUSE_PROMPT =
  'Create an expanded Deep House song sketch with soulful chords, warm bassline, late-night groove, and jazzy lead phrases.'
const TECH_HOUSE_PROMPT =
  'Create an expanded Tech House song sketch with rolling bass, dark industrial textures, tight hi-hats, and relentless kick.'
```

---

### `app/layout.tsx` — config, request-response

**Analog:** `app/layout.tsx` (lines 1–9 — existing bare layout)

```tsx
import type { ReactNode } from 'react'

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
```

**CSS import addition** — add one import line. Two options per RESEARCH.md Open Question 1:
- Option A (preferred): `import '../web/styles.css'` — add as first line
- Option B (fallback): Copy `:root` block (lines 1–16 of `web/styles.css`) into `app/globals.css` and add `import './globals.css'`

Resulting layout:
```tsx
import '../web/styles.css'   // ADD — supplies all var(--accent), var(--panel-strong) tokens
import type { ReactNode } from 'react'

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
```

---

### `tests/test_genre_dna.py` — test, batch

**Analog:** `tests/test_genre_dna.py` — existing `GenreDNATest` class (lines 1–102)

**Import pattern** (lines 1–14 — copy and extend):
```python
from __future__ import annotations
import unittest
from vibelton.actions import genre_bassline, genre_chords, genre_drums, genre_lead
from vibelton.genre_dna import (
    CURATED_GENRES,
    GENRE_REGISTRY,
    GROOVE_TEMPLATES,
    GrooveProfile,
    build_curated_prompt_context,
    detect_style_from_text,
    find_curated_genres_by_vibe,
)
```

**Add to imports** (after `detect_style_from_text`):
```python
from vibelton.genre_dna import (
    ...
    RESOLVED_GENRE_REGISTRY,   # ADD — for AC-4 bass list test
)
```

**Test structure pattern** (lines 17–46 — copy `subTest` and `assertEqual` patterns):
```python
class GenreDNATest(unittest.TestCase):
    def test_required_groove_templates_exist(self) -> None:
        self.assertTrue({"mpc_58", "mpc_62", "dnb_tight", "ukg_shuffle", "dembow", "trap_triplet"}.issubset(GROOVE_TEMPLATES))

    def test_curated_genre_prompt_layer_covers_phase_one_genres(self) -> None:
        self.assertEqual(
            {
                "afrobeats", "amapiano", "drum n bass", "dubstep", "grime",
                "house", "jungle", "techno", "trap", "uk garage",
            },
            set(CURATED_GENRES),
        )
```

**UPDATE existing test** (lines 31–46) — extend expected set:
```python
    def test_curated_genre_prompt_layer_covers_phase_one_genres(self) -> None:
        self.assertEqual(
            {
                "afrobeats", "amapiano", "drum n bass", "dubstep", "grime",
                "house", "jungle", "techno", "trap", "uk garage",
                "deep_house",   # ADD
                "tech_house",   # ADD
            },
            set(CURATED_GENRES),
        )
```

**Add new tests** — copy structure from `test_curated_only_genres_do_not_fall_back_to_house` (lines 57–61) and `test_all_genres_have_groove_profiles` (lines 18–26):
```python
    def test_deep_house_bpm_range(self) -> None:
        # AC-1
        curated = CURATED_GENRES["deep_house"]
        self.assertEqual((120, 124), curated.bpm_range)

    def test_tech_house_bpm_range(self) -> None:
        # AC-2
        curated = CURATED_GENRES["tech_house"]
        self.assertEqual((127, 132), curated.bpm_range)

    def test_bass_list_extended_by_parent(self) -> None:
        # AC-4: RESOLVED_GENRE_REGISTRY["deep_house"] has >= 5 bass patterns
        # (3 from HOUSE parent + >= 2 from DEEP_HOUSE child)
        self.assertGreaterEqual(len(RESOLVED_GENRE_REGISTRY["deep_house"].bass_patterns), 5)

    def test_kick_pattern_divergence(self) -> None:
        # AC-3
        self.assertNotEqual(
            CURATED_GENRES["deep_house"].kick_pattern,
            CURATED_GENRES["tech_house"].kick_pattern,
        )

    def test_detect_style_deep_house(self) -> None:
        self.assertEqual("deep_house", detect_style_from_text("Create a deep house track"))

    def test_detect_style_tech_house(self) -> None:
        self.assertEqual("tech_house", detect_style_from_text("Create a tech house track"))
```

**Also update `test_required_groove_templates_exist`** (line 29) — extend expected set:
```python
    def test_required_groove_templates_exist(self) -> None:
        self.assertTrue(
            {"mpc_58", "mpc_62", "dnb_tight", "ukg_shuffle", "dembow", "trap_triplet",
             "laid_back", "push"}.issubset(GROOVE_TEMPLATES)   # ADD "laid_back", "push"
        )
```

---

## Shared Patterns

### Frozen Dataclass Constants (Python)

**Source:** `vibelton/genre_dna.py` lines 19–34 (`CuratedGenreDNA`), lines 111–138 (`GenreDNA`)
**Apply to:** All new Python data constants (`DEEP_HOUSE`, `TECH_HOUSE`, new `CURATED_GENRES` entries, new `GROOVE_TEMPLATES` entries)

Pattern: All data is module-level frozen dataclass instances. No mutation after import. No factory functions for individual constants — all fields set inline at definition site.

### `pick_pattern()` Deterministic Seed

**Source:** `vibelton/genre_dna.py` lines 1205–1208
```python
def pick_pattern(patterns: tuple | list, seed: int) -> list:
    """Deterministically pick a pattern variant from a list using a seed."""
    if not patterns:
        return []
    return patterns[seed % len(patterns)]
```
**Apply to:** D-07 intro strategy seed derivation — use `sum(ord(c) for c in message) % 3` to match this deterministic seed pattern. Same approach as `_pattern_seed()` references elsewhere in planner.py.

### CSS Token System

**Source:** `web/styles.css` lines 1–16 (`:root` block)
```css
:root {
  --bg: #101312;
  --ink: #f3f0e8;
  --muted: #b9c2ba;
  --soft: #d7ded5;
  --line: #2c342f;
  --panel: #171c1a;
  --panel-strong: #202823;
  --dark: #0b0e0d;
  --accent: #67b99a;
  --accent-2: #d38b5d;
  --amber: #d9b56f;
  --danger: #d46a5f;
  ...
}
```
**Apply to:** All new CSS in `app/page.tsx` inline styles or a `<style>` block. Use only existing tokens — no new primitives. Must import `web/styles.css` in `app/layout.tsx` first.

### `<details>`/`<summary>` Expand Pattern

**Source:** `web/styles.css` lines 637–665 (`.vst-settings details`)
```css
.vst-settings details { border: 0; }
.vst-settings summary { cursor: pointer; list-style: none; }
.vst-settings summary::-webkit-details-marker { display: none; }
.vst-settings summary h2::after {
  content: "▸";
  transition: transform 200ms ease;
  font-size: 13px;
  color: var(--muted);
}
.vst-settings details[open] summary h2::after {
  transform: rotate(90deg);
}
```
**Apply to:** `app/page.tsx` House parent card. Copy the CSS class to a new `.genre-parent-card` scoped version in `app/globals.css`, or add inline `<style>` block in `app/page.tsx`.

### `route.ts` Input Validation Pattern

**Source:** `app/api/finisher/route.ts` lines 432–444
```typescript
export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as FinisherRequest
    if (!body.genreId || !GENRES[body.genreId]) {
      return NextResponse.json({ error: 'Invalid or missing genreId' }, { status: 400 })
    }
    if (!body.userInput || typeof body.userInput !== 'string') {
      return NextResponse.json({ error: 'Missing userInput' }, { status: 400 })
    }
    if (body.blendWith && !GENRES[body.blendWith]) {
      return NextResponse.json({ error: 'Invalid blendWith genre' }, { status: 400 })
    }
```
**Apply to:** `lib/genreDNA.ts` additions must use camelCase keys (`deepHouse`, `techHouse`) so `GENRES[body.genreId]` resolves at line 436. Genre card `data-genreId` attribute must match.

### `unittest.TestCase` + `subTest` Pattern

**Source:** `tests/test_genre_dna.py` lines 17–26
```python
class GenreDNATest(unittest.TestCase):
    def test_all_genres_have_groove_profiles(self) -> None:
        for name, dna in GENRE_REGISTRY.items():
            with self.subTest(name=name):
                self.assertIsInstance(dna.groove_profile, GrooveProfile)
```
**Apply to:** All new tests in `tests/test_genre_dna.py`. Use `self.assertEqual`, `self.assertGreaterEqual`, `self.assertNotEqual` — same assertion methods as existing tests.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `LISTENING_NOTES.md` | config | — | No template document analog exists; planner should use RESEARCH.md SPEC §6 AC-7 for structure |

---

## Metadata

**Analog search scope:** `vibelton/`, `app/`, `lib/`, `tests/`, `web/styles.css`
**Files scanned:** 9 source files read
**Pattern extraction date:** 2026-05-22
