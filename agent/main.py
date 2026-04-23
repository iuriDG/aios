import time
import json
import os
import subprocess
from observer import observe
from decision_engine import decide
from llm_interface import ask, is_ollama_running
from profile_store import init_db, get_user_pref, set_user_pref, log_action, cleanup_audit_log
from config import LOOP_CADENCE, DRY_RUN, SOCKET_PATH, READY_FILE
from ipc import send_actions

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
    # Uses native OS notification - Linux only
    try:
        subprocess.run(["notify-send", "AIOS", message], check=False)
    except FileNotFoundError:
        print(f"[NOTIFY] {message}")

def send_to_helper(actions: list, gear: str, mode: str):
    # Placeholder until helper IPC is built in phase 2
    # For now just logs what would be sent
    for action in actions:
        print(f"[HELPER] {json.dumps(action)}")
        log_action(
            action=action.get("action"),
            target=str(action.get("pid") or action.get("unit") or "system"),
            mode=mode,
            gear=gear,
            result="dry_run" if DRY_RUN else "sent"
        )

def run():
    init_db()
    cleanup_audit_log()
    print("AIOS agent starting...")
    print(f"Dry run: {DRY_RUN}")
    print(f"Ollama available: {is_ollama_running()}")

    # Track last 3 snapshots for stability check
    history = []

    while True:
        if os.path.exists("/run/aios/paused"):
            print("[LOOP] Paused")
            time.sleep(10)
            continue
        try:
            # Observe
            snapshot = observe()

            # Decide
            decision = decide(snapshot)
            mode = decision["mode"]
            gear = decision["gear"]
            actions = decision["actions"]

            # If Ollama is running supplement rule-based actions with LLM
            if is_ollama_running() and gear != "heavy":
                llm_actions = ask(snapshot, mode, gear)
                if llm_actions:
                    # LLM actions take priority over rule-based
                    actions = llm_actions

            # Stability check - only act if last 3 snapshots agree on mode
            history.append(mode)
            if len(history) > 3:
                history.pop(0)

            stable = len(set(history)) == 1

            if not stable:
                print(f"[LOOP] Mode unstable {history} - holding last decision")
                time.sleep(LOOP_CADENCE.get(gear, 5))
                continue

            # Notify user if mismatch detected
            if decision.get("prompt_user") and decision.get("prompt_message"):
                send_notification(decision["prompt_message"])

            # Send actions to helper
            if actions:
                print(f"[LOOP] Mode: {mode} | Gear: {gear} | Actions: {len(actions)} | Source: {decision['source']}")
                send_to_helper(actions, gear, mode)
            else:
                print(f"[LOOP] Mode: {mode} | Gear: {gear} | No actions")

            time.sleep(LOOP_CADENCE.get(gear, 5))

        except KeyboardInterrupt:
            print("\nAIOS agent stopped")
            break

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)

if __name__ == "__main__":
    run()