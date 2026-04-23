import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

from profile_store import init_db, set_user_pref, upsert_app_profile

AUTONOMY_LEVELS = ["conservative", "balanced", "aggressive"]
MODES = ["gaming", "dev", "browsing", "mixed"]
GOVERNORS = ["performance", "balanced", "powersave"]

def ask(question, options=None, multi=False):
    print(f"\n{question}")
    if options:
        for i, o in enumerate(options, 1):
            print(f"  {i}. {o}")
        while True:
            try:
                if multi:
                    raw = input("Enter numbers separated by commas: ")
                    picks = [int(x.strip()) - 1 for x in raw.split(",")]
                    if all(0 <= p < len(options) for p in picks):
                        return [options[p] for p in picks]
                else:
                    pick = int(input("Enter number: ")) - 1
                    if 0 <= pick < len(options):
                        return options[pick]
            except (ValueError, IndexError):
                pass
            print("Invalid choice - try again")
    else:
        return input("> ").strip()

def run():
    init_db()

    print("=" * 50)
    print("AIOS First Run Setup")
    print("=" * 50)
    print("Answer a few questions so the AI knows how to behave.")

    # Primary use
    primary_use = ask(
        "What do you primarily use this machine for?",
        MODES
    )
    set_user_pref("primary_use", primary_use)

    # Apps they use most
    apps_raw = ask(
        "Which apps do you use most? (type them separated by commas)\nExample: steam, vscode, firefox, discord"
    )
    apps = [a.strip().lower() for a in apps_raw.split(",") if a.strip()]
    set_user_pref("primary_apps", ",".join(apps))

    # Apps that should never be killed
    protected_raw = ask(
        "Which apps should NEVER be killed or suspended?\nExample: vscode, firefox"
    )
    protected = [a.strip().lower() for a in protected_raw.split(",") if a.strip()]
    set_user_pref("user_protected_apps", ",".join(protected))

    # Autonomy level
    autonomy = ask(
        "How aggressive should the AI be?",
        AUTONOMY_LEVELS
    )
    set_user_pref("autonomy_level", autonomy)

    # Power source
    power = ask(
        "Are you usually on AC power or battery?",
        ["ac", "battery", "both"]
    )
    set_user_pref("power_preference", power)

    # Network priority app
    net_primary = ask(
        "Which app needs network priority? (leave blank to skip)"
    )
    if net_primary:
        set_user_pref("network_priority_app", net_primary.lower())
        net_impact = ask(
            "How much can other apps be affected during network contention?",
            ["low", "medium", "high"]
        )
        set_user_pref("network_impact_tolerance", net_impact)

    # Idle threshold
    idle_minutes = ask(
        "After how many minutes of no input should the system be considered idle?",
        ["2", "5", "10", "15"]
    )
    set_user_pref("idle_threshold_minutes", idle_minutes)

    # Seed bootstrap profiles from answers
    seed_profiles(primary_use, apps)

    print("\n" + "=" * 50)
    print("Setup complete - AIOS is ready")
    print("=" * 50)

def seed_profiles(primary_use, apps):
    # Seed basic profiles based on quiz answers
    # These get refined by observation over time
    defaults = {
        "gaming": {
            "cpu_avg": 60.0, "ram_avg_mb": 4000.0,
            "gpu_avg": 80.0, "disk_read_avg_mb": 10.0,
            "disk_write_avg_mb": 5.0
        },
        "dev": {
            "cpu_avg": 40.0, "ram_avg_mb": 3000.0,
            "gpu_avg": 5.0, "disk_read_avg_mb": 50.0,
            "disk_write_avg_mb": 30.0
        },
        "browsing": {
            "cpu_avg": 20.0, "ram_avg_mb": 2000.0,
            "gpu_avg": 10.0, "disk_read_avg_mb": 5.0,
            "disk_write_avg_mb": 2.0
        }
    }

    for app in apps:
        # Seed profile for each app in the mode that matches primary use
        mode = primary_use if primary_use != "mixed" else "browsing"
        metrics = defaults.get(mode, defaults["browsing"])
        upsert_app_profile(app, mode, metrics)

    print(f"\nSeeded profiles for: {', '.join(apps)}")

if __name__ == "__main__":
    run()