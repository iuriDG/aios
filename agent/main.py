import os
import time
import json
import subprocess
from datetime import datetime
from observer import observe
from decision_engine import decide
from llm_interface import ask, is_ollama_running, is_model_available
from profile_store import init_db, get_user_pref, set_user_pref, log_action, cleanup_audit_log, upsert_app_profile
from ipc import send_actions
from network_monitor import start as start_network_monitor
from network_monitor import stop as stop_network_monitor
from config import LOOP_CADENCE, DRY_RUN, READY_FILE, OLLAMA_MODEL, PAUSED_FILE, PROMPT_FILE, PROMPT_REPLY_FILE


def send_to_helper(actions: list, gear: str, mode: str):
    results = send_actions(actions)
    for r in results:
        log_action(
            action=r["action"].get("action"),
            target=str(r["action"].get("pid") or r["action"].get("unit") or "system"),
            mode=mode,
            gear=gear,
            result="ok" if r["result"].get("success") else r["result"].get("message")
        )

def send_notification(message: str):
    try:
        subprocess.run(["notify-send", "AIOS", message], check=False)
    except FileNotFoundError:
        print(f"[NOTIFY] {message}")

def record_profile(snapshot: dict, mode: str):
    import psutil
    focus = snapshot.get("focus") or {}
    binary = focus.get("class", "").strip()
    if not binary:
        return
    focus_pid = focus.get("pid", 0)
    proc = next((p for p in snapshot.get("processes", []) if p["pid"] == focus_pid), None)
    if not proc:
        try:
            p = psutil.Process(focus_pid)
            proc = {"cpu_pct": p.cpu_percent(interval=0.1), "ram_mb": round(p.memory_info().rss / 1e6, 1)}
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return
    upsert_app_profile(binary, mode, {
        "cpu_avg":          proc.get("cpu_pct", 0),
        "ram_avg_mb":       proc.get("ram_mb", 0),
        "gpu_avg":          snapshot.get("gpu", {}).get("utilisation_pct", 0),
        "disk_read_avg_mb": snapshot.get("disk", {}).get("read_mb", 0),
        "disk_write_avg_mb":snapshot.get("disk", {}).get("write_mb", 0),
    })

def run():
    init_db()
    cleanup_audit_log()
    start_network_monitor()

    if is_ollama_running():
        if not is_model_available():
            print(f"[LLM] Model {OLLAMA_MODEL} not found - run: ollama pull {OLLAMA_MODEL}")

    os.makedirs("/run/aios", exist_ok=True)
    with open(READY_FILE, "w") as f:
        f.write("ready")

    print("AIOS agent starting...")
    print(f"Dry run: {DRY_RUN}")
    print(f"Ollama available: {is_ollama_running()}")

    history = []

    while True:
        if os.path.exists(PAUSED_FILE):
            print("[LOOP] Paused")
            time.sleep(10)
            continue

        try:
            snapshot = observe()

            decision = decide(snapshot)
            mode = decision["mode"]
            gear = decision["gear"]
            actions = decision["actions"]
            source = decision["source"]

            if is_ollama_running():
                llm_actions = ask(snapshot, mode, gear)
                if llm_actions:
                    actions = llm_actions
                    source = "llm"
                    print(f"[LLM] Ollama decisions: {len(llm_actions)} actions", flush=True)
                else:
                    print("[LLM] No valid response - using rule-based", flush=True)

            record_profile(snapshot, mode)

            history.append(mode)
            if len(history) > 3:
                history.pop(0)

            stable = len(set(history)) == 1

            if not stable:
                print(f"[LOOP] Mode unstable {history} - holding last decision")
                time.sleep(LOOP_CADENCE.get(gear, 5))
                continue

            if decision.get("prompt_user") and decision.get("prompt_message"):
                send_notification(decision["prompt_message"])
                with open(PROMPT_FILE, "w") as f:
                    f.write(decision["prompt_message"])

            if os.path.exists(PROMPT_REPLY_FILE):
                with open(PROMPT_REPLY_FILE) as f:
                    reply = f.read().strip().lower()
                if reply in ["gaming", "dev", "browsing", "idle"]:
                    set_user_pref("prompt_reply_mode", reply)
                    set_user_pref("prompt_reply_set_at", datetime.now().isoformat())
                os.remove(PROMPT_REPLY_FILE)

            if actions:
                print(f"[LOOP] Mode: {mode} | Gear: {gear} | Actions: {len(actions)} | Source: {source}")
                send_to_helper(actions, gear, mode)
            else:
                print(f"[LOOP] Mode: {mode} | Gear: {gear} | No actions")

            time.sleep(LOOP_CADENCE.get(gear, 5))

        except KeyboardInterrupt:
            stop_network_monitor()
            print("\nAIOS agent stopped")
            break

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)

if __name__ == "__main__":
    run()
