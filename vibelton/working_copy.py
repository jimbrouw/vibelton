"""Server-side enforcement of the working-copy rule (AGENTS.md).

Scaffolding, executing and rolling back production plans is allowed only while
Live has a *saved* Set whose file name matches the working-copy pattern.
Default pattern: ``vibelton-working-copy`` (case-insensitive substring of the
file name).  Override in ``~/.vibelton/config.json``::

    { "working_copy_pattern": "my-copy" }
"""
from __future__ import annotations

import json
from typing import Any

from . import security

DEFAULT_PATTERN = "vibelton-working-copy"


MIN_PATTERN_LENGTH = 8
TOO_GENERIC = {"copy", "backup", "working", "project", "untitled", "live", "set", "song", "final", "master", "original"}


def pattern_problem(value: object) -> str | None:
    """Why a configured pattern would weaken the rule (None when it is acceptable)."""
    if not isinstance(value, str) or not value.strip():
        return "it is empty"
    text = value.strip()
    if len(text) < MIN_PATTERN_LENGTH:
        return "it is shorter than %d characters" % MIN_PATTERN_LENGTH
    if not any(ch.isalpha() for ch in text):
        return "it contains no letters"
    if text.lower().strip(" -_.") in TOO_GENERIC:
        return "it is too generic to tell a working copy from an original"
    return None


def _configured_pattern() -> object:
    try:
        config = json.loads((security.home_dir() / "config.json").read_text(encoding="utf-8"))
        return config.get("working_copy_pattern") if isinstance(config, dict) else None
    except (OSError, ValueError):
        return None


def pattern() -> str:
    """The configured pattern, unless it is too weak: then the default stays in force."""
    value = _configured_pattern()
    if value is not None and pattern_problem(value) is None:
        return value.strip()
    return DEFAULT_PATTERN


def set_name(set_path: str | None) -> str:
    return (set_path or "").replace("\\", "/").rsplit("/", 1)[-1]


def check(set_path: str | None) -> dict[str, Any]:
    """Describe whether scaffolding is allowed for the Set Live reports."""
    wanted = pattern()
    name = set_name(set_path)
    base = {"set_path": set_path or None, "set_name": name or None, "pattern": wanted}
    configured = _configured_pattern()
    if configured is not None and pattern_problem(configured):
        base["pattern_warning"] = "Ignoring working_copy_pattern in config.json: %s. Using “%s”." % (pattern_problem(configured), wanted)
    if not name:
        return dict(base, allowed=False, reason="untitled",
                    message="This Live Set is unsaved. Use File > Save Live Set As… to save a working copy "
                            f"with “{wanted}” in the name, then try again.")
    if wanted.lower() not in name.lower():
        return dict(base, allowed=False, reason="original_set",
                    message=f"“{name}” does not look like a working copy (its name must contain “{wanted}”). "
                            "Scaffolding is disabled to protect your original Set. Use Save Live Set As… first.")
    return dict(base, allowed=True, reason="working_copy", message=f"Working copy: {name}")


def require(set_path: str | None) -> dict[str, Any]:
    verdict = check(set_path)
    if not verdict["allowed"]:
        raise ValueError(verdict["message"])
    return verdict
