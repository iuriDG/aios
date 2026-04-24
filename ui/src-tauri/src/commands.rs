use rusqlite::{Connection, Result as SqlResult};
use serde::{Deserialize, Serialize};
use std::fs;

const DB_PATH: &str = "/opt/aios-agent/profiles/aios.db";
const AUDIT_LOG: &str = "/var/log/aios/audit.log";
const OBSERVER_LOG: &str = "/var/log/aios/observer.log";

#[derive(Serialize, Deserialize)]
pub struct SystemState {
    pub mode: String,
    pub gear: String,
    pub cpu_pct: f64,
    pub ram_pct: f64,
    pub gpu_pct: f64,
    pub available_ram_gb: f64,
    pub processes: Vec<ProcessInfo>,
    pub dry_run: bool,
    pub ollama_available: bool,
}

#[derive(Serialize, Deserialize)]
pub struct ProcessInfo {
    pub pid: i64,
    pub name: String,
    pub cpu_pct: f64,
    pub ram_mb: f64,
}

#[derive(Serialize, Deserialize)]
pub struct AppProfile {
    pub binary_name: String,
    pub mode: String,
    pub cpu_avg: f64,
    pub ram_avg_mb: f64,
    pub gpu_avg: f64,
    pub session_count: i64,
    pub user_override: bool,
}

#[derive(Serialize, Deserialize)]
pub struct AuditEntry {
    pub timestamp: String,
    pub action: String,
    pub target: String,
    pub mode: String,
    pub gear: String,
    pub result: String,
}

#[derive(Serialize, Deserialize)]
pub struct UserPref {
    pub key: String,
    pub value: String,
}

fn open_db() -> SqlResult<Connection> {
    Connection::open(DB_PATH)
}

fn get_pref(key: &str) -> Option<String> {
    let conn = open_db().ok()?;
    conn.query_row(
        "SELECT value FROM user_profile WHERE key = ?1",
        [key],
        |row| row.get(0),
    ).ok()
}

#[tauri::command]
pub fn get_system_state() -> SystemState {
    let mode = get_pref("last_mode").unwrap_or("unknown".into());
    let gear = get_pref("last_gear").unwrap_or("unknown".into());
    let dry_run = get_pref("dry_run").map(|v| v == "True").unwrap_or(true);

    let mut cpu_pct = 0.0;
    let mut ram_pct = 0.0;
    let mut gpu_pct = 0.0;
    let mut available_ram_gb = 0.0;
    let mut processes = vec![];

    if let Ok(content) = fs::read_to_string(OBSERVER_LOG) {
        if let Some(last_line) = content.lines().last() {
            if let Some(json_start) = last_line.find('{') {
                let json = &last_line[json_start..];
                if let Ok(v) = serde_json::from_str::<serde_json::Value>(json) {
                    cpu_pct = v["cpu"]["percent_total"].as_f64().unwrap_or(0.0);
                    ram_pct = v["ram"]["used_pct"].as_f64().unwrap_or(0.0);
                    gpu_pct = v["gpu"]["utilisation_pct"].as_f64().unwrap_or(0.0);
                    available_ram_gb = v["ram"]["available_gb"].as_f64().unwrap_or(0.0);
                    if let Some(procs) = v["processes"].as_array() {
                        processes = procs.iter().take(10).map(|p| ProcessInfo {
                            pid: p["pid"].as_i64().unwrap_or(0),
                            name: p["name"].as_str().unwrap_or("").to_string(),
                            cpu_pct: p["cpu_pct"].as_f64().unwrap_or(0.0),
                            ram_mb: p["ram_mb"].as_f64().unwrap_or(0.0),
                        }).collect();
                    }
                }
            }
        }
    }

    SystemState {
        mode, gear, cpu_pct, ram_pct, gpu_pct,
        available_ram_gb, processes, dry_run,
        ollama_available: false,
    }
}

#[tauri::command]
pub fn get_app_profiles() -> Vec<AppProfile> {
    let conn = match open_db() {
        Ok(c) => c,
        Err(_) => return vec![],
    };
    let mut stmt = match conn.prepare(
        "SELECT binary_name, mode, cpu_avg, ram_avg_mb, gpu_avg,
         session_count, user_override FROM app_profiles
         ORDER BY session_count DESC"
    ) {
        Ok(s) => s,
        Err(_) => return vec![],
    };
    stmt.query_map([], |row| {
        Ok(AppProfile {
            binary_name: row.get(0)?,
            mode: row.get(1)?,
            cpu_avg: row.get(2).unwrap_or(0.0),
            ram_avg_mb: row.get(3).unwrap_or(0.0),
            gpu_avg: row.get(4).unwrap_or(0.0),
            session_count: row.get(5).unwrap_or(0),
            user_override: row.get::<_, i64>(6).unwrap_or(0) == 1,
        })
    })
    .map(|rows| rows.filter_map(|r| r.ok()).collect())
    .unwrap_or_default()
}

#[tauri::command]
pub fn get_audit_log(limit: usize) -> Vec<AuditEntry> {
    let content = match fs::read_to_string(AUDIT_LOG) {
        Ok(c) => c,
        Err(_) => return vec![],
    };
    content.lines().rev().take(limit)
        .filter_map(|line| {
            serde_json::from_str::<serde_json::Value>(line).ok().map(|v| AuditEntry {
                timestamp: v["timestamp"].as_str().unwrap_or("").to_string(),
                action: v["action"].as_str().unwrap_or("").to_string(),
                target: v["target"].as_str().unwrap_or("").to_string(),
                mode: v["mode"].as_str().unwrap_or("").to_string(),
                gear: v["gear"].as_str().unwrap_or("").to_string(),
                result: v["result"].as_str().unwrap_or("").to_string(),
            })
        })
        .collect()
}

#[tauri::command]
pub fn get_prefs() -> Vec<UserPref> {
    let conn = match open_db() {
        Ok(c) => c,
        Err(_) => return vec![],
    };
    let mut stmt = match conn.prepare(
        "SELECT key, value FROM user_profile ORDER BY key"
    ) {
        Ok(s) => s,
        Err(_) => return vec![],
    };
    stmt.query_map([], |row| {
        Ok(UserPref { key: row.get(0)?, value: row.get(1)? })
    })
    .map(|rows| rows.filter_map(|r| r.ok()).collect())
    .unwrap_or_default()
}

#[tauri::command]
pub fn set_pref(key: String, value: String) -> bool {
    let conn = match open_db() {
        Ok(c) => c,
        Err(_) => return false,
    };
    conn.execute(
        "INSERT INTO user_profile (key, value) VALUES (?1, ?2)
         ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        [&key, &value],
    ).is_ok()
}
