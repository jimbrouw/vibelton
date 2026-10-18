from __future__ import annotations

import copy
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from vibelton import arrangements, finish_diagnosis, production, role_maps


def track(track_id, name, *, devices=None):
    return {"id": track_id, "index": 0, "name": name, "type": "midi",
            "devices": devices or [], "routing": "Main", "arrangement_clips": []}


class RoleMapTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = {"connected": True, "updated_at": time.time(),
                      "capabilities": ["production_v1"], "session_id": "set-1",
                      "tempo": 124, "metre": [4, 4], "arrangement_readable": True,
                      "production": {"session_id": "set-1", "revision": "rev-1",
                                     "tempo": 124, "metre": [4, 4], "tracks": [
                                         track("kick", "Kick Drum"),
                                         track("ambiguous", "1-MIDI"),
                                     ]}}
        for target, replacement in (("vibelton.production.ROOT", self.root),):
            patcher = patch(target, replacement)
            patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(production.queue, "current_state", side_effect=lambda: self.state)
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(production.queue, "enqueue")
        self.enqueue = patcher.start(); self.addCleanup(patcher.stop)

    def propose(self, request_id=None):
        return production.propose_track_roles({"request_id": request_id or str(uuid.uuid4())})

    def test_confident_ambiguous_override_and_no_live_change(self):
        before = copy.deepcopy(self.state)
        proposal = self.propose()
        self.assertEqual("Kick", proposal["tracks"][0]["suggested_role"])
        self.assertGreater(proposal["tracks"][0]["confidence"], .9)
        self.assertIsNone(proposal["tracks"][1]["suggested_role"])
        self.assertIn("Unknown / leave unchanged", proposal["tracks"][1]["options"])
        self.assertFalse(proposal["active"])
        roles = {"kick": "Bass", "ambiguous": None}
        confirmed = production.confirm_track_roles({"proposal_id": proposal["id"], "roles": roles})
        self.assertEqual("Bass", production.active_track_roles()["roles"]["kick"])
        self.assertEqual("confirmed", confirmed["status"])
        inventory = arrangements._role_inventory(self.state, self.state["production"], confirmed)
        self.assertEqual("confirmed", inventory["likely_roles"][0]["role_source"])
        self.assertEqual("Bass", inventory["likely_roles"][0]["role"])
        self.assertEqual(before, self.state)
        self.enqueue.assert_not_called()

    def test_retry_safety_and_conflicting_confirmation(self):
        request_id = str(uuid.uuid4())
        proposal = self.propose(request_id)
        self.assertEqual(proposal, self.propose(request_id))
        roles = {"kick": "Kick", "ambiguous": None}
        first = production.confirm_track_roles({"proposal_id": proposal["id"], "roles": roles})
        self.assertEqual(first, production.confirm_track_roles({"proposal_id": proposal["id"], "roles": roles}))
        with self.assertRaisesRegex(ValueError, "different choices"):
            production.confirm_track_roles({"proposal_id": proposal["id"],
                                            "roles": {"kick": "Bass", "ambiguous": None}})
        self.enqueue.assert_not_called()

    def test_stale_and_deleted_tracks_require_reconfirmation(self):
        proposal = self.propose()
        roles = {"kick": "Kick", "ambiguous": None}
        production.confirm_track_roles({"proposal_id": proposal["id"], "roles": roles})
        self.state["production"]["revision"] = "rev-2"
        self.assertFalse(production.active_track_roles()["active"])
        with self.assertRaisesRegex(ValueError, "stale"):
            production.confirm_track_roles({"proposal_id": proposal["id"], "roles": roles})
        self.state["production"]["revision"] = "rev-1"
        self.state["production"]["tracks"].pop()
        self.assertFalse(production.active_track_roles()["active"])
        with self.assertRaisesRegex(ValueError, "stale"):
            production.confirm_track_roles({"proposal_id": proposal["id"], "roles": roles})

    def test_context_change_invalidates_and_confirmed_roles_feed_diagnosis(self):
        proposal = self.propose()
        confirmed = production.confirm_track_roles({"proposal_id": proposal["id"],
                                                    "roles": {"kick": "Bass", "ambiguous": None}})
        analysis = production.analyse()
        result = finish_diagnosis.diagnose(analysis, "club-version", confirmed)
        missing = next(f for f in result["findings"] if f["code"] == "missing_roles")
        self.assertEqual("confirmed", missing["evidence"]["role_source"])
        self.assertIn("Kick", missing["evidence"]["missing_roles"])
        self.assertNotIn("Bass", missing["evidence"]["missing_roles"])
        self.state["production"]["tracks"][0]["routing"] = "No Output"
        self.assertFalse(production.active_track_roles()["active"])

    def test_shape_change_track_roles_key_hints_and_empty_flags(self):
        self.state["production"]["tracks"] = [
            {"id": "t0", "index": 0, "name": "1-Audio", "type": "audio",
             "devices": [{"name": "VOCAL"}], "routing": "Main", "arrangement_clips": [{"name": "v", "start_beat": 72, "end_beat": 134}]},
            {"id": "t1", "index": 1, "name": "2-Light Electro", "type": "midi",
             "devices": [{"name": "Light Electro"}], "routing": "Main", "arrangement_clips": [{"name": "e", "start_beat": 159, "end_beat": 271}]},
            {"id": "t3", "index": 3, "name": "4-FHP_120_DRMLP_7", "type": "audio",
             "devices": [], "routing": "Main", "arrangement_clips": [{"name": "d", "start_beat": 136, "end_beat": 240}]},
            {"id": "t4", "index": 4, "name": "5-Audio", "type": "audio",
             "devices": [], "routing": "Main", "arrangement_clips": [], "session_clips": []},
            {"id": "t9", "index": 9, "name": "10-Shaker 1-96 bpm", "type": "audio",
             "devices": [], "routing": "Main", "arrangement_clips": [{"name": "s", "start_beat": 136, "end_beat": 240}]},
            {"id": "t22", "index": 22, "name": "moog short 5 A flat1", "type": "midi",
             "devices": [{"name": "moog short 5 A flat1"}], "routing": "Main", "arrangement_clips": [{"name": "m", "start_beat": 0, "end_beat": 64}]},
        ]
        proposal = self.propose()
        by_id = {row["track_id"]: row for row in proposal["tracks"]}
        self.assertEqual("Vocal", by_id["t0"]["suggested_role"])
        self.assertEqual("Chords", by_id["t1"]["suggested_role"])
        self.assertEqual("Percussion", by_id["t3"]["suggested_role"])
        self.assertTrue(by_id["t4"]["is_empty"])
        self.assertIsNone(by_id["t4"]["suggested_role"])
        self.assertEqual("Percussion", by_id["t9"]["suggested_role"])
        self.assertEqual("Bass", by_id["t22"]["suggested_role"])
        self.assertEqual({"key": "Ab", "octave": 1}, by_id["t22"]["key_hint"])


if __name__ == "__main__":
    unittest.main()
