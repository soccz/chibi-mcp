# chibi-mcp (server)

MCP server for **tteoki** — a Korean rice cake (가래떡) desktop character that visualizes Claude Code or Codex session state.

The server has two jobs running together in one process:
1. **MCP server (stdio)** — Claude Code / Codex calls these tools to interact with tteoki.
2. **WebSocket server (`ws://127.0.0.1:9876`)** — pushes state snapshots and events to the desktop app.

## Install from GitHub

```bash
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
```

PyPI install, once published:

```bash
pipx install chibi-mcp
```

(For local development from this repo, see "Develop" below.)

## Register with Claude Code or Codex

```bash
claude mcp add chibi -- chibi-mcp
codex mcp add chibi -- chibi-mcp
```

Then call `open_pet_window` from the client — it launches the floating tteoki window and connects to the local WebSocket.

## CLI checks

```bash
chibi-mcp --check      # verify packaged assets + local runtime support
chibi-mcp --version
chibi-mcp --ws-only    # development: run only ws://127.0.0.1:9876
```

## MCP tools

| Tool | Description |
|---|---|
| `get_pet_state` | Returns mood, system metrics (CPU/RAM/battery), counters, timing. Counts as a Claude interaction (may trigger a slice every N calls). |
| `pet_say(text)` | Make tteoki say something in a speech bubble. |
| `slice_now` | Force a slice (resets the lengthen cycle, fires a slice event). |
| `set_slice_interval(n)` | Change how often (every N Claude tool calls) the auto-slice fires. Default: 10. |

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

State is pushed every 2 seconds. `say` and `slice` are pushed on demand.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `CHIBI_WS_HOST` | `127.0.0.1` | WebSocket bind host |
| `CHIBI_WS_PORT` | `9876` | WebSocket bind port |
| `CHIBI_LOG_LEVEL` | `INFO` | Logging level |

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
- **Slice trigger is Claude-call-based** (not wall-clock) — measures actual work, not just time sitting.

See `../SPEC.md` and `../CHARACTER_DESIGN.md` for the broader project context.
