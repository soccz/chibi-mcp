//! chibi-mcp desktop — tteoki window runtime (v0.2).

#![allow(clippy::collapsible_if, clippy::needless_borrows_for_generic_args, clippy::let_underscore_must_use)]

use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    Manager,
};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if let Some(win) = app.get_webview_window("pet") {
                let _ = win.set_always_on_top(true);
            }
            build_tray(&app.handle())?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running chibi-mcp tauri application");
}

fn build_tray(app: &tauri::AppHandle) -> tauri::Result<()> {
    let show = MenuItem::with_id(app, "show", "tteoki 보기", true, None::<&str>)?;
    let hide = MenuItem::with_id(app, "hide", "숨기기", true, None::<&str>)?;
    let collection = MenuItem::with_id(app, "collection", "보관함", true, None::<&str>)?;
    let gacha = MenuItem::with_id(app, "gacha", "뽑기", true, None::<&str>)?;
    let about = MenuItem::with_id(app, "about", "chibi-mcp v0.2", false, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let quit = MenuItem::with_id(app, "quit", "종료", true, None::<&str>)?;

    let menu = Menu::with_items(
        app,
        &[
            &show,
            &hide,
            &separator,
            &collection,
            &gacha,
            &separator,
            &about,
            &quit,
        ],
    )?;

    let _ = TrayIconBuilder::with_id("tteoki-tray")
        .tooltip("tteoki")
        .menu(&menu)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show" => {
                if let Some(w) = app.get_webview_window("pet") {
                    let _ = w.show();
                    let _ = w.set_focus();
                }
            }
            "hide" => {
                if let Some(w) = app.get_webview_window("pet") {
                    let _ = w.hide();
                }
            }
            "collection" => {
                if let Some(w) = app.get_webview_window("pet") {
                    let _ = w.show();
                    let _ = w.eval("window.dispatchEvent(new CustomEvent('tray:collection'));");
                }
            }
            "gacha" => {
                if let Some(w) = app.get_webview_window("pet") {
                    let _ = w.show();
                    let _ = w.eval("window.dispatchEvent(new CustomEvent('tray:gacha'));");
                }
            }
            "quit" => app.exit(0),
            _ => {}
        })
        .build(app)?;

    Ok(())
}
