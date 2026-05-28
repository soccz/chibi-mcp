# chibi-mcp

> 치비 (chibi) — Korean rice cake desktop pet for Claude Code, shipped as a Claude Code plugin.
>
> Gacha-collect squishy characters (떡·과일·치즈·만두). They react to your coding session and get sliced every N tool calls.
>
> **100% free, MIT, no telemetry, OS-agnostic** — runs wherever Claude Code runs.

## Install (two lines)

```bash
pipx install chibi-mcp                                # 1. server binary on PATH
```

Then inside Claude Code:

```
/plugin marketplace add soccz/chibi-mcp
/plugin install chibi@chibi-mcp
```

(First time only — Claude Code prompts you to enable the plugin's MCP server. Type `y`.)

That's it. Now ask Claude:

> `/chibi`
> "내 치비 보여줘"
> "뽑기 한 번"
> "보관함 열어"

## What you get

- 🍡 **8 starter characters** released now (white_tteok, garaetteok_short, baekseolgi, mochi, green_grape, melon, cheddar, toast — all ★★)
- 🔒 **21 more characters coming later** including the ★★★★★ rainbow series, all 떡 varieties, cheeses, fruits, mandu. Catalog shows them as "???" placeholders until release.
- 🎟 **Gacha pulls** — weighted by rarity (1% / 5% / 24% / 70%)
- 📦 **Collection** — see what you've got, switch active character, rename them
- ⏱ **Slice cycle** — every N Claude tool calls (default 10), your pet gets sliced
- 🎭 **Mood** driven by CPU·RAM·battery·idle (panting / drowsy / lonely / happy / surprised / joyful / calm)

> v0.4 is the open-source freemium baseline. The remaining 21 characters will be released alongside a Pro tier later; pricing and release date TBD.

## MCP tools

| Tool | Description |
|---|---|
| `get_pet_state` | mood + system metrics + counters + active character |
| `pet_say(text)` | Speech bubble (text sanitized to 200 chars) |
| `slice_now` | Force a slice event |
| `set_slice_interval(n)` | Change slice cadence (default 10) |

## Layout (for contributors)

```
chibi-mcp/
├── .claude-plugin/plugin.json   # plugin manifest
├── .mcp.json                    # stdio MCP server spec
├── skills/chibi/SKILL.md        # behaviour guide for Claude
├── commands/chibi.md            # /chibi slash command
├── assets/                      # 29 PNG + meta.json
├── server/                      # Python MCP server (PyPI: chibi-mcp)
└── server-rs/                   # (optional) Rust rewrite, same protocol
```

## Deprecated paths

The earlier v0.1/v0.2 lineage included:

- **Tauri desktop app** (`desktop/`) — required macOS code signing and per-platform builds. Removed in v0.3 in favor of the plugin model.
- **VS Code extension** (`vscode-ext/`) — folder retained for reference but not actively published. The plugin already covers the inline-chat use case.

Both folders are kept in the repo for archival reasons; they are not part of v0.3 install.

## Not affiliated with Anthropic

chibi-mcp is an independent open-source project. The `claude` CLI and the MCP protocol it implements are tools by Anthropic; this project is not endorsed by them.

## License

MIT.
