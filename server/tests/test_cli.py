"""Tests for the human-facing chibi-mcp CLI helpers."""

from __future__ import annotations

from chibi_mcp import __version__
from chibi_mcp.__main__ import _check


def test_version_matches_release():
    assert __version__ == "1.1.0"


def test_check_finds_packaged_assets():
    result = _check()
    assert result["ok"] is True
    assert result["catalog_count"] >= 8
    assert result["free_assets_missing"] == []
