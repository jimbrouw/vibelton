# Codex operating instructions for Vibelton

## Purpose

Use Vibelton as the structured control layer for Ableton Live. Use computer use for Ableton or plug-in interactions that the bridge cannot perform, and for visible verification of the result.

## Start of every Ableton task

1. Read `README.md`, `COMPOSITION_LAB.md`, and the relevant smoke-test notes.
2. Check `http://127.0.0.1:8765/api/status` before sending commands. Confirm `connected: true`, note the `session_id`, bridge version, tempo, tracks, and capabilities.
3. Preserve the user's original Set. Work in an explicitly named copy before making musical changes. Do not overwrite, rename, or delete the original Set.
4. Inspect the current Live state and existing musical material before proposing or applying changes.

## How to control Live

- Prefer the Vibelton local API and queue for exact MIDI notes, clip timing, metre, arrangement placement, transport, mixer values, and other supported actions.
- Prefer Composition Lab for original MIDI composition on existing instruments. Save a revision, compile it, apply it to a confirmed working copy, then check job status and readback.
- Use computer use for browser navigation, plug-in windows, unsupported device/effect operations, export dialogs, and visual checks in Live.
- Do not reinstall the Remote Script when the installed copy matches the repository. The installer replaces the installed `Vibelton` folder and requires a Live restart.
- Never expose `.env.local`, API keys, or other secrets.

## Musical workflow

1. Establish the brief from the user's musical references, constraints, protected material, target duration, and desired level of experimentation.
2. Build one short musical prototype first, normally 8 to 16 bars. Compose actual notes and rhythms and develop the instrument or sample treatment; do not treat clip duplication or randomisation as composition.
3. When useful, create two or three meaningfully different alternatives. Change musical logic, density, metre, phrasing, harmony, timbre, or interaction between parts.
4. Let the user audition the prototype before expanding it into a full arrangement unless they explicitly ask for autonomous completion.
5. Develop variations so repeated sections have a reason to return. Preserve groove anchors while changing fills, ghost notes, bass answers, orchestration, automation, and transitions.
6. Arrange only after the core musical idea works. Mix and master as separate passes.

## Verification

- Apply one reversible musical step at a time and verify it through Vibelton state/events and visible Ableton state.
- Treat intended actions, queued actions, successful bridge execution, visible placement, and satisfactory sound as separate claims.
- Do not claim to have heard or mastered audio unless an actual render was analysed and the user auditioned it. Use measured evidence for loudness, true peak, clipping, silence, and channel problems; use the user's listening feedback for musical judgement.
- After code changes, run `python3 -m unittest discover -s tests`. For Live changes, follow the relevant real-Ableton smoke test and record only evidence actually observed.

## Repository safety

The repository may contain active uncommitted Composition Lab work. Preserve all existing changes. Do not reset, clean, pull over, or replace them. Avoid editing unrelated files.
