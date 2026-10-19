"""Deterministic Song Sketch preset data and read-only cleanup proposals.

This module intentionally contains no queue or Ableton access.  The preset is
small, versioned data; the production service validates it against a fresh
bridge state before it becomes a plan.
"""
from __future__ import annotations

import re
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


# (words, role, confidence).  Checked in this order within one source, so "bass drum" is a Kick
# before it can be a Bass.  Words of three letters or fewer must stand alone ("bd", "vox", "sub"),
# (a plural "s" is fine), so they don't match inside other words; longer words may sit inside a
# name ("hihat", "Basslines").
ROLE_RULES: tuple[tuple[tuple[str, ...], str, float], ...] = (
    (("kick", "kik", "bd", "bass drum", "bassdrum"), "Kick", 0.98),
    (("snare", "clap", "sd", "rim", "rimshot", "snap"), "Snare / Clap", 0.94),
    (("hat", "hihat", "hh", "oh", "cymbal", "ride", "top loop", "tops"), "Hats", 0.92),
    (("perc", "shaker", "tamb", "conga", "bongo", "tom", "toms", "drmlp", "drm", "drum", "drums",
      "drumloop", "break", "breaks", "kit"), "Percussion", 0.86),
    (("808", "bass", "sub", "reese", "donk", "moog"), "Bass", 0.92),
    (("chord", "chords", "piano", "keys", "rhodes", "wurli", "organ", "epiano", "electric", "electro",
      "studioverse", "stab", "stabs", "operator"), "Chords", 0.8),
    (("lead", "solo", "melody", "guitar", "gtr", "flute", "sax", "horn", "brass", "strings"), "Lead", 0.82),
    (("hook", "riff", "pluck", "arp", "theme", "the_instrument"), "Hook", 0.84),
    (("atmos", "atmo", "ambien", "texture", "pad", "pads", "drone", "foley", "noise"), "Atmosphere", 0.82),
    (("vocal", "vocals", "voice", "vox", "vx", "acapella", "chant", "choir", "adlib", "adlibs"), "Vocal", 0.94),
    (("riser", "sweep", "fx", "sfx", "impact", "downlifter", "uplifter", "whoosh", "transition"), "FX / Risers", 0.8),
    (("reference", "ref"), "Reference", 0.96),
    (("serum", "synth"), "Bass", 0.6),
)
# How far each place a word can come from is trusted, strongest first.
ROLE_SOURCES = (("track name", 1.0), ("clip name", 0.85), ("device", 0.7))
_DEVICE_CLASS_ROLES = {"DrumGroupDevice": ("Percussion", 0.6, "uses a Drum Rack")}


def _word_pattern(word: str) -> re.Pattern[str]:
    escaped = re.escape(word)
    if len(word) <= 3:   # standalone, optionally plural: "hat"/"hats", "sub", "vox"
        return re.compile(r"(?<![a-z])%ss?(?![a-z])" % escaped)
    return re.compile(escaped)


_RULE_PATTERNS = tuple((tuple((word, _word_pattern(word)) for word in words), role, confidence)
                       for words, role, confidence in ROLE_RULES)


def _match_role(text: str) -> tuple[str, float, str] | None:
    for words, role, confidence in _RULE_PATTERNS:
        for word, pattern in words:
            if pattern.search(text):
                return role, confidence, word
    return None


def _role_for(track: dict[str, Any]) -> tuple[str | None, float, str]:
    """Deterministic role guess with a confidence and a plain reason.

    The track name is trusted over clip names, and clip names over device names, so a vocal
    track named "Vox main" stays a Vocal even when one of its devices mentions keys."""
    lane_role = str(track.get("name", "")).rpartition(" · ")[2]
    if " · " in str(track.get("name", "")) and lane_role in {role for _group, role, _kind in TRACKS}:
        # A drum lane made by splitting a Drum Rack ("808 kick kit · Hats") is exactly what its suffix says.
        return lane_role, 0.99, "Drum lane for %s" % lane_role
    devices = [device for device in track.get("devices", []) if isinstance(device, dict)]
    clips = [clip for key in ("arrangement_clips", "session_clips")
             for clip in track.get(key, []) if isinstance(clip, dict)]
    texts = {
        "track name": str(track.get("name", "")),
        "clip name": " ".join(str(clip.get("name", "")) for clip in clips),
        "device": " ".join(str(device.get("name", "")) for device in devices),
    }
    for source, trust in ROLE_SOURCES:
        found = _match_role(texts[source].lower())
        if found:
            role, confidence, word = found
            return role, round(confidence * trust, 2), '%s has "%s"' % (source.replace("track ", "").capitalize(), word)
    for device in devices:
        known = _DEVICE_CLASS_ROLES.get(str(device.get("class_name", "")))
        if known:
            return known[0], known[1], "Track %s" % known[2]
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
