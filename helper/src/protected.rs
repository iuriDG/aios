const PROTECTED_NAMES: &[&str] = &[
    "systemd", "init", "sshd", "networkmanager",
    "dbus", "aios-agent", "aios-helper", "aios-watchdog",
    "kworker", "migration", "rcu_sched"
];

pub fn is_protected(pid: i32) -> bool {
    // PID below 100 always protected
    if pid < 100 {
        return true;
    }

    // Check process name via /proc
    if let Ok(name) = std::fs::read_to_string(format!("/proc/{}/comm", pid)) {
        let name = name.trim().to_lowercase();
        return PROTECTED_NAMES.iter().any(|p| name.contains(p));
    }

    false
}