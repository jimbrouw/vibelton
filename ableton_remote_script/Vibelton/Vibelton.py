from __future__ import annotations

import json
import math
import os
import time

from _Framework.ControlSurface import ControlSurface


QUEUE_DIR = os.path.join(os.path.expanduser("~"), ".vibelton")
COMMANDS_FILE = os.path.join(QUEUE_DIR, "commands.jsonl")
EVENTS_FILE = os.path.join(QUEUE_DIR, "events.jsonl")
STATE_FILE = os.path.join(QUEUE_DIR, "state.json")
BRIDGE_VERSION = "2026-05-01-finisher-1"


class Vibelton(ControlSurface):
    def __init__(self, c_instance):
        super(Vibelton, self).__init__(c_instance)
        self._command_offset = 0
        self._pending_play_position = None
        self._pending_play_attempts = 0
        self._ensure_files()
        self._command_offset = os.path.getsize(COMMANDS_FILE)
        self._write_state("connected")
        self._log("ready", "Vibelton bridge loaded %s" % BRIDGE_VERSION)
        self.schedule_message(10, self._poll)
        self.schedule_message(30, self._dump_browser_tree)

    def _dump_browser_tree(self):
        try:
            browser = self.application().browser
            plugins_root = getattr(browser, "plugins", None)
            if plugins_root is None:
                self._log("debug", "No plugins root found to dump")
                return
            lines = []
            def traverse(item, path_parts):
                if item is None:
                    return
                name = getattr(item, "name", "")
                is_loadable = bool(getattr(item, "is_loadable", False))
                current_path = path_parts + [name]
                if is_loadable:
                    lines.append("/".join(current_path))
                try:
                    children = item.children
                except Exception:
                    children = []
                for child in children:
                    traverse(child, current_path)
            traverse(plugins_root, ["Plug-ins"])
            dump_file = os.path.join(QUEUE_DIR, "browser_dump.txt")
            with open(dump_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self._log("debug", "Dumped browser tree of plugins: %d items" % len(lines))
        except Exception as e:
            self._log("debug", "Failed to dump browser tree: %s" % e)

    def disconnect(self):
        self._write_state("disconnected")
        self._log("disconnected", "Vibelton bridge unloaded")
        super(Vibelton, self).disconnect()

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
        elif action_type == "set_song_position":
            self._set_song_position(action.get("beat", 0))
        elif action_type == "start_playback":
            self._start_playback(action)
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
        elif action_type == "duplicate_track":
            self._duplicate_track(action.get("track_name"))
        elif action_type == "mute_track":
            track = self._find_track(action.get("track_name"))
            if track:
                track.mute = True
        elif action_type == "copy_session_to_arrangement":
            self._copy_session_to_arrangement(action)
        elif action_type == "load_stock_instruments":
            self._load_stock_instruments(action)
        elif action_type == "load_user_vst_instruments":
            self._load_user_vst_instruments(action)
        elif action_type == "route_midi":
            source_track = self._find_track(action.get("source_track"))
            target_track = self._find_track(action.get("target_track"))
            if source_track and target_track:
                self._route_midi(source_track, target_track)
        elif action_type == "rename_tracks_from_devices":
            self._rename_tracks_from_devices()
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

    def _rename_tracks_from_devices(self):
        renamed = []
        for index, track in enumerate(self.song().tracks):
            current_name = getattr(track, "name", "")
            if not self._is_generic_track_name(current_name):
                continue
            suggested = self._suggest_track_name_from_devices(track, index)
            if not suggested:
                continue
            track.name = suggested
            renamed.append("%s -> %s" % (current_name, suggested))
        if renamed:
            self._log("tracks_renamed", "Renamed tracks: %s" % "; ".join(renamed))
        else:
            self._log("tracks_renamed", "No generic track names matched loaded devices")

    def _is_generic_track_name(self, name):
        lowered = str(name).strip().lower()
        if not lowered:
            return True
        prefixes = ("midi", "audio", "track", "channel", "inst", "instrument")
        return any(lowered == prefix or lowered.startswith(prefix + " ") for prefix in prefixes)

    def _suggest_track_name_from_devices(self, track, index):
        try:
            devices = list(getattr(track, "devices", []))
        except Exception:
            devices = []
        device_names = [getattr(device, "name", "") for device in devices if getattr(device, "name", "")]
        joined = " ".join(device_names).lower()
        if any(word in joined for word in ["drum", "kit", "rack", "808", "909"]):
            return "Drums %s" % (index + 1)
        if any(word in joined for word in ["bass", "sub", "operator"]):
            return "Bass %s" % (index + 1)
        if any(word in joined for word in ["electric", "piano", "keys", "rhodes"]):
            return "Keys %s" % (index + 1)
        if any(word in joined for word in ["pad", "wavetable", "meld", "analog"]):
            return "Pad %s" % (index + 1)
        if any(word in joined for word in ["lead", "pluck", "tension", "collision"]):
            return "Lead %s" % (index + 1)
        if device_names:
            return "%s %s" % (device_names[0][:20], index + 1)
        return None

    def _set_song_position(self, beat):
        position = max(0.0, float(beat))
        self._pending_play_position = position
        try:
            self.song().current_song_time = position
        except Exception as exc:
            self._log("error", "Could not set song position: %s" % exc)

    def _start_playback(self, action):
        position = action.get("beat", action.get("start_beat", self._pending_play_position))
        if position is None:
            self.song().start_playing()
            return
        self._pending_play_position = max(0.0, float(position))
        self._pending_play_attempts = 2
        self._play_from_pending_position()
        self.schedule_message(3, self._play_from_pending_position)

    def _play_from_pending_position(self):
        if self._pending_play_position is None:
            return
        position = self._pending_play_position
        try:
            self.song().stop_playing()
        except Exception:
            pass
        try:
            self.song().view.show_view("Arranger")
        except Exception:
            pass
        try:
            self.song().current_song_time = position
            self.song().start_playing()
            self._log("transport_start", "Started Arrangement playback at beat %.2f" % position)
        except Exception as exc:
            self._log("error", "Could not start playback at beat %.2f: %s" % (position, exc))

        self._pending_play_attempts -= 1
        if self._pending_play_attempts > 0:
            self.schedule_message(8, self._play_from_pending_position)
        else:
            self._pending_play_position = None

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

    def _load_user_vst_instruments(self, action):
        """Load user-specified VST plugins (e.g. Serum 2) onto named tracks.

        action["tracks"]: dict mapping track_name -> list[str] of browser search queries.
        Searches Ableton's browser (including Plug-ins node) for each query.
        Falls back gracefully when a plugin is not found in the browser tree.
        """
        loaded = []
        failed = []
        track_map = action.get("tracks", {})
        for track_name, queries in track_map.items():
            try:
                track = self._find_track(track_name)
                
                # Expand queries with smart fallbacks
                expanded_queries = []
                for q in queries:
                    q_str = str(q)
                    if q_str not in expanded_queries:
                        expanded_queries.append(q_str)
                    
                    # Try without spaces (e.g. "Serum 2" -> "Serum2")
                    no_spaces = q_str.replace(" ", "")
                    if no_spaces != q_str and no_spaces not in expanded_queries:
                        expanded_queries.append(no_spaces)
                    
                    # Fallback for BM- prefixed beatmakers
                    if q_str.upper().startswith("BM-"):
                        base = q_str[3:]
                        for fb in (base, "Beatmaker " + base, "UJAM " + base):
                            if fb not in expanded_queries:
                                expanded_queries.append(fb)
                    
                    # Fallback for trailing numbers (e.g., Serum2 -> Serum)
                    base = q_str
                    while base and base[-1].isdigit():
                        base = base[:-1]
                    base = base.strip()
                    if base and base != q_str and base not in expanded_queries:
                        expanded_queries.append(base)

                        
                    # Stripping numbers from BM- prefixed bases
                    if q_str.upper().startswith("BM-"):
                        base_no_bm = q_str[3:]
                        base = base_no_bm
                        while base and base[-1].isdigit():
                            base = base[:-1]
                        base = base.strip()
                        if base and base != base_no_bm:
                            for fb in (base, "Beatmaker " + base, "UJAM " + base):
                                if fb not in expanded_queries:
                                    expanded_queries.append(fb)
                
                item = self._find_vst_browser_item(expanded_queries)
                if item is None:
                    # Fall back to stock/general search across all browser roots
                    item = self._find_browser_item(expanded_queries)
                if item is None:
                    failed.append("%s: VST not found in browser for %s" % (track_name, ", ".join(expanded_queries)))
                    continue
                self.song().view.selected_track = track
                self.application().browser.load_item(item)
                loaded.append("%s <- %s" % (track_name, getattr(item, "name", "plugin")))
            except Exception as exc:
                failed.append("%s: %s" % (track_name, exc))

        if loaded:
            self._log("vst_loaded", "Loaded VST instruments: %s" % "; ".join(loaded))
        if failed:
            self._log("vst_load_failed", "VST load issues (falling back to stock): %s" % "; ".join(failed))

    def _find_vst_browser_item(self, queries):
        """Search specifically in the Plug-ins browser node for a VST by name."""
        browser = self.application().browser
        try:
            plugins_root = getattr(browser, "plugins", None)
        except Exception:
            plugins_root = None
        if plugins_root is None:
            return None
        for query in queries:
            wanted = str(query).lower()
            # Deepen max_depth from 6 to 12 to resolve deeply nested manufacturer paths
            item = self._search_browser_tree(plugins_root, wanted, depth=0, max_depth=12, exact_only=True)
            if item is not None:
                return item
            item = self._search_browser_tree(plugins_root, wanted, depth=0, max_depth=12, exact_only=False)
            if item is not None:
                return item
        return None

    def _find_browser_item(self, queries):
        browser = self.application().browser
        roots = []
        # Added "plugins" to fallback roots to double-check in case direct plugins_root access had folder depth issues
        for attr in ("sounds", "drums", "instruments", "plugins", "packs", "user_library"):
            try:
                root = getattr(browser, attr)
                if root:
                    roots.append(root)
            except Exception:
                pass

        for query in queries:
            wanted = str(query).lower()
            for root in roots:
                item = self._search_browser_tree(root, wanted, depth=0, max_depth=10, exact_only=True)
                if item is not None:
                    return item
            for root in roots:
                item = self._search_browser_tree(root, wanted, depth=0, max_depth=10, exact_only=False)
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

    def _route_midi(self, source_track, target_track):
        try:
            if hasattr(source_track, "available_output_routing_types"):
                target_name = target_track.name.lower().strip()
                matched_routing = None
                
                # Log available options for debugging
                try:
                    options = [getattr(r, "display_name", "") for r in source_track.available_output_routing_types]
                    self._log("debug", "Routing types for %s: %s" % (source_track.name, str(options)))
                except Exception:
                    pass

                for routing in source_track.available_output_routing_types:
                    disp = getattr(routing, "display_name", "").lower().strip()
                    if not disp:
                        continue
                    
                    # 1. Exact match
                    if disp == target_name:
                        matched_routing = routing
                        break
                    
                    # 2. Clean track index prefix (e.g. "1-Drum Instrument" -> "Drum Instrument")
                    disp_clean = disp
                    if "-" in disp:
                        parts = disp.split("-", 1)
                        prefix = parts[0].strip()
                        if prefix.isdigit():
                            disp_clean = parts[1].strip()
                    
                    # 3. Clean comparison
                    if disp_clean == target_name:
                        matched_routing = routing
                        break
                        
                    # 4. Handle truncations (e.g. "Drum Instrum" or "Drum Instrume" vs "Drum Instrument")
                    if len(disp_clean) >= 4 and len(target_name) >= 4:
                        if disp_clean.startswith(target_name) or target_name.startswith(disp_clean):
                            matched_routing = routing
                            break

                if matched_routing:
                    source_track.output_routing_type = matched_routing
                    self._log("debug", "Routed %s MIDI output to %s via output_routing_type" % (source_track.name, target_track.name))
                    
                    if hasattr(source_track, "available_output_routing_channels"):
                        device_channel = None
                        fallback_channel = None
                        for channel in source_track.available_output_routing_channels:
                            disp = getattr(channel, "display_name", "").lower()
                            if "track in" in disp or "midi in" in disp:
                                fallback_channel = channel
                            elif disp:
                                device_channel = channel
                                break
                        
                        best_channel = device_channel or fallback_channel
                        if best_channel:
                            source_track.output_routing_channel = best_channel
                            self._log("debug", "Selected routing channel: %s" % getattr(best_channel, "display_name", "unknown"))
                    return
                else:
                    self._log("error", "Could not find routing type matching target track name: %s" % target_track.name)
            
            if hasattr(source_track, "current_output_routing"):
                # Avoid passing Track object if the API requires a string (per C++ signature mismatch error)
                # Try setting it as the target track object, fallback to name if it throws
                try:
                    source_track.current_output_routing = target_track
                    self._log("debug", "Routed %s MIDI output to %s via current_output_routing (object)" % (source_track.name, target_track.name))
                    return
                except Exception:
                    source_track.current_output_routing = target_track.name
                    self._log("debug", "Routed %s MIDI output to %s via current_output_routing (string)" % (source_track.name, target_track.name))
                    return
                
            self._log("error", "No routing properties supported on this Live build for track %s" % source_track.name)
        except Exception as exc:
            self._log("error", "Failed to route MIDI from %s to %s: %s" % (source_track.name, target_track.name, exc))

    def _create_midi_track(self, name):
        track = self._find_track(name, required=False)
        if track:
            return track
        self.song().create_midi_track(-1)
        track = self.song().tracks[-1]
        track.name = name
        return track

    def _duplicate_track(self, name):
        track = self._find_track(name, required=False)
        if not track:
            self._log("error", "Cannot duplicate missing track: %s" % name)
            return
        try:
            index = list(self.song().tracks).index(track)
            self.song().duplicate_track(index)
            # Rename the newly duplicated track (typically placed at index + 1)
            new_track = self.song().tracks[index + 1]
            new_track.name = "%s Copy" % name
        except Exception as exc:
            self._log("error", "Failed to duplicate track: %s" % exc)

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
        reuse_available_scenes = bool(action.get("reuse_available_scenes", False))
        copied = 0
        for section in sections:
            scene_index = int(section.get("scene_index", 0))
            start_beat = float(section.get("start_beat", 0))
            active_tracks = section.get("active_tracks")
            if active_tracks is not None:
                active_tracks = [str(t).lower().strip() for t in active_tracks]

            if len(self.song().scenes) <= scene_index:
                if not reuse_available_scenes or len(self.song().scenes) == 0:
                    continue
                scene_index = scene_index % len(self.song().scenes)
            for track in self.song().tracks:
                if active_tracks is not None:
                    track_name = getattr(track, "name", "").lower().strip()
                    if track_name not in active_tracks:
                        continue
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
        tracks_data = []
        try:
            for index, track in enumerate(self.song().tracks):
                clips_data = []
                for scene_index, slot in enumerate(track.clip_slots):
                    if slot.has_clip:
                        clip_name = ""
                        clip_length = 0.0
                        try:
                            if slot.clip:
                                clip_name = getattr(slot.clip, "name", "")
                                clip_length = float(getattr(slot.clip, "length", 0.0))
                        except Exception:
                            pass
                        clips_data.append({
                            "scene_index": scene_index,
                            "name": clip_name,
                            "length": clip_length
                        })
                
                track_type = "midi" if (hasattr(track, "has_midi_input") and track.has_midi_input) else "audio"
                tracks_data.append({
                    "index": index,
                    "name": getattr(track, "name", ""),
                    "type": track_type,
                    "clips": clips_data
                })
        except Exception as exc:
            self._log("error", "Failed to compile track state: %s" % exc)

        data = {
            "connected": status == "connected",
            "status": status,
            "updated_at": time.time(),
            "tempo": getattr(self.song(), "tempo", None),
            "track_count": len(self.song().tracks),
            "scene_count": len(self.song().scenes),
            "bridge_version": BRIDGE_VERSION,
            "tracks": tracks_data,
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
