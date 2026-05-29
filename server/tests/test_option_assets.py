"""Asset integrity checks for free option layers."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOTS = [
    ROOT / "assets",
    ROOT / "server" / "chibi_mcp" / "assets",
    ROOT / "vscode-ext" / "resources",
]
EXPECTED_OPTIONS = {
    "jocheong_drip",
    "honey_glaze",
    "sugar_beads",
    "rainbow_sprinkles",
    "condensed_milk",
    "kinako_dust",
    "black_sesame",
    "red_bean_bits",
    "flower_petals",
    "resin_stars",
    "matcha_powder",
    "spicy_sauce",
}
REQUIRED_RIGHTS_FIELDS = {
    "license",
    "source_rights",
    "rights_owner",
    "asset_origin",
    "permission_scope",
    "no_third_party_ip",
}


def test_free_option_assets_match_across_install_surfaces():
    expected_ids: list[str] | None = None

    for asset_root in ASSET_ROOTS:
        catalog = json.loads((asset_root / "meta.json").read_text(encoding="utf-8"))
        assert set(catalog) >= REQUIRED_RIGHTS_FIELDS
        assert catalog["no_third_party_ip"] is True
        options = [option for option in catalog["options"] if option["tier"] == "free"]
        ids = [option["id"] for option in options]

        assert set(ids) >= EXPECTED_OPTIONS
        assert len(ids) >= 12
        if expected_ids is None:
            expected_ids = ids
        else:
            assert ids == expected_ids

        for option in options:
            image_path = asset_root / option["image"]
            assert image_path.exists(), image_path
            with Image.open(image_path) as image:
                assert image.size == (512, 512), image_path
                assert image.mode == "RGBA", image_path
                alpha = image.getchannel("A")
                assert alpha.getbbox() is not None, image_path
