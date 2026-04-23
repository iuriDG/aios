const ALLOWED_ACTIONS: &[&str] = &[
    "renice",
    "cgroup_cpu_limit",
    "cgroup_ram_limit",
    "kill",
    "systemctl",
    "cpuset_assign",
    "tc_priority",
    "set_governor",
];

pub fn is_allowed(action: &str) -> bool {
    ALLOWED_ACTIONS.contains(&action)
}