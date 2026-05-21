from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton.planner import local_plan, enrich_actions, plan


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "ableton_remote_script" / "Vibelton" / "Vibelton.py"

SMOKE_PROMPTS = [
    "Set tempo to 124 BPM and start playback.",
    "Create house drums for 4 bars.",
    "Create a 4 bar Am F C G chord progression.",
    (
        "Create an expanded 125 BPM house song sketch with genre-aware Ableton instruments, "
        "warm chords, bouncy bass, club kick, open hats, percussion, clap, pad, riff, "
        "ambience, and a simple lead hook. Copy it to Arrangement View and start playback."
    ),
    "Humanize the drums and add ghost notes.",
    "Finish my existing Session View loops into a house arrangement.",
]


def canonical_bridge_actions() -> set[str]:
    source = BRIDGE.read_text(encoding="utf-8")
    return set(re.findall(r'action_type == "([^"]+)"', source))


class PlannerActionSupportTest(unittest.TestCase):
    def test_smoke_prompts_emit_only_supported_actions(self) -> None:
        supported = canonical_bridge_actions()
        self.assertIn("duplicate_track", supported)
        self.assertIn("mute_track", supported)
        self.assertIn("set_song_position", supported)
        self.assertIn("rename_tracks_from_devices", supported)

        unsupported: dict[str, list[str]] = {}
        for prompt in SMOKE_PROMPTS:
            plan = local_plan(prompt)
            action_types = [str(action.get("type")) for action in plan["actions"]]
            missing = sorted(set(action_types) - supported)
            if missing:
                unsupported[prompt] = missing

        self.assertEqual({}, unsupported)

    def test_focused_genre_drum_prompt_stays_drum_only(self) -> None:
        plan = local_plan("Create house drums for 4 bars.")
        self.assertEqual("Queued 2 action(s) for Ableton Live.", plan["reply"])
        self.assertEqual(["create_midi_track", "create_midi_clip"], [action["type"] for action in plan["actions"]])
        clip = plan["actions"][1]
        self.assertEqual("AI Drums", clip["track_name"])
        self.assertEqual(16, clip["length_beats"])
        self.assertTrue(clip["notes"])
        self.assertFalse(any(action["type"] == "copy_session_to_arrangement" for action in plan["actions"]))

    def test_expanded_song_track_order_groups_drums(self) -> None:
        plan = local_plan("Create an expanded 125 BPM house song sketch with genre-aware Ableton instruments.")
        created = [action["name"] for action in plan["actions"] if action["type"] == "create_midi_track"]
        self.assertEqual(
            [
                "Riff",
                "Hook",
                "Chords",
                "Ambience",
                "Bass",
                "Pad",
                "Drum Instrument",
                "Snare / Clap",
                "Hh / Sh / Rd",
                "Percussion",
                "Hh / Sh / Rd +",
                "Bd",
            ],
            created,
        )

    def test_expanded_song_resets_transport_before_playing(self) -> None:
        plan = local_plan("Create an expanded 125 BPM house song sketch with genre-aware Ableton instruments.")
        action_types = [action["type"] for action in plan["actions"]]
        self.assertLess(action_types.index("copy_session_to_arrangement"), action_types.index("set_song_position"))
        self.assertLess(action_types.index("set_song_position"), action_types.index("start_playback"))
        position_action = next(action for action in plan["actions"] if action["type"] == "set_song_position")
        start_action = next(action for action in plan["actions"] if action["type"] == "start_playback")
        self.assertEqual(0, position_action["beat"])
        self.assertEqual(0, start_action["beat"])

    def test_drum_palettes_do_not_use_empty_rack_fallback(self) -> None:
        plan = local_plan("Create an expanded Drum n Bass arrangement at 172 BPM with atmospheric pad and fast drums.")
        load_action = next(action for action in plan["actions"] if action["type"] == "load_stock_instruments")
        self.assertNotIn("Drum Rack", load_action["tracks"]["Drum Instrument"])

    def test_named_soft_keys_melody_stays_single_track(self) -> None:
        plan = local_plan("Make a track called Soft Keys and add a C major melody.")
        self.assertEqual("Queued 2 action(s) for Ableton Live.", plan["reply"])
        self.assertEqual(["create_midi_track", "create_midi_clip"], [action["type"] for action in plan["actions"]])
        self.assertEqual("Soft Keys", plan["actions"][0]["name"])
        clip = plan["actions"][1]
        self.assertEqual("Soft Keys", clip["track_name"])
        self.assertEqual("Generated Melody", clip["clip_name"])
        self.assertTrue(clip["notes"])
        self.assertFalse(any(action["type"] == "copy_session_to_arrangement" for action in plan["actions"]))

    def test_finisher_existing_session_uses_non_destructive_arrangement_copy(self) -> None:
        plan = local_plan("Finish my existing Session View loops into a house arrangement and rename badly named tracks.")
        action_types = [action["type"] for action in plan["actions"]]
        self.assertEqual(
            ["rename_tracks_from_devices", "create_midi_clip", "create_midi_clip", "copy_session_to_arrangement", "set_song_position", "start_playback"],
            action_types,
        )
        self.assertEqual("AI Riser", plan["actions"][1]["track_name"])
        self.assertEqual("AI Crash", plan["actions"][2]["track_name"])
        self.assertTrue(plan["actions"][3]["sections"])
        self.assertTrue(plan["actions"][3]["reuse_available_scenes"])
        self.assertFalse(any(action["type"] in {"create_midi_track", "mute_track"} for action in plan["actions"]))

    def test_curated_genre_controls_default_bpm_and_arrangement(self) -> None:
        plan = local_plan("Create an expanded UK Garage song sketch with skippy drums and soulful vocal chops.")
        tempo = next(action for action in plan["actions"] if action["type"] == "set_tempo")
        arrangement = next(action for action in plan["actions"] if action["type"] == "copy_session_to_arrangement")
        self.assertEqual(133, tempo["bpm"])
        self.assertEqual(["Intro", "Build", "Drop", "Break", "Drop 2", "Outro"], [section["name"] for section in arrangement["sections"]])

    def test_curated_vibe_words_trigger_expanded_song_sketch(self) -> None:
        plan = local_plan("Create something skippy and soulful with vocal chops.")
        self.assertIn("genre-aware", plan["reply"])
        tempo = next(action for action in plan["actions"] if action["type"] == "set_tempo")
        self.assertEqual(133, tempo["bpm"])

    @patch("vibelton.queue.current_state", return_value={
        "connected": True,
        "tracks": [
            {"name": "Pad Atmosphere", "index": 0, "clips": [{"scene_index": 0}]},
            {"name": "Bass Sub", "index": 1, "clips": [{"scene_index": 0}]},
            {"name": "Lead Pluck", "index": 2, "clips": [{"scene_index": 0}]},
            {"name": "Drums Kit", "index": 3, "clips": [{"scene_index": 0}]},
        ],
        "scene_count": 1,
    })
    def test_finisher_with_vst_map_prepends_load_user_vst_instruments(self, _mock_state) -> None:
        vst_map = {"pad": "Serum2", "bass": "Serum2", "lead": "Serum2"}
        plan = local_plan(
            "Finish my existing Session View loops into a house arrangement.",
            vst_map=vst_map,
        )
        action_types = [action["type"] for action in plan["actions"]]
        # load_user_vst_instruments must be the very first action
        self.assertEqual("load_user_vst_instruments", action_types[0])
        vst_action = plan["actions"][0]
        self.assertIn("tracks", vst_action)
        # Pad, Bass, Lead tracks should be mapped; Drums should not
        self.assertIn("Pad Atmosphere", vst_action["tracks"])
        self.assertIn("Bass Sub", vst_action["tracks"])
        self.assertIn("Lead Pluck", vst_action["tracks"])
        self.assertNotIn("Drums Kit", vst_action["tracks"])
        # The track map should contain plugin name references
        for queries in vst_action["tracks"].values():
            self.assertIn("Serum2", queries)

    def test_finisher_without_vst_map_has_no_vst_action(self) -> None:
        plan = local_plan("Finish my existing Session View loops into a house arrangement.")
        action_types = [action["type"] for action in plan["actions"]]
        self.assertNotIn("load_user_vst_instruments", action_types)

    def test_expanded_song_sketch_with_vst_map_loads_vsts(self) -> None:
        vst_map = {"pad": "Serum2", "bass": "Serum2", "lead": "Serum2"}
        plan = local_plan(
            "Create an expanded 125 BPM house song sketch with genre-aware Ableton instruments.",
            vst_map=vst_map,
        )
        action_types = [action["type"] for action in plan["actions"]]
        self.assertIn("load_user_vst_instruments", action_types)
        self.assertIn("load_stock_instruments", action_types)
        
        vst_action = next(a for a in plan["actions"] if a["type"] == "load_user_vst_instruments")
        stock_action = next(a for a in plan["actions"] if a["type"] == "load_stock_instruments")
        
        # User specified roles (Pad, Bass, Hook/Riff) should use VST
        self.assertIn("Pad", vst_action["tracks"])
        self.assertIn("Bass", vst_action["tracks"])
        self.assertIn("Hook", vst_action["tracks"])
        self.assertIn("Riff", vst_action["tracks"])
        self.assertNotIn("Pad", stock_action["tracks"])
        self.assertNotIn("Bass", stock_action["tracks"])
        
        # Drums, keys etc should fallback to stock instruments
        self.assertIn("Drum Instrument", stock_action["tracks"])
        self.assertNotIn("Bd", stock_action["tracks"])
        self.assertNotIn("Snare / Clap", stock_action["tracks"])

    def test_expanded_song_sketch_routes_midi(self) -> None:
        plan = local_plan("Create an expanded 125 BPM house song sketch with genre-aware Ableton instruments.")
        route_actions = [action for action in plan["actions"] if action["type"] == "route_midi"]
        self.assertEqual(5, len(route_actions))
        for act in route_actions:
            self.assertEqual("Drum Instrument", act["target_track"])
            self.assertIn(act["source_track"], ["Snare / Clap", "Hh / Sh / Rd", "Percussion", "Hh / Sh / Rd +", "Bd"])

    def test_single_track_creation_with_vst_map_loads_vst(self) -> None:
        vst_map = {"bass": "Serum2"}
        plan = local_plan("Create a 4 bar bass progression.", vst_map=vst_map)
        action_types = [action["type"] for action in plan["actions"]]
        self.assertIn("load_user_vst_instruments", action_types)
        
        vst_action = next(a for a in plan["actions"] if a["type"] == "load_user_vst_instruments")
        self.assertIn("AI Bass", vst_action["tracks"])
        self.assertEqual(["Serum2"], vst_action["tracks"]["AI Bass"])

    def test_enrich_actions_auto_enriches_vst_for_created_midi_track(self) -> None:
        actions = [
            {"type": "create_midi_track", "name": "AI Lead Track"},
            {"type": "create_midi_clip", "track_name": "AI Lead Track", "clip_name": "Melody"}
        ]
        vst_map = {"lead": "Serum2"}
        enriched = enrich_actions("Make a song", actions, vst_map=vst_map)
        action_types = [a["type"] for a in enriched]
        self.assertIn("load_user_vst_instruments", action_types)
        
        vst_action = next(a for a in enriched if a["type"] == "load_user_vst_instruments")
        self.assertIn("AI Lead Track", vst_action["tracks"])
        self.assertEqual(["Serum2"], vst_action["tracks"]["AI Lead Track"])

    def test_local_single_track_stock_fallback_loads_stock_instruments(self) -> None:
        # Test that when no VST map is provided, the main plan (or fallback local plan) still appends load_stock_instruments
        result = plan("Create a 4 bar bass progression.", vst_map={})
        action_types = [a["type"] for a in result["actions"]]
        self.assertIn("load_stock_instruments", action_types)
        
        stock_action = next(a for a in result["actions"] if a["type"] == "load_stock_instruments")
        self.assertIn("AI Bass", stock_action["tracks"])
        self.assertTrue(len(stock_action["tracks"]["AI Bass"]) > 0)

    def test_drums_vst_map_loads_ujam_beatmaker(self) -> None:
        # Test that Ujam beatmaker / Drums VST mapping works for drum-related tracks
        actions = [
            {"type": "create_midi_track", "name": "AI Drums"},
            {"type": "create_midi_track", "name": "Bd"},
            {"type": "create_midi_track", "name": "Snare / Clap"}
        ]
        vst_map = {"drums": "BM-HUSTLE"}
        enriched = enrich_actions("Make some house beats", actions, vst_map=vst_map)
        action_types = [a["type"] for a in enriched]
        self.assertIn("load_user_vst_instruments", action_types)
        
        vst_action = next(a for a in enriched if a["type"] == "load_user_vst_instruments")
        self.assertIn("AI Drums", vst_action["tracks"])
        self.assertIn("Bd", vst_action["tracks"])
        self.assertIn("Snare / Clap", vst_action["tracks"])
        self.assertEqual(["BM-HUSTLE"], vst_action["tracks"]["AI Drums"])
        self.assertEqual(["BM-HUSTLE"], vst_action["tracks"]["Bd"])
        self.assertEqual(["BM-HUSTLE"], vst_action["tracks"]["Snare / Clap"])


if __name__ == "__main__":
    unittest.main()
