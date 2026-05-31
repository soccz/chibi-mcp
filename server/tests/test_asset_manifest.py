"""Official asset integrity manifest — provenance baseline + tamper detection."""

from __future__ import annotations

import hashlib
from pathlib import Path

from chibi_mcp.cli import verify_asset_manifest

ROOT = Path(__file__).resolve().parents[2]


def test_official_asset_manifest_matches_committed_art():
    asset_dir = ROOT / "server" / "chibi_mcp" / "assets"
    result = verify_asset_manifest(str(asset_dir))
    assert result["manifest_present"] is True
    assert result["ok"] is True, result
    assert result["checked"] >= 20  # 8 characters + 12 option layers


def test_all_three_asset_mirrors_have_manifests():
    for rel in ("assets", "server/chibi_mcp/assets", "vscode-ext/resources"):
        assert (ROOT / rel / "ASSET_MANIFEST.sha256").exists(), rel


def test_tampered_asset_is_detected(tmp_path):
    (tmp_path / "a.png").write_bytes(b"original")
    good = hashlib.sha256(b"original").hexdigest()
    (tmp_path / "ASSET_MANIFEST.sha256").write_text(f"{good}  a.png\n", encoding="utf-8")
    assert verify_asset_manifest(str(tmp_path))["ok"] is True

    (tmp_path / "a.png").write_bytes(b"tampered")
    result = verify_asset_manifest(str(tmp_path))
    assert result["ok"] is False
    assert "a.png" in result["mismatches"]


def test_missing_manifest_is_soft_skip(tmp_path):
    result = verify_asset_manifest(str(tmp_path))
    assert result["manifest_present"] is False
    assert result["ok"] is True  # older installs without a manifest don't fail
