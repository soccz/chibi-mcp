"""Tests for the human-facing chibi-mcp CLI helpers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

from chibi_mcp import __main__ as main_mod
from chibi_mcp import __version__
from chibi_mcp.__main__ import _check, _ws_endpoint
from chibi_mcp.commercial import (
    _missing_project_files,
    build_trust_audit,
    init_pack,
    validate_pack,
    write_pack_preview,
    write_share_card,
)

ROOT = Path(__file__).resolve().parents[2]


def test_version_matches_release():
    assert __version__ == "1.4.28"


def test_stdio_startup_does_not_write_non_protocol_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "server")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "chibi_mcp", "--no-ws"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            timeout=1.5,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        assert exc.stdout in (None, b"")
        assert exc.stderr in (None, b"")
    else:
        assert result.returncode == 0
        assert result.stdout == b""
        assert result.stderr == b""


def test_stdio_jsonrpc_handles_initialize_list_and_call():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "server")
    env["CHIBI_ASSET_DIR"] = str(ROOT / "server" / "chibi_mcp" / "assets")
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_catalog", "arguments": {}},
        },
    ]
    payload = "".join(json.dumps(message) + "\n" for message in messages)

    result = subprocess.run(
        [sys.executable, "-m", "chibi_mcp", "--no-ws"],
        cwd=ROOT,
        env=env,
        input=payload.encode(),
        capture_output=True,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == b""
    responses = [json.loads(line) for line in result.stdout.decode().splitlines()]
    assert [response["id"] for response in responses] == [1, 2, 3]
    assert responses[0]["result"]["serverInfo"] == {
        "name": "chibi-mcp",
        "version": "1.4.28",
    }
    tools = {tool["name"] for tool in responses[1]["result"]["tools"]}
    assert {"get_catalog", "get_pet_state", "pull_gacha"}.issubset(tools)
    call_result = responses[2]["result"]
    assert call_result["isError"] is False
    assert call_result["structuredContent"]["total_in_tier"] >= 8


def test_check_finds_packaged_assets():
    result = _check()
    assert result["ok"] is True
    assert result["catalog_count"] >= 8
    assert result["option_count"] >= 12
    assert result["free_assets_missing"] == []
    assert result["free_options_missing"] == []


def test_open_cli_reports_direct_window_result(monkeypatch, capsys):
    def fake_open_pet_window(character_id=None, view_mode=None):
        return {
            "opened": True,
            "pid": 123,
            "character": character_id or "mochi",
            "name_ko": "mochi",
            "rarity": 2,
            "mood": "calm",
            "view_mode": view_mode,
            "log_path": "/tmp/window.log",
        }

    monkeypatch.setattr(main_mod.server_tools, "open_pet_window", fake_open_pet_window)

    assert main_mod.main(["--open", "--character-id", "mochi", "--view-mode", "debug"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["opened"] is True
    assert payload["character"] == "mochi"
    assert payload["view_mode"] == "debug"
    assert payload["log_path"] == "/tmp/window.log"


def test_invalid_ws_port_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("CHIBI_WS_PORT", "bad")
    assert _ws_endpoint() == ("127.0.0.1", 9876)


def test_trust_audit_reports_local_first_defaults():
    report = build_trust_audit()
    assert report["ok"] is True
    assert report["trust"]["telemetry"] == "none"
    assert report["trust"]["localhost_only_by_default"] is True
    assert report["trust"]["paid_core_gate"] == "none"
    assert report["assets"]["option_count"] >= 12
    assert report["assets"]["free_options_missing"] == []
    readiness = report["commercial_readiness"]
    assert readiness["monetization_enabled"] is False
    assert readiness["readiness_files_missing"] == []
    assert readiness["pilot_feedback_template"] is True
    assert readiness["collaboration_template"] is True


def test_project_readiness_missing_handles_windows_paths():
    expected = [
        "docs/PRODUCT_MARKET_READINESS.md",
        ".github/ISSUE_TEMPLATE/team_pilot.yml",
    ]
    found = [
        r"D:\a\chibi-mcp\chibi-mcp\docs\PRODUCT_MARKET_READINESS.md",
        r"D:\a\chibi-mcp\chibi-mcp\.github\ISSUE_TEMPLATE\team_pilot.yml",
    ]
    assert _missing_project_files(expected, found) == []


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


def test_pack_submission_validation_requires_rights_metadata(tmp_path):
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
    result = validate_pack(tmp_path, submission=True)
    assert result["ok"] is False
    assert "meta.json license is required for submissions" in result["errors"]
    assert "meta.json source_rights is required for submissions" in result["errors"]
    assert "meta.json rights_owner is required for submissions" in result["errors"]
    assert "meta.json asset_origin is required for submissions" in result["errors"]
    assert "meta.json permission_scope is required for submissions" in result["errors"]
    assert "meta.json no_third_party_ip must be true for submissions" in result["errors"]


def test_pack_submission_requires_no_third_party_ip_true(tmp_path):
    Image.new("RGBA", (256, 256), (255, 240, 210, 255)).save(tmp_path / "custom_tteok.png")
    (tmp_path / "meta.json").write_text(
        json.dumps(
            {
                "license": "original-submission",
                "source_rights": "Original artwork by Test Artist, submitted with permission.",
                "rights_owner": "Test Artist",
                "asset_origin": "original",
                "permission_scope": "May be reviewed, previewed, and distributed by chibi-mcp if accepted.",
                "no_third_party_ip": False,
                "characters": [
                    {
                        "id": "custom_tteok",
                        "name_ko": "Custom Tteok",
                        "category": "tteok",
                        "rarity": 3,
                        "tier": "creator",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = validate_pack(tmp_path, submission=True)
    assert result["ok"] is False
    assert result["errors"] == ["meta.json no_third_party_ip must be true for submissions"]


def test_pack_submission_accepts_complete_rights_metadata(tmp_path):
    Image.new("RGBA", (256, 256), (255, 240, 210, 255)).save(tmp_path / "custom_tteok.png")
    (tmp_path / "meta.json").write_text(
        json.dumps(
            {
                "license": "original-submission",
                "source_rights": "Original artwork by Test Artist, submitted with permission.",
                "rights_owner": "Test Artist",
                "asset_origin": "original",
                "permission_scope": "May be reviewed, previewed, and distributed by chibi-mcp if accepted.",
                "no_third_party_ip": True,
                "characters": [
                    {
                        "id": "custom_tteok",
                        "name_ko": "Custom Tteok",
                        "category": "tteok",
                        "rarity": 3,
                        "tier": "creator",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = validate_pack(tmp_path, submission=True)
    assert result["ok"] is True
    assert result["metadata"]["rights_owner"] == "Test Artist"


def test_pack_init_scaffolds_valid_pack(tmp_path):
    pack_dir = tmp_path / "pack"
    result = init_pack(
        pack_dir,
        character_id="starter_tteok",
        name="Starter Tteok",
        category="tteok",
        tier="creator",
    )
    assert result["ok"] is True
    validation = validate_pack(pack_dir)
    assert validation["ok"] is True
    assert validation["characters"][0]["id"] == "starter_tteok"
    submission_validation = validate_pack(pack_dir, submission=True)
    assert submission_validation["ok"] is False
    assert "meta.json license is required for submissions" in submission_validation["errors"]
    assert "meta.json source_rights is required for submissions" in submission_validation["errors"]
    assert "meta.json rights_owner is required for submissions" in submission_validation["errors"]
    assert "meta.json permission_scope is required for submissions" in submission_validation["errors"]
    assert "meta.json no_third_party_ip must be true for submissions" in submission_validation["errors"]


def test_sample_commercial_packs_validate():
    for pack_dir in [
        ROOT / "examples" / "packs" / "spring-hwajeon",
        ROOT / "examples" / "packs" / "team-sprint",
    ]:
        result = validate_pack(pack_dir, submission=True)
        assert result["ok"] is True
        assert len(result["characters"]) == 1
        assert len(result["options"]) == 1


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


def test_pack_validate_rejects_image_path_escape(tmp_path):
    outside = tmp_path / "outside.png"
    Image.new("RGBA", (256, 256), (255, 240, 210, 255)).save(outside)
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "meta.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "escape_tteok",
                        "name_ko": "Escape",
                        "category": "tteok",
                        "rarity": 2,
                        "tier": "creator",
                        "image": "../outside.png",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = validate_pack(pack_dir)
    assert result["ok"] is False
    assert any("inside the pack directory" in error for error in result["errors"])


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


def test_pack_validate_accepts_option_only_pack(tmp_path):
    option_dir = tmp_path / "options"
    option_dir.mkdir()
    Image.new("RGBA", (256, 256), (255, 180, 20, 180)).save(option_dir / "honey_glaze.png")
    (tmp_path / "meta.json").write_text(
        json.dumps(
            {
                "options": [
                    {
                        "id": "honey_glaze",
                        "name_ko": "Honey Glaze",
                        "category": "glaze",
                        "tier": "creator",
                        "image": "options/honey_glaze.png",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = validate_pack(tmp_path)
    assert result["ok"] is True
    assert result["options"][0]["id"] == "honey_glaze"


def test_share_card_writes_png(tmp_path):
    out = tmp_path / "card.png"
    result = write_share_card(
        out=out,
        character_id="white_tteok",
        title="chibi coding recap",
        subtitle="local MCP pet",
    )
    assert result["ok"] is True
    assert result["size"] == [1080, 1080]
    with Image.open(out) as image:
        assert image.size == (1080, 1080)


def test_social_preview_writes_expected_size(tmp_path):
    out = tmp_path / "social-preview.png"
    result = write_share_card(
        out=out,
        character_id="white_tteok",
        title="chibi",
        subtitle="local MCP pet",
        preset="social-preview",
    )
    assert result["ok"] is True
    assert result["size"] == [1280, 640]
    with Image.open(out) as image:
        assert image.size == (1280, 640)


def test_lineup_preview_writes_expected_size(tmp_path):
    out = tmp_path / "starter-lineup.png"
    result = write_share_card(
        out=out,
        character_id="white_tteok",
        title="chibi starter lineup",
        subtitle="local MCP pet",
        preset="lineup",
    )
    assert result["ok"] is True
    assert result["size"] == [1600, 900]
    with Image.open(out) as image:
        assert image.size == (1600, 900)


def test_options_preview_writes_expected_size(tmp_path):
    out = tmp_path / "option-showcase.png"
    result = write_share_card(
        out=out,
        character_id="white_tteok",
        title="chibi options",
        subtitle="honey, jocheong, beads",
        preset="options",
    )
    assert result["ok"] is True
    assert result["size"] == [1600, 900]
    with Image.open(out) as image:
        assert image.size == (1600, 900)
