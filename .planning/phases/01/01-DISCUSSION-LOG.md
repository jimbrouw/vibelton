# Phase 1: House Sub-Genre Expansion - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** 01-House Sub-Genre Expansion
**Areas discussed:** Card Grouping, Arrangement Sections

---

## Card Grouping

### Q1: How should sub-genres relate to their parent genre in the card UI?

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped under parent | "House" is a section header with Deep House, Tech House as cards underneath | |
| Flat grid, all equal | Independent cards in a flat grid alongside Techno, UKG, etc. | |
| Expandable parent card | "House" card click opens it to reveal sub-genre cards inside. Collapsed by default. | ✓ |

**User's choice:** Expandable parent card

### Q2: When House card is expanded, should generic "House" prompt still be available?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep generic House | Expanded view shows generic House + sub-genres | |
| Sub-genres only | Only Deep House and Tech House shown. Forces sub-genre choice. | ✓ |

**User's choice:** Sub-genres only

### Q3: For genres without sub-genres, clicking fires prompt directly or expandable?

| Option | Description | Selected |
|--------|-------------|----------|
| Direct click fires prompt | Non-parent genres are simple clickable cards. Different visual. | ✓ |
| All expandable, uniform look | Every genre card expands on click, even with just one option. | |

**User's choice:** Direct click fires prompt

### Q4: Animation for expand/collapse?

| Option | Description | Selected |
|--------|-------------|----------|
| Subtle slide-down | ~200ms slide-down animation. Feels polished. | ✓ |
| Instant toggle | Appear/disappear immediately. | |
| You decide | Claude picks simplest option. | |

**User's choice:** Subtle slide-down

---

## Arrangement Sections

### Q1: Deep House arrangement shape?

| Option | Description | Selected |
|--------|-------------|----------|
| Long groove sections | 112 bars. Hypnotic, patient, like Amapiano. | |
| Classic house with softer drops | 128 bars. Same as parent House. | |
| Extended intro/outro DJ format | 160 bars. Extra-long intro/outro for DJ mixing. | ✓ |

**User's choice:** Extended intro/outro DJ format

### Q2: Tech House arrangement shape?

| Option | Description | Selected |
|--------|-------------|----------|
| Relentless peak-hour | 120 bars. Short break, long drops. | |
| Techno-influenced long builds | 144 bars. Slow tension builds into long relentless peaks. | ✓ |
| Hybrid — short but punchy | 96 bars. Compact, punchy. | |

**User's choice:** Techno-influenced long builds

### Q3: Deep House intro elements?

| Option | Description | Selected |
|--------|-------------|----------|
| Drums only, slow reveal | Kick + hats first, bass enters bar 16, chords enter bar 24. | |
| Chords + atmosphere first | Pads/chords and ambient texture first, drums join at bar 16. | |
| Full but filtered | All elements play from bar 1 with heavy low-pass filtering that opens over 32 bars. | |

**User's choice:** "all can it randomise then so its not the same" — all three intro styles should be randomly selected per generation for maximum variety.

### Q4: Should randomisation apply to Tech House intros too?

| Option | Description | Selected |
|--------|-------------|----------|
| Randomise Tech House too | Both sub-genres get the 3-strategy random intro. | ✓ |
| Tech House always drums-first | Only Deep House gets randomised intros. | |

**User's choice:** Randomise Tech House too

---

## Claude's Discretion

- Card click behavior: how genre card clicks route to the plan API
- Groove profile numeric values for "laid_back" and "push"
- CuratedGenreDNA full entries for both sub-genres
- detect_style_from_text() keyword ordering

## Deferred Ideas

None — discussion stayed within phase scope
