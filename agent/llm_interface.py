import requests
import json
from profile_store import get_user_pref

from config import OLLAMA_URL, OLLAMA_MODEL
MODEL = OLLAMA_MODEL

SYSTEM_PROMPT = """
You are an OS process manager for an AI-driven operating system.
You receive a system state snapshot and current mode.
You return a JSON array of actions to optimise the system.

Rules:
- Never touch protected processes: systemd, init, sshd, networkmanager, 
  dbus, aios-agent, aios-helper, aios-watchdog, any PID below 100
- Only use these action types:
    renice, cgroup_cpu_limit, cgroup_ram_limit, kill, 
    systemctl, cpuset_assign, tc_priority, set_governor
- Always return valid JSON array only - no explanation, no markdown
- If gear is heavy, be aggressive with background processes
- If gear is low, be conservative

Example output:
[
  {"action": "renice", "pid": 1234, "priority": -10},
  {"action": "set_governor", "governor": "performance"},
  {"action": "systemctl", "command": "stop", "unit": "apt-daily.timer"}
]
"""

def build_prompt(snapshot: dict, mode: str, gear: str) -> str:
    # Trim snapshot to save tokens - LLM doesnt need everything
    trimmed = {
        "cpu_total": snapshot.get("cpu", {}).get("percent_total"),
        "ram_used_pct": snapshot.get("ram", {}).get("used_pct"),
        "gpu_utilisation": snapshot.get("gpu", {}).get("utilisation_pct", 0),
        "mode": mode,
        "gear": gear,
        "autonomy": get_user_pref("autonomy_level") or "balanced",
        "top_processes": snapshot.get("processes", [])[:10]
    }
    return json.dumps(trimmed)

def parse_response(raw: str) -> list:
    # Strip markdown code blocks if model adds them
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError:
        return []

def ask(snapshot: dict, mode: str, gear: str) -> list:
    prompt = build_prompt(snapshot, mode, gear)

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temp - we want consistent decisions
                "num_predict": 512
            }
        }, timeout=30)

        raw = response.json().get("response", "")
        actions = parse_response(raw)
        return actions

    except requests.exceptions.ConnectionError:
        # Ollama not running - fall back to rule-based decision engine
        print("Ollama unavailable - falling back to rule-based decisions")
        return []

    except Exception as e:
        print(f"LLM error: {e}")
        return []

def is_ollama_running() -> bool:
    try:
        r = requests.get("http://localhost:11434", timeout=2)
        return r.status_code == 200
    except:
        return False