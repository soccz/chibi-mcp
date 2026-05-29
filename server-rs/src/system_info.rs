//! Thin sysinfo wrapper — CPU/RAM/battery snapshot for chibi.

use serde::Serialize;
use sysinfo::System;

#[derive(Debug, Clone, Serialize)]
pub struct SystemSnapshot {
    pub cpu_percent: f32,
    pub ram_percent: f32,
    pub battery_percent: Option<f32>,
    pub battery_plugged: Option<bool>,
}

pub struct SystemReader {
    sys: System,
}

impl Default for SystemReader {
    fn default() -> Self {
        let mut sys = System::new();
        sys.refresh_cpu_all();
        sys.refresh_memory();
        Self { sys }
    }
}

impl SystemReader {
    pub fn read(&mut self) -> SystemSnapshot {
        self.sys.refresh_cpu_all();
        self.sys.refresh_memory();

        let cpu_percent = self.sys.global_cpu_usage();
        let total = self.sys.total_memory();
        let used = self.sys.used_memory();
        let ram_percent = if total > 0 {
            (used as f64 / total as f64) as f32 * 100.0
        } else {
            0.0
        };

        // Battery: best-effort via the `battery` crate would add a heavy
        // dep. For v0.2 alpha we leave battery as None on non-laptop hosts.
        // (sysinfo 0.32 doesn't expose battery directly.)
        SystemSnapshot {
            cpu_percent: round1(cpu_percent),
            ram_percent: round1(ram_percent),
            battery_percent: None,
            battery_plugged: None,
        }
    }
}

fn round1(v: f32) -> f32 {
    (v * 10.0).round() / 10.0
}
