from __future__ import annotations

import json
import mimetypes
import os
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DEFAULT_VST_DIRS = [
    Path("/Library/Audio/Plug-Ins/VST3"),
    Path.home() / "Library" / "Audio" / "Plug-Ins" / "VST3",
    Path("/Library/Audio/Plug-Ins/VST"),
    Path.home() / "Library" / "Audio" / "Plug-Ins" / "VST",
]


def scan_vst_folder(extra_path: str | None = None) -> list[str]:
    """Return sorted list of plugin names (no extension) found in VST/VST3 dirs."""
    search_dirs = list(DEFAULT_VST_DIRS)
    if extra_path:
        search_dirs.insert(0, Path(extra_path))
    seen: set[str] = set()
    names: list[str] = []
    for d in search_dirs:
        try:
            if not d.is_dir():
                continue
            for entry in sorted(d.iterdir()):
                stem = entry.name
                for ext in (".vst3", ".vst", ".component"):
                    if stem.lower().endswith(ext):
                        stem = stem[: -len(ext)]
                        break
                if stem not in seen:
                    seen.add(stem)
                    names.append(stem)
        except PermissionError:
            pass
    return sorted(names)

from .actions import infer_key
from .music_theory import producer_theory_card
from .planner import plan
from .queue import current_state, enqueue, ensure_queue, recent_events, write_event
from . import composition_service
from . import production
from . import samples
from . import errors
from . import security
from . import versions


ROOT = Path(__file__).resolve().parent.parent


def load_env_file() -> None:
    env_path = ROOT / ".env.local"
    if env_path.is_file():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    os.environ[k] = v
        except Exception as exc:
            print(f"Warning: Failed to load .env.local: {exc}")


load_env_file()

WEB = ROOT / "web"
HOST = "127.0.0.1"
PORT = int(os.environ.get("VIBELTON_PORT", "8765"))


class Handler(BaseHTTPRequestHandler):
    def _port(self) -> int:
        return self.server.server_address[1]

    def end_headers(self) -> None:
        for name, value in security.SECURITY_HEADERS.items():
            self.send_header(name, value)
        super().end_headers()

    def _send_cors(self) -> None:
        allowed = security.cors_origin(self.headers.get("Origin"), self._port())
        if allowed:
            self.send_header("Access-Control-Allow-Origin", allowed)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
            self.send_header("Access-Control-Allow-Headers", f"Content-Type, Range, {security.TOKEN_HEADER}")

    def _guard_request(self, mutating: bool) -> bool:
        """Return True if the request may proceed; otherwise send 403."""
        if not security.host_allowed(self.headers.get("Host")):
            self.send_json({"error": "Forbidden host"}, status=403)
            return False
        if mutating:
            small = self.path.split("?", 1)[0] in ("/api/chat", "/api/feedback", "/api/theory", "/api/device/hello")
            if security.body_too_large(self.headers.get("Content-Length"), small=small):
                self.send_json({"error": "Request body is too large"}, status=413)
                return False
            if security.rate_limited():
                self.send_json({"error": "Too many requests; slow down"}, status=429)
                return False
            if not security.origin_allowed(self.headers.get("Origin"), self._port()):
                self.send_json({"error": "Forbidden origin"}, status=403)
                return False
            if not security.token_valid(self.headers.get(security.TOKEN_HEADER)):
                message = "Missing or invalid session token"
                self.send_json({"error": message, "explanation": errors.explain(message)}, status=403)
                return False
        return True

    def do_OPTIONS(self) -> None:
        if not security.host_allowed(self.headers.get("Host")):
            self.send_json({"error": "Forbidden host"}, status=403)
            return
        self.send_response(204 if security.cors_origin(self.headers.get("Origin"), self._port()) else 403)
        self._send_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        path = WEB / (parsed.path.lstrip("/") or "index.html")
        if not path.resolve().is_relative_to(WEB.resolve()) or not path.exists() or path.is_dir():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        # /api/popout launches a window, so it is treated as state-changing.
        if not self._guard_request(mutating=parsed.path == "/api/popout"):
            return
        if parsed.path == "/api/session-token":
            if self.headers.get("Sec-Fetch-Site") == "cross-site" or not security.origin_allowed(self.headers.get("Origin"), self._port()):
                self.send_json({"error": "Forbidden origin"}, status=403)
                return
            self.send_json({"token": security.current_token()})
            return
        if parsed.path.startswith('/api/samples'):
            try:
                query = parse_qs(parsed.query)
                if parsed.path == '/api/samples':
                    result = samples.catalogue(query.get('query', [''])[0],
                                               int(query.get('offset', ['0'])[0]),
                                               int(query.get('limit', ['100'])[0]))
                elif parsed.path == '/api/samples/metadata':
                    result = samples.metadata(
                        query.get('path', [''])[0],
                        target_key=query.get('target_key', [None])[0],
                    )
                elif parsed.path == '/api/samples/audio':
                    path = samples.source_path(query.get('path', [''])[0])
                    size = path.stat().st_size
                    start, end, partial = 0, size - 1, False
                    requested = self.headers.get('Range')
                    if requested:
                        import re
                        match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                        if not match or not any(match.groups()):
                            self.send_error(416)
                            return
                        left, right = match.groups()
                        if left:
                            start = int(left)
                            end = min(int(right), end) if right else end
                        else:
                            start = max(0, size - int(right))
                        if not 0 <= start <= end < size:
                            self.send_response(416)
                            self.send_header('Content-Range', f'bytes */{size}')
                            self.end_headers()
                            return
                        partial = True
                    self.send_response(206 if partial else 200)
                    self.send_header('Content-Type', mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Content-Length', str(max(0, end - start + 1)))
                    if partial:
                        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                    self.end_headers()
                    with path.open('rb') as stream:
                        stream.seek(start)
                        remaining = end - start + 1
                        while remaining > 0:
                            block = stream.read(min(1024 * 1024, remaining))
                            if not block:
                                break
                            self.wfile.write(block)
                            remaining -= len(block)
                    return
                elif parsed.path.startswith('/api/samples/status/') or parsed.path.startswith('/api/samples/imports/'):
                    result = samples.job_status(parsed.path.rsplit('/', 1)[1])

                else:
                    self.send_error(404)
                    return
                self.send_json(result)
            except (ValueError, KeyError, TypeError, OSError, TimeoutError) as exc:
                self.send_json({'error': str(exc)}, status=400)
            except Exception as exc:
                self.send_json({'error': 'Sample inspection failed: ' + type(exc).__name__}, status=400)
            return
        if parsed.path.startswith('/api/production'):
            try:
                if parsed.path == '/api/production':
                    result = production.overview()
                elif parsed.path == '/api/production/working-copy':
                    result = production.working_copy_status()
                elif parsed.path == '/api/production/scaffold-sections':
                    query_params = parse_qs(parsed.query)
                    result = production.scaffold_sections(query_params.get('genre', ['House'])[0],
                                                          query_params.get('variant_id', [''])[0])
                elif parsed.path == '/api/production/role-memory':
                    result = production.role_memory_status()
                elif parsed.path == '/api/production/analysis':
                    result = production.analyse()
                elif parsed.path == '/api/production/comparison':
                    result = production.comparison_contract()
                elif parsed.path == '/api/production/track-roles':
                    result = production.active_track_roles()
                elif parsed.path.startswith('/api/production/cleanup-proposals/'):
                    result = production._read(production.ROOT / 'cleanup-proposals' / (parsed.path.rsplit('/', 1)[1] + '.json'))
                    if not result:
                        raise ValueError('Cleanup proposal not found')
                elif parsed.path.startswith('/api/production/plans/'):
                    result = production.get_plan(parsed.path.rsplit('/', 1)[1])
                elif parsed.path == '/api/production/finish-diagnosis':
                    query_params = parse_qs(parsed.query)
                    variant = query_params.get('template_variant_id', ['streaming-edit'])[0]
                    analysis = production.analyse()
                    result = production.diagnose_finish({
                        'template_variant_id': variant,
                        'expected_revision': analysis['source_revision'],
                    })
                elif parsed.path == '/api/production/track-role-proposal':
                    result = production.propose_track_roles({'request_id': str(uuid.uuid4())})
                elif parsed.path == '/api/production/mix-balance-proposal':
                    result = production.create_mix_balance_proposal({'request_id': str(uuid.uuid4())})
                elif parsed.path.startswith('/api/production/arrangement-proposals/'):
                    result = production.get_arrangement_proposal(parsed.path.rsplit('/', 1)[1])
                elif parsed.path.startswith('/api/production/status/'):
                    result = production.job_status(parsed.path.rsplit('/', 1)[1])
                else:
                    self.send_error(404)
                    return
                self.send_json(result)
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.send_json({'error': str(exc), 'explanation': errors.explain(str(exc))}, status=400)
            return
        if parsed.path.startswith('/api/composition'):
            try:
                if parsed.path == '/api/composition':
                    result = composition_service.overview()
                elif parsed.path.startswith('/api/composition/revisions/'):
                    result = composition_service.get_revision(int(parsed.path.rsplit('/', 1)[1]))
                elif parsed.path.startswith('/api/composition/status/'):
                    result = composition_service.job_status(parsed.path.rsplit('/', 1)[1])
                else:
                    self.send_error(404)
                    return
                self.send_json(result)
            except (ValueError, KeyError, TypeError) as exc:
                self.send_json({'error': str(exc)}, status=400)
            return
        if parsed.path == "/api/status":
            self.send_json({"state": current_state(), "events": recent_events()})
            return
        if parsed.path == "/api/versions":
            self.send_json(versions.collect(current_state(), loaded=versions.loaded_device()))
            return
        if parsed.path == "/api/vst-scan":
            plugins = scan_vst_folder()
            self.send_json({"plugins": plugins})
            return
        if parsed.path == "/api/popout":
            self.handle_popout()
            return

        path = WEB / (parsed.path.lstrip("/") or "index.html")
        if not path.resolve().is_relative_to(WEB.resolve()) or not path.exists() or path.is_dir():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        if path.suffix == ".html":
            meta = f'<meta name="vibelton-token" content="{security.current_token()}">'.encode()
            lowered = data.lower()
            at = lowered.find(b"<head>")
            if at != -1:
                at += len(b"<head>")
                data = data[:at] + meta + data[at:]
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if not self._guard_request(mutating=True):
            return
        if self.path in (
            '/api/samples/import',
            '/api/samples/import-smart',
            '/api/samples/region',
            '/api/samples/recommend',
            '/api/samples/shuffle',
            '/api/samples/audio-to-midi',
            '/api/samples/slice-transients',
        ):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if self.path in ('/api/samples/import', '/api/samples/import-smart', '/api/samples/region', '/api/samples/audio-to-midi', '/api/samples/slice-transients'):
                    if not 0 < length <= 1_000_000:
                        raise ValueError('Sample request is empty or too large')
                    payload = json.loads(self.rfile.read(length).decode('utf-8'))
                else:
                    if not 0 <= length <= 1_000_000:
                        raise ValueError('Sample request is too large')
                    payload = json.loads(self.rfile.read(length).decode('utf-8')) if length else {}
                sample_handlers = {
                    '/api/samples/region': samples.reserve_region,
                    '/api/samples/import': samples.apply,
                    '/api/samples/import-smart': samples.import_shuffled_slot,
                    '/api/samples/recommend': samples.recommend_samples,
                    '/api/samples/shuffle': samples.quick_shuffle,
                    '/api/samples/audio-to-midi': samples.audio_to_midi,
                    '/api/samples/slice-transients': samples.slice_transients,
                }
                handler = sample_handlers[self.path]
                self.send_json(handler(payload))
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.send_json({'error': str(exc)}, status=400)
            except Exception as exc:
                self.send_json({'error': 'Sample import failed: ' + type(exc).__name__}, status=400)
            return
        if self.path.startswith('/api/production/'):
            handlers = {'plan': production.create_plan,
                        'plans': lambda p: (production.create_scaffold_plan(p) if ('genre' in p or 'variant_id' in p) else production.create_plan(p)),
                        'scaffold-plan': production.create_scaffold_plan,
                        'template': production.create_classic_house_template,
                        'cleanup-proposal': production.create_cleanup_proposal, 'apply': production.execute,
                        'rollback': production.rollback, 'analyse': lambda _payload: production.analyse(),
                        'locator-probe': production.probe_locators,
                        'role-memory': production.save_role_memory,
                        'arrangement-options': production.create_house_arrangement_options,
                        'arrangement-selection': production.select_house_arrangement,
                        'arrangement-execution-plan': production.create_house_arrangement_execution_plan,
                        'finish-diagnosis': production.diagnose_finish,
                        'track-role-proposal': production.propose_track_roles,
                        'track-role-confirmation': production.confirm_track_roles,
                        'mix-balance-proposal': production.create_mix_balance_proposal,
                        'session-to-arrangement-plan': production.create_session_to_arrangement_plan,
                        'device-parameter-plan': production.create_device_parameter_plan,
                        'reference-compare': production.compare_reference_renders,
                        'low-end-check': production.check_low_end_clash}
            action_key = self.path.rsplit('/', 1)[1]
            handler = handlers.get(action_key)
            if handler is None:
                self.send_error(404)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= 1_000_000:
                    raise ValueError('Production request is too large')
                payload = json.loads(self.rfile.read(length).decode('utf-8')) if length else {}
                if self.path.startswith('/api/production/plans/') and self.path.endswith('/rollback'):
                    plan_id = self.path.split('/')[4]
                    payload.setdefault('plan_id', plan_id)
                self.send_json(handler(payload))
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.send_json({'error': str(exc), 'explanation': errors.explain(str(exc), {'skipped_sources': getattr(exc, 'skipped_sources', None)})}, status=400)
            return
        if self.path.startswith('/api/composition/'):
            action_key = self.path.rsplit('/', 1)[1]
            handlers = {'save': composition_service.save, 'compile': composition_service.compile_revision,
                        'apply': composition_service.apply, 'verify-markers': composition_service.verify_markers,
                        'from-project': composition_service.create_from_project,
                        'bass-companion': composition_service.generate_bass_companion_revision}
            handler = handlers.get(action_key)
            if handler is None:
                self.send_error(404)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if action_key in ('from-project', 'bass-companion'):
                    if not 0 <= length <= 32_000_000:
                        raise ValueError('Composition request is too large')
                    payload = json.loads(self.rfile.read(length).decode('utf-8')) if length else {}
                else:
                    if not 0 < length <= 32_000_000:
                        raise ValueError('Composition request is empty or too large')
                    payload = json.loads(self.rfile.read(length).decode('utf-8'))
                self.send_json(handler(payload))
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.send_json({'error': str(exc)}, status=400)
            return
        if self.path == "/api/device/hello":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("Device hello is empty or too large")
                self.send_json(versions.record_device(json.loads(self.rfile.read(length).decode("utf-8"))))
            except (ValueError, KeyError, TypeError) as exc:
                self.send_json({"error": str(exc)}, status=400)
            return
        if self.path == "/api/chat":
            self.handle_chat()
            return
        if self.path == "/api/feedback":
            self.handle_feedback()
            return
        if self.path == "/api/theory":
            self.handle_theory()
            return
        if self.path == "/api/popout":
            self.handle_popout()
            return
        self.send_error(404)

    def handle_popout(self) -> None:
        try:
            import subprocess, platform
            url = f"http://{HOST}:{PORT}/arranger_device.html?popout=1"
            opened = False
            if platform.system() == "Darwin":
                chrome = Path("/Applications/Google Chrome.app")
                brave = Path("/Applications/Brave Browser.app")
                if chrome.exists():
                    subprocess.Popen(["open", "-na", "Google Chrome", "--args", f"--app={url}", "--window-size=1120,680"])
                    subprocess.Popen(["osascript", "-e", 'tell application "Google Chrome" to activate'])
                    opened = True
                elif brave.exists():
                    subprocess.Popen(["open", "-na", "Brave Browser", "--args", f"--app={url}", "--window-size=1120,680"])
                    subprocess.Popen(["osascript", "-e", 'tell application "Brave Browser" to activate'])
                    opened = True
            if not opened:
                webbrowser.open(url)
            self.send_json({"status": "opened", "url": url})
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=400)

    def handle_chat(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message = str(payload.get("message", "")).strip()
            if not message:
                raise ValueError("Message is required")
            # vst_map: dict mapping role → plugin name (e.g. {"pad": "Serum2"})
            vst_map = payload.get("vst_map", {})
            action_plan = plan(message, vst_map=vst_map)
            command = enqueue(action_plan["actions"])
            self.send_json({"reply": action_plan["reply"], "command": command, "events": recent_events()})
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=400)

    def handle_feedback(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            rating = str(payload.get("rating", "")).strip().lower()
            if rating not in {"up", "down"}:
                raise ValueError("Feedback rating must be up or down")
            prompt_text = str(payload.get("prompt", ""))[:1000]
            reply = str(payload.get("reply", ""))[:1000]
            write_event("feedback", f"Feedback: {rating}", {"rating": rating, "prompt": prompt_text, "reply": reply})
            self.send_json({"events": recent_events()})
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=400)

    def handle_theory(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            text = str(payload.get("message", "")).strip()
            root = str(payload.get("root", "")).strip()
            mode = str(payload.get("mode", "")).strip()
            if not root or not mode:
                inferred_root, inferred_mode = infer_key(text)
                root = root or inferred_root
                mode = mode or inferred_mode
            self.send_json({"theory": producer_theory_card(root, mode, vibe=text)})
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=400)

    def send_json(self, data: dict, status: int = 200) -> None:
        encoded = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors()
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def approved_roots_lines() -> list[str]:
    """Startup log: which folders Vibelton may read samples and MIDI from (edit ~/.vibelton/config.json to change)."""
    from . import midi_library, samples
    return ["Approved sample folders: " + ", ".join(str(p) for p in samples.approved_roots()),
            "MIDI library folders: " + ", ".join(midi_library.configured_midi_roots()),
            "Add more via extra_sample_roots / midi_library_roots in ~/.vibelton/config.json"]


def main() -> None:
    ensure_queue()
    security.issue_token()
    server, port = create_server()
    url = f"http://{HOST}:{port}"
    print(f"Vibelton is running at {url}")
    print("Keep this process open while using the Ableton Live bridge.")
    for line in approved_roots_lines():
        print(line)
    # Browser tabs get the token via the served HTML; nothing to put in the URL.
    # Never steal focus by default (the device starts this headless); opt in with VIBELTON_OPEN_BROWSER=1.
    if should_open_browser():
        webbrowser.open(url)
    server.serve_forever()


def should_open_browser(env: "os._Environ[str] | dict[str, str] | None" = None) -> bool:
    env = os.environ if env is None else env
    return env.get("VIBELTON_OPEN_BROWSER") == "1" and env.get("VIBELTON_DAEMON") != "1"


def create_server() -> tuple[ThreadingHTTPServer, int]:
    for port in range(PORT, PORT + 20):
        try:
            return ThreadingHTTPServer((HOST, port), Handler), port
        except OSError:
            continue
    raise RuntimeError(f"No open port found between {PORT} and {PORT + 19}")


if __name__ == "__main__":
    main()
