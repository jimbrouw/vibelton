# Phase 1: House Sub-Genre Expansion - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Deep House and Tech House as sub-genres of House, using parent-pointer inheritance on GenreDNA. Deliver a Next.js genre card UI where users pick sub-genres without knowing genre vocabulary. Manual listening gate for acceptance.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**7 requirements are locked.** See `01-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `01-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- `vibelton/genre_dna.py`: parent-pointer inheritance mechanism + `DEEP_HOUSE` and `TECH_HOUSE` entries
- `vibelton/planner.py` / `vibelton/actions.py`: `detect_style_from_text()` extended to match new sub-genre names and vibe words
- `app/page.tsx`: clickable genre cards with pre-written prompt templates
- `LISTENING_NOTES.md`: acceptance gate document

**Out of scope (from SPEC.md):**
- Instrument loading / patch selection
- Automated evaluation / classification tests
- Any House sub-genres beyond Deep House and Tech House
- Changes to the Ableton Remote Script bridge

</spec_lock>

<decisions>
## Implementation Decisions

### Card Grouping (UI pattern)
- **D-01:** Expandable parent card — House card clicks to reveal sub-genre cards inside. Collapsed by default.
- **D-02:** Sub-genres only when expanded — no generic "House" fallback option. Expanding House shows Deep House and Tech House directly.
- **D-03:** Non-parent genres (Techno, UKG, Trap, etc.) are direct-click cards — one click fires the prompt. No expand behavior. Different visual from parent cards.
- **D-04:** Subtle slide-down animation (~200ms) for expand/collapse of sub-genre cards.

### Arrangement Sections
- **D-05:** Deep House uses extended intro/outro DJ format — `intro 32 → build 16 → main 32 → break 16 → main 2 32 → outro 32` (160 bars total). Extra-long intro/outro for DJ mixing.
- **D-06:** Tech House uses Techno-influenced long builds — `intro 16 → build 32 → peak 32 → reduction 16 → peak 2 32 → outro 16` (144 bars total). Slow tension builds into long relentless peaks.
- **D-07:** Randomised intro strategy — both Deep House and Tech House intros randomly select from 3 intro styles per generation: (a) drums-only slow reveal, (b) chords + atmosphere first, (c) full but filtered. Ensures each sketch has a different intro character.

### Claude's Discretion
- Card click behavior: Claude determines how genre card clicks route to the plan API, given the existing `/api/finisher` endpoint
- Groove profile values: Concrete `GrooveProfile` numeric entries for `"laid_back"` and `"push"` — derived from SPEC descriptions
- `CuratedGenreDNA` entries: Full entries for Deep House and Tech House following existing pattern, using section structures from D-05 and D-06
- `detect_style_from_text()` keyword ordering: Sub-genre keywords inserted before the `"house"` catch-all

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements
- `.planning/phases/01/01-SPEC.md` — Locked requirements, acceptance criteria, data model for parent-pointer inheritance, Deep House and Tech House field values

### Musical intelligence
- `MUSICAL_INTELLIGENCE_CRITIQUE.md` — Original critique defining the 14-point intelligence checklist, Phase 0/1/2 breakdown, and verification gate

### Codebase entry points
- `vibelton/genre_dna.py` — GenreDNA dataclass, GENRE_REGISTRY, CuratedGenreDNA, detect_style_from_text(), GROOVE_TEMPLATES
- `vibelton/actions.py` — `_pick_bar_pattern()` (bar variation engine), `genre_drums()`, `genre_bassline()`, `genre_lead()`
- `vibelton/harmony.py` — `plan_harmony()` with section-aware energy, `_EDM_STYLES` set
- `vibelton/planner.py` — `expanded_song_sketch_plan()`, `_build_section_transitions()`, `local_plan()`
- `app/page.tsx` — Current Next.js frontend (barebones, needs genre card UI)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GenreDNA` frozen dataclass: Add `parent: str | None = None` field. All existing genres have `parent=None` by default.
- `GROOVE_TEMPLATES` dict: Add `"laid_back"` and `"push"` entries alongside existing `"straight"`, `"mpc_58"`, etc.
- `CuratedGenreDNA` dataclass: Create entries for Deep House and Tech House following the exact same pattern as existing genres.
- `curated_sections_for_genre()`: Already parses structure tuples into `(name, bars, energy)` triples — new sub-genres work automatically.

### Established Patterns
- All GenreDNA entries are module-level frozen constants (e.g., `HOUSE = GenreDNA(...)`)
- `GENRE_REGISTRY` is a flat dict mapping lowercase names to GenreDNA instances — sub-genres need `"deep_house"` and `"tech_house"` keys
- `detect_style_from_text()` uses a priority chain of `if/elif` blocks — sub-genre checks must precede the generic `"house"` check
- `_pick_bar_pattern()` already handles multi-pattern selection per bar — concatenated bass/lead lists work transparently

### Integration Points
- `_EDM_STYLES` in `harmony.py` gates 2-chord drop behavior — sub-genre keys need adding
- `expanded_song_sketch_plan()` calls `curated_sections_for_genre()` for arrangement structure — new CuratedGenreDNA entries flow through automatically
- Randomised intro strategy (D-07) requires a new mechanism in `expanded_song_sketch_plan()` to vary which instruments play in intro sections

</code_context>

<specifics>
## Specific Ideas

- Deep House intros should feel like "arriving at a late-night club" — patient and atmospheric
- Tech House intros should build tension like Techno — relentless and machine-like
- Every generation should sound different from the last (randomised intro strategies, bar variation from Phase 0)
- Genre cards must work for users who know nothing about music — the card labels and descriptions carry all the context

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-House Sub-Genre Expansion*
*Context gathered: 2026-05-21*
