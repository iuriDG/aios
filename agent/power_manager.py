import subprocess
from profile_store import get_user_pref, set_user_pref

def get_power_state() -> dict:
    try:
        out = subprocess.check_output(
            ["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"],
            timeout=5
        ).decode()

        state = {
            "on_battery": False,
            "percentage": 100,
            "charging": True
        }

        for line in out.splitlines():
            if "state:" in line:
                state["charging"] = "charging" in line or "fully-charged" in line
                state["on_battery"] = "discharging" in line
            if "percentage:" in line:
                pct = line.split(":")[1].strip().replace("%", "")
                state["percentage"] = float(pct)

        return state

    except Exception:
        # No battery - desktop machine or upower not available
        return {
            "on_battery": False,
            "percentage": 100,
            "charging": True
        }

def get_power_recommendation(mode: str, gear: str) -> dict:
    state = get_power_state()
    on_battery = state["on_battery"]
    battery_pct = state["percentage"]

    recommendation = {
        "governor": "schedutil",
        "warn_user": False,
        "warn_message": None,
        "defer_heavy_tasks": False
    }

    if not on_battery:
        # On AC - be aggressive
        if mode == "gaming":
            recommendation["governor"] = "performance"
        elif mode == "dev":
            recommendation["governor"] = "performance"
        elif mode == "idle":
            recommendation["governor"] = "powersave"
        else:
            recommendation["governor"] = "schedutil"
        return recommendation

    # On battery - be conservative
    if mode == "gaming":
        recommendation["governor"] = "schedutil"
        recommendation["warn_user"] = True
        recommendation["warn_message"] = "Gaming on battery - consider plugging in for best performance"

    elif mode == "dev":
        if battery_pct < 20:
            recommendation["governor"] = "powersave"
            recommendation["defer_heavy_tasks"] = True
            recommendation["warn_user"] = True
            recommendation["warn_message"] = "Battery below 20% - heavy builds deferred until charged"
        else:
            recommendation["governor"] = "schedutil"

    elif mode == "idle":
        recommendation["governor"] = "powersave"

    else:
        recommendation["governor"] = "powersave" if battery_pct < 30 else "schedutil"

    return recommendation