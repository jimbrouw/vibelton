from __future__ import annotations

import unittest
import json
from pathlib import Path

from vibelton import arrangements
from vibelton import song_sketch


def disposable_loop_state() -> tuple[dict, dict]:
    """A read-only dry-run fixture: one existing 16-bar loop, no mutations."""
    fixture = json.loads((Path(__file__).parent / "fixtures" / "phase3a-disposable-16-bar-loop.json").read_text())
    tracks = []
    live_tracks = []
    for index, (_group, role, track_type) in enumerate(song_sketch.TRACKS):
        track_id = "track-%d" % index
        arrangement_clips = []
        if role == "Kick":
            material = fixture["existing_material"]
            arrangement_clips = [{"name": material["clip_name"], "start_time": material["start_time"], "length": material["length"]}]
        tracks.append({"id": track_id, "name": role, "type": track_type, "devices": [],
                       "arrangement_clips": arrangement_clips})
        live_tracks.append({"id": track_id, "name": role, "type": track_type, "clips": []})
    state = {"tempo": 124.0, "metre": [4, 4], "tracks": live_tracks}
    production = {"tempo": 124.0, "metre": [4, 4], "tracks": tracks}
    return state, production


class HouseArrangementTests(unittest.TestCase):
    def test_three_variants_are_distinct_bar_aligned_and_timed_at_project_bpm(self) -> None:
        state, production = disposable_loop_state()
        options = arrangements.build_house_options(state, production)
        arrangements.validate_options(options)
        self.assertEqual(["streaming-edit", "club-version", "dj-extended-mix"],
                         [variant["id"] for variant in options["variants"]])
        self.assertEqual([104, 144, 184], [variant["total_bars"] for variant in options["variants"]])
        self.assertEqual([201.29, 278.71, 356.129],
                         [variant["approximate_duration_seconds"] for variant in options["variants"]])
        self.assertEqual(1, options["role_inventory"]["material_summary"]["arrangement_or_session_clip_count"])
        for variant in options["variants"]:
            self.assertEqual(7, len(variant["intended_locators"]))
            self.assertEqual(0, variant["sections"][0]["start_bar"])
            self.assertEqual(variant["total_bars"], variant["sections"][-1]["end_bar"])
            for previous, current in zip(variant["sections"], variant["sections"][1:]):
                self.assertEqual(previous["end_bar"], current["start_bar"])
            self.assertTrue(all(locator["time"] == locator["bar"] * 4 for locator in variant["intended_locators"]))

    def test_invalid_overlap_or_duplicate_structures_fail_closed(self) -> None:
        state, production = disposable_loop_state()
        options = arrangements.build_house_options(state, production)
        options["variants"][0]["sections"][1]["start_bar"] = 7
        with self.assertRaisesRegex(ValueError, "contiguous"):
            arrangements.validate_options(options)

        options = arrangements.build_house_options(state, production)
        options["variants"][2]["total_bars"] = options["variants"][1]["total_bars"]
        with self.assertRaisesRegex(ValueError, "locator or duration"):
            arrangements.validate_options(options)

    def test_material_assumptions_stay_explicit_when_roles_are_missing(self) -> None:
        state, production = disposable_loop_state()
        production["tracks"] = production["tracks"][:1]
        options = arrangements.build_house_options(state, production)
        self.assertIn("Bass", options["role_inventory"]["missing_roles"])
        self.assertTrue(options["role_inventory"]["material_summary"]["reuse_only"])
        self.assertFalse(options["execution_available"])

    def test_drum_and_bass_variants_are_distinct_and_planning_only(self) -> None:
        state, production = disposable_loop_state()
        state["tempo"] = production["tempo"] = 170.0
        options = arrangements.build_dnb_options(state, production)
        arrangements.validate_options(options)
        self.assertEqual("Drum & Bass", options["genre"])
        self.assertEqual(list(arrangements.DNB_VARIANT_IDS), [v["id"] for v in options["variants"]])
        self.assertEqual([128, 168, 208], [v["total_bars"] for v in options["variants"]])
        self.assertFalse(options["execution_available"])
        for variant in options["variants"]:
            self.assertEqual(7, len(variant["sections"]))
            self.assertEqual(variant["total_bars"], variant["sections"][-1]["end_bar"])
            self.assertTrue(all(marker["time"] == marker["bar"] * 4 for marker in variant["intended_locators"]))
        self.assertNotEqual(options["variants"][0]["sections"][0]["active_track_roles"],
                            options["variants"][1]["sections"][0]["active_track_roles"])

    def test_additional_genres_have_three_valid_distinct_maps(self) -> None:
        state, production = disposable_loop_state()
        for genre in ("Techno", "UK Garage", "Hip Hop", "Disco / Nu-disco"):
            with self.subTest(genre=genre):
                options = arrangements.build_options(genre, state, production)
                arrangements.validate_options(options)
                self.assertEqual(genre, options["genre"])
                self.assertEqual(list(arrangements.GENRE_VARIANTS[genre]),
                                 [variant["id"] for variant in options["variants"]])
                self.assertEqual(3, len({variant["total_bars"] for variant in options["variants"]}))
                self.assertFalse(options["execution_available"])
                for variant in options["variants"]:
                    self.assertEqual(7, len(variant["sections"]))
                    self.assertEqual(variant["total_bars"], variant["sections"][-1]["end_bar"])
                    self.assertTrue(all(item["time"] == item["bar"] * 4 for item in variant["intended_locators"]))


if __name__ == "__main__":
    unittest.main()
