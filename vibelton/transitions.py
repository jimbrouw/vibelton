"""Shared deterministic MIDI transition generators for Song Maker, Ideas, and Composition Lab.

Provides snare rolls, pre-drop kick dropouts, crash hits on downbeats, tom fills,
reverse cymbals, riser sweeps, and section-aware transition orchestration.
"""
from __future__ import annotations

from typing import Any


def snare_roll(
    bar_start_beat: float,
    bars: int = 2,
    velocity_start: int = 54,
    velocity_end: int = 118,
    snare_pitch: int = 38,
) -> list[dict[str, Any]]:
    """Generate an accelerating 8th -> 16th -> 32nd snare roll across `bars` bars (4 beats/bar)."""
    total_beats = max(1.0, float(bars) * 4.0)
    half_point = total_beats * 0.5
    three_quarter_point = total_beats * 0.75

    events: list[tuple[float, float]] = []
    pos = 0.0
    while pos < total_beats - 0.001:
        if pos < half_point:
            step = 0.5
        elif pos < three_quarter_point:
            step = 0.25
        else:
            step = 0.125
        events.append((pos, min(0.11, step * 0.8)))
        pos = round(pos + step, 5)

    n = max(1, len(events) - 1)
    notes: list[dict[str, Any]] = []
    for idx, (offset, dur) in enumerate(events):
        frac = idx / n if n > 0 else 1.0
        vel = int(round(velocity_start + frac * (velocity_end - velocity_start)))
        vel = max(1, min(127, vel))
        notes.append({
            "pitch": int(snare_pitch),
            "start": round(float(bar_start_beat) + offset, 4),
            "duration": round(dur, 4),
            "velocity": vel,
            "mute": False,
        })
    return notes


def kick_drop(
    drum_notes: list[dict[str, Any]],
    drop_start_beat: float,
    drop_length_beats: float = 4.0,
    kick_pitch: int = 36,
) -> list[dict[str, Any]]:
    """Strip kick notes (pitch 36) within `[drop_start_beat, drop_start_beat + drop_length_beats)`."""
    window_start = float(drop_start_beat)
    window_end = window_start + max(0.0, float(drop_length_beats))
    kept: list[dict[str, Any]] = []
    for note in drum_notes:
        pitch = int(note.get("pitch", 0))
        start = float(note.get("start", 0.0))
        if pitch == int(kick_pitch) and window_start - 0.001 <= start < window_end - 0.001:
            continue
        kept.append(dict(note))
    return kept


def crash_on_one(
    section_start_beat: float = 0.0,
    velocity: int = 102,
    crash_pitch: int = 49,
) -> list[dict[str, Any]]:
    """Return a crash cymbal hit (MIDI 49) on beat 1 of a drop/main section."""
    return [{
        "pitch": int(crash_pitch),
        "start": round(float(section_start_beat), 4),
        "duration": 0.75,
        "velocity": max(1, min(127, int(velocity))),
        "mute": False,
    }]


def tom_fill(
    bar_start_beat: float,
    bar_length: float = 4.0,
) -> list[dict[str, Any]]:
    """Descending tom fill (pitches 47, 45, 43, 41) over the final 2 beats of a bar."""
    fill_start = float(bar_start_beat) + max(0.0, float(bar_length) - 2.0)
    pitches = (47, 45, 43, 41)
    velocities = (90, 96, 102, 110)
    notes: list[dict[str, Any]] = []
    for idx, (pitch, vel) in enumerate(zip(pitches, velocities)):
        notes.append({
            "pitch": pitch,
            "start": round(fill_start + idx * 0.5, 4),
            "duration": 0.35,
            "velocity": vel,
            "mute": False,
        })
    return notes


def riser_sweep(
    section_start_beat: float = 0.0,
    length_beats: float = 16.0,
    pitch: int = 72,
) -> list[dict[str, Any]]:
    """Generate a rising chromatic/stepwise tension sweep leading to the end of a build section."""
    total = max(2.0, float(length_beats))
    steps = max(2, int(total // 2))
    step_len = total / steps
    notes: list[dict[str, Any]] = []
    for idx in range(steps):
        frac = idx / max(1, steps - 1)
        vel = max(48, min(124, int(round(56 + frac * 62))))
        semitone_offset = int(round(frac * 12))
        notes.append({
            "pitch": max(0, min(127, int(pitch) + semitone_offset)),
            "start": round(float(section_start_beat) + idx * step_len, 4),
            "duration": round(max(0.25, step_len * 0.92), 4),
            "velocity": vel,
            "mute": False,
        })
    return notes


def reverse_cymbal(
    bar_start_beat: float,
    bar_length: float = 4.0,
    pitch: int = 55,
) -> list[dict[str, Any]]:
    """Insert a reverse cymbal / splash swell leading into the next downbeat."""
    start = float(bar_start_beat) + max(0.0, float(bar_length) - 2.0)
    return [{
        "pitch": int(pitch),
        "start": round(start, 4),
        "duration": round(min(1.95, float(bar_length) * 0.48), 4),
        "velocity": 94,
        "mute": False,
    }]


def kick_choke(
    drum_notes: list[dict[str, Any]],
    choke_beat: float,
    window_beats: float = 1.0,
) -> list[dict[str, Any]]:
    """Mute/strip all drum hits in a short pre-drop choke window `[choke_beat, choke_beat + window_beats)`."""
    w0 = float(choke_beat)
    w1 = w0 + max(0.0, float(window_beats))
    return [
        dict(n)
        for n in drum_notes
        if not (w0 - 0.001 <= float(n.get("start", 0.0)) < w1 - 0.001)
    ]


def apply_section_transitions(
    notes_by_role: dict[str, list[dict[str, Any]]],
    section_kind: str,
    genre: str = "house",
    section_length_beats: float = 32.0,
) -> dict[str, list[dict[str, Any]]]:
    """Apply deterministic musical transitions to a section's role notes dictionary."""
    out: dict[str, list[dict[str, Any]]] = {
        role: [dict(n) for n in notes] for role, notes in (notes_by_role or {}).items()
    }
    kind = str(section_kind or "main").lower().strip()
    total = max(4.0, float(section_length_beats))
    drums = list(out.get("drums", []))

    if kind == "build":
        # Strip kicks in final bar (or final 4 beats) and add snare roll build
        drop_len = min(8.0, max(4.0, total * 0.25))
        drop_start = max(0.0, total - drop_len)
        drums = kick_drop(drums, drop_start_beat=drop_start, drop_length_beats=drop_len)
        roll_bars = 2 if total >= 8.0 else 1
        roll_start = max(0.0, total - roll_bars * 4.0)
        drums.extend(snare_roll(bar_start_beat=roll_start, bars=roll_bars))
        out["drums"] = sorted(drums, key=lambda n: (float(n.get("start", 0.0)), int(n.get("pitch", 0))))
    elif kind in ("drop", "main", "drop_2", "main_2", "peak", "peak_2"):
        # Crash on beat 1.0 and tom fill at end of section
        has_crash_on_one = any(
            int(n.get("pitch", 0)) == 49 and abs(float(n.get("start", 0.0))) < 0.05
            for n in drums
        )
        if not has_crash_on_one:
            drums.extend(crash_on_one(0.0))
        if total >= 8.0:
            last_bar_start = total - 4.0
            drums = kick_drop(drums, drop_start_beat=total - 2.0, drop_length_beats=2.0)
            drums.extend(tom_fill(bar_start_beat=last_bar_start, bar_length=4.0))
        out["drums"] = sorted(drums, key=lambda n: (float(n.get("start", 0.0)), int(n.get("pitch", 0))))
    elif kind in ("break", "breakdown", "bridge"):
        if total >= 8.0:
            drums.extend(reverse_cymbal(bar_start_beat=total - 4.0, bar_length=4.0))
            out["drums"] = sorted(drums, key=lambda n: (float(n.get("start", 0.0)), int(n.get("pitch", 0))))

    return out


def inject_pre_drop_silence(
    notes: list[dict[str, Any]],
    bars: int = 8,
    silence_beats: float = 1.0,
) -> list[dict[str, Any]]:
    """Strip or truncate notes in the final `silence_beats` of a `bars`-bar section."""
    total_beats = max(4.0, float(bars) * 4.0)
    cutoff = max(0.0, total_beats - max(0.0, float(silence_beats)))
    kept: list[dict[str, Any]] = []
    for n in notes:
        start = float(n.get("start", 0.0))
        if start >= cutoff - 0.001:
            continue
        copy_n = dict(n)
        dur = float(copy_n.get("duration", 0.25))
        if start + dur > cutoff:
            copy_n["duration"] = round(max(0.0312, cutoff - start), 4)
        kept.append(copy_n)
    return kept


def generate_snare_roll(
    bars: int = 8,
    roll_bars: int = 2,
    silence_beats: float = 1.0,
    pitch: int = 38,
) -> list[dict[str, Any]]:
    """Generate an accelerating snare roll in the final `roll_bars` of a `bars`-bar build section,
    respecting `silence_beats` at the very end."""
    total_beats = max(4.0, float(bars) * 4.0)
    r_bars = max(1, min(int(bars), int(roll_bars)))
    start_beat = max(0.0, total_beats - r_bars * 4.0)
    roll = snare_roll(bar_start_beat=start_beat, bars=r_bars, snare_pitch=pitch)
    if silence_beats > 0:
        roll = inject_pre_drop_silence(roll, bars=bars, silence_beats=silence_beats)
    return roll


def generate_turnaround_bass_fill(
    bass_notes: list[dict[str, Any]],
    bars: int = 8,
    root_midi: int = 36,
) -> list[dict[str, Any]]:
    """Replace the final 2 beats of a `bars`-bar bassline with a root -> fifth -> octave turnaround walk-up."""
    total_beats = max(4.0, float(bars) * 4.0)
    fill_start = total_beats - 2.0
    kept: list[dict[str, Any]] = []
    for n in bass_notes:
        start = float(n.get("start", 0.0))
        if start >= fill_start - 0.001:
            continue
        copy_n = dict(n)
        dur = float(copy_n.get("duration", 0.25))
        if start + dur > fill_start:
            copy_n["duration"] = round(max(0.0312, fill_start - start), 4)
        kept.append(copy_n)
    base_root = int(root_midi)
    while base_root < 24:
        base_root += 12
    while base_root > 43:
        base_root -= 12
    fill_steps = (
        (fill_start, base_root, 0.45, 96),
        (fill_start + 0.5, min(55, base_root + 7), 0.45, 102),
        (fill_start + 1.0, min(55, base_root + 12), 0.45, 108),
    )
    for st, p, dur, vel in fill_steps:
        kept.append({
            "pitch": int(p),
            "start": round(st, 4),
            "duration": dur,
            "velocity": vel,
            "mute": False,
        })
    return sorted(kept, key=lambda n: (float(n.get("start", 0.0)), int(n.get("pitch", 0))))

