import json
from profile_store import get_app_profile, get_user_pref, log_action
from signal_combiner import resolve

# Processes the AI can never touch regardless of anything
PROTECTED = [
    "systemd", "init", "sshd", "networkmanager",
    "dbus", "kworker", "aios-agent", "aios-helper",
    "aios-watchdog", "kernel", "migration", "rcu"
]

# CPU nice levels
NICE_REALTIME   = -20
NICE_HIGH       = -10
NICE_NORMAL     =   0
NICE_LOW        =  10
NICE_BACKGROUND =  19

def deduplicate(actions: list) -> list:
    seen = set()
    result = []
    for a in actions:
        key = (a.get("action"), a.get("pid"), a.get("unit"))
        if not key in seen:
            seen.add(key)
            result.append(a)
    return result

def is_protected(process_name):
    return any(p in process_name.lower() for p in PROTECTED)

def get_gear(snapshot) -> str:
    cpu = snapshot.get("cpu", {}).get("percent_total", 0)
    ram = snapshot.get("ram", {}).get("used_pct", 0)
    gpu = snapshot.get("gpu", {}).get("utilisation_pct", 0)

    hw_cpu_weight = float(get_user_pref("hw_weight_cpu") or 1.0)
    hw_ram_weight = float(get_user_pref("hw_weight_ram") or 1.0)
    hw_gpu_weight = float(get_user_pref("hw_weight_gpu") or 1.0)

    scores = {
        "cpu": (cpu / 100) * hw_cpu_weight,
        "ram": (ram / 100) * hw_ram_weight,
        "gpu": (gpu / 100) * hw_gpu_weight,
    }

    bottleneck = max(scores.values())

    if bottleneck < 0.5:
        return "low"
    elif bottleneck < 0.8:
        return "medium"
    else:
        return "heavy"

def build_gaming_actions(snapshot, gear):
    actions = []
    processes = snapshot.get("processes", [])

    for p in processes:
        name = p["name"].lower()
        pid = p["pid"]

        if is_protected(name):
            continue

        # Known game process - give it everything
        if any(g in name for g in ["steam", "wine", "proton", "game"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_REALTIME})
            actions.append({"action": "cgroup_cpu_limit", "pid": pid, "quota": 90})

        # Background noise - kill or deprioritise
        elif any(b in name for b in ["update", "sync", "backup", "index", "tracker"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_BACKGROUND})
            if gear == "heavy":
                actions.append({"action": "kill", "pid": pid, "signal": 19})  # SIGSTOP

        # Everything else gets low priority
        else:
            actions.append({"action": "renice", "pid": pid, "priority": NICE_LOW})

    actions.append({"action": "systemctl", "command": "stop", "unit": "apt-daily.timer"})
    actions.append({"action": "systemctl", "command": "stop", "unit": "fwupd.service"})
    actions.append({"action": "set_governor", "governor": "performance"})

    return actions

def build_dev_actions(snapshot, gear):
    actions = []
    processes = snapshot.get("processes", [])

    for p in processes:
        name = p["name"].lower()
        pid = p["pid"]

        if is_protected(name):
            continue

        # Compiler or build tool - high priority
        if any(c in name for c in ["gcc", "g++", "cargo", "rustc", "make", "cmake", "clang"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_HIGH})
            actions.append({"action": "cgroup_cpu_limit", "pid": pid, "quota": 70})

        # Dev tools - normal priority
        elif any(d in name for d in ["code", "nvim", "vim", "terminal", "node", "python"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_NORMAL})

        # Games - deprioritise
        elif any(g in name for g in ["steam", "wine", "game"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_BACKGROUND})

    actions.append({"action": "set_governor", "governor": "performance"})

    return actions

def build_browsing_actions(snapshot, gear):
    actions = []
    processes = snapshot.get("processes", [])

    for p in processes:
        name = p["name"].lower()
        pid = p["pid"]

        if is_protected(name):
            continue

        if any(b in name for b in ["firefox", "chrome", "chromium", "brave"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_NORMAL})

        elif any(h in name for h in ["update", "backup", "sync", "index"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_BACKGROUND})

    actions.append({"action": "set_governor", "governor": "balanced"})

    return actions

def build_idle_actions(snapshot, gear):
    return [
        {"action": "set_governor", "governor": "powersave"},
        {"action": "systemctl", "command": "start", "unit": "fwupd.service"},
        {"action": "systemctl", "command": "start", "unit": "apt-daily.timer"},
    ]

MODE_BUILDERS = {
    "gaming":   build_gaming_actions,
    "dev":      build_dev_actions,
    "browsing": build_browsing_actions,
    "idle":     build_idle_actions,
}

def decide(snapshot) -> dict:
    resolution = resolve(snapshot)
    mode = resolution["active_mode"]
    gear = get_gear(snapshot)

    builder = MODE_BUILDERS.get(mode, build_browsing_actions)
    actions = builder(snapshot, gear)

    # Log each action
    for a in actions:
        log_action(
            action=a.get("action"),
            target=str(a.get("pid") or a.get("unit") or "system"),
            mode=mode,
            gear=gear,
            result="pending",
            actions = deduplicate(actions)
        )

    return {
        "mode": mode,
        "gear": gear,
        "source": resolution["source"],
        "prompt_user": resolution["prompt_user"],
        "prompt_message": resolution["prompt_message"],
        "actions": actions
    }