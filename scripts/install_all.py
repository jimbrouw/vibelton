#!/usr/bin/env python3
"""One-step install of Vibelton Arranger: Remote Script + Max device + default config.

Dry run by default; pass --apply to change anything.  It never overwrites an existing
~/.vibelton/config.json, never touches Live's preferences, and never starts Live.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_amxd  # noqa: E402
import deploy_m4l  # noqa: E402
import install_remote_script  # noqa: E402

ROOT = build_amxd.ROOT
MIN_PYTHON = (3, 11)


def library_for(home: Path) -> Path:
    return home / "Music" / "Ableton" / "User Library"


def device_folder(library: Path) -> Path:
    return library / "Presets" / "Audio Effects" / "Max Audio Effect"


def device_targets(library: Path) -> list[Path]:
    """Folders that already hold the device (so no stray second copy appears), else the standard one."""
    folder = device_folder(library)
    return [t for t in (folder, folder / "m4l") if (t / deploy_m4l.DEVICE).exists()] or [folder]


def preflight(home: Path, version=sys.version_info) -> list[str]:
    """Reasons the install cannot safely go ahead (empty list = go)."""
    problems = []
    if tuple(version[:2]) < MIN_PYTHON:
        problems.append("Python %d.%d or newer is required (this is %d.%d)." % (MIN_PYTHON + tuple(version[:2])))
    if sys.platform != "darwin":
        problems.append("Only macOS is supported by this installer.")
    if not library_for(home).parent.is_dir():
        problems.append("Ableton's User Library was not found at %s. Open Live once, then retry." % library_for(home))
    problems += ["Device: " + p for p in deploy_m4l.preflight()]
    return problems


def run(home: Path, apply: bool, python_path: str = sys.executable, out=print) -> int:
    problems = preflight(home)
    for problem in problems:
        out("BLOCKED: " + problem)
    if problems:
        return 1
    library = library_for(home)
    config = home / ".vibelton" / "config.json"
    out("%s Remote Script -> %s" % ("Would install" if not apply else "Installing", library / "Remote Scripts" / "Vibelton"))
    out("%s device     -> %s" % ("Would deploy" if not apply else "Deploying", ", ".join(str(t) for t in device_targets(library))))
    out("%s config     -> %s%s" % ("Would keep" if config.exists() else ("Would write" if not apply else "Writing"), config,
                                  " (already exists, left untouched)" if config.exists() else ""))
    if not apply:
        out("Dry run: nothing changed. Re-run with --apply.")
        return 0
    install_remote_script.install(library)
    failed = deploy_m4l.deploy(device_targets(library))
    if failed:
        for item in failed:
            out("FAILED: " + item)
        return 1
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps({"repo_path": str(ROOT), "python_path": python_path}, indent=2) + "\n", encoding="utf-8")
    out("")
    out("Done. Next steps (these cannot be automated):")
    out("  1. Quit and reopen Ableton Live.")
    out("  2. Settings > Link, Tempo & MIDI > Control Surface: choose Vibelton.")
    out("  3. Save your Set as a working copy whose name contains 'vibelton-working-copy'.")
    out("  4. Drag 'Vibelton Arranger' (User Library > Audio Effects > Max Audio Effect) onto an audio track.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="make the changes (default: dry run)")
    args = parser.parse_args(argv)
    return run(Path.home(), args.apply)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
