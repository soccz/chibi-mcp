"""chibi state — mood derivation + gacha inventory + persistence.

Persistence: only inventory/tickets/active character are persisted across
server restarts. Counters (calls, slices) reset per server lifecycle by design.
"""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from threading import Lock

from .system_info import SystemSnapshot, read_snapshot

log = logging.getLogger(__name__)


class Mood(StrEnum):
    CALM = "calm"
    PANTING = "panting"
    DROWSY = "drowsy"
    LONELY = "lonely"
    HAPPY = "happy"
    SURPRISED = "surprised"
    JOYFUL = "joyful"


# Slice trigger: every N Claude tool calls (user-decided default = 10)
DEFAULT_SLICE_INTERVAL = 10
LONELY_IDLE_SECONDS = 30 * 60  # 30 minutes
HAPPY_WINDOW_SECONDS = 30
SURPRISE_DELTA = 30.0

# Gacha config
RARITY_WEIGHTS = {5: 1, 4: 5, 3: 24, 2: 70}  # %
TICKETS_PER_100_CALLS = 1
TICKETS_PER_10_SLICES = 1

# Persistence
STATE_DIR = Path.home() / ".chibi-mcp"
STATE_FILE = STATE_DIR / "state.json"
STATE_SCHEMA_VERSION = 3


@dataclass
class ChibiState:
    """In-memory + persisted state of the active chibi collection."""

    slice_interval: int = DEFAULT_SLICE_INTERVAL
    _lock: Lock = field(default_factory=Lock, repr=False)

    # Runtime-only counters (not persisted)
    call_count: int = 0
    calls_since_slice: int = 0
    slices_today: int = 0
    started_at: float = field(default_factory=time.time)
    last_call_at: float | None = None
    last_activity_source: str | None = None
    last_cpu: float = 0.0

    # Persisted state
    active_character_id: str | None = None
    active_option_ids: list[str] = field(default_factory=list)
    inventory: dict[str, dict] = field(default_factory=dict)
    tickets: int = 0
    last_free_pull_date: str | None = None  # ISO date
    total_pulls: int = 0
    last_pull: dict | None = None

    # ── Persistence ──────────────────────────────────────────────────────────

    def _persisted_dict(self) -> dict:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "active_character_id": self.active_character_id,
            "active_option_ids": self.active_option_ids,
            "inventory": self.inventory,
            "tickets": self.tickets,
            "last_free_pull_date": self.last_free_pull_date,
            "total_pulls": self.total_pulls,
            "last_pull": self.last_pull,
        }

    def save(self) -> None:
        """Persist to ~/.chibi-mcp/state.json.

        Snapshots data while briefly holding the lock, then writes the file
        without it — so file I/O doesn't block other state mutations.
        """
        with self._lock:
            data = self._persisted_dict()
        self._save_data(data)

    @staticmethod
    def _save_data(data: dict) -> None:
        """Write a pre-snapshotted dict. Caller must NOT hold the instance lock.

        Serialized via _SAVE_LOCK so concurrent callers (e.g. record_call
        granting a ticket while pull_gacha persists an inventory change) don't
        race on tmp file write + rename, which would silently lose one of
        the snapshots (last-write-wins).
        """
        with _SAVE_LOCK:
            try:
                STATE_DIR.mkdir(parents=True, exist_ok=True)
                tmp = STATE_FILE.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
                tmp.replace(STATE_FILE)
            except OSError as e:
                log.warning("state save failed: %s", e)

    def load(self) -> None:
        """Hydrate from ~/.chibi-mcp/state.json. Tolerates missing file."""
        if not STATE_FILE.exists():
            return
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            log.warning("state load failed (%s) — starting fresh", e)
            return
        with self._lock:
            self.active_character_id = data.get("active_character_id")
            self.active_option_ids = _clean_option_ids(data.get("active_option_ids"))
            self.inventory = data.get("inventory") or {}
            self.tickets = int(data.get("tickets", 0))
            self.last_free_pull_date = data.get("last_free_pull_date")
            self.total_pulls = int(data.get("total_pulls", 0))
            last_pull = data.get("last_pull")
            self.last_pull = last_pull if isinstance(last_pull, dict) else None

    # ── Call tracking + ticket grants ────────────────────────────────────────

    def record_call(self, force_slice: bool = False) -> dict:
        """Increment call counters. Auto-grants tickets at milestones."""
        save_data: dict | None = None
        with self._lock:
            self.call_count += 1
            self.calls_since_slice += 1
            self.last_call_at = time.time()
            self.last_activity_source = "tool_call"
            sliced = False
            ticket_grants = 0

            if self.call_count % 100 == 0:
                self.tickets += TICKETS_PER_100_CALLS
                ticket_grants += TICKETS_PER_100_CALLS

            if force_slice or self.calls_since_slice >= self.slice_interval:
                self.calls_since_slice = 0
                self.slices_today += 1
                sliced = True
                if self.slices_today % 10 == 0:
                    self.tickets += TICKETS_PER_10_SLICES
                    ticket_grants += TICKETS_PER_10_SLICES

            if ticket_grants:
                save_data = self._persisted_dict()

            result = {
                "call_count": self.call_count,
                "calls_since_slice": self.calls_since_slice,
                "slices_today": self.slices_today,
                "sliced": sliced,
                "ticket_grants": ticket_grants,
                "tickets": self.tickets,
            }

        if save_data is not None:
            self._save_data(save_data)
        return result

    def note_activity(self, source: str = "activity") -> dict:
        """Mark recent local activity without granting milestone tickets.

        `chibi-say` and desktop-window actions are not always MCP tool calls,
        but they still mean the user is actively working. Recording the recency
        keeps the mood model honest without inflating gacha/ticket counters.
        """
        source = str(source or "activity").strip()[:32] or "activity"
        now = time.time()
        with self._lock:
            self.last_call_at = now
            self.last_activity_source = source
            return {
                "last_call_at": self.last_call_at,
                "last_activity_source": self.last_activity_source,
            }

    # ── Gacha ────────────────────────────────────────────────────────────────

    def pull_gacha(self, characters: list[dict]) -> dict:
        """Weighted pull from given catalog list. Mutates inventory & saves.

        Returns:
            { "drawn": {id, name_ko, rarity}, "was_free": bool, "tickets": N, "owned_count": M }
            or { "drawn": None, "reason": "..." } if no tickets and no free pull
        """
        if not characters:
            return {"drawn": None, "reason": "empty catalog"}

        today = datetime.now().date().isoformat()

        with self._lock:
            had_free = self.last_free_pull_date != today
            if not had_free and self.tickets < 1:
                return {
                    "drawn": None,
                    "reason": "no free pull today, no tickets",
                    "tickets": self.tickets,
                    "next_free_in_seconds": _seconds_until_midnight(),
                }

            # Build weighted pool — weight = RARITY_WEIGHTS[rarity] / N_in_bucket
            buckets: dict[int, list[dict]] = {}
            for c in characters:
                buckets.setdefault(int(c.get("rarity", 2)), []).append(c)

            # Pick rarity by weight, but only from rarities that have entries
            available_rarities = [r for r in (5, 4, 3, 2) if r in buckets]
            weights = [RARITY_WEIGHTS.get(r, 0) for r in available_rarities]
            picked_rarity = random.choices(available_rarities, weights=weights, k=1)[0]
            pick = random.choice(buckets[picked_rarity])

            # Spend ticket / mark free pull
            if had_free:
                self.last_free_pull_date = today
                was_free = True
            else:
                self.tickets -= 1
                was_free = False

            self.total_pulls += 1

            # Update inventory
            inv = self.inventory.setdefault(
                pick["id"],
                {
                    "count": 0,
                    "nickname": pick.get("name_ko") or pick["id"],
                    "first_rolled_at": datetime.now().isoformat(),
                },
            )
            inv["count"] = int(inv.get("count", 0)) + 1

            previous_active = self.active_character_id
            self.active_character_id = pick["id"]

            drawn = {
                "id": pick["id"],
                "name_ko": pick.get("name_ko"),
                "rarity": pick.get("rarity"),
                "category": pick.get("category"),
            }
            self.last_pull = {
                "drawn": drawn,
                "was_free": was_free,
                "tickets": self.tickets,
                "owned_count": inv["count"],
                "active_character_id": self.active_character_id,
                "previous_active_character_id": previous_active,
                "total_pulls": self.total_pulls,
                "pulled_at": datetime.now().isoformat(),
            }

            save_data = self._persisted_dict()
            result = {
                "drawn": drawn,
                "was_free": was_free,
                "tickets": self.tickets,
                "owned_count": inv["count"],
                "active_character_id": self.active_character_id,
                "previous_active_character_id": previous_active,
                "total_pulls": self.total_pulls,
                "last_pull": self.last_pull,
            }

        self._save_data(save_data)
        return result

    def set_active(self, character_id: str) -> dict:
        with self._lock:
            if character_id not in self.inventory:
                return {"ok": False, "reason": f"you don't own {character_id!r}"}
            self.active_character_id = character_id
            save_data = self._persisted_dict()
            result = {"ok": True, "active_character_id": character_id}
        self._save_data(save_data)
        return result

    def set_active_options(self, option_ids: list[str], available_ids: set[str]) -> dict:
        cleaned: list[str] = []
        for option_id in option_ids:
            option_id = str(option_id).strip()
            if not option_id:
                continue
            if option_id not in available_ids:
                return {"ok": False, "reason": f"unknown option: {option_id!r}"}
            if option_id not in cleaned:
                cleaned.append(option_id)
        if len(cleaned) > 3:
            return {"ok": False, "reason": "choose at most 3 active options"}
        with self._lock:
            self.active_option_ids = cleaned
            save_data = self._persisted_dict()
            result = {"ok": True, "active_option_ids": list(self.active_option_ids)}
        self._save_data(save_data)
        return result

    def rename(self, character_id: str, nickname: str) -> dict:
        with self._lock:
            if character_id not in self.inventory:
                return {"ok": False, "reason": f"you don't own {character_id!r}"}
            self.inventory[character_id]["nickname"] = nickname[:40]
            save_data = self._persisted_dict()
            result = {
                "ok": True,
                "character_id": character_id,
                "nickname": self.inventory[character_id]["nickname"],
            }
        self._save_data(save_data)
        return result

    def grant_tickets(self, n: int) -> dict:
        with self._lock:
            self.tickets += int(n)
            save_data = self._persisted_dict()
            result = {"tickets": self.tickets}
        self._save_data(save_data)
        return result

    # ── Mood derivation ──────────────────────────────────────────────────────

    def compute_mood(self, snap: SystemSnapshot) -> Mood:
        now = time.time()
        with self._lock:
            last_call = self.last_call_at
            last_cpu = self.last_cpu
            self.last_cpu = snap.cpu_percent

        if (
            snap.battery_percent is not None
            and snap.battery_percent < 20
            and snap.battery_plugged is False
        ):
            return Mood.DROWSY
        if snap.cpu_percent - last_cpu >= SURPRISE_DELTA and snap.cpu_percent > 50:
            return Mood.SURPRISED
        if snap.cpu_percent >= 80:
            return Mood.PANTING
        if last_call is not None and (now - last_call) <= HAPPY_WINDOW_SECONDS:
            return Mood.HAPPY
        if last_call is None:
            session_age = now - self.started_at
            if session_age > LONELY_IDLE_SECONDS:
                return Mood.LONELY
        elif (now - last_call) > LONELY_IDLE_SECONDS:
            return Mood.LONELY
        return Mood.CALM

    # ── Public snapshot ──────────────────────────────────────────────────────

    def snapshot(self) -> dict:
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
                    "last_activity_source": self.last_activity_source,
                },
                "gacha": {
                    "active_character_id": self.active_character_id,
                    "active_option_ids": list(self.active_option_ids),
                    "tickets": self.tickets,
                    "total_pulls": self.total_pulls,
                    "owned_count": len(self.inventory),
                    "last_free_pull_date": self.last_free_pull_date,
                    "last_pull": self.last_pull,
                },
            }


def _seconds_until_midnight() -> int:
    now = datetime.now()
    seconds_today = now.hour * 3600 + now.minute * 60 + now.second
    return max(0, 86400 - seconds_today)


def _clean_option_ids(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for value in raw:
        option_id = str(value).strip()
        if option_id and option_id not in cleaned:
            cleaned.append(option_id)
    return cleaned[:3]


# Module-level singleton + init lock (avoids TOCTOU when two threads
# request state simultaneously during cold start).
_STATE: ChibiState | None = None
_STATE_INIT_LOCK = Lock()

# Serializes file writes from _save_data so concurrent persistence calls
# can't lose snapshots via overlapping write+rename.
_SAVE_LOCK = Lock()


def get_state() -> ChibiState:
    global _STATE
    if _STATE is None:
        with _STATE_INIT_LOCK:
            if _STATE is None:
                inst = ChibiState()
                inst.load()
                _STATE = inst
    return _STATE


def reset_state_for_tests() -> None:
    global _STATE
    with _STATE_INIT_LOCK:
        _STATE = None
