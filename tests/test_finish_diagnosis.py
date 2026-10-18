from __future__ import annotations

import copy
import time
import unittest
from unittest.mock import patch

from vibelton import finish_diagnosis, production


def analysis(tracks, *, readable=True):
    return {"schema_version": production.PROJECT_ANALYSIS_SCHEMA,
            "source_revision": "revision-1", "session_id": "session-1",
            "project": {"tempo": 124, "metre": [4, 4], "arrangement_readable": readable,
                        "locators": []}, "tracks": tracks,
            "missing_measurements": ["audio_render", "loudness", "spectrum", "stereo"]}


def track(name, clips=()):
    return {"id": name, "name": name, "type": "midi", "devices": [],
            "arrangement_clips": list(clips)}


class FinishDiagnosisTests(unittest.TestCase):
    def test_drum_and_bass_diagnosis_uses_selected_structure(self):
        source = analysis([track("Bass")], readable=False)
        source["project"]["tempo"] = 170
        result = finish_diagnosis.diagnose(source, "dnb-rolling-club")
        self.assertEqual("Drum & Bass", result["genre"])
        self.assertEqual("dnb-rolling-club", result["template_variant_id"])
        self.assertLessEqual(len(result["findings"]), 5)

    def test_each_added_genre_can_drive_read_only_diagnosis(self):
        for genre, variant in (("Techno", "techno-peak-time"), ("UK Garage", "ukg-vocal-club"),
                               ("Hip Hop", "hiphop-verse-hook"), ("Disco / Nu-disco", "disco-club-lift")):
            with self.subTest(genre=genre):
                result = finish_diagnosis.diagnose(analysis([track("Bass")], readable=False), variant)
                self.assertEqual(genre, result["genre"])
                self.assertEqual("read_only", result["status"])

    def test_repetitive_loop_and_no_change(self):
        clips = [{"start_beat": i * 64, "end_beat": (i + 1) * 64,
                  "fingerprint": "a" * 64} for i in range(9)]
        source = analysis([track("Kick", clips)])
        before = copy.deepcopy(source)
        result = finish_diagnosis.diagnose(source, "club-version")
        self.assertEqual(source, before)
        self.assertEqual("repeated_material", result["findings"][0]["code"])
        self.assertEqual(9, result["findings"][0]["evidence"]["copy_count"])
        self.assertLessEqual(len(result["findings"]), 5)
        self.assertEqual(result, finish_diagnosis.diagnose(source, "club-version"))
        self.assertNotIn("clipping", str(result).lower())

    def test_incomplete_roles(self):
        result = finish_diagnosis.diagnose(analysis([track("Kick")]), "club-version")
        finding = next(f for f in result["findings"] if f["code"] == "missing_roles")
        self.assertIn("Bass", finding["evidence"]["missing_roles"])
        self.assertEqual("needs_user_approval", finding["action_status"])

    def test_well_structured_arrangement(self):
        names = ["Kick", "Snare", "Hats", "Percussion", "Bass", "Chords", "Lead",
                 "Hook", "Atmosphere", "Vocal", "Risers"]
        tracks = [track(name, [{"start_beat": (n % 7) * 64,
                                "end_beat": (n % 7 + 1) * 64,
                                "fingerprint": "%064x" % (n + 1)}])
                  for n, name in enumerate(names)]
        result = finish_diagnosis.diagnose(analysis(tracks), "club-version")
        self.assertFalse(any(f["code"] in {"repeated_material", "missing_roles", "weak_section_contrast"}
                             for f in result["findings"]))

    def test_stale_state_rejected_without_queue(self):
        state = {"connected": True, "updated_at": time.time(), "session_id": "session-1",
                 "capabilities": ["production_v1"], "tempo": 124, "metre": [4, 4],
                 "arrangement_readable": True,
                 "production": {"session_id": "session-1", "revision": "current",
                                "tracks": [track("Kick")]}}
        with patch.object(production.queue, "current_state", return_value=state), \
             patch.object(production.queue, "enqueue") as enqueue:
            with self.assertRaisesRegex(ValueError, "changed"):
                production.diagnose_finish({"template_variant_id": "club-version",
                                           "expected_revision": "old"})
            enqueue.assert_not_called()
            state["updated_at"] = time.time() - 60
            with self.assertRaisesRegex(ValueError, "stale"):
                production.diagnose_finish({"template_variant_id": "club-version",
                                           "expected_revision": "current"})
            enqueue.assert_not_called()

    def test_unreadable_arrangement_is_qualified(self):
        result = finish_diagnosis.diagnose(analysis([track("Kick")], readable=False), "club-version")
        self.assertEqual("arrangement_unreadable", result["findings"][0]["code"])
        self.assertFalse(any(f["code"] == "repeated_material" for f in result["findings"]))

    def test_group_track_error_does_not_block_structural_diagnosis(self):
        clips = [{"start_beat": i * 64, "end_beat": (i + 1) * 64, "fingerprint": "a" * 64} for i in range(4)]
        group = {"id": "group-1", "name": "15-Group", "type": "audio", "is_group": True,
                 "devices": [], "arrangement_clips": []}
        source = analysis([track("Kick", clips), group], readable=False)
        source["project"]["arrangement_errors"] = [{"track_id": "group-1", "track_name": "15-Group",
                                                    "is_group": True, "error": "Main, Group and Return Tracks have no arrangement clips"}]
        result = finish_diagnosis.diagnose(source, "club-version")
        self.assertNotEqual("arrangement_unreadable", result["findings"][0]["code"])
        self.assertEqual("repeated_material", result["findings"][0]["code"])

    def test_unplaced_session_material_and_empty_tracks_diagnosed(self):
        serum = {"id": "serum-6", "name": "6-Serum 2", "type": "midi",
                 "devices": [{"name": "Serum 2"}], "arrangement_clips": [],
                 "session_clips": [{"scene_index": 0, "name": "Idea 1", "length": 64.0}]}
        empty = {"id": "empty-5", "name": "5-Audio", "type": "audio",
                 "devices": [], "arrangement_clips": [], "session_clips": []}
        source = analysis([track("Kick", [{"start_beat": 0, "end_beat": 64, "fingerprint": "a" * 64}]), serum, empty])
        result = finish_diagnosis.diagnose(source, "club-version")
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("unplaced_session_material", codes)
        self.assertIn("empty_unused_tracks", codes)
        unplaced = next(f for f in result["findings"] if f["code"] == "unplaced_session_material")
        self.assertEqual(["6-Serum 2"], unplaced["evidence"]["track_names"])


if __name__ == "__main__":
    unittest.main()
