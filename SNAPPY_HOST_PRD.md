# Clean-Room VST Host Plugin PRD

## Build Prompt

Build a clean-room audio plugin host inspired by the general workflow of snapshot-based plugin control tools. Do not reverse engineer, copy, decompile, inspect, or reproduce proprietary binaries, UI, text, presets, protocols, assets, or private behavior from any commercial plugin.

The product should be an original VST3/AU-capable host plugin and companion control layer that can load a third-party VST3/AU plugin, expose its parameters, store snapshots, morph between snapshots, randomize safely, and allow external control from the existing Vibelton V2 app.

Use public SDKs and documentation only. Prefer JUCE with CMake for the first implementation because it provides cross-platform audio plugin scaffolding, plugin scanning, plugin hosting primitives, state management, and UI components.

## Product Goal

Create an original plugin named **SnapHost** that gives producers a fast way to explore, save, morph, and automate sound-design states from hosted VST3/AU instruments or effects.

SnapHost should run inside Ableton Live as a plugin. It should host one child plugin at a time, receive MIDI/audio from Ableton, process the child plugin, and return audio to Ableton.

## Problem

Producers often have powerful plugins with too many parameters. They need a faster way to:

- Capture useful plugin states.
- Morph between sounds.
- Randomize sound design without destroying gain staging.
- Control sound design from an external AI/app workflow.
- Integrate hosted plugin control into arrangement-building tools.

## Non-Goals

- Do not clone any existing commercial plugin.
- Do not reverse engineer proprietary products.
- Do not duplicate protected UI layouts, names, manuals, assets, presets, or private APIs.
- Do not support every plugin format in V1.
- Do not build a full DAW.
- Do not promise compatibility with every VST3/AU plugin.

## Target Users

- Electronic music producers using Ableton Live.
- Producers who want rapid sound-design exploration.
- Users of the existing Vibelton V2 app who want AI-assisted plugin control.

## V1 Scope

### Plugin Hosting

- Scan installed VST3 plugins.
- Load one hosted plugin at a time.
- Pass MIDI from the DAW into the hosted plugin.
- Pass audio through the hosted plugin.
- Open or embed hosted plugin editor if supported by the framework.
- Unload/reload hosted plugins safely.

### Parameter Discovery

- Read hosted plugin parameter list.
- Store each parameter with:
  - ID/index
  - name
  - normalized value
  - default value when available
  - automation/control eligibility

### Snapshots

- Save a complete normalized parameter state as a named snapshot.
- Recall a snapshot.
- Rename/delete snapshots.
- Store snapshots inside the plugin state so Ableton project recall works.

### Morphing

- Morph between two snapshots with a single normalized control: `0.0` to `1.0`.
- Smooth parameter changes to reduce audible stepping.
- Allow parameter exclusions from morphing.

### Randomization

- Randomize eligible hosted plugin parameters.
- Provide intensity control.
- Exclude risky parameters by default:
  - output gain
  - master volume
  - bypass
  - mix/wet if unsafe for the use case
- Add per-parameter lock toggles.

### Macros

- Provide 8 macro controls.
- Each macro can map to multiple hosted plugin parameters.
- Each mapping stores:
  - target parameter
  - min value
  - max value
  - curve type
  - polarity

### External Control API

- Provide a local control interface for Vibelton V2.
- Start with localhost HTTP or WebSocket.
- Later option: MCP-style tool interface.
- Required commands:
  - get status
  - list hosted plugin parameters
  - set parameter
  - get parameter
  - save snapshot
  - recall snapshot
  - morph snapshots
  - randomize
  - list snapshots
  - lock/unlock parameter

## V2 Scope

- AU hosting on macOS.
- Hosted plugin search UI.
- Preset browser.
- XY morphing between four snapshots.
- Snapshot banks.
- MIDI learn.
- Automation lane helpers.
- AI-readable parameter summaries.
- Safer loudness monitoring.
- Bridge directly into Vibelton V2 command planning.

## Technical Architecture

### Recommended Stack

- Language: C++20
- Framework: JUCE
- Build: CMake
- Plugin formats produced:
  - VST3
  - AU on macOS if enabled
- Initial platform:
  - macOS first
  - Windows later

### Main Modules

```text
SnapHost/
  Source/
    PluginProcessor.*
    PluginEditor.*
    HostedPluginManager.*
    PluginScanner.*
    SnapshotStore.*
    MorphEngine.*
    Randomizer.*
    MacroMapper.*
    ControlServer.*
    StateSerializer.*
```

### Audio Flow

```text
Ableton MIDI/audio
  -> SnapHost processor
  -> hosted plugin instance
  -> SnapHost output
  -> Ableton
```

### State Model

```json
{
  "hostedPlugin": {
    "format": "VST3",
    "name": "Example Synth",
    "identifier": "plugin-id-or-path"
  },
  "snapshots": [
    {
      "id": "snapshot-1",
      "name": "Warm Bass",
      "parameters": {
        "param-id-1": 0.42,
        "param-id-2": 0.77
      }
    }
  ],
  "lockedParameters": ["output-gain"],
  "macros": []
}
```

## Vibelton V2 Integration

Add a backend connector in the existing Python app:

```text
vibelton/
  snaphost_client.py
```

Responsibilities:

- Detect SnapHost control server.
- Authenticate if a token is configured.
- Send sound-design commands.
- Return status and errors to the web UI.

Example app commands:

```text
Randomize the bass synth lightly but keep output stable.
Save this sound as Snapshot 1 called Warm Bass.
Morph the lead 30 percent toward Snapshot 2.
Lock cutoff and randomize the rest.
```

## API Draft

### GET `/status`

Returns hosted plugin and server state.

### GET `/parameters`

Returns available hosted plugin parameters.

### POST `/parameter`

```json
{
  "id": "cutoff",
  "value": 0.42
}
```

### POST `/snapshots`

```json
{
  "name": "Warm Bass"
}
```

### POST `/snapshots/recall`

```json
{
  "id": "snapshot-1"
}
```

### POST `/morph`

```json
{
  "from": "snapshot-1",
  "to": "snapshot-2",
  "amount": 0.5
}
```

### POST `/randomize`

```json
{
  "intensity": 0.25,
  "respectLocks": true
}
```

## Implementation Plan

### Phase 1: Project Scaffold

- Create JUCE/CMake plugin project.
- Build empty VST3 plugin.
- Verify it loads in a test host.
- Add basic editor with hosted plugin status.

Acceptance criteria:

- VST3 builds successfully.
- Plugin opens in a host.
- Plugin state saves and restores a simple setting.

### Phase 2: Plugin Scanner and Loader

- Add VST3 scanning.
- Display discovered plugins.
- Load one plugin by description/path.
- Route prepare/process/release lifecycle correctly.

Acceptance criteria:

- At least one installed VST3 can be discovered.
- Hosted plugin receives MIDI/audio.
- Audio output returns to the DAW.

### Phase 3: Parameter Layer

- Read hosted plugin parameters.
- Show parameter list.
- Set normalized parameter values.
- Store parameter metadata.

Acceptance criteria:

- User can change a hosted plugin parameter from SnapHost UI.
- Changes are audible/visible in the hosted plugin.

### Phase 4: Snapshots

- Save current parameter state.
- Recall saved state.
- Persist snapshots in DAW project state.

Acceptance criteria:

- User can save two different states.
- User can recall both after closing/reopening the project.

### Phase 5: Morph Engine

- Interpolate between snapshots.
- Add smoothing.
- Add parameter lock/exclusion support.

Acceptance criteria:

- Morph control moves smoothly between two stored snapshots.
- Locked parameters do not change.

### Phase 6: Randomizer

- Add intensity-based randomization.
- Add default safety exclusions.
- Add per-parameter locks.

Acceptance criteria:

- Randomize produces parameter changes.
- Locked/safety-excluded parameters remain unchanged.

### Phase 7: Control API

- Add localhost server.
- Add status, parameters, snapshots, morph, and randomize endpoints.
- Add optional bearer token.

Acceptance criteria:

- Existing Vibelton V2 backend can query SnapHost status.
- Existing app can trigger randomize/save/recall/morph commands.

### Phase 8: Vibelton V2 UI

- Add SnapHost status card.
- Add sound-design command routing.
- Show recent SnapHost actions.
- Surface clear errors when SnapHost is not loaded/running.

Acceptance criteria:

- User can issue natural-language sound-design commands from the app.
- App distinguishes Ableton arrangement actions from SnapHost sound-design actions.

## Risks

- [Inference] Some hosted plugins may not expose stable parameter IDs across versions.
- [Inference] Some plugin editors may not embed cleanly inside another plugin.
- [Inference] Hosting plugins inside plugins can behave differently across DAWs.
- [Inference] Real-time safety requires care: avoid allocation, locks, and network calls on the audio thread.
- [Inference] AU hosting inside an AU/VST may require additional platform-specific work.

## Legal and Compliance Requirements

- Use public SDKs and documentation only.
- Do not reverse engineer commercial plugins.
- Do not copy protected UI, branding, manuals, presets, or assets.
- Use an original name, visual identity, and file format.
- Review JUCE and Steinberg licensing before distribution.

## Success Metrics

- Loads at least one common VST3 instrument in Ableton.
- Saves and recalls hosted plugin snapshots.
- Morphs between snapshots without obvious stepping.
- Randomizes parameters while respecting locks.
- Receives at least one command from Vibelton V2.
- Project can be reopened with hosted plugin and snapshots restored.

## First Development Task

Create a new `snaphost/` folder with a JUCE/CMake plugin scaffold. Build an empty VST3 named `SnapHost`, then add a minimal UI showing:

- hosted plugin: none
- snapshot count: 0
- morph amount slider
- randomize button
- status text

Do not implement plugin hosting until the empty plugin builds and loads successfully.
