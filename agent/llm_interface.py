import requests
import json
from profile_store import get_user_pref

from config import OLLAMA_URL, OLLAMA_MODEL

SYSTEM_PROMPT = """You are an OS process manager. Return a JSON array of actions only — no explanation, no markdown.
Required fields per action:
- renice: {"action":"renice","pid":<int>,"priority":<int -20..19>}
- kill: {"action":"kill","pid":<int>,"signal":<9|15>}
- set_governor: {"action":"set_governor","governor":<"performance"|"schedutil"|"powersave">}
- systemctl: {"action":"systemctl","command":<"stop"|"restart">,"unit":<string>}
- cgroup_cpu_limit: {"action":"cgroup_cpu_limit","pid":<int>,"quota":<1..100>}
Never touch PIDs below 100 or: systemd, init, sshd, networkmanager, dbus, aios-agent, aios-helper, aios-watchdog, code, electron, gnome-shell, plasmashell, Xorg, pipewire, pulseaudio
Never use kill action on interactive user processes or desktop applications."""

# Base URL derived from OLLAMA_URL so config is the single source of truth
_OLLAMA_BASE = "http://localhost:11434"

def build_prompt(snapshot: dict, mode: str, gear: str) -> str:
    procs = [
        {"pid": p["pid"], "name": p["name"], "cpu": round(p["cpu_pct"], 1)}
        for p in snapshot.get("processes", [])[:5]
    ]
    trimmed = {
        "cpu": round(snapshot.get("cpu", {}).get("percent_total", 0), 1),
        "ram": round(snapshot.get("ram", {}).get("used_pct", 0), 1),
        "mode": mode,
        "gear": gear,
        "procs": procs
    }
    return json.dumps(trimmed)

def parse_response(raw: str) -> list:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
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

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 256
            }
        }, timeout=90)

        if response.status_code != 200:
            print(f"[LLM] HTTP {response.status_code} - falling back to rule-based")
            return []

        raw = response.json().get("response", "")
        actions = parse_response(raw)
        if not actions:
            print("[LLM] Empty/invalid response - falling back to rule-based")
        return actions

    except requests.exceptions.Timeout:
        print("[LLM] Timed out - falling back to rule-based")
        return []
    except Exception as e:
        print(f"[LLM] Error: {e} - falling back to rule-based")
        return []

def has_enough_ram() -> bool:
    import psutil
    from profile_store import get_user_pref
    # If the Ollama runner is already active, the model is already in memory —
    # calling it costs no additional RAM.
    for p in psutil.process_iter(['name']):
        try:
            if 'ollama' in p.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
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
