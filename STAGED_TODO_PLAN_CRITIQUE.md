# Critique of STAGED_TODO_PLAN.md

Date: 2026-04-30
Tone: deliberately blunt, as requested
Scope: structural and content issues. No code changes proposed here. A revised plan is in `STAGED_TODO_PLAN_V2.md`.

A note on the labels:
- [Inference] = reasoned from the plan + repo, not directly tested
- [Speculation] = a guess worth checking before acting
- [Unverified] = no source confirmed

---

## Top-line judgement

It's a checklist, not a plan.

240+ checkboxes, no priorities, no dates, no kill switches, no risk register, no definition of "done" for the listening tests. A real plan tells you what to drop when you slip. This document tells you what to do if everything goes perfectly. That's a wish list.

The structural skeleton is fine — Stage 1 → 5 → Immediate next → Open decisions. The problems are in *content placement* and *missing rigor*, not in section order. Below: 18 specific issues, ranked by how much damage each one causes if left in.

---

## P0 — these will bite you within two weeks

### 1. Two Remote Scripts in tree, neither marked canonical

**Lines 22-23.** `AbletonCopilot` handles `duplicate_track` and `mute_track`. `AbletonCopilotArranger` does not. Both are in the repo. The plan files this as Stage 1 task ("Decide whether `AbletonCopilot` or `AbletonCopilotArranger` is the canonical Remote Script") *and* as an Open Decision in §6 ("Which Remote Script should users install by default?").

Listing the same decision twice doesn't make it more decided. It guarantees both copies of the question rot in parallel. Pick one **before** any other Stage 1 work, freeze the other behind a `/legacy` directory or delete it. Every Finisher action you ship without that decision works on script A and breaks on script B.

**Fix:** elevate to a P0 hot-fix stage that runs *before* Stage 1. 1 hour of decision, 30 minutes of git move, done.

### 2. Open Decisions sit at the bottom of the document

**§6, lines 246-254.** Naming (Idea Engine, The Finisher), palette direction, mode gating, canonical script, listening-test references — these *gate* downstream work. They are listed last.

That tells me the document was written by walking through source files in order, not by ranking. If the name "Idea Engine" changes after Stage 2, every prompt template, every UI string, and every README example needs a sweep. Do it once, up front.

**Fix:** move §6 to §0. Resolve the script-canonical question and the two name questions before Stage 1 begins.

### 3. No deadlines anywhere

The original `IMPROVEMENTS_PLAN.md` had Iteration A by 2026-05-07, B by 05-21, etc. `STAGED_TODO_PLAN.md` deletes them. Without dates, the accountability scaffold collapses. Your own preferences explicitly call for upfront deadlines and ~90-minute checkpoints; the plan honours neither.

**Fix:** copy the deadline grid back in, or replace it with a more aggressive one if Stage 1 turns out to be smaller than expected. Either way, dates on the page.

### 4. No "stop work / kill switch" trigger per stage

What evidence would make you scrap Iteration C and double down on D? What would force a Stage 2 redesign? The plan doesn't say.

This is the difference between an agile plan and a religious one. If `music21` import latency is >300 ms in Stage 3 prep work, you need a fallback path *named in advance*, not invented at the moment of pain.

**Fix:** add a "Stop conditions" subsection under each stage. Two lines each is enough.

---

## P1 — these will erode quality if left

### 5. Exit criteria are code-shaped, not music-shaped

**Stage 2 exit, lines 178-183:** "Generated notes stay within valid MIDI bounds. Humanisation is deterministic for the same prompt unless explicit variation is requested. Listening notes identify which genres improved and which still need work."

The first two are unit-test conditions. The third is the only musical one and it's the vaguest of the three. The whole point of Iteration A is "stop sounding like a metronome." The exit gate should be: *N producers, blind-listen, A/B against reference, ≥X correct identifications.* As written, you can ship a stage by writing a sentence in `LISTENING_NOTES.md`.

**Fix:** define listening test rigor — minimum two outside ears, blind comparison, written note saying which generated loop fooled them.

### 6. Listening test "by whom?" is undefined

**Lines 104, 116.** "Add listening-test notes for at least three genres." "Add A/B listening notes against reference loops." Same hole as #5. If it's just you listening to your own work, confirmation bias makes the test meaningless.

**Fix:** name the panel up front. Two producer friends + you is fine. Bake it into the deadline math.

### 7. Stage 5 is sequenced too late

Stage 5 covers stock-device chains (`.adv`), reference-track ingestion, and SnapHost. The biggest single complaint about AI music tools is that the *sound* is generic, not the notes. Bundling 5 to 10 well-curated stock-device chains is a 2-3 day move that lifts perceived quality more than 6 weeks of harmony-engine work.

**Fix:** pull the first two `.adv` chain tasks (lines 130-131) forward into Stage 1.5 or fold into Stage 2. Defer SnapHost integration explicitly to V2 — it has its own PRD and its own product surface and crowding it into the tail of the Vibelton plan disguises its real cost.

### 8. Deterministic seed handling is in Stage 2, but Stage 2 onwards depends on it

**Line 174.** "Add deterministic seed handling so repeat prompts remain reproducible."

Every smoke test, every A/B comparison, every listening test downstream needs this. If it lands halfway through Stage 2, the listening tests run on Stage 1 with non-reproducible output. The signal is noisy and you can't tell what changed why.

**Fix:** move seed handling to Stage 1.

### 9. Magenta Groove license check is buried

**Line 99.** "Verify licensing before bundling any dataset-derived groove templates." This is a *blocker*, not a checklist item. If the license is unsuitable for redistribution, Iteration A's groove-template bundle disappears and you need a new sourcing plan.

**Fix:** make this a Stage 0 / pre-flight check. One afternoon, settle the question, then plan.

### 10. No risk / load-bearing assumptions register

The plan assumes:
- Live's API exposes automation writes (Stage 4 needs it).
- The file-queue bridge can carry `.adv` loading reliably (Stage 5).
- `music21` latency is acceptable in the planner (Stage 3).
- You can ship audio-derived groove templates legally (Stage 2).
- SnapHost can be built in the time available (Stage 5).

None of these are listed as risks. All five would change the plan if disconfirmed.

**Fix:** add a §0.5 "Load-bearing assumptions" section. If any one is wrong, downstream stages re-sequence.

### 11. No rollback or branch strategy

Plan touches the planner, the harmony engine, GenreDNA, the bridge, and the UI. Nothing about feature branches per stage, nothing about main staying releasable. For a project moving toward sale, that's fragile.

**Fix:** one paragraph naming the branching policy. e.g. one branch per stage, main always-runnable, listening test on the branch before merge.

---

## P2 — useful polish, not blocking

### 12. "Split mode-specific planner logic into clearer modules" is premature

**Line 87.** Two modes today (Idea Engine, Finisher). Splitting `idea_engine.py` and `finisher_tools.py` before a third use case lands is YAGNI. Keep the planner monolithic until it hurts.

**Fix:** drop, or defer to "consider after Stage 4."

### 13. "Route-level or payload-level mode metadata for future UI and analytics"

**Line 90.** Speculative scaffolding for analytics that don't exist. Don't build infrastructure for ghosts.

**Fix:** drop. Add when an actual analytics need lands.

### 14. The audit conflates local file state with GitHub PR state

**Lines 7-23.** Mixes "this file exists in the workspace" (stable, you control it) with "PR #1 is mergeable" (mutable, GitHub controls it). When PR #1 gets merged or rebased, half the bullets become stale and the doc looks rotted.

**Fix:** split into two subsections. Local Repo Audit + Remote PR Snapshot (with timestamp).

### 15. `humanize_groove` is described as "generic randomness" without verification

**Line 174.** "Replace generic `humanize_groove` randomness with profile-aware humanisation." That assumes the function is generic. The plan never reads the function to confirm. (My own `IMPROVEMENTS_PLAN.md` made the same mistake. Both should correct.)

**Fix:** read the function before assuming. One bullet of evidence in the audit.

### 16. Smaller Wins are buried

**Lines 140-145.** "Ship a curated example prompt library and generated demo sets" is probably the single highest-leverage onboarding move in the entire document. It sits as a one-liner in §3 Smaller Wins.

**Fix:** elevate to Stage 1. A weekend's work, demo material that ships with every release, immediate marketing material.

### 17. No feedback loop / telemetry, even local-only

When a generated loop feels wrong, where does that signal go? The plan has no answer.

**Fix:** add a one-paragraph "Add a thumbs-up / thumbs-down inline write to `events.jsonl`" task. One weekend. Compounds for the rest of the project's life.

### 18. No buddy-check / cadence beyond a single 90-min mention

You said up front you have accountability needs. The plan honours this with one bullet. That's not enough scaffolding for a multi-month build.

**Fix:** name a weekly cadence. Even "Friday 1700 — write a 5-line summary of progress + blockers, post it somewhere visible (Discord, mom, journal)" is better than nothing.

---

## Things the plan got right (don't change)

- Idea Engine vs Finisher product split is real and worth keeping.
- Two-mode UI is committed to in code already; the plan correctly preserves it.
- Deterministic local fallback when `OPENAI_API_KEY` is absent is a strong product principle and the plan keeps it.
- Stage 4 correctly defers unsupported automation/sidechain commands until bridge support is confirmed (lines 211-218). That's exactly the right discipline.
- "Defer unsupported routing, compression, sidechain, or automation commands until bridge support is confirmed" — this is the single best line in the document. It belongs in every iteration's exit gate, not just Stage 4.

---

## What "good" looks like

A plan I'd bet on:

1. Decisions resolved at the top, dated.
2. Load-bearing assumptions named.
3. Each stage: 4-7 tasks max, deadline, exit gate (with at least one *musical* gate, not just code), kill switch.
4. Branch policy and listening-test panel named once, applied everywhere.
5. The thing that ships value fastest (curated demos, stock-device chains) lives in Stage 1, not Stage 5.
6. SnapHost broken out as a parallel V2 product, not crammed into the V1 tail.
7. Total length: ~150 lines, not 250.

The revised version is in `STAGED_TODO_PLAN_V2.md`.

---

## One paragraph summary

The current plan is a thorough audit followed by a long checklist. It's not wrong, it's just not load-bearing — there are no dates, no kill switches, no listening-test rigor, and the highest-leverage moves (canonical script, demo library, stock-device chains) are buried under lower-leverage harmony work. Move decisions to the top, name your assumptions, get the demo loop and the canonical script settled in week one, and treat SnapHost as the V2 product it actually is.
