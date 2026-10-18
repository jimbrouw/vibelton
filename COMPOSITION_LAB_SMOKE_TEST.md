# Composition Lab — real Ableton smoke test

Verified on 11 September 2026 in Ableton Live 12 Suite on macOS, using the local Safari interface and bridge `2026-09-11-composition-1`.

## Preserved working copies

Before writing, the original session was saved as `~/Music/Ableton/Vibelton Before Composition Lab Project/Vibelton Before Composition Lab.als`. All composition work was performed in the separate `Vibelton Composition Lab Working.als` in that folder. No instruments, presets, effects, or mixer settings were written by Composition Lab.

## Results

- Opening preview: revision 1, job `44fa4444-ce65-4716-89fa-cf37d97dc8ad`, two clips, beats 360–416, 20 seconds. Only the selected section looped. Clip readback and original-material preservation passed. Its historical marker checklist remains pending following a bridge restart.
- Full arrangement: revision 2, job `b8e54976-0aa0-4d76-8bd5-749fc63855e2`, 65 clips across 21 sections, beats 424–1096. Exactly 672 quarter-note beats at 168 BPM = 240 seconds. Build left playback stopped and disabled the previous preview loop.
- Every generated clip was read back for notes, metre, length and Arrangement placement. Existing Session and Arrangement clips and instrument/mixer snapshots matched their before-build values.
- All 21 Arrangement time-signature markers were inserted through Live's Create menu at exact generated Strings clip boundaries. The saved Set was inspected read-only to verify every marker position and metre against the compiled plan, including the eight alternating 7/8 + 9/8 exit pairs. Full job status is **Verified**.
- Execution evidence is retained locally in `~/.vibelton/compositions/` and `~/.vibelton/composition-executions/`; development snapshots are in ignored `output/composition-lab/`.
- Safari mode-switch checks passed for Inspiration, Song Maker and The Finisher, including the existing Finisher working-copy prompt. Reloading and reopening Composition Lab retained revision 2, the exact four-minute timing, and the Verified execution result.

## Musical follow-up

The first experiment uses the user's existing percussion, drum, Serum and Meld instruments. Musical-role assignment is separate from sound choice; the user can choose different sounds in Live. No audio analysis or subjective listening assessment was performed. A focused listening revision awaits the user's audition feedback.

## Automated coverage

`python3 -m unittest discover -s tests` covers the existing workflows plus metre conversion, grouping, timing, exact fixture boundaries, note bounds, duration fitting, locks, revisions, safe command generation, duplicate submissions, missing tracks, disconnection, occupied slots, partial failures and bridge readback. The native Live smoke test above complements the in-memory bridge tests.

Final result: **85 tests passed**. JavaScript syntax and whitespace-diff checks also passed.
