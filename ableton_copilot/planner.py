from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
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
from .genre_dna import detect_style_from_text as detect_style
from .midi_library import generate_library_drums, mutate_clones, humanize_groove, add_ghost_notes
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
Return only JSON matching the schema.
Use these action types:
- set_tempo {bpm}
- start_playback {}
- stop_playback {}
- create_midi_track {name}
- create_audio_track {name}
- create_scene {name}
- create_midi_clip {track_name, clip_name, scene_index, length_beats, notes}
- set_track_volume {track_name, db}
- set_track_pan {track_name, pan}
- set_send {track_name, send_index, value}
- add_device {track_name, device_name}

Notes are objects: {pitch, start, duration, velocity, mute}. MIDI pitch is 0-127. Beat positions use Ableton beats.
If a request asks for chords, bass, melody, or drums, include concrete MIDI notes.
If a request asks for unsupported device/effect details, include add_device anyway and mention it may require a later bridge upgrade in reply.
Do not claim the DAW action succeeded; the Ableton bridge reports execution separately."""


def plan(message: str) -> dict[str, Any]:
    if os.environ.get("OPENAI_API_KEY"):
        try:
            return openai_plan(message)
        except Exception as exc:
            fallback = local_plan(message)
            fallback["reply"] = f"OpenAI planning failed locally: {exc}. I queued a local interpretation instead."
            return fallback
    return local_plan(message)


def openai_plan(message: str) -> dict[str, Any]:
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-5.2"),
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "ableton_action_plan",
                "strict": True,
                "schema": ACTION_SCHEMA,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
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
    parsed = json.loads(text)
    parsed["actions"] = enrich_actions(message, parsed.get("actions", []))
    return parsed


def extract_response_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                    return content["text"]
    raise RuntimeError("No text output found in OpenAI response")


def local_plan(message: str) -> dict[str, Any]:
    lowered = message.lower()
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
    ) or any(word in lowered for word in genre_words()):
        return expanded_song_sketch_plan(message)
    if any(word in lowered for word in ["better", "complicated", "complex", "interesting", "richer", "enhance"]):
        return edm_enhancement_plan(message)
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
    if any(word in lowered for word in ["arrangement", "song", "edm", "track"]):
        return edm_arrangement_plan(message)

    bars = extract_bars(lowered)
    actions: list[dict[str, Any]] = []

    bpm = extract_bpm(lowered)
    if bpm:
        actions.append({"type": "set_tempo", "bpm": bpm})

    if "audio track" in lowered:
        actions.append({"type": "create_audio_track", "name": extract_named_track(message, "Audio")})

    if any(word in lowered for word in ["chord", "progression", "keys", "piano"]):
        track = "AI Chords"
        actions.append({"type": "create_midi_track", "name": track})
        actions.append(clip_action(track, "Generated Chords", generate_chords(message, bars), bars))

    if "bass" in lowered:
        track = "AI Bass"
        actions.append({"type": "create_midi_track", "name": track})
        actions.append(clip_action(track, "Generated Bassline", generate_bassline(message, bars), bars))

    if any(word in lowered for word in ["melody", "counter-melody", "counter melody", "lead"]):
        track = "AI Melody"
        actions.append({"type": "create_midi_track", "name": track})
        actions.append(clip_action(track, "Generated Melody", generate_melody(message, bars), bars))

    if any(word in lowered for word in ["drum", "beat", "groove"]):
        track = "AI Drums"
        actions.append({"type": "create_midi_track", "name": track})
        actions.append(clip_action(track, "Generated Drum Pattern", library_drums(message, bars, genre=detect_style(message)), bars))

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


def finisher_plan(message: str, mutation_type: str) -> dict[str, Any]:
    track_name = extract_track_reference(message)
    bars = extract_bars(message.lower())
    style = detect_style(message)
    
    # Generate some base notes since we can't read from Ableton yet
    if "drum" in message.lower() or "ghost notes" in mutation_type:
        base_notes = library_drums(message, bars, genre=style)
        track_name = "AI Drums" if track_name == "AI Chords" else track_name
    elif "bass" in message.lower():
        base_notes = genre_bassline(message, bars, genre=style)
    else:
        base_notes = genre_chords(message, bars, genre=style)

    if mutation_type == "mutate_clones":
        notes = mutate_clones(base_notes, 1)
        reply = "Queued a sibling variation (Mutation of Clones)."
    elif mutation_type == "humanize":
        notes = humanize_groove(base_notes)
        reply = "Queued a humanized variation with randomized timing and velocity."
    elif mutation_type == "ghost_notes":
        notes = add_ghost_notes(base_notes)
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
        # Keep only pads/chords
        actions.extend(finisher_mutation("AI Drums", "Carved Intro", [], 8))
        actions.extend(finisher_mutation("AI Bass", "Carved Intro", [], 8))
        actions.extend(finisher_mutation("AI Melody", "Carved Intro", [], 8))
        reply = "Queued a subtractive arrangement: carved out an Intro by removing drums, bass, and lead."
    elif "breakdown" in message.lower():
        # Keep pads, remove high energy drums/bass
        actions.extend(finisher_mutation("AI Drums", "Carved Breakdown", [], 8))
        reply = "Queued a subtractive arrangement: carved a breakdown by muting high-energy drums."
    else:
        actions.extend(finisher_mutation("AI Drums", "Carved Section", [], 8))
        reply = "Queued a generic subtractive arrangement."

    return {
        "reply": reply,
        "actions": actions,
    }


def edm_arrangement_plan(message: str) -> dict[str, Any]:
    actions: list[dict[str, Any]] = [{"type": "set_tempo", "bpm": extract_bpm(message.lower()) or 126}]
    tracks = ["EDM Chords", "EDM Bass", "EDM Drums", "EDM Lead"]
    for track in tracks:
        actions.append({"type": "create_midi_track", "name": track})

    sections = default_edm_sections()

    for scene_index, (section, bars, parts) in enumerate(sections):
        actions.append({"type": "set_scene_name", "scene_index": scene_index, "name": section})
        style = detect_style(message)
        if parts.get("chords"):
            energy = section_energy(section)
            notes = genre_chords(message, bars, energy, style)
            actions.append(scene_clip("EDM Chords", section, "Chords - voiced stabs", scene_index, notes, bars))
        if parts.get("bass"):
            energy = "build" if section == "Build" else "main"
            notes = genre_bassline(message, bars, energy, style)
            if parts.get("lift"):
                notes = transpose_notes(notes, 12)
            actions.append(scene_clip("EDM Bass", section, "Bass - octave groove", scene_index, notes, bars))
        if parts.get("lead"):
            energy = section_energy(section)
            notes = genre_lead(message, bars, energy, style)
            if parts.get("lift"):
                notes = transpose_notes(notes, 12)
            actions.append(scene_clip("EDM Lead", section, "Lead - hook phrase", scene_index, notes, bars))

        drum_mode = parts.get("drums")
        if drum_mode and drum_mode != "none":
            energy = "hats" if drum_mode == "hats" else ("build" if drum_mode == "light" else "main")
            drums = library_drums(message, bars, energy, genre=style)
            if drum_mode == "hats":
                drums = filter_drums(drums, {42})
            actions.append(scene_clip("EDM Drums", section, "Drums - hats fills claps", scene_index, drums, bars))

    actions.append({"type": "copy_session_to_arrangement", "sections": arrangement_sections(sections)})
    actions.append({"type": "start_playback"})
    return {
        "reply": "Queued a basic EDM song arrangement: intro, build, drop, break, second drop, and outro.",
        "actions": actions,
    }


def edm_enhancement_plan(message: str) -> dict[str, Any]:
    sections = default_edm_sections()
    actions: list[dict[str, Any]] = [
        {
            "type": "load_stock_instruments",
            "tracks": {
                **edm_track_palette(message),
            },
        }
    ]

    for scene_index, (section, bars, parts) in enumerate(sections):
        actions.append({"type": "set_scene_name", "scene_index": scene_index, "name": section})
        energy = section_energy(section)
        style = detect_style(message)
        if parts.get("chords"):
            actions.append(
                scene_clip("EDM Chords", section, "Chords - voiced stabs", scene_index, genre_chords(message, bars, energy, style), bars)
            )
        if parts.get("bass"):
            bass = genre_bassline(message, bars, "build" if section == "Build" else "main", style)
            if parts.get("lift"):
                bass = transpose_notes(bass, 12)
            actions.append(scene_clip("EDM Bass", section, "Bass - octave groove", scene_index, bass, bars))
        if parts.get("lead"):
            lead = genre_lead(message, bars, energy, style)
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
            {"type": "start_playback"},
        ]
    )
    return {
        "reply": "Queued a richer EDM rewrite with stronger labels, denser drums, voiced chords, active bass, hook lead, instruments, and arrangement copy.",
        "actions": actions,
    }


def quick_default_idea_plan(message: str) -> dict[str, Any]:
    return expanded_song_sketch_plan(message)


def expanded_song_sketch_plan(message: str) -> dict[str, Any]:
    lowered = message.lower()
    bpm = extract_bpm(lowered) or default_bpm_for_style(lowered)
    sections = expanded_sections(lowered)
    track_names = [
        "Chords",
        "Hh / Sh / Rd",
        "Pad",
        "Riff",
        "Hook",
        "Percussion",
        "Snare / Clap",
        "Ambience",
        "Hh / Sh / Rd +",
        "Bd",
        "Bass",
    ]
    actions: list[dict[str, Any]] = [{"type": "set_tempo", "bpm": bpm}]
    for track in track_names:
        actions.append({"type": "create_midi_track", "name": track})

    actions.append(
        {
            "type": "load_stock_instruments",
            "tracks": {
                **song_track_palette(message),
            },
        }
    )

    for scene_index, (section, bars, energy) in enumerate(sections):
        actions.append({"type": "set_scene_name", "scene_index": scene_index, "name": section})
        style = detect_style(message)
        actions.append(scene_clip("Chords", section, "progression", scene_index, genre_chords(message, bars, energy, style), bars))
        actions.append(scene_clip("Pad", section, "wide pad", scene_index, pad_notes(message, bars, energy, style), bars))
        if energy != "intro":
            actions.append(scene_clip("Bass", section, "bassline", scene_index, genre_bassline(message, bars, "build" if energy == "build" else "main", style), bars))
        if energy in {"build", "main"}:
            actions.append(scene_clip("Riff", section, "riff", scene_index, riff_notes(message, bars, energy, style), bars))
        if energy in {"main", "break"}:
            actions.append(scene_clip("Hook", section, "hook", scene_index, hook_notes(message, bars, energy, style), bars))
        actions.append(scene_clip("Hh / Sh / Rd", section, "hat groove", scene_index, drum_only(message, bars, energy, {42, 46, 49}, style), bars))
        if energy in {"build", "main"}:
            actions.append(scene_clip("Hh / Sh / Rd +", section, "top lift", scene_index, drum_only(message, bars, "build", {42, 46, 49}, style), bars))
        if energy != "break":
            actions.append(scene_clip("Bd", section, "kick", scene_index, drum_only(message, bars, energy, {36}, style), bars))
            actions.append(scene_clip("Snare / Clap", section, "backbeat", scene_index, drum_only(message, bars, energy, {38, 39}, style), bars))
            actions.append(scene_clip("Percussion", section, "perc", scene_index, percussion_notes(bars, energy), bars))
        actions.append(scene_clip("Ambience", section, "texture", scene_index, ambience_notes(message, bars, energy), bars))

    actions.extend(
        [
            {"type": "set_track_volume", "track_name": "Chords", "db": -11},
            {"type": "set_track_volume", "track_name": "Pad", "db": -14},
            {"type": "set_track_volume", "track_name": "Riff", "db": -12},
            {"type": "set_track_volume", "track_name": "Hook", "db": -10},
            {"type": "set_track_volume", "track_name": "Bass", "db": -7},
            {"type": "set_track_volume", "track_name": "Bd", "db": -6},
            {"type": "set_track_volume", "track_name": "Snare / Clap", "db": -9},
            {"type": "set_track_volume", "track_name": "Hh / Sh / Rd", "db": -13},
            {"type": "set_track_volume", "track_name": "Hh / Sh / Rd +", "db": -15},
            {"type": "set_track_volume", "track_name": "Percussion", "db": -14},
            {"type": "set_track_volume", "track_name": "Ambience", "db": -18},
            {"type": "copy_session_to_arrangement", "sections": arrangement_sections([(name, bars, {}) for name, bars, _energy in sections])},
            {"type": "start_playback"},
        ]
    )
    return {
        "reply": "Queued an expanded song sketch with dedicated musical parts, genre-aware Ableton instrument candidates, arrangement copy, and playback.",
        "actions": actions,
    }


def default_bpm_for_style(text: str) -> int:
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


def expanded_sections(text: str) -> list[tuple[str, int, str]]:
    if any(word in text for word in ["ambient", "cinematic"]):
        return [("Texture", 8, "intro"), ("Pulse", 8, "build"), ("Theme", 16, "main"), ("Drift", 8, "break"), ("Bloom", 16, "main")]
    if any(word in text for word in ["pop", "rock and country"]):
        return [("Intro", 4, "intro"), ("Verse", 8, "build"), ("Pre", 4, "build"), ("Chorus", 8, "main"), ("Verse 2", 8, "build"), ("Final Chorus", 8, "main"), ("Outro", 4, "intro")]
    if any(word in text for word in ["hip-hop", "hip hop", "trap", "lo-fi", "lofi"]):
        return [("Intro", 4, "intro"), ("Verse", 16, "main"), ("Hook", 8, "main"), ("Verse 2", 16, "build"), ("Final Hook", 8, "main"), ("Outro", 4, "intro")]
    return [("Intro", 8, "intro"), ("Groove", 8, "build"), ("Hook", 16, "main"), ("Break", 8, "break"), ("Final Hook", 16, "main"), ("Outro", 8, "intro")]


def genre_words() -> list[str]:
    return [
        "dance and mainstage",
        "downtempo",
        "drum n bass",
        "dnb",
        "hip hop",
        "hip-hop",
        "house",
        "90s jungle",
        "jungle",
        "modern pop",
        "reggae",
        "dance hall",
        "dancehall",
        "reggaeton",
        "rock and country",
        "techno",
        "trance",
        "trap",
        "hyperpop",
        "uk garage",
    ]


ROLE_PALETTES: dict[str, list[str]] = {
    "chords": ["Electric Piano", "Bright Piano", "Warm Pad", "Saw Chords", "Electric", "Analog", "Wavetable", "Meld"],
    "pad": ["Warm Pad", "Deep Pad", "Atmospheric Pad", "Meld", "Wavetable", "Analog", "Tension"],
    "riff": ["Pluck Synth", "Acid Riff", "Short Lead", "Drift", "Wavetable", "Operator", "Meld"],
    "hook": ["Bright Lead", "Square Lead", "Saw Lead", "Wavetable", "Meld", "Drift", "Operator"],
    "bass": ["Basic Sub", "Acid Bass", "Sub Bass", "Electric Bass", "Operator", "Drift", "Analog", "Wavetable"],
    "ambience": ["Texture", "Vinyl Crackle", "Rain", "Meld", "Wavetable", "Tension", "Collision"],
    "bd": ["909 Core Kit", "808 Core Kit", "Kick Kit", "Drum Rack"],
    "snare": ["909 Core Kit", "808 Core Kit", "Clap Kit", "Snare Kit", "Drum Rack"],
    "hats": ["909 Core Kit", "808 Core Kit", "Hihat Kit", "Drum Rack"],
    "percussion": ["Percussion Kit", "Conga Kit", "Collision", "Drum Rack"],
}


STYLE_PALETTES: dict[str, dict[str, list[str]]] = {
    "dance and mainstage": {
        "chords": ["Bright Saw Chords", "Wavetable", "Meld", "Analog"],
        "pad": ["Big Pad", "Wavetable", "Meld", "Analog"],
        "riff": ["Acid Riff", "Wavetable", "Drift", "Operator"],
        "hook": ["Mainstage Lead", "Wavetable", "Meld", "Drift"],
        "bass": ["Sub Bass", "Operator", "Wavetable", "Drift"],
        "bd": ["909 Core Kit", "Kick Kit", "Drum Rack"],
    },
    "downtempo": {
        "chords": ["Rhodes", "Electric", "Analog", "Wavetable"],
        "pad": ["Warm Pad", "Tension", "Meld", "Wavetable"],
        "riff": ["Pluck Synth", "Tension", "Collision", "Drift"],
        "hook": ["Mellow Lead", "Electric", "Tension", "Wavetable"],
        "bass": ["Deep Sub", "Analog", "Drift", "Operator"],
        "percussion": ["Organic Percussion", "Collision", "Drum Rack"],
    },
    "drum n bass": {
        "pad": ["Atmospheric Pad", "Wavetable", "Meld", "Tension"],
        "riff": ["Urgent Pluck", "Operator", "Wavetable", "Drift"],
        "hook": ["DnB Lead", "Wavetable", "Meld", "Operator"],
        "bass": ["Reese Bass", "Sub Bass", "Operator", "Wavetable", "Drift"],
        "bd": ["DnB Kick", "909 Core Kit", "Drum Rack"],
        "snare": ["DnB Snare", "909 Core Kit", "Drum Rack"],
        "hats": ["Fast Hats", "Drum Rack", "909 Core Kit"],
    },
    "hip hop": {
        "chords": ["Dusty Rhodes", "Electric", "Analog", "Drift"],
        "pad": ["Subtle Pad", "Analog", "Wavetable", "Meld"],
        "riff": ["Short Riff", "Drift", "Electric", "Tension"],
        "hook": ["Simple Hook", "Electric", "Drift", "Wavetable"],
        "bass": ["Sub Bass", "808 Bass", "Operator", "Analog", "Drift"],
        "bd": ["808 Core Kit", "Hip Hop Kit", "Drum Rack"],
        "snare": ["808 Core Kit", "Snare Kit", "Drum Rack"],
    },
    "house": {
        "chords": ["House Stabs", "Electric", "Analog", "Wavetable"],
        "pad": ["Warm House Pad", "Analog", "Meld", "Wavetable"],
        "riff": ["Bouncy Riff", "Drift", "Wavetable", "Operator"],
        "hook": ["House Lead", "Wavetable", "Drift", "Electric"],
        "bass": ["Bouncy Bass", "Analog", "Drift", "Operator"],
        "bd": ["909 Core Kit", "House Kit", "Drum Rack"],
        "hats": ["909 Core Kit", "Open Hat Kit", "Drum Rack"],
    },
    "jungle": {
        "chords": ["Rave Chords", "Wavetable", "Tension", "Analog"],
        "pad": ["Airy Pad", "Tension", "Wavetable", "Meld"],
        "riff": ["Acid Riff", "Wavetable", "Operator", "Drift"],
        "hook": ["Rave Hook", "Wavetable", "Drift", "Meld"],
        "bass": ["Sub Bass", "Operator", "Analog", "Drift"],
        "bd": ["Jungle Kick", "Drum Rack", "808 Core Kit"],
        "snare": ["Jungle Snare", "Drum Rack", "909 Core Kit"],
        "hats": ["Breakbeat Hats", "Drum Rack", "Drum Rack"],
    },
    "modern pop": {
        "chords": ["Clean Piano", "Electric", "Wavetable", "Analog"],
        "pad": ["Soulful Pad", "Meld", "Wavetable", "Analog"],
        "riff": ["Pop Pluck", "Drift", "Wavetable", "Electric"],
        "hook": ["Pop Lead", "Wavetable", "Meld", "Drift"],
        "bass": ["Clean Bass", "Drift", "Analog", "Operator"],
    },
    "reggae": {
        "chords": ["Reggae Skank", "Electric", "Analog", "Wavetable"],
        "pad": ["Warm Pad", "Analog", "Tension", "Meld"],
        "riff": ["Short Pluck", "Electric", "Tension", "Drift"],
        "hook": ["Melodic Lead", "Electric", "Wavetable", "Tension"],
        "bass": ["Deep Reggae Bass", "Analog", "Drift", "Operator"],
        "percussion": ["Hand Drums", "Collision", "Drum Rack"],
    },
    "reggaeton": {
        "chords": ["Rhythmic Chords", "Wavetable", "Electric", "Analog"],
        "pad": ["Warm Pad", "Meld", "Wavetable", "Analog"],
        "riff": ["Percussive Riff", "Drift", "Wavetable", "Operator"],
        "hook": ["Reggaeton Lead", "Wavetable", "Meld", "Drift"],
        "bass": ["Sub Bass", "Operator", "Drift", "Analog"],
        "bd": ["808 Core Kit", "Reggaeton Kit", "Drum Rack"],
        "snare": ["Reggaeton Snare", "808 Core Kit", "Drum Rack"],
    },
    "rock and country": {
        "chords": ["Electric Guitar", "Electric", "Tension", "Analog"],
        "pad": ["Warm Pad", "Tension", "Analog", "Meld"],
        "riff": ["Guitar Riff", "Tension", "Electric", "Wavetable"],
        "hook": ["Lead Guitar", "Electric", "Tension", "Wavetable"],
        "bass": ["Electric Bass", "Analog", "Electric", "Drift"],
    },
    "techno": {
        "chords": ["Hypnotic Chords", "Analog", "Drift", "Wavetable"],
        "pad": ["Dark Pad", "Meld", "Wavetable", "Analog"],
        "riff": ["Hypnotic Riff", "Drift", "Operator", "Wavetable"],
        "hook": ["Minimal Hook", "Operator", "Drift", "Meld"],
        "bass": ["Driving Bass", "Operator", "Drift", "Analog"],
        "bd": ["909 Core Kit", "Techno Kick", "Drum Rack"],
    },
    "trance": {
        "chords": ["Uplifting Chords", "Wavetable", "Meld", "Analog"],
        "pad": ["Wide Pad", "Wavetable", "Meld", "Analog"],
        "riff": ["Arp Riff", "Wavetable", "Operator", "Drift"],
        "hook": ["Trance Lead", "Wavetable", "Meld", "Operator"],
        "bass": ["Rolling Bass", "Operator", "Wavetable", "Drift"],
    },
    "trap": {
        "chords": ["Dark Chords", "Wavetable", "Analog", "Drift"],
        "pad": ["Moody Pad", "Meld", "Wavetable", "Analog"],
        "riff": ["Trap Pluck", "Drift", "Wavetable", "Meld"],
        "hook": ["Trap Lead", "Wavetable", "Operator", "Drift"],
        "bass": ["808 Bass", "Sub Bass", "Operator", "Analog", "Drift"],
        "bd": ["808 Core Kit", "Trap Kick", "Drum Rack"],
        "snare": ["808 Core Kit", "Trap Snare", "Drum Rack"],
    },
    "ambient": {
        "chords": ["Hazy Chords", "Tension", "Meld", "Wavetable"],
        "pad": ["Drifting Pad", "Meld", "Tension", "Wavetable"],
        "riff": ["Subtle Riff", "Tension", "Collision", "Wavetable"],
        "hook": ["Ethereal Hook", "Tension", "Meld", "Electric"],
        "bass": ["Deep Sub", "Analog", "Operator", "Drift"],
        "ambience": ["Texture", "Meld", "Tension", "Collision", "Wavetable"],
        "percussion": ["Soft Percussion", "Collision", "Drum Rack"],
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
        "bd": ["909 Core Kit", "808 Core Kit", "Drum Rack"],
        "snare": ["909 Core Kit", "Drum Rack"],
    },
    "afrobeats": {
        "chords": ["Electric Piano", "Rhodes", "Wavetable"],
        "pad": ["Warm Pad", "Meld", "Analog"],
        "riff": ["Pluck Synth", "Mallets", "Tension"],
        "hook": ["Lead Synth", "Pluck", "Wavetable"],
        "bass": ["Sub Bass", "Electric Bass", "Analog"],
        "bd": ["808 Core Kit", "909 Core Kit"],
        "snare": ["Clap Kit", "808 Core Kit"],
        "percussion": ["Afro Percussion", "Conga Kit", "Collision"],
    },
    "amapiano": {
        "chords": ["Rhodes", "Electric Piano", "Warm Pad"],
        "pad": ["Deep Pad", "Soulful Pad", "Meld"],
        "riff": ["Percussive Synth", "Pluck Synth", "Drift"],
        "hook": ["Lead Synth", "Square Lead", "Operator"],
        "bass": ["Log Drum", "Sub Bass", "Operator"],
        "bd": ["909 Core Kit", "House Kit"],
        "snare": ["Snare Kit", "909 Core Kit"],
        "percussion": ["Shaker Kit", "Organic Percussion"],
    },
}


# Removed local detect_style, now imported from genre_dna as detect_style


def role_palette(text: str, role: str) -> list[str]:
    style = detect_style(text)
    palette = STYLE_PALETTES.get(style, {})
    return unique_candidates(palette.get(role, []) + ROLE_PALETTES.get(role, []))


def song_track_palette(text: str) -> dict[str, list[str]]:
    return {
        "Chords": role_palette(text, "chords"),
        "Hh / Sh / Rd": role_palette(text, "hats"),
        "Pad": role_palette(text, "pad"),
        "Riff": role_palette(text, "riff"),
        "Hook": role_palette(text, "hook"),
        "Percussion": role_palette(text, "percussion"),
        "Snare / Clap": role_palette(text, "snare"),
        "Ambience": role_palette(text, "ambience"),
        "Hh / Sh / Rd +": role_palette(text, "hats"),
        "Bd": role_palette(text, "bd"),
        "Bass": role_palette(text, "bass"),
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


def drum_only(text: str, bars: int, energy: str, keep: set[int], genre: str = "") -> list[dict[str, Any]]:
    return filter_drums(library_drums(text, bars, energy, keep, genre=genre), keep)


def pad_notes(text: str, bars: int, energy: str, genre: str = "") -> list[dict[str, Any]]:
    notes = genre_chords(text, bars, energy, genre)
    for note in notes:
        note["duration"] = 7.75 if energy in {"intro", "break"} else 3.75
        note["velocity"] = 54 if energy in {"intro", "break"} else 64
    return notes


def hook_notes(text: str, bars: int, energy: str, genre: str = "") -> list[dict[str, Any]]:
    notes = genre_lead(text, bars, "break" if energy == "break" else "main", genre)
    return transpose_notes(notes, 0 if energy == "break" else 12)


def riff_notes(text: str, bars: int, energy: str, genre: str = "") -> list[dict[str, Any]]:
    notes = genre_lead(text, bars, "build" if energy == "build" else "main", genre)
    shifted = transpose_notes(notes, -12)
    for index, note in enumerate(shifted):
        if index % 3 == 0:
            note["mute"] = True
        note["velocity"] = max(45, int(note["velocity"]) - 12)
    return shifted


def percussion_notes(bars: int, energy: str) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    velocity = 58 if energy == "intro" else 74
    for bar in range(bars):
        start = bar * 4.0
        for offset in [0.75, 1.25, 2.75, 3.25]:
            notes.append({"pitch": 40, "start": start + offset, "duration": 0.08, "velocity": velocity, "mute": False})
        if energy in {"build", "main"}:
            for offset in [0.5, 1.75, 2.5, 3.75]:
                notes.append({"pitch": 37, "start": start + offset, "duration": 0.08, "velocity": velocity - 10, "mute": False})
    return notes


def ambience_notes(text: str, bars: int, energy: str) -> list[dict[str, Any]]:
    notes = transpose_notes(generate_melody(text, max(1, min(bars, 8))), 24)
    result = []
    for index, note in enumerate(notes):
        if index % 6 == 0:
            copy = dict(note)
            copy["start"] = min(float(copy["start"]) * 2, bars * 4 - 0.5)
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


def enrich_actions(message: str, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bars = extract_bars(message.lower())
    enriched: list[dict[str, Any]] = []
    for action in actions:
        if action.get("type") == "create_midi_clip" and not action.get("notes"):
            name = f"{action.get('track_name', '')} {action.get('clip_name', '')}".lower()
            style = detect_style(message)
            if "bass" in name:
                action["notes"] = genre_bassline(message, bars, genre=style)
            elif "drum" in name:
                action["notes"] = library_drums(message, bars, genre=style)
            elif "melody" in name or "lead" in name:
                action["notes"] = genre_lead(message, bars, genre=style)
            else:
                action["notes"] = genre_chords(message, bars, genre=style)
            action.setdefault("length_beats", bars * 4)
            action.setdefault("scene_index", 0)
        enriched.append(action)
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
    match = re.search(r"(?:called|named)\s+([A-Za-z0-9 _-]{2,32})", message)
    if match:
        return match.group(1).strip()
    return fallback


def extract_track_reference(message: str) -> str:
    match = re.search(r"(?:track|channel)\s+(?:called|named)?\s*([A-Za-z0-9 _-]{2,32})", message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "AI Chords"
