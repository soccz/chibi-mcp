"""Tk window for the floating chibi.

v1.1 visual upgrade:
    - overrideredirect(True): no title bar — floats as a compact pet window.
    - macOS uses the same stable Tk panel path as other platforms by default.
      PyObjC transparency is experimental opt-in only because some
      Python/Tk/PyObjC combinations segfault before Python can catch errors.
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
import wave
from ctypes import c_void_p
from pathlib import Path

from PIL import Image, ImageEnhance, ImageTk

log = logging.getLogger(__name__)

CANVAS_SIZE = 240
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

IDLE_BUBBLE_MIN_MS = 4 * 60_000
IDLE_BUBBLE_MAX_MS = 7 * 60_000

SOUND_DIR = Path.home() / ".chibi-mcp" / "sounds"
SOUND_VERSION = "2"

IDLE_PHRASES_BY_MOOD: dict[str, list[str]] = {
    "calm":      ["말랑...", "심심해", "쉬자", "..."],
    "happy":     ["굳굳", "오늘 잘되네", "ㅎㅎ"],
    "joyful":    ["반짝", "오예", "엣헴"],
    "panting":   ["헐 바쁘다", "잠깐만", "엥"],
    "drowsy":    ["졸려", "충전해줘", "..."],
    "lonely":    ["보고싶었어", "심심해", "어디갔어"],
    "surprised": ["오?!", "헐", "잠시만"],
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


def _load_image_for_mood(image_path: Path, mood: str) -> tuple[Image.Image, bool]:
    """Use <stem>_<mood>.png if shipped alongside; else fall back to base PNG.

    Returns (image, is_mood_variant). When True, the caller should NOT also
    apply the procedural mood filter (the variant PNG already has expression).
    """
    variant = image_path.with_name(f"{image_path.stem}_{mood}.png")
    if variant.exists():
        return Image.open(variant).convert("RGBA"), True
    return Image.open(image_path).convert("RGBA"), False


def _macos_make_transparent(root: tk.Tk) -> bool:
    """Use PyObjC to give the Tk window a truly clear NSWindow background.

    This is intentionally disabled by default. PyObjC can segfault in native
    code on some Homebrew Python 3.14 + Tk 9 macOS builds before Python can
    catch an exception. Users can opt in with:

        CHIBI_EXPERIMENTAL_MACOS_PYOBJC_TRANSPARENCY=1

    Returns True when applied. Stable no-op unless explicitly enabled.
    """
    if sys.platform != "darwin":
        return False
    if os.environ.get("CHIBI_EXPERIMENTAL_MACOS_PYOBJC_TRANSPARENCY") != "1":
        return False
    try:
        import objc  # noqa: F401  — sanity-check pyobjc-core is importable
        from AppKit import NSColor
    except ImportError:
        return False
    try:
        import objc as _objc

        root.update_idletasks()
        nsview_id = root.winfo_id()
        nsview = _objc.objc_object(c_void_p=c_void_p(nsview_id))
        nswindow = nsview.window()
        if nswindow is None:
            return False
        nswindow.setOpaque_(False)
        nswindow.setBackgroundColor_(NSColor.clearColor())
        nswindow.setHasShadow_(False)
        return True
    except Exception as e:
        log.debug("PyObjC transparency failed: %s", e)
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
        return

    backoff = RECONNECT_BACKOFF_MIN_S
    while not stop_event.is_set():
        try:
            with ws_connect(url, open_timeout=3) as conn:
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
        except Exception as e:
            log.debug("ws reconnect in %.1fs after error: %s", backoff, e)
        if stop_event.wait(backoff):
            return
        backoff = min(RECONNECT_BACKOFF_MAX_S, backoff * 1.7)


def _send_ws_action(url: str | None, message: dict, event_queue: queue.Queue) -> None:
    """Send one small desktop action to the MCP WebSocket server."""
    if not url:
        event_queue.put({"type": "say", "text": "서버 연결이 필요해"})
        return
    try:
        from websockets.sync.client import connect as ws_connect
    except ImportError:
        event_queue.put({"type": "say", "text": "websockets 설치가 필요해"})
        return

    try:
        with ws_connect(url, open_timeout=3) as conn:
            conn.send(json.dumps(message, ensure_ascii=False))
    except Exception as exc:
        log.debug("window action send failed: %s", exc)
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
        self._min_width = min_width
        self._button_height = 34
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

    def _draw(self) -> None:
        width = max(self._min_width, int(self.winfo_width() or self._min_width))
        height = self._button_height
        self.delete("all")

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

        self._rounded_rect(3, 5, width - 2, height - 1, 13, fill=shadow, outline="")
        self._rounded_rect(1, 1, width - 3, height - 5, 13, fill=fill, outline=border, width=1)
        if self._focused and self._enabled:
            self._rounded_rect(3, 3, width - 5, height - 7, 11, fill="", outline=TEXT_FG, width=1)

        text_anchor = "center"
        text_x = width // 2
        if self._anchor == "w":
            text_anchor = "w"
            text_x = 16 if not self._colors.get("indicator") else 20

        if self._colors.get("indicator"):
            self._rounded_rect(8, 10, 12, 24, 3, fill=self._colors["indicator"], outline="")

        if self._icon:
            self.create_oval(8, 8, 25, 25, fill=icon_bg, outline="")
            self.create_text(16, 16, text=self._icon, fill=fg, font=("Helvetica", 8, "bold"))
            text_x = width // 2 + 9 if self._anchor != "w" else 32
            text_anchor = "center" if self._anchor != "w" else "w"

        self.create_text(
            text_x,
            16,
            text=self._text,
            anchor=text_anchor,
            fill=fg,
            font=("Helvetica", 9, "bold"),
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
        self._card_width = width
        self._card_height = 66
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

    def set_mood(self, mood: str) -> None:
        self._mood = mood
        self._draw()

    def set_identity(self, *, name: str, rarity: int) -> None:
        self._display_name = name
        self._rarity = rarity
        self._draw()

    def set_progress(self, progress: str) -> None:
        self._progress = progress or "리듬 준비"
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

    def _draw(self) -> None:
        width = max(280, int(self.winfo_width() or self._card_width))
        height = self._card_height
        mood_label, mood_icon = MOOD_LABELS.get(self._mood, (self._mood, "•"))
        stars = "★" * self._rarity + "☆" * max(0, 5 - self._rarity)

        self.delete("all")
        self._rounded_rect(6, 8, width - 5, height - 2, 18, fill=STATUS_SHADOW, outline="")
        self._rounded_rect(
            3,
            2,
            width - 8,
            height - 8,
            18,
            fill=STATUS_BG,
            outline=STATUS_BORDER,
            width=1,
        )
        self.create_text(
            18,
            19,
            text=self._display_name,
            anchor="w",
            fill=TEXT_FG,
            font=("Helvetica", 13, "bold"),
        )
        self.create_text(
            width - 24,
            19,
            text=stars,
            anchor="e",
            fill="#5f4d3f",
            font=("Helvetica", 10, "bold"),
        )

        self._rounded_rect(
            16,
            36,
            92,
            57,
            10,
            fill=STATUS_CHIP_BG,
            outline=STATUS_CHIP_BORDER,
            width=1,
        )
        self.create_text(
            54,
            46,
            text=f"{mood_label} {mood_icon}",
            fill=TEXT_FG,
            font=("Helvetica", 9, "bold"),
        )
        self.create_text(
            104,
            46,
            text=self._progress,
            anchor="w",
            fill=MUTED_FG,
            font=("Helvetica", 9),
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
        self._drawer_render_signature: tuple | None = None
        self.frameless = frameless
        self.sounds_enabled = sounds

        self.base_image: Image.Image = _scale_to_fit(
            Image.open(image_path).convert("RGBA"), CANVAS_SIZE - 20
        )
        self._img_w, self._img_h = self.base_image.size
        # Cache (mood → rendered RGBA at display size). Variants bypass filter.
        self._mood_image_cache: dict[str, Image.Image] = {}
        self._option_cache: dict[tuple[int, int], list[Image.Image]] = {}

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
        self.root.attributes("-topmost", True)

        # Use a light panel by default. macOS PyObjC clear-window hacks are
        # opt-in only because incompatible Python/Tk/PyObjC builds can crash
        # the whole interpreter in native code.
        self._transparent = False
        if (
            sys.platform == "darwin"
            and os.environ.get("CHIBI_EXPERIMENTAL_MACOS_PYOBJC_TRANSPARENCY") == "1"
        ):
            with contextlib.suppress(tk.TclError):
                self.root.wm_attributes("-transparent", True)

        bg = PANEL_BG
        self.root.configure(bg=bg)

        # Frameless mode
        if self.frameless:
            with contextlib.suppress(tk.TclError):
                self.root.overrideredirect(True)
            # macOS workaround: re-assert topmost after overrideredirect
            self.root.update_idletasks()
            self.root.attributes("-topmost", True)

        # PyObjC clear background path is experimental opt-in only.
        self._macos_clear = False
        if sys.platform == "darwin":
            self._macos_clear = _macos_make_transparent(self.root)
            if self._macos_clear:
                self._transparent = True
                bg = "systemTransparent"
                with contextlib.suppress(tk.TclError):
                    self.root.configure(bg=bg)
                # Drop the -alpha translucent fallback when we have true clear
                with contextlib.suppress(tk.TclError):
                    self.root.wm_attributes("-alpha", 1.0)

        # Total window: character stage + compact identity/status card.
        total_w = max(CANVAS_SIZE + 72, self._img_w + 80)
        canvas_h = self._img_h + 28

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

        shadow_w = min(total_w - 52, max(80, self._img_w - 16))
        shadow_y = min(canvas_h - 14, self._canvas_center[1] + self._img_h // 2 - 8)
        self.canvas.create_oval(
            self._canvas_center[0] - shadow_w // 2,
            shadow_y - 5,
            self._canvas_center[0] + shadow_w // 2,
            shadow_y + 5,
            fill="#d8c1aa",
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

        # Bind drag + clicks on canvas and labels
        for w in (self.canvas, self.status_card):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._do_drag)
            w.bind("<Button-3>", lambda _e: self.shutdown())  # right-click close
        self.canvas.bind("<Double-Button-1>", self._squish)

        self.root.bind("<Escape>", lambda _e: self.shutdown())
        self.root.bind("<Command-w>", lambda _e: self.shutdown())
        self.root.bind("<Control-w>", lambda _e: self.shutdown())
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        self._place_and_raise()

        # Idle bob state
        self._bob_phase = 0.0
        # Track pending after() callbacks so shutdown can cancel them and
        # avoid "invalid command name" errors firing on the destroyed root.
        self._after_ids: set[str] = set()

    def _place_and_raise(self) -> None:
        """Make the first window placement visible on desktop launch."""
        with contextlib.suppress(tk.TclError):
            self.root.update_idletasks()
            screen_w = self.root.winfo_screenwidth()
            win_w = self.root.winfo_width()
            x = max(24, screen_w - win_w - 40)
            y = 80
            self.root.geometry(f"+{x}+{y}")
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            self.root.after(250, self.root.lift)

    # ── Rendering ────────────────────────────────────────────────────────────

    def _get_mood_image(self, mood: str) -> Image.Image:
        cached = self._mood_image_cache.get(mood)
        if cached is not None:
            return cached
        raw, is_variant = _load_image_for_mood(self.image_path, mood)
        scaled = _scale_to_fit(raw, CANVAS_SIZE - 20)
        # Variant PNGs (artist-drawn mood expressions) bypass the filter.
        out = scaled if is_variant else _apply_mood_filter(scaled, mood)
        out = self._apply_option_layers(out)
        self._mood_image_cache[mood] = out
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
        img = self._get_mood_image(mood)
        if scale is not None:
            sx, sy = scale
            img = img.resize(
                (max(1, int(img.width * sx)), max(1, int(img.height * sy))),
                Image.LANCZOS,
            )
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.itemconfigure(self._image_id, image=self._photo)
        self.current_mood = mood

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
        gacha = payload.get("gacha") or {}
        changed = False

        active_id = str(gacha.get("active_character_id") or "").strip()
        if active_id and active_id != self.character_id:
            character = self._catalog_item("characters", active_id)
            image_path = self._catalog_image_path(character)
            if character is not None and image_path is not None:
                try:
                    self.base_image = _scale_to_fit(
                        Image.open(image_path).convert("RGBA"), CANVAS_SIZE - 20
                    )
                except OSError as exc:
                    log.warning("active character image skipped: %s", exc)
                else:
                    self.image_path = image_path
                    self.character_id = active_id
                    self.name = self._display_name_for_character(character)
                    self.rarity = int(character.get("rarity", self.rarity) or self.rarity)
                    self._img_w, self._img_h = self.base_image.size
                    self._mood_image_cache.clear()
                    self._option_cache.clear()
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
        counters = payload.get("counters") or {}
        calls = counters.get("calls_since_slice")
        interval = counters.get("slice_interval")
        slices = counters.get("slices_today")
        gacha = payload.get("gacha") or {}
        tickets = gacha.get("tickets")

        parts: list[str] = []
        if calls is not None and interval:
            parts.append(f"{calls}/{interval}")
        if slices is not None:
            parts.append(f"리듬 {slices}")
        if tickets is not None:
            parts.append(f"티켓 {tickets}")
        self.status_card.set_progress(" · ".join(parts))

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
        return ChibiButton(
            parent,
            text,
            command,
            colors,
            panel_bg=panel_bg,
            icon=icon,
            min_width=min_width,
            anchor=anchor,
        )

    def _toggle_drawer(self, mode: str) -> None:
        if self.drawer_mode == mode and self.drawer.winfo_ismapped():
            self.drawer.pack_forget()
            self.drawer_mode = None
            self._drawer_render_signature = None
            return
        self.drawer_mode = mode
        self._render_drawer()
        if not self.drawer.winfo_ismapped():
            self.drawer.pack(pady=(0, 8), padx=10, fill="x")

    def _render_drawer(self) -> None:
        for child in self.drawer.winfo_children():
            child.destroy()
        if self.drawer_mode == "inventory":
            self._render_inventory_drawer()
        elif self.drawer_mode == "options":
            self._render_options_drawer()
        self._drawer_render_signature = self._current_drawer_signature()

    def _current_drawer_signature(self) -> tuple:
        state = _load_persisted_state()
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

    def _drawer_header(self, text: str) -> None:
        tk.Label(
            self.drawer,
            text=text,
            bg=PANEL_BG_2,
            fg=TEXT_FG,
            font=("Helvetica", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

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
        if not owned_ids:
            tk.Label(
                self.drawer,
                text="아직 보유 캐릭터가 없어",
                bg=PANEL_BG_2,
                fg=MUTED_FG,
                font=("Helvetica", 9),
            ).pack(anchor="w", pady=(0, 6))
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
            btn.pack(anchor="w", fill="x", pady=2)

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
            btn.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=(0, 6), pady=2)
            self._option_vars[f"{option_id}__button"] = btn

        actions = tk.Frame(self.drawer, bg=PANEL_BG_2)
        actions.pack(anchor="w", pady=(8, 0))
        self._make_button(
            actions,
            "적용",
            self._apply_options_from_drawer,
            kind="primary",
            icon="✓",
            min_width=74,
        ).pack(side="left", padx=(0, 6))
        self._make_button(
            actions,
            "해제",
            lambda: self._send_action("clear_active_options"),
            icon="x",
            min_width=74,
        ).pack(side="left")

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
        offset = int(BOB_AMPLITUDE_PX * math.sin(2 * math.pi * BOB_HZ * self._bob_phase))
        self.canvas.coords(
            self._image_id, self._canvas_center[0], self._canvas_center[1] + offset
        )
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
        base_y = self._canvas_center[1] + self._img_h // 2 - 12
        piece = self.canvas.create_oval(
            cx - 18,
            base_y - 8,
            cx + 18,
            base_y + 8,
            fill="#F6F1E8",
            outline="#CBA16A",
            width=2,
        )
        seam = self.canvas.create_line(
            cx - 8,
            base_y - 2,
            cx + 9,
            base_y + 2,
            fill="#E2C184",
            width=2,
        )

        def tick(step: int = 0) -> None:
            if step >= 16:
                with contextlib.suppress(tk.TclError):
                    self.canvas.delete(piece)
                    self.canvas.delete(seam)
                return
            with contextlib.suppress(tk.TclError):
                self.canvas.move(piece, 0, 2)
                self.canvas.move(seam, 0, 2)
            self._after(45, lambda: tick(step + 1))

        tick()

    def show_bubble(self, text: str) -> None:
        if not text:
            return
        clipped = text[:120] + ("…" if len(text) > 120 else "")
        self.bubble.configure(text=clipped)
        self._play_safe("bubble")
        try:
            self.bubble.pack(pady=(2, 10), padx=10, before=self.status_card)
        except (AttributeError, tk.TclError):
            self.bubble.pack(pady=(2, 10), padx=10)
        if self._bubble_hide_after is not None:
            with contextlib.suppress(tk.TclError):
                self.root.after_cancel(self._bubble_hide_after)
            self._after_ids.discard(self._bubble_hide_after)
        self._bubble_hide_after = self._after(BUBBLE_VISIBLE_MS, self._hide_bubble)

    def _hide_bubble(self) -> None:
        self.bubble.pack_forget()
        self._bubble_hide_after = None

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

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )

    def _do_drag(self, event: tk.Event) -> None:
        offset = getattr(self, "_drag_offset", None)
        if offset is None:
            return
        dx, dy = offset
        self.root.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")

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
            payload = evt.get("payload") or {}
            visual_changed = self._sync_visual_state(payload)
            mood = payload.get("mood")
            if mood and (mood != self.current_mood or visual_changed):
                self._render_image(mood)
                self._update_mood_label(mood)
            elif visual_changed:
                self._render_image(self.current_mood)
            gacha = payload.get("gacha") or {}
            active_options = gacha.get("active_option_ids")
            if isinstance(active_options, list):
                self.active_option_ids = [str(option_id) for option_id in active_options]
            self._update_progress_label(payload)
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
    )
    _write_ready_file(args.ready_file)
    win.start(args.ws)
    return 0


if __name__ == "__main__":
    sys.exit(main())
