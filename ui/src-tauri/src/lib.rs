mod commands;
use commands::{get_system_state, get_app_profiles, get_audit_log, get_prefs, set_pref};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_system_state,
            get_app_profiles,
            get_audit_log,
            get_prefs,
            set_pref,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
