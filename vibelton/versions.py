"""What is running vs what is on disk: server, Remote Script (bridge) and the Max device.

Everything here is read-only.  Each mismatch becomes a plain warning with the exact fix.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from pathlib import Path
from typing import Any

SERVER_VERSION = "2026-10-18-arranger-1"
ROOT = Path(__file__).resolve().parent.parent

DEVICE_FILES = ("Vibelton Arranger.amxd", "daemon_guard.js", "autoresize.js")

_loaded_device: dict[str, Any] | None = None
_lock = threading.Lock()


def user_library() -> Path:
    return Path.home() / "Music" / "Ableton" / "User Library"


def remote_script_dir(library: Path | None = None) -> Path:
    return (library or user_library()) / "Remote Scripts" / "Vibelton"


def device_dirs(library: Path | None = None) -> list[Path]:
    base = (library or user_library()) / "Presets" / "Audio Effects" / "Max Audio Effect"
    return [base, base / "m4l"]


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def tree_hash(directory: Path) -> str | None:
    """Hash of every .py file in a Remote Script folder (caches and .DS_Store are ignored)."""
    if not directory.is_dir():
        return None
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        digest.update(path.relative_to(directory).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _constant(path: Path, name: str) -> str | None:
    try:
        match = re.search(r"""\b%s\s*=\s*['"]([^'"]+)['"]""" % re.escape(name), path.read_text(encoding="utf-8"))
    except OSError:
        return None
    return match.group(1) if match else None


def repo_bridge_version(root: Path = ROOT) -> str | None:
    return _constant(root / "ableton_remote_script" / "Vibelton" / "Vibelton.py", "BRIDGE_VERSION")


def repo_device_version(root: Path = ROOT) -> str | None:
    return _constant(root / "m4l" / "daemon_guard.js", "DEVICE_VERSION")


def code_hash(root: Path = ROOT) -> str:
    """Hash of the server's own source; compared with the value taken at startup."""
    digest = hashlib.sha256()
    for path in sorted((root / "vibelton").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


STARTUP_CODE_HASH = code_hash()


def record_device(info: dict[str, Any]) -> dict[str, Any]:
    """The Max device reports which version is actually loaded in Live."""
    global _loaded_device
    version = info.get("device_version")
    if not isinstance(version, str) or not 0 < len(version) <= 80:
        raise ValueError("device_version is required")
    with _lock:
        _loaded_device = {"device_version": version, "reported_at": time.time()}
        return dict(_loaded_device)


def loaded_device() -> dict[str, Any] | None:
    with _lock:
        return dict(_loaded_device) if _loaded_device else None


def _warning(code: str, message: str, fix: str) -> dict[str, str]:
    return {"code": code, "message": message, "fix": fix}


def collect(state: dict[str, Any] | None = None, *, root: Path = ROOT, library: Path | None = None,
            loaded: dict[str, Any] | None = None, startup_hash: str | None = None) -> dict[str, Any]:
    """Versions of every moving part plus a warning for each mismatch."""
    state = state or {}
    warnings: list[dict[str, str]] = []
    running_bridge = state.get("bridge_version")
    repo_bridge = repo_bridge_version(root)
    installed_dir = remote_script_dir(library)
    installed_bridge = _constant(installed_dir / "Vibelton.py", "BRIDGE_VERSION")
    repo_tree, installed_tree = tree_hash(root / "ableton_remote_script" / "Vibelton"), tree_hash(installed_dir)

    if installed_tree is None:
        warnings.append(_warning("bridge_not_installed", "The Vibelton Remote Script is not in your User Library.",
                                 "Run: python3 install_remote_script.py, then restart Live."))
    elif installed_tree != repo_tree:
        warnings.append(_warning("bridge_installed_stale",
                                 "The installed Remote Script (%s) differs from this repository's (%s)." % (installed_bridge, repo_bridge),
                                 "Run: python3 install_remote_script.py, then restart Live."))
    if running_bridge and installed_bridge and running_bridge != installed_bridge:
        warnings.append(_warning("bridge_running_stale",
                                 "Live is running Remote Script %s but %s is installed." % (running_bridge, installed_bridge),
                                 "Restart Live so it loads the installed script."))
    elif running_bridge and installed_tree is not None and installed_tree == repo_tree and repo_bridge and running_bridge != repo_bridge:
        warnings.append(_warning("bridge_running_stale",
                                 "Live is running Remote Script %s but the current one is %s." % (running_bridge, repo_bridge),
                                 "Restart Live so it loads the installed script."))

    repo_device = repo_device_version(root)
    libraries = []
    for directory in device_dirs(library):
        files = {name: (_sha(directory / name), _sha(root / "m4l" / name)) for name in DEVICE_FILES}
        # A folder without the device itself holds only unused leftovers (see deploy_m4l.py --clean-stale).
        if files["Vibelton Arranger.amxd"][0] is None:
            continue
        stale = [name for name, (theirs, ours) in files.items() if theirs is not None and theirs != ours]
        libraries.append({"path": str(directory), "version": _constant(directory / "daemon_guard.js", "DEVICE_VERSION"),
                          "stale_files": stale, "up_to_date": not stale})
        if stale:
            warnings.append(_warning("device_library_stale",
                                     "The device in %s is out of date (%s)." % (directory, ", ".join(stale)),
                                     "Run: python3 scripts/deploy_m4l.py --apply, then reload the device in Live."))
    if not libraries:
        warnings.append(_warning("device_not_in_library", "No Vibelton Arranger device was found in your User Library.",
                                 "Run: python3 scripts/deploy_m4l.py --apply"))

    if loaded and repo_device and loaded.get("device_version") != repo_device:
        warnings.append(_warning("device_loaded_stale",
                                 "The device loaded in Live is %s but the current version is %s." % (loaded.get("device_version"), repo_device),
                                 "Delete the device from its track and drag it in again from the User Library (or reopen the Set)."))

    now_hash = code_hash(root)
    if (startup_hash or STARTUP_CODE_HASH) != now_hash:
        warnings.append(_warning("server_stale", "The Vibelton server was started before its code was updated.",
                                 "Restart the server (reload the device, or run: python3 -m vibelton.server)."))

    return {
        "server_version": SERVER_VERSION,
        "bridge": {"running": running_bridge, "installed": installed_bridge, "repo": repo_bridge,
                   "files_match": installed_tree is not None and installed_tree == repo_tree},
        "device": {"loaded": (loaded or {}).get("device_version"), "repo": repo_device, "library": libraries},
        "warnings": warnings,
        "ok": not warnings,
    }
