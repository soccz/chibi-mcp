# chibi-mcp (server)

MCP server for **chibi** — a local desktop character that visualizes Claude Code or Codex session state.

> Code is MIT; bundled official artwork has separate terms (see `OFFICIAL_ASSET_TERMS.md`). `chibi` and `chibi-mcp` are unregistered trademarks of the project.

The server has two jobs running together in one process:
1. **MCP server (stdio)** — Claude Code / Codex calls these tools to interact with chibi.
2. **WebSocket server (`ws://127.0.0.1:9876`)** — pushes state snapshots and events to the desktop app.

## Install from GitHub

```bash
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
```

Upgrade or refresh an existing install:

```bash
pipx uninstall chibi-mcp || true
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
```

(For local development from this repo, see "Develop" below.)

## Register with Claude Code or Codex

```bash
claude mcp add chibi -- chibi-mcp
codex mcp add chibi -- chibi-mcp
```

Then call `open_pet_window` from the client — it launches the floating chibi window and connects to the local WebSocket.

## CLI checks

```bash
chibi-mcp --check      # verify packaged assets + local runtime support
chibi-mcp --doctor     # verify local runtime + Claude/Codex/VS Code client state
chibi-mcp --open       # open the window and auto-start ws-only if needed
chibi-mcp --version
chibi-mcp --ws-only    # development: run only ws://127.0.0.1:9876
chibi-audit            # local trust report for team/security review
chibi-pack init ./my-pack
chibi-pack validate ./my-pack
chibi-pack preview ./my-pack
chibi-share --out share-card.png
chibi-share --preset social-preview --out social-preview.png
chibi-share --preset lineup --out starter-lineup.png
chibi-share --preset options --out option-showcase.png
```

In `--doctor`, `ok: true` means the local server/runtime is healthy, while
`ready: true` means the checked Claude, Codex, and VS Code paths are also ready.

## MCP tools

| Tool | Description |
|---|---|
| `get_pet_state` | Returns mood, system metrics (CPU/RAM/battery), counters, timing. Counts as a Claude interaction (may trigger a milestone event every N calls). |
| `pet_say(text)` | Make chibi say something in a speech bubble. |
| `slice_now` | Force a milestone animation immediately. |
| `set_slice_interval(n)` | Change how often (every N Claude tool calls) the milestone animation fires. Default: 10. |
| `get_options` | List free visual option layers such as honey, beads, sprinkles, powder, sesame, petals, resin, and sauce. |
| `set_active_options([ids])` / `clear_active_options` | Apply or clear up to 3 free option layers. |

## WebSocket protocol (server → desktop)

JSON messages broadcast to all connected desktop clients:

```jsonc
{ "type": "state",
  "payload": {
    "mood": "calm | panting | drowsy | lonely | happy | surprised | joyful",
    "system": { "cpu_percent": 12.3, "ram_percent": 51.2, "battery_percent": 84.0, "battery_plugged": false },
    "counters": { "calls_total": 23, "calls_since_slice": 3, "slice_interval": 10, "slices_today": 2 },
    "timing": { "session_seconds": 1842, "idle_seconds": 7 }
  }
}

{ "type": "say", "text": "오늘도 같이 코딩!" }

{ "type": "slice" }
```

State is pushed every 2 seconds. `say` and milestone events are pushed on demand.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `CHIBI_WS_HOST` | `127.0.0.1` | WebSocket bind host |
| `CHIBI_WS_PORT` | `9876` | WebSocket bind port |
| `CHIBI_LOG_LEVEL` | `INFO` | Logging level |
| `CHIBI_EXPERIMENTAL_MACOS_PYOBJC_TRANSPARENCY` | ignored | Legacy flag. PyObjC transparency is disabled; macOS always uses the stable Tk panel. |

## Develop

```bash
cd server
python3.12 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest
```

Run directly (without an MCP client) for the WebSocket side only:

```bash
CHIBI_LOG_LEVEL=DEBUG python -m chibi_mcp
```

The stdio MCP side will wait for a client on stdin/stdout, so to test the WebSocket alone, connect a simple ws client to `ws://localhost:9876` while the process runs.

## Design notes

- **Counter resets only when the process restarts** — intentional "today's-work" scope.
- **All metrics are local** — no network calls, no telemetry, no accounts.
- **Milestone trigger is Claude-call-based** (not wall-clock) — measures actual work, not just time sitting.

See `../SPEC.md` and `../CHARACTER_DESIGN.md` for the broader project context.
