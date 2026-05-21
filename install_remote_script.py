from __future__ import annotations

import platform
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS = ["Vibelton"]


def user_library() -> Path:
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        return home / "Music" / "Ableton" / "User Library"
    if system == "Windows":
        return home / "Documents" / "Ableton" / "User Library"
    return home / "Ableton" / "User Library"


def main() -> None:
    target_root = user_library() / "Remote Scripts"
    target_root.mkdir(parents=True, exist_ok=True)

    installed = []
    for script_name in SCRIPTS:
        source = ROOT / "ableton_remote_script" / script_name
        if not source.exists():
            raise SystemExit(f"Remote script source is missing: {source}")
        target = target_root / script_name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        installed.append(target)

    print("Installed Ableton remote script:")
    for target in installed:
        print(f"- {target}")
    print("Restart Ableton Live, then select Vibelton in Settings -> Link, Tempo & MIDI.")


if __name__ == "__main__":
    main()
