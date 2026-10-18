"""Keep a user's home directory out of text they might paste into a bug report."""
from __future__ import annotations

import os
from pathlib import Path


def home_to_tilde(text: object) -> str:
    """Replace the home directory (and its resolved form) with ``~``."""
    value = str(text)
    homes = {str(Path.home()), os.path.realpath(str(Path.home()))}
    for home in sorted(homes, key=len, reverse=True):
        if home and home != "/":
            value = value.replace(home, "~")
    return value
