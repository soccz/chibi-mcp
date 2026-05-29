"""Tests for gacha mechanics, inventory persistence, ticket grants."""

from __future__ import annotations

import json

import pytest

from chibi_mcp import state as state_mod
from chibi_mcp.state import TteokiState, reset_state_for_tests


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    monkeypatch.setattr(state_mod, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state_mod, "STATE_FILE", tmp_path / "state.json")
    reset_state_for_tests()
    yield
    reset_state_for_tests()


CATALOG = [
    {"id": "white_tteok", "name_ko": "흰떡", "rarity": 2, "category": "tteok"},
    {"id": "garaetteok_short", "name_ko": "가래떡(짧)", "rarity": 2, "category": "tteok"},
    {"id": "baekseolgi", "name_ko": "백설기", "rarity": 2, "category": "tteok"},
    {"id": "mochi", "name_ko": "모찌", "rarity": 3, "category": "tteok"},
    {"id": "cheddar", "name_ko": "체다", "rarity": 4, "category": "cheese"},
    {"id": "rainbow_tteok", "name_ko": "무지개떡", "rarity": 5, "category": "tteok"},
]


def test_first_pull_is_free_today():
    s = TteokiState()
    result = s.pull_gacha(CATALOG)
    assert result["drawn"] is not None
    assert result["was_free"] is True
    assert result["tickets"] == 0


def test_second_pull_same_day_costs_ticket():
    s = TteokiState()
    s.pull_gacha(CATALOG)
    # No tickets after free pull
    result = s.pull_gacha(CATALOG)
    assert result["drawn"] is None
    assert "no free pull today" in result["reason"]


def test_pull_with_ticket_succeeds():
    s = TteokiState()
    s.pull_gacha(CATALOG)  # consume free pull
    s.tickets = 1
    result = s.pull_gacha(CATALOG)
    assert result["drawn"] is not None
    assert result["was_free"] is False
    assert s.tickets == 0


def test_first_pulled_becomes_active():
    s = TteokiState()
    result = s.pull_gacha(CATALOG)
    assert s.active_character_id == result["drawn"]["id"]


def test_inventory_count_increments():
    s = TteokiState()
    s.tickets = 5
    s.pull_gacha(CATALOG)  # free
    for _ in range(4):
        s.pull_gacha(CATALOG)
    total = sum(c["count"] for c in s.inventory.values())
    assert total == 5


def test_persistence_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(state_mod, "STATE_FILE", tmp_path / "rt.json")
    s = TteokiState()
    s.tickets = 7
    s.active_character_id = "white_tteok"
    s.inventory = {"white_tteok": {"count": 2, "nickname": "흰떡이"}}
    s.save()

    s2 = TteokiState()
    s2.load()
    assert s2.tickets == 7
    assert s2.active_character_id == "white_tteok"
    assert s2.inventory["white_tteok"]["nickname"] == "흰떡이"


def test_ticket_grant_every_100_calls():
    s = TteokiState(slice_interval=1000)  # avoid slice noise
    for _ in range(99):
        s.record_call()
    assert s.tickets == 0
    r = s.record_call()
    assert r["ticket_grants"] == 1
    assert s.tickets == 1


def test_ticket_grant_every_10_slices():
    s = TteokiState(slice_interval=1)
    grants = 0
    for _ in range(20):
        r = s.record_call()
        grants += r["ticket_grants"]
    # 20 calls x interval=1 = 20 slices.
    # At call_count=100? No — only 20 calls, so 0 call-based grants.
    # But 10-slice milestone: hits at 10 slices and 20 slices = 2 grants
    assert grants == 2
    assert s.tickets == 2


def test_rename_persists():
    s = TteokiState()
    s.tickets = 1
    s.pull_gacha(CATALOG)
    cid = s.active_character_id
    r = s.rename(cid, "내떡이")
    assert r["ok"] is True
    assert s.inventory[cid]["nickname"] == "내떡이"


def test_set_active_requires_ownership():
    s = TteokiState()
    r = s.set_active("white_tteok")  # not owned
    assert r["ok"] is False


def test_set_active_after_owning():
    s = TteokiState()
    s.pull_gacha(CATALOG)  # owns something
    s.tickets = 5
    # Pull until we get a different character
    for _ in range(5):
        s.pull_gacha(CATALOG)
    owned_ids = list(s.inventory.keys())
    if len(owned_ids) >= 2:
        new_active = owned_ids[1]
        r = s.set_active(new_active)
        assert r["ok"] is True
        assert s.active_character_id == new_active


def test_state_file_is_atomic_json():
    s = TteokiState()
    s.pull_gacha(CATALOG)
    data = json.loads(state_mod.STATE_FILE.read_text())
    assert data["schema_version"] == state_mod.STATE_SCHEMA_VERSION
    assert "inventory" in data
    assert "tickets" in data


def test_save_does_not_hold_lock_during_io(monkeypatch):
    """Regression: state.save() used to do file I/O while holding self._lock.

    After v1.3.1 the lock is released before _save_data runs. We verify by
    having _save_data try to call a method that requires the lock — if save
    were still holding it, this would deadlock.
    """
    s = TteokiState()
    s.tickets = 1
    s.pull_gacha(CATALOG)  # consume free pull
    captured: list[bool] = []

    original = state_mod.TteokiState._save_data

    def spy(data):
        # If lock is held by caller, this acquire would block forever.
        # We try non-blocking acquire; should always succeed.
        got = s._lock.acquire(blocking=False)
        captured.append(got)
        if got:
            s._lock.release()
        original(data)

    monkeypatch.setattr(state_mod.TteokiState, "_save_data", staticmethod(spy))

    # Trigger a save by pulling with a ticket (consumes ticket, calls save)
    s.tickets = 1
    r = s.pull_gacha(CATALOG)
    assert r["drawn"] is not None
    assert captured, "_save_data was not called"
    assert all(captured), "lock was still held during _save_data"


def test_invalid_character_id_rejected_by_set_active():
    s = TteokiState()
    s.pull_gacha(CATALOG)
    r = s.set_active("../etc/passwd")
    assert r["ok"] is False
    assert "don't own" in r["reason"]
