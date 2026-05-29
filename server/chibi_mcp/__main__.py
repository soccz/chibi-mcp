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

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from contextlib import suppress
from pathlib import Path

from . import __version__
from .server import _resolve_asset_dir, mcp
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


def _ws_endpoint() -> tuple[str, int]:
    host = os.environ.get("CHIBI_WS_HOST", DEFAULT_WS_HOST)
    port_raw = os.environ.get("CHIBI_WS_PORT", str(DEFAULT_WS_PORT))
    try:
        port = int(port_raw)
        if not 1 <= port <= 65535:
            raise ValueError("out of range")
    except ValueError:
        logging.getLogger(__name__).warning(
            "invalid CHIBI_WS_PORT=%r; falling back to %d", port_raw, DEFAULT_WS_PORT
        )
        port = DEFAULT_WS_PORT
    return host, port


async def _run_ws_optional(host: str, port: int) -> None:
    """Run WS if available; keep MCP alive if another process owns the port."""
    log = logging.getLogger(__name__)
    try:
        await run_ws_server(host=host, port=port)
    except OSError as e:
        log.warning("ws://%s:%d unavailable (%s); continuing with MCP stdio only", host, port, e)
        await asyncio.Event().wait()


async def _run_concurrent(ws_enabled: bool = True) -> None:
    """Run MCP (stdio) and WebSocket server concurrently."""
    host, port = _ws_endpoint()

    ws_task = asyncio.create_task(_run_ws_optional(host=host, port=port)) if ws_enabled else None
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
            {t for t in (mcp_task, ws_task, stop) if t is not None},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in done:
            exc = t.exception() if not t.cancelled() else None
            if exc:
                logging.getLogger(__name__).error("task failed: %r", exc)
    finally:
        for t in (mcp_task, ws_task):
            if t is None:
                continue
            if not t.done():
                t.cancel()
        with suppress(asyncio.CancelledError):
            await asyncio.gather(*(t for t in (mcp_task, ws_task) if t is not None), return_exceptions=True)


async def _run_ws_only() -> None:
    host, port = _ws_endpoint()
    await run_ws_server(host=host, port=port)


def _check() -> dict:
    asset_dir = _resolve_asset_dir()
    assets_ok = False
    free_assets_missing: list[str] = []
    catalog_count = 0
    catalog_error: str | None = None
    if asset_dir:
        meta_path = Path(asset_dir) / "meta.json"
        if meta_path.exists():
            try:
                catalog = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                catalog_error = f"{type(e).__name__}: {e}"
                catalog = {"characters": []}
            chars = catalog.get("characters", [])
            catalog_count = len(chars)
            for ch in chars:
                if ch.get("tier") == "free" and not (Path(asset_dir) / f"{ch['id']}.png").exists():
                    free_assets_missing.append(ch["id"])
            assets_ok = catalog_error is None and not free_assets_missing

    try:
        import tkinter  # noqa: F401

        tkinter_ok = True
    except Exception:
        tkinter_ok = False

    return {
        "ok": bool(asset_dir and assets_ok),
        "version": __version__,
        "asset_dir": asset_dir,
        "catalog_count": catalog_count,
        "free_assets_missing": free_assets_missing,
        "tkinter": tkinter_ok,
        "ws_default": f"ws://{DEFAULT_WS_HOST}:{DEFAULT_WS_PORT}",
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="chibi-mcp",
        description="MCP server for tteoki, the Korean rice cake coding pet.",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--check", action="store_true", help="Check assets and local runtime support")
    parser.add_argument("--ws-only", action="store_true", help="Run only the localhost WebSocket server")
    parser.add_argument("--no-ws", action="store_true", help="Run MCP stdio without the WebSocket server")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.check:
        result = _check()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    _setup_logging()
    log = logging.getLogger("chibi_mcp")
    host, port = _ws_endpoint()
    if args.ws_only:
        log.info("chibi-mcp starting (ws://%s:%d only)", host, port)
        with suppress(KeyboardInterrupt):
            asyncio.run(_run_ws_only())
    else:
        mode = "stdio MCP only" if args.no_ws else f"stdio MCP + ws://{host}:{port}"
        log.info("chibi-mcp starting (%s)", mode)
        with suppress(KeyboardInterrupt):
            asyncio.run(_run_concurrent(ws_enabled=not args.no_ws))
    log.info("chibi-mcp stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
