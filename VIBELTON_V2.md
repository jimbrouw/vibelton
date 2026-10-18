# Vibelton V2

## Purpose

Build Vibelton V2 as an **AI production assistant for Ableton Live**, not an autonomous musician. It should help a person who already has ideas, loops, and taste move from a promising sketch to a finished, release-ready track—without requiring them to become an expert in every production technique.

The human remains the musical director and final judge. Vibelton should take on repeatable production mechanics, session organisation, measurable audio problems, structured choices, and safe execution in Ableton.

The intended product promise is:

> I have the tune. Help me finish it.

V2 must not be a generic chat interface that happens to click around Ableton. It should turn a small number of high-level musical outcomes into an explicit plan and then use deterministic bridge operations to carry that plan out safely.

## Non-negotiable implementation rules

1. **Audit before changing anything.** Do not begin by adding a new architecture or features. First map the existing Vibelton repository, bridge capabilities, data model, Ableton integration, tests, commands, and current user flows.
2. **Preserve working code.** Extend the current project where practical. Do not replace functioning bridge or theory functionality merely because a different architecture seems cleaner.
3. **Use deterministic Ableton actions for execution.** The model should decide *what outcome to pursue*; typed, validated bridge commands should create tracks, move clips, set routing, alter devices, render previews, and so on.
4. **Use local analysis before expensive intelligence.** Obtain project facts and audio measurements locally. Only ask a model to interpret a concise diagnostic packet, make a plan, or explain trade-offs.
5. **Operate non-destructively by default.** Every meaningful batch of edits needs a named snapshot, clear before/after summary, A/B path, and rollback.
6. **Keep the person in control.** Never silently rewrite a song, commit a mix decision, or claim that a result is better. Offer bounded alternatives, explain them in plain language, and let the user choose.
7. **Build against one real benchmark track first.** Use one genuinely unfinished Vibelton user's track as the initial end-to-end test. The target is useful progress on that track, not a large feature checklist.

## V2 position and boundaries

### What Vibelton should do well

- Translate outcome-led requests into a production plan.
- Inspect an Ableton set for tracks, clips, devices, routing, automation, section density, repetition, and obvious conflicts.
- Organise session housekeeping: names, colours, groups, buses, sends, return tracks, locators, routing, and Song Sketch-friendly labels.
- Use genre knowledge as reusable structured data: BPM ranges, roles, section shapes, energy arcs, transition conventions, and arrangement variants.
- Turn existing loops into arrangements while preserving the core material.
- Identify measurable low-end, gain-staging, masking, dynamics, stereo, clipping, and headroom issues.
- Prepare reversible sidechain, mix, and master options that can be heard and compared.
- Teach through decisions: describe production changes as musical outcomes such as **subtle**, **tight**, or **pumping**, with optional technical detail.

### What Vibelton should not try to do in V2

- Replace the user's taste, composition, or final listening decision.
- Generate an entire generic genre track from one vague prompt.
- Drive Ableton through visual computer use as the normal execution path.
- Spend model calls on menu navigation, repeated state reads, per-parameter clicks, or clip-by-clip execution.
- Ship automatic mastering, reference matching, preference learning, audio embeddings, and every genre template simultaneously.
- Expose hundreds of low-level Ableton controls as the main user experience.

Computer use may exist as a temporary escape hatch for an action the bridge genuinely cannot yet expose. It is not the architecture and must be isolated, opt-in, logged, and easy to remove as a deterministic bridge command becomes available.

## The five Vibelton workflows

V2 should present five clear jobs rather than one giant assistant.

| Workflow | User goal | Vibelton responsibility | Human decision |
| --- | --- | --- | --- |
| **Write** | Start or develop a musical idea | Theory support, chords, rhythms, roles, controlled variations | What is emotionally/musically worth keeping |
| **Generate** | Create bounded musical material | Generate requested MIDI/parts inside constraints and existing project context | Which ideas fit the track |
| **Arrange** | Turn material into a full structure | Genre-template plan, locators, clip placement, density and transition options | Structure and energy arc to keep |
| **Produce** | Make the session work like a production | Organisation, routing, low-end, mix diagnostics, technical options | Sound and aesthetic preference |
| **Finish** | Get an already-good sketch over the line | Prioritised diagnosis, reversible fixes, arrangement/mix/master preparation and comparison | When the record is finished |

Each workflow should have a focused entry point and reuse shared analysis, planning, executor, snapshot, render, and comparison components.

## Finish Track mode

### Primary V2 feature

**Finish Track** is for the moment when the user has a song or loop they like but cannot turn it into a finished record. It is not a one-button autonomous finisher.

The flow is:

```text
Inspect → Diagnose → Prioritise → Propose → Snapshot → Apply → Render/A-B → Keep or Roll Back
```

On entry, Vibelton should inspect the set and return no more than three to five high-impact findings. For example:

> I found four areas worth addressing:
>
> 1. The arrangement changes very little for 48 bars.
> 2. The kick and bass overlap heavily in the low end.
> 3. The main section is not noticeably larger than the preceding section.
> 4. The master has substantial unused headroom.
>
> Suggested order: **Arrangement → Low end → Mix → Master**.

Then give the user two intentional paths:

- **Fix one at a time** — explain and apply one reversible intervention.
- **Make me a version** — create a named alternative snapshot for listening.

Important constraints:

- Keep the central groove, hook, and existing musical identity unless the user explicitly asks to replace them.
- Explain the reason for every meaningful change in plain English.
- Do not make large multi-device edits without a snapshot and explicit proposal.
- Never label a version “better”; label it by its treatment and provide an A/B comparison.

### Finish Track capabilities

1. **Analyse:** tracks, clips, routing, device inventory, levels, arrangement, render metrics, and missing/ambiguous project data.
2. **Diagnose:** section repetition/density, kick-bass relationship, clipping/headroom, obvious masking, stereo/phase warnings, gain staging, and transitions.
3. **Arrange:** extend or reshape a loop using approved section maps and existing clips before adding new musical content.
4. **Produce:** organise the set, establish groups/buses/returns where warranted, and propose reversible production interventions.
5. **Low end:** identify likely kick and bass roles, measure conflict, and provide distinct sidechain choices.
6. **Mix:** focus on the few highest-impact fixes rather than an endless parameter checklist.
7. **Master preparation:** assess readiness, headroom, dynamics, loudness, and peak safety; do not pretend a master-bus chain repairs upstream problems.
8. **Compare:** render before/after previews, retain measurements, and support accept/reject/rollback.

## Genre timing and arrangement templates

Treat genre as structured, editable data—not a prompt the model reinvents every time. Templates are **timing and structure maps**, not a demand that every track follows one arrangement.

Each template should define at least:

```text
genre
variant
bpm_range
target_duration_range
time_signature
sections: name, bars, energy (1-10), purpose
active_track_roles
transition_types
variation_amount
dj_friendly
notes
```

All structural work must be calculated in **bars**, then displayed alongside approximate duration at the current BPM. This makes templates musically actionable and easy to adapt.

Starter data, subject to editable project presets:

| Genre | Typical BPM | Intro | Main sections | Breaks | Typical duration |
| --- | ---: | ---: | ---: | ---: | ---: |
| House | 120–128 | 16–32 bars | 32–64 bars | 16–32 bars | 4–6 min |
| Techno | 125–140 | 32–64 bars | 32–64 bars | 16–32 bars | 5–7 min |
| Disco / Nu-disco | 110–125 | 8–16 bars | 16–32 bars | 8–16 bars | 3–5 min |
| Hip-hop | 70–100 | 4–8 bars | 16-bar verse / 8-bar hook | As needed | 2.5–4 min |
| UK Garage | 125–135 | 8–16 bars | 16–32 bars | 8–16 bars | 3–5 min |
| Drum & Bass | 165–180 | 16–32 bars | 32–64 bars | 16–32 bars | 3–5 min |

Templates should include variants, for example House: **DJ-friendly**, **radio/streaming**, **classic vocal**, **minimal/hypnotic**, and **peak-time**.

### Required arrangement experience

The user should be able to ask:

> Arrange this loop as a five-minute DJ-friendly house track. Keep the main groove and do not add new melodies unless necessary.

Vibelton should propose an explicit plan such as:

```text
126 BPM · 192 bars
1–16    INTRO: drums and percussion
17–32   GROOVE: introduce bass
33–64   MAIN GROOVE
65–80   TENSION
81–96   BREAKDOWN
97–128  MAIN SECTION
129–144 SHORT BREAK
145–176 FINAL PEAK
177–192 DJ OUTRO
```

It should map existing clips and track roles to the plan, show any gaps or assumptions, and require approval before execution.

### Show me three arrangements

Add a deterministic variant generator that can create and compare three structural plans from the same material. A first house implementation could offer:

- **A — Streaming edit** (about 3:15)
- **B — Club version** (about 4:30)
- **C — DJ extended mix** (about 6:00)

The three plans must differ in structure and energy—not merely duplicate clips to different lengths. The user chooses one plan before Vibelton applies it. The initial implementation may create locators and a proposed timeline before it touches clips.

## Song Sketch-friendly template builder

### New Track / Template Builder

Vibelton should create a ready-to-write Ableton session that removes the friction of naming and organising tracks for Song Sketch.

Example entry:

> House → Classic → 124 BPM → Club Mix

The template builder creates named, coloured, grouped tracks with Song Sketch-compatible role labels. A starter House layout:

```text
DRUMS
  Kick
  Snare / Clap
  Hats
  Percussion

BASS
  Bass

MUSIC
  Chords
  Lead
  Hook
  Atmosphere

VOCALS
  Vocal

FX
  FX / Risers

REFERENCE
  Reference
```

For each preset, define and validate:

- Track name and Song Sketch role/category.
- Track type (MIDI/audio/return/group), colour, group, ordering, and default monitor/arm state.
- Standard buses, routing, and return tracks where supported by the existing bridge.
- Basic sidechain-ready routing, but no fragile device chains until the minimum bridge contract is proven.
- Default BPM and time signature.
- Arrangement locators based on the selected genre variant.
- Optional empty clips only where that helps the current workflow.
- Minimal optional devices; do not turn templates into a plugin bundle.

The builder must be idempotent or clearly offer a new-set action. It must not duplicate groups/tracks if a command is retried.

### Existing project cleanup

Add **Prepare this project for Song Sketch** as a proposed, reviewable cleanup workflow.

It should inspect names, track type, devices, clips, routing, and audio/MIDI characteristics where available, then propose—not silently apply—a mapping such as:

```text
Audio 1       → Kick
Serum         → Bass
3-Audio       → Percussion
Operator      → Chords
Kick Final    → Kick (requires duplicate-name resolution)
Thing         → FX
```

The review screen/output should show, per track: current name, suggested name, confidence, suggested group/colour, Song Sketch role, and reason. Ambiguous mappings require the user to choose. After approval, snapshot first, then rename/group/colour/map in a deterministic batch.

## Local project and audio analysis

### Analysis architecture

Use this loop:

```text
Ableton project state
        ↓
Local set and audio render analysis
        ↓
Compact structured measurements
        ↓
Rules engine and, only if needed, one reasoning call
        ↓
Explicit production plan
        ↓
Deterministic Vibelton executor
        ↓
Snapshot, A/B render, comparison, user decision
```

The local analysis layer should provide facts before any model is asked to reason. Reuse existing project inspection or render capability if present; extend it rather than introducing a parallel path.

### Minimum local analysis packet

Use versioned JSON schemas and record tool/runtime versions. The packet should include only supported or clearly qualified measurements, for example:

- Project: tempo, time signature, duration/bars, tracks, groups, routing, devices, clips, locators, automation count, muted/disabled state.
- Arrangement: activity/density by section, first/last activity, section similarity/repetition, clip overlap, transitions, role presence.
- Loudness/dynamics: integrated/short-term LUFS where valid, sample peak, true peak where supported, crest factor, dynamic range, clipping warnings, headroom.
- Spectrum/low end: low-band energy, spectrum summaries, kick candidates, bass candidates, overlap/masking indicators, kick-bass timing estimates.
- Stereo: width by frequency band and phase-correlation warnings.
- Render metadata: source set revision, render range, sample rate, channel layout, timestamp, and failure state.

Analysis should surface uncertainty. “Possible bass track based on name and low-frequency content” is more trustworthy than a confident but unsupported claim.

### Audio render policy

- Render short, relevant previews by default (for example, a selected loop, section, or 15–30 seconds), not the full song for every edit.
- Render a before preview and persist its ID before a batch change.
- Re-render only affected ranges after a change when possible.
- Never overwrite the user's original exports.
- Treat failed/incomplete renders as errors; do not make a recommendation from stale audio without saying so.

## Low-end and sidechain assistant

Build **Fix My Low End** early. It is constrained, useful, measurable, and exercises the complete analyse → propose → apply → A/B system.

### Required behaviour

1. Identify likely kick and bass tracks using names, routing, clip/device context, and audio measurements.
2. Show the evidence and confidence; allow the user to correct the chosen tracks.
3. Measure low-band overlap and kick/bass timing from a selected representative region.
4. Recommend a small, named set of treatments rather than exposing raw compressor settings first:
   - **Transparent:** roughly 1–2 dB ducking; mostly inaudible.
   - **Tight:** roughly 3–4 dB ducking; kick punches through.
   - **Pumping:** roughly 6–8 dB ducking; deliberate rhythmic movement.
5. Translate the chosen treatment into deterministic device/routing/parameter commands, using Ableton-supported sidechain mechanisms.
6. Snapshot, apply, render the same range, show measured before/after context, and offer A/B/rollback.

Parameter values are starting points, not universal truths. If the system proposes values such as ratio, attack, release, threshold, or target gain reduction, label them as the generated settings and explain the musical intention.

Example user experience:

> Your kick and bass overlap most around 60–100 Hz. I can make room for the kick by ducking the bass when it hits. Which feel do you want: **Transparent**, **Tight**, or **Pumping**?

After a selection:

> I added kick-triggered ducking to the bass. This version targets about 3 dB of gain reduction so the kick is clearer without an obvious pumping effect. Compare **Before** and **Tight**; keep it or roll it back.

## Mix and master assistance

### Mix assist

The mix assistant should begin upstream and prioritise the highest-impact interventions. Avoid the false promise that it can fix a poor arrangement with master-bus processing.

Initial checks:

- Obvious gain-staging problems and unused headroom.
- Clipping and unsafe peaks.
- Likely low-end conflicts.
- Major masking or excessive density in an active section.
- Stereo/phase warnings.
- Missing or inconsistent group/bus organisation where it impedes the task.
- Section contrast and whether the intended main section is materially bigger.

For each suggestion, output: observation, evidence, proposed action, expected musical result, confidence, reversibility, and plain-English explanation. Limit an initial Finish Track diagnosis to three to five fixes.

### Master assist

V2 master assistance is **master preparation and comparison**, not a promise of automated professional mastering.

It should:

- Check loudness, peak safety, headroom, dynamic range, clipping, and obvious tonal imbalance indicators.
- Identify upstream problems before proposing master changes.
- Propose a minimal, reversible master chain only when the mix is ready enough.
- Render and compare versions at matched perceived loudness where feasible.
- Clearly distinguish a technical warning from an aesthetic choice.

Do not offer reference matching as an implementation requirement in the first V2 increment.

## Future reference-track support

Design the interfaces so a future reference workflow can attach a licensed or user-supplied reference audio file and compare it with a project render.

Future comparison dimensions may include:

- Loudness, peak margin, and dynamics.
- Spectral balance and low-end energy.
- Stereo width and phase behaviour.
- Arrangement density, transition frequency, and section energy.
- Optional audio/music embeddings, after evaluation proves they are useful.

The future output should be an explanation such as “your main section has less low-mid energy and lower density than this reference,” not an instruction to copy a particular song. Do not claim legal, creative, or sonic equivalence.

## Deterministic action contract

Model output must not be free-form commands executed directly in Ableton. Define a typed action plan that is validated before execution.

Example shape:

```json
{
  "plan_id": "finish-low-end-001",
  "source_revision": "set-state-hash",
  "snapshot_name": "Before tight sidechain",
  "intent": "Create kick space in the low end",
  "assumptions": ["Bass is track 12", "Kick is track 3"],
  "actions": [
    {
      "type": "configure_sidechain",
      "target_track_id": "12",
      "trigger_track_id": "3",
      "treatment": "tight",
      "parameters": {"ratio": 3, "attack_ms": 2, "release_ms": 90}
    }
  ],
  "verification": ["render_range", "analyse_low_end", "compare_to_snapshot"]
}
```

The actual schema must use IDs and command names supported by the existing bridge. Do not invent an action that cannot be deterministically executed and verified.

Executor requirements:

- Validate schema, project revision, target IDs, action preconditions, supported device parameters, and routing compatibility before changing the set.
- Return structured per-action results, including skipped, failed, changed, and verification status.
- Be retry-safe: identify whether an action has already been applied before applying it again.
- Stop the batch on an unsafe/unrecoverable failure and retain the snapshot.
- Record enough state to roll back the batch exactly where the bridge supports it.

## Snapshots, A/B, and rollback

Trust is a core product feature.

Before meaningful edits, create a named snapshot that records at least the set/state revision, targeted tracks/devices, planned actions, and before-render ID. Use Ableton-native undo only as a convenience; do not depend on a fragile arbitrary-depth undo stack as the sole safety mechanism.

For every comparison:

- Name versions by what changed: `Before`, `Tight sidechain`, `Pumping sidechain`, `Arrangement B`.
- Render the same region and use consistent playback gain where comparison tooling supports it.
- Show a compact summary of changed tracks/devices and relevant measurements.
- Provide **Keep**, **Roll back**, and **Create another variant** actions.
- Never overwrite the user’s set, export, or prior comparison without explicit confirmation.

## Model and cost policy

The central cost rule is:

> One high-level reasoning request should produce a plan; deterministic Vibelton code should perform the many Ableton operations.

### Local / deterministic work first

Use local code or bridge calls for:

- Reading project state and device values.
- Template selection and bar calculations.
- Track naming, colouring, grouping, routing, and locator placement.
- Clip copying/muting/placement when a plan has been approved.
- Audio/DSP measurements and before/after comparisons.
- Validation, snapshots, rollback, logging, and UI state.

### Model calls only when reasoning adds value

Use a capable model for bounded tasks such as:

- Interpreting the analysis packet into a prioritised diagnosis.
- Turning an ambiguous outcome request into a structured plan.
- Choosing/adapting a template variant based on the user's stated intent.
- Explaining trade-offs and presenting compact options.

Do not use a frontier model for clicks, menus, repeated polling, raw state transcription, or each individual parameter change. Do not make an additional model call merely to execute an already validated plan.

### Computer-use policy

- Default: disabled for normal flows.
- Allowed only as explicit opt-in fallback when a required, documented bridge capability is missing.
- Bound it to a short task, a fixed screen/operation budget, and an auditable log.
- On success, create a bridge capability issue or implementation task so the fallback can be retired.

### Cost logging

Log each session and model/computer-use operation with:

- Workflow, request/plan ID, model/provider, purpose, timestamp, latency, success/failure.
- Input/output token counts and estimated/actual cost when available.
- Computer-use steps, duration, fallback reason, and outcome.
- Render and DSP runtime costs separately.
- Snapshot and action counts.

Show the user a simple session total and an optional detailed developer view. Include budget controls: per-operation warning, per-session cap, and an explicit opt-in for higher-cost analysis.

## Suggested user commands and prompts

These are product-level prompts; the implementation must compile them into typed plans and ask for confirmation whenever changes are material.

### Start and organise

- “Create a Classic House template at 124 BPM for a club mix.”
- “Start a Song Sketch-ready UK Garage session at 132 BPM.”
- “Prepare this project for Song Sketch. Show me the proposed names before changing anything.”
- “Group and colour this project, but do not change clips, devices, or routing.”

### Arrange

- “Arrange this loop as a five-minute DJ-friendly house track. Keep the main groove.”
- “Show me three arrangements: streaming, club, and extended.”
- “Make the second drop feel bigger without adding a new melody.”
- “Find the section that is too repetitive and propose two changes.”

### Produce and finish

- “I have the tune. Finish it.”
- “What are the three biggest things stopping this sounding finished?”
- “Fix my low end. Use the current kick and bass, and show me the choices.”
- “Give the vocal more space, but preserve its tone.”
- “Prepare this for mastering. Do not add a master chain until you explain the mix issues.”
- “Make a reversible version with a tighter kick and bass relationship.”

### Compare and learn

- “Render A/B for the last change.”
- “Roll back the pumping version and keep the tight version.”
- “Explain what you changed without technical jargon.”
- “Show the exact Ableton settings you used.”

## Codex implementation instructions

### Phase 0 — Audit and plan (required gate)

Before writing production code, inspect the repository and produce a short implementation note covering:

1. Repository structure, runtime/tooling, test commands, and existing documentation.
2. Existing Ableton bridge API/capabilities and which are deterministic.
3. Existing Vibelton theory, generation, arrangement, analysis, UI, and persistence capabilities.
4. Existing state/snapshot/undo/render/audio-analysis support.
5. Exact gaps for: template builder, project cleanup, Finish Track diagnosis, low-end assistant, action plans, A/B/rollback, and cost logging.
6. A phased change plan that names files/modules to extend and avoids unnecessary replacement.
7. Risks, unknown Ableton API limitations, and the smallest proof-of-capability required for each risk.

Do not implement Phase 1 until the audit has identified the actual integration points. If a requested capability is absent from the current bridge, add a small typed bridge primitive with a focused integration test rather than using computer use by default.

### Phase 1 — Foundations and trust

Implement only the shared plumbing necessary for later workflows:

- Versioned project-analysis schema.
- Typed production-plan/action schema and validator.
- Named snapshots with source revision and structured change log.
- Render/analyse comparison contract.
- Structured operation/cost logging.
- A small number of deterministic bridge primitives that are demonstrably needed.

Deliverable: a dry-run plan can be created from a known project state, validated, shown to the user, executed in a controlled fixture, and rolled back.

### Phase 2 — Song Sketch template builder and cleanup

Implement a single end-to-end genre preset first (Classic House / 124 BPM / Club Mix is suitable) and the review-first cleanup proposal.

Deliverable: create a correctly named/grouped/coloured Song Sketch-ready set; generate a cleanup proposal for a messy fixture; require approval; apply it through a snapshot; verify exact final state. On Live versions where a pristine blank Set cannot seek far enough to create the full locator range, Phase 2 must omit locators, explicitly report the deferral, and retain the seven locator definitions as template metadata. Full locator placement is deferred to Phase 3, after arrangement content establishes sufficient song length. No placeholder clip or locator-length workaround is permitted.

**Status: complete (2026-09-22).** A new disposable blank Live Set was used for the real-Live acceptance: the capability-aware flat template produced the 12 ordered, coloured role tracks at 124 BPM with no clips, devices, placeholders, or locators; it returned the explicit deferral warning and retained all seven locator definitions as metadata. The normal snapshot rollback restored the original four-track, 120 BPM blank Set exactly at the user-visible state level. Full locator placement remains Phase 3 work only.

### Phase 3 — Arrangement templates and three variants

Implement the genre template data model and a single House template family. Start by generating plans and locators, then add deterministic approved clip/section operations.

Deliverable: given the same loop fixture, generate three meaningfully different bar-based structures, preserve the core loop, and apply only the user-selected variant.

#### Phase 3A — planning only (implemented 2026-09-22)

`vibelton.arrangement-plan/v1` persists three read-only Classic House options against the exact Live session and production revision: `streaming-edit` (about 3:15), `club-version` (about 4:39), and `dj-extended-mix` (about 6:00). Their whole-bar totals are derived from the current project BPM (at 124 BPM: 101, 144, and 186 bars respectively); bar structure remains authoritative and duration is calculated as `bars × 4 × 60 ÷ project BPM`. The Club benchmark uses 144 bars specifically so a 16-bar source loop can form nine exact, non-overlapping copies.

Each variant contains contiguous 4/4 bar ranges, named sections, energy, purpose, active role suggestions, transition suggestions, and seven intended locator records. Those records retain the Phase 2 locator names as source metadata while adapting the positions and visible bar counts to the selected structure. The planner inspects known tracks and clips, reports likely roles, missing material, and reuse-only assumptions. It never creates, copies, moves, mutes, extends, or otherwise changes clips, locators, devices, or Live state.

`POST /api/production/arrangement-options` accepts a UUID `request_id` and returns/persists the three options without queueing. `POST /api/production/arrangement-selection` requires `{proposal_id, variant_id, approved: true, request_id}` and persists exactly one explicitly approved variant with its source revision. Both operations are idempotent by request ID and logged. Selection does **not** create an execution plan; Phase 3B must re-check capabilities and create a separate approved plan.

Phase 3B requires reliable reading of existing Session and Arrangement clips, deterministic approved clip operations, and clip/track readback adequate for exact rollback. Ableton Live 12.3.2's Remote Script cue API was tested after a 144-bar arrangement was established: it did not preserve requested cue positions/names for deterministic readback. Therefore Phase 3B persists the seven intended locators as arrangement metadata and returns an explicit deferral warning; it does not mutate native locators. A future bridge may enable native locator creation only after it advertises and proves deterministic locator readback.

#### Phase 3B — approved copy-only execution (completed 2026-09-24)

The production action accepts only a uniquely identified 16-bar Arrangement source (stable track ID, start beat, and full fingerprint), then copies it to eight disjoint destinations for a 144-bar Club benchmark. Each copy is read back by destination and fingerprint. Retry requests are rejected before mutation. The inverse deletes only copies recorded by that execution and verifies return to the original observable Set state. Live's retained internal song length is excluded only from this post-delete comparison because it changes the derived `locator_range` capability after all editable arrangement content has returned; the normal full revision remains the stale-state preflight guard.

Real-Live acceptance on a fresh disposable Set confirmed nine identical contiguous clips through beat 576, no native locators, persisted seven-locator metadata with the explicit deferral warning, retry rejection, and exact rollback to the original single 16-bar loop. Phase 4 remains out of scope.

### Phase 4 — Finish Track diagnosis

Combine project analysis and any existing local render analysis to produce a compact, evidence-backed diagnosis. Begin with arrangement repetition, project organisation, headroom, and selected low-end observations.

Deliverable: a real or fixture set returns at most five prioritised findings with evidence, assumptions, recommended order, and no changes until the user approves one.

### Phase 5 — Fix My Low End

Implement kick/bass selection, confidence/review, low-end analysis, three named sidechain treatments, deterministic execution, A/B render, and rollback. Do not broaden to general mix automation until this closed loop is reliable.

Deliverable: an integration fixture confirms the correct routing/device configuration, produces before/after renders, logs measurements, and restores the pre-change snapshot exactly.

### Phase 6 — Mix/master preparation and polish

Add only the high-impact mix checks proven by the benchmark track. Implement master preparation and comparison with conservative guardrails. Add user-facing explanations, preference capture only where a clear decision exists, and cost/budget controls.

Deliverable: the benchmark track can move through Diagnose → chosen interventions → A/B → keep/rollback, with the user retaining all creative decisions.

### Deferred work

Leave these behind interfaces or documented backlog items until the core loop is working:

- Reference-track matching and embedding-based similarity.
- General autonomous composition.
- Broad automatic mix/master processing.
- Persistent personal production-profile learning.
- Computer-use-first integration.
- Many genre presets before one template family works end-to-end.

## Acceptance criteria

V2 is not complete because an LLM can write an Ableton command. It is complete when these behaviours have evidence-backed tests and manual verification.

### Audit and compatibility

- [ ] An audit note identifies existing Vibelton integration points and the final design extends them rather than needlessly replacing working code.
- [ ] Existing public behaviour/tests remain working, or each intentional compatibility change is documented and tested.
- [ ] New bridge capabilities are typed, validated, and integration-tested against the supported Ableton environment.

### Safety and determinism

- [ ] A material action always has a validated plan, source-revision check, named snapshot, and structured result.
- [ ] Invalid/missing targets, stale state, unsupported devices, and partial failures stop safely and produce actionable errors.
- [ ] A completed batch can be rolled back to its recorded pre-change state within the supported bridge contract.
- [ ] Retrying a completed request does not duplicate tracks, groups, devices, or destructive edits.

### Template builder and cleanup

- [x] The first Song Sketch template creates the specified groups/tracks, names, colours, BPM, and locators deterministically when the Live capability reports `locator_range: true`; for a pristine blank Set reporting `locator_range: false`, it creates the flat role tracks and BPM without locators, returns the explicit Phase 3 deferral warning, and preserves the seven locator definitions as metadata.
- [x] The resulting template is usable without manual track naming for the supported Song Sketch roles.
- [ ] Existing-project cleanup shows a reviewable mapping with confidence/reasons and makes no changes before approval.
- [ ] Cleanup applies only approved changes and is reversible.

### Arrangement and Finish Track

- [ ] Arrangement plans are bar-based, editable, and use the chosen genre/template variant.
- [ ] “Show me three arrangements” produces materially distinct structures from the same source material.
- [ ] Finish Track returns no more than five prioritised, evidence-backed findings and does not alter the set while diagnosing.
- [ ] The user can choose one intervention, hear a before/after comparison, and keep or rollback it.

### Low end, mix, and master preparation

- [ ] Kick/bass selection is reviewable and confidence-qualified.
- [ ] Transparent, Tight, and Pumping treatments configure supported Ableton routing/devices deterministically and explain their intended musical effect.
- [ ] Before/after renders cover the same range and retain comparison metadata.
- [ ] Master preparation identifies upstream mix issues before offering a master-bus intervention.

### Costs and user experience

- [ ] Normal execution uses deterministic bridge calls and local analysis; model calls are bounded to planning/interpretation/explanation.
- [ ] Computer-use fallback is opt-in, bounded, and logged.
- [ ] Session costs and model/computer-use usage are recorded and visible.
- [ ] User-facing language is outcome-led and understandable without production-engineering knowledge, while exact settings remain available on request.

## Definition of success

Use one real unfinished track as the initial benchmark. V2 has succeeded when the owner can start with a good 16-bar idea and use Vibelton to make meaningful, reversible progress toward a release-ready arrangement and production—without Vibelton taking over the musical taste decisions and without an unsustainable model/computer-use bill.

The north star is not “Can AI make a techno track?” It is:

> Can Vibelton help its user finish a track they genuinely want to release, while the user remains the artist and final listener?
