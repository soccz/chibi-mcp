"""WebSocket server — pushes tteoki state to the desktop app.

Protocol (JSON messages, server → client):
    {"type": "state", "payload": {...full state snapshot...}}
    {"type": "say", "text": "..."}
    {"type": "slice"}                  # fires when N-call milestone hits

The desktop app connects to ws://localhost:9876 and listens for events.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

import websockets
from websockets.legacy.server import WebSocketServerProtocol

from .state import get_state

log = logging.getLogger(__name__)

DEFAULT_WS_HOST = "127.0.0.1"
DEFAULT_WS_PORT = 9876
STATE_PUSH_INTERVAL_SECONDS = 2.0  # snapshot push cadence


class TteokiBroadcaster:
    """Holds connected desktop clients and broadcasts events."""

    def __init__(self) -> None:
        self._clients: Set[WebSocketServerProtocol] = set()
        self._lock = asyncio.Lock()

    async def register(self, ws: WebSocketServerProtocol) -> None:
        async with self._lock:
            self._clients.add(ws)
        log.info("ws client connected (%d total)", len(self._clients))

    async def unregister(self, ws: WebSocketServerProtocol) -> None:
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
    async def _send_safe(ws: WebSocketServerProtocol, payload: str) -> None:
        try:
            await ws.send(payload)
        except websockets.ConnectionClosed:
            pass


_BROADCASTER: TteokiBroadcaster | None = None


def get_broadcaster() -> TteokiBroadcaster:
    global _BROADCASTER
    if _BROADCASTER is None:
        _BROADCASTER = TteokiBroadcaster()
    return _BROADCASTER


async def _handle_client(ws: WebSocketServerProtocol) -> None:
    broadcaster = get_broadcaster()
    await broadcaster.register(ws)

    # Send current state immediately on connect
    state = get_state()
    await ws.send(json.dumps({"type": "state", "payload": state.snapshot()}))

    try:
        async for _raw in ws:
            # Desktop app may send pings or settings updates later; ignore for v0.1
            pass
    except websockets.ConnectionClosed:
        pass
    finally:
        await broadcaster.unregister(ws)


async def _state_push_loop() -> None:
    """Periodically push state to all connected clients."""
    broadcaster = get_broadcaster()
    state = get_state()
    while True:
        try:
            await broadcaster.broadcast({"type": "state", "payload": state.snapshot()})
        except Exception:
            log.exception("state push failed")
        await asyncio.sleep(STATE_PUSH_INTERVAL_SECONDS)


async def run_ws_server(host: str = DEFAULT_WS_HOST, port: int = DEFAULT_WS_PORT) -> None:
    """Run WebSocket server + periodic state push concurrently."""
    push_task = asyncio.create_task(_state_push_loop())
    async with websockets.serve(_handle_client, host, port):
        log.info("ws server listening on ws://%s:%d", host, port)
        try:
            await asyncio.Future()  # run forever
        finally:
            push_task.cancel()
