# chibi-mcp

> tteoki — Korean rice cake desktop character that visualizes your Claude Code session.

A small **MCP server + cross-platform desktop pet**. tteoki sits in the corner of your screen as a 가래떡 (Korean rice cake stick) and reacts to your system state and Claude tool calls. Every 10 Claude calls, it gets sliced into a piece on the cutting board. Syrup (조청) drips faster when your CPU spikes.

**Free, MIT, no telemetry.**

## Quick start

```bash
# 1. Install the MCP server
pip install chibi-mcp     # (PyPI release pending)

# 2. Register with Claude Code
claude mcp add chibi -- chibi-mcp

# 3. Download the desktop app from Releases and launch it
```

The desktop app connects to `ws://127.0.0.1:9876` and shows tteoki.

## Features (v0.1)

- 🍡 Emoji-style garaetteok character (Korean rice cake stick)
- 😌 7 moods (calm / happy / panting / drowsy / lonely / surprised / joyful) driven by CPU·RAM·battery·idle time
- 🍯 Syrup drip animation, cadence based on CPU load
- 🔪 Slice motion every N Claude tool calls (default 10) — pieces stack on a cutting board
- 💬 `pet_say()` MCP tool for speech bubbles
- 🆓 100% free, MIT licensed
- 🇰🇷 Korean rice cake (떡) series planned — illustrator commissions after first traction

## MCP tools

| Tool | Description |
|---|---|
| `get_pet_state` | Returns mood, system metrics, counters, session time |
| `pet_say(text)` | Make tteoki say something in a speech bubble |
| `slice_now` | Manually trigger a slice |
| `set_slice_interval(n)` | Change auto-slice cadence (default 10) |

## Architecture

```
[Claude Code / Codex]
       │ MCP stdio
       ▼
[chibi-mcp server]  ←──── psutil ──── CPU / RAM / battery
       │
       │ ws://127.0.0.1:9876
       ▼
[chibi-mcp desktop]  (Tauri, transparent always-on-top)
       │
       └─ renders tteoki SVG with mood / slice / drip
```

## Repo layout

- `server/` — Python MCP server (FastMCP), tests
- `desktop/` — Tauri 2.x app (Rust shell + HTML/CSS/JS frontend)
- `desktop/src/characters/<id>/` — character art slot (swap files to change look)
- `.github/workflows/build.yml` — CI: server tests + Tauri builds for macOS/Windows/Linux

See [`SPEC.md`](SPEC.md), [`CHARACTER_DESIGN.md`](CHARACTER_DESIGN.md), [`STYLE_GUIDE.md`](STYLE_GUIDE.md), [`PROCESS.md`](PROCESS.md) for project decisions and rationale.

## Sources & inspirations

- 한국 아티잔 키캡 group buy / raffle 모델 — [SMKX](https://www.klc-smkx.com/), [Artisan Keycap History](https://artisancollector.com/artisan-keycap-history/)
- 슬라임 ASMR (시청각 만족감·인스타그래머블) — [TikTok #slimeasmr](https://www.tiktok.com/tag/slimeasmr)
- chibi · kawaii 디자인 — [chibi.pics](https://www.chibi.pics/blog/what-is-chibi-why-its-style-is-so-popular)
- 한국 2025 마스코트 트렌드 — [캐릿](https://www.careet.net/1853)

## Disclaimer

chibi-mcp is an independent open-source project. It implements the standard
[Model Context Protocol](https://modelcontextprotocol.io/) and is **not affiliated with or endorsed by Anthropic**.
"Claude" and "Claude Code" are trademarks of Anthropic.

The desktop app reads local system metrics (CPU/RAM/battery) via psutil and
communicates only with `localhost`. No data leaves your machine.

## License

MIT
