"""FastMCP server — tools Claude Code calls to interact with tteoki."""

from __future__ import annotations

import asyncio
import logging

from fastmcp import FastMCP

from .state import get_state
from .ws_server import get_broadcaster

log = logging.getLogger(__name__)

mcp = FastMCP("chibi-mcp")


def _record_call_and_maybe_slice() -> dict:
    """Increment counter; if slice milestone hit, broadcast a slice event."""
    state = get_state()
    result = state.record_call()
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
        text: short message (≤ 60 chars recommended).

    Returns:
        Confirmation dict with the broadcast status.
    """
    counter = _record_call_and_maybe_slice()

    broadcaster = get_broadcaster()
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcaster.broadcast({"type": "say", "text": text}))
        broadcasted = True
    except RuntimeError:
        broadcasted = False

    return {
        "spoken": text,
        "broadcasted": broadcasted,
        "counter": counter,
    }


@mcp.tool()
def slice_now() -> dict:
    """Manually trigger a slice (force the lengthen-cycle to reset).

    Useful when the user wants to mark a milestone without waiting for the
    N-call automatic trigger.
    """
    state = get_state()
    state.calls_since_slice = state.slice_interval  # force next record_call to slice
    counter = _record_call_and_maybe_slice()

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
