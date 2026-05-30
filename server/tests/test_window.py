"""Tests for the Tk floating window helpers."""

from __future__ import annotations

import math

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


def test_view_mode_helpers_are_stable():
    assert window._normalize_view_mode("debug") == "debug"
    assert window._normalize_view_mode("bad") == "normal"
    assert window._initial_view_mode("compact") == "compact"
    assert window._next_view_mode("normal") == "debug"
    assert window._next_view_mode("debug") == "compact"
    assert window._next_view_mode("compact") == "normal"


def test_window_view_mode_prefs_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(window, "WINDOW_PREFS_FILE", tmp_path / "prefs.json")

    assert window._initial_view_mode() == "normal"
    window._save_window_prefs({"view_mode": "debug"})

    assert window._load_window_prefs()["view_mode"] == "debug"
    assert window._initial_view_mode() == "debug"
    assert window._initial_view_mode("compact") == "compact"


def test_resize_drag_scale_uses_larger_axis():
    assert window._scale_from_resize_drag(1.0, 100, 10, 400, 300) == 1.25
    assert window._scale_from_resize_drag(1.0, 10, 90, 400, 300) == 1.3
    assert window._scale_from_resize_drag(1.0, -1000, -1000, 400, 300) == window.WINDOW_MIN_SCALE


def test_system_hud_formats_developer_metrics():
    assert (
        window._format_system_hud(
            {
                "cpu_percent": 12.3,
                "ram_percent": 48.8,
                "battery_percent": 84.0,
                "battery_plugged": False,
            }
        )
        == "CPU 12% · RAM 49% · BAT 84%"
    )
    assert (
        window._format_system_hud(
            {
                "cpu_percent": 10,
                "ram_percent": 20,
                "battery_percent": 91,
                "battery_plugged": True,
            }
        )
        == "CPU 10% · RAM 20% · BAT 91%+"
    )


def test_system_hud_ignores_invalid_numbers():
    assert (
        window._format_system_hud(
            {
                "cpu_percent": math.nan,
                "ram_percent": math.inf,
                "battery_percent": True,
                "battery_plugged": False,
            }
        )
        == "CPU -- · RAM -- · BAT --"
    )


def test_status_warning_matches_mood_thresholds():
    assert window._metric_is_warn({"cpu_percent": 80, "battery_percent": 80, "battery_plugged": False})
    assert window._metric_is_warn({"cpu_percent": 10, "battery_percent": 19, "battery_plugged": False})
    assert not window._metric_is_warn({"cpu_percent": 10, "battery_percent": 19, "battery_plugged": True})
    assert not window._metric_is_warn({"cpu_percent": math.inf, "battery_percent": math.nan})


def test_tool_idle_and_mood_reason_labels_are_compact():
    assert window._format_tool_idle({"idle_seconds": 42}) == "툴 42초"
    assert window._format_tool_idle({"idle_seconds": 180}) == "툴 3분"
    assert window._format_tool_idle({"idle_seconds": 999999}) == "툴 99시간+"
    assert window._format_tool_idle({"idle_seconds": None}) == "툴 대기"
    assert window._mood_reason_for_payload("happy", {"timing": {"idle_seconds": 7}}) == "최근 tool call 7초"
    assert window._mood_reason_for_payload("lonely", {"timing": {"idle_seconds": 3700}}) == "오래 idle 1시간"


def test_click_reaction_prioritizes_system_context():
    assert (
        window._click_reaction_for_payload("calm", {"system": {"cpu_percent": 91}})
        == "CPU 91% · 잠깐 숨 고르는 중"
    )
    assert (
        window._click_reaction_for_payload(
            "calm",
            {"system": {"battery_percent": 9, "battery_plugged": False}},
        )
        == "BAT 9% · 충전 필요"
    )
    assert (
        window._click_reaction_for_payload("happy", {"timing": {"idle_seconds": 3}})
        == "최근 tool call 3초"
    )


def test_display_counters_are_bounded():
    assert window._format_counter(0) == "0"
    assert window._format_counter(999) == "999"
    assert window._format_counter(1000) == "999+"
    assert window._format_counter(math.nan) is None


def test_debug_hud_formats_next_ticket_context():
    assert (
        window._format_debug_hud(
            {
                "mood": "happy",
                "timing": {"idle_seconds": 4},
                "counters": {"calls_total": 123, "slices_today": 12},
                "gacha": {"tickets": 2},
            }
        )
        == "최근 tool call 4초 · 티켓 2 · call티켓 77 · slice티켓 8"
    )
