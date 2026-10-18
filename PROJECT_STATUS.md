# Vibelton Project Status Update

**Date**: 2026-10-17  
**Status**: Production & Musical Intelligence Layer Active (V2 / V3 Complete)  

## Overview
Vibelton operates as the structured control layer and musical intelligence engine for Ableton Live 12. Following the completion of the 7 ranked upgrades in `MUSICAL_UPGRADE_HANDOVER_PLAN.md`, Vibelton provides real-time track diagnosis, intelligent non-clashing sample curation, humanized phrase compilation, reversible mix balancing, and acoustic phase/loudness matching directly in the browser and in Ableton Live.

---

## Current Architecture & System State

- **Local Server (`vibelton.server`):**
  - Runs on port `8765` (with bidirectional forwarding on port `8766`).
  - Python HTTP server serving REST API (`/api/status`, `/api/production/*`, `/api/composition/*`, `/api/samples/*`) and web UI.
- **Remote Script Bridge:**
  - Installed at `/Users/standard/Music/Ableton/User Library/Remote Scripts/Vibelton/` and synced with `ableton_remote_script/Vibelton/`.
  - Communicates via state JSON and command queue with strict verification levels (**Intended → Queued → Applied → Readback Verified → Auditioned/Measured**).
  - Handles group tracks (`is_foldable`) cleanly without arrangement readback errors.
- **Test Suite:**
  - **178 automated unit tests passing** (executed in ~9.4s via `/opt/homebrew/bin/python3 -m unittest discover -s tests`).
- **Live Set Integration:**
  - Working copy: `/Users/standard/Music/Ableton/shape chnage Project/shape change vibelton-working-copy .als` (119.0 BPM, 4/4). Original Set preserved untouched.

---

## Key Capabilities (Live in UI & API)

### 1. Production Finishing & Structural Diagnosis (`/api/production/*`)
- **Finish Track Diagnosis:** Analyzes arrangement length, repetition, section contrast, track roles, unplaced session material, and empty tracks.
- **Session-to-Arrangement Placement:** Reversibly duplicates Session clips into Arrangement scenes based on confirmed track roles.
- **Arrangement Maps:** 6 genres (House, Techno, Drum & Bass, UK Garage, Hip Hop, Disco) with 3 structural variants each.

### 2. Audio Intelligence & Anti-Clash (`vibelton/audio_intelligence.py`)
- **4-Band Spectral Energy:** Analyzes Sub/Low (20–120 Hz), Low-Mid (120–500 Hz), Mid (500–4 kHz), and High (4–11 kHz) distribution.
- **KeyScope Tuning:** Zero-crossing pitch tracking, fundamental note identification, and cent-detuning calculation (+/- cents / semitones).
- **StudioPilot Anti-Clash & Quick Shuffle:** Curates 4 non-clashing loop slots (`top_loop`, `percussion`, `bass`, `fx`) locked to project tempo and key.

### 3. Musical Composition Lab (`/api/composition/*`)
- **Project Seeding:** One-click seeding (`POST /api/composition/from-project`) extracts tempo, key hints, and active tracks from the open Ableton Set into an editable score.
- **Humanized Phrasing:** Multi-bar `AAAB` and `ABAC` variations, call-and-response lead rest gaps, and drop transition fills.
- **Bass Companion:** Locks bass downbeats and syncopations to kick timestamps with dynamic groove and density.

### 4. SMYLZ Mix Assistant & Preflight Snapshots
- **Role-Based Balancing:** Anchors Kick (-6.0 dB), Bass (-7.5 dB), Vocal (-6.5 dB), Drums (-7.0 dB), Chords (-9.5 dB), and Percussion (-12.0 dB) with stereo panning offsets.
- **Instant Rollback:** Captures disk snapshots (`~/.vibelton/production/snapshots/`) prior to execution for 1-click rollback.
- **Automation & Parameters:** Bridge primitives for `sends` (`send_0`, `send_1`) and `set_device_parameter`.

### 5. PumpLab Low-End Phase Doctor & Reference A/B
- **Sub-Bass Phase Correlation:** Measures 30–110 Hz cross-correlation between Kick and Bass audio, flags acoustic cancellation (< 0.0), and calculates polarity inversion gain (+dB).
- **Reference Matcher:** Compares rough bounces against reference audio for loudness delta, True Peak, crest factor, and 4-band spectral variance.

---

## Active Web UI Workspaces (`http://127.0.0.1:8765` & `http://127.0.0.1:8766`)

1. **Finish Track:** Structural diagnosis, unplaced session clip detection, and action review.
2. **Arrange:** Genre structural maps, candidate clip assignment, copy plan generation, and rollback.
3. **Prepare Project:** Classic House template creation, empty track cleanup proposals, and role confirmation.
4. **04 / Mix Assistant:** Level and pan balance proposals with Live execution and snapshot rollback.
5. **05 / Quick Loop & Anti-Clash:** 4-slot card grid, spectral energy bars, KeyScope tuning, slot locks, and shuffle re-rolls.
6. **06 / PumpLab Low-End Clash & Reference A/B:** Low-end phase meter, cancellation alert, polarity gain, and reference comparison.
7. **Composition Lab:** Interactive multi-part score editor with section timeline, part locks, and "Seed from Open Set".

---

## Verification & Next Horizons

- **Recent Acceptance:**
  - Track roles confirmed on `shape change vibelton-working-copy .als` (13 active tracks, 10 empty tagged).
  - Unplaced `6-Serum 2` clips integrated into Arrangement timeline (`140.0..252.0`).
  - Mix balance applied across 12 tracks with snapshot `87650614-4ecf-4bcb-a97b-d02a2c356629` verified.
  - Revision 12 project-seeded composition compiled at 119 BPM in $A\flat$ minor.
- **Future Steps:**
  - Automated GUI bounce integration for seamless roundtrip audio analysis in Live without manual stem export.
  - VST/AU third-party plugin window management via computer-use layer.
