# Vibelton Staged Plan — V2

Date: 2026-04-30. Replaces `STAGED_TODO_PLAN.md`. Critique of V1 lives in `STAGED_TODO_PLAN_CRITIQUE.md`.

[Inference] effort estimates assume one engineer-musician working evenings + weekends. Halve them for full-time.

A note on labels:
- [Inference] = reasoned, not directly tested
- [Speculation] = guess worth checking
- [Unverified] = no source confirmed

---

## §0. Decisions to make this week (deadline: 2026-05-04)

These gate everything downstream. Resolve before any code work.

| # | Decision | Default if unsure | Owner | Due |
|---|---|---|---|---|
| D1 | Canonical Remote Script | `AbletonCopilot` (older, has duplicate/mute) | Jim | 05-01 |
| D2 | Move the other Remote Script | `/legacy/AbletonCopilotArranger/` with a `README.md` saying "frozen on YYYY-MM-DD" | Jim | 05-01 |
| D3 | Final mode names | Keep "Idea Engine" and "The Finisher" | Jim | 05-04 |
| D4 | Final UI palette direction | Keep current muted-beige; revisit after Stage 2 | Jim | 05-04 |
| D5 | Listening-test panel | Jim + 2 producer friends, blind A/B against reference loop | Jim | 05-04 |
| D6 | Branch policy | One branch per stage, main always-runnable, listening test on branch before merge | Jim | 05-01 |
| D7 | Magenta Groove license suitability for redistribution | Read CC-BY 4.0 attribution requirements; if unsuitable, swap to hand-recorded grooves | Jim | 05-04 |

Until D1, D2, D7 are resolved, do not start Stage 1.

---

## §0.5. Load-bearing assumptions

If any of these turn out to be wrong, downstream stages re-sequence.

| # | Assumption | Probability OK [Inference] | Mitigation if wrong |
|---|---|---|---|
| A1 | Live 12 API exposes automation envelope writes from a Remote Script | medium | Stage 4 ships clip-level automation only (clip envelopes), not arrangement automation |
| A2 | File-queue bridge can carry `.adv` loading reliably | low-medium | Stage 5 reduces to documented manual chain-load workflow |
| A3 | `music21` import latency in the planner is <300 ms | medium-high | Stage 3 keeps `music21` strictly server-side, lazy-loaded, with fallback path |
| A4 | Magenta Groove dataset is redistributable under CC-BY 4.0 with attribution | medium | Stage 2 swaps to grooves recorded by Jim or sourced from a clearly-licensed alternative |
| A5 | SnapHost is a 2-3 month parallel build, not a Stage 5 sub-task | high | Already mitigated: this plan defers SnapHost to V2 |
| A6 | Audio-feel issues outweigh harmony-feel issues for perceived "AI slop" | high | Stage 1.5 ships stock-device chains regardless |

---

## §1. Stage 0 — Hot fix (deadline: 2026-05-04)

Goal: one canonical Remote Script, decisions documented, smoke test in place.

- [ ] Move non-canonical Remote Script to `/legacy/`. Commit message references D1.
- [ ] Add a 30-line `SMOKE_TEST.md` describing exactly the 5 prompts to run after every stage. (e.g. "Set tempo 124, make house drums, generate Am-F-C-G chords, finish with humanise + ghost notes, save .als.")
- [ ] Run the smoke test on a fresh Live install to confirm a working baseline.
- [ ] Decide D7 (Magenta Groove license).
- [ ] Add `LISTENING_NOTES.md` skeleton with one row per stage.

Exit gate:
- One Remote Script in tree under the canonical name, the other in `/legacy/`.
- 5-prompt smoke test runs end-to-end without manual intervention.
- License decision (D7) recorded in `LICENSE_AUDIT.md`.

Stop conditions:
- If the smoke test reveals a bridge regression, stop and fix before Stage 1.

---

## §2. Stage 1 — Stabilise + ship the demo loop (deadline: 2026-05-11)

Goal: the *user-visible polish* that costs the least and signals the most.

- [ ] Resolve D3 + D4 decisions in code (mode names final, palette frozen for now).
- [ ] Update `README.md` to match what the app actually does. Drop "Snowball from zero" placeholder if D-day naming changes.
- [ ] Add deterministic seed handling at the planner level. Every prompt becomes reproducible unless the user explicitly asks for variation. (Without this, every downstream listening test is noisy.)
- [ ] Action-support test: `tests/test_action_support.py` checks every action type the planner emits is in the canonical bridge's handler dict. Fail loud.
- [ ] Add a thumbs-up / thumbs-down button to the chat UI; writes a line into `events.jsonl`. One weekend's work. Compounds.
- [ ] Ship `demos/` directory: 10 prompts + 10 `.als` files + 10 30-second renders. Curated, not generated. This is the single highest-leverage marketing asset.
- [ ] Add a "Known limits" section to the README covering unsupported device insertion and unverified Live browser-loading behaviour.

Exit gate:
- A producer who has never seen Vibelton can install, follow the README, and reproduce demo #1 in <10 minutes.
- The action-support test passes.
- Smoke test still green.
- 5 of the 10 demos pass a blind A/B with the listening panel (D5) — i.e. at least 1 panel member can't immediately spot the AI demo against a reference.

Stop conditions:
- If <2 of 10 demos pass blind A/B, stop and back-fill stock-device chains (Stage 1.5) before Stage 2.

---

## §3. Stage 1.5 — Sound chains (deadline: 2026-05-18)

Goal: the *audio*, not just the notes, sounds like the genre. Pulled forward from V1's Stage 5 because perceived "AI slop" is mostly an audio problem.

- [ ] Curate 15 stock-device chains (`.adv`) covering kick, sub, lead, pad, keys × 3 genre families (house/techno, hip-hop/lo-fi, DnB/UKG).
- [ ] Map each chain to {role, genre, energy} in `device_chains.json`.
- [ ] Document the manual load workflow if A2 fails. Even "drag this `.adv` from the browser to the track" instructions are valuable; automate later.
- [ ] Re-run blind A/B on demos with chains loaded. Update `LISTENING_NOTES.md`.

Exit gate:
- ≥7 of 10 demos pass a blind A/B with the panel.
- `device_chains.json` parses and the manual-load README step works.

Stop conditions:
- If chain loading via the bridge proves unreliable in Live, ship as manual-load-only and move on. Don't sink a week into bridge work here.

---

## §4. Stage 2 — Humanisation and groove (deadline: 2026-06-01)

Goal: drum and bass MIDI feel less metronomic.

- [ ] Replace `swing: float` on `GenreDNA` with `groove_profile: GrooveProfile` covering position jitter, velocity jitter, length jitter, weak-beat curve, push/pull per subdivision.
- [ ] Migrate every existing genre profile (do not lose existing patterns).
- [ ] Bundle 6 groove templates per D7's outcome (Magenta Groove if redistributable, otherwise hand-recorded by Jim).
- [ ] Per-role velocity curves replacing flat velocity ranges. Hats: strong-weak-mid-weak; kicks: ramp into bar 4 fills; etc.
- [ ] Probability-based bar-to-bar drum mutation (90/70/fill at bar 4).
- [ ] Profile-aware humanisation in `humanize_groove` (read it first to confirm what's actually there).
- [ ] Listening test, written notes for ≥3 genres.

Exit gate (musical, not just code):
- Listening panel (D5) blind-listens 5 generated 8-bar loops × 3 genres against reference loops; ≥50% of the time the panel cannot tell which is generated.
- All notes within MIDI range, regardless of jitter.
- Smoke test still green.

Stop conditions:
- If the `groove_profile` migration breaks >2 genre profiles, stop and stabilise before adding new templates.
- If the listening panel says it sounds *worse* than V1 (more "trying too hard"), pull back jitter ranges.

90-min checkpoint: end of week 1, drums-only blind A/B. Note which genres still fail.

---

## §5. Stage 3 — Harmony and melody (deadline: 2026-06-22)

Goal: chord progressions and melody phrases feel chosen, not stamped.

- [ ] `harmony.py` module, `music21` as optional dependency, fallback path when not installed. Lazy-load to honour A3.
- [ ] Genre-weighted progression model (Markov over Roman numerals, hand-built from genre conventions, not scraped).
- [ ] Voice-leading minimisation pass on chord pitches.
- [ ] Inversion selection.
- [ ] `colour: "neutral" | "moody" | "cinematic" | "jazzy"` knob exposed in chat.
- [ ] Phrase-shape pass for melody: contour, rest density per energy level, chord-tone landings on phrase ends.
- [ ] Listening test against 3 reference tracks per genre.

Exit gate:
- Listening panel blind-tests 5 generated 8-bar loops; ≥40% misidentify which is the AI loop.
- Code still runs and tests still pass with `music21` *uninstalled*.
- Planner latency end-to-end <1s for typical prompts.

Stop conditions:
- If `music21` lazy-load adds >300 ms even when warm, drop it and ship hand-rolled voice leading.
- If listening tests show no improvement vs Stage 2, debug instead of adding D-knobs.

90-min checkpoint: end of week 1, after voice-leading lands. Compare a chord progression to the same prompt run through Captain Chords or Scaler.

---

## §6. Stage 4 — Arrangement (deadline: 2026-07-13)

Goal: 3-minute arrangement reads as a song, not a sketch.

- [ ] `arrangement_templates/*.json` schema. 3 templates per genre family.
- [ ] Arrangement template parser + validator.
- [ ] Section-aware mutation in the Arranger pass (rests, fills, hat-density envelopes, register shifts).
- [ ] Clip-level automation (filter cutoff opens through builds, sidechain depth, reverb send rises into breakdowns) — clip envelopes only if A1 fails.
- [ ] Default mix staging (kick -8 dB, snare -10, sub -10, mid bass -14, pads -16, lead -12, FX -18) emitted with every sketch.
- [ ] Defer any unsupported automation/sidechain commands until the bridge supports them. Do not silently queue.

Exit gate:
- A 3-minute arrangement is mixable in <30 minutes of human work to release-ready (panel verdict).
- Section names, bar lengths, and start positions in Live match the template JSON.
- No queued action is silently unsupported.

Stop conditions:
- If A1 turns out false (no automation writes), pull back to clip envelopes only and document what's deferred to V1.5.

---

## §7. Stage 5 — Reference tracks + polish (deadline: 2026-08-03)

Goal: producer-grade onboarding and one differentiator competitors don't have.

- [ ] Reference-track ingestion: drag audio into chat, BPM/key detection via `librosa`, lock generation to it.
- [ ] Suggest-only mode: chat suggests next moves based on `state.json`, doesn't generate. (DeSantis Strategy 1.)
- [ ] Vibelton history view: last 10 prompts + outcomes. Reads `events.jsonl`.
- [ ] Final memo against the competitor set (VIXSOUND, Scaler, Captain, Magenta, Orb). Update marketing copy with what's measurable.

Exit gate:
- Reference-track flow works end-to-end on 3 different audio inputs.
- Suggest-only mode produces ≥3 useful suggestions on a typical session.
- Memo identifies 2-3 things still missing and the size of those gaps.

Stop conditions:
- If `librosa` adds an ffmpeg dependency that breaks the install, gate reference-track behind a flag.

---

## §8. SnapHost — separate V2 track

SnapHost has its own PRD (`SNAPPY_HOST_PRD.md`) and is a 2-3 month JUCE/C++ build. Crowding it into a Vibelton stage hides its real cost.

Treat as parallel work:
- Reachable from Vibelton chat via `snaphost_client.py` once the SnapHost host exists and exposes its localhost API.
- Don't block any Vibelton stage on SnapHost progress.
- First SnapHost milestone target: 2026-09-01 (empty VST3 builds and loads). [Inference] aggressive but achievable solo.

---

## §9. Cadence and accountability

Per Jim's stated needs.

- Weekly: Friday 17:00, write a 5-line update — what shipped, what slipped, blockers, next-week target. Post somewhere visible (Discord, journal, partner).
- Mid-stage: 90-minute checkpoint at the rough midpoint of every stage. Specific instruction: blind-listen current build, write 3 lines.
- Stage end: smoke test + listening panel + write `LISTENING_NOTES.md` row. Don't mark the stage done in this file until the row exists.
- If two consecutive weekly updates report no shipped work, halve the next stage's scope before the third Friday.

---

## §10. What this plan deliberately does *not* do

To stay honest:
- Does not split the planner into `idea_engine.py` / `finisher_tools.py`. Premature with two modes. Revisit if a third mode lands.
- Does not add analytics-style mode metadata. No analytics today.
- Does not make any commercial claims about competitor parity until the panel A/B in Stage 5 backs them up.
- Does not bundle Magenta Groove without resolving D7. If unsuitable, swap groove sources.
- Does not promise SnapHost in V1.

---

## §11. Immediate next steps (this week)

1. Resolve D1, D2, D7. (~half day)
2. Move the non-canonical Remote Script to `/legacy/`.
3. Write the 5-prompt `SMOKE_TEST.md` and run it.
4. Skim `humanize_groove` to confirm what's actually there before Stage 2 plans against it.
5. Identify the 2 producer friends for the listening panel and ask them.

After step 5, Stage 1 starts.

---

## §12. One paragraph summary

V1's plan was an audit + a 240-checkbox wish list with no dates, no kill switches, and the highest-leverage moves buried at the back. V2 puts decisions at the top (canonical script, license check, panel), names the load-bearing assumptions, pulls demo loops and stock-device chains forward into weeks 1-2 because perceived AI-slop is mostly audio, defers SnapHost to a parallel V2 track where it belongs, and gates every stage on a *musical* exit criterion (panel A/B), not just a code one. Total length: ~150 lines, deadlines on every stage, kill switches on every stage, accountability cadence baked in.
