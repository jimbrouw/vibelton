"""Local-server access control: per-session token, Origin and Host checks."""
from __future__ import annotations

import hmac
import os
import secrets
import threading
import time
from pathlib import Path

TOKEN_HEADER = "X-Vibelton-Token"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "[::1]")

_token: str | None = None


def home_dir() -> Path:
    return Path(os.environ.get("VIBELTON_HOME") or (Path.home() / ".vibelton"))


def token_path() -> Path:
    return home_dir() / "session_token"


def issue_token() -> str:
    """Generate a fresh token and write it to a 0600 file owned by the user."""
    global _token
    _token = secrets.token_urlsafe(32)
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(_token)
    os.chmod(path, 0o600)
    return _token


def current_token() -> str:
    return _token if _token is not None else issue_token()


def token_valid(supplied: str | None) -> bool:
    if not supplied:
        return False
    return hmac.compare_digest(supplied.encode("utf-8"), current_token().encode("utf-8"))


def host_allowed(host_header: str | None) -> bool:
    """Reject DNS-rebinding: Host must be a loopback name."""
    if not host_header:
        return False
    host = host_header.strip().lower()
    name = host.rsplit(":", 1)[0] if not host.endswith("]") else host
    return name in LOOPBACK_HOSTS


def own_origins(port: int) -> set[str]:
    return {f"http://{h}:{port}" for h in LOOPBACK_HOSTS}


def origin_allowed(origin: str | None, port: int) -> bool:
    """Absent Origin (curl, jweb navigation) and our own origins pass.

    The literal "null" origin also passes this check; it can never read the
    token (no CORS headers are sent for it), so the token remains the gate.
    """
    if origin is None or origin == "null":
        return True
    return origin in own_origins(port)


def cors_origin(origin: str | None, port: int) -> str | None:
    """Value for Access-Control-Allow-Origin, or None to send no CORS header."""
    if origin and origin in own_origins(port):
        return origin
    return None


# --- Shared-use hardening -------------------------------------------------

MAX_BODY_BYTES = 32_000_000          # largest body any endpoint accepts (composition payloads)
SMALL_BODY_BYTES = 1_000_000         # chat / feedback / theory / device hello style bodies
RATE_LIMIT_PER_MINUTE = int(os.environ.get("VIBELTON_RATE_LIMIT", "240"))

_hits: list[float] = []
_hits_lock = threading.Lock()


def rate_limited(now: float | None = None, limit: int | None = None) -> bool:
    """True when more than ``limit`` state-changing requests arrived in the last minute."""
    limit = RATE_LIMIT_PER_MINUTE if limit is None else limit
    now = time.monotonic() if now is None else now
    with _hits_lock:
        while _hits and now - _hits[0] > 60.0:
            _hits.pop(0)
        if len(_hits) >= limit:
            return True
        _hits.append(now)
        return False


def reset_rate_limit() -> None:
    with _hits_lock:
        _hits.clear()


def body_too_large(content_length: str | None, small: bool = False) -> bool:
    try:
        length = int(content_length or "0")
    except ValueError:
        return True
    return length < 0 or length > (SMALL_BODY_BYTES if small else MAX_BODY_BYTES)


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    # The device page and popout are only ever framed by this same origin (jweb loads it top-level).
    "X-Frame-Options": "SAMEORIGIN",
    "Cross-Origin-Resource-Policy": "same-origin",
}
