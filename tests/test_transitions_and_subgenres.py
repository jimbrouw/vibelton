from __future__ import annotations

import unittest

from vibelton.actions import (
    genre_bassline,
    genre_chords,
    genre_drums,
    validate_and_repair_genre_rules,
)
from vibelton.genre_dna import (
    detect_style_from_text,
    lookup_curated_genre,
    lookup_genre,
)
from vibelton.harmony import plan_harmony
from vibelton.transitions import (
    apply_section_transitions,
    crash_on_one,
    kick_drop,
    snare_roll,
    tom_fill,
)


class TransitionsAndSubgenresTests(unittest.TestCase):
    HOUSE_SUBGENRES = (
        ("deep house", "deep_house"),
        ("tech house", "tech_house"),
        ("garage house", "garage_house"),
        ("afro house", "afro_house"),
        ("bass house", "bass_house"),
        ("disco house", "disco_house"),
        ("progressive house", "progressive_house"),
    )

    def test_seven_house_subgenres_resolve_and_have_distinct_profiles(self) -> None:
        drum_signatures = set()
        bass_signatures = set()
        chord_signatures = set()

        for phrase, style_id in self.HOUSE_SUBGENRES:
            with self.subTest(style_id=style_id):
                self.assertEqual(style_id, detect_style_from_text(f"Create a {phrase} groove in A minor"))
                dna = lookup_genre(style_id)
                self.assertEqual(style_id, dna.name)
                curated = lookup_curated_genre(style_id)
                self.assertIsNotNone(curated)

                drums = genre_drums(4, "main", style_id)
                bass = genre_bassline(f"Create {phrase} in A minor", 4, "main", style_id)
                chords = genre_chords(f"Create {phrase} in A minor", 4, "main", style_id)

                self.assertTrue(drums)
                self.assertTrue(bass)
                self.assertTrue(chords)

                drum_signatures.add(tuple((n["pitch"], round(n["start"], 2)) for n in drums[:16]))
                bass_signatures.add(tuple((n["pitch"], round(n["start"], 2), round(n["duration"], 2)) for n in bass[:12]))
                chord_signatures.add(tuple((n["pitch"], round(n["start"], 2), round(n["duration"], 2)) for n in chords[:12]))

        # All 7 House sub-genres produce distinct drum, bass, and chord signatures
        self.assertEqual(7, len(drum_signatures))
        self.assertEqual(7, len(bass_signatures))
        self.assertEqual(7, len(chord_signatures))

    def test_transitions_module_strips_kicks_rolls_snares_and_crashes_drops(self) -> None:
        raw_drums = [
            {"pitch": 36, "start": float(b), "duration": 0.2, "velocity": 110, "mute": False}
            for b in range(16)
        ]
        stripped = kick_drop(raw_drums, drop_start_beat=12.0, drop_length_beats=4.0)
        kicks_in_bar4 = [n for n in stripped if n["pitch"] == 36 and 12.0 <= n["start"] < 16.0]
        self.assertEqual([], kicks_in_bar4)

        roll = snare_roll(bar_start_beat=8.0, bars=2, velocity_start=54, velocity_end=118)
        self.assertGreaterEqual(len(roll), 16)
        self.assertEqual(54, roll[0]["velocity"])
        self.assertEqual(118, roll[-1]["velocity"])
        self.assertTrue(all(n["pitch"] == 38 for n in roll))

        crash = crash_on_one(0.0)
        self.assertEqual(49, crash[0]["pitch"])
        self.assertEqual(0.0, crash[0]["start"])

        toms = tom_fill(bar_start_beat=12.0, bar_length=4.0)
        self.assertEqual([47, 45, 43, 41], [n["pitch"] for n in toms])

        build_section = apply_section_transitions(
            {"drums": raw_drums},
            section_kind="build",
            genre="tech_house",
            section_length_beats=16.0,
        )
        build_kicks_end = [n for n in build_section["drums"] if n["pitch"] == 36 and n["start"] >= 12.0]
        build_snares_end = [n for n in build_section["drums"] if n["pitch"] == 38 and n["start"] >= 8.0]
        self.assertEqual([], build_kicks_end)
        self.assertGreaterEqual(len(build_snares_end), 16)

        drop_section = apply_section_transitions(
            {"drums": raw_drums},
            section_kind="drop",
            genre="tech_house",
            section_length_beats=16.0,
        )
        self.assertTrue(any(n["pitch"] == 49 and n["start"] == 0.0 for n in drop_section["drums"]))

    def test_validate_and_repair_genre_rules_enforces_monophonic_sub_and_ukg_2step(self) -> None:
        overlapping_bass = [
            {"pitch": 36, "start": 0.0, "duration": 1.5, "velocity": 100, "mute": False},
            {"pitch": 41, "start": 0.0, "duration": 1.0, "velocity": 95, "mute": False},  # simultaneous sub note
            {"pitch": 38, "start": 0.75, "duration": 1.0, "velocity": 98, "mute": False},  # overlaps first note
        ]
        repaired_bass = validate_and_repair_genre_rules(overlapping_bass, "bass", "deep_house")
        sub_notes = [n for n in repaired_bass if n["pitch"] < 43]
        self.assertEqual(2, len(sub_notes))
        self.assertLessEqual(sub_notes[0]["start"] + sub_notes[0]["duration"], sub_notes[1]["start"] + 1e-4)

        four_on_floor_ukg = [
            {"pitch": 36, "start": 0.0, "duration": 0.16, "velocity": 110, "mute": False},
            {"pitch": 36, "start": 1.0, "duration": 0.16, "velocity": 105, "mute": False},
            {"pitch": 36, "start": 2.0, "duration": 0.16, "velocity": 108, "mute": False},
            {"pitch": 36, "start": 3.0, "duration": 0.16, "velocity": 105, "mute": False},
        ]
        repaired_ukg = validate_and_repair_genre_rules(four_on_floor_ukg, "drums", "uk garage")
        kick_starts = [round(n["start"], 2) for n in repaired_ukg if n["pitch"] == 36]
        self.assertEqual([0.0, 2.5], kick_starts)

        repaired_ukg_underscore = validate_and_repair_genre_rules(four_on_floor_ukg, "drums", "uk_garage")
        self.assertEqual([0.0, 2.5], [round(n["start"], 2) for n in repaired_ukg_underscore if n["pitch"] == 36])

        # Verify no duplicate 2.5 kick when 2.5 already exists alongside 0, 1, 2, 3
        ukg_with_existing_2_5 = four_on_floor_ukg + [
            {"pitch": 36, "start": 2.5, "duration": 0.16, "velocity": 102, "mute": False},
        ]
        repaired_no_dup = validate_and_repair_genre_rules(ukg_with_existing_2_5, "drums", "uk_garage")
        kicks_at_2_5 = [n for n in repaired_no_dup if n["pitch"] == 36 and abs(n["start"] - 2.5) < 0.08]
        self.assertEqual(1, len(kicks_at_2_5))

    def test_section_aware_harmony_build_turnaround_and_drop2_lift(self) -> None:
        build_h = plan_harmony(57, "minor", "progressive_house", "neutral", 4, 4, 42, energy="build")
        self.assertEqual(["i", "VI", "bVII", "V"], build_h.degrees)

        drop1_h = plan_harmony(57, "minor", "progressive_house", "neutral", 4, 4, 42, energy="drop")
        drop2_h = plan_harmony(57, "minor", "progressive_house", "neutral", 4, 4, 42, energy="drop_2")
        self.assertEqual(drop1_h.degrees, drop2_h.degrees)
        self.assertNotEqual(drop1_h.voiced_chords[0], drop2_h.voiced_chords[0])

    def test_expanded_song_sketch_plan_applies_build_to_drop_transitions(self) -> None:
        from vibelton.planner import expanded_song_sketch_plan, genre_words
        self.assertIn("afro house", genre_words())
        plan = expanded_song_sketch_plan("Create an expanded tech house arrangement")
        # Scene 1 is Build (build energy, 32 bars = 128 beats) preceding Peak (main energy)
        build_bd_clips = [
            a for a in plan["actions"]
            if a.get("type") == "create_midi_clip" and a.get("track_name") == "Bd" and a.get("scene_index") == 1
        ]
        self.assertEqual(1, len(build_bd_clips))
        bd_notes = build_bd_clips[0]["notes"]
        # Pre-drop silence strips final 1.0 beat [127.0, 128.0)
        self.assertTrue(all(float(n["start"]) < 127.0 for n in bd_notes))

        # Snare / Clap in Build has snare roll notes in final 2 bars [120.0, 127.0)
        build_snare_clips = [
            a for a in plan["actions"]
            if a.get("type") == "create_midi_clip" and a.get("track_name") == "Snare / Clap" and a.get("scene_index") == 1
        ]
        self.assertEqual(1, len(build_snare_clips))
        snare_notes = build_snare_clips[0]["notes"]
        roll_notes = [n for n in snare_notes if 120.0 <= float(n["start"]) < 127.0]
        self.assertGreaterEqual(len(roll_notes), 10)
        self.assertTrue(all(float(n["start"]) < 127.0 for n in snare_notes))

        # Bass in Build has turnaround fill walk-up and pre-drop silence in [127.0, 128.0)
        build_bass_clips = [
            a for a in plan["actions"]
            if a.get("type") == "create_midi_clip" and a.get("track_name") == "Bass" and a.get("scene_index") == 1
        ]
        self.assertEqual(1, len(build_bass_clips))
        bass_notes = build_bass_clips[0]["notes"]
        self.assertTrue(all(float(n["start"]) < 127.0 for n in bass_notes))
        self.assertTrue(any(126.0 <= float(n["start"]) < 127.0 for n in bass_notes))

        # FX / Riser is created once and has a stock instrument loaded before its clips are created
        fx_create_indices = [
            idx for idx, a in enumerate(plan["actions"])
            if a.get("type") == "create_midi_track" and a.get("name") == "FX / Riser"
        ]
        self.assertEqual(1, len(fx_create_indices))
        stock_load_indices = [
            idx for idx, a in enumerate(plan["actions"])
            if a.get("type") == "load_stock_instruments" and "FX / Riser" in (a.get("tracks") or {})
        ]
        self.assertEqual(1, len(stock_load_indices))
        fx_clip_indices = [
            idx for idx, a in enumerate(plan["actions"])
            if a.get("type") == "create_midi_clip" and a.get("track_name") == "FX / Riser"
        ]
        self.assertTrue(fx_clip_indices)
        self.assertLess(fx_create_indices[0], stock_load_indices[0])
        self.assertLess(stock_load_indices[0], fx_clip_indices[0])

    def test_turnaround_bass_fill_truncates_overlap_and_preserves_ascending_walkup(self) -> None:
        from vibelton.transitions import generate_turnaround_bass_fill
        # Sustained note starting at beat 12.0 with duration 4.0 crosses fill_start (14.0 on 4-bar clip)
        sustained = [{"pitch": 45, "start": 12.0, "duration": 4.0, "velocity": 100, "mute": False}]
        filled = generate_turnaround_bass_fill(sustained, bars=4, root_midi=45)
        before_fill = [n for n in filled if float(n["start"]) < 14.0]
        self.assertEqual(1, len(before_fill))
        self.assertLessEqual(float(before_fill[0]["start"]) + float(before_fill[0]["duration"]), 14.0)

        walkup = [n for n in filled if float(n["start"]) >= 14.0]
        self.assertEqual(3, len(walkup))
        pitches = [int(n["pitch"]) for n in walkup]
        self.assertLess(pitches[0], pitches[1])
        self.assertLess(pitches[1], pitches[2])


if __name__ == "__main__":
    unittest.main()

