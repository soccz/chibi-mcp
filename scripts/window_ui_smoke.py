#!/usr/bin/env python3
"""Exercise the Tk floating window with real widgets.

Run this under a desktop session or xvfb. It intentionally avoids the
WebSocket server so it can focus on local window behavior.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
os.environ["CHIBI_ASSET_DIR"] = str(ROOT / "server" / "chibi_mcp" / "assets")
sys.path.insert(0, str(ROOT / "server"))


def main() -> int:
    with TemporaryDirectory() as home:
        os.environ["HOME"] = home

        from chibi_mcp.window import PetWindow

        asset_dir = ROOT / "server" / "chibi_mcp" / "assets"
        pet = PetWindow(
            asset_dir / "white_tteok.png",
            "White Chibi",
            2,
            "calm",
            asset_dir=asset_dir,
            character_id="white_tteok",
            frameless=False,
            sounds=False,
        )
        try:
            pet.root.update_idletasks()
            base_photo = pet._photo.width(), pet._photo.height()
            base_canvas = int(pet.canvas.cget("width")), int(pet.canvas.cget("height"))
            base_root_h = pet.root.winfo_height()

            pet._start_resize(SimpleNamespace(x_root=0, y_root=0))
            pet._do_resize(SimpleNamespace(x_root=140, y_root=140))
            pet._end_resize(SimpleNamespace())
            pet.root.update_idletasks()
            assert pet._photo.width() > base_photo[0]
            assert pet._photo.height() > base_photo[1]
            assert int(pet.canvas.cget("width")) > base_canvas[0]
            assert int(pet.canvas.cget("height")) > base_canvas[1]
            assert pet.root.winfo_height() > base_root_h

            pet._reset_window_scale()
            pet.root.update_idletasks()
            assert abs(pet._window_scale - 1.0) < 0.01

            pet._toggle_drawer("options")
            pet.root.update_idletasks()
            assert pet.drawer.winfo_ismapped()
            assert hasattr(pet, "_option_vars")
            for option_id in ("jocheong_drip", "honey_glaze", "sugar_beads"):
                pet._toggle_option_chip(option_id)
            pet._toggle_option_chip("rainbow_sprinkles")
            pet.root.update_idletasks()
            assert "3" in str(pet.bubble.cget("text"))

            before_character = pet.character_id
            pet._handle_event(
                {
                    "type": "state",
                    "payload": {
                        "mood": "happy",
                        "gacha": {
                            "active_character_id": "garaetteok_short",
                            "active_option_ids": ["honey_glaze"],
                            "tickets": 1,
                            "total_pulls": 1,
                        },
                        "counters": {
                            "calls_since_slice": 1,
                            "slice_interval": 10,
                            "slices_today": 0,
                        },
                        "timing": {
                            "idle_seconds": 3,
                        },
                        "system": {
                            "cpu_percent": 82.0,
                            "ram_percent": 48.0,
                            "battery_percent": 17.0,
                            "battery_plugged": False,
                        },
                    },
                }
            )
            pet.root.update_idletasks()
            assert before_character != pet.character_id
            assert pet.character_id == "garaetteok_short"
            assert pet.active_option_ids == ["honey_glaze"]
            assert pet.status_card._system_warn is True
            assert "CPU 82%" in pet.status_card._system_hud

            pet._start_drag(SimpleNamespace(x_root=10, y_root=10, widget=pet.canvas))
            pet._end_drag(SimpleNamespace())
            pet.root.update_idletasks()
            assert "CPU 82%" in str(pet.bubble.cget("text"))

            pet._start_drag(SimpleNamespace(x_root=10, y_root=10, widget=pet.status_card))
            pet._end_drag(SimpleNamespace())
            pet.root.update_idletasks()
            assert "리듬 1/10" in str(pet.bubble.cget("text"))

            pet._toggle_drawer("options")
            pet.root.update_idletasks()
            assert not pet.drawer.winfo_ismapped()
        finally:
            pet.shutdown()
    print("window UI smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
