//! IPC commands exposed to the frontend layer.

#[tauri::command]
pub fn ping() -> String {
    "pong".to_string()
}
