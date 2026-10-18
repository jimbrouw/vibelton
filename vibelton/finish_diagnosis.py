"""Deterministic, read-only Finish Track diagnosis from revision-bound facts."""
from __future__ import annotations

from collections import Counter
from typing import Any

from . import arrangements, song_sketch

SCHEMA = "vibelton.finish-diagnosis/v1"


def diagnose(analysis: dict[str, Any], variant_id: str, confirmed_roles: dict[str, Any] | None = None) -> dict[str, Any]:
    genre = arrangements.genre_for_variant(variant_id)
    tracks = analysis["tracks"]
    project = analysis["project"]
    options = arrangements.build_options(
        genre,
        {"tracks": tracks, "tempo": project["tempo"]},
        {"tracks": tracks, "tempo": project["tempo"], "metre": project["metre"]},
        confirmed_roles,
    )
    template = next(item for item in options["variants"] if item["id"] == variant_id)
    findings: list[tuple[int, dict[str, Any]]] = []

    def add(priority: int, code: str, observation: str, evidence: dict[str, Any],
            confidence: str, assumptions: list[str], why: str, action: str,
            action_status: str) -> None:
        findings.append((priority, {
            "code": code, "observation": observation, "evidence": evidence,
            "confidence": confidence, "assumptions": assumptions,
            "musical_importance": why, "suggested_next_action": action,
            "action_status": action_status,
        }))

    clips = [(track, clip) for track in tracks for clip in track.get("arrangement_clips", [])
             if isinstance(clip, dict)]
    errors = project.get("arrangement_errors")
    readable = bool(project.get("arrangement_readable")) or (
        isinstance(errors, list) and bool(errors) and all(
            isinstance(err, dict) and err.get("is_group") is True for err in errors
        )
    )
    if readable:
        signatures = Counter((track.get("id"), clip.get("fingerprint")) for track, clip in clips
                             if clip.get("fingerprint"))
        repeated = [(track_id, fingerprint, count) for (track_id, fingerprint), count in signatures.items()
                    if count >= 3]
        if repeated:
            track_id, fingerprint, count = sorted(repeated, key=lambda row: (-row[2], str(row[0])))[0]
            add(95, "repeated_material", "The same Arrangement clip material repeats at least three times.",
                {"track_id": track_id, "fingerprint": fingerprint, "copy_count": count}, "high", [],
                "Long stretches of identical material can reduce forward motion.",
                "Review repeated sections and propose a variation in role or phrasing.", "deferred")
        elif len(clips) >= 3 and not all(clip.get("fingerprint") for _, clip in clips):
            add(42, "repetition_uncertain", "Clip repetition cannot be checked reliably for every Arrangement clip.",
                {"clip_count": len(clips), "fingerprinted_count": sum(bool(c.get("fingerprint")) for _, c in clips)},
                "low", ["A clip name does not prove identical musical content."],
                "Repetition may need a closer review before changing the arrangement.",
                "Refresh clip fingerprints before proposing a variation.", "deferred")
        if clips:
            sections = template["sections"]
            signatures_by_section = []
            for section in sections:
                start, end = section["start_bar"] * 4, section["end_bar"] * 4
                active = sorted({track.get("id") for track, clip in clips
                                 if float(clip.get("start_beat", clip.get("start_time", -1))) < end
                                 and float(clip.get("end_beat", float(clip.get("start_beat", clip.get("start_time", 0))) + float(clip.get("length", 0)))) > start})
                signatures_by_section.append((section["id"], active))
            occupied = [row for row in signatures_by_section if row[1]]
            if len(occupied) >= 3 and len({tuple(row[1]) for row in occupied}) == 1:
                add(88, "weak_section_contrast", "The same set of tracks is active across the occupied template sections.",
                    {"sections": [row[0] for row in occupied], "active_track_ids": occupied[0][1]},
                    "medium", ["Track activity is a structural proxy; it does not describe sound or note variation."],
                    "A breakdown or return usually benefits from a clear change in active roles.",
                    "Review a section level subtraction or re-entry using existing material.", "deferred")
            elif len(occupied) < 3 and clips:
                add(75, "incomplete_sections", "Arrangement material occupies fewer than three template sections.",
                    {"occupied_sections": [row[0] for row in occupied], "template_section_count": len(sections)},
                    "medium", ["The chosen template is the intended finishing structure."],
                    "The Set may still need a beginning, development, and ending.",
                    "Review a proposed arrangement map before any clip placement.", "needs_user_approval")
    else:
        add(98, "arrangement_unreadable", "Arrangement clips are not currently readable.",
            {"arrangement_readable": False}, "high", [],
            "Section and repetition findings would be unreliable.",
            "Refresh the bridge's Arrangement readback.", "deferred")

    unplaced = []
    for track in tracks:
        session_clips = track.get("session_clips") or track.get("clips") or []
        arrangement_clips = track.get("arrangement_clips") or []
        if session_clips and not arrangement_clips:
            unplaced.append({"track_id": track.get("id"), "track_name": track.get("name"),
                             "session_clip_count": len(session_clips)})
    if unplaced:
        add(86, "unplaced_session_material",
            "Some tracks contain Session View clips that have not been placed into the Arrangement timeline.",
            {"tracks": unplaced, "track_names": [row["track_name"] for row in unplaced]},
            "high", [],
            "Unplaced Session ideas may hold key hooks, basslines, or variations missing from the Arrangement.",
            "Review unplaced Session clips and place or audition them in a confirmed working copy.",
            "needs_user_approval")

    inventory = options["role_inventory"]
    identified = {row["role"] for row in inventory["likely_roles"] if row["role"]}
    expected = {role for section in template["sections"] for role in section["active_track_roles"]}
    missing = sorted(expected - identified)
    if missing:
        add(83, "missing_roles", "Several roles expected by the selected template have no clearly identified track.",
            {"missing_roles": missing, "identified_roles": sorted(identified),
             "role_source": "confirmed" if confirmed_roles else "suggested"}, "high" if confirmed_roles else "medium",
            [] if confirmed_roles else ["Roles are inferred from track and device names; an unnamed track may contain a missing role."],
            "Missing roles can limit the intended section shape and transitions.",
            "Confirm track roles and adapt the template to the actual material.", "needs_user_approval")
    empty_tracks = [track.get("name") for track in tracks
                    if song_sketch.is_empty_track(track) and song_sketch._role_for(track)[0] is None]
    empty_names_set = set(empty_tracks)
    group_names_set = {track.get("name") for track in tracks if track.get("is_group")}
    generic = [row["track_name"] for row in inventory["unassigned_tracks"]
               if not row["role"] and row["track_name"] not in empty_names_set and row["track_name"] not in group_names_set]
    if generic:
        add(55, "unclear_track_roles", "Some tracks have no clear finishing role from their names or devices.",
            {"track_names": generic}, "high", [],
            "Unclear roles make section decisions harder to verify.",
            "Review and label these tracks after confirming their contents.", "needs_user_approval")
    if empty_tracks:
        add(45, "empty_unused_tracks", "Several tracks have no devices, Session clips, or Arrangement clips.",
            {"track_names": empty_tracks, "empty_track_count": len(empty_tracks)}, "high", [],
            "Empty placeholder tracks clutter mixer balance and arrangement planning.",
            "Review and archive or ignore empty placeholder tracks during cleanup.", "needs_user_approval")
    if not project.get("locators"):
        add(48, "section_markers_uncertain", "No readable section locators are present in the project facts.",
            {"locator_count": 0}, "medium",
            ["The bridge may not read native Arrangement locators reliably."],
            "Clear section boundaries help evaluate development and transitions.",
            "Use the template section map for review; defer native locator edits.", "deferred")
    if not findings:
        add(20, "no_structural_issue", "No high-impact structural issue was detected in the available facts.",
            {"track_count": len(tracks), "arrangement_clip_count": len(clips)}, "medium",
            ["This is a structural check only; no audio was rendered or measured."],
            "The arrangement can move to an audition and targeted review.",
            "Ask the user to audition the Set and identify the next musical concern.", "supported")
    selected = [item for _, item in sorted(findings, key=lambda pair: (-pair[0], pair[1]["code"]))[:5]]
    return {"schema_version": SCHEMA, "session_id": analysis["session_id"],
            "source_revision": analysis["source_revision"], "source_schema": analysis["schema_version"],
            "template_variant_id": variant_id, "genre": options["genre"],
            "status": "read_only", "findings": selected,
            "capabilities": {"live_mutation": False, "render_analysis": False, "model_required": False},
            "unmeasured": analysis["missing_measurements"]}
