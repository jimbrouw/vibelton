"""Deterministic Song Sketch preset data and read-only cleanup proposals.

This module intentionally contains no queue or Ableton access.  The preset is
small, versioned data; the production service validates it against a fresh
bridge state before it becomes a plan.
"""
from __future__ import annotations

from typing import Any


CLASSIC_HOUSE_CLUB_MIX_ID = "classic-house-124-club-mix/v1"

# Ableton colour indices, chosen once for the preset so plans do not depend on
# host-specific RGB palette values.
COLOURS = {
    "DRUMS": 3,
    "BASS": 11,
    "MUSIC": 43,
    "VOCALS": 49,
    "FX": 58,
    "REFERENCE": 62,
}

TRACKS = (
    ("DRUMS", "Kick", "midi"),
    ("DRUMS", "Snare / Clap", "midi"),
    ("DRUMS", "Hats", "midi"),
    ("DRUMS", "Percussion", "midi"),
    ("BASS", "Bass", "midi"),
    ("MUSIC", "Chords", "midi"),
    ("MUSIC", "Lead", "midi"),
    ("MUSIC", "Hook", "midi"),
    ("MUSIC", "Atmosphere", "midi"),
    ("VOCALS", "Vocal", "audio"),
    ("FX", "FX / Risers", "audio"),
    ("REFERENCE", "Reference", "audio"),
)

# 144 bars at 124 BPM is about 4:39.  This is a deliberately fixed Club Mix
# map for Phase 2; VIBELTON_V2 does not prescribe a more specific one.
LOCATORS = (
    (0.0, "INTRO · 16 bars"),
    (64.0, "GROOVE · 16 bars"),
    (128.0, "MAIN GROOVE · 32 bars"),
    (256.0, "TENSION · 16 bars"),
    (320.0, "BREAKDOWN · 16 bars"),
    (384.0, "MAIN SECTION · 32 bars"),
    (512.0, "DJ OUTRO · 16 bars"),
)


def classic_house_preset() -> dict[str, Any]:
    """Return the immutable first Song Sketch preset as JSON-safe data."""
    groups = [{"name": name, "color_index": COLOURS[name]} for name in COLOURS]
    tracks = [
        {"group": group, "name": name, "track_type": track_type, "color_index": COLOURS[group]}
        for group, name, track_type in TRACKS
    ]
    return {
        "id": CLASSIC_HOUSE_CLUB_MIX_ID,
        "genre": "House",
        "style": "Classic",
        "variant": "Club Mix",
        "tempo": 124.0,
        "metre": [4, 4],
        "total_bars": 144,
        "approximate_duration_seconds": round(144 * 4 * 60 / 124, 3),
        "groups": groups,
        "intended_groups": [{"name": group, "roles": [name for candidate, name, _kind in TRACKS if candidate == group]}
                            for group in COLOURS],
        "tracks": tracks,
        "locators": [{"time": time, "name": name} for time, name in LOCATORS],
        "excluded": ["devices", "clips", "returns", "routing", "sidechain"],
    }


def layout_mode(group_creation: bool) -> tuple[str, list[str]]:
    """Select only a real host layout, never a simulated group relationship."""
    if group_creation:
        return "grouped", []
    return "flat", ["Groups were not created because this Ableton Live Remote Script cannot create group tracks deterministically."]


import re


def is_empty_track(track: dict[str, Any], session_clips: list[Any] | None = None) -> bool:
    """Return True when a non-group track has no devices, no Session clips, and no Arrangement clips."""
    if bool(track.get("is_group")):
        return False
    if track.get("devices") or track.get("arrangement_clips"):
        return False
    s_clips = session_clips if session_clips is not None else track.get("session_clips", [])
    if s_clips or track.get("clips"):
        return False
    return True


def detect_key_hint(track: dict[str, Any]) -> dict[str, Any] | None:
    """Extract deterministic musical key/octave hints from track, device, or clip names."""
    parts = [str(track.get("name", ""))]
    for device in track.get("devices", []) if isinstance(track.get("devices"), list) else []:
        if isinstance(device, dict):
            parts.append(str(device.get("name", "")))
    for clip in track.get("arrangement_clips", []) if isinstance(track.get("arrangement_clips"), list) else []:
        if isinstance(clip, dict):
            parts.append(str(clip.get("name", "")))
    text = " ".join(parts)
    match = re.search(r"\b([A-G])\s*(?:flat|b)\s*(\d)?\b", text, re.IGNORECASE)
    if match:
        note = match.group(1).upper() + "b"
        octave = int(match.group(2)) if match.group(2) is not None else None
        return {"key": note, "octave": octave}
    match = re.search(r"\b([A-G])\s*(?:sharp|#)\s*(\d)?\b", text, re.IGNORECASE)
    if match:
        note = match.group(1).upper() + "#"
        octave = int(match.group(2)) if match.group(2) is not None else None
        return {"key": note, "octave": octave}
    match = re.search(r"\b([A-G][b#]?)\s*(min|maj|m)\b", text)
    if match:
        qual = "m" if match.group(2).lower().startswith("m") and match.group(2).lower() != "maj" else ""
        return {"key": match.group(1)[0].upper() + match.group(1)[1:] + qual, "octave": None}
    return None


def _role_for(track: dict[str, Any]) -> tuple[str | None, float, str]:
    """Return only deterministic suggestions; uncertainty stays explicit."""
    name = str(track.get("name", "")).lower()
    devices = " ".join(str(device.get("name", "")).lower() for device in track.get("devices", []) if isinstance(device, dict))
    arr_clips = " ".join(str(clip.get("name", "")).lower() for clip in track.get("arrangement_clips", []) if isinstance(clip, dict))
    sess_clips = " ".join(str(clip.get("name", "")).lower() for clip in track.get("session_clips", []) if isinstance(clip, dict))
    text = " ".join(part for part in (name, devices, arr_clips, sess_clips) if part)
    rules = (
        (("kick",), "Kick", 0.98, "name/device contains kick"),
        (("snare", "clap"), "Snare / Clap", 0.94, "name/device identifies snare or clap"),
        (("hat", "cymbal", "top loop"), "Hats", 0.92, "name/device identifies hats or cymbals"),
        (("perc", "shaker", "conga", "bongo", "drmlp", "drm", "drumloop", "drum", "break"), "Percussion", 0.88, "name/device identifies percussion"),
        (("moog", "808", "reese", "donk", "bass", "sub"), "Bass", 0.92, "name/device identifies a bass source"),
        (("chord", "piano", "keys", "operator", "electro", "studioverse", "stab"), "Chords", 0.78, "name/device identifies chordal material"),
        (("lead",), "Lead", 0.90, "name/device identifies a lead"),
        (("hook", "riff", "pluck", "arp", "the_instrument"), "Hook", 0.84, "name/device identifies a hook or riff"),
        (("serum", "synth"), "Bass", 0.72, "name/device identifies a synth/bass source"),
        (("atmos", "ambien", "texture", "pad"), "Atmosphere", 0.82, "name/device identifies atmosphere"),
        (("vocal", "voice"), "Vocal", 0.94, "name/device identifies vocals"),
        (("riser", "sweep", " fx", "fx "), "FX / Risers", 0.80, "name/device identifies transition FX"),
        (("reference", "ref "), "Reference", 0.96, "name/device identifies reference audio"),
    )
    for terms, role, confidence, reason in rules:
        if any(term in text for term in terms):
            return role, confidence, reason
    return None, 0.0, "No deterministic role match"


def cleanup_proposal(tracks: list[dict[str, Any]], *, proposal_id: str, session_id: str, source_revision: str,
                     confirmed_roles: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a review-only mapping; it never emits an execution action."""
    rows: list[dict[str, Any]] = []
    proposed_names: dict[str, int] = {}
    for track in tracks:
        role, confidence, reason = _role_for(track)
        empty = is_empty_track(track) and role is None
        key_hint = detect_key_hint(track)
        source = "suggested"
        if confirmed_roles and track["id"] in confirmed_roles.get("roles", {}):
            role = confirmed_roles["roles"][track["id"]]
            confidence, reason, source = 1.0, "User confirmed role" if role else "User chose Unknown / leave unchanged", "confirmed"
        group = next((group for group, name, _kind in TRACKS if name == role), None)
        suggested_name = role
        if suggested_name:
            proposed_names[suggested_name] = proposed_names.get(suggested_name, 0) + 1
        rows.append({
            "id": str(track["id"]),
            "current_name": str(track["name"]),
            "suggested_name": suggested_name,
            "confidence": confidence,
            "role": role,
            "role_source": source,
            "suggested_group": group,
            "suggested_color_index": COLOURS[group] if group else None,
            "reason": "Empty unused track with no devices or clips" if empty else reason,
            "requires_choice": role is None,
            "is_empty": empty,
            "key_hint": key_hint,
        })
    existing_names = {str(track["name"]) for track in tracks}
    for row in rows:
        if row["suggested_name"] and (proposed_names[row["suggested_name"]] > 1 or
                                      (row["suggested_name"] in existing_names and row["current_name"] != row["suggested_name"])):
            row["requires_choice"] = True
            row["reason"] += "; duplicate-name resolution required"
    return {
        "schema_version": "vibelton.song-sketch-cleanup-proposal/v1",
        "id": proposal_id,
        "status": "Proposal",
        "session_id": session_id,
        "source_revision": source_revision,
        "tracks": rows,
        "apply_available": False,
        "reason": "Cleanup is review-only in Phase 2 and cannot change Live until explicitly expanded.",
    }
