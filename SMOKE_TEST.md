# Vibelton Smoke Test

Run this after every stage branch before marking the stage complete.

[Unverified] These prompts still need to be run inside Ableton Live on a fresh setup.

## Setup

1. Install the canonical Remote Script:

   ```bash
   python3 install_remote_script.py
   ```

2. Restart Ableton Live 12.
3. In Settings -> Link, Tempo & MIDI, select `Vibelton`.
4. Start the local server:

   ```bash
   python3 -m vibelton.server
   ```

5. Open `http://127.0.0.1:8765`.

## Five Prompts

1. `Set tempo to 124 BPM and start playback.`
2. `Create house drums for 4 bars.`
3. `Create a 4 bar Am F C G chord progression.`
4. `Create an expanded 125 BPM house song sketch with genre-aware Ableton instruments, warm chords, bouncy bass, club kick, open hats, percussion, clap, pad, riff, ambience, and a simple lead hook. Copy it to Arrangement View and start playback.`
5. `Humanize the drums and add ghost notes.`

## Pass Notes

- Server starts without an exception.
- Ableton bridge reports connected state.
- Each prompt queues actions.
- The bridge reports command completion or a clear unsupported-action event.
- Any unsupported action is copied into `LISTENING_NOTES.md` before merge.
