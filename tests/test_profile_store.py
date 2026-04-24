import sys
import os
import tempfile
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

# Use temp db for tests
os.environ["AIOS_PROFILES_DIR"] = tempfile.mkdtemp()

from profile_store import init_db, upsert_app_profile, get_app_profile, set_user_pref, get_user_pref

def test_init_db():
    init_db()
    print("test_init_db passed")

def test_upsert_and_get_profile():
    init_db()
    metrics = {
        "cpu_avg": 50.0,
        "ram_avg_mb": 2000.0,
        "gpu_avg": 30.0,
        "disk_read_avg_mb": 10.0,
        "disk_write_avg_mb": 5.0
    }
    upsert_app_profile("firefox", "browsing", metrics)
    profile = get_app_profile("firefox", "browsing")
    assert profile is not None
    print("test_upsert_and_get_profile passed")

def test_user_pref():
    init_db()
    set_user_pref("test_key", "test_value")
    value = get_user_pref("test_key")
    assert value == "test_value"
    print("test_user_pref passed")

def test_profile_rolling_average():
    init_db()
    metrics1 = {"cpu_avg": 40.0, "ram_avg_mb": 1000.0, "gpu_avg": 0.0,
                "disk_read_avg_mb": 0.0, "disk_write_avg_mb": 0.0}
    metrics2 = {"cpu_avg": 60.0, "ram_avg_mb": 3000.0, "gpu_avg": 0.0,
                "disk_read_avg_mb": 0.0, "disk_write_avg_mb": 0.0}
    upsert_app_profile("vscode", "dev", metrics1)
    upsert_app_profile("vscode", "dev", metrics2)
    profile = get_app_profile("vscode", "dev")
    # Average of 40 and 60 should be 50
    assert profile[3] == 50.0, f"Expected 50.0 got {profile[3]}"
    print("test_profile_rolling_average passed")

if __name__ == "__main__":
    test_init_db()
    test_upsert_and_get_profile()
    test_user_pref()
    test_profile_rolling_average()
    print("All profile store tests passed")