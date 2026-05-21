# Vibelton Staged Todo Plan

[Unverified] This planning document combines confirmed local-file facts with labelled inferences. Confirmed items are based on files present in this workspace on 2026-04-30. Items marked [Inference] are reasoned from the current code and docs, not independently tested in Ableton Live.

## 0. Current Workspace Audit

- [x] Confirmed: `PROJECT_STATUS.md`, `implementation_plan.md`, and `IMPROVEMENTS_PLAN.md` exist in this workspace.
- [x] Confirmed: GitHub PR #1 exists at `https://github.com/jimbrouw/vibelton/pull/1`.
- [x] Confirmed: PR #1 is titled "Initial implementation upload".
- [x] Confirmed: PR #1 is open and mergeable.
- [x] Confirmed: PR #1 targets `main` from `initial-upload`.
- [x] Confirmed: PR #1 reports no status checks.
- [x] Confirmed: local `initial-upload` matches `origin/initial-upload`.
- [x] Confirmed: PR #1 contains 23 changed files against `main`: project docs, Python server/planner modules, Ableton Remote Scripts, installer, web UI, and `.gitignore`.
- [x] Confirmed: `STAGED_TODO_PLAN.md` is local-only and is not in PR #1.
- [x] Confirmed: the web UI already includes an Idea Engine / The Finisher mode toggle in `web/index.html`.
- [x] Confirmed: `web/styles.css` already includes a `body.mode-finisher` theme.
- [x] Confirmed: `web/app.js` already includes a Finisher save-copy prompt before switching into Finisher mode.
- [x] Confirmed: `vibelton/genre_dna.py` includes Afrobeats and Amapiano profiles.
- [x] Confirmed: `vibelton/planner.py` queues Finisher mutations for `mutate_clones`, `humanize`, `ghost_notes`, and subtractive arrangement prompts.
- [x] Confirmed: `vibelton/actions.py` has a `finisher_mutation` helper that queues duplicate, mute, and copied-clip creation actions.
- [x] Confirmed: the main `ableton_remote_script/Vibelton/Vibelton.py` handles `duplicate_track` and `mute_track`.
- [ ] Confirmed gap: `legacy/AbletonCopilotArranger/AbletonCopilot.py` does not handle `duplicate_track` or `mute_track`.
- [ ] Confirmed gap: `GenreDNA` still stores a single `swing: float`; no `groove_profile` dataclass exists yet.
- [ ] Confirmed gap: no `music21` integration or `harmony.py` module exists yet.
- [ ] Confirmed gap: no JSON arrangement-template DSL exists yet.
- [ ] Confirmed gap: no SnapHost client integration exists in the Vibelton code yet.
- [Inference] The current code has moved beyond the older planning docs in UI, prompt-library, Finisher, genre palette, and arrangement-copy areas.

## 1. Todo Breakdown From `PROJECT_STATUS.md`

### Confirmed Status Items To Preserve

- [ ] Keep the local HTTP server entrypoint: `python3 -m vibelton.server`.
- [ ] Keep the queue bridge files compatible with `commands.jsonl`, `events.jsonl`, and `state.json`.
- [ ] Keep deterministic local planning as the fallback path when `OPENAI_API_KEY` is absent.
- [ ] Keep optional OpenAI planning behind environment configuration.
- [ ] Keep GenreDNA-based generation as the primary local musical brain.
- [ ] Keep the new Afrobeats and Amapiano profiles active in detection, prompts, and palettes.
- [ ] Keep Finisher mutation commands routed through a duplicate-and-mute pattern.

### Active Roadmap Items

- [ ] Replace `swing: float` with a richer `groove_profile` object.
- [ ] Add dynamic velocity curves by drum role and genre.
- [ ] Add probability-based drum mutation loops.
- [ ] Add optional `music21`-backed harmony helpers.
- [ ] Add genre-weighted progression selection.
- [ ] Add voice-leading minimisation.
- [ ] Add a musical colour control for borrowed chords.
- [ ] Add melody phrase contours, rests, and chord-tone landing rules.
- [ ] Add a JSON arrangement DSL for full song structures.
- [ ] Add mix decisions for generated sketches, including level staging and routing candidates.
- [ ] Add SnapHost integration after the core arrangement and sound-chain path is stable.

## 2. Todo Breakdown From `implementation_plan.md`

### Product Structure

- [x] Confirmed: introduce two modes: Idea Engine and The Finisher.
- [x] Confirmed: expose a global UI toggle between those modes.
- [x] Confirmed: add dynamic visual theming for Finisher mode.
- [ ] Review mode naming and brand fit with the user.
- [ ] Decide whether the current colors are final or need another design pass.
- [ ] Gate Finisher more deliberately after the user has generated or loaded an idea.

### Idea Engine

- [x] Confirmed: include Genre DNA Generator prompts.
- [ ] Add a true Mise en Place command that creates high-quality tracks without MIDI clips.
- [ ] Add arbitrary creative-constraint prompts.
- [ ] Add avoidance prompts that suggest what not to do in a session.
- [ ] Separate Idea Engine prompts from Finisher prompts more clearly in the UI state.

### The Finisher

- [x] Confirmed: mutation helpers exist for sibling variations, humanising, and ghost notes.
- [x] Confirmed: subtractive arrangement prompts exist for intro and breakdown carving.
- [x] Confirmed: the UI prompts the user to save a copy before entering Finisher mode.
- [ ] Add explicit UI controls for selecting target track or clip before mutation.
- [ ] Add a formal skeleton tool that creates arrangement locators or section markers.
- [ ] Add automation rhythm generation for filter, send, and movement lanes.
- [ ] Align both Remote Script variants so Finisher actions behave the same way.

### Backend Shape

- [ ] Split mode-specific planner logic into clearer modules, for example `idea_engine.py` and `finisher_tools.py`.
- [ ] Keep shared note, rhythm, palette, and arrangement helpers in common modules.
- [ ] Add action validation tests so the planner does not queue actions unsupported by the selected Remote Script.
- [ ] Add route-level or payload-level mode metadata for future UI and analytics.

## 3. Todo Breakdown From `IMPROVEMENTS_PLAN.md`

### Iteration A: Humanisation And Groove

- [ ] Define `GrooveProfile` with position jitter, velocity jitter, note-length jitter, weak-beat curve, and subdivision push/pull.
- [ ] Migrate every `GenreDNA` profile from `swing` to `groove_profile`.
- [ ] Build six initial groove templates: boom-bap, MPC-style 58, MPC-style 62, DnB tight, UKG shuffle, dembow, and trap triplet.
- [ ] Verify licensing before bundling any dataset-derived groove templates.
- [ ] Add per-role velocity curves for hats, kicks, snares, claps, percussion, bass, chords, and leads.
- [ ] Add bar-to-bar drum variation rules.
- [ ] Add a dedicated fill generator for bar 4, 8, and 16 boundaries.
- [ ] Add listening-test notes for at least three genres.

### Iteration B: Harmony And Melody

- [ ] Add optional `music21` dependency behind a small `harmony.py` interface.
- [ ] Add a fallback harmony path when `music21` is unavailable.
- [ ] Add genre-weighted Roman-numeral progression models.
- [ ] Add inversion selection and voice-leading scoring.
- [ ] Add borrowed-chord colour controls.
- [ ] Add phrase contours for melody generation.
- [ ] Add rest-density controls by energy level.
- [ ] Add chord-tone resolution rules for phrase endings.
- [ ] Add A/B listening notes against reference loops.

### Iteration C: Arrangement And Mix

- [ ] Define `arrangement_templates/*.json` with sections, bar counts, energy, active tracks, automation candidates, and mix notes.
- [ ] Add parser and validation for arrangement templates.
- [ ] Connect the planner to the arrangement DSL instead of hard-coded section lists.
- [ ] Add section-aware clip mutation for rests, fills, density, register, and hook re-entry.
- [ ] Add automation actions or a bridge-compatible automation workaround.
- [ ] Add default mix staging for core roles.
- [ ] Add sidechain and return-track planning as queued actions only after bridge support is confirmed.
- [ ] Add full-arrangement listening-test notes.

### Iteration D: Sound, SnapHost, And Reference Tracks

- [ ] Build a small stock-device-chain library using Ableton-native devices.
- [ ] Map device chains to role, genre, and energy.
- [ ] Add a bridge route for loading local `.adv` chains if Live exposes a reliable path.
- [ ] Add SnapHost client commands after the SnapHost host exists.
- [ ] Add light plugin morph/randomise commands through SnapHost.
- [ ] Add reference-track ingestion design.
- [ ] Evaluate BPM/key detection through `librosa` or another local tool.
- [ ] Add final A/B memo against the selected competitor/reference set.

### Smaller Wins

- [ ] Move queue files toward an app-support directory after migration is planned.
- [ ] Replace the README one-liner with clearer product copy.
- [ ] Add a command or UI view for recent prompt and outcome history.
- [ ] Ship a curated example prompt library and generated demo sets.
- [ ] Add a suggest-only mode based on current Ableton state.

## 4. Staged Execution Plan

### Stage 1: Stabilise What Already Changed

Goal: make the current user-visible modes and queued actions internally consistent.

- [x] Decide whether `Vibelton` or `AbletonCopilotArranger` is the canonical Remote Script.
- [x] Move the non-canonical script to legacy and ensure `Vibelton` is used.
- [x] Add a small action-support matrix test for planner output versus bridge handlers.
- [x] Smoke-test local planner prompts for Idea Engine, Finisher humanise, Finisher ghost notes, and arrangement copy.
- [x] Update README to match the current two-mode UI and expanded prompt library.
- [ ] Add a short "Known limits" section for unsupported device insertion and unverified Live browser-loading behavior.

Exit check:

- [ ] A Finisher prompt queues only bridge-supported actions for the chosen Remote Script.
- [ ] Idea Engine prompts still generate tracks, clips, palettes, arrangement copy, and playback actions.
- [ ] Documentation describes the current behavior without relying on older future-tense claims.

### Stage 2: Finish Iteration A

Goal: make generated MIDI feel less grid-stiff before adding more harmonic complexity.

- [ ] Add `GrooveProfile`.
- [ ] Migrate all genre profiles.
- [ ] Apply microtiming and velocity curves in `genre_drums`, `genre_bassline`, `genre_chords`, and `genre_lead` where musically useful.
- [ ] Replace generic `humanize_groove` randomness with profile-aware humanisation.
- [ ] Add deterministic seed handling so repeat prompts remain reproducible.
- [ ] Add focused unit tests for timing, velocity bounds, and repeatability.
- [ ] Add first listening-test notes in `LISTENING_NOTES.md`.

Exit check:

- [ ] Generated notes stay within valid MIDI bounds.
- [ ] Humanisation is deterministic for the same prompt unless explicit variation is requested.
- [ ] Listening notes identify which genres improved and which still need work.

### Stage 3: Finish Iteration B

Goal: make chords and melodies feel selected rather than stamped from one default progression.

- [ ] Add `harmony.py`.
- [ ] Add optional dependency handling for `music21`.
- [ ] Replace fixed common progressions with genre-weighted progression choices.
- [ ] Add voice-leading and inversion selection.
- [ ] Add colour control parsing in the planner.
- [ ] Add melody contour and rest-density passes.
- [ ] Add tests for chord generation, fallback behavior, and deterministic results.

Exit check:

- [ ] Chord output varies by genre, mood, and colour setting.
- [ ] The code still works without `music21` installed.
- [ ] Melody output includes purposeful rests and phrase endings.

### Stage 4: Finish Iteration C

Goal: move from prompt-generated loops to structured arrangements.

- [ ] Add arrangement-template JSON files.
- [ ] Replace hard-coded section helpers with template lookup.
- [ ] Add schema validation for templates.
- [ ] Add section-aware mutation rules.
- [ ] Add bridge-compatible support for locators or section naming if Live exposes it.
- [ ] Add mix-stage actions that are already supported by the bridge.
- [ ] Defer unsupported routing, compression, sidechain, or automation commands until bridge support is confirmed.

Exit check:

- [ ] A full-song prompt produces a readable arrangement from template data.
- [ ] Section names, bar lengths, and start positions match the template.
- [ ] Unsupported mix or automation ideas are not silently queued as if they are executable.

### Stage 5: Finish Iteration D

Goal: improve sound identity after MIDI, harmony, and arrangement structure are stable.

- [ ] Curate stock-device candidates by role and genre.
- [ ] Test Live browser loading against the actual installed Ableton library.
- [ ] Add `.adv` chain loading only if a reliable bridge path is confirmed.
- [ ] Add SnapHost integration as a separate module.
- [ ] Add reference-track ingestion only after file upload and analysis flow is designed.
- [ ] Write final A/B notes and update the roadmap based on the results.

Exit check:

- [ ] Sound-loading behavior is documented as confirmed or unsupported.
- [ ] SnapHost commands are isolated from core Ableton arrangement commands.
- [ ] Reference-track features are clearly marked as experimental until tested.

## 5. Immediate Next Todo List

- [x] Pick the canonical Remote Script.
- [x] Align duplicate/mute Finisher support across active Remote Script code.
- [x] Add action-support tests for queued action types.
- [x] Run a local planner smoke test for representative prompts.
- [x] Update README to match the current app.
- [ ] Start `GrooveProfile` implementation after Stage 1 passes.

## 6. Open Decisions

- [ ] Is "Idea Engine" the final name?
- [ ] Is "The Finisher" the final name?
- [ ] Should the current muted-beige Idea Engine palette stay, or should it move closer to the bright neon direction from `implementation_plan.md`?
- [ ] Should Finisher be available immediately, or only after a generated/loaded idea is detected?
- [ ] Which Remote Script should users install by default?
- [ ] Which genres matter most for the first listening-test pass?
- [ ] Which references are acceptable for A/B tests?
