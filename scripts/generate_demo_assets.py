#!/usr/bin/env python3
"""Generate public demo GIF and client preview screenshots from local assets."""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = Path(os.environ.get("CHIBI_DEMO_OUT_ROOT", ROOT)).resolve()
ASSET_DIR = ROOT / "server" / "chibi_mcp" / "assets"
SCREENSHOT_DIR = OUT_ROOT / "docs" / "screenshots"
DEMO_GIF = OUT_ROOT / "docs" / "demo.gif"


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: str, outline: str | None = None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_fit(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_width: int) -> str:
    if draw.textlength(text, font=fnt) <= max_width:
        return text
    clipped = text
    while clipped and draw.textlength(f"{clipped}...", font=fnt) > max_width:
        clipped = clipped[:-1]
    return f"{clipped}..." if clipped else "..."


def paste_asset(canvas: Image.Image, asset_name: str, center: tuple[int, int], max_side: int, *, mood: str = "calm", options: tuple[str, ...] = ()) -> None:
    img = Image.open(ASSET_DIR / asset_name).convert("RGBA")
    if mood == "happy":
        img = ImageEnhance.Brightness(img).enhance(1.16)
        img = ImageEnhance.Color(img).enhance(1.18)
    elif mood == "panting":
        tint = Image.new("RGBA", img.size, (255, 110, 100, 58))
        img = Image.alpha_composite(img, tint)
    elif mood == "drowsy":
        img = ImageEnhance.Brightness(img).enhance(0.78)
        img = ImageEnhance.Color(img).enhance(0.82)
    for option_id in options:
        option = Image.open(ASSET_DIR / "options" / f"{option_id}.png").convert("RGBA")
        option = option.resize(img.size, Image.Resampling.LANCZOS)
        img.alpha_composite(option)
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    x = center[0] - img.width // 2
    y = center[1] - img.height // 2
    canvas.alpha_composite(img, (x, y))


def draw_pet_window(
    canvas: Image.Image,
    xy: tuple[int, int],
    *,
    scale: float = 1.0,
    mood: str = "happy",
    calls: int = 7,
    cpu: int = 42,
    battery: int = 78,
    asset: str = "mochi.png",
) -> None:
    draw = ImageDraw.Draw(canvas)
    x, y = xy
    w = round(360 * scale)
    h = round(520 * scale)
    rounded(draw, (x, y, x + w, y + h), round(28 * scale), "#fff8ef", "#dbc3aa", max(1, round(2 * scale)))
    rounded(draw, (x, y, x + w, y + round(58 * scale)), round(26 * scale), "#f7efe5", "#dbc3aa", max(1, round(1 * scale)))
    for idx, color in enumerate(("#ff5f57", "#ffbd2e", "#28c840")):
        cx = x + round((30 + idx * 34) * scale)
        cy = y + round(29 * scale)
        draw.ellipse((cx - round(11 * scale), cy - round(11 * scale), cx + round(11 * scale), cy + round(11 * scale)), fill=color, outline="#8d6d62")
    draw.text((x + round(132 * scale), y + round(17 * scale)), "chibi", fill="#4b4540", font=font(max(13, round(20 * scale)), bold=True))

    glow = {"happy": "#fff0b8", "panting": "#ffe0db", "drowsy": "#e6e3ff", "calm": "#ffe8f0"}.get(mood, "#ffe8f0")
    draw.ellipse((x + round(78 * scale), y + round(94 * scale), x + round(282 * scale), y + round(306 * scale)), fill=glow)
    draw.ellipse((x + round(102 * scale), y + round(300 * scale), x + round(258 * scale), y + round(322 * scale)), fill="#d8c1aa")
    paste_asset(canvas, asset, (x + w // 2, y + round(206 * scale)), round(190 * scale), mood=mood, options=("honey_glaze", "resin_stars"))

    card = (x + round(24 * scale), y + round(338 * scale), x + w - round(24 * scale), y + round(468 * scale))
    rounded(draw, card, round(18 * scale), "#fffdf8", "#efd8bf", max(1, round(2 * scale)))
    draw.text((card[0] + round(18 * scale), card[1] + round(14 * scale)), "Mochi Chibi", fill="#2a211a", font=font(max(12, round(18 * scale)), bold=True))
    draw.text((card[2] - round(112 * scale), card[1] + round(16 * scale)), "★★★☆☆", fill="#5f4d3f", font=font(max(10, round(14 * scale)), bold=True))
    rounded(draw, (card[0] + round(18 * scale), card[1] + round(44 * scale), card[0] + round(92 * scale), card[1] + round(70 * scale)), round(12 * scale), "#ffe5ec", "#ffc4d5")
    draw.text((card[0] + round(30 * scale), card[1] + round(49 * scale)), "happy", fill="#2a211a", font=font(max(8, round(11 * scale)), bold=True))
    bar_x = card[0] + round(108 * scale)
    bar_y = card[1] + round(58 * scale)
    rounded(draw, (bar_x, bar_y, card[2] - round(22 * scale), bar_y + round(8 * scale)), round(5 * scale), "#ead7c3")
    fill = bar_x + round((card[2] - round(22 * scale) - bar_x) * min(1.0, calls / 10))
    rounded(draw, (bar_x, bar_y, fill, bar_y + round(8 * scale)), round(5 * scale), "#55bd83" if cpu < 80 else "#f05f4b")

    labels = (("CPU", f"{cpu}%"), ("RAM", "48%"), ("BAT", f"{battery}%"))
    for idx, (label, value) in enumerate(labels):
        bx = card[0] + round((18 + idx * 94) * scale)
        by = card[1] + round(84 * scale)
        rounded(draw, (bx, by, bx + round(82 * scale), by + round(28 * scale)), round(10 * scale), "#edfdf4", "#b7e4c7")
        draw.text((bx + round(8 * scale), by + round(7 * scale)), label, fill="#6f5d50", font=font(max(7, round(9 * scale)), bold=True))
        draw.text((bx + round(42 * scale), by + round(7 * scale)), value, fill="#2a211a", font=font(max(7, round(9 * scale)), bold=True))


def terminal_lines(draw: ImageDraw.ImageDraw, x: int, y: int, lines: list[tuple[str, str]], *, line_h: int = 36) -> None:
    mono = font(24)
    for idx, (prompt, text) in enumerate(lines):
        yy = y + idx * line_h
        draw.text((x, yy), prompt, fill="#55bd83", font=mono)
        draw.text((x + 32, yy), text, fill="#e5eef8", font=mono)


def mac_frame(title: str) -> Image.Image:
    image = Image.new("RGB", (1600, 900), "#f5efe7")
    draw = ImageDraw.Draw(image)
    rounded(draw, (70, 58, 1530, 842), 26, "#fffaf2", "#dfc3a6", 3)
    rounded(draw, (70, 58, 1530, 122), 24, "#f3e9dc", "#dfc3a6", 2)
    for idx, color in enumerate(("#ff5f57", "#ffbd2e", "#28c840")):
        draw.ellipse((104 + idx * 34, 82, 126 + idx * 34, 104), fill=color, outline="#93695d")
    draw.text((202, 80), title, fill="#4b4540", font=font(26, bold=True))
    return image


def draw_claude_code() -> None:
    image = mac_frame("Claude Code - chibi-mcp")
    draw = ImageDraw.Draw(image)
    rounded(draw, (110, 160, 990, 790), 18, "#111827", "#263244", 2)
    terminal_lines(
        draw,
        150,
        208,
        [
            ("$", "bash <(curl -fsSL .../scripts/install-claude.sh)"),
            ("$", "Claude install complete. Restart, then run: /chibi-mcp:chibi"),
            (">", "/chibi-mcp:chibi"),
            ("", "Mochi Chibi ★★★ - happy"),
            (">", "/chibi-mcp:chibi pull"),
            ("", "Green Grape Chibi ★★ came home."),
        ],
    )
    rgba = image.convert("RGBA")
    draw_pet_window(rgba, (1070, 180), mood="happy", calls=7, cpu=42, battery=78)
    image = rgba.convert("RGB")
    image.save(SCREENSHOT_DIR / "claude-code.png")


def draw_codex_terminal() -> None:
    image = mac_frame("Codex terminal - local chibi")
    draw = ImageDraw.Draw(image)
    rounded(draw, (110, 160, 1010, 790), 18, "#0f172a", "#334155", 2)
    terminal_lines(
        draw,
        150,
        210,
        [
            ("$", "bash <(curl -fsSL .../scripts/install-codex.sh)"),
            ("$", "chibi-mcp --check"),
            ("", '{"ok": true, "version": "1.4.39", "telemetry": "none"}'),
            (">", "/chibi-mcp:chibi inventory"),
            ("", "tickets 1 | owned 4/8 | localhost-first"),
        ],
    )
    rgba = image.convert("RGBA")
    draw_pet_window(rgba, (1090, 185), mood="panting", calls=9, cpu=84, battery=63, asset="toast.png")
    image = rgba.convert("RGB")
    image.save(SCREENSHOT_DIR / "codex-terminal.png")


def draw_vscode_sidebar() -> None:
    image = Image.new("RGB", (1600, 900), "#0f172a")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 72, 900), fill="#111827")
    draw.rectangle((72, 0, 390, 900), fill="#172033")
    draw.rectangle((390, 0, 1600, 900), fill="#0b1020")
    draw.text((104, 42), "CHIBI-MCP", fill="#cbd5e1", font=font(24, bold=True))
    rounded(draw, (104, 92, 352, 174), 12, "#243247", "#35445c", 2)
    draw.text((128, 114), "Mochi Chibi", fill="#f8fafc", font=font(22, bold=True))
    draw.text((128, 144), "happy | calls 7/10", fill="#94a3b8", font=font(18))
    rounded(draw, (104, 202, 352, 438), 14, "#fff8ef", "#dfc3a6", 2)
    rgba = image.convert("RGBA")
    paste_asset(rgba, "mochi.png", (228, 314), 150, mood="happy", options=("honey_glaze",))
    image = rgba.convert("RGB")
    draw = ImageDraw.Draw(image)
    for idx, (label, value, color) in enumerate((("CPU", "42%", "#55bd83"), ("RAM", "48%", "#55bd83"), ("BAT", "78%", "#55bd83"))):
        y = 488 + idx * 62
        rounded(draw, (104, y, 352, y + 42), 10, "#1e293b", "#334155", 1)
        draw.text((126, y + 11), label, fill="#cbd5e1", font=font(17, bold=True))
        draw.rectangle((182, y + 18, 324, y + 25), fill="#334155")
        draw.rectangle((182, y + 18, 182 + round(142 * int(value[:-1]) / 100), y + 25), fill=color)
        draw.text((286, y + 10), value, fill="#e2e8f0", font=font(17, bold=True))
    draw.text((438, 50), "src/session.ts", fill="#cbd5e1", font=font(24))
    for idx, line in enumerate(
        [
            "export async function runCodingSession() {",
            "  await tools.call('edit');",
            "  await tools.call('test');",
            "  chibi.react('milestone');",
            "}",
        ]
    ):
        draw.text((458, 128 + idx * 42), line, fill="#dbeafe" if idx == 3 else "#e5e7eb", font=font(24))
    rounded(draw, (1040, 172, 1410, 694), 28, "#fff8ef", "#dfc3a6", 3)
    rgba = image.convert("RGBA")
    draw_pet_window(rgba, (1048, 178), mood="happy", calls=7, cpu=42, battery=78)
    image = rgba.convert("RGB")
    image.save(SCREENSHOT_DIR / "vscode-sidebar.png")


def draw_demo_gif() -> None:
    frames: list[Image.Image] = []
    moods = ["calm", "happy", "panting", "drowsy"]
    for idx in range(24):
        mood = moods[(idx // 6) % len(moods)]
        cpu = [32, 44, 84, 38][(idx // 6) % len(moods)]
        battery = [88, 78, 62, 16][(idx // 6) % len(moods)]
        image = Image.new("RGB", (960, 540), "#fff7ed")
        draw = ImageDraw.Draw(image)
        draw.text((58, 46), "chibi-mcp", fill="#0f766e", font=font(56, bold=True))
        draw.text((62, 112), "local coding pet for Claude Code, Codex, and VS Code", fill="#475569", font=font(24))
        rounded(draw, (60, 176, 500, 452), 22, "#111827", "#263244", 2)
        terminal_lines(
            draw,
            92,
            212,
            [
                (">", "/chibi-mcp:chibi"),
                ("", f"mood {mood} | CPU {cpu}% | BAT {battery}%"),
                (">", "/chibi-mcp:chibi pull"),
                ("", "new chibi joined the collection"),
            ],
            line_h=42,
        )
        bob = int(math.sin(idx / 24 * math.tau * 2) * 8)
        rgba = image.convert("RGBA")
        draw_pet_window(rgba, (570, 46 + bob), scale=0.9, mood=mood, calls=(idx % 10) + 1, cpu=cpu, battery=battery)
        frames.append(rgba.convert("P", palette=Image.ADAPTIVE, colors=96))
    DEMO_GIF.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(DEMO_GIF, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)


def main() -> int:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    draw_claude_code()
    draw_codex_terminal()
    draw_vscode_sidebar()
    draw_demo_gif()
    for path in (
        DEMO_GIF,
        SCREENSHOT_DIR / "claude-code.png",
        SCREENSHOT_DIR / "codex-terminal.png",
        SCREENSHOT_DIR / "vscode-sidebar.png",
    ):
        print(f"demo_asset: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
