#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Runtime desktop prerequisites =="

"$ROOT/scripts/check-linux-tauri-deps.sh"

python - <<'PY'
import os
import sys

try:
    import tkinter
except Exception as exc:
    raise SystemExit(
        "fail: Python tkinter unavailable; open_pet_window cannot show a Tk window. "
        "Ubuntu/Debian system Python: sudo apt-get install -y python3-tk. "
        "pyenv Python: install tk-dev, then rebuild the Python version used by pipx. "
        f"({exc})"
    )

if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    raise SystemExit(
        "fail: no Linux desktop display session found. Run from a desktop session "
        "or set DISPLAY/WAYLAND_DISPLAY for GUI forwarding."
    )

root = tkinter.Tk()
root.update_idletasks()
root.destroy()

print("desktop runtime ok")
PY

(
  cd "$ROOT/desktop/src-tauri"
  cargo fmt -- --check
  cargo check --all-targets
)

echo "runtime checks passed"
