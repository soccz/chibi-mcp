"""System metrics (CPU, RAM, battery) via psutil."""

from __future__ import annotations

from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class SystemSnapshot:
    cpu_percent: float
    ram_percent: float
    battery_percent: float | None  # None when no battery (desktop)
    battery_plugged: bool | None

    def to_dict(self) -> dict:
        return {
            "cpu_percent": round(self.cpu_percent, 1),
            "ram_percent": round(self.ram_percent, 1),
            "battery_percent": (
                round(self.battery_percent, 1) if self.battery_percent is not None else None
            ),
            "battery_plugged": self.battery_plugged,
        }


def read_snapshot(interval: float = 0.0) -> SystemSnapshot:
    """Read current CPU/RAM/battery state.

    interval=0.0 returns the cached value since last call (non-blocking).
    interval>0 measures CPU over that window (blocking).
    """
    cpu = psutil.cpu_percent(interval=interval)
    ram = psutil.virtual_memory().percent
    bat = psutil.sensors_battery()
    if bat is None:
        return SystemSnapshot(cpu_percent=cpu, ram_percent=ram, battery_percent=None, battery_plugged=None)
    return SystemSnapshot(
        cpu_percent=cpu,
        ram_percent=ram,
        battery_percent=bat.percent,
        battery_plugged=bat.power_plugged,
    )
