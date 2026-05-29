"""Tk window for the floating chibi.

v1.1 visual upgrade:
    - overrideredirect(True): no title bar — floats as a pure sprite.
    - macOS transparency: -transparent attribute + systemTransparent bg
      (with -alpha 0.92 fallback if the window manager doesn't honor it).
    - Canvas-based image rendering: bob animation via canvas.move (no flicker).
    - Idle bob: 4px gentle vertical oscillation, ~0.6 Hz, like a slime breathing.
    - Sounds: short procedurally-generated wavs played via `afplay` (darwin),
      `paplay`/`aplay` (linux), winsound (windows). Plays on dbl-click squish
      and on slice events.

Live behaviour (unchanged from v1.0):
    - Connects to ws://127.0.0.1:9876, receives state/say/slice events.
    - Mood filter applied to base PNG (brightness/saturation/tint).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import math
import queue
import struct
import subprocess
import sys
import threading
import tkinter as tk
import wave
from pathlib import Path

from PIL import Image, ImageEnhance, ImageTk

log = logging.getLogger(__name__)

CANVAS_SIZE = 240
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

    Tk's `-transparent` attribute is unreliable on macOS — many versions
    still render the window bg as solid. Reaching into the NSView/NSWindow
    via objc fixes it for real on macOS 11+.

    Returns True when applied. Safe no-op when pyobjc isn't installed or
    not on darwin.
    """
    if sys.platform != "darwin":
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
        nsview = _objc.objc_object(c_void_p=nsview_id)
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


# ── Procedural sounds ────────────────────────────────────────────────────────


def _ensure_sounds() -> dict[str, Path]:
    """Generate small wav files in ~/.chibi-mcp/sounds/ on first need."""
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "bubble": SOUND_DIR / "bubble.wav",
        "slice":  SOUND_DIR / "slice.wav",
    }
    if not paths["bubble"].exists():
        _write_bubble_wav(paths["bubble"])
    if not paths["slice"].exists():
        _write_slice_wav(paths["slice"])
    return paths


def _write_bubble_wav(path: Path) -> None:
    """A short rising-then-falling tone — like a soft 'boyoing'."""
    sr = 22050
    duration = 0.28
    n = int(sr * duration)
    frames = bytearray()
    for i in range(n):
        t = i / sr
        # Pitch: 360 Hz → 720 Hz → 540 Hz
        env_t = i / n
        if env_t < 0.5:
            freq = 360 + (720 - 360) * (env_t * 2)
        else:
            freq = 720 - (720 - 540) * ((env_t - 0.5) * 2)
        # Smooth attack + decay envelope
        env = (1.0 - abs(2 * env_t - 1)) ** 1.3
        sample = int(0.32 * 32767 * env * math.sin(2 * math.pi * freq * t))
        frames += struct.pack("<h", max(-32768, min(32767, sample)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))


def _write_slice_wav(path: Path) -> None:
    """A short descending sweep — like a soft 'schhk' slice."""
    sr = 22050
    duration = 0.18
    n = int(sr * duration)
    frames = bytearray()
    import random as _r

    for i in range(n):
        env_t = i / n
        # Frequency sweeps down 1600 -> 400 Hz, mixed with noise
        freq = 1600 - (1600 - 400) * env_t
        env = (1.0 - env_t) ** 1.4
        tone = math.sin(2 * math.pi * freq * (i / sr))
        noise = (_r.random() * 2 - 1) * 0.6
        sample = int(0.28 * 32767 * env * (tone * 0.4 + noise * 0.6))
        frames += struct.pack("<h", max(-32768, min(32767, sample)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))


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


# ── Tk window ────────────────────────────────────────────────────────────────


class PetWindow:
    def __init__(
        self,
        image_path: Path,
        name: str,
        rarity: int,
        mood: str,
        option_paths: list[Path] | None = None,
        frameless: bool = True,
        sounds: bool = True,
    ):
        self.image_path = image_path
        self.name = name
        self.rarity = rarity
        self.current_mood = mood
        self.option_paths = option_paths or []
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

        # Transparency on macOS
        self._transparent = False
        if sys.platform == "darwin":
            try:
                self.root.wm_attributes("-transparent", True)
                self._transparent = True
            except tk.TclError:
                pass
            # Translucent fallback if -transparent doesn't really clear bg
            with contextlib.suppress(tk.TclError):
                self.root.wm_attributes("-alpha", 0.96)

        bg = "systemTransparent" if self._transparent else "#1a1a1a"
        try:
            self.root.configure(bg=bg)
        except tk.TclError:
            bg = "#1a1a1a"
            self.root.configure(bg=bg)

        # Frameless mode
        if self.frameless:
            with contextlib.suppress(tk.TclError):
                self.root.overrideredirect(True)
            # macOS workaround: re-assert topmost after overrideredirect
            self.root.update_idletasks()
            self.root.attributes("-topmost", True)

        # PyObjC: try a real clear NSWindow background on macOS. The Tk
        # -transparent attribute alone is unreliable; this nukes the bg
        # for real on macOS 11+ when pyobjc-framework-Cocoa is available.
        self._macos_clear = False
        if sys.platform == "darwin":
            self._macos_clear = _macos_make_transparent(self.root)
            if self._macos_clear:
                self._transparent = True
                # Drop the -alpha translucent fallback when we have true clear
                with contextlib.suppress(tk.TclError):
                    self.root.wm_attributes("-alpha", 1.0)

        # Total window: canvas + name label + mood label
        total_w = max(CANVAS_SIZE, self._img_w + 24)
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
            fill="#000000",
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

        fg = "#222222" if self._transparent else "#ffffff"
        meta_fg = "#555555" if self._transparent else "#aaaaaa"

        stars = "★" * rarity + "☆" * max(0, 5 - rarity)
        self.name_label = tk.Label(
            self.root,
            text=f"{name}  {stars}",
            bg=bg,
            fg=fg,
            font=("Helvetica", 13, "bold"),
        )
        self.name_label.pack(pady=(2, 0))

        self.mood_label = tk.Label(
            self.root,
            text=f"기분: {mood}",
            bg=bg,
            fg=meta_fg,
            font=("Helvetica", 10),
        )
        self.mood_label.pack(pady=(2, 6))
        self._update_mood_label(mood)

        self.progress_label = tk.Label(
            self.root,
            text="",
            bg=bg,
            fg=meta_fg,
            font=("Helvetica", 9),
        )
        self.progress_label.pack(pady=(0, 8))

        # Speech bubble
        self.bubble = tk.Label(
            self.root,
            text="",
            bg="#ffffe0" if self._transparent else "#ffffff",
            fg="#222222",
            font=("Helvetica", 10),
            wraplength=total_w - 30,
            padx=10,
            pady=6,
            relief="solid",
            borderwidth=1,
        )
        self._bubble_hide_after: str | None = None

        # Bind drag + clicks on canvas and labels
        for w in (self.canvas, self.name_label, self.mood_label, self.progress_label):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._do_drag)
            w.bind("<Button-3>", lambda _e: self.shutdown())  # right-click close
        self.canvas.bind("<Double-Button-1>", self._squish)

        self.root.bind("<Escape>", lambda _e: self.shutdown())
        self.root.bind("<Command-w>", lambda _e: self.shutdown())
        self.root.bind("<Control-w>", lambda _e: self.shutdown())
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        # Idle bob state
        self._bob_phase = 0.0
        # Track pending after() callbacks so shutdown can cancel them and
        # avoid "invalid command name" errors firing on the destroyed root.
        self._after_ids: set[str] = set()

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

    def _update_mood_label(self, mood: str) -> None:
        label, emoji = MOOD_LABELS.get(mood, (mood, "•"))
        self.mood_label.configure(text=f"{label} {emoji}")

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
            parts.append(f"{slices}도막")
        if tickets is not None:
            parts.append(f"티켓 {tickets}")
        self.progress_label.configure(text=" · ".join(parts))

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
        self._play_safe("bubble")
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
        try:
            self.bubble.pack(pady=(2, 10), padx=10, before=self.mood_label)
        except tk.TclError:
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
            mood = payload.get("mood")
            if mood and mood != self.current_mood:
                self._render_image(mood)
                self._update_mood_label(mood)
            self._update_progress_label(payload)
        elif kind == "slice":
            self._slice_flash()
        elif kind == "say":
            self.show_bubble(evt.get("text", ""))

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self, ws_url: str | None) -> None:
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
    parser.add_argument("--ws", default=None, help="WebSocket URL for live updates")
    parser.add_argument(
        "--no-frameless", action="store_true",
        help="Show the OS title bar (default: frameless)",
    )
    parser.add_argument(
        "--no-sounds", action="store_true",
        help="Disable click/slice sound effects",
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

    win = PetWindow(
        image_path,
        args.name,
        args.rarity,
        args.mood,
        option_paths=option_paths,
        frameless=not args.no_frameless,
        sounds=not args.no_sounds,
    )
    win.start(args.ws)
    return 0


if __name__ == "__main__":
    sys.exit(main())
