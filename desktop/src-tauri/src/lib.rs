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
    use cocoa::appkit::NSColor;
    use cocoa::appkit::NSWindow;
    use cocoa::base::{id, nil};

    // 1. Make NSWindow itself transparent
    if let Ok(ns_win) = win.ns_window() {
        let ns_win = ns_win as id;
        unsafe {
            NSWindow::setBackgroundColor_(ns_win, NSColor::clearColor(nil));
            let _: () = msg_send![ns_win, setOpaque: false];
            let _: () = msg_send![ns_win, setHasShadow: false];
        }
    }

    // 2. Make WKWebView transparent (the actual rendering surface)
    //    Without this, the webview draws its own white/opaque background
    //    even though the window above it is clear.
    if let Ok(ns_view) = win.ns_view() {
        let ns_view = ns_view as id;
        unsafe {
            // WKWebView._setDrawsBackground = NO
            let _: () = msg_send![ns_view, setValue:cocoa::base::NO forKey:"drawsBackground"];

            // Also try the subview (Tauri nests: NSView > WKWebView)
            let subviews: id = msg_send![ns_view, subviews];
            let count: usize = msg_send![subviews, count];
            for i in 0..count {
                let child: id = msg_send![subviews, objectAtIndex: i];
                let _: () = msg_send![child, setValue:cocoa::base::NO forKey:"drawsBackground"];
            }
        }
    }
}

#[cfg(target_os = "macos")]
#[macro_use]
extern crate objc;
