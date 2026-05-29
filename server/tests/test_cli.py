"""Tests for the human-facing chibi-mcp CLI helpers."""

from __future__ import annotations

from chibi_mcp import __version__
from chibi_mcp.__main__ import _check, _ws_endpoint


def test_version_matches_release():
    assert __version__ == "1.3.3"


def test_check_finds_packaged_assets():
    result = _check()
    assert result["ok"] is True
    assert result["catalog_count"] >= 8
    assert result["free_assets_missing"] == []


def test_invalid_ws_port_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("CHIBI_WS_PORT", "bad")
    assert _ws_endpoint() == ("127.0.0.1", 9876)
