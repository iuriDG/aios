import subprocess
import statistics
import threading
import time
from profile_store import get_user_pref, set_user_pref
from config import NETWORK_PING_INTERVAL_SECS, NETWORK_PING_COUNT

_monitor_thread = None
_running = False

def measure_ping(host: str, count: int = 5) -> float:
    try:
        out = subprocess.check_output(
            ["ping", "-c", str(count or NETWORK_PING_COUNT), host],
            timeout=15
        ).decode()

        times = []
        for line in out.splitlines():
            if "time=" in line:
                t = float(line.split("time=")[1].split()[0])
                times.append(t)

        return round(statistics.mean(times), 2) if times else 999.0

    except Exception:
        return 999.0

def get_primary_app_host() -> str:
    app = get_user_pref("network_priority_app") or ""
    # Map known apps to their endpoints
    known = {
        "steam":    "cm.steampowered.com",
        "zoom":     "zoom.us",
        "discord":  "discord.com",
        "firefox":  "1.1.1.1",
        "chrome":   "1.1.1.1",
        "vscode":   "1.1.1.1",
    }
    return known.get(app.lower(), "1.1.1.1")

def apply_throttle(throttle: bool):
    impact = get_user_pref("network_impact_tolerance") or "medium"
    interface = get_default_interface()
    if not interface:
        return

    if throttle:
        # Throttle background traffic based on impact tolerance
        rates = {
            "low":    "50mbit",
            "medium": "10mbit",
            "high":   "1mbit"
        }
        rate = rates.get(impact, "10mbit")
        subprocess.run([
            "tc", "qdisc", "add", "dev", interface,
            "root", "tbf", "rate", rate,
            "burst", "32kbit", "latency", "400ms"
        ], check=False)
    else:
        # Remove throttle
        subprocess.run([
            "tc", "qdisc", "del", "dev", interface, "root"
        ], check=False)

def get_default_interface() -> str:
    try:
        out = subprocess.check_output(
            ["ip", "route", "show", "default"],
            timeout=5
        ).decode().strip()

        for part in out.split():
            if part == "dev":
                idx = out.split().index(part)
                return out.split()[idx + 1]
        return ""
    except Exception:
        return ""

def monitor_loop():
    global _running
    baseline = float(get_user_pref("network_baseline_ping_ms") or 50)
    threshold = float(get_user_pref("network_ping_threshold_ms") or baseline * 2)
    host = get_primary_app_host()
    throttling = False

    print(f"[NETWORK] Monitoring {host} threshold {threshold}ms")

    while _running:
        current_ping = measure_ping(host)

        if current_ping > threshold and not throttling:
            print(f"[NETWORK] Latency spike {current_ping}ms - throttling background traffic")
            apply_throttle(True)
            throttling = True

        elif current_ping <= threshold and throttling:
            print(f"[NETWORK] Latency restored {current_ping}ms - removing throttle")
            apply_throttle(False)
            throttling = False

        time.sleep(NETWORK_PING_INTERVAL_SECS)

def start():
    global _monitor_thread, _running
    if get_user_pref("network_priority_app"):
        _running = True
        _monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        _monitor_thread.start()
        print("[NETWORK] Monitor started")
    else:
        print("[NETWORK] No priority app set - monitor not started")

def stop():
    global _running
    _running = False
    apply_throttle(False)
    print("[NETWORK] Monitor stopped")