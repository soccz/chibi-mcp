# Changelog

All notable changes to chibi-mcp. Format: keep-a-changelog inspired, but condensed.

## v1.3.2 — 2026-05-29

Audit follow-up polish.

- WS reconnect: exponential backoff (1s → 30s cap, ×1.7) instead of fixed 2s; resets on successful connect.
- WS drops now log at debug (json parse error vs queue full with current size) instead of bare suppress.
- `MOOD_FILTERS` schema documented inline.
- `skills/chibi/SKILL.md`: documents the exact `pull_gacha` success / failure response shape; clarifies catalog vs inventory roles.
- `tests/test_gacha.py`: +2 regression tests for the v1.3.1 defer-save refactor.
- README "Client Paths" reframed to match the actual Python tk window path (Tauri marked archived).

## v1.3.1 — 2026-05-29

Final review pass — 12 confirmed fixes from a 20-loop multi-agent audit (110 subagents, 50 raw → 28 confirmed).

- VSCode gacha race: `_gachaInProgress` guard.
- `state.save()` now snapshots under the lock and writes outside it.
- `get_catalog` / `_check` JSON & I/O exception handling.
- `open_pet_window` log_fh always closed; subprocess inherits the fd.
- character_id path-traversal hardening (`^[a-z][a-z0-9_]{0,40}$` regex + `asset_root not in image_path.parents` check).
- Window `after()` callbacks tracked & cancelled on shutdown.
- `get_state` singleton init lock (TOCTOU).
- `CHIBI_WS_PORT` safe parsing (warn + fall back to default on invalid).
- `bin/chibi-react.sh` POSIX char class removed.
- Cohesion: removed duplicate `_seconds_until_local_midnight`; one canonical helper in state.py.

## v1.3.0 — 2026-05-29

Host-agnostic chibi-say bridge.

- VSCode extension 0.5.0: spawns `chibi-say` on save / task start·end / debug start·terminate. Setting `chibiMcp.sayBridge.enabled`.
- README "Anywhere" section: git post-commit, Makefile, CI, zsh `precmd` examples.
- MCP tools table refreshed (13 tools).

## v1.2.0 — 2026-05-29

Claude Code hooks bridge, PyObjC transparency, idle bubbles, mood variant loader.

- `ws_server` handles inbound `{type:say,text:...}`; new `chibi-say` & `chibi-check` CLIs.
- `hooks/hooks.json` + `bin/chibi-react.sh` for PreToolUse / PostToolUse.
- PyObjC real transparency on darwin (`pyobjc-framework-Cocoa` conditional dep).
- Per-mood PNG variant loader (`<id>_<mood>.png` if shipped).
- Idle bubbles every 4–7 minutes.

## v1.1.0 — 2026-05-28

Frameless transparent window, idle bob, sound effects.

- `overrideredirect(True)` — no title bar.
- macOS `-transparent` + `systemTransparent` bg + `-alpha 0.96` fallback.
- Canvas-based render; bob via `canvas.coords`; ±4px / 0.6Hz.
- Procedurally-generated wavs (`bubble.wav`, `slice.wav`) at `~/.chibi-mcp/sounds/`. Playback via afplay / paplay·aplay / winsound.

## v1.0.0 — 2026-05-28

Live updates, real gacha, mood-tinted transparent window.

- Persistence at `~/.chibi-mcp/state.json` (inventory, tickets, active char, last free pull, total pulls).
- `pull_gacha`, `get_inventory`, `set_active_character`, `rename_character`, `add_ticket` MCP tools.
- Window subscribes to local WS for live state / slice / say events.
- Mood filter (brightness · saturation · tint) per Mood — 7 expressions from one base PNG.
- Speech bubble (4s) below the character.

## v0.5.0 — 2026-05-28

Floating tk window.

- `open_pet_window` / `close_pet_window` spawn a detached Python subprocess.
- `~/.chibi-mcp/window.pid` tracking.
- Mood label, drag, dbl-click squish, Esc / Cmd-W / right-click to close.

## v0.4.x — 2026-05-28

- v0.4.0: Freemium baseline — 8 free / 21 Pro placeholders, HMAC license verification (`license.py`), `get_license_status`, `get_catalog` tier filter, 37 tests.
- v0.4.1: 21 placeholder PNGs removed from the public repo (kept local-only).
- v0.4.2: `chibi` rebrand, `.claude-plugin/marketplace.json`, `/chibi` slash command.

## v0.3.0 — 2026-05-28

Reborn as a Claude Code plugin (`.claude-plugin/`, `skills/`, `.mcp.json`). Tauri desktop app moved to archival.

## v0.1.x / v0.2.x — earlier

Tauri attempts (`desktop/`). Deprecated mid-project due to macOS signing pain; kept under `desktop/` for reference.
