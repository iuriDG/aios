import sys
import os
import subprocess
import time
import statistics
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

from profile_store import set_user_pref, init_db

PING_TARGETS = ["1.1.1.1", "8.8.8.8"]
PING_COUNT   = 20

def measure_ping(host: str, count: int = 20) -> dict:
    try:
        out = subprocess.check_output(
            ["ping", "-c", str(count), host],
            timeout=30
        ).decode()

        times = []
        for line in out.splitlines():
            if "time=" not in line:
                continue
            try:
                part = line.split("time=")[1]
                t = float(part.split()[0])
                times.append(t)
            except (IndexError, ValueError):
                continue

        if not times:
            return {}

        return {
            "host": host,
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "avg_ms": round(statistics.mean(times), 2),
            "jitter_ms": round(statistics.stdev(times), 2) if len(times) > 1 else 0
        }
    except Exception as e:
        print(f"Ping failed for {host}: {e}")
        return {}

def measure_bandwidth() -> dict:
    try:
        start = time.time()
        subprocess.check_output(
            ["curl", "-s", "-o", "/dev/null",
             "http://speedtest.tele2.net/10MB.zip",
             "--max-time", "15"],
            timeout=20
        )
        elapsed = time.time() - start
        mbps = round((10 * 8) / elapsed, 2)  # 10MB file to Mbps
        return {"download_mbps": mbps, "elapsed_secs": round(elapsed, 2)}
    except Exception as e:
        print(f"Bandwidth test failed: {e}")
        return {"download_mbps": 0}

def run():
    init_db()

    print("=" * 50)
    print("AIOS Network Profile Setup")
    print("=" * 50)

    # Baseline ping
    print("\nMeasuring baseline latency...")
    pings = []
    for target in PING_TARGETS:
        result = measure_ping(target, PING_COUNT)
        if result:
            print(f"  {target}: avg {result['avg_ms']}ms "
                  f"jitter {result['jitter_ms']}ms")
            pings.append(result["avg_ms"])

    baseline_ping = None
    if pings:
        baseline_ping = round(statistics.mean(pings), 2)
        set_user_pref("network_baseline_ping_ms", str(baseline_ping))
        print(f"\nBaseline ping: {baseline_ping}ms")

    # Bandwidth
    print("\nMeasuring bandwidth (downloading 10MB test file)...")
    bw = measure_bandwidth()
    print(f"Download speed: {bw.get('download_mbps', 0)} Mbps")
    set_user_pref("network_baseline_mbps", str(bw.get("download_mbps", 0)))

    # Primary app
    print("\nWhich app needs network priority?")
    print("Examples: firefox, steam, zoom, vscode")
    try:
        primary = input("> ").strip().lower()
    except EOFError:
        primary = ""

    if primary:
        set_user_pref("network_priority_app", primary)

        print("\nHow much can other apps be affected during contention?")
        print("  1. low    - barely noticeable")
        print("  2. medium - some slowdown acceptable")
        print("  3. high   - background apps can be heavily throttled")
        impact_options = ["low", "medium", "high"]
        while True:
            try:
                raw = int(input("> ")) - 1
                if 0 <= raw < len(impact_options):
                    impact = impact_options[raw]
                    set_user_pref("network_impact_tolerance", impact)
                    break
                print("Enter 1, 2 or 3")
            except (ValueError, EOFError):
                print("Enter 1, 2 or 3")

        # Set ping threshold - alert if primary app latency exceeds this
        threshold = round(baseline_ping * 2, 2) if baseline_ping is not None else 100
        set_user_pref("network_ping_threshold_ms", str(threshold))
        print(f"\nPing alert threshold set to {threshold}ms")

    print("\nNetwork profile complete")

if __name__ == "__main__":
    run()
