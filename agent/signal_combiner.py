import json
from datetime import datetime, timedelta
from profile_store import get_user_pref, set_user_pref
from context_engine import classify
from config import CONFIDENCE_THRESHOLD, MANUAL_MODE_EXPIRY_MINUTES, SUPPRESS_PROMPT_MINUTES, PROMPT_REPLY_EXPIRY_HOURS

def get_manual_mode():
    mode = get_user_pref("manual_mode")
    set_time = get_user_pref("manual_mode_set_at")
    if not mode or not set_time:
        return None
    set_at = datetime.fromisoformat(set_time)
    if datetime.now() - set_at > timedelta(minutes=MANUAL_MODE_EXPIRY_MINUTES):
        # Expired - clear it
        set_user_pref("manual_mode", "")
        return None
    return mode

def get_prompt_reply():
    reply = get_user_pref("prompt_reply_mode")
    reply_time = get_user_pref("prompt_reply_set_at")
    if not reply or not reply_time:
        return None
    set_at = datetime.fromisoformat(reply_time)
    # Prompt reply valid for one session only - 4 hours
    if datetime.now() - set_at > timedelta(hours=PROMPT_REPLY_EXPIRY_HOURS):
        set_user_pref("prompt_reply_mode", "")
        return None
    return reply

def is_suppressed(mode):
    suppress_until = get_user_pref(f"suppress_prompt_until_{mode}")
    if not suppress_until:
        return False
    return datetime.now() < datetime.fromisoformat(suppress_until)

def suppress_prompt(mode):
    until = datetime.now() + timedelta(minutes=SUPPRESS_PROMPT_MINUTES)
    set_user_pref(f"suppress_prompt_until_{mode}", until.isoformat())

def should_prompt(detected_mode, manual_mode, confidence):
    # No mismatch if no manual mode set
    if not manual_mode:
        return False
    # No mismatch if they agree
    if detected_mode == manual_mode:
        return False
    # Not confident enough to bother user
    if confidence < CONFIDENCE_THRESHOLD:
        return False
    # Suppressed after previous dismiss
    if is_suppressed(detected_mode):
        return False
    return True

def resolve(snapshot) -> dict:
    classification = classify(snapshot)
    detected_mode = classification["mode"]
    confidence = classification["confidence"]

    manual_mode = get_manual_mode()
    prompt_reply = get_prompt_reply()

    # Priority 1 - manual mode
    if manual_mode:
        prompt_needed = should_prompt(detected_mode, manual_mode, confidence)
        return {
            "active_mode": manual_mode,
            "source": "manual",
            "confidence": 100,
            "prompt_user": prompt_needed,
            "prompt_message": f"Looks like you switched to {detected_mode} - optimise for that?" if prompt_needed else None,
            "detected_mode": detected_mode
        }

    # Priority 2 - prompt reply
    if prompt_reply:
        return {
            "active_mode": prompt_reply,
            "source": "prompt_reply",
            "confidence": 90,
            "prompt_user": False,
            "prompt_message": None,
            "detected_mode": detected_mode
        }

    # Priority 3 - auto detection
    return {
        "active_mode": detected_mode,
        "source": "auto",
        "confidence": confidence,
        "prompt_user": False,
        "prompt_message": None,
        "detected_mode": detected_mode
    }