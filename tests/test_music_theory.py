from __future__ import annotations

import unittest

from vibelton.music_theory import (
    chord_quality_from_intervals,
    chord_tones,
    circle_of_fifths,
    diatonic_chords,
    producer_theory_card,
    relative_key,
    rhythm_feel,
    scale_notes,
)
from vibelton.planner import local_plan


class MusicTheoryBrainTest(unittest.TestCase):
    def test_relative_keys_use_scale_degrees(self) -> None:
        self.assertEqual("A minor", relative_key("C", "major"))
        self.assertEqual("C major", relative_key("A", "minor"))

    def test_scale_and_diatonic_chords(self) -> None:
        self.assertEqual(("C", "D", "E", "F", "G", "A", "B"), scale_notes("C", "major"))
        chords = diatonic_chords("C", "major")
        self.assertEqual("C", chords[0]["chord"])
        self.assertEqual("Am", chords[5]["chord"])
        self.assertEqual("Bdim", chords[6]["chord"])

    def test_chord_quality_and_tones(self) -> None:
        self.assertEqual("major", chord_quality_from_intervals((0, 4, 7)))
        self.assertEqual("minor", chord_quality_from_intervals((0, 3, 7)))
        self.assertEqual("diminished", chord_quality_from_intervals((0, 3, 6)))
        self.assertEqual(("A", "C", "E"), chord_tones("A", "minor"))

    def test_circle_memory_shortcut(self) -> None:
        circle = circle_of_fifths()
        self.assertEqual(("F", "C", "G", "D", "A", "E", "B"), circle["sharps"])
        self.assertEqual(("B", "E", "A", "D", "G", "C", "F"), circle["flats"])

    def test_rhythm_feels_are_actionable(self) -> None:
        upbeat = rhythm_feel("upbeat")
        self.assertIn(0.5, upbeat.primary_hits)
        self.assertEqual("upbeat", upbeat.name)

    def test_producer_card_contains_progression(self) -> None:
        card = producer_theory_card("A", "minor", "sentimental romantic")
        self.assertEqual("A minor", card["key"])
        self.assertEqual("C major", card["relative_key"])
        self.assertEqual(("i", "III", "VI", "iv"), card["recommended_progression"]["degrees"])

    def test_planner_returns_theory_payload_without_ableton_actions(self) -> None:
        plan = local_plan("Explain the music theory brain for C major and circle of fifths")
        self.assertEqual([], plan["actions"])
        self.assertIn("theory", plan)
        self.assertIn("Relative key: A minor", plan["reply"])


if __name__ == "__main__":
    unittest.main()
