# Rollback safety (Arranger scaffold)

## What is stored

Every applied production plan writes, under `~/.vibelton/production/`:

| File | Contents |
|---|---|
| `plans/<id>.json` | The approved actions. |
| `snapshots/<id>.json` | `before` (for arrangement copies: every track with its Arrangement clips + fingerprints, and the locators), `inverse_actions`, `session_id`, `set_path`, `source_revision`. |
| `jobs/<id>.json` | Job status, `snapshot_id`, `set_path`, and (for rollbacks) `rollback_report`. |
| `placements/<job>.json` | One **placement record** per clip the bridge reports it actually created: track id, track name, track index, clip name, `destination_beat`, `end_beat`, `source_start_beat`, `source_fingerprint`, `set_path`. |
| `queue/production-executions/<job>.json` | What the Remote Script did (`created_copies`, `status`, `deleted_copies`, …). |

All of it is on disk, so rollback works after a server restart. Placement records are built from
`created_copies` (what Live confirmed), never from the plan, so a scaffold that failed halfway lists
exactly the clips that really exist. If Live crashes before it writes the execution file there is no
record of what was placed; rollback then refuses rather than guessing.

## What rollback deletes

Before queueing anything, rollback re-reads the Arrangement from Live and checks each recorded clip
(`vibelton/rollback_safety.py`). A clip is removed only if **all** of these hold:

1. its track still exists (matched by id, or by unique name if Live regenerated ids after reloading the Set);
2. exactly one clip starts at the recorded position and its content fingerprint equals the recorded one;
3. its end matches the recorded end (not resized);
4. no other clip overlaps it;
5. it is not the source loop of any recorded copy (your original loops are never deletable);
6. its source loop is still intact (the Remote Script requires this).

Anything else is **skipped and reported** (`edited`, `moved_or_deleted`, `overlapped`, `source_changed`,
`track_missing`, `is_source`). Clips you added are never in the record, so they are never touched.
Only cue points that still exist exactly as created are removed.

Result text, e.g.: `Removed 41 of 43 clips. 2 skipped because you edited them: Kick bar 17, Bass bar 33.`

## Dry run

`POST /api/production/rollback` (or `/plans/<id>/rollback`) with `"dry_run": true` returns what would be removed and
skipped without creating a plan, snapshot or job and without queueing anything. The device shows this
summary and asks for **Confirm undo** before the real rollback is sent.

## Exact-state check

The Remote Script verifies the whole Set against an expected hash after deleting. With skipped clips the
expected state is no longer the original, so the server derives it from the current Live state minus the
clips being removed. If everything is removed and nothing else changed, the originally captured hash is used.

## Session-to-Arrangement copies

`apply_session_to_arrangement_copies` jobs use the same per-clip rollback, placement records, dry run and
exact-state check. Their records carry `source_scene_index` instead of an Arrangement source position, so the
"source intact" test (6) checks that the Session clip in that scene still has the recorded fingerprint, and the
"is the source loop" test (5) does not apply. These jobs have no sections; `section` is refused for them unless
the plan recorded sections. No Remote Script change was needed: its rollback already accepts a subset of copies.

## Sections and markers

* Each placement record carries its `section`; `POST /api/production/rollback` with `section` (plus `genre` and
  `variant_id`, or a `job_id`) removes only that section's clips. Removed records are remembered (`removed` in
  `placements/<job>.json`) so a later whole-job rollback never reports them as missing.
* Section markers (Live locators) are created only when the bridge advertises `arrangement_locator_readback`,
  which becomes true only after a `locator-probe` job passes in the current Live session. Markers belong to the
  whole arrangement for a full rollback and to their own section for a section rollback. Your own cue points are
  never touched; a marker you deleted or renamed is reported as missing and skipped.

## Not covered by this change

* Session-scene, song-sketch-template, mixer and device-parameter jobs keep the previous strict rule:
  rollback is refused if Live's state changed after the job. Only Arrangement copy jobs get per-clip handling.
* Session-to-arrangement copy jobs (`apply_session_to_arrangement_copies`) are not yet per-clip.
* Rolling back onto a different Set is refused when both Set paths are known (Task 4 adds the working-copy gate).

## Verification status

* Verified by unit tests (`tests/test_rollback_safety.py`, fake bridge that enforces the same checks as the
  Remote Script, including the exact post-rollback hash): clean rollback; partial scaffold; edited clip skipped;
  moved clip skipped; user-added clips untouched; overlap; rebuilt after losing the placement file; Live reload
  with regenerated track ids; dry run makes no changes (Session-to-Arrangement: `tests/test_rollback_session_to_arrangement.py`); different Set refused; source loop never removable.
* **Not verified in Live.** Manual check on a `vibelton-working-copy` Set (record what you observe):
  1. Scaffold. 2. Drag one placed clip to a different bar and add one new clip of your own on any track.
  3. Click Undo and read the preview. 4. Confirm. Expected: moved clip and your new clip remain; all other
  placed clips are gone; the message names the moved clip. Restart the server first (it must run this code).
