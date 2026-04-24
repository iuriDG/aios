#!/usr/bin/env python3
import subprocess, time, json, re, os, sys

DISPLAY = os.environ.get("DISPLAY", ":0")
OUT_FILE = "/tmp/aios_focus"
ENV = {**os.environ, "DISPLAY": DISPLAY}

def get_active_window():
    try:
        root = subprocess.check_output(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"], env=ENV, text=True, stderr=subprocess.DEVNULL
        )
        win_id = re.search(r"0x[0-9a-f]+", root)
        if not win_id:
            return None
        info = subprocess.check_output(
            ["xprop", "-id", win_id.group(), "WM_CLASS", "_NET_WM_NAME", "_NET_WM_PID"],
            env=ENV, text=True, stderr=subprocess.DEVNULL
        )
        cls   = re.search(r'WM_CLASS.*?= "(.*?)"', info)
        title = re.search(r'_NET_WM_NAME.*?= "(.*?)"', info)
        pid   = re.search(r'_NET_WM_PID.*?= (\d+)', info)
        return {
            "class": cls.group(1).lower() if cls else "",
            "title": title.group(1) if title else "",
            "pid":   int(pid.group(1)) if pid else 0,
        }
    except Exception:
        return None

def main():
    print(f"[focus-watcher] started, writing to {OUT_FILE}", flush=True)
    while True:
        window = get_active_window()
        if window:
            with open(OUT_FILE, "w") as f:
                json.dump(window, f)
        time.sleep(1)

if __name__ == "__main__":
    main()
