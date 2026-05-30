"""chibi-mcp entry point.

Runs the MCP stdio transport for Claude Code AND a localhost WebSocket server
(for the desktop app) in the same asyncio loop.

Install:
    pip install chibi-mcp

Register with Claude Code:
    claude mcp add chibi -- chibi-mcp

Then launch the chibi-desktop app, which will connect to ws://localhost:9876.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import logging
import os
import signal
import sys
import threading
from contextlib import suppress
from pathlib import Path

from . import __version__
from . import server as server_tools
from .server import _resolve_asset_dir
from .ws_server import DEFAULT_WS_HOST, DEFAULT_WS_PORT, run_ws_server


def _setup_logging() -> None:
    level_name = os.environ.get("CHIBI_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
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
    # Keep stdout under our control. FastMCP's stdio transport currently emits
    # startup output and has caused Claude Code health checks to fail.
    mcp_task = asyncio.create_task(_run_mcp_stdio())

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


_TOOL_FUNCTIONS = {
    "get_pet_state": server_tools.get_pet_state,
    "pet_say": server_tools.pet_say,
    "slice_now": server_tools.slice_now,
    "get_license_status": server_tools.get_license_status,
    "get_catalog": server_tools.get_catalog,
    "get_options": server_tools.get_options,
    "set_active_options": server_tools.set_active_options,
    "clear_active_options": server_tools.clear_active_options,
    "open_pet_window": server_tools.open_pet_window,
    "close_pet_window": server_tools.close_pet_window,
    "set_slice_interval": server_tools.set_slice_interval,
    "pull_gacha": server_tools.pull_gacha,
    "get_inventory": server_tools.get_inventory,
    "set_active_character": server_tools.set_active_character,
    "rename_character": server_tools.rename_character,
    "add_ticket": server_tools.add_ticket,
}


def _annotation_schema(annotation: object) -> dict:
    if annotation in {str, str | None, "str", "str | None"}:
        return {"type": "string"}
    if annotation in {int, "int"}:
        return {"type": "integer"}
    if annotation in {list[str], list, "list[str]", "list"}:
        return {"type": "array", "items": {"type": "string"}}
    return {}


def _tool_schema(fn) -> dict:
    signature = inspect.signature(fn)
    properties: dict[str, dict] = {}
    required: list[str] = []
    for name, parameter in signature.parameters.items():
        properties[name] = _annotation_schema(parameter.annotation)
        if parameter.default is inspect.Parameter.empty:
            required.append(name)
    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _tool_descriptor(name: str, fn) -> dict:
    return {
        "name": name,
        "description": inspect.getdoc(fn) or "",
        "inputSchema": _tool_schema(fn),
    }


def _jsonrpc_result(message_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _jsonrpc_error(message_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _write_jsonrpc(message: dict) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _call_tool(name: str, arguments: dict | None) -> dict:
    fn = _TOOL_FUNCTIONS.get(name)
    if fn is None:
        payload = {"ok": False, "reason": f"unknown tool: {name}"}
        return {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
            "structuredContent": payload,
            "isError": True,
        }

    try:
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise TypeError("tool arguments must be an object")
        payload = fn(**arguments)
        is_error = False
    except Exception as exc:
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        is_error = True

    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
        "structuredContent": payload,
        "isError": is_error,
    }


def _handle_mcp_message(message: dict) -> dict | None:
    method = message.get("method")
    message_id = message.get("id")
    params = message.get("params") or {}

    if method == "initialize":
        requested_version = (
            params.get("protocolVersion") if isinstance(params, dict) else None
        ) or "2025-11-25"
        return _jsonrpc_result(
            message_id,
            {
                "protocolVersion": requested_version,
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "chibi-mcp", "version": __version__},
            },
        )
    if method and str(method).startswith("notifications/"):
        return None
    if method == "ping":
        return _jsonrpc_result(message_id, {})
    if method == "tools/list":
        return _jsonrpc_result(
            message_id,
            {
                "tools": [
                    _tool_descriptor(name, fn) for name, fn in sorted(_TOOL_FUNCTIONS.items())
                ]
            },
        )
    if method == "tools/call":
        if not isinstance(params, dict):
            return _jsonrpc_error(message_id, -32602, "invalid tools/call params")
        return _jsonrpc_result(
            message_id,
            _call_tool(str(params.get("name") or ""), params.get("arguments") or {}),
        )
    if method == "resources/list":
        return _jsonrpc_result(message_id, {"resources": []})
    if method == "resources/templates/list":
        return _jsonrpc_result(message_id, {"resourceTemplates": []})
    if method == "prompts/list":
        return _jsonrpc_result(message_id, {"prompts": []})
    if method == "logging/setLevel":
        return _jsonrpc_result(message_id, {})
    return _jsonrpc_error(message_id, -32601, f"method not found: {method}")


async def _run_mcp_stdio() -> None:
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _read_stdin_lines() -> None:
        try:
            for stdin_line in sys.stdin:
                loop.call_soon_threadsafe(queue.put_nowait, stdin_line)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=_read_stdin_lines, daemon=True).start()

    while True:
        line = await queue.get()
        if line is None:
            return
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("message must be an object")
            response = _handle_mcp_message(message)
        except Exception as exc:
            response = _jsonrpc_error(None, -32700, f"parse error: {exc}")
        if response is not None:
            _write_jsonrpc(response)


async def _run_ws_only() -> None:
    host, port = _ws_endpoint()
    await run_ws_server(host=host, port=port)


def _check() -> dict:
    asset_dir = _resolve_asset_dir()
    assets_ok = False
    free_assets_missing: list[str] = []
    free_options_missing: list[str] = []
    catalog_count = 0
    option_count = 0
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
            options = catalog.get("options", [])
            catalog_count = len(chars)
            option_count = len(options)
            for ch in chars:
                if ch.get("tier") == "free" and not (Path(asset_dir) / f"{ch['id']}.png").exists():
                    free_assets_missing.append(ch["id"])
            for option in options:
                image = option.get("image") or f"options/{option.get('id')}.png"
                if option.get("tier") == "free" and not (Path(asset_dir) / str(image)).exists():
                    free_options_missing.append(option.get("id", "<missing-id>"))
            assets_ok = catalog_error is None and not free_assets_missing and not free_options_missing

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
        "option_count": option_count,
        "free_assets_missing": free_assets_missing,
        "free_options_missing": free_options_missing,
        "tkinter": tkinter_ok,
        "ws_default": f"ws://{DEFAULT_WS_HOST}:{DEFAULT_WS_PORT}",
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="chibi-mcp",
        description="MCP server for chibi, the local coding pet.",
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
