use std::process::Command;
use std::time::Duration;
use std::thread;
use std::fs;
use std::collections::HashMap;
use sha2::{Sha256, Digest};

const AGENT_BINARY: &str = "/opt/aios-agent/main.py";
const HELPER_BINARY: &str = "/usr/local/bin/aios-helper";
const READY_FILE: &str = "/run/aios/ready";
const TAMPER_LOG: &str = "/var/log/aios/tamper.log";
const CHECK_INTERVAL_SECS: u64 = 5;

fn main() {
    fs::create_dir_all("/run/aios").expect("Failed to create /run/aios");
    fs::create_dir_all("/var/log/aios").expect("Failed to create /var/log/aios");

    eprintln!("aios-watchdog started");

    // Hash binaries at startup - abort if either is unreadable
    let mut known_hashes: HashMap<&str, String> = HashMap::new();
    for path in &[AGENT_BINARY, HELPER_BINARY] {
        match hash_file(path) {
            Some(h) => { known_hashes.insert(path, h); }
            None => {
                eprintln!("[WATCHDOG] Cannot hash {} at startup - aborting", path);
                std::process::exit(1);
            }
        }
    }

    loop {
        // Check for binary tampering
        for (path, known_hash) in &known_hashes {
            match hash_file(path) {
                Some(current_hash) if current_hash != *known_hash => {
                    handle_tamper(path);
                    return;
                }
                None => {
                    // Binary became unreadable - treat as tamper
                    handle_tamper(path);
                    return;
                }
                _ => {}
            }
        }

        // Check agent is running
        if !is_process_running("aios-agent") {
            eprintln!("[WATCHDOG] Agent not running - restoring defaults and restarting");
            restore_defaults();
            restart_process("aios-agent");
        }

        // Check helper is running
        if !is_process_running("aios-helper") {
            eprintln!("[WATCHDOG] Helper not running - restoring defaults");
            restore_defaults();
            send_notification("AIOS helper stopped unexpectedly - manual restart required");
            log_tamper("helper process died unexpectedly");
        }

        thread::sleep(Duration::from_secs(CHECK_INTERVAL_SECS));
    }
}

fn hash_file(path: &str) -> Option<String> {
    let bytes = fs::read(path).ok()?;
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    Some(hex::encode(hasher.finalize()))
}

fn is_process_running(name: &str) -> bool {
    let output = Command::new("pgrep")
        .arg("-x")
        .arg(name)
        .output();

    match output {
        Ok(o) => !o.stdout.is_empty(),
        Err(_) => false
    }
}

fn restore_defaults() {
    eprintln!("[WATCHDOG] Restoring system defaults");

    // Reset CPU governor to balanced
    if let Ok(entries) = fs::read_dir("/sys/devices/system/cpu") {
        for entry in entries.flatten() {
            let gov_path = entry.path().join("cpufreq/scaling_governor");
            if gov_path.exists() {
                let _ = fs::write(&gov_path, "balanced");
            }
        }
    }

    // Remove aios cgroups
    let _ = Command::new("cgdelete")
        .args(["-r", "cpu:aios"])
        .output();

    // Renice PIDs that aios managed back to 0
    // Only read the last 500 lines to bound recovery time on large logs
    if let Ok(log) = fs::read_to_string("/var/log/aios/audit.log") {
        for line in log.lines().rev().take(500) {
            if let Ok(entry) = serde_json::from_str::<serde_json::Value>(line) {
                if entry["action"] == "renice" {
                    if let Some(pid) = entry["target"].as_str() {
                        // Validate PID is numeric before passing to renice
                        if pid.chars().all(|c| c.is_ascii_digit()) && !pid.is_empty() {
                            let _ = Command::new("renice")
                                .args(["0", "-p", pid])
                                .output();
                        }
                    }
                }
            }
        }
    }

    let _ = fs::remove_file(READY_FILE);

    eprintln!("[WATCHDOG] Defaults restored");
}

fn restart_process(name: &str) {
    let _ = Command::new("systemctl")
        .args(["restart", &format!("aios-{}.service", name)])
        .output();
}

fn handle_tamper(path: &str) {
    let msg = format!("TAMPER DETECTED: {} hash mismatch", path);
    eprintln!("[WATCHDOG] {}", msg);
    log_tamper(&msg);

    restore_defaults();
    let _ = fs::remove_file("/run/aios/helper.sock");

    send_notification(&msg);

    // Call panic script directly - no shell involved
    Command::new("/usr/local/bin/aios-panic.sh")
        .arg(format!("Tamper detected on {}", path))
        .output()
        .ok();

    eprintln!("[WATCHDOG] System locked - manual restart required");
}

fn log_tamper(message: &str) {
    use std::io::Write;
    if let Ok(mut f) = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(TAMPER_LOG)
    {
        let _ = writeln!(f, "{} {}", chrono_now(), message);
    }
}

fn send_notification(message: &str) {
    let _ = Command::new("notify-send")
        .args(["AIOS Security Alert", message, "--urgency=critical"])
        .output();
}

fn chrono_now() -> String {
    Command::new("date")
        .arg("+%Y-%m-%dT%H:%M:%S")
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .unwrap_or_else(|_| String::from("unknown"))
}
