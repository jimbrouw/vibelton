from __future__ import annotations

import unittest
import math
from vibelton.actions import infer_key, genre_bassline, genre_chords
from vibelton.planner import extract_theory_key


class EnhancementsTest(unittest.TestCase):
    def test_camelot_key_parsing(self) -> None:
        # Test actions.infer_key
        self.assertEqual(infer_key("make a house track in 8A"), ("a", "minor"))
        self.assertEqual(infer_key("deep house in 5B"), ("eb", "major"))
        self.assertEqual(infer_key("8a key"), ("a", "minor"))
        self.assertEqual(infer_key("11b progression"), ("a", "major"))
        self.assertEqual(infer_key("3a tech house"), ("bb", "minor"))

        # Test planner.extract_theory_key
        self.assertEqual(extract_theory_key("generate an upbeat pop tune in 12B"), ("e", "major"))
        self.assertEqual(extract_theory_key("chords in 1A"), ("ab", "minor"))
        self.assertEqual(extract_theory_key("a dark minimal techno vibe in 4A"), ("f", "minor"))

    def test_trap_portamento_slides(self) -> None:
        # Generate a trap bassline using the trap genre
        notes = genre_bassline("sliding bass trap", bars=4, energy="main", genre="trap")
        
        has_slide = False
        for i in range(len(notes) - 1):
            curr = notes[i]
            nxt = notes[i+1]
            
            # Check if duration was extended to overlap next note by exactly 0.1 beats
            overlap = float(nxt["start"]) - (float(curr["start"]) + float(curr["duration"]))
            if math.isclose(overlap, -0.1, abs_tol=1e-4):
                has_slide = True
                self.assertGreaterEqual(nxt["velocity"], 110)
                
        self.assertTrue(has_slide, "A portamento slide should be triggered in the trap bassline template.")

    def test_parallel_motion_lock(self) -> None:
        # Generate house chords with parallel motion enabled by prompt trigger
        parallel_chords = genre_chords("lock chord house progression in A minor", bars=4, energy="main", genre="house")
        
        # Group notes by start time to form chords (round to nearest 0.25 to handle groove jitter)
        chords_by_time = {}
        for note in parallel_chords:
            start = round(float(note["start"]) * 4) / 4
            chords_by_time.setdefault(start, []).append(note["pitch"])
            
        sorted_chords = [sorted(pitches) for pitches in chords_by_time.values()]
        
        self.assertTrue(len(sorted_chords) > 1, "There should be multiple chords generated in the progression.")
        
        # The intervals relative to the lowest note of the chord must be identical for every chord!
        first_chord = sorted_chords[0]
        first_intervals = [p - first_chord[0] for p in first_chord]
        
        for chord in sorted_chords[1:]:
            current_intervals = [p - chord[0] for p in chord]
            self.assertEqual(first_intervals, current_intervals, "Chord interval structure must be physically locked when parallel_motion is enabled.")

    def test_genre_chord_progression_diversity(self) -> None:
        # Import generate_chords to test high-level routing
        from vibelton.actions import generate_chords

        # 1. Test auto-detection and routing
        # "progressive house track" -> house genre -> minor mode default (due to seed/profile)
        house_chords = generate_chords("progressive house track")
        # "hard trap beats" -> trap genre -> minor mode default (usually c# minor or similar)
        trap_chords = generate_chords("hard trap beats")
        # "dreamy pop anthem" -> pop genre -> major/minor mix (usually c major or similar)
        pop_chords = generate_chords("dreamy pop anthem")

        # Group pitches to see which keys/scales were chosen
        house_pitches = {n["pitch"] for n in house_chords}
        trap_pitches = {n["pitch"] for n in trap_chords}
        pop_pitches = {n["pitch"] for n in pop_chords}

        # Verify that these genres don't all default to the exact same pitch set (avoiding the uniform C-major fallback)
        self.assertNotEqual(house_pitches, trap_pitches, "House and Trap chords must have distinct pitches/voicings.")
        self.assertNotEqual(trap_pitches, pop_pitches, "Trap and Pop chords must have distinct pitches/voicings.")
        self.assertNotEqual(house_pitches, pop_pitches, "House and Pop chords must have distinct pitches/voicings.")

        # 2. Test explicit modal restrictions in default key fallback
        # "dark ambient space" -> ambient (which has C, F, G major and A minor)
        # Because of "dark" (minor), it should filter the ambient pool down to only minor keys (A minor)
        from vibelton.actions import infer_key
        root, mode = infer_key("dark ambient space")
        self.assertEqual(mode, "minor")
        self.assertEqual(root, "a")  # A minor is the only minor key in the ambient pool

        # "happy pop tune" -> pop (which has C, G, F major and A minor)
        # Because of "major" / default, and no "dark"/"minor" keyword, it can be a major key
        root_pop, mode_pop = infer_key("major pop song")
        self.assertEqual(mode_pop, "major")
        self.assertIn(root_pop, ["c", "g", "f"])


    def test_expanded_song_sketch_diversity(self) -> None:
        from vibelton.planner import expanded_song_sketch_plan

        # Generate local plans for House vs Reggaeton vs Drum & Bass
        house_plan = expanded_song_sketch_plan("Create an expanded House arrangement")
        reggaeton_plan = expanded_song_sketch_plan("Create an expanded Reggaeton arrangement")
        dnb_plan = expanded_song_sketch_plan("Create an expanded Drum n Bass arrangement")

        # Helper to check if a clip is a primary groove/hook/drop section clip
        def is_primary_section(clip_name: str) -> bool:
            name_lower = clip_name.lower()
            return any(w in name_lower for w in ["hook", "drop", "groove", "chorus", "peak", "theme", "bloom"])

        # 1. Test Percussion Rhythmic Diversity
        house_perc_notes = []
        reggaeton_perc_notes = []
        dnb_perc_notes = []

        for action in house_plan["actions"]:
            if action.get("type") == "create_midi_clip" and action.get("track_name") == "Percussion" and is_primary_section(action.get("clip_name", "")):
                house_perc_notes = action["notes"]
        for action in reggaeton_plan["actions"]:
            if action.get("type") == "create_midi_clip" and action.get("track_name") == "Percussion" and is_primary_section(action.get("clip_name", "")):
                reggaeton_perc_notes = action["notes"]
        for action in dnb_plan["actions"]:
            if action.get("type") == "create_midi_clip" and action.get("track_name") == "Percussion" and is_primary_section(action.get("clip_name", "")):
                dnb_perc_notes = action["notes"]

        # Ensure we found percussion notes
        self.assertTrue(len(house_perc_notes) > 0)
        self.assertTrue(len(reggaeton_perc_notes) > 0)
        self.assertTrue(len(dnb_perc_notes) > 0)

        # Reggaeton should have dembow/clave style syncopations (starts at 0.75, 1.5, 2.75, 3.5 offsets)
        reggaeton_starts = {round(n["start"] % 4, 3) for n in reggaeton_perc_notes}
        self.assertTrue(any(math.isclose(s, 1.5, abs_tol=1e-3) for s in reggaeton_starts))

        # DnB should have fast ghost drum 16th roll timings (starts at 0.75, 1.25, 2.25, 2.75, 3.75)
        dnb_starts = {round(n["start"] % 4, 3) for n in dnb_perc_notes}
        self.assertTrue(any(math.isclose(s, 1.25, abs_tol=1e-3) for s in dnb_starts))

        # House has classic driving rhythms
        self.assertNotEqual(reggaeton_starts, dnb_starts, "Reggaeton and DnB percussion rhythms must be distinct.")

        # 2. Test Melodic Riff & Hook Diversity (Genre Lead routing instead of standard fallback)
        house_hook_notes = []
        dnb_hook_notes = []

        for action in house_plan["actions"]:
            if action.get("type") == "create_midi_clip" and action.get("track_name") == "Hook" and is_primary_section(action.get("clip_name", "")):
                house_hook_notes = action["notes"]
        for action in dnb_plan["actions"]:
            if action.get("type") == "create_midi_clip" and action.get("track_name") == "Hook" and is_primary_section(action.get("clip_name", "")):
                dnb_hook_notes = action["notes"]

        house_hook_pitches = {n["pitch"] for n in house_hook_notes}
        dnb_hook_pitches = {n["pitch"] for n in dnb_hook_notes}

        # House and DnB hooks should be completely distinct rather than sharing the exact same fallback melody!
        self.assertNotEqual(house_hook_pitches, dnb_hook_pitches, "House and DnB hooks must have distinct pitch structures.")

        # 3. Test Pad Alignment & Clean Sustained Voicings
        house_pad_notes = []
        for action in house_plan["actions"]:
            if action.get("type") == "create_midi_clip" and action.get("track_name") == "Pad" and is_primary_section(action.get("clip_name", "")):
                house_pad_notes = action["notes"]

        self.assertTrue(len(house_pad_notes) > 0)
        # Pad notes must ONLY start exactly on bar boundaries (e.g. 0.0, 4.0, 8.0, 12.0)
        for note in house_pad_notes:
            start_mod_4 = note["start"] % 4.0
            self.assertTrue(math.isclose(start_mod_4, 0.0, abs_tol=1e-3), f"Pad note start time {note['start']} must be strictly aligned to bar boundary.")
            self.assertTrue(note["duration"] > 3.0, f"Pad note duration {note['duration']} must be long and sustained.")

    def test_expanded_song_sketch_track_inclusions_exclusions_and_consolidation(self) -> None:
        from vibelton.planner import expanded_song_sketch_plan

        # 1. Test Exclusions: "without chords or pads"
        plan_ex = expanded_song_sketch_plan("Create an expanded house track without chords or pads")
        created_ex = [action["name"] for action in plan_ex["actions"] if action["type"] == "create_midi_track"]
        self.assertNotIn("Chords", created_ex)
        self.assertNotIn("Pad", created_ex)
        self.assertIn("Bass", created_ex)
        self.assertIn("Bd", created_ex)

        # 2. Test Inclusions: "only bass and drums"
        plan_in = expanded_song_sketch_plan("Create an expanded pop sketch with only bass and drums")
        created_in = [action["name"] for action in plan_in["actions"] if action["type"] == "create_midi_track"]
        self.assertIn("Bass", created_in)
        self.assertIn("Bd", created_in)
        self.assertNotIn("Chords", created_in)
        self.assertNotIn("Pad", created_in)
        self.assertNotIn("Riff", created_in)
        self.assertNotIn("Hook", created_in)

        # 3. Test Drum Consolidation: "consolidate drums"
        plan_con = expanded_song_sketch_plan("Create an expanded techno song and consolidate drums")
        created_con = [action["name"] for action in plan_con["actions"] if action["type"] == "create_midi_track"]
        self.assertIn("Drum Instrument", created_con)
        self.assertNotIn("Bd", created_con)
        self.assertNotIn("Snare / Clap", created_con)
        self.assertNotIn("Hh / Sh / Rd", created_con)
        self.assertNotIn("Percussion", created_con)


if __name__ == "__main__":
    unittest.main()



