# Arranger smoke test (manual, in real Ableton Live)

Unit tests cover planning, rollback logic and the working-copy gate (see `tests/test_arranger_edge_cases.py`,
`tests/test_rollback_safety.py`, `tests/test_working_copy.py`). This checklist covers what they cannot:
what Live actually does. **Record only what you observe.** Leave a box empty if you did not run the step.

Never run this on your original Set. Use **File > Save Live Set As…** to create a file whose name contains
`vibelton-working-copy`, e.g. `edge-cases vibelton-working-copy.als`.

## 0. Preconditions

- [ ] Server running the current code (`python3 -m vibelton.server` or via the device), `GET /api/status` shows `connected: true`.
- [ ] Device reloaded after `python3 scripts/deploy_m4l.py --apply` (device header/badge shows the Set name).
- [ ] Remote Script installed copy matches the repo (do not reinstall if it does).

## 1. Build the edge-case Set (matches `tests/fixtures/arranger-*.json`)

Create these in the working copy, each on its own named track (names matter for role detection: Kick, Bass, Hats, Chords):

| Case | How to build it | Fixture |
|---|---|---|
| 6-bar loops | 6-bar clips on Kick/Bass/Hats/Chords | `arranger-6-bar-loop.json` |
| 12-bar loops | same with 12 bars (use a second Set, or replace) | `arranger-12-bar-loop.json` |
| 2.5-bar loop | one clip with loop length 2.2.0 (2.5 bars) | `arranger-2p5-bar-loop.json` |
| Nested groups | group "Drums" containing group "Percussion"; put Kick in Drums, Hats in Percussion | `arranger-nested-groups.json` |
| Group track | confirm Live does not let you drop a clip on the group track itself (note what happens) | `arranger-clip-on-group-track.json` |
| Track automation | draw a filter-sweep automation lane on the Kick track in the Arrangement | `arranger-track-automation.json` |
| Mixed audio/MIDI | Kick and Hats as audio clips, Bass and Chords as MIDI | `arranger-mixed-audio-midi.json` |
| Warped audio | audio loop recorded at ~100 BPM, Warp on, Set tempo 124 | `arranger-warped-audio-other-tempo.json` |
| Partly filled | extra clips so the Arrangement already ends at bar 26 | `arranger-partly-filled-arrangement.json` |

## 2. Safety gates (Tasks 1, 4)

- [ ] Open a Set **without** `vibelton-working-copy` in its name: device shows red "Original Set — scaffolding disabled"; Scaffold button disabled. Observed: ______
- [ ] With that Set open, `curl -X POST http://127.0.0.1:8765/api/production/plans -d '{"genre":"House"}'` without a token → 403. Observed: ______
- [ ] Same with a valid token (from `~/.vibelton/session_token`) → 400 "does not look like a working copy". Observed: ______
- [ ] Unsaved (untitled) Set → message says to Save As. Observed: ______
- [ ] Open the working copy: badge turns green; Scaffold enables only after ticking the confirmation box. Observed: ______

## 3. Scaffold and rollback (Task 3)

- [ ] Scaffold the partly-filled Set. Existing clips unchanged; new clips start at bar 33. Observed: ______
- [ ] Manually **move** one placed clip and **add** one new clip of your own. Click Undo: preview shows "Would remove N of M…" naming the moved clip. Observed: ______
- [ ] Confirm. Moved clip and your clip remain; every other placed clip is gone; result message matches. Observed: ______
- [ ] Rollback after restarting the server (then Undo again on a fresh scaffold). Observed: ______
- [ ] Rollback after closing and reopening the Set (Live regenerates track ids). Observed: ______

- [ ] (Skipped sources) On a Set where most clips are looped/stretched, the Scaffold error or preview note names the reason (e.g. "N clips were looped or stretched… Consolidate them in Live (Cmd+J)"), and **Details** lists each track/clip. Observed: ______
- [ ] (Gaps) With a loop longer than the final section, planning succeeds, the preview shows a striped **Gaps** row and a note that the arrangement ends early; only whole clips are placed. Observed: ______
- [ ] (Session-to-Arrangement undo) Place Session clips on the Arrangement, edit one copy, Undo: the edited copy stays, the rest go. Observed: ______

## 4. Things only ears and eyes can check

- [ ] **Automation preservation:** after scaffolding, the Kick filter-sweep automation lane is unchanged (not copied, not extended, not deleted). Observed: ______
- [ ] **Warping:** the warped audio copies keep Warp on and sit in time at 124 BPM; no stretching artefacts introduced by the copy. Observed: ______
- [ ] **Clicks:** play across every section boundary where a stem starts or stops (audio clips especially). Note any audible click, with bar number: ______
- [ ] **Odd loops:** 6-bar and 12-bar sections end where the plan's "unfilled bars" list says (no half-clips). Observed: ______
- [ ] **Locators:** the plan notes section cues are not created as Live locators (current behaviour). Observed: ______

## 4b. Phrase boundaries and cuts (Task 9)

Section lengths now snap to 8-bar phrases (4-bar for short arrangements), so totals move to the nearest phrase
(e.g. 101 → 104 bars at 124 BPM). The plan lists every stem entry/exit and asserts each clip edge is on a bar line.
This bridge does **not** set clip fades (no verified fade API), so audio cuts rely on bar-line edges only.

- [ ] Every section start lands on a multiple of 8 bars from the scaffold start (check the locators/plan). Observed: ______
- [ ] At each audio stem entry/exit listed in the preview, play 2 bars either side: any click or pop? Bar numbers: ______
- [ ] If clicks occur, note whether the clip has Live's default fade on (Clip view → Fade) and whether adding a short fade by hand removes it: ______

## 5. Section markers (Task 8) — requires the updated Remote Script

Markers are **off by default**: earlier real-Live testing (`PHASE_3B_NOTES.md`) found cue creation did not read back
reliably on Live 12.3.2. The bridge now enables them only after it proves exact readback in your session.

Install first (the installed Remote Script must match the repo, then **restart Live**):
`python3 install_remote_script.py`

- [ ] Before probing: scaffold preview shows "Markers (plan only)" and no cues appear in Live. Observed: ______
- [ ] Run the probe on the working copy (needs the token in `~/.vibelton/session_token`):
  `curl -X POST http://127.0.0.1:8765/api/production/locator-probe -H "X-Vibelton-Token: $(cat ~/.vibelton/session_token)" -H "Content-Type: application/json" -d '{"working_copy_confirmed": true}'`
  then poll `GET /api/production/status/<job id>`. Expected: `locator_probe.passed: true`, and no `VIBELTON_PROBE` cue left in Live.
  Observed (passed / failed / error text / stray cue?): ______
- [ ] If it **failed**: markers stay plan-only. The bridge now makes one best-effort delete of any stray probe cue; check `locator_probe.leftover_cues` (empty = clean) and delete any remaining `VIBELTON_PROBE` cue by hand. Observed: ______
- [ ] If it **passed**: preview now shows "Markers in Live". Scaffold: cues INTRO, GROOVE, MAIN GROOVE, TENSION, BREAKDOWN, DROP, OUTRO sit exactly on each section's first bar with those names. Observed: ______
- [ ] Your own existing cue points are unchanged. Observed: ______
- [ ] Undo removes exactly those cues (and your own remain). Observed: ______
- [ ] Section-only Undo removes only that section's cue. Observed: ______
- [ ] Capability resets after restarting Live (probe again). Observed: ______

## 6. Result

Date: ______  Live version: ______  Set: ______  Tester: ______
Failures / notes: ______
