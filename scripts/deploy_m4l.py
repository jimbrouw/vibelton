#!/usr/bin/env python3
"""Deploy the Vibelton Arranger device to the Ableton User Library.

Dry-run by default; pass --apply to copy. Refuses to deploy when:
  * the .amxd is not an exact pack of the .maxpat (run scripts/build_amxd.py),
  * a JS file the patcher's node.script/js objects reference is missing,
  * (frozen devices) a referenced JS file's bytes are not found inside the .amxd.
After copying it re-hashes every file and fails on any mismatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_amxd  # noqa: E402

ROOT = build_amxd.ROOT
M4L = ROOT / "m4l"
DEVICE = "Vibelton Arranger.amxd"
SUPPORT_JS = ("daemon_guard.js", "autoresize.js")
USER_LIBRARY = Path.home() / "Music" / "Ableton" / "User Library" / "Presets" / "Audio Effects" / "Max Audio Effect"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def referenced_js(maxpat: dict) -> set[str]:
    found: set[str] = set()

    def walk(patcher: dict) -> None:
        for item in patcher.get("boxes", []):
            box = item["box"]
            found.update(re.findall(r"[\w.-]+\.js\b", str(box.get("text", ""))))
            if "patcher" in box:
                walk(box["patcher"])
    walk(maxpat["patcher"])
    return found


def preflight(m4l: Path = M4L) -> list[str]:
    """Return a list of problems; empty means safe to deploy."""
    problems: list[str] = []
    maxpat_path, amxd_path = m4l / "Vibelton Arranger.maxpat", m4l / DEVICE
    if not amxd_path.is_file() or not maxpat_path.is_file():
        return ["device or patcher source missing from m4l/"]
    if amxd_path.read_bytes() != build_amxd.pack(maxpat_path.read_bytes()):
        problems.append(".amxd does not match .maxpat (run scripts/build_amxd.py)")
    for name in sorted(referenced_js(json.loads(maxpat_path.read_bytes()))):
        if not (m4l / name).is_file():
            problems.append(f"patcher references {name} but it is not in m4l/")
    amxd_bytes = amxd_path.read_bytes()
    if b"dlst" in amxd_bytes:  # frozen: embedded files must equal the repo copies
        for name in SUPPORT_JS:
            if (m4l / name).is_file() and (m4l / name).read_bytes() not in amxd_bytes:
                problems.append(f"frozen device embeds a different {name} than the repo; re-freeze it")
    return problems


def plan(targets: list[Path], m4l: Path = M4L) -> list[tuple[Path, Path, str]]:
    """(source, destination, state) for every file; state: same | differs | missing."""
    out = []
    for target in targets:
        for name in (DEVICE, *SUPPORT_JS):
            src, dst = m4l / name, target / name
            state = "missing" if not dst.exists() else ("same" if sha(src) == sha(dst) else "differs")
            out.append((src, dst, state))
    return out


def stale_support_files(folders: list[Path]) -> list[Path]:
    """Support JS files sitting in a folder that has no device beside them (never loaded by anything)."""
    return [folder / name for folder in folders if folder.is_dir() and not (folder / DEVICE).exists()
            for name in SUPPORT_JS if (folder / name).is_file()]


def deploy(targets: list[Path], m4l: Path = M4L) -> list[str]:
    problems = preflight(m4l)
    if problems:
        return problems
    for src, dst, state in plan(targets, m4l):
        if state != "same":
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return [f"{dst} differs after copy" for src, dst, _ in plan(targets, m4l) if sha(src) != sha(dst)]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="copy files (default: dry run)")
    parser.add_argument("--target", action="append", type=Path,
                        help="deploy folder (repeatable); default: User Library folders that already hold the device, else the Max Audio Effect folder")
    parser.add_argument("--clean-stale", action="store_true",
                        help="list (and with --apply delete) daemon_guard.js/autoresize.js in folders with no device; deploys nothing")
    args = parser.parse_args(argv)
    if args.clean_stale:
        folders = args.target or [USER_LIBRARY, USER_LIBRARY / "m4l"]
        stale = stale_support_files(folders)
        for path in stale:
            print(f"{'removing' if args.apply else 'would remove'} {path}")
        if not stale:
            print("no stale support files")
        elif args.apply:
            for path in stale:
                path.unlink()
        else:
            print("dry run: nothing removed (use --clean-stale --apply)")
        return 0
    # Default: only folders that already hold the device, so no stray copies appear.
    existing = [t for t in (USER_LIBRARY, USER_LIBRARY / "m4l") if (t / DEVICE).exists()]
    # First install: put the device where Live's browser lists Max Audio Effects.
    targets = args.target or existing or [USER_LIBRARY]
    problems = preflight()
    for problem in problems:
        print("BLOCKED:", problem)
    if problems:
        return 1
    for src, dst, state in plan(targets):
        print(f"{state:8} {dst}")
    if not args.apply:
        print("dry run: nothing copied (use --apply)")
        return 0
    problems = deploy(targets)
    for problem in problems:
        print("FAILED:", problem)
    print("deployed and verified" if not problems else "deploy failed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
