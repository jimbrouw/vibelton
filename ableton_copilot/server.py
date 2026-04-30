from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .planner import plan
from .queue import current_state, enqueue, ensure_queue, recent_events


ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
HOST = "127.0.0.1"
PORT = int(os.environ.get("ABLETON_COPILOT_PORT", "8765"))


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
        if self.path != "/api/chat":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message = str(payload.get("message", "")).strip()
            if not message:
                raise ValueError("Message is required")
            action_plan = plan(message)
            command = enqueue(action_plan["actions"])
            self.send_json({"reply": action_plan["reply"], "command": command, "events": recent_events()})
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
    print(f"Vibelton is running at http://{HOST}:{port}")
    print("Keep this process open while using the Ableton Live bridge.")
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
