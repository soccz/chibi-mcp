"""Tk window that shows the active 치비 character as a small floating pet.

Runs as a standalone subprocess spawned by the MCP server's `open_pet_window`
tool. Reads everything from CLI args, holds no shared state with the server —
so the window survives MCP server restarts.

Usage:
    python -m chibi_mcp.window --image /path/to.png --name 가래떡 --rarity 2 --mood happy
"""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path


def _build_window(image_path: Path, name: str, rarity: int, mood: str) -> tk.Tk:
    root = tk.Tk()
    root.title(f"치비 — {name}")
    root.attributes("-topmost", True)
    root.configure(bg="#1a1a1a")
    root.geometry("+240+200")

    photo = tk.PhotoImage(file=str(image_path))
    w, h = photo.width(), photo.height()
    max_side = 220
    if max(w, h) > max_side:
        ratio = max(1, max(w, h) // max_side)
        photo = photo.subsample(ratio)

    img_label = tk.Label(root, image=photo, bg="#1a1a1a", borderwidth=0)
    img_label.image = photo  # keep a ref so GC doesn't collect
    img_label.pack(padx=14, pady=(14, 6))

    stars = "★" * rarity + "☆" * max(0, 5 - rarity)
    name_label = tk.Label(
        root,
        text=f"{name}  {stars}",
        bg="#1a1a1a",
        fg="#ffffff",
        font=("Helvetica", 13),
    )
    name_label.pack()

    mood_label = tk.Label(
        root,
        text=f"기분: {mood}",
        bg="#1a1a1a",
        fg="#aaaaaa",
        font=("Helvetica", 10),
    )
    mood_label.pack(pady=(2, 12))

    # Drag-to-move (works even with native title bar)
    def start_drag(event: tk.Event) -> None:
        root._drag_offset = (  # type: ignore[attr-defined]
            event.x_root - root.winfo_x(),
            event.y_root - root.winfo_y(),
        )

    def do_drag(event: tk.Event) -> None:
        offset = getattr(root, "_drag_offset", None)
        if offset is None:
            return
        dx, dy = offset
        root.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")

    for widget in (img_label, name_label, mood_label):
        widget.bind("<Button-1>", start_drag)
        widget.bind("<B1-Motion>", do_drag)

    # Squish on left-click of the image — quick scale-down then back
    def squish(_event: tk.Event) -> None:
        img_label.configure(padx=6, pady=6)
        root.after(120, lambda: img_label.configure(padx=0, pady=0))

    img_label.bind("<Double-Button-1>", squish)

    root.bind("<Escape>", lambda _e: root.destroy())
    root.bind("<Command-w>", lambda _e: root.destroy())
    root.bind("<Control-w>", lambda _e: root.destroy())

    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chibi_mcp.window")
    parser.add_argument("--image", required=True, help="Absolute path to character PNG")
    parser.add_argument("--name", default="치비", help="Korean display name")
    parser.add_argument("--rarity", type=int, default=2, help="Rarity 1-5 (★ count)")
    parser.add_argument("--mood", default="calm", help="Mood string for the label")
    args = parser.parse_args(argv)

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        print(f"image not found: {image_path}", file=sys.stderr)
        return 1

    root = _build_window(image_path, args.name, args.rarity, args.mood)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
