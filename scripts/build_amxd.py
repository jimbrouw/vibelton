#!/usr/bin/env python3
"""Pack m4l/Vibelton Arranger.maxpat into the .amxd container, or verify they match.

Container layout (observed from the shipped device): 28-byte header
('ampf' 4 'aaaa' 'meta' 4 <4 zero bytes>) + 'ptch' + little-endian length +
patcher JSON + NUL.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAXPAT = ROOT / "m4l" / "Vibelton Arranger.maxpat"
AMXD = ROOT / "m4l" / "Vibelton Arranger.amxd"
HEADER = b"ampf\x04\x00\x00\x00aaaameta\x04\x00\x00\x00\x00\x00\x00\x00ptch"


def pack(maxpat_bytes: bytes) -> bytes:
    json.loads(maxpat_bytes)  # refuse to pack invalid JSON
    body = maxpat_bytes + b"\x00"
    return HEADER + struct.pack("<I", len(body)) + body


def unpack(amxd_bytes: bytes) -> bytes:
    if not amxd_bytes.startswith(HEADER):
        raise ValueError("Not a recognised .amxd container")
    (length,) = struct.unpack("<I", amxd_bytes[len(HEADER):len(HEADER) + 4])
    body = amxd_bytes[len(HEADER) + 4:]
    if len(body) != length:
        raise ValueError(f"Length field {length} does not match body {len(body)}")
    return body[:-1] if body.endswith(b"\x00") else body


def in_sync() -> bool:
    return AMXD.read_bytes() == pack(MAXPAT.read_bytes())


def main(argv: list[str]) -> int:
    if "--check" in argv:
        ok = in_sync()
        print("amxd matches maxpat" if ok else "amxd is STALE: run scripts/build_amxd.py")
        return 0 if ok else 1
    AMXD.write_bytes(pack(MAXPAT.read_bytes()))
    print(f"wrote {AMXD}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
