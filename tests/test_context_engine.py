import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

from context_engine import classify

GAMING_SNAPSHOT = {
    "cpu": {"percent_total": 60},
    "gpu": {"utilisation_pct": 80},
    "processes": [
        {"name": "steam", "cpu_pct": 40, "ram_mb": 2000},
        {"name": "firefox", "cpu_pct": 5, "ram_mb": 300},
    ]
}

DEV_SNAPSHOT = {
    "cpu": {"percent_total": 70},
    "gpu": {"utilisation_pct": 5},
    "processes": [
        {"name": "cargo", "cpu_pct": 60, "ram_mb": 1000},
        {"name": "code", "cpu_pct": 10, "ram_mb": 500},
    ]
}

BROWSING_SNAPSHOT = {
    "cpu": {"percent_total": 20},
    "gpu": {"utilisation_pct": 5},
    "processes": [
        {"name": "firefox", "cpu_pct": 15, "ram_mb": 800},
        {"name": "code", "cpu_pct": 2, "ram_mb": 200},
    ]
}

IDLE_SNAPSHOT = {
    "cpu": {"percent_total": 2},
    "gpu": {"utilisation_pct": 0},
    "processes": []
}

def test_gaming_detected():
    result = classify(GAMING_SNAPSHOT)
    assert result["mode"] == "gaming", f"Expected gaming got {result['mode']}"
    print("test_gaming_detected passed")

def test_dev_detected():
    result = classify(DEV_SNAPSHOT)
    assert result["mode"] == "dev", f"Expected dev got {result['mode']}"
    print("test_dev_detected passed")

def test_browsing_detected():
    result = classify(BROWSING_SNAPSHOT)
    assert result["mode"] == "browsing", f"Expected browsing got {result['mode']}"
    print("test_browsing_detected passed")

def test_idle_detected():
    result = classify(IDLE_SNAPSHOT)
    assert result["mode"] == "idle", f"Expected idle got {result['mode']}"
    print("test_idle_detected passed")

def test_result_has_required_fields():
    result = classify(GAMING_SNAPSHOT)
    assert "mode" in result
    assert "confidence" in result
    assert "scores" in result
    assert "top_cpu_process" in result
    print("test_result_has_required_fields passed")

if __name__ == "__main__":
    test_gaming_detected()
    test_dev_detected()
    test_browsing_detected()
    test_idle_detected()
    test_result_has_required_fields()
    print("All context engine tests passed")