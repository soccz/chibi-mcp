//! chibi-mcp desktop — tteoki window runtime.
//!
//! For v0.1, the Rust side is a thin Tauri shell. All character logic lives in
//! the frontend (`src/`), which talks to the MCP server's WebSocket on
//! `ws://127.0.0.1:9876` for state. The window itself is configured in
//! `tauri.conf.json` (transparent, frameless, always-on-top, click-through-aware).

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            // Drag-by-anywhere: the pet window has no titlebar, so we rely on
            // the frontend to call window.startDragging() on mousedown.
            if let Some(win) = app.get_webview_window("pet") {
                // Make sure the pet stays above other windows.
                let _ = win.set_always_on_top(true);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running chibi-mcp tauri application");
}
