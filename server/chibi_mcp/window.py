"""Tk window for the floating chibi.

v1.1 visual upgrade:
    - overrideredirect(True): no title bar — floats as a compact pet window.
    - macOS uses the same stable Tk panel path as other platforms. The old
      PyObjC transparency experiment is disabled because some Python/Tk/PyObjC
      combinations segfault before Python can catch errors.
    - Canvas-based image rendering: bob animation via canvas.move (no flicker).
    - Idle bob: 4px gentle vertical oscillation, ~0.6 Hz, like a slime breathing.
    - Sounds: short procedurally-generated wavs played via `afplay` (darwin),
      `paplay`/`aplay` (linux), winsound (windows). Event-specific sounds cover
      squish, milestones, gacha, rare pulls, option changes, and speech bubbles.

Live behaviour (unchanged from v1.0):
    - Connects to ws://127.0.0.1:9876, receives state/say/milestone events.
    - Mood filter applied to base PNG (brightness/saturation/tint).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import math
import os
import queue
import struct
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
import wave
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageEnhance, ImageTk

log = logging.getLogger(__name__)

CANVAS_SIZE = 240
WINDOW_MIN_SCALE = 0.65
WINDOW_MAX_SCALE = 1.85
RESIZE_GRIP_SIZE = 20
PANEL_BG = "#fff8ef"
PANEL_BG_2 = "#fff1df"
PANEL_BORDER = "#e7c9a6"
TEXT_FG = "#2a211a"
MUTED_FG = "#806f62"
STATUS_BG = "#fffdf8"
STATUS_BORDER = "#efd8bf"
STATUS_SHADOW = "#ead8c1"
STATUS_CHIP_BG = "#ffe5ec"
STATUS_CHIP_BORDER = "#ffc4d5"
STATUS_METRIC_BG = "#edfdf4"
STATUS_METRIC_BORDER = "#b7e4c7"
STATUS_WARN_BG = "#fff2d7"
STATUS_WARN_BORDER = "#e2b35b"
METER_TRACK = "#ead7c3"
METER_GOOD = "#55bd83"
METER_WARN = "#f4a23a"
METER_DANGER = "#f05f4b"
BUTTON_SECONDARY_BG = "#fffdf7"
BUTTON_SECONDARY_HOVER = "#edfdf4"
BUTTON_SECONDARY_ACTIVE = "#d7f4e2"
BUTTON_SECONDARY_BORDER = "#b7e4c7"
BUTTON_SECONDARY_SHADOW = "#ead7be"
BUTTON_SECONDARY_ICON_BG = "#e8f8ee"
BUTTON_PRIMARY_BG = "#ff6b9d"
BUTTON_PRIMARY_HOVER = "#ff7fac"
BUTTON_PRIMARY_ACTIVE = "#f6558e"
BUTTON_PRIMARY_BORDER = "#ff9dbd"
BUTTON_PRIMARY_SHADOW = "#d8497a"
BUTTON_PRIMARY_ICON_BG = "#ffd5e3"
BUTTON_DANGER_BG = "#fff2f0"
BUTTON_DANGER_HOVER = "#ffe0dc"
BUTTON_DANGER_ACTIVE = "#ffc7bf"
BUTTON_DANGER_BORDER = "#ffb0a6"
BUTTON_DANGER_SHADOW = "#e7b1a9"
BUTTON_DANGER_ICON_BG = "#ffd8d2"
BUTTON_DANGER_FG = "#7d302a"
BUTTON_DISABLED_BG = "#eee0d2"
BUTTON_DISABLED_FG = "#9b8b7d"
RECONNECT_BACKOFF_MIN_S = 1.0
RECONNECT_BACKOFF_MAX_S = 30.0
POLL_INTERVAL_MS = 80
BUBBLE_VISIBLE_MS = 4000
BOB_AMPLITUDE_PX = 4
BOB_HZ = 0.6
BOB_TICK_MS = 30
VIEW_MODES = ("normal", "debug", "compact")

IDLE_BUBBLE_MIN_MS = 4 * 60_000
IDLE_BUBBLE_MAX_MS = 7 * 60_000

SOUND_DIR = Path.home() / ".chibi-mcp" / "sounds"
SOUND_VERSION = "2"
WINDOW_PREFS_FILE = Path.home() / ".chibi-mcp" / "window-prefs.json"
WINDOW_DEFAULT_POSITION_Y = 80

IDLE_PHRASES_BY_MOOD: dict[str, list[str]] = {
    "calm":      ["말랑...", "심심해", "쉬자", "..."],
    "happy":     ["굳굳", "오늘 잘되네", "ㅎㅎ"],
    "joyful":    ["반짝", "오예", "엣헴"],
    "panting":   ["헐 바쁘다", "잠깐만", "엥"],
    "drowsy":    ["졸려", "충전해줘", "..."],
    "lonely":    ["보고싶었어", "심심해", "어디갔어"],
    "surprised": ["오?!", "헐", "잠시만"],
}

CLICK_PHRASES_BY_MOOD: dict[str, list[str]] = {
    "calm":      ["말랑 체크 완료", "대기 중", "좋아, 계속 가자"],
    "happy":     ["방금 작업 감지", "리듬 좋아", "흐름 탔어"],
    "joyful":    ["반짝!", "좋은 페이스", "오늘 잘 굴러가"],
    "panting":   ["CPU 바빠", "조금 뜨거워", "작업량 많아"],
    "drowsy":    ["배터리 낮아", "충전 필요", "절전 모드 느낌"],
    "lonely":    ["오래 조용했어", "다시 시작할까", "기다리는 중"],
    "surprised": ["스파이크 감지", "갑자기 바빠졌어", "오?!"],
}

MOOD_LABELS: dict[str, tuple[str, str]] = {
    "calm": ("말랑", "😌"),
    "happy": ("신남", "😊"),
    "joyful": ("반짝", "🤩"),
    "panting": ("헐떡", "😅"),
    "drowsy": ("졸림", "😴"),
    "lonely": ("시무룩", "🥺"),
    "surprised": ("깜짝", "😮"),
}

MOOD_BOB_PROFILES: dict[str, tuple[int, float]] = {
    "calm": (4, 0.6),
    "happy": (5, 0.85),
    "joyful": (6, 0.95),
    "panting": (7, 1.3),
    "drowsy": (2, 0.35),
    "lonely": (2, 0.42),
    "surprised": (5, 1.05),
}

MOOD_STAGE_COLORS: dict[str, tuple[str, str]] = {
    "calm": ("#ffe8f0", "#d8c1aa"),
    "happy": ("#fff0b8", "#d8bd79"),
    "joyful": ("#ffe0f2", "#d7a9c7"),
    "panting": ("#ffe0db", "#d7a39a"),
    "drowsy": ("#e6e3ff", "#b8b0d5"),
    "lonely": ("#ece7df", "#c8bbae"),
    "surprised": ("#fff3bf", "#d7be79"),
}

VIEW_MODE_BUTTONS: dict[str, tuple[str, str]] = {
    "normal": ("일반", "◐"),
    "debug": ("상세", "▤"),
    "compact": ("작게", "•"),
}


# ── Mood → Pillow filter ─────────────────────────────────────────────────────

# Each tuple: (brightness, saturation, tint_rgb_or_None, tint_alpha).
#   brightness 1.0 = neutral; <1 darkens, >1 brightens.
#   saturation 1.0 = neutral; 0 = grayscale, >1 amplifies color.
#   tint_rgb is blended into RGB at `tint_alpha` while preserving the
#     original alpha channel. None means no tint.
#   tint_alpha 0.0 = no effect, ~0.35 = strongly tinted.
MOOD_FILTERS: dict[str, tuple[float, float, tuple[int, int, int] | None, float]] = {
    "calm":      (1.00, 1.00, None,              0.00),
    "happy":     (1.15, 1.20, (255, 230, 180),   0.18),
    "joyful":    (1.25, 1.35, (255, 200, 230),   0.22),
    "panting":   (1.05, 1.10, (255, 100, 100),   0.30),
    "drowsy":    (0.70, 0.80, (100, 120, 180),   0.25),
    "lonely":    (0.85, 0.55, None,              0.00),
    "surprised": (1.20, 1.10, (255, 255, 200),   0.20),
}


def _apply_mood_filter(img: Image.Image, mood: str) -> Image.Image:
    cfg = MOOD_FILTERS.get(mood, MOOD_FILTERS["calm"])
    brightness, saturation, tint_rgb, tint_alpha = cfg

    if img.mode != "RGBA":
        img = img.convert("RGBA")
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)
    if tint_rgb and tint_alpha > 0:
        alpha = img.getchannel("A")
        tint_layer = Image.new("RGB", img.size, tint_rgb)
        rgb = Image.blend(img.convert("RGB"), tint_layer, tint_alpha)
        img = Image.merge("RGBA", (*rgb.split(), alpha))
    return img


def _scale_to_fit(img: Image.Image, max_side: int) -> Image.Image:
    w, h = img.size
    if max(w, h) <= max_side:
        return img
    ratio = max_side / max(w, h)
    return img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)


def _clamp_window_scale(scale: float) -> float:
    return max(WINDOW_MIN_SCALE, min(WINDOW_MAX_SCALE, scale))


def _scale_from_resize_drag(
    start_scale: float,
    delta_x: int,
    delta_y: int,
    base_width: int,
    base_height: int,
) -> float:
    base_width = max(1, base_width)
    base_height = max(1, base_height)
    start_width = base_width * start_scale
    start_height = base_height * start_scale
    return _clamp_window_scale(
        max((start_width + delta_x) / base_width, (start_height + delta_y) / base_height)
    )


def _normalize_view_mode(value: object) -> str:
    mode = str(value or "normal").strip().lower()
    return mode if mode in VIEW_MODES else "normal"


def _load_window_prefs() -> dict:
    try:
        data = json.loads(WINDOW_PREFS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_window_prefs(data: dict) -> None:
    try:
        WINDOW_PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        current = _load_window_prefs()
        current.update(data)
        WINDOW_PREFS_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        log.debug("window prefs save failed: %s", exc)


def _initial_view_mode(requested: object = None) -> str:
    if requested:
        return _normalize_view_mode(requested)
    return _normalize_view_mode(_load_window_prefs().get("view_mode"))


def _initial_window_scale() -> float:
    prefs = _load_window_prefs()
    return _clamp_window_scale(_finite_number(prefs.get("window_scale")) or 1.0)


def _initial_bool_pref(key: str, default: bool) -> bool:
    value = _load_window_prefs().get(key)
    return value if isinstance(value, bool) else default


def _initial_sounds_enabled(default: bool = True) -> bool:
    return bool(default and _initial_bool_pref("sounds_enabled", True))


def _initial_topmost_enabled() -> bool:
    return _initial_bool_pref("topmost_enabled", True)


def _window_position_from_prefs(
    *,
    screen_w: int,
    screen_h: int,
    win_w: int,
    win_h: int,
) -> tuple[int, int] | None:
    prefs = _load_window_prefs()
    position = prefs.get("position")
    if not isinstance(position, dict):
        return None
    x = _finite_number(position.get("x"))
    y = _finite_number(position.get("y"))
    if x is None or y is None:
        return None

    # Keep restored windows reachable after monitor/layout changes.
    margin = 24
    max_x = max(margin, screen_w - max(1, win_w) - margin)
    max_y = max(margin, screen_h - max(1, win_h) - margin)
    return (
        max(margin, min(max_x, round(x))),
        max(margin, min(max_y, round(y))),
    )


def _next_view_mode(mode: str) -> str:
    current = _normalize_view_mode(mode)
    idx = VIEW_MODES.index(current)
    return VIEW_MODES[(idx + 1) % len(VIEW_MODES)]


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _format_percent(value: object) -> str:
    number = _finite_number(value)
    if number is not None:
        return f"{round(number):d}%"
    return "--"


def _format_short_duration(seconds: object) -> str:
    number = _finite_number(seconds)
    if number is None or number < 0:
        return "대기"
    seconds_i = int(number)
    if seconds_i < 60:
        return f"{seconds_i}초"
    minutes = seconds_i // 60
    if minutes < 60:
        return f"{minutes}분"
    hours = minutes // 60
    return "99시간+" if hours > 99 else f"{hours}시간"


def _seconds_until_midnight_local(now: datetime | None = None) -> int:
    now = now or datetime.now()
    seconds_today = now.hour * 3600 + now.minute * 60 + now.second
    return max(0, 86400 - seconds_today)


def _format_refill_duration(seconds: object) -> str:
    number = _finite_number(seconds)
    if number is None or number <= 0:
        return "곧"
    seconds_i = int(number)
    hours = seconds_i // 3600
    minutes = (seconds_i % 3600) // 60
    if hours:
        return f"{hours}시간 {minutes:02d}분"
    if minutes:
        return f"{minutes}분"
    return f"{seconds_i}초"


def _format_counter(value: object) -> str | None:
    number = _finite_number(value)
    if number is None:
        return None
    count = max(0, int(number))
    return "999+" if count > 999 else str(count)


def _free_pull_status(payload: dict, persisted_state: dict) -> str:
    payload = _as_dict(payload)
    persisted_state = _as_dict(persisted_state)
    gacha = _as_dict(payload.get("gacha"))
    today = datetime.now().date().isoformat()
    last_free = str(
        gacha.get("last_free_pull_date") or persisted_state.get("last_free_pull_date") or ""
    )
    if last_free != today:
        return "무료뽑기 가능"
    refill_seconds = gacha.get("next_free_in_seconds") or _seconds_until_midnight_local()
    return f"무료뽑기 {_format_refill_duration(refill_seconds)} 후"


def _gacha_refill_lines(payload: dict, persisted_state: dict) -> list[str]:
    payload = _as_dict(payload)
    persisted_state = _as_dict(persisted_state)
    gacha = _as_dict(payload.get("gacha"))
    counters = _as_dict(payload.get("counters"))
    tickets = _format_counter(gacha.get("tickets"))
    if tickets is None:
        tickets = _format_counter(persisted_state.get("tickets")) or "0"

    lines = [f"티켓 {tickets} · {_free_pull_status(payload, persisted_state)}"]
    calls_total = _finite_number(counters.get("calls_total"))
    slices_today = _finite_number(counters.get("slices_today"))
    if calls_total is not None:
        next_call_ticket = 100 - (int(calls_total) % 100)
        lines.append(f"call티켓까지 {next_call_ticket} tool call")
    if slices_today is not None:
        next_slice_ticket = 10 - (int(slices_today) % 10)
        lines.append(f"slice티켓까지 {next_slice_ticket} 리듬")
    return lines


def _format_battery(system: dict) -> str:
    system = _as_dict(system)
    plugged = system.get("battery_plugged")
    percent = _finite_number(system.get("battery_percent"))
    if percent is not None:
        suffix = "+" if plugged is True else ""
        return f"{round(percent):d}%{suffix}"
    return "AC" if plugged is True else "--"


def _format_system_hud(system: dict) -> str:
    system = _as_dict(system)
    return (
        f"CPU {_format_percent(system.get('cpu_percent'))} · "
        f"RAM {_format_percent(system.get('ram_percent'))} · "
        f"BAT {_format_battery(system)}"
    )


def _metric_is_warn(system: dict) -> bool:
    system = _as_dict(system)
    cpu = system.get("cpu_percent")
    ram = system.get("ram_percent")
    battery = system.get("battery_percent")
    plugged = system.get("battery_plugged")
    cpu_value = _finite_number(cpu)
    ram_value = _finite_number(ram)
    battery_value = _finite_number(battery)
    cpu_warn = cpu_value is not None and cpu_value >= 80
    ram_warn = ram_value is not None and ram_value >= 90
    battery_warn = battery_value is not None and battery_value < 20 and plugged is False
    return cpu_warn or ram_warn or battery_warn


def _metric_percent_value(value: object) -> int | None:
    number = _finite_number(value)
    if number is None:
        return None
    return max(0, min(100, round(number)))


def _metric_meter_values(system: dict) -> dict[str, int | None]:
    system = _as_dict(system)
    return {
        "CPU": _metric_percent_value(system.get("cpu_percent")),
        "RAM": _metric_percent_value(system.get("ram_percent")),
        "BAT": _metric_percent_value(system.get("battery_percent")),
    }


def _metric_alerts(system: dict) -> set[str]:
    system = _as_dict(system)
    alerts: set[str] = set()
    cpu = _metric_percent_value(system.get("cpu_percent"))
    ram = _metric_percent_value(system.get("ram_percent"))
    battery = _metric_percent_value(system.get("battery_percent"))
    if cpu is not None and cpu >= 80:
        alerts.add("CPU")
    if ram is not None and ram >= 90:
        alerts.add("RAM")
    if battery is not None and battery < 20 and system.get("battery_plugged") is False:
        alerts.add("BAT")
    return alerts


def _rhythm_fraction(counters: dict) -> float:
    counters = _as_dict(counters)
    calls = _finite_number(counters.get("calls_since_slice"))
    interval = _finite_number(counters.get("slice_interval"))
    if calls is None or interval is None or interval <= 0:
        return 0.0
    return max(0.0, min(1.0, calls / interval))


def _format_tool_idle(timing: dict) -> str:
    timing = _as_dict(timing)
    idle = timing.get("idle_seconds")
    if idle is None:
        return "툴 대기"
    return f"툴 {_format_short_duration(idle)}"


def _mood_reason_for_payload(mood: str, payload: dict) -> str:
    payload = _as_dict(payload)
    timing = _as_dict(payload.get("timing"))
    idle = timing.get("idle_seconds")
    if mood == "panting":
        return "CPU 높음"
    if mood == "drowsy":
        return "배터리 낮음"
    if mood == "happy":
        return f"최근 tool call {_format_short_duration(idle)}"
    if mood == "lonely":
        return f"오래 idle {_format_short_duration(idle)}"
    if mood == "surprised":
        return "CPU 스파이크"
    return "안정적"


def _format_debug_hud(payload: dict) -> str:
    payload = _as_dict(payload)
    counters = _as_dict(payload.get("counters"))
    gacha = _as_dict(payload.get("gacha"))
    mood = str(payload.get("mood") or "calm")
    calls_total = _finite_number(counters.get("calls_total")) or 0
    slices_today = _finite_number(counters.get("slices_today")) or 0
    next_call_ticket = 100 - (int(calls_total) % 100)
    next_slice_ticket = 10 - (int(slices_today) % 10)
    tickets = _format_counter(gacha.get("tickets")) or "0"
    return (
        f"{_mood_reason_for_payload(mood, payload)} · "
        f"티켓 {tickets} · call티켓 {next_call_ticket} · slice티켓 {next_slice_ticket}"
    )


def _click_reaction_for_payload(mood: str, payload: dict) -> str:
    payload = _as_dict(payload)
    system = _as_dict(payload.get("system"))
    cpu = _finite_number(system.get("cpu_percent"))
    battery = _finite_number(system.get("battery_percent"))
    plugged = system.get("battery_plugged")
    if cpu is not None and cpu >= 80:
        return f"CPU {_format_percent(cpu)} · 잠깐 숨 고르는 중"
    if battery is not None and battery < 20 and plugged is False:
        return f"BAT {_format_percent(battery)} · 충전 필요"
    if mood in {"happy", "lonely", "surprised"}:
        return _mood_reason_for_payload(mood, payload)
    pool = CLICK_PHRASES_BY_MOOD.get(mood, CLICK_PHRASES_BY_MOOD["calm"])
    import random as _r

    return _r.choice(pool)


def _pull_signature(payload: dict) -> str | None:
    payload = _as_dict(payload)
    gacha = _as_dict(payload.get("gacha"))
    last_pull = _as_dict(gacha.get("last_pull"))
    drawn = _as_dict(last_pull.get("drawn"))
    character_id = str(drawn.get("id") or "").strip()
    pulled_at = str(last_pull.get("pulled_at") or "").strip()
    if not character_id or not pulled_at:
        return None
    return f"{character_id}:{pulled_at}"


def _load_image_for_mood(image_path: Path, mood: str) -> tuple[Image.Image, bool]:
    """Use <stem>_<mood>.png if shipped alongside; else fall back to base PNG.

    Returns (image, is_mood_variant). When True, the caller should NOT also
    apply the procedural mood filter (the variant PNG already has expression).
    """
    variant = image_path.with_name(f"{image_path.stem}_{mood}.png")
    if variant.exists():
        return Image.open(variant).convert("RGBA"), True
    return Image.open(image_path).convert("RGBA"), False


def _macos_make_transparent(_root: tk.Tk) -> bool:
    """Return False: macOS uses the stable Tk panel only.

    Older builds exposed an opt-in PyObjC transparency experiment. That path
    can segfault inside native ObjC/Tk code on Homebrew Python/Tk combinations,
    so it is intentionally dead even if the old environment variable is set.
    """
    return False


def _write_ready_file(path_value: str | None) -> None:
    if not path_value:
        return
    try:
        path = Path(path_value).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"ready": True, "pid": os.getpid()}), encoding="utf-8")
    except OSError as exc:
        print(f"ready file write failed: {exc}", file=sys.stderr)


# ── Procedural sounds ────────────────────────────────────────────────────────


def _ensure_sounds() -> dict[str, Path]:
    """Generate small wav files in ~/.chibi-mcp/sounds/ on first need."""
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "bubble": SOUND_DIR / "bubble.wav",
        "slice": SOUND_DIR / "slice.wav",
        "squish": SOUND_DIR / "squish.wav",
        "gacha": SOUND_DIR / "gacha.wav",
        "rare": SOUND_DIR / "rare.wav",
        "option": SOUND_DIR / "option.wav",
    }
    version_file = SOUND_DIR / ".version"
    regenerate = version_file.read_text(encoding="utf-8").strip() != SOUND_VERSION if version_file.exists() else True
    writers = {
        "bubble": _write_bubble_wav,
        "slice": _write_slice_wav,
        "squish": _write_squish_wav,
        "gacha": _write_gacha_wav,
        "rare": _write_rare_wav,
        "option": _write_option_wav,
    }
    for key, path in paths.items():
        if regenerate or not path.exists():
            writers[key](path)
    version_file.write_text(SOUND_VERSION, encoding="utf-8")
    return paths


def _write_wav(path: Path, samples: list[int] | bytearray, sr: int = 22050) -> None:
    if isinstance(samples, bytearray):
        frames = bytes(samples)
    else:
        frames = b"".join(struct.pack("<h", max(-32768, min(32767, sample))) for sample in samples)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(frames)


def _noise(seed: int, i: int) -> float:
    # Cheap deterministic pseudo-noise so generated sounds are stable.
    x = math.sin((i + 1) * (seed * 12.9898 + 78.233)) * 43758.5453
    return (x - math.floor(x)) * 2 - 1


def _write_bubble_wav(path: Path) -> None:
    """Soft gel bubble pop."""
    sr = 22050
    duration = 0.34
    n = int(sr * duration)
    samples: list[int] = []
    for i in range(n):
        t = i / sr
        env_t = i / n
        if env_t < 0.5:
            freq = 260 + (620 - 260) * (env_t * 2)
        else:
            freq = 620 - (620 - 420) * ((env_t - 0.5) * 2)
        env = (1.0 - abs(2 * env_t - 1)) ** 1.3
        wobble = math.sin(2 * math.pi * 9 * t) * 22
        tone = math.sin(2 * math.pi * (freq + wobble) * t)
        samples.append(int(0.26 * 32767 * env * tone))
    _write_wav(path, samples, sr)


def _write_slice_wav(path: Path) -> None:
    """Soft milestone tick with airy texture."""
    sr = 22050
    duration = 0.26
    n = int(sr * duration)
    samples: list[int] = []
    for i in range(n):
        t = i / sr
        env_t = i / n
        freq = 1800 - 1350 * env_t
        env = (1.0 - env_t) ** 1.55
        scrape = math.sin(2 * math.pi * freq * t) * 0.34
        flour = _noise(3, i) * 0.66
        samples.append(int(0.24 * 32767 * env * (scrape + flour)))
    _write_wav(path, samples, sr)


def _write_squish_wav(path: Path) -> None:
    """Low, wet squish for double-clicking the pet."""
    sr = 22050
    duration = 0.42
    n = int(sr * duration)
    samples: list[int] = []
    for i in range(n):
        t = i / sr
        env_t = i / n
        env = math.sin(math.pi * env_t) ** 0.45
        freq = 95 + 55 * math.sin(2 * math.pi * 3.2 * t)
        tone = math.sin(2 * math.pi * freq * t)
        slap = _noise(7, i) * max(0.0, 1.0 - env_t * 2.3)
        samples.append(int(0.31 * 32767 * env * (tone * 0.72 + slap * 0.28)))
    _write_wav(path, samples, sr)


def _write_gacha_wav(path: Path) -> None:
    """Small capsule roll and pop for normal pulls."""
    sr = 22050
    duration = 0.72
    n = int(sr * duration)
    samples: list[int] = []
    notes = [392, 494, 587]
    for i in range(n):
        t = i / sr
        env_t = i / n
        note = notes[min(len(notes) - 1, int(env_t * len(notes)))]
        pop_env = max(0.0, 1.0 - abs((env_t - 0.72) / 0.18)) ** 2
        roll_env = max(0.0, 1.0 - env_t) ** 1.4
        bell = math.sin(2 * math.pi * note * t) * pop_env
        roll = _noise(11, i) * roll_env * 0.42
        samples.append(int(0.24 * 32767 * (bell + roll)))
    _write_wav(path, samples, sr)


def _write_rare_wav(path: Path) -> None:
    """Brighter sparkle reveal for rare pulls."""
    sr = 22050
    duration = 0.95
    n = int(sr * duration)
    samples: list[int] = []
    notes = [523, 659, 784, 1046]
    for i in range(n):
        t = i / sr
        env_t = i / n
        note = notes[min(len(notes) - 1, int(env_t * len(notes)))]
        attack = min(1.0, env_t * 8)
        decay = (1.0 - env_t) ** 0.65
        env = attack * decay
        shimmer = math.sin(2 * math.pi * note * t) + 0.45 * math.sin(2 * math.pi * note * 2.01 * t)
        sparkle = _noise(17, i) * max(0.0, math.sin(math.pi * env_t)) * 0.18
        samples.append(int(0.22 * 32767 * env * (shimmer * 0.74 + sparkle)))
    _write_wav(path, samples, sr)


def _write_option_wav(path: Path) -> None:
    """Sticky syrup/glaze brush for option changes."""
    sr = 22050
    duration = 0.5
    n = int(sr * duration)
    samples: list[int] = []
    for i in range(n):
        t = i / sr
        env_t = i / n
        env = math.sin(math.pi * env_t) ** 0.7
        sticky = math.sin(2 * math.pi * (150 + 70 * env_t) * t)
        brush = _noise(23, i) * 0.5
        samples.append(int(0.2 * 32767 * env * (sticky * 0.5 + brush * 0.5)))
    _write_wav(path, samples, sr)


def _play_sound(path: Path) -> None:
    """Fire-and-forget short wav playback. Silently no-ops if unsupported."""
    if not path.exists():
        return
    try:
        if sys.platform == "darwin":
            subprocess.Popen(
                ["afplay", str(path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif sys.platform == "win32":
            import winsound

            winsound.PlaySound(
                str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
            )
        else:
            # Linux — try paplay (PulseAudio) then aplay (ALSA)
            for player in ("paplay", "aplay"):
                try:
                    subprocess.Popen(
                        [player, str(path)],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return
                except FileNotFoundError:
                    continue
    except (OSError, FileNotFoundError) as e:
        log.debug("sound playback failed: %s", e)


# ── WebSocket subscriber thread ──────────────────────────────────────────────


def _ws_listener(url: str, event_queue: queue.Queue, stop_event: threading.Event) -> None:
    try:
        from websockets.sync.client import connect as ws_connect
    except ImportError:
        log.warning("websockets sync client unavailable — window won't get live updates")
        event_queue.put({"type": "connection", "connected": False})
        return

    backoff = RECONNECT_BACKOFF_MIN_S
    connected = False
    while not stop_event.is_set():
        try:
            with ws_connect(url, open_timeout=3) as conn:
                if not connected:
                    event_queue.put({"type": "connection", "connected": True})
                    connected = True
                backoff = RECONNECT_BACKOFF_MIN_S  # reset on successful connect
                for raw in conn:
                    if stop_event.is_set():
                        return
                    try:
                        event_queue.put_nowait(json.loads(raw))
                    except json.JSONDecodeError as e:
                        log.debug("ws drop (bad json): %s", e)
                    except queue.Full:
                        log.debug("ws drop (queue full: %d)", event_queue.qsize())
                if connected:
                    event_queue.put({"type": "connection", "connected": False})
                    connected = False
        except Exception as e:
            log.debug("ws reconnect in %.1fs after error: %s", backoff, e)
            if connected:
                event_queue.put({"type": "connection", "connected": False})
                connected = False
        if stop_event.wait(backoff):
            return
        backoff = min(RECONNECT_BACKOFF_MAX_S, backoff * 1.7)


def _send_ws_action(url: str | None, message: dict, event_queue: queue.Queue) -> None:
    """Send one small desktop action to the MCP WebSocket server."""
    if not url:
        event_queue.put({"type": "connection", "connected": False})
        event_queue.put({"type": "say", "text": "서버 연결이 필요해"})
        return
    try:
        from websockets.sync.client import connect as ws_connect
    except ImportError:
        event_queue.put({"type": "connection", "connected": False})
        event_queue.put({"type": "say", "text": "websockets 설치가 필요해"})
        return

    try:
        with ws_connect(url, open_timeout=3) as conn:
            conn.send(json.dumps(message, ensure_ascii=False))
    except Exception as exc:
        log.debug("window action send failed: %s", exc)
        event_queue.put({"type": "connection", "connected": False})
        event_queue.put({"type": "say", "text": "서버에 연결하지 못했어"})


def _load_json_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _load_persisted_state() -> dict:
    return _load_json_file(Path.home() / ".chibi-mcp" / "state.json")


def _load_catalog(asset_dir: Path | None) -> dict:
    if asset_dir is None:
        return {}
    return _load_json_file(asset_dir / "meta.json")


def _released_items(catalog: dict, key: str) -> list[dict]:
    items = catalog.get(key)
    if not isinstance(items, list):
        return []
    return [
        item
        for item in items
        if isinstance(item, dict) and not item.get("locked") and item.get("tier") == "free"
    ]


class ChibiButton(tk.Canvas):
    """Small drawn pill button, avoiding platform-native Tk button chrome."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command,
        colors: dict[str, str],
        *,
        panel_bg: str,
        icon: str | None = None,
        min_width: int = 70,
        anchor: str = "center",
    ):
        self._text = text
        self._command = command
        self._colors = colors
        self._icon = icon
        self._base_min_width = min_width
        self._base_button_height = 34
        self._scale = 1.0
        self._min_width = min_width
        self._button_height = self._base_button_height
        self._anchor = anchor
        self._tone = "bg"
        self._enabled = True
        self._focused = False
        super().__init__(
            parent,
            width=min_width,
            height=self._button_height,
            bg=panel_bg,
            bd=0,
            highlightthickness=0,
            takefocus=1,
        )
        with contextlib.suppress(tk.TclError):
            self.configure(cursor="hand2")
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", lambda _event: self._set_tone("hover"))
        self.bind("<Leave>", lambda _event: self._set_tone("bg"))
        self.bind("<ButtonPress-1>", lambda _event: self._set_tone("active"))
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<FocusIn>", lambda _event: self._set_focus(True))
        self.bind("<FocusOut>", lambda _event: self._set_focus(False))
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())
        self._draw()

    def set_scale(self, scale: float) -> None:
        scale = _clamp_window_scale(scale)
        if abs(scale - self._scale) < 0.01:
            return
        self._scale = scale
        self._min_width = max(44, round(self._base_min_width * scale))
        self._button_height = max(24, round(self._base_button_height * scale))
        self.configure(width=self._min_width, height=self._button_height)
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        with contextlib.suppress(tk.TclError):
            self.configure(cursor="hand2" if enabled else "")
        self._draw()

    def set_style(
        self,
        colors: dict[str, str],
        *,
        icon: str | None = None,
        text: str | None = None,
    ) -> None:
        self._colors = colors
        self._icon = icon
        if text is not None:
            self._text = text
        self._tone = "bg"
        self._draw()

    def invoke(self) -> None:
        if self._enabled:
            self._command()

    def _release(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._set_tone("hover")
        self.invoke()

    def _set_tone(self, tone: str) -> None:
        if not self._enabled:
            return
        self._tone = tone
        self._draw()

    def _set_focus(self, focused: bool) -> None:
        self._focused = focused
        self._draw()

    def _rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, splinesteps=12, **kwargs)

    def _s(self, value: int) -> int:
        return max(1, round(value * self._scale))

    def _draw(self) -> None:
        width = max(self._min_width, int(self.winfo_width() or self._min_width))
        height = self._button_height
        self.delete("all")
        press_offset = self._s(2) if self._enabled and self._tone == "active" else 0

        if self._enabled:
            fill = self._colors[self._tone]
            fg = self._colors["fg"]
            shadow = self._colors["shadow"]
            border = self._colors["border"]
            icon_bg = self._colors["icon_bg"]
        else:
            fill = BUTTON_DISABLED_BG
            fg = BUTTON_DISABLED_FG
            shadow = "#d7c8b9"
            border = "#d6c4b2"
            icon_bg = "#e8d9ca"

        self._rounded_rect(
            self._s(3),
            self._s(5),
            width - self._s(2),
            height - self._s(1),
            self._s(13),
            fill=shadow,
            outline="",
        )
        self._rounded_rect(
            self._s(1),
            self._s(1) + press_offset,
            width - self._s(3),
            height - self._s(5) + press_offset,
            self._s(13),
            fill=fill,
            outline=border,
            width=max(1, self._s(1)),
        )
        if self._enabled:
            self.create_line(
                self._s(12),
                self._s(6) + press_offset,
                width - self._s(14),
                self._s(6) + press_offset,
                fill="#ffffff",
                width=max(1, self._s(1)),
                capstyle="round",
            )
        if self._focused and self._enabled:
            self._rounded_rect(
                self._s(3),
                self._s(3) + press_offset,
                width - self._s(5),
                height - self._s(7) + press_offset,
                self._s(11),
                fill="",
                outline=TEXT_FG,
                width=max(1, self._s(1)),
            )

        text_anchor = "center"
        text_x = width // 2
        center_y = height // 2 - self._s(1) + press_offset // 2
        if self._anchor == "w":
            text_anchor = "w"
            text_x = self._s(16 if not self._colors.get("indicator") else 20)

        if self._colors.get("indicator"):
            self._rounded_rect(
                self._s(8),
                self._s(10) + press_offset,
                self._s(12),
                height - self._s(10) + press_offset,
                self._s(3),
                fill=self._colors["indicator"],
                outline="",
            )

        if self._icon:
            icon_left = self._s(8)
            icon_size = self._s(17)
            icon_center = icon_left + icon_size // 2
            self.create_oval(
                icon_left,
                center_y - icon_size // 2,
                icon_left + icon_size,
                center_y + icon_size // 2,
                fill=icon_bg,
                outline="",
            )
            self.create_text(
                icon_center,
                center_y,
                text=self._icon,
                fill=fg,
                font=("Helvetica", max(6, self._s(8)), "bold"),
            )
            text_x = width // 2 + self._s(9) if self._anchor != "w" else self._s(32)
            text_anchor = "center" if self._anchor != "w" else "w"

        self.create_text(
            text_x,
            center_y,
            text=self._text,
            anchor=text_anchor,
            fill=fg,
            font=("Helvetica", max(7, self._s(9)), "bold"),
        )


class ChibiStatusCard(tk.Canvas):
    """Compact identity/status surface for the floating pet."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        name: str,
        rarity: int,
        mood: str,
        width: int,
        panel_bg: str,
    ):
        self._display_name = name
        self._rarity = rarity
        self._mood = mood
        self._progress = "리듬 준비"
        self._system_hud = "CPU -- · RAM -- · BAT --"
        self._system_warn = False
        self._rhythm_fraction = 0.0
        self._metric_values: dict[str, int | None] = {"CPU": None, "RAM": None, "BAT": None}
        self._metric_alerts: set[str] = set()
        self._connection_ok = False
        self._debug_hud = "상세 준비"
        self._view_mode = "normal"
        self._card_width = width
        self._normal_card_height = 122
        self._debug_card_height = 158
        self._scale = 1.0
        self._card_height = self._scaled_card_height()
        super().__init__(
            parent,
            width=width,
            height=self._card_height,
            bg=panel_bg,
            bd=0,
            highlightthickness=0,
        )
        self.bind("<Configure>", lambda _event: self._draw())
        self._draw()

    def _base_card_height(self) -> int:
        return self._debug_card_height if self._view_mode == "debug" else self._normal_card_height

    def _scaled_card_height(self) -> int:
        minimum = 80 if self._view_mode == "debug" else 60
        return max(minimum, round(self._base_card_height() * self._scale))

    def set_scale(self, scale: float) -> None:
        scale = _clamp_window_scale(scale)
        if abs(scale - self._scale) < 0.01:
            return
        self._scale = scale
        self._card_height = self._scaled_card_height()
        self.configure(height=self._card_height)
        self._draw()

    def set_view_mode(self, mode: str) -> None:
        mode = _normalize_view_mode(mode)
        if mode == "compact":
            mode = "normal"
        if mode == self._view_mode:
            return
        self._view_mode = mode
        self._card_height = self._scaled_card_height()
        self.configure(height=self._card_height)
        self._draw()

    def set_mood(self, mood: str) -> None:
        self._mood = mood
        self._draw()

    def set_identity(self, *, name: str, rarity: int) -> None:
        self._display_name = name
        self._rarity = rarity
        self._draw()

    def set_connection(self, connected: bool) -> None:
        if self._connection_ok == connected:
            return
        self._connection_ok = connected
        self._draw()

    def set_progress(
        self,
        progress: str,
        *,
        system_hud: str | None = None,
        system_warn: bool | None = None,
        debug_hud: str | None = None,
        rhythm_fraction: float | None = None,
        metric_values: dict[str, int | None] | None = None,
        metric_alerts: set[str] | None = None,
    ) -> None:
        self._progress = progress or "리듬 준비"
        if system_hud is not None:
            self._system_hud = system_hud or "CPU -- · RAM -- · BAT --"
        if system_warn is not None:
            self._system_warn = system_warn
        if debug_hud is not None:
            self._debug_hud = debug_hud or "상세 준비"
        if rhythm_fraction is not None:
            self._rhythm_fraction = max(0.0, min(1.0, float(rhythm_fraction)))
        if metric_values is not None:
            self._metric_values = {key: metric_values.get(key) for key in ("CPU", "RAM", "BAT")}
        if metric_alerts is not None:
            self._metric_alerts = set(metric_alerts)
        self._draw()

    def _rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, splinesteps=12, **kwargs)

    def _s(self, value: int) -> int:
        return max(1, round(value * self._scale))

    def _fit_text(self, text: str, font: tuple, max_width: int) -> str:
        if max_width <= self._s(12):
            return "…"
        try:
            font_obj = tkfont.Font(font=font)
        except tk.TclError:
            return text
        if font_obj.measure(text) <= max_width:
            return text
        clipped = text
        while clipped and font_obj.measure(f"{clipped}…") > max_width:
            clipped = clipped[:-1]
        return f"{clipped}…" if clipped else "…"

    def _status_chip(self) -> tuple[str, str, str, str]:
        if not self._connection_ok:
            return ("오프", "#f6eee6", "#cdbdaa", "#806f62")
        if self._system_warn:
            return ("주의", STATUS_WARN_BG, STATUS_WARN_BORDER, "#77521b")
        return ("정상", STATUS_METRIC_BG, STATUS_METRIC_BORDER, "#4b725d")

    def _meter_color(self, label: str, value: int | None) -> str:
        if label in self._metric_alerts:
            return METER_DANGER
        if value is None:
            return "#cdbdaa"
        if label == "BAT" and value < 35:
            return METER_WARN
        if label == "CPU" and value >= 65:
            return METER_WARN
        if label == "RAM" and value >= 80:
            return METER_WARN
        return METER_GOOD

    def _draw_metric_meter(
        self,
        *,
        label: str,
        value: int | None,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> None:
        alert = label in self._metric_alerts
        fill = STATUS_WARN_BG if alert else STATUS_METRIC_BG
        outline = STATUS_WARN_BORDER if alert else STATUS_METRIC_BORDER
        self._rounded_rect(
            x1,
            y1,
            x2,
            y2,
            self._s(8),
            fill=fill,
            outline=outline,
            width=max(1, self._s(1)),
            tags=("metric_meter",),
        )
        self.create_text(
            x1 + self._s(9),
            y1 + self._s(10),
            text=label,
            anchor="w",
            fill="#6f5d50",
            font=("Helvetica", max(5, self._s(7)), "bold"),
            tags=("metric_meter",),
        )
        value_text = "--" if value is None else f"{value}%"
        self.create_text(
            x2 - self._s(8),
            y1 + self._s(10),
            text=value_text,
            anchor="e",
            fill=TEXT_FG if value is not None else "#9b8b7d",
            font=("Helvetica", max(6, self._s(8)), "bold"),
            tags=("metric_meter",),
        )
        track_x1 = x1 + self._s(8)
        track_x2 = x2 - self._s(8)
        track_y1 = y2 - self._s(8)
        track_y2 = y2 - self._s(4)
        self._rounded_rect(
            track_x1,
            track_y1,
            track_x2,
            track_y2,
            self._s(3),
            fill=METER_TRACK,
            outline="",
            tags=("metric_meter",),
        )
        if value is not None:
            fill_w = max(self._s(3), round((track_x2 - track_x1) * (value / 100)))
            self._rounded_rect(
                track_x1,
                track_y1,
                min(track_x2, track_x1 + fill_w),
                track_y2,
                self._s(3),
                fill=self._meter_color(label, value),
                outline="",
                tags=("metric_meter",),
            )

    def _draw(self) -> None:
        width = max(self._s(280), int(self.winfo_width() or self._card_width))
        height = self._card_height
        mood_label, mood_icon = MOOD_LABELS.get(self._mood, (self._mood, "•"))
        stars = "★" * self._rarity + "☆" * max(0, 5 - self._rarity)
        mood_glow, _shadow = MOOD_STAGE_COLORS.get(self._mood, MOOD_STAGE_COLORS["calm"])
        status_text, status_fill, status_outline, status_fg = self._status_chip()

        self.delete("all")
        self._rounded_rect(
            self._s(6),
            self._s(8),
            width - self._s(5),
            height - self._s(2),
            self._s(18),
            fill=STATUS_SHADOW,
            outline="",
        )
        self._rounded_rect(
            self._s(3),
            self._s(2),
            width - self._s(8),
            height - self._s(8),
            self._s(18),
            fill=STATUS_BG,
            outline=STATUS_BORDER,
            width=max(1, self._s(1)),
        )
        self._rounded_rect(
            self._s(10),
            self._s(8),
            self._s(15),
            height - self._s(18),
            self._s(4),
            fill=mood_glow,
            outline="",
        )
        self.create_text(
            self._s(18),
            self._s(20),
            text=self._display_name,
            anchor="w",
            fill=TEXT_FG,
            font=("Helvetica", max(9, self._s(13)), "bold"),
        )
        self.create_text(
            width - self._s(24),
            self._s(20),
            text=stars,
            anchor="e",
            fill="#5f4d3f",
            font=("Helvetica", max(7, self._s(10)), "bold"),
        )

        self._rounded_rect(
            self._s(16),
            self._s(38),
            self._s(92),
            self._s(60),
            self._s(10),
            fill=STATUS_CHIP_BG,
            outline=STATUS_CHIP_BORDER,
            width=max(1, self._s(1)),
        )
        self.create_text(
            self._s(54),
            self._s(49),
            text=f"{mood_label} {mood_icon}",
            fill=TEXT_FG,
            font=("Helvetica", max(7, self._s(9)), "bold"),
        )
        status_x1 = max(self._s(210), width - self._s(78))
        status_x2 = width - self._s(22)
        self._rounded_rect(
            status_x1,
            self._s(38),
            status_x2,
            self._s(60),
            self._s(10),
            fill=status_fill,
            outline=status_outline,
            width=max(1, self._s(1)),
            tags=("status_pill",),
        )
        status_chip_w = status_x2 - status_x1
        dot_x1 = status_x1 + self._s(8)
        if status_chip_w < self._s(46):
            dot_x1 = status_x1 + status_chip_w // 2 - self._s(3)
        self.create_oval(
            dot_x1,
            self._s(46),
            dot_x1 + self._s(6),
            self._s(52),
            fill=METER_DANGER if self._system_warn else METER_GOOD,
            outline="",
            tags=("status_pill",),
        )
        if status_chip_w >= self._s(46):
            self.create_text(
                status_x1 + self._s(18),
                self._s(49),
                text=status_text,
                anchor="w",
                fill=status_fg,
                font=("Helvetica", max(6, self._s(8)), "bold"),
                tags=("status_pill",),
            )

        progress_font = ("Helvetica", max(7, self._s(9)))
        progress_max = max(self._s(72), status_x1 - self._s(112))
        self.create_text(
            self._s(104),
            self._s(49),
            text=self._fit_text(self._progress, progress_font, progress_max),
            anchor="w",
            fill=MUTED_FG,
            font=progress_font,
            tags=("progress_text",),
        )

        self.create_text(
            self._s(18),
            self._s(73),
            text="리듬",
            anchor="w",
            fill="#6f5d50",
            font=("Helvetica", max(6, self._s(8)), "bold"),
            tags=("rhythm_meter",),
        )
        bar_x1 = self._s(56)
        bar_x2 = width - self._s(24)
        bar_y1 = self._s(70)
        bar_y2 = self._s(77)
        self._rounded_rect(
            bar_x1,
            bar_y1,
            bar_x2,
            bar_y2,
            self._s(4),
            fill="#ead7c3",
            outline="",
            tags=("rhythm_meter",),
        )
        fill_x2 = bar_x1 + max(self._s(4), round((bar_x2 - bar_x1) * self._rhythm_fraction))
        self._rounded_rect(
            bar_x1,
            bar_y1,
            min(bar_x2, fill_x2),
            bar_y2,
            self._s(4),
            fill="#ff6b9d" if self._rhythm_fraction >= 0.8 else "#55bd83",
            outline="",
            tags=("rhythm_meter",),
        )

        meter_y1 = self._s(88)
        meter_y2 = self._s(113)
        gap = self._s(6)
        meter_x1 = self._s(16)
        available = width - self._s(36) - gap * 2
        meter_w = max(self._s(70), available // 3)
        for idx, label in enumerate(("CPU", "RAM", "BAT")):
            x1 = meter_x1 + idx * (meter_w + gap)
            self._draw_metric_meter(
                label=label,
                value=self._metric_values.get(label),
                x1=x1,
                y1=meter_y1,
                x2=min(width - self._s(20), x1 + meter_w),
                y2=meter_y2,
            )

        if self._view_mode == "debug":
            self._rounded_rect(
                self._s(16),
                self._s(120),
                width - self._s(20),
                height - self._s(10),
                self._s(8),
                fill="#eef4ff",
                outline="#b9c9ed",
                width=max(1, self._s(1)),
            )
            self.create_text(
                self._s(28),
                height - self._s(23),
                text=self._debug_hud,
                anchor="w",
                fill="#41506b",
                font=("Helvetica", max(6, self._s(8)), "bold"),
            )


# ── Tk window ────────────────────────────────────────────────────────────────


class PetWindow:
    def __init__(
        self,
        image_path: Path,
        name: str,
        rarity: int,
        mood: str,
        option_paths: list[Path] | None = None,
        asset_dir: Path | None = None,
        character_id: str | None = None,
        active_option_ids: list[str] | None = None,
        frameless: bool = True,
        sounds: bool = True,
        view_mode: str | None = None,
    ):
        self.image_path = image_path
        self.name = name
        self.rarity = rarity
        self.current_mood = mood
        self.option_paths = option_paths or []
        self.asset_dir = asset_dir
        self.character_id = character_id
        self.active_option_ids = active_option_ids or []
        self.catalog = _load_catalog(asset_dir)
        self.ws_url: str | None = None
        self.drawer_mode: str | None = None
        self.view_mode = _initial_view_mode(view_mode)
        self.connection_ok = False
        self._drawer_render_signature: tuple | None = None
        self.frameless = frameless
        self.sounds_enabled = _initial_sounds_enabled(sounds)
        self.topmost_enabled = _initial_topmost_enabled()

        self._initial_window_scale_value = _initial_window_scale()
        self._window_scale = 1.0
        self._render_max_side = CANVAS_SIZE - 20
        self._base_total_w = CANVAS_SIZE + 72
        self._base_total_h = 1
        self._layout_ready = False
        self._suspend_resize_events = False
        self._resize_after: str | None = None
        self._resize_start: tuple[int, int, float] | None = None
        self._drag_start: tuple[int, int, tk.Misc] | None = None
        self._drag_moved = False
        self._last_state_payload: dict = {}
        self._last_pull_signature: str | None = None
        self._mood_fx_items: list[int] = []
        self._last_bob_offset = 0
        self._mood_fx_phase = 0
        # Cache ((mood, max_side) → rendered RGBA). Variants bypass filter.
        self._mood_image_cache: dict[tuple[str, int], Image.Image] = {}
        self._option_cache: dict[tuple[int, int], list[Image.Image]] = {}
        self.base_image = self._get_mood_image(mood)
        self._img_w, self._img_h = self.base_image.size
        self._base_total_w = max(CANVAS_SIZE + 72, self._img_w + 80)

        self.event_queue: queue.Queue = queue.Queue(maxsize=64)
        self.stop_event = threading.Event()

        # Generate sounds on demand
        self._sound_paths: dict[str, Path] = {}
        if self.sounds_enabled:
            try:
                self._sound_paths = _ensure_sounds()
            except (OSError, wave.Error) as e:
                log.warning("sound generation failed: %s", e)

        self.root = tk.Tk()
        self.root.title(f"chibi — {name}")
        self._set_topmost_attribute(self.topmost_enabled)

        # Use a light panel by default. macOS PyObjC clear-window hacks are
        # disabled completely because incompatible Python/Tk/PyObjC builds can
        # crash the whole interpreter in native code.
        self._transparent = False

        bg = PANEL_BG
        self.root.configure(bg=bg)

        # Frameless mode
        if self.frameless:
            with contextlib.suppress(tk.TclError):
                self.root.overrideredirect(True)
            # macOS workaround: re-assert topmost after overrideredirect
            self.root.update_idletasks()
            self._set_topmost_attribute(self.topmost_enabled)

        # Keep the attribute for diagnostics/backward compatibility, but never
        # enter PyObjC from the shipped runtime.
        self._macos_clear = False
        if sys.platform == "darwin":
            self._macos_clear = _macos_make_transparent(self.root)

        # Total window: character stage + compact identity/status card.
        total_w, canvas_h = self._stage_dimensions()

        self.canvas = tk.Canvas(
            self.root,
            width=total_w,
            height=canvas_h,
            bg=bg,
            borderwidth=0,
            highlightthickness=0,
        )
        self.canvas.pack()
        self._canvas_center = (total_w // 2, canvas_h // 2)

        self._stage_glow_id = self.canvas.create_oval(
            0,
            0,
            1,
            1,
            fill=MOOD_STAGE_COLORS.get(mood, MOOD_STAGE_COLORS["calm"])[0],
            outline="",
            stipple="gray25",
            tags=("stage_glow",),
        )
        shadow_w, shadow_y = self._shadow_metrics(total_w, canvas_h)
        self._shadow_id = self.canvas.create_oval(
            self._canvas_center[0] - shadow_w // 2,
            shadow_y - self._s(5),
            self._canvas_center[0] + shadow_w // 2,
            shadow_y + self._s(5),
            fill=MOOD_STAGE_COLORS.get(mood, MOOD_STAGE_COLORS["calm"])[1],
            outline="",
            stipple="gray50",
        )

        self._photo = ImageTk.PhotoImage(self._get_mood_image(mood))
        self._image_id = self.canvas.create_image(
            self._canvas_center[0],
            self._canvas_center[1],
            image=self._photo,
            anchor="center",
        )
        self._refresh_mood_fx(force=True)
        self._update_stage_chrome()

        self.status_card = ChibiStatusCard(
            self.root,
            name=name,
            rarity=rarity,
            mood=mood,
            width=total_w - 20,
            panel_bg=bg,
        )
        self.status_card.pack(pady=(2, 8), padx=10, fill="x")

        self.toolbar = tk.Frame(self.root, bg=bg)
        self.toolbar.pack(pady=(0, 10), padx=8)
        self.inventory_button = self._make_button(
            self.toolbar,
            "보관함",
            lambda: self._toggle_drawer("inventory"),
            icon="▣",
            min_width=74,
        )
        self.inventory_button.pack(side="left", padx=3)
        self.options_button = self._make_button(
            self.toolbar,
            "옵션",
            lambda: self._toggle_drawer("options"),
            icon="✦",
            min_width=68,
        )
        self.options_button.pack(side="left", padx=3)
        self.settings_button = self._make_button(
            self.toolbar,
            "설정",
            lambda: self._toggle_drawer("settings"),
            icon="⚙",
            min_width=62,
        )
        self.settings_button.pack(side="left", padx=3)
        mode_text, mode_icon = VIEW_MODE_BUTTONS[self.view_mode]
        self.mode_button = self._make_button(
            self.toolbar,
            mode_text,
            self._cycle_view_mode,
            kind="selected" if self.view_mode != "normal" else "secondary",
            icon=mode_icon,
            min_width=62,
        )
        self.mode_button.pack(side="left", padx=3)
        self.pull_button = self._make_button(
            self.toolbar, "뽑기", self._pull_from_window, kind="primary", icon="★", min_width=68
        )
        self.pull_button.pack(side="left", padx=3)
        self.close_button = self._make_button(
            self.toolbar, "닫기", self.shutdown, kind="danger", icon="x", min_width=68
        )
        self.close_button.pack(side="left", padx=3)

        self.drawer = tk.Frame(
            self.root,
            bg=PANEL_BG_2,
            highlightthickness=1,
            highlightbackground=PANEL_BORDER,
            padx=8,
            pady=8,
        )

        # Speech bubble
        self.bubble = tk.Label(
            self.root,
            text="",
            bg="#fffdf7",
            fg=TEXT_FG,
            font=("Helvetica", 10),
            wraplength=total_w - 30,
            padx=10,
            pady=6,
            relief="solid",
            borderwidth=1,
        )
        self._bubble_hide_after: str | None = None

        self.resize_grip = tk.Canvas(
            self.root,
            width=self._s(RESIZE_GRIP_SIZE),
            height=self._s(RESIZE_GRIP_SIZE),
            bg=bg,
            borderwidth=0,
            highlightthickness=0,
        )
        with contextlib.suppress(tk.TclError):
            self.resize_grip.configure(cursor="bottom_right_corner")
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se")
        self.resize_grip.bind("<Button-1>", self._start_resize)
        self.resize_grip.bind("<B1-Motion>", self._do_resize)
        self.resize_grip.bind("<ButtonRelease-1>", self._end_resize)
        self.resize_grip.bind("<Double-Button-1>", lambda _event: self._reset_window_scale())
        self._draw_resize_grip()

        # Bind drag + clicks on canvas and labels
        for w in (self.canvas, self.status_card):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._do_drag)
            w.bind("<ButtonRelease-1>", self._end_drag)
            w.bind("<Button-3>", lambda _e: self.shutdown())  # right-click close
        self.canvas.bind("<Double-Button-1>", self._squish)

        self.root.bind("<Escape>", lambda _e: self.shutdown())
        self.root.bind("<Command-w>", lambda _e: self.shutdown())
        self.root.bind("<Control-w>", lambda _e: self.shutdown())
        self.root.bind("<Command-plus>", lambda _e: self._nudge_window_scale(0.1))
        self.root.bind("<Command-equal>", lambda _e: self._nudge_window_scale(0.1))
        self.root.bind("<Control-plus>", lambda _e: self._nudge_window_scale(0.1))
        self.root.bind("<Control-equal>", lambda _e: self._nudge_window_scale(0.1))
        self.root.bind("<Command-minus>", lambda _e: self._nudge_window_scale(-0.1))
        self.root.bind("<Control-minus>", lambda _e: self._nudge_window_scale(-0.1))
        self.root.bind("<Command-0>", lambda _e: self._reset_window_scale())
        self.root.bind("<Control-0>", lambda _e: self._reset_window_scale())
        self.root.bind("<Command-m>", lambda _e: self._cycle_view_mode())
        self.root.bind("<Control-m>", lambda _e: self._cycle_view_mode())
        with contextlib.suppress(tk.TclError):
            self.root.bind("<Command-comma>", lambda _e: self._toggle_drawer("settings"))
            self.root.bind("<Control-comma>", lambda _e: self._toggle_drawer("settings"))
        self.root.bind("<Configure>", self._on_root_configure)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        with contextlib.suppress(tk.TclError):
            self.root.update_idletasks()
            self._base_total_w = max(self._base_total_w, self.root.winfo_width())
            self._base_total_h = max(1, self.root.winfo_height())
            self.root.minsize(
                round(self._base_total_w * WINDOW_MIN_SCALE),
                round(self._base_total_h * WINDOW_MIN_SCALE),
            )

        # Idle bob state
        self._bob_phase = 0.0
        # Track pending after() callbacks so shutdown can cancel them and
        # avoid "invalid command name" errors firing on the destroyed root.
        self._after_ids: set[str] = set()
        self._layout_ready = True
        self._apply_window_scale(self._initial_window_scale_value, persist=False)
        self._apply_view_mode(self.view_mode, announce=False, persist=False)
        self._place_and_raise()

    def _place_and_raise(self) -> None:
        """Make the first window placement visible on desktop launch."""
        with contextlib.suppress(tk.TclError):
            self.root.update_idletasks()
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            win_w = self.root.winfo_width()
            win_h = self.root.winfo_height()
            restored = _window_position_from_prefs(
                screen_w=screen_w,
                screen_h=screen_h,
                win_w=win_w,
                win_h=win_h,
            )
            if restored is None:
                x = max(24, screen_w - win_w - 40)
                y = WINDOW_DEFAULT_POSITION_Y
            else:
                x, y = restored
            self.root.geometry(f"+{x}+{y}")
            self.root.lift()
            self._set_topmost_attribute(self.topmost_enabled)
            self.root.focus_force()
            self._after(250, self.root.lift)

    def _set_topmost_attribute(self, enabled: bool) -> None:
        with contextlib.suppress(tk.TclError):
            self.root.attributes("-topmost", bool(enabled))

    def _save_window_layout(self, **extra: object) -> None:
        data: dict[str, object] = {"window_scale": round(self._window_scale, 2)}
        with contextlib.suppress(tk.TclError):
            data["position"] = {"x": self.root.winfo_x(), "y": self.root.winfo_y()}
        data.update(extra)
        _save_window_prefs(data)

    # ── Rendering ────────────────────────────────────────────────────────────

    def _s(self, value: int) -> int:
        return max(1, round(value * self._window_scale))

    def _stage_dimensions(self) -> tuple[int, int]:
        total_w = max(self._s(CANVAS_SIZE + 72), self._img_w + self._s(80))
        canvas_h = self._img_h + self._s(28)
        return total_w, canvas_h

    def _shadow_metrics(self, total_w: int, canvas_h: int) -> tuple[int, int]:
        shadow_w = min(total_w - self._s(52), max(self._s(80), self._img_w - self._s(16)))
        shadow_y = min(
            canvas_h - self._s(14),
            self._canvas_center[1] + self._img_h // 2 - self._s(8),
        )
        return shadow_w, shadow_y

    def _update_stage_chrome(self) -> None:
        if not hasattr(self, "canvas"):
            return
        glow, shadow = MOOD_STAGE_COLORS.get(self.current_mood, MOOD_STAGE_COLORS["calm"])
        glow_w = max(self._s(132), self._img_w + self._s(58))
        glow_h = max(self._s(92), self._img_h + self._s(38))
        glow_y = self._canvas_center[1] - self._s(4)
        shadow_w, shadow_y = self._shadow_metrics(int(self.canvas.cget("width")), int(self.canvas.cget("height")))
        with contextlib.suppress(tk.TclError):
            self.canvas.coords(
                self._stage_glow_id,
                self._canvas_center[0] - glow_w // 2,
                glow_y - glow_h // 2,
                self._canvas_center[0] + glow_w // 2,
                glow_y + glow_h // 2,
            )
            self.canvas.itemconfigure(self._stage_glow_id, fill=glow)
            self.canvas.coords(
                self._shadow_id,
                self._canvas_center[0] - shadow_w // 2,
                shadow_y - self._s(5),
                self._canvas_center[0] + shadow_w // 2,
                shadow_y + self._s(5),
            )
            self.canvas.itemconfigure(self._shadow_id, fill=shadow)
            self.canvas.tag_lower(self._stage_glow_id)
            self.canvas.tag_raise(self._shadow_id, self._stage_glow_id)
            if hasattr(self, "_image_id"):
                self.canvas.tag_raise(self._image_id, self._shadow_id)

    def _point_near_character(self, x_frac: float, y_frac: float) -> tuple[int, int]:
        left = self._canvas_center[0] - self._img_w // 2
        top = self._canvas_center[1] - self._img_h // 2
        return (
            left + round(self._img_w * x_frac),
            top + round(self._img_h * y_frac),
        )

    def _clear_mood_fx(self) -> None:
        for item in self._mood_fx_items:
            with contextlib.suppress(tk.TclError):
                self.canvas.delete(item)
        self._mood_fx_items = []

    def _add_mood_fx_item(self, item: int, *, bob: bool = True) -> None:
        self._mood_fx_items.append(item)
        with contextlib.suppress(tk.TclError):
            self.canvas.addtag_withtag("mood_fx", item)
            if bob:
                self.canvas.addtag_withtag("mood_fx_bob", item)

    def _refresh_mood_fx(self, *, force: bool = False) -> None:
        if not force and self._mood_fx_items:
            return
        if not hasattr(self, "canvas"):
            return
        self._clear_mood_fx()
        mood = self.current_mood
        if mood == "panting":
            self._draw_panting_fx()
        elif mood == "drowsy":
            self._draw_drowsy_fx()
        elif mood in {"happy", "joyful"}:
            self._draw_happy_fx(mood)
        elif mood == "lonely":
            self._draw_lonely_fx()
        elif mood == "surprised":
            self._draw_surprised_fx()
        if self._last_bob_offset:
            with contextlib.suppress(tk.TclError):
                self.canvas.move("mood_fx_bob", 0, self._last_bob_offset)
        with contextlib.suppress(tk.TclError):
            self.canvas.tag_raise("mood_fx")

    def _mood_fx_tick(self) -> None:
        if self.stop_event.is_set():
            return
        self._mood_fx_phase += 1
        phase = self._mood_fx_phase
        with contextlib.suppress(tk.TclError):
            for idx, item in enumerate(self._mood_fx_items):
                if self.current_mood in {"happy", "joyful", "surprised"}:
                    self.canvas.itemconfigure(
                        item,
                        state="hidden" if (phase + idx) % 4 == 0 else "normal",
                    )
                elif self.current_mood == "panting":
                    self.canvas.itemconfigure(
                        item,
                        width=max(1, self._s(1 + ((phase + idx) % 2))),
                    )
                elif self.current_mood == "drowsy":
                    fill = "#6f83b7" if (phase + idx) % 2 == 0 else "#94a4cf"
                    self.canvas.itemconfigure(item, fill=fill)
                elif self.current_mood == "lonely":
                    fill = "#e7e1da" if idx == 0 and phase % 2 == 0 else ""
                    if fill:
                        self.canvas.itemconfigure(item, fill=fill)
        self._after(320, self._mood_fx_tick)

    def _draw_panting_fx(self) -> None:
        for x_frac, y_frac, size in ((0.78, 0.22, 7), (0.84, 0.36, 5)):
            x, y = self._point_near_character(x_frac, y_frac)
            r = self._s(size)
            self._add_mood_fx_item(
                self.canvas.create_oval(
                    x - r,
                    y - r,
                    x + r,
                    y + r,
                    fill="#8bd3ff",
                    outline="#4da9df",
                    width=max(1, self._s(1)),
                )
            )
        for x_frac in (0.18, 0.88):
            x, y = self._point_near_character(x_frac, 0.52)
            self._add_mood_fx_item(
                self.canvas.create_line(
                    x,
                    y - self._s(18),
                    x + self._s(8),
                    y,
                    x,
                    y + self._s(18),
                    fill="#ff8b7f",
                    width=max(1, self._s(2)),
                    smooth=True,
                ),
                bob=False,
            )

    def _draw_drowsy_fx(self) -> None:
        for idx, (x_frac, y_frac) in enumerate(((0.78, 0.16), (0.86, 0.04), (0.92, -0.05))):
            x, y = self._point_near_character(x_frac, y_frac)
            self._add_mood_fx_item(
                self.canvas.create_text(
                    x,
                    y,
                    text="Z",
                    fill="#6f83b7",
                    font=("Helvetica", max(8, self._s(10 + idx * 2)), "bold"),
                )
            )

    def _draw_happy_fx(self, mood: str) -> None:
        colors = ("#ff9dbd", "#f4c542", "#55bd83", "#78a8ff")
        points = ((0.20, 0.22), (0.82, 0.18), (0.16, 0.56), (0.88, 0.54))
        for idx, (x_frac, y_frac) in enumerate(points):
            x, y = self._point_near_character(x_frac, y_frac)
            text = "✦" if mood == "joyful" or idx % 2 == 0 else "·"
            self._add_mood_fx_item(
                self.canvas.create_text(
                    x,
                    y,
                    text=text,
                    fill=colors[idx % len(colors)],
                    font=("Helvetica", max(8, self._s(11)), "bold"),
                )
            )

    def _draw_lonely_fx(self) -> None:
        x, y = self._point_near_character(0.18, 0.20)
        self._add_mood_fx_item(
            self.canvas.create_oval(
                x - self._s(15),
                y - self._s(9),
                x + self._s(18),
                y + self._s(10),
                fill="#e7e1da",
                outline="#c8bbae",
                width=max(1, self._s(1)),
            )
        )
        self._add_mood_fx_item(
            self.canvas.create_text(
                x + self._s(1),
                y - self._s(1),
                text="...",
                fill="#8d8177",
                font=("Helvetica", max(7, self._s(9)), "bold"),
            )
        )

    def _draw_surprised_fx(self) -> None:
        x, y = self._point_near_character(0.80, 0.12)
        self._add_mood_fx_item(
            self.canvas.create_text(
                x,
                y,
                text="!",
                fill="#f05f4b",
                font=("Helvetica", max(12, self._s(18)), "bold"),
            )
        )

    def _update_stage_layout(self) -> None:
        total_w, canvas_h = self._stage_dimensions()
        self.canvas.configure(width=total_w, height=canvas_h)
        self._canvas_center = (total_w // 2, canvas_h // 2)
        self.canvas.coords(self._image_id, self._canvas_center[0], self._canvas_center[1])
        shadow_w, shadow_y = self._shadow_metrics(total_w, canvas_h)
        self.canvas.coords(
            self._shadow_id,
            self._canvas_center[0] - shadow_w // 2,
            shadow_y - self._s(5),
            self._canvas_center[0] + shadow_w // 2,
            shadow_y + self._s(5),
        )
        self._update_stage_chrome()
        self.status_card.configure(width=max(self._s(260), total_w - self._s(20)))
        self._last_bob_offset = 0
        self._refresh_mood_fx(force=True)
        self.bubble.configure(
            wraplength=max(self._s(160), total_w - self._s(30)),
            font=("Helvetica", max(8, self._s(10))),
            padx=self._s(10),
            pady=self._s(6),
        )
        self._draw_resize_grip()

    def _set_control_scale(self) -> None:
        for button in (
            self.inventory_button,
            self.options_button,
            self.settings_button,
            self.mode_button,
            self.pull_button,
            self.close_button,
        ):
            button.set_scale(self._window_scale)
        self.status_card.set_scale(self._window_scale)
        if self.status_card.winfo_ismapped():
            self.status_card.pack_configure(
                pady=(self._s(2), self._s(8)),
                padx=self._s(10),
                fill="x",
            )
        self._pack_toolbar_for_mode()
        self.drawer.configure(padx=self._s(8), pady=self._s(8))
        self.toolbar.pack_configure(pady=(0, self._s(10)), padx=self._s(8))
        self._draw_resize_grip()

    def _fit_root_to_content(self) -> None:
        if not self._layout_ready:
            return
        self._suspend_resize_events = True
        try:
            with contextlib.suppress(tk.TclError):
                self.root.update_idletasks()
                width = max(self.root.winfo_reqwidth(), self._stage_dimensions()[0])
                height = self.root.winfo_reqheight()
                self.root.geometry(
                    f"{width}x{height}+{self.root.winfo_x()}+{self.root.winfo_y()}"
                )
                self.root.update_idletasks()
        finally:
            self._suspend_resize_events = False

    def _pack_status_card(self) -> None:
        if self.status_card.winfo_ismapped():
            return
        try:
            self.status_card.pack(
                pady=(self._s(2), self._s(8)),
                padx=self._s(10),
                fill="x",
                before=self.toolbar,
            )
        except (AttributeError, tk.TclError):
            self.status_card.pack(pady=(self._s(2), self._s(8)), padx=self._s(10), fill="x")

    def _pack_toolbar_for_mode(self) -> None:
        for button in (
            self.inventory_button,
            self.options_button,
            self.settings_button,
            self.mode_button,
            self.pull_button,
            self.close_button,
        ):
            button.pack_forget()
        if self.view_mode == "compact":
            buttons = (self.mode_button, self.close_button)
        else:
            buttons = (
                self.inventory_button,
                self.options_button,
                self.settings_button,
                self.mode_button,
                self.pull_button,
                self.close_button,
            )
        for button in buttons:
            button.pack(side="left", padx=self._s(3))

    def _apply_view_mode(self, mode: str, *, announce: bool = True, persist: bool = True) -> str:
        self.view_mode = _normalize_view_mode(mode)
        status_mode = "debug" if self.view_mode == "debug" else "normal"
        self.status_card.set_view_mode(status_mode)

        text, icon = VIEW_MODE_BUTTONS[self.view_mode]
        self.mode_button.set_style(
            self._button_colors("selected" if self.view_mode != "normal" else "secondary"),
            icon=icon,
            text=text,
        )

        if self.view_mode == "compact":
            self.status_card.pack_forget()
            if self.drawer.winfo_ismapped():
                self.drawer.pack_forget()
                self.drawer_mode = None
                self._drawer_render_signature = None
        else:
            self._pack_status_card()

        self._pack_toolbar_for_mode()
        self._fit_root_to_content()
        if persist:
            self._save_window_layout(view_mode=self.view_mode)
        if announce:
            labels = {"normal": "일반 모드", "debug": "상세 모드", "compact": "작게 보기"}
            self.show_bubble(labels[self.view_mode])
        return "break"

    def _cycle_view_mode(self) -> str:
        return self._apply_view_mode(_next_view_mode(self.view_mode))

    def _draw_resize_grip(self) -> None:
        if not hasattr(self, "resize_grip"):
            return
        size = self._s(RESIZE_GRIP_SIZE)
        self.resize_grip.configure(width=size, height=size)
        self.resize_grip.delete("all")
        line_width = max(1, self._s(1))
        colors = ("#d6b98c", "#ad8151", "#7c5b3c")
        for idx, color in enumerate(colors):
            offset = self._s(4 + idx * 5)
            self.resize_grip.create_line(
                size - offset,
                size - self._s(2),
                size - self._s(2),
                size - offset,
                fill=color,
                width=line_width,
                capstyle="round",
            )
        with contextlib.suppress(tk.TclError):
            self.resize_grip.tk.call("raise", self.resize_grip._w)

    def _apply_window_scale(self, scale: float, *, persist: bool = False) -> None:
        scale = _clamp_window_scale(scale)
        if abs(scale - self._window_scale) < 0.03:
            return
        self._window_scale = scale
        self._render_max_side = max(72, round((CANVAS_SIZE - 20) * scale))
        self._mood_image_cache.clear()
        self._option_cache.clear()
        self._render_image(self.current_mood)
        self._set_control_scale()
        self._update_stage_layout()
        if self.drawer_mode and self.drawer.winfo_ismapped():
            self._render_drawer()
        self._fit_root_to_content()
        if persist:
            self._save_window_layout()

    def _on_root_configure(self, event: tk.Event) -> None:
        if self._suspend_resize_events or not self._layout_ready or event.widget is not self.root:
            return
        width = int(getattr(event, "width", 0) or 0)
        if width <= 0:
            return
        next_scale = _clamp_window_scale(width / self._base_total_w)
        if abs(next_scale - self._window_scale) < 0.05:
            return
        if self._resize_after is not None:
            with contextlib.suppress(tk.TclError):
                self.root.after_cancel(self._resize_after)
            self._after_ids.discard(self._resize_after)
        self._resize_after = self._after(80, lambda scale=next_scale: self._finish_resize(scale))

    def _finish_resize(self, scale: float) -> None:
        self._resize_after = None
        self._apply_window_scale(scale, persist=True)

    def _nudge_window_scale(self, delta: float) -> str:
        self._apply_window_scale(self._window_scale + delta, persist=True)
        return "break"

    def _reset_window_scale(self) -> str:
        self._apply_window_scale(1.0, persist=True)
        return "break"

    def _get_mood_image(self, mood: str) -> Image.Image:
        cache_key = (mood, self._render_max_side)
        cached = self._mood_image_cache.get(cache_key)
        if cached is not None:
            return cached
        raw, is_variant = _load_image_for_mood(self.image_path, mood)
        scaled = _scale_to_fit(raw, self._render_max_side)
        # Variant PNGs (artist-drawn mood expressions) bypass the filter.
        out = scaled if is_variant else _apply_mood_filter(scaled, mood)
        out = self._apply_option_layers(out)
        self._mood_image_cache[cache_key] = out
        return out

    def _apply_option_layers(self, img: Image.Image) -> Image.Image:
        if not self.option_paths:
            return img
        size = img.size
        overlays = self._option_cache.get(size)
        if overlays is None:
            overlays = []
            for option_path in self.option_paths:
                try:
                    with Image.open(option_path) as raw:
                        overlay = raw.convert("RGBA").resize(size, Image.LANCZOS)
                        overlays.append(overlay)
                except OSError as exc:
                    log.warning("option image skipped: %s", exc)
            self._option_cache[size] = overlays
        if not overlays:
            return img
        out = img.copy()
        for overlay in overlays:
            out.alpha_composite(overlay)
        return out

    def _render_image(self, mood: str, scale: tuple[float, float] | None = None) -> None:
        base_img = self._get_mood_image(mood)
        if scale is None:
            self._img_w, self._img_h = base_img.size
        img = base_img
        if scale is not None:
            sx, sy = scale
            img = img.resize(
                (max(1, int(img.width * sx)), max(1, int(img.height * sy))),
                Image.LANCZOS,
            )
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.itemconfigure(self._image_id, image=self._photo)
        self.current_mood = mood
        self._update_stage_chrome()
        if scale is None:
            self._refresh_mood_fx(force=True)

    def _catalog_item(self, key: str, item_id: str) -> dict | None:
        for item in self.catalog.get(key, []):
            if isinstance(item, dict) and str(item.get("id") or "") == item_id:
                return item
        return None

    def _catalog_image_path(self, item: dict | None) -> Path | None:
        if not item:
            return None
        if self.asset_dir is None:
            return None
        asset_root = self.asset_dir.resolve()
        item_id = str(item.get("id") or "").strip()
        candidates: list[Path] = []
        raw = str(item.get("image") or "").strip()
        if raw:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = asset_root / path
            candidates.append(path)
        if item_id:
            candidates.extend(
                [
                    asset_root / f"{item_id}.png",
                    asset_root / "characters" / f"{item_id}.png",
                    asset_root / "options" / f"{item_id}.png",
                ]
            )
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.exists() and resolved != asset_root and asset_root in resolved.parents:
                return resolved
        return None

    def _display_name_for_character(self, character: dict) -> str:
        character_id = str(character.get("id") or "")
        state = _load_persisted_state()
        inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
        owned = inventory.get(character_id) if isinstance(inventory.get(character_id), dict) else {}
        nickname = str(owned.get("nickname") or "").strip()
        if nickname:
            return nickname
        return str(character.get("name_ko") or character_id)

    def _option_paths_for_ids(self, option_ids: list[str]) -> list[Path]:
        paths: list[Path] = []
        for option_id in option_ids:
            option = self._catalog_item("options", option_id)
            path = self._catalog_image_path(option)
            if path is not None:
                paths.append(path)
        return paths

    def _sync_visual_state(self, payload: dict) -> bool:
        """Apply persisted character/option changes without reopening the window."""
        payload = _as_dict(payload)
        gacha = _as_dict(payload.get("gacha"))
        changed = False

        active_id = str(gacha.get("active_character_id") or "").strip()
        if active_id and active_id != self.character_id:
            character = self._catalog_item("characters", active_id)
            image_path = self._catalog_image_path(character)
            if character is not None and image_path is not None:
                try:
                    with Image.open(image_path) as image:
                        image.verify()
                except OSError as exc:
                    log.warning("active character image skipped: %s", exc)
                else:
                    self.image_path = image_path
                    self.character_id = active_id
                    self.name = self._display_name_for_character(character)
                    self.rarity = int(character.get("rarity", self.rarity) or self.rarity)
                    self._mood_image_cache.clear()
                    self._option_cache.clear()
                    self.base_image = self._get_mood_image(self.current_mood)
                    self._img_w, self._img_h = self.base_image.size
                    self.status_card.set_identity(name=self.name, rarity=self.rarity)
                    self.root.title(f"chibi — {self.name}")
                    changed = True

        active_options = gacha.get("active_option_ids")
        if isinstance(active_options, list):
            next_ids = [str(option_id) for option_id in active_options]
            if next_ids != self.active_option_ids:
                self.active_option_ids = next_ids
                self.option_paths = self._option_paths_for_ids(next_ids)
                self._mood_image_cache.clear()
                self._option_cache.clear()
                changed = True

        return changed

    def _update_mood_label(self, mood: str) -> None:
        self.status_card.set_mood(mood)

    def _update_progress_label(self, payload: dict) -> None:
        payload = _as_dict(payload)
        self._last_state_payload = payload
        counters = _as_dict(payload.get("counters"))
        calls = _format_counter(counters.get("calls_since_slice"))
        interval = _format_counter(counters.get("slice_interval"))
        slices = _format_counter(counters.get("slices_today"))
        gacha = _as_dict(payload.get("gacha"))
        tickets = _format_counter(gacha.get("tickets"))
        system = _as_dict(payload.get("system"))
        timing = _as_dict(payload.get("timing"))

        parts: list[str] = []
        if calls is not None and interval is not None:
            parts.append(f"{calls}/{interval}")
        parts.append(_format_tool_idle(timing))
        if slices is not None:
            parts.append(f"리듬 {slices}")
        if tickets is not None:
            parts.append(f"티켓 {tickets}")
        self.status_card.set_progress(
            " · ".join(parts),
            system_hud=_format_system_hud(system),
            system_warn=_metric_is_warn(system),
            debug_hud=_format_debug_hud(payload),
            rhythm_fraction=_rhythm_fraction(counters),
            metric_values=_metric_meter_values(system),
            metric_alerts=_metric_alerts(system),
        )

    # ── Built-in controls ───────────────────────────────────────────────────

    def _button_colors(self, kind: str) -> dict[str, str]:
        if kind == "primary":
            return {
                "bg": BUTTON_PRIMARY_BG,
                "hover": BUTTON_PRIMARY_HOVER,
                "active": BUTTON_PRIMARY_ACTIVE,
                "border": BUTTON_PRIMARY_BORDER,
                "shadow": BUTTON_PRIMARY_SHADOW,
                "icon_bg": BUTTON_PRIMARY_ICON_BG,
                "fg": TEXT_FG,
            }
        if kind == "danger":
            return {
                "bg": BUTTON_DANGER_BG,
                "hover": BUTTON_DANGER_HOVER,
                "active": BUTTON_DANGER_ACTIVE,
                "border": BUTTON_DANGER_BORDER,
                "shadow": BUTTON_DANGER_SHADOW,
                "icon_bg": BUTTON_DANGER_ICON_BG,
                "fg": BUTTON_DANGER_FG,
            }
        if kind == "selected":
            return {
                "bg": BUTTON_SECONDARY_ACTIVE,
                "hover": BUTTON_SECONDARY_HOVER,
                "active": BUTTON_SECONDARY_ACTIVE,
                "border": BUTTON_SECONDARY_BORDER,
                "shadow": BUTTON_SECONDARY_SHADOW,
                "icon_bg": BUTTON_SECONDARY_ICON_BG,
                "indicator": "#55bd83",
                "fg": TEXT_FG,
            }
        return {
            "bg": BUTTON_SECONDARY_BG,
            "hover": BUTTON_SECONDARY_HOVER,
            "active": BUTTON_SECONDARY_ACTIVE,
            "border": BUTTON_SECONDARY_BORDER,
            "shadow": BUTTON_SECONDARY_SHADOW,
            "icon_bg": BUTTON_SECONDARY_ICON_BG,
            "fg": TEXT_FG,
        }

    def _make_button(
        self,
        parent: tk.Misc,
        text: str,
        command,
        *,
        kind: str = "secondary",
        icon: str | None = None,
        min_width: int = 70,
        anchor: str = "center",
    ) -> ChibiButton:
        colors = self._button_colors(kind)
        panel_bg = PANEL_BG
        with contextlib.suppress(tk.TclError):
            panel_bg = str(parent.cget("bg"))
        button = ChibiButton(
            parent,
            text,
            command,
            colors,
            panel_bg=panel_bg,
            icon=icon,
            min_width=min_width,
            anchor=anchor,
        )
        button.set_scale(self._window_scale)
        return button

    def _toggle_drawer(self, mode: str) -> None:
        if self.drawer_mode == mode and self.drawer.winfo_ismapped():
            self.drawer.pack_forget()
            self.drawer_mode = None
            self._drawer_render_signature = None
            self._fit_root_to_content()
            return
        self.drawer_mode = mode
        self._render_drawer()
        if not self.drawer.winfo_ismapped():
            self.drawer.pack(pady=(0, self._s(8)), padx=self._s(10), fill="x")
        self._fit_root_to_content()

    def _render_drawer(self) -> None:
        for child in self.drawer.winfo_children():
            child.destroy()
        if self.drawer_mode == "inventory":
            self._render_inventory_drawer()
        elif self.drawer_mode == "options":
            self._render_options_drawer()
        elif self.drawer_mode == "settings":
            self._render_settings_drawer()
        elif self.drawer_mode == "guide":
            self._render_guide_drawer()
        self._drawer_render_signature = self._current_drawer_signature()

    def _current_drawer_signature(self) -> tuple:
        state = _load_persisted_state()
        if self.drawer_mode == "settings":
            return (
                "settings",
                bool(self.sounds_enabled),
                bool(self.topmost_enabled),
                self.view_mode,
                round(self._window_scale, 2),
                bool(self.connection_ok),
            )
        if self.drawer_mode == "guide":
            return ("guide",)
        if self.drawer_mode == "options":
            option_ids = state.get("active_option_ids")
            if not isinstance(option_ids, list):
                option_ids = self.active_option_ids
            return ("options", tuple(str(option_id) for option_id in option_ids))

        inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
        inventory_sig = tuple(
            sorted(
                (
                    str(character_id),
                    int(value.get("count", 0) or 0) if isinstance(value, dict) else 0,
                    str(value.get("nickname") or "") if isinstance(value, dict) else "",
                )
                for character_id, value in inventory.items()
            )
        )
        return (
            "inventory",
            str(state.get("active_character_id") or self.character_id or ""),
            int(state.get("tickets", 0) or 0),
            int(state.get("total_pulls", 0) or 0),
            inventory_sig,
        )

    def _refresh_drawer_if_state_changed(self) -> None:
        if not self.drawer_mode or not self.drawer.winfo_ismapped():
            return
        signature = self._current_drawer_signature()
        if signature != self._drawer_render_signature:
            self._render_drawer()
            self._fit_root_to_content()

    def _drawer_header(self, text: str) -> None:
        tk.Label(
            self.drawer,
            text=text,
            bg=PANEL_BG_2,
            fg=TEXT_FG,
            font=("Helvetica", max(8, self._s(10)), "bold"),
        ).pack(anchor="w", pady=(0, self._s(6)))

    def _drawer_note(self, text: str, *, strong: bool = False) -> None:
        tk.Label(
            self.drawer,
            text=text,
            bg=PANEL_BG_2,
            fg=TEXT_FG if strong else MUTED_FG,
            font=("Helvetica", max(7, self._s(9)), "bold" if strong else "normal"),
            wraplength=max(self._s(180), int(self.drawer.winfo_width() or self._s(280))),
            justify="left",
        ).pack(anchor="w", pady=(0, self._s(4)))

    def _render_inventory_drawer(self) -> None:
        state = _load_persisted_state()
        inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
        active_id = state.get("active_character_id") or self.character_id
        tickets = int(state.get("tickets", 0) or 0)
        characters = _released_items(self.catalog, "characters")
        by_id = {str(ch.get("id")): ch for ch in characters}
        owned_ids = [cid for cid in inventory if cid in by_id]
        if active_id in by_id and active_id not in owned_ids:
            owned_ids.insert(0, str(active_id))

        self._drawer_header(f"보관함 · {len(inventory)}종 · 티켓 {tickets}")
        for idx, line in enumerate(_gacha_refill_lines(self._last_state_payload, state)):
            self._drawer_note(line, strong=idx == 0)
        if not owned_ids:
            tk.Label(
                self.drawer,
                text="아직 보유 캐릭터가 없어",
                bg=PANEL_BG_2,
                fg=MUTED_FG,
                font=("Helvetica", max(7, self._s(9))),
            ).pack(anchor="w", pady=(0, self._s(6)))
            self._make_button(
                self.drawer,
                "오늘 무료 뽑기",
                self._pull_from_window,
                kind="primary",
                icon="★",
                min_width=128,
            ).pack(anchor="w")
            return

        for cid in owned_ids[:8]:
            ch = by_id[cid]
            inv = inventory.get(cid) if isinstance(inventory.get(cid), dict) else {}
            count = int(inv.get("count", 0) or 0)
            rarity = int(ch.get("rarity", 2) or 2)
            prefix = "✓ " if cid == active_id else ""
            count_text = f" x{count}" if count else " 미보유"
            text = f"{prefix}{ch.get('name_ko') or cid} ★{rarity}{count_text}"
            btn = self._make_button(
                self.drawer,
                text,
                lambda character_id=cid: self._send_action(
                    "set_active_character", character_id=character_id
                ),
                kind="selected" if cid == active_id else "secondary",
                min_width=224,
                anchor="w",
            )
            if count <= 0:
                btn.set_enabled(False)
            btn.pack(anchor="w", fill="x", pady=self._s(2))

    def _render_options_drawer(self) -> None:
        state = _load_persisted_state()
        selected = state.get("active_option_ids")
        if not isinstance(selected, list):
            selected = self.active_option_ids
        selected_ids = {str(option_id) for option_id in selected}
        options = _released_items(self.catalog, "options")

        self._drawer_header("옵션 · 최대 3개")
        self._option_vars: dict[str, tk.IntVar | ChibiButton] = {}
        grid = tk.Frame(self.drawer, bg=PANEL_BG_2)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        for idx, option in enumerate(options[:12]):
            option_id = str(option.get("id") or "")
            var = tk.IntVar(value=1 if option_id in selected_ids else 0)
            self._option_vars[option_id] = var
            selected = int(var.get()) == 1
            btn = self._make_button(
                grid,
                str(option.get("name_ko") or option_id),
                lambda oid=option_id: self._toggle_option_chip(oid),
                kind="selected" if selected else "secondary",
                icon="✓" if selected else "·",
                min_width=126,
                anchor="w",
            )
            btn.grid(
                row=idx // 2,
                column=idx % 2,
                sticky="ew",
                padx=(0, self._s(6)),
                pady=self._s(2),
            )
            self._option_vars[f"{option_id}__button"] = btn

        actions = tk.Frame(self.drawer, bg=PANEL_BG_2)
        actions.pack(anchor="w", pady=(self._s(8), 0))
        self._make_button(
            actions,
            "적용",
            self._apply_options_from_drawer,
            kind="primary",
            icon="✓",
            min_width=74,
        ).pack(side="left", padx=(0, self._s(6)))
        self._make_button(
            actions,
            "해제",
            lambda: self._send_action("clear_active_options"),
            icon="x",
            min_width=74,
        ).pack(side="left")

    def _render_settings_drawer(self) -> None:
        self._drawer_header("설정 · 작업 중 방해 줄이기")
        grid = tk.Frame(self.drawer, bg=PANEL_BG_2)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(2, weight=1)

        controls = [
            (
                "sounds",
                "사운드",
                bool(self.sounds_enabled),
                self._toggle_sounds,
                "♪",
            ),
            (
                "topmost",
                "항상 위",
                bool(self.topmost_enabled),
                self._toggle_topmost,
                "↑",
            ),
            (
                "connection",
                "서버",
                bool(self.connection_ok),
                lambda: self.show_bubble(
                    "서버 연결됨" if self.connection_ok else "Claude에서 /chibi-mcp:chibi 실행"
                ),
                "●",
            ),
        ]
        for idx, (_key, label, enabled, command, icon) in enumerate(controls):
            state_text = "켜짐" if enabled else ("대기" if label == "서버" else "꺼짐")
            self._make_button(
                grid,
                f"{label} {state_text}",
                command,
                kind="selected" if enabled else "secondary",
                icon=icon if enabled else "·",
                min_width=106,
                anchor="w",
            ).grid(
                row=0,
                column=idx,
                sticky="ew",
                padx=(0, self._s(6)),
                pady=self._s(2),
            )

        size_row = tk.Frame(self.drawer, bg=PANEL_BG_2)
        size_row.pack(fill="x", pady=(self._s(8), 0))
        self._make_button(
            size_row,
            "작게",
            lambda: self._nudge_window_scale(-0.1),
            icon="-",
            min_width=70,
        ).pack(side="left", padx=(0, self._s(6)))
        self._make_button(
            size_row,
            f"{round(self._window_scale * 100)}%",
            self._reset_window_scale,
            kind="selected" if abs(self._window_scale - 1.0) < 0.03 else "secondary",
            icon="↺",
            min_width=78,
        ).pack(side="left", padx=(0, self._s(6)))
        self._make_button(
            size_row,
            "크게",
            lambda: self._nudge_window_scale(0.1),
            icon="+",
            min_width=70,
        ).pack(side="left", padx=(0, self._s(6)))

        mode_row = tk.Frame(self.drawer, bg=PANEL_BG_2)
        mode_row.pack(fill="x", pady=(self._s(8), 0))
        for mode in VIEW_MODES:
            text, icon = VIEW_MODE_BUTTONS[mode]
            self._make_button(
                mode_row,
                text,
                lambda next_mode=mode: self._apply_view_mode(next_mode),
                kind="selected" if self.view_mode == mode else "secondary",
                icon=icon,
                min_width=70,
            ).pack(side="left", padx=(0, self._s(6)))
        self._make_button(
            self.drawer,
            "작동 방식",
            lambda: self._toggle_drawer("guide"),
            icon="?",
            min_width=116,
            anchor="w",
        ).pack(anchor="w", pady=(self._s(8), 0))

    def _render_guide_drawer(self) -> None:
        self._drawer_header("작동 방식 · 실제로 하는 일")
        for line in (
            "CPU 80% 이상 → 헐떡",
            "배터리 20% 미만 → 졸림",
            "Claude/Codex tool call → 신남 + 리듬 진행",
            "30분 이상 조용함 → 시무룩",
            "뽑기: 하루 1회 무료 · 100 tool call 또는 10리듬마다 티켓 +1",
        ):
            self._drawer_note(line, strong="→" in line)
        self._make_button(
            self.drawer,
            "설정으로",
            lambda: self._toggle_drawer("settings"),
            icon="←",
            min_width=96,
        ).pack(anchor="w", pady=(self._s(6), 0))

    def _toggle_sounds(self) -> None:
        if self.sounds_enabled:
            self.sounds_enabled = False
            self._save_window_layout(sounds_enabled=False)
            self.show_bubble("사운드 꺼짐")
        else:
            try:
                self._sound_paths = _ensure_sounds()
            except (OSError, wave.Error) as exc:
                log.warning("sound generation failed: %s", exc)
                self.show_bubble("사운드 준비 실패")
                return
            self.sounds_enabled = True
            self._save_window_layout(sounds_enabled=True)
            self.show_bubble("사운드 켜짐")
            self._play_safe("bubble")
        if self.drawer_mode == "settings" and self.drawer.winfo_ismapped():
            self._render_drawer()
            self._fit_root_to_content()

    def _toggle_topmost(self) -> None:
        self.topmost_enabled = not self.topmost_enabled
        self._set_topmost_attribute(self.topmost_enabled)
        self._save_window_layout(topmost_enabled=self.topmost_enabled)
        self.show_bubble("항상 위 켜짐" if self.topmost_enabled else "항상 위 꺼짐")
        if self.drawer_mode == "settings" and self.drawer.winfo_ismapped():
            self._render_drawer()
            self._fit_root_to_content()

    def _toggle_option_chip(self, option_id: str) -> None:
        var = self._option_vars.get(option_id)
        btn = self._option_vars.get(f"{option_id}__button")
        if not isinstance(var, tk.IntVar) or not isinstance(btn, ChibiButton):
            return
        selected = int(var.get()) == 1
        if not selected:
            selected_count = sum(
                int(value.get()) == 1
                for key, value in self._option_vars.items()
                if not key.endswith("__button") and isinstance(value, tk.IntVar)
            )
            if selected_count >= 3:
                self.show_bubble("옵션은 3개까지")
                return
        var.set(0 if selected else 1)
        now_selected = int(var.get()) == 1
        btn.set_style(
            self._button_colors("selected" if now_selected else "secondary"),
            icon="✓" if now_selected else "·",
        )

    def _apply_options_from_drawer(self) -> None:
        selected = [
            option_id
            for option_id, var in getattr(self, "_option_vars", {}).items()
            if isinstance(var, tk.IntVar) and int(var.get()) == 1
        ]
        if len(selected) > 3:
            self.show_bubble("옵션은 3개까지")
            return
        self._send_action("set_active_options", option_ids=selected)

    def _pull_from_window(self) -> None:
        self.show_bubble("뽑는 중...")
        self._send_action("pull_gacha")

    def _send_action(self, action: str, **payload) -> None:
        message = {"type": "action", "action": action, **payload}
        threading.Thread(
            target=_send_ws_action,
            args=(self.ws_url, message, self.event_queue),
            daemon=True,
        ).start()

    # ── Animations ───────────────────────────────────────────────────────────

    def _idle_bob_tick(self) -> None:
        if self.stop_event.is_set():
            return
        self._bob_phase += BOB_TICK_MS / 1000.0
        amplitude, hz = MOOD_BOB_PROFILES.get(self.current_mood, (BOB_AMPLITUDE_PX, BOB_HZ))
        offset = int(self._s(amplitude) * math.sin(2 * math.pi * hz * self._bob_phase))
        self.canvas.coords(
            self._image_id, self._canvas_center[0], self._canvas_center[1] + offset
        )
        if offset != self._last_bob_offset:
            with contextlib.suppress(tk.TclError):
                self.canvas.move("mood_fx_bob", 0, offset - self._last_bob_offset)
            self._last_bob_offset = offset
        self._after(BOB_TICK_MS, self._idle_bob_tick)

    def _squish(self, _event: tk.Event) -> None:
        self._render_image(self.current_mood, scale=(1.15, 0.6))
        self._play_safe("squish")
        self._after(180, lambda: self._render_image(self.current_mood))

    def _slice_flash(self) -> None:
        # Brighten whatever the current mood image is (variant or filtered base).
        current = self._get_mood_image(self.current_mood)
        bright = ImageEnhance.Brightness(current).enhance(1.6)
        self._photo = ImageTk.PhotoImage(bright)
        self.canvas.itemconfigure(self._image_id, image=self._photo)
        self._drop_slice_piece()
        self._play_safe("slice")
        self._after(140, lambda: self._render_image(self.current_mood))

    def _drop_slice_piece(self) -> None:
        cx = self._canvas_center[0]
        base_y = self._canvas_center[1] + self._img_h // 2 - self._s(12)
        piece = self.canvas.create_oval(
            cx - self._s(18),
            base_y - self._s(8),
            cx + self._s(18),
            base_y + self._s(8),
            fill="#F6F1E8",
            outline="#CBA16A",
            width=self._s(2),
        )
        seam = self.canvas.create_line(
            cx - self._s(8),
            base_y - self._s(2),
            cx + self._s(9),
            base_y + self._s(2),
            fill="#E2C184",
            width=self._s(2),
        )

        def tick(step: int = 0) -> None:
            if step >= 16:
                with contextlib.suppress(tk.TclError):
                    self.canvas.delete(piece)
                    self.canvas.delete(seam)
                return
            with contextlib.suppress(tk.TclError):
                self.canvas.move(piece, 0, self._s(2))
                self.canvas.move(seam, 0, self._s(2))
            self._after(45, lambda: tick(step + 1))

        tick()

    def show_bubble(self, text: str) -> None:
        if not text:
            return
        clipped = text[:120] + ("…" if len(text) > 120 else "")
        self.bubble.configure(text=clipped)
        self._play_safe("bubble")
        try:
            self.bubble.pack(
                pady=(self._s(2), self._s(10)),
                padx=self._s(10),
                before=self.status_card,
            )
        except (AttributeError, tk.TclError):
            self.bubble.pack(pady=(self._s(2), self._s(10)), padx=self._s(10))
        self._fit_root_to_content()
        if self._bubble_hide_after is not None:
            with contextlib.suppress(tk.TclError):
                self.root.after_cancel(self._bubble_hide_after)
            self._after_ids.discard(self._bubble_hide_after)
        self._bubble_hide_after = self._after(BUBBLE_VISIBLE_MS, self._hide_bubble)

    def _hide_bubble(self) -> None:
        self.bubble.pack_forget()
        self._bubble_hide_after = None
        self._fit_root_to_content()

    # ── Idle bubbles ─────────────────────────────────────────────────────────

    def _schedule_idle_bubble(self) -> None:
        if self.stop_event.is_set():
            return
        import random as _r

        delay = _r.randint(IDLE_BUBBLE_MIN_MS, IDLE_BUBBLE_MAX_MS)
        self._after(delay, self._idle_bubble_tick)

    def _idle_bubble_tick(self) -> None:
        if self.stop_event.is_set():
            return
        import random as _r

        # Skip if a bubble is already showing — don't stack.
        if self._bubble_hide_after is None:
            pool = IDLE_PHRASES_BY_MOOD.get(self.current_mood, ["..."])
            self.show_bubble(_r.choice(pool))
        self._schedule_idle_bubble()

    def _play_safe(self, key: str) -> None:
        if not self.sounds_enabled:
            return
        p = self._sound_paths.get(key)
        if p is None:
            return
        _play_sound(p)

    def _poke_character(self) -> str:
        self._render_image(self.current_mood, scale=(1.08, 0.86))
        self._spawn_click_sparkle()
        self._play_safe("squish")
        self.show_bubble(_click_reaction_for_payload(self.current_mood, self._last_state_payload))
        self._after(140, lambda: self._render_image(self.current_mood))
        return "break"

    def _show_status_detail(self) -> str:
        payload = _as_dict(self._last_state_payload)
        system = _as_dict(payload.get("system"))
        counters = _as_dict(payload.get("counters"))
        timing = _as_dict(payload.get("timing"))
        calls = _format_counter(counters.get("calls_since_slice")) or "?"
        interval = _format_counter(counters.get("slice_interval")) or "?"
        reason = _mood_reason_for_payload(self.current_mood, self._last_state_payload)
        self.show_bubble(
            f"{_format_system_hud(system)} · {_format_tool_idle(timing)} · {reason} · 리듬 {calls}/{interval}"
        )
        return "break"

    def _spawn_click_sparkle(self) -> None:
        cx = self._canvas_center[0] + self._s(40)
        cy = self._canvas_center[1] - self._s(52)
        colors = ("#ff9dbd", "#f4c542", "#55bd83")
        items: list[int] = []
        ring_r = max(self._s(28), min(self._img_w, self._img_h) // 3)
        ring = self.canvas.create_oval(
            self._canvas_center[0] - ring_r,
            self._canvas_center[1] - ring_r,
            self._canvas_center[0] + ring_r,
            self._canvas_center[1] + ring_r,
            fill="",
            outline="#ff9dbd",
            width=max(1, self._s(2)),
            tags=("click_fx",),
        )
        items.append(ring)
        for idx, color in enumerate(colors):
            x = cx + self._s((idx - 1) * 13)
            y = cy + self._s((idx % 2) * 9)
            r = self._s(4)
            items.append(
                self.canvas.create_oval(
                    x - r,
                    y - r,
                    x + r,
                    y + r,
                    fill=color,
                    outline="",
                    tags=("click_fx",),
                )
            )
        self.canvas.tag_raise("click_fx")

        def tick(step: int = 0) -> None:
            if step >= 10:
                with contextlib.suppress(tk.TclError):
                    for item in items:
                        self.canvas.delete(item)
                return
            with contextlib.suppress(tk.TclError):
                for idx, item in enumerate(items):
                    if item == ring:
                        grow = self._s(2)
                        self.canvas.coords(
                            ring,
                            self.canvas.coords(ring)[0] - grow,
                            self.canvas.coords(ring)[1] - grow,
                            self.canvas.coords(ring)[2] + grow,
                            self.canvas.coords(ring)[3] + grow,
                        )
                        self.canvas.itemconfigure(
                            ring,
                            outline="#ffd5e3" if step > 5 else "#ff9dbd",
                            width=max(1, self._s(2 - step // 6)),
                        )
                    else:
                        self.canvas.move(item, self._s(idx - 2), -self._s(2))
            self._after(35, lambda: tick(step + 1))

        tick()

    def _landing_jiggle(self) -> None:
        steps = ((1.08, 0.88), (0.96, 1.06), (1.03, 0.98), (1.0, 1.0))

        def tick(idx: int = 0) -> None:
            if idx >= len(steps):
                self._render_image(self.current_mood)
                return
            self._render_image(self.current_mood, scale=steps[idx])
            self._after(55, lambda: tick(idx + 1))

        self._play_safe("squish")
        tick()

    def _spawn_pull_reveal(self, last_pull: dict) -> None:
        drawn = _as_dict(last_pull.get("drawn"))
        rarity = int(_finite_number(drawn.get("rarity")) or 2)
        rare = rarity >= 4
        halo = self.canvas.create_oval(
            self._canvas_center[0] - self._img_w // 2 - self._s(14),
            self._canvas_center[1] - self._img_h // 2 - self._s(14),
            self._canvas_center[0] + self._img_w // 2 + self._s(14),
            self._canvas_center[1] + self._img_h // 2 + self._s(14),
            fill="",
            outline="#ff6b9d" if rare else "#f4c542",
            width=max(2, self._s(3)),
        )
        self.canvas.addtag_withtag("pull_fx", halo)
        sparkles: list[int] = [halo]
        palette = ("#ff6b9d", "#f4c542", "#55bd83", "#78a8ff") if rare else ("#f4c542", "#ffb36b", "#55bd83")
        for idx, color in enumerate(palette):
            angle = (math.tau / len(palette)) * idx
            x = self._canvas_center[0] + round(math.cos(angle) * (self._img_w * 0.52))
            y = self._canvas_center[1] + round(math.sin(angle) * (self._img_h * 0.62))
            item = self.canvas.create_text(
                x,
                y,
                text="✦" if rare or idx % 2 == 0 else "·",
                fill=color,
                font=("Helvetica", max(9, self._s(13)), "bold"),
            )
            self.canvas.addtag_withtag("pull_fx", item)
            sparkles.append(item)
        self.canvas.tag_raise("pull_fx")

        def tick(step: int = 0) -> None:
            if step >= 16:
                with contextlib.suppress(tk.TclError):
                    for item in sparkles:
                        self.canvas.delete(item)
                return
            grow = self._s(1 + step // 4)
            with contextlib.suppress(tk.TclError):
                self.canvas.coords(
                    halo,
                    self._canvas_center[0] - self._img_w // 2 - self._s(14) - grow,
                    self._canvas_center[1] - self._img_h // 2 - self._s(14) - grow,
                    self._canvas_center[0] + self._img_w // 2 + self._s(14) + grow,
                    self._canvas_center[1] + self._img_h // 2 + self._s(14) + grow,
                )
                if step % 2 == 0:
                    state = "hidden" if step % 4 == 0 else "normal"
                    for item in sparkles[1:]:
                        self.canvas.itemconfigure(item, state=state)
            self._after(45, lambda: tick(step + 1))

        tick()

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_start = (event.x_root, event.y_root, event.widget)
        self._drag_moved = False
        self._drag_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )

    def _do_drag(self, event: tk.Event) -> None:
        offset = getattr(self, "_drag_offset", None)
        if offset is None:
            return
        start = self._drag_start
        if start is not None and (
            abs(event.x_root - start[0]) > self._s(4) or abs(event.y_root - start[1]) > self._s(4)
        ):
            self._drag_moved = True
        dx, dy = offset
        self.root.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")

    def _end_drag(self, _event: tk.Event) -> str | None:
        start = self._drag_start
        self._drag_start = None
        self._drag_offset = None
        if start is None or self._drag_moved:
            if start is not None and self._drag_moved:
                self._save_window_layout()
                self._landing_jiggle()
            return None
        if start[2] is self.canvas:
            return self._poke_character()
        if start[2] is self.status_card:
            return self._show_status_detail()
        return None

    def _start_resize(self, event: tk.Event) -> str:
        self._resize_start = (event.x_root, event.y_root, self._window_scale)
        return "break"

    def _do_resize(self, event: tk.Event) -> str:
        if self._resize_start is None:
            return "break"
        start_x, start_y, start_scale = self._resize_start
        scale = _scale_from_resize_drag(
            start_scale,
            event.x_root - start_x,
            event.y_root - start_y,
            self._base_total_w,
            self._base_total_h,
        )
        self._apply_window_scale(scale)
        return "break"

    def _end_resize(self, _event: tk.Event) -> str:
        self._resize_start = None
        self._save_window_layout()
        return "break"

    # ── Event pump ───────────────────────────────────────────────────────────

    def _poll_events(self) -> None:
        try:
            while True:
                evt = self.event_queue.get_nowait()
                self._handle_event(evt)
        except queue.Empty:
            pass
        if not self.stop_event.is_set():
            self._after(POLL_INTERVAL_MS, self._poll_events)

    def _handle_event(self, evt: dict) -> None:
        kind = evt.get("type")
        if kind == "state":
            payload = _as_dict(evt.get("payload"))
            had_state = bool(self._last_state_payload)
            pull_signature = _pull_signature(payload)
            is_new_pull = (
                pull_signature is not None
                and pull_signature != self._last_pull_signature
            )
            visual_changed = self._sync_visual_state(payload)
            mood = payload.get("mood")
            if mood and (mood != self.current_mood or visual_changed):
                self._render_image(mood)
                self._update_mood_label(mood)
            elif visual_changed:
                self._render_image(self.current_mood)
            if visual_changed:
                self._update_stage_layout()
                self._fit_root_to_content()
            gacha = _as_dict(payload.get("gacha"))
            active_options = gacha.get("active_option_ids")
            if isinstance(active_options, list):
                self.active_option_ids = [str(option_id) for option_id in active_options]
            self._update_progress_label(payload)
            if pull_signature is not None:
                self._last_pull_signature = pull_signature
            if had_state and is_new_pull:
                self._spawn_pull_reveal(_as_dict(_as_dict(payload.get("gacha")).get("last_pull")))
            self._refresh_drawer_if_state_changed()
        elif kind == "connection":
            self.connection_ok = bool(evt.get("connected"))
            self.status_card.set_connection(self.connection_ok)
            self._refresh_drawer_if_state_changed()
        elif kind == "slice":
            self._slice_flash()
        elif kind == "say":
            self.show_bubble(evt.get("text", ""))
        elif kind == "sound":
            sound = str(evt.get("name") or "")
            if sound in self._sound_paths:
                self._play_safe(sound)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self, ws_url: str | None) -> None:
        self.ws_url = ws_url
        if ws_url:
            t = threading.Thread(
                target=_ws_listener,
                args=(ws_url, self.event_queue, self.stop_event),
                daemon=True,
            )
            t.start()
        self._after(POLL_INTERVAL_MS, self._poll_events)
        self._after(BOB_TICK_MS, self._idle_bob_tick)
        self._after(320, self._mood_fx_tick)
        self._schedule_idle_bubble()
        self.root.mainloop()

    def _after(self, ms: int, callback) -> str:
        """tk.after wrapper that records the callback id for cancellation."""
        aid = self.root.after(ms, lambda: self._run_after(aid, callback))
        self._after_ids.add(aid)
        return aid

    def _run_after(self, aid: str, callback) -> None:
        self._after_ids.discard(aid)
        if self.stop_event.is_set():
            return
        callback()

    def shutdown(self) -> None:
        self.stop_event.set()
        self._save_window_layout(view_mode=self.view_mode)
        # Cancel any scheduled callbacks before destroying the root so they
        # don't fire on a half-torn-down widget tree.
        for aid in list(self._after_ids):
            with contextlib.suppress(tk.TclError, ValueError):
                self.root.after_cancel(aid)
        self._after_ids.clear()
        with contextlib.suppress(tk.TclError):
            self.root.destroy()


# ── Entry point ──────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chibi_mcp.window")
    parser.add_argument("--image", required=True)
    parser.add_argument("--name", default="chibi")
    parser.add_argument("--rarity", type=int, default=2)
    parser.add_argument("--mood", default="calm")
    parser.add_argument("--option-image", action="append", default=[], help="Transparent option PNG")
    parser.add_argument("--active-option-id", action="append", default=[], help="Selected option id")
    parser.add_argument("--asset-dir", default=None, help="Directory containing assets/meta.json")
    parser.add_argument("--character-id", default=None, help="Current catalog character id")
    parser.add_argument("--ready-file", default=None, help="Write this file after Tk startup")
    parser.add_argument("--ws", default=None, help="WebSocket URL for live updates")
    parser.add_argument(
        "--view-mode",
        choices=VIEW_MODES,
        default=None,
        help="Initial window display mode",
    )
    parser.add_argument(
        "--no-frameless", action="store_true",
        help="Show the OS title bar (default: frameless)",
    )
    parser.add_argument(
        "--no-sounds", action="store_true",
        help="Disable click/milestone sound effects",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        print(f"image not found: {image_path}", file=sys.stderr)
        return 1
    option_paths = [Path(value).expanduser().resolve() for value in args.option_image]
    missing_options = [path for path in option_paths if not path.exists()]
    if missing_options:
        print(f"option image not found: {missing_options[0]}", file=sys.stderr)
        return 1
    asset_dir = Path(args.asset_dir).expanduser().resolve() if args.asset_dir else None
    if asset_dir is not None and not (asset_dir / "meta.json").exists():
        print(f"asset meta not found: {asset_dir / 'meta.json'}", file=sys.stderr)
        return 1

    win = PetWindow(
        image_path,
        args.name,
        args.rarity,
        args.mood,
        option_paths=option_paths,
        asset_dir=asset_dir,
        character_id=args.character_id,
        active_option_ids=args.active_option_id,
        frameless=not args.no_frameless,
        sounds=not args.no_sounds,
        view_mode=args.view_mode or os.environ.get("CHIBI_WINDOW_MODE"),
    )
    _write_ready_file(args.ready_file)
    win.start(args.ws)
    return 0


if __name__ == "__main__":
    sys.exit(main())
