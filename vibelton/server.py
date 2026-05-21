from __future__ import annotations

import json
import mimetypes
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

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
        if parsed.path == "/api/status":
            self.send_json({"state": current_state(), "events": recent_events()})
            return
        if parsed.path == "/api/vst-scan":
            plugins = scan_vst_folder()
            self.send_json({"plugins": plugins})
            return

        path = WEB / (parsed.path.lstrip("/") or "index.html")
        if not path.resolve().is_relative_to(WEB.resolve()) or not path.exists() or path.is_dir():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if self.path == "/api/chat":
            self.handle_chat()
            return
        if self.path == "/api/feedback":
            self.handle_feedback()
            return
        if self.path == "/api/theory":
            self.handle_theory()
            return
        self.send_error(404)

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
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def main() -> None:
    ensure_queue()
    server, port = create_server()
    url = f"http://{HOST}:{port}"
    print(f"Vibelton is running at {url}")
    print("Keep this process open while using the Ableton Live bridge.")
    webbrowser.open(url)
    server.serve_forever()


def create_server() -> tuple[ThreadingHTTPServer, int]:
    for port in range(PORT, PORT + 20):
        try:
            return ThreadingHTTPServer((HOST, port), Handler), port
        except OSError:
            continue
    raise RuntimeError(f"No open port found between {PORT} and {PORT + 19}")


if __name__ == "__main__":
    main()
