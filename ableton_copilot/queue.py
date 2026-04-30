from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


QUEUE_DIR = Path.home() / ".ableton_copilot"
COMMANDS_FILE = QUEUE_DIR / "commands.jsonl"
EVENTS_FILE = QUEUE_DIR / "events.jsonl"
STATE_FILE = QUEUE_DIR / "state.json"


def ensure_queue() -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    COMMANDS_FILE.touch(exist_ok=True)
    EVENTS_FILE.touch(exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps({"connected": False, "updated_at": None}, indent=2), encoding="utf-8")


def enqueue(actions: list[dict[str, Any]], source: str = "chat") -> dict[str, Any]:
    ensure_queue()
    command = {
        "id": str(uuid.uuid4()),
        "source": source,
        "created_at": time.time(),
        "actions": actions,
    }
    with COMMANDS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(command, separators=(",", ":")) + "\n")
    return command


def recent_events(limit: int = 40) -> list[dict[str, Any]]:
    ensure_queue()
    lines = EVENTS_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def current_state() -> dict[str, Any]:
    ensure_queue()
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"connected": False, "updated_at": None}
