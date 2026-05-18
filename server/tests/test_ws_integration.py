"""WebSocket E2E integration tests.

Spin up the real ws_server on an ephemeral port and assert that:
  - connecting clients receive an initial `state` message,
  - the periodic state push fires,
  - manual `pet_say` and `slice` broadcasts reach the client.

These tests run in CI alongside the unit tests.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import socket

import pytest
from websockets.asyncio.client import connect

from chibi_mcp.state import reset_state_for_tests
from chibi_mcp.ws_server import (
    get_broadcaster,
    reset_broadcaster_for_tests,
    run_ws_server,
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def ws_url():
    """Start a fresh ws_server on a free port for each test."""
    reset_state_for_tests()
    reset_broadcaster_for_tests()
    port = _free_port()
    server_task = asyncio.create_task(run_ws_server(host="127.0.0.1", port=port))
    # Allow the server a tick to start listening
    for _ in range(20):
        await asyncio.sleep(0.05)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                s.connect(("127.0.0.1", port))
            break
        except OSError:
            continue
    yield f"ws://127.0.0.1:{port}"
    server_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await server_task


async def test_initial_state_pushed_on_connect(ws_url):
    async with connect(ws_url) as ws:
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)
        assert msg["type"] == "state"
        p = msg["payload"]
        assert "mood" in p
        assert "system" in p
        assert "counters" in p
        assert "timing" in p


async def test_pet_say_broadcasts_to_client(ws_url):
    async with connect(ws_url) as ws:
        # First message: state. Skip it.
        await asyncio.wait_for(ws.recv(), timeout=2.0)

        # Trigger a say broadcast
        await get_broadcaster().broadcast({"type": "say", "text": "hello!"})
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)
        assert msg["type"] == "say"
        assert msg["text"] == "hello!"


async def test_slice_event_broadcasts_to_client(ws_url):
    async with connect(ws_url) as ws:
        await asyncio.wait_for(ws.recv(), timeout=2.0)

        await get_broadcaster().broadcast({"type": "slice"})
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)
        assert msg["type"] == "slice"


async def test_multiple_clients_all_receive_broadcast(ws_url):
    async with connect(ws_url) as ws1, connect(ws_url) as ws2:
        # Drain initial state on both
        await asyncio.wait_for(ws1.recv(), timeout=2.0)
        await asyncio.wait_for(ws2.recv(), timeout=2.0)

        await get_broadcaster().broadcast({"type": "say", "text": "broadcast"})

        m1 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
        m2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
        assert m1["type"] == "say" and m2["type"] == "say"
        assert m1["text"] == "broadcast" and m2["text"] == "broadcast"


async def test_state_pushes_periodically(ws_url):
    """Verify the 2s push loop fires at least once during the test window."""
    async with connect(ws_url) as ws:
        # initial connect message
        await asyncio.wait_for(ws.recv(), timeout=2.0)
        # next message should be the periodic state (within ~3s)
        raw = await asyncio.wait_for(ws.recv(), timeout=3.5)
        msg = json.loads(raw)
        assert msg["type"] == "state"


async def test_disconnect_unregisters_client(ws_url):
    broadcaster = get_broadcaster()
    async with connect(ws_url) as ws:
        await asyncio.wait_for(ws.recv(), timeout=2.0)
        # one client should be registered after connect+initial recv
        # give the server a tick to register
        await asyncio.sleep(0.05)
        assert len(broadcaster._clients) == 1
    # After context exit, ws is closed. Give server a tick to unregister.
    await asyncio.sleep(0.2)
    assert len(broadcaster._clients) == 0
