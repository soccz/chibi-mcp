"""FastMCP server — tools Claude Code calls to interact with tteoki."""

from __future__ import annotations

import asyncio
import logging

from fastmcp import FastMCP

from .state import get_state
from .ws_server import get_broadcaster

log = logging.getLogger(__name__)

mcp = FastMCP("chibi-mcp")


# Limits for incoming MCP tool inputs. Claude may emit large strings — we
# defend the desktop UI from rendering pathological payloads.
MAX_SAY_LEN = 200
SAY_CONTROL_CHARS = "".join(chr(c) for c in range(32) if c not in (9, 10))  # keep tab+LF


def _sanitize_say(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    # Drop control characters (except tab and newline)
    cleaned = text.translate({ord(c): None for c in SAY_CONTROL_CHARS})
    # Collapse to single line for speech bubble
    cleaned = cleaned.replace("\r", " ").replace("\n", " ").strip()
    if len(cleaned) > MAX_SAY_LEN:
        cleaned = cleaned[: MAX_SAY_LEN - 1] + "…"
    return cleaned


def _record_call_and_maybe_slice(force_slice: bool = False) -> dict:
    """Increment counter; if slice milestone hit, broadcast a slice event."""
    state = get_state()
    result = state.record_call(force_slice=force_slice)
    if result["sliced"]:
        broadcaster = get_broadcaster()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(broadcaster.broadcast({"type": "slice"}))
        except RuntimeError:
            # No loop in current thread — best-effort, skip broadcast
            log.debug("slice event skipped (no running loop)")
    return result


@mcp.tool()
def get_pet_state() -> dict:
    """Return tteoki's current state: mood, system metrics, counters, timing.

    The desktop app reads this to render the character. Calling this tool
    counts as a Claude interaction and may trigger a slice every N calls.
    """
    counter = _record_call_and_maybe_slice()
    state = get_state()
    snapshot = state.snapshot()
    snapshot["last_call_result"] = counter
    return snapshot


@mcp.tool()
def pet_say(text: str) -> dict:
    """Make tteoki say something via a speech bubble in the desktop app.

    Args:
        text: short message (≤ 200 chars; longer text is truncated with "…").
              Control characters and newlines are stripped to keep the bubble
              renderable.

    Returns:
        Confirmation dict with the sanitized text and broadcast status.
    """
    safe = _sanitize_say(text)
    counter = _record_call_and_maybe_slice()

    broadcaster = get_broadcaster()
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcaster.broadcast({"type": "say", "text": safe}))
        broadcasted = True
    except RuntimeError:
        broadcasted = False

    return {
        "spoken": safe,
        "broadcasted": broadcasted,
        "counter": counter,
    }


@mcp.tool()
def slice_now() -> dict:
    """Manually trigger a slice (force the lengthen-cycle to reset).

    Useful when the user wants to mark a milestone without waiting for the
    N-call automatic trigger.
    """
    counter = _record_call_and_maybe_slice(force_slice=True)
    return {
        "forced": True,
        "counter": counter,
    }


@mcp.tool()
def set_slice_interval(n: int) -> dict:
    """Change how often (every N Claude tool calls) tteoki gets sliced.

    Args:
        n: positive integer. Default is 10. Suggested values: 5, 10, 25, 50, 100.
    """
    if n < 1:
        raise ValueError("slice interval must be ≥ 1")
    state = get_state()
    old = state.slice_interval
    state.slice_interval = n
    return {"previous": old, "current": n}
