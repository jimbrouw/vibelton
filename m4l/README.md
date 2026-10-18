# Vibelton Arranger device (Max for Live)

## Config file (optional): `~/.vibelton/config.json`

```json
{ "repo_path": "/path/to/vibelton", "python_path": "/opt/homebrew/bin/python3", "port": 8765,
  "working_copy_pattern": "vibelton-working-copy" }
```

`working_copy_pattern` (default shown) is matched case-insensitively against the Live Set's **file name**.
The server refuses to scaffold, execute or roll back unless the open Set is saved and matches; an
unsaved Set is blocked with a "Save As" message. Dry-run previews stay allowed. See `vibelton/working_copy.py`.

Repo path is resolved in this order: `VIBELTON_PATH` env var, `repo_path` above, then the folder
relative to the device (`m4l/..`). Python is chosen by actually running
`python -c "import sys; print(sys.version_info >= (3,11))"` on each candidate (`VIBELTON_PYTHON`,
`PYTHON`, `python_path`, Homebrew, `/usr/local`, `python3` on PATH, then `/usr/bin/python3` only
if the Xcode command line tools are installed). Server output goes to `~/.vibelton/logs/server.log`.
Startup failures reach the device as `error_code` (`repo_not_found`, `python_not_found`,
`port_in_use`, `server_crashed`, `startup_timeout`) plus a readable message.

## Build and deploy

```bash
python3 scripts/build_amxd.py          # pack the .maxpat into the .amxd
python3 scripts/deploy_m4l.py          # dry run: shows what would change, blocks stale builds
python3 scripts/deploy_m4l.py --apply  # copy, then re-hash every file
```

Restart nothing in Live for the JS files, but **reload the device** (delete and re-add it, or reopen the Set).

## Freezing the device (manual, not automated)

Freezing embeds `daemon_guard.js` and `autoresize.js` inside the `.amxd` so they no longer need to
sit next to it. It is a Max editor action and cannot be done from Python here:

1. In Live, click the wrench icon on the device title bar to open the Max editor.
2. Click **Freeze Device** (snowflake icon in the bottom toolbar).
3. Save the device (Cmd+S), then close the editor.
4. Copy the saved `.amxd` from the User Library back to `m4l/Vibelton Arranger.amxd`.
5. Run `python3 scripts/deploy_m4l.py` — for a frozen device it checks the repo JS bytes appear inside it.

Note: re-freezing is required after any change to `daemon_guard.js`. `build_amxd.py` repacks the
**unfrozen** patcher, so run it only when you intend to replace a frozen device with an unfrozen one.

## Remembered stem roles

Roles you pick in the device are saved per Live Set (keyed by the Set's file path) in
`~/.vibelton/production/role-memory/`. On reload they are re-attached to tracks by id, then by unique
name, then by position (flagged "check this role"). Tracks that disappear keep their entry (restored if the
track comes back); new tracks simply have no remembered role. An unsaved Set cannot remember roles.
Precedence when planning: choice in this request > exact-revision confirmation > remembered > name guess.
"Forget" in the Stem Roles header clears the memory for the open Set.

## Versions and stale-install warnings

The device header shows the device, bridge (Remote Script) and server versions; an amber **⚠ updates**
button appears when something doesn't match, with the exact fix. `GET /api/versions` returns the same data.

It warns when: the installed Remote Script differs from the repo (`bridge_installed_stale`); Live is running a
different script than the installed one (`bridge_running_stale`); a User Library device file differs from the repo
(`device_library_stale`); the device loaded in Live reports an older version than the repo (`device_loaded_stale`);
or the server was started before its code changed (`server_stale`).

**Bump rules** (so the warnings stay meaningful): change `DEVICE_VERSION` in `m4l/daemon_guard.js` whenever any
device file (`.maxpat`/`.amxd`, `daemon_guard.js`, `autoresize.js`) changes; change `BRIDGE_VERSION` in
`ableton_remote_script/Vibelton/Vibelton.py` whenever the Remote Script changes; change `SERVER_VERSION` in
`vibelton/versions.py` for notable server releases. Content differences are detected even without a bump.
The loaded-device check relies on the device announcing itself (`POST /api/device/hello`) when it connects.

## Lessons from the first run in Live (2026-10-18)

- `node.script` must be saved as `"maxclass": "newobj"` with `saved_object_attributes` keys `node` and `npm`. Any other
  class is deleted on load together with its patchcords (`patchcord source not found: deleting patchcord` in the Max console).
- Never route a message the helper sends to Max back into the message box that calls the helper (`open_popout` → `popout`).
- The helper restarts a stopped server by itself (about every 5 seconds); the Retry button is not required.
- A server started by the device never picks another port, so a second start cannot create a stray server on 8766.
