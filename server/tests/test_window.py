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
