# Phase 3B — Arrangement copy acceptance notes

## Club benchmark

The disposable Live benchmark is Classic House Club at 124 BPM and 144 bars.
It uses one existing 16-bar Arrangement MIDI source at beat 0 and eight exact,
non-overlapping copies at beats 64 through 512. The source and every copy must
share the same full clip fingerprint.

## Locator capability decision

Ableton Live 12.3.2 exposes `Song.set_or_delete_cue`, but native cue creation
did not read back the requested cue positions and names deterministically after
the arrangement reached its intended length. Phase 3B therefore advertises
`arrangement_locator_readback: false` and does not create native locators.

The seven intended locator definitions remain durable arrangement-plan and
execution metadata, together with this user-facing warning:

> Arrangement locators were not created because this Ableton Live Remote Script
> cannot read them back deterministically.

Native locator mutation may be enabled only by a future bridge capability that
has passed exact position/name readback in real Live. It is not approximated
with UI automation or placeholder clips.

## Final real-Live acceptance (2026-09-24)

On a fresh disposable 124 BPM Set, the production bridge created eight copies
at beats 64, 128, 192, 256, 320, 384, 448, and 512. Readback confirmed nine
contiguous 64-beat clips ending at beat 576; every copy and the original had
the same full source fingerprint. No native locator, note, device, routing,
automation, or extra track was created. Repeating the same plan was rejected
before mutation.

Rollback then deleted exactly those eight recorded copies and passed bridge
readback. The Set returned to its original single clip at beats 0–64 and its
original production revision. Live retains an internal extended song length
after deleted Arrangement content; that changes only the bridge's derived
`locator_range` capability. Rollback compares all observable Set content while
excluding that runtime capability field; ordinary full-revision preflight still
rejects stale state before any mutation.
