"""Tests for license verification + catalog tier filtering."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from chibi_mcp import license as license_mod
from chibi_mcp.license import (
    LicenseStatus,
    filter_catalog_by_tier,
    verify_license,
)


def _make_license(email: str, expires: datetime, secret: bytes | None = None) -> str:
    secret = secret if secret is not None else license_mod._HMAC_SECRET
    iso = expires.isoformat()
    payload = f"{email}|{iso}".encode()
    sig = hmac.new(secret, payload, hashlib.sha256).digest()
    b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    return f"chibi-pro|{email}|{iso}|{b64}"


def test_no_license_returns_free(monkeypatch):
    monkeypatch.delenv("CHIBI_LICENSE_KEY", raising=False)
    monkeypatch.setattr(license_mod, "_read_license_text", lambda: None)
    s = verify_license()
    assert s.tier == "free"
    assert s.is_pro is False


def test_valid_license_returns_pro(monkeypatch):
    expires = datetime.now(UTC) + timedelta(days=365)
    key = _make_license("a@b.com", expires)
    monkeypatch.setenv("CHIBI_LICENSE_KEY", key)
    s = verify_license()
    assert s.tier == "pro"
    assert s.is_pro is True
    assert s.email == "a@b.com"


def test_expired_license_returns_free(monkeypatch):
    expires = datetime.now(UTC) - timedelta(days=1)
    key = _make_license("a@b.com", expires)
    monkeypatch.setenv("CHIBI_LICENSE_KEY", key)
    s = verify_license()
    assert s.tier == "free"
    assert s.reason == "license expired"


def test_forged_license_rejected(monkeypatch):
    expires = datetime.now(UTC) + timedelta(days=365)
    # Sign with a wrong secret → signature mismatch
    key = _make_license("a@b.com", expires, secret=b"wrong-key")
    monkeypatch.setenv("CHIBI_LICENSE_KEY", key)
    s = verify_license()
    assert s.tier == "free"
    assert s.reason == "invalid signature"


def test_malformed_license(monkeypatch):
    monkeypatch.setenv("CHIBI_LICENSE_KEY", "not-a-license")
    s = verify_license()
    assert s.tier == "free"
    assert s.reason == "malformed license"


def test_filter_catalog_free_strips_pro():
    catalog = {
        "characters": [
            {"id": "a", "tier": "free"},
            {"id": "b", "tier": "pro"},
            {"id": "c", "tier": "free"},
        ]
    }
    out = filter_catalog_by_tier(catalog, LicenseStatus(tier="free"))
    ids = [c["id"] for c in out["characters"]]
    assert ids == ["a", "c"]


def test_filter_catalog_pro_returns_all():
    catalog = {
        "characters": [
            {"id": "a", "tier": "free"},
            {"id": "b", "tier": "pro"},
        ]
    }
    out = filter_catalog_by_tier(catalog, LicenseStatus(tier="pro"))
    assert len(out["characters"]) == 2
