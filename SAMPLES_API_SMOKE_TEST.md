# Sample API evidence — 1 October 2026

## Observed

- The required Python unittest discovery passed 152 tests, including the new
  sample service, HTTP catalogue/metadata/range playback and audio bridge fixtures.
- Reserved prototype range tests passed for layering, stale sessions, tampered
  reservations and out-of-range imports.
- Syntax compilation and whitespace checks passed for edited code.
- Updated local HTTP server restarted on `127.0.0.1:8765`; catalogue and metadata
  were subsequently read through its API.
- Zero-G Total Drum Bass contains 1,581 catalogued audio files. Its folder names
  include 100 drum loops labelled 170 BPM (tracks 53–62). Eight track-53 candidate
  headers were inspected: all measured 5.647052 seconds at 44.1 kHz, PCM 16-bit,
  mono or stereo. That duration is consistent with four bars at the labelled
  170 BPM; the BPM is not independently detected.
- AMG Prototype Drum & Bass contains 358 catalogued audio files, including bass,
  percussion, atmosphere and FX material. Filenames/categories were inspected.
- Three changed bridge files were staged in the installed Vibelton folder.
  Their bytes matched repository files. Previous installed files were backed up
  under `~/.vibelton/bridge-backups/20261001T191048Z`.
- Before staging, Live had changed from the earlier 43-track, 170 BPM session to
  session `62adda4a-f1d0-47e9-a3cf-9f6987fcdb92`, with 35 tracks, nine scenes,
  140 BPM and Arrangement ending at beat 528. Existing clip metadata and devices
  were inspected through `/api/status`. Arrangement readback was true then.
- At the final check the session had changed again to
  `4386b4b6-5023-4a3d-870d-1a429553e147`, four tracks, eight scenes and 120 BPM.
  Live still reported old loaded bridge `2026-09-25-session-scenes-7`; no
  sample-import or composition jobs were sent. A full application restart is
  needed; opening another Set alone has not activated the staged code.
- The final running HTTP server returned the catalogue and an actual 206 audio
  preview range response containing the original WAV header bytes.

No computer use, Live restart, Set-save action, subjective audition, audio render,
mix or new musical placement was performed during this implementation.

## Pending real-Live smoke checks

1. Preserve the original, save/open a clearly named working copy and restart Live
   to load bridge `2026-10-01-audio-import-8`.
2. Inspect the fresh session, active Set path, target capabilities and all readback
   errors. Investigate actual exceptions rather than assuming group-track behavior.
3. Import one selected loop with explicit warp state and confirmed source BPM.
   Check durable job status and actual source/settings/warp-map readback.
4. If native auto-warp differs from confirmed timing, inspect the partial result;
   do not retry or make an Arrangement copy without resolving the limitation.
5. Verify one fresh Arrangement copy, then the 16-bar musical prototype step by
   step. Actual Live behavior may differ from the contract fixtures.
6. Let the user audition before expansion; perform mixing separately afterward.

## Implementation lesson

Never use an unwarped audio clip's seconds as Arrangement beats. Arrangement
imports require explicit warping and verified source timing. A Warp checkbox
alone does not prove musical synchronization.
