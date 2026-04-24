import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

from observer import observe, get_processes

def test_observe_returns_required_keys():
    snapshot = observe()
    assert "cpu" in snapshot
    assert "ram" in snapshot
    assert "disk" in snapshot
    assert "network" in snapshot
    assert "gpu" in snapshot
    assert "processes" in snapshot
    print("test_observe_returns_required_keys passed")

def test_processes_list_not_empty():
    procs = get_processes()
    assert len(procs) > 0
    print("test_processes_list_not_empty passed")

def test_process_has_required_fields():
    procs = get_processes()
    for p in procs:
        assert "pid" in p
        assert "name" in p
        assert "cpu_pct" in p
        assert "ram_mb" in p
        assert "status" in p
    print("test_process_has_required_fields passed")

if __name__ == "__main__":
    test_observe_returns_required_keys()
    test_processes_list_not_empty()
    test_process_has_required_fields()
    print("All observer tests passed")