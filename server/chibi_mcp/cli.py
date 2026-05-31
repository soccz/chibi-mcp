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

import hashlib
import json
import os
import sys
from pathlib import Path

from .runtime import DEFAULT_WS_HOST, DEFAULT_WS_PORT

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

    host = os.environ.get("CHIBI_WS_HOST", DEFAULT_WS_HOST)
    port = os.environ.get("CHIBI_WS_PORT", str(DEFAULT_WS_PORT))
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


def verify_asset_manifest(asset_dir: str) -> dict:
    """Compare official asset hashes against the bundled ASSET_MANIFEST.sha256.

    Lets a user confirm offline that the official artwork in their install was
    not swapped by a copycat/tampered build. Returns ok=True with
    manifest_present=False when no manifest ships (older installs), so callers
    treat that as a soft skip rather than a failure.
    """
    base = Path(asset_dir)
    manifest = base / "ASSET_MANIFEST.sha256"
    if not manifest.exists():
        return {"ok": True, "manifest_present": False, "checked": 0, "mismatches": [], "missing": []}
    mismatches: list[str] = []
    missing: list[str] = []
    checked = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, rel = line.partition("  ")
        rel = rel.strip()
        if not rel:
            continue
        path = base / rel
        if not path.exists():
            missing.append(rel)
            continue
        checked += 1
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            mismatches.append(rel)
    return {
        "ok": not mismatches and not missing,
        "manifest_present": True,
        "checked": checked,
        "mismatches": mismatches,
        "missing": missing,
    }


def check_main(argv: list[str] | None = None) -> int:
    """`chibi-check` — quick offline asset + license + integrity self-check."""
    from .license import verify_license
    from .server import _resolve_asset_dir

    asset_dir = _resolve_asset_dir()
    if not asset_dir:
        print("FAIL: no asset directory found", file=sys.stderr)
        return 1
    print(f"asset_dir: {asset_dir}")
    print(f"license:   {verify_license().tier}")
    integrity = verify_asset_manifest(asset_dir)
    if not integrity["manifest_present"]:
        print("integrity: no manifest (older install)")
    elif integrity["ok"]:
        print(f"integrity: ok ({integrity['checked']} official assets verified)")
    else:
        print(
            f"integrity: FAIL mismatches={integrity['mismatches']} missing={integrity['missing']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(say_main())
