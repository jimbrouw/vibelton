# Phase 1: House Sub-Genre Expansion - Research

**Researched:** 2026-05-22
**Domain:** Python GenreDNA data model + Next.js genre card UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Expandable parent card — House card clicks to reveal sub-genre cards inside. Collapsed by default.
**D-02:** Sub-genres only when expanded — no generic "House" fallback option. Expanding House shows Deep House and Tech House directly.
**D-03:** Non-parent genres (Techno, UKG, Trap, etc.) are direct-click cards — one click fires the prompt. No expand behavior. Different visual from parent cards.
**D-04:** Subtle slide-down animation (~200ms) for expand/collapse of sub-genre cards.
**D-05:** Deep House uses extended intro/outro DJ format — `intro 32 → build 16 → main 32 → break 16 → main 2 32 → outro 32` (160 bars total). Extra-long intro/outro for DJ mixing.
**D-06:** Tech House uses Techno-influenced long builds — `intro 16 → build 32 → peak 32 → reduction 16 → peak 2 32 → outro 16` (144 bars total). Slow tension builds into long relentless peaks.
**D-07:** Randomised intro strategy — both Deep House and Tech House intros randomly select from 3 intro styles per generation: (a) drums-only slow reveal, (b) chords + atmosphere first, (c) full but filtered. Ensures each sketch has a different intro character.

### Claude's Discretion
- Card click behavior: Claude determines how genre card clicks route to the plan API, given the existing `/api/finisher` endpoint.
- Groove profile values: Concrete `GrooveProfile` numeric entries for `"laid_back"` and `"push"` — derived from SPEC descriptions.
- `CuratedGenreDNA` entries: Full entries for Deep House and Tech House following existing pattern, using section structures from D-05 and D-06.
- `detect_style_from_text()` keyword ordering: Sub-genre keywords inserted before the `"house"` catch-all.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SPEC §3.1 | Add `parent: str | None = None` field to `GenreDNA` frozen dataclass | Direct field addition; no downstream breakage — all callers use named fields |
| SPEC §3.2 | Implement `_resolve_genre()` + `_RESOLVED_GENRE_REGISTRY` at module load | New function; existing `GENRE_REGISTRY` dict replaced by resolved version |
| SPEC §3.3 | Add `DEEP_HOUSE` constant + `CuratedGenreDNA` entry + registry keys | Follows exact same module-level constant pattern as existing genres |
| SPEC §3.4 | Add `TECH_HOUSE` constant + `CuratedGenreDNA` entry + registry keys | Same pattern |
| SPEC §4 | Extend `detect_style_from_text()` with sub-genre keyword priority chain | Insert before existing `"techno"` check (which catches "tech house" ambiguity) |
| SPEC §5 | Add genre cards section to `app/page.tsx` | `app/page.tsx` is currently 8 lines; `web/styles.css` CSS tokens available via import |
| SPEC §6 AC-7 | Create `LISTENING_NOTES.md` template for Jim's manual listening gate | New file, no code dependency |
| D-07 | Randomised intro strategy in `expanded_song_sketch_plan()` | New mechanism required; existing energy-based branching is the extension point |
| GROOVE | Add `"laid_back"` and `"push"` to `GROOVE_TEMPLATES` | Same `GrooveProfile` pattern; values derived from swing/feel descriptions |
</phase_requirements>

---

## Summary

Phase 1 has three distinct implementation surfaces that must coordinate: (1) the Python data model in `genre_dna.py`, (2) the planner/actions Python backend, and (3) the Next.js `app/page.tsx` frontend. All three are well-isolated and can be implemented in sequence without cross-contamination risk.

The GenreDNA inheritance mechanism is a new concept not yet in the codebase. The SPEC defines it completely: a depth-1 parent pointer on `GenreDNA`, a `_resolve_genre()` function that merges fields at module load time, and a `_RESOLVED_GENRE_REGISTRY` that replaces `GENRE_REGISTRY` as the lookup target. The merge rules are precise per field group (replace vs. concatenate). The existing `lookup_genre()` function just needs to query `_RESOLVED_GENRE_REGISTRY` instead of `GENRE_REGISTRY`.

The frontend work is the most open-ended surface. `app/page.tsx` is currently 8 lines. The UI-SPEC defines exact CSS class reuse, component structure, copy, and interaction behavior. The critical routing decision (Claude's Discretion) is: genre card clicks must populate `userInput` from the card's prompt template and pass `genreId` as `"deep_house"` or `"tech_house"` to `POST /api/finisher`. This works because `lib/genreDNA.ts` is the TypeScript genre registry for the finisher API, and `GENRES` must receive `"deepHouse"` and `"techHouse"` entries (camelCase per existing convention). The `genreId` from the UI should match a key in the TypeScript `GENRES` object, so the card's `data-genreId` attribute should use camelCase (`deepHouse`, `techHouse`) to match `lib/genreDNA.ts` conventions — or the route.ts validation must be updated to accept the underscore keys.

**Primary recommendation:** Implement in four waves: (1) GROOVE_TEMPLATES additions + GenreDNA parent field + _resolve_genre() infrastructure, (2) DEEP_HOUSE and TECH_HOUSE constants + CuratedGenreDNA entries + registry updates, (3) detect_style_from_text() + expanded_song_sketch_plan() D-07 intro strategy + harmony.py _EDM_STYLES update, (4) app/page.tsx genre card UI + lib/genreDNA.ts TypeScript entries.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| GenreDNA inheritance resolution | API / Backend (Python) | — | Module-level at import time; no runtime cost |
| BPM selection (Deep House / Tech House) | API / Backend (Python) | — | `curated_default_bpm()` reads from `CuratedGenreDNA.bpm_range` |
| Arrangement sections (D-05, D-06) | API / Backend (Python) | — | `curated_sections_for_genre()` parses `CuratedGenreDNA.structure` |
| Drum/bass/lead pattern generation | API / Backend (Python) | — | `genre_drums()`, `genre_bassline()`, `genre_lead()` in actions.py |
| Groove profile application | API / Backend (Python) | — | `apply_groove()` in actions.py reads from `GenreDNA.groove_profile` |
| Harmony plan (2-chord drop) | API / Backend (Python) | — | `_EDM_STYLES` set in harmony.py gates the 2-chord drop behavior |
| Genre detection from text | API / Backend (Python) | — | `detect_style_from_text()` in genre_dna.py; sub-genre checks must precede "house" |
| D-07 randomised intro strategy | API / Backend (Python) | — | New branching inside `expanded_song_sketch_plan()` |
| Genre card UI | Frontend Server (Next.js SSR) | Browser / Client | `app/page.tsx` React component; `<details>`/`<summary>` expand is native browser behavior |
| Prompt routing to /api/finisher | Browser / Client | Frontend Server | Card click writes `data-prompt` into `<textarea>` via React state |
| TypeScript genre registry | Frontend Server (Next.js SSR) | — | `lib/genreDNA.ts` — server-side context builder for the LLM prompt |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses (frozen) | stdlib | GenreDNA / CuratedGenreDNA / GrooveProfile | Already used for every genre constant in genre_dna.py |
| Next.js | ^16.2.4 | React SSR framework for app/page.tsx | Already installed; project uses App Router |
| React | ^19.2.5 | Component model for genre card UI | Already installed |

[VERIFIED: package.json in project root]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Unit test runner | All Python tests; `python3 -m pytest tests/` |
| TypeScript | ^6.0.3 | Type-safe lib/genreDNA.ts | Already installed; lib/genreDNA.ts is the TypeScript genre registry |

[VERIFIED: package.json and pytest --version output]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `<details>`/`<summary>` for expand | React state toggle | `<details>` is native, zero JS, keyboard-accessible; React toggle needs JS event handlers and ARIA — no benefit |
| CSS `max-height` transition for slide | JS height calculation | CSS-only is simpler; already matches D-04 200ms ease |
| Module-load merge (depth-1) | Runtime merge per lookup | SPEC mandates module-load caching in `_RESOLVED_GENRE_REGISTRY`; runtime merge would add latency every API call |

---

## Architecture Patterns

### System Architecture Diagram

```
User clicks genre card
        |
        v
app/page.tsx (React)
  └── onClick: writes data-prompt → textarea, data-genreId → hidden input
        |
        v
User clicks "Generate" (or auto-submits)
        |
        v
POST /api/finisher (Next.js API route)
  ├── reads genreId → lib/genreDNA.ts GENRES lookup
  ├── builds LLM prompt from genre context (TypeScript side)
  └── returns FinisherResponse JSON
        |
        v
Python backend (vibelton/)
  ├── detect_style_from_text() → "deep_house" or "tech_house"
  ├── lookup_genre() → _RESOLVED_GENRE_REGISTRY["deep_house"] (merged GenreDNA)
  ├── curated_sections_for_genre() → section list from CuratedGenreDNA.structure
  ├── expanded_song_sketch_plan() → calls genre_drums/genre_bassline/genre_lead/genre_chords
  └── returns action list with set_tempo, create_midi_clip, etc.
```

Note: The TypeScript side (`lib/genreDNA.ts`) and Python side (`vibelton/genre_dna.py`) are parallel, independent registries. Both must receive Deep House and Tech House entries. The TypeScript registry feeds the LLM prompt context for the Finisher API. The Python registry drives the MIDI generation logic.

### Recommended Project Structure (changes only)

```
vibelton/
├── genre_dna.py      # ADD: parent field, GROOVE_TEMPLATES entries, DEEP_HOUSE,
│                     #      TECH_HOUSE, _resolve_genre(), _RESOLVED_GENRE_REGISTRY,
│                     #      CuratedGenreDNA entries, detect_style_from_text() extensions
vibelton/
├── planner.py        # ADD: "deep house"/"tech house" to genre_words(),
│                     #      D-07 intro strategy in expanded_song_sketch_plan(),
│                     #      STYLE_PALETTES entries for deep_house/tech_house
vibelton/
├── harmony.py        # ADD: "deep_house" and "tech_house" to _EDM_STYLES set
lib/
├── genreDNA.ts       # ADD: deepHouse and techHouse entries to GENRES object
app/
├── page.tsx          # REPLACE: 8-line stub with genre cards section
├── globals.css       # ADD (or update): CSS token import from web/styles.css
                      #   (OR copy :root block into globals.css)
tests/
├── test_genre_dna.py # UPDATE: test_curated_genre_prompt_layer_covers_phase_one_genres
│                     #         will need deep_house and tech_house added to expected set
LISTENING_NOTES.md    # CREATE: acceptance gate template for Jim
```

### Pattern 1: Parent-Pointer Inheritance with Module-Load Resolution

**What:** `GenreDNA` gains `parent: str | None = None`. At module load, `_resolve_genre(key)` merges child over parent per field-group rules, caches the result in `_RESOLVED_GENRE_REGISTRY`. `lookup_genre()` switches to query `_RESOLVED_GENRE_REGISTRY`.

**When to use:** Any time a new sub-genre is added in Phase 2.

```python
# Source: SPEC.md §3.2 (locked requirements)
# Filed under genre_dna.py

@dataclass(frozen=True)
class GenreDNA:
    # ... existing fields ...
    parent: str | None = None  # key into GENRE_REGISTRY (e.g. "house")


def _resolve_genre(key: str, base_registry: dict[str, "GenreDNA"]) -> "GenreDNA":
    """Merge child GenreDNA over parent per SPEC §3.2 merge rules (depth-1 only)."""
    child = base_registry[key]
    if child.parent is None:
        return child
    if child.parent not in base_registry:
        return child
    if child.parent == key:
        raise ValueError(f"Circular parent: {key!r} points to itself")
    parent = base_registry[child.parent]
    # Drums + BPM + swing + groove: child replaces parent entirely
    # Bass + lead: child extends parent (concatenate, parent first)
    # Chord rhythm: child replaces
    merged_bass = parent.bass_patterns + child.bass_patterns
    merged_lead = parent.lead_phrases + child.lead_phrases
    return dataclasses.replace(
        child,
        bass_patterns=merged_bass,
        lead_phrases=merged_lead,
    )


# Build resolved registry at module load — no runtime cost
_BASE_GENRE_REGISTRY: dict[str, GenreDNA] = { ... }  # same as current GENRE_REGISTRY

_RESOLVED_GENRE_REGISTRY: dict[str, GenreDNA] = {
    key: _resolve_genre(key, _BASE_GENRE_REGISTRY)
    for key in _BASE_GENRE_REGISTRY
}

def lookup_genre(name: str) -> GenreDNA:
    return _RESOLVED_GENRE_REGISTRY.get(name.lower().strip(), DEFAULT_DNA)
```

[VERIFIED: SPEC.md §3.2 merge rules, genre_dna.py existing `lookup_genre()` implementation]

### Pattern 2: GROOVE_TEMPLATES additions for "laid_back" and "push"

**What:** New entries in `GROOVE_TEMPLATES` dict, using `GrooveProfile.from_swing()` for laid_back and a hand-crafted `GrooveProfile` for push.

**When to use:** Referenced by DEEP_HOUSE (`groove_profile="laid_back"`) and TECH_HOUSE (`groove_profile="push"`).

```python
# Source: SPEC §3.3–3.4 + existing GrooveProfile.from_swing() factory pattern
# [ASSUMED] Exact numeric values derived from SPEC swing descriptions:
# Deep House swing=0.62 (soulful, slightly ahead of MPC_58 which is 0.58-equivalent)
# Tech House swing=0.50 (near-quantised), push = negative jitter for forward lean

GROOVE_TEMPLATES["laid_back"] = GrooveProfile.from_swing(0.62, "laid_back")
# Result: position_jitter_ms≈28.8, velocity_jitter≈28, length_jitter≈0.06

GROOVE_TEMPLATES["push"] = GrooveProfile(
    name="push",
    position_jitter_ms=3.0,      # tight, near-quantised
    velocity_jitter=4,
    length_jitter=0.007,
    weak_beat_curve=(1.0, 0.88, 0.96, 0.84),   # strong beat emphasis
    push_pull_per_subdivision=(-0.005, 0.0, -0.003, 0.0),  # slightly ahead
)
```

[CITED: SPEC.md §3.3 swing=0.62 for Deep House, §3.4 swing=0.50 for Tech House]
[ASSUMED: Exact `push_pull_per_subdivision` values for "push" profile — these are Claude's discretion per CONTEXT.md]

### Pattern 3: CuratedGenreDNA entries (section structures from D-05/D-06)

**What:** New entries in `CURATED_GENRES` dict with the exact section structures locked by CONTEXT.md D-05 and D-06.

```python
# Source: SPEC §3.3 + CONTEXT.md D-05
CURATED_GENRES["deep_house"] = CuratedGenreDNA(
    name="Deep House",
    bpm_range=(120, 124),
    swing_percent=(60, 65),
    bar_grid="4/4 16-bar phrases",
    structure=(
        "intro 32", "build 16", "main 32", "break 16", "main 2 32", "outro 32"
    ),
    kick_pattern="Four-on-the-floor with a ghost hit on beat 3 at low velocity. Patient, patient feel.",
    bass_pattern="Sub-bass focused, octave drop on bar 3. Breathes around the kick.",
    hi_hat_pattern="Open hat on upbeats, or closed 8th-note drive. Two alternating patterns.",
    energy_arc="sustained",
    rules=(
        "Kick stays patient — no double hits.",
        "Whole-bar chord tones let the harmony breathe.",
        "Sub bass octave drops give forward momentum every 4 bars.",
        "Rhodes or warm pad lead phrases are slow and stepwise.",
        "Extra-long intro and outro make it DJ-friendly at 120-124 BPM.",
    ),
    rule_breakers=(
        "add a #11 to the chord voicing",
        "drop the kick for 4 bars",
    ),
    blends_with=("house", "amapiano", "uk garage"),
    vibe_words=("deep", "soulful", "late-night", "rhodes", "warm", "hypnotic", "jazzy"),
)

# Source: SPEC §3.4 + CONTEXT.md D-06
CURATED_GENRES["tech_house"] = CuratedGenreDNA(
    name="Tech House",
    bpm_range=(127, 132),
    swing_percent=(50, 52),
    bar_grid="4/4 16-bar phrases",
    structure=(
        "intro 16", "build 32", "peak 32", "reduction 16", "peak 2 32", "outro 16"
    ),
    kick_pattern="Hard four-on-the-floor, velocity 110-127 on every beat. No ghosts.",
    bass_pattern="Tight 16th-note rolling riff. Industrial distorted tone. Relentless.",
    hi_hat_pattern="16th-note closed hats at high velocity, or alternating open/closed 16ths.",
    energy_arc="meditative",
    rules=(
        "Kick is relentless and machine-like — full velocity every beat.",
        "Bass rolls continuously in 16th-notes, acting as texture as much as groove.",
        "8th-note chord stabs alternate chord and silence for percussive effect.",
        "Short, staccato lead phrases use minor 3rd motifs.",
        "Builds are long (32 bars) — tension accumulates slowly.",
    ),
    rule_breakers=(
        "drop all chords, keep only kick and bass for 8 bars",
        "add a pitched LFO stab repeating every beat",
    ),
    blends_with=("techno", "house", "uk garage"),
    vibe_words=("dark", "industrial", "techno-edge", "rolling", "minimal", "peak-hour", "pressure"),
)
```

[CITED: SPEC.md §3.3, §3.4, CONTEXT.md D-05, D-06]

### Pattern 4: detect_style_from_text() sub-genre priority chain

**What:** New `if` blocks inserted BEFORE the existing `if "techno" in lowered` check (critical — "tech house" contains "tech", would otherwise match techno first). The "tech house" check must also precede "house".

```python
# Source: SPEC.md §4 keyword mappings
# Insert BEFORE the existing "techno" check in detect_style_from_text()
if any(word in lowered for word in [
    "deep house", "soulful house", "late-night house", "rhodes house"
]):
    return "deep_house"
if any(word in lowered for word in [
    "tech house", "techno house", "dark house", "industrial house", "peak-hour house"
]):
    return "tech_house"
# existing "techno" check follows here
```

[CITED: SPEC.md §4]
[VERIFIED: genre_dna.py — "techno" check is currently at line 1175; sub-genre checks must precede it]

### Pattern 5: D-07 Randomised Intro Strategy

**What:** New mechanism in `expanded_song_sketch_plan()` that, when `energy == "intro"` and the style is `"deep_house"` or `"tech_house"`, randomly selects from 3 intro character presets per generation. Currently, the planner uses `energy` uniformly for all sections of the same type.

**When to use:** Only for intro sections of deep_house and tech_house.

**Extension point:** The loop at planner.py line 1150 already branches on `energy`. The intro strategy variation needs a `seed` derived from the message text to ensure determinism per prompt, while varying across different prompts.

```python
# Source: CONTEXT.md D-07
# In expanded_song_sketch_plan(), inside the section loop for intro sections:

intro_seed = sum(ord(c) for c in message) % 3  # 0, 1, or 2
INTRO_STRATEGIES = {
    0: "drums_reveal",   # (a) drums-only slow reveal
    1: "atmosphere",     # (b) chords + atmosphere first, no drums
    2: "filtered",       # (c) full but filtered — all parts at low velocity
}
intro_style = INTRO_STRATEGIES[intro_seed]

# Then gate track inclusion in intro sections based on intro_style:
if energy == "intro" and style in ("deep_house", "tech_house"):
    if intro_style == "drums_reveal":
        # Only Bd, Hh/Sh/Rd — no Bass, Chords, Hook, Pad in intro
    elif intro_style == "atmosphere":
        # Only Chords, Pad, Ambience — no Bd, Bass in intro
    elif intro_style == "filtered":
        # All tracks but at reduced velocity (already handled by energy="intro" in genre_*())
```

[CITED: CONTEXT.md D-07]
[ASSUMED: Exact gating logic and velocity reduction for "filtered" strategy — Claude's discretion]

### Pattern 6: TypeScript genre registry (lib/genreDNA.ts)

**What:** Add `deepHouse` and `techHouse` entries to the `GENRES` object in `lib/genreDNA.ts`. These entries are consumed by `app/api/finisher/route.ts` to build LLM prompts. The `genreId` field in `POST /api/finisher` requests must match these keys.

**Key decision (Claude's Discretion):** The `POST /api/finisher` body uses `genreId: string` which is validated against `GENRES[body.genreId]`. Genre card clicks from `app/page.tsx` should set `genreId` to `"deepHouse"` or `"techHouse"` (camelCase, matching `lib/genreDNA.ts` key convention). The Python `detect_style_from_text()` returns `"deep_house"` / `"tech_house"` (snake_case) — these are different registries and conventions.

```typescript
// Source: lib/genreDNA.ts existing pattern
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

[CITED: SPEC.md §3.3, §3.4, lib/genreDNA.ts existing GenreDNA type and GENRES object]

### Pattern 7: Genre card UI — `<details>`/`<summary>` expand pattern

**What:** Reuse the existing `.vst-settings details` expand/collapse CSS pattern from `web/styles.css`. The House parent card is `<details class="genre-parent-card">`, sub-genre cards are `<button class="prompt-button genre-sub-card">`.

**Critical implementation note:** `web/styles.css` is NOT currently imported in `app/layout.tsx`. The CSS tokens (`--bg`, `--ink`, `--panel-strong`, `--accent`, etc.) must be made available to `app/page.tsx` by either:
- Importing `web/styles.css` in `app/layout.tsx`, or
- Copying the `:root` token block into `app/globals.css`

[CITED: app/layout.tsx (verified — no CSS import), web/styles.css `:root` block, 01-UI-SPEC.md Implementation Notes §2]

### Anti-Patterns to Avoid

- **`detect_style_from_text()` catch-all ordering:** Placing "tech house" check AFTER the `"techno"` check. "tech house" contains neither "techno" nor "house" as exact substrings, but "tech-house" variants might be ambiguous. The SPEC ordering (sub-genres before parent) is mandatory.
- **`GENRE_REGISTRY` as lookup target post-merge:** After adding inheritance, `lookup_genre()` must point to `_RESOLVED_GENRE_REGISTRY`, not the old `GENRE_REGISTRY`. Using the old dict returns unmerged child entries (missing parent bass/lead patterns).
- **Not adding to `_EDM_STYLES`:** Deep House and Tech House intros use `plan_harmony()` with `energy="intro"`. For their drop sections to correctly reduce to 2-chord hypnotic loops, both `"deep_house"` and `"tech_house"` must be in `_EDM_STYLES` in `harmony.py`.
- **Test not updated for new CURATED_GENRES keys:** `test_curated_genre_prompt_layer_covers_phase_one_genres` in `test_genre_dna.py` has a hardcoded expected set of 10 keys. After adding `deep_house` and `tech_house`, the test will FAIL unless the expected set is updated.
- **camelCase vs. snake_case mismatch:** TypeScript `GENRES` uses camelCase keys (`deepHouse`). Python `GENRE_REGISTRY` uses snake_case (`deep_house`). The genre card's `data-genreId` must use camelCase to pass validation in `route.ts`. The Python `userInput` string detection works independently from the genreId.
- **CSS tokens not available in app/page.tsx:** `app/layout.tsx` currently has no CSS import. All `var(--accent)`, `var(--panel-strong)` references in new component styles will be undefined unless the token source is wired in.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Expand/collapse animation | JS-driven height animation | CSS `<details>`/`<summary>` + `transition: opacity` | Native semantics, keyboard support, zero JS; matches `.vst-settings details` existing pattern |
| Genre pattern selection | Custom random per-bar picker | Existing `_pick_bar_pattern()` in actions.py | Already implements musical mutation schedule (fill bars, alt 4-bar phrases) |
| Section energy mapping | Custom section-to-energy logic | Existing `curated_sections_for_genre()` in genre_dna.py | Already parses structure tuples into `(name, bars, energy)` triples |
| BPM default | Hardcoded per-style BPM map | `curated_default_bpm()` reading from `CuratedGenreDNA.bpm_range` | Already integrated into `default_bpm_for_style()` → `expanded_song_sketch_plan()` |
| Harmony 2-chord drop | Custom per-genre harmony logic | `plan_harmony()` with `_EDM_STYLES` gate | Just add "deep_house" / "tech_house" to the set |
| Groove humanisation | New groove implementation | `GrooveProfile.from_swing()` + existing `apply_groove()` | Fully implemented; only need new template entries |

**Key insight:** The architecture of this codebase front-loads complexity into module-level constants (GenreDNA, CuratedGenreDNA, GrooveProfile). Adding new genres is primarily a data entry task, not a logic task. The planner and actions code picks up new genres automatically once the data is correctly registered.

---

## Common Pitfalls

### Pitfall 1: Test suite failure on CURATED_GENRES key count

**What goes wrong:** `test_curated_genre_prompt_layer_covers_phase_one_genres` in `tests/test_genre_dna.py` (line 32-46) asserts `set(CURATED_GENRES)` equals exactly 10 specific keys. Adding `deep_house` and `tech_house` expands the set to 12 — the test will fail with an assertion error.

**Why it happens:** The test was written to lock the Phase 0 genre set. It was not pre-updated for Phase 1.

**How to avoid:** Update the expected set in the test to include `"deep_house"` and `"tech_house"`. This is an intended update, not a regression.

**Warning signs:** CI/pytest run fails with `AssertionError: {'deep_house', 'tech_house'} != ...`.

### Pitfall 2: GENRE_REGISTRY vs. _RESOLVED_GENRE_REGISTRY naming collision

**What goes wrong:** If `GENRE_REGISTRY` is kept as a public name pointing to the old unresolved dict, callers that directly access `GENRE_REGISTRY["deep_house"]` get an unmerged entry (only child bass/lead patterns, missing parent's 3 patterns). AC-4 will fail.

**Why it happens:** Several test files and external code import `GENRE_REGISTRY` by name. Renaming breaks them.

**How to avoid:** Keep `GENRE_REGISTRY` as an alias pointing to `_RESOLVED_GENRE_REGISTRY` for backward compatibility. The internal `_BASE_GENRE_REGISTRY` holds the unresolved entries. Or expose `RESOLVED_GENRE_REGISTRY` as a separate public name per SPEC AC-4: `RESOLVED_GENRE_REGISTRY["deep_house"].bass_patterns` is the AC-4 test target.

**Warning signs:** `len(GENRE_REGISTRY["deep_house"].bass_patterns) < 5` after implementation.

### Pitfall 3: "tech house" detection ambiguity with "techno" keyword

**What goes wrong:** The phrase "dark house" or "peak-hour house" should resolve to `tech_house`. But if the `"techno"` check runs first, it catches `"techno house"`. If the `"house"` fallback runs first, `"tech house"` resolves to generic `"house"`.

**Why it happens:** `detect_style_from_text()` uses `if/elif` chain — order is decisive.

**How to avoid:** Insert sub-genre checks before line 1175 (current `"techno"` check). The `any(word in lowered ...)` check for "tech house" uses exact multi-word phrases, which are safe.

**Warning signs:** `detect_style_from_text("Create a tech house track")` returns `"house"` instead of `"tech_house"`.

### Pitfall 4: CSS tokens absent in app/page.tsx

**What goes wrong:** Genre cards render with no background color, no accent color on hover, broken borders. All `var(--accent)`, `var(--panel-strong)`, etc. are undefined.

**Why it happens:** `app/layout.tsx` currently imports no CSS. `web/styles.css` exists but is not wired into the Next.js app.

**How to avoid:** Add `import '../web/styles.css'` to `app/layout.tsx` (if the path resolves correctly from the Next.js app directory), or copy the `:root` token block to `app/globals.css` and import that.

**Warning signs:** Cards render with default browser white/black styling.

### Pitfall 5: genreId casing mismatch between UI and route.ts validation

**What goes wrong:** Card sends `genreId: "deep_house"` (snake_case). `route.ts` validates `body.genreId` against `GENRES[body.genreId]` where GENRES keys are camelCase (`deepHouse`). Validation fails with 400.

**Why it happens:** Python uses snake_case conventions; TypeScript/JS uses camelCase. The two registries evolved with different conventions.

**How to avoid:** Either (a) use camelCase in the genre card's data attribute matching TypeScript convention (`deepHouse`, `techHouse`), or (b) add snake_case aliases to the TypeScript GENRES object. Option (a) is cleaner.

**Warning signs:** `POST /api/finisher` returns `{ "error": "Invalid or missing genreId" }`.

### Pitfall 6: D-07 intro strategy breaks section-level determinism

**What goes wrong:** D-07 requires each generation to have a "different intro character". If the seed is derived from the prompt text, the same prompt always produces the same intro style — which is correct determinism. But if the seed is time-based or random, the same prompt produces different results on re-run, breaking test assertions.

**Why it happens:** Misunderstanding "different from last" as "different every run" vs. "different from other section types in the same sketch".

**How to avoid:** Use `sum(ord(c) for c in message) % 3` — deterministic per prompt text, but produces a different value for each unique prompt. The three seed values (0, 1, 2) map to the three intro styles. This matches the existing `_pattern_seed()` pattern.

**Warning signs:** Repeated calls to `expanded_song_sketch_plan("Create an expanded Deep House song sketch...")` produce different intro track compositions.

---

## Code Examples

### Resolving DEEP_HOUSE from its parent at module load

```python
# Source: SPEC.md §3.2 + inferred from genre_dna.py dataclass pattern
# [ASSUMED] import dataclasses needed for dataclasses.replace()
import dataclasses

def _resolve_genre(key: str, registry: dict[str, GenreDNA]) -> GenreDNA:
    child = registry[key]
    if not child.parent:
        return child
    if child.parent not in registry:
        return child
    if child.parent == key:
        raise ValueError(f"Circular parent: {key!r}")
    parent = registry[child.parent]
    return dataclasses.replace(
        child,
        bass_patterns=parent.bass_patterns + child.bass_patterns,
        lead_phrases=parent.lead_phrases + child.lead_phrases,
    )
```

### Verifying AC-4 (bass list extension)

```python
# AC-4: RESOLVED_GENRE_REGISTRY["deep_house"].bass_patterns has length >= 5
# (3 parent HOUSE patterns + 2 child DEEP_HOUSE patterns)
assert len(RESOLVED_GENRE_REGISTRY["deep_house"].bass_patterns) >= 5
```

### Genre card click routing (React)

```tsx
// Source: CONTEXT.md §Claude's Discretion + app/api/finisher/route.ts FinisherRequest type
// app/page.tsx
const [userInput, setUserInput] = useState('')
const [genreId, setGenreId] = useState('house')

function handleCardClick(promptTemplate: string, cardGenreId: string) {
  setUserInput(promptTemplate)
  setGenreId(cardGenreId)  // e.g. "deepHouse" | "techHouse"
}

// The existing submit handler posts { genreId, userInput } to /api/finisher
```

### _EDM_STYLES update in harmony.py

```python
# Source: harmony.py line 296-300 (verified)
_EDM_STYLES = {
    "house", "uk garage", "techno", "trance",
    "drum n bass", "jungle", "dubstep", "grime",
    "trap",
    "deep_house",   # ADD
    "tech_house",   # ADD
}
```

### Adding sub-genres to genre_words() in planner.py

```python
# Source: planner.py line 1253-1279 (verified)
# Add to genre_words() list so detect_style triggers expanded_song_sketch_plan():
def genre_words() -> list[str]:
    return [
        ...
        "deep house",    # ADD
        "tech house",    # ADD
        ...
    ]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat GENRE_REGISTRY dict | Flat dict (current) | — | Phase 1 adds depth-1 inheritance on top |
| GenreDNA has no parent field | Add `parent: str | None = None` | Phase 1 | Enables sub-genre inheritance |
| House catch-all at end of detect_style_from_text() | House catch-all still at end, sub-genres inserted before | Phase 1 | Sub-genre prompts correctly routed |
| app/page.tsx is 8-line stub | Full genre card section | Phase 1 | First user-facing UI for genre selection |

**Not deprecated:** Everything in Phase 0 (multi-bar variation, section-aware reharmonisation, transitions) is preserved as-is. Phase 1 builds on top of it.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `GrooveProfile` values for `"push"` profile: `position_jitter_ms=3.0`, `velocity_jitter=4`, `push_pull_per_subdivision=(-0.005, 0.0, -0.003, 0.0)` | Standard Stack / Pattern 2 | If wrong, groove will feel different from intended "tight, forward-leaning" character. Low audio risk — values are adjustable without API changes |
| A2 | D-07 intro strategy gating: "drums_reveal" = only drum tracks; "atmosphere" = only Chords/Pad/Ambience; "filtered" = all tracks but energy="intro" velocity | Architecture Patterns / Pattern 5 | If Jim expects a different split per strategy, sections will have wrong instrumentation. Easily tuned post-listening |
| A3 | `CURATED_GENRES` "laid_back" and `"push"` `swing_percent` ranges for CuratedGenreDNA (Deep House: 60-65, Tech House: 50-52) | Code Examples / Pattern 3 | If wrong, `build_curated_prompt_context()` will feed the LLM slightly incorrect swing range. Low impact on MIDI generation (swing_percent in CuratedGenreDNA is for LLM context only) |
| A4 | Genre card genreId convention: use camelCase (`"deepHouse"`, `"techHouse"`) matching TypeScript GENRES keys | Architecture Patterns / Pattern 6 | If snake_case is used instead, route.ts validation returns 400 until aliases are added to TypeScript GENRES |

---

## Open Questions (RESOLVED)

1. **Stylesheet wiring for app/page.tsx**
   - What we know: `app/layout.tsx` imports no CSS; `web/styles.css` holds all design tokens.
   - What's unclear: Whether `import '../web/styles.css'` will resolve correctly from `app/layout.tsx` given the Next.js app directory structure, or if a copy/import into `app/globals.css` is safer.
   - RESOLVED: Use `import '../web/styles.css'` in `app/layout.tsx`. The Next.js app directory is one level below the project root, so `../web/styles.css` correctly resolves to the `web/` sibling directory. If path resolution fails at build time, fall back to copying the `:root` block into `app/globals.css`.

2. **D-07 "filtered" intro — what exactly is filtered?**
   - What we know: CONTEXT.md D-07 says "(c) full but filtered". The existing `energy="intro"` in `genre_*()`functions already reduces velocity for all generators.
   - What's unclear: Whether "filtered" means "all tracks present, lower velocity only" (already handled by energy="intro") or "all tracks present plus an explicit low-pass filter action".
   - RESOLVED: "full but filtered" means all tracks play but non-drum tracks start at `energy=0.3` (low) via the existing energy parameter. No new action types are needed. The existing velocity reduction in all genre generators handles this when energy is set to 0.3 for non-drum tracks in the intro section.

3. **`RESOLVED_GENRE_REGISTRY` public name for AC-4**
   - What we know: SPEC AC-4 references `RESOLVED_GENRE_REGISTRY["deep_house"].bass_patterns`. This implies the resolved registry should be accessible by that exact name.
   - What's unclear: Whether the SPEC means this as a test-accessible module-level variable or just as prose shorthand.
   - RESOLVED: Expose as a module-level public alias: `RESOLVED_GENRE_REGISTRY = _RESOLVED_GENRE_REGISTRY` on the line immediately after `_RESOLVED_GENRE_REGISTRY` is built. This allows `from vibelton.genre_dna import RESOLVED_GENRE_REGISTRY` in tests and satisfies AC-4 exactly.

---

## Environment Availability

Step 2.6: No external dependencies beyond the project's own Python and Node.js runtimes. The Python test suite (`pytest`) and Next.js dev server (`npm run dev`) are verified present.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | genre_dna.py, tests/ | ✓ | 3.12.4 | — |
| pytest | tests/ | ✓ | 9.0.2 | — |
| Node.js / npm | app/page.tsx, next build | ✓ | (via package.json) | — |
| Next.js | app/ | ✓ | ^16.2.4 | — |

[VERIFIED: `python3 -m pytest --version`, `package.json`]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none — rootdir auto-detected |
| Quick run command | `python3 -m pytest tests/test_genre_dna.py -v` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPEC §3.1 | `GenreDNA` has `parent` field | unit | `python3 -m pytest tests/test_genre_dna.py -k "groove_profiles" -v` | ✅ (update existing) |
| SPEC §3.2 AC-4 | `deep_house` bass_patterns length >= 5 | unit | `python3 -m pytest tests/test_genre_dna.py -k "bass_list" -v` | ❌ Wave 0 |
| SPEC §3.3 AC-1 | Deep House BPM in [120, 124] | unit | `python3 -m pytest tests/test_genre_dna.py -k "deep_house_bpm" -v` | ❌ Wave 0 |
| SPEC §3.4 AC-2 | Tech House BPM in [127, 132] | unit | `python3 -m pytest tests/test_genre_dna.py -k "tech_house_bpm" -v` | ❌ Wave 0 |
| SPEC AC-3 | Deep House kick != Tech House kick | unit | `python3 -m pytest tests/test_genre_dna.py -k "kick_divergence" -v` | ❌ Wave 0 |
| SPEC §4 | `detect_style_from_text("Create a deep house track")` → `"deep_house"` | unit | `python3 -m pytest tests/test_genre_dna.py -k "detect_style" -v` | ✅ (update existing) |
| SPEC §4 | `detect_style_from_text("Create a tech house track")` → `"tech_house"` | unit | `python3 -m pytest tests/test_genre_dna.py -k "detect_style" -v` | ✅ (update existing) |
| SPEC §6 AC-5 | genre cards render in app/page.tsx | manual | npm run dev + visual check | N/A |
| SPEC §6 AC-6 | Cards readable without music knowledge | manual | Jim reads cold | N/A |
| SPEC §6 AC-7 | Listening gate | manual | Jim fills LISTENING_NOTES.md | N/A |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/test_genre_dna.py -v`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green + LISTENING_NOTES.md both PASS before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_genre_dna.py` — add `test_deep_house_bpm_range()` asserting `plan("Create a deep house track")` BPM in [120, 124]
- [ ] `tests/test_genre_dna.py` — add `test_tech_house_bpm_range()` asserting `plan("Create a tech house track")` BPM in [127, 132]
- [ ] `tests/test_genre_dna.py` — add `test_bass_list_extended_by_parent()` asserting `RESOLVED_GENRE_REGISTRY["deep_house"].bass_patterns` length >= 5
- [ ] `tests/test_genre_dna.py` — add `test_kick_pattern_divergence()` asserting Deep House kick != Tech House kick
- [ ] `tests/test_genre_dna.py` — UPDATE `test_curated_genre_prompt_layer_covers_phase_one_genres` expected set to include `"deep_house"` and `"tech_house"`

---

## Security Domain

No new authentication, session management, or data persistence is introduced in Phase 1. The genre card UI is a static read-only component that writes to a `<textarea>` state value. The `/api/finisher` endpoint already exists with its own input validation (`genreId` must exist in `GENRES`, `userInput` must be a string).

The only security-relevant addition: the genre card sets `userInput` from a hardcoded string constant (the prompt template from SPEC §5.1). This is not user-controlled input — it cannot introduce injection risks.

ASVS V5 Input Validation applies only to the existing `genreId` and `userInput` validation in `route.ts`, which already validates both fields. No new validation surface is added.

---

## Sources

### Primary (HIGH confidence)

- `vibelton/genre_dna.py` — GenreDNA dataclass, GROOVE_TEMPLATES, GENRE_REGISTRY, CURATED_GENRES, detect_style_from_text(), curated_sections_for_genre(), lookup_genre() — read in full
- `vibelton/planner.py` — expanded_song_sketch_plan(), genre_words(), STYLE_PALETTES — read in full
- `vibelton/actions.py` — genre_drums(), genre_bassline(), genre_lead(), genre_chords(), _pick_bar_pattern(), apply_groove() — read in full
- `vibelton/harmony.py` — _EDM_STYLES, plan_harmony() — read in full
- `app/page.tsx` — current 8-line stub — read in full
- `app/api/finisher/route.ts` — FinisherRequest type, genreId validation, GENRES reference — read in full
- `lib/genreDNA.ts` — TypeScript GENRES object and GenreDNA type — read in full
- `app/layout.tsx` — confirmed no CSS import
- `web/styles.css` — CSS token definitions (:root block)
- `tests/test_genre_dna.py` — current test assertions (especially `test_curated_genre_prompt_layer_covers_phase_one_genres`)
- `.planning/phases/01/01-SPEC.md` — locked requirements and data model
- `.planning/phases/01/01-CONTEXT.md` — locked decisions (D-01 through D-07)
- `.planning/phases/01/01-UI-SPEC.md` — CSS class reuse, component inventory, interaction contract

### Secondary (MEDIUM confidence)

- `package.json` — confirmed Next.js 16.2.4, React 19.2.5, TypeScript 6.0.3 [VERIFIED]
- `python3 -m pytest tests/ -v` output — all 46 tests passing at research time [VERIFIED]

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries verified from package.json and existing imports
- Architecture: HIGH — full codebase read; data model, planner, actions, harmony all examined
- Pitfalls: HIGH — verified from actual test assertions and code; not assumed
- D-07 intro strategy implementation: MEDIUM — mechanism identified, exact gating logic is Claude's discretion
- Groove profile values for "push": LOW — derived from SPEC description; exact numerics are Claude's discretion

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (stable codebase; no fast-moving external dependencies)
