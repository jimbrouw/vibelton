"""Plain-language explanations for server, job and Remote Script failures.

The raw message is always kept (for the device's "Details" toggle); the explanation is what
a producer reads.  Nothing here ever includes a stack trace.
"""
from __future__ import annotations

import re
from typing import Any

from .redact import home_to_tilde

# (code, regex over the raw message, title, plain message, next step)
CATALOGUE: list[tuple[str, str, str, str, str]] = [
    ("live_disconnected", r"disconnected or its heartbeat is stale", "Ableton Live isn't responding",
     "Vibelton can't reach Live right now.", "Check that Live is open with the Vibelton control surface enabled, then try again."),
    ("bridge_outdated", r"Install the Phase 1 Vibelton bridge|Restart Ableton Live with the updated Vibelton|Production state is incomplete",
     "Live is running an older Vibelton script", "The Vibelton Remote Script inside Live is out of date for this action.",
     "Install the current Remote Script and restart Live."),
    ("session_expired", r"Missing or invalid session token", "The device session expired",
     "The device lost its permission to talk to the Vibelton server.", "Reload the device (or refresh the page) and try again."),
    ("blocked_origin", r"Forbidden (host|origin)", "Request blocked", "That request didn't come from the Vibelton device.",
     "Use the device or the Vibelton page itself."),
    ("working_copy", r"does not look like a working copy|Live Set is unsaved|Save Live Set As|working copy",
     "Not a working copy", "", "Use File > Save Live Set As… to make a working copy first."),
    ("other_set", r"different Live Set", "Different Live Set", "That job belongs to another Set.", "Open the Set it was applied to, then undo."),
    ("undo_unsafe", r"rollback is no longer safe", "Can't undo automatically",
     "The Set changed after this job, so Vibelton can't be sure an automatic undo is safe.",
     "Undo by hand in Live (Cmd+Z or delete the new clips)."),
    ("stale_plan", r"state changed|Set changed|Live Set changed", "Live changed since the preview",
     "The Set was edited after this plan was made, so it is no longer safe to apply.", "Press Scaffold again for a fresh preview."),
    ("no_sources", r"No fingerprinted", "No loops to build from",
     "Vibelton couldn't find a whole-bar loop (1–16 bars, played exactly once) on a track whose role it recognises.",
     "Name or tag your stems (Kick, Bass, Hats…), and make sure each has one whole-bar clip in the Arrangement."),
    ("outro_uncovered", r"final section so the arrangement reaches its outro", "Nothing fits the ending",
     "No stem has a loop short enough to fill the final section without being cut.", "Use a shorter loop for one stem, or scaffold the other sections one at a time."),
    ("bad_source_clip", r"Choose a fingerprinted, whole-bar", "That clip can't be copied",
     "Only whole-bar clips up to 16 bars, placed exactly once (not looped or stretched), can be used.", "Trim or consolidate the clip in Live."),
    ("arrangement_full", r"The Arrangement is full", "The Arrangement is full",
     "", "Each full scaffold is placed after everything already in the Arrangement. Undo earlier scaffolds, "
     "or delete old copies at the end of the Arrangement in Live, then scaffold again."),
    ("loops_too_long", r"do not fit", "Loops too long for that section", "The loops you have are longer than the section.", "Pick a longer section or a shorter loop."),
    ("section_occupied", r"already has clips", "That section already has clips", "", "Undo that section first, then scaffold it again."),
    ("unknown_section", r"Unknown section", "Unknown section", "", "Choose one of the listed sections."),
    ("not_4_4", r"requires a 4/4", "Only 4/4 Sets are supported", "This Set isn't in 4/4.", "Switch the Set to 4/4."),
    ("too_many_copies", r"over 400 copies", "Too many clips needed", "This plan would need over 400 clips.", "Use longer source loops."),
    ("destination_occupied", r"destination is already occupied|copies overlap each other", "Those bars aren't empty",
     "Something already sits where Vibelton wanted to place a clip.", "Scaffold again for a fresh plan, or undo the earlier scaffold."),
    ("source_changed", r"source is missing, ambiguous, or changed|Expected arrangement copy is missing or changed", "A clip changed",
     "A loop Vibelton relies on was moved, edited or deleted.", "Leave the loops untouched, or undo and scaffold again."),
    ("readback_mismatch", r"readback did not (match|reach)|fingerprint changed after placement",
     "Live didn't confirm the change", "Vibelton placed clips but Live's readback didn't match the plan exactly.", "Check the Arrangement, then undo if anything looks wrong."),
    ("rollback_inexact", r"did not restore the exact original state", "Undo didn't restore everything",
     "Clips were removed, but the Set doesn't exactly match its earlier state (something else changed).", "Review the Arrangement by hand."),
    ("replay", r"already attempted; automatic replay rejected", "Already attempted", "That job was already sent to Live and won't be repeated automatically.", "Check the Arrangement, then plan again if needed."),
    ("interrupted", r"Live restarted before the production job", "Live restarted", "Live restarted before the job was confirmed.", "Check the Arrangement, then plan again."),
    ("queue_uncertain", r"Queue submission uncertain", "Unsure if it was sent", "Vibelton couldn't confirm the job reached Live.", "Check the Arrangement before retrying."),
    ("nothing_to_undo", r"nothing to roll back|Nothing to roll back|recorded no reversible", "Nothing to undo",
     "No clips from this job are left to remove.", "Nothing to do."),
    ("markers", r"locator", "Section markers", "Live couldn't create or read back the section markers.", "Markers are optional; the clips are unaffected."),
]


SKIP_REASON_SHORT = {
    "looped_or_extended": "looped or stretched", "not_whole_bar": "not a whole number of bars",
    "longer_than_16_bars": "longer than 16 bars", "no_fingerprint": "not readable yet",
    "no_role": "on tracks with no recognised role", "group_track": "on group tracks",
    "role_ignored": "on tracks you set to ignore", "role_already_used": "on a second track with an already-used role",
    "source_limit": "on tracks beyond the 16-track limit",
    "split_into_lanes": "on drum tracks already split into lanes",
}
# (count-aware plain sentence, what to do) per reason
SKIP_REASON_TEXT = {
    "looped_or_extended": ("{n} clips were looped or stretched and can't be copied.",
                           "Consolidate them in Live (Cmd+J) first."),
    "not_whole_bar": ("{n} clips are not a whole number of bars long.", "Trim them to whole bars in Live."),
    "longer_than_16_bars": ("{n} clips are longer than 16 bars.", "Split or shorten them to 16 bars or less."),
    "no_fingerprint": ("{n} clips could not be read by Vibelton.", "Press Refresh, or re-save the Set and try again."),
    "no_role": ("{n} clips sit on tracks whose role Vibelton doesn't recognise.", "Pick a role for those stems."),
    "group_track": ("{n} clips sit on group tracks, which are never used.", "Move them onto a normal track."),
    "role_ignored": ("{n} clips are on tracks you set to ignore.", "Give those stems a role if you want them used."),
    "role_already_used": ("{n} clips are on a second track with a role that is already used.", "Give that track a different role if you want it used."),
    "source_limit": ("{n} tracks were left out because a scaffold uses at most 16 tracks.", "Set the stems you don't need to Ignore."),
    "split_into_lanes": ("{n} clips are on drum tracks that were split; their lanes are used instead.", "Undo the split to use the whole drum track."),
}


def _skip_summary(skipped: list[dict[str, Any]]) -> tuple[str, list[str]]:
    counts: dict[str, int] = {}
    for item in skipped:
        counts[item["reason"]] = counts.get(item["reason"], 0) + 1
    top = max(counts, key=lambda r: counts[r])
    sentence, fix = SKIP_REASON_TEXT[top]
    details = ["%s — %s (bar %s): %s" % (i["track_name"], i.get("clip_name") or "clip", i.get("start_bar"),
                                         SKIP_REASON_SHORT[i["reason"]]) for i in skipped]
    return f"{sentence.format(n=counts[top])} {fix}", details


def explain(raw: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Turn a raw error string into {code, title, message, next_step, raw, severity}."""
    text = str(raw or "").strip()
    context = context or {}
    for code, pattern, title, message, next_step in CATALOGUE:
        if re.search(pattern, text, re.IGNORECASE):
            # Messages that were already written for people (gate, section names) are kept as the body.
            body = message or text
            skipped = context.get("skipped_sources")
            if skipped and code in ("no_sources", "outro_uncovered", "bad_source_clip"):
                body, details = _skip_summary(skipped)
                result = _finish(code, title, body, "", text, context)
                result["next_step"] = next_step if code != "no_sources" else "Fix the clips above, or name your stems so Vibelton can place them."
                result["details"] = details
                return result
            return _finish(code, title, body, next_step, text, context)
    return _finish("unexpected", "Something went wrong", "Vibelton hit a problem it doesn't recognise.",
                   "Try again; if it keeps happening, open Details and share it.", text, context)


def _finish(code: str, title: str, body: str, next_step: str, raw: str, context: dict[str, Any]) -> dict[str, Any]:
    placed, planned = context.get("placed"), context.get("planned")
    lead = ""
    if placed is not None and planned:
        lead = f"{placed} of {planned} clips placed. " if placed else "Nothing was placed in Live. "
        if placed:
            next_step = "Undo is available and removes exactly those clips."
    return {"code": code, "title": title, "message": (lead + body).strip(), "next_step": next_step,
            "undo_available": bool(placed), "raw": home_to_tilde(raw)[:2000], "severity": "error"}


def explain_job(job: dict[str, Any], planned: int | None) -> dict[str, Any] | None:
    """Explanation for a finished job that did not fully succeed (None when it did)."""
    execution = job.get("execution") or {}
    status = job.get("status")
    if status == "Applied":
        return None
    raw = job.get("error") or execution.get("error") or status or ""
    placed = len(execution.get("created_copies") or [])
    verb = "undo" if job.get("rollback_of") else "scaffold"
    result = explain(raw, {"placed": placed if not job.get("rollback_of") else None,
                           "planned": planned if not job.get("rollback_of") else None})
    if job.get("rollback_of"):
        result["title"] = "Undo didn't finish" if result["code"] in ("unexpected", "readback_mismatch") else result["title"]
        result["message"] = ("Undo stopped part-way. " + result["message"]).strip()
    elif status == "Interrupted" and result["code"] == "unexpected":
        result = explain("Live restarted before the production job", {})
    result["action"] = verb
    return result
