from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any

from .actions import (
    clip_action,
    filter_drums,
    generate_bassline,
    generate_chords,
    generate_edm_bassline,
    generate_edm_chords,
    generate_edm_drums,
    generate_edm_lead,
    generate_melody,
    genre_bassline,
    genre_chords,
    genre_drums,
    genre_lead,
    transpose_notes,
)
from .genre_dna import (
    build_curated_prompt_context,
    curated_default_bpm,
    curated_sections_for_genre,
    detect_style_from_text as detect_style,
    lookup_genre,
)
from .music_theory import producer_theory_card
from .midi_library import generate_library_drums, generate_library_chords, generate_library_melody, generate_library_bass, mutate_clones, humanize_groove, add_ghost_notes, stable_seed
from .actions import finisher_mutation


ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "reply": {"type": "string"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "type": {"type": "string"},
                },
                "required": ["type"],
            },
        },
    },
    "required": ["reply", "actions"],
}


SYSTEM_PROMPT = """You convert music production requests into safe Ableton Live actions.

CRITICAL: Return ONLY valid JSON in exactly this structure — no other text:
{"reply": "brief human description", "actions": [{"type": "action_name", ...params...}, ...]}

Each action MUST have "type" as a top-level key with the action name as its string value, plus any parameters as sibling keys at the same level. Example:
{"type": "set_tempo", "bpm": 124}
{"type": "create_midi_track", "name": "Bass"}
{"type": "create_midi_clip", "track_name": "Bass", "clip_name": "Bassline", "scene_index": 0, "length_beats": 16, "notes": [{"pitch": 36, "start": 0, "duration": 0.5, "velocity": 100, "mute": false}]}

Available action types (type value → required params):
- set_tempo → bpm
- set_song_position → beat
- start_playback → (no extra params)
- stop_playback → (no extra params)
- create_midi_track → name
- create_audio_track → name
- create_scene → name
- create_midi_clip → track_name, clip_name, scene_index, length_beats, notes
- set_track_volume → track_name, db
- set_track_pan → track_name, pan
- set_send → track_name, send_index, value
- add_device → track_name, device_name
- rename_tracks_from_devices → (no extra params)
- route_midi → source_track, target_track

Notes are objects: {pitch, start, duration, velocity, mute}. MIDI pitch is 0-127. Beat positions use Ableton beats.
Bass tracks must be strictly monophonic (one note at a time, never chords) and sit in a low register (MIDI note numbers 24 to 55). Never write chords or high-pitched melodies for the bass track.
If a request asks for chords, bass, melody, or drums, include concrete MIDI notes.
If a request asks for unsupported device/effect details, include add_device anyway and mention it may require a later bridge upgrade in reply.
Do not claim the DAW action succeeded; the Ableton bridge reports execution separately.

Camelot Wheel Key Resolution:
To perform harmonic mixing and transitions, resolve Camelot codes to standard notation:
- 1A = ab minor, 2A = eb minor, 3A = bb minor, 4A = f minor, 5A = c minor, 6A = g minor, 7A = d minor, 8A = a minor, 9A = e minor, 10A = b minor, 11A = f# minor, 12A = c# minor.
- 1B = b major, 2B = f# major, 3B = db major, 4B = ab major, 5B = eb major, 6B = bb major, 7B = f major, 8B = c major, 9B = g major, 10B = d major, 11B = a major, 12B = e major.
Adjacent codes (e.g. 8A to 7A or 9A, or 8A to 8B) are harmonically compatible. If asked to make a relative key transition, shift between A and B with the same number (e.g. 8A to 8B is a minor to C major)."""


def plan(message: str, vst_map: dict[str, str] | None = None) -> dict[str, Any]:
    vst_map = vst_map or {}
    lowered = message.lower()

    # Arrangement / song-sketch requests always use the local planner.
    # The local planner has curated multi-section logic (expanded_song_sketch_plan,
    # existing_session_finisher_plan, edm_arrangement_plan) that produces full
    # arrangements with copy_session_to_arrangement — something OpenAI can't
    # reliably replicate in a single API call.
    if _is_arrangement_request(lowered):
        lp = local_plan(message, vst_map=vst_map)
        lp["actions"] = enrich_actions(message, lp.get("actions", []), vst_map=vst_map)
        return lp

    # Focused creative requests (specific part, theory, key, BPM) benefit from
    # OpenAI's harmonic intelligence.
    if os.environ.get("OPENAI_API_KEY"):
        try:
            return openai_plan(message, vst_map=vst_map)
        except Exception as exc:
            fallback = local_plan(message, vst_map=vst_map)
            fallback["reply"] = f"OpenAI planning failed: {exc}. I queued a local interpretation instead."
            fallback["actions"] = enrich_actions(message, fallback.get("actions", []), vst_map=vst_map)
            return fallback

    lp = local_plan(message, vst_map=vst_map)
    lp["actions"] = enrich_actions(message, lp.get("actions", []), vst_map=vst_map)
    return lp


def _is_arrangement_request(lowered: str) -> bool:
    """Return True when the request calls for a full multi-section arrangement.

    These requests should always go through the local planner, which has
    curated genre-aware song structure logic.  OpenAI is reserved for focused
    creative requests (specific parts, theory, key/BPM overrides).
    """
    # Explicit arrangement / sketch phrases
    arrangement_phrases = [
        "song sketch", "full track", "full song", "song structure",
        "arrangement", "produce a", "make a track", "make me a track",
        "create a track", "hear something", "quick idea", "quick demo",
        "production sketch", "reference song", "inspirational", "inspiration",
        "song idea", "starting idea", "starting point",
        "finish", "finisher", "arrange", "existing loops", "session loops",
        "session view", "my loops",
    ]
    if any(phrase in lowered for phrase in arrangement_phrases):
        return True

    # Genre keyword without a focused-part qualifier → song sketch
    detected = detect_style(lowered)
    if detected and not is_focused_part_prompt(lowered):
        return True

    return False


def openai_plan(message: str, vst_map: dict[str, str] | None = None) -> dict[str, Any]:
    style = detect_style(message)
    genre_context = build_curated_prompt_context(style)
    system_prompt = SYSTEM_PROMPT
    if genre_context:
        system_prompt = f"{SYSTEM_PROMPT}\n\nUse this curated genre grammar when generating musical actions:\n{genre_context}"
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API returned {exc.code}: {body[:400]}") from exc

    text = extract_response_text(data)
    # Strip markdown code fences if model wraps JSON in ```json ... ```
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        stripped = stripped.rsplit("```", 1)[0]
    parsed = json.loads(stripped)
    parsed["actions"] = enrich_actions(message, parsed.get("actions", []), vst_map=vst_map)
    return parsed


def extract_response_text(data: dict[str, Any]) -> str:
    # Chat Completions API: choices[0].message.content
    choices = data.get("choices")
    if choices and isinstance(choices, list):
        content = choices[0].get("message", {}).get("content")
        if isinstance(content, str):
            return content
    # Responses API fallback
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                    return content["text"]
    raise RuntimeError("No text output found in OpenAI response")


def local_plan(message: str, vst_map: dict[str, str] | None = None) -> dict[str, Any]:
    lowered = message.lower()
    detected_style = detect_style(message)
    if wants_theory_brain(lowered):
        return theory_brain_plan(message)
    if wants_existing_session_finisher(lowered):
        return existing_session_finisher_plan(message, vst_map=vst_map or {})
    if any(
        phrase in lowered
        for phrase in [
            "hear something fast",
            "quick idea",
            "quick demo",
            "quick sketch",
            "default ableton instruments",
            "default instruments",
            "stock instruments",
            "more tracks",
            "each part",
            "production sketch",
            "song sketch",
            "reference song",
            "inspirational",
            "inspiration",
        ]
    ) or (
        (detected_style != "house" or any(word in lowered for word in genre_words()))
        and not is_focused_part_prompt(lowered)
    ):
        return expanded_song_sketch_plan(message, vst_map=vst_map or {})
    if any(word in lowered for word in ["better", "complicated", "complex", "interesting", "richer", "enhance"]):
        return edm_enhancement_plan(message, vst_map=vst_map or {})
    if "mutate clones" in lowered:
        return finisher_plan(message, "mutate_clones")
    if "humanize" in lowered:
        return finisher_plan(message, "humanize")
    if "ghost notes" in lowered:
        return finisher_plan(message, "ghost_notes")
    if "maximal density" in lowered or "carve" in lowered:
        return subtractive_arrangement_plan(message)
    if any(word in lowered for word in ["instrument", "instruments", "sound", "preset", "device"]) and any(
        word in lowered for word in ["edm", "track", "tracks", "bass", "lead", "chord", "drum"]
    ):
        return {
            "reply": "Queued genre-aware Ableton instrument choices for the current tracks.",
            "actions": [
                {
                    "type": "load_stock_instruments",
                    "tracks": current_track_palette(message),
                }
            ],
        }
    if "arrangement" in lowered and any(word in lowered for word in ["copy", "move", "put", "place", "timeline"]):
        return {
            "reply": "Queued a command to copy the existing EDM Session View clips into Arrangement View.",
            "actions": [
                {
                    "type": "copy_session_to_arrangement",
                    "sections": arrangement_sections(default_edm_sections()),
                }
            ],
        }
    if wants_arrangement_plan(lowered):
        return edm_arrangement_plan(message, vst_map=vst_map or {})

    bars = extract_bars(lowered)
    actions: list[dict[str, Any]] = []

    bpm = extract_bpm(lowered)
    if bpm:
        actions.append({"type": "set_tempo", "bpm": bpm})

    if "audio track" in lowered:
        actions.append({"type": "create_audio_track", "name": extract_named_track(message, "Audio")})

    named_track = extract_named_track(message, "")
    vst_track_map: dict[str, list[str]] = {}
    _vst_map = {k.lower(): v for k, v in (vst_map or {}).items()}

    wants_chords = any(word in lowered for word in ["chord", "progression", "piano"]) or (
        "keys" in lowered and not named_track
    )
    if wants_chords:
        track = named_track or "AI Chords"
        actions.append({"type": "create_midi_track", "name": track})
        actions.append(clip_action(track, "Generated Chords", generate_chords(message, bars), bars))
        plugin_name = _vst_map.get("chords") or _vst_map.get("all")
        if plugin_name:
            vst_track_map[track] = [plugin_name]

    if "bass" in lowered:
        track = "AI Bass"
        actions.append({"type": "create_midi_track", "name": track})
        actions.append(clip_action(track, "Generated Bassline", generate_bassline(message, bars), bars))
        plugin_name = _vst_map.get("bass") or _vst_map.get("all")
        if plugin_name:
            vst_track_map[track] = [plugin_name]

    if any(word in lowered for word in ["melody", "counter-melody", "counter melody", "lead"]):
        track = named_track or "AI Melody"
        actions.append({"type": "create_midi_track", "name": track})
        actions.append(clip_action(track, "Generated Melody", library_melody(message, bars, genre=detect_style(message)), bars))
        plugin_name = _vst_map.get("lead") or _vst_map.get("all")
        if plugin_name:
            vst_track_map[track] = [plugin_name]

    if any(word in lowered for word in ["drum", "beat", "groove"]):
        track = "AI Drums"
        actions.append({"type": "create_midi_track", "name": track})
        actions.append(clip_action(track, "Generated Drum Pattern", library_drums(message, bars, genre=detect_style(message)), bars))

    if vst_track_map:
        actions.append({
            "type": "load_user_vst_instruments",
            "tracks": vst_track_map,
        })

    volume = extract_db(lowered)
    if volume is not None:
        actions.append({"type": "set_track_volume", "track_name": extract_track_reference(message), "db": volume})

    pan = extract_pan(lowered)
    if pan is not None:
        actions.append({"type": "set_track_pan", "track_name": extract_track_reference(message), "pan": pan})

    if "play" in lowered or "start" in lowered:
        actions.append({"type": "start_playback"})
    if "stop" in lowered:
        actions.append({"type": "stop_playback"})

    if not actions:
        track = extract_named_track(message, "AI MIDI")
        actions = [{"type": "create_midi_track", "name": track}]

    return {
        "reply": f"Queued {len(actions)} action(s) for Ableton Live.",
        "actions": actions,
    }


def wants_theory_brain(text: str) -> bool:
    theory_words = [
        "music theory",
        "theory brain",
        "relative major",
        "relative minor",
        "circle of fifths",
        "diatonic",
        "scale degrees",
        "chord quality",
        "chord progression generator",
        "progression based on vibe",
    ]
    return any(phrase in text for phrase in theory_words)


def theory_brain_plan(message: str) -> dict[str, Any]:
    root, mode = extract_theory_key(message)
    card = producer_theory_card(root, mode, vibe=message)
    progression = card["recommended_progression"]
    chords = ", ".join(progression["chords"])
    notes = ", ".join(card["notes"])
    diatonic = ", ".join(item["chord"] for item in card["diatonic_chords"])
    return {
        "reply": (
            f"Theory brain for {card['key']}: notes are {notes}. "
            f"Relative key: {card['relative_key']}. "
            f"Diatonic chords: {diatonic}. "
            f"Suggested {progression['vibe']} progression: {' - '.join(progression['degrees'])} ({chords})."
        ),
        "actions": [],
        "theory": card,
    }


def extract_theory_key(message: str) -> tuple[str, str]:
    lowered = message.lower().replace("♯", "#").replace("♭", "b")
    
    # Check Camelot Wheel codes first
    camelot_match = re.search(r"\b(1[0-2]|[1-9])\s*([ab])\b", lowered)
    if camelot_match:
        code = f"{camelot_match.group(1)}{camelot_match.group(2)}"
        camelot_map = {
            "1a": ("ab", "minor"), "2a": ("eb", "minor"), "3a": ("bb", "minor"), "4a": ("f", "minor"),
            "5a": ("c", "minor"), "6a": ("g", "minor"), "7a": ("d", "minor"), "8a": ("a", "minor"),
            "9a": ("e", "minor"), "10a": ("b", "minor"), "11a": ("f#", "minor"), "12a": ("c#", "minor"),
            "1b": ("b", "major"), "2b": ("f#", "major"), "3b": ("db", "major"), "4b": ("ab", "major"),
            "5b": ("eb", "major"), "6b": ("bb", "major"), "7b": ("f", "major"), "8b": ("c", "major"),
            "9b": ("g", "major"), "10b": ("d", "major"), "11b": ("a", "major"), "12b": ("e", "major"),
        }
        if code in camelot_map:
            return camelot_map[code]

    mode = "minor" if "minor" in lowered or any(word in lowered for word in ["sad", "dark", "romantic"]) else "major"
    match = re.search(r"\b([a-g](?:#|b)?)\s+(major|minor)\b", lowered)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r"\bin\s+([a-g](?:#|b)?)\b", lowered)
    if match:
        return match.group(1), mode
    return ("a", "minor") if mode == "minor" else ("c", "major")


def is_focused_part_prompt(text: str) -> bool:
    part_words = [
        "drum",
        "drums",
        "beat",
        "groove",
        "bass",
        "bassline",
        "chord",
        "chords",
        "progression",
        "melody",
        "lead",
        "hook",
        "riff",
        "pad",
    ]
    expanded_words = [
        "arrangement",
        "song",
        "song sketch",
        "track",
        "full",
        "complete",
        "expanded",
        "all parts",
        "each part",
        "copy it",
        "arrangement view",
    ]
    return any(word in text for word in part_words) and not any(word in text for word in expanded_words)


def wants_arrangement_plan(text: str) -> bool:
    if any(word in text for word in ["arrangement", "song", "edm"]):
        return True
    if "track" not in text:
        return False
    if re.search(r"(?:track|channel)\s+(?:called|named)", text):
        return False
    return any(word in text for word in ["full track", "complete track", "expanded track", "song track"])


def wants_existing_session_finisher(text: str) -> bool:
    intent = any(word in text for word in ["finish", "finisher", "arrange", "structure", "song structure"])
    source = any(phrase in text for phrase in ["existing loops", "session loops", "session view", "my loops", "what is already there"])
    return intent and source


ARRANGEMENT_TEMPLATES = {
    "house": [
        ("DJ Intro", 8, ["Drums", "Pad", "FX", "Other"]),
        ("Groove", 8, ["Drums", "Bass", "Pad", "Other"]),
        ("Verse", 16, ["Drums", "Bass", "Chords", "Pad", "Other"]),
        ("Build", 8, ["Drums", "Chords", "Pad", "Lead", "FX", "Other"]),
        ("Drop/Chorus", 16, ["Drums", "Bass", "Chords", "Pad", "Lead", "Vocal", "Other"]),
        ("Breakdown", 8, ["Chords", "Pad", "Vocal", "FX", "Other"]),
        ("Drop 2", 16, ["Drums", "Bass", "Chords", "Pad", "Lead", "Vocal", "Other"]),
        ("Outro", 8, ["Drums", "Bass", "Pad", "Other"]),
    ],
    "techno": [
        ("DJ Intro", 8, ["Drums", "FX", "Other"]),
        ("Groove", 16, ["Drums", "Bass", "Other"]),
        ("Main/Hypnotic", 16, ["Drums", "Bass", "Lead", "FX", "Other"]),
        ("Build", 8, ["Drums", "Lead", "FX", "Other"]),
        ("Drop", 16, ["Drums", "Bass", "Lead", "FX", "Other"]),
        ("Breakdown", 8, ["Pad", "FX", "Other"]),
        ("Drop 2", 16, ["Drums", "Bass", "Lead", "FX", "Other"]),
        ("Outro", 8, ["Drums", "Other"]),
    ],
    "pop": [
        ("Intro", 4, ["Chords", "Pad", "Vocal", "Other"]),
        ("Verse", 8, ["Bass", "Chords", "Pad", "Vocal", "Other"]),
        ("Pre-Chorus", 4, ["Bass", "Chords", "Pad", "Lead", "FX", "Other"]),
        ("Chorus", 8, ["Drums", "Bass", "Chords", "Pad", "Lead", "Vocal", "FX", "Other"]),
        ("Verse 2", 8, ["Drums", "Bass", "Chords", "Pad", "Vocal", "Other"]),
        ("Bridge", 8, ["Chords", "Pad", "Vocal", "Other"]),
        ("Final Chorus", 8, ["Drums", "Bass", "Chords", "Pad", "Lead", "Vocal", "FX", "Other"]),
        ("Outro", 4, ["Chords", "Pad", "Vocal", "Other"]),
    ],
    "trap": [
        ("Intro", 4, ["Chords", "Pad", "Other"]),
        ("Verse", 16, ["Drums", "Bass", "Chords", "Vocal", "Other"]),
        ("Pre-Hook", 4, ["Chords", "Pad", "Lead", "FX", "Other"]),
        ("Hook", 8, ["Drums", "Bass", "Chords", "Lead", "Vocal", "FX", "Other"]),
        ("Verse 2", 16, ["Drums", "Bass", "Chords", "Other"]),
        ("Outro", 4, ["Chords", "Pad", "Other"]),
    ],
    "drum n bass": [
        ("Intro", 8, ["Pad", "FX", "Other"]),
        ("Build", 8, ["Drums", "Pad", "Lead", "FX", "Other"]),
        ("Drop", 16, ["Drums", "Bass", "Pad", "Lead", "FX", "Other"]),
        ("Breakdown", 8, ["Pad", "Vocal", "Other"]),
        ("Drop 2", 16, ["Drums", "Bass", "Pad", "Lead", "FX", "Other"]),
        ("Outro", 8, ["Drums", "Pad", "Other"]),
    ],
    "ambient": [
        ("Texture", 8, ["Pad", "FX", "Other"]),
        ("Pulse", 8, ["Pad", "FX", "Other"]),
        ("Theme", 16, ["Chords", "Pad", "Lead", "Other"]),
        ("Drift", 8, ["Pad", "Other"]),
        ("Bloom", 16, ["Chords", "Pad", "Lead", "Other"]),
    ],
}
ARRANGEMENT_TEMPLATES["default"] = ARRANGEMENT_TEMPLATES["house"]


def classify_track_role(track_name: str) -> str:
    name_lower = track_name.lower()
    if any(k in name_lower for k in ["drum", "kit", "kick", "bd", "snare", "clap", "hat", "hh", "shaker", "perc"]):
        return "Drums"
    if any(k in name_lower for k in ["bass", "sub", "808", "sawbass"]):
        return "Bass"
    if any(k in name_lower for k in ["chord", "piano", "keys", "rhodes", "guitar"]):
        return "Chords"
    if any(k in name_lower for k in ["pad", "synth", "strings", "atmosphere"]):
        return "Pad"
    if any(k in name_lower for k in ["lead", "pluck", "riff", "melody", "hook"]):
        return "Lead"
    if any(k in name_lower for k in ["vocal", "vox", "chop", "singer"]):
        return "Vocal"
    if any(k in name_lower for k in ["fx", "riser", "noise", "sweep", "impact"]):
        return "FX"
    return "Other"


def map_section_to_scene(section_name: str, scene_count: int) -> int:
    if scene_count <= 1:
        return 0
    name = section_name.lower()
    if "drop" in name or "chorus" in name or "main" in name or "bloom" in name or "theme" in name:
        return scene_count - 1
    if "build" in name or "pre" in name or "groove" in name:
        return max(0, scene_count - 2)
    if "verse" in name or "pulse" in name:
        if scene_count > 2:
            return 1
        return 0
    if "break" in name or "drift" in name:
        if scene_count > 3:
            return 1
        return 0
    return 0


def generate_riser_notes(length_beats: int) -> list[dict[str, Any]]:
    notes = []
    rise_length = min(16, length_beats)
    start_beat = length_beats - rise_length
    num_notes = int(rise_length * 2)
    start_pitch = 36
    for i in range(num_notes):
        beat = start_beat + (i * 0.5)
        pitch = start_pitch + int((i / num_notes) * 24)
        notes.append({
            "pitch": pitch,
            "start": beat,
            "duration": 0.4,
            "velocity": int(40 + (i / num_notes) * 60),
            "mute": False
        })
    return notes


def generate_crash_notes() -> list[dict[str, Any]]:
    return [{
        "pitch": 49,
        "start": 0.0,
        "duration": 4.0,
        "velocity": 100,
        "mute": False
    }]


def _build_section_transitions(
    sections: list[tuple[str, int, str]],
) -> list[dict[str, Any]]:
    """Return actions that add a FX / Riser track with riser and crash clips at
    section boundaries.  Called from expanded_song_sketch_plan after the main
    track/clip creation loop.

    - Build sections get a rising sweep clip (pitch ramp, velocity ramp).
    - Main sections that immediately follow a build get a single crash cymbal clip.
    """
    if not any(energy == "build" for _, _, energy in sections):
        return []

    actions: list[dict[str, Any]] = [
        {"type": "create_midi_track", "name": "FX / Riser"},
        {"type": "set_track_volume", "track_name": "FX / Riser", "db": -12},
    ]

    prev_energy = ""
    for scene_index, (section, bars, energy) in enumerate(sections):
        length_beats = bars * 4
        if energy == "build":
            actions.append({
                "type": "create_midi_clip",
                "track_name": "FX / Riser",
                "clip_name": f"{section} riser",
                "scene_index": scene_index,
                "length_beats": length_beats,
                "notes": generate_riser_notes(length_beats),
            })
        elif energy == "main" and prev_energy == "build":
            actions.append({
                "type": "create_midi_clip",
                "track_name": "FX / Riser",
                "clip_name": f"{section} crash",
                "scene_index": scene_index,
                "length_beats": length_beats,
                "notes": generate_crash_notes(),
            })
        prev_energy = energy

    return actions


def existing_session_finisher_plan(message: str, vst_map: dict[str, str] | None = None) -> dict[str, Any]:
    from .queue import current_state
    lowered = message.lower()
    style = detect_style(message)
    
    style_key = "house"
    if "techno" in style or "techno" in lowered:
        style_key = "techno"
    elif "pop" in style or "pop" in lowered or "rock" in lowered or "country" in lowered:
        style_key = "pop"
    elif "trap" in style or "trap" in lowered or "hip hop" in lowered or "hip-hop" in lowered or "rap" in lowered or "hiphop" in lowered:
        style_key = "trap"
    elif "dnb" in style or "dnb" in lowered or "drum n bass" in lowered or "drum & bass" in lowered or "jungle" in lowered:
        style_key = "drum n bass"
    elif "ambient" in style or "ambient" in lowered or "cinematic" in lowered or "drift" in lowered:
        style_key = "ambient"
    elif "house" in style or "house" in lowered or "garage" in lowered:
        style_key = "house"
        
    template = ARRANGEMENT_TEMPLATES.get(style_key, ARRANGEMENT_TEMPLATES["default"])
    
    state = current_state()
    tracks = state.get("tracks", [])
    scene_count = state.get("scene_count", 0)
    
    max_clip_scene = -1
    for t in tracks:
        for c in t.get("clips", []):
            if c.get("scene_index", -1) > max_clip_scene:
                max_clip_scene = c.get("scene_index", -1)
                
    active_scenes_count = max(scene_count, max_clip_scene + 1)
    if active_scenes_count == 0:
        active_scenes_count = 1
        
    classified_tracks = []
    for t in tracks:
        name = t.get("name", "")
        role = classify_track_role(name)
        classified_tracks.append({
            "name": name,
            "role": role,
            "index": t.get("index", 0)
        })
        
    arrangement_sections_list = []
    queued_clips = set()
    actions = []

    # --- VST instrument loading ---
    _vst_map = {k.lower(): v for k, v in (vst_map or {}).items()}
    if _vst_map and classified_tracks:
        # Build track_name → [browser search queries] using the user's chosen VST per role
        vst_track_map: dict[str, list[str]] = {}
        for t in classified_tracks:
            role_key = t["role"].lower()  # e.g. "pad", "bass", "chords", "lead"
            plugin_name = _vst_map.get(role_key) or _vst_map.get("all")
            if plugin_name:
                vst_track_map[t["name"]] = [plugin_name]
        if vst_track_map:
            actions.append({
                "type": "load_user_vst_instruments",
                "tracks": vst_track_map,
            })

    if any(word in lowered for word in ["rename", "badly named", "track names", "name the tracks"]):
        actions.append({"type": "rename_tracks_from_devices"})
        
    start_beat = 0.0
    for section_name, bars, active_roles in template:
        length_beats = bars * 4
        mapped_scene_idx = map_section_to_scene(section_name, active_scenes_count)
        
        is_riser_section = any(k in section_name.lower() for k in ["build", "pre-chorus", "pre-hook"])
        is_crash_section = any(k in section_name.lower() for k in ["drop", "chorus", "hook", "main", "bloom"])
        
        section_active_tracks = []
        for t in classified_tracks:
            if t["role"] in active_roles:
                section_active_tracks.append(t["name"])
                
        if is_riser_section:
            section_active_tracks.append("AI Riser")
            clip_key = ("AI Riser", mapped_scene_idx)
            if clip_key not in queued_clips:
                queued_clips.add(clip_key)
                actions.append({
                    "type": "create_midi_clip",
                    "track_name": "AI Riser",
                    "clip_name": f"{section_name} - Rise",
                    "scene_index": mapped_scene_idx,
                    "length_beats": length_beats,
                    "notes": generate_riser_notes(length_beats)
                })
                
        if is_crash_section:
            section_active_tracks.append("AI Crash")
            clip_key = ("AI Crash", mapped_scene_idx)
            if clip_key not in queued_clips:
                queued_clips.add(clip_key)
                actions.append({
                    "type": "create_midi_clip",
                    "track_name": "AI Crash",
                    "clip_name": f"{section_name} - Crash",
                    "scene_index": mapped_scene_idx,
                    "length_beats": 4.0,
                    "notes": generate_crash_notes()
                })
                
        section_data = {
            "scene_index": mapped_scene_idx,
            "name": section_name,
            "start_beat": start_beat,
            "length_beats": length_beats,
        }
        if len(tracks) > 0:
            section_data["active_tracks"] = section_active_tracks
            
        arrangement_sections_list.append(section_data)
        start_beat += length_beats
        
    actions.extend([
        {
            "type": "copy_session_to_arrangement",
            "sections": arrangement_sections_list,
            "reuse_available_scenes": True
        },
        {"type": "set_song_position", "beat": 0},
        {"type": "start_playback", "beat": 0}
    ])
    
    detected_desc = ""
    if len(classified_tracks) > 0:
        detected_desc = "\n\n**Detected Track Classifications:**"
        for t in classified_tracks:
            detected_desc += f"\n- `{t['name']}` → Classified as **{t['role']}**"
            
    timeline_desc = "\n\n**Arrangement Timeline Structure:**"
    for sec in arrangement_sections_list:
        tracks_str = ", ".join(sec.get("active_tracks", [])) if "active_tracks" in sec else "All Tracks"
        timeline_desc += f"\n- **{sec['name']}** ({int(sec['length_beats']/4)} bars) → Scene {sec['scene_index']}. *Playing: {tracks_str}*"
        
    reply = (
        f"I analyzed your active loops in Session View and generated a custom **{style_key.title()}** arrangement. "
        "I've mapped out the sections on the timeline, using subtractive muting to build and release tension naturally, "
        "and generated custom rising sweeps and impact crashes at the major transitions without touching your original loops."
        f"{detected_desc}"
        f"{timeline_desc}"
    )
    
    return {
        "reply": reply,
        "actions": actions,
    }


def finisher_sections(text: str) -> list[tuple[str, int]]:
    return finisher_sections_for_style(text, detect_style(text))


def finisher_sections_for_style(text: str, style: str) -> list[tuple[str, int]]:
    curated = curated_sections_for_genre(style)
    if curated:
        return [(name, bars) for name, bars, _energy in curated]
    if any(word in text for word in ["hip hop", "hip-hop", "trap", "rap"]):
        return [("Intro", 4), ("Verse", 16), ("Hook", 8), ("Verse 2", 16), ("Final Hook", 8), ("Outro", 4)]
    if any(word in text for word in ["ambient", "cinematic"]):
        return [("Texture", 8), ("Pulse", 8), ("Theme", 16), ("Drift", 8), ("Bloom", 16)]
    if any(word in text for word in ["pop", "rock", "country"]):
        return [("Intro", 4), ("Verse", 8), ("Pre", 4), ("Chorus", 8), ("Verse 2", 8), ("Bridge", 8), ("Final Chorus", 8), ("Outro", 4)]
    if any(word in text for word in ["techno", "house", "garage", "dnb", "drum n bass", "jungle"]):
        return [("DJ Intro", 8), ("Groove", 8), ("Main", 16), ("Break", 8), ("Return", 16), ("Outro", 8)]
    return [("Intro", 8), ("Groove", 8), ("Hook", 16), ("Break", 8), ("Final Hook", 16), ("Outro", 8)]


def finisher_plan(message: str, mutation_type: str) -> dict[str, Any]:
    track_name = extract_track_reference(message)
    bars = extract_bars(message.lower())
    style = detect_style(message)
    seed = stable_seed({"message": message.lower(), "mutation_type": mutation_type, "bars": bars, "style": style})
    
    lowered = message.lower()
    seed = stable_seed({"message": lowered, "mutation_type": mutation_type, "bars": bars, "style": style})
    
    if "drum" in lowered or "ghost notes" in mutation_type:
        base_notes = library_drums(message, bars, genre=style)
        track_name = "AI Drums" if track_name == "AI Chords" else track_name
    elif "bass" in lowered:
        base_notes = library_bassline(message, bars, genre=style)
    elif "chord" in lowered or "pad" in lowered or "key" in lowered:
        base_notes = library_chords(message, bars, genre=style)
    else:
        base_notes = library_chords(message, bars, genre=style)

    if mutation_type == "mutate_clones":
        notes = mutate_clones(base_notes, 1, seed=seed)
        reply = "Queued a sibling variation (Mutation of Clones)."
    elif mutation_type == "humanize":
        notes = humanize_groove(base_notes, seed=seed, groove_profile=lookup_genre(style).groove_profile)
        reply = "Queued a humanized variation with seeded timing and velocity changes."
    elif mutation_type == "ghost_notes":
        notes = add_ghost_notes(base_notes, seed=seed)
        reply = "Queued a drum variation with added rhythmic ghost notes."
    else:
        notes = base_notes
        reply = "Queued a standard variation."

    actions = finisher_mutation(track_name, f"Mutated {mutation_type}", notes, bars)
    return {
        "reply": reply,
        "actions": actions,
    }

def subtractive_arrangement_plan(message: str) -> dict[str, Any]:
    actions = []
    
    if "intro" in message.lower():
        actions.extend(finisher_mutation("AI Drums", "Carved Intro", [], 8))
        actions.extend(finisher_mutation("AI Bass", "Carved Intro", [], 8))
        actions.extend(finisher_mutation("AI Melody", "Carved Intro", [], 8))
        reply = "Queued a subtractive arrangement: carved out an Intro by removing drums, bass, and lead."
    elif "breakdown" in message.lower():
        actions.extend(finisher_mutation("AI Drums", "Carved Breakdown", [], 8))
        reply = "Queued a subtractive arrangement: carved a breakdown by muting high-energy drums."
    else:
        actions.extend(finisher_mutation("AI Drums", "Carved Section", [], 8))
        reply = "Queued a generic subtractive arrangement."

    return {
        "reply": reply,
        "actions": actions,
    }


def edm_arrangement_plan(message: str, vst_map: dict[str, str] | None = None) -> dict[str, Any]:
    actions: list[dict[str, Any]] = [{"type": "set_tempo", "bpm": extract_bpm(message.lower()) or 126}]
    tracks = ["EDM Chords", "EDM Bass", "EDM Drums", "EDM Lead"]
    for track in tracks:
        actions.append({"type": "create_midi_track", "name": track})

    _vst_map = {k.lower(): v for k, v in (vst_map or {}).items()}
    vst_track_map: dict[str, list[str]] = {}
    role_mapping = {
        "EDM Chords": "chords",
        "EDM Bass": "bass",
        "EDM Lead": "lead",
        "EDM Drums": "drums"
    }
    for track_name, role_key in role_mapping.items():
        plugin_name = _vst_map.get(role_key) or _vst_map.get("all")
        if plugin_name:
            vst_track_map[track_name] = [plugin_name]

    if vst_track_map:
        actions.append({
            "type": "load_user_vst_instruments",
            "tracks": vst_track_map,
        })

    sections = default_edm_sections()

    for scene_index, (section, bars, parts) in enumerate(sections):
        actions.append({"type": "set_scene_name", "scene_index": scene_index, "name": section})
        energy = section_energy(section)
        style = detect_style(message)
        if parts.get("chords"):
            actions.append(scene_clip("EDM Chords", section, "Chords - voiced stabs", scene_index, library_chords(message, bars, energy, style), bars))
        if parts.get("bass"):
            bass = library_bassline(message, bars, "build" if section == "Build" else "main", style)
            if parts.get("lift"):
                bass = transpose_notes(bass, 12)
            actions.append(scene_clip("EDM Bass", section, "Bass - octave groove", scene_index, bass, bars))
        if parts.get("lead"):
            lead = library_melody(message, bars, energy, style)
            if parts.get("lift"):
                lead = transpose_notes(lead, 12)
            actions.append(scene_clip("EDM Lead", section, "Lead - hook phrase", scene_index, lead, bars))

        drum_mode = parts.get("drums")
        if drum_mode and drum_mode != "none":
            drums = library_drums(message, bars, "hats" if drum_mode == "hats" else ("build" if drum_mode == "light" else "main"), genre=style)
            if drum_mode == "hats":
                drums = filter_drums(drums, {42})
            actions.append(scene_clip("EDM Drums", section, "Drums - hats fills claps", scene_index, drums, bars))

    actions.append({"type": "copy_session_to_arrangement", "sections": arrangement_sections(sections)})
    actions.append({"type": "set_song_position", "beat": 0})
    actions.append({"type": "start_playback", "beat": 0})
    return {
        "reply": "Queued a basic EDM song arrangement: intro, build, drop, break, second drop, and outro.",
        "actions": actions,
    }


def edm_enhancement_plan(message: str, vst_map: dict[str, str] | None = None) -> dict[str, Any]:
    sections = default_edm_sections()
    
    stock_tracks = {}
    vst_track_map = {}
    
    _vst_map = {k.lower(): v for k, v in (vst_map or {}).items()}
    role_mapping = {
        "EDM Chords": "chords",
        "EDM Bass": "bass",
        "EDM Lead": "lead",
        "EDM Drums": "drums"
    }
    
    palette = edm_track_palette(message)
    for track_name, device_query in palette.items():
        role_key = role_mapping.get(track_name)
        plugin_name = _vst_map.get(role_key) if role_key else None
        if plugin_name:
            vst_track_map[track_name] = [plugin_name]
        else:
            stock_tracks[track_name] = device_query
            
    actions: list[dict[str, Any]] = []
    if stock_tracks:
        actions.append({
            "type": "load_stock_instruments",
            "tracks": stock_tracks,
        })
    if vst_track_map:
        actions.append({
            "type": "load_user_vst_instruments",
            "tracks": vst_track_map,
        })

    for scene_index, (section, bars, parts) in enumerate(sections):
        actions.append({"type": "set_scene_name", "scene_index": scene_index, "name": section})
        energy = section_energy(section)
        style = detect_style(message)
        if parts.get("chords"):
            actions.append(
                scene_clip("EDM Chords", section, "Chords - voiced stabs", scene_index, library_chords(message, bars, energy, style), bars)
            )
        if parts.get("bass"):
            bass = library_bassline(message, bars, "build" if section == "Build" else "main", style)
            if parts.get("lift"):
                bass = transpose_notes(bass, 12)
            actions.append(scene_clip("EDM Bass", section, "Bass - octave groove", scene_index, bass, bars))
        if parts.get("lead"):
            lead = library_melody(message, bars, energy, style)
            if parts.get("lift"):
                lead = transpose_notes(lead, 12)
            actions.append(scene_clip("EDM Lead", section, "Lead - hook phrase", scene_index, lead, bars))
        drum_mode = parts.get("drums")
        if drum_mode and drum_mode != "none":
            drums = library_drums(message, bars, "hats" if drum_mode == "hats" else ("build" if drum_mode == "light" else "main"), genre=style)
            if drum_mode == "hats":
                drums = filter_drums(drums, {42})
            actions.append(scene_clip("EDM Drums", section, "Drums - hats fills claps", scene_index, drums, bars))

    actions.extend(
        [
            {"type": "set_track_volume", "track_name": "EDM Chords", "db": -9},
            {"type": "set_track_volume", "track_name": "EDM Bass", "db": -7},
            {"type": "set_track_volume", "track_name": "EDM Drums", "db": -6},
            {"type": "set_track_volume", "track_name": "EDM Lead", "db": -10},
            {"type": "copy_session_to_arrangement", "sections": arrangement_sections(sections)},
            {"type": "set_song_position", "beat": 0},
            {"type": "start_playback", "beat": 0},
        ]
    )
    return {
        "reply": "Queued a richer EDM rewrite with stronger labels, denser drums, voiced chords, active bass, hook lead, instruments, and arrangement copy.",
        "actions": actions,
    }


def quick_default_idea_plan(message: str, vst_map: dict[str, str] | None = None) -> dict[str, Any]:
    return expanded_song_sketch_plan(message, vst_map=vst_map)


def expanded_song_sketch_plan(message: str, vst_map: dict[str, str] | None = None) -> dict[str, Any]:
    lowered = message.lower()
    style = detect_style(message)
    bpm = extract_bpm(lowered) or default_bpm_for_style(lowered, style)
    sections = expanded_sections(lowered, style)
    
    # Map each genre/style dynamically to its optimal signature tracks
    style_key = (style or "").lower().strip()
    if "ambient" in style_key or "cinematic" in style_key:
        allowed_tracks = {"Pad", "Chords", "Ambience", "Bass"}
    elif style_key in {"deep_house", "tech_house"}:
        allowed_tracks = {
            "Chords", "Pad", "Bass", "Riff", "Hook", "Bd", "Snare / Clap",
            "Hh / Sh / Rd", "Percussion", "Drum Instrument", "Ambience"
        }
    elif "techno" in style_key:
        allowed_tracks = {"Bass", "Pad", "Riff", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Drum Instrument", "Ambience"}
    elif "trap" in style_key or "hip hop" in style_key or "hip-hop" in style_key or "drill" in style_key:
        allowed_tracks = {"Chords", "Riff", "Bass", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Drum Instrument"}
    elif "jungle" in style_key:
        allowed_tracks = {"Bass", "Pad", "Riff", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Drum Instrument", "Ambience"}
    elif "drum n bass" in style_key or "dnb" in style_key:
        allowed_tracks = {"Bass", "Pad", "Riff", "Hook", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Drum Instrument"}
    elif "uk garage" in style_key or "garage" in style_key or "grime" in style_key or "2-step" in style_key:
        allowed_tracks = {"Chords", "Bass", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Drum Instrument", "Ambience"}
    elif "reggaeton" in style_key or "dancehall" in style_key or "dance hall" in style_key or "reggae" in style_key:
        allowed_tracks = {"Chords", "Hook", "Bass", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Drum Instrument"}
    elif "afrobeats" in style_key or "amapiano" in style_key:
        allowed_tracks = {"Chords", "Riff", "Hook", "Bass", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Drum Instrument"}
    elif "rock" in style_key or "country" in style_key:
        allowed_tracks = {"Chords", "Riff", "Hook", "Bass", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Drum Instrument"}
    elif "trance" in style_key:
        allowed_tracks = {"Chords", "Pad", "Riff", "Hook", "Bass", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Hh / Sh / Rd +", "Percussion", "Drum Instrument", "Ambience"}
    else:
        # Full standard track set for House, Pop, Downtempo, Hyperpop, and Default fallback
        allowed_tracks = {
            "Riff", "Hook", "Chords", "Ambience", "Bass", "Pad", "Drum Instrument",
            "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Hh / Sh / Rd +", "Bd"
        }

    # Parse explicit prompt additions/exclusions
    # 1. Negative filters (exclusions)
    neg_parts = re.split(r'\b(?:without|no|except|excluding|exclude|minus|discard|remove|off)\b', lowered)
    if len(neg_parts) > 1:
        # Check all segments after a negative keyword
        exclusion_text = " ".join(neg_parts[1:])
        if any(w in exclusion_text for w in ["chord", "progression", "piano", "keys"]):
            allowed_tracks.discard("Chords")
        if any(w in exclusion_text for w in ["pad", "pads"]):
            allowed_tracks.discard("Pad")
        if "riff" in exclusion_text:
            allowed_tracks.discard("Riff")
        if any(w in exclusion_text for w in ["hook", "lead", "melody", "melodies"]):
            allowed_tracks.discard("Hook")
        if any(w in exclusion_text for w in ["bass", "sub", "bassline"]):
            allowed_tracks.discard("Bass")
        if any(w in exclusion_text for w in ["ambience", "texture", "fx"]):
            allowed_tracks.discard("Ambience")
        if any(w in exclusion_text for w in ["drum", "drums", "beat", "beats"]):
            for t in ["Drum Instrument", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Hh / Sh / Rd +", "Percussion"]:
                allowed_tracks.discard(t)

    # Legacy fallback checks
    if "no chords" in lowered or "without chords" in lowered or "no chord" in lowered or "without chord" in lowered:
        allowed_tracks.discard("Chords")
    if "no pad" in lowered or "without pad" in lowered or "no pads" in lowered or "without pads" in lowered:
        allowed_tracks.discard("Pad")
    if "no riff" in lowered or "without riff" in lowered:
        allowed_tracks.discard("Riff")
    if "no hook" in lowered or "without hook" in lowered or "no lead" in lowered or "without lead" in lowered:
        allowed_tracks.discard("Hook")
    if "no bass" in lowered or "without bass" in lowered or "no bassline" in lowered or "without bassline" in lowered:
        allowed_tracks.discard("Bass")
    if "no ambience" in lowered or "without ambience" in lowered or "no texture" in lowered or "without texture" in lowered or "no fx" in lowered or "without fx" in lowered:
        allowed_tracks.discard("Ambience")
    if "no drums" in lowered or "without drums" in lowered or "no beat" in lowered or "without beat" in lowered or "no beats" in lowered or "without beats" in lowered:
        for t in ["Drum Instrument", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Hh / Sh / Rd +", "Percussion"]:
            allowed_tracks.discard(t)

    # 2. Positive filters ("only ...")
    if "only" in lowered:
        mentioned = set()
        if any(w in lowered for w in ["chord", "chords", "key", "keys"]):
            mentioned.add("Chords")
        if "pad" in lowered or "pads" in lowered:
            mentioned.add("Pad")
        if "riff" in lowered or "arp" in lowered:
            mentioned.add("Riff")
        if any(w in lowered for w in ["hook", "lead", "melody", "melodies"]):
            mentioned.add("Hook")
        if "bass" in lowered or "sub" in lowered or "bassline" in lowered:
            mentioned.add("Bass")
        if any(w in lowered for w in ["ambience", "texture", "fx"]):
            mentioned.add("Ambience")
        if any(w in lowered for w in ["drum", "drums", "beat", "beats", "kick", "snare", "clap", "hat", "hats", "perc", "percussion"]):
            mentioned.update(["Drum Instrument", "Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion"])
            if "trance" in style_key:
                mentioned.add("Hh / Sh / Rd +")
        
        if mentioned:
            allowed_tracks = allowed_tracks.intersection(mentioned)

    # 3. Drum Consolidation
    wants_consolidated_drums = any(
        phrase in lowered
        for phrase in [
            "consolidate drums",
            "consolidated drums",
            "single drum track",
            "drums on one track",
            "drum rack only",
            "single drums",
            "one drum track",
            "combined drums",
            "clean layout",
            "clean track",
            "fewer tracks"
        ]
    )
    if wants_consolidated_drums:
        for t in ["Bd", "Snare / Clap", "Hh / Sh / Rd", "Hh / Sh / Rd +", "Percussion"]:
            allowed_tracks.discard(t)
        allowed_tracks.add("Drum Instrument")

    track_names = [t for t in [
        "Riff",
        "Hook",
        "Chords",
        "Ambience",
        "Bass",
        "Pad",
        "Drum Instrument",
        "Snare / Clap",
        "Hh / Sh / Rd",
        "Percussion",
        "Hh / Sh / Rd +",
        "Bd",
    ] if t in allowed_tracks]

    actions: list[dict[str, Any]] = [{"type": "set_tempo", "bpm": bpm}]
    for track in track_names:
        actions.append({"type": "create_midi_track", "name": track})

    stock_tracks = {}
    vst_track_map = {}
    
    _vst_map = {k.lower(): v for k, v in (vst_map or {}).items()}
    role_mapping = {
        "Pad": "pad",
        "Bass": "bass",
        "Hook": "lead",
        "Riff": "lead",
        "Chords": "chords",
        "Ambience": "fx",
        "Drum Instrument": "drums",
    }
    
    palette = song_track_palette(message)
    # Filter the palette to only allowed tracks
    palette = {k: v for k, v in palette.items() if k in track_names}
    
    for drum_track in ["Snare / Clap", "Hh / Sh / Rd", "Percussion", "Hh / Sh / Rd +", "Bd"]:
        if drum_track in palette:
            del palette[drum_track]
            
    if "Drum Instrument" in track_names:
        palette["Drum Instrument"] = unique_candidates(
            role_palette(message, "bd") + role_palette(message, "snare") + role_palette(message, "hats")
        )
    
    for track_name, device_query in palette.items():
        role_key = role_mapping.get(track_name)
        plugin_name = _vst_map.get(role_key) if role_key else None
        if plugin_name:
            vst_track_map[track_name] = [plugin_name]
        else:
            stock_tracks[track_name] = device_query
            
    if stock_tracks:
        actions.append({
            "type": "load_stock_instruments",
            "tracks": stock_tracks,
        })
        
    if vst_track_map:
        actions.append({
            "type": "load_user_vst_instruments",
            "tracks": vst_track_map,
        })

    # Route individual drum tracks to the single Drum Instrument VST/host track
    if "Drum Instrument" in track_names:
        for drum_track in ["Snare / Clap", "Hh / Sh / Rd", "Percussion", "Hh / Sh / Rd +", "Bd"]:
            if drum_track in track_names:
                actions.append({
                    "type": "route_midi",
                    "source_track": drum_track,
                    "target_track": "Drum Instrument"
                })

    intro_strategies = {0: "drums_reveal", 1: "atmosphere", 2: "filtered"}
    intro_seed = sum(ord(char) for char in message) % 3 if style_key in {"deep_house", "tech_house"} else None
    intro_style = intro_strategies[intro_seed] if intro_seed is not None else None

    for scene_index, (section, bars, energy) in enumerate(sections):
        intro_allowed_tracks = set(track_names)
        if energy == "intro" and intro_style == "drums_reveal":
            intro_allowed_tracks = {"Bd", "Snare / Clap", "Hh / Sh / Rd"}
        elif energy == "intro" and intro_style == "atmosphere":
            intro_allowed_tracks = {"Chords", "Pad", "Ambience"}

        actions.append({"type": "set_scene_name", "scene_index": scene_index, "name": section})
        if "Chords" in track_names and "Chords" in intro_allowed_tracks:
            actions.append(scene_clip("Chords", section, "progression", scene_index, library_chords(message, bars, energy, style), bars))
        if "Pad" in track_names and "Pad" in intro_allowed_tracks:
            actions.append(scene_clip("Pad", section, "wide pad", scene_index, pad_notes(message, bars, energy, style), bars))
        if "Bass" in track_names and "Bass" in intro_allowed_tracks and energy != "intro":
            actions.append(scene_clip("Bass", section, "bassline", scene_index, library_bassline(message, bars, "build" if energy == "build" else "main", style), bars))
        if "Riff" in track_names and "Riff" in intro_allowed_tracks and energy in {"build", "main"}:
            actions.append(scene_clip("Riff", section, "riff", scene_index, riff_notes(message, bars, energy, style), bars))
        if "Hook" in track_names and "Hook" in intro_allowed_tracks and energy in {"main", "break"}:
            actions.append(scene_clip("Hook", section, "hook", scene_index, hook_notes(message, bars, energy, style), bars))
        if "Hh / Sh / Rd" in track_names and "Hh / Sh / Rd" in intro_allowed_tracks:
            actions.append(scene_clip("Hh / Sh / Rd", section, "hat groove", scene_index, drum_only(message, bars, energy, {42, 46, 49}, style), bars))
        if "Hh / Sh / Rd +" in track_names and "Hh / Sh / Rd +" in intro_allowed_tracks and energy in {"build", "main"}:
            actions.append(scene_clip("Hh / Sh / Rd +", section, "top lift", scene_index, drum_only(message, bars, "build", {42, 46, 49}, style), bars))
        if energy != "break":
            if "Bd" in track_names and "Bd" in intro_allowed_tracks:
                actions.append(scene_clip("Bd", section, "kick", scene_index, drum_only(message, bars, energy, {36}, style), bars))
            if "Snare / Clap" in track_names and "Snare / Clap" in intro_allowed_tracks:
                actions.append(scene_clip("Snare / Clap", section, "backbeat", scene_index, drum_only(message, bars, energy, {38, 39}, style), bars))
            if "Percussion" in track_names and "Percussion" in intro_allowed_tracks:
                actions.append(scene_clip("Percussion", section, "perc", scene_index, percussion_notes(bars, energy, style), bars))
        if "Drum Instrument" in track_names and "Drum Instrument" in intro_allowed_tracks and not any(t in track_names for t in ["Bd", "Snare / Clap", "Hh / Sh / Rd"]):
            actions.append(scene_clip("Drum Instrument", section, "drums", scene_index, library_drums(message, bars, energy, genre=style), bars))
        if "Ambience" in track_names and "Ambience" in intro_allowed_tracks:
            actions.append(scene_clip("Ambience", section, "texture", scene_index, ambience_notes(message, bars, energy, style), bars))

    actions.extend(_build_section_transitions(sections))

    volume_actions = []
    default_volumes = {
        "Chords": -11,
        "Pad": -14,
        "Riff": -12,
        "Hook": -10,
        "Bass": -7,
        "Bd": -6,
        "Snare / Clap": -9,
        "Hh / Sh / Rd": -13,
        "Hh / Sh / Rd +": -15,
        "Percussion": -14,
        "Ambience": -18,
        "Drum Instrument": -6,
    }
    for track_name in track_names:
        if track_name in default_volumes:
            volume_actions.append({"type": "set_track_volume", "track_name": track_name, "db": default_volumes[track_name]})
            
    actions.extend(volume_actions)
    actions.extend([
        {"type": "copy_session_to_arrangement", "sections": arrangement_sections([(name, bars, {}) for name, bars, _energy in sections])},
        {"type": "set_song_position", "beat": 0},
        {"type": "start_playback", "beat": 0},
    ])
    return {
        "reply": "Queued an expanded song sketch with dedicated musical parts, genre-aware Ableton instrument candidates, arrangement copy, and playback.",
        "actions": actions,
    }


def default_bpm_for_style(text: str, style: str | None = None) -> int:
    curated_bpm = curated_default_bpm(style or detect_style(text))
    if curated_bpm is not None:
        return curated_bpm
    if any(word in text for word in ["drum n bass", "dnb", "jungle"]):
        return 172
    if any(word in text for word in ["trap", "hyperpop", "drill"]):
        return 140
    if any(word in text for word in ["hip-hop", "hip hop", "lo-fi", "lofi"]):
        return 88
    if any(word in text for word in ["reggaeton", "dance hall", "dancehall", "reggae"]):
        return 96
    if any(word in text for word in ["trance"]):
        return 138
    if any(word in text for word in ["techno"]):
        return 132
    if any(word in text for word in ["mainstage"]):
        return 128
    if any(word in text for word in ["house", "garage"]):
        return 124
    if any(word in text for word in ["downtempo"]):
        return 92
    if any(word in text for word in ["ambient", "cinematic"]):
        return 78
    if any(word in text for word in ["pop"]):
        return 104
    return 126


def expanded_sections(text: str, style: str | None = None) -> list[tuple[str, int, str]]:
    curated = curated_sections_for_genre(style or detect_style(text))
    if curated:
        return curated
    if any(word in text for word in ["ambient", "cinematic"]):
        return [("Texture", 8, "intro"), ("Pulse", 8, "build"), ("Theme", 16, "main"), ("Drift", 8, "break"), ("Bloom", 16, "main")]
    if any(word in text for word in ["pop", "rock and country"]):
        return [("Intro", 4, "intro"), ("Verse", 8, "build"), ("Pre", 4, "build"), ("Chorus", 8, "main"), ("Verse 2", 8, "build"), ("Final Chorus", 8, "main"), ("Outro", 4, "intro")]
    if any(word in text for word in ["hip-hop", "hip hop", "trap", "lo-fi", "lofi"]):
        return [("Intro", 4, "intro"), ("Verse", 16, "main"), ("Hook", 8, "main"), ("Verse 2", 16, "build"), ("Final Hook", 8, "main"), ("Outro", 4, "intro")]
    return [("Intro", 8, "intro"), ("Groove", 8, "build"), ("Hook", 16, "main"), ("Break", 8, "break"), ("Final Hook", 16, "main"), ("Outro", 8, "intro")]


def genre_words() -> list[str]:
    return [
        "acid house",
        "ambient house",
        "bass house",
        "chicago house",
        "dance and mainstage",
        "downtempo",
        "drum n bass",
        "dnb",
        "dubstep",
        "grime",
        "hip hop",
        "hip-hop",
        "deep house",
        "disco house",
        "electro house",
        "french house",
        "funky house",
        "garage house",
        "g-house",
        "house",
        "minimal house",
        "progressive house",
        "90s jungle",
        "jungle",
        "modern pop",
        "reggae",
        "dance hall",
        "dancehall",
        "reggaeton",
        "rock and country",
        "tech house",
        "techno",
        "tribal house",
        "tropical house",
        "trance",
        "trap",
        "hyperpop",
        "uk garage",
        "afrobeats",
        "amapiano",
    ]


ROLE_PALETTES: dict[str, list[str]] = {
    "chords": ["Electric Piano", "Analog Chords", "Wavetable Chords", "Meld Chords", "Operator Chords", "Electric", "Analog", "Wavetable", "Meld", "Operator"],
    "pad": ["Warm Pad", "Deep Pad", "Atmospheric Pad", "Analog Pad", "Wavetable Pad", "Meld Pad", "Tension Pad", "Meld", "Wavetable", "Analog", "Tension"],
    "riff": ["Pluck Synth", "Acid Riff", "Short Lead", "Drift Pluck", "Wavetable Pluck", "Operator Pluck", "Meld Pluck", "Drift", "Wavetable", "Operator", "Meld"],
    "hook": ["Bright Lead", "Square Lead", "Saw Lead", "Analog Lead", "Wavetable Lead", "Meld Lead", "Drift Lead", "Operator Lead", "Wavetable", "Meld", "Drift", "Operator"],
    "bass": ["Basic Sub", "Acid Bass", "Sub Bass", "Electric Bass", "Operator Bass", "Drift Bass", "Analog Bass", "Wavetable Bass", "Operator", "Drift", "Analog", "Wavetable"],
    "ambience": ["Ambient Texture", "Vinyl Crackle", "Rain Texture", "Meld Texture", "Wavetable Texture", "Tension Texture", "Collision Texture", "Meld", "Wavetable", "Tension", "Collision"],
    "bd": ["909 Core Kit", "808 Core Kit", "707 Core Kit", "606 Core Kit"],
    "snare": ["909 Core Kit", "808 Core Kit", "707 Core Kit", "606 Core Kit"],
    "hats": ["909 Core Kit", "808 Core Kit", "707 Core Kit", "606 Core Kit"],
    "percussion": ["909 Core Kit", "808 Core Kit", "707 Core Kit", "606 Core Kit", "Collision Percussion", "Collision"],
}

DRUM_ROLES = {"bd", "snare", "hats", "percussion"}

DEFAULT_ABLETON_FACTORY_PACK_ROOTS = (
    Path.home() / "Music" / "Ableton" / "Factory Packs",
    Path.home() / "Library" / "Application Support" / "Ableton" / "Factory Packs",
)

DRUM_KIT_FALLBACKS = [
    "909 Core Kit",
    "808 Core Kit",
    "707 Core Kit",
    "606 Core Kit",
    "Techno Kit",
]


STOCK_PRESET_PALETTES: dict[str, dict[str, list[str]]] = {
    "house": {
        "chords": ["Electric Piano", "Analog Chords", "Wavetable Chords"],
        "pad": ["Analog Pad", "Warm Pad", "Wavetable Pad"],
        "riff": ["Drift Pluck", "Analog Pluck", "Wavetable Pluck"],
        "hook": ["Analog Lead", "Wavetable Lead", "Drift Lead"],
        "bass": ["Analog Bass", "Drift Bass", "Operator Bass"],
        "bd": ["909 Core Kit", "707 Core Kit", "Techno Kit", "808 Core Kit", "606 Core Kit"],
        "snare": ["707 Core Kit", "909 Core Kit", "Techno Kit", "606 Core Kit", "808 Core Kit"],
        "hats": ["606 Core Kit", "707 Core Kit", "Techno Kit", "909 Core Kit", "808 Core Kit"],
        "percussion": ["707 Core Kit", "606 Core Kit", "Techno Kit", "Collision Percussion"],
    },
    "acid_house": {
        "chords": ["Analog Chords", "Operator Chords", "Whose Organ", "TX Piano"],
        "pad": ["Slow Motion Pad", "Slow 5th Pad", "MembUFORelease"],
        "riff": ["Acid Riff", "Operator Pluck", "Drift Pluck", "Percu Tone"],
        "hook": ["Analog Lead", "Retro Steam Lead", "Metal-o Feedbackisimo Lead"],
        "bass": ["Acid Bass", "Analog Bass", "Operator Bass", "Drift Bass", "sawbass", "Gooey Sub Rubber"],
        "bd": ["Kit-909 Classic", "Kit-909 Tresor", "Kit-909 Myrtle", "Kit-909 Alteration", "Kit-606 Cathode"],
        "snare": ["Kit-909 Classic", "Kit-909 Tresor", "Kit-707 Classic"],
        "hats": ["Kit-909 Classic", "Kit-606 Cathode", "Kit-707 Classic"],
        "percussion": ["Kit-909 Classic", "Kit-606 Cathode", "Kit-C78 Classic"],
    },
    "ambient_house": {
        "chords": ["Grand Piano Pad", "Grand Piano Lost Ship", "elec. piano", "TX Piano"],
        "pad": ["Slow Motion Pad", "Slow 5th Pad", "sludgepad", "bocpad", "czpad", "bellpad"],
        "riff": ["Tension Pluck", "Collision", "Bell", "FM Prayer Bell", "TwoPluckedStrings"],
        "hook": ["Dreamy", "SlowMotion", "AirMembrane", "AirPlate"],
        "bass": ["Warm Bass", "Deep Sub", "Operator Bass", "Curt Bass"],
        "bd": ["Kit-Wood", "Kit-White", "Acoustified Kit", "Grounded Kit", "Kindified Kit"],
        "snare": ["Kit-Wood", "Kit-White", "Grounded Kit"],
        "hats": ["Kit-Wood", "Grounded Kit", "Kindified Kit"],
        "percussion": ["Kit-Wood", "Kit-Ethno", "Grounded Kit", "AirPlate"],
        "ambience": ["Slow Motion Pad", "Slow 5th Pad", "sludgepad", "bocpad", "czpad", "bellpad", "MembUFORelease"],
    },
    "bass_house": {
        "chords": ["Wavetable Chords", "Meld Chords", "BigChord"],
        "pad": ["Dark Pad", "Meld Pad", "Wavetable Texture"],
        "riff": ["Glitch Machine 2", "TheFMMachine", "MegaSquare", "Wavetable Pluck"],
        "hook": ["Wavetable Lead", "MegaSquare", "VideoGameLead", "Metal-o Feedbackisimo Lead"],
        "bass": ["Wavetable Bass", "Operator Bass", "Drift Bass", "Gooey Sub Rubber", "MatrixBass", "FMBass"],
        "bd": ["Kit-808 Classic", "Kit-808 Magnetikz", "Kit-808 Babblebox", "Kit-909 Mastodon", "Electrified Kit"],
        "snare": ["Kit-808 Classic", "Kit-DMX Tightdope", "Kit-909 Mastodon"],
        "hats": ["Kit-808 Classic", "Kit-909 Mastodon", "Electrified Kit"],
        "percussion": ["Electrified Kit", "Kit-808 Babblebox", "Static Kit (Glitch)"],
        "ambience": ["AllFX", "KJ Sawka FX Swells", "Cluster Sound FX - Grainer"],
    },
    "chicago_house": {
        "chords": ["TX Piano", "Grand Piano Classic LA Stack", "elec. piano", "Whose Organ"],
        "pad": ["Slow Motion Pad", "Grand Piano Pad"],
        "riff": ["Sine Keys", "Whose Organ", "Electric Piano"],
        "hook": ["Vocal Chop", "Piano House", "Whose Organ", "TX Piano"],
        "bass": ["Curt Bass", "Warm Bass", "Analog Bass", "Operator Bass"],
        "bd": ["Kit-707 Classic", "Kit-909 Classic", "Kit-808 Classic", "Kit-Trax Classic", "Kit-DMX Classic"],
        "snare": ["Kit-707 Classic", "Kit-909 Classic", "Kit-DMX Classic"],
        "hats": ["Kit-707 Classic", "Kit-909 Classic", "Kit-606 Classic"],
        "percussion": ["Kit-707 Classic", "Kit-Trax Classic", "Kit-DMX Classic"],
    },
    "deep_house": {
        "chords": ["Rhodes", "Electric Piano", "Analog Chords"],
        "pad": ["Warm Pad", "Analog Pad", "Meld Pad"],
        "riff": ["Electric Riff", "Drift Pluck", "Wavetable Pluck"],
        "hook": ["Electric Lead", "Drift Lead", "Wavetable Lead"],
        "bass": ["Sub Bass", "Analog Bass", "Drift Bass", "Operator Bass"],
        "bd": ["707 Core Kit", "606 Core Kit", "909 Core Kit", "Techno Kit"],
        "snare": ["707 Core Kit", "606 Core Kit", "909 Core Kit", "Techno Kit"],
        "hats": ["606 Core Kit", "707 Core Kit", "909 Core Kit", "Techno Kit"],
    },
    "disco_house": {
        "chords": ["Guitar-Chopper Chords", "TX Piano", "Grand Piano Classic LA Stack", "synth. strings"],
        "pad": ["Guitar-French Guitar Pad", "Grand Piano Pad"],
        "riff": ["Guitar-Chopper Chords", "Guitar-French Guitar Pad", "synth. strings"],
        "hook": ["synth. strings", "brass ens. 1", "brass ens. 2", "violin"],
        "bass": ["Electric Bass", "Electric Bass Slap", "Electric Bass Open", "Analog Bass"],
        "bd": ["Kit-707 Classic", "Kit-909 Classic", "Kit-DMX Classic", "Kit-Trax Classic", "Kit-Yellow"],
        "snare": ["Kit-707 Classic", "Kit-909 Classic", "Kit-DMX Classic", "Kit-Yellow"],
        "hats": ["Kit-707 Classic", "Kit-909 Classic", "Kit-Trax Classic"],
        "percussion": ["Kit-Yellow", "Kit-Wood", "Kit-Trax Classic"],
    },
    "electro_house": {
        "chords": ["Wavetable Chords", "BigChord", "Meld Chords"],
        "pad": ["Wide Pad", "Wavetable Pad", "Meld Pad"],
        "riff": ["MegaSquare", "VideoGameLead", "TheFMMachine"],
        "hook": ["Wavetable Lead", "MegaSquare", "Retro Steam Lead", "Metal-o Feedbackisimo Lead"],
        "bass": ["Wavetable Bass", "MegaSquare", "FMBass", "Gooey Sub Rubber"],
        "bd": ["Kit-909 Mastodon", "Kit-808 Magnetikz", "Electrified Kit", "Kit-Largeness", "Kit-Meaty"],
        "snare": ["Kit-909 Mastodon", "Kit-DMX Steroid", "Kit-Largeness"],
        "hats": ["Electrified Kit", "Kit-909 Mastodon", "Kit-808 Magnetikz"],
        "percussion": ["Electrified Kit", "Kit-Meaty", "Kit-Largeness"],
    },
    "french_house": {
        "chords": ["Guitar-Chopper Chords", "Guitar-French Guitar Pad", "Grand Piano Classic LA Stack", "synth. strings"],
        "pad": ["Guitar-French Guitar Pad", "Grand Piano Pad", "Slow Motion Pad"],
        "riff": ["Guitar-Chopper Chords", "synth. strings", "TX Piano"],
        "hook": ["brass ens. 1", "synth. strings", "vibraphone", "bell"],
        "bass": ["Electric Bass Slap", "Electric Bass Open", "sawbass", "Warm Bass"],
        "bd": ["Kit-909 Classic", "Kit-707 Classic", "Kit-DMX Studio", "Kit-Trax Deeptrax", "Kit-Yellow"],
        "snare": ["Kit-909 Classic", "Kit-707 Classic", "Kit-DMX Studio"],
        "hats": ["Kit-707 Classic", "Kit-909 Classic", "Kit-Trax Deeptrax"],
        "percussion": ["Kit-Yellow", "Kit-Trax Deeptrax", "Kit-DMX Studio"],
    },
    "funky_house": {
        "chords": ["Guitar-Chopper Chords", "TX Piano", "Whose Organ", "brass ens. 1"],
        "pad": ["Grand Piano Pad", "Guitar-French Guitar Pad"],
        "riff": ["Guitar-Chopper Chords", "Electric Riff", "brass ens. 2"],
        "hook": ["brass ens. 1", "Whose Organ", "TX Piano", "vibraphone"],
        "bass": ["Electric Bass Slap", "Electric Bass", "sawbass", "Curt Bass"],
        "bd": ["Kit-707 Freshen Up", "Kit-909 Classic", "Kit-DMX Classic", "Kit-Yellow", "Kit-Wood"],
        "snare": ["Kit-707 Freshen Up", "Kit-909 Classic", "Kit-DMX Classic"],
        "hats": ["Kit-707 Freshen Up", "Kit-606 Classic", "Kit-909 Classic"],
        "percussion": ["Kit-Wood", "Kit-Yellow", "Kit-DMX Classic"],
    },
    "garage_house": {
        "chords": ["Whose Organ", "elec. piano", "TX Piano", "Grand Piano Classic LA Stack"],
        "pad": ["Warm Pad", "Grand Piano Pad"],
        "riff": ["Whose Organ", "Sine Keys", "elec. organ"],
        "hook": ["Vocal Chop", "TX Piano", "Whose Organ"],
        "bass": ["Whose Organ", "elec. organ", "Operator Bass", "Warm Bass"],
        "bd": ["Kit-909 Classic", "Kit-707 Classic", "Kit-606 Classic", "Kit-Trax Classic", "Otari Bounce Kit"],
        "snare": ["Kit-909 Classic", "Kit-707 Classic", "Otari Bounce Kit"],
        "hats": ["Kit-606 Classic", "Kit-909 Classic", "Kit-707 Classic"],
        "percussion": ["Kit-Trax Classic", "Otari Bounce Kit", "Kit-707 Classic"],
    },
    "g_house": {
        "chords": ["Analog Chords", "Dark Pad", "Whose Organ"],
        "pad": ["Slow Motion Pad", "Dark Pad", "Cluster Sound FX - Grainer"],
        "riff": ["Drift Pluck", "Wavetable Pluck", "Percu Bass"],
        "hook": ["Vocal Chop", "MegaSquare", "Trap Lead", "Retro Steam Lead"],
        "bass": ["808 Bass", "Gooey Sub Rubber", "Operator Bass", "Drift Bass", "MatrixBass"],
        "bd": ["Kit-808 Classic", "Kit-DMX Tightdope", "Kit-DMX Bust It", "Kit-909 Mastodon", "Swang Bap Kit"],
        "snare": ["Kit-DMX Tightdope", "Kit-808 Classic", "Swang Bap Kit"],
        "hats": ["Kit-808 Classic", "Kit-DMX Tightdope", "Swang Bap Kit"],
        "percussion": ["Kit-DMX Bust It", "Swang Bap Kit", "Static Kit (Glitch)"],
        "ambience": ["Slow Motion Pad", "Cluster Sound FX - Grainer", "AllFX"],
    },
    "minimal_house": {
        "chords": ["Analog Chords", "Sine Keys", "Whose Organ"],
        "pad": ["Slow 5th Pad", "AirMembrane", "Dreamy"],
        "riff": ["Percu Tone", "TwoPluckedStrings", "Drift Pluck"],
        "hook": ["HypnoticFM", "ElectricSeq", "PureFMSequence"],
        "bass": ["Operator Bass", "Drift Bass", "Warm Bass", "Percu Bass"],
        "bd": ["Kit-Minimum", "Kit-606 Classic", "Kit-606 Cathode", "Kit-707 Studio", "Grounded Kit"],
        "snare": ["Kit-Minimum", "Kit-606 Classic", "Kit-707 Studio"],
        "hats": ["Kit-606 Classic", "Kit-Minimum", "Kit-707 Studio"],
        "percussion": ["Kit-Minimum", "Grounded Kit", "Percu Tone"],
    },
    "progressive_house": {
        "chords": ["Wavetable Chords", "BigChord", "Grand Piano Classic LA Stack", "Analog Chords"],
        "pad": ["Slow Motion Pad", "Grand Piano Pad", "Dreamy", "WarmStrings"],
        "riff": ["Wavetable Pluck", "ElectricSeq", "HypnoticFM"],
        "hook": ["Wavetable Lead", "MegaSquare", "SlowMotion", "Retro Steam Lead"],
        "bass": ["Wavetable Bass", "Drift Bass", "Warm Bass", "MatrixBass"],
        "bd": ["Kit-909 Classic", "Kit-909 Myrtle", "Kit-Largeness", "Electrified Kit", "Kit-707 Studio"],
        "snare": ["Kit-909 Classic", "Kit-Largeness", "Electrified Kit"],
        "hats": ["Kit-909 Classic", "Kit-707 Studio", "Electrified Kit"],
        "percussion": ["Electrified Kit", "Kit-707 Studio", "Kit-909 Myrtle"],
    },
    "tech_house": {
        "chords": ["Analog Chords", "Drift Chords", "Wavetable Chords"],
        "pad": ["Dark Pad", "Meld Pad", "Wavetable Pad"],
        "riff": ["Acid Riff", "Operator Pluck", "Drift Pluck"],
        "hook": ["Operator Lead", "Drift Lead", "Meld Lead"],
        "bass": ["Operator Bass", "Drift Bass", "Analog Bass"],
        "bd": ["Techno Kit", "909 Core Kit", "606 Core Kit", "707 Core Kit"],
        "snare": ["Techno Kit", "909 Core Kit", "707 Core Kit", "606 Core Kit"],
        "hats": ["Techno Kit", "606 Core Kit", "909 Core Kit", "707 Core Kit"],
        "percussion": ["Techno Kit", "909 Core Kit", "606 Core Kit", "Collision Percussion"],
    },
    "tribal_house": {
        "chords": ["Analog Chords", "Slow 5th Pad", "Whose Organ"],
        "pad": ["Slow Motion Pad", "AirMembrane", "MembUFORelease"],
        "riff": ["AfroBars1", "AfroBars2", "Percu Tone", "Bongo", "Conga"],
        "hook": ["brass ens. 1", "flute", "Metal Agogo", "Dynamic Klang"],
        "bass": ["Warm Bass", "Operator Bass", "Curt Bass", "Analog Bass"],
        "bd": ["Kit-Ethno", "Kit-Wood", "Kit-C78 Classic", "Kit-808 Classic", "AfroBars1", "AfroBars2", "Grounded Kit"],
        "snare": ["Kit-Ethno", "Kit-Wood", "Kit-C78 Classic"],
        "hats": ["Kit-Ethno", "Kit-Wood", "Grounded Kit"],
        "percussion": ["Kit-Ethno", "Kit-Wood", "AfroBars1", "AfroBars2", "Conga C78"],
        "ambience": ["Slow Motion Pad", "AirMembrane", "MembUFORelease"],
    },
    "tropical_house": {
        "chords": ["elec. piano", "TX Piano", "Grand Piano Equal Bright Production", "Guitar-Soft Tremolo Room"],
        "pad": ["Guitar-French Guitar Pad", "Grand Piano Thin Air", "Slow Motion Pad"],
        "riff": ["Tension Pluck", "Collision", "vibraphone", "crispy xylophone", "bell"],
        "hook": ["flute", "bell", "vibraphone", "fairy tale", "Wavetable Lead"],
        "bass": ["Warm Bass", "Curt Bass", "Electric Bass Open", "Drift Bass"],
        "bd": ["Kit-Wood", "Kit-Yellow", "Kit-707 Freshen Up", "Acoustified Kit", "Kindified Kit"],
        "snare": ["Kit-Wood", "Kit-Yellow", "Acoustified Kit"],
        "hats": ["Kit-Wood", "Kit-707 Freshen Up", "Kindified Kit"],
        "percussion": ["Kit-Wood", "Kit-Ethno", "Kindified Kit", "vibraphone"],
        "ambience": ["Guitar-French Guitar Pad", "Grand Piano Thin Air", "Slow Motion Pad"],
    },
    "techno": {
        "chords": ["Analog Chords", "Drift Chords", "Operator Chords"],
        "pad": ["Dark Pad", "Analog Pad", "Meld Pad", "Wavetable Pad"],
        "riff": ["Hypnotic Riff", "Operator Pluck", "Drift Pluck"],
        "hook": ["Minimal Hook", "Operator Lead", "Drift Lead"],
        "bass": ["Driving Bass", "Operator Bass", "Drift Bass", "Analog Bass"],
        "bd": ["Techno Kit", "909 Core Kit", "606 Core Kit", "808 Core Kit"],
        "snare": ["Techno Kit", "909 Core Kit", "707 Core Kit", "606 Core Kit"],
        "hats": ["Techno Kit", "606 Core Kit", "909 Core Kit", "707 Core Kit"],
        "percussion": ["Techno Kit", "909 Core Kit", "Collision Percussion", "606 Core Kit"],
    },
    "drum n bass": {
        "pad": ["Atmospheric Pad", "Wavetable Pad", "Meld Pad"],
        "riff": ["Operator Pluck", "Wavetable Pluck", "Drift Pluck"],
        "hook": ["Wavetable Lead", "Meld Lead", "Operator Lead"],
        "bass": ["Reese Bass", "Wavetable Bass", "Operator Bass", "Drift Bass"],
        "bd": ["Break Kit", "909 Core Kit", "808 Core Kit", "Techno Kit"],
        "snare": ["Break Kit", "909 Core Kit", "808 Core Kit", "Techno Kit"],
        "hats": ["Break Kit", "909 Core Kit", "808 Core Kit", "606 Core Kit"],
        "percussion": ["Break Kit", "Collision Percussion", "909 Core Kit"],
    },
    "uk garage": {
        "chords": ["Electric Piano", "Wavetable Chords", "Drift Chords"],
        "pad": ["Warm Pad", "Wavetable Pad", "Meld Pad"],
        "riff": ["Garage Pluck", "Drift Pluck", "Wavetable Pluck"],
        "hook": ["Garage Lead", "Wavetable Lead", "Drift Lead"],
        "bass": ["Bouncy Bass", "Operator Bass", "Drift Bass", "Analog Bass"],
        "bd": ["909 Core Kit", "808 Core Kit", "707 Core Kit", "Techno Kit"],
        "snare": ["909 Core Kit", "808 Core Kit", "707 Core Kit", "Techno Kit"],
        "hats": ["606 Core Kit", "909 Core Kit", "707 Core Kit", "Techno Kit"],
    },
    "trap": {
        "chords": ["Wavetable Chords", "Analog Chords", "Drift Chords"],
        "pad": ["Moody Pad", "Meld Pad", "Wavetable Pad"],
        "riff": ["Trap Pluck", "Drift Pluck", "Wavetable Pluck"],
        "hook": ["Trap Lead", "Wavetable Lead", "Operator Lead"],
        "bass": ["808 Bass", "Sub Bass", "Operator Bass", "Analog Bass"],
        "bd": ["808 Core Kit", "909 Core Kit", "Techno Kit"],
        "snare": ["808 Core Kit", "909 Core Kit", "707 Core Kit"],
        "hats": ["808 Core Kit", "909 Core Kit", "606 Core Kit"],
    },
}


def ableton_factory_pack_roots() -> tuple[Path, ...]:
    configured = os.environ.get("VIBELTON_ABLETON_FACTORY_PACK_ROOTS", "")
    if configured.strip():
        return tuple(Path(part).expanduser() for part in configured.split(os.pathsep) if part.strip())
    return DEFAULT_ABLETON_FACTORY_PACK_ROOTS


def kit_query_name(path: Path) -> str:
    return path.stem.strip()


def kit_search_text(path: Path) -> str:
    return " ".join(part.lower() for part in path.with_suffix("").parts)


def is_stock_drum_kit(path: Path) -> bool:
    if path.suffix.lower() != ".adg":
        return False
    text = kit_search_text(path)
    name = path.stem.lower()
    if "factory packs" not in text:
        return False
    if "drum hits" in text:
        return False
    if "/drums/" not in path.as_posix().lower():
        return False
    return "kit" in name or "drum" in name


@lru_cache(maxsize=8)
def discover_installed_drum_kits(roots: tuple[Path, ...] | None = None) -> tuple[dict[str, str], ...]:
    search_roots = roots or ableton_factory_pack_roots()
    kits: dict[str, dict[str, str]] = {}
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.adg"):
            if not is_stock_drum_kit(path):
                continue
            name = kit_query_name(path)
            key = name.lower()
            if key in kits:
                continue
            kits[key] = {
                "name": name,
                "path": str(path),
                "search_text": kit_search_text(path),
            }
    return tuple(sorted(kits.values(), key=lambda item: item["name"].lower()))


def score_drum_kit(kit: dict[str, str], text: str, style: str, role: str) -> int:
    haystack = f"{kit.get('name', '')} {kit.get('search_text', '')}".lower()
    prompt = text.lower()
    score = 0

    style_terms = {
        "acid_house": ["909", "303", "acid", "606", "classic", "tresor", "myrtle", "alteration", "cathode"],
        "ambient_house": ["wood", "white", "acoustified", "grounded", "kindified", "granular", "pitchy", "shadowed"],
        "bass_house": ["808", "909", "electrified", "magnetikz", "babblebox", "mastodon", "largeness", "meaty"],
        "chicago_house": ["707", "909", "808", "trax", "dmx", "classic", "freshen"],
        "deep_house": ["707", "606", "909", "minimum", "yellow", "wood", "grounded", "designer"],
        "disco_house": ["707", "909", "dmx", "trax", "yellow", "classic", "freshen"],
        "electro_house": ["909", "808", "electrified", "mastodon", "largeness", "meaty", "dmx", "steroid"],
        "french_house": ["909", "707", "dmx", "trax", "deeptrax", "yellow", "studio"],
        "funky_house": ["707", "909", "dmx", "yellow", "wood", "freshen", "classic"],
        "garage_house": ["909", "707", "606", "trax", "otari", "bounce", "classic"],
        "g_house": ["808", "dmx", "tightdope", "bust it", "909", "swang", "golden era"],
        "minimal_house": ["minimum", "606", "707", "grounded", "cathode", "studio", "clean"],
        "progressive_house": ["909", "myrtle", "largeness", "electrified", "707", "studio"],
        "tech_house": ["techno", "909", "606", "minimum", "carbon", "designer", "digicussion", "tresor"],
        "tribal_house": ["ethno", "wood", "c78", "808", "afro", "grounded", "conga", "bongo"],
        "tropical_house": ["wood", "yellow", "707", "freshen", "acoustified", "kindified", "ethno"],
        "techno": ["techno", "909", "606", "industrial", "metal", "carbon", "carbonized", "scorched", "burned", "raged", "wicked", "minimum"],
        "house": ["909", "707", "606", "minimum", "yellow", "designer"],
        "drum n bass": ["break", "breakbeats", "konkrete", "ninja", "glitch", "static", "jagged", "captain", "head spins"],
        "jungle": ["break", "breakbeats", "konkrete", "ninja", "jagged", "head spins", "funky"],
        "uk garage": ["909", "707", "606", "swing", "bounce", "konkrete", "designer"],
        "trap": ["808", "golden era", "hip-hop", "oracle", "slingshot", "pain killer", "deep space"],
        "hip hop": ["golden era", "hip-hop", "breakbeats", "oracle", "boom", "swing", "otari", "swang", "slingshot"],
        "afrobeats": ["ethno", "wood", "percussion", "yellow", "designer"],
        "amapiano": ["ethno", "wood", "808", "percussion", "designer"],
        "ambient": ["granular", "grain", "pitchy", "shadowed", "melodized", "konkrete", "glitch"],
    }
    prompt_terms = {
        "dark": ["dark", "carbon", "carbonized", "scorched", "burned", "shadowed", "wicked", "metal"],
        "machine": ["909", "808", "606", "707", "techno", "minimum", "carbon"],
        "acoustic": ["drum booth", "session", "room", "wood"],
        "break": ["break", "breakbeats", "konkrete", "ninja", "jagged", "funky"],
        "glitch": ["glitch", "static", "grain", "granular", "konkrete", "pitchy"],
        "lo-fi": ["golden era", "hip-hop", "otari", "swang", "vinyl", "sugar"],
        "minimal": ["minimum", "606", "707", "clean"],
        "heavy": ["metal", "meaty", "largeness", "wicked", "raged", "burned"],
    }
    role_terms = {
        "bd": ["kick", "808", "909", "meaty", "largeness"],
        "snare": ["snare", "rim", "707", "909", "white"],
        "hats": ["hat", "606", "707", "909", "tight"],
        "percussion": ["perc", "ethno", "wood", "collision", "konkrete"],
    }

    for term in style_terms.get(style, []):
        if term in haystack:
            score += 8
    for trigger, terms in prompt_terms.items():
        if trigger in prompt:
            score += sum(10 for term in terms if term in haystack)
    for term in role_terms.get(role, []):
        if term in haystack:
            score += 2
    for token in re.findall(r"[a-z0-9]+", prompt):
        if len(token) > 3 and token in haystack:
            score += 3
    if "mpe " in haystack:
        score -= 3
    if "drum hits" in haystack:
        score -= 20
    return score


def score_drum_kits(text: str, style: str, role: str, limit: int = 12, roots: tuple[Path, ...] | None = None) -> list[str]:
    kits = discover_installed_drum_kits(roots)
    if not kits:
        return []
    seed = stable_seed(f"{style}:{role}:{text}")
    ranked = sorted(
        kits,
        key=lambda kit: (-score_drum_kit(kit, text, style, role), stable_seed(f"{seed}:{kit['name']}")),
    )
    return [kit["name"] for kit in ranked[:limit]]


STYLE_PALETTES: dict[str, dict[str, list[str]]] = {
    "dance and mainstage": {
        "chords": ["Bright Saw Chords", "Wavetable", "Meld", "Analog"],
        "pad": ["Big Pad", "Wavetable", "Meld", "Analog"],
        "riff": ["Acid Riff", "Wavetable", "Drift", "Operator"],
        "hook": ["Mainstage Lead", "Wavetable", "Meld", "Drift"],
        "bass": ["Sub Bass", "Operator", "Wavetable", "Drift"],
        "bd": ["909 Core Kit", "808 Core Kit"],
    },
    "downtempo": {
        "chords": ["Rhodes", "Electric", "Analog", "Wavetable"],
        "pad": ["Warm Pad", "Tension", "Meld", "Wavetable"],
        "riff": ["Pluck Synth", "Tension", "Collision", "Drift"],
        "hook": ["Mellow Lead", "Electric", "Tension", "Wavetable"],
        "bass": ["Deep Sub", "Analog", "Drift", "Operator"],
        "percussion": ["Collision", "909 Core Kit", "808 Core Kit"],
    },
    "drum n bass": {
        "pad": ["Atmospheric Pad", "Wavetable", "Meld", "Tension"],
        "riff": ["Urgent Pluck", "Operator", "Wavetable", "Drift"],
        "hook": ["DnB Lead", "Wavetable", "Meld", "Operator"],
        "bass": ["Reese Bass", "Sub Bass", "Operator", "Wavetable", "Drift"],
        "bd": ["909 Core Kit", "808 Core Kit"],
        "snare": ["909 Core Kit", "808 Core Kit"],
        "hats": ["909 Core Kit", "808 Core Kit"],
    },
    "hip hop": {
        "chords": ["Electric", "Analog", "Drift", "Wavetable"],
        "pad": ["Subtle Pad", "Analog", "Wavetable", "Meld"],
        "riff": ["Short Riff", "Drift", "Electric", "Tension"],
        "hook": ["Simple Hook", "Electric", "Drift", "Wavetable"],
        "bass": ["Sub Bass", "808 Bass", "Operator", "Analog", "Drift"],
        "bd": ["808 Core Kit", "909 Core Kit"],
        "snare": ["808 Core Kit", "909 Core Kit"],
    },
    "house": {
        "chords": ["Electric", "Analog", "Wavetable", "Meld"],
        "pad": ["Warm House Pad", "Analog", "Meld", "Wavetable"],
        "riff": ["Bouncy Riff", "Drift", "Wavetable", "Operator"],
        "hook": ["House Lead", "Wavetable", "Drift", "Electric"],
        "bass": ["Bouncy Bass", "Analog", "Drift", "Operator"],
        "bd": ["808 Core Kit", "909 Core Kit", "707 Core Kit", "606 Core Kit"],
        "snare": ["707 Core Kit", "909 Core Kit", "808 Core Kit", "606 Core Kit"],
        "hats": ["707 Core Kit", "606 Core Kit", "909 Core Kit", "808 Core Kit"],
    },
    "deep_house": {
        "chords": ["Rhodes", "Electric", "Analog", "Meld"],
        "pad": ["Warm House Pad", "Warm Pad", "Meld", "Analog"],
        "riff": ["Soulful Riff", "Electric", "Drift", "Wavetable"],
        "hook": ["House Lead", "Electric", "Drift", "Wavetable"],
        "bass": ["Sub Bass", "Analog", "Drift", "Operator"],
        "bd": ["707 Core Kit", "808 Core Kit", "606 Core Kit", "909 Core Kit"],
        "snare": ["707 Core Kit", "606 Core Kit", "808 Core Kit", "909 Core Kit"],
        "hats": ["606 Core Kit", "707 Core Kit", "808 Core Kit", "909 Core Kit"],
        "percussion": ["Collision", "707 Core Kit", "606 Core Kit", "808 Core Kit", "909 Core Kit"],
    },
    "tech_house": {
        "chords": ["Analog", "Drift", "Wavetable", "Operator"],
        "pad": ["Dark Pad", "Tension", "Meld", "Wavetable"],
        "riff": ["Hypnotic Riff", "Acid Riff", "Drift", "Operator"],
        "hook": ["Minimal Hook", "Operator", "Drift", "Meld"],
        "bass": ["Rolling Bass", "Driving Bass", "Operator", "Drift"],
        "bd": ["909 Core Kit", "606 Core Kit", "707 Core Kit", "808 Core Kit"],
        "snare": ["909 Core Kit", "707 Core Kit", "606 Core Kit", "808 Core Kit"],
        "hats": ["606 Core Kit", "909 Core Kit", "707 Core Kit", "808 Core Kit"],
        "percussion": ["909 Core Kit", "606 Core Kit", "707 Core Kit", "Collision", "808 Core Kit"],
    },
    "jungle": {
        "chords": ["Rave Chords", "Wavetable", "Tension", "Analog"],
        "pad": ["Airy Pad", "Tension", "Wavetable", "Meld"],
        "riff": ["Acid Riff", "Wavetable", "Operator", "Drift"],
        "hook": ["Rave Hook", "Wavetable", "Drift", "Meld"],
        "bass": ["Sub Bass", "Operator", "Analog", "Drift"],
        "bd": ["808 Core Kit", "909 Core Kit"],
        "snare": ["909 Core Kit", "808 Core Kit"],
        "hats": ["909 Core Kit", "808 Core Kit"],
    },
    "modern pop": {
        "chords": ["Clean Piano", "Electric", "Wavetable", "Analog"],
        "pad": ["Soulful Pad", "Meld", "Wavetable", "Analog"],
        "riff": ["Pop Pluck", "Drift", "Wavetable", "Electric"],
        "hook": ["Pop Lead", "Wavetable", "Meld", "Drift"],
        "bass": ["Clean Bass", "Drift", "Analog", "Operator"],
    },
    "reggae": {
        "chords": ["Electric", "Analog", "Wavetable", "Tension"],
        "pad": ["Warm Pad", "Analog", "Tension", "Meld"],
        "riff": ["Short Pluck", "Electric", "Tension", "Drift"],
        "hook": ["Melodic Lead", "Electric", "Wavetable", "Tension"],
        "bass": ["Deep Reggae Bass", "Analog", "Drift", "Operator"],
        "percussion": ["Collision", "909 Core Kit", "808 Core Kit"],
    },
    "reggaeton": {
        "chords": ["Wavetable", "Electric", "Analog", "Meld"],
        "pad": ["Warm Pad", "Meld", "Wavetable", "Analog"],
        "riff": ["Percussive Riff", "Drift", "Wavetable", "Operator"],
        "hook": ["Reggaeton Lead", "Wavetable", "Meld", "Drift"],
        "bass": ["Sub Bass", "Operator", "Drift", "Analog"],
        "bd": ["808 Core Kit", "909 Core Kit"],
        "snare": ["808 Core Kit", "909 Core Kit"],
    },
    "rock and country": {
        "chords": ["Electric Guitar", "Electric", "Tension", "Analog"],
        "pad": ["Warm Pad", "Tension", "Analog", "Meld"],
        "riff": ["Guitar Riff", "Tension", "Electric", "Wavetable"],
        "hook": ["Lead Guitar", "Electric", "Tension", "Wavetable"],
        "bass": ["Electric Bass", "Analog", "Electric", "Drift"],
    },
    "techno": {
        "chords": ["Analog", "Drift", "Wavetable", "Operator"],
        "pad": ["Dark Pad", "Meld", "Wavetable", "Analog"],
        "riff": ["Hypnotic Riff", "Drift", "Operator", "Wavetable"],
        "hook": ["Minimal Hook", "Operator", "Drift", "Meld"],
        "bass": ["Driving Bass", "Operator", "Drift", "Analog"],
        "bd": ["909 Core Kit", "808 Core Kit"],
    },
    "trance": {
        "chords": ["Wavetable", "Meld", "Analog", "Operator"],
        "pad": ["Wide Pad", "Wavetable", "Meld", "Analog"],
        "riff": ["Arp Riff", "Wavetable", "Operator", "Drift"],
        "hook": ["Trance Lead", "Wavetable", "Meld", "Operator"],
        "bass": ["Rolling Bass", "Operator", "Wavetable", "Drift"],
    },
    "trap": {
        "chords": ["Wavetable", "Analog", "Drift", "Operator"],
        "pad": ["Moody Pad", "Meld", "Wavetable", "Analog"],
        "riff": ["Trap Pluck", "Drift", "Wavetable", "Meld"],
        "hook": ["Trap Lead", "Wavetable", "Operator", "Drift"],
        "bass": ["808 Bass", "Sub Bass", "Operator", "Analog", "Drift"],
        "bd": ["808 Core Kit", "909 Core Kit"],
        "snare": ["808 Core Kit", "909 Core Kit"],
    },
    "ambient": {
        "chords": ["Tension", "Meld", "Wavetable", "Electric"],
        "pad": ["Drifting Pad", "Meld", "Tension", "Wavetable"],
        "riff": ["Subtle Riff", "Tension", "Collision", "Wavetable"],
        "hook": ["Ethereal Hook", "Tension", "Meld", "Electric"],
        "bass": ["Deep Sub", "Analog", "Operator", "Drift"],
        "ambience": ["Texture", "Meld", "Tension", "Collision", "Wavetable"],
        "percussion": ["Collision", "909 Core Kit", "808 Core Kit"],
    },
    "hyperpop": {
        "chords": ["Saturated Chords", "Meld", "Wavetable", "Operator"],
        "pad": ["Bright Pad", "Meld", "Wavetable", "Drift"],
        "riff": ["Glitched Riff", "Operator", "Meld", "Wavetable"],
        "hook": ["Hyperpop Lead", "Meld", "Wavetable", "Operator"],
        "bass": ["Distorted Bass", "Operator", "Meld", "Wavetable"],
        "bd": ["Hard Kick", "808 Core Kit", "909 Core Kit"],
    },
    "uk garage": {
        "chords": ["Shuffled Chords", "Electric", "Wavetable", "Drift"],
        "pad": ["Warm Pad", "Wavetable", "Meld", "Analog"],
        "riff": ["Garage Pluck", "Drift", "Wavetable", "Operator"],
        "hook": ["Garage Lead", "Wavetable", "Drift", "Electric"],
        "bass": ["Bouncy Bass", "Operator", "Drift", "Analog"],
        "bd": ["909 Core Kit", "808 Core Kit"],
        "snare": ["909 Core Kit", "808 Core Kit"],
    },
    "afrobeats": {
        "chords": ["Electric Piano", "Rhodes", "Wavetable"],
        "pad": ["Warm Pad", "Meld", "Analog"],
        "riff": ["Pluck Synth", "Mallets", "Tension"],
        "hook": ["Lead Synth", "Pluck", "Wavetable"],
        "bass": ["Sub Bass", "Electric Bass", "Analog"],
        "bd": ["808 Core Kit", "909 Core Kit"],
        "snare": ["808 Core Kit", "909 Core Kit"],
        "percussion": ["Collision", "808 Core Kit", "909 Core Kit"],
    },
    "amapiano": {
        "chords": ["Rhodes", "Electric Piano", "Warm Pad"],
        "pad": ["Deep Pad", "Soulful Pad", "Meld"],
        "riff": ["Percussive Synth", "Pluck Synth", "Drift"],
        "hook": ["Lead Synth", "Square Lead", "Operator"],
        "bass": ["Log Drum", "Sub Bass", "Operator"],
        "bd": ["909 Core Kit", "808 Core Kit"],
        "snare": ["909 Core Kit", "808 Core Kit"],
        "percussion": ["909 Core Kit", "808 Core Kit", "Collision"],
    },
}


def role_palette(text: str, role: str) -> list[str]:
    style = detect_style(text)
    if role in DRUM_ROLES:
        scored_kits = score_drum_kits(text, style, role)
        return unique_candidates(scored_kits + STOCK_PRESET_PALETTES.get(style, {}).get(role, []) + ROLE_PALETTES.get(role, []) + DRUM_KIT_FALLBACKS)

    palette = STYLE_PALETTES.get(style, {})
    preset_palette = STOCK_PRESET_PALETTES.get(style, {})
    candidates = unique_candidates(preset_palette.get(role, []) + palette.get(role, []) + ROLE_PALETTES.get(role, []))
    return candidates


def song_track_palette(text: str) -> dict[str, list[str]]:
    return {
        "Riff": role_palette(text, "riff"),
        "Hook": role_palette(text, "hook"),
        "Chords": role_palette(text, "chords"),
        "Ambience": role_palette(text, "ambience"),
        "Bass": role_palette(text, "bass"),
        "Pad": role_palette(text, "pad"),
        "Snare / Clap": role_palette(text, "snare"),
        "Hh / Sh / Rd": role_palette(text, "hats"),
        "Percussion": role_palette(text, "percussion"),
        "Hh / Sh / Rd +": role_palette(text, "hats"),
        "Bd": role_palette(text, "bd"),
    }


def edm_track_palette(text: str) -> dict[str, list[str]]:
    return {
        "EDM Chords": role_palette(text, "chords"),
        "EDM Bass": role_palette(text, "bass"),
        "EDM Drums": unique_candidates(role_palette(text, "bd") + role_palette(text, "snare") + role_palette(text, "hats")),
        "EDM Lead": role_palette(text, "hook"),
    }


def current_track_palette(text: str) -> dict[str, list[str]]:
    palette = song_track_palette(text)
    palette.update(edm_track_palette(text))
    return palette


def unique_candidates(candidates: list[str]) -> list[str]:
    seen = set()
    result = []
    for candidate in candidates:
        if candidate.lower() in seen:
            continue
        seen.add(candidate.lower())
        result.append(candidate)
    return result


def library_drums(text: str, bars: int, energy: str = "main", keep: set[int] | None = None, genre: str = "") -> list[dict[str, Any]]:
    library_notes = generate_library_drums(text, bars, energy, keep)
    if library_notes:
        return library_notes
    fallback = genre_drums(bars, energy, genre)
    return filter_drums(fallback, keep) if keep else fallback


def library_chords(text: str, bars: int, energy: str = "main", genre: str = "", parallel_motion: bool = False) -> list[dict[str, Any]]:
    library_notes = generate_library_chords(text, bars, energy)
    if library_notes:
        return library_notes
    return genre_chords(text, bars, energy, genre, parallel_motion=parallel_motion)


def library_bassline(text: str, bars: int, energy: str = "main", genre: str = "") -> list[dict[str, Any]]:
    library_notes = generate_library_bass(text, bars, energy)
    if library_notes:
        return library_notes
    return genre_bassline(text, bars, energy, genre)


def library_melody(text: str, bars: int, energy: str = "main", genre: str = "") -> list[dict[str, Any]]:
    library_notes = generate_library_melody(text, bars, energy)
    if library_notes:
        return library_notes
    if genre:
        return genre_lead(text, bars, energy, genre)
    return generate_melody(text, max(1, min(bars, 8)))


def drum_only(text: str, bars: int, energy: str, keep: set[int], genre: str = "") -> list[dict[str, Any]]:
    return filter_drums(library_drums(text, bars, energy, keep, genre=genre), keep)


def pad_notes(text: str, bars: int, energy: str, genre: str = "") -> list[dict[str, Any]]:
    import math
    notes = library_chords(text, bars, energy, genre)
    # We only keep the very first chord (meaning notes at the lowest start time in each bar)
    # to form a beautiful, clean sustained bed rather than a muddy rhythmic overlap.
    by_bar: dict[int, list[dict[str, Any]]] = {}
    for note in notes:
        bar_idx = int(float(note.get("start", 0.0)) // 4.0)
        by_bar.setdefault(bar_idx, []).append(note)
    
    clean_notes = []
    for bar_idx, bar_notes in by_bar.items():
        if not bar_notes:
            continue
        min_start = min(float(n.get("start", 0.0)) for n in bar_notes)
        for n in bar_notes:
            if math.isclose(float(n.get("start", 0.0)), min_start, abs_tol=1e-3):
                copy_note = dict(n)
                copy_note["start"] = float(bar_idx) * 4.0  # Align strictly to bar boundary!
                copy_note["duration"] = 3.9  # Sustained almost full bar
                copy_note["velocity"] = 50 if energy in {"intro", "break"} else 58
                clean_notes.append(copy_note)
    return clean_notes


def hook_notes(text: str, bars: int, energy: str, genre: str = "") -> list[dict[str, Any]]:
    notes = library_melody(text, bars, "break" if energy == "break" else "main", genre)
    return transpose_notes(notes, 0 if energy == "break" else 12)


def riff_notes(text: str, bars: int, energy: str, genre: str = "") -> list[dict[str, Any]]:
    notes = library_melody(text, bars, "build" if energy == "build" else "main", genre)
    shifted = transpose_notes(notes, -12)
    for index, note in enumerate(shifted):
        if index % 3 == 0:
            note["mute"] = True
        note["velocity"] = max(45, int(note.get("velocity", 80)) - 12)
    return shifted


def percussion_notes(bars: int, energy: str, genre: str = "") -> list[dict[str, Any]]:
    import math
    notes: list[dict[str, Any]] = []
    velocity = 54 if energy == "intro" else 70
    genre = genre.strip().lower() if genre else ""

    for bar in range(bars):
        start = bar * 4.0
        
        if genre in {"reggaeton", "afrobeats", "amapiano"}:
            # Syncopated clave-style percussion
            offsets = [0.75, 1.5, 2.75, 3.5] if energy in {"main", "build"} else [0.75, 2.75]
            for offset in offsets:
                pitch = 37 if offset in [0.75, 2.75] else 40
                notes.append({"pitch": pitch, "start": start + offset, "duration": 0.08, "velocity": velocity, "mute": False})

        elif genre in {"drum n bass", "jungle"}:
            # Fast breakbeat ghost snares / rolls
            if energy in {"main", "build"}:
                for offset in [0.75, 1.25, 2.25, 2.75, 3.75]:
                    notes.append({"pitch": 40, "start": start + offset, "duration": 0.05, "velocity": velocity - 15, "mute": False})
            else:
                for offset in [1.5, 3.5]:
                    notes.append({"pitch": 40, "start": start + offset, "duration": 0.08, "velocity": velocity - 10, "mute": False})

        elif genre in {"trap", "hip hop", "hyperpop"}:
            # Skippy rolls and rims
            if energy in {"main", "build"}:
                for offset in [0.25, 0.75, 1.25, 2.25, 2.75, 3.25]:
                    notes.append({"pitch": 37, "start": start + offset, "duration": 0.06, "velocity": velocity - 8, "mute": False})
                if bar % 2 == 1:
                    notes.append({"pitch": 40, "start": start + 3.75, "duration": 0.04, "velocity": velocity, "mute": False})
                    notes.append({"pitch": 40, "start": start + 3.875, "duration": 0.04, "velocity": velocity - 10, "mute": False})
            else:
                for offset in [1.0, 3.0]:
                    notes.append({"pitch": 37, "start": start + offset, "duration": 0.08, "velocity": velocity - 5, "mute": False})

        elif genre == "uk garage":
            # Swung garage rimshots/clicks
            for offset in [0.5, 1.25, 2.0, 2.75, 3.5]:
                swung = offset
                if math.isclose(offset, 1.25) or math.isclose(offset, 2.75):
                    swung += 0.04
                notes.append({"pitch": 40, "start": start + swung, "duration": 0.06, "velocity": velocity - 5, "mute": False})

        elif genre in {"ambient", "downtempo"}:
            # Sparse texture bells / hand percussion
            if bar % 2 == 0:
                notes.append({"pitch": 40, "start": start + 2.5, "duration": 0.15, "velocity": velocity - 15, "mute": False})
            if energy in {"main", "build"} and bar % 2 == 1:
                notes.append({"pitch": 37, "start": start + 1.0, "duration": 0.12, "velocity": velocity - 12, "mute": False})

        else:
            # House, Techno, Trance, Pop, and defaults
            for offset in [0.75, 1.25, 2.75, 3.25]:
                notes.append({"pitch": 40, "start": start + offset, "duration": 0.08, "velocity": velocity, "mute": False})
            if energy in {"build", "main"}:
                for offset in [0.5, 1.75, 2.5, 3.75]:
                    notes.append({"pitch": 37, "start": start + offset, "duration": 0.08, "velocity": velocity - 10, "mute": False})

    return notes


def ambience_notes(text: str, bars: int, energy: str, genre: str = "") -> list[dict[str, Any]]:
    notes = transpose_notes(library_melody(text, max(1, min(bars, 8)), energy, genre), 24)
    result = []
    for index, note in enumerate(notes):
        if index % 6 == 0:
            copy = dict(note)
            copy["start"] = min(float(copy.get("start", 0.0)) * 2, bars * 4 - 0.5)
            copy["duration"] = 1.75 if energy in {"intro", "break"} else 0.75
            copy["velocity"] = 38 if energy in {"intro", "break"} else 48
            result.append(copy)
    return result


def section_energy(section: str) -> str:
    lowered = section.lower()
    if "intro" in lowered or "outro" in lowered:
        return "intro"
    if "build" in lowered:
        return "build"
    if "break" in lowered:
        return "break"
    return "main"


def scene_clip(
    track_name: str,
    section: str,
    part: str,
    scene_index: int,
    notes: list[dict[str, Any]],
    bars: int,
) -> dict[str, Any]:
    action = clip_action(track_name, f"{section} - {part}", notes, bars)
    action["scene_index"] = scene_index
    return action


def arrangement_sections(sections: list[tuple[str, int, dict[str, Any]]]) -> list[dict[str, Any]]:
    start = 0
    result = []
    for scene_index, (name, bars, _parts) in enumerate(sections):
        length_beats = bars * 4
        result.append(
            {
                "scene_index": scene_index,
                "name": name,
                "start_beat": start,
                "length_beats": length_beats,
            }
        )
        start += length_beats
    return result


def default_edm_sections() -> list[tuple[str, int, dict[str, Any]]]:
    return [
        ("Intro", 8, {"chords": True, "bass": False, "drums": "hats", "lead": False}),
        ("Build", 8, {"chords": True, "bass": True, "drums": "light", "lead": True}),
        ("Drop", 16, {"chords": True, "bass": True, "drums": "full", "lead": True}),
        ("Break", 8, {"chords": True, "bass": False, "drums": "none", "lead": True}),
        ("Drop 2", 16, {"chords": True, "bass": True, "drums": "full", "lead": True, "lift": True}),
        ("Outro", 8, {"chords": True, "bass": False, "drums": "hats", "lead": False}),
    ]


def consolidate_drums_in_actions(actions: list[dict[str, Any]], message: str, vst_map: dict[str, str] | None = None) -> list[dict[str, Any]]:
    # Find all created midi tracks
    created = []
    for action in actions:
        if action.get("type") == "create_midi_track":
            name = action.get("name")
            if name:
                created.append(name)
                
    drum_sequencers = {"Bd", "Snare / Clap", "Hh / Sh / Rd", "Percussion", "Hh / Sh / Rd +"}
    # Check if we have multiple drum tracks created but NO Drum Instrument track
    has_multiple_drums = len([t for t in created if t in drum_sequencers]) >= 3
    has_drum_instrument = "Drum Instrument" in created
    
    if has_multiple_drums and not has_drum_instrument:
        new_actions = []
        drum_track_inserted = False
        
        # 1. Insert "Drum Instrument" track creation before the first drum track creation
        for action in actions:
            if action.get("type") == "create_midi_track" and action.get("name") in drum_sequencers:
                if not drum_track_inserted:
                    new_actions.append({"type": "create_midi_track", "name": "Drum Instrument"})
                    drum_track_inserted = True
            new_actions.append(action)
            
        if not drum_track_inserted:
            new_actions.append({"type": "create_midi_track", "name": "Drum Instrument"})
            
        # 2. Append route_midi actions at the end of the action plan so that VSTs/instruments are loaded first
        final_actions = list(new_actions)
        for seq in drum_sequencers:
            final_actions.append({
                "type": "route_midi",
                "source_track": seq,
                "target_track": "Drum Instrument"
            })
                
        # 3. Clean up existing instrument loading actions on drum sequencers
        for action in final_actions:
            act_type = action.get("type")
            if act_type in ("load_stock_instruments", "load_user_vst_instruments"):
                tracks = action.get("tracks") or {}
                for seq in list(tracks.keys()):
                    if seq in drum_sequencers:
                        del tracks[seq]
                        
        # 4. Clean up any empty instrument loading actions
        cleaned_actions = []
        for action in final_actions:
            act_type = action.get("type")
            if act_type in ("load_stock_instruments", "load_user_vst_instruments"):
                tracks = action.get("tracks") or {}
                if not tracks:
                    continue
            cleaned_actions.append(action)
        return cleaned_actions
        
    return actions


def enrich_actions(message: str, actions: list[dict[str, Any]], vst_map: dict[str, str] | None = None) -> list[dict[str, Any]]:
    actions = consolidate_drums_in_actions(actions, message, vst_map)
    bars = extract_bars(message.lower())
    enriched: list[dict[str, Any]] = []
    
    # Identify which tracks are being routed to another track
    routed_sources = set()
    for action in actions:
        if action.get("type") == "route_midi":
            src = action.get("source_track")
            if src:
                routed_sources.add(src)

    # 1. Identify track names already targeted by loading actions
    existing_instrument_tracks = set()
    for action in actions:
        if action.get("type") in ("load_stock_instruments", "load_user_vst_instruments"):
            tracks = action.get("tracks") or {}
            existing_instrument_tracks.update(tracks.keys())

    # 2. Collect newly created MIDI tracks lacking an instrument
    created_midi_tracks = []
    for action in actions:
        if action.get("type") == "create_midi_track":
            track_name = action.get("name")
            if track_name and track_name not in existing_instrument_tracks and track_name not in routed_sources:
                created_midi_tracks.append(track_name)

    # 3. Classify and route to custom VST or genre-aware Stock fallback
    new_vst_tracks = {}
    new_stock_tracks = {}
    _vst_map = {k.lower(): v for k, v in (vst_map or {}).items()}

    for track_name in created_midi_tracks:
        role = classify_track_role(track_name).lower()
        plugin_name = _vst_map.get(role) or _vst_map.get("all")
        if plugin_name:
            new_vst_tracks[track_name] = [plugin_name]
        else:
            # Fallback to Stock Ableton instruments
            if role == "drums":
                new_stock_tracks[track_name] = unique_candidates(
                    role_palette(message, "bd") + role_palette(message, "snare") + role_palette(message, "hats")
                )
            elif role == "lead":
                new_stock_tracks[track_name] = role_palette(message, "hook")
            elif role == "chords":
                new_stock_tracks[track_name] = role_palette(message, "chords")
            elif role == "bass":
                new_stock_tracks[track_name] = role_palette(message, "bass")
            elif role == "pad":
                new_stock_tracks[track_name] = role_palette(message, "pad")
            elif role == "fx":
                new_stock_tracks[track_name] = role_palette(message, "ambience")
            else:
                new_stock_tracks[track_name] = role_palette(message, "chords")

    # 4. Insert loading actions right after the last track creation action
    last_track_idx = -1
    for i, action in enumerate(actions):
        if action.get("type") in ("create_midi_track", "create_audio_track"):
            last_track_idx = i

    for idx, action in enumerate(actions):
        # Inject midi clip notes if missing
        if action.get("type") == "create_midi_clip" and not action.get("notes"):
            name = f"{action.get('track_name', '')} {action.get('clip_name', '')}".lower()
            style = detect_style(message)
            if "bass" in name:
                action["notes"] = library_bassline(message, bars, genre=style)
            elif "drum" in name:
                action["notes"] = library_drums(message, bars, genre=style)
            elif "melody" in name or "lead" in name:
                action["notes"] = library_melody(message, bars, genre=style)
            else:
                action["notes"] = library_chords(message, bars, genre=style)
            action.setdefault("length_beats", bars * 4)
            action.setdefault("scene_index", 0)

        enriched.append(action)

        if idx == last_track_idx:
            if new_stock_tracks:
                enriched.append({
                    "type": "load_stock_instruments",
                    "tracks": new_stock_tracks
                })
            if new_vst_tracks:
                enriched.append({
                    "type": "load_user_vst_instruments",
                    "tracks": new_vst_tracks
                })

    if last_track_idx == -1:
        if new_stock_tracks:
            enriched.append({
                "type": "load_stock_instruments",
                "tracks": new_stock_tracks
            })
        if new_vst_tracks:
            enriched.append({
                "type": "load_user_vst_instruments",
                "tracks": new_vst_tracks
            })

    return enriched


def extract_bpm(text: str) -> int | None:
    match = re.search(r"\b(\d{2,3})\s*(?:bpm|tempo)\b|\btempo\s*(?:to|at)?\s*(\d{2,3})", text)
    if not match:
        return None
    value = int(next(group for group in match.groups() if group))
    return max(20, min(999, value))


def extract_bars(text: str) -> int:
    match = re.search(r"\b(\d{1,2})\s*bar", text)
    if not match:
        return 4
    return max(1, min(32, int(match.group(1))))


def extract_db(text: str) -> float | None:
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*db", text)
    return float(match.group(1)) if match else None


def extract_pan(text: str) -> float | None:
    if "pan" not in text and "left" not in text and "right" not in text:
        return None
    match = re.search(r"(left|right)\s*(\d{1,3})?", text)
    if match:
        value = int(match.group(2) or 25) / 100
        return -value if match.group(1) == "left" else value
    match = re.search(r"pan\s*(-?\d+(?:\.\d+)?)", text)
    if match:
        value = float(match.group(1))
        return max(-1, min(1, value / 100 if abs(value) > 1 else value))
    return None


def extract_named_track(message: str, fallback: str) -> str:
    match = re.search(
        r"(?:called|named)\s+([A-Za-z0-9 _-]{2,32}?)(?=\s+(?:and|with|that|to|for|then)\b|[.!?,]|$)",
        message,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return fallback


def extract_track_reference(message: str) -> str:
    match = re.search(r"(?:track|channel)\s+(?:called|named)?\s*([A-Za-z0-9 _-]{2,32})", message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "AI Chords"
