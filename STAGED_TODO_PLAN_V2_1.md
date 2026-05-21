# Vibelton Build Plan V2.1

Date: 2026-04-30  
Status: replaces `STAGED_TODO_PLAN.md` as the working build plan  
Inputs read: `STAGED_TODO_PLAN_CRITIQUE.md`, `STAGED_TODO_PLAN_V2.md`, current repo files

[Unverified] This document contains confirmed repo facts plus labelled planning assumptions. Anything about Ableton Live runtime behavior, listening-panel results, licensing, or third-party tools remains unverified until tested.

## 0. Confirmed Snapshot

### Local repo

- [x] Confirmed: current work branch is `codex/v2-1-stage-0`.
- [x] Confirmed: `main` was created from updated `origin/main` after PR #1 merged.
- [x] Confirmed: PR #1 was merged on 2026-04-30.
- [x] Confirmed: PR #1 targets `main` from `initial-upload`.
- [x] Confirmed: PR #1 reports no status checks.
- [x] Confirmed: `STAGED_TODO_PLAN.md`, `STAGED_TODO_PLAN_CRITIQUE.md`, and `STAGED_TODO_PLAN_V2.md` are local-only.

### Code facts

- [x] Confirmed: `Vibelton` handles `duplicate_track` and `mute_track`.
- [x] Confirmed: `AbletonCopilotArranger` does not handle `duplicate_track` or `mute_track`.
- [x] Confirmed: `GenreDNA` still uses `swing: float`.
- [x] Confirmed: no `GrooveProfile` exists yet.
- [x] Confirmed: no `harmony.py` or `music21` integration exists yet.
- [x] Confirmed: `mutate_clones` uses a seeded random generator based on sibling index.
- [x] Confirmed: `humanize_groove` currently uses unseeded random timing and velocity jitter.
- [x] Confirmed: `add_ghost_notes` currently uses unseeded random note insertion and velocity.

## 1. Decisions First

Deadline: 2026-05-04. Do these before feature work.

| ID | Decision | V2.1 default | Due |
|---|---|---|---|
| D1 | Canonical Remote Script | Use `Vibelton` | 2026-05-01 |
| D2 | Non-canonical script handling | Move `AbletonCopilotArranger` to `legacy/` with a freeze note | 2026-05-01 |
| D3 | Mode names | Keep `Idea Engine` and `The Finisher` through Stage 2 | 2026-05-04 |
| D4 | Palette | Done: default high-contrast dark mode; Finisher uses warm dark mode | 2026-05-04 |
| D5 | Listening panel | Jim plus two producer friends | 2026-05-04 |
| D6 | Branch policy | One branch per stage, `main` runnable, PR per stage | 2026-05-01 |
| D7 | Groove licensing | Source checked; use CC BY 4.0 attribution if deriving from Magenta Groove | 2026-05-04 |
| D8 | PR #1 handling | Done: PR #1 merged before Stage 0 branch | 2026-05-01 |

Stop condition:

- If D1, D2, D7, or D8 is unresolved by 2026-05-04, pause feature work and finish decisions.

## 2. Load-Bearing Assumptions

| ID | Assumption | Label | Mitigation if false |
|---|---|---|---|
| A1 | Live 12 exposes the arrangement or clip automation APIs needed for Stage 4 | [Unverified] | Ship section arrangement without automation; document automation as deferred |
| A2 | Browser or file paths can load `.adv` chains reliably | [Unverified] | Ship manual chain-load workflow with `device_chains.json` |
| A3 | Optional `music21` can stay below the Stage 3 latency target | [Unverified] | Use hand-rolled voice-leading and keep `music21` optional |
| A4 | Magenta Groove can be redistributed with attribution | [Unverified] | Use hand-made or clearly licensed grooves |
| A5 | Sound identity matters earlier than harmony depth for perceived quality | [Inference] | Pull stock-device chains into Stage 1.5 before harmony |
| A6 | SnapHost is a separate build track | [Inference] | Do not block Vibelton V2.1 on SnapHost |

## 3. Branch And Release Policy

- Branch from updated `main` after PR #1 lands.
- Use branch names like `codex/v2-1-stage-0`, `codex/v2-1-stage-1`, etc.
- Keep each branch small enough to review in one sitting.
- Each stage PR must include: smoke-test result, code-test result, and a short `LISTENING_NOTES.md` entry when the stage has a listening gate.
- Do not queue unsupported bridge actions silently. If an action cannot be executed by the canonical bridge, either add bridge support in that stage or mark the feature deferred.

## 4. Stage 0: Hot Path Stabilisation

Deadline: 2026-05-04  
Goal: one canonical bridge, repeatable smoke test, decisions recorded.

Build tasks, in order:

1. [x] Merge PR #1 or otherwise make `main` the current project baseline.
2. [x] Create `codex/v2-1-stage-0` from updated `main`.
3. [x] Move `ableton_remote_script/AbletonCopilotArranger/` to `legacy/AbletonCopilotArranger/`.
4. [x] Add `legacy/AbletonCopilotArranger/README.md` with freeze date and reason.
5. [x] Update `install_remote_script.py` and README references so users install only `Vibelton`.
6. [x] Add `SMOKE_TEST.md` with exactly five prompts:
   - set tempo and start playback
   - create house drums
   - create Am-F-C-G chords
   - create an expanded house song sketch
   - run a Finisher humanise or ghost-note action
7. [x] Add `LICENSE_AUDIT.md` with the D7 decision.
8. [x] Add `LISTENING_NOTES.md` skeleton.

Exit gate:

- [x] Canonical script decision is visible in repo structure.
- [x] Installer and README point to one script.
- [x] Smoke-test doc exists and has five prompts.
- [x] Python compile passes.
- [x] User-reported smoke test passed on 2026-04-30.

Stop condition:

- If the canonical script cannot run the Finisher prompt, Stage 0 expands to repair bridge parity before Stage 1.

## 5. Stage 1: Demo-Ready App

Deadline: 2026-05-11  
Goal: make the current app understandable, repeatable, and demoable before deeper music work.

Build tasks, in order:

1. [x] Lock mode names and palette in README and UI copy.
2. [x] Add deterministic planner seed handling at the top of generation flow.
3. [x] Make `humanize_groove` and `add_ghost_notes` accept seeded randomness.
4. [x] Add `tests/test_action_support.py` so planner-emitted action types are checked against canonical bridge handlers.
5. [x] Add prompt smoke tests for the five `SMOKE_TEST.md` prompts.
6. [x] Add thumbs-up / thumbs-down UI feedback that appends a structured event line.
7. [x] Add `demos/` with 10 curated prompts.
8. [x] Add demo artifact placeholders first if `.als` and audio renders are not ready, then fill them as Ableton renders are made.
9. [x] Update README with current setup, known limits, and demo instructions.
10. [x] Add `FINISHER_SMOKE_TEST.md` for focused The Finisher checks.

Exit gate:

- Action-support test passes.
- [x] The five smoke prompts produce action plans without unsupported action types.
- [x] README smoke flow is working, based on user report on 2026-05-01.
- [x] 10 demo prompts have user smoke-test notes in `LISTENING_NOTES.md`.
- Finisher smoke test has been run in Ableton and notes added to `LISTENING_NOTES.md`. [Unverified until tested]

Stop condition:

- If fewer than two demo prompts sound usable to Jim, move immediately to Stage 1.5 before more planner work.

90-minute checkpoint:

- Run the five smoke prompts and write the three biggest rough edges in `LISTENING_NOTES.md`.

## 6. Stage 1.5: Sound Chains

Deadline: 2026-05-18  
Goal: improve audio identity before deeper MIDI intelligence.

Build tasks, in order:

1. [x] Create `device_chains.json` schema: role, genre family, energy, file path, manual-load notes.
2. [x] Curate 15 starter Ableton-native chain targets:
   - house/techno: kick, bass, pad, lead, keys
   - hip-hop/lo-fi: kick, bass, pad, lead, keys
   - DnB/UKG: kick, bass, pad, lead, keys
3. [x] Add chain references or placeholders under `device_chains/`.
4. [ ] Test whether the bridge can load a chain reliably. [Unverified until Live test]
5. [x] If bridge loading is unreliable, document manual loading and keep moving.
6. [ ] Re-run demos with chains and update `LISTENING_NOTES.md`.

Exit gate:

- `device_chains.json` parses.
- Manual chain-load workflow is documented.
- At least 7 of 10 demos have a chosen chain set or documented placeholder.

Stop condition:

- If chain loading burns more than one day without a reliable path, ship manual-load-only for V2.1.

## 7. Stage 2: Humanisation And Groove

Deadline: 2026-06-01  
Goal: drums and bass feel less rigid without losing genre identity.

Build tasks, in order:

1. [x] Add `GrooveProfile` dataclass.
2. [x] Replace `swing: float` with `groove_profile` across all `GenreDNA` entries.
3. [x] Preserve existing genre patterns during migration.
4. [x] Add six groove templates based on D7 outcome.
5. [x] Add role velocity curves.
6. [x] Add seeded bar-to-bar drum mutation.
7. [x] Make Finisher humanisation profile-aware.
8. [x] Add tests for bounds, determinism, and profile migration.
9. Run listening test: 5 loops x 3 genres against reference loops.

Exit gate:

- MIDI bounds tests pass.
- Same prompt and same seed produce same output.
- Listening panel cannot identify the generated loop at least 50% of the time. [Unverified until tested]

Stop condition:

- If migrated grooves make more than two genres sound worse in panel notes, reduce jitter ranges and retest before adding templates.

90-minute checkpoint:

- Drums-only blind A/B for house, UKG, and hip-hop.

## 8. Stage 3: Harmony And Melody

Deadline: 2026-06-22  
Goal: chords and melodies feel intentionally chosen.

Build tasks, in order:

1. [x] Add `harmony.py` with no hard dependency on `music21`.
2. [x] Add optional lazy-loaded `music21` path.
3. [x] Add fallback voice-leading path.
4. [x] Add genre-weighted progression models.
5. [x] Add inversion selection.
6. [x] Add colour knob parsing: neutral, moody, cinematic, jazzy.
7. [x] Add melody contour, rest density, and phrase-ending rules.
8. [x] Add tests with `music21` absent.
9. Run listening test against Stage 2 output.

Exit gate:

- Planner still works without `music21`.
- Typical local planner prompt completes under 1 second. [Unverified until measured]
- Listening panel misidentifies generated loops at least 40% of the time. [Unverified until tested]

Stop condition:

- If `music21` adds more than 300 ms warm latency, keep it out of the default path.

90-minute checkpoint:

- Compare one generated progression against Captain Chords or Scaler and write the difference in `LISTENING_NOTES.md`.

## 9. Stage 4: Arrangement

Deadline: 2026-07-13  
Goal: full arrangements read as songs, not stacked loops.

Build tasks, in order:

1. [x] Reframe The Finisher around existing Session View loops, non-destructive Arrangement View copying, and optional track renaming.
2. Add conversational Finisher flow: ask genre, target length, energy arc, reference structure, and whether Arrangement View already contains material.
3. Add `arrangement_templates/*.json` schema.
4. Add three templates per genre family.
5. Add parser and validator.
6. Replace hard-coded section helpers with template lookup.
7. Add section-aware mutation: rests, fills, density, register shifts, hook re-entry.
8. Add default mix staging using already supported bridge actions.
9. Probe automation support.
10. Probe existing Arrangement View edit support.
11. Add automation only for confirmed bridge-supported paths.
12. Add optional `rename_tracks_from_devices` workflow for generic track names.

Exit gate:

- A full-song prompt produces section names, bar lengths, and start positions matching JSON.
- No unsupported action is silently queued.
- The Finisher can copy existing Session View loops into Arrangement View without deleting Session View clips. [Unverified until tested]
- Panel verdict: one 3-minute arrangement is mixable in under 30 minutes. [Unverified until tested]

Stop condition:

- If automation support is not confirmed within one day, defer automation and ship arrangement plus mix staging.

## 10. Stage 5: Reference Tracks And Polish

Deadline: 2026-08-03  
Goal: add producer-grade onboarding and one clear workflow differentiator.

Build tasks, in order:

1. Add Vibelton history view from recent prompt and outcome events.
2. Add suggest-only mode based on `state.json`.
3. Design reference-track ingestion before coding it.
4. Add optional BPM/key analysis path.
5. Test three audio inputs.
6. Write competitor/reference memo with only measured claims.
7. Update README and PRD with V2.1 actual capabilities.

Exit gate:

- History view shows last 10 prompts and outcomes.
- Suggest-only mode gives at least three useful suggestions on a typical session. [Unverified until tested]
- Reference-track flow works on three test files or is clearly marked experimental.

Stop condition:

- If audio analysis adds brittle install requirements, put it behind an experimental flag.

## 11. SnapHost Track

[Inference] SnapHost is not part of the V2.1 critical path.

- Keep SnapHost in `SNAPPY_HOST_PRD.md`.
- Add only a thin future-facing `snaphost_client.py` design note after Vibelton Stage 4.
- Do not block V2.1 on JUCE, plugin hosting, or morphing work.
- First separate SnapHost milestone: empty VST3 host builds and loads by 2026-09-01. [Speculation]

## 12. Weekly Cadence

- Friday 17:00: write five lines: shipped, slipped, blockers, next target, one listening note.
- Mid-stage: 90-minute checkpoint with one blind-listen note.
- Stage end: smoke test, code tests, listening note, then PR.
- If two weekly updates show no shipped work, halve the next stage scope before adding new tasks.

## 13. V2.1 Build Order

1. Merge PR #1.
2. Stage 0: canonical bridge and smoke test.
3. Stage 1: deterministic demo-ready app.
4. Stage 1.5: stock-device sound chains.
5. Stage 2: groove and humanisation.
6. Stage 3: harmony and melody.
7. Stage 4: arrangement.
8. Stage 5: reference tracks and polish.
9. SnapHost stays parallel.
