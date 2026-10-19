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
        for genre in arrangements.OTHER_GENRE_VARIANTS:
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




class GenreCatalogueTests(unittest.TestCase):
    def test_catalogue_lists_every_supported_genre_once(self) -> None:
        catalogue = arrangements.genre_catalogue()
        names = [entry["genre"] for entry in catalogue["genres"]]
        self.assertEqual(sorted(arrangements.SUPPORTED_GENRES), sorted(names))
        self.assertEqual(len(names), len(set(names)))
        self.assertIn(catalogue["default_genre"], names)

    def test_catalogue_variants_match_the_scaffold_variants(self) -> None:
        for entry in arrangements.genre_catalogue()["genres"]:
            with self.subTest(genre=entry["genre"]):
                ids = [variant["id"] for variant in entry["variants"]]
                self.assertEqual(list(arrangements.GENRE_VARIANTS[entry["genre"]]), ids)
                self.assertIn(entry["default_variant"], ids)
                low, high = entry["bpm_range"]
                self.assertTrue(low <= entry["bpm_default"] <= high)
                for variant in entry["variants"]:
                    self.assertGreater(variant["target_duration_seconds"], 0)
                    self.assertRegex(variant["target_duration"], r"^\d+:\d\d$")

    def test_borrowed_genre_dna_does_not_borrow_the_tempo(self) -> None:
        tempos = {entry["genre"]: entry["bpm_range"] for entry in arrangements.genre_catalogue()["genres"]}
        self.assertEqual([138, 142], tempos["Grime"])
        self.assertEqual([140, 180], tempos["Hyperpop"])
        self.assertEqual([84, 96], tempos["Boom Bap"])
        self.assertNotEqual(tempos["Trap"], tempos["Hyperpop"])

    def test_new_genres_build_valid_maps_at_their_own_tempos(self) -> None:
        for entry in arrangements.genre_catalogue()["genres"]:
            for bpm in sorted({entry["bpm_default"], *entry["bpm_range"]}):
                with self.subTest(genre=entry["genre"], bpm=bpm):
                    options = arrangements.build_options(
                        entry["genre"], {"tempo": bpm}, {"tempo": float(bpm), "tracks": [], "metre": [4, 4]})
                    arrangements.validate_options(options)
                    roles = {role for variant in options["variants"] for section in variant["sections"]
                             for role in section["active_track_roles"]}
                    self.assertLessEqual(roles, set(arrangements.ROLE_ORDER))


if __name__ == "__main__":
    unittest.main()
