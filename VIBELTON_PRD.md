# Vibelton (Ableton Copilot) - Product Requirements Document

## 1. Product Overview
**Vibelton** is an AI-powered natural language interface for **Ableton Live 12**. It allows music producers to control their DAW, generate musical content (MIDI), and build full song arrangements using simple text prompts. 

By bridging the gap between high-level creative intent and low-level DAW operations, Vibelton aims to reduce friction in the "blank slate" phase of music production and automate tedious setup tasks.

---

## 2. Problem Statement
The traditional DAW workflow is highly manual, requiring thousands of mouse clicks and menu navigations to perform tasks like:
- Setting up track routing and naming.
- Creating musically coherent MIDI patterns for different genres.
- Transitioning between Session View (jamming) and Arrangement View (song structure).
- Implementing complex song structures (Intro -> Verse -> Build -> Drop).

Producers often lose creative momentum during these technical hurdles.

---

## 3. Solution
Vibelton provides a "Command Center" interface that translates natural language into executable Ableton Live actions. It uses a combination of:
1.  **Large Language Models (OpenAI)**: For complex planning and reasoning.
2.  **Deterministic Local Planner**: For fast, reliable execution of common tasks without needing an API key.
3.  **Generative Music Engines**: Algorithmic MIDI generation for chords, basslines, melodies, and drums based on music theory.
4.  **Live 12 Bridge**: A custom Python-based Remote Script that executes commands directly within the Live environment.

---

## 4. Core Features

### 4.1 Natural Language Command Interface
- **Transport Control**: Set tempo, start/stop playback.
- **Track Management**: Create MIDI and Audio tracks with descriptive names.
- **Mixer Control**: Adjust volume (in dB), panning, and send levels.
- **Device Management**: Add stock Ableton devices (Synths, Effects) to tracks.

### 4.2 Generative Music Engines
- **Theory-Aware Generation**:
    - **Chords**: Automatic chord progression generation (e.g., I-V-vi-IV) in specified keys.
    - **Bass**: Rhythmically active basslines that follow chord roots.
    - **Melody**: Scale-aligned hook generation.
    - **Drums**: Genre-appropriate drum patterns (Kick, Snare, Hats, Percussion).
- **Style Customization**: Support for different "energies" (Intro, Build, Main, Break).

### 4.3 Song Sketching & Genre Templates
- **Instant Sketches**: Generate a 4-8 track foundation with one prompt (e.g., "Give me a quick Lo-fi sketch").
- **Genre Support**: Built-in logic for House, Techno, DnB, Trap, Hip-Hop, Pop, Ambient, and more.
- **Arrangement Workflow**: Automatically copies Session View clips into a structured Arrangement View timeline with labeled sections.

### 4.4 Hybrid Planning System
- **LLM Mode**: Uses GPT-4 (or higher) to handle complex, multi-step requests.
- **Local Mode**: A fast, regex-based planner for standard requests (e.g., "Set tempo to 128").

---

## 5. Technical Architecture

### 5.1 System Components
- **Client (Web UI)**: A vanilla HTML/JS/CSS interface for chatting with the assistant.
- **Server (Python)**: A lightweight HTTP server (`server.py`) that handles planning, MIDI generation, and queue management.
- **Bridge (Ableton Remote Script)**: A Python 3 script running inside Ableton Live 12 that polls for new commands and executes them using the Live API.

### 5.2 Communication Protocol
The system uses a file-based queue system located in `~/.ableton_copilot/`:
- `commands.jsonl`: Outgoing actions from Server to Live.
- `events.jsonl`: Feedback and status updates from Live to Server.
- `state.json`: Current Live state (tracks, clips, transport).

---

## 6. User Workflow
1.  **Initialization**: User starts the Vibelton server and selects the `AbletonCopilot` Control Surface in Live.
2.  **Prompting**: User types a request (e.g., "Create a dark techno buildup for 8 bars").
3.  **Planning**: Vibelton determines the necessary actions (Create tracks, generate MIDI, set scene names).
4.  **Execution**: The Ableton Bridge reads the command queue and performs the actions in real-time.
5.  **Iteration**: User reviews the result and refines (e.g., "Lower the volume of the lead by 3dB").

---

## 6. Future Roadmap (V2)
- **Plugin Integration (SnapHost)**: Snapshot-based control and morphing of VST3/AU plugins.
- **Sample Selection**: Intelligent searching and loading of samples into Simpler/Sampler.
- **Context-Aware Recommendations**: Suggesting appropriate effects or sounds based on existing track content.
- **Voice Control**: Integrating speech-to-text for hands-free production.
