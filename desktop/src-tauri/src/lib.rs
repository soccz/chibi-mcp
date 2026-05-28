//! chibi-mcp desktop — tteoki window runtime (v0.2 lineage).
//!
//! v0.1.6 tried to call cocoa NSView APIs to force WKWebView transparency,
//! which segfaults on macOS 12. v0.2 keeps the Rust shell minimal — the
//! window is configured via `tauri.conf.json` (transparent, frameless,
//! always-on-top) and the frontend handles everything else.

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if let Some(win) = app.get_webview_window("pet") {
                let _ = win.set_always_on_top(true);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running chibi-mcp tauri application");
}
