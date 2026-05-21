# Vibelton User Manual

> **Version:** V2.1 · Ableton Live 12 · macOS

---

## 1. Introduction

Vibelton is a local AI co-pilot for Ableton Live 12. It lets you describe what you want in plain English — "Give me a 8-bar house groove in A minor" — and Ableton responds in seconds with MIDI clips, tracks, tempo, arrangement structure, and mixer settings already placed.

Nothing is sent to the cloud unless you opt in with an OpenAI API key. The default engine runs entirely on your machine.

---

## 2. How Vibelton Works

*(High-level overview for newcomers — one paragraph per point)*

- **You type a prompt** in the Vibelton web UI.
- **The Planner** reads the prompt, detects style and intent, and converts it into a list of Ableton actions.
- **The Queue** writes those actions to a small file on disk (`~/.vibelton/commands.jsonl`).
- **The Ableton Bridge** (a Remote Script running inside Live) polls that file every fraction of a second, executes each action through the Live API, and writes feedback back to `~/.vibelton/events.jsonl`.
- **The UI** shows you the reply and any status messages from Live.

There are two planning modes:

| Mode | When it activates | Notes |
|---|---|---|
| **Local Planner** | Always (default) | Fast, deterministic, no API key needed |
| **OpenAI Planner** | When `OPENAI_API_KEY` is set | Handles complex, multi-step requests |

If OpenAI is configured but fails, the system automatically falls back to the local planner.

---

## 3. System Requirements & Installation

### 3.1 Requirements

- macOS (primary target) or Windows
- Ableton Live 12 (Standard or Suite)
- Python 3.10 or later
- A modern web browser

### 3.2 Installing the Ableton Remote Script

The Remote Script is the bridge that runs *inside* Live and executes commands:

```bash
python3 install_remote_script.py
```

This copies the `Vibelton` folder from `ableton_remote_script/` into your Ableton User Library so Live can find it.

### 3.3 Setting Up Ableton

1. Open **Ableton Live 12**.
2. Go to **Settings → Link, Tempo & MIDI**.
3. In one of the **Control Surface** slots, choose **Vibelton**.
4. Leave the Input and Output set to **None** — Vibelton communicates via files, not MIDI ports.
5. Close Settings. You should see a brief status flash at the bottom of Live saying the bridge loaded.

### 3.4 Optional: OpenAI API Key

To enable AI-enhanced planning (for complex or unusual prompts):

```bash
# macOS / Linux
export OPENAI_API_KEY="your_key_here"

# Windows PowerShell
$env:OPENAI_API_KEY="your_key_here"
```

Alternatively, put it in a `.env.local` file in the project root:

```
OPENAI_API_KEY=your_key_here
```

Without a key, all features work — the local planner handles the vast majority of common requests perfectly.

---

## 4. Running Vibelton

### 4.1 Launching the Server

From the project root, run:

```bash
python3 -m vibelton.server
```

This starts a small local web server on `http://127.0.0.1:8765` and opens your browser automatically.

> **Keep this terminal window open** while you use the app. Closing it stops the server and the Ableton bridge will no longer receive commands.

Alternatively, double-click **Start Vibelton.app** if the launcher app has been set up on your machine.

### 4.2 The Web UI

The chat window at `http://127.0.0.1:8765` is the main interface. Type a prompt and press Enter (or click Send). The panel on the right shows recent events from Ableton — use this to confirm that actions were received and executed.

---

## 5. Typing Prompts — The Basics

Vibelton understands natural language. You do not need to learn special commands.

### 5.1 What You Can Ask For

| Task | Example prompt |
|---|---|
| Set tempo | `Set tempo to 128 BPM` |
| Create a chord progression | `Make a 4-bar Am F C G chord progression` |
| Add a bassline | `Add a bassline in A minor for 8 bars` |
| Add a drum beat | `Create drums` |
| Add a melody | `Add a lead melody in C major for 4 bars` |
| Control the mixer | `Set the Pad volume to -6 dB and pan it left 20` |
| Generate a full song sketch | `Give me a quick UK Garage sketch at 132 BPM` |
| Copy to Arrangement View | `Finish my existing session loops as a house track` |
| Ask theory questions | `What are the diatonic chords in D minor?` |

### 5.2 How the Planner Reads Your Prompt

The local planner detects:

- **Key and mode** — looks for note names followed by "major" or "minor", or mood words like "dark" (→ minor) 
- **Bars** — numbers followed by "bar" or "bars"
- **BPM** — numbers followed by "BPM" or "bpm"
- **Genre** — style words like "house", "techno", "DnB", "trap"
- **Intent** — words like "chord", "bass", "drum", "melody", "arrangement", "humanize"

If your prompt is ambiguous, the planner makes a sensible default (usually A minor, 4 bars, House style).

---

## 6. Styles (Genre Profiles)

Vibelton ships with built-in genre "DNA" profiles that shape every aspect of the generated music — tempo range, groove, drum patterns, bass patterns, chord voicings, and lead phrases.

### 6.1 Available Styles

| Style | Typical BPM | Groove | Character |
|---|---|---|---|
| **House** | 120–128 | Straight | Four-on-the-floor kick, rolling bass, offbeat open hats |
| **UK Garage** | 128–136 | UKG shuffle | Skippy 2-step kick, syncopated bass, jazzy 7th/9th chords |
| **Drum & Bass** | 170–180 | DNB tight | Fast broken kick, rolling sub/Reese bass, busy 16th hats |
| **Jungle** | 160–175 | DNB tight | Chopped breakbeat, dub-influenced melodic bass |
| **Techno** | 125–140 | Straight | Relentless four-on-the-floor, minimal acid bass, driving 16ths |
| **Trance** | 136–142 | Straight | Four-on-the-floor, uplifting arpeggio lead, sustained pads |
| **Trap** | 130–150 | Trap triplet | Half-time snare, long 808 bass, fast hat rolls |
| **Grime** | 138–142 | Straight | Sparse 140 BPM kick, raw square-wave bass, icy stabs |
| **Dubstep** | 138–142 | Straight | Half-time boom-clap, wobble/growl bass, sub underneath |
| **Hip-Hop** | 80–100 | MPC 58% swing | Boom-bap kick, classic backbeat snare, sampled-feel bass |
| **Reggaeton** | 88–100 | Dembow | Dembow kick pattern, syncopated bass, off-beat stabs |
| **Downtempo** | 80–100 | MPC 58% swing | Slow, relaxed groove, long-note bass, lush pads |
| **Ambient** | 60–90 | Straight | No drums, drone bass, long sustained chords |
| **Pop** | 96–120 | Straight | Clean four-on-the-floor, simple quarter-note bass, stepwise melody |
| **Afrobeats** | 100–115 | Dembow | Syncopated clave kick, melodic bass, shaker-led 16ths, polyrhythm |
| **Amapiano** | 110–115 | UKG shuffle | Four-on-the-floor with log-drum bass riffs, jazzy piano chords |

Aliases like `dnb`, `drum and bass`, `2-step`, `UKG`, and `hip-hop` all resolve correctly.

### 6.2 How Styles Affect Generation

Each style profile defines:

- **Kick patterns** — multiple alternatives selected by a deterministic seed
- **Snare/clap patterns** — including ghost-note variants
- **Hi-hat patterns** — straight, offbeat, 16th, or triplet
- **Groove profile** — timing jitter, velocity curve, push/pull per subdivision
- **Bass octave and patterns** — style-specific note sequences with interval movement
- **Chord octave, style (stab, pad), rhythm, and extensions** — e.g. UK Garage adds 7ths and 9ths
- **Lead phrases** — melodic shapes characteristic of the genre

When no style is found in your prompt, Vibelton defaults to **House**.

---

## 7. Song Maker (Expanded Song Sketch)

The Song Maker is triggered when you ask for a full track or song sketch rather than a single part.

### 7.1 Triggering the Song Maker

Prompts like any of the following activate it:

- `"Give me a quick house sketch"`
- `"Create a full drum & bass song"`
- `"Make a production sketch"`
- `"Inspirational DnB track at 174 BPM"`
- `"Song sketch in B minor"`

### 7.2 What It Creates

Depending on the detected genre, the Song Maker generates:

1. **Multiple MIDI tracks** — typically Drums, Bass, Chords, Lead (and sometimes Pad, FX, Riser, Crash)
2. **Session View clips** — one per track, placed in labelled scenes (Intro, Groove, Drop, Break, Drop 2, Outro)
3. **An Arrangement View layout** — clips are copied to the timeline with correct start positions
4. **Playback** — transport jumps to beat 0 and starts playing automatically

### 7.3 Arrangement Templates

Each genre has a built-in arrangement template. For example:

**House:**
> DJ Intro (8 bars) → Groove (8) → Verse (16) → Build (8) → Drop/Chorus (16) → Breakdown (8) → Drop 2 (16) → Outro (8)

**Trap:**
> Intro (4) → Verse (16) → Pre-Hook (4) → Hook (8) → Verse 2 (16) → Outro (4)

**Ambient:**
> Texture (8) → Pulse (8) → Theme (16) → Drift (8) → Bloom (16)

Each section specifies which track roles are active (Drums, Bass, Chords, Lead, Pad, Vocal, FX, Other) — tracks not in a section are silenced in Arrangement View, creating natural build-up and drop-down dynamics automatically.

### 7.4 Energy Levels

Parts adjust their density and velocity based on the section energy:

| Energy | Effect on MIDI |
|---|---|
| `intro` | Sparser notes, lower velocity, longer durations |
| `build` | Velocity increases bar-by-bar, denser hats |
| `main` / `drop` | Full density, full velocity |
| `break` | Stripped back, long notes, lower velocity |

---

## 8. Inspiration Mode

Inspiration mode is closely related to the Song Maker. It activates when your prompt contains words like **"inspiration"**, **"inspirational"**, **"reference song"**, or **"quick idea"**.

### 8.1 What It Does

*(To be written — describe how Inspiration builds a quick creative starting point, what it generates, and how it differs from a full Song Maker run)*

### 8.2 Using Vibe Words

Vibelton's curated genre database includes **vibe words** — mood/feel descriptors mapped to each genre. If you describe a vibe rather than a genre name, Vibelton matches it:

| Vibe words | → Genre |
|---|---|
| "four on the floor", "driving", "pumping" | House |
| "skippy", "bouncy", "2-step", "soulful" | UK Garage |
| "fast", "rolling", "liquid", "neurofunk" | Drum & Bass |
| "chopped", "ragga", "amen break" | Jungle |
| "hypnotic", "minimal", "industrial" | Techno |
| "808", "half-time", "drill", "dark" | Trap |
| "wobble", "growl", "bass music" | Dubstep |
| "log drum", "jazzy", "soulful piano" | Amapiano |
| "shaker", "polyrhythm", "naija" | Afrobeats |

---

## 9. The Finisher

The Finisher takes your existing Session View loops and turns them into a finished arrangement — no new MIDI is generated from scratch, your clips are used as-is.

### 9.1 Triggering the Finisher

Prompts that contain **both** a finishing intent word and a reference to your existing session:

- `"Finish my existing session loops as a house track"`
- `"Arrange what is already there into a song structure"`
- `"Finish my session view loops as drum & bass"`

### 9.2 What It Does

1. **Reads your current Live state** — track names, clip positions, scene count
2. **Classifies each track** by name into a role: Drums, Bass, Chords, Pad, Lead, Vocal, FX, Other
3. **Selects an arrangement template** matching the genre you described (or defaults to House)
4. **Maps each section** to an available session scene, using your clips
5. **Creates a Riser MIDI clip** on a new AI Riser track before every build/pre-chorus section
6. **Creates a Crash MIDI clip** on a new AI Crash track at the start of every drop/chorus section
7. **Copies everything to Arrangement View** with the correct timing and track muting
8. **Starts playback** from bar 0

Track classification is based on name keywords. For example, a track named "Reese Bass" is classified as Bass, and "808 Sub" is also Bass, while "Lead Pluck" is classified as Lead.

### 9.3 Finisher Mutations (Advanced)

The Finisher also includes three mutation commands that apply to individual clips rather than the full arrangement:

| Command | What it does |
|---|---|
| `"Mutate clones"` | Duplicates the track, mutes the original, places a velocity/timing-varied clone on the copy |
| `"Humanize"` | Adds random timing and velocity jitter using the genre's groove profile |
| `"Ghost notes"` | Adds quiet off-beat snare ghost notes to a drum part |

All mutations use a **deterministic seed** based on your prompt text, so the same prompt always produces the same result. The original track is always muted — not deleted — so you can undo safely.

---

## 10. VHD Instruments

*(VHD = VST / Hardware / Device — to be written)*

### 10.1 What VHD Means

*(Explain the concept of user-specified instruments — VSTs like Serum 2, or stock Ableton devices, being loaded onto generated tracks)*

### 10.2 Selecting Instruments in the UI

*(Describe the instrument selector panel, how to assign a VST per role: bass, chords, lead, pad, drums)*

### 10.3 How Ableton Loads Them

When a VST is assigned, the bridge searches the **Ableton browser** for a matching item. It checks:
1. The **Plug-ins** node (VST3 and VST) — up to 12 levels deep
2. **Sounds**, **Instruments**, **Packs**, **User Library** as fallbacks

Smart fallbacks handle common naming quirks:
- `Serum2` → also tries `Serum`
- `BM-Electric` → also tries `Electric`, `Beatmaker Electric`, `UJAM Electric`

If a match is found, `browser.load_item()` loads it onto the selected track.

### 10.4 Stock Ableton Instruments

If no VST is assigned, the planner can load stock Ableton instruments by searching the browser for genre-aware candidates. Results depend on your installed Live edition and packs.

---

## 11. The Editable Prompt Sent to Ableton (System Prompt & Action Schema)

When OpenAI mode is active, Vibelton constructs a carefully formatted prompt before sending your request to the AI. Understanding this helps you write better prompts and troubleshoot unexpected output.

### 11.1 The System Prompt

The system prompt tells the AI exactly what action types are available and how notes must be formatted. Key rules baked into the system prompt:

- Actions must match a specific schema with a `type` field and parameters
- MIDI pitches are 0–127
- **Bass tracks must be strictly monophonic** (one note at a time) in the range 24–55
- If a request mentions chords, bass, melody, or drums, the AI must include concrete MIDI notes — not just track creation
- Device insertion is listed as unsupported in the current bridge version

### 11.2 Genre Context Injection

When a genre is detected in your prompt, Vibelton automatically appends a **curated genre grammar block** to the system prompt. This block contains:

- BPM range and swing percentage
- Kick, bass, and hi-hat pattern descriptions in plain English
- Energy arc (tension-release, sustained, meditative, wave)
- Genre rules (what must be true) and rule-breakers (optional creative twists)
- Vibe words

This means the AI has structured musical context before it writes a single note, reducing the chance of genre-inappropriate output.

### 11.3 The Action Schema

The AI must return valid JSON matching this structure:

```json
{
  "reply": "A short description of what was planned",
  "actions": [
    { "type": "set_tempo", "bpm": 128 },
    { "type": "create_midi_track", "name": "AI Bass" },
    { "type": "create_midi_clip", "track_name": "AI Bass", "clip_name": "Bassline", "scene_index": 0, "length_beats": 16, "notes": [...] }
  ]
}
```

The `notes` array items each have: `pitch`, `start`, `duration`, `velocity`, `mute`.

### 11.4 Supported Action Types

| Action | Parameters |
|---|---|
| `set_tempo` | `bpm` |
| `set_song_position` | `beat` |
| `start_playback` | — |
| `stop_playback` | — |
| `create_midi_track` | `name` |
| `create_audio_track` | `name` |
| `create_scene` | `name` |
| `set_scene_name` | `scene_index`, `name` |
| `create_midi_clip` | `track_name`, `clip_name`, `scene_index`, `length_beats`, `notes` |
| `duplicate_track` | `track_name` |
| `mute_track` | `track_name` |
| `copy_session_to_arrangement` | `sections` |
| `load_stock_instruments` | `tracks` |
| `load_user_vst_instruments` | `tracks` |
| `rename_tracks_from_devices` | — |
| `set_track_volume` | `track_name`, `db` |
| `set_track_pan` | `track_name`, `pan` |
| `set_send` | `track_name`, `send_index`, `value` |
| `add_device` | `track_name`, `device_name` *(logs as unsupported)* |

---

## 12. How the Ableton Bridge Works

The bridge is a Python file located at `ableton_remote_script/Vibelton/Vibelton.py`. It runs inside Ableton's Python runtime as a **Control Surface**.

### 12.1 Communication via Files

The server and bridge talk through three files in `~/.vibelton/`:

| File | Direction | Purpose |
|---|---|---|
| `commands.jsonl` | Server → Bridge | Each line is a JSON command with an array of actions |
| `events.jsonl` | Bridge → Server | Each line is an event (executed, error, state change) |
| `state.json` | Bridge → Server | Current Live state: tempo, tracks, clips, scene count |

Using files (rather than sockets or MIDI) means the bridge needs zero dependencies and runs safely in Ableton's restricted Python environment.

### 12.2 Polling

The bridge polls `commands.jsonl` approximately every 10 frames (roughly every 165ms). It reads only new lines since the last poll (using a byte offset) so it never re-executes old commands.

After each poll it writes an updated `state.json` so the UI always has a fresh picture of Live.

### 12.3 What Ableton's API Can and Cannot Do

Actions that work reliably:
- Tempo, transport (play/stop/position)
- Track creation (MIDI and Audio)
- Scene creation and naming
- MIDI clip creation and note writing
- Mixer (volume, pan, send)
- Track duplication and muting
- Browser item loading (instruments/plugins)
- Copy session clips to Arrangement View

Actions that are currently unsupported:
- **Device/effect insertion** via `add_device` — logged but not executed; requires a verified browser route or Max for Live helper
- `duplicate_clip_to_arrangement` — depends on the current Live build exposing this method

---

## 13. MIDI Library

Vibelton can draw on your own MIDI files to generate patterns rather than using only the built-in algorithmic generators.

### 13.1 What the MIDI Library Is

The MIDI library is a cache (`~/.cache/vibelton/midi_grooves.json`) built by scanning MIDI files on your disk. It stores normalized patterns categorised by style (house, dnb, trap, etc.) and type (drum, chord, bass, melody).

### 13.2 Building the Cache

```bash
python3 -m vibelton.midi_library
```

Default scan locations:

- `~/Music/free-midi-chords-*`
- `~/Music/GM Mapped`
- `~/Music/free-midi-progressions-*`
- `~/Music/Cymatics_*`
- `~/Music/DrumPlug Ascension Sound Pack/_MIDI`
- `~/Music/` (general fallback)

Patterns are categorised by file name and folder name keywords. If a file is in a folder called "dnb" or has "drum" in its name, it is stored under the matching style.

### 13.3 How Patterns Are Used

When generating drums, chords, bass, or melody, the planner first checks the MIDI library for a matching style/type pattern. If one is found, that real MIDI pattern is used (fitted to the requested bar length). If the library has no match, the algorithmic GenreDNA generator is used instead.

---

## 14. Music Theory Brain

Vibelton has a built-in music theory engine that you can query directly or that the planner uses automatically.

### 14.1 Theory Questions

Ask in the chat:

- `"What are the diatonic chords in D minor?"`
- `"Give me a sentimental progression in A minor"`
- `"Explain the circle of fifths for C major"`

### 14.2 What the Theory Card Contains

- Scale notes for the key
- Relative major/minor
- All 7 diatonic chord names and qualities
- Circle of fifths sharp/flat order
- Voice roles (bass, tenor, alto, soprano) with MIDI ranges
- Rhythm feels (downbeat, upbeat, syncopated)
- A recommended chord progression matched to the vibe of your prompt

### 14.3 Supported Scales

Major, natural minor, harmonic minor, melodic minor, Dorian, Mixolydian, minor pentatonic, major pentatonic.

---

## 15. Ableton Setup Details

### 15.1 Control Surface Slot

Only one Vibelton Control Surface is needed. It does not use MIDI input or output — leave both set to **None**.

### 15.2 Confirming the Bridge is Connected

After selecting the Control Surface and closing Settings, look at the bottom bar in Live. You should briefly see a message like "Vibelton bridge loaded". You can also check `~/.vibelton/state.json` — the `"connected"` field should be `true`.

### 15.3 Port Conflicts

If port 8765 is already in use, the server automatically tries the next 19 ports (8765–8784) and opens the browser at whichever one succeeds.

### 15.4 Ableton Version Notes

- The bridge targets **Ableton Live 12**.
- `duplicate_clip_to_arrangement` was introduced in a specific minor build — if the Finisher arrangement copy logs an error about this method, check your Live version.
- `clip.set_notes()` and `clip.add_new_notes()` are both supported; the bridge tries `set_notes` first and falls back gracefully.

---

## 16. Known Limitations

| Feature | Status |
|---|---|
| Device/effect insertion (`add_device`) | Logged as unsupported; requires future bridge upgrade |
| Stock instrument auto-loading | Depends on Ableton's browser API and your installed packs |
| `duplicate_clip_to_arrangement` | Depends on the Live build; may raise an error on older builds |
| Arrangement copy | Clips must already exist in Session View |
| Windows support | Paths and shell commands differ; test each step |

---

## 17. Troubleshooting

### Vibelton says "Queued X actions" but nothing happens in Ableton

1. Confirm the **Vibelton** Control Surface is selected in Live Settings.
2. Check that the server is still running in your terminal.
3. Open `~/.vibelton/state.json` and check `"connected": true`.
4. Check `~/.vibelton/events.jsonl` for error messages from the bridge.

### OpenAI planning fails

- The server falls back to the local planner automatically and notes this in the reply.
- Check that `OPENAI_API_KEY` is set correctly (`echo $OPENAI_API_KEY`).

### Wrong genre or key detected

- Be explicit: `"4-bar progression in F# minor, trap style"` is unambiguous.
- If the wrong genre is picked, re-state it at the start of the prompt.

### Browser fails to load a VST

- Check that the plugin name in the UI matches the name shown in Ableton's browser exactly (no version number, correct casing).
- The bridge searches up to 12 levels deep in the Plug-ins node; deeply nested manufacturer folders should still be found.

---

## 18. Quick Reference — Example Prompts

```
Set tempo to 124 BPM and create a 4-bar Am F C G chord progression.
Add a bassline in A minor for 8 bars.
Create drums and start playback.
Make a track called Soft Keys and add a C major melody.
Set Soft Keys volume to -8 dB and pan it left 20.
Create an expanded 125 BPM house song sketch with genre-aware Ableton instruments and copy it to Arrangement View.
Humanize the drums and add ghost notes.
Finish my existing session loops as a drum & bass track.
What are the diatonic chords in B minor?
Give me a sentimental chord progression in D minor.
```

---

## 19. File & Folder Reference

| Path | Purpose |
|---|---|
| `vibelton/server.py` | Python HTTP server, main entry point |
| `vibelton/planner.py` | Local planner and OpenAI planner |
| `vibelton/actions.py` | MIDI generation (chords, bass, melody, drums) |
| `vibelton/genre_dna.py` | Genre DNA profiles and curated genre grammars |
| `vibelton/midi_library.py` | MIDI file scanner and cache |
| `vibelton/music_theory.py` | Scale, chord, and progression theory engine |
| `vibelton/harmony.py` | Chord voicing and colour detection |
| `vibelton/queue.py` | File-queue read/write helpers |
| `ableton_remote_script/Vibelton/Vibelton.py` | Ableton Control Surface bridge |
| `install_remote_script.py` | Copies the bridge to your Ableton User Library |
| `web/` | HTML/CSS/JS for the chat UI |
| `~/.vibelton/commands.jsonl` | Command queue (server → bridge) |
| `~/.vibelton/events.jsonl` | Event log (bridge → server) |
| `~/.vibelton/state.json` | Current Live state snapshot |
| `~/.cache/vibelton/midi_grooves.json` | MIDI library cache |
| `.env.local` | Optional environment variables (API key, port) |
