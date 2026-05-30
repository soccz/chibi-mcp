"""Tests for server.py — input sanitization for MCP tool args."""

from __future__ import annotations

from pathlib import Path

from chibi_mcp import server as server_mod
from chibi_mcp import state as state_mod
from chibi_mcp.server import (
    MAX_SAY_LEN,
    _handle_window_action,
    _resolve_asset_dir,
    _sanitize_say,
    _window_runtime_issue,
    _window_startup_failure,
    clear_active_options,
    get_options,
    set_active_options,
)
from chibi_mcp.state import get_state, reset_state_for_tests


def test_sanitize_short_text_passthrough():
    assert _sanitize_say("hi") == "hi"
    assert _sanitize_say("오늘도 같이 코딩!") == "오늘도 같이 코딩!"


def test_sanitize_truncates_long_text():
    long = "a" * 1000
    result = _sanitize_say(long)
    assert len(result) == MAX_SAY_LEN
    assert result.endswith("…")


def test_sanitize_strips_control_chars():
    # \x00 NULL, \x07 BEL — should be stripped; tab and newline are collapsed to space
    result = _sanitize_say("hi\x00there\x07world\nnewline\ttab")
    assert "\x00" not in result
    assert "\x07" not in result
    assert "\n" not in result
    # tab is preserved in SAY_CONTROL_CHARS exclusion but newline collapses to space
    assert "hi" in result and "world" in result


def test_sanitize_collapses_newlines_for_single_line_bubble():
    assert "\n" not in _sanitize_say("line1\nline2")
    assert "\r" not in _sanitize_say("line1\r\nline2")


def test_sanitize_handles_non_string_input():
    assert _sanitize_say(42) == "42"  # type: ignore[arg-type]
    assert _sanitize_say(None) == "None"  # type: ignore[arg-type]


def test_sanitize_strips_surrounding_whitespace():
    assert _sanitize_say("   hello   ") == "hello"


def test_asset_dir_resolves_for_direct_mcp_installs():
    asset_dir = _resolve_asset_dir()
    assert asset_dir is not None
    assert (Path(asset_dir) / "meta.json").exists()


def test_options_catalog_exposes_free_layers():
    result = get_options()
    ids = {option["id"] for option in result["options"]}
    assert result["total"] >= 12
    assert {
        "jocheong_drip",
        "honey_glaze",
        "sugar_beads",
        "rainbow_sprinkles",
        "condensed_milk",
        "kinako_dust",
        "black_sesame",
        "red_bean_bits",
        "flower_petals",
        "resin_stars",
        "matcha_powder",
        "spicy_sauce",
    } <= ids
    assert all(option["image_exists"] for option in result["options"])


def test_set_active_options_persists_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(state_mod, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state_mod, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(server_mod, "_WINDOW_PID_FILE", tmp_path / "window.pid")
    reset_state_for_tests()
    try:
        result = set_active_options(["jocheong_drip", "sugar_beads"])
        assert result["ok"] is True
        assert get_state().active_option_ids == ["jocheong_drip", "sugar_beads"]

        result = clear_active_options()
        assert result["ok"] is True
        assert get_state().active_option_ids == []
    finally:
        reset_state_for_tests()


def test_window_action_routes_option_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(state_mod, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state_mod, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(server_mod, "_WINDOW_PID_FILE", tmp_path / "window.pid")
    reset_state_for_tests()
    try:
        result = _handle_window_action(
            {
                "type": "action",
                "action": "set_active_options",
                "option_ids": ["honey_glaze"],
            }
        )
        assert result["ok"] is True
        assert get_state().active_option_ids == ["honey_glaze"]

        result = _handle_window_action({"type": "action", "action": "clear_active_options"})
        assert result["ok"] is True
        assert get_state().active_option_ids == []
    finally:
        reset_state_for_tests()


def test_window_action_rejects_unknown_action():
    result = _handle_window_action({"type": "action", "action": "not_real"})
    assert result["ok"] is False
    assert "unknown window action" in result["reason"]


def test_window_runtime_issue_reports_missing_tkinter(monkeypatch):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "tkinter":
            raise ModuleNotFoundError("No module named '_tkinter'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    issue = _window_runtime_issue()
    assert issue is not None
    assert issue["opened"] is False
    assert issue["reason"] == "python tkinter unavailable"


class _FakeProc:
    def __init__(self, code=None):
        self.pid = 12345
        self.code = code
        self.terminated = False

    def poll(self):
        return self.code

    def terminate(self):
        self.terminated = True


def test_window_startup_wait_accepts_ready_file(tmp_path):
    ready = tmp_path / "ready.json"
    ready.write_text('{"ready": true}', encoding="utf-8")
    log = tmp_path / "window.log"

    assert _window_startup_failure(_FakeProc(), ready, log, timeout_seconds=0.01) is None


def test_window_startup_wait_reports_early_exit(tmp_path):
    ready = tmp_path / "ready.json"
    log = tmp_path / "window.log"
    log.write_text("boom", encoding="utf-8")

    result = _window_startup_failure(_FakeProc(code=11), ready, log, timeout_seconds=0.01)

    assert result is not None
    assert result["opened"] is False
    assert "died before ready" in result["reason"]
    assert result["log_tail"] == "boom"


def test_window_startup_wait_times_out_and_terminates(tmp_path):
    proc = _FakeProc()
    ready = tmp_path / "ready.json"
    log = tmp_path / "window.log"

    result = _window_startup_failure(
        proc, ready, log, timeout_seconds=0.01, poll_interval=0.001
    )

    assert result is not None
    assert result["opened"] is False
    assert "did not report ready" in result["reason"]
    assert proc.terminated is True
