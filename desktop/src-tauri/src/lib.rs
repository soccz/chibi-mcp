use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if let Some(win) = app.get_webview_window("pet") {
                let _ = win.set_always_on_top(true);

                #[cfg(target_os = "macos")]
                force_transparent_macos(&win);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running chibi-mcp tauri application");
}

#[cfg(target_os = "macos")]
fn force_transparent_macos(win: &tauri::WebviewWindow) {
    use cocoa::appkit::NSWindow;
    use cocoa::base::{id, nil};
    use cocoa::appkit::NSColor;

    if let Ok(ns_win) = win.ns_window() {
        let ns_win = ns_win as id;
        unsafe {
            NSWindow::setBackgroundColor_(ns_win, NSColor::clearColor(nil));
            let _: () = msg_send![ns_win, setOpaque: false];
            let _: () = msg_send![ns_win, setHasShadow: false];
        }
    }
}

#[cfg(target_os = "macos")]
#[macro_use]
extern crate objc;
