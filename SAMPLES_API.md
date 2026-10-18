# Vibelton local sample API

Added 1 October 2026. The HTTP server exposes loop discovery independently of the
Live bridge. Audio mutations require bridge `2026-10-01-audio-import-8`, an actual
runtime `audio_import_v1` capability and complete Arrangement readback.

## Read-only endpoints

- `GET /api/samples?query=<substring>&offset=0&limit=100`: paginated audio files
  beneath `~/Music/LOOP PACKS` and the user-approved
  `~/Music/Shadow Samples - UK Bass Vol. 1`. The response includes `roots`.
  Maximum page size is 500. Outside symlinks are
  excluded. Results are filenames and file sizes, not listening judgements.
- `GET /api/samples/metadata?path=<URL-encoded absolute path>`: SHA-256, measured
  duration, channels, sample rate and codec from the installed `ffprobe` utility.
  BPM numbers in filenames are labelled hints; no beat detector is used.
- `GET /api/samples/audio?path=<URL-encoded absolute path>`: original audio bytes,
  including single HTTP byte-range requests for audition and seeking.
- `GET /api/status`: additionally reports `set_path`, per-track
  `arrangement_errors` and runtime audio import availability after bridge reload.

## Import a new clip

For a layered prototype, first call `POST /api/samples/region` with
`session_id`, `source_revision`, `expected_set_path`, `working_copy_confirmed`,
`start_beat` and `length_beats`. The range must start at least four beats after
the current Arrangement end. This stores a reservation without changing Live.
Reserve it before writing complementary MIDI. Include its returned `id` as
`region_id` on subsequent audio imports. The bridge checks the durable reservation,
session, Set path, range bounds and empty destination on the target track. This
permits layering over earlier newly written prototype parts on other tracks and
placing adjacent loop variations without overwriting any existing target clip.
Pass the same `region_id` to `/api/composition/apply` to place complementary MIDI
at the reservation's exact start. MIDI must be applied first, while the whole
range is still empty; audio can then be layered onto its own empty target lanes.

`POST /api/samples/import` accepts this JSON shape:

```json
{
  "session_id": "<current Live session ID>",
  "source_revision": "<state.production.revision>",
  "expected_set_path": "/absolute/path/to/Named Working Copy.als",
  "working_copy_confirmed": true,
  "path": "/Users/standard/Music/LOOP PACKS/<chosen loop>.wav",
  "track_id": "<existing non-group audio track ID>",
  "scene_index": 9,
  "name": "DnB prototype break",
  "source_bpm": 170,
  "settings": {
    "warping": true,
    "looping": true,
    "start_marker": 0,
    "end_marker": 16,
    "loop_start": 0,
    "loop_end": 16,
    "pitch_coarse": 0,
    "gain": 0.7
  },
  "arrangement_beat": 536
}
```

Use the current `scene_count` as `scene_index`. Exactly one new scene is appended;
occupied slots are never overwritten. `arrangement_beat` is optional and must
be at least four beats beyond the observed Arrangement end unless a reserved
prototype range is supplied. Set filenames and
scene numbers above are examples, not claims about the active Set.

`warping` must be explicit. Warped marker units are beats; unwarped units are
seconds. Unwarped imports are Session-only. `source_bpm` is required for warped
imports. Observed warp-marker timing must match that BPM within 0.01 beat; the
executor does **not** infer or rewrite a file's warp-marker timing. If Live's
auto-warp result differs, it stops before Arrangement copy and reports the
already-created scene/clip as a partial failure. No silent retry occurs.

Marker positions are bounded by measured source duration (converted to beats
using confirmed source BPM for warped audio). Other supported new-clip settings
are `pitch_fine` and `warp_mode`. Sound-device insertion, device automation,
audio slicing/resequencing, warp-marker rewriting, Save As, opening Sets and
render/export remain unsupported. Configuration affects only the imported clip.

The response includes a durable job ID. Read `GET /api/samples/status/<job_id>`.
The bridge verifies source hash/path, settings, warp timing, optional Arrangement
placement and preservation of existing clip content/positions, scenes,
instruments, mixers and tempo. Audio fingerprints include source path, markers,
warp mapping/mode, transpose, detune and gain; MIDI fingerprints remain unchanged.

Statuses distinguish `Queued`, `Applied`, `Failed`, `Partial failure` and
`Interrupted`. `Applied` requires readback, not just queue acknowledgement.
Recorded job IDs cannot replay. Partial failures leave their recorded new
material for inspection; no automatic deletion is implemented.

## Additional approved library

The server catalogues the Shadow library without moving its originals. When
importing from it, the server stages only the selected file in
`~/Music/LOOP PACKS/.vibelton-imports/<sha256>.<extension>`. The bytes must match
the metadata hash; existing mismatching files and destination symlinks are
rejected. This cache is omitted from catalogue results. `job.source.path`
retains the original path, while `job.action.path` records the bridge's verified
copy. The installed bridge's original library guard is unchanged; no Live
restart is needed for this server extension.

Unwarped imports remain Session-only in the guarded sample API. The existing
`copy_session_to_arrangement` queue command can place them, but it has no durable
sample placement job or automatic collision/preservation guard. Actual native
Arrangement length may exceed the selected marker range. Generic repeat-copy
content checks also failed for an unwarped snare during the Shadow prototype.
Treat that path as unverified for repeatable content, inspect partial results,
and do not blindly retry. Warped imports succeeded for kick, snare, hat and
percussion one-shots with actual verified 170 BPM maps; the selected sub sample
failed both 170 and its filename's 125 BPM guard. Warp rewriting remains
unsupported.

## Activation and preservation

Server code requires a server restart. Bridge code requires updating the
installed files and restarting Live; session and track IDs must then be refreshed.
The 1 October update was staged with a backup of existing installed files.

`working_copy_confirmed` is a human acknowledgement. Active-path equality
guards the destination but cannot prove that the original was preserved.
Save/open a separate named working copy manually before authorizing any music
job. The server cannot perform native Save As or restart Live.

Composition Lab now accepts 4/4 scores alongside its existing metres, allowing
complementary original MIDI in a steady 4/4 prototype. Full Arrangement readback
is still mandatory; diagnostic errors never weaken that guard.

See `SAMPLES_API_SMOKE_TEST.md` for observed evidence and pending real-Live checks.
