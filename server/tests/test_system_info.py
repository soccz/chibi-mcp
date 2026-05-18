"""Tests for system_info.py — psutil wrapper."""

from __future__ import annotations

from chibi_mcp.system_info import SystemSnapshot, read_snapshot


def test_read_snapshot_returns_floats():
    snap = read_snapshot(interval=0.0)
    assert isinstance(snap, SystemSnapshot)
    assert isinstance(snap.cpu_percent, float)
    assert 0.0 <= snap.cpu_percent <= 100.0
    assert 0.0 <= snap.ram_percent <= 100.0
    # battery may be None on desktops
    if snap.battery_percent is not None:
        assert 0.0 <= snap.battery_percent <= 100.0
        assert isinstance(snap.battery_plugged, bool)


def test_to_dict_rounds_and_handles_no_battery():
    snap = SystemSnapshot(cpu_percent=12.345, ram_percent=67.891, battery_percent=None, battery_plugged=None)
    d = snap.to_dict()
    assert d == {
        "cpu_percent": 12.3,
        "ram_percent": 67.9,
        "battery_percent": None,
        "battery_plugged": None,
    }


def test_to_dict_with_battery():
    snap = SystemSnapshot(cpu_percent=10.0, ram_percent=20.0, battery_percent=55.555, battery_plugged=True)
    assert snap.to_dict()["battery_percent"] == 55.6
    assert snap.to_dict()["battery_plugged"] is True
