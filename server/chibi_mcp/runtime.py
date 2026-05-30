"""Runtime paths shared by CLI, server state, and the Tk window."""

from __future__ import annotations

import os
from pathlib import Path


def runtime_dir() -> Path:
    """Return the per-user chibi runtime directory.

    `CHIBI_RUNTIME_DIR` is intentionally supported for tests, CI, portable
    installs, and users who need the logs/state outside their OS home dir.
    """
    override = os.environ.get("CHIBI_RUNTIME_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".chibi-mcp"


def runtime_file(name: str) -> Path:
    return runtime_dir() / name
