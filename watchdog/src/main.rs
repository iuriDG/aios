use std::process::Command;
use std::time::Duration;
use std::thread;
use std::fs;
use std::collections::HashMap;

const AGENT_BINARY: &str = "/usr/local/bin/aios-agent";
const HELPER_BINARY: &str = "/usr/local/bin/aios-helper";
const READY_FILE: &str = "/run/aios/ready";
const TAMPER_LOG: &str = "/var/log/aios/tamper.log";
const CHECK_INTERVAL_SECS: u64 = 5;

fn main() {
    fs::create_dir_all("/run/aios").expect("Failed to create /run/aios");
    fs::create_dir_all("/var/log/aios").expect("Failed to create /var/log/aios");

    println!("aios-watchdog started");

    // Store binary hashes at startup
    let mut known_hashes: HashMap<&str, String> = HashMap::new();
    known_hashes.insert(AGENT_BINARY, hash_file(AGENT_BINARY));
    known_hashes.insert(HELPER_BINARY, hash_file(HELPER_BINARY));

    loop {
        // Check for binary tampering
        for (path, known_hash) in &known_hashes {
            let current_hash = hash_file(path);
            if current_hash != *known_hash && !known_hash.is_empty() {
                handle_tamper(path);
                return; // Hard stop - require manual restart
            }
        }

        // Check agent is running
        if !is_process_running("aios-agent") {
            println!("[WATCHDOG] Agent not running - restoring defaults and restarting");
            restore_defaults();
            restart_process("aios-agent");
        }

        // Check helper is running
        if !is_process_running("aios-helper") {
            println!("[WATCHDOG] Helper not running - restoring defaults");
            restore_defaults();
            // Helper requires manual restart - security boundary
            send_notification("AIOS helper stopped unexpectedly - manual restart required");
            log_tamper("helper process died unexpectedly");
        }

        thread::sleep(Duration::from_secs(CHECK_INTERVAL_SECS));
    }
}

fn hash_file(path: &str) -> String {
    match fs::read(path) {
        Ok(bytes) => {
            // Simple checksum - replace with SHA256 in hardening phase
            let sum: u64 = bytes.iter().map(|&b| b as u64).sum();
            format!("{:x}", sum)
        }
        Err(_) => String::new()
    }
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
    println!("[WATCHDOG] Restoring system defaults");

    // Reset CPU governor to balanced
    if let Ok(entries) = fs::read_dir("/sys/devices/system/cpu") {
        for entry in entries.flatten() {
            let gov_path = entry.path()
                .join("cpufreq/scaling_governor");
            let _ = fs::write(&gov_path, "balanced");
        }
    }

    // Remove aios cgroups
    let _ = Command::new("cgdelete")
        .args(["-r", "cpu:aios"])
        .output();

    // Reset all process nice values managed by aios
    // Read pids from audit log and renice back to 0
    if let Ok(log) = fs::read_to_string("/var/log/aios/audit.log") {
        for line in log.lines() {
            if let Ok(entry) = serde_json::from_str::<serde_json::Value>(line) {
                if entry["action"] == "renice" {
                    if let Some(pid) = entry["target"].as_str() {
                        let _ = Command::new("renice")
                            .args(["0", "-p", pid])
                            .output();
                    }
                }
            }
        }
    }

    // Remove ready file so nothing launches until agent is back
    let _ = fs::remove_file(READY_FILE);

    println!("[WATCHDOG] Defaults restored");
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
    send_notification(&msg);
    restore_defaults();

    // Remove socket so helper cannot be contacted
    let _ = fs::remove_file("/run/aios/helper.sock");

    println!("[WATCHDOG] System locked - manual restart required");
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
    // Simple timestamp without pulling in chrono crate
    let output = Command::new("date")
        .arg("+%Y-%m-%dT%H:%M:%S")
        .output()
        .unwrap_or_else(|_| std::process::Output {
            status: std::process::ExitStatus::from_raw(0),
            stdout: vec![],
            stderr: vec![]
        });
    String::from_utf8_lossy(&output.stdout).trim().to_string()
}