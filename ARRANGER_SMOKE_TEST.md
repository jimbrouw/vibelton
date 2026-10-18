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

Date: 2026-10-18  Live version: 12.3.2  Set: `shape change vibelton-working-copy .als` (real 22-track Set, not the edge-case Set)  Tester: the user, with Claude driving the server/API checks
Failures / notes: see section 7.

## 7. Observed results, 2026-10-18 (Live 12.3.2)

Only what was actually observed. Anything not listed was **not run**. The edge-case Set from section 1 was not built;
everything ran on the user's real working copy, so audio-specific checks (4, 4b) could not be exercised.

### Passed in Live
- **Install (B1):** `GET /api/versions` → `ok: true`; running Remote Script `2026-10-18-markers-2` matches the repo;
  the device announced itself (`versions.device.loaded`) as `2026-10-18-arranger-8`. No warnings.
- **Safety gates (section 2):** untitled Set → red "Original Set — scaffolding disabled (Untitled Set)", Scaffold greyed,
  POST without token → "Missing or invalid session token", POST with token → "This Live Set is unsaved… Save Live Set As…".
  Working copy → green "Working copy" badge; Scaffold needs the confirmation box.
  **Not run:** a Set whose name does *not* contain `vibelton-working-copy` (the original), by choice.
- **Skipped-source note (A2):** preview on the real Set said "17 clips were not used as sources: 13 looped or stretched,
  4 not a whole number of bars."
- **Scaffold, edit, undo (section 3):** 13-clip scaffold placed and read back ("Verified"). After moving one placed clip and
  adding one of the user's own, the undo dry run said "Would remove 12 of 13 clips. 1 would be skipped because they were
  moved…"; the real undo removed 12, kept the moved clip and the user's clip, and the bridge verified the exact state.
- **Undo after a server restart:** server killed and restarted (new process); the 13 placement records survived; undo
  removed 13 of 13.
- **Undo after reopening the Set:** dry run 13 of 13, real undo 13 of 13. Track ids were still valid after the reopen
  here, so the regenerated-id path is covered only by unit tests.
- **Single section:** scoping to Groove placed 2 clips (bars 145–161, same base as a full scaffold); undoing that section
  removed 2 of 2.
- **Section starts (4b, partial):** scaffold starts landed on 8-bar multiples from the scaffold start (bars 129, 145, 161).
- **Server recovery (B6, partial):** server killed with the device loaded; the device's watchdog brought it back in about
  5 seconds with exactly one server on 8765.

### Failed or not working
- **Marker probe (section 5 / B4): failed, markers stay off.** Run 1: "Cannot set the Songtime behind the Songlength"
  (`leftover_cues: []`, cleanup found and removed a stray cue). Run 2 (playhead at bar 1): Live created the cue at beat 612
  (bar 154, named "1") instead of beat 4, then "Locator deletion readback did not match"; the cleanup did not remove it
  and the user deleted it by hand. `arrangement_locator_readback` stayed false. Consistent with `PHASE_3B_NOTES.md`.
- **Retry button:** pressing Retry did nothing after the server was stopped. The helper's retry handler works when driven
  from outside Max, so the break is somewhere between the page's `window.max.outlet('retry')` and the helper; the cause was
  not found. The helper's watchdog now restarts the server without it.

### Bugs found by this run (all fixed, with tests; commit `7cca6da`)
- The patcher saved `node.script` as a class Max cannot create, so Max deleted every patchcord to it and the helper never
  started (blank panel, no server, no log folder).
- The helper answered `popout` with `open_popout`, which routed straight back into `popout`: thousands of POSTs to
  `/api/popout`, exhausting the rate limit and opening dozens of Chrome windows. The server no longer opens a browser
  unless `VIBELTON_POPOUT_BROWSER=1`.
- Two servers could start at once on a device reload; the second silently took port 8766. A device-started server now
  never falls back to another port.
- A clip the user added on a second track of an already-used role made planning fail with "Choose one valid source clip per
  role". One source per role is used; the other track is reported as `role_already_used`.
- An older job's placement record (a clip the user had moved away) could match a newer job's identical clip at the same
  spot, so undoing the older job could delete it. A newer job now takes over such records.
- The success line said "Placed 1 loop copies" (it counted actions). It now shows the clip count.

### Not verified
- Audio cuts and clicks, warped-audio behaviour, automation lanes, odd-length loop gaps (sections 4, 4b): no audio sources
  were usable on this Set (all MIDI instrument stems; audio clips were looped or not whole-bar).
- Whether an audio clip exposes fade properties (no read-only check was run).
- The striped **Gaps** row in the plan preview (viewed only in unit tests, never in a browser or Live).
- Session-to-Arrangement undo (section 3, last item) and re-scaffolding one section after it was already placed.
- Stale-device warning appearing and clearing (`device_loaded_stale`), and the offline page (`Server offline`) as shown in Max.
- The unexplained "a project without a name is like a day without sunshine. fatal." line in Max's console.
