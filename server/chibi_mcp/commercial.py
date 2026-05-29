"""Commercial-readiness helper CLIs.

These commands do not turn on paid gates. They make the free core easier to
trust, share, and extend with creator/team character packs.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from . import __version__
from .server import _resolve_asset_dir
from .state import STATE_FILE, get_state
from .ws_server import DEFAULT_WS_HOST, DEFAULT_WS_PORT

CHARACTER_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
CATEGORY_RE = re.compile(r"^[a-z][a-z0-9_-]{0,40}$")
VALID_TIERS = {"free", "upcoming", "creator", "supporter", "team", "collab"}
VALID_RARITIES = {2, 3, 4, 5}
VALID_ASSET_ORIGINS = {"original", "commissioned", "generated", "licensed", "public-domain", "sample"}


def audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chibi-audit",
        description="Print a local trust/readiness report for chibi-mcp.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    report = build_trust_audit()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_format_audit(report))
    return 0 if report["ok"] else 1


def pack_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chibi-pack",
        description="Validate and preview creator/team character packs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a starter character pack")
    init.add_argument("pack_dir", type=Path)
    init.add_argument("--id", default="my_tteok", help="Starter character id")
    init.add_argument("--name", default="My Tteok", help="Starter display name")
    init.add_argument("--category", default="tteok", help="Starter category slug")
    init.add_argument("--tier", default="creator", help="Pack tier")
    init.add_argument("--force", action="store_true", help="Overwrite existing starter files")

    validate = sub.add_parser("validate", help="Validate a pack directory")
    validate.add_argument("pack_dir", type=Path)
    validate.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    validate.add_argument(
        "--submission",
        action="store_true",
        help="Require rights metadata for public submissions",
    )

    preview = sub.add_parser("preview", help="Write a static HTML pack preview")
    preview.add_argument("pack_dir", type=Path)
    preview.add_argument("--out", type=Path, help="Output HTML path; defaults to <pack_dir>/preview.html")
    preview.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    args = parser.parse_args(argv)
    if args.command == "init":
        result = init_pack(
            args.pack_dir,
            character_id=args.id,
            name=args.name,
            category=args.category,
            tier=args.tier,
            force=args.force,
        )
        if result["ok"]:
            print(f"created: {result['pack_dir']}")
            print("next: chibi-pack validate " + result["pack_dir"])
            print(
                "submit: fill rights metadata, then chibi-pack validate --submission "
                + result["pack_dir"]
            )
        else:
            print(result["error"], file=sys.stderr)
        return 0 if result["ok"] else 1

    if args.command == "validate":
        result = validate_pack(args.pack_dir, submission=args.submission)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(_format_pack_validation(result))
        return 0 if result["ok"] else 1

    if args.command == "preview":
        result = validate_pack(args.pack_dir)
        if not result["ok"]:
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(_format_pack_validation(result), file=sys.stderr)
            return 1
        out = args.out or (args.pack_dir / "preview.html")
        out = out.expanduser().resolve()
        write_pack_preview(result, out)
        payload = {"ok": True, "preview": str(out), "characters": result["characters"]}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"preview: {out}")
        return 0

    return 2


def share_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chibi-share",
        description="Generate a local share card PNG for your coding session.",
    )
    parser.add_argument("--out", type=Path, help="Output PNG path")
    parser.add_argument(
        "--preset",
        choices=("square", "social-preview", "lineup", "options"),
        default="square",
        help="Card dimensions: square=1080x1080, social-preview=1280x640, lineup/options=1600x900",
    )
    parser.add_argument("--character", default=None, help="Character id to render")
    parser.add_argument("--title", default="tteoki coding recap")
    parser.add_argument(
        "--subtitle",
        default="local MCP pet for Claude Code, Codex, and VS Code",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    default_names = {
        "square": "share-card.png",
        "social-preview": "social-preview.png",
        "lineup": "starter-lineup.png",
        "options": "option-showcase.png",
    }
    default_name = default_names[args.preset]
    out = args.out or (Path.home() / ".chibi-mcp" / default_name)
    out = out.expanduser().resolve()
    result = write_share_card(
        out=out,
        character_id=args.character,
        title=args.title,
        subtitle=args.subtitle,
        preset=args.preset,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"share_card: {result['path']}")
    return 0 if result["ok"] else 1


def init_pack(
    pack_dir: Path,
    *,
    character_id: str,
    name: str,
    category: str,
    tier: str,
    force: bool = False,
) -> dict[str, Any]:
    pack_dir = pack_dir.expanduser().resolve()
    character_id = character_id.strip()
    category = category.strip()
    tier = tier.strip()
    name = name.strip()
    if not CHARACTER_ID_RE.fullmatch(character_id):
        return {"ok": False, "error": f"invalid id: {character_id!r}", "pack_dir": str(pack_dir)}
    if not CATEGORY_RE.fullmatch(category):
        return {"ok": False, "error": f"invalid category: {category!r}", "pack_dir": str(pack_dir)}
    if tier not in VALID_TIERS:
        return {"ok": False, "error": f"invalid tier: {tier!r}", "pack_dir": str(pack_dir)}
    if not name:
        return {"ok": False, "error": "name must not be empty", "pack_dir": str(pack_dir)}

    meta_path = pack_dir / "meta.json"
    image_dir = pack_dir / "characters"
    image_path = image_dir / f"{character_id}.png"
    existing = [str(path) for path in (meta_path, image_path) if path.exists()]
    if existing and not force:
        return {
            "ok": False,
            "error": "refusing to overwrite existing files without --force: " + ", ".join(existing),
            "pack_dir": str(pack_dir),
        }

    image_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "license": "draft",
        "source_rights": "TODO: replace before public submission with artwork source, license, and permission.",
        "rights_owner": "TODO: replace with the owner or authorized submitter.",
        "asset_origin": "original",
        "permission_scope": "TODO: explain how chibi-mcp may review, preview, and distribute this pack.",
        "no_third_party_ip": False,
        "characters": [
            {
                "id": character_id,
                "name_ko": name,
                "category": category,
                "rarity": 2,
                "tier": tier,
                "image": f"characters/{character_id}.png",
            }
        ]
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_starter_pack_png(image_path, label=character_id)
    return {
        "ok": True,
        "pack_dir": str(pack_dir),
        "meta": str(meta_path),
        "image": str(image_path),
    }


def build_trust_audit() -> dict[str, Any]:
    asset_dir = _resolve_asset_dir()
    catalog_count = 0
    free_assets_missing: list[str] = []
    if asset_dir:
        meta_path = Path(asset_dir) / "meta.json"
        try:
            catalog = json.loads(meta_path.read_text(encoding="utf-8"))
            characters = catalog.get("characters", [])
            catalog_count = len(characters)
            for character in characters:
                if character.get("tier") == "free":
                    image = _resolve_character_image(Path(asset_dir), character)
                    if image is None:
                        free_assets_missing.append(str(character.get("id", "<missing-id>")))
            options = catalog.get("options", [])
            free_options_missing = []
            for option in options:
                if option.get("tier") == "free":
                    image = _resolve_character_image(Path(asset_dir), option, subdir="options")
                    if image is None:
                        free_options_missing.append(str(option.get("id", "<missing-id>")))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            free_assets_missing.append("meta.json")
            options = []
            free_options_missing = ["meta.json"]
    else:
        options = []
        free_options_missing = []

    entrypoints = {
        name: shutil.which(name)
        for name in (
            "chibi-mcp",
            "chibi-say",
            "chibi-check",
            "chibi-audit",
            "chibi-pack",
            "chibi-share",
        )
    }
    hook_files = _find_project_files(
        [
            "hooks/hooks.json",
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
            ".mcp.json",
        ]
    )
    readiness_expected = [
        "COMMERCIAL_STRATEGY.md",
        "docs/PRODUCT_MARKET_READINESS.md",
        "docs/TEAM_ADOPTION.md",
        "docs/PILOT_PLAYBOOK.md",
        "docs/LAUNCH_KIT.md",
        "docs/CREATOR_PACKS.md",
        "docs/IP_AND_RIGHTS.md",
        "OFFICIAL_ASSET_TERMS.md",
        "TRADEMARK.md",
        ".github/ISSUE_TEMPLATE/team_pilot.yml",
        ".github/ISSUE_TEMPLATE/collaboration_idea.yml",
    ]
    readiness_files = _find_project_files(readiness_expected)
    readiness_missing = _missing_project_files(readiness_expected, readiness_files)
    report = {
        "ok": bool(asset_dir and not free_assets_missing),
        "version": __version__,
        "trust": {
            "telemetry": "none",
            "network_default": f"ws://{DEFAULT_WS_HOST}:{DEFAULT_WS_PORT}",
            "localhost_only_by_default": DEFAULT_WS_HOST in {"127.0.0.1", "localhost"},
            "state_file": str(STATE_FILE),
            "paid_core_gate": "none",
        },
        "assets": {
            "asset_dir": asset_dir,
            "catalog_count": catalog_count,
            "option_count": len(options),
            "free_assets_missing": free_assets_missing,
            "free_options_missing": free_options_missing,
        },
        "entrypoints": entrypoints,
        "project_files": hook_files,
        "commercial_readiness": {
            "monetization_enabled": False,
            "readiness_files_found": readiness_files,
            "readiness_files_missing": readiness_missing,
            "pilot_feedback_template": not any(
                missing == ".github/ISSUE_TEMPLATE/team_pilot.yml" for missing in readiness_missing
            ),
            "collaboration_template": not any(
                missing == ".github/ISSUE_TEMPLATE/collaboration_idea.yml" for missing in readiness_missing
            ),
        },
        "environment": {
            "CHIBI_WS_HOST": os.environ.get("CHIBI_WS_HOST"),
            "CHIBI_WS_PORT": os.environ.get("CHIBI_WS_PORT"),
            "CHIBI_ASSET_DIR": os.environ.get("CHIBI_ASSET_DIR"),
        },
    }
    return report


def validate_pack(pack_dir: Path, *, submission: bool = False) -> dict[str, Any]:
    pack_dir = pack_dir.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    characters_out: list[dict[str, Any]] = []
    options_out: list[dict[str, Any]] = []

    meta_path = pack_dir / "meta.json"
    if not pack_dir.exists():
        return _pack_result(pack_dir, errors=[f"pack directory does not exist: {pack_dir}"])
    if not meta_path.exists():
        return _pack_result(pack_dir, errors=[f"missing meta.json: {meta_path}"])

    try:
        catalog = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _pack_result(pack_dir, errors=[f"meta.json is invalid JSON: {exc}"])
    except OSError as exc:
        return _pack_result(pack_dir, errors=[f"cannot read meta.json: {exc}"])

    characters = catalog.get("characters", [])
    options = catalog.get("options", [])
    if not isinstance(characters, list):
        return _pack_result(pack_dir, errors=["meta.json characters must be a list"])
    if not isinstance(options, list):
        return _pack_result(pack_dir, errors=["meta.json options must be a list"])
    if not characters and not options:
        return _pack_result(pack_dir, errors=["meta.json must contain characters or options"])

    license_value = str(catalog.get("license") or "").strip()
    rights_value = str(catalog.get("source_rights") or catalog.get("rights") or "").strip()
    rights_owner = str(catalog.get("rights_owner") or "").strip()
    asset_origin = str(catalog.get("asset_origin") or "").strip().lower()
    permission_scope = str(catalog.get("permission_scope") or "").strip()
    no_third_party_ip = catalog.get("no_third_party_ip")
    if submission:
        if _missing_submission_value(license_value):
            errors.append("meta.json license is required for submissions")
        if _missing_submission_value(rights_value):
            errors.append("meta.json source_rights is required for submissions")
        if _missing_submission_value(rights_owner):
            errors.append("meta.json rights_owner is required for submissions")
        if _missing_submission_value(asset_origin):
            errors.append("meta.json asset_origin is required for submissions")
        elif asset_origin not in VALID_ASSET_ORIGINS:
            errors.append(f"meta.json asset_origin must be one of {sorted(VALID_ASSET_ORIGINS)}")
        if _missing_submission_value(permission_scope):
            errors.append("meta.json permission_scope is required for submissions")
        if no_third_party_ip is not True:
            errors.append("meta.json no_third_party_ip must be true for submissions")
    elif _missing_submission_value(rights_value):
        warnings.append("meta.json source_rights is recommended for public submissions")
    if not submission and no_third_party_ip is not True:
        warnings.append("meta.json no_third_party_ip=true is recommended before public submissions")

    seen: set[str] = set()
    for index, character in enumerate(characters):
        prefix = f"characters[{index}]"
        if not isinstance(character, dict):
            errors.append(f"{prefix} must be an object")
            continue

        character_id = str(character.get("id", "")).strip()
        if not CHARACTER_ID_RE.fullmatch(character_id):
            errors.append(f"{prefix}.id must match {CHARACTER_ID_RE.pattern!r}")
            continue
        if character_id in seen:
            errors.append(f"{prefix}.id duplicates {character_id!r}")
        seen.add(character_id)

        name = str(character.get("name_ko") or character.get("name") or "").strip()
        if not name:
            errors.append(f"{prefix}.name_ko is required")

        category = str(character.get("category", "")).strip()
        if not CATEGORY_RE.fullmatch(category):
            errors.append(f"{prefix}.category must be a lowercase slug")

        try:
            rarity = int(character.get("rarity"))
        except (TypeError, ValueError):
            rarity = 0
        if rarity not in VALID_RARITIES:
            errors.append(f"{prefix}.rarity must be one of {sorted(VALID_RARITIES)}")

        tier = str(character.get("tier", "creator")).strip()
        if tier not in VALID_TIERS:
            warnings.append(f"{prefix}.tier {tier!r} is unusual; expected one of {sorted(VALID_TIERS)}")

        locked = bool(character.get("locked"))
        image_path = _resolve_character_image(pack_dir, character, errors=errors, prefix=prefix)
        if image_path is None:
            if locked or tier == "upcoming":
                warnings.append(f"{prefix} is locked/upcoming and has no image")
            else:
                errors.append(f"{prefix} image is missing; add image or {character_id}.png")
        else:
            _validate_png(prefix, image_path, errors, warnings)

        characters_out.append(
            {
                "id": character_id,
                "name": name,
                "category": category,
                "rarity": rarity,
                "tier": tier,
                "locked": locked,
                "image": str(image_path) if image_path else None,
            }
        )

    seen_options: set[str] = set()
    for index, option in enumerate(options):
        prefix = f"options[{index}]"
        if not isinstance(option, dict):
            errors.append(f"{prefix} must be an object")
            continue

        option_id = str(option.get("id", "")).strip()
        if not CHARACTER_ID_RE.fullmatch(option_id):
            errors.append(f"{prefix}.id must match {CHARACTER_ID_RE.pattern!r}")
            continue
        if option_id in seen_options:
            errors.append(f"{prefix}.id duplicates {option_id!r}")
        seen_options.add(option_id)

        name = str(option.get("name_ko") or option.get("name") or "").strip()
        if not name:
            errors.append(f"{prefix}.name_ko is required")

        category = str(option.get("category", "")).strip()
        if not CATEGORY_RE.fullmatch(category):
            errors.append(f"{prefix}.category must be a lowercase slug")

        tier = str(option.get("tier", "creator")).strip()
        if tier not in VALID_TIERS:
            warnings.append(f"{prefix}.tier {tier!r} is unusual; expected one of {sorted(VALID_TIERS)}")

        locked = bool(option.get("locked"))
        image_path = _resolve_character_image(pack_dir, option, errors=errors, prefix=prefix, subdir="options")
        if image_path is None:
            if locked or tier == "upcoming":
                warnings.append(f"{prefix} is locked/upcoming and has no image")
            else:
                errors.append(f"{prefix} image is missing; add image or options/{option_id}.png")
        else:
            _validate_png(prefix, image_path, errors, warnings)

        options_out.append(
            {
                "id": option_id,
                "name": name,
                "category": category,
                "tier": tier,
                "locked": locked,
                "image": str(image_path) if image_path else None,
            }
        )

    return _pack_result(
        pack_dir,
        errors=errors,
        warnings=warnings,
        characters=characters_out,
        options=options_out,
        metadata={
            "license": license_value,
            "source_rights": rights_value,
            "rights_owner": rights_owner,
            "asset_origin": asset_origin,
            "permission_scope": permission_scope,
            "no_third_party_ip": no_third_party_ip,
            "submission": submission,
        },
    )


def write_pack_preview(validation: dict[str, Any], out: Path) -> None:
    pack_dir = Path(validation["pack_dir"])
    metadata = validation.get("metadata") or {}
    license_text = str(metadata.get("license") or "missing")
    rights_value = str(metadata.get("source_rights") or "")
    rights_text = "source rights provided" if not _missing_submission_value(rights_value) else "source rights missing"
    out.parent.mkdir(parents=True, exist_ok=True)
    cards = []
    for character in validation["characters"]:
        detail = f'{character["id"]} | {character["category"]} | star {int(character["rarity"])}'
        cards.append(_pack_preview_card(character, out.parent, detail))
    for option in validation.get("options", []):
        detail = f'{option["id"]} | {option["category"]} | option'
        cards.append(_pack_preview_card(option, out.parent, detail))
    body = "\n".join(cards)
    html_doc = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>chibi pack preview</title>
<style>
  :root {{
    color-scheme: light;
    --ink: #1f2937;
    --muted: #64748b;
    --bg: #fff7ed;
    --panel: #ffffff;
    --line: #fed7aa;
    --accent: #0f766e;
  }}
  body {{
    margin: 0;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--ink);
  }}
  header {{
    max-width: 1040px;
    margin: 0 auto;
    padding: 32px 20px 18px;
  }}
  h1 {{
    margin: 0 0 8px;
    font-size: 30px;
    letter-spacing: 0;
  }}
  .meta {{
    margin: 0;
    color: var(--muted);
  }}
  main {{
    max-width: 1040px;
    margin: 0 auto;
    padding: 0 20px 40px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 14px;
  }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px;
    min-height: 220px;
  }}
  img {{
    width: 128px;
    height: 128px;
    object-fit: contain;
    display: block;
    margin: 0 auto 12px;
  }}
  .placeholder {{
    width: 128px;
    height: 128px;
    margin: 0 auto 12px;
    display: grid;
    place-items: center;
    border-radius: 8px;
    background: #f8fafc;
    color: #94a3b8;
    font-weight: 700;
  }}
  h2 {{
    margin: 0 0 6px;
    font-size: 17px;
    letter-spacing: 0;
  }}
  p {{
    margin: 0;
    color: var(--muted);
    font-size: 13px;
  }}
</style>
<header>
  <h1>chibi pack preview</h1>
  <p class="meta">{html.escape(str(pack_dir))}</p>
  <p class="meta">license: {html.escape(license_text)} | {html.escape(rights_text)}</p>
</header>
<main>
{body}
</main>
</html>
"""
    out.write_text(html_doc, encoding="utf-8")


def _pack_preview_card(item: dict[str, Any], base_dir: Path, detail: str) -> str:
    image_path = item.get("image")
    if image_path:
        src = os.path.relpath(image_path, base_dir)
        media = f'  <img src="{html.escape(src)}" alt="{html.escape(item["id"])}">'
    else:
        media = '  <div class="placeholder">???</div>'
    return "\n".join(
        [
            '<article class="card">',
            media,
            f'  <h2>{html.escape(item["name"] or item["id"])}</h2>',
            f"  <p>{html.escape(detail)}</p>",
            "</article>",
        ]
    )


def write_share_card(
    *,
    out: Path,
    character_id: str | None = None,
    title: str,
    subtitle: str,
    preset: str = "square",
) -> dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    asset_dir = _resolve_asset_dir()
    if not asset_dir:
        return {"ok": False, "path": str(out), "reason": "asset directory not found"}

    asset_path = _pick_share_asset(Path(asset_dir), character_id)
    if asset_path is None:
        return {"ok": False, "path": str(out), "reason": "no PNG asset found"}

    state = get_state().snapshot()
    counters = state["counters"]
    gacha = state["gacha"]
    mood = state["mood"]

    if preset == "social-preview":
        width, height = 1280, 640
    elif preset in {"lineup", "options"}:
        width, height = 1600, 900
    else:
        width = height = 1080
    image = Image.new("RGB", (width, height), "#fff7ed")
    draw = ImageDraw.Draw(image)
    title_font = _load_font(68, bold=True)
    subtitle_font = _load_font(32)
    metric_font = _load_font(30, bold=True)
    small_font = _load_font(24)

    if preset == "social-preview":
        _draw_social_preview_card(
            image=image,
            draw=draw,
            asset_path=asset_path,
            title=title,
            subtitle=subtitle,
            mood=mood,
            counters=counters,
            gacha=gacha,
            title_font=title_font,
            subtitle_font=subtitle_font,
            metric_font=metric_font,
            small_font=small_font,
        )
    elif preset == "lineup":
        _draw_lineup_share_card(
            image=image,
            draw=draw,
            asset_path=asset_path,
            title=title,
            subtitle=subtitle,
            mood=mood,
            counters=counters,
            gacha=gacha,
            title_font=title_font,
            subtitle_font=subtitle_font,
            metric_font=metric_font,
            small_font=small_font,
        )
    elif preset == "options":
        _draw_options_share_card(
            image=image,
            draw=draw,
            asset_path=asset_path,
            title=title,
            subtitle=subtitle,
            mood=mood,
            counters=counters,
            gacha=gacha,
            title_font=title_font,
            subtitle_font=subtitle_font,
            metric_font=metric_font,
            small_font=small_font,
        )
    else:
        _draw_square_share_card(
            image=image,
            draw=draw,
            asset_path=asset_path,
            title=title,
            subtitle=subtitle,
            mood=mood,
            counters=counters,
            gacha=gacha,
            title_font=title_font,
            subtitle_font=subtitle_font,
            metric_font=metric_font,
            small_font=small_font,
        )
    image.save(out, "PNG")
    return {
        "ok": True,
        "path": str(out),
        "preset": preset,
        "size": [width, height],
        "character_asset": str(asset_path),
        "mood": mood,
        "calls": counters["calls_total"],
        "slices": counters["slices_today"],
    }


def _draw_square_share_card(
    *,
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    asset_path: Path,
    title: str,
    subtitle: str,
    mood: str,
    counters: dict[str, Any],
    gacha: dict[str, Any],
    title_font: ImageFont.ImageFont,
    subtitle_font: ImageFont.ImageFont,
    metric_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
) -> None:
    width, _height = image.size
    draw.rounded_rectangle((58, 58, 1022, 1022), radius=36, fill="#ffffff", outline="#fed7aa", width=4)
    draw.rounded_rectangle((86, 86, 994, 188), radius=22, fill="#0f766e")
    draw.text((120, 106), _fit_text(draw, title, title_font, 820), fill="#ffffff", font=title_font)
    draw.text((122, 200), _fit_text(draw, subtitle, subtitle_font, 835), fill="#475569", font=subtitle_font)

    draw.ellipse((280, 285, 800, 805), fill="#ffedd5", outline="#f59e0b", width=6)
    _paste_pet(image, asset_path, max_size=(430, 430), center=(width // 2, 530))

    metrics = [
        ("calls", str(counters["calls_total"])),
        ("slices", str(counters["slices_today"])),
        ("mood", mood),
        ("tickets", str(gacha["tickets"])),
    ]
    x0 = 120
    for label, value in metrics:
        draw.rounded_rectangle((x0, 835, x0 + 190, 925), radius=18, fill="#f8fafc", outline="#dbeafe")
        draw.text((x0 + 18, 850), label, fill="#64748b", font=small_font)
        draw.text((x0 + 18, 878), _fit_text(draw, value, metric_font, 154), fill="#1f2937", font=metric_font)
        x0 += 215

    footer = f"chibi-mcp {__version__} | no telemetry | localhost-first"
    draw.text((120, 956), _fit_text(draw, footer, small_font, 840), fill="#64748b", font=small_font)


def _draw_social_preview_card(
    *,
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    asset_path: Path,
    title: str,
    subtitle: str,
    mood: str,
    counters: dict[str, Any],
    gacha: dict[str, Any],
    title_font: ImageFont.ImageFont,
    subtitle_font: ImageFont.ImageFont,
    metric_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
) -> None:
    draw.rounded_rectangle((40, 40, 1240, 600), radius=30, fill="#ffffff", outline="#fed7aa", width=4)
    draw.rounded_rectangle((76, 78, 742, 168), radius=20, fill="#0f766e")
    draw.text((108, 94), _fit_text(draw, title, title_font, 595), fill="#ffffff", font=title_font)
    draw.text((106, 194), _fit_text(draw, subtitle, subtitle_font, 690), fill="#475569", font=subtitle_font)
    draw.text((106, 270), "Claude Code / Codex / VS Code", fill="#1f2937", font=metric_font)
    draw.text((108, 318), "local-first MCP pet | no telemetry | creator packs", fill="#64748b", font=small_font)

    metrics = [
        ("calls", str(counters["calls_total"])),
        ("slices", str(counters["slices_today"])),
        ("mood", mood),
        ("tickets", str(gacha["tickets"])),
    ]
    x0 = 106
    value_font = _load_font(24, bold=True)
    for label, value in metrics:
        draw.rounded_rectangle((x0, 418, x0 + 150, 505), radius=16, fill="#f8fafc", outline="#dbeafe")
        draw.text((x0 + 16, 432), label, fill="#64748b", font=small_font)
        draw.text((x0 + 16, 464), _fit_text(draw, value, value_font, 118), fill="#1f2937", font=value_font)
        x0 += 160

    draw.ellipse((805, 92, 1175, 462), fill="#ffedd5", outline="#f59e0b", width=6)
    _paste_pet(image, asset_path, max_size=(315, 315), center=(990, 277))
    characters = _load_catalog_character_assets(asset_path.parent)[:6]
    for index, character in enumerate(characters):
        x = 812 + index * 60
        y = 482
        draw.rounded_rectangle((x, y, x + 48, y + 48), radius=14, fill="#fff7ed", outline="#fed7aa")
        _paste_pet(image, character["image"], max_size=(42, 42), center=(x + 24, y + 24))
    draw.text((812, 548), f"chibi-mcp {__version__}", fill="#64748b", font=small_font)


def _draw_lineup_share_card(
    *,
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    asset_path: Path,
    title: str,
    subtitle: str,
    mood: str,
    counters: dict[str, Any],
    gacha: dict[str, Any],
    title_font: ImageFont.ImageFont,
    subtitle_font: ImageFont.ImageFont,
    metric_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
) -> None:
    width, height = image.size
    draw.rounded_rectangle(
        (42, 42, width - 42, height - 42),
        radius=34,
        fill="#ffffff",
        outline="#fed7aa",
        width=4,
    )
    draw.rounded_rectangle((82, 78, 1034, 174), radius=22, fill="#0f766e")
    draw.text((116, 96), _fit_text(draw, title, title_font, 860), fill="#ffffff", font=title_font)
    draw.text((116, 206), _fit_text(draw, subtitle, subtitle_font, 1200), fill="#475569", font=subtitle_font)
    draw.text((116, 268), "8 free starter PNG characters from the local catalog", fill="#1f2937", font=metric_font)
    draw.text(
        (116, 316),
        f"calls {counters['calls_total']} | slices {counters['slices_today']} | mood {mood} | tickets {gacha['tickets']}",
        fill="#64748b",
        font=small_font,
    )

    characters = _load_catalog_character_assets(asset_path.parent)[:8]
    if not characters:
        characters = [
            {
                "id": asset_path.stem,
                "name": asset_path.stem,
                "category": "character",
                "rarity": 2,
                "image": asset_path,
            }
        ]

    label_font = _load_font(23, bold=True)
    detail_font = _load_font(22)
    start_x = 86
    start_y = 388
    tile_w = 340
    tile_h = 190
    gap_x = 28
    gap_y = 34
    for index, character in enumerate(characters):
        row, col = divmod(index, 4)
        x = start_x + col * (tile_w + gap_x)
        y = start_y + row * (tile_h + gap_y)
        draw.rounded_rectangle((x, y, x + tile_w, y + tile_h), radius=18, fill="#f8fafc", outline="#dbeafe")
        draw.ellipse((x + 22, y + 30, x + 132, y + 140), fill="#ffedd5", outline="#fed7aa", width=3)
        _paste_pet(image, character["image"], max_size=(102, 102), center=(x + 77, y + 85))
        text_x = x + 154
        max_text_width = tile_w - 176
        label = str(character["id"]).replace("_", " ")
        if label.endswith(" short"):
            label = label.removesuffix(" short")
        draw.text((text_x, y + 48), _fit_text(draw, label, label_font, max_text_width), fill="#1f2937", font=label_font)
        detail = f"{character['category']} | star {character['rarity']}"
        draw.text((text_x, y + 92), _fit_text(draw, detail, detail_font, max_text_width), fill="#64748b", font=detail_font)
        draw.text((text_x, y + 128), "free starter", fill="#0f766e", font=detail_font)

    footer = f"chibi-mcp {__version__} | generated from local PNG assets | no telemetry | localhost-first"
    draw.text((116, height - 88), _fit_text(draw, footer, small_font, 1260), fill="#64748b", font=small_font)


def _draw_options_share_card(
    *,
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    asset_path: Path,
    title: str,
    subtitle: str,
    mood: str,
    counters: dict[str, Any],
    gacha: dict[str, Any],
    title_font: ImageFont.ImageFont,
    subtitle_font: ImageFont.ImageFont,
    metric_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
) -> None:
    width, height = image.size
    draw.rounded_rectangle(
        (42, 42, width - 42, height - 42),
        radius=34,
        fill="#ffffff",
        outline="#fed7aa",
        width=4,
    )
    draw.rounded_rectangle((82, 78, 1080, 174), radius=22, fill="#0f766e")
    draw.text((116, 96), _fit_text(draw, title, title_font, 900), fill="#ffffff", font=title_font)
    draw.text((116, 206), _fit_text(draw, subtitle, subtitle_font, 1200), fill="#475569", font=subtitle_font)
    draw.text((116, 268), "12 free option layers: glaze, powder, seeds, petals, resin, and sauce", fill="#1f2937", font=metric_font)
    draw.text(
        (116, 316),
        f"calls {counters['calls_total']} | slices {counters['slices_today']} | mood {mood} | tickets {gacha['tickets']}",
        fill="#64748b",
        font=small_font,
    )

    options = _load_catalog_option_assets(asset_path.parent)[:12]
    if not options:
        options = [
            {
                "id": "none",
                "name": "No options found",
                "category": "option",
                "image": None,
            }
        ]

    start_x = 92
    start_y = 354
    tile_w = 334
    tile_h = 138
    gap_x = 28
    gap_y = 20
    columns = 4
    label_font = _load_font(20, bold=True)
    detail_font = _load_font(17)
    for index, option in enumerate(options):
        col = index % columns
        row = index // columns
        x = start_x + col * (tile_w + gap_x)
        y = start_y + row * (tile_h + gap_y)
        draw.rounded_rectangle((x, y, x + tile_w, y + tile_h), radius=18, fill="#f8fafc", outline="#dbeafe")
        draw.ellipse((x + 22, y + 22, x + 118, y + 118), fill="#ffedd5", outline="#fed7aa", width=3)
        option_paths = [option["image"]] if option.get("image") else []
        _paste_pet(image, asset_path, max_size=(86, 86), center=(x + 70, y + 70), option_paths=option_paths)
        label = str(option["id"]).replace("_", " ")
        draw.text((x + 132, y + 38), _fit_text(draw, label, label_font, 184), fill="#1f2937", font=label_font)
        detail = f"{option['category']} | free"
        draw.text((x + 132, y + 76), _fit_text(draw, detail, detail_font, 184), fill="#0f766e", font=detail_font)

    footer = f"chibi-mcp {__version__} | option layers are free cosmetics | no telemetry"
    draw.text((116, height - 88), _fit_text(draw, footer, small_font, 1260), fill="#64748b", font=small_font)


def _paste_pet(
    image: Image.Image,
    asset_path: Path,
    *,
    max_size: tuple[int, int],
    center: tuple[int, int],
    option_paths: list[Path] | None = None,
) -> None:
    with Image.open(asset_path) as pet:
        pet = pet.convert("RGBA")
        for option_path in option_paths or []:
            with Image.open(option_path) as option:
                overlay = option.convert("RGBA").resize(pet.size, Image.Resampling.LANCZOS)
                pet.alpha_composite(overlay)
        pet.thumbnail(max_size, Image.Resampling.LANCZOS)
        x = center[0] - pet.width // 2
        y = center[1] - pet.height // 2
        image.paste(pet, (x, y), pet)


def _write_starter_pack_png(image_path: Path, *, label: str) -> None:
    image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((92, 166, 420, 346), radius=84, fill="#fff7ed", outline="#f59e0b", width=10)
    draw.ellipse((182, 226, 210, 254), fill="#1f2937")
    draw.ellipse((302, 226, 330, 254), fill="#1f2937")
    draw.arc((212, 230, 300, 304), start=10, end=170, fill="#1f2937", width=6)
    draw.ellipse((150, 265, 202, 310), fill="#fecaca")
    draw.ellipse((310, 265, 362, 310), fill="#fecaca")
    font = _load_font(28, bold=True)
    draw.text((112, 382), label[:18], fill="#0f766e", font=font)
    image.save(image_path, "PNG")


def _load_catalog_character_assets(asset_dir: Path) -> list[dict[str, Any]]:
    asset_dir = asset_dir.resolve()
    meta_path = asset_dir / "meta.json"
    characters: list[dict[str, Any]] = []
    try:
        catalog = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        catalog = {"characters": []}

    for character in catalog.get("characters", []):
        if not isinstance(character, dict) or character.get("tier") != "free":
            continue
        image_path = _resolve_character_image(asset_dir, character)
        if image_path is None:
            continue
        character_id = str(character.get("id", image_path.stem)).strip() or image_path.stem
        characters.append(
            {
                "id": character_id,
                "name": str(character.get("name_ko") or character_id),
                "category": str(character.get("category", "character")),
                "rarity": int(character.get("rarity", 2)),
                "image": image_path,
            }
        )

    if characters:
        return characters
    return [
        {
            "id": path.stem,
            "name": path.stem,
            "category": "character",
            "rarity": 2,
            "image": path,
        }
        for path in sorted(asset_dir.glob("*.png"))
    ]


def _load_catalog_option_assets(asset_dir: Path) -> list[dict[str, Any]]:
    asset_dir = asset_dir.resolve()
    meta_path = asset_dir / "meta.json"
    options: list[dict[str, Any]] = []
    try:
        catalog = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        catalog = {"options": []}

    for option in catalog.get("options", []):
        if not isinstance(option, dict) or option.get("tier") != "free":
            continue
        image_path = _resolve_character_image(asset_dir, option, subdir="options")
        if image_path is None:
            continue
        option_id = str(option.get("id", image_path.stem)).strip() or image_path.stem
        options.append(
            {
                "id": option_id,
                "name": str(option.get("name_ko") or option_id),
                "category": str(option.get("category", "option")),
                "image": image_path,
            }
        )

    if options:
        return options
    return [
        {
            "id": path.stem,
            "name": path.stem,
            "category": "option",
            "image": path,
        }
        for path in sorted((asset_dir / "options").glob("*.png"))
    ]


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> str:
    text = str(text)
    if draw.textlength(text, font=font) <= max_width:
        return text
    suffix = "..."
    trimmed = text
    while trimmed and draw.textlength(trimmed.rstrip() + suffix, font=font) > max_width:
        trimmed = trimmed[:-1]
    if not trimmed:
        return suffix
    return trimmed.rstrip() + suffix


def _format_audit(report: dict[str, Any]) -> str:
    entrypoints = report["entrypoints"]
    found_entrypoints = ", ".join(name for name, path in entrypoints.items() if path) or "none"
    project_files = report["project_files"]
    found_files = ", ".join(project_files) if project_files else "not found from current checkout"
    readiness = report.get("commercial_readiness") or {}
    return "\n".join(
        [
            "chibi-mcp trust audit",
            f"ok: {report['ok']}",
            f"version: {report['version']}",
            f"telemetry: {report['trust']['telemetry']}",
            f"network_default: {report['trust']['network_default']}",
            f"paid_core_gate: {report['trust']['paid_core_gate']}",
            f"state_file: {report['trust']['state_file']}",
            f"asset_dir: {report['assets']['asset_dir']}",
            f"catalog_count: {report['assets']['catalog_count']}",
            f"option_count: {report['assets']['option_count']}",
            f"free_assets_missing: {report['assets']['free_assets_missing']}",
            f"free_options_missing: {report['assets']['free_options_missing']}",
            f"entrypoints_found: {found_entrypoints}",
            f"project_files_found: {found_files}",
            f"commercial_monetization_enabled: {readiness.get('monetization_enabled')}",
            f"commercial_readiness_missing: {readiness.get('readiness_files_missing', [])}",
        ]
    )


def _format_pack_validation(result: dict[str, Any]) -> str:
    metadata = result.get("metadata") or {}
    lines = [
        f"pack: {result['pack_dir']}",
        f"ok: {result['ok']}",
        f"characters: {len(result['characters'])}",
        f"options: {len(result['options'])}",
    ]
    if metadata:
        lines.append(f"license: {metadata.get('license') or '<missing>'}")
        rights_value = str(metadata.get("source_rights") or "")
        rights_line = "source_rights: present" if not _missing_submission_value(rights_value) else "source_rights: <missing>"
        lines.append(rights_line)
        if metadata.get("submission"):
            lines.append(f"rights_owner: {metadata.get('rights_owner') or '<missing>'}")
            lines.append(f"asset_origin: {metadata.get('asset_origin') or '<missing>'}")
            lines.append(f"permission_scope: {'present' if metadata.get('permission_scope') else '<missing>'}")
            lines.append(f"no_third_party_ip: {metadata.get('no_third_party_ip') is True}")
    for warning in result["warnings"]:
        lines.append(f"warning: {warning}")
    for error in result["errors"]:
        lines.append(f"error: {error}")
    return "\n".join(lines)


def _pack_result(
    pack_dir: Path,
    *,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    characters: list[dict[str, Any]] | None = None,
    options: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors = errors or []
    return {
        "ok": not errors,
        "pack_dir": str(pack_dir),
        "errors": errors,
        "warnings": warnings or [],
        "characters": characters or [],
        "options": options or [],
        "metadata": metadata or {},
    }


def _missing_submission_value(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        not normalized
        or normalized in {"todo", "tbd", "draft", "replace-me"}
        or "replace before public submission" in normalized
        or "replace with" in normalized
        or "explain how" in normalized
    )


def _resolve_character_image(
    pack_dir: Path,
    character: dict[str, Any],
    *,
    errors: list[str] | None = None,
    prefix: str = "character",
    subdir: str = "characters",
) -> Path | None:
    image_value = character.get("image")
    candidates: list[Path] = []
    if image_value:
        explicit = pack_dir / str(image_value)
        resolved = explicit.resolve()
        if not resolved.is_relative_to(pack_dir):
            if errors is not None:
                errors.append(f"{prefix}.image must stay inside the pack directory")
            return None
        candidates.append(explicit)
    character_id = str(character.get("id", "")).strip()
    if character_id:
        candidates.append(pack_dir / f"{character_id}.png")
        candidates.append(pack_dir / subdir / f"{character_id}.png")
    for candidate in candidates:
        resolved = candidate.resolve()
        if candidate.exists() and resolved.is_relative_to(pack_dir):
            return resolved
    return None


def _validate_png(prefix: str, image_path: Path, errors: list[str], warnings: list[str]) -> None:
    if image_path.suffix.lower() != ".png":
        errors.append(f"{prefix}.image must be a PNG: {image_path}")
        return
    try:
        with Image.open(image_path) as image:
            width, height = image.size
            mode = image.mode
    except OSError as exc:
        errors.append(f"{prefix}.image is unreadable: {exc}")
        return
    if width < 128 or height < 128:
        warnings.append(f"{prefix}.image is small ({width}x{height}); 256+ px is recommended")
    if mode not in {"RGBA", "LA", "P"}:
        warnings.append(f"{prefix}.image has mode {mode}; transparent PNG is recommended")


def _find_project_files(relative_paths: list[str]) -> list[str]:
    found: list[str] = []
    roots = [Path.cwd(), *Path(__file__).resolve().parents]
    seen_roots: set[Path] = set()
    for root in roots:
        if root in seen_roots:
            continue
        seen_roots.add(root)
        for relative in relative_paths:
            candidate = root / relative
            if candidate.exists():
                found.append(str(candidate))
    return sorted(set(found))


def _missing_project_files(expected: list[str], found: list[str]) -> list[str]:
    normalized_found = [path.replace("\\", "/") for path in found]
    return [relative for relative in expected if not any(path.endswith(relative) for path in normalized_found)]


def _pick_share_asset(asset_dir: Path, character_id: str | None) -> Path | None:
    if character_id:
        candidate = asset_dir / f"{character_id}.png"
        if candidate.exists():
            return candidate
    for preferred in ("garaetteok_short.png", "white_tteok.png", "mochi.png"):
        candidate = asset_dir / preferred
        if candidate.exists():
            return candidate
    pngs = sorted(asset_dir.glob("*.png"))
    return pngs[0] if pngs else None


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ["DejaVuSans-Bold.ttf", "Arial Bold.ttf"] if bold else ["DejaVuSans.ttf", "Arial.ttf"]
    candidates = [
        *(Path("/usr/share/fonts/truetype/dejavu") / name for name in names),
        *(Path("/System/Library/Fonts/Supplemental") / name for name in names),
        *(Path("C:/Windows/Fonts") / name for name in names),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()
