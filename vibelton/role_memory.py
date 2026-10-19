"""Remember confirmed stem roles per Live Set, and re-match them when tracks change.

Unlike ``role_maps`` confirmations (bound to one exact Live revision), this memory
survives edits, reloads and restarts.  Entries are keyed by the Set's file path and
re-attached to tracks by id, then by unique name (ignoring Live's track number), then by
position (flagged for review).
Entries whose track disappeared are kept as *orphaned* so undoing a deletion restores them.
"""
from __future__ import annotations

import re
import time
from typing import Any

SCHEMA = "vibelton.role-memory/v1"
IGNORE = "Ignore / Unknown"


def _normalise(role: Any, allowed: tuple[str, ...]) -> str | None:
    """A stored role is one of the known roles, or None meaning 'deliberately ignored'."""
    if role is None or role == IGNORE or role == "":
        return None
    if role not in allowed:
        raise ValueError("Unsupported track role '%s'" % role)
    return role


_LIVE_NUMBER = re.compile(r"^\d+-")


def _base_name(name: Any) -> str:
    """A track name without the number Live puts in front ("12-Guitar" -> "Guitar"); that number
    changes whenever tracks are added or removed above it."""
    return _LIVE_NUMBER.sub("", str(name or ""))


def playable(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [t for t in tracks if not t.get("is_group")]


def resolve(entries: list[dict[str, Any]], tracks: list[dict[str, Any]]) -> dict[str, Any]:
    """Match remembered entries to the current tracks."""
    current = playable(tracks)
    matches: dict[str, dict[str, Any]] = {}
    used_entries: set[int] = set()

    def attach(entry_index: int, track: dict[str, Any], how: str, review: bool = False) -> None:
        entry = entries[entry_index]
        matches[track["id"]] = {
            "role": entry["role"], "matched_by": how, "needs_review": review,
            "renamed_from": entry.get("track_name") if entry.get("track_name") != track.get("name") else None,
            "entry": entry_index,
        }
        used_entries.add(entry_index)

    # 1. same track id (survives renames and reordering within a session)
    by_id = {t["id"]: t for t in current}
    for index, entry in enumerate(entries):
        track = by_id.get(entry.get("track_id"))
        if track is not None and track["id"] not in matches:
            attach(index, track, "id")

    free_tracks = [t for t in current if t["id"] not in matches]
    free_entries = [i for i in range(len(entries)) if i not in used_entries]

    # 2. identical name, unique on both sides (Live regenerates ids when a Set is reopened)
    for index in list(free_entries):
        same = [t for t in free_tracks if t.get("name") == entries[index].get("track_name")]
        rivals = [i for i in free_entries if entries[i].get("track_name") == entries[index].get("track_name")]
        if len(same) == 1 and len(rivals) == 1:
            attach(index, same[0], "name")
            free_tracks.remove(same[0])
            free_entries.remove(index)

    # 2b. same name apart from Live's track number (tracks were added or removed above).  Several
    # tracks sharing a name ("12-Guitar", "13-Guitar"…) pair up in Set order when both sides count the same.
    for base in sorted({_base_name(entries[i].get("track_name")) for i in free_entries} - {""}):
        group = sorted((i for i in free_entries if _base_name(entries[i].get("track_name")) == base),
                       key=lambda i: entries[i].get("track_index") if isinstance(entries[i].get("track_index"), int) else 0)
        same = sorted((t for t in free_tracks if _base_name(t.get("name")) == base),
                      key=lambda t: t.get("index") if isinstance(t.get("index"), int) else 0)
        if group and len(same) == len(group):
            for index, track in zip(group, same):   # a pairing by order is a guess when names repeat: ask for review
                attach(index, track, "name" if len(group) == 1 else "order", review=len(group) > 1)
                free_tracks.remove(track)
                free_entries.remove(index)

    # 3. same position and type, when that pairing is unambiguous: probably renamed, so ask for review
    for index in list(free_entries):
        entry = entries[index]
        same = [t for t in free_tracks if t.get("index") == entry.get("track_index") and t.get("type") == entry.get("track_type")]
        rivals = [i for i in free_entries if entries[i].get("track_index") == entry.get("track_index")
                  and entries[i].get("track_type") == entry.get("track_type")]
        if len(same) == 1 and len(rivals) == 1:
            attach(index, same[0], "position", review=True)
            free_tracks.remove(same[0])
            free_entries.remove(index)

    return {
        "matches": matches,
        "orphaned": [entries[i] for i in free_entries],
        "new_tracks": [t["id"] for t in free_tracks],
    }


def merge(entries: list[dict[str, Any]], tracks: list[dict[str, Any]], roles: dict[str, Any],
          allowed: tuple[str, ...]) -> list[dict[str, Any]]:
    """Apply user-confirmed roles, and refresh matched entries to the tracks' current identity."""
    current = {t["id"]: t for t in playable(tracks)}
    unknown = [track_id for track_id in roles if track_id not in current]
    if unknown:
        raise ValueError("Roles refer to tracks that are not in the open Set")
    resolved = resolve(entries, tracks)
    merged = [dict(entry) for entry in entries]
    now = time.time()

    def identity(entry: dict[str, Any], track: dict[str, Any]) -> None:
        entry.update(track_id=track["id"], track_name=track.get("name"), track_index=track.get("index"),
                     track_type=track.get("type"))

    for track_id, info in resolved["matches"].items():
        if info["matched_by"] != "position" or track_id in roles:  # an unreviewed guess is not re-stamped
            identity(merged[info["entry"]], current[track_id])
    for track_id, role in roles.items():
        value = _normalise(role, allowed)
        match = resolved["matches"].get(track_id)
        if match is not None:
            merged[match["entry"]].update(role=value, saved_at=now)
        else:
            entry = {"role": value, "saved_at": now}
            identity(entry, current[track_id])
            merged.append(entry)
    return merged


def remembered_roles(entries: list[dict[str, Any]], tracks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """{track_id: {role, matched_by, needs_review, renamed_from}} for the current tracks."""
    return {track_id: {k: v for k, v in info.items() if k != "entry"}
            for track_id, info in resolve(entries, tracks)["matches"].items()}
