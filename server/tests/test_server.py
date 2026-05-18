"""Tests for server.py — input sanitization for MCP tool args."""

from __future__ import annotations

from chibi_mcp.server import _sanitize_say, MAX_SAY_LEN


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
