# Composition Lab

Composition Lab is the fourth mode in the local Vibelton app (normally http://127.0.0.1:8765). It writes original MIDI on existing user-selected instruments. It does not load devices, choose presets, change mixer settings, or write device automation.

## Getting started

1. Save your current Live Set, then **Save Live Set As** to create a working copy.
2. Start the local Vibelton server. Install the current remote script with `python3 install_remote_script.py`, then restart Live and open the working copy. The app requires the `composition_v1` capability and a fresh heartbeat before applying.
3. Open Composition Lab. Expand **Your instruments**, refresh Live tracks, and assign the musical roles to existing MIDI tracks. Several parts can share a track. For drums, set the MIDI note mapping to match your instrument's one-shot notes; a plugin's phrase-trigger keys may behave differently.
4. Edit sections, accent groups and expression. **Save draft** generates missing or changed unlocked parts and creates an immutable local revision. It does not change Live.
5. **Preview selected section** writes and loops only that section in a fresh Arrangement range. **Build arrangement** writes the whole composition into another fresh range and leaves playback stopped.
6. Complete Arrangement time-signature markers with Codex in the Live UI. Clip metre alone does not change the Arrangement ruler. The result remains **Applied**, with a marker checklist, until marker verification is recorded.

The default score has 21 editable passages grouped conceptually into six movements. The exit is **eight pairs** of one bar 7/8 and one bar 9/8, not four pairs. At 168 BPM the score is 672 quarter-note beats, exactly 240 seconds. Duration excludes instrument/reverb release tails.

## Working with Codex

Use **Copy brief for Codex** and paste the brief into the conversation. Codex can read and revise the score through the local endpoints below. No in-app model/API account is needed. Musical feedback comes from listening with the user; the app does not claim to analyse audio.

- Keep the bass phrase: set that section's `parts.bass.locked` to true and save before revising.
- More fractured: edit the selected section's `motif_transform` to `fragment`, adjust energy or expression, or submit explicit MIDI note edits.
- Return the opening motif: keep the shared `motif` intervals and set the later section's transformation to `return`.
- To change locked material, unlock it in a separate saved revision first. Locks apply to section order/material and individual parts' notes, metre, length and active state. A locked section can still move in elapsed time if an earlier unlocked section changes length.
- Explicit note edits take precedence over automatic regeneration. **Vary unlocked parts** changes only the selected passage's unlocked parts, preserving the global seed and other passages.
- Global expression changes regenerate unlocked material on save. Sound locks are mandatory in v1; change sounds in Ableton.

## Local API

All request/response bodies are JSON. Times are quarter-note beats; seconds = beats × 60 / BPM. Save and compile never enqueue mutations. No calls pass through the existing `/api/chat` planner or instrument enrichment.

| Method and path | Input / result |
|---|---|
| `GET /api/composition` | Latest `{revision, composition}`, revision history, current Live state, execution history. Revision 0 is the unsaved starter. |
| `GET /api/composition/revisions/{revision}` | Read an immutable score revision. To recall one, save its composition against the latest base revision; existing locks still apply. |
| `POST /api/composition/save` | `{base_revision, composition, fit_duration?: bool, regenerate?: {sections: [section_id], roles: [role]}}` → new revision and compiled timing. Conflicting base revisions are rejected. |
| `POST /api/composition/compile` | `{revision, section_id?: string}` → section timing, total beats, seconds and target difference. |
| `POST /api/composition/apply` | `{revision, section_id?: string, working_copy_confirmed: true}` → durable job. Omit section_id for a full arrangement. A revision/section pair is applied once; save a new revision to create another version. |
| `GET /api/composition/status/{job_id}` | Queued, Applied, Verified, Failed, Partial failure, or Interrupted, plus durable execution readback. |
| `POST /api/composition/verify-markers` | `{job_id, markers: <exact job.markers list>, evidence: <UI verification note>}`. Only after actual clip readback and UI checks; never submit based solely on the intended plan. |

Read the default document to obtain the complete editable score shape. It contains brief/mood, BPM, duration target, seed, root MIDI note, mode, shared motif intervals, ingredients by musical role, expression amounts, track assignments, sound locks, drum-note map, and ordered sections. Each section has a unique ID, metre `[numerator, denominator]`, grouping, bars, energy, active parts, lock, motif relationship/transform and `parts` with locks and MIDI notes. Each note has pitch, start, duration and velocity.

Track assignments contain `id`, `name`, and `session_id` from bridge state. After reopening a Set or reloading the bridge, refresh and reassign tracks. Names alone never authorize writes.

## Execution and recovery

Drafts and revisions live in `~/.vibelton/compositions/`; bridge execution records live in `~/.vibelton/composition-executions/`. Browser drafts also survive refresh in local storage. The server saves files atomically and serializes revision/apply reservations.

Each command checks session identity, track identity, fresh scene allocation, and empty Arrangement range before writing. Generated parts sharing a track are merged into a single section-length clip. Readback checks notes, length, metre, placement, original Session/Arrangement clips, and instrument/mixer snapshots. Tempo automation is rejected rather than overridden.

Partial failures are recorded with the last clip index and completed count. They are never blindly retried or described as successful. New versions use fresh ranges; no automatic deletion or rollback of user material occurs. If Live restarts before a queued command is acknowledged, the UI reports Interrupted. Live's bridge does not replay commands queued before startup.

Metre-marker verification is a recorded human/Codex UI check, not an automated marker API. **Applied** means clips were applied and checked; **Verified** additionally records the Arrangement marker check. These are historical execution results, not continuous monitoring of later manual edits.

## Validation

Run `python3 -m unittest discover -s tests`. Composition tests cover exact timing, note bounds, metres, grouping, duration fitting, locks, explicit edits, revisions, isolated previews, duplicate submissions, stale sessions, safe placement, partial failures and verification states. The bridge tests use an in-memory Live host; real Live checks are separately recorded in `COMPOSITION_LAB_SMOKE_TEST.md`.
