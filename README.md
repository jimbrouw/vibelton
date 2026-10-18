# Vibelton

A local natural-language copilot for Ableton Live 12.

**Composition Lab** adds a separate fourth tab for original MIDI compositions with changing metres, locked parts, local revisions, and preserved user instruments. See [the workflow and local API](COMPOSITION_LAB.md) and [real Ableton verification](COMPOSITION_LAB_SMOKE_TEST.md).

Natural-language control for Ableton Live 12 on macOS and Windows.

This project has two active parts:

- `vibelton/server.py`: local chat app and action planner.
- `ableton_remote_script/Vibelton`: Ableton Control Surface script that runs inside Live and executes queued actions.
- `vibelton/music_theory.py`: reusable music theory brain for scales, relative keys, diatonic chords, rhythm feels, voice roles, and vibe-based progression recipes.

`Vibelton` is the canonical Remote Script for V2.1 work. The old `AbletonCopilotArranger` script has been moved to `legacy/` because it does not contain the current Finisher duplicate/mute actions.

The current working surface covers tempo, playback, tracks, scenes, MIDI clips, generated chord progressions, basslines, melodies, volume, pan, sends, arrangement copy, stock-instrument browser candidates, and Finisher mutations. Device/effect insertion is represented in the action schema but is still marked as unsupported until a verified Live 12 device-browser route or a Max for Live helper is added.

## Quick Start

1. Install the Remote Script into your Ableton User Library:

   ```bash
   python3 install_remote_script.py
   ```

2. Open Ableton Live 12.
3. Go to `Settings -> Link, Tempo & MIDI`.
4. Choose `Vibelton` in a Control Surface slot.
5. Start the local chat app:

   ```bash
   python3 -m vibelton.server
   ```

6. Open `http://127.0.0.1:8765`.

## Arrange a selected map in Live

In **Production → Arrange**, choose a style and one of its three bar maps. Select the existing Arrangement clips and the roles they should play, then review the exact section placements and any unfilled bars. Vibelton copies those clips into a new range after the current Arrangement; it does not replace the original material or generate new notes. Save and open a named working copy of the Set before pressing **Apply to working copy**. Check the job result before treating the placement as complete. **Roll back recorded changes** deletes only the copies the bridge reports creating.

Choose **Build in → Session View scenes** when the material lives in Session View. The source picker lists every Live track, including tracks with no Session clips. Assign a role and a source clip, then review a seven-scene plan. Apply appends new named scenes and duplicates the selected clips into their matching section roles; the original scenes and clips stay in place. Rollback deletes the recorded new scenes if they have not been changed. The bar counts are scene labels and arrangement guidance: Live continues looping the clips until you launch another scene. Session scene execution requires the `session_scene_v1` bridge capability and a Live restart after installing this Remote Script update.

The Arrangement timeline path requires the `arrangement_copy_v2` Live bridge capability. After updating the Remote Script, restart Ableton Live and draft a fresh map for the new session. Existing locators remain untouched; planned section cues are review metadata because native locator readback is not deterministic. Whole-bar Arrangement source clips of up to 16 bars are supported; clips with extended loop regions are not currently Arrangement copy sources. Unfilled roles and bars are shown in the plan for musical review.

## Optional ChatGPT Planning

Set an OpenAI API key before starting the server:

```bash
export OPENAI_API_KEY="your_key_here"
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your_key_here"
```

Without an API key, the app uses a deterministic local planner for common music commands.

## Music Theory Brain

Vibelton now has a deterministic backend theory layer that can be used by the planner, mentor features, and future UI panels.

It covers:

- major/minor scale notes
- relative major/minor shortcuts
- circle of fifths sharp/flat order
- diatonic chord maps
- chord qualities from intervals
- bass, tenor, alto, and soprano producer roles
- downbeat, upbeat, and syncopated rhythm feels
- vibe-based progression recipes

Backend endpoint:

```bash
curl -X POST http://127.0.0.1:8765/api/theory \
  -H "Content-Type: application/json" \
  -d '{"root":"A","mode":"minor","message":"sentimental romantic progression"}'
```

You can also ask the chat planner theory questions such as:

```text
Explain the music theory brain for C major and circle of fifths.
Make a sentimental romantic chord progression generator in A minor.
```

## Example Prompts

- `Set tempo to 124 BPM and create a 4 bar Am F C G chord progression.`
- `Add a bassline in A minor for 8 bars.`
- `Create drums and start playback.`
- `Make a track called Soft Keys and add a C major melody.`
- `Set Soft Keys volume to -8 dB and pan it left 20.`
- `Create an expanded 125 BPM house song sketch with genre-aware Ableton instruments and copy it to Arrangement View.`
- `Humanize the drums and add ghost notes.`

## V2.1 Smoke Test

Run the five prompts in `SMOKE_TEST.md` after each stage branch. Record Ableton-specific results in `LISTENING_NOTES.md`.

## Demo Set

The curated V2.1 demo prompts live in `demos/README.md`. Ableton sets and 30-second renders are pending.

## Device Chains

Stage 1.5 sound-chain targets live in `device_chains.json`. The current entries are manual-load placeholders until `.adv` files are created and tested in Ableton Live.

Focused Finisher checks live in `FINISHER_SMOKE_TEST.md`.

## Local Tests

Run:

```bash
python3 -m unittest discover -s tests
```

The current tests check deterministic Finisher output and planner action types against the canonical bridge.

## Known Limits

- [Unverified] Stock-instrument loading depends on Ableton's browser search API and local library contents.
- Device insertion is logged as unsupported by the current bridge.
- [Unverified] Arrangement copy depends on the current Live build exposing `duplicate_clip_to_arrangement`.
- [Unverified] Listening-panel results have not been collected yet.
- [Unverified] Demo `.als` files and audio renders have not been created yet.

## Queue Files

The server and Ableton bridge communicate through:

```text
~/.vibelton/commands.jsonl
~/.vibelton/events.jsonl
~/.vibelton/state.json
```

This keeps the first bridge dependency-free inside Ableton's Python runtime.

## V2 production desk

The Production tab offers six selectable arrangement styles: House, Drum & Bass, Techno, UK Garage, Hip Hop, and Disco / Nu-disco. Each has three deterministic, read-only bar maps and a matching Finish Track structural diagnosis. Tempo can suggest a style when the range is distinctive; overlapping ranges are shown as possibilities because BPM does not identify a genre. The user always chooses the style and map.

These maps reuse existing material as planning references. They do not generate notes or apply clips. Only the verified House Club copy workflow currently has a Live execution path, limited to a 124 BPM, 4/4 Set with one fingerprinted 16-bar source loop at beat 0. Other styles remain planning-only until separately verified bridge execution exists.
