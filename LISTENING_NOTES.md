# Listening Notes

[Unverified] No external listening-panel A/B tests have been run yet.

Panel target for V2.1: Jim plus two producer friends.

| Date | Stage | Material | Reference | Listeners | Result | Notes |
|---|---|---|---|---|---|---|
| 2026-05-01 | Stage 0 / README smoke flow | README and smoke-test prompts | Not applicable | Jim | Passed | User reported everything in the smoke test / README is working. Two routing issues were found and fixed: `Create house drums for 4 bars.` now stays drum-only; `Make a track called Soft Keys and add a C major melody.` now creates one named melody track. |
| 2026-04-30 | Stage 1 | 10 demo prompts | Not applicable | Jim | User smoke pass with rough edges | User ran all 10 demo prompts in Ableton. Prompts generated usable results overall, with rough edges around playback start position, empty hat racks, chord instrument loading, and genre sameness on trap/ambient. Follow-up patches were made on 2026-05-01. Audio renders are still pending. |
| 2026-04-30 | Stage 1 API check | Feedback endpoint and Finisher chat prompt | Not applicable | Not applicable | Local server passed | Local-only check: `/api/feedback` accepted an `up` rating; `/api/chat` returned supported Finisher actions. This does not confirm Ableton playback or musical quality. |
| 2026-04-30 | Stage 1.5 | 15 device-chain targets | Not selected | Not selected | Placeholder targets only | `device_chains.json` has 15 manual-load target descriptions. Real `.adv` files and reliable bridge chain loading are still pending. |
| 2026-04-30 | Stage 2 local generation | GrooveProfile templates and generated note bounds | Not selected | Not selected | Local tests passed | Groove templates, velocity shaping, seeded drum mutation, and profile-aware Finisher humanisation added. Listening panel still pending. |
| 2026-05-01 | Stage 3 harmony fallback | Harmony module, colour parsing, voice leading | Not selected | Not selected | Local tests passed | `harmony.py` added with optional lazy `music21`; fallback voice-leading, genre-weighted progressions, inversions, and colour knob tests pass without `music21` installed. |
| 2026-05-01 | Stage 1 demo smoke pass | 10 Vibelton demo prompts in Ableton | Not applicable | Jim | Needs patch | User reported all demo prompts starting playback around bar 52, prompt 3 hat racks loading empty, prompt 7 chords getting only FX, and prompts 5/8 sounding too harmonically similar. Patched explicit playback reset, safer stock instrument candidates, and stronger trap/ambient harmonic cues. |
| 2026-05-01 | Stage 3 melody shaping | Generated house, trap, and ambient hooks | Not selected | Not selected | Local tests passed | Added deterministic melody contour, rest-density, and phrase-ending rules. Local generation check showed house hooks denser than trap and ambient endings held longer; Ableton listening test still pending. |
| 2026-05-01 | Stage 4 Finisher reframing | Existing Session View loop arranger | Not applicable | Jim | Requirements clarified | User clarified The Finisher should arrange existing Session View loops non-destructively, ask follow-up questions when needed, open Arrangement View, optionally edit existing arrangements later, and rename badly named tracks from loaded devices where possible. |
