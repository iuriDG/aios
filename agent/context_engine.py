import psutil
import json
from profile_store import get_app_profile, get_user_pref
from config import KNOWN_GAMES, KNOWN_DEV, KNOWN_BROWSER, COMPILERS


def get_running_process_names(snapshot):
    return [p["name"].lower() for p in snapshot.get("processes", [])]

def get_top_cpu_process(snapshot):
    procs = snapshot.get("processes", [])
    if not procs:
        return None
    return procs[0]["name"].lower()

def is_compiling(process_names):
    return any(c in process_names for c in COMPILERS)

def gpu_load(snapshot):
    return snapshot.get("gpu", {}).get("utilisation_pct", 0)

def classify(snapshot) -> dict:
    process_names = get_running_process_names(snapshot)
    top_cpu = get_top_cpu_process(snapshot)
    gpu = gpu_load(snapshot)
    cpu_total = snapshot.get("cpu", {}).get("percent_total", 0)

    scores = {
        "gaming":   0,
        "dev":      0,
        "browsing": 0,
        "idle":     0
    }

    # Gaming signals
    if gpu > 60:
        scores["gaming"] += 40
    if any(g in process_names for g in KNOWN_GAMES):
        scores["gaming"] += 40
    if top_cpu in KNOWN_GAMES:
        scores["gaming"] += 20

    # Dev signals
    if is_compiling(process_names):
        scores["dev"] += 50
    if any(d in process_names for d in KNOWN_DEV):
        scores["dev"] += 30
    if top_cpu in KNOWN_DEV:
        scores["dev"] += 20

    # Browsing signals
    if any(b in process_names for b in KNOWN_BROWSER):
        scores["browsing"] += 40
    if top_cpu in KNOWN_BROWSER:
        scores["browsing"] += 30

    # Idle signals
    idle_threshold = int(get_user_pref("idle_threshold_minutes") or 5)
    if cpu_total < 5 and gpu < 5:
        scores["idle"] += 60

    # Weight scores using existing profiles
    for process in snapshot.get("processes", []):
        name = process["name"].lower()
        for mode in ["gaming", "dev", "browsing"]:
            profile = get_app_profile(name, mode)
            if profile:
                scores[mode] = scores.get(mode, 0) + 15

    # Winner
    mode = max(scores, key=scores.get)
    confidence = scores[mode]

    return {
        "mode": mode,
        "confidence": confidence,
        "scores": scores,
        "top_cpu_process": top_cpu,
        "compiling": is_compiling(process_names),
        "gpu_active": gpu > 30
    }

if __name__ == "__main__":
    fake_snapshot = {
        "cpu": {"percent_total": 45},
        "gpu": {"utilisation_pct": 75},
        "processes": [
            {"name": "steam", "cpu_pct": 30, "ram_mb": 400},
            {"name": "firefox", "cpu_pct": 10, "ram_mb": 300},
        ]
    }
    result = classify(fake_snapshot)
    print(json.dumps(result, indent=2))