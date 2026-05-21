# Vibelton Finisher Smoke Test

[Unverified] These prompts need to be run inside Ableton Live against an existing Session View loop set.

The Finisher is not mainly a mutation tool. Its main job is to help turn existing Session View loops into a non-destructive Arrangement View structure.

## Product Shape

- Use clips that already exist in Session View.
- Ask follow-up questions when the requested arrangement is underspecified.
- Copy clips into Arrangement View without deleting or changing Session View clips.
- Open Arrangement View and start at bar 1.
- Optionally rename generic tracks from loaded devices when Live exposes device names.
- Later: edit an existing Arrangement View structure without destroying the source material. [Unverified until bridge support is probed]

## Setup

1. Create or load a Live set with several Session View loops.
2. Use simple or badly named tracks such as `MIDI 1`, `Audio 2`, or `Track 3`.
3. Load at least one instrument or drum device on a badly named MIDI track.
4. Keep the local Vibelton server running.
5. In the UI, switch to `The Finisher`.

## Prompts

1. `Finish my existing Session View loops into a house arrangement.`
2. `Arrange my existing loops as a DJ-friendly techno structure and start from bar 1.`
3. `Finish my Session View loops as a hip-hop beat with intro, verse, hook, verse two, final hook, and outro.`
4. `Rename the badly named tracks based on the loaded instruments, then arrange my existing loops.`

## Pass Notes

- Session View clips remain in place.
- Arrangement View opens.
- Clips are copied into a genre-shaped structure.
- Playback starts from bar 1.
- Generic track names are renamed only when a loaded device gives a useful clue.
- The bridge reports command completion or a clear unsupported-action event.

## Current Known Limits

[Inference] The current bridge can copy Session View clips to Arrangement View through `duplicate_clip_to_arrangement`. It does not yet read clip content semantically, ask multi-turn questions, or make deep arrangement edits to existing Arrangement View material.
