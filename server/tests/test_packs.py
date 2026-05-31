"""Creator-pack runtime loading: discovery, merge, image-path safety, install."""

from __future__ import annotations

from pathlib import Path

import pytest

from chibi_mcp import server, state
from chibi_mcp.commercial import init_pack, install_pack


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("CHIBI_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.delenv("CHIBI_PACK_DIRS", raising=False)
    state.reset_state_for_tests()
    server._CATALOG_PARSE_CACHE.clear()
    server._ASSET_DIR_CACHE = None
    yield tmp_path
    state.reset_state_for_tests()
    server._CATALOG_PARSE_CACHE.clear()
    server._ASSET_DIR_CACHE = None


def _make_pack(pack_dir: Path, char_id: str = "cloud_chibi") -> Path:
    result = init_pack(
        pack_dir, character_id=char_id, name="Cloud Chibi", category="chibi", tier="creator", force=True
    )
    assert result["ok"], result
    return pack_dir


def test_pack_dir_characters_appear_in_catalog(runtime, monkeypatch):
    pack = _make_pack(runtime / "mypack")
    monkeypatch.setenv("CHIBI_PACK_DIRS", str(pack))
    server._CATALOG_PARSE_CACHE.clear()

    catalog = server.get_catalog()
    ids = [c["id"] for c in catalog["characters"]]
    assert "cloud_chibi" in ids
    assert catalog["creator_characters"] >= 1
    # official released count stays unchanged by packs
    assert catalog["total_in_tier"] == 8

    pack_ch = next(c for c in catalog["characters"] if c["id"] == "cloud_chibi")
    assert pack_ch.get("source") == "creator"
    image = server._resolve_catalog_image(catalog["asset_dir"], pack_ch, "characters")
    assert image is not None and image.exists()


def test_pack_image_path_traversal_is_rejected(runtime):
    pack = runtime / "evil"
    item = {"id": "evil_one", "image": "../../../../etc/passwd", "pack_dir": str(pack)}
    # pack_dir is the trusted root; an image escaping it must not resolve.
    assert server._resolve_catalog_image(str(runtime / "assets"), item, "characters") is None


def test_install_pack_copies_and_grants_ownership(runtime):
    pack = _make_pack(runtime / "starpack", char_id="star_chibi")
    result = install_pack(pack)
    assert result["ok"], result

    dest = Path(result["installed"])
    assert dest.exists() and (dest / "meta.json").exists()
    assert "star_chibi" in result["owned"]
    assert "star_chibi" in state.get_state().inventory


def test_install_pack_makes_character_usable_in_catalog(runtime):
    pack = _make_pack(runtime / "usable", char_id="usable_chibi")
    install_pack(pack)
    server._CATALOG_PARSE_CACHE.clear()
    catalog = server.get_catalog()
    assert "usable_chibi" in [c["id"] for c in catalog["characters"]]


def test_official_ids_win_over_pack_duplicates(runtime, monkeypatch):
    pack = runtime / "dup"
    _make_pack(pack, char_id="white_tteok")  # collides with an official id
    monkeypatch.setenv("CHIBI_PACK_DIRS", str(pack))
    server._CATALOG_PARSE_CACHE.clear()

    catalog = server.get_catalog()
    white = [c for c in catalog["characters"] if c["id"] == "white_tteok"]
    assert len(white) == 1
    assert white[0].get("source") != "creator"  # official entry kept, pack dropped


def test_invalid_pack_is_not_installed(runtime):
    bad = runtime / "bad"
    bad.mkdir()
    (bad / "meta.json").write_text('{"characters": []}', encoding="utf-8")
    result = install_pack(bad)
    assert result["ok"] is False
    assert not (server.runtime_file("packs") / "bad").exists()
