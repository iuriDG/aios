import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

from decision_engine import get_gear, deduplicate, is_protected

def test_gear_low():
    snapshot = {
        "cpu": {"percent_total": 20},
        "ram": {"used_pct": 30},
        "gpu": {"utilisation_pct": 10}
    }
    assert get_gear(snapshot) == "low"
    print("test_gear_low passed")

def test_gear_medium():
    snapshot = {
        "cpu": {"percent_total": 60},
        "ram": {"used_pct": 50},
        "gpu": {"utilisation_pct": 40}
    }
    assert get_gear(snapshot) == "medium"
    print("test_gear_medium passed")

def test_gear_heavy():
    snapshot = {
        "cpu": {"percent_total": 90},
        "ram": {"used_pct": 85},
        "gpu": {"utilisation_pct": 80}
    }
    assert get_gear(snapshot) == "heavy"
    print("test_gear_heavy passed")

def test_deduplicate():
    actions = [
        {"action": "renice", "pid": 123, "priority": 10},
        {"action": "renice", "pid": 123, "priority": 10},
        {"action": "renice", "pid": 456, "priority": 5},
    ]
    result = deduplicate(actions)
    assert len(result) == 2
    print("test_deduplicate passed")

def test_protected_process():
    assert is_protected("systemd") == True
    assert is_protected("firefox") == False
    assert is_protected("sshd") == True
    print("test_protected_process passed")

if __name__ == "__main__":
    test_gear_low()
    test_gear_medium()
    test_gear_heavy()
    test_deduplicate()
    test_protected_process()
    print("All decision engine tests passed")