from __future__ import annotations

import unittest

from vibelton.actions import genre_bassline, genre_chords, genre_drums, genre_lead
from vibelton.genre_dna import (
    CURATED_GENRES,
    GENRE_REGISTRY,
    GROOVE_TEMPLATES,
    RESOLVED_GENRE_REGISTRY,
    GrooveProfile,
    build_curated_prompt_context,
    detect_style_from_text,
    find_curated_genres_by_vibe,
)
from vibelton.planner import expanded_song_sketch_plan


class GenreDNATest(unittest.TestCase):
    def test_all_genres_have_groove_profiles(self) -> None:
        self.assertGreaterEqual(len(GENRE_REGISTRY), 10)
        for name, dna in GENRE_REGISTRY.items():
            with self.subTest(name=name):
                self.assertIsInstance(dna.groove_profile, GrooveProfile)
                self.assertGreaterEqual(dna.groove_profile.position_jitter_ms, 0)
                self.assertGreaterEqual(dna.groove_profile.velocity_jitter, 0)
                self.assertEqual(4, len(dna.groove_profile.weak_beat_curve))
                self.assertGreaterEqual(len(dna.groove_profile.push_pull_per_subdivision), 4)

    def test_required_groove_templates_exist(self) -> None:
        self.assertTrue(
            {
                "mpc_58",
                "mpc_62",
                "dnb_tight",
                "ukg_shuffle",
                "dembow",
                "trap_triplet",
                "laid_back",
                "push",
            }.issubset(GROOVE_TEMPLATES)
        )

    def test_curated_genre_prompt_layer_covers_phase_one_genres(self) -> None:
        self.assertEqual(
            {
                "afrobeats",
                "amapiano",
                "drum n bass",
                "dubstep",
                "grime",
                "deep_house",
                "house",
                "jungle",
                "techno",
                "tech_house",
                "trap",
                "uk garage",
            },
            set(CURATED_GENRES),
        )
        context = build_curated_prompt_context("uk garage")
        self.assertIn("GENRE: UK Garage", context)
        self.assertIn("KICK:", context)
        self.assertIn("CREATIVE RULE-BREAKERS:", context)

    def test_curated_vibe_matching_ranks_genres(self) -> None:
        matches = find_curated_genres_by_vibe(["skippy", "soulful"])
        self.assertTrue(matches)
        self.assertEqual("UK Garage", matches[0].name)

    def test_deep_house_bpm_range(self) -> None:
        self.assertEqual((120, 124), CURATED_GENRES["deep_house"].bpm_range)

    def test_tech_house_bpm_range(self) -> None:
        self.assertEqual((127, 132), CURATED_GENRES["tech_house"].bpm_range)

    def test_kick_pattern_divergence(self) -> None:
        self.assertNotEqual(CURATED_GENRES["deep_house"].kick_pattern, CURATED_GENRES["tech_house"].kick_pattern)

    def test_bass_list_extended_by_parent(self) -> None:
        self.assertGreaterEqual(len(RESOLVED_GENRE_REGISTRY["deep_house"].bass_patterns), 5)

    def test_detect_style_deep_house(self) -> None:
        self.assertEqual("deep_house", detect_style_from_text("Create a deep house track"))

    def test_detect_style_tech_house(self) -> None:
        self.assertEqual("tech_house", detect_style_from_text("Create a tech house track"))

    def test_detects_16_house_subgenres_for_sound_selection(self) -> None:
        expected = {
            "acid house": "acid_house",
            "ambient house": "ambient_house",
            "bass house": "bass_house",
            "chicago house": "chicago_house",
            "deep house": "deep_house",
            "disco house": "disco_house",
            "electro house": "electro_house",
            "french house": "french_house",
            "funky house": "funky_house",
            "garage house": "garage_house",
            "g-house": "g_house",
            "minimal house": "minimal_house",
            "progressive house": "progressive_house",
            "tech house": "tech_house",
            "tribal house": "tribal_house",
            "tropical house": "tropical_house",
        }
        for phrase, style_id in expected.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(style_id, detect_style_from_text(f"Create a {phrase} song sketch"))

    def test_deep_house_plan_emits_set_tempo_in_range(self) -> None:
        plan = expanded_song_sketch_plan(message="Create a deep house track")
        tempo_action = next(action for action in plan["actions"] if action.get("type") == "set_tempo")
        self.assertIn(tempo_action["bpm"], range(120, 125))

    def test_tech_house_plan_emits_set_tempo_in_range(self) -> None:
        plan = expanded_song_sketch_plan(message="Create a tech house track")
        tempo_action = next(action for action in plan["actions"] if action.get("type") == "set_tempo")
        self.assertIn(tempo_action["bpm"], range(127, 133))

    def test_curated_only_genres_do_not_fall_back_to_house(self) -> None:
        self.assertEqual("grime", detect_style_from_text("Make a sparse dark 140 grime riddim"))
        self.assertEqual("dubstep", detect_style_from_text("Make a wobble bass dubstep drop"))
        self.assertIs(GENRE_REGISTRY["grime"], GENRE_REGISTRY["trap"])
        self.assertIs(GENRE_REGISTRY["dubstep"], GENRE_REGISTRY["trap"])

    def test_genre_generators_are_deterministic_and_bounded(self) -> None:
        generators = [
            lambda: genre_drums(4, "main", "uk garage"),
            lambda: genre_bassline("Create uk garage in A minor", 4, "main", "uk garage"),
            lambda: genre_chords("Create uk garage in A minor", 4, "main", "uk garage"),
            lambda: genre_lead("Create uk garage in A minor", 4, "main", "uk garage"),
        ]
        for generate in generators:
            with self.subTest(generator=generate):
                first = generate()
                second = generate()
                self.assertEqual(first, second)
                self.assertTrue(first)
                for note in first:
                    self.assertGreaterEqual(note["pitch"], 0)
                    self.assertLessEqual(note["pitch"], 127)
                    self.assertGreaterEqual(note["start"], 0)
                    self.assertGreater(note["duration"], 0)
                    self.assertGreaterEqual(note["velocity"], 1)
                    self.assertLessEqual(note["velocity"], 127)

    def test_melody_rules_make_trap_sparser_than_house(self) -> None:
        house = genre_lead("Create house hook in A minor", 8, "main", "house")
        trap = genre_lead("Create dark trap hook in A minor", 8, "main", "trap")
        self.assertLess(len(trap), len(house))

    def test_melody_phrase_endings_resolve_deterministically(self) -> None:
        first = genre_lead("Create ambient cinematic hook in C major", 8, "main", "ambient")
        second = genre_lead("Create ambient cinematic hook in C major", 8, "main", "ambient")
        self.assertEqual(first, second)
        phrase_end_notes = []
        for phrase in range(2):
            phrase_notes = [note for note in first if int(float(note["start"]) // 16) == phrase]
            phrase_end_notes.append(max(phrase_notes, key=lambda note: note["start"]))
        self.assertTrue(all(note["pitch"] % 12 == 7 for note in phrase_end_notes))
        self.assertTrue(all(note["duration"] >= 1.4 for note in phrase_end_notes))


if __name__ == "__main__":
    unittest.main()
