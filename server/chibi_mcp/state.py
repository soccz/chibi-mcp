"""Character state — derives tteoki's mood from system metrics and call counter."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock

from .system_info import SystemSnapshot, read_snapshot


class Mood(str, Enum):
    CALM = "calm"          # 평온 — default
    PANTING = "panting"    # 헐떡 — CPU 80%+
    DROWSY = "drowsy"      # 졸림 — battery < 20% unplugged
    LONELY = "lonely"      # 시무룩 — long idle (no Claude calls)
    HAPPY = "happy"        # 기쁨 — recent Claude call
    SURPRISED = "surprised"  # 놀람 — CPU sudden spike
    JOYFUL = "joyful"      # 행복 — milestone (slice triggered)


# Slice trigger: every N Claude tool calls (user-decided default = 10)
DEFAULT_SLICE_INTERVAL = 10
LONELY_IDLE_SECONDS = 30 * 60  # 30 minutes
HAPPY_WINDOW_SECONDS = 30
SURPRISE_DELTA = 30.0  # CPU jump of 30%+ within one tick = surprise


@dataclass
class TteokiState:
    """In-memory state of the tteoki character.

    Thread-safe via a single lock. Counters reset only when the server process restarts
    (today's-work scope, intentional).
    """

    slice_interval: int = DEFAULT_SLICE_INTERVAL
    _lock: Lock = field(default_factory=Lock, repr=False)

    # Counters
    call_count: int = 0           # cumulative Claude tool calls since server start
    calls_since_slice: int = 0    # resets on each slice
    slices_today: int = 0         # cumulative slice events since server start

    # Timing
    started_at: float = field(default_factory=time.time)
    last_call_at: float | None = None

    # CPU spike detection
    last_cpu: float = 0.0

    def record_call(self) -> dict:
        """Increment call counters. Returns a dict signaling if a slice fired."""
        with self._lock:
            self.call_count += 1
            self.calls_since_slice += 1
            self.last_call_at = time.time()
            sliced = False
            if self.calls_since_slice >= self.slice_interval:
                self.calls_since_slice = 0
                self.slices_today += 1
                sliced = True
            return {
                "call_count": self.call_count,
                "calls_since_slice": self.calls_since_slice,
                "slices_today": self.slices_today,
                "sliced": sliced,
            }

    def compute_mood(self, snap: SystemSnapshot) -> Mood:
        """Derive mood from current snapshot and timing history."""
        now = time.time()

        with self._lock:
            last_call = self.last_call_at
            last_cpu = self.last_cpu
            self.last_cpu = snap.cpu_percent

        # Battery drowsiness wins if unplugged and low
        if (
            snap.battery_percent is not None
            and snap.battery_percent < 20
            and snap.battery_plugged is False
        ):
            return Mood.DROWSY

        # CPU sudden spike (≥30% jump)
        if snap.cpu_percent - last_cpu >= SURPRISE_DELTA and snap.cpu_percent > 50:
            return Mood.SURPRISED

        # Sustained high CPU
        if snap.cpu_percent >= 80:
            return Mood.PANTING

        # Recent Claude call → happy
        if last_call is not None and (now - last_call) <= HAPPY_WINDOW_SECONDS:
            return Mood.HAPPY

        # Long idle → lonely
        if last_call is None:
            session_age = now - self.started_at
            if session_age > LONELY_IDLE_SECONDS:
                return Mood.LONELY
        elif (now - last_call) > LONELY_IDLE_SECONDS:
            return Mood.LONELY

        return Mood.CALM

    def snapshot(self) -> dict:
        """Return a JSON-serializable snapshot of full state (for MCP/WebSocket)."""
        snap = read_snapshot(interval=0.0)
        mood = self.compute_mood(snap)

        with self._lock:
            now = time.time()
            session_seconds = int(now - self.started_at)
            idle_seconds = int(now - self.last_call_at) if self.last_call_at else None

            return {
                "mood": mood.value,
                "system": snap.to_dict(),
                "counters": {
                    "calls_total": self.call_count,
                    "calls_since_slice": self.calls_since_slice,
                    "slice_interval": self.slice_interval,
                    "slices_today": self.slices_today,
                },
                "timing": {
                    "session_seconds": session_seconds,
                    "idle_seconds": idle_seconds,
                },
            }


# Module-level singleton — one tteoki per server process
_STATE: TteokiState | None = None


def get_state() -> TteokiState:
    global _STATE
    if _STATE is None:
        _STATE = TteokiState()
    return _STATE


def reset_state_for_tests() -> None:
    """Test helper — DO NOT call from runtime code."""
    global _STATE
    _STATE = None
