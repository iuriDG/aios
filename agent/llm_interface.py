import requests
import json
from profile_store import get_user_pref

from config import OLLAMA_URL, OLLAMA_MODEL

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

# Base URL derived from OLLAMA_URL so config is the single source of truth
_OLLAMA_BASE = "http://localhost:11434"

def build_prompt(snapshot: dict, mode: str, gear: str) -> str:
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
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        # parts[1] is the fenced block content, parts[2] is after closing fence
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError:
        return []

def ask(snapshot: dict, mode: str, gear: str) -> list:
    if not has_enough_ram():
        print("[LLM] Not enough RAM - using rule-based decisions")
        return []
    prompt = build_prompt(snapshot, mode, gear)
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "system": SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 512
                }
            }, timeout=30)

            if response.status_code != 200:
                print(f"[LLM] HTTP {response.status_code} on attempt {attempt + 1} - retrying")
                continue

            raw = response.json().get("response", "")
            actions = parse_response(raw)

            if actions:
                return actions

            print(f"[LLM] Empty response on attempt {attempt + 1} - retrying")

        except requests.exceptions.ConnectionError:
            print(f"[LLM] Connection error on attempt {attempt + 1} - retrying")

        except Exception as e:
            print(f"[LLM] Error on attempt {attempt + 1}: {e}")

    print("[LLM] All retries failed - falling back to rule-based decisions")
    return []

def has_enough_ram() -> bool:
    import psutil
    from profile_store import get_user_pref
    required = float(get_user_pref("hw_llm_ram_gb") or 3.5)
    available = psutil.virtual_memory().available / 1e9
    return available >= required + 0.5

def is_ollama_running() -> bool:
    try:
        r = requests.get(f"{_OLLAMA_BASE}", timeout=2)
        return r.status_code < 400
    except Exception:
        return False

def is_model_available() -> bool:
    try:
        r = requests.get(f"{_OLLAMA_BASE}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        return any(OLLAMA_MODEL in m for m in models)
    except Exception:
        return False
