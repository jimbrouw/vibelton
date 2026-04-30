from __future__ import annotations

import argparse
import json
import os
import re
import struct
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from .genre_dna import detect_style_from_text as detect_style


DEFAULT_MIDI_ROOTS = [
    "/Users/standard/Music/free-midi-chords-20240314",
    "/Users/standard/Music/GM Mapped",
    "/Users/standard/Music/free-midi-progressions-20240314",
    "/Users/standard/Music/Cymatics_Black_Friday_Deluxe_Bundle",
    "/Users/standard/Music",
]

CACHE_PATH = Path.home() / ".cache" / "ableton_copilot" / "midi_grooves.json"

DRUM_KEYWORDS = {
    "beat",
    "breakbeat",
    "breakdown",
    "clap",
    "cowbell",
    "drum",
    "fill",
    "groove",
    "hat",
    "hihat",
    "kick",
    "perc",
    "percussion",
    "ride",
    "snare",
    "tom",
}

STYLE_ALIASES = [
    ("drum n bass", ("drum n bass", "dnb")),
    ("jungle", ("jungle", "old skool", "breakbeat")),
    ("uk garage", ("uk garage", "garage")),
    ("hip hop", ("hip hop", "hip-hop", "hiphop", "trap")),
    ("house", ("house", "four to the floor")),
    ("techno", ("techno",)),
    ("trance", ("trance",)),
    ("reggaeton", ("reggaeton", "dembow")),
    ("reggae", ("reggae", "dancehall", "dance hall")),
    ("downtempo", ("downtempo",)),
    ("afrobeats", ("afrobeats", "afrobeat")),
    ("amapiano", ("amapiano",)),
]

STYLE_WORDS = {alias: style for style, aliases in STYLE_ALIASES for alias in aliases}

PITCH_MAP = {
    35: 36,
    36: 36,
    37: 39,
    38: 38,
    39: 39,
    40: 38,
    41: 41,
    42: 42,
    43: 41,
    44: 42,
    45: 41,
    46: 46,
    47: 41,
    48: 41,
    49: 49,
    50: 41,
    51: 49,
    52: 49,
    53: 49,
    54: 46,
    55: 49,
    56: 39,
    57: 49,
    58: 39,
    59: 49,
}


class MidiParseError(ValueError):
    pass


def generate_library_drums(message: str, bars: int, energy: str = "main", keep: set[int] | None = None) -> list[dict[str, Any]]:
    library = load_cached_library()
    if not library:
        return []

    style = detect_style(message)
    candidates = library.get("styles", {}).get(style) or []
    if not candidates and style == "drum n bass":
        candidates = library.get("styles", {}).get("jungle") or []
    if not candidates:
        candidates = library.get("styles", {}).get("generic") or []
    if not candidates:
        return []

    wanted = keep or {36, 38, 39, 42, 46, 49, 41}
    usable = [pattern for pattern in candidates if any(int(note["pitch"]) in wanted for note in pattern.get("notes", []))]
    if not usable:
        return []

    seed = sum(ord(char) for char in f"{style}:{energy}:{bars}:{message.lower()}")
    pattern = usable[seed % len(usable)]
    return fit_pattern(pattern["notes"], bars, wanted, energy)


@lru_cache(maxsize=4)
def load_cached_library(path: Path = CACHE_PATH) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def build_library(roots: list[str] | None = None, limit: int | None = None) -> dict[str, Any]:
    paths = discover_midi_files(roots or DEFAULT_MIDI_ROOTS)
    if limit is not None:
        paths = paths[:limit]

    styles: dict[str, list[dict[str, Any]]] = {}
    skipped = Counter()
    parsed = 0
    for path in paths:
        style = style_from_path(path)
        try:
            notes, ticks_per_beat = parse_midi_notes(path)
        except (OSError, MidiParseError, struct.error, UnicodeDecodeError):
            skipped["parse_error"] += 1
            continue

        drum_notes = extract_drum_notes(notes, path)
        if len(drum_notes) < 4:
            skipped["not_drum"] += 1
            continue

        pattern = normalize_pattern(drum_notes, ticks_per_beat)
        if len(pattern["notes"]) < 4:
            skipped["too_short"] += 1
            continue
        pattern["source"] = str(path)
        pattern["style"] = style
        pattern["bpm"] = bpm_from_path(path)
        styles.setdefault(style, []).append(pattern)
        if style != "generic":
            styles.setdefault("generic", []).append(pattern)
        parsed += 1

    for style_patterns in styles.values():
        style_patterns.sort(key=lambda item: (item.get("bpm") or 999, item["source"]))

    return {
        "version": 1,
        "roots": roots or DEFAULT_MIDI_ROOTS,
        "file_count": len(paths),
        "groove_count": parsed,
        "skipped": dict(skipped),
        "styles": styles,
    }


def save_library(library: dict[str, Any], path: Path = CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(library, handle, indent=2)
    load_cached_library.cache_clear()


def discover_midi_files(roots: list[str]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for root in roots:
        root_path = Path(root).expanduser()
        if not root_path.exists():
            continue
        for path in root_path.rglob("*"):
            if path.suffix.lower() not in {".mid", ".midi"}:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            result.append(resolved)
    return sorted(result, key=lambda item: str(item).lower())


def parse_midi_notes(path: Path) -> tuple[list[dict[str, Any]], int]:
    data = path.read_bytes()
    if data[:4] != b"MThd":
        raise MidiParseError("missing MIDI header")
    header_length = struct.unpack(">I", data[4:8])[0]
    if header_length < 6:
        raise MidiParseError("short MIDI header")
    _format_type, track_count, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        raise MidiParseError("SMPTE MIDI timing is not supported")
    ticks_per_beat = int(division)
    offset = 8 + header_length
    notes: list[dict[str, Any]] = []

    for _track_index in range(track_count):
        if data[offset : offset + 4] != b"MTrk":
            raise MidiParseError("missing MIDI track")
        track_length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        track = data[offset + 8 : offset + 8 + track_length]
        offset += 8 + track_length
        notes.extend(parse_track_notes(track, ticks_per_beat))
    return notes, ticks_per_beat


def parse_track_notes(track: bytes, ticks_per_beat: int) -> list[dict[str, Any]]:
    index = 0
    tick = 0
    running_status: int | None = None
    active: dict[tuple[int, int], list[tuple[int, int]]] = {}
    notes: list[dict[str, Any]] = []

    while index < len(track):
        delta, index = read_varlen(track, index)
        tick += delta
        status = track[index]
        if status & 0x80:
            index += 1
            if status < 0xF0:
                running_status = status
        elif running_status is not None:
            status = running_status
        else:
            raise MidiParseError("running status without previous status")

        if status == 0xFF:
            if index >= len(track):
                break
            meta_type = track[index]
            index += 1
            length, index = read_varlen(track, index)
            index += length
            if meta_type == 0x2F:
                break
            continue
        if status in {0xF0, 0xF7}:
            length, index = read_varlen(track, index)
            index += length
            continue

        event_type = status & 0xF0
        channel = status & 0x0F
        data_len = 1 if event_type in {0xC0, 0xD0} else 2
        payload = track[index : index + data_len]
        index += data_len
        if len(payload) < data_len:
            break

        if event_type == 0x90 and payload[1] > 0:
            active.setdefault((channel, payload[0]), []).append((tick, payload[1]))
        elif event_type in {0x80, 0x90}:
            key = (channel, payload[0])
            starts = active.get(key)
            if not starts:
                continue
            start_tick, velocity = starts.pop(0)
            duration_ticks = max(1, tick - start_tick)
            notes.append(
                {
                    "pitch": int(payload[0]),
                    "channel": channel,
                    "start": start_tick / ticks_per_beat,
                    "duration": duration_ticks / ticks_per_beat,
                    "velocity": int(velocity),
                }
            )
    return notes


def read_varlen(data: bytes, index: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        byte = data[index]
        index += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, index
    return value, index


def extract_drum_notes(notes: list[dict[str, Any]], path: Path) -> list[dict[str, Any]]:
    text = str(path).lower()
    if any(word in text for word in ["melody", "chord", "progression", "acapella", "vocal"]):
        return []
    channel_10 = [note for note in notes if note["channel"] == 9 and int(note["pitch"]) in PITCH_MAP]
    if len(channel_10) >= 4:
        return channel_10
    if not any(keyword in text for keyword in DRUM_KEYWORDS):
        return []
    mapped = [note for note in notes if int(note["pitch"]) in PITCH_MAP]
    if len(mapped) >= 4:
        return mapped
    if "hihat" in text or "hi hat" in text or "hat midi" in text:
        return [{**note, "pitch": 42} for note in notes[:256]]
    return []


def normalize_pattern(notes: list[dict[str, Any]], ticks_per_beat: int) -> dict[str, Any]:
    del ticks_per_beat
    max_end = max(float(note["start"]) + float(note["duration"]) for note in notes)
    length_beats = choose_length(max_end)
    normalized: list[dict[str, Any]] = []
    for note in notes:
        start = float(note["start"]) % length_beats
        pitch = PITCH_MAP.get(int(note["pitch"]), int(note["pitch"]))
        if pitch not in {36, 38, 39, 41, 42, 46, 49}:
            continue
        normalized.append(
            {
                "pitch": pitch,
                "start": round(start, 4),
                "duration": round(max(0.04, min(float(note["duration"]), 0.5)), 4),
                "velocity": max(1, min(127, int(note["velocity"]))),
                "mute": False,
            }
        )
    normalized.sort(key=lambda item: (item["start"], item["pitch"]))
    return {"length_beats": length_beats, "notes": normalized[:512]}


def choose_length(max_end: float) -> int:
    for length in (4, 8, 16, 32):
        if max_end <= length + 0.01:
            return length
    return 32


def fit_pattern(notes: list[dict[str, Any]], bars: int, keep: set[int], energy: str) -> list[dict[str, Any]]:
    total_beats = bars * 4
    source_length = choose_length(max(float(note["start"]) + float(note["duration"]) for note in notes))
    repeats = max(1, int((total_beats + source_length - 1) // source_length))
    result: list[dict[str, Any]] = []
    for repeat in range(repeats):
        base = repeat * source_length
        for note in notes:
            if int(note["pitch"]) not in keep:
                continue
            start = base + float(note["start"])
            if start >= total_beats:
                continue
            copy = dict(note)
            copy["start"] = round(start, 4)
            if energy == "intro" and int(copy["pitch"]) in {36, 38, 39}:
                copy["mute"] = True
            elif energy == "build":
                copy["velocity"] = min(127, int(copy["velocity"]) + (repeat % 4) * 3)
            result.append(copy)
    return result


# Removed local detect_style, now imported from genre_dna as detect_style


def style_from_path(path: Path) -> str:
    filename_style = style_from_text(path.stem)
    if filename_style != "generic":
        return filename_style
    return detect_style(str(path).replace("_", " ").replace("-", " "))


def bpm_from_path(path: Path) -> int | None:
    filename_match = re.match(r"^\s*(\d{2,3})(?=\D)", path.stem)
    if filename_match:
        value = int(filename_match.group(1))
        if 40 <= value <= 240:
            return value
    match = re.search(r"(?<!\d)(\d{2,3})\s*(?:bpm)?(?!\d)", str(path).lower())
    if not match:
        return None
    value = int(match.group(1))
    return value if 40 <= value <= 240 else None


def style_from_text(text: str) -> str:
    normalized = re.sub(r"[_-]+", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for alias, style in sorted(STYLE_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(^|[^a-z0-9]){re.escape(alias)}([^a-z0-9]|$)", normalized):
            return style
    return "generic"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Ableton Copilot MIDI groove cache.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--cache", type=Path, default=CACHE_PATH)
    args = parser.parse_args()

    library = build_library(limit=args.limit)
    save_library(library, args.cache)
    style_counts = {style: len(patterns) for style, patterns in library["styles"].items() if style != "generic"}
    print(json.dumps({"cache": str(args.cache), "file_count": library["file_count"], "groove_count": library["groove_count"], "styles": style_counts}, indent=2))


if __name__ == "__main__":
    main()

import random

def mutate_clones(notes: list[dict[str, Any]], sibling_index: int) -> list[dict[str, Any]]:
    """Mutate a set of notes slightly based on its sibling index."""
    mutated = []
    # Seed based on sibling index to ensure determinism for a given clone index
    rng = random.Random(sibling_index + 42)
    for note in notes:
        copy_note = dict(note)
        # Randomly adjust velocity by up to +/- 10
        vel_shift = rng.randint(-10, 10)
        copy_note["velocity"] = max(1, min(127, int(copy_note["velocity"]) + vel_shift))
        
        # 10% chance to drop a note if it's not on a downbeat
        if rng.random() < 0.1 and (float(copy_note["start"]) % 1.0) != 0.0:
            continue
            
        # 5% chance to shift note by an octave
        if rng.random() < 0.05:
            shift = 12 if rng.random() < 0.5 else -12
            copy_note["pitch"] = max(0, min(127, int(copy_note["pitch"]) + shift))
            
        mutated.append(copy_note)
    return mutated

def humanize_groove(notes: list[dict[str, Any]], velocity_amount: int = 10, timing_amount: float = 0.03) -> list[dict[str, Any]]:
    """Randomize velocity and start times to simulate human playing."""
    mutated = []
    for note in notes:
        copy_note = dict(note)
        # Shift start time
        start_shift = random.uniform(-timing_amount, timing_amount)
        copy_note["start"] = max(0.0, round(float(copy_note["start"]) + start_shift, 4))
        
        # Shift velocity
        vel_shift = random.randint(-velocity_amount, velocity_amount)
        copy_note["velocity"] = max(1, min(127, int(copy_note["velocity"]) + vel_shift))
        
        mutated.append(copy_note)
    return mutated

def add_ghost_notes(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add rhythmic ghost notes (snares/hats) to a drum pattern."""
    mutated = list(notes)
    existing_starts = {float(note["start"]) for note in notes}
    
    # We'll just look at the bounds
    if not notes:
        return mutated
        
    max_end = max(float(n["start"]) + float(n["duration"]) for n in notes)
    length_beats = choose_length(max_end)
    
    # Add ghost notes on off-16ths that are empty
    ghost_pitch = 38 # snare
    for beat in range(int(length_beats * 4)):
        start = beat * 0.25
        if start not in existing_starts and start % 1.0 != 0.0:
            # 15% chance to add a ghost note
            if random.random() < 0.15:
                mutated.append({
                    "pitch": ghost_pitch,
                    "start": start,
                    "duration": 0.1,
                    "velocity": random.randint(20, 45),
                    "mute": False
                })
                
    mutated.sort(key=lambda x: x["start"])
    return mutated
