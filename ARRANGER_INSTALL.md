# Vibelton Arranger — install, update, uninstall

Vibelton Arranger is a Max for Live device plus a small local server and a Remote Script inside Live.
This file says what it needs, how to set it up, how to update it, and how to remove every trace.

> **Status of these instructions:** the commands and file locations below were checked against this repository
> and the machine it was developed on (macOS, Live 12.3.2, Max 8.5.6). Nothing here has been tried on a clean
> second machine, on Windows, or by anyone else. Where a step depends on Live or Max behaviour that was not
> observed, it says so.

## 1. Requirements

| Need | Detail |
|---|---|
| macOS | Developed and tested on macOS only. `install_remote_script.py` contains Windows/Linux paths, but they are untested, and `scripts/deploy_m4l.py` assumes the macOS User Library location. |
| Ableton Live 12 **Suite** | Max for Live is included in Suite (Standard needs the Max for Live add-on). Developed against **Live 12.3.2** with Max 8.5.6. Other versions are untested. |
| Python **3.11 or newer** | The test suite passes on 3.11, 3.12 and 3.14. 3.9 and 3.10 were not tested, so the device refuses to start the server with them. There are **no pip dependencies** (`music21` is optional). |
| Node | Only for running the device tests (`node --test`); Max for Live uses its own bundled Node. |
| The repository | Any location. If the device is not stored next to the repository, tell it where the repo is (section 3). |

macOS note: `/usr/bin/python3` triggers an Xcode licence prompt if you have not accepted it. Use a Homebrew or python.org Python and, if needed, set `python_path` (section 3).

## 2. First-time install

**One step (recommended):** this does steps 2–4 below (Remote Script, device, default config) and nothing else.
It is a dry run unless you add `--apply`, never overwrites an existing `config.json`, and never touches Live's preferences.

```bash
python3 scripts/install_all.py            # shows what it would do
python3 scripts/install_all.py --apply
```

Then quit and reopen Live, pick **Vibelton** as a Control Surface, and continue at step 5. The manual steps follow.

1. **Check Python and the tests**

   ```bash
   python3 --version            # 3.11 or newer
   python3 -m unittest discover -s tests
   ```

2. **Install the Remote Script into Live's User Library, then restart Live**

   ```bash
   python3 install_remote_script.py
   ```

   In Live: *Settings → Link, Tempo & MIDI → Control Surface* → choose **Vibelton** in a free slot. The installer replaces the installed `Vibelton` folder, so it needs a Live restart to take effect.

3. **Build and deploy the device**

   ```bash
   python3 scripts/build_amxd.py --check      # the .amxd must match the .maxpat
   python3 scripts/deploy_m4l.py              # dry run: shows what would be copied
   python3 scripts/deploy_m4l.py --apply      # copies and verifies every file by hash
   ```

   The device and its two scripts (`daemon_guard.js`, `autoresize.js`) must sit in the same folder:
   `~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/`. The deploy script refuses to copy a stale `.amxd` or a device whose referenced scripts are missing.

4. **Tell the device where the repository is, if it isn't next to it** (usual case after step 3). Create `~/.vibelton/config.json`:

   ```json
   { "repo_path": "/path/to/vibelton", "python_path": "/opt/homebrew/bin/python3" }
   ```

   Resolution order for the repository: `VIBELTON_PATH` environment variable → `repo_path` → the folder next to the device. Python: `VIBELTON_PYTHON`, `PYTHON`, `python_path`, Homebrew, `/usr/local`, `python3` on PATH, then `/usr/bin/python3`; each is actually run and must report 3.11+.

5. **Use it in Live**

   1. **File → Save Live Set As…** and save a copy whose name contains `vibelton-working-copy`. The server refuses to scaffold, apply or undo on any other Set (change the pattern with `"working_copy_pattern"` in `config.json`).
   2. Drag **Vibelton Arranger** (User Library → Audio Effects → Max Audio Effect) onto an audio track.
   3. The device starts the local server if it isn't running. On a wide window the header shows the device, bridge and server versions; at any size, `GET /api/versions` returns them and an amber **⚠ updates** button appears when something is stale.

6. **Check it worked**

   ```bash
   curl -s http://127.0.0.1:8765/api/status | head -c 300
   curl -s http://127.0.0.1:8765/api/versions
   ```

   `"connected": true` means the Remote Script in Live is talking to the server. `"ok": true` in `/api/versions` means nothing is stale.

Before trusting it on real material, work through [`ARRANGER_SMOKE_TEST.md`](ARRANGER_SMOKE_TEST.md) on a working copy.

## 3. Files, ports and the config file

| What | Where |
|---|---|
| Server | `python3 -m vibelton.server`, listens on **127.0.0.1:8765** only (`VIBELTON_PORT` or `"port"` to change) |
| Config | `~/.vibelton/config.json` — `repo_path`, `python_path`, `port`, `working_copy_pattern` (min. 8 characters; a weaker value is ignored and the default stays), `extra_sample_roots` and `midi_library_roots` (lists of extra folders the server may read) |
| Session token | `~/.vibelton/session_token` (mode 0600). Every state-changing request must carry it; the device reads it from here. |
| Server log | `~/.vibelton/logs/server.log` |
| Plans, snapshots, placement records (for Undo) | `~/.vibelton/production/` |
| Remembered stem roles | `~/.vibelton/production/role-memory/` |
| Remote Script | `~/Music/Ableton/User Library/Remote Scripts/Vibelton/` |
| Device | `~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/` |

**Approved folders.** The server only reads audio from the loop-pack folder (`~/Music/LOOP PACKS`), the built-in `~/Music/Shadow Samples - UK Bass Vol. 1`, and any folder you list in `extra_sample_roots`; MIDI is scanned in the built-in `~/Music` folders plus `midi_library_roots`. It prints these on startup (`Approved sample folders: …`), and a file outside them is refused. To use other folders, add them to `~/.vibelton/config.json`, e.g. `{"extra_sample_roots": ["~/Samples"], "midi_library_roots": ["~/MIDI"]}`, and restart the server.

Optional: an OpenAI key for the chat planner goes in `.env.local` in the repository (never committed, never printed). The Arranger works without it.

## 4. Updating

1. Update the repository. **If you have uncommitted work, don't pull over it** — merge deliberately.
2. `python3 -m unittest discover -s tests`
3. Open the device and look at the amber **⚠ updates** button (or `GET /api/versions`). It says exactly what is stale:
   - *Remote Script stale* → `python3 install_remote_script.py`, then **restart Live**.
   - *Library device stale* → `python3 scripts/deploy_m4l.py --apply`, then reload the device: delete it from its track and drag it in again (or reopen the Set).
   - *Server stale* → restart the server (reloading the device does this).
4. If you edited device files: `python3 scripts/build_amxd.py`, bump `DEVICE_VERSION` in `m4l/daemon_guard.js`, then deploy. Bump `BRIDGE_VERSION` when the Remote Script changes.

Freezing the device (so the scripts are bundled inside the `.amxd`) is a manual Max step: see `m4l/README.md`.

## 5. Uninstalling cleanly

Do these in order. Nothing outside the paths listed is touched by Vibelton.

1. **In Live:** remove the Vibelton Arranger device from every track; set the Control Surface slot back to *None* (*Settings → Link, Tempo & MIDI*). Save or discard the Set as you wish.
2. **Quit Live.**
3. **Stop the server** if it is still running:

   ```bash
   lsof -nP -iTCP:8765 -sTCP:LISTEN     # note the PID
   kill <PID>
   ```

4. **Remove the device files** (only these three plus the `m4l` folder, if present):

   ```bash
   cd ~/Music/Ableton/User\ Library/Presets/Audio\ Effects/Max\ Audio\ Effect/
   rm -f "Vibelton Arranger.amxd" daemon_guard.js autoresize.js
   rm -rf m4l
   ```

   (`m4l/` is where an earlier install placed the device; check it holds only Vibelton files before deleting.)
5. **Remove the Remote Script:**

   ```bash
   rm -rf ~/Music/Ableton/User\ Library/Remote\ Scripts/Vibelton
   ```

6. **Remove Vibelton's data** — this deletes your undo history, snapshots and remembered roles, so only do it when you are done with every Set it touched:

   ```bash
   rm -rf ~/.vibelton
   ```

7. Delete the repository folder if you no longer want it.

Clips Vibelton already placed in your Sets stay where they are; they are ordinary Live clips.

## 6. Troubleshooting

| Device says | Meaning | Fix |
|---|---|---|
| `repo_not_found` | The device can't find the repository | Set `repo_path` in `config.json` or `VIBELTON_PATH` |
| `python_not_found` | No Python 3.11+ that actually runs | Install one; set `python_path` |
| `port_in_use` | Something else answers on 8765 | Quit it, or set `"port"` in `config.json` |
| `server_crashed` / `startup_timeout` | The server failed to start | Read `~/.vibelton/logs/server.log` |
| "Original Set — scaffolding disabled" | The open Set's name doesn't match the working-copy pattern, or it is unsaved | Save As a working copy |
| ⚠ updates | An installed piece is older than the repository | Follow the fix shown (section 4) |

## 7. Sharing it with other people

You chose to share this, so these defaults were tightened. Everything marked **done** is covered by tests; the rest is a
manual or product decision that code can't make for you.

**Local server (Task 1) — done**

- Binds to `127.0.0.1` only; rejects non-loopback `Host` headers (DNS rebinding) and foreign `Origin`s; no wildcard CORS.
- Every state-changing request needs the per-session token in `~/.vibelton/session_token` (mode 0600).
- Request bodies are capped (1 MB for chat-style endpoints, 32 MB otherwise → `413`) and state-changing requests are rate-limited (240/min, `VIBELTON_RATE_LIMIT`; → `429`).
- Responses carry `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: no-referrer` and `Cross-Origin-Resource-Policy`.
- The server no longer opens a browser tab by default (set `VIBELTON_OPEN_BROWSER=1` to get that back).
- File-by-path endpoints (sample audio) only read audio files inside approved sample folders, with symlinks resolved. Approved folders are `~/Music/LOOP PACKS` plus `extra_sample_roots`. One extra pack folder is still built in (`~/Music/Shadow Samples - UK Bass Vol. 1`); remove it from `vibelton/samples.py` before distributing.
- **Still open:** a per-*install* secret is not used (the token is per session); the MIDI library search defaults include the whole `~/Music` folder (`vibelton/midi_library.py`; add or replace roots with `midi_library_roots`). Decide whether that default is acceptable for other people.

**Device start-up (Task 2) — partly done**

- Done: no hard-coded user paths anywhere in the code; one-step installer; Python 3.11+ enforced and actually run-checked; readable errors; home directory replaced by `~` in device error messages, the server log header and the "Details" text.
- **Not done, needs you:** freeze, sign and notarise the `.amxd` (Max "Freeze Device", then Apple's notarisation). This cannot be done from this repository; without it other people get a device that depends on the scripts sitting next to it and may be blocked by Gatekeeper.
- **Not done:** bundling or auto-installing Python; Windows and Linux are unsupported.

**Working-copy rule (Task 4) — done within what code can know**

- A `working_copy_pattern` shorter than 8 characters, without letters, or in a generic list (`copy`, `backup`, `final`, …) is ignored and the default stays; the device shows why.
- The rule is enforced server-side for scaffold, apply and undo, and stored with every snapshot and job.
- **Limit:** it checks the Set's *file name*. Nothing can tell a true original from a copy someone named carelessly, so tell users to Save As first.

**Licensing — open:** see `LICENSE_AUDIT.md`. The repository's own licence and any bundled or referenced material need an explicit decision before you distribute anything.
