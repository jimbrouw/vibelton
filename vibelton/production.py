"""Phase 1 production-plan safety boundary.

This module deliberately sits beside the legacy chat planner and Composition
Lab.  It accepts only a small, typed, reversible action set; it never turns a
natural-language request directly into an Ableton command.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from . import errors
from . import queue
from . import arrangements
from . import finish_diagnosis
from . import role_maps
from . import role_memory
from . import rollback_safety
from . import song_sketch
from . import working_copy


ROOT = Path.home() / ".vibelton" / "production"
LOCK = threading.RLock()
# Latest Arrangement beat Vibelton will write to (900 bars of 4/4).
MAX_ARRANGEMENT_BEAT = 3600.0
# Most source tracks one scaffold uses; further tracks are listed as skipped.
MAX_SCAFFOLD_SOURCES = 16
# Roles a split drum track's lanes can take, in lane order.
DRUM_LANE_ROLES = ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "FX / Risers")
# General MIDI drum notes, used when a pad's name says nothing (Drum Racks start at C1 = 36).
_GM_DRUM_ROLES = {35: "Kick", 36: "Kick", 37: "Snare / Clap", 38: "Snare / Clap", 39: "Snare / Clap",
                  40: "Snare / Clap", 42: "Hats", 44: "Hats", 46: "Hats", 49: "Hats", 51: "Hats",
                  52: "Hats", 53: "Hats", 55: "Hats", 57: "Hats", 59: "Hats"}
PROJECT_ANALYSIS_SCHEMA = "vibelton.project-analysis/v1"
PLAN_SCHEMA = "vibelton.production-plan/v1"
SNAPSHOT_SCHEMA = "vibelton.production-snapshot/v1"
OPERATION_SCHEMA = "vibelton.production-operation/v1"
COMPARISON_SCHEMA = "vibelton.render-comparison/v1"
ARRANGEMENT_PLAN_SCHEMA = "vibelton.arrangement-plan/v1"
SUPPORTED_ACTIONS = {"set_track_mixer", "set_device_parameter", "probe_arrangement_locators",
                     "apply_song_sketch_template", "rollback_song_sketch_template",
                     "apply_arrangement_copies", "rollback_arrangement_copies",
                     "apply_session_scene_map", "rollback_session_scene_map",
                     "apply_session_to_arrangement_copies", "rollback_session_to_arrangement_copies",
                     "split_drum_track", "rollback_split_drum_track"}


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, allow_nan=False, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _production_state(state: dict[str, Any]) -> dict[str, Any]:
    production = state.get("production")
    if not isinstance(production, dict):
        raise ValueError("Install the Phase 1 Vibelton bridge and refresh Live before using Production plans")
    return production


def _effective_arrangement_readable(state_or_prod: dict[str, Any]) -> bool:
    if bool(state_or_prod.get("arrangement_readable")):
        return True
    errors = state_or_prod.get("arrangement_errors")
    if not isinstance(errors, list) or not errors:
        prod = state_or_prod.get("production")
        if isinstance(prod, dict):
            if bool(prod.get("arrangement_readable")):
                return True
            errors = prod.get("arrangement_errors")
    return isinstance(errors, list) and bool(errors) and all(
        isinstance(err, dict) and err.get("is_group") is True for err in errors
    )


def _observable_rollback_revision(production: dict[str, Any]) -> str:
    """Hash the observable Set state used to verify arrangement rollback.

    Live keeps its internal song length after long Arrangement clips are
    removed.  That changes the bridge's ``locator_range`` capability even
    though no musical or editable Set content remains.  It is therefore not
    part of the exact observable rollback comparison; the regular revision
    remains the pre-mutation stale-state guard.
    """
    observable = copy.deepcopy(production)
    observable.pop("revision", None)
    capabilities = observable.get("template_capabilities")
    if isinstance(capabilities, dict):
        capabilities.pop("locator_range", None)
    return hashlib.sha256(json.dumps(
        observable, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def _ready_state() -> tuple[dict[str, Any], dict[str, Any]]:
    state = queue.current_state()
    if not state.get("connected") or time.time() - float(state.get("updated_at") or 0) > 10:
        raise ValueError("Ableton is disconnected or its heartbeat is stale")
    if "production_v1" not in state.get("capabilities", []):
        raise ValueError("Install the Phase 1 Vibelton bridge and restart Live before using Production plans")
    production = _production_state(state)
    if production.get("session_id") != state.get("session_id") or not production.get("revision"):
        raise ValueError("Production state is incomplete; refresh Live before continuing")
    return state, production


def _finite_number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("%s must be a finite number" % label)
    if not minimum <= value <= maximum:
        raise ValueError("%s must be between %s and %s" % (label, minimum, maximum))
    return float(value)


def _tracks_by_id(production: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tracks = production.get("tracks")
    if not isinstance(tracks, list):
        raise ValueError("Production state tracks are missing")
    result = {track.get("id"): track for track in tracks if isinstance(track, dict) and isinstance(track.get("id"), str)}
    if len(result) != len(tracks):
        raise ValueError("Production state has invalid track IDs")
    return result


def _validate_action(action: Any, tracks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if isinstance(action, dict) and action.get("type") == "probe_arrangement_locators":
        if set(action) != {"type"}:
            raise ValueError("The locator probe takes no parameters")
        return {"type": "probe_arrangement_locators"}
    if isinstance(action, dict) and action.get("type") == "apply_session_scene_map":
        if set(action) != {"type", "source_scene_count", "scenes"} or type(action["source_scene_count"]) is not int or action["source_scene_count"] < 0:
            raise ValueError("Invalid Session scene plan")
        if not isinstance(action["scenes"], list) or len(action["scenes"]) != 7:
            raise ValueError("Session plan needs seven scenes")
        scenes = []
        for scene in action["scenes"]:
            if not isinstance(scene, dict) or set(scene) != {"name", "bar_count", "copies"}:
                raise ValueError("Invalid Session scene")
            if not isinstance(scene["name"], str) or not scene["name"].strip() or len(scene["name"]) > 160 or type(scene["bar_count"]) is not int or scene["bar_count"] < 1:
                raise ValueError("Invalid Session scene name or duration")
            if not isinstance(scene["copies"], list):
                raise ValueError("Invalid Session clip choices")
            copies, used = [], set()
            for spec in scene["copies"]:
                if not isinstance(spec, dict) or set(spec) != {"track_id", "source_scene_index", "source_fingerprint"}:
                    raise ValueError("Invalid Session clip source")
                track_id, index, fingerprint = spec["track_id"], spec["source_scene_index"], spec["source_fingerprint"]
                if (track_id not in tracks or track_id in used or type(index) is not int or not 0 <= index < action["source_scene_count"] or
                        not isinstance(fingerprint, str) or len(fingerprint) != 64):
                    raise ValueError("Invalid Session clip source or duplicate track")
                used.add(track_id)
                copies.append(dict(spec))
            scenes.append({"name": scene["name"], "bar_count": scene["bar_count"], "copies": copies})
        return {"type": "apply_session_scene_map", "source_scene_count": action["source_scene_count"], "scenes": scenes}
    if isinstance(action, dict) and action.get("type") == "split_drum_track":
        if set(action) != {"type", "track_id", "lanes"} or action["track_id"] not in tracks:
            raise ValueError("Invalid drum split")
        if not tracks[action["track_id"]].get("drum_rack"):
            raise ValueError("That track has no Drum Rack to split")
        lanes, seen = [], set()
        if not isinstance(action["lanes"], list) or not 2 <= len(action["lanes"]) <= 8:
            raise ValueError("A drum split needs two to eight lanes")
        for lane in action["lanes"]:
            if (not isinstance(lane, dict) or set(lane) != {"name", "role", "notes"} or not isinstance(lane["name"], str)
                    or not lane["name"].strip() or len(lane["name"]) > 120 or lane["role"] not in DRUM_LANE_ROLES
                    or not isinstance(lane["notes"], list) or not lane["notes"]
                    or any(type(n) is not int or not 0 <= n <= 127 or n in seen for n in lane["notes"])):
                raise ValueError("Invalid drum lane")
            seen.update(lane["notes"])
            lanes.append({"name": lane["name"], "role": lane["role"], "notes": sorted(lane["notes"])})
        return {"type": "split_drum_track", "track_id": action["track_id"], "lanes": lanes}
    if isinstance(action, dict) and action.get("type") == "rollback_split_drum_track":
        if (set(action) != {"type", "created_tracks", "expected_post_rollback_observable_revision", "source_track_id", "unmute_source"}
                or not isinstance(action["created_tracks"], list) or not isinstance(action["unmute_source"], bool)
                or not isinstance(action["expected_post_rollback_observable_revision"], str)
                or len(action["expected_post_rollback_observable_revision"]) != 64):
            raise ValueError("Invalid drum split undo")
        return copy.deepcopy(action)
    if isinstance(action, dict) and action.get("type") == "rollback_session_scene_map":
        if set(action) != {"type", "source_scene_count", "created_scenes", "expected_post_rollback_observable_revision"}:
            raise ValueError("Invalid Session rollback plan")
        if (type(action["source_scene_count"]) is not int or not isinstance(action["created_scenes"], list) or
                not isinstance(action["expected_post_rollback_observable_revision"], str) or
                len(action["expected_post_rollback_observable_revision"]) != 64):
            raise ValueError("Invalid Session rollback targets")
        return copy.deepcopy(action)
    if isinstance(action, dict) and action.get("type") == "apply_arrangement_copies":
        required = {"type", "copies", "locators", "locator_definitions", "locators_deferred", "expected_end_beat"}
        if set(action) != required:
            raise ValueError("Invalid arrangement-copy action")
        end = _finite_number(action["expected_end_beat"], "expected arrangement end", 0.001, MAX_ARRANGEMENT_BEAT)
        if not isinstance(action["copies"], list) or not action["copies"]:
            raise ValueError("Arrangement copy action requires copies")
        copies = []
        destinations = set()
        for item in action["copies"]:
            required = {"source_track_id", "source_start_beat", "source_fingerprint", "destination_beat"}
            if not isinstance(item, dict) or set(item) != required or item["source_track_id"] not in tracks:
                raise ValueError("Invalid arrangement copy source")
            start = _finite_number(item["source_start_beat"], "source start", 0.0, 3600.0)
            destination = _finite_number(item["destination_beat"], "copy destination", 0.0, 3600.0)
            fingerprint = item["source_fingerprint"]
            target = (item["source_track_id"], destination)
            if not isinstance(fingerprint, str) or len(fingerprint) != 64 or target in destinations:
                raise ValueError("Invalid or duplicate arrangement copy target")
            destinations.add(target)
            copies.append({"source_track_id": item["source_track_id"], "source_start_beat": start,
                           "source_fingerprint": fingerprint, "destination_beat": destination})
        if not isinstance(action["locators_deferred"], bool) or not isinstance(action["locator_definitions"], list) or len(action["locator_definitions"]) != 7:
            raise ValueError("Arrangement copy action requires seven locator definitions")
        if action["locators_deferred"] and action["locators"]:
            raise ValueError("Deferred arrangement locators must not mutate Live")
        if not action["locators_deferred"] and (not isinstance(action["locators"], list) or not 1 <= len(action["locators"]) <= 7):
            raise ValueError("Arrangement copy action requires between one and seven locators")
        locators = []
        for item in action["locator_definitions"]:
            if not isinstance(item, dict) or set(item) != {"time", "name"}:
                raise ValueError("Invalid arrangement locator")
            # Definitions are plan metadata (a one-section plan lists later sections too); only the cues
            # actually created are bounded by the plan's end (checked below).
            time_value = _finite_number(item["time"], "locator time", 0.0, 3600.0)
            if not isinstance(item["name"], str) or not item["name"].strip() or len(item["name"]) > 160:
                raise ValueError("Invalid arrangement locator name")
            locators.append({"time": time_value, "name": item["name"]})
        if sorted(item["time"] for item in locators) != [item["time"] for item in locators]:
            raise ValueError("Arrangement locators must be ordered")
        chosen = []
        if not action["locators_deferred"]:
            for item in action["locators"]:
                entry = {"time": _finite_number(item.get("time") if isinstance(item, dict) else None, "locator time", 0.0, end),
                         "name": item.get("name")}
                if set(item) != {"time", "name"} or entry not in locators:
                    raise ValueError("Each created locator must be one of the plan's locator definitions")
                chosen.append(entry)
            if sorted(item["time"] for item in chosen) != [item["time"] for item in chosen]:
                raise ValueError("Arrangement locators must be ordered")
        return {"type": "apply_arrangement_copies", "copies": copies,
                "locators": chosen,
                "locator_definitions": locators, "locators_deferred": action["locators_deferred"],
                "expected_end_beat": end}
    if isinstance(action, dict) and action.get("type") == "rollback_arrangement_copies":
        if set(action) != {"type", "copies", "locators", "expected_post_rollback_observable_revision"}:
            raise ValueError("Invalid arrangement-copy rollback action")
        if not isinstance(action["copies"], list) or not isinstance(action["locators"], list):
            raise ValueError("Invalid arrangement-copy rollback targets")
        return {"type": "rollback_arrangement_copies", "copies": copy.deepcopy(action["copies"]),
                "locators": copy.deepcopy(action["locators"]),
                "expected_post_rollback_observable_revision": action["expected_post_rollback_observable_revision"]}
    if isinstance(action, dict) and action.get("type") == "apply_session_to_arrangement_copies":
        if set(action) not in ({"type", "copies"}, {"type", "copies", "expected_end_beat"}):
            raise ValueError("Invalid session-to-arrangement copy action")
        if not isinstance(action.get("copies"), list) or not action["copies"]:
            raise ValueError("Session-to-arrangement copy action requires copies")
        copies = []
        destinations = set()
        for item in action["copies"]:
            required = {"track_id", "source_scene_index", "source_fingerprint", "destination_beat"}
            if not isinstance(item, dict) or set(item) != required or item["track_id"] not in tracks:
                raise ValueError("Invalid session-to-arrangement copy source")
            s_idx = item["source_scene_index"]
            if type(s_idx) is not int or s_idx < 0:
                raise ValueError("Invalid session scene index")
            destination = _finite_number(item["destination_beat"], "copy destination", 0.0, 3600.0)
            fingerprint = item["source_fingerprint"]
            target = (item["track_id"], destination)
            if not isinstance(fingerprint, str) or len(fingerprint) != 64 or target in destinations:
                raise ValueError("Invalid or duplicate session-to-arrangement copy target")
            destinations.add(target)
            copies.append({
                "track_id": item["track_id"],
                "source_scene_index": s_idx,
                "source_fingerprint": fingerprint,
                "destination_beat": destination,
            })
        normalized_s2a: dict[str, Any] = {"type": "apply_session_to_arrangement_copies", "copies": copies}
        if "expected_end_beat" in action and action["expected_end_beat"] is not None:
            normalized_s2a["expected_end_beat"] = _finite_number(action["expected_end_beat"], "expected arrangement end", 0.001, 3600.0)
        return normalized_s2a
    if isinstance(action, dict) and action.get("type") == "rollback_session_to_arrangement_copies":
        if set(action) != {"type", "copies", "expected_post_rollback_observable_revision"}:
            raise ValueError("Invalid session-to-arrangement rollback action")
        if (not isinstance(action["copies"], list) or not action["copies"] or
                not isinstance(action["expected_post_rollback_observable_revision"], str) or
                len(action["expected_post_rollback_observable_revision"]) != 64):
            raise ValueError("Invalid session-to-arrangement rollback targets")
        return {
            "type": "rollback_session_to_arrangement_copies",
            "copies": copy.deepcopy(action["copies"]),
            "expected_post_rollback_observable_revision": action["expected_post_rollback_observable_revision"],
        }
    if isinstance(action, dict) and action.get("type") == "apply_song_sketch_template":
        if (set(action) != {"type", "preset_id", "layout_mode", "locator_range"} or
                action.get("preset_id") != song_sketch.CLASSIC_HOUSE_CLUB_MIX_ID or
                action.get("layout_mode") not in {"grouped", "flat"} or
                not isinstance(action.get("locator_range"), bool)):
            raise ValueError("Invalid Song Sketch template action")
        return {"type": "apply_song_sketch_template", "preset_id": song_sketch.CLASSIC_HOUSE_CLUB_MIX_ID,
                "layout_mode": action["layout_mode"], "locator_range": action["locator_range"]}
    if isinstance(action, dict) and action.get("type") == "rollback_song_sketch_template":
        required = {"type", "preset_id", "created_track_ids", "created_locators", "restore_tempo", "restore_metre", "restore_tracks"}
        if set(action) != required or action.get("preset_id") != song_sketch.CLASSIC_HOUSE_CLUB_MIX_ID:
            raise ValueError("Invalid Song Sketch template rollback action")
        if (not isinstance(action["created_track_ids"], list) or not all(isinstance(item, str) for item in action["created_track_ids"]) or
                not isinstance(action["created_locators"], list) or not all(isinstance(item, dict) for item in action["created_locators"])):
            raise ValueError("Invalid Song Sketch template rollback targets")
        if not isinstance(action["restore_tracks"], list) or not all(isinstance(item, dict) for item in action["restore_tracks"]):
            raise ValueError("Invalid Song Sketch template rollback state")
        tempo = _finite_number(action["restore_tempo"], "tempo", 40.0, 240.0)
        metre = action["restore_metre"]
        if not isinstance(metre, list) or len(metre) != 2 or tuple(metre) not in {(4, 4)}:
            raise ValueError("Unsupported Song Sketch template rollback metre")
        return {"type": "rollback_song_sketch_template", "preset_id": song_sketch.CLASSIC_HOUSE_CLUB_MIX_ID,
                "created_track_ids": list(action["created_track_ids"]), "created_locators": copy.deepcopy(action["created_locators"]),
                "restore_tempo": tempo, "restore_metre": [4, 4], "restore_tracks": copy.deepcopy(action["restore_tracks"])}
    if isinstance(action, dict) and action.get("type") == "set_device_parameter":
        allowed_keys = {"type", "target_track_id", "track_id", "device_index", "parameter_index", "value"}
        if not set(action).issubset(allowed_keys):
            raise ValueError("Invalid set_device_parameter action fields")
        track_id = action.get("target_track_id") or action.get("track_id")
        if not isinstance(track_id, str) or track_id not in tracks:
            raise ValueError("Production action target does not exist in the current Live state")
        dev_idx = action.get("device_index")
        param_idx = action.get("parameter_index")
        devices = tracks[track_id].get("devices")
        if not isinstance(devices, list) or type(dev_idx) is not int or not 0 <= dev_idx < len(devices):
            raise ValueError("Invalid device_index for set_device_parameter")
        device = devices[dev_idx] if isinstance(devices[dev_idx], dict) else {}
        params = device.get("parameters")
        p_min, p_max = 0.0, 1.0
        if isinstance(params, list) and params:
            if type(param_idx) is not int or not 0 <= param_idx < len(params):
                raise ValueError("Invalid parameter_index for set_device_parameter")
            p_spec = params[param_idx] if isinstance(params[param_idx], dict) else {}
            p_min = float(p_spec.get("min", 0.0))
            p_max = float(p_spec.get("max", 1.0))
        else:
            if type(param_idx) is not int or not 0 <= param_idx < 64:
                raise ValueError("Invalid parameter_index for set_device_parameter")
        val = _finite_number(action.get("value"), "parameter value", p_min, p_max)
        return {
            "type": "set_device_parameter",
            "target_track_id": track_id,
            "device_index": dev_idx,
            "parameter_index": param_idx,
            "value": val,
        }
    if not isinstance(action, dict) or set(action) != {"type", "target_track_id", "values"}:
        raise ValueError("Production actions must contain only type, target_track_id, and values")
    if action.get("type") not in SUPPORTED_ACTIONS:
        raise ValueError("Unsupported production action: %s" % action.get("type"))
    track_id = action.get("target_track_id")
    if not isinstance(track_id, str) or track_id not in tracks:
        raise ValueError("Production action target does not exist in the current Live state")
    values = action.get("values")
    allowed_mixer = {"volume", "pan", "send_0", "send_1", "sends"}
    if not isinstance(values, dict) or not values or set(values) - allowed_mixer:
        raise ValueError("set_track_mixer values must contain volume, pan, send_0, send_1, and/or sends")
    mixer = tracks[track_id].get("mixer")
    if not isinstance(mixer, dict):
        raise ValueError("Production state lacks the mixer fields needed for this action")
    mixer_sends = mixer.get("sends") if isinstance(mixer.get("sends"), list) else []
    normalized: dict[str, Any] = {}
    if "volume" in values:
        if "volume" not in mixer:
            raise ValueError("Production state lacks the mixer fields needed for this action")
        normalized["volume"] = _finite_number(values["volume"], "volume", 0.0, 1.0)
    if "pan" in values:
        if "pan" not in mixer:
            raise ValueError("Production state lacks the mixer fields needed for this action")
        normalized["pan"] = _finite_number(values["pan"], "pan", -1.0, 1.0)
    if "send_0" in values:
        if len(mixer_sends) < 1:
            raise ValueError("Track has no send_0 available in mixer state")
        normalized["send_0"] = _finite_number(values["send_0"], "send_0", 0.0, 1.0)
    if "send_1" in values:
        if len(mixer_sends) < 2:
            raise ValueError("Track has no send_1 available in mixer state")
        normalized["send_1"] = _finite_number(values["send_1"], "send_1", 0.0, 1.0)
    if "sends" in values:
        raw_sends = values["sends"]
        if not isinstance(raw_sends, list) or not raw_sends or len(raw_sends) > len(mixer_sends):
            raise ValueError("Invalid mixer sends list for target track")
        normalized["sends"] = [_finite_number(sv, "send", 0.0, 1.0) for sv in raw_sends]
    return {"type": "set_track_mixer", "target_track_id": track_id, "values": normalized}


def _append_operation(kind: str, request_id: str, data: dict[str, Any]) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": OPERATION_SCHEMA,
        "id": str(uuid.uuid4()),
        "kind": kind,
        "request_id": request_id,
        "timestamp": time.time(),
        "data": data,
        "cost": {"model_tokens": None, "estimated_cost": None, "computer_use_steps": 0},
    }
    with (ROOT / "operations.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n")


def _recent_operations(limit: int = 30) -> list[dict[str, Any]]:
    path = ROOT / "operations.jsonl"
    if not path.exists():
        return []
    results: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results


def _extract_audio_clips_in_set(state: dict[str, Any], production_tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_tracks_by_id = {
        str(t.get("id")): t
        for t in (state.get("tracks") or [])
        if isinstance(t, dict) and t.get("id")
    }
    raw_tracks_by_idx = {
        int(t.get("index")): t
        for t in (state.get("tracks") or [])
        if isinstance(t, dict) and isinstance(t.get("index"), int)
    }
    audio_clips: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for tr in production_tracks:
        tr_id = str(tr.get("id") or "")
        tr_name = str(tr.get("name") or "")
        tr_idx = tr.get("index")
        raw_tr = raw_tracks_by_id.get(tr_id) or (raw_tracks_by_idx.get(tr_idx) if isinstance(tr_idx, int) else {}) or {}
        role = tr.get("suggested_role") or raw_tr.get("suggested_role") or tr.get("type") or "audio"

        # 1. Arrangement clips from state.tracks (which include summary.file_path)
        for c in (raw_tr.get("arrangement_clips") or tr.get("arrangement_clips") or []):
            if not isinstance(c, dict):
                continue
            summary = c.get("summary") or {}
            fp = str(c.get("file_path") or summary.get("file_path") or "").strip()
            if fp:
                c_name = str(c.get("name") or Path(fp).stem)
                key = (tr_id, c_name, fp)
                if key not in seen_keys:
                    seen_keys.add(key)
                    audio_clips.append({
                        "track_id": tr_id,
                        "track_name": tr_name,
                        "clip_name": c_name,
                        "file_path": fp,
                        "role": role,
                        "location": "arrangement",
                    })

        # 2. Session clips from session_clip_summaries or clips
        sess_summaries = raw_tr.get("session_clip_summaries") or tr.get("session_clip_summaries") or {}
        for c in (raw_tr.get("clips") or tr.get("session_clips") or []):
            if not isinstance(c, dict):
                continue
            s_idx = str(c.get("scene_index"))
            summary = c.get("summary") or sess_summaries.get(s_idx) or {}
            fp = str(c.get("file_path") or summary.get("file_path") or "").strip()
            if fp:
                c_name = str(c.get("name") or Path(fp).stem)
                key = (tr_id, c_name, fp)
                if key not in seen_keys:
                    seen_keys.add(key)
                    audio_clips.append({
                        "track_id": tr_id,
                        "track_name": tr_name,
                        "clip_name": c_name,
                        "file_path": fp,
                        "role": role,
                        "location": "session",
                    })
    return audio_clips


def _with_role_guess(track: dict[str, Any], all_tracks: list[dict[str, Any]]) -> dict[str, Any]:
    """The role the scaffold would guess for this track, so the device shows the same guess."""
    role, confidence, reason = song_sketch._role_for(track)
    track.update(suggested_role=role, role_confidence=confidence, role_reason=reason)
    lanes = split_lanes_of(track, all_tracks) if track.get("drum_rack") else []
    if lanes:
        track.update(split_into_lanes=len(lanes))
    elif track.get("drum_rack"):
        preview = drum_split_preview(track)
        if preview:
            track.update(drum_split_preview=[{"role": lane["role"], "pads": [p["name"] or "note %d" % p["note"] for p in lane["pads"]]}
                                             for lane in preview])
    return track


def analyse() -> dict[str, Any]:
    """Return qualified, local project facts; no audio claims are made here."""
    state, production = _ready_state()
    tracks = _tracks_by_id(production)
    audio_clips_in_set = _extract_audio_clips_in_set(state, production["tracks"])
    return {
        "schema_version": PROJECT_ANALYSIS_SCHEMA,
        "source_revision": production["revision"],
        "session_id": state["session_id"],
        "project": {
            "tempo": state.get("tempo"),
            "metre": state.get("metre"),
            "track_count": len(tracks),
            "arrangement_readable": _effective_arrangement_readable(state),
            "arrangement_end": state.get("arrangement_end"),
            "locators": copy.deepcopy(production.get("locators", [])),
        },
        "tracks": [_with_role_guess(track, production["tracks"]) for track in copy.deepcopy(production["tracks"])],
        "audio_clips_in_set": audio_clips_in_set,
        "missing_measurements": [
            item for item in ("audio_render", "loudness", "spectrum", "stereo", "automation")
        ] + ([] if production.get("template_capabilities", {}).get("locators") else ["locators"]),
    }


def diagnose_finish(payload: dict[str, Any]) -> dict[str, Any]:
    """Read a fresh revision and diagnose it without queueing Live actions."""
    if not isinstance(payload, dict) or set(payload) != {"template_variant_id", "expected_revision"}:
        raise ValueError("Diagnosis requires template_variant_id and expected_revision")
    analysis = analyse()
    if payload["expected_revision"] != analysis["source_revision"]:
        raise ValueError("Production state changed; refresh analysis before diagnosis")
    state, project = _ready_state()
    if state["session_id"] != analysis["session_id"] or project["revision"] != analysis["source_revision"]:
        raise ValueError("Production state changed during diagnosis; refresh analysis")
    active = role_maps.validate_active(_read(ROOT / "role-maps" / "active.json"), state, project)
    result = finish_diagnosis.diagnose(analysis, payload["template_variant_id"], active)
    _append_operation("finish_diagnosed", analysis["source_revision"], {
        "template_variant_id": payload["template_variant_id"],
        "finding_codes": [item["code"] for item in result["findings"]],
        "workflow": "phase_4_read_only",
    })
    return result


def propose_track_roles(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"request_id"}:
        raise ValueError("Role proposal requires request_id")
    with LOCK:
        request_id = _request_id(payload)
        state, project = _ready_state()
        previous = _read(ROOT / "role-requests" / (request_id + ".json"))
        if previous:
            proposal = _read(ROOT / "role-proposals" / (previous["proposal_id"] + ".json"))
            if not proposal or (proposal["session_id"], proposal["source_revision"], proposal["track_signature"]) != (
                    state["session_id"], project["revision"], role_maps.track_signature(project["tracks"], state.get("tracks", []))):
                raise ValueError("Role proposal is stale; create a new proposal")
            return proposal
        proposal = role_maps.proposal(state, project, str(uuid.uuid4()))
        _write(ROOT / "role-proposals" / (proposal["id"] + ".json"), proposal)
        _write(ROOT / "role-requests" / (request_id + ".json"), {"proposal_id": proposal["id"]})
        _append_operation("track_roles_proposed", proposal["id"], {"track_count": len(proposal["tracks"])})
        return proposal


def confirm_track_roles(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"proposal_id", "roles"}:
        raise ValueError("Role confirmation requires proposal_id and roles")
    try:
        uuid.UUID(str(payload["proposal_id"]))
    except ValueError:
        raise ValueError("Invalid role proposal ID")
    with LOCK:
        proposal = _read(ROOT / "role-proposals" / (str(payload["proposal_id"]) + ".json"))
        if not proposal:
            raise ValueError("Role proposal not found")
        state, project = _ready_state()
        if (proposal["session_id"], proposal["source_revision"], proposal["track_signature"]) != (
                state["session_id"], project["revision"], role_maps.track_signature(project["tracks"], state.get("tracks", []))):
            raise ValueError("Role proposal is stale; confirm again from a fresh proposal")
        roles = payload["roles"]
        if not isinstance(roles, dict) or set(roles) != {track["id"] for track in project["tracks"]}:
            raise ValueError("Confirm a role or Unknown for every current track")
        if any(role is not None and role not in role_maps.ROLES for role in roles.values()):
            raise ValueError("Unsupported track role; use null for Unknown / leave unchanged")
        existing = _read(ROOT / "role-confirmations" / (proposal["id"] + ".json"))
        if existing:
            if existing["roles"] != roles:
                raise ValueError("Proposal already confirmed with different choices")
            return existing
        record = {"schema_version": role_maps.SCHEMA, "proposal_id": proposal["id"],
                  "status": "confirmed", "active": True, "session_id": state["session_id"],
                  "source_revision": project["revision"], "track_signature": proposal["track_signature"],
                  "roles": copy.deepcopy(roles), "confirmed_at": time.time(), "live_mutation": False}
        _write(ROOT / "role-confirmations" / (proposal["id"] + ".json"), record)
        _write(ROOT / "role-maps" / "active.json", record)
        _append_operation("track_roles_confirmed", proposal["id"], {"track_count": len(roles)})
        return record


def _role_memory_path(set_path: str) -> Path:
    return ROOT / "role-memory" / (hashlib.sha256(set_path.encode()).hexdigest()[:32] + ".json")


def _role_memory_entries(set_path: str | None) -> list[dict[str, Any]]:
    if not set_path:
        return []
    return (_read(_role_memory_path(set_path)) or {}).get("entries", [])


def arranger_selection() -> dict[str, Any]:
    """The genre and variant last chosen in any Arranger view, so the docked device and pop-out agree."""
    stored = _read(ROOT / "arranger-selection.json") or {}
    genre, variant_id = stored.get("genre"), stored.get("variant_id")
    if genre not in arrangements.SUPPORTED_GENRES or variant_id not in arrangements.GENRE_VARIANTS[genre]:
        return {"genre": None, "variant_id": None, "updated_at": 0}
    return {"genre": genre, "variant_id": variant_id, "updated_at": stored.get("updated_at", 0)}


def save_arranger_selection(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"genre", "variant_id"}:
        raise ValueError("Arranger selection takes genre and variant_id")
    genre, variant_id = payload["genre"], payload["variant_id"]
    if genre not in arrangements.SUPPORTED_GENRES:
        raise ValueError("Choose a supported arrangement genre")
    if variant_id not in arrangements.GENRE_VARIANTS[genre]:
        raise ValueError(f"Variant '{variant_id}' is not valid for genre '{genre}'")
    with LOCK:
        previous = _read(ROOT / "arranger-selection.json") or {}
        # Strictly increasing, so a view never mistakes a newer choice for one it has already seen.
        updated_at = max(time.time(), float(previous.get("updated_at", 0)) + 0.001)
        selection = {"genre": genre, "variant_id": variant_id, "updated_at": updated_at}
        _write(ROOT / "arranger-selection.json", selection)
    return selection


def role_memory_status() -> dict[str, Any]:
    """Roles remembered for the open Set, matched to its current tracks (read-only)."""
    state, project = _ready_state()
    set_path = project.get("set_path") or None
    if not set_path:
        return {"schema_version": role_memory.SCHEMA, "set_path": None, "remembered": {}, "orphaned": [],
                "new_tracks": [], "reason": "unsaved",
                "message": "Save the Live Set to remember stem roles between sessions."}
    entries = _role_memory_entries(set_path)
    resolved = role_memory.resolve(entries, project["tracks"])
    reviewing = [t for t, info in resolved["matches"].items() if info["needs_review"]]
    return {"schema_version": role_memory.SCHEMA, "set_path": set_path,
            "remembered": {t: {k: v for k, v in info.items() if k != "entry"} for t, info in resolved["matches"].items()},
            "orphaned": [{"track_name": e.get("track_name"), "track_index": e.get("track_index"), "role": e["role"]}
                         for e in resolved["orphaned"]],
            "new_tracks": resolved["new_tracks"], "needs_review": reviewing,
            "message": "%d remembered, %d need review, %d no longer in the Set, %d new" % (
                len(resolved["matches"]), len(reviewing), len(resolved["orphaned"]), len(resolved["new_tracks"]))}


def save_role_memory(payload: dict[str, Any]) -> dict[str, Any]:
    """Remember confirmed roles ({track_id: role or null}) or forget them all ({"clear": true})."""
    if not isinstance(payload, dict) or set(payload) not in ({"roles"}, {"clear"}):
        raise ValueError("Role memory takes either roles or clear")
    with LOCK:
        state, project = _ready_state()
        set_path = project.get("set_path") or None
        if not set_path:
            raise ValueError("Save the Live Set first so its stem roles can be remembered")
        path = _role_memory_path(set_path)
        if payload.get("clear") is True:
            if path.exists():
                path.unlink()
            return role_memory_status()
        roles = payload["roles"]
        if not isinstance(roles, dict):
            raise ValueError("roles must map track ids to roles")
        entries = role_memory.merge(_role_memory_entries(set_path), project["tracks"], roles, role_maps.ROLES)
        _write(path, {"schema_version": role_memory.SCHEMA, "set_path": set_path, "updated_at": time.time(),
                      "entries": entries})
        return role_memory_status()


def _remembered_roles_for_planning(project: dict[str, Any]) -> dict[str, str | None]:
    """{track_id: role} (None = deliberately ignored) for tracks whose memory matched."""
    entries = _role_memory_entries(project.get("set_path"))
    return {track_id: info["role"] for track_id, info in role_memory.remembered_roles(entries, project["tracks"]).items()}


def active_track_roles() -> dict[str, Any]:
    state, project = _ready_state()
    record = role_maps.validate_active(_read(ROOT / "role-maps" / "active.json"), state, project)
    if record:
        return record
    return {"schema_version": role_maps.SCHEMA, "status": "reconfirmation_required",
            "active": False, "session_id": state["session_id"],
            "source_revision": project["revision"], "roles": {}}


def comparison_contract() -> dict[str, Any]:
    """Describe the future A/B record without claiming a render exists."""
    state, production = _ready_state()
    return {
        "schema_version": COMPARISON_SCHEMA,
        "source_revision": production["revision"],
        "session_id": state["session_id"],
        "status": "render_not_supported",
        "same_range_required": True,
        "before_render": None,
        "after_render": None,
        "measurements": None,
        "reason": "The current bridge has no verified render or audio-analysis primitive.",
    }


def _drum_pad_role(pad: dict[str, Any]) -> tuple[str, str]:
    """Role for one Drum Rack pad: from its name when that says something, else its note number."""
    found = song_sketch._match_role(str(pad.get("name") or "").lower())
    if found:
        role = found[0] if found[0] in DRUM_LANE_ROLES else "Percussion"
        return role, 'pad "%s"' % pad["name"]
    return _GM_DRUM_ROLES.get(int(pad["note"]), "Percussion"), "note %d" % int(pad["note"])


def drum_split_preview(track: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Lanes a split would create for this track, or None when there is nothing to split."""
    rack = track.get("drum_rack")
    if not isinstance(rack, dict) or not rack.get("pads"):
        return None
    lanes: dict[str, dict[str, Any]] = {}
    for pad in rack["pads"]:
        role, why = _drum_pad_role(pad)
        lane = lanes.setdefault(role, {"name": "%s · %s" % (track.get("name"), role), "role": role, "notes": [], "pads": []})
        lane["notes"].append(int(pad["note"]))
        lane["pads"].append({"note": int(pad["note"]), "name": pad.get("name") or "", "matched_by": why})
    ordered = [lanes[role] for role in DRUM_LANE_ROLES if role in lanes]
    return ordered if len(ordered) >= 2 else None


def split_lanes_of(track: dict[str, Any], all_tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tracks that are drum lanes split from ``track`` ("<name> · <role>")."""
    prefix = "%s · " % track.get("name")
    return [other for other in all_tracks if other is not track and str(other.get("name", "")).startswith(prefix)
            and str(other["name"])[len(prefix):] in DRUM_LANE_ROLES]


def create_drum_split_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Draft splitting one Drum Rack track into a lane per drum role; nothing reaches Live yet."""
    if not isinstance(payload, dict) or set(payload) != {"track_id"}:
        raise ValueError("Drum split takes track_id")
    with LOCK:
        _state, project = _ready_state()
        tracks = _tracks_by_id(project)
        track = tracks.get(payload["track_id"])
        if track is None:
            raise ValueError("That track is no longer in the Set; press Refresh")
        if not track.get("drum_rack"):
            raise ValueError("%s has no Drum Rack playing MIDI clips, so there is nothing to split" % track.get("name"))
        if split_lanes_of(track, project["tracks"]):
            raise ValueError("%s is already split into drum lanes. Undo that split first." % track.get("name"))
        lanes = drum_split_preview(track)
        if not lanes:
            raise ValueError("Every pad %s plays has the same role, so there is nothing to split" % track.get("name"))
        plan = create_plan({"intent": "Split %s into %d drum lanes" % (track.get("name"), len(lanes)),
                            "snapshot_name": "Before splitting %s" % track.get("name"),
                            "actions": [{"type": "split_drum_track", "track_id": track["id"],
                                         "lanes": [{k: lane[k] for k in ("name", "role", "notes")} for lane in lanes]}]})
        plan.update(workflow="drum_split", source_track_name=track.get("name"), lanes=lanes,
                    warnings=["Each lane is a copy of %s with its Drum Rack and clips, keeping only that role's notes. "
                              "The original is muted so nothing plays twice; its clips are not changed, and the scaffold "
                              "uses the lanes instead." % track.get("name")],
                    rollback_guarantee="Undo deletes only the lanes this split created, if you haven't edited them, and unmutes the original.")
        _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
        _append_operation("drum_split_drafted", plan["id"], {"lane_count": len(lanes)})
        return plan


def create_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a durable, reviewable plan without queueing a Live mutation."""
    with LOCK:
        if not isinstance(payload, dict) or set(payload) != {"intent", "snapshot_name", "actions"}:
            raise ValueError("Plan input must contain only intent, snapshot_name, and actions")
        intent = payload.get("intent")
        snapshot_name = payload.get("snapshot_name")
        if not isinstance(intent, str) or not intent.strip() or len(intent) > 500:
            raise ValueError("Plan intent is required and must be at most 500 characters")
        if not isinstance(snapshot_name, str) or not snapshot_name.strip() or len(snapshot_name) > 160:
            raise ValueError("Snapshot name is required and must be at most 160 characters")
        state, production = _ready_state()
        tracks = _tracks_by_id(production)
        actions = payload.get("actions")
        if not isinstance(actions, list) or not 1 <= len(actions) <= 20:
            raise ValueError("A production plan needs 1–20 actions")
        normalized_actions = [_validate_action(action, tracks) for action in actions]
        plan_id = str(uuid.uuid4())
        plan = {
            "schema_version": PLAN_SCHEMA,
            "id": plan_id,
            "status": "Draft",
            "created_at": time.time(),
            "intent": intent.strip(),
            "snapshot_name": snapshot_name.strip(),
            "session_id": state["session_id"],
            "source_revision": production["revision"],
            "actions": normalized_actions,
        }
        _write(ROOT / "plans" / (plan_id + ".json"), plan)
        _append_operation("plan_created", plan_id, {"action_count": len(normalized_actions), "workflow": "production"})
        return plan


def create_classic_house_template(payload: dict[str, Any]) -> dict[str, Any]:
    """Draft the one Phase-2 preset for a new, pristine Live Set only."""
    if not isinstance(payload, dict) or set(payload) != {"snapshot_name"}:
        raise ValueError("Template input must contain only snapshot_name")
    with LOCK:
        state, production = _ready_state()
        capabilities = production.get("template_capabilities", {})
        if capabilities.get("track_colours") is not True:
            raise ValueError("This Live build lacks a required deterministic template capability")
        if not production.get("is_pristine_default_set"):
            raise ValueError("Classic House template requires an untouched new default Live Set")
        layout_mode, warnings = song_sketch.layout_mode(capabilities.get("group_creation") is True)
        locator_range = capabilities.get("locator_range") is True
        if locator_range and capabilities.get("locators") is not True:
            raise ValueError("This Live build cannot create the requested deterministic locator range")
        warnings = list(warnings)
        if not locator_range:
            warnings.append("Arrangement locators were deferred: Ableton cannot create the full locator range until arrangement content establishes sufficient song length.")
        actions = []
        actions.append({"type": "apply_song_sketch_template", "preset_id": song_sketch.CLASSIC_HOUSE_CLUB_MIX_ID,
                        "layout_mode": layout_mode, "locator_range": locator_range})
        plan = create_plan({
            "intent": "Create Classic House · 124 BPM · Club Mix Song Sketch template",
            "snapshot_name": payload["snapshot_name"],
            "actions": actions,
        })
        preset = song_sketch.classic_house_preset()
        plan.update(layout_mode=layout_mode, warnings=warnings, locator_range=locator_range,
                    locator_definitions=copy.deepcopy(preset["locators"]),
                    locators_deferred=not locator_range,
                    intended_groups=preset["intended_groups"])
        _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
        _append_operation("template_drafted", plan["id"], {"preset_id": song_sketch.CLASSIC_HOUSE_CLUB_MIX_ID,
                                                             "layout_mode": layout_mode, "locator_range": locator_range,
                                                             "locators_deferred": not locator_range})
        return plan


def create_cleanup_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist a reviewable mapping without creating a plan or queue command."""
    if payload not in ({}, None):
        raise ValueError("Cleanup proposal input must be empty")
    with LOCK:
        state, production = _ready_state()
        active_roles = role_maps.validate_active(_read(ROOT / "role-maps" / "active.json"), state, production)
        proposal = song_sketch.cleanup_proposal(
            copy.deepcopy(production["tracks"]), proposal_id=str(uuid.uuid4()),
            session_id=state["session_id"], source_revision=production["revision"],
            confirmed_roles=active_roles,
        )
        proposal["created_at"] = time.time()
        _write(ROOT / "cleanup-proposals" / (proposal["id"] + ".json"), proposal)
        _append_operation("cleanup_proposed", proposal["id"], {"track_count": len(proposal["tracks"]), "workflow": "song_sketch"})
        return proposal


def _request_id(payload: dict[str, Any]) -> str:
    request_id = payload.get("request_id") if isinstance(payload, dict) else None
    try:
        return str(uuid.UUID(request_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("request_id must be a UUID so draft and selection retries are safe")


def create_house_arrangement_options(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist three review-only maps for the explicitly selected genre."""
    if not isinstance(payload, dict) or set(payload) not in ({"request_id"}, {"request_id", "genre"}):
        raise ValueError("Arrangement-options input requires request_id and optional genre")
    genre = payload.get("genre", "House")
    if genre not in arrangements.SUPPORTED_GENRES:
        raise ValueError("Choose a supported arrangement genre")
    with LOCK:
        request_id = _request_id(payload)
        previous = _read(ROOT / "arrangement-requests" / (request_id + ".json"))
        if previous:
            proposal = _read(ROOT / "arrangement-proposals" / (previous["proposal_id"] + ".json"))
            if proposal and proposal.get("genre") != genre:
                raise ValueError("Request ID was already used for a different genre")
            return proposal
        state, project = _ready_state()
        active_roles = role_maps.validate_active(_read(ROOT / "role-maps" / "active.json"), state, project)
        remembered = _remembered_roles_for_planning(project)
        # Precedence: explicit choice in this request > exact-revision confirmation > remembered for this Set > name heuristics.
        known = {**remembered, **((active_roles or {}).get("roles") or {})}
        options = arrangements.build_options(genre, state, project, {"roles": known} if known else active_roles)
        arrangements.validate_options(options)
        proposal_id = str(uuid.uuid4())
        proposal = {
            "schema_version": ARRANGEMENT_PLAN_SCHEMA,
            "id": proposal_id,
            "status": "Options",
            "created_at": time.time(),
            "session_id": state["session_id"],
            "source_revision": project["revision"],
            "request_id": request_id,
            **options,
        }
        _write(ROOT / "arrangement-proposals" / (proposal_id + ".json"), proposal)
        _write(ROOT / "arrangement-requests" / (request_id + ".json"), {"proposal_id": proposal_id})
        _append_operation("arrangement_options_drafted", proposal_id, {
            "request_id": request_id, "variant_ids": [item["id"] for item in proposal["variants"]],
            "workflow": "phase_3a_planning_only",
        })
        return proposal


def get_arrangement_proposal(proposal_id: str) -> dict[str, Any]:
    try:
        uuid.UUID(proposal_id)
    except (ValueError, TypeError):
        raise ValueError("Invalid arrangement proposal ID")
    proposal = _read(ROOT / "arrangement-proposals" / (proposal_id + ".json"))
    if not proposal:
        raise ValueError("Arrangement proposal not found")
    return proposal


def select_house_arrangement(payload: dict[str, Any]) -> dict[str, Any]:
    """Record explicit approval only; Phase 3A cannot produce execution actions."""
    required = {"proposal_id", "variant_id", "approved", "request_id"}
    allowed = required | {"phase_3b_benchmark"}
    if not isinstance(payload, dict) or (set(payload) != required and set(payload) != allowed):
        raise ValueError("Arrangement selection must contain proposal_id, variant_id, approved, request_id, and optional phase_3b_benchmark")
    if payload.get("approved") is not True:
        raise ValueError("Explicit approval is required before selecting an arrangement variant")
    arrangements.genre_for_variant(payload.get("variant_id"))
    with LOCK:
        request_id = _request_id(payload)
        previous = _read(ROOT / "arrangement-selection-requests" / (request_id + ".json"))
        if previous:
            return _read(ROOT / "arrangement-selections" / (previous["selection_id"] + ".json"))
        proposal = get_arrangement_proposal(payload["proposal_id"])
        state, project = _ready_state()
        if proposal["session_id"] != state["session_id"] or proposal["source_revision"] != project["revision"]:
            raise ValueError("Live project state changed; draft three new arrangement options before selecting")
        if payload["variant_id"] not in {item["id"] for item in proposal["variants"]}:
            raise ValueError("That variant does not belong to the selected genre proposal")
        selected = next(item for item in proposal["variants"] if item["id"] == payload["variant_id"])
        benchmark = payload.get("phase_3b_benchmark")
        if benchmark is not None:
            if proposal["genre"] != "House":
                raise ValueError("Phase 3B benchmark is available only for House")
            if not isinstance(benchmark, dict) or set(benchmark) != {"bpm", "total_bars"}:
                raise ValueError("phase_3b_benchmark must contain only bpm and total_bars")
            benchmark_bpm = _finite_number(benchmark["bpm"], "benchmark BPM", 40.0, 240.0)
            expected_bars = int(round(selected["target_duration_seconds"] * benchmark_bpm / 240.0))
            if benchmark.get("total_bars") != expected_bars:
                raise ValueError("phase_3b_benchmark bar total does not match the selected duration target at its BPM")
            benchmark = {"bpm": benchmark_bpm, "total_bars": expected_bars,
                         "purpose": "Primary Phase 3B implementation benchmark; it does not change the current Live Set."}
        selection_id = str(uuid.uuid4())
        selection = {
            "schema_version": ARRANGEMENT_PLAN_SCHEMA,
            "id": selection_id,
            "status": "Selected",
            "selected_at": time.time(),
            "request_id": request_id,
            "proposal_id": proposal["id"],
            "session_id": state["session_id"],
            "source_revision": project["revision"],
            "genre": proposal["genre"],
            "variant": copy.deepcopy(selected),
            "phase_3b_benchmark": benchmark,
            "role_inventory": copy.deepcopy(proposal["role_inventory"]),
            "assumptions": copy.deepcopy(proposal["assumptions"]),
            "execution_available": True,
            "next_step": "Choose verified Arrangement source clips, then review a copy-only Live placement plan.",
        }
        _write(ROOT / "arrangement-selections" / (selection_id + ".json"), selection)
        _write(ROOT / "arrangement-selection-requests" / (request_id + ".json"), {"selection_id": selection_id})
        _append_operation("arrangement_variant_selected", selection_id, {
            "proposal_id": proposal["id"], "variant_id": selected["id"], "request_id": request_id,
            "workflow": "phase_3a_planning_only",
        })
        return selection


def create_house_arrangement_execution_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Turn one explicitly selected Phase 3A Club map into a copy-only draft."""
    if isinstance(payload, dict) and payload.get("view") == "session":
        return _create_session_scene_plan(payload)
    if isinstance(payload, dict) and "sources" in payload:
        return _create_selected_arrangement_plan(payload)
    if not isinstance(payload, dict) or set(payload) != {"selection_id", "snapshot_name", "approved"}:
        raise ValueError("Arrangement execution input must contain selection_id, snapshot_name, and approved")
    if payload["approved"] is not True:
        raise ValueError("Explicit execution approval is required")
    with LOCK:
        try:
            uuid.UUID(payload["selection_id"])
        except (ValueError, TypeError):
            raise ValueError("Invalid arrangement selection ID")
        selection = _read(ROOT / "arrangement-selections" / (payload["selection_id"] + ".json"))
        if not selection or selection.get("status") != "Selected" or selection.get("variant", {}).get("id") != "club-version":
            raise ValueError("Select the Club version before creating its execution plan")
        state, project = _ready_state()
        if selection["session_id"] != state["session_id"] or selection["source_revision"] != project["revision"]:
            raise ValueError("Live project state changed; create a new arrangement proposal")
        if project.get("tempo") != 124.0 or project.get("metre") != [4, 4]:
            raise ValueError("Phase 3B Club execution requires a 124 BPM 4/4 Set")
        locator_readback = project.get("template_capabilities", {}).get("arrangement_locator_readback") is True
        sources = []
        for track in project["tracks"]:
            for clip in track.get("arrangement_clips", []):
                if (clip.get("start_beat") == 0.0 and clip.get("length") == 64.0 and
                        isinstance(clip.get("fingerprint"), str)):
                    sources.append((track["id"], clip))
        if len(sources) != 1:
            raise ValueError("Phase 3B requires exactly one fingerprinted 16-bar Arrangement source loop at beat 0")
        track_id, source = sources[0]
        # Nine complete 16-bar blocks: one original plus eight disjoint
        # copies.  No copy overlaps another or needs a partial final loop.
        destinations = (64.0, 128.0, 192.0, 256.0, 320.0, 384.0, 448.0, 512.0)
        action = {"type": "apply_arrangement_copies", "expected_end_beat": 576.0,
                  "copies": [{"source_track_id": track_id, "source_start_beat": 0.0,
                              "source_fingerprint": source["fingerprint"], "destination_beat": destination}
                             for destination in destinations],
                  "locator_definitions": [{"time": item["time"], "name": item["name"]}
                                          for item in selection["variant"]["intended_locators"]],
                  "locators": ([{"time": item["time"], "name": item["name"]}
                                for item in selection["variant"]["intended_locators"]] if locator_readback else []),
                  "locators_deferred": not locator_readback}
        plan = create_plan({"intent": "Execute approved 144-bar Club arrangement by copying the existing 16-bar source loop",
                            "snapshot_name": payload["snapshot_name"], "actions": [action]})
        plan.update(arrangement_selection_id=selection["id"], variant=copy.deepcopy(selection["variant"]),
                    execution_approval=True,
                    locator_definitions=copy.deepcopy(action["locator_definitions"]),
                    locators_deferred=not locator_readback,
                    warnings=["The original plus eight copied 16-bar loops form nine non-overlapping blocks ending exactly at bar 144."] +
                             ([] if locator_readback else ["Arrangement locators were not created because this Ableton Live Remote Script cannot read them back deterministically."]),
                    rollback_guarantee="Rollback deletes only the copies and locators recorded by this execution.")
        _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
        _append_operation("arrangement_execution_drafted", plan["id"], {"selection_id": selection["id"], "copy_count": len(destinations)})
        return plan


def _create_session_scene_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Draft seven new Session scenes using only selected existing clips."""
    if not isinstance(payload, dict) or set(payload) != {"selection_id", "snapshot_name", "approved", "sources", "view"} or payload.get("approved") is not True:
        raise ValueError("Choose Session clips and approve the scene plan")
    if not isinstance(payload.get("sources"), list) or not 1 <= len(payload["sources"]) <= 12:
        raise ValueError("Choose between one and twelve Session source clips")
    with LOCK:
        selection = _read(ROOT / "arrangement-selections" / (str(payload["selection_id"]) + ".json"))
        if not selection or selection.get("status") != "Selected":
            raise ValueError("Select an arrangement shape first")
        state, project = _ready_state()
        if selection["session_id"] != state["session_id"] or selection["source_revision"] != project["revision"]:
            raise ValueError("Live Set changed; refresh the Session scene plan")
        if "session_scene_v1" not in state.get("capabilities", []):
            raise ValueError("Restart Ableton Live with the updated Vibelton bridge to build Session scenes")
        scene_names = project.get("scene_names")
        if not isinstance(scene_names, list):
            raise ValueError("Live did not report its Session scenes")
        tracks = _tracks_by_id(project)
        variant = selection["variant"]
        roles = {role for section in variant["sections"] for role in section["active_track_roles"]}
        chosen = {}
        for source in payload["sources"]:
            if not isinstance(source, dict) or set(source) != {"role", "track_id", "source_scene_index"}:
                raise ValueError("Invalid Session source choice")
            role, track_id, index = source["role"], source["track_id"], source["source_scene_index"]
            if role not in roles or role in chosen or track_id not in tracks or type(index) is not int:
                raise ValueError("Choose one valid Session source per role")
            matches = [clip for clip in tracks[track_id].get("session_clips", []) if clip["scene_index"] == index]
            if len(matches) != 1 or not isinstance(matches[0].get("fingerprint"), str):
                raise ValueError("Selected Session clip is missing or unreadable")
            chosen[role] = (track_id, matches[0])
        if len({item[0] for item in chosen.values()}) != len(chosen):
            raise ValueError("Choose a different Live track for each role")
        scenes, coverage, gaps = [], [], []
        for section in variant["sections"]:
            copies = []
            for role in section["active_track_roles"]:
                if role in chosen:
                    track_id, clip = chosen[role]
                    copies.append({"track_id": track_id, "source_scene_index": clip["scene_index"],
                                   "source_fingerprint": clip["fingerprint"]})
                    coverage.append({"section": section["name"], "role": role,
                                     "track_name": tracks[track_id]["name"], "source_name": clip["name"],
                                     "source_scene": clip["scene_index"] + 1})
            if not copies:
                gaps.append("%s: no selected clips for this scene" % section["name"])
            scenes.append({"name": "Vibelton · %s · %d bars" % (section["name"], section["bar_count"]),
                           "bar_count": section["bar_count"], "copies": copies})
        action = {"type": "apply_session_scene_map", "source_scene_count": len(scene_names), "scenes": scenes}
        plan = create_plan({"intent": "%s · %s as new Session scenes" % (selection.get("genre", "Arrangement"), variant["name"]),
                            "snapshot_name": payload["snapshot_name"], "actions": [action]})
        plan.update(arrangement_selection_id=selection["id"], variant=copy.deepcopy(variant),
                    execution_approval=True, view="session", source_coverage=coverage, gaps=gaps,
                    first_new_scene=len(scene_names) + 1,
                    warnings=["Seven new scenes are appended after the existing Session scenes; original clips stay in place.",
                              "Scene labels show intended bars. Live does not advance scenes after that duration; launch the next scene when ready."],
                    rollback_guarantee="Rollback deletes only the new scenes recorded by this execution.")
        _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
        _append_operation("session_scene_plan_drafted", plan["id"], {"selection_id": selection["id"]})
        return plan


def _layer_sections(sections: list[dict[str, Any]], chosen: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, str]]:
    """Which sections each source track plays in.

    The first track of a role plays wherever the role is active. Each further track of the same
    role joins only from a higher energy level, so same-role stems build up towards the peak, where
    all of them play. The second result gives each track's "k of n" for the plan summary."""
    by_role: dict[str, list[str]] = {}
    for track_id, (role, _clip, _length) in chosen.items():
        by_role.setdefault(role, []).append(track_id)
    plays: dict[str, set[str]] = {}
    layers: dict[str, str] = {}
    for role, track_ids in by_role.items():
        energies = [float(sec.get("energy_level", 0)) for sec in sections if role in sec["active_track_roles"]]
        low, high = (min(energies), max(energies)) if energies else (0.0, 0.0)
        for k, track_id in enumerate(track_ids):
            threshold = low + (high - low) * k / len(track_ids)
            plays[track_id] = {sec["name"] for sec in sections if role in sec["active_track_roles"]
                               and float(sec.get("energy_level", 0)) >= threshold - 0.00001}
            layers[track_id] = "%d of %d" % (k + 1, len(track_ids))
    return plays, layers


def _stem_boundaries(sections: list[dict[str, Any]], chosen: dict[str, Any], copies: list[dict[str, Any]],
                     lengths: dict[str, float], tracks: dict[str, dict[str, Any]], start_beat: float,
                     only_section: str | None, plays: dict[str, set[str]]) -> list[dict[str, Any]]:
    """Every point where a stem enters or exits, with the actual clip edge Live will get.

    Raises if any placed clip edge is not on a bar line: a mid-bar cut is never acceptable.
    """
    found = []
    for before, after in zip(sections, sections[1:]):
        if only_section is not None and only_section not in (before["name"], after["name"]):
            continue
        beat = start_beat + 4.0 * after["start_bar"]
        for track_id, (role, _clip, length) in chosen.items():
            was, now = before["name"] in plays[track_id], after["name"] in plays[track_id]
            if was == now:
                continue
            mine = [c for c in copies if c["source_track_id"] == track_id]
            if now:
                edge = beat if any(abs(c["destination_beat"] - beat) < 0.00001 for c in mine) else None
            else:
                ends = [c["destination_beat"] + length for c in mine if c["destination_beat"] < beat - 0.00001]
                edge = max(ends) if ends else None
            if edge is not None and abs(edge / 4.0 - round(edge / 4.0)) > 0.00001:
                raise ValueError("A clip edge would fall inside a bar; refusing to plan a mid-bar cut")
            found.append({"bar": int(beat / 4) + 1, "from": before["name"], "to": after["name"],
                          "track": tracks[track_id]["name"], "role": role,
                          "event": "enter" if now else "exit",
                          "audio": tracks[track_id].get("type") == "audio",
                          "edge_beat": edge, "on_bar_line": True, "handling": "bar_line"})
    return found


def _boundary_summary(boundaries: list[dict[str, Any]]) -> str:
    enters = sum(1 for item in boundaries if item["event"] == "enter")
    exits = len(boundaries) - enters
    return "%d stem entries and %d exits across section boundaries; every clip edge lands on a bar line." % (enters, exits)


MARKER_ALIASES = {"main_section": "DROP", "outro": "OUTRO"}


def marker_name(section: dict[str, Any]) -> str:
    """Live locator label for a section: INTRO, GROOVE, BREAKDOWN, DROP, OUTRO, …"""
    return MARKER_ALIASES.get(section.get("id"), str(section["name"]).upper())


def _create_selected_arrangement_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Copy confirmed, fingerprinted source clips into the selected bar map.

    Sources are Arrangement clips (``source_start_beat``) or, for a Set that has only Session
    loops, Session clips (``source_scene_index``); both are placed into the Arrangement."""
    base_keys = {"selection_id", "snapshot_name", "approved", "sources"}
    if set(payload) not in (base_keys, base_keys | {"section"}) or payload.get("approved") is not True:
        raise ValueError("Choose source clips and approve the arrangement plan")
    only_section = payload.get("section")
    if only_section is not None and (not isinstance(only_section, str) or not only_section.strip()):
        raise ValueError("section must be a section name")
    if not isinstance(payload["sources"], list) or not 1 <= len(payload["sources"]) <= MAX_SCAFFOLD_SOURCES:
        raise ValueError("Choose between one and %d source clips" % MAX_SCAFFOLD_SOURCES)
    with LOCK:
        selection = _read(ROOT / "arrangement-selections" / (str(payload["selection_id"]) + ".json"))
        if not selection or selection.get("status") != "Selected":
            raise ValueError("Select an arrangement shape first")
        state, project = _ready_state()
        if selection["session_id"] != state["session_id"] or selection["source_revision"] != project["revision"]:
            raise ValueError("Live Set changed; refresh the arrangement options and source clips")
        if project.get("metre") != [4, 4]:
            raise ValueError("Arrangement execution currently requires a 4/4 Live Set")
        variant = selection["variant"]
        roles = {role for section in variant["sections"] for role in section["active_track_roles"]}
        tracks = _tracks_by_id(project)
        chosen = {}
        from_session = all(isinstance(source, dict) and "source_scene_index" in source for source in payload["sources"])
        for source in payload["sources"]:
            expected_keys = {"role", "track_id", "source_scene_index" if from_session else "source_start_beat"}
            if not isinstance(source, dict) or set(source) != expected_keys:
                raise ValueError("Invalid source clip choice")
            role, track_id = source["role"], source["track_id"]
            if role not in roles or track_id in chosen or track_id not in tracks:
                raise ValueError("Choose one valid source clip per track")
            if from_session:
                index = source["source_scene_index"]
                matches = [clip for clip in tracks[track_id].get("session_clips", []) if clip.get("scene_index") == index] if type(index) is int else []
                if len(matches) != 1:
                    raise ValueError("Selected Session clip is missing or unreadable")
                clip = matches[0]
                length = float(clip.get("length") or 0)
                if (not isinstance(clip.get("fingerprint"), str) or len(clip["fingerprint"]) != 64 or
                        not 4 <= length <= 64 or abs(length / 4 - round(length / 4)) > 0.00001):
                    raise ValueError("Choose a fingerprinted, whole-bar Session clip of at most 16 bars")
                chosen[track_id] = (role, clip, length)
                continue
            start = _finite_number(source["source_start_beat"], "source clip start", 0, 3600)
            matches = [clip for clip in tracks[track_id].get("arrangement_clips", [])
                       if abs(float(clip.get("start_beat", -1)) - start) < 0.00001]
            if len(matches) != 1:
                raise ValueError("Selected source clip is missing or ambiguous")
            clip = matches[0]
            length = float(clip.get("end_beat", 0)) - start
            if (not isinstance(clip.get("fingerprint"), str) or len(clip["fingerprint"]) != 64 or
                    not 4 <= length <= 64 or abs(length / 4 - round(length / 4)) > 0.00001 or
                    abs(float(clip.get("length", -1)) - length) > 0.00001):
                raise ValueError("Choose a fingerprinted, whole-bar Arrangement clip of at most 16 bars")
            chosen[track_id] = (role, clip, length)
        plays, layers = _layer_sections(variant["sections"], chosen)
        start_beat = float(math.ceil(float(project.get("arrangement_end", 0)) / 64) * 64)
        if only_section is not None:
            match = [sec for sec in variant["sections"] if sec["name"].lower() == only_section.strip().lower()]
            if not match:
                raise ValueError("Unknown section '%s'. Sections: %s" % (only_section, ", ".join(sec["name"] for sec in variant["sections"])))
            only_section = match[0]["name"]
            # A section lands exactly where the full scaffold would put it: reuse this variant's base bar.
            reused = _active_scaffold_base(project.get("set_path"), selection.get("genre"), variant.get("id"))
            if reused is not None:
                start_beat = reused
        copies, coverage, gaps, section_gaps = [], [], [], []
        for section in variant["sections"]:
            if only_section is not None and section["name"] != only_section:
                continue
            section_start = start_beat + 4 * section["start_bar"]
            section_end = start_beat + 4 * section["end_bar"]
            active = [track_id for track_id in chosen if section["name"] in plays[track_id]]
            unfilled: dict[str, int] = {}
            placed_roles = 0
            for track_id in active:
                role, clip, length = chosen[track_id]
                cursor = section_start
                while cursor + length <= section_end + 0.00001:
                    item = {"source_track_id": track_id, "source_fingerprint": clip["fingerprint"], "destination_beat": cursor}
                    if from_session:
                        item["source_scene_index"] = clip["scene_index"]
                    else:
                        item["source_start_beat"] = float(clip["start_beat"])
                    copies.append(item)
                    cursor += length
                coverage.append({"section": section["name"], "role": role, "track_name": tracks[track_id]["name"],
                                 "source_name": clip.get("name"),
                                 "source_bar": None if from_session else int(clip["start_beat"] / 4) + 1,
                                 "source_scene": clip["scene_index"] + 1 if from_session else None,
                                 "destination_bar": int(section_start / 4) + 1, "placed_bars": int((cursor - section_start) / 4),
                                 "layer": layers[track_id]})
                if cursor > section_start + 0.00001:
                    placed_roles += 1
                if cursor < section_end - 0.00001:
                    missing = int((section_end - cursor) / 4)
                    unfilled[role] = max(unfilled.get(role, 0), missing)
                    gaps.append("%s: %s (%s) has %d unfilled bars" % (section["name"], role, tracks[track_id]["name"], missing))
            if not active:
                gaps.append("%s: no chosen source matches its suggested roles" % section["name"])
            section_bars = int(section["end_bar"] - section["start_bar"])
            if unfilled or not active:
                section_gaps.append({"section": section["name"], "section_bars": section_bars,
                                     "max_unfilled_bars": max(unfilled.values()) if unfilled else section_bars,
                                     "empty": placed_roles == 0,
                                     "roles": [{"role": r, "unfilled_bars": n} for r, n in unfilled.items()]})
        if not copies:
            raise ValueError("The chosen clips do not fit %s; choose shorter whole-bar clips" % (
                "section " + only_section if only_section else "any section"))
        if only_section is not None:
            lengths = {track_id: length for track_id, (_role, _clip, length) in chosen.items()}
            for item in copies:
                span = (item["destination_beat"], item["destination_beat"] + lengths[item["source_track_id"]])
                busy = [c for c in tracks[item["source_track_id"]].get("arrangement_clips", [])
                        if float(c["start_beat"]) < span[1] - 0.00001 and float(c["end_beat"]) > span[0] + 0.00001]
                if busy:
                    raise ValueError("Section %s already has clips on %s where it would be placed. Undo that section first." % (
                        only_section, tracks[item["source_track_id"]]["name"]))
        if len(copies) > 400:
            raise ValueError("This draft needs over 400 copies; choose longer source clips")
        lengths_by_track = {track_id: length for track_id, (_role, _clip, length) in chosen.items()}
        actual_end = max(item["destination_beat"] + lengths_by_track[item["source_track_id"]] for item in copies)
        boundaries = _stem_boundaries(variant["sections"], chosen, copies, lengths_by_track, tracks, start_beat, only_section, plays)
        locators = [{"time": start_beat + 4 * section["start_bar"], "name": marker_name(section)}
                    for section in variant["sections"]]
        # Native cues are created only if this Live build proved exact position/name readback (probe_locators).
        # The Session-to-Arrangement bridge action has no marker support.
        locators_created = not from_session and bool((project.get("template_capabilities") or {}).get("arrangement_locator_readback"))
        section_markers = ([locators[[sec["name"] for sec in variant["sections"]].index(only_section)]]
                           if only_section is not None else locators)
        outro_warning = None
        if only_section is None and actual_end < locators[-1]["time"]:
            # Reported, not fatal: no source fits the final section whole, and clips are never trimmed.
            final = variant["sections"][-1]["name"]
            outro_warning = ("No source loop fits %s without being cut, so it stays empty. The arrangement ends at bar %d."
                             % (final, int(actual_end / 4)))
            gaps.append("%s: no loop short enough to fit" % final)
        if actual_end > MAX_ARRANGEMENT_BEAT:
            raise ValueError("The Arrangement is full: the Set already runs to bar %d, and this scaffold would end at bar %d, past Vibelton's %d-bar limit"
                             % (math.ceil(float(project.get("arrangement_end", 0)) / 4), math.ceil(actual_end / 4), MAX_ARRANGEMENT_BEAT // 4))
        # The bridge checks the Set's overall end afterwards; a middle section must not lower it.
        expected_end = max(actual_end, float(project.get("arrangement_end", 0))) if only_section is not None else actual_end
        if from_session:
            action = {"type": "apply_session_to_arrangement_copies", "expected_end_beat": expected_end,
                      "copies": [{"track_id": item["source_track_id"], "source_scene_index": item["source_scene_index"],
                                  "source_fingerprint": item["source_fingerprint"], "destination_beat": item["destination_beat"]}
                                 for item in copies]}
        else:
            action = {"type": "apply_arrangement_copies", "copies": copies, "expected_end_beat": expected_end,
                      "locators": section_markers if locators_created else [], "locator_definitions": locators,
                      "locators_deferred": not locators_created}
        plan = create_plan({"intent": "%s · %s in Live" % (selection.get("genre", "Arrangement"), variant["name"]),
                            "snapshot_name": payload["snapshot_name"], "actions": [action]})
        plan.update(arrangement_selection_id=selection["id"], variant=copy.deepcopy(variant),
                    execution_approval=True, start_bar=int(start_beat / 4) + 1,
                    planned_end_bar=int(start_beat / 4) + variant["total_bars"],
                    actual_end_bar=int(actual_end / 4), source_coverage=coverage,
                    gaps=gaps, section_gaps=section_gaps, locator_definitions=locators, locators_deferred=not locators_created,
                    source_view="session" if from_session else "arrangement",
                    warnings=["Existing Arrangement clips and locators stay in place. New copies begin after the current material."]
                             + (["Your Session loops are copied into the Arrangement; the Session clips stay where they are."] if from_session else []) + [
                              ("Section markers will be created in Live and removed again by Undo." if locators_created else
                               "Section markers are shown here but are not created in Live (this Live build has not proven marker readback)."),
                              "Arrangement track automation is not copied or extended by this scaffold."],
                    rollback_guarantee="Rollback removes only copies recorded by this execution.",
                    scaffold_scope={"genre": selection.get("genre"), "variant_id": variant.get("id"),
                                    "section": only_section, "base_beat": start_beat},
                    phrase_bars=variant.get("phrase_bars"), boundaries=boundaries,
                    boundary_summary=_boundary_summary(boundaries))
        if outro_warning:
            plan["warnings"].append(outro_warning)
        if any(item["audio"] for item in boundaries):
            plan["warnings"].append(
                "Audio stems start or stop at %d boundaries. Clip edges land on bar lines, but this bridge does not "
                "apply clip fades; listen to those cuts for clicks." % sum(1 for item in boundaries if item["audio"]))
        _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
        _append_operation("arrangement_execution_drafted", plan["id"],
                          {"selection_id": selection["id"], "copy_count": len(copies)})
        return plan


def get_plan(plan_id: str) -> dict[str, Any]:
    try:
        uuid.UUID(plan_id)
    except (ValueError, TypeError):
        raise ValueError("Invalid production plan ID")
    plan = _read(ROOT / "plans" / (plan_id + ".json"))
    if not plan:
        raise ValueError("Production plan not found")
    return plan


def _snapshot_for_plan(plan: dict[str, Any], production: dict[str, Any]) -> dict[str, Any]:
    tracks = _tracks_by_id(production)
    before: list[dict[str, Any]] = []
    inverse_actions: list[dict[str, Any]] = []
    for action in plan["actions"]:
        if action["type"] == "probe_arrangement_locators":
            before.append({"locator_probe": True})
            continue
        if action["type"] == "apply_session_scene_map":
            before.append({"session": {"scene_names": copy.deepcopy(production.get("scene_names", [])),
                                       "tracks": copy.deepcopy(production["tracks"])}})
            inverse_actions.append({"type": "rollback_session_scene_map", "source_scene_count": action["source_scene_count"],
                                    "created_scenes": [],
                                    "expected_post_rollback_observable_revision": _observable_rollback_revision(production)})
            continue
        if action["type"] == "rollback_session_scene_map":
            before.append({"session_rollback": True})
            continue
        if action["type"] == "split_drum_track":
            before.append({"drum_split": {"track_id": action["track_id"], "tracks": copy.deepcopy(production["tracks"])}})
            inverse_actions.append({"type": "rollback_split_drum_track", "created_tracks": [],
                                    "expected_post_rollback_observable_revision": _observable_rollback_revision(production),
                                    "source_track_id": action["track_id"], "unmute_source": False})
            continue
        if action["type"] == "rollback_split_drum_track":
            before.append({"drum_split_rollback": True})
            continue
        if action["type"] == "apply_arrangement_copies":
            before.append({"arrangement": {"tracks": copy.deepcopy(production["tracks"]),
                                            "locators": copy.deepcopy(production.get("locators", [])),
                                            "revision": production["revision"],
                                            **({"is_pristine_default_set": production["is_pristine_default_set"]}
                                               if "is_pristine_default_set" in production else {})}})
            inverse_actions.append({"type": "rollback_arrangement_copies", "copies": copy.deepcopy(action["copies"]),
                                    "locators": copy.deepcopy(action["locators"]),
                                    "expected_post_rollback_observable_revision": _observable_rollback_revision(production)})
            continue
        if action["type"] == "rollback_arrangement_copies":
            before.append({"arrangement_rollback": True})
            continue
        if action["type"] == "apply_session_to_arrangement_copies":
            before.append({"session_to_arrangement": {"tracks": copy.deepcopy(production["tracks"]),
                                                      "revision": production["revision"],
                                                      **({"is_pristine_default_set": production["is_pristine_default_set"]}
                                                         if "is_pristine_default_set" in production else {})}})
            inverse_actions.append({"type": "rollback_session_to_arrangement_copies",
                                    "copies": copy.deepcopy(action["copies"]),
                                    "expected_post_rollback_observable_revision": _observable_rollback_revision(production)})
            continue
        if action["type"] == "rollback_session_to_arrangement_copies":
            before.append({"session_to_arrangement_rollback": True})
            continue
        if action["type"] == "apply_song_sketch_template":
            before.append({"template": {"tempo": production["tempo"], "metre": production["metre"],
                                        "track_count": len(production["tracks"]),
                                        "locators": copy.deepcopy(production.get("locators", []))}})
            continue
        if action["type"] == "rollback_song_sketch_template":
            before.append({"template_rollback": True})
            continue
        if action["type"] == "set_device_parameter":
            track = tracks[action["target_track_id"]]
            dev_idx = action["device_index"]
            param_idx = action["parameter_index"]
            dev = track["devices"][dev_idx] if isinstance(track.get("devices"), list) and dev_idx < len(track["devices"]) else {}
            params = dev.get("parameters") if isinstance(dev, dict) else None
            orig_val = 0.0
            if isinstance(params, list) and param_idx < len(params) and isinstance(params[param_idx], dict):
                orig_val = float(params[param_idx].get("value", 0.0))
            inv = {
                "type": "set_device_parameter",
                "target_track_id": action["target_track_id"],
                "device_index": dev_idx,
                "parameter_index": param_idx,
                "value": orig_val,
            }
            before.append(dict(inv))
            inverse_actions.append(dict(inv))
            continue
        track = tracks[action["target_track_id"]]
        mixer = track["mixer"]
        mixer_sends = mixer.get("sends") if isinstance(mixer.get("sends"), list) else []
        values: dict[str, Any] = {}
        for key in action["values"]:
            if key in ("volume", "pan"):
                values[key] = float(mixer[key])
            elif key == "send_0":
                values["send_0"] = float(mixer_sends[0])
            elif key == "send_1":
                values["send_1"] = float(mixer_sends[1])
            elif key == "sends":
                values["sends"] = [float(mixer_sends[i]) for i in range(len(action["values"]["sends"]))]
        before.append({"target_track_id": action["target_track_id"], "values": copy.deepcopy(values)})
        inverse_actions.append({"type": "set_track_mixer", "target_track_id": action["target_track_id"], "values": copy.deepcopy(values)})
    snapshot_id = str(uuid.uuid4())
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA,
        "id": snapshot_id,
        "name": plan["snapshot_name"],
        "created_at": time.time(),
        "source_revision": plan["source_revision"],
        "session_id": plan["session_id"],
        "plan_id": plan["id"],
        "set_path": production.get("set_path") or None,
        "before": before,
        "inverse_actions": inverse_actions,
    }
    _write(ROOT / "snapshots" / (snapshot_id + ".json"), snapshot)
    return snapshot


def _queue_job(plan: dict[str, Any], snapshot: dict[str, Any], state: dict[str, Any], production: dict[str, Any], *, rollback_of: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    action = {
        "type": "production_apply",
        "job_id": job_id,
        "session_id": state["session_id"],
        "source_revision": production["revision"],
        "actions": plan["actions"],
    }
    job = {
        "id": job_id,
        "status": "Queued",
        "created_at": time.time(),
        "plan_id": plan["id"],
        "snapshot_id": snapshot["id"],
        "session_id": state["session_id"],
        "source_revision": production["revision"],
        "set_path": production.get("set_path") or None,
        "rollback_of": rollback_of,
    }
    if extra:
        job.update(extra)
    _write(ROOT / "jobs" / (job_id + ".json"), job)
    try:
        command = queue.enqueue([action], source="production")
        job["command_id"] = command["id"]
        _write(ROOT / "jobs" / (job_id + ".json"), job)
    except Exception:
        job.update(status="Failed", error="Queue submission uncertain; inspect bridge results before retrying.")
        _write(ROOT / "jobs" / (job_id + ".json"), job)
        raise
    _append_operation("rollback_queued" if rollback_of else "plan_queued", job_id, {"plan_id": plan["id"], "action_count": len(plan["actions"])})
    return job


def execute(payload: dict[str, Any]) -> dict[str, Any]:
    """Queue a draft exactly once after an explicit working-copy confirmation."""
    with LOCK:
        if not isinstance(payload, dict) or set(payload) != {"plan_id", "working_copy_confirmed"}:
            raise ValueError("Execution input must contain only plan_id and working_copy_confirmed")
        if payload.get("working_copy_confirmed") is not True:
            raise ValueError("Save a working copy of your Live Set, then confirm it before applying a production plan")
        plan = get_plan(payload.get("plan_id"))
        if plan.get("status") != "Draft":
            raise ValueError("This production plan has already been submitted")
        state, production = _ready_state()
        working_copy.require(production.get("set_path"))
        if plan["session_id"] != state["session_id"] or plan["source_revision"] != production["revision"]:
            raise ValueError("Live project state changed; create a new production plan")
        if plan.get("start_bar") and "arrangement_copy_v2" not in state.get("capabilities", []):
            raise ValueError("Restart Ableton Live with the updated Vibelton Remote Script before applying this arrangement")
        if plan.get("view") == "session" and "session_scene_v1" not in state.get("capabilities", []):
            raise ValueError("Restart Ableton Live with the updated Vibelton bridge before building Session scenes")
        snapshot = _snapshot_for_plan(plan, production)
        job = _queue_job(plan, snapshot, state, production)
        plan["status"] = "Queued"
        _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
        _register_scaffold_job(plan, job, production)
        return job


def _placement_records(job: dict[str, Any], persist: bool = True) -> list[dict[str, Any]]:
    """Clips a scaffold job actually created, as stable on-disk records."""
    path = ROOT / "placements" / (job["id"] + ".json")
    stored = _read(path)
    if stored is not None:
        removed = set(stored.get("removed", []))
        return [r for r in stored["records"] if r.get("key") not in removed]
    copies = (job.get("execution") or {}).get("created_copies")
    if not copies or job.get("rollback_of"):
        return []
    snapshot = _read(ROOT / "snapshots" / (job["snapshot_id"] + ".json")) or {}
    before = next((item["arrangement"] for item in snapshot.get("before", []) if "arrangement" in item), None)
    from_session = before is None
    if from_session:
        before = next((item["session_to_arrangement"] for item in snapshot.get("before", [])
                       if "session_to_arrangement" in item), None)
    if before is None:
        return []
    plan = _read(ROOT / "plans" / (job["plan_id"] + ".json")) or {}
    base = (int(plan.get("start_bar", 1)) - 1) * 4.0
    sections = [{"name": sec["name"], "start_beat": base + 4.0 * sec["start_bar"], "end_beat": base + 4.0 * sec["end_bar"]}
                for sec in (plan.get("variant") or {}).get("sections", [])]
    build = rollback_safety.build_session_records if from_session else rollback_safety.build_records
    records = build(copies, before["tracks"], snapshot.get("set_path") or job.get("set_path"), sections)
    if persist and job.get("status") in {"Applied", "Partial failure", "Failed"}:
        _write(path, {"job_id": job["id"], "plan_id": job["plan_id"], "records": records})
        _supersede_older_records(job["id"], records)
    return records


def _supersede_older_records(job_id: str, records: list[dict[str, Any]]) -> None:
    """A clip now at a spot an older job once filled (and you since moved away) belongs to the newer job.

    Without this, rolling back the older job would delete the newer job's identical clip."""
    def spot(record: dict[str, Any]) -> tuple[Any, float, str]:
        # By track name: Live regenerates track ids when a Set is reopened.
        return (record.get("track_name") or record.get("track_id"), float(record["destination_beat"]), record["source_fingerprint"])

    spots = {spot(r) for r in records if r.get("key")}
    folder = ROOT / "placements"
    for other in folder.glob("*.json") if spots and folder.exists() else []:
        if other.stem == job_id:
            continue
        stored = _read(other)
        if not stored:
            continue
        clash = [r["key"] for r in stored.get("records", []) if r.get("key") and spot(r) in spots and r["key"] not in stored.get("removed", [])]
        if clash:
            stored["removed"] = sorted(set(stored.get("removed", [])) | set(clash))
            _write(other, stored)


def _session_path(set_path: str | None, genre: str | None, variant_id: str | None) -> Path:
    key = hashlib.sha256(f"{set_path}|{genre}|{variant_id}".encode()).hexdigest()[:32]
    return ROOT / "scaffold-sessions" / (key + ".json")


def _session_jobs(set_path: str | None, genre: str | None, variant_id: str | None) -> list[dict[str, Any]]:
    record = _read(_session_path(set_path, genre, variant_id)) or {}
    return record.get("jobs", [])


def _active_scaffold_base(set_path: str | None, genre: str | None, variant_id: str | None) -> float | None:
    """Base beat of the newest scaffold of this variant that still has clips in the Set."""
    for entry in reversed(_session_jobs(set_path, genre, variant_id)):
        job = _read(ROOT / "jobs" / (entry["job_id"] + ".json"))
        if not job:
            continue
        job = job_status(entry["job_id"])
        if job["status"] in {"Applied", "Partial failure"} and _placement_records(job, persist=False):
            return float(entry["base_beat"])
    return None


def _register_scaffold_job(plan: dict[str, Any], job: dict[str, Any], production: dict[str, Any]) -> None:
    scope = plan.get("scaffold_scope")
    if not scope:
        return
    path = _session_path(production.get("set_path"), scope["genre"], scope["variant_id"])
    record = _read(path) or {"set_path": production.get("set_path"), "genre": scope["genre"],
                             "variant_id": scope["variant_id"], "jobs": []}
    record["jobs"].append({"job_id": job["id"], "base_beat": scope["base_beat"], "section": scope.get("section")})
    _write(path, record)


def _job_for_section(set_path: str | None, genre: str | None, variant_id: str | None, section: str) -> str:
    """The newest scaffold job whose clips for ``section`` are still in the Set.

    Older scaffolds of the same variant may still sit further back in the arrangement; the section the panel
    shows (and re-scaffolds) is always the newest one, so that is the one a section Undo removes."""
    production = _ready_state()[1]
    for entry in reversed(_session_jobs(set_path, genre, variant_id)):
        job = _read(ROOT / "jobs" / (entry["job_id"] + ".json"))
        if not job:
            continue
        job = job_status(entry["job_id"])
        records = [r for r in _placement_records(job, persist=False) if (r.get("section") or "").lower() == section.lower()]
        if not records:
            continue
        verdict = rollback_safety.classify(records, production)
        present = [item for item in verdict["skipped"] if item["reason"] not in ("moved_or_deleted", "track_missing")]
        if verdict["removable"] or present:
            return job["id"]
    raise ValueError("No scaffolded clips are recorded for section '%s'" % section)


def scaffold_sections(genre: str, variant_id: str) -> dict[str, Any]:
    """Which sections of this variant currently have Vibelton clips in the open Set (read-only)."""
    state, production = _ready_state()
    sections: dict[str, dict[str, Any]] = {}
    for entry in _session_jobs(production.get("set_path"), genre, variant_id):
        job = _read(ROOT / "jobs" / (entry["job_id"] + ".json"))
        if not job:
            continue
        job = job_status(entry["job_id"])
        records = _placement_records(job, persist=False)
        verdict = rollback_safety.classify(records, production)
        present = [item["record"] for item in verdict["skipped"] if item["reason"] not in ("moved_or_deleted", "track_missing")]
        for record in verdict["removable"] + present:
            name = record.get("section")
            if name:
                info = sections.setdefault(name, {"clips": 0, "job_id": job["id"]})
                info["clips"] += 1
    return {"genre": genre, "variant_id": variant_id, "sections": sections}


def _mark_removed(original_job_id: str, keys: list[str], locators: list[dict[str, Any]] | None = None) -> None:
    """Remember clips/cues a rollback deleted so later rollbacks don't report them as missing."""
    path = ROOT / "placements" / (original_job_id + ".json")
    stored = _read(path)
    if stored is not None and (keys or locators):
        stored["removed"] = sorted(set(stored.get("removed", [])) | set(keys))
        known = stored.get("removed_locators", [])
        stored["removed_locators"] = known + [l for l in (locators or []) if l not in known]
        _write(path, stored)


def _remaining_locators(job: dict[str, Any]) -> list[dict[str, Any]]:
    """Cue points this job created that no earlier rollback has already removed."""
    created = (job.get("execution") or {}).get("created_locators", [])
    stored = _read(ROOT / "placements" / (job["id"] + ".json")) or {}
    gone = stored.get("removed_locators", [])
    return [l for l in created if l not in gone]


def _section_marker(plan: dict[str, Any], section: str, locators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The recorded cue that opens ``section`` (by position), if this job created it."""
    base = (int(plan.get("start_bar", 1)) - 1) * 4.0
    for sec in (plan.get("variant") or {}).get("sections", []):
        if sec["name"].lower() == section.strip().lower():
            start = base + 4.0 * sec["start_bar"]
            return [l for l in locators if abs(float(l["time"]) - start) < rollback_safety.EPS]
    return []


def job_status(job_id: str) -> dict[str, Any]:
    try:
        uuid.UUID(job_id)
    except (ValueError, TypeError):
        raise ValueError("Invalid production job ID")
    job = _read(ROOT / "jobs" / (job_id + ".json"))
    if not job:
        raise ValueError("Production job not found")
    execution = _read(queue.QUEUE_DIR / "production-executions" / (job_id + ".json"))
    if execution:
        job["execution"] = execution
        job["status"] = execution["status"]
        if not job.get("execution_logged"):
            _append_operation("bridge_result", job_id, {
                "status": execution["status"], "completed_actions": execution.get("completed_actions", 0),
            })
            job["execution_logged"] = True
            _write(ROOT / "jobs" / (job_id + ".json"), job)
    state = queue.current_state()
    if job["status"] == "Queued" and state.get("session_id") and job["session_id"] != state["session_id"]:
        job.update(status="Interrupted", error="Live restarted before the production job was acknowledged. It will not be retried automatically.")
    if job["status"] in {"Failed", "Partial failure", "Interrupted"}:
        plan = _read(ROOT / "plans" / (job["plan_id"] + ".json")) or {}
        planned = sum(len(a.get("copies", [])) for a in plan.get("actions", []) if a.get("type") == "apply_arrangement_copies")
        job["explanation"] = errors.explain_job(job, planned or None)
    if execution:
        placements = _placement_records(job)
        if placements:
            job["placements"] = placements
        report = job.get("rollback_report")
        if report and execution.get("status") == "Applied":
            removed = int(execution.get("deleted_copies", report["removable_count"]))
            job["message"] = rollback_safety.summarise(removed, report["total"], report["skipped"],
                                                       markers=len(report.get("locators_to_remove", [])))
            if not job.get("placements_updated"):
                _mark_removed(job["rollback_of"], [r["key"] for r in report.get("would_remove", []) if r.get("key")],
                              report.get("locators_to_remove", []))
                job["placements_updated"] = True
                _write(ROOT / "jobs" / (job_id + ".json"), job)
    return job


def rollback(payload: dict[str, Any]) -> dict[str, Any]:
    """Queue only the explicit inverse actions captured by the original snapshot."""
    with LOCK:
        if not isinstance(payload, dict):
            raise ValueError("Rollback input must be a dictionary")
        section = payload.get("section")
        scope = {k: payload.get(k) for k in ("genre", "variant_id")}
        payload = {k: v for k, v in payload.items() if k not in ("section", "genre", "variant_id")}
        if section is not None and (not isinstance(section, str) or not section.strip()):
            raise ValueError("section must be a section name")
        if section and "job_id" not in payload and "plan_id" not in payload:
            if not scope["genre"] or not scope["variant_id"]:
                raise ValueError("Rolling back a section needs genre and variant_id (or a job_id)")
            payload["job_id"] = _job_for_section(_ready_state()[1].get("set_path"), scope["genre"], scope["variant_id"], section.strip())
        if "plan_id" in payload and "job_id" not in payload:
            target_plan_id = str(payload["plan_id"])
            jobs = [job_status(p.stem) for p in (ROOT / "jobs").glob("*.json")] if (ROOT / "jobs").exists() else []
            matching_jobs = [j for j in jobs if j.get("plan_id") == target_plan_id and not j.get("rollback_of")]
            if not matching_jobs:
                raise ValueError(f"No applied job found for production plan {target_plan_id}")
            matching_jobs.sort(key=lambda j: float(j.get("created_at") or 0.0), reverse=True)
            payload = {"job_id": matching_jobs[0]["id"], "working_copy_confirmed": payload.get("working_copy_confirmed"),
                       **({"dry_run": payload["dry_run"]} if "dry_run" in payload else {})}
        dry_run = payload.get("dry_run", False)
        payload = {k: v for k, v in payload.items() if k != "dry_run"}
        if not isinstance(dry_run, bool):
            raise ValueError("dry_run must be true or false")
        if set(payload) not in ({"job_id", "working_copy_confirmed"}, {"job_id", "plan_id", "working_copy_confirmed"}):
            raise ValueError("Rollback input must contain only job_id, working_copy_confirmed and optional dry_run")
        if payload.get("working_copy_confirmed") is not True and not dry_run:
            raise ValueError("Confirm the working copy before rolling back a production plan")
        original = job_status(payload.get("job_id"))
        if original["status"] not in {"Applied", "Partial failure", "Failed"}:
            raise ValueError("Only an applied or partially applied production job can be rolled back")
        execution = original.get("execution", {})
        snapshot = _read(ROOT / "snapshots" / (original["snapshot_id"] + ".json"))
        if not snapshot:
            raise ValueError("The original production snapshot is missing")
        if not snapshot["inverse_actions"]:
            raise ValueError("This job changed nothing in the Set, so there is nothing to roll back")
        state, production = _ready_state()
        granular = any(a.get("type") in ("rollback_arrangement_copies", "rollback_session_to_arrangement_copies")
                       for a in snapshot["inverse_actions"])
        recorded_set = snapshot.get("set_path") or original.get("set_path")
        if not dry_run:
            working_copy.require(production.get("set_path"))
        if recorded_set and recorded_set != production.get("set_path"):
            raise ValueError("This job was applied to a different Live Set; open that Set to roll it back")
        if not granular:
            if original["status"] == "Failed":
                raise ValueError("Only an applied or partially applied production job can be rolled back")
            if original["session_id"] != state["session_id"] or execution.get("post_revision") != production["revision"]:
                raise ValueError("Live project state changed after this job; rollback is no longer safe")
        rollback_report = None
        inverse_actions = copy.deepcopy(snapshot["inverse_actions"])
        # A copy batch can fail after a subset of its deterministic copies was
        # read back.  Its rollback may target only that recorded subset—never
        # a planned destination that was not actually created.
        for action in inverse_actions:
            if action.get("type") == "rollback_session_scene_map":
                action["created_scenes"] = copy.deepcopy(execution.get("created_scenes", []))
                if not action["created_scenes"]:
                    raise ValueError("The Session job recorded no scenes to roll back")
            if action.get("type") == "rollback_split_drum_track":
                action["created_tracks"] = copy.deepcopy(execution.get("created_tracks", []))
                # Splits recorded before muting existed lack these; such a split never muted anything.
                action.setdefault("source_track_id", next((item["drum_split"]["track_id"] for item in snapshot.get("before", [])
                                                           if "drum_split" in item), None))
                action["unmute_source"] = bool(execution.get("muted_source"))
                if not action["created_tracks"]:
                    raise ValueError("The drum split recorded no lanes to remove")
            if action.get("type") == "rollback_arrangement_copies":
                # Re-read Live: delete only recorded clips that are still exactly as placed.
                records = _placement_records(original, persist=not dry_run)
                created_cues = _remaining_locators(original)
                if section:
                    records = [r for r in records if (r.get("section") or "").lower() == section.strip().lower()]
                    created_cues = _section_marker(get_plan(original["plan_id"]), section, created_cues)
                    if not records and not created_cues:
                        raise ValueError("No scaffolded clips are recorded for section '%s' in this job" % section)
                if not records and not created_cues:
                    raise ValueError("The arrangement job recorded no reversible changes")
                verdict = rollback_safety.classify(records, production)
                present = [l for l in created_cues if l in production.get("locators", [])]
                rollback_report = {
                    "dry_run": dry_run, "total": len(records), "removable_count": len(verdict["removable"]),
                    "would_remove": verdict["removable"], "skipped": verdict["skipped"],
                    "locators_to_remove": present,
                    "locators_missing": [l for l in created_cues if l not in present],
                    "section": section.strip() if section else None,
                }
                rollback_report["summary"] = rollback_safety.summarise(
                    len(verdict["removable"]), len(records), verdict["skipped"], dry_run, len(present))
                if dry_run:
                    return dict(rollback_report, job_id=original["id"])
                if not verdict["removable"] and not present:
                    raise ValueError("Nothing to roll back. " + rollback_report["summary"])
                action["copies"] = [{"source_track_id": r["track_id"], "source_start_beat": r["source_start_beat"],
                                     "source_fingerprint": r["source_fingerprint"],
                                     "destination_beat": r["destination_beat"]} for r in verdict["removable"]]
                action["locators"] = copy.deepcopy(present)
                expected_state = rollback_safety.state_after_removal(production, verdict["removable"], present)
                originally = next((i["arrangement"] for i in snapshot["before"] if "arrangement" in i), None)
                back_to_start = (originally and snapshot.get("session_id") == production.get("session_id")
                                 and expected_state["tracks"] == originally["tracks"]
                                 and expected_state.get("locators") == originally["locators"])
                if back_to_start and "is_pristine_default_set" not in originally:
                    pass  # legacy snapshot: keep the originally captured expectation
                else:
                    if back_to_start:
                        # Live derives this flag from track/cue content; restore the original's value.
                        expected_state["is_pristine_default_set"] = originally["is_pristine_default_set"]
                    action["expected_post_rollback_observable_revision"] = _observable_rollback_revision(expected_state)
            if action.get("type") == "rollback_session_to_arrangement_copies":
                # Same per-clip rule as Arrangement scaffolds: delete only recorded copies still exactly as placed.
                records = _placement_records(original, persist=not dry_run)
                if section:
                    records = [r for r in records if (r.get("section") or "").lower() == section.strip().lower()]
                    if not records:
                        raise ValueError("No placed clips are recorded for section '%s' in this job" % section)
                if not records:
                    raise ValueError("The session-to-arrangement job recorded no reversible copies")
                verdict = rollback_safety.classify(records, production)
                rollback_report = {
                    "dry_run": dry_run, "total": len(records), "removable_count": len(verdict["removable"]),
                    "would_remove": verdict["removable"], "skipped": verdict["skipped"],
                    "locators_to_remove": [], "locators_missing": [],
                    "section": section.strip() if section else None,
                }
                rollback_report["summary"] = rollback_safety.summarise(
                    len(verdict["removable"]), len(records), verdict["skipped"], dry_run)
                if dry_run:
                    return dict(rollback_report, job_id=original["id"])
                if not verdict["removable"]:
                    raise ValueError("Nothing to roll back. " + rollback_report["summary"])
                action["copies"] = [{"track_id": r["track_id"], "source_scene_index": r["source_scene_index"],
                                     "source_fingerprint": r["source_fingerprint"],
                                     "destination_beat": r["destination_beat"]} for r in verdict["removable"]]
                expected_state = rollback_safety.state_after_removal(production, verdict["removable"], [])
                originally = next((i["session_to_arrangement"] for i in snapshot["before"] if "session_to_arrangement" in i), None)
                back_to_start = (originally and snapshot.get("session_id") == production.get("session_id")
                                 and expected_state["tracks"] == originally["tracks"])
                if back_to_start and "is_pristine_default_set" not in originally:
                    pass  # snapshot without the flag: the originally captured expectation (already on the action) is exact
                else:
                    if back_to_start:
                        expected_state["is_pristine_default_set"] = originally["is_pristine_default_set"]
                    action["expected_post_rollback_observable_revision"] = _observable_rollback_revision(expected_state)
        original_actions = get_plan(original["plan_id"])["actions"]
        template_action = next((action for action in original_actions
                                if action["type"] == "apply_song_sketch_template"), None)
        if template_action:
            template_before = next(item["template"] for item in snapshot["before"] if "template" in item)
            inverse_actions = [{
                "type": "rollback_song_sketch_template",
                "preset_id": song_sketch.CLASSIC_HOUSE_CLUB_MIX_ID,
                "created_track_ids": execution.get("created_track_ids", []),
                "created_locators": execution.get("created_locators", []),
                "restore_tempo": template_before["tempo"],
                "restore_metre": template_before["metre"],
                "restore_tracks": execution.get("restore_tracks", []),
            }]
            if not execution.get("created_track_ids") or not execution.get("restore_tracks"):
                raise ValueError("Template execution did not record created tracks; rollback is unsafe")
        # Inverses are generated only from the captured snapshot and applied readback.
        tracks = _tracks_by_id(production)
        inverse_actions = [_validate_action(action, tracks) for action in inverse_actions]
        lanes = [record for action in inverse_actions if action["type"] == "rollback_split_drum_track"
                 for record in action["created_tracks"]]
        if dry_run and lanes:
            return {"dry_run": True, "job_id": original["id"], "total": len(lanes), "removable_count": len(lanes),
                    "would_remove": [], "skipped": [],
                    "summary": "Would delete the %d drum lanes this split made: %s. The original track stays and is unmuted." % (
                        len(lanes), ", ".join(record["name"] for record in lanes))}
        if dry_run:  # non-arrangement jobs: nothing per-clip to preview, and nothing may be queued
            return {"dry_run": True, "job_id": original["id"], "total": len(inverse_actions),
                    "removable_count": len(inverse_actions), "would_remove": [], "skipped": [],
                    "summary": "Would restore %d recorded value%s from the original snapshot." % (
                        len(inverse_actions), "" if len(inverse_actions) == 1 else "s")}
        plan_id = str(uuid.uuid4())
        plan = {
            "schema_version": PLAN_SCHEMA,
            "id": plan_id,
            "status": "Draft",
            "created_at": time.time(),
            "intent": "Roll back %s" % original["id"],
            "snapshot_name": "Before rollback of %s" % snapshot["name"],
            "session_id": state["session_id"],
            "source_revision": production["revision"],
            "actions": inverse_actions,
        }
        _write(ROOT / "plans" / (plan_id + ".json"), plan)
        rollback_snapshot = _snapshot_for_plan(plan, production)
        job = _queue_job(plan, rollback_snapshot, state, production, rollback_of=original["id"],
                         extra={"rollback_report": rollback_report} if rollback_report else None)
        plan["status"] = "Queued"
        _write(ROOT / "plans" / (plan_id + ".json"), plan)
        return job


def probe_locators(payload: dict[str, Any]) -> dict[str, Any]:
    """Ask Live to create, read back and delete one test cue; success enables section markers.

    Writes a temporary cue named VIBELTON_PROBE into the open Set, so it needs a working copy.
    """
    if not isinstance(payload, dict) or set(payload) != {"working_copy_confirmed"} or payload["working_copy_confirmed"] is not True:
        raise ValueError("Confirm the working copy to probe marker support")
    plan = create_plan({"intent": "Probe whether this Live build can create arrangement markers",
                        "snapshot_name": "Before marker probe",
                        "actions": [{"type": "probe_arrangement_locators"}]})
    return execute({"plan_id": plan["id"], "working_copy_confirmed": True})


def working_copy_status() -> dict[str, Any]:
    """Gate verdict for the Set Live currently has open (read-only)."""
    state = queue.current_state()
    production = state.get("production") if isinstance(state.get("production"), dict) else {}
    verdict = working_copy.check(production.get("set_path") or state.get("set_path"))
    verdict["connected"] = bool(state.get("connected"))
    return verdict


def overview() -> dict[str, Any]:
    state = queue.current_state()
    plans = [_read(path) for path in sorted((ROOT / "plans").glob("*.json"))] if (ROOT / "plans").exists() else []
    jobs = [job_status(path.stem) for path in sorted((ROOT / "jobs").glob("*.json"))] if (ROOT / "jobs").exists() else []
    return {"live": state, "plans": plans[-30:], "jobs": jobs[-30:], "operations": _recent_operations()}


def create_session_to_arrangement_plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Draft a reversible plan that places unplaced (or selected) Session clips onto the Arrangement timeline."""
    payload = dict(payload or {})
    snapshot_name = str(payload.get("snapshot_name") or "Before Session-to-Arrangement placement").strip()
    intent = str(payload.get("intent") or "Place unplaced Session clips onto the Arrangement timeline").strip()
    explicit_start = payload.get("destination_beat")
    with LOCK:
        state, project = _ready_state()
        tracks = _tracks_by_id(project)
        copies: list[dict[str, Any]] = []
        placed_summary: list[dict[str, Any]] = []

        if isinstance(payload.get("sources"), list) and payload["sources"]:
            for item in payload["sources"]:
                if not isinstance(item, dict):
                    raise ValueError("Invalid session-to-arrangement source")
                tid = str(item.get("track_id") or "")
                s_idx = item.get("source_scene_index")
                if tid not in tracks or type(s_idx) is not int:
                    raise ValueError("Invalid session-to-arrangement track_id or source_scene_index")
                tr = tracks[tid]
                matches = [c for c in (tr.get("session_clips") or []) if c.get("scene_index") == s_idx]
                if len(matches) != 1 or not isinstance(matches[0].get("fingerprint"), str):
                    raise ValueError("Selected Session clip is missing or unreadable")
                clip = matches[0]
                arr_end_on_track = max([0.0] + [float(c.get("end_beat", 0.0)) for c in (tr.get("arrangement_clips") or [])])
                dest_beat = float(item["destination_beat"]) if item.get("destination_beat") is not None else (
                    float(explicit_start) if explicit_start is not None else arr_end_on_track
                )
                copies.append({
                    "track_id": tid,
                    "source_scene_index": s_idx,
                    "source_fingerprint": clip["fingerprint"],
                    "destination_beat": dest_beat,
                })
                placed_summary.append({
                    "track_id": tid,
                    "track_name": tr.get("name", ""),
                    "clip_name": clip.get("name", ""),
                    "source_scene_index": s_idx,
                    "destination_beat": dest_beat,
                    "length": float(clip.get("length") or 4.0),
                })
        else:
            # Automatically select tracks with unplaced session material first; fallback to any fingerprinted session clip
            candidate_tracks = [
                tr for tr in project["tracks"]
                if not tr.get("is_group")
                and (tr.get("session_clips") or [])
                and not (tr.get("arrangement_clips") or [])
            ]
            if not candidate_tracks:
                candidate_tracks = [
                    tr for tr in project["tracks"]
                    if not tr.get("is_group") and (tr.get("session_clips") or [])
                ]
            for tr in candidate_tracks:
                tid = tr["id"]
                arr_end_on_track = max([0.0] + [float(c.get("end_beat", 0.0)) for c in (tr.get("arrangement_clips") or [])])
                cursor = float(explicit_start) if explicit_start is not None else arr_end_on_track
                for clip in (tr.get("session_clips") or []):
                    fp = clip.get("fingerprint")
                    s_idx = clip.get("scene_index")
                    length = float(clip.get("length") or 0.0)
                    if not isinstance(fp, str) or len(fp) != 64 or type(s_idx) is not int or length <= 0.0:
                        continue
                    copies.append({
                        "track_id": tid,
                        "source_scene_index": s_idx,
                        "source_fingerprint": fp,
                        "destination_beat": cursor,
                    })
                    placed_summary.append({
                        "track_id": tid,
                        "track_name": tr.get("name", ""),
                        "clip_name": clip.get("name", ""),
                        "source_scene_index": s_idx,
                        "destination_beat": cursor,
                        "length": length,
                    })
                    cursor += length

        if not copies:
            raise ValueError("No readable Session clips found to place on the Arrangement timeline")

        action = {"type": "apply_session_to_arrangement_copies", "copies": copies}
        plan = create_plan({
            "intent": intent,
            "snapshot_name": snapshot_name,
            "actions": [action],
        })
        plan["placed_clips_summary"] = placed_summary
        plan["workflow"] = "session_to_arrangement"
        plan["rollback_guarantee"] = "Rollback deletes only the Arrangement clip copies recorded by this execution."
        _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
        _append_operation("session_to_arrangement_plan_drafted", plan["id"], {"copy_count": len(copies)})
        return plan


_MIX_ROLE_TARGETS: dict[str, dict[str, float]] = {
    "Kick": {"volume": 0.70, "pan": 0.0, "target_db": -6.0, "send_0": 0.0, "send_1": 0.0},
    "Bass": {"volume": 0.66, "pan": 0.0, "target_db": -7.5, "send_0": 0.0, "send_1": 0.0},
    "Vocal": {"volume": 0.69, "pan": 0.0, "target_db": -6.5, "send_0": 0.28, "send_1": 0.18},
    "Snare / Clap": {"volume": 0.68, "pan": 0.0, "target_db": -7.0, "send_0": 0.15, "send_1": 0.08},
    "Hats": {"volume": 0.55, "pan": -0.15, "target_db": -11.0, "send_0": 0.12, "send_1": 0.08},
    "Percussion": {"volume": 0.52, "pan": 0.22, "target_db": -12.0, "send_0": 0.12, "send_1": 0.08},
    "Chords": {"volume": 0.58, "pan": -0.12, "target_db": -9.5, "send_0": 0.35, "send_1": 0.24},
    "Lead": {"volume": 0.63, "pan": 0.10, "target_db": -8.0, "send_0": 0.28, "send_1": 0.18},
    "Hook": {"volume": 0.63, "pan": -0.10, "target_db": -8.0, "send_0": 0.28, "send_1": 0.18},
    "Atmosphere": {"volume": 0.50, "pan": 0.16, "target_db": -12.5, "send_0": 0.35, "send_1": 0.24},
    "FX / Risers": {"volume": 0.48, "pan": -0.18, "target_db": -13.0, "send_0": 0.35, "send_1": 0.24},
}


def create_mix_balance_proposal(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate a reversible SMYLZ Mix Assistant production plan from confirmed or inferred track roles."""
    payload = dict(payload or {})
    snapshot_name = str(payload.get("snapshot_name") or "Before Mix Assistant balance").strip()
    intent = str(payload.get("intent") or "Apply Mix Assistant role-based level, stereo pan, and spatial send balance").strip()
    include_sends = payload.get("include_sends", True) is not False
    with LOCK:
        state, project = _ready_state()
        active_roles = role_maps.validate_active(_read(ROOT / "role-maps" / "active.json"), state, project)
        cleanup = song_sketch.cleanup_proposal(
            copy.deepcopy(project["tracks"]),
            proposal_id=str(uuid.uuid4()),
            session_id=state["session_id"],
            source_revision=project["revision"],
            confirmed_roles=active_roles,
        )
        role_by_id = {(item.get("id") or item.get("track_id")): item for item in cleanup["tracks"]}

        actions: list[dict[str, Any]] = []
        balance_summary: list[dict[str, Any]] = []
        skipped_empty: list[dict[str, Any]] = []
        role_counts: dict[str, int] = {}

        for track in project["tracks"]:
            if track.get("is_group"):
                continue
            tid = track["id"]
            info = role_by_id.get(tid, {})
            if info.get("is_empty") or song_sketch.is_empty_track(track):
                skipped_empty.append({"track_id": tid, "name": track.get("name", "")})
                continue

            role = info.get("role") or info.get("confirmed_role") or info.get("suggested_role") or info.get("suggested_name") or "Unknown"
            name_lower = str(track.get("name", "")).lower()
            if role == "Percussion" and any(k in name_lower for k in ("drmlp", "drum loop", "full drum", "break")):
                target_spec = {"volume": 0.68, "pan": 0.0, "target_db": -7.0, "send_0": 0.06, "send_1": 0.04}
            else:
                target_spec = dict(_MIX_ROLE_TARGETS.get(role, {"volume": 0.60, "pan": 0.0, "target_db": -9.0, "send_0": 0.14, "send_1": 0.08}))

            count = role_counts.get(role, 0)
            role_counts[role] = count + 1
            if role in ("Chords", "Lead", "Hook") and count % 2 == 1:
                target_spec["pan"] = round(-target_spec["pan"], 2)

            if len(actions) < 20:
                mixer_before = track.get("mixer") or {}
                mixer_sends = mixer_before.get("sends") if isinstance(mixer_before.get("sends"), list) else []
                action_values: dict[str, Any] = {
                    "volume": float(target_spec["volume"]),
                    "pan": float(target_spec["pan"]),
                }
                before_summary: dict[str, Any] = {
                    "volume": mixer_before.get("volume"),
                    "pan": mixer_before.get("pan"),
                }
                after_summary: dict[str, Any] = {
                    "volume": float(target_spec["volume"]),
                    "pan": float(target_spec["pan"]),
                    "target_db": float(target_spec["target_db"]),
                }
                if include_sends and len(mixer_sends) >= 1:
                    action_values["send_0"] = float(target_spec.get("send_0", 0.0))
                    before_summary["send_0"] = float(mixer_sends[0])
                    after_summary["send_0"] = float(target_spec.get("send_0", 0.0))
                if include_sends and len(mixer_sends) >= 2:
                    action_values["send_1"] = float(target_spec.get("send_1", 0.0))
                    before_summary["send_1"] = float(mixer_sends[1])
                    after_summary["send_1"] = float(target_spec.get("send_1", 0.0))

                actions.append({
                    "type": "set_track_mixer",
                    "target_track_id": tid,
                    "values": action_values,
                })
                balance_summary.append({
                    "track_id": tid,
                    "track_name": track.get("name", ""),
                    "role": role,
                    "before": before_summary,
                    "after": after_summary,
                })

        if not actions:
            raise ValueError("No active non-empty tracks found for mix balance")

        plan = create_plan({
            "intent": intent,
            "snapshot_name": snapshot_name,
            "actions": actions,
        })
        plan["role_balance_summary"] = balance_summary
        plan["skipped_empty_tracks"] = skipped_empty
        plan["workflow"] = "mix_assistant"
        _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
        _append_operation("mix_balance_proposed", plan["id"], {
            "balanced_track_count": len(actions),
            "skipped_empty_count": len(skipped_empty),
        })
        return plan


def create_device_parameter_plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a reversible production plan for tweaking one or more Live device parameters."""
    if not isinstance(payload, dict):
        raise ValueError("Device parameter plan payload must be a JSON object")
    snapshot_name = str(payload.get("snapshot_name") or "Before Device Macro tweak").strip()
    intent = str(payload.get("intent") or "Adjust Live device macros / parameters").strip()
    raw_changes = payload.get("changes")
    if not isinstance(raw_changes, list) or not raw_changes:
        if payload.get("target_track_id") or payload.get("track_id"):
            raw_changes = [payload]
        else:
            raise ValueError("Provide a non-empty changes list of device parameter tweaks")
    if len(raw_changes) > 20:
        raise ValueError("A device parameter plan can adjust at most 20 parameters at once")
    actions = []
    for item in raw_changes:
        if not isinstance(item, dict):
            raise ValueError("Invalid device parameter tweak item")
        actions.append({
            "type": "set_device_parameter",
            "target_track_id": item.get("target_track_id") or item.get("track_id"),
            "device_index": item.get("device_index"),
            "parameter_index": item.get("parameter_index"),
            "value": item.get("value"),
        })
    plan = create_plan({
        "intent": intent,
        "snapshot_name": snapshot_name,
        "actions": actions,
    })
    with LOCK:
        _state, project = _ready_state()
        tracks = _tracks_by_id(project)
        before_actions: list[dict[str, Any]] = []
        for action in plan["actions"]:
            track = tracks[action["target_track_id"]]
            dev_idx = int(action["device_index"])
            param_idx = int(action["parameter_index"])
            devices = track.get("devices") or []
            params = (devices[dev_idx].get("parameters") or []) if 0 <= dev_idx < len(devices) else []
            param = next((p for p in params if isinstance(p, dict) and p.get("index") == param_idx), None)
            if param is None and 0 <= param_idx < len(params) and isinstance(params[param_idx], dict):
                param = params[param_idx]
            if param is None or "value" not in param:
                raise ValueError("Could not capture before_actions snapshot for device parameter")
            before_actions.append({
                "type": "set_device_parameter",
                "target_track_id": action["target_track_id"],
                "device_index": dev_idx,
                "parameter_index": param_idx,
                "value": float(param["value"]),
            })
    plan["workflow"] = "device_parameters"
    plan["before_actions"] = before_actions
    if isinstance(plan.get("verification"), dict):
        plan["verification"]["before_actions"] = before_actions
    _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
    _append_operation("device_parameter_plan_drafted", plan["id"], {"action_count": len(actions)})
    return plan



def _ensure_demo_audio_file(raw_path: str) -> None:
    """Create deterministic demo WAV files in /tmp when the UI demo actions are used."""
    import struct
    import wave
    name = Path(str(raw_path)).name
    target = Path("/tmp") / name
    if str(raw_path) != str(target) or target.is_file():
        return
    sr = 22050
    n_samples = sr  # 1.0 second
    if name == "pumplab_demo_kick.wav":
        samples = [int(22000 * math.sin(2.0 * math.pi * 60.0 * (i / sr))) for i in range(n_samples)]
    elif name == "pumplab_demo_bass.wav":
        samples = [int(-20000 * math.sin(2.0 * math.pi * 60.0 * (i / sr))) for i in range(n_samples)]
    elif name == "ref_demo_target.wav":
        samples = [
            int(16000 * math.sin(2.0 * math.pi * 65.0 * (i / sr)) + 9000 * math.sin(2.0 * math.pi * 2200.0 * (i / sr)))
            for i in range(n_samples)
        ]
    elif name == "ref_demo_candidate.wav":
        samples = [
            int(11000 * math.sin(2.0 * math.pi * 65.0 * (i / sr)) + 4000 * math.sin(2.0 * math.pi * 600.0 * (i / sr)))
            for i in range(n_samples)
        ]
    else:
        return
    with wave.open(str(target), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def compare_reference_renders(payload: dict[str, Any]) -> dict[str, Any]:
    """Compare a candidate bounce against a before-render or commercial reference WAV."""
    from . import audio_intelligence
    if not isinstance(payload, dict):
        raise ValueError("Reference comparison payload must be a JSON object")
    before_raw = payload.get("before_path") or payload.get("reference_path")
    after_raw = payload.get("after_path") or payload.get("candidate_path")
    if not before_raw or not after_raw:
        raise ValueError("Provide before_path/reference_path and after_path/candidate_path")
    _ensure_demo_audio_file(str(before_raw))
    _ensure_demo_audio_file(str(after_raw))
    before_path = Path(str(before_raw)).expanduser().resolve(strict=True)
    after_path = Path(str(after_raw)).expanduser().resolve(strict=True)
    if not before_path.is_file() or not after_path.is_file():
        raise ValueError("Both audio files must exist")
    comp = audio_intelligence.compare_renders(before_path, after_path)
    comp["schema_version"] = COMPARISON_SCHEMA
    _append_operation("reference_compared", str(uuid.uuid4()), {
        "before_path": str(before_path),
        "after_path": str(after_path),
        "loudness_delta_db": comp["deltas"]["loudness_delta_db"],
    })
    return comp


def check_low_end_clash(payload: dict[str, Any]) -> dict[str, Any]:
    """Run PumpLab sub-band phase correlation and envelope clash diagnosis on kick and bass WAVs."""
    from . import audio_intelligence
    if not isinstance(payload, dict):
        raise ValueError("Low-end check payload must be a JSON object")
    kick_raw = payload.get("kick_path")
    bass_raw = payload.get("bass_path")
    if not kick_raw or not bass_raw:
        raise ValueError("Provide kick_path and bass_path")
    _ensure_demo_audio_file(str(kick_raw))
    _ensure_demo_audio_file(str(bass_raw))
    kick_path = Path(str(kick_raw)).expanduser().resolve(strict=True)
    bass_path = Path(str(bass_raw)).expanduser().resolve(strict=True)
    if not kick_path.is_file() or not bass_path.is_file():
        raise ValueError("Both kick_path and bass_path must exist")
    report = audio_intelligence.diagnose_kick_bass_clash(kick_path, bass_path)
    _append_operation("low_end_checked", str(uuid.uuid4()), {
        "kick_path": str(kick_path),
        "bass_path": str(bass_path),
        "clash_detected": report["clash_detected"],
        "phase_cancellation_detected": report["phase_cancellation_detected"],
    })
    return report


def rollback_plan(plan_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Roll back a production plan by finding its executed job."""
    payload = dict(payload or {})
    payload["plan_id"] = plan_id
    payload.setdefault("working_copy_confirmed", True)
    return rollback(payload)


class ScaffoldPlanError(ValueError):
    """Planning failed; carries the clips that were passed over so the error can say why."""

    def __init__(self, message: str, skipped_sources: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.skipped_sources = skipped_sources


def _source_clip_problem(clip: dict[str, Any]) -> str | None:
    """Why an Arrangement clip cannot be copied as a source (None when it can)."""
    fp = clip.get("fingerprint")
    if not (isinstance(fp, str) and len(fp) == 64):
        return "no_fingerprint"
    length = float(clip.get("length", 0.0))
    span = float(clip.get("end_beat", 0.0)) - float(clip.get("start_beat", 0.0))
    # A looped/extended clip (placed span != loop length) cannot be copied as one unit.
    if abs(span - length) >= 0.00001:
        return "looped_or_extended"
    if length < 4.0 or abs(length / 4.0 - round(length / 4.0)) >= 0.00001:
        return "not_whole_bar"
    if length > 64.0:
        return "longer_than_16_bars"
    return None


def _note_skipped(skipped: list[dict[str, Any]], track: dict[str, Any], clips: list[dict[str, Any]], reason: str) -> None:
    for clip in clips:
        skipped.append({"track_name": track.get("name") or track.get("id"), "clip_name": clip.get("name"),
                        "start_bar": int(float(clip.get("start_beat", 0.0)) // 4) + 1, "reason": reason})


def _skipped_sources_note(skipped: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for item in skipped:
        counts[item["reason"]] = counts.get(item["reason"], 0) + 1
    parts = ", ".join("%d %s" % (n, errors.SKIP_REASON_SHORT[r]) for r, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    return "%d clips were not used as sources: %s." % (len(skipped), parts)


def _within_source_limit(sources: list[dict[str, Any]], tracks: dict[str, dict[str, Any]],
                         skipped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The first MAX_SCAFFOLD_SOURCES sources, in Set order; the rest are reported as skipped."""
    for source in sources[MAX_SCAFFOLD_SOURCES:]:
        skipped.append({"track_name": tracks[source["track_id"]].get("name") or source["track_id"], "clip_name": None,
                        "start_bar": None, "reason": "source_limit"})
    return sources[:MAX_SCAFFOLD_SOURCES]


def create_scaffold_plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """1-click subtractive arrangement scaffolding for the Arranger M4L Companion."""
    payload = dict(payload or {})
    genre = str(payload.get("genre") or "House").strip()
    if genre not in arrangements.SUPPORTED_GENRES:
        raise ValueError(f"Unsupported genre '{genre}'. Supported genres: {', '.join(arrangements.SUPPORTED_GENRES)}")

    variant_id = payload.get("variant_id")
    expected_variants = arrangements.GENRE_VARIANTS.get(genre, ())
    if not variant_id:
        variant_id = expected_variants[1] if len(expected_variants) > 1 else expected_variants[0]
    elif variant_id not in expected_variants:
        raise ValueError(f"Variant '{variant_id}' is not valid for genre '{genre}'")

    snapshot_name = str(payload.get("snapshot_name") or f"Before {genre} {variant_id} arrangement").strip()
    user_roles = payload.get("roles") or {}
    section = payload.get("section")
    if section is not None and (not isinstance(section, str) or not section.strip()):
        raise ValueError("section must be a section name")
    scoped = {"section": section} if section else {}

    with LOCK:
        state, project = _ready_state()
        working_copy.require(project.get("set_path"))
        if project.get("metre") != [4, 4]:
            raise ValueError("Arrangement scaffolding currently requires a 4/4 Live Set")

        active_roles = role_maps.validate_active(_read(ROOT / "role-maps" / "active.json"), state, project)
        remembered = _remembered_roles_for_planning(project)
        # Precedence: explicit choice in this request > exact-revision confirmation > remembered for this Set > name heuristics.
        known = {**remembered, **((active_roles or {}).get("roles") or {})}
        options = arrangements.build_options(genre, state, project, {"roles": known} if known else active_roles)
        arrangements.validate_options(options)

        proposal_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())
        proposal = {
            "schema_version": ARRANGEMENT_PLAN_SCHEMA,
            "id": proposal_id,
            "status": "Options",
            "created_at": time.time(),
            "session_id": state["session_id"],
            "source_revision": project["revision"],
            "request_id": request_id,
            **options,
        }
        _write(ROOT / "arrangement-proposals" / (proposal_id + ".json"), proposal)
        _write(ROOT / "arrangement-requests" / (request_id + ".json"), {"proposal_id": proposal_id})

        selection = select_house_arrangement({
            "proposal_id": proposal_id,
            "variant_id": variant_id,
            "approved": True,
            "request_id": str(uuid.uuid4()),
        })

        explicit_sources = payload.get("sources")
        if isinstance(explicit_sources, list) and explicit_sources:
            return _create_selected_arrangement_plan({
                "selection_id": selection["id"],
                "snapshot_name": snapshot_name,
                "approved": True,
                "sources": explicit_sources,
                **scoped,
            })

        tracks = _tracks_by_id(project)
        variant = selection["variant"]
        needed_roles = {r for section in variant["sections"] for r in section["active_track_roles"]}

        sources = []
        assigned_tracks = set()
        skipped: list[dict[str, Any]] = []
        for track_id, track in tracks.items():
            arr_clips = track.get("arrangement_clips") or []
            if track.get("is_group"):
                _note_skipped(skipped, track, arr_clips, "group_track")
                continue
            if track.get("drum_rack") and split_lanes_of(track, project["tracks"]):
                _note_skipped(skipped, track, arr_clips, "split_into_lanes")   # its lanes play instead
                continue
            role = user_roles.get(track_id)
            if not role and active_roles and "roles" in active_roles:
                role = active_roles["roles"].get(track_id)
            if not role and track_id in remembered:
                role = remembered[track_id] or role_memory.IGNORE  # remembered None = you chose to ignore this stem
            if not role:
                suggested, _conf, _re = song_sketch._role_for(track)
                role = suggested

            if not role:
                _note_skipped(skipped, track, arr_clips, "no_role")
                continue
            if role == role_memory.IGNORE:
                _note_skipped(skipped, track, arr_clips, "role_ignored")
                continue
            if role not in needed_roles or track_id in assigned_tracks:
                continue

            valid_clips = []
            for c in arr_clips:
                reason = _source_clip_problem(c)
                if reason:
                    _note_skipped(skipped, track, [c], reason)
                else:
                    valid_clips.append(c)

            if valid_clips:
                valid_clips.sort(key=lambda c: (0 if c.get("start_beat") == 0.0 else 1, float(c.get("start_beat", 0.0))))
                chosen_clip = valid_clips[0]
                sources.append({
                    "track_id": track_id,
                    "role": role,
                    "source_start_beat": float(chosen_clip["start_beat"]),
                })
                assigned_tracks.add(track_id)

        if not sources:
            session_sources = []
            to_scenes = payload.get("view") == "session"   # otherwise Session loops are placed into the Arrangement
            session_skipped: list[dict[str, Any]] = []
            session_roles: set[str] = set()
            for track_id, track in tracks.items():
                if track.get("is_group"):
                    continue
                if track.get("drum_rack") and split_lanes_of(track, project["tracks"]):
                    continue   # its lanes play instead
                role = user_roles.get(track_id) or (active_roles.get("roles", {}).get(track_id) if active_roles else None)
                if not role and track_id in remembered:
                    role = remembered[track_id] or role_memory.IGNORE
                if not role:
                    suggested, _conf, _re = song_sketch._role_for(track)
                    role = suggested
                if not role or role not in needed_roles or track_id in assigned_tracks:
                    continue
                readable = [c for c in (track.get("session_clips") or [])
                            if isinstance(c.get("fingerprint"), str) and len(c["fingerprint"]) == 64
                            and type(c.get("scene_index")) is int]
                if to_scenes:
                    usable = [c for c in readable if float(c.get("length", 0.0)) >= 4.0]
                else:   # Arrangement copies are tiled, so the loop must be 1–16 whole bars
                    usable = [c for c in readable if 4.0 <= float(c.get("length", 0.0)) <= 64.0
                              and abs(float(c["length"]) / 4 - round(float(c["length"]) / 4)) < 0.00001]
                    if readable and not usable:   # only worth reporting when the track has no loop that fits
                        c = readable[0]
                        session_skipped.append({"track_name": track.get("name") or track_id, "clip_name": c.get("name"),
                                                "start_bar": None,
                                                "reason": "longer_than_16_bars" if float(c.get("length", 0.0)) > 64.0 else "not_whole_bar"})
                if not usable:
                    continue
                if to_scenes and role in session_roles:   # a scene plan takes one source per role; the rest are reported
                    session_skipped.append({"track_name": track.get("name") or track_id, "clip_name": usable[0].get("name"),
                                            "start_bar": None, "reason": "role_already_used"})
                    continue
                session_sources.append({
                    "track_id": track_id,
                    "role": role,
                    "source_scene_index": usable[0]["scene_index"],
                })
                assigned_tracks.add(track_id)
                session_roles.add(role)
            if session_sources and section and to_scenes:
                raise ValueError("Scaffolding one section needs Arrangement clips as sources")
            if session_sources and not to_scenes:
                try:
                    plan = _create_selected_arrangement_plan({
                        "selection_id": selection["id"],
                        "snapshot_name": snapshot_name,
                        "approved": True,
                        "sources": _within_source_limit(session_sources, tracks, session_skipped),
                        **scoped,
                    })
                except ValueError as exc:
                    raise ScaffoldPlanError(str(exc), session_skipped) from exc
                if session_skipped:
                    plan["skipped_sources"] = session_skipped
                    plan["warnings"].append(_skipped_sources_note(session_skipped))
                    _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
                return plan
            if session_sources:
                plan = _create_session_scene_plan({
                    "selection_id": selection["id"],
                    "snapshot_name": snapshot_name,
                    "approved": True,
                    "sources": session_sources,
                    "view": "session",
                })
                if session_skipped:
                    plan["skipped_sources"] = session_skipped
                    plan["warnings"].append(_skipped_sources_note(session_skipped))
                    _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
                return plan
            raise ScaffoldPlanError("No fingerprinted 4-bar to 16-bar source loops found in the Set to scaffold from", skipped)

        sources = _within_source_limit(sources, tracks, skipped)
        try:
            plan = _create_selected_arrangement_plan({
                "selection_id": selection["id"],
                "snapshot_name": snapshot_name,
                "approved": True,
                "sources": sources,
                **scoped,
            })
        except ValueError as exc:
            raise ScaffoldPlanError(str(exc), skipped) from exc
        if skipped:
            plan["skipped_sources"] = skipped
            plan["warnings"].append(_skipped_sources_note(skipped))
            _write(ROOT / "plans" / (plan["id"] + ".json"), plan)
        return plan



