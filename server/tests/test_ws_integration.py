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

from chibi_mcp import state as state_mod
from chibi_mcp.state import reset_state_for_tests
from chibi_mcp.system_info import SystemSnapshot
from chibi_mcp.ws_server import (
    get_broadcaster,
    reset_broadcaster_for_tests,
    run_ws_server,
    set_action_handler,
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
    set_action_handler(None)
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


async def test_inbound_say_marks_recent_activity_and_pushes_state(ws_url, monkeypatch):
    monkeypatch.setattr(
        state_mod,
        "read_snapshot",
        lambda interval=0.0: SystemSnapshot(
            cpu_percent=10.0,
            ram_percent=40.0,
            battery_percent=80.0,
            battery_plugged=False,
        ),
    )
    async with connect(ws_url) as listener, connect(ws_url) as actor:
        await asyncio.wait_for(listener.recv(), timeout=2.0)
        await asyncio.wait_for(actor.recv(), timeout=2.0)

        await actor.send(json.dumps({"type": "say", "text": "hook fired"}))

        state_msg = json.loads(await asyncio.wait_for(listener.recv(), timeout=2.0))
        say_msg = json.loads(await asyncio.wait_for(listener.recv(), timeout=2.0))
        assert state_msg["type"] == "state"
        assert state_msg["payload"]["mood"] == "happy"
        assert state_msg["payload"]["timing"]["last_activity_source"] == "say"
        assert say_msg["type"] == "say"
        assert say_msg["text"] == "hook fired"


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


async def test_window_action_pushes_fresh_state(ws_url):
    def handler(_message):
        from chibi_mcp.state import get_state

        get_state().grant_tickets(1)
        return {"ok": True}

    set_action_handler(handler)

    async with connect(ws_url) as listener, connect(ws_url) as actor:
        await asyncio.wait_for(listener.recv(), timeout=2.0)
        await asyncio.wait_for(actor.recv(), timeout=2.0)
        await actor.send(json.dumps({"type": "action", "action": "test"}))

        raw = await asyncio.wait_for(listener.recv(), timeout=1.0)
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
