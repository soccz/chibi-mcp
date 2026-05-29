"""Tests for the human-facing chibi-mcp CLI helpers."""

from __future__ import annotations

import json

from PIL import Image

from chibi_mcp import __version__
from chibi_mcp.__main__ import _check, _ws_endpoint
from chibi_mcp.commercial import (
    build_trust_audit,
    validate_pack,
    write_pack_preview,
    write_share_card,
)


def test_version_matches_release():
    assert __version__ == "1.4.0"


def test_check_finds_packaged_assets():
    result = _check()
    assert result["ok"] is True
    assert result["catalog_count"] >= 8
    assert result["free_assets_missing"] == []


def test_invalid_ws_port_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("CHIBI_WS_PORT", "bad")
    assert _ws_endpoint() == ("127.0.0.1", 9876)


def test_trust_audit_reports_local_first_defaults():
    report = build_trust_audit()
    assert report["ok"] is True
    assert report["trust"]["telemetry"] == "none"
    assert report["trust"]["localhost_only_by_default"] is True
    assert report["trust"]["paid_core_gate"] == "none"


def test_pack_validate_accepts_minimal_creator_pack(tmp_path):
    Image.new("RGBA", (256, 256), (255, 240, 210, 255)).save(tmp_path / "custom_tteok.png")
    (tmp_path / "meta.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "custom_tteok",
                        "name_ko": "Custom Tteok",
                        "category": "tteok",
                        "rarity": 3,
                        "tier": "creator",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = validate_pack(tmp_path)
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["characters"][0]["id"] == "custom_tteok"


def test_pack_validate_rejects_duplicate_ids(tmp_path):
    Image.new("RGBA", (256, 256), (255, 240, 210, 255)).save(tmp_path / "dupe.png")
    (tmp_path / "meta.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "dupe",
                        "name_ko": "Dupe",
                        "category": "tteok",
                        "rarity": 2,
                        "tier": "creator",
                    },
                    {
                        "id": "dupe",
                        "name_ko": "Dupe Again",
                        "category": "tteok",
                        "rarity": 2,
                        "tier": "creator",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    result = validate_pack(tmp_path)
    assert result["ok"] is False
    assert any("duplicates" in error for error in result["errors"])


def test_pack_preview_writes_html(tmp_path):
    Image.new("RGBA", (256, 256), (255, 240, 210, 255)).save(tmp_path / "preview_tteok.png")
    (tmp_path / "meta.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "preview_tteok",
                        "name_ko": "Preview Tteok",
                        "category": "tteok",
                        "rarity": 2,
                        "tier": "creator",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = validate_pack(tmp_path)
    out = tmp_path / "preview.html"
    write_pack_preview(result, out)
    html = out.read_text(encoding="utf-8")
    assert "Preview Tteok" in html
    assert "preview_tteok.png" in html


def test_share_card_writes_png(tmp_path):
    out = tmp_path / "card.png"
    result = write_share_card(
        out=out,
        character_id="white_tteok",
        title="tteoki coding recap",
        subtitle="local MCP pet",
    )
    assert result["ok"] is True
    with Image.open(out) as image:
        assert image.size == (1080, 1080)
