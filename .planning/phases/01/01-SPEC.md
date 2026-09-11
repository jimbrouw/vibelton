# Phase 01 SPEC — Vibelton v3 House Sub-Genre Expansion

**Status:** LOCKED  
**Phase:** 01  
**Written:** 2026-05-21  
**Prerequisite:** Phase 0 (multi-bar variation, section reharmonisation, transitions) is merged AND Jim has confirmed the output sounds less robotic via manual listening.

---

## 1. Goal

Extend Vibelton's music brain to produce genre-accurate output for two House sub-genres — **Deep House** and **Tech House** — that are sonically distinguishable from each other and from the existing generic `HOUSE` style. A user who knows nothing about music genre terminology must be able to trigger either sub-genre through pre-written prompt templates in the Next.js UI.

---

## 2. Scope Boundaries

### In scope
- `vibelton/genre_dna.py`: parent-pointer inheritance mechanism + `DEEP_HOUSE` and `TECH_HOUSE` entries
- `vibelton/planner.py` / `vibelton/actions.py`: `detect_style_from_text()` extended to match new sub-genre names and vibe words
- `app/page.tsx`: clickable genre cards with pre-written prompt templates (no genre vocabulary required from the user)
- `LISTENING_NOTES.md`: acceptance gate document (manual only)

### Out of scope
- Instrument loading / patch selection (Phase 2 concern)
- Automated evaluation / classification tests
- Any House sub-genres beyond Deep House and Tech House
- Changes to the Ableton Remote Script bridge

---

## 3. Data Model

### 3.1 Parent-pointer field on `GenreDNA`

Add an optional `parent: str | None = None` field to the `GenreDNA` frozen dataclass. The value is a key into `GENRE_REGISTRY` (e.g. `"house"`).

### 3.2 Inheritance merge rules

At module load time, `GENRE_REGISTRY` is built via `_resolve_genre(key)`:

| Field group | Merge behaviour |
|-------------|----------------|
| `bpm_range`, `swing`, `groove_profile` | **Child replaces parent** — child values overwrite entirely |
| `kick_patterns`, `snare_patterns`, `hat_patterns` | **Child replaces parent** — child owns all drum patterns; parent patterns are not used |
| `bass_patterns`, `lead_phrases` | **Child extends parent** — lists are concatenated (parent first, child appended); `_pick_bar_pattern()` selects across the full combined list |
| `chord_rhythm` | **Child replaces parent** |

Resolution is depth-1 only (no grandparent chains). Circular parents raise `ValueError` at load time. The resolved registry is cached in `_RESOLVED_GENRE_REGISTRY` at import time; no runtime merge cost.

### 3.3 Deep House entry (`DEEP_HOUSE`)

| Field | Value |
|-------|-------|
| `parent` | `"house"` |
| `bpm_range` | `(120, 124)` |
| `swing` | `0.62` (soulful shuffle — higher than parent 0.55) |
| `groove_profile` | `"laid_back"` |
| Kick patterns | 1 pattern: four-on-floor, with beat-3 ghost at velocity 55 (no double kick) |
| Snare patterns | 1 pattern: snare on 2 and 4 only, velocity 90–100, no ghost |
| Hat patterns | 2 patterns: (a) closed 8th-note, (b) open hat on upbeats |
| Bass patterns | 2 new patterns (sub-bass focused, octave drops on bar 3); parent's 3 patterns prepended |
| Lead phrases | 2 new phrases (slow, stepwise, Rhodes-style); parent's 2 phrases prepended |
| Chord rhythm | Whole-bar long tones (1 chord per bar, no arpeggiation) |
| `vibe_words` in `CuratedGenreDNA` | `["deep", "soulful", "late-night", "rhodes", "warm", "hypnotic", "jazzy"]` |
| `rule_breakers` in `CuratedGenreDNA` | `["add a #11 to the chord voicing", "drop the kick for 4 bars"]` |

### 3.4 Tech House entry (`TECH_HOUSE`)

| Field | Value |
|-------|-------|
| `parent` | `"house"` |
| `bpm_range` | `(127, 132)` |
| `swing` | `0.50` (tight, near-quantised) |
| `groove_profile` | `"push"` |
| Kick patterns | 1 pattern: four-on-floor, no ghost, hard velocity 110–127 on all beats |
| Snare patterns | 1 pattern: clap layer on beat 2 and 4, plus sidestick ghost on the "and" of 3 |
| Hat patterns | 2 patterns: (a) 16th-note closed, high velocity, (b) alternating open/closed 16ths |
| Bass patterns | 2 new patterns (tight rolling 16th-note riff, industrial distorted tone intent); parent's 3 patterns prepended |
| Lead phrases | 2 new phrases (short, staccato, minor 3rd motif); parent's 2 phrases prepended |
| Chord rhythm | 8th-note stabs (2 chords per bar, same chord alternating with silence) |
| `vibe_words` in `CuratedGenreDNA` | `["dark", "industrial", "techno-edge", "rolling", "minimal", "peak-hour", "pressure"]` |
| `rule_breakers` in `CuratedGenreDNA` | `["drop all chords, keep only kick and bass for 8 bars", "add a pitched LFO stab repeating every beat"]` |

---

## 4. Detection

`detect_style_from_text()` in `planner.py` is extended with keyword → style mappings:

```
"deep house", "soulful house", "late-night house", "rhodes house" → "deep_house"
"tech house", "techno house", "dark house", "industrial house", "peak-hour house" → "tech_house"
```

These mappings fire before the existing `"house"` catch-all so sub-genres take priority.

---

## 5. Next.js Genre Card UI

`app/page.tsx` gains a **Genre Cards** section above the existing content. Each card is a clickable button that fires the pre-written prompt template into the chat input (or the plan API — whichever the UI currently uses).

### 5.1 Card definitions

**Deep House**
- Label: `Deep House`
- Subline: `120–124 BPM · Soulful · Late-night`
- Description: `Slow, soulful, Rhodes-driven House. 120–124 BPM. Built for late-night dancefloors.`
- Prompt template: `Create an expanded Deep House song sketch with soulful chords, warm bassline, late-night groove, and jazzy lead phrases.`

**Tech House**
- Label: `Tech House`
- Subline: `127–132 BPM · Dark · Peak-hour`
- Description: `Dark, groove-locked House with a Techno edge. 127–132 BPM. Industrial textures and relentless kick pressure.`
- Prompt template: `Create an expanded Tech House song sketch with rolling bass, dark industrial textures, tight hi-hats, and relentless kick.`

### 5.2 UI constraints
- Cards must be usable by someone with zero music genre vocabulary — label, subline, and description must be self-explanatory
- No genre jargon without inline explanation in the description
- Clicking a card fires the prompt template without requiring the user to type anything

---

## 6. Acceptance Criteria

All criteria are binary pass/fail. Phase 1 is done when all pass.

| # | Criterion | Pass condition | Fail signal |
|---|-----------|---------------|-------------|
| AC-1 | Deep House BPM | `plan("Create a deep house track")["actions"]` contains `set_tempo` with `bpm` in `[120, 124]` | BPM is 128 (generic house) |
| AC-2 | Tech House BPM | `plan("Create a tech house track")["actions"]` contains `set_tempo` with `bpm` in `[127, 132]` | BPM is 128 |
| AC-3 | Kick pattern divergence | Deep House kick and Tech House kick have ≥1 different note position or velocity class across a 4-bar sequence | Identical kick patterns (primary fail signal) |
| AC-4 | Bass list extension | `RESOLVED_GENRE_REGISTRY["deep_house"].bass_patterns` has length ≥ 5 (3 parent + 2 child) | Length < 5 means merge failed |
| AC-5 | Card renders | `app/page.tsx` renders both genre cards; clicking either populates the prompt field | Card absent or click does nothing |
| AC-6 | No genre vocabulary required | Card label + description conveys the vibe without requiring music knowledge; confirmed by Jim reading cold | Jim needs to Google a term |
| AC-7 | Manual listening gate | Jim generates 1 Deep House sketch and 1 Tech House sketch, fills `LISTENING_NOTES.md`, and marks both as PASS | Either marked FAIL |

---

## 7. Out-of-Scope Clarifications

- **Instruments**: No instrument loading, patch selection, or rack recommendations. The `load_stock_instruments` action continues to use existing mappings.
- **Automated evaluation**: No classification model, no programmatic genre identification test. AC-3 is a unit assertion on note data, not a listening model.
- **Remaining 5 sub-genres** (Garage House, Afro House, Bass House, Disco House, Progressive House): Deferred to Phase 2.
- **Grandparent chains**: `DEEP_HOUSE.parent = "house"` only. If `HOUSE` ever gains a parent, resolution is still depth-1 and stops at `HOUSE`.

---

## 8. Open Questions (resolved)

| Question | Decision |
|----------|----------|
| Inheritance merge strategy | Drums + BPM: child replaces. Bass + lead: child extends (concatenate). |
| Scope of sub-genres | Deep House + Tech House only for Phase 1 |
| Instrument selection | Out of scope |
| Verification gate | Manual only — Jim signs off in `LISTENING_NOTES.md` |
| Genre discovery UX | Pre-written prompt templates in Next.js genre cards |
| Tech House card copy | "Dark, groove-locked House with a Techno edge. 127–132 BPM. Industrial textures and relentless kick pressure." |
| Module-load caching | Resolved registry cached in `_RESOLVED_GENRE_REGISTRY` at import; no runtime merge cost |
