//! In-memory tteoki state — mood derivation + slice counter.
//!
//! Mirrors the v0.1 Python implementation so the desktop frontend protocol
//! stays unchanged.

use std::time::Instant;

use parking_lot::Mutex;
use serde::Serialize;
use serde_json::{Value, json};

use crate::system_info::SystemSnapshot;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Mood {
    Calm,
    Panting,
    Drowsy,
    Lonely,
    Happy,
    Surprised,
    Joyful,
}

impl Mood {
    pub fn as_str(self) -> &'static str {
        match self {
            Mood::Calm => "calm",
            Mood::Panting => "panting",
            Mood::Drowsy => "drowsy",
            Mood::Lonely => "lonely",
            Mood::Happy => "happy",
            Mood::Surprised => "surprised",
            Mood::Joyful => "joyful",
        }
    }
}

pub const DEFAULT_SLICE_INTERVAL: u32 = 10;
const LONELY_IDLE_SECS: u64 = 30 * 60;
const HAPPY_WINDOW_SECS: u64 = 30;
const SURPRISE_DELTA: f32 = 30.0;

pub struct Tteoki {
    inner: Mutex<Inner>,
}

struct Inner {
    slice_interval: u32,
    call_count: u32,
    calls_since_slice: u32,
    slices_today: u32,
    started_at: Instant,
    last_call_at: Option<Instant>,
    last_cpu: f32,
}

impl Tteoki {
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(Inner {
                slice_interval: DEFAULT_SLICE_INTERVAL,
                call_count: 0,
                calls_since_slice: 0,
                slices_today: 0,
                started_at: Instant::now(),
                last_call_at: None,
                last_cpu: 0.0,
            }),
        }
    }

    /// Increment counters; return `true` if the slice milestone fired.
    pub fn record_call(&self, force_slice: bool) -> CallResult {
        let mut s = self.inner.lock();
        s.call_count += 1;
        s.calls_since_slice += 1;
        s.last_call_at = Some(Instant::now());
        let sliced = force_slice || s.calls_since_slice >= s.slice_interval;
        if sliced {
            s.calls_since_slice = 0;
            s.slices_today += 1;
        }
        CallResult {
            call_count: s.call_count,
            calls_since_slice: s.calls_since_slice,
            slices_today: s.slices_today,
            sliced,
        }
    }

    pub fn compute_mood(&self, snap: &SystemSnapshot) -> Mood {
        let mut s = self.inner.lock();
        let last_call = s.last_call_at;
        let last_cpu = s.last_cpu;
        s.last_cpu = snap.cpu_percent;
        let started_at = s.started_at;
        drop(s);

        let now = Instant::now();

        if let (Some(pct), Some(plugged)) = (snap.battery_percent, snap.battery_plugged) {
            if pct < 20.0 && !plugged {
                return Mood::Drowsy;
            }
        }
        if snap.cpu_percent - last_cpu >= SURPRISE_DELTA && snap.cpu_percent > 50.0 {
            return Mood::Surprised;
        }
        if snap.cpu_percent >= 80.0 {
            return Mood::Panting;
        }
        match last_call {
            Some(t) if now.duration_since(t).as_secs() <= HAPPY_WINDOW_SECS => Mood::Happy,
            Some(t) if now.duration_since(t).as_secs() > LONELY_IDLE_SECS => Mood::Lonely,
            None if now.duration_since(started_at).as_secs() > LONELY_IDLE_SECS => Mood::Lonely,
            _ => Mood::Calm,
        }
    }

    pub fn snapshot(&self, snap: &SystemSnapshot, mood: Mood) -> Value {
        let s = self.inner.lock();
        let now = Instant::now();
        let session_secs = now.duration_since(s.started_at).as_secs();
        let idle_secs = s.last_call_at.map(|t| now.duration_since(t).as_secs());

        json!({
            "mood": mood.as_str(),
            "system": {
                "cpu_percent": snap.cpu_percent,
                "ram_percent": snap.ram_percent,
                "battery_percent": snap.battery_percent,
                "battery_plugged": snap.battery_plugged,
            },
            "counters": {
                "calls_total": s.call_count,
                "calls_since_slice": s.calls_since_slice,
                "slice_interval": s.slice_interval,
                "slices_today": s.slices_today,
            },
            "timing": {
                "session_seconds": session_secs,
                "idle_seconds": idle_secs,
            },
        })
    }

    pub fn set_slice_interval(&self, n: u32) -> (u32, u32) {
        let mut s = self.inner.lock();
        let prev = s.slice_interval;
        s.slice_interval = n.max(1);
        (prev, s.slice_interval)
    }

    pub fn slice_interval(&self) -> u32 {
        self.inner.lock().slice_interval
    }
}

pub struct CallResult {
    pub call_count: u32,
    pub calls_since_slice: u32,
    pub slices_today: u32,
    pub sliced: bool,
}
