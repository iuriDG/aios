import sys
import os
import time
import subprocess
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

from profile_store import set_user_pref
from config import OLLAMA_URL, OLLAMA_MODEL

TEST_PROMPT = "List 5 Linux process names. Reply in JSON array only."

def benchmark_cpu_inference() -> float:
    import requests
    start = time.time()
    try:
        requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": TEST_PROMPT,
            "stream": False,
            "options": {"num_gpu": 0}  # Force CPU
        }, timeout=60)
        return time.time() - start
    except Exception as e:
        print(f"CPU benchmark failed: {e}")
        return 999.0

def benchmark_gpu_inference() -> float:
    import requests
    start = time.time()
    try:
        requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": TEST_PROMPT,
            "stream": False,
            "options": {"num_gpu": 99}  # Force GPU
        }, timeout=60)
        return time.time() - start
    except Exception as e:
        print(f"GPU benchmark failed: {e}")
        return 999.0

def get_cpu_info() -> dict:
    try:
        import psutil
        return {
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
            "freq_max_mhz": psutil.cpu_freq().max if psutil.cpu_freq() else 0
        }
    except:
        return {}

def get_gpu_info() -> dict:
    # Try ROCm for AMD
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showmeminfo", "vram", "--json"],
            timeout=5
        )
        import json
        data = json.loads(out)
        return {"type": "amd_rocm", "data": data}
    except:
        pass

    # Try nvidia-smi
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader"],
            timeout=5
        )
        return {"type": "nvidia", "data": out.decode().strip()}
    except:
        pass

    return {"type": "integrated_or_unknown"}

def run():
    print("=" * 50)
    print("AIOS Hardware Benchmark")
    print("=" * 50)

    # CPU info
    cpu = get_cpu_info()
    print(f"\nCPU: {cpu.get('cores_physical')} physical cores "
          f"/ {cpu.get('cores_logical')} logical "
          f"/ {cpu.get('freq_max_mhz')} MHz max")
    set_user_pref("hw_cpu_cores_physical", str(cpu.get("cores_physical", 1)))
    set_user_pref("hw_cpu_cores_logical", str(cpu.get("cores_logical", 1)))
    set_user_pref("hw_cpu_freq_max", str(cpu.get("freq_max_mhz", 0)))

    # GPU info
    gpu = get_gpu_info()
    print(f"GPU: {gpu.get('type')}")
    set_user_pref("hw_gpu_type", gpu.get("type", "unknown"))

    # Inference benchmark
    print("\nBenchmarking CPU inference...")
    cpu_time = benchmark_cpu_inference()
    print(f"CPU inference time: {cpu_time:.2f}s")
    set_user_pref("hw_cpu_inference_secs", str(round(cpu_time, 3)))

    print("Benchmarking GPU inference...")
    gpu_time = benchmark_gpu_inference()
    print(f"GPU inference time: {gpu_time:.2f}s")
    set_user_pref("hw_gpu_inference_secs", str(round(gpu_time, 3)))

    # Calculate weights for load arbiter
    # Faster pool gets lower weight - it has more headroom
    total = cpu_time + gpu_time
    cpu_weight = round(cpu_time / total, 3) if total > 0 else 1.0
    gpu_weight = round(gpu_time / total, 3) if total > 0 else 1.0

    set_user_pref("hw_weight_cpu", str(cpu_weight))
    set_user_pref("hw_weight_gpu", str(gpu_weight))
    set_user_pref("hw_weight_ram", "1.0")  # RAM weight is fixed

    print(f"\nLoad arbiter weights:")
    print(f"  CPU weight: {cpu_weight}")
    print(f"  GPU weight: {gpu_weight}")
    print(f"  Faster pool: {'GPU' if gpu_time < cpu_time else 'CPU'}")
    print("\nBenchmark complete")

if __name__ == "__main__":
    run()