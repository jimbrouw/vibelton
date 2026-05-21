from __future__ import annotations

import json
import math
import os
import time

from _Framework.ControlSurface import ControlSurface


QUEUE_DIR = os.path.join(os.path.expanduser("~"), ".ableton_copilot")
COMMANDS_FILE = os.path.join(QUEUE_DIR, "commands.jsonl")
EVENTS_FILE = os.path.join(QUEUE_DIR, "events.jsonl")
STATE_FILE = os.path.join(QUEUE_DIR, "state.json")
BRIDGE_VERSION = "2026-04-28-instruments-3"


class AbletonCopilot(ControlSurface):
    def __init__(self, c_instance):
        super(AbletonCopilot, self).__init__(c_instance)
        self._command_offset = 0
        self._ensure_files()
        self._command_offset = os.path.getsize(COMMANDS_FILE)
        self._write_state("connected")
        self._log("ready", "AbletonCopilot bridge loaded %s" % BRIDGE_VERSION)
        self.schedule_message(10, self._poll)

    def disconnect(self):
        self._write_state("disconnected")
        self._log("disconnected", "AbletonCopilot bridge unloaded")
        super(AbletonCopilot, self).disconnect()

    def _poll(self):
        try:
            self._ensure_files()
            with open(COMMANDS_FILE, "r", encoding="utf-8") as handle:
                handle.seek(self._command_offset)
                lines = handle.readlines()
                self._command_offset = handle.tell()
            for line in lines:
                self._handle_command(line)
            self._write_state("connected")
        except Exception as exc:
            self._log("error", "Polling failed: %s" % exc)
        self.schedule_message(10, self._poll)

    def _handle_command(self, line):
        try:
            command = json.loads(line)
            actions = command.get("actions", [])
            for action in actions:
                self._execute(action)
            self._log("command_complete", "Executed %s action(s)" % len(actions), {"command_id": command.get("id")})
        except Exception as exc:
            self._log("error", "Command failed: %s" % exc)

    def _execute(self, action):
        action_type = action.get("type")
        if action_type == "set_tempo":
            self.song().tempo = float(action.get("bpm", self.song().tempo))
        elif action_type == "start_playback":
            self.song().start_playing()
        elif action_type == "stop_playback":
            self.song().stop_playing()
        elif action_type == "create_midi_track":
            self._create_midi_track(action.get("name", "AI MIDI"))
        elif action_type == "create_audio_track":
            self._create_audio_track(action.get("name", "AI Audio"))
        elif action_type == "create_scene":
            self._create_scene(action.get("name", "AI Scene"))
        elif action_type == "set_scene_name":
            self._set_scene_name(action)
        elif action_type == "create_midi_clip":
            self._create_midi_clip(action)
        elif action_type == "copy_session_to_arrangement":
            self._copy_session_to_arrangement(action)
        elif action_type == "load_stock_instruments":
            self._load_stock_instruments(action)
        elif action_type == "set_track_volume":
            track = self._find_track(action.get("track_name"))
            track.mixer_device.volume.value = self._db_to_amp(float(action.get("db", 0)))
        elif action_type == "set_track_pan":
            track = self._find_track(action.get("track_name"))
            track.mixer_device.panning.value = max(-1.0, min(1.0, float(action.get("pan", 0))))
        elif action_type == "set_send":
            track = self._find_track(action.get("track_name"))
            send_index = int(action.get("send_index", 0))
            track.mixer_device.sends[send_index].value = max(0.0, min(1.0, float(action.get("value", 0))))
        elif action_type == "add_device":
            self._log("unsupported", "Device insertion is not enabled in this bridge yet", action)
        else:
            self._log("unsupported", "Unknown action type: %s" % action_type, action)

    def _load_stock_instruments(self, action):
        loaded = []
        failed = []
        track_map = action.get("tracks", {})
        for track_name, queries in track_map.items():
            try:
                track = self._find_track(track_name)
                item = self._find_browser_item(queries)
                if item is None:
                    failed.append("%s: no matching browser item for %s" % (track_name, ", ".join(queries)))
                    continue
                self.song().view.selected_track = track
                self.application().browser.load_item(item)
                loaded.append("%s <- %s" % (track_name, getattr(item, "name", "browser item")))
            except Exception as exc:
                failed.append("%s: %s" % (track_name, exc))

        if loaded:
            self._log("instruments_loaded", "Loaded instruments: %s" % "; ".join(loaded))
        if failed:
            self._log("instrument_load_failed", "Instrument load issues: %s" % "; ".join(failed))

    def _find_browser_item(self, queries):
        browser = self.application().browser
        roots = []
        for attr in ("sounds", "drums", "instruments", "packs", "user_library"):
            try:
                root = getattr(browser, attr)
                if root:
                    roots.append(root)
            except Exception:
                pass

        for query in queries:
            wanted = str(query).lower()
            for root in roots:
                item = self._search_browser_tree(root, wanted, depth=0, max_depth=8, exact_only=True)
                if item is not None:
                    return item
            for root in roots:
                item = self._search_browser_tree(root, wanted, depth=0, max_depth=8, exact_only=False)
                if item is not None:
                    return item
        return None

    def _search_browser_tree(self, item, wanted, depth, max_depth, exact_only=False):
        if depth > max_depth or item is None:
            return None
        try:
            name = getattr(item, "name", "")
            is_loadable = bool(getattr(item, "is_loadable", False))
            lowered_name = name.lower()
            if is_loadable and (lowered_name == wanted or (not exact_only and wanted in lowered_name)):
                return item
        except Exception:
            pass

        try:
            children = item.children
        except Exception:
            children = []

        exact_candidate = None
        fuzzy_candidate = None
        for child in children:
            try:
                child_name = getattr(child, "name", "").lower()
                child_loadable = bool(getattr(child, "is_loadable", False))
                if child_loadable and child_name == wanted:
                    exact_candidate = child
                    break
                if not exact_only and child_loadable and wanted in child_name and fuzzy_candidate is None:
                    fuzzy_candidate = child
            except Exception:
                pass
        if exact_candidate is not None:
            return exact_candidate
        if fuzzy_candidate is not None:
            return fuzzy_candidate

        for child in children:
            found = self._search_browser_tree(child, wanted, depth + 1, max_depth, exact_only=exact_only)
            if found is not None:
                return found
        return None

    def _create_midi_track(self, name):
        track = self._find_track(name, required=False)
        if track:
            return track
        self.song().create_midi_track(-1)
        track = self.song().tracks[-1]
        track.name = name
        return track

    def _create_audio_track(self, name):
        track = self._find_track(name, required=False)
        if track:
            return track
        self.song().create_audio_track(-1)
        track = self.song().tracks[-1]
        track.name = name
        return track

    def _create_scene(self, name):
        self.song().create_scene(-1)
        scene = self.song().scenes[-1]
        scene.name = name
        return scene

    def _set_scene_name(self, action):
        scene_index = int(action.get("scene_index", 0))
        while len(self.song().scenes) <= scene_index:
            self.song().create_scene(-1)
        self.song().scenes[scene_index].name = action.get("name", "AI Scene")

    def _create_midi_clip(self, action):
        track_name = action.get("track_name") or "AI MIDI"
        track = self._create_midi_track(track_name)
        scene_index = int(action.get("scene_index", 0))
        while len(self.song().scenes) <= scene_index:
            self.song().create_scene(-1)
        slot = track.clip_slots[scene_index]
        length = float(action.get("length_beats", 16))
        if slot.has_clip:
            slot.delete_clip()
        slot.create_clip(length)
        clip = slot.clip
        clip.name = action.get("clip_name") or "Generated MIDI"
        self._write_notes(clip, action.get("notes", []))
        try:
            clip.loop_start = 0
            clip.loop_end = length
            clip.looping = True
        except Exception:
            pass

    def _copy_session_to_arrangement(self, action):
        sections = action.get("sections", [])
        copied = 0
        for section in sections:
            scene_index = int(section.get("scene_index", 0))
            start_beat = float(section.get("start_beat", 0))
            if len(self.song().scenes) <= scene_index:
                continue
            for track in self.song().tracks:
                if scene_index >= len(track.clip_slots):
                    continue
                slot = track.clip_slots[scene_index]
                if not slot.has_clip:
                    continue
                if not hasattr(track, "duplicate_clip_to_arrangement"):
                    raise RuntimeError("Track.duplicate_clip_to_arrangement is not available in this Live build")
                track.duplicate_clip_to_arrangement(slot.clip, start_beat)
                copied += 1
        try:
            self.song().view.show_view("Arranger")
            self.song().current_song_time = 0
        except Exception:
            pass
        self._log("arrangement_copy", "Copied %s clip(s) to Arrangement View" % copied)

    def _write_notes(self, clip, notes):
        normalized = []
        for note in notes:
            pitch = int(max(0, min(127, note.get("pitch", 60))))
            start = float(max(0, note.get("start", 0)))
            duration = float(max(0.03125, note.get("duration", 0.25)))
            velocity = int(max(1, min(127, note.get("velocity", 96))))
            mute = bool(note.get("mute", False))
            normalized.append((pitch, start, duration, velocity, mute))

        if hasattr(clip, "set_notes"):
            clip.set_notes(tuple(normalized))
            return

        if hasattr(clip, "add_new_notes"):
            note_specs = []
            for pitch, start, duration, velocity, mute in normalized:
                note_specs.append(
                    {
                        "pitch": pitch,
                        "start_time": start,
                        "duration": duration,
                        "velocity": velocity,
                        "mute": mute,
                    }
                )
            clip.add_new_notes(tuple(note_specs))
            return

        raise RuntimeError("This Live build does not expose a supported clip note writer")

    def _find_track(self, name, required=True):
        if not name:
            if required:
                raise RuntimeError("Track name is required")
            return None
        wanted = str(name).lower()
        for track in self.song().tracks:
            if track.name.lower() == wanted:
                return track
        if required:
            raise RuntimeError("Track not found: %s" % name)
        return None

    def _db_to_amp(self, db):
        if db <= -70.0:
            return 0.0
        if db >= 6.0:
            return 1.0
        # Calibrated cubic polynomial fader curve mapping for Ableton Live fader
        val = (1.3344569750529607e-06 * (db ** 3) +
               0.000246703214432097 * (db ** 2) +
               0.022915085718092733 * db +
               0.8519213998572046)
        return max(0.0, min(1.0, val))


    def _ensure_files(self):
        if not os.path.exists(QUEUE_DIR):
            os.makedirs(QUEUE_DIR)
        for path in (COMMANDS_FILE, EVENTS_FILE):
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8"):
                    pass

    def _write_state(self, status):
        data = {
            "connected": status == "connected",
            "status": status,
            "updated_at": time.time(),
            "tempo": getattr(self.song(), "tempo", None),
            "track_count": len(self.song().tracks),
            "scene_count": len(self.song().scenes),
            "bridge_version": BRIDGE_VERSION,
        }
        with open(STATE_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def _log(self, event_type, message, data=None):
        event = {
            "type": event_type,
            "message": message,
            "data": data or {},
            "created_at": time.time(),
        }
        with open(EVENTS_FILE, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
        try:
            self.show_message(message)
        except Exception:
            pass
