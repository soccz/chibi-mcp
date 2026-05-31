"""MCP tool definitions — tools Claude Code calls to interact with chibi."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from .runtime import runtime_file
from .state import _seconds_until_midnight, get_state
from .ws_server import get_broadcaster, set_action_handler

# Catalog ids are tightly controlled — catalog-defined slugs only.
# Any external string passed as a character/option id is validated against this.
_CHAR_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
MAX_ACTIVE_OPTIONS = 3

log = logging.getLogger(__name__)

# Tracks the spawned tk window process across MCP calls. A PID file persists
# across MCP server restarts (the window is a detached subprocess).
_WINDOW_PID_FILE = runtime_file("window.pid")
_DEFAULT_WINDOW_PID_FILE = _WINDOW_PID_FILE
_WINDOW_READY_TIMEOUT_SECONDS = 5.0
_WINDOW_VIEW_MODES = {"normal", "debug", "compact"}

class _ToolRegistry:
    """Identity stand-in for FastMCP.

    The runtime MCP transport is the hand-rolled JSON-RPC loop in
    `__main__.py` (`_TOOL_FUNCTIONS`), so the FastMCP instance was never run —
    it only hosted the `@mcp.tool()` decorators. An identity decorator
    preserves every tool function (name, signature, docstring) while avoiding
    fastmcp's ~600ms import on every entry point. The `@mcp.tool()` markers
    stay as the documented server.py + __main__.py dual-registration contract.
    """

    def tool(self, *args, **kwargs):
        def decorator(fn):
            return fn

        return decorator


mcp = _ToolRegistry()


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
        with contextlib.suppress(Exception):
            coro.close()
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


def _broadcast_sound(name: str) -> bool:
    """Ask any open floating window to play a local sound by key."""
    if name not in {"bubble", "slice", "squish", "gacha", "rare", "option"}:
        return False
    broadcaster = get_broadcaster()
    return _fire_and_forget(broadcaster.broadcast({"type": "sound", "name": name}))


def _broadcast_say(text: str) -> bool:
    broadcaster = get_broadcaster()
    return _fire_and_forget(broadcaster.broadcast({"type": "say", "text": _sanitize_say(text)}))


def _broadcast_state() -> bool:
    broadcaster = get_broadcaster()
    return _fire_and_forget(
        broadcaster.broadcast({"type": "state", "payload": get_state().snapshot()})
    )


@mcp.tool()
def get_pet_state() -> dict:
    """Return chibi's current state: mood, system metrics, counters, timing.

    The desktop app reads this to render the character. Calling this tool
    counts as a Claude interaction and may trigger a milestone every N calls.
    """
    counter = _record_call_and_maybe_slice()
    state = get_state()
    snapshot = state.snapshot()
    snapshot["last_call_result"] = counter
    return snapshot


@mcp.tool()
def pet_say(text: str) -> dict:
    """Make chibi say something via a speech bubble in the desktop app.

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
    """Manually trigger a milestone animation.

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
    """Return the current catalog access status.

    Kept as a stable MCP tool name. The open-source core has no paid
    entitlement gate; unreleased catalog placeholders stay hidden.
    """
    from .license import verify_license

    s = verify_license()
    return {
        "tier": s.tier,
        "email": s.email,
        "expires": s.expires.isoformat() if s.expires else None,
        "reason": s.reason,
    }


def _resolve_asset_dir() -> str | None:
    """Find the chibi plugin's assets/ directory robustly.

    Priority:
        1. $CHIBI_ASSET_DIR if it's a real expanded path with meta.json
           (skip literal "${...}" values that some Claude Code versions
           don't substitute).
        2. Glob ~/.claude/plugins/cache/**/assets/meta.json — pick the
           most-recently-modified match (latest installed plugin version).
        3. Walk up from this source file to find a sibling assets/meta.json
           (works for source installs and packaged wheel assets).
    """
    env = os.environ.get("CHIBI_ASSET_DIR", "")
    if env and "$" not in env and "{" not in env:
        p = Path(env).expanduser() / "meta.json"
        if p.exists():
            return str(p.parent)

    cache_bases = [
        Path.home() / ".claude" / "plugins" / "cache",
        Path.home() / ".config" / "claude" / "plugins" / "cache",
    ]
    candidates: list[Path] = []
    for base in cache_bases:
        if base.exists():
            candidates.extend(base.glob("**/assets/meta.json"))
    if candidates:
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        return str(latest.parent)

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "assets" / "meta.json"
        if candidate.exists():
            return str(candidate.parent)

    return None


_CATALOG_PARSE_CACHE: dict[str, tuple[float, dict]] = {}


def _load_meta_cached(meta_path: Path) -> dict:
    """Parse meta.json, memoized by (path, mtime) so repeated catalog/options
    tool calls skip re-reading and re-parsing. Re-reads when the file changes."""
    key = str(meta_path)
    mtime = meta_path.stat().st_mtime
    cached = _CATALOG_PARSE_CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    _CATALOG_PARSE_CACHE[key] = (mtime, data)
    return data


def _pack_roots() -> list[Path]:
    """Directories holding installed/registered creator packs (each has meta.json).

    Sources: the `CHIBI_PACK_DIRS` env (os.pathsep-separated) plus every
    subdirectory of `~/.chibi-mcp/packs/` that `chibi-pack install` populated.
    """
    roots: list[Path] = []
    for part in os.environ.get("CHIBI_PACK_DIRS", "").split(os.pathsep):
        part = part.strip()
        if part:
            candidate = Path(part).expanduser()
            if (candidate / "meta.json").exists():
                roots.append(candidate)
    packs_home = runtime_file("packs")
    if packs_home.is_dir():
        for child in sorted(packs_home.iterdir()):
            if child.is_dir() and (child / "meta.json").exists():
                roots.append(child)
    return roots


def _load_pack_catalog() -> dict:
    """Merge free characters/options from installed creator packs.

    Each item is tagged with its own `pack_dir` (used as the trusted image root
    by `_resolve_catalog_image`) and `source: "creator"`. Malformed packs are
    skipped; official ids win over pack ids (handled by the caller).
    """
    characters: list[dict] = []
    options: list[dict] = []
    for root in _pack_roots():
        try:
            meta = json.loads((root / "meta.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(meta, dict):
            continue
        for ch in meta.get("characters", []):
            # Local pack content is visible regardless of label; only hidden
            # "upcoming" placeholders are skipped. No tier gates anything paid.
            if isinstance(ch, dict) and ch.get("tier") != "upcoming" and _CHAR_ID_RE.match(
                str(ch.get("id", ""))
            ):
                characters.append({**ch, "pack_dir": str(root), "source": "creator"})
        for opt in meta.get("options", []):
            if isinstance(opt, dict) and opt.get("tier") != "upcoming" and _CHAR_ID_RE.match(
                str(opt.get("id", ""))
            ):
                options.append({**opt, "pack_dir": str(root), "source": "creator"})
    return {"characters": characters, "options": options}


@mcp.tool()
def get_catalog() -> dict:
    """Return the released character catalog.

    Users see released starter characters; unreleased placeholders stay hidden.
    Resolves the assets/ directory via `$CHIBI_ASSET_DIR`, the Claude Code
    plugin cache glob, then a source-tree walk — in that order.
    """
    from .license import filter_catalog_by_tier, verify_license

    asset_dir = _resolve_asset_dir()
    if not asset_dir:
        return {
            "error": "asset directory not found",
            "tried": {
                "CHIBI_ASSET_DIR": os.environ.get("CHIBI_ASSET_DIR"),
                "plugin_cache_globs": [
                    str(Path.home() / ".claude" / "plugins" / "cache"),
                    str(Path.home() / ".config" / "claude" / "plugins" / "cache"),
                ],
            },
            "characters": [],
        }

    meta_path = Path(asset_dir) / "meta.json"
    try:
        catalog = _load_meta_cached(meta_path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        return {
            "error": f"meta.json unreadable at {meta_path}: {type(e).__name__}: {e}",
            "asset_dir": asset_dir,
            "characters": [],
        }
    status = verify_license()
    filtered = filter_catalog_by_tier(catalog, status)
    chars = list(filtered.get("characters", []))
    opts = list(filtered.get("options", []))
    official_char_ids = {c.get("id") for c in chars}
    official_opt_ids = {o.get("id") for o in opts}
    packs = _load_pack_catalog()
    pack_chars = [c for c in packs["characters"] if c.get("id") not in official_char_ids]
    pack_opts = [o for o in packs["options"] if o.get("id") not in official_opt_ids]
    chars.extend(pack_chars)
    opts.extend(pack_opts)
    return {
        "tier": status.tier,
        "total_in_tier": len(filtered.get("characters", [])),
        "total_full": len(catalog.get("characters", [])),
        "total_options": len(opts),
        "creator_characters": len(pack_chars),
        "characters": chars,
        "options": opts,
        "asset_dir": asset_dir,
    }


@mcp.tool()
def get_options() -> dict:
    """Return free visual option layers such as honey, amber glaze, and beads."""
    catalog = get_catalog()
    asset_dir = catalog.get("asset_dir")
    state = get_state()
    options: list[dict] = []
    if asset_dir:
        for option in catalog.get("options", []):
            option_id = str(option.get("id", "")).strip()
            if not _CHAR_ID_RE.match(option_id):
                continue
            image_path = _resolve_catalog_image(asset_dir, option, "options")
            options.append(
                {
                    **option,
                    "image_exists": image_path is not None,
                    "image_path": str(image_path) if image_path else None,
                }
            )
    return {
        "total": len(options),
        "max_active": MAX_ACTIVE_OPTIONS,
        "active_option_ids": list(state.active_option_ids),
        "options": options,
    }


@mcp.tool()
def set_active_options(option_ids: list[str]) -> dict:
    """Choose up to three free visual option layers for the floating pet."""
    if not isinstance(option_ids, list):
        return {"ok": False, "reason": "option_ids must be a list"}
    cleaned: list[str] = []
    for option_id in option_ids:
        option_id = str(option_id).strip()
        if not option_id:
            continue
        if not _CHAR_ID_RE.match(option_id):
            return {"ok": False, "reason": f"invalid option id: {option_id!r}"}
        cleaned.append(option_id)
    if len(cleaned) > MAX_ACTIVE_OPTIONS:
        return {"ok": False, "reason": f"choose at most {MAX_ACTIVE_OPTIONS} active options"}

    options = get_options()
    available = {option["id"] for option in options["options"] if option.get("image_exists")}
    state = get_state()
    result = state.set_active_options(cleaned, available)
    if result.get("ok"):
        _broadcast_sound("option")
        result["broadcasted"] = _broadcast_state()
    return result


@mcp.tool()
def clear_active_options() -> dict:
    """Remove all visual option layers from the floating pet."""
    return set_active_options([])


def _resolve_catalog_image(asset_dir: str, item: dict, subdir: str) -> Path | None:
    # Creator-pack items carry their own trusted root via `pack_dir`; official
    # items resolve against the shared asset_dir. Either way the image must stay
    # inside that root (path-traversal guard below).
    asset_root = Path(item.get("pack_dir") or asset_dir).resolve()
    item_id = str(item.get("id", "")).strip()
    candidates: list[Path] = []
    image_value = item.get("image")
    if image_value:
        explicit = (asset_root / str(image_value)).resolve()
        if explicit != asset_root and asset_root in explicit.parents:
            candidates.append(explicit)
        else:
            return None
    if item_id:
        candidates.append(asset_root / f"{item_id}.png")
        candidates.append(asset_root / subdir / f"{item_id}.png")
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and resolved != asset_root and asset_root in resolved.parents:
            return resolved
    return None


def _kill_existing_window() -> None:
    pid_file = _window_pid_file()
    if not pid_file.exists():
        return
    try:
        pid = int(pid_file.read_text().strip())
    except (OSError, ValueError):
        pid = None
    if pid:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(pid, signal.SIGTERM)
    with contextlib.suppress(OSError):
        pid_file.unlink(missing_ok=True)


def _window_pid_file() -> Path:
    if _WINDOW_PID_FILE != _DEFAULT_WINDOW_PID_FILE:
        return _WINDOW_PID_FILE
    return runtime_file("window.pid")


def _window_log_file() -> Path:
    return runtime_file("window.log")


def _window_ws_url() -> str:
    # Validate the port so a bad CHIBI_WS_PORT falls back to 9876 — the same
    # value the WS server binds — keeping the window URL and the server in sync.
    host = os.environ.get("CHIBI_WS_HOST", "127.0.0.1") or "127.0.0.1"
    raw_port = os.environ.get("CHIBI_WS_PORT", "9876")
    try:
        port = int(raw_port)
        if not (1 <= port <= 65535):
            raise ValueError
    except (TypeError, ValueError):
        port = 9876
    return f"ws://{host}:{port}"


def _window_runtime_issue() -> dict | None:
    try:
        import tkinter  # noqa: F401
    except Exception as exc:
        return {
            "opened": False,
            "reason": "python tkinter unavailable",
            "error": str(exc),
            "next_step": (
                "Ubuntu/Debian system Python: sudo apt-get install -y python3-tk. "
                "macOS Homebrew Python: install the matching python-tk@X.Y package "
                "(for example, brew install python-tk@3.14). "
                "pyenv Python: install tk-dev, then rebuild the Python version used by pipx."
            ),
        }

    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get(
        "WAYLAND_DISPLAY"
    ):
        return {
            "opened": False,
            "reason": "no desktop display session",
            "next_step": "Run from a real desktop session, or set DISPLAY/WAYLAND_DISPLAY for a forwarded GUI session.",
        }

    return None


def _read_log_tail(log_path: Path) -> str:
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
    except OSError:
        return "(no log)"


def _window_startup_failure(
    proc: subprocess.Popen,
    ready_path: Path,
    log_path: Path,
    *,
    timeout_seconds: float = _WINDOW_READY_TIMEOUT_SECONDS,
    poll_interval: float = 0.05,
) -> dict | None:
    """Return a failure payload unless the child reports Tk startup readiness."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if ready_path.exists():
            return None
        exit_code = proc.poll()
        if exit_code is not None:
            return {
                "opened": False,
                "reason": f"window subprocess died before ready (exit {exit_code})",
                "log_tail": _read_log_tail(log_path),
                "log_path": str(log_path),
                "ready_file": str(ready_path),
                "next_step": "Run `chibi-mcp --open` and inspect the returned log_path.",
            }
        time.sleep(poll_interval)

    with contextlib.suppress(OSError, ProcessLookupError):
        proc.terminate()
    return {
        "opened": False,
        "reason": "window subprocess did not report ready before timeout",
        "pid": proc.pid,
        "log_tail": _read_log_tail(log_path),
        "log_path": str(log_path),
        "ready_file": str(ready_path),
        "next_step": "Run `chibi-mcp --open`; if it repeats, attach ~/.chibi-mcp/window.log.",
    }


@mcp.tool()
def open_pet_window(character_id: str | None = None, view_mode: str | None = None) -> dict:
    """Pop up a small always-on-top tk window showing the active chibi.

    Spawns a detached Python subprocess that connects to the local WebSocket
    (ws://127.0.0.1:9876) and updates mood/milestone/say events live. Only one
    window at a time — re-calling closes the previous one.

    Args:
        character_id: optional. If given (and you own it), shows that one.
            Otherwise uses your active character; if no active, the first
            character in your catalog.
        view_mode: optional. One of normal, debug, compact. If omitted, the
            window uses the last saved user mode.
    """
    if character_id and not _CHAR_ID_RE.match(character_id):
        return {
            "opened": False,
            "reason": f"invalid character id: {character_id!r}",
            "message_ko": "잘못된 chibi ID야",
        }
    if view_mode is not None:
        view_mode = str(view_mode).strip().lower()
        if view_mode not in _WINDOW_VIEW_MODES:
            return {
                "opened": False,
                "reason": f"invalid view_mode: {view_mode!r}",
                "allowed_view_modes": sorted(_WINDOW_VIEW_MODES),
            }

    catalog = get_catalog()
    chars = catalog.get("characters", [])
    if not chars:
        return {"opened": False, "reason": "no released characters available"}

    state = get_state()
    snap = state.snapshot()
    mood = snap["mood"]
    active_id = snap["gacha"]["active_character_id"]

    target_id = character_id or active_id
    with state._lock:
        owns_requested = character_id in state.inventory if character_id else True
    if character_id and not owns_requested:
        return {
            "opened": False,
            "reason": f"you don't own {character_id!r}",
            "message_ko": "아직 보유하지 않은 chibi야. 보관함이나 뽑기에서 먼저 얻어야 해.",
        }
    if target_id:
        ch = next((c for c in chars if c["id"] == target_id), None)
        if ch is None:
            return {
                "opened": False,
                "reason": f"character {target_id!r} is not released",
            }
    else:
        ch = chars[0]

    asset_dir = catalog.get("asset_dir")
    if not asset_dir:
        return {"opened": False, "reason": "asset_dir not configured"}
    # Defense in depth: even though character_id is matched against the
    # catalog, prevent any path-traversal via a malformed id field.
    safe_id = ch["id"]
    if not _CHAR_ID_RE.match(safe_id):
        return {"opened": False, "reason": f"unsafe character id: {safe_id!r}"}
    image_path = _resolve_catalog_image(asset_dir, ch, "characters")
    if image_path is None:
        return {"opened": False, "reason": f"image not found for {safe_id!r}"}

    options_by_id = {
        option["id"]: option
        for option in catalog.get("options", [])
        if isinstance(option, dict) and _CHAR_ID_RE.match(str(option.get("id", "")))
    }
    option_images: list[tuple[str, Path]] = []
    for option_id in snap["gacha"].get("active_option_ids", []):
        option = options_by_id.get(option_id)
        if not option:
            continue
        option_path = _resolve_catalog_image(asset_dir, option, "options")
        if option_path:
            option_images.append((option_id, option_path))

    runtime_issue = _window_runtime_issue()
    if runtime_issue:
        return {
            **runtime_issue,
            "character": ch["id"],
            "name_ko": ch.get("name_ko") or ch["id"],
            "image": str(image_path),
            "options": [option_id for option_id, _path in option_images],
            "view_mode": view_mode,
        }

    # Prefer the user-given nickname if any
    nickname = ch.get("name_ko") or ch["id"]
    inv = state.inventory.get(ch["id"])
    if inv and inv.get("nickname"):
        nickname = inv["nickname"]

    _kill_existing_window()

    # Capture stderr to a log file so import/tk errors are debuggable.
    log_path = _window_log_file()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = log_path.open("ab")
    ready_path = log_path.parent / f"window-ready-{uuid.uuid4().hex}.json"

    popen_kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": log_fh,
        "stderr": log_fh,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        popen_kwargs["start_new_session"] = True

    command = [
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
        _window_ws_url(),
        "--initial-state",
        json.dumps(snap, ensure_ascii=False, separators=(",", ":")),
        "--asset-dir",
        str(asset_dir),
        "--character-id",
        ch["id"],
        "--ready-file",
        str(ready_path),
    ]
    if view_mode is not None:
        command.extend(["--view-mode", view_mode])
    for _option_id, option_path in option_images:
        command.extend(["--option-image", str(option_path)])
    for option_id in snap["gacha"].get("active_option_ids", []):
        command.extend(["--active-option-id", str(option_id)])

    proc = subprocess.Popen(command, **popen_kwargs)
    startup_failure = _window_startup_failure(proc, ready_path, log_path)
    with contextlib.suppress(OSError):
        log_fh.close()
    # Clean up the unique ready-file on every path (success or failure) so
    # timed-out / crashed launches don't leave window-ready-*.json behind.
    with contextlib.suppress(OSError):
        ready_path.unlink(missing_ok=True)
    if startup_failure is not None:
        return startup_failure

    pid_file_written = True
    pid_file_warning = None
    try:
        pid_file = _window_pid_file()
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(proc.pid))
    except OSError as exc:
        pid_file_written = False
        pid_file_warning = str(exc)

    result = {
        "opened": True,
        "pid": proc.pid,
        "character": ch["id"],
        "name_ko": nickname,
        "rarity": ch.get("rarity"),
        "mood": mood,
        "image": str(image_path),
        "options": [option_id for option_id, _path in option_images],
        "view_mode": view_mode,
        "log_path": str(log_path),
        "ready": True,
        "pid_file": str(_window_pid_file()),
        "pid_file_written": pid_file_written,
    }
    if pid_file_warning:
        result["pid_file_warning"] = pid_file_warning
    return result


@mcp.tool()
def close_pet_window() -> dict:
    """Close the floating chibi window if one is open."""
    existed = _window_pid_file().exists()
    _kill_existing_window()
    return {"closed": True, "had_window": existed}


@mcp.tool()
def set_slice_interval(n: int) -> dict:
    """Change how often (every N Claude tool calls) chibi shows a milestone.

    Args:
        n: positive integer. Default is 10. Suggested values: 5, 10, 25, 50, 100.
    """
    if n < 1:
        raise ValueError("slice interval must be ≥ 1")
    state = get_state()
    result = state.set_slice_interval(n)
    result["broadcasted"] = _broadcast_state()
    return result


# ── Gacha + inventory ───────────────────────────────────────────────────────


@mcp.tool()
def pull_gacha() -> dict:
    """Pull one chibi from the gacha.

    Costs:
        - First pull of the calendar day is free (resets at local midnight).
        - Otherwise costs 1 ticket.

    Tickets are auto-granted: +1 per 100 Claude tool calls and +1 per 10
    slices. Use `add_ticket` for manual grants (debug / promo).

    Rarity weights: ★★★★★ 1%, ★★★★ 5%, ★★★ 24%, ★★ 70%. Only rarities that
    have released characters can be drawn — the current starter roster is all
    ★★, so the higher-rarity odds apply as more of the 29 chibis are released.
    Newly pulled character becomes your active chibi if you didn't have one.
    """
    catalog = get_catalog()
    chars = catalog.get("characters", [])
    state = get_state()
    result = state.pull_gacha(chars)
    if result.get("drawn") is None:
        return result

    # Broadcast the fresh state immediately so the window shows the pulled
    # character/inventory without waiting for the periodic state tick.
    broadcaster = get_broadcaster()
    drawn = result["drawn"]
    rarity = drawn.get("rarity") or 0
    sound_name = "rare" if int(rarity) >= 4 else "gacha"
    _broadcast_sound(sound_name)
    result["broadcasted"] = _broadcast_state()
    name_ko = drawn.get("name_ko") or drawn.get("id") or "???"
    _fire_and_forget(
        broadcaster.broadcast(
            {
                "type": "say",
                "text": f"✨ {name_ko} ★{int(rarity)} 등장!",
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
        "last_pull": state.last_pull,
        "next_free_in_seconds": _seconds_until_midnight(),
        "summary": snap,
    }


@mcp.tool()
def set_active_character(character_id: str) -> dict:
    """Switch which chibi is shown in the window. Must own the character."""
    if not _CHAR_ID_RE.match(character_id):
        return {
            "ok": False,
            "reason": f"invalid character id: {character_id!r}",
            "message_ko": "잘못된 chibi ID야",
        }
    state = get_state()
    result = state.set_active(character_id)
    if result.get("ok"):
        result["broadcasted"] = _broadcast_state()
    return result


@mcp.tool()
def rename_character(character_id: str, nickname: str) -> dict:
    """Rename a chibi you own. Nickname is clipped to 40 chars."""
    if not _CHAR_ID_RE.match(character_id):
        return {
            "ok": False,
            "reason": f"invalid character id: {character_id!r}",
            "message_ko": "잘못된 chibi ID야",
        }
    state = get_state()
    result = state.rename(character_id, nickname)
    if result.get("ok"):
        result["broadcasted"] = _broadcast_state()
    return result


@mcp.tool()
def add_ticket(n: int = 1) -> dict:
    """Grant N gacha tickets. n must be 1..100."""
    if not 1 <= n <= 100:
        raise ValueError("n must be between 1 and 100")
    state = get_state()
    result = state.grant_tickets(n)
    result["broadcasted"] = _broadcast_state()
    return result


def _handle_window_action(message: dict) -> dict:
    """Run actions requested by the floating window toolbar.

    The window never edits ~/.chibi-mcp/state.json directly. It sends a small
    localhost WebSocket action and this MCP server reuses the same validated
    tool paths that Claude/Codex use.
    """
    action = str(message.get("action") or "").strip()
    if action == "pull_gacha":
        result = pull_gacha()
        return {"ok": result.get("drawn") is not None, **result}
    if action == "set_active_character":
        character_id = str(message.get("character_id") or "").strip()
        return set_active_character(character_id)
    if action == "set_active_options":
        option_ids = message.get("option_ids")
        if not isinstance(option_ids, list):
            return {"ok": False, "reason": "option_ids must be a list"}
        return set_active_options([str(option_id) for option_id in option_ids])
    if action == "clear_active_options":
        return clear_active_options()
    _broadcast_say("알 수 없는 창 액션")
    return {"ok": False, "reason": f"unknown window action: {action!r}"}


set_action_handler(_handle_window_action)
