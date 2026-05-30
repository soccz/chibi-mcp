"""Small CLI helpers shipped alongside the MCP server.

`chibi-say <text>` — opens a transient connection to the local chibi WS
server (ws://127.0.0.1:9876 by default), publishes a say event, exits.
`chibi-say --tool-call [text...]` records one Claude/Codex tool call and
optionally shows a speech bubble. Hooks use that form so rhythm milestones and
gacha tickets advance during real coding sessions, even when the bubble is
throttled.

Fails silently when no chibi server is running (so hooks don't break the
user's session).
"""

from __future__ import annotations

import json
import os
import sys

MAX_TEXT_LEN = 200


def _build_message(args: list[str]) -> dict | None:
    tool_call = bool(args and args[0] == "--tool-call")
    if tool_call:
        args = args[1:]
    text = " ".join(args).strip()
    if not tool_call and not text:
        return None
    message = {"type": "tool_call" if tool_call else "say"}
    if text:
        message["text"] = text[:MAX_TEXT_LEN]
    return message


def say_main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    message = _build_message(args)
    if message is None:
        print("usage: chibi-say [--tool-call] <text...>", file=sys.stderr)
        return 2

    host = os.environ.get("CHIBI_WS_HOST", "127.0.0.1")
    port = os.environ.get("CHIBI_WS_PORT", "9876")
    url = f"ws://{host}:{port}"

    try:
        from websockets.sync.client import connect as ws_connect
    except ImportError:
        return 0  # websockets missing — silent

    try:
        with ws_connect(url, open_timeout=3, close_timeout=1) as conn:
            conn.send(json.dumps(message))
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
