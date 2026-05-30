"""Tests for the Tk floating window helpers."""

from __future__ import annotations

from chibi_mcp import window


def test_macos_pyobjc_transparency_is_opt_in(monkeypatch):
    monkeypatch.setattr(window.sys, "platform", "darwin")
    monkeypatch.delenv("CHIBI_EXPERIMENTAL_MACOS_PYOBJC_TRANSPARENCY", raising=False)

    class Root:
        def update_idletasks(self):
            raise AssertionError("PyObjC path should not run by default")

    assert window._macos_make_transparent(Root()) is False


def test_write_ready_file(tmp_path):
    ready = tmp_path / "ready.json"

    window._write_ready_file(str(ready))

    assert '"ready": true' in ready.read_text(encoding="utf-8")


def test_window_scale_is_clamped():
    assert window._clamp_window_scale(0.1) == window.WINDOW_MIN_SCALE
    assert window._clamp_window_scale(1.2) == 1.2
    assert window._clamp_window_scale(10.0) == window.WINDOW_MAX_SCALE
