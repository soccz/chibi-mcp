"""Tests for generated local sound assets."""

from __future__ import annotations

import wave

import pytest

window = pytest.importorskip("chibi_mcp.window")


def test_ensure_sounds_generates_event_specific_wavs(tmp_path, monkeypatch):
    monkeypatch.setattr(window, "SOUND_DIR", tmp_path)

    sounds = window._ensure_sounds()

    assert {"bubble", "slice", "squish", "gacha", "rare", "option"} <= set(sounds)
    assert (tmp_path / ".version").read_text(encoding="utf-8") == window.SOUND_VERSION
    for path in sounds.values():
        assert path.exists()
        assert path.stat().st_size > 1000
        with wave.open(str(path), "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 22050
            assert wav.getnframes() > 1000
