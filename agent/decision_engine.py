import json
import subprocess
from profile_store import get_user_pref, set_user_pref, log_action
from signal_combiner import resolve
from power_manager import get_power_recommendation
from config import (PROTECTED_PROCESSES, NICE_REALTIME, NICE_HIGH, NICE_NORMAL, NICE_LOW, NICE_BACKGROUND)

PROTECTED = PROTECTED_PROCESSES

def deduplicate(actions: list) -> list:
    seen = set()
    result = []
    for a in actions:
        key = (a.get("action"), a.get("pid"), a.get("unit"))
        if key not in seen:
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
    for p in snapshot.get("processes", []):
        name = p["name"].lower()
        pid = p["pid"]
        if is_protected(name):
            continue
        if any(g in name for g in ["steam", "wine", "proton", "game"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_REALTIME})
            actions.append({"action": "cgroup_cpu_limit", "pid": pid, "quota": 90})
        elif any(b in name for b in ["update", "sync", "backup", "index", "tracker"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_BACKGROUND})
            if gear == "heavy":
                actions.append({"action": "kill", "pid": pid, "signal": 19})
        else:
            actions.append({"action": "renice", "pid": pid, "priority": NICE_LOW})
    actions.append({"action": "systemctl", "command": "stop", "unit": "apt-daily.timer"})
    actions.append({"action": "systemctl", "command": "stop", "unit": "fwupd.service"})
    return actions

def build_dev_actions(snapshot, gear):
    actions = []
    for p in snapshot.get("processes", []):
        name = p["name"].lower()
        pid = p["pid"]
        if is_protected(name):
            continue
        if any(c in name for c in ["gcc", "g++", "cargo", "rustc", "make", "cmake", "clang"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_HIGH})
            actions.append({"action": "cgroup_cpu_limit", "pid": pid, "quota": 70})
        elif any(d in name for d in ["code", "nvim", "vim", "terminal", "node", "python"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_NORMAL})
        elif any(g in name for g in ["steam", "wine", "game"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_BACKGROUND})
    return actions

def build_browsing_actions(snapshot, gear):
    actions = []
    for p in snapshot.get("processes", []):
        name = p["name"].lower()
        pid = p["pid"]
        if is_protected(name):
            continue
        if any(b in name for b in ["firefox", "chrome", "chromium", "brave"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_NORMAL})
        elif any(h in name for h in ["update", "backup", "sync", "index"]):
            actions.append({"action": "renice", "pid": pid, "priority": NICE_BACKGROUND})
    return actions

def build_idle_actions(snapshot, gear):
    return [
        {"action": "systemctl", "command": "start", "unit": "fwupd.service"},
        {"action": "systemctl", "command": "start", "unit": "apt-daily.timer"},
    ]

MODE_BUILDERS = {
    "gaming":   build_gaming_actions,
    "dev":      build_dev_actions,
    "browsing": build_browsing_actions,
    "idle":     build_idle_actions,
}

def build_transition_actions(snapshot, old_mode, new_mode) -> list:
    actions = []
    for p in snapshot.get("processes", []):
        name = p["name"].lower()
        pid = p["pid"]
        if is_protected(name):
            continue
        if old_mode == "gaming":
            if any(g in name for g in ["steam", "wine", "proton"]):
                actions.append({"action": "renice", "pid": pid, "priority": NICE_LOW})
        elif old_mode == "dev":
            if any(d in name for d in ["gcc", "cargo", "make"]):
                actions.append({"action": "renice", "pid": pid, "priority": NICE_NORMAL})
    actions.append({"action": "set_governor", "governor": "balanced"})
    return actions

def decide(snapshot) -> dict:
    resolution = resolve(snapshot)
    mode = resolution["active_mode"]
    gear = get_gear(snapshot)
    last_mode = get_user_pref("last_mode")
    transition_step = int(get_user_pref("transition_step") or 0)

    # Transition handling
    if last_mode and last_mode != mode:
        transition_step += 1
        set_user_pref("transition_step", str(transition_step))
        if transition_step < 3:
            print(f"[TRANSITION] {last_mode} -> {mode} step {transition_step}/3")
            actions = build_transition_actions(snapshot, last_mode, mode)
            return {
                "mode": last_mode,
                "gear": gear,
                "source": resolution["source"],
                "prompt_user": resolution["prompt_user"],
                "prompt_message": resolution["prompt_message"],
                "actions": deduplicate(actions)
            }
        else:
            print(f"[TRANSITION] Complete - now in {mode}")
            set_user_pref("last_mode", mode)
            set_user_pref("transition_step", "0")
    else:
        set_user_pref("last_mode", mode)
        set_user_pref("transition_step", "0")

    # Build actions for current mode
    builder = MODE_BUILDERS.get(mode, build_browsing_actions)
    actions = builder(snapshot, gear)

    # Apply power recommendation
    power = get_power_recommendation(mode, gear)
    actions.append({"action": "set_governor", "governor": power["governor"]})

    if power["warn_user"] and power["warn_message"]:
        subprocess.run(["notify-send", "AIOS Power", power["warn_message"]], check=False)

    if power["defer_heavy_tasks"]:
        actions = [a for a in actions if not (
            a.get("action") == "renice" and
            a.get("priority", 0) < 0
        )]

    # Deduplicate before logging
    actions = deduplicate(actions)

    # Log each action
    for a in actions:
        log_action(
            action=a.get("action"),
            target=str(a.get("pid") or a.get("unit") or "system"),
            mode=mode,
            gear=gear,
            result="pending"
        )

    return {
        "mode": mode,
        "gear": gear,
        "source": resolution["source"],
        "prompt_user": resolution["prompt_user"],
        "prompt_message": resolution["prompt_message"],
        "actions": actions
    }