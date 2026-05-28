"""FastMCP server — tools Claude Code calls to interact with tteoki."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

from fastmcp import FastMCP

from .state import get_state
from .ws_server import get_broadcaster

log = logging.getLogger(__name__)

# Tracks the spawned tk window process across MCP calls. A PID file persists
# across MCP server restarts (the window is a detached subprocess).
_WINDOW_PID_FILE = Path.home() / ".chibi-mcp" / "window.pid"

mcp = FastMCP("chibi-mcp")


# Limits for incoming MCP tool inputs. Claude may emit large strings — we
# defend the desktop UI from rendering pathological payloads.
MAX_SAY_LEN = 200
SAY_CONTROL_CHARS = "".join(chr(c) for c in range(32) if c not in (9, 10))  # keep tab+LF

# Holds references to fire-and-forget asyncio tasks so they aren't garbage
# collected mid-flight. (RUF006 — Python may drop tasks that have no strong
# reference, silently dropping the WebSocket broadcast.)
_PENDING_TASKS: set[asyncio.Task] = set()


def _fire_and_forget(coro) -> bool:
    """Schedule `coro` on the running loop, keep a hard reference until done.

    Returns True if scheduled, False if there's no running loop in the current
    thread (which means MCP is being called synchronously without an event loop).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    task = loop.create_task(coro)
    _PENDING_TASKS.add(task)
    task.add_done_callback(_PENDING_TASKS.discard)
    return True


def _sanitize_say(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    # Drop control characters (except tab and newline)
    cleaned = text.translate({ord(c): None for c in SAY_CONTROL_CHARS})
    # Collapse to single line for speech bubble
    cleaned = cleaned.replace("\r", " ").replace("\n", " ").strip()
    if len(cleaned) > MAX_SAY_LEN:
        cleaned = cleaned[: MAX_SAY_LEN - 1] + "…"
    return cleaned


def _record_call_and_maybe_slice(force_slice: bool = False) -> dict:
    """Increment counter; if slice milestone hit, broadcast a slice event."""
    state = get_state()
    result = state.record_call(force_slice=force_slice)
    if result["sliced"]:
        broadcaster = get_broadcaster()
        scheduled = _fire_and_forget(broadcaster.broadcast({"type": "slice"}))
        if not scheduled:
            log.debug("slice event skipped (no running loop)")
    return result


@mcp.tool()
def get_pet_state() -> dict:
    """Return tteoki's current state: mood, system metrics, counters, timing.

    The desktop app reads this to render the character. Calling this tool
    counts as a Claude interaction and may trigger a slice every N calls.
    """
    counter = _record_call_and_maybe_slice()
    state = get_state()
    snapshot = state.snapshot()
    snapshot["last_call_result"] = counter
    return snapshot


@mcp.tool()
def pet_say(text: str) -> dict:
    """Make tteoki say something via a speech bubble in the desktop app.

    Args:
        text: short message (≤ 200 chars; longer text is truncated with "…").
              Control characters and newlines are stripped to keep the bubble
              renderable.

    Returns:
        Confirmation dict with the sanitized text and broadcast status.
    """
    safe = _sanitize_say(text)
    counter = _record_call_and_maybe_slice()

    broadcaster = get_broadcaster()
    broadcasted = _fire_and_forget(broadcaster.broadcast({"type": "say", "text": safe}))

    return {
        "spoken": safe,
        "broadcasted": broadcasted,
        "counter": counter,
    }


@mcp.tool()
def slice_now() -> dict:
    """Manually trigger a slice (force the lengthen-cycle to reset).

    Useful when the user wants to mark a milestone without waiting for the
    N-call automatic trigger.
    """
    counter = _record_call_and_maybe_slice(force_slice=True)
    return {
        "forced": True,
        "counter": counter,
    }


@mcp.tool()
def get_license_status() -> dict:
    """Return the user's license tier (free / pro) and any details.

    The plugin and the Claude skill should use this before showing
    Pro-only characters or pulls.
    """
    from .license import verify_license

    s = verify_license()
    return {
        "tier": s.tier,
        "email": s.email,
        "expires": s.expires.isoformat() if s.expires else None,
        "reason": s.reason,
    }


@mcp.tool()
def get_catalog() -> dict:
    """Return the character catalog filtered by the user's license tier.

    Free users see 8 starter characters; Pro users see all 29.
    Loads metadata from `$CHIBI_ASSET_DIR/meta.json` (the plugin's bundled
    assets directory). Falls back to an embedded path if the env var is
    not set (e.g. running outside the plugin).
    """
    import json
    import os
    from pathlib import Path

    from .license import filter_catalog_by_tier, verify_license

    asset_dir = os.environ.get("CHIBI_ASSET_DIR")
    if not asset_dir:
        # Fallback: walk up from this file to <repo>/assets/meta.json
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "assets" / "meta.json"
            if candidate.exists():
                asset_dir = str(candidate.parent)
                break

    if not asset_dir:
        return {"error": "asset directory not found", "characters": []}

    meta_path = Path(asset_dir) / "meta.json"
    if not meta_path.exists():
        return {"error": f"meta.json missing at {meta_path}", "characters": []}

    catalog = json.loads(meta_path.read_text(encoding="utf-8"))
    status = verify_license()
    filtered = filter_catalog_by_tier(catalog, status)
    return {
        "tier": status.tier,
        "total_in_tier": len(filtered.get("characters", [])),
        "total_full": len(catalog.get("characters", [])),
        "characters": filtered.get("characters", []),
        "asset_dir": asset_dir,
    }


def _kill_existing_window() -> None:
    if not _WINDOW_PID_FILE.exists():
        return
    try:
        pid = int(_WINDOW_PID_FILE.read_text().strip())
    except (OSError, ValueError):
        pid = None
    if pid:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(pid, signal.SIGTERM)
    _WINDOW_PID_FILE.unlink(missing_ok=True)


@mcp.tool()
def open_pet_window(character_id: str | None = None) -> dict:
    """Pop up a small always-on-top tk window showing the active 치비.

    Spawns a detached Python subprocess that connects to the local WebSocket
    (ws://127.0.0.1:9876) and updates mood/slice/say events live. Only one
    window at a time — re-calling closes the previous one.

    Args:
        character_id: optional. If given (and you own it), shows that one.
            Otherwise uses your active character; if no active, the first
            character in your catalog.
    """
    catalog = get_catalog()
    chars = catalog.get("characters", [])
    if not chars:
        return {"opened": False, "reason": "no characters in your tier"}

    state = get_state()
    snap = state.snapshot()
    mood = snap["mood"]
    active_id = snap["gacha"]["active_character_id"]

    target_id = character_id or active_id
    if target_id:
        ch = next((c for c in chars if c["id"] == target_id), None)
        if ch is None:
            return {
                "opened": False,
                "reason": f"character {target_id!r} not in your tier",
            }
    else:
        ch = chars[0]

    asset_dir = catalog.get("asset_dir")
    if not asset_dir:
        return {"opened": False, "reason": "asset_dir not configured"}
    image_path = Path(asset_dir) / f"{ch['id']}.png"
    if not image_path.exists():
        return {"opened": False, "reason": f"image not found: {image_path}"}

    # Prefer the user-given nickname if any
    nickname = ch.get("name_ko") or ch["id"]
    inv = state.inventory.get(ch["id"])
    if inv and inv.get("nickname"):
        nickname = inv["nickname"]

    _kill_existing_window()

    # Capture stderr to a log file so import/tk errors are debuggable.
    log_path = Path.home() / ".chibi-mcp" / "window.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = log_path.open("ab")

    popen_kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": log_fh,
        "stderr": log_fh,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "chibi_mcp.window",
            "--image",
            str(image_path),
            "--name",
            nickname,
            "--rarity",
            str(ch.get("rarity", 2)),
            "--mood",
            mood,
            "--ws",
            f"ws://127.0.0.1:{os.environ.get('CHIBI_WS_PORT', '9876')}",
        ],
        **popen_kwargs,
    )

    # Tk import failures, missing display, etc. show up in the first 500ms.
    # If the subprocess is already dead by then, surface the tail of its log.
    import time as _time

    _time.sleep(0.5)
    exit_code = proc.poll()
    if exit_code is not None:
        log_fh.close()
        try:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
        except OSError:
            tail = "(no log)"
        return {
            "opened": False,
            "reason": f"window subprocess died (exit {exit_code})",
            "log_tail": tail,
            "log_path": str(log_path),
            "hint": (
                "macOS: ensure pipx is using a Python with tkinter "
                "(python.org installer or `brew install python-tk@3.12`). "
                "Check with: python3 -c 'import tkinter'"
            ),
        }

    _WINDOW_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WINDOW_PID_FILE.write_text(str(proc.pid))

    return {
        "opened": True,
        "pid": proc.pid,
        "character": ch["id"],
        "name_ko": nickname,
        "rarity": ch.get("rarity"),
        "mood": mood,
        "image": str(image_path),
        "log_path": str(log_path),
    }


@mcp.tool()
def close_pet_window() -> dict:
    """Close the floating 치비 window if one is open."""
    existed = _WINDOW_PID_FILE.exists()
    _kill_existing_window()
    return {"closed": True, "had_window": existed}


@mcp.tool()
def set_slice_interval(n: int) -> dict:
    """Change how often (every N Claude tool calls) tteoki gets sliced.

    Args:
        n: positive integer. Default is 10. Suggested values: 5, 10, 25, 50, 100.
    """
    if n < 1:
        raise ValueError("slice interval must be ≥ 1")
    state = get_state()
    old = state.slice_interval
    state.slice_interval = n
    return {"previous": old, "current": n}


# ── Gacha + inventory ───────────────────────────────────────────────────────


@mcp.tool()
def pull_gacha() -> dict:
    """Pull one 치비 from the gacha.

    Costs:
        - First pull of the calendar day is free (resets at local midnight).
        - Otherwise costs 1 ticket.

    Tickets are auto-granted: +1 per 100 Claude tool calls and +1 per 10
    slices. Use `add_ticket` for manual grants (debug / promo).

    Rarity weights: ★★★★★ 1%, ★★★★ 5%, ★★★ 24%, ★★ 70%. Newly pulled
    character becomes your active 치비 if you didn't have one.
    """
    catalog = get_catalog()
    chars = catalog.get("characters", [])
    state = get_state()
    result = state.pull_gacha(chars)
    if result.get("drawn") is None:
        return result

    # Broadcast a slice-like event so any open window celebrates
    broadcaster = get_broadcaster()
    _fire_and_forget(
        broadcaster.broadcast(
            {
                "type": "say",
                "text": f"✨ {result['drawn']['name_ko']} ★{result['drawn']['rarity']} 등장!",
            }
        )
    )
    return result


@mcp.tool()
def get_inventory() -> dict:
    """Return everything you own + ticket balance + active character."""
    state = get_state()
    snap = state.snapshot()["gacha"]
    return {
        "active_character_id": state.active_character_id,
        "tickets": state.tickets,
        "total_pulls": state.total_pulls,
        "owned_count": len(state.inventory),
        "inventory": state.inventory,
        "last_free_pull_date": state.last_free_pull_date,
        "next_free_in_seconds": _seconds_until_local_midnight(),
        "summary": snap,
    }


@mcp.tool()
def set_active_character(character_id: str) -> dict:
    """Switch which 치비 is shown in the window. Must own the character."""
    state = get_state()
    result = state.set_active(character_id)
    if result.get("ok") and _WINDOW_PID_FILE.exists():
        # Auto-reopen the window with the new character if one was open
        try:
            open_pet_window(character_id=character_id)
        except Exception as e:
            log.warning("window reopen after set_active failed: %s", e)
    return result


@mcp.tool()
def rename_character(character_id: str, nickname: str) -> dict:
    """Rename a 치비 you own. Nickname is clipped to 40 chars."""
    state = get_state()
    return state.rename(character_id, nickname)


@mcp.tool()
def add_ticket(n: int = 1) -> dict:
    """Grant N gacha tickets. n must be 1..100."""
    if not 1 <= n <= 100:
        raise ValueError("n must be between 1 and 100")
    state = get_state()
    return state.grant_tickets(n)


def _seconds_until_local_midnight() -> int:
    from datetime import datetime as _dt

    now = _dt.now()
    seconds_today = now.hour * 3600 + now.minute * 60 + now.second
    return max(0, 86400 - seconds_today)
