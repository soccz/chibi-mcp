#!/usr/bin/env python3
"""Exercise open_pet_window through the shipped server subprocess path."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "server"
ASSET_DIR = SERVER_DIR / "chibi_mcp" / "assets"

os.environ["CHIBI_ASSET_DIR"] = str(ASSET_DIR)
os.environ["PYTHONPATH"] = (
    str(SERVER_DIR)
    if not os.environ.get("PYTHONPATH")
    else f"{SERVER_DIR}{os.pathsep}{os.environ['PYTHONPATH']}"
)
sys.path.insert(0, str(SERVER_DIR))


def main() -> int:
    with TemporaryDirectory() as home:
        os.environ["HOME"] = home
        # Regression guard: this legacy flag must not enter PyObjC anymore.
        os.environ["CHIBI_EXPERIMENTAL_MACOS_PYOBJC_TRANSPARENCY"] = "1"

        from chibi_mcp import server

        result = server.open_pet_window()
        try:
            assert result.get("opened") is True, result
            assert result.get("ready") is True, result
            assert result.get("pid"), result
            assert result.get("character"), result

            log_path = Path(str(result["log_path"]))
            if log_path.exists():
                log_text = log_path.read_text(encoding="utf-8", errors="replace")
                assert "Traceback" not in log_text, log_text[-2000:]
                assert "_objc" not in log_text, log_text[-2000:]
        finally:
            close_result = server.close_pet_window()
            assert close_result.get("closed") is True, close_result

    print("server window smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
