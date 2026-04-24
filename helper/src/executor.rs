use serde_json::Value;
use std::process::Command;

pub fn execute(request: &Value) -> Result<String, Box<dyn std::error::Error>> {
    let action = request["action"].as_str().unwrap_or("");

    match action {
        "renice" => {
            let pid = request["pid"].as_i64().ok_or("missing pid")?;
            let priority = request["priority"].as_i64().ok_or("missing priority")?;
            Command::new("renice")
                .args([&priority.to_string(), "-p", &pid.to_string()])
                .output()?;
            Ok(format!("reniced {} to {}", pid, priority))
        }

        "kill" => {
            let pid = request["pid"].as_i64().ok_or("missing pid")?;
            let signal = request["signal"].as_i64().unwrap_or(15);
            // Whitelist: SIGTERM=15, SIGKILL=9, SIGSTOP=19, SIGCONT=18
            if ![9i64, 15, 18, 19].contains(&signal) {
                return Err(format!("signal {} not allowed", signal).into());
            }
            Command::new("kill")
                .args([&format!("-{}", signal), &pid.to_string()])
                .output()?;
            Ok(format!("sent signal {} to {}", signal, pid))
        }

        "systemctl" => {
            let cmd = request["command"].as_str().ok_or("missing command")?;
            let unit = request["unit"].as_str().ok_or("missing unit")?;
            if !["start", "stop", "restart", "reload"].contains(&cmd) {
                return Err("unsafe systemctl command".into());
            }
            Command::new("systemctl")
                .args([cmd, unit])
                .output()?;
            Ok(format!("systemctl {} {}", cmd, unit))
        }

        "set_governor" => {
            let governor = request["governor"].as_str().ok_or("missing governor")?;
            if !["performance", "balanced", "powersave"].contains(&governor) {
                return Err("invalid governor".into());
            }

            let mut errors: Vec<String> = Vec::new();

            for i in 0..num_cpus() {
                let path = format!(
                    "/sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor", i
                );
                if let Err(e) = std::fs::write(&path, governor) {
                    errors.push(format!("cpu{}: {}", i, e));
                }
            }

            let amd_gpu_path = "/sys/class/drm/card0/device/power_dpm_force_performance_level";
            if std::path::Path::new(amd_gpu_path).exists() {
                let amd_level = match governor {
                    "performance" => "high",
                    "balanced"    => "auto",
                    "powersave"   => "low",
                    _             => "auto"
                };
                if let Err(e) = std::fs::write(amd_gpu_path, amd_level) {
                    errors.push(format!("amd_gpu: {}", e));
                }
            }

            if errors.is_empty() {
                Ok(format!("governor set to {}", governor))
            } else {
                Err(format!("governor partially applied, errors: {}", errors.join("; ")).into())
            }
        }

        "cgroup_cpu_limit" => {
            let pid = request["pid"].as_i64().ok_or("missing pid")?;
            let quota = request["quota"].as_i64().ok_or("missing quota")?;
            if !(1..=100).contains(&quota) {
                return Err(format!("quota {} out of range (1-100)", quota).into());
            }
            let path = format!("/sys/fs/cgroup/aios/{}/cpu.max", pid);
            std::fs::create_dir_all(format!("/sys/fs/cgroup/aios/{}", pid))?;
            std::fs::write(&path, format!("{} 100000", quota * 1000))?;
            Ok(format!("cpu limit {}% set for pid {}", quota, pid))
        }

        "cgroup_ram_limit" => {
            let pid = request["pid"].as_i64().ok_or("missing pid")?;
            let bytes = request["bytes"].as_i64().ok_or("missing bytes")?;
            let path = format!("/sys/fs/cgroup/aios/{}", pid);
            std::fs::create_dir_all(&path)?;
            std::fs::write(format!("{}/memory.max", path), bytes.to_string())?;
            Ok(format!("ram limit {}MB set for pid {}", bytes / 1_000_000, pid))
        }

        "cpuset_assign" => {
            let pid = request["pid"].as_i64().ok_or("missing pid")?;
            let cores = request["cores"].as_str().ok_or("missing cores")?;
            // Validate cores is a simple CPU range like "0", "0-3", "0,2"
            if !cores.chars().all(|c| c.is_ascii_digit() || c == '-' || c == ',') {
                return Err(format!("invalid cores format: {}", cores).into());
            }
            let path = format!("/sys/fs/cgroup/aios/{}", pid);
            std::fs::create_dir_all(&path)?;
            std::fs::write(format!("{}/cpuset.cpus", path), cores)?;
            std::fs::write(format!("{}/cgroup.procs", path), pid.to_string())?;
            Ok(format!("pid {} assigned to cores {}", pid, cores))
        }

        "tc_priority" => {
            let interface = request["interface"].as_str().ok_or("missing interface")?;
            let class = request["class"].as_str().ok_or("missing class")?;
            // Validate interface name: alphanumeric + dash/colon only
            if !interface.chars().all(|c| c.is_alphanumeric() || c == '-' || c == ':') {
                return Err(format!("invalid interface name: {}", interface).into());
            }
            // Validate class is a valid HTB classid like "1:10"
            if !class.chars().all(|c| c.is_ascii_digit() || c == ':') {
                return Err(format!("invalid class id: {}", class).into());
            }
            Command::new("tc")
                .args(["class", "add", "dev", interface,
                    "parent", "1:", "classid", class,
                    "htb", "rate", "100mbit", "prio", "1"])
                .output()?;
            Ok(format!("tc priority set on {} class {}", interface, class))
        }

        _ => Err(format!("unknown action: {}", action).into())
    }
}

fn num_cpus() -> usize {
    std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(1)
}
