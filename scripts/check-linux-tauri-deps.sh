#!/usr/bin/env bash
set -euo pipefail

SOFT=0
if [[ "${1:-}" == "--soft" ]]; then
  SOFT=1
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  exit 0
fi

if ! command -v pkg-config >/dev/null 2>&1; then
  if (( SOFT )); then
    echo "skip: pkg-config is not installed; local Linux Tauri backend check skipped."
    exit 2
  else
    echo "fail: pkg-config is required for Linux Tauri builds." >&2
    echo "install: sudo apt-get install -y pkg-config" >&2
    exit 1
  fi
fi

missing=()
for pkg in webkit2gtk-4.1 javascriptcoregtk-4.1 glib-2.0 atk; do
  if ! pkg-config --exists "$pkg"; then
    missing+=("$pkg")
  fi
done

if (( ${#missing[@]} > 0 )); then
  if (( SOFT )); then
    echo "skip: missing Linux Tauri pkg-config packages: ${missing[*]}"
    echo "      install with: sudo apt-get install -y libwebkit2gtk-4.1-dev build-essential curl wget file pkg-config libdbus-1-dev libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev"
    exit 2
  else
    echo "fail: missing Linux Tauri pkg-config packages: ${missing[*]}" >&2
    echo "Ubuntu/Debian install:" >&2
    echo "  sudo apt-get install -y libwebkit2gtk-4.1-dev build-essential curl wget file pkg-config libdbus-1-dev libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev" >&2
    exit 1
  fi
fi
