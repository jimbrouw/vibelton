# Vibelton

Snowball from zero.

Natural-language control for Ableton Live 12 on macOS and Windows.

This project has two parts:

- `ableton_copilot/server.py`: local chat app and action planner.
- `ableton_remote_script/AbletonCopilot`: Ableton Control Surface script that runs inside Live and executes queued actions.

The first working surface covers tempo, playback, tracks, scenes, MIDI clips, generated chord progressions, basslines, melodies, volume, pan, and sends. Device/effect insertion is represented in the action schema but is marked as unsupported by the first bridge until it is wired through a verified Live 12 device-browser route or a Max for Live helper.

## Quick Start

1. Install the Remote Script into your Ableton User Library:

   ```bash
   python3 install_remote_script.py
   ```

2. Open Ableton Live 12.
3. Go to `Settings -> Link, Tempo & MIDI`.
4. Choose `AbletonCopilot` in a Control Surface slot.
5. Start the local chat app:

   ```bash
   python3 -m ableton_copilot.server
   ```

6. Open `http://127.0.0.1:8765`.

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

## Example Prompts

- `Set tempo to 124 BPM and create a 4 bar Am F C G chord progression.`
- `Add a bassline in A minor for 8 bars.`
- `Create drums and start playback.`
- `Make a track called Soft Keys and add a C major melody.`
- `Set Soft Keys volume to -8 dB and pan it left 20.`

## Queue Files

The server and Ableton bridge communicate through:

```text
~/.ableton_copilot/commands.jsonl
~/.ableton_copilot/events.jsonl
~/.ableton_copilot/state.json
```

This keeps the first bridge dependency-free inside Ableton's Python runtime.
