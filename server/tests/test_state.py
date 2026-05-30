"""Tests for state.py — mood derivation and slice counter."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from chibi_mcp.state import (
    DEFAULT_SLICE_INTERVAL,
    HAPPY_WINDOW_SECONDS,
    LONELY_IDLE_SECONDS,
    ChibiState,
    Mood,
    reset_state_for_tests,
)
from chibi_mcp.system_info import SystemSnapshot


@pytest.fixture(autouse=True)
def _reset():
    reset_state_for_tests()
    yield
    reset_state_for_tests()


def _snap(cpu=10.0, ram=40.0, bat=None, plugged=None) -> SystemSnapshot:
    return SystemSnapshot(cpu_percent=cpu, ram_percent=ram, battery_percent=bat, battery_plugged=plugged)


# ---- slice counter ----


def test_slice_fires_every_default_interval():
    state = ChibiState()
    fired = []
    for _ in range(DEFAULT_SLICE_INTERVAL):
        r = state.record_call()
        fired.append(r["sliced"])
    # First N-1 calls don't slice; N-th does
    assert fired == [False] * (DEFAULT_SLICE_INTERVAL - 1) + [True]
    assert state.slices_today == 1
    assert state.calls_since_slice == 0


def test_slice_interval_is_configurable():
    state = ChibiState(slice_interval=3)
    sliced = [state.record_call()["sliced"] for _ in range(6)]
    assert sliced == [False, False, True, False, False, True]
    assert state.slices_today == 2


def test_call_count_keeps_growing_across_slices():
    state = ChibiState(slice_interval=2)
    for _ in range(5):
        state.record_call()
    assert state.call_count == 5


# ---- force_slice (manual slice_now path) ----


def test_force_slice_fires_immediately():
    state = ChibiState(slice_interval=100)
    r = state.record_call(force_slice=True)
    assert r["sliced"] is True
    assert state.slices_today == 1
    assert state.calls_since_slice == 0


def test_force_slice_does_not_affect_natural_counter():
    state = ChibiState(slice_interval=3)
    state.record_call()
    state.record_call()              # calls_since_slice = 2
    state.record_call(force_slice=True)  # forced — resets, +1 slice
    assert state.slices_today == 1
    # next 3 normal calls should slice again
    sliced = [state.record_call()["sliced"] for _ in range(3)]
    assert sliced == [False, False, True]
    assert state.slices_today == 2


# ---- mood derivation ----


def test_default_mood_is_calm():
    state = ChibiState()
    assert state.compute_mood(_snap()) == Mood.CALM


def test_high_cpu_triggers_panting():
    state = ChibiState()
    state.last_cpu = 75.0  # so jump isn't enough for SURPRISED
    assert state.compute_mood(_snap(cpu=85.0)) == Mood.PANTING


def test_sudden_cpu_spike_triggers_surprised():
    state = ChibiState()
    state.last_cpu = 5.0
    assert state.compute_mood(_snap(cpu=60.0)) == Mood.SURPRISED


def test_low_battery_unplugged_triggers_drowsy():
    state = ChibiState()
    assert state.compute_mood(_snap(bat=15.0, plugged=False)) == Mood.DROWSY


def test_low_battery_but_plugged_is_not_drowsy():
    state = ChibiState()
    assert state.compute_mood(_snap(bat=15.0, plugged=True)) != Mood.DROWSY


def test_recent_call_triggers_happy():
    state = ChibiState()
    state.last_call_at = time.time() - 5
    assert state.compute_mood(_snap()) == Mood.HAPPY


def test_note_activity_triggers_happy_without_counting_ticket_calls():
    state = ChibiState()
    state.note_activity("say")
    assert state.compute_mood(_snap()) == Mood.HAPPY
    assert state.call_count == 0
    assert state.calls_since_slice == 0
    with patch("chibi_mcp.state.read_snapshot", return_value=_snap()):
        snap = state.snapshot()
    assert snap["timing"]["last_activity_source"] == "say"


def test_long_idle_after_calls_triggers_lonely():
    state = ChibiState()
    state.last_call_at = time.time() - (LONELY_IDLE_SECONDS + 60)
    assert state.compute_mood(_snap()) == Mood.LONELY


def test_long_session_without_any_call_triggers_lonely():
    state = ChibiState()
    state.started_at = time.time() - (LONELY_IDLE_SECONDS + 60)
    state.last_call_at = None
    assert state.compute_mood(_snap()) == Mood.LONELY


def test_happy_window_boundary():
    state = ChibiState()
    state.last_call_at = time.time() - (HAPPY_WINDOW_SECONDS - 1)
    assert state.compute_mood(_snap()) == Mood.HAPPY


# ---- snapshot ----


def test_snapshot_contains_expected_keys():
    state = ChibiState()
    state.record_call()
    with patch("chibi_mcp.state.read_snapshot", return_value=_snap()):
        snap = state.snapshot()
    assert set(snap.keys()) >= {"mood", "system", "counters", "timing"}
    assert snap["counters"]["calls_total"] == 1
    assert snap["counters"]["slice_interval"] == DEFAULT_SLICE_INTERVAL


def test_slice_interval_persists_with_user_state(tmp_path, monkeypatch):
    from chibi_mcp import state as state_mod

    monkeypatch.setattr(state_mod, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state_mod, "STATE_FILE", tmp_path / "state.json")
    state = ChibiState()
    result = state.set_slice_interval(25)
    assert result == {"previous": DEFAULT_SLICE_INTERVAL, "current": 25}

    restored = ChibiState()
    restored.load()
    assert restored.slice_interval == 25


def test_runtime_dir_env_is_respected_after_import(tmp_path, monkeypatch):
    from chibi_mcp import state as state_mod

    monkeypatch.setattr(state_mod, "STATE_DIR", state_mod._DEFAULT_STATE_DIR)
    monkeypatch.setattr(state_mod, "STATE_FILE", state_mod._DEFAULT_STATE_FILE)
    monkeypatch.setenv("CHIBI_RUNTIME_DIR", str(tmp_path))
    state = ChibiState()
    state.grant_tickets(2)
    assert (tmp_path / "state.json").exists()


def test_corrupt_persisted_state_is_sanitized(tmp_path, monkeypatch):
    from chibi_mcp import state as state_mod

    monkeypatch.setattr(state_mod, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state_mod, "STATE_FILE", tmp_path / "state.json")
    (tmp_path / "state.json").write_text(
        """{
          "slice_interval": 0,
          "active_character_id": "mochi",
          "active_option_ids": ["honey_glaze", "../bad", "honey_glaze"],
          "tickets": -5,
          "total_pulls": "bad",
          "inventory": {
            "white_tteok": {"count": -1, "nickname": " hi\\nthere "},
            "../bad": {"count": 3, "nickname": "bad"}
          }
        }""",
        encoding="utf-8",
    )
    state = ChibiState()
    state.load()
    assert state.slice_interval == DEFAULT_SLICE_INTERVAL
    assert state.active_character_id is None
    assert state.active_option_ids == ["honey_glaze"]
    assert state.tickets == 0
    assert state.total_pulls == 0
    assert state.inventory == {"white_tteok": {"count": 1, "nickname": "hi there"}}
