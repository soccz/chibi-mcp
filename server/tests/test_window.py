"""Tests for the Tk floating window helpers."""

from __future__ import annotations

from chibi_mcp import window


def test_macos_pyobjc_transparency_is_disabled_even_if_env_set(monkeypatch):
    monkeypatch.setattr(window.sys, "platform", "darwin")
    monkeypatch.setenv("CHIBI_EXPERIMENTAL_MACOS_PYOBJC_TRANSPARENCY", "1")

    class Root:
        def update_idletasks(self):
            raise AssertionError("PyObjC path should never run")

    assert window._macos_make_transparent(Root()) is False


def test_write_ready_file(tmp_path):
    ready = tmp_path / "ready.json"

    window._write_ready_file(str(ready))

    assert '"ready": true' in ready.read_text(encoding="utf-8")


def test_window_scale_is_clamped():
    assert window._clamp_window_scale(0.1) == window.WINDOW_MIN_SCALE
    assert window._clamp_window_scale(1.2) == 1.2
    assert window._clamp_window_scale(10.0) == window.WINDOW_MAX_SCALE


def test_resize_drag_scale_uses_larger_axis():
    assert window._scale_from_resize_drag(1.0, 100, 10, 400, 300) == 1.25
    assert window._scale_from_resize_drag(1.0, 10, 90, 400, 300) == 1.3
    assert window._scale_from_resize_drag(1.0, -1000, -1000, 400, 300) == window.WINDOW_MIN_SCALE
