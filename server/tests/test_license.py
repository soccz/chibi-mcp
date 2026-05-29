"""Tests for open-source catalog access policy."""

from __future__ import annotations

from chibi_mcp.license import (
    LicenseStatus,
    filter_catalog_by_tier,
    verify_license,
)


def test_no_license_returns_free(monkeypatch):
    monkeypatch.delenv("CHIBI_LICENSE_KEY", raising=False)
    s = verify_license()
    assert s.tier == "free"
    assert s.is_pro is False
    assert s.email is None


def test_license_env_is_ignored_until_commercial_entitlements_exist(monkeypatch):
    monkeypatch.setenv("CHIBI_LICENSE_KEY", "chibi-pro|a@b.com|2099-01-01|fake")
    s = verify_license()
    assert s.tier == "free"
    assert s.is_pro is False


def test_filter_catalog_returns_only_released_free_characters():
    catalog = {
        "characters": [
            {"id": "a", "tier": "free"},
            {"id": "b", "tier": "upcoming"},
            {"id": "c", "tier": "free"},
        ],
        "options": [
            {"id": "jocheong_drip", "tier": "free"},
            {"id": "future_glaze", "tier": "upcoming"},
        ],
    }
    out = filter_catalog_by_tier(catalog, LicenseStatus(tier="free"))
    ids = [c["id"] for c in out["characters"]]
    assert ids == ["a", "c"]
    assert [o["id"] for o in out["options"]] == ["jocheong_drip"]


def test_filter_catalog_ignores_pro_status_until_entitlements_exist():
    catalog = {
        "characters": [
            {"id": "a", "tier": "free"},
            {"id": "b", "tier": "upcoming"},
        ]
    }
    out = filter_catalog_by_tier(catalog, LicenseStatus(tier="pro"))
    assert [c["id"] for c in out["characters"]] == ["a"]
