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

    validate = sub.add_parser("validate", help="Validate a pack directory")
    validate.add_argument("pack_dir", type=Path)
    validate.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    preview = sub.add_parser("preview", help="Write a static HTML pack preview")
    preview.add_argument("pack_dir", type=Path)
    preview.add_argument("--out", type=Path, help="Output HTML path; defaults to <pack_dir>/preview.html")
    preview.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    args = parser.parse_args(argv)
    if args.command == "validate":
        result = validate_pack(args.pack_dir)
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
    parser.add_argument("--character", default=None, help="Character id to render")
    parser.add_argument("--title", default="tteoki coding recap")
    parser.add_argument(
        "--subtitle",
        default="local MCP pet for Claude Code, Codex, and VS Code",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    out = args.out or (Path.home() / ".chibi-mcp" / "share-card.png")
    out = out.expanduser().resolve()
    result = write_share_card(
        out=out,
        character_id=args.character,
        title=args.title,
        subtitle=args.subtitle,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"share_card: {result['path']}")
    return 0 if result["ok"] else 1


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
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            free_assets_missing.append("meta.json")

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
            "free_assets_missing": free_assets_missing,
        },
        "entrypoints": entrypoints,
        "project_files": hook_files,
        "environment": {
            "CHIBI_WS_HOST": os.environ.get("CHIBI_WS_HOST"),
            "CHIBI_WS_PORT": os.environ.get("CHIBI_WS_PORT"),
            "CHIBI_ASSET_DIR": os.environ.get("CHIBI_ASSET_DIR"),
        },
    }
    return report


def validate_pack(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    characters_out: list[dict[str, Any]] = []

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

    characters = catalog.get("characters")
    if not isinstance(characters, list) or not characters:
        return _pack_result(pack_dir, errors=["meta.json must contain a non-empty characters list"])

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
        image_path = _resolve_character_image(pack_dir, character)
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

    return _pack_result(
        pack_dir,
        errors=errors,
        warnings=warnings,
        characters=characters_out,
    )


def write_pack_preview(validation: dict[str, Any], out: Path) -> None:
    pack_dir = Path(validation["pack_dir"])
    out.parent.mkdir(parents=True, exist_ok=True)
    cards = []
    for character in validation["characters"]:
        image_path = character.get("image")
        src = ""
        if image_path:
            src = os.path.relpath(image_path, out.parent)
            media = f'  <img src="{html.escape(src)}" alt="{html.escape(character["id"])}">'
        else:
            media = '  <div class="placeholder">???</div>'
        cards.append(
            "\n".join(
                [
                    '<article class="card">',
                    media,
                    f'  <h2>{html.escape(character["name"] or character["id"])}</h2>',
                    (
                        "  <p>"
                        f'{html.escape(character["id"])} · '
                        f'{html.escape(character["category"])} · '
                        f'★{int(character["rarity"])}'
                        "</p>"
                    ),
                    "</article>",
                ]
            )
        )
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
</header>
<main>
{body}
</main>
</html>
"""
    out.write_text(html_doc, encoding="utf-8")


def write_share_card(
    *,
    out: Path,
    character_id: str | None = None,
    title: str,
    subtitle: str,
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

    width = height = 1080
    image = Image.new("RGB", (width, height), "#fff7ed")
    draw = ImageDraw.Draw(image)
    title_font = _load_font(68, bold=True)
    subtitle_font = _load_font(32)
    metric_font = _load_font(30, bold=True)
    small_font = _load_font(24)

    draw.rounded_rectangle((58, 58, 1022, 1022), radius=36, fill="#ffffff", outline="#fed7aa", width=4)
    draw.rounded_rectangle((86, 86, 994, 188), radius=22, fill="#0f766e")
    draw.text((120, 106), title[:48], fill="#ffffff", font=title_font)
    draw.text((122, 200), subtitle[:82], fill="#475569", font=subtitle_font)

    draw.ellipse((280, 285, 800, 805), fill="#ffedd5", outline="#f59e0b", width=6)
    with Image.open(asset_path) as pet:
        pet = pet.convert("RGBA")
        pet.thumbnail((430, 430), Image.Resampling.LANCZOS)
        x = (width - pet.width) // 2
        y = 350 + (360 - pet.height) // 2
        image.paste(pet, (x, y), pet)

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
        draw.text((x0 + 18, 878), value[:12], fill="#1f2937", font=metric_font)
        x0 += 215

    footer = f"chibi-mcp {__version__} | no telemetry | localhost-first"
    draw.text((120, 956), footer, fill="#64748b", font=small_font)
    image.save(out, "PNG")
    return {
        "ok": True,
        "path": str(out),
        "character_asset": str(asset_path),
        "mood": mood,
        "calls": counters["calls_total"],
        "slices": counters["slices_today"],
    }


def _format_audit(report: dict[str, Any]) -> str:
    entrypoints = report["entrypoints"]
    found_entrypoints = ", ".join(name for name, path in entrypoints.items() if path) or "none"
    project_files = report["project_files"]
    found_files = ", ".join(project_files) if project_files else "not found from current checkout"
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
            f"free_assets_missing: {report['assets']['free_assets_missing']}",
            f"entrypoints_found: {found_entrypoints}",
            f"project_files_found: {found_files}",
        ]
    )


def _format_pack_validation(result: dict[str, Any]) -> str:
    lines = [
        f"pack: {result['pack_dir']}",
        f"ok: {result['ok']}",
        f"characters: {len(result['characters'])}",
    ]
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
) -> dict[str, Any]:
    errors = errors or []
    return {
        "ok": not errors,
        "pack_dir": str(pack_dir),
        "errors": errors,
        "warnings": warnings or [],
        "characters": characters or [],
    }


def _resolve_character_image(pack_dir: Path, character: dict[str, Any]) -> Path | None:
    image_value = character.get("image")
    candidates: list[Path] = []
    if image_value:
        candidates.append(pack_dir / str(image_value))
    character_id = str(character.get("id", "")).strip()
    if character_id:
        candidates.append(pack_dir / f"{character_id}.png")
        candidates.append(pack_dir / "characters" / f"{character_id}.png")
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
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
