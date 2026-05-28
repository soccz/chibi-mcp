"""Tk window for the floating 치비.

Live behaviour:
    - Connects to the local WebSocket (ws://127.0.0.1:9876) in a thread.
    - State events update the mood label + re-tint the character image.
    - Slice events play a quick flash + bounce.
    - Say events show a speech bubble below the image for 4 seconds.

Visual:
    - Transparent window background on macOS (via -transparent attribute).
    - Falls back to dark bg on Linux/Windows if transparency unavailable.
    - Mood applied as a Pillow filter at runtime (brightness/saturation/tint)
      so we don't need 56 hand-drawn mood-variant PNGs.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageEnhance, ImageTk

log = logging.getLogger(__name__)

WINDOW_SIZE = 240
RECONNECT_BACKOFF_SECONDS = 2.0
POLL_INTERVAL_MS = 80
BUBBLE_VISIBLE_MS = 4000


# ── Mood → Pillow filter ─────────────────────────────────────────────────────

# Each entry: (brightness, saturation, tint_color, tint_alpha)
# tint_alpha 0.0 = no tint; 0.35 = noticeable.
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
    """Apply mood-specific Pillow filter to a PNG with alpha."""
    cfg = MOOD_FILTERS.get(mood, MOOD_FILTERS["calm"])
    brightness, saturation, tint_rgb, tint_alpha = cfg

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)

    if tint_rgb and tint_alpha > 0:
        # Blend a flat color layer over RGB while preserving original alpha
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


# ── WebSocket subscriber thread ──────────────────────────────────────────────


def _ws_listener(url: str, event_queue: queue.Queue, stop_event: threading.Event) -> None:
    """Background thread: connects to chibi-mcp WS and pushes events into queue."""
    try:
        from websockets.sync.client import connect as ws_connect
    except ImportError:
        log.warning("websockets sync client unavailable — window won't get live updates")
        return

    while not stop_event.is_set():
        try:
            with ws_connect(url, open_timeout=3) as conn:
                for raw in conn:
                    if stop_event.is_set():
                        return
                    with contextlib.suppress(json.JSONDecodeError, queue.Full):
                        event_queue.put_nowait(json.loads(raw))
        except Exception as e:
            log.debug("ws reconnect after error: %s", e)
        if stop_event.wait(RECONNECT_BACKOFF_SECONDS):
            return


# ── Tk window ────────────────────────────────────────────────────────────────


class PetWindow:
    def __init__(self, image_path: Path, name: str, rarity: int, mood: str):
        self.image_path = image_path
        self.name = name
        self.rarity = rarity
        self.current_mood = mood
        self.base_image: Image.Image = _scale_to_fit(
            Image.open(image_path).convert("RGBA"), WINDOW_SIZE - 20
        )

        self.event_queue: queue.Queue = queue.Queue(maxsize=64)
        self.stop_event = threading.Event()

        self.root = tk.Tk()
        self.root.title(f"치비 — {name}")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(False)  # keep title bar for drag/close

        # Try transparency on macOS
        self._transparent = False
        if sys.platform == "darwin":
            try:
                self.root.wm_attributes("-transparent", True)
                self.root.configure(bg="systemTransparent")
                self._transparent = True
            except tk.TclError:
                pass
        if not self._transparent:
            self.root.configure(bg="#1a1a1a")

        bg = "systemTransparent" if self._transparent else "#1a1a1a"
        fg = "#ffffff" if not self._transparent else "#222222"
        meta_fg = "#aaaaaa" if not self._transparent else "#555555"

        self.img_label = tk.Label(self.root, bg=bg, borderwidth=0, highlightthickness=0)
        self.img_label.pack(padx=10, pady=(10, 4))

        stars = "★" * rarity + "☆" * max(0, 5 - rarity)
        self.name_label = tk.Label(
            self.root,
            text=f"{name}  {stars}",
            bg=bg,
            fg=fg,
            font=("Helvetica", 13, "bold"),
        )
        self.name_label.pack()

        self.mood_label = tk.Label(
            self.root,
            text=f"기분: {mood}",
            bg=bg,
            fg=meta_fg,
            font=("Helvetica", 10),
        )
        self.mood_label.pack(pady=(2, 4))

        # Speech bubble — hidden until pet_say fires
        self.bubble = tk.Label(
            self.root,
            text="",
            bg="#ffffff" if not self._transparent else "#ffffe0",
            fg="#222222",
            font=("Helvetica", 10),
            wraplength=WINDOW_SIZE - 30,
            padx=10,
            pady=6,
            relief="solid",
            borderwidth=1,
        )
        # Don't pack — toggled via show_bubble.
        self._bubble_hide_after: str | None = None

        # Apply initial mood
        self._render_image(mood)

        # Interactions
        for w in (self.img_label, self.name_label, self.mood_label):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._do_drag)

        self.img_label.bind("<Double-Button-1>", self._squish)

        self.root.bind("<Escape>", lambda _e: self.shutdown())
        self.root.bind("<Command-w>", lambda _e: self.shutdown())
        self.root.bind("<Control-w>", lambda _e: self.shutdown())
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    # ── Rendering ────────────────────────────────────────────────────────────

    def _render_image(self, mood: str) -> None:
        filtered = _apply_mood_filter(self.base_image, mood)
        self._photo = ImageTk.PhotoImage(filtered)
        self.img_label.configure(image=self._photo)
        self.current_mood = mood

    def _update_mood_label(self, mood: str) -> None:
        emoji = {
            "calm": "😌", "happy": "😊", "joyful": "🤩", "panting": "😅",
            "drowsy": "😴", "lonely": "🥺", "surprised": "😮",
        }.get(mood, "•")
        self.mood_label.configure(text=f"기분: {mood} {emoji}")

    # ── Animations ───────────────────────────────────────────────────────────

    def _squish(self, _event: tk.Event) -> None:
        original = self.base_image
        squished = original.resize(
            (original.width, max(8, int(original.height * 0.6))),
            Image.LANCZOS,
        )
        self._photo = ImageTk.PhotoImage(_apply_mood_filter(squished, self.current_mood))
        self.img_label.configure(image=self._photo)
        self.root.after(180, lambda: self._render_image(self.current_mood))

    def _slice_flash(self) -> None:
        # Quick brightness pulse
        bright = _apply_mood_filter(
            ImageEnhance.Brightness(self.base_image).enhance(1.8),
            self.current_mood,
        )
        self._photo = ImageTk.PhotoImage(bright)
        self.img_label.configure(image=self._photo)
        self.root.after(140, lambda: self._render_image(self.current_mood))

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
            self.root.after_cancel(self._bubble_hide_after)
        self._bubble_hide_after = self.root.after(BUBBLE_VISIBLE_MS, self._hide_bubble)

    def _hide_bubble(self) -> None:
        self.bubble.pack_forget()
        self._bubble_hide_after = None

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
            self.root.after(POLL_INTERVAL_MS, self._poll_events)

    def _handle_event(self, evt: dict) -> None:
        kind = evt.get("type")
        if kind == "state":
            payload = evt.get("payload") or {}
            mood = payload.get("mood")
            if mood and mood != self.current_mood:
                self._render_image(mood)
                self._update_mood_label(mood)
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
        self.root.after(POLL_INTERVAL_MS, self._poll_events)
        self.root.mainloop()

    def shutdown(self) -> None:
        self.stop_event.set()
        with contextlib.suppress(tk.TclError):
            self.root.destroy()


# ── Entry point ──────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chibi_mcp.window")
    parser.add_argument("--image", required=True)
    parser.add_argument("--name", default="치비")
    parser.add_argument("--rarity", type=int, default=2)
    parser.add_argument("--mood", default="calm")
    parser.add_argument("--ws", default=None, help="WebSocket URL for live updates")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        print(f"image not found: {image_path}", file=sys.stderr)
        return 1

    win = PetWindow(image_path, args.name, args.rarity, args.mood)
    win.start(args.ws)
    return 0


if __name__ == "__main__":
    sys.exit(main())
