"""chibi-mcp entry point.

Runs the FastMCP server (stdio transport for Claude Code) AND a localhost
WebSocket server (for the desktop app) in the same asyncio loop.

Install:
    pip install chibi-mcp

Register with Claude Code:
    claude mcp add chibi -- chibi-mcp

Then launch the chibi-desktop app, which will connect to ws://localhost:9876.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from contextlib import suppress

from .server import mcp
from .ws_server import DEFAULT_WS_HOST, DEFAULT_WS_PORT, run_ws_server


def _setup_logging() -> None:
    level_name = os.environ.get("CHIBI_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    # Log to stderr — stdout is reserved for MCP stdio transport
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def _run_concurrent() -> None:
    """Run MCP (stdio) and WebSocket server concurrently."""
    host = os.environ.get("CHIBI_WS_HOST", DEFAULT_WS_HOST)
    port = int(os.environ.get("CHIBI_WS_PORT", DEFAULT_WS_PORT))

    ws_task = asyncio.create_task(run_ws_server(host=host, port=port))
    # FastMCP's run_stdio_async is the asyncio variant of mcp.run()
    mcp_task = asyncio.create_task(mcp.run_stdio_async())

    # Graceful shutdown on SIGTERM/SIGINT
    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    def _signal_stop() -> None:
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _signal_stop)

    try:
        # Wait for any of: MCP exit, WS exit, signal
        done, _pending = await asyncio.wait(
            {mcp_task, ws_task, stop},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in done:
            exc = t.exception() if not t.cancelled() else None
            if exc:
                logging.getLogger(__name__).error("task failed: %r", exc)
    finally:
        for t in (mcp_task, ws_task):
            if not t.done():
                t.cancel()
        with suppress(asyncio.CancelledError):
            await asyncio.gather(mcp_task, ws_task, return_exceptions=True)


def main() -> int:
    _setup_logging()
    log = logging.getLogger("chibi_mcp")
    log.info("chibi-mcp starting (stdio MCP + ws://%s:%d)",
             os.environ.get("CHIBI_WS_HOST", DEFAULT_WS_HOST),
             int(os.environ.get("CHIBI_WS_PORT", DEFAULT_WS_PORT)))
    with suppress(KeyboardInterrupt):
        asyncio.run(_run_concurrent())
    log.info("chibi-mcp stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
