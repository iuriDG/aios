use rusqlite::{Connection, OpenFlags, Result as SqlResult};
use serde::{Deserialize, Serialize};
use sysinfo::System;

const DB_PATH: &str = "/opt/aios-agent/profiles/aios.db";
const DB_URI: &str = "file:/opt/aios-agent/profiles/aios.db?immutable=1";

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
    Connection::open_with_flags(
        DB_URI,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_URI | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )
}

fn open_db_rw() -> SqlResult<Connection> {
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
    let mode = get_pref("manual_mode")
        .filter(|m| !m.is_empty())
        .or_else(|| get_pref("last_mode"))
        .unwrap_or("unknown".into());
    let dry_run = get_pref("dry_run").map(|v| v == "True").unwrap_or(true);

    let mut sys = System::new_all();
    sys.refresh_all();

    let cpu_pct = sys.global_cpu_usage() as f64;
    let gear = if cpu_pct >= 80.0 { "heavy" } else if cpu_pct >= 50.0 { "medium" } else { "low" }.to_string();
    let ram = sys.total_memory();
    let ram_used = sys.used_memory();
    let ram_available = sys.available_memory();
    let ram_pct = if ram > 0 { ram_used as f64 / ram as f64 * 100.0 } else { 0.0 };
    let available_ram_gb = ram_available as f64 / 1_073_741_824.0;

    let mut proc_list: Vec<_> = sys.processes().values().collect();
    proc_list.sort_by(|a, b| b.cpu_usage().partial_cmp(&a.cpu_usage()).unwrap_or(std::cmp::Ordering::Equal));
    let processes = proc_list.iter().take(10).map(|p| ProcessInfo {
        pid: p.pid().as_u32() as i64,
        name: p.name().to_string_lossy().to_string(),
        cpu_pct: p.cpu_usage() as f64,
        ram_mb: p.memory() as f64 / 1_048_576.0,
    }).collect();

    SystemState {
        mode, gear, cpu_pct, ram_pct, gpu_pct: 0.0,
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
    let conn = match open_db() {
        Ok(c) => c,
        Err(_) => return vec![],
    };
    let mut stmt = match conn.prepare(
        "SELECT timestamp, action, target, mode, gear, result
         FROM audit_log ORDER BY id DESC LIMIT ?1"
    ) {
        Ok(s) => s,
        Err(_) => return vec![],
    };
    stmt.query_map([limit as i64], |row| {
        Ok(AuditEntry {
            timestamp: row.get(0)?,
            action: row.get(1)?,
            target: row.get(2)?,
            mode: row.get(3)?,
            gear: row.get(4)?,
            result: row.get(5)?,
        })
    })
    .map(|rows| rows.filter_map(|r| r.ok()).collect())
    .unwrap_or_default()
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
    let conn = match open_db_rw() {
        Ok(c) => c,
        Err(_) => return false,
    };
    conn.execute(
        "INSERT INTO user_profile (key, value) VALUES (?1, ?2)
         ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        [&key, &value],
    ).is_ok()
}
