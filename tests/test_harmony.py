from __future__ import annotations

import unittest

from vibelton.actions import genre_chords, note_number
from vibelton.harmony import detect_colour, optional_music21, plan_harmony


class HarmonyTest(unittest.TestCase):
    def test_detect_colour(self) -> None:
        self.assertEqual("jazzy", detect_colour("make it jazzy"))
        self.assertEqual("cinematic", detect_colour("cinematic house chords"))
        self.assertEqual("moody", detect_colour("dark moody chords"))
        self.assertEqual("neutral", detect_colour("house chords"))

    def test_fallback_plan_voice_leads(self) -> None:
        plan = plan_harmony(
            root_midi=note_number("c", 4),
            mode="major",
            style="uk garage",
            colour="jazzy",
            bars=4,
            octave=4,
            seed=123,
            extensions=(10, 14),
        )
        self.assertEqual(4, len(plan.voiced_chords))
        self.assertFalse(plan.used_music21)
        for previous, current in zip(plan.voiced_chords, plan.voiced_chords[1:]):
            movement = sum(abs(a - b) for a, b in zip(previous, current[: len(previous)]))
            self.assertLess(movement, 36)

    def test_genre_chords_change_with_colour(self) -> None:
        neutral = genre_chords("Create house chords in C major", 4, "main", "house")
        jazzy = genre_chords("Create jazzy house chords in C major", 4, "main", "house")
        self.assertNotEqual(neutral, jazzy)
        self.assertTrue(all(0 <= note["pitch"] <= 127 for note in jazzy))

    def test_trap_and_ambient_harmony_are_distinct(self) -> None:
        trap = genre_chords("Create dark trap chords in A minor", 4, "main", "trap")
        ambient = genre_chords("Create cinematic ambient chords in A minor", 4, "main", "ambient")
        self.assertNotEqual(trap, ambient)

    def test_music21_is_optional(self) -> None:
        # This environment currently does not install music21; the fallback must remain valid.
        self.assertIsNone(optional_music21())
        chords = genre_chords("Create cinematic chords in A minor", 4, "main", "ambient")
        self.assertTrue(chords)


if __name__ == "__main__":
    unittest.main()
