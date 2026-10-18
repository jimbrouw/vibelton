"""Placement records and per-clip rollback classification for arrangement scaffolds.

A scaffold only ever *creates* clips (native duplicates of the user's loops).
Rollback must therefore delete only those clips, and only if they are still
exactly as placed.  Everything here is pure: it works on the production state
dictionary the bridge reports, so it is testable without Live.
"""
from __future__ import annotations

import copy
from typing import Any

EPS = 1e-5

REASON_TEXT = {
    "edited": "you edited them",
    "moved_or_deleted": "they were moved, resized or deleted",
    "overlapped": "another clip now overlaps them",
    "source_changed": "their source loop changed",
    "track_missing": "their track was removed or renamed",
    "is_source": "they are your original loops",
}


def _near(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) < EPS


def section_for(beat: float, sections: list[dict[str, Any]]) -> str | None:
    for section in sections:
        if float(section["start_beat"]) - EPS <= beat < float(section["end_beat"]) - EPS:
            return section["name"]
    return None


def record_key(record: dict[str, Any]) -> str:
    return f"{record['track_id']}|{record['destination_beat']}|{record['source_fingerprint']}"


def build_records(created_copies: list[dict[str, Any]], before_tracks: list[dict[str, Any]],
                  set_path: str | None = None, sections: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """One stable record per clip the bridge reports it actually created.

    ``sections`` (name/start_beat/end_beat in absolute beats) tags each record with the
    arrangement section it was placed in, so a single section can be rolled back.
    """
    by_id = {t.get("id"): (index, t) for index, t in enumerate(before_tracks)}
    records = []
    for item in created_copies:
        index, track = by_id.get(item.get("source_track_id"), (None, {}))
        source = next((c for c in track.get("arrangement_clips", [])
                       if _near(c.get("start_beat", -1), item["source_start_beat"])
                       and c.get("fingerprint") == item["source_fingerprint"]), None)
        length = float(source["end_beat"]) - float(source["start_beat"]) if source else None
        destination = float(item["destination_beat"])
        record = {
            "track_id": item["source_track_id"],
            "track_name": track.get("name"),
            "track_index": index,
            "clip_name": source.get("name") if source else None,
            "destination_beat": destination,
            "end_beat": destination + length if length is not None else None,
            "source_start_beat": float(item["source_start_beat"]),
            "source_fingerprint": item["source_fingerprint"],
            "set_path": set_path or None,
            "section": section_for(destination, sections or []),
        }
        record["key"] = record_key(record)
        records.append(record)
    return records


def build_session_records(created_copies: list[dict[str, Any]], before_tracks: list[dict[str, Any]],
                          set_path: str | None = None, sections: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Placement records for Session-to-Arrangement copies (``track_id`` / ``source_scene_index`` shape)."""
    by_id = {t.get("id"): (index, t) for index, t in enumerate(before_tracks)}
    records = []
    for item in created_copies:
        index, track = by_id.get(item.get("track_id"), (None, {}))
        source = next((c for c in track.get("session_clips", [])
                       if c.get("scene_index") == item["source_scene_index"]
                       and c.get("fingerprint") == item["source_fingerprint"]), None)
        length = float(source["length"]) if source and source.get("length") else None
        destination = float(item["destination_beat"])
        record = {
            "track_id": item["track_id"],
            "track_name": track.get("name"),
            "track_index": index,
            "clip_name": source.get("name") if source else None,
            "destination_beat": destination,
            "end_beat": destination + length if length is not None else None,
            "source_scene_index": int(item["source_scene_index"]),
            "source_start_beat": None,
            "source_fingerprint": item["source_fingerprint"],
            "set_path": set_path or None,
            "section": section_for(destination, sections or []),
        }
        record["key"] = record_key(record)
        records.append(record)
    return records


def _resolve_track(record: dict[str, Any], tracks: list[dict[str, Any]]) -> dict[str, Any] | None:
    for track in tracks:
        if track.get("id") == record["track_id"]:
            return track
    # Live reloaded the Set: ids are regenerated.  Fall back to an unambiguous name (+ index) match.
    same_name = [t for t in tracks if t.get("name") == record.get("track_name") and record.get("track_name")]
    if len(same_name) == 1:
        return same_name[0]
    at_index = [t for t in same_name if t.get("index") == record.get("track_index")]
    return at_index[0] if len(at_index) == 1 else None


def classify(records: list[dict[str, Any]], production: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Split records into removable clips and skipped ones (with reasons)."""
    tracks = production.get("tracks", [])
    removable: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def skip(record: dict[str, Any], reason: str) -> None:
        skipped.append({"record": record, "reason": reason, "reason_text": REASON_TEXT[reason]})

    for record in records:
        track = _resolve_track(record, tracks)
        if track is None:
            skip(record, "track_missing")
            continue
        clips = track.get("arrangement_clips") or []
        start, fingerprint = record["destination_beat"], record["source_fingerprint"]
        at_start = [c for c in clips if _near(c["start_beat"], start)]
        matches = [c for c in at_start if c.get("fingerprint") == fingerprint]
        if len(matches) != 1:
            skip(record, "edited" if at_start else "moved_or_deleted")
            continue
        clip = matches[0]
        # Never delete a clip that is the source of any recorded copy on this track.
        if any(r.get("source_start_beat") is not None and _near(clip["start_beat"], r["source_start_beat"])
               for r in records if _resolve_track(r, tracks) is track):
            skip(record, "is_source")
            continue
        end = float(clip["end_beat"])
        if record.get("end_beat") is not None and not _near(end, record["end_beat"]):
            skip(record, "edited")
            continue
        if any(c is not clip and float(c["start_beat"]) < end - EPS and float(c["end_beat"]) > start + EPS for c in clips):
            skip(record, "overlapped")
            continue
        # The bridge deletes a copy only while its source loop is intact.
        if record.get("source_scene_index") is not None:   # Session-to-Arrangement: the source is a Session clip
            sources = [c for c in (track.get("session_clips") or []) if c.get("scene_index") == record["source_scene_index"]]
        else:
            sources = [c for c in clips if _near(c["start_beat"], record["source_start_beat"])]
        if len(sources) != 1 or sources[0].get("fingerprint") != fingerprint:
            skip(record, "source_changed")
            continue
        removable.append(dict(record, track_id=track["id"]))
    return {"removable": removable, "skipped": skipped}


def state_after_removal(production: dict[str, Any], removable: list[dict[str, Any]],
                        locators: list[dict[str, Any]]) -> dict[str, Any]:
    """The production state Live should report once exactly these clips/cues are gone."""
    after = copy.deepcopy(production)
    for record in removable:
        for track in after["tracks"]:
            if track["id"] == record["track_id"]:
                track["arrangement_clips"] = [
                    c for c in track["arrangement_clips"]
                    if not (_near(c["start_beat"], record["destination_beat"])
                            and c.get("fingerprint") == record["source_fingerprint"])]
    ends = [float(c["end_beat"]) for t in after["tracks"] for c in t.get("arrangement_clips", [])]
    after["arrangement_end"] = max([0.0] + ends)
    if "locators" in after:
        after["locators"] = [l for l in after["locators"] if l not in locators]
    return after


def _bar(beat: float) -> int:
    return int(beat // 4) + 1


def summarise(removed: int, total: int, skipped: list[dict[str, Any]], dry_run: bool = False, markers: int = 0) -> str:
    verb = "Would remove" if dry_run else "Removed"
    text = f"{verb} {removed} of {total} clips."
    if markers:
        text += f" {verb} {markers} section marker{'s' if markers != 1 else ''}."
    if not skipped:
        return text
    groups: dict[str, list[str]] = {}
    for item in skipped:
        record = item["record"]
        label = f"{record.get('track_name') or 'track'} bar {_bar(record['destination_beat'])}"
        groups.setdefault(item["reason"], []).append(label)
    parts = [f"{len(labels)} {'would be ' if dry_run else ''}skipped because {REASON_TEXT[reason]}: {', '.join(labels)}"
             for reason, labels in groups.items()]
    return f"{text} " + ". ".join(p[0].upper() + p[1:] if i == 0 else p for i, p in enumerate(parts)) + "."
