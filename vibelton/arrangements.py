"""Phase 3A deterministic, planning-only House arrangement templates.

This module has no queue or Ableton mutation access.  It turns qualified Live
state into reviewable bar maps, preserving the Phase 2 locator *intent* while
leaving clip placement and locator creation to later approved phases.
"""
from __future__ import annotations

import copy
import math
from typing import Any

from . import song_sketch


HOUSE_TEMPLATE_FAMILY_ID = "classic-house-arrangements/v1"
VARIANT_IDS = ("streaming-edit", "club-version", "dj-extended-mix")
DNB_TEMPLATE_FAMILY_ID = "drum-and-bass-arrangements/v1"
DNB_VARIANT_IDS = ("dnb-quick-cut", "dnb-rolling-club", "dnb-extended-journey")
OTHER_GENRE_VARIANTS = {
    "Techno": ("techno-hypnotic", "techno-peak-time", "techno-extended-dj"),
    "UK Garage": ("ukg-compact", "ukg-vocal-club", "ukg-extended-shuffle"),
    "Hip Hop": ("hiphop-tight-beat", "hiphop-verse-hook", "hiphop-instrumental"),
    "Disco / Nu-disco": ("disco-radio-groove", "disco-club-lift", "disco-extended-mix"),
}
SUPPORTED_GENRES = ("House", "Drum & Bass", *OTHER_GENRE_VARIANTS)
GENRE_VARIANTS = {"House": VARIANT_IDS, "Drum & Bass": DNB_VARIANT_IDS, **OTHER_GENRE_VARIANTS}
ROLE_ORDER = tuple(name for _group, name, _kind in song_sketch.TRACKS)

# The seven Phase 2 locator definitions are deliberately retained as semantic
# anchors.  Phase 3A adapts their bar positions and visible labels to each
# variant; it does not create cue points.
LOCATOR_ANCHORS = (
    "INTRO", "GROOVE", "MAIN GROOVE", "TENSION", "BREAKDOWN", "MAIN SECTION", "DJ OUTRO",
)

_VARIANTS = {
    "streaming-edit": {
        "name": "Streaming edit",
        "target_duration": "approximately 3:15",
        "target_seconds": 195,
        "sections": (
            ("intro", "INTRO", 8, 2, "Establish pulse quickly", ("Kick", "Hats", "Atmosphere"), "Introduce the groove with a short filtered pickup."),
            ("groove", "GROOVE", 16, 4, "Establish the main dancefloor loop", ("Kick", "Snare / Clap", "Hats", "Bass", "Chords"), "Open percussion and bass over the first two bars."),
            ("main_groove", "MAIN GROOVE", 24, 6, "Deliver the first concise hook statement", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Lead", "Hook"), "Use a four-bar hook reveal; keep the loop recognisable."),
            ("tension", "TENSION", 8, 5, "Create a compact reset before the break", ("Kick", "Hats", "Percussion", "Bass", "FX / Risers"), "Reduce harmony, then suggest a riser into the breakdown."),
            ("breakdown", "BREAKDOWN", 16, 3, "Give contrast and reset anticipation", ("Chords", "Lead", "Hook", "Atmosphere", "Vocal", "FX / Risers"), "Strip drums first, then return the kick in the final bar."),
            ("main_section", "MAIN SECTION", 24, 8, "Deliver the final peak efficiently", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Lead", "Hook", "Atmosphere", "Vocal", "FX / Risers"), "Reintroduce the full loop, reserving a final fill suggestion for the last two bars."),
            ("outro", "DJ OUTRO", 8, 3, "Exit cleanly for a streaming ending", ("Kick", "Hats", "Bass", "Atmosphere", "FX / Risers"), "Remove hook and harmony, then suggest a short tail."),
        ),
    },
    "club-version": {
        "name": "Club version",
        "target_duration": "approximately 4:39",
        # Nine complete 16-bar source loops at the 124 BPM Phase 3B
        # benchmark.  Unlike 140 bars, this never requires Live to trim an
        # overlapping final copy.
        "target_seconds": 278.7096774193548,
        "sections": (
            ("intro", "INTRO", 16, 2, "Establish a mixable opening", ("Kick", "Hats", "Percussion", "Atmosphere", "FX / Risers"), "Bring bass in after an eight-bar DJ-friendly lead-in."),
            ("groove", "GROOVE", 16, 4, "Lock the core groove before the hook", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords"), "Suggest gradual percussion and chord additions."),
            ("main_groove", "MAIN GROOVE", 32, 6, "Make the first full club statement", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Lead", "Hook", "Atmosphere"), "Cycle the existing 16-bar loop with subtraction on the second pass."),
            ("tension", "TENSION", 16, 5, "Build anticipation without new material", ("Kick", "Hats", "Percussion", "Bass", "FX / Risers"), "Reduce chord density, then suggest a riser into the break."),
            ("breakdown", "BREAKDOWN", 16, 3, "Reset energy and spotlight available musical material", ("Chords", "Lead", "Hook", "Atmosphere", "Vocal", "FX / Risers"), "Hold back the kick until the final two bars."),
            ("main_section", "MAIN SECTION", 32, 8, "Sustain the final peak for the floor", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Lead", "Hook", "Atmosphere", "Vocal", "FX / Risers"), "Return full groove, then subtract the hook for the final eight bars."),
            ("outro", "DJ OUTRO", 16, 3, "Provide a practical mix-out", ("Kick", "Hats", "Percussion", "Bass", "Atmosphere", "FX / Risers"), "Remove musical hooks first and leave a stable rhythmic bed."),
        ),
    },
    "dj-extended-mix": {
        "name": "DJ extended mix",
        "target_duration": "approximately 6:00",
        "target_seconds": 360,
        "sections": (
            ("intro", "INTRO", 32, 2, "Provide a long, mixable opening", ("Kick", "Hats", "Percussion", "Atmosphere", "FX / Risers"), "Keep the first 16 bars sparse; introduce bass only in the second half."),
            ("groove", "GROOVE", 32, 4, "Develop the core loop for beat matching", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords"), "Add one role at a time across the first 16 bars; reuse the loop thereafter."),
            ("main_groove", "MAIN GROOVE", 48, 6, "Create a long first peak with controlled variation", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Lead", "Hook", "Atmosphere"), "Use subtraction and role rotation rather than new melodies."),
            ("tension", "TENSION", 16, 5, "Clear space for the central break", ("Kick", "Hats", "Percussion", "Bass", "FX / Risers"), "Pull harmony and hook; suggest a gradual transition effect."),
            ("breakdown", "BREAKDOWN", 24, 3, "Create the extended contrast section", ("Chords", "Lead", "Hook", "Atmosphere", "Vocal", "FX / Risers"), "Let existing atmosphere and hook lead; stage the drum return over the final eight bars."),
            ("main_section", "MAIN SECTION", 24, 8, "Deliver a final, focused peak", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Lead", "Hook", "Atmosphere", "Vocal", "FX / Risers"), "Return the complete loop, then remove lead or hook for the handoff."),
            ("outro", "DJ OUTRO", 10, 3, "Leave a concise but usable final mix-out", ("Kick", "Hats", "Percussion", "Bass", "Atmosphere", "FX / Risers"), "Strip musical material in layers while retaining the beat."),
        ),
    },
}


def _duration_seconds(bars: int, bpm: float) -> float:
    return round(bars * 4.0 * 60.0 / bpm, 3)


def _validate_bpm(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 40 <= value <= 240:
        raise ValueError("Project BPM must be a finite value between 40 and 240")
    return float(value)


def phrase_unit(total_bars: int, section_count: int) -> int:
    """Phrase length every section boundary snaps to: 8 bars, or 4 for short arrangements."""
    return 8 if total_bars >= 96 and total_bars // 8 >= section_count else 4


def _scaled_section_bars(sections: tuple[tuple[Any, ...], ...], total_bars: int) -> list[int]:
    """Scale a template's proportions to the duration implied by project BPM.

    Every section is a whole number of phrases (see ``phrase_unit``), so every boundary
    falls on a 4- or 8-bar phrase.  The total moves to the nearest phrase multiple.
    """
    unit = phrase_unit(total_bars, len(sections))
    total_units = max(len(sections), round(total_bars / unit))
    source_total = sum(int(section[2]) for section in sections)
    scaled = [int(section[2]) * total_units / source_total for section in sections]
    units = [max(1, int(math.floor(value))) for value in scaled]
    remainder = total_units - sum(units)
    order = sorted(range(len(sections)), key=lambda item: (scaled[item] - math.floor(scaled[item]), -item), reverse=True)
    for index in order[:max(0, remainder)]:
        units[index] += 1
    for index in reversed(order):  # a minimum of one phrase per section can overshoot; take it back from the largest
        while sum(units) > total_units and units[index] > 1:
            units[index] -= 1
    return [value * unit for value in units]


def _role_inventory(state: dict[str, Any], production: dict[str, Any], confirmed_roles: dict[str, Any] | None = None) -> dict[str, Any]:
    live_tracks = {item.get("id"): item for item in state.get("tracks", []) if isinstance(item, dict)}
    assigned: dict[str, dict[str, Any]] = {}
    unassigned: list[dict[str, Any]] = []
    for track in production.get("tracks", []):
        if not isinstance(track, dict):
            continue
        role, confidence, reason = song_sketch._role_for(track)
        source = "suggested"
        if confirmed_roles and track.get("id") in confirmed_roles.get("roles", {}):
            role = confirmed_roles["roles"][track["id"]]
            confidence, reason, source = 1.0, "User confirmed role" if role else "User chose Unknown / leave unchanged", "confirmed"
        clips = copy.deepcopy(track.get("arrangement_clips", []))
        clips.extend(copy.deepcopy(live_tracks.get(track.get("id"), {}).get("clips", [])))
        row = {"track_id": track.get("id"), "track_name": track.get("name"), "track_type": track.get("type"),
               "role": role, "confidence": confidence, "reason": reason, "role_source": source, "existing_clips": clips}
        if role and role not in assigned:
            assigned[role] = row
        elif role and confidence > assigned[role]["confidence"]:
            unassigned.append(assigned[role])
            assigned[role] = row
        else:
            unassigned.append(row)
    available = [assigned[role] for role in ROLE_ORDER if role in assigned]
    return {
        "likely_roles": available,
        "unassigned_tracks": unassigned,
        "missing_roles": [role for role in ROLE_ORDER if role not in assigned],
        "material_summary": {
            "arrangement_or_session_clip_count": sum(len(row["existing_clips"]) for row in available + unassigned),
            "reuse_only": True,
            "new_melodies_or_musical_ideas": "not permitted",
        },
    }


def build_house_options(state: dict[str, Any], production: dict[str, Any], confirmed_roles: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return three validated, non-executable House structures for review."""
    bpm = _validate_bpm(production.get("tempo", state.get("tempo")))
    if production.get("metre") != [4, 4]:
        raise ValueError("Phase 3A House templates currently require 4/4")
    locator_definitions = song_sketch.classic_house_preset()["locators"]
    variants: list[dict[str, Any]] = []
    for variant_id in VARIANT_IDS:
        definition = _VARIANTS[variant_id]
        sections = []
        cursor = 0
        total_bars = int(round(definition["target_seconds"] * bpm / 240.0))
        for (section_id, anchor, _nominal_bars, energy, purpose, roles, transition), bars in zip(
                definition["sections"], _scaled_section_bars(definition["sections"], total_bars)):
            section = {
                "id": section_id, "name": anchor.title(), "start_bar": cursor, "end_bar": cursor + bars,
                "bar_count": bars, "energy_level": energy, "purpose": purpose,
                "active_track_roles": list(roles), "transition_suggestion": transition,
            }
            sections.append(section)
            cursor += bars
        locators = [
            {"source_name": locator_definitions[index]["name"], "source_time": locator_definitions[index]["time"],
             "name": "%s · %d bars" % (anchor, section["bar_count"]), "bar": section["start_bar"],
             "time": float(section["start_bar"] * 4), "section_id": section["id"]}
            for index, (anchor, section) in enumerate(zip(LOCATOR_ANCHORS, sections))
        ]
        variants.append({
            "id": variant_id, "name": definition["name"], "target_duration": definition["target_duration"],
            "target_duration_seconds": definition["target_seconds"],
            "total_bars": cursor, "approximate_duration_seconds": _duration_seconds(cursor, bpm),
            "phrase_bars": phrase_unit(total_bars, len(sections)),
            "sections": sections, "intended_locators": locators,
        })
    return {
        "template_family_id": HOUSE_TEMPLATE_FAMILY_ID,
        "genre": "House", "metre": [4, 4], "bpm": bpm,
        "duration_method": "bars × 4 beats × 60 ÷ project BPM; durations are estimates separate from bar structure",
        "source_locator_definitions": locator_definitions,
        "role_inventory": _role_inventory(state, production, confirmed_roles),
        "assumptions": [
            "Plans reuse only existing clips or musical material; they do not generate melodies, notes, or new musical ideas.",
            "Section roles are planning suggestions, not mute, copy, move, extend, or create-clip operations.",
            "Locator positions are intended metadata only. Phase 3B must check locator_range and create them only after approved arrangement content establishes sufficient song length.",
        ],
        "variants": variants,
        "execution_available": False,
        "selection_required": "Select one variant and explicitly approve it before Phase 3B may create any execution plan.",
    }


def validate_options(options: dict[str, Any]) -> None:
    """Fail closed if an internal template change breaks a bar-map invariant."""
    if options.get("metre") != [4, 4] or _validate_bpm(options.get("bpm")) != options.get("bpm"):
        raise ValueError("Invalid arrangement timing")
    variants = options.get("variants")
    expected = GENRE_VARIANTS.get(options.get("genre"), ())
    if not isinstance(variants, list) or [item.get("id") for item in variants] != list(expected):
        raise ValueError("Arrangement variants are incomplete or out of order")
    totals: set[int] = set()
    for variant in variants:
        cursor = 0
        phrase = variant.get("phrase_bars")
        if phrase not in (4, 8):
            raise ValueError("Arrangement variants must declare a 4- or 8-bar phrase length")
        for section in variant.get("sections", []):
            if section.get("start_bar") != cursor or section.get("end_bar") != cursor + section.get("bar_count", 0):
                raise ValueError("Arrangement sections must be contiguous, non-overlapping, and bar-aligned")
            if not isinstance(section.get("bar_count"), int) or section["bar_count"] <= 0:
                raise ValueError("Arrangement sections require positive whole bar counts")
            if section["start_bar"] % phrase or section["end_bar"] % phrase:
                raise ValueError("Arrangement section boundaries must fall on %d-bar phrases" % phrase)
            cursor = section["end_bar"]
        if cursor != variant.get("total_bars") or len(variant.get("intended_locators", [])) != 7:
            raise ValueError("Arrangement locator or duration map is invalid")
        if variant.get("approximate_duration_seconds") != _duration_seconds(cursor, options["bpm"]):
            raise ValueError("Arrangement duration does not match project BPM")
        totals.add(cursor)
    if len(totals) != 3:
        raise ValueError("Arrangement variants must have genuinely different structures")


_DNB_VARIANTS = {
    "dnb-quick-cut": {
        "name": "Quick cut", "target_seconds": 180,
        "sections": (
            ("intro", "INTRO", 8, 2, "Establish a brief atmospheric hook", ("Atmosphere", "Hook", "FX / Risers"), "Hint at the break before the first drop."),
            ("build", "BUILD", 8, 5, "Raise anticipation", ("Hats", "Percussion", "Bass", "FX / Risers"), "Introduce drum fragments without adding new notes."),
            ("drop_one", "FIRST DROP", 32, 8, "State the main break and bass idea", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Hook"), "Use the existing break and bass together."),
            ("switch", "SWITCH", 16, 6, "Change the rhythmic focus", ("Kick", "Snare / Clap", "Percussion", "Bass", "Lead"), "Subtract a drum layer or rotate existing parts."),
            ("breakdown", "BREAKDOWN", 16, 2, "Create contrast", ("Atmosphere", "Chords", "Vocal", "Hook"), "Pull the full drums and low end."),
            ("drop_two", "FINAL DROP", 32, 9, "Return with a stronger role combination", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Lead", "Hook"), "Bring back the break with a different existing layer balance."),
            ("outro", "OUTRO", 8, 3, "Close cleanly", ("Kick", "Snare / Clap", "Atmosphere", "FX / Risers"), "Remove bass and hook before the final tail."),
        ),
    },
    "dnb-rolling-club": {
        "name": "Rolling club", "target_seconds": 240,
        "sections": (
            ("intro", "INTRO", 16, 2, "Give a DJ a mixable opening", ("Hats", "Atmosphere", "FX / Risers"), "Bring in break fragments over an existing texture."),
            ("build", "BUILD", 16, 5, "Prepare the first impact", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass"), "Build density in eight-bar steps."),
            ("drop_one", "FIRST DROP", 48, 8, "Let the break and bass roll", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Hook"), "Keep the groove anchor, varying role presence."),
            ("switch", "SWITCH", 24, 6, "Change the conversation", ("Kick", "Snare / Clap", "Bass", "Lead", "Vocal"), "Trade existing hook space for a bass answer."),
            ("breakdown", "BREAKDOWN", 24, 2, "Reset the floor", ("Atmosphere", "Chords", "Vocal", "Hook"), "Leave room before the re-entry."),
            ("drop_two", "SECOND DROP", 48, 9, "Deliver a second peak", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Lead", "Hook"), "Re-enter with the strongest existing break variation."),
            ("outro", "DJ OUTRO", 16, 3, "Provide a mix-out", ("Kick", "Snare / Clap", "Hats", "Percussion", "Atmosphere"), "Strip bass and melodic material first."),
        ),
    },
    "dnb-extended-journey": {
        "name": "Extended journey", "target_seconds": 300,
        "sections": (
            ("intro", "INTRO", 32, 2, "Build a long atmospheric runway", ("Atmosphere", "Chords", "FX / Risers"), "Tease an existing break in the second half."),
            ("build", "BUILD", 24, 5, "Make the first drop earned", ("Hats", "Percussion", "Bass", "FX / Risers"), "Add rhythmic layers gradually."),
            ("drop_one", "FIRST DROP", 64, 8, "Establish a sustained rolling section", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Hook"), "Use eight-bar subtraction and fills from existing clips."),
            ("switch", "MID-TRACK SWITCH", 32, 6, "Change the groove perspective", ("Kick", "Snare / Clap", "Percussion", "Bass", "Lead", "Vocal"), "Thin the drums and make room for a different existing part."),
            ("breakdown", "BREAKDOWN", 32, 2, "Create a spacious reset", ("Atmosphere", "Chords", "Vocal", "Hook"), "Hold the full rhythm back until the final phrase."),
            ("drop_two", "FINAL DROP", 64, 9, "Return for the final peak", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Lead", "Hook"), "Recombine existing parts and vary the last pass."),
            ("outro", "DJ OUTRO", 24, 3, "Give a long mix-out", ("Kick", "Snare / Clap", "Hats", "Atmosphere"), "Remove the musical hooks in layers."),
        ),
    },
}


def build_dnb_options(state: dict[str, Any], production: dict[str, Any], confirmed_roles: dict[str, Any] | None = None) -> dict[str, Any]:
    """Planning-only Drum & Bass structures; no Live execution path is implied."""
    bpm = _validate_bpm(production.get("tempo", state.get("tempo")))
    if production.get("metre") != [4, 4]:
        raise ValueError("Drum & Bass templates currently require 4/4")
    variants = []
    for variant_id in DNB_VARIANT_IDS:
        definition = _DNB_VARIANTS[variant_id]
        total_bars = round(definition["target_seconds"] * bpm / 240.0)
        cursor = 0
        sections = []
        for (section_id, name, _nominal, energy, purpose, roles, transition), bars in zip(
                definition["sections"], _scaled_section_bars(definition["sections"], total_bars)):
            sections.append({"id": section_id, "name": name.title(), "start_bar": cursor,
                             "end_bar": cursor + bars, "bar_count": bars, "energy_level": energy,
                             "purpose": purpose, "active_track_roles": list(roles),
                             "transition_suggestion": transition})
            cursor += bars
        locators = [{"name": "%s · %d bars" % (section["name"].upper(), section["bar_count"]),
                     "bar": section["start_bar"], "time": float(section["start_bar"] * 4),
                     "section_id": section["id"]} for section in sections]
        variants.append({"id": variant_id, "name": definition["name"],
                         "target_duration": "approximately %d:%02d" % divmod(definition["target_seconds"], 60),
                         "target_duration_seconds": definition["target_seconds"],
                         "total_bars": cursor, "approximate_duration_seconds": _duration_seconds(cursor, bpm),
                         "phrase_bars": phrase_unit(total_bars, len(sections)),
                         "sections": sections, "intended_locators": locators})
    return {"template_family_id": DNB_TEMPLATE_FAMILY_ID, "genre": "Drum & Bass", "metre": [4, 4],
            "bpm": bpm, "duration_method": "bars × 4 beats × 60 ÷ project BPM",
            "source_locator_definitions": [],
            "role_inventory": _role_inventory(state, production, confirmed_roles),
            "assumptions": ["This is a structure proposal based on the user's genre choice, not audio genre detection.",
                            "The plan reuses existing material and does not create new notes or melodies.",
                            "Section roles are suggestions. Native locators and clip execution are unavailable for Drum & Bass."],
            "variants": variants, "execution_available": False,
            "selection_required": "Choose one structure for review; Drum & Bass Live execution is not yet supported."}


# Each style has its own section logic. The three variants adjust duration,
# proportions, and peak/break energy; these are proposals, never bridge actions.
_OTHER_GENRES = {
    "Techno": {
        "sections": (
            ("intro", "DJ intro", 2, "Give a mixable opening", ("Kick", "Hats", "Atmosphere"), "Introduce percussion in layers."),
            ("pulse", "Pulse", 4, "Establish the central rhythm", ("Kick", "Hats", "Percussion", "Bass"), "Bring in the bass pulse."),
            ("drive", "Drive", 7, "Sustain the first full groove", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Hook"), "Rotate existing drum roles."),
            ("tension", "Tension", 6, "Increase pressure", ("Kick", "Hats", "Bass", "FX / Risers"), "Subtract elements before the break."),
            ("break", "Break", 2, "Reset density", ("Atmosphere", "Hook", "FX / Risers"), "Hold the kick back."),
            ("peak", "Peak", 9, "Return to the strongest groove", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Hook", "FX / Risers"), "Recombine existing parts."),
            ("outro", "DJ outro", 3, "Provide a steady mix-out", ("Kick", "Hats", "Percussion", "Atmosphere"), "Remove the hook and bass in stages."),
        ),
        "variants": (
            ("techno-hypnotic", "Hypnotic", 300, (24, 32, 64, 32, 16, 64, 24), -1),
            ("techno-peak-time", "Peak time", 330, (24, 24, 64, 32, 24, 80, 24), 1),
            ("techno-extended-dj", "Extended DJ", 390, (48, 48, 80, 32, 24, 80, 48), 0),
        ),
    },
    "UK Garage": {
        "sections": (
            ("intro", "Skippy intro", 2, "Hint at the two-step pocket", ("Hats", "Percussion", "Atmosphere"), "Tease a shuffled drum fragment."),
            ("groove", "First groove", 5, "Set the syncopated bass and drum relationship", ("Kick", "Snare / Clap", "Hats", "Bass", "Chords"), "Bring in the bass after the first phrase."),
            ("hook", "Hook", 8, "Deliver the main melodic idea", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Hook", "Vocal"), "Keep the existing hook clear."),
            ("switch", "Rhythm switch", 6, "Shift the pocket", ("Kick", "Snare / Clap", "Percussion", "Bass", "Lead"), "Thin the hats or rotate percussion."),
            ("break", "Vocal break", 3, "Make breathing room", ("Chords", "Vocal", "Atmosphere", "Hook"), "Pull the bass and full drums."),
            ("return", "Final return", 9, "Bring back the fullest groove", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Hook", "Vocal"), "Reintroduce existing parts in layers."),
            ("outro", "Outro", 3, "End or mix out", ("Kick", "Snare / Clap", "Hats", "Bass"), "Strip the vocal and hook."),
        ),
        "variants": (
            ("ukg-compact", "Compact 2-step", 180, (8, 16, 24, 8, 16, 24, 8), 0),
            ("ukg-vocal-club", "Vocal club", 240, (16, 24, 32, 16, 24, 40, 16), 1),
            ("ukg-extended-shuffle", "Extended shuffle", 300, (24, 32, 48, 24, 24, 48, 24), 0),
        ),
    },
    "Hip Hop": {
        "sections": (
            ("intro", "Intro", 2, "Introduce the beat or sample texture", ("Chords", "Atmosphere", "Hook"), "Keep the opening concise."),
            ("verse_one", "Verse one", 5, "Leave space for the first vocal idea", ("Kick", "Snare / Clap", "Hats", "Bass", "Chords", "Vocal"), "Use a stable beat with small changes."),
            ("hook_one", "Hook one", 8, "Make the refrain larger", ("Kick", "Snare / Clap", "Hats", "Bass", "Chords", "Hook", "Vocal"), "Bring back the existing hook."),
            ("verse_two", "Verse two", 5, "Return with a changed backing", ("Kick", "Snare / Clap", "Bass", "Chords", "Lead", "Vocal"), "Subtract or replace one existing layer."),
            ("bridge", "Bridge", 3, "Create lyrical or instrumental contrast", ("Chords", "Atmosphere", "Vocal", "Hook"), "Thin the drums and low end."),
            ("final_hook", "Final hook", 9, "Give the refrain its last return", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Hook", "Vocal"), "Use the fullest existing combination."),
            ("outro", "Outro", 2, "Close the story", ("Chords", "Atmosphere", "Hook"), "Remove the beat in stages."),
        ),
        "variants": (
            ("hiphop-tight-beat", "Tight beat", 150, (4, 16, 8, 16, 8, 8, 4), 0),
            ("hiphop-verse-hook", "Verse / hook", 205, (8, 24, 8, 24, 8, 16, 8), 1),
            ("hiphop-instrumental", "Instrumental journey", 240, (8, 32, 16, 24, 16, 24, 8), 0),
        ),
    },
    "Disco / Nu-disco": {
        "sections": (
            ("intro", "Intro", 2, "Set a warm dancefloor pulse", ("Kick", "Hats", "Percussion", "Chords"), "Introduce the groove quickly."),
            ("groove", "Groove", 5, "Bring bass and chords together", ("Kick", "Snare / Clap", "Hats", "Bass", "Chords"), "Let the bass establish movement."),
            ("refrain", "Refrain", 8, "Present the hook", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Hook", "Vocal"), "Open up the existing melodic layers."),
            ("verse", "Verse / reset", 5, "Reduce density without losing the groove", ("Kick", "Snare / Clap", "Hats", "Bass", "Chords", "Vocal"), "Pull back the hook."),
            ("break", "Breakdown", 3, "Create lift for the return", ("Chords", "Atmosphere", "Vocal", "FX / Risers"), "Drop drums briefly."),
            ("final_refrain", "Final refrain", 9, "Bring back the full dancefloor idea", ("Kick", "Snare / Clap", "Hats", "Percussion", "Bass", "Chords", "Hook", "Vocal"), "Return all existing groove anchors."),
            ("outro", "Outro", 3, "Give a clean ending or mix-out", ("Kick", "Hats", "Bass", "Chords"), "Remove the refrain first."),
        ),
        "variants": (
            ("disco-radio-groove", "Radio groove", 185, (8, 16, 24, 16, 8, 24, 8), 0),
            ("disco-club-lift", "Club lift", 240, (16, 24, 32, 24, 16, 32, 16), 1),
            ("disco-extended-mix", "Extended mix", 300, (24, 32, 48, 32, 16, 48, 24), 0),
        ),
    },
}


def build_other_genre_options(genre: str, state: dict[str, Any], production: dict[str, Any],
                              confirmed_roles: dict[str, Any] | None = None) -> dict[str, Any]:
    if genre not in _OTHER_GENRES:
        raise ValueError("Unsupported arrangement genre")
    bpm = _validate_bpm(production.get("tempo", state.get("tempo")))
    if production.get("metre", state.get("metre")) != [4, 4]:
        raise ValueError("%s templates currently require 4/4" % genre)
    definition = _OTHER_GENRES[genre]
    variants = []
    for variant_id, name, target_seconds, weights, peak_delta in definition["variants"]:
        total_bars = round(target_seconds * bpm / 240.0)
        weighted = tuple((section[0], section[1], weight) for section, weight in zip(definition["sections"], weights))
        bars_by_section = _scaled_section_bars(weighted, total_bars)
        cursor = 0
        sections = []
        for (section_id, label, energy, purpose, roles, transition), bars in zip(definition["sections"], bars_by_section):
            adjusted_energy = max(1, min(10, energy + peak_delta)) if energy >= 8 else energy
            sections.append({"id": section_id, "name": label, "start_bar": cursor, "end_bar": cursor + bars,
                             "bar_count": bars, "energy_level": adjusted_energy, "purpose": purpose,
                             "active_track_roles": list(roles), "transition_suggestion": transition})
            cursor += bars
        locators = [{"name": "%s · %d bars" % (section["name"].upper(), section["bar_count"]),
                     "bar": section["start_bar"], "time": float(section["start_bar"] * 4),
                     "section_id": section["id"]} for section in sections]
        variants.append({"id": variant_id, "name": name,
                         "target_duration": "approximately %d:%02d" % divmod(target_seconds, 60),
                         "target_duration_seconds": target_seconds, "total_bars": cursor,
                         "approximate_duration_seconds": _duration_seconds(cursor, bpm),
                         "phrase_bars": phrase_unit(total_bars, len(sections)),
                         "sections": sections, "intended_locators": locators})
    return {"template_family_id": genre.lower().replace(" / ", "-").replace(" ", "-") + "-arrangements/v1",
            "genre": genre, "metre": [4, 4], "bpm": bpm,
            "duration_method": "bars × 4 beats × 60 ÷ project BPM",
            "source_locator_definitions": [], "role_inventory": _role_inventory(state, production, confirmed_roles),
            "assumptions": ["This is a structure proposal based on the user's genre choice, not audio genre detection.",
                            "The plan reuses existing material and does not create new notes or melodies.",
                            "Section roles are suggestions. Native locators and clip execution are unavailable for this style."],
            "variants": variants, "execution_available": False,
            "selection_required": "Choose one structure for review; Live execution is not yet supported for this style."}


def build_options(genre: str, state: dict[str, Any], production: dict[str, Any],
                  confirmed_roles: dict[str, Any] | None = None) -> dict[str, Any]:
    if genre == "House":
        return build_house_options(state, production, confirmed_roles)
    if genre == "Drum & Bass":
        return build_dnb_options(state, production, confirmed_roles)
    return build_other_genre_options(genre, state, production, confirmed_roles)


def genre_for_variant(variant_id: str) -> str:
    for genre, ids in GENRE_VARIANTS.items():
        if variant_id in ids:
            return genre
    raise ValueError("Choose a supported arrangement variant")
