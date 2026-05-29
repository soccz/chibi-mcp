"""Small CLI helpers shipped alongside the MCP server.

`chibi-say <text>` — opens a transient connection to the local chibi WS
server (ws://127.0.0.1:9876 by default), publishes a say event, exits.
Used by Claude Code plugin hooks to make the pet react to tool calls.

Fails silently when no chibi server is running (so hooks don't break the
user's session).
"""

from __future__ import annotations

import json
import os
import sys


def say_main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: chibi-say <text...>", file=sys.stderr)
        return 2
    text = " ".join(args).strip()
    if not text:
        return 0

    host = os.environ.get("CHIBI_WS_HOST", "127.0.0.1")
    port = os.environ.get("CHIBI_WS_PORT", "9876")
    url = f"ws://{host}:{port}"

    try:
        from websockets.sync.client import connect as ws_connect
    except ImportError:
        return 0  # websockets missing — silent

    try:
        with ws_connect(url, open_timeout=3, close_timeout=1) as conn:
            conn.send(json.dumps({"type": "say", "text": text[:200]}))
    except Exception:
        # No window / server up. Silent.
        return 0
    return 0


def check_main(argv: list[str] | None = None) -> int:
    """`chibi-check` — quick offline asset + license self-check."""
    from .license import verify_license
    from .server import _resolve_asset_dir

    asset_dir = _resolve_asset_dir()
    if not asset_dir:
        print("FAIL: no asset directory found", file=sys.stderr)
        return 1
    print(f"asset_dir: {asset_dir}")
    print(f"license:   {verify_license().tier}")
    return 0


if __name__ == "__main__":
    sys.exit(say_main())
