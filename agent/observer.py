import psutil
import json
import time
import logging
import os
from datetime import datetime

logging.basicConfig(
    filename='observer.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

_GOVERNOR_PATH = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"


def _get_processes():
    result = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
        try:
            result.append({
                "pid": p.pid,
                "name": p.name(),
                "cpu_pct": p.cpu_percent(),
                "ram_mb": round(p.memory_info().rss / 1e6, 1),
                "status": p.status()
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(result, key=lambda x: x["cpu_pct"], reverse=True)[:15]


def observe():
    governor = None
    if os.path.exists(_GOVERNOR_PATH):
        with open(_GOVERNOR_PATH) as f:
            governor = f.read().strip()

    return {
        "timestamp": datetime.now().isoformat(),
        "cpu": {
            "percent_total": psutil.cpu_percent(interval=1),
            "percent_per_core": psutil.cpu_percent(interval=1, percpu=True),
            "freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else None,
            "governor": governor
        },
        "ram": {
            "total_gb": round(psutil.virtual_memory().total / 1e9, 1),
            "used_pct": psutil.virtual_memory().percent,
            "available_gb": round(psutil.virtual_memory().available / 1e9, 1),
            "swap_used_pct": psutil.swap_memory().percent
        },
        "disk": {
            "read_mb": round(psutil.disk_io_counters().read_bytes / 1e6, 1),
            "write_mb": round(psutil.disk_io_counters().write_bytes / 1e6, 1)
        },
        "network": {
            "bytes_sent_mb": round(psutil.net_io_counters().bytes_sent / 1e6, 1),
            "bytes_recv_mb": round(psutil.net_io_counters().bytes_recv / 1e6, 1)
        },
        "processes": _get_processes()
    }

if __name__ == "__main__":
    print("Observer running — logging to observer.log")
    while True:
        try:
            snapshot = observe()
            logging.info(json.dumps(snapshot))
            print(json.dumps(snapshot, indent=2))
        except Exception as e:
            logging.error(f"Observer error: {e}")
        time.sleep(5)