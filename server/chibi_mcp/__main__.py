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
import shutil
import signal
import subprocess
import sys
import threading
import time
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
    payload = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    stdout_buffer = getattr(sys.stdout, "buffer", None)
    if stdout_buffer is None:
        sys.stdout.write(payload.decode("utf-8"))
        sys.stdout.flush()
    else:
        stdout_buffer.write(payload)
        stdout_buffer.flush()


def _decode_stdin_line(raw_line: str | bytes) -> str:
    return (
        raw_line.decode("utf-8", errors="replace")
        if isinstance(raw_line, bytes)
        else raw_line
    )


def _handle_mcp_line(line: str) -> None:
    if not line.strip():
        return
    try:
        message = json.loads(line)
        if not isinstance(message, dict):
            raise ValueError("message must be an object")
        response = _handle_mcp_message(message)
    except Exception as exc:
        response = _jsonrpc_error(None, -32700, f"parse error: {exc}")
    if response is not None:
        _write_jsonrpc(response)


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
        stdin_stream = getattr(sys.stdin, "buffer", sys.stdin)
        try:
            for raw_line in stdin_stream:
                loop.call_soon_threadsafe(queue.put_nowait, _decode_stdin_line(raw_line))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=_read_stdin_lines, daemon=True).start()

    while True:
        line = await queue.get()
        if line is None:
            return
        _handle_mcp_line(line)


def _run_mcp_stdio_sync() -> None:
    stdin_stream = getattr(sys.stdin, "buffer", sys.stdin)
    for raw_line in stdin_stream:
        _handle_mcp_line(_decode_stdin_line(raw_line))


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


def _run_client_command(args: list[str], timeout: float = 8.0) -> dict:
    executable = shutil.which(args[0])
    if executable is None:
        return {
            "installed": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "status": "missing",
        }
    try:
        completed = subprocess.run(
            [executable, *args[1:]],
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "installed": True,
            "returncode": None,
            "stdout": "",
            "stderr": "timed out",
            "status": "timeout",
        }
    except OSError as exc:
        return {
            "installed": True,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "status": "error",
        }
    return {
        "installed": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
        "status": "ok" if completed.returncode == 0 else "error",
    }


def _compact_output(text: str) -> str:
    return " ".join(text.strip().split())[:240]


def _auth_status_from_output(client: str, result: dict) -> dict:
    if not result.get("installed"):
        return {
            "installed": False,
            "status": "missing",
            "next_step": f"Install {client} CLI first.",
        }

    stdout = str(result.get("stdout") or "")
    stderr = str(result.get("stderr") or "")
    combined = f"{stdout}\n{stderr}".strip()
    lower = combined.lower()

    if result.get("returncode") == 0:
        if client == "claude":
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                payload = {}
            if payload.get("loggedIn") is False:
                return {
                    "installed": True,
                    "status": "login_required",
                    "next_step": "Run /login in Claude Code or `claude auth login` in a terminal.",
                }
            return {
                "installed": True,
                "status": "ok",
                "auth_method": payload.get("authMethod") or "detected",
                "api_provider": payload.get("apiProvider"),
            }
        return {"installed": True, "status": "ok"}

    if any(term in lower for term in ("401", "login", "log in", "not authenticated", "auth")):
        next_step = (
            "Run /login in Claude Code or `claude auth login` in a terminal."
            if client == "claude"
            else "Run `codex login`, then retry the chibi command."
        )
        return {
            "installed": True,
            "status": "login_required",
            "next_step": next_step,
            "message": _compact_output(combined),
        }

    return {
        "installed": True,
        "status": "unknown",
        "next_step": f"Run `{client} --help` and check the CLI install.",
        "message": _compact_output(combined),
    }


def _mcp_registration_status(client: str, mcp_name: str) -> dict:
    result = _run_client_command([client, "mcp", "get", mcp_name], timeout=12.0)
    if not result.get("installed"):
        return {"status": "missing_client"}
    combined = f"{result.get('stdout') or ''}\n{result.get('stderr') or ''}"
    if result.get("returncode") == 0:
        return {"status": "registered"}
    if result.get("status") == "timeout":
        return {
            "status": "unknown",
            "next_step": f"Run `{client} mcp get {mcp_name}` directly; the client did not answer the doctor check in time.",
            "message": _compact_output(combined),
        }
    if "no mcp server" not in combined.lower() and "not found" not in combined.lower():
        return {
            "status": "unknown",
            "next_step": f"Run `{client} mcp get {mcp_name}` directly and inspect the client output.",
            "message": _compact_output(combined),
        }
    return {
        "status": "not_registered",
        "next_step": f"Run `{client} mcp add {mcp_name} -- chibi-mcp`.",
        "message": _compact_output(combined),
    }


def _vscode_status() -> dict:
    result = _run_client_command(["code", "--list-extensions"], timeout=12.0)
    if not result.get("installed"):
        return {
            "installed": False,
            "status": "missing",
            "next_step": "Install VS Code and add the `code` command to PATH.",
        }
    combined = f"{result.get('stdout') or ''}\n{result.get('stderr') or ''}"
    if result.get("returncode") != 0:
        return {
            "installed": True,
            "status": "unknown",
            "next_step": "Open VS Code once, install the `code` command in PATH, then rerun.",
            "message": _compact_output(combined),
        }
    extensions = {line.strip().lower() for line in str(result.get("stdout") or "").splitlines()}
    if "soccz.chibi-mcp" in extensions:
        return {"installed": True, "status": "ok", "extension": "soccz.chibi-mcp"}
    return {
        "installed": True,
        "status": "extension_missing",
        "next_step": "Run the VS Code installer or `code --install-extension chibi-mcp-*.vsix --force`.",
    }


def _doctor(mcp_name: str = "chibi") -> dict:
    local = _check()
    claude_auth = _auth_status_from_output(
        "claude", _run_client_command(["claude", "auth", "status"], timeout=8.0)
    )
    codex_auth = _auth_status_from_output(
        "codex", _run_client_command(["codex", "login", "status"], timeout=8.0)
    )
    clients = {
        "claude": {
            "auth": claude_auth,
            "mcp": _mcp_registration_status("claude", mcp_name),
        },
        "codex": {
            "auth": codex_auth,
            "mcp": _mcp_registration_status("codex", mcp_name),
        },
        "vscode": _vscode_status(),
    }
    client_ready = {
        "claude": clients["claude"]["auth"].get("status") == "ok"
        and clients["claude"]["mcp"].get("status") == "registered",
        "codex": clients["codex"]["auth"].get("status") == "ok"
        and clients["codex"]["mcp"].get("status") == "registered",
        "vscode": clients["vscode"].get("status") == "ok",
    }
    next_steps: list[str] = []
    if not local.get("tkinter"):
        next_steps.append("Install Python tkinter/Tcl-Tk support, then reinstall chibi-mcp.")
    for client_name, client_status in clients.items():
        if client_name in {"claude", "codex"}:
            for section in ("auth", "mcp"):
                step = client_status[section].get("next_step")
                if step:
                    next_steps.append(step)
        else:
            step = client_status.get("next_step")
            if step:
                next_steps.append(step)
    return {
        "ok": bool(local.get("ok")),
        "ready": bool(local.get("ok")) and all(client_ready.values()),
        "version": __version__,
        "local": local,
        "clients": clients,
        "client_ready": client_ready,
        "next_steps": next_steps,
    }


def _ws_accepts(host: str, port: int, *, timeout: float = 0.6) -> bool:
    url = f"ws://{host}:{port}"
    try:
        from websockets.sync.client import connect as ws_connect

        with ws_connect(url, open_timeout=timeout, close_timeout=0.2):
            return True
    except Exception:
        return False


def _runtime_dir() -> Path:
    override = os.environ.get("CHIBI_RUNTIME_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".chibi-mcp"


def _ensure_ws_server_for_open() -> dict:
    host, port = _ws_endpoint()
    url = f"ws://{host}:{port}"
    if _ws_accepts(host, port):
        return {"ok": True, "started": False, "url": url}

    runtime_dir = _runtime_dir()
    runtime_dir.mkdir(parents=True, exist_ok=True)
    log_path = runtime_dir / "ws.log"
    pid_path = runtime_dir / "ws.pid"
    log_fh = log_path.open("ab")
    popen_kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": log_fh,
        "stderr": log_fh,
        "env": os.environ.copy(),
    }
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        popen_kwargs["creationflags"] = flags
    else:
        popen_kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen([sys.executable, "-m", "chibi_mcp", "--ws-only"], **popen_kwargs)
    finally:
        with suppress(OSError):
            log_fh.close()
    with suppress(OSError):
        pid_path.write_text(str(proc.pid), encoding="utf-8")

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if _ws_accepts(host, port):
            return {
                "ok": True,
                "started": True,
                "pid": proc.pid,
                "url": url,
                "log_path": str(log_path),
            }
        if proc.poll() is not None:
            break
        time.sleep(0.1)

    with suppress(OSError):
        pid_path.unlink(missing_ok=True)
    return {
        "ok": False,
        "started": True,
        "pid": proc.pid,
        "returncode": proc.poll(),
        "url": url,
        "log_path": str(log_path),
        "next_step": "Run `chibi-mcp --ws-only` in another terminal, then `chibi-mcp --open`.",
    }


def _open_window_once(character_id: str | None = None, view_mode: str | None = None) -> dict:
    """Open the floating window from the CLI and return the MCP tool payload."""
    return server_tools.open_pet_window(character_id=character_id, view_mode=view_mode)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="chibi-mcp",
        description="MCP server for chibi, the local coding pet.",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--check", action="store_true", help="Check assets and local runtime support")
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Check local runtime plus Claude, Codex, and VS Code client state",
    )
    parser.add_argument(
        "--mcp-name",
        default="chibi",
        help="MCP server name to inspect with --doctor",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the floating chibi window once, print the result as JSON, and exit",
    )
    parser.add_argument(
        "--character-id",
        default=None,
        help="Optional released character id to use with --open",
    )
    parser.add_argument(
        "--view-mode",
        choices=("normal", "debug", "compact"),
        default=None,
        help="Optional initial window mode to use with --open",
    )
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
    if args.doctor:
        result = _doctor(mcp_name=args.mcp_name)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    if args.open:
        _setup_logging()
        ws_server = _ensure_ws_server_for_open()
        result = _open_window_once(character_id=args.character_id, view_mode=args.view_mode)
        result["ws_server"] = ws_server
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("opened") else 1

    _setup_logging()
    log = logging.getLogger("chibi_mcp")
    host, port = _ws_endpoint()
    if args.ws_only:
        log.info("chibi-mcp starting (ws://%s:%d only)", host, port)
        with suppress(KeyboardInterrupt):
            asyncio.run(_run_ws_only())
    elif args.no_ws:
        log.info("chibi-mcp starting (stdio MCP only)")
        with suppress(KeyboardInterrupt):
            _run_mcp_stdio_sync()
    else:
        log.info("chibi-mcp starting (stdio MCP + ws://%s:%d)", host, port)
        with suppress(KeyboardInterrupt):
            asyncio.run(_run_concurrent(ws_enabled=True))
    log.info("chibi-mcp stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
