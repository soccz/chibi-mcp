"""WebSocket server — pushes chibi state to the desktop app.

Protocol (JSON messages, server → client):
    {"type": "state", "payload": {...full state snapshot...}}
    {"type": "say", "text": "..."}
    {"type": "slice"}                  # internal event for N-call milestones

Protocol (JSON messages, hook/client → server):
    {"type": "say", "text": "..."}       # speech only; marks recent activity
    {"type": "tool_call", "text": "..."} # counts one Claude/Codex tool call

The desktop app connects to ws://localhost:9876 and listens for events.

Uses the websockets >= 14 asyncio API (`websockets.asyncio.server`).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from .runtime import DEFAULT_WS_HOST, DEFAULT_WS_PORT
from .state import get_state

log = logging.getLogger(__name__)

# DEFAULT_WS_HOST / DEFAULT_WS_PORT are re-exported from .runtime so existing
# `from .ws_server import DEFAULT_WS_HOST, DEFAULT_WS_PORT` callers keep working.
STATE_PUSH_INTERVAL_SECONDS = 2.0  # snapshot push cadence


class ChibiBroadcaster:
    """Holds connected desktop clients and broadcasts events."""

    def __init__(self) -> None:
        self._clients: set[ServerConnection] = set()
        self._lock = asyncio.Lock()

    async def register(self, ws: ServerConnection) -> None:
        async with self._lock:
            self._clients.add(ws)
        log.info("ws client connected (%d total)", len(self._clients))

    async def unregister(self, ws: ServerConnection) -> None:
        async with self._lock:
            self._clients.discard(ws)
        log.info("ws client disconnected (%d total)", len(self._clients))

    async def broadcast(self, message: dict) -> None:
        payload = json.dumps(message)
        async with self._lock:
            clients = list(self._clients)
        if not clients:
            return
        results = await asyncio.gather(
            *(self._send_safe(c, payload) for c in clients), return_exceptions=True
        )
        for r in results:
            if isinstance(r, Exception):
                log.debug("broadcast send failed: %s", r)

    @staticmethod
    async def _send_safe(ws: ServerConnection, payload: str) -> None:
        with contextlib.suppress(ConnectionClosed):
            await ws.send(payload)


_BROADCASTER: ChibiBroadcaster | None = None
_ACTION_HANDLER: Callable[[dict], dict] | None = None


def get_broadcaster() -> ChibiBroadcaster:
    global _BROADCASTER
    if _BROADCASTER is None:
        _BROADCASTER = ChibiBroadcaster()
    return _BROADCASTER


def reset_broadcaster_for_tests() -> None:
    """Test helper — DO NOT call from runtime code."""
    global _BROADCASTER
    _BROADCASTER = None


def set_action_handler(handler: Callable[[dict], dict] | None) -> None:
    """Register the server-side handler for desktop-window actions."""
    global _ACTION_HANDLER
    _ACTION_HANDLER = handler


_INBOUND_SAY_MAX_LEN = 200


def _sanitize_inbound_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.replace("\n", " ").replace("\r", " ").strip()[:_INBOUND_SAY_MAX_LEN]


def _action_failure_text(result: dict) -> str:
    for key in ("message_ko", "message", "reason"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return _sanitize_inbound_text(value) or "실패"
    return "실패"


async def _handle_client(ws: ServerConnection) -> None:
    broadcaster = get_broadcaster()
    await broadcaster.register(ws)

    try:
        # Send current state immediately on connect
        state = get_state()
        await ws.send(json.dumps({"type": "state", "payload": state.snapshot()}))

        async for raw in ws:
            # Inbound: a non-window client (chibi-say CLI, claude-code hooks)
            # publishes a say event that we forward to all windows.
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(msg, dict):
                continue
            if msg.get("type") == "say" and isinstance(msg.get("text"), str):
                text = _sanitize_inbound_text(msg.get("text"))
                if text:
                    state = get_state()
                    state.note_activity("say")
                    await broadcaster.broadcast({"type": "state", "payload": state.snapshot()})
                    await broadcaster.broadcast({"type": "say", "text": text})
            elif msg.get("type") == "tool_call":
                text = _sanitize_inbound_text(msg.get("text"))
                state = get_state()
                result = state.record_call()
                if result.get("sliced"):
                    await broadcaster.broadcast({"type": "slice"})
                await broadcaster.broadcast({"type": "state", "payload": state.snapshot()})
                if text:
                    await broadcaster.broadcast({"type": "say", "text": text})
            elif msg.get("type") == "action" and _ACTION_HANDLER is not None:
                state = get_state()
                state.note_activity("window_action")
                try:
                    result = _ACTION_HANDLER(msg)
                except Exception:
                    log.exception("window action failed")
                    await broadcaster.broadcast({"type": "say", "text": "액션 실패"})
                    continue
                if isinstance(result, dict) and result.get("ok") is False:
                    await broadcaster.broadcast({"type": "state", "payload": state.snapshot()})
                    await broadcaster.broadcast({"type": "say", "text": _action_failure_text(result)})
                else:
                    await broadcaster.broadcast({"type": "state", "payload": get_state().snapshot()})
    except ConnectionClosed:
        pass
    finally:
        await broadcaster.unregister(ws)


async def _state_push_loop() -> None:
    """Periodically push state to all connected clients."""
    broadcaster = get_broadcaster()
    state = get_state()
    while True:
        try:
            # Skip building a psutil snapshot when nobody is listening.
            if broadcaster._clients:
                await broadcaster.broadcast({"type": "state", "payload": state.snapshot()})
        except Exception:
            log.exception("state push failed")
        await asyncio.sleep(STATE_PUSH_INTERVAL_SECONDS)


async def run_ws_server(host: str = DEFAULT_WS_HOST, port: int = DEFAULT_WS_PORT) -> None:
    """Run WebSocket server + periodic state push concurrently."""
    if host not in ("127.0.0.1", "localhost", "::1"):
        log.warning(
            "chibi WS bound to non-loopback host %r — window actions are "
            "unauthenticated, so anyone who can reach this port could drive the "
            "pet. Use the default 127.0.0.1 unless you intend remote access.",
            host,
        )
    push_task = asyncio.create_task(_state_push_loop())
    async with serve(_handle_client, host, port):
        log.info("ws server listening on ws://%s:%d", host, port)
        try:
            await asyncio.Future()  # run forever
        finally:
            push_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await push_task
