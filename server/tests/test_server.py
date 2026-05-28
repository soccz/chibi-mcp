"""Tests for server.py — input sanitization for MCP tool args."""

from __future__ import annotations

from pathlib import Path

from chibi_mcp.server import (
    MAX_SAY_LEN,
    _resolve_asset_dir,
    _sanitize_say,
    _window_runtime_issue,
)


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
