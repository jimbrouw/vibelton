"""Read-only track-role suggestions and exact-revision confirmation records."""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from . import song_sketch

SCHEMA = "vibelton.track-role-map/v1"
ROLES = tuple(name for _group, name, _kind in song_sketch.TRACKS)


def track_signature(tracks: list[dict[str, Any]], live_tracks: list[dict[str, Any]] | None = None) -> str:
    """Bind confirmations to the observed track identities and context."""
    fields = ("id", "index", "name", "type", "devices", "routing", "group_track_id",
              "arrangement_clips", "song_sketch", "song_sketch_metadata")
    rows = [{key: copy.deepcopy(track.get(key)) for key in fields} for track in tracks]
    if live_tracks is not None:
        by_id = {track.get("id"): track for track in live_tracks if isinstance(track, dict)}
        for row in rows:
            row["session_clips"] = copy.deepcopy(by_id.get(row["id"], {}).get("clips", []))
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def suggest(track: dict[str, Any], session_track: dict[str, Any] | None = None) -> dict[str, Any]:
    session_track = session_track or {}
    role, confidence, reason = song_sketch._role_for(track)
    metadata = track.get("song_sketch")
    if not isinstance(metadata, dict):
        metadata = track.get("song_sketch_metadata")
    if isinstance(metadata, dict) and metadata.get("role") in ROLES:
        role, confidence, reason = metadata["role"], .99, "Existing Song Sketch role metadata"
    session_clips = session_track.get("clips") if "clips" in session_track else track.get("session_clips", [])
    empty = song_sketch.is_empty_track(track, session_clips) and role is None
    key_hint = song_sketch.detect_key_hint(track)
    context = {
        "name": track.get("name"), "type": track.get("type"),
        "devices": [device.get("name") for device in track.get("devices", []) if isinstance(device, dict)],
        "routing": track.get("routing"),
        "arrangement_clip_count": len(track.get("arrangement_clips", [])),
        "session_clip_count": len(session_clips or []),
        "song_sketch_metadata": copy.deepcopy(metadata) if isinstance(metadata, dict) else None,
        "is_empty": empty,
        "key_hint": key_hint,
    }
    if role is None:
        reason = "Empty unused track with no devices or clips." if empty else (
            "Name, device, and Song Sketch metadata do not identify a role; clip count and routing alone are inconclusive."
        )
    else:
        if key_hint:
            reason += " (detected key hint: %s)" % key_hint["key"]
        reason += "; clip and routing context is shown for user review, not treated as proof"
    return {"track_id": track["id"], "context": context,
            "suggested_role": role, "confidence": confidence, "reason": reason,
            "is_empty": empty, "key_hint": key_hint,
            "options": list(ROLES) + ["Unknown / leave unchanged"],
            "selection_required": True}


def proposal(state: dict[str, Any], production: dict[str, Any], proposal_id: str) -> dict[str, Any]:
    live_tracks = {track.get("id"): track for track in state.get("tracks", []) if isinstance(track, dict)}
    tracks = production["tracks"]
    return {"schema_version": SCHEMA, "id": proposal_id, "status": "proposed",
            "session_id": state["session_id"], "source_revision": production["revision"],
            "track_signature": track_signature(tracks, state.get("tracks", [])),
            "tracks": [suggest(track, live_tracks.get(track.get("id"))) for track in tracks],
            "active": False, "live_mutation": False}


def validate_active(record: dict[str, Any] | None, state: dict[str, Any],
                    production: dict[str, Any]) -> dict[str, Any] | None:
    if not record or record.get("status") != "confirmed":
        return None
    if (record.get("session_id") != state.get("session_id") or
            record.get("source_revision") != production.get("revision") or
            record.get("track_signature") != track_signature(production["tracks"], state.get("tracks", []))):
        return None
    if set(record.get("roles", {})) != {track["id"] for track in production["tracks"]}:
        return None
    return record
