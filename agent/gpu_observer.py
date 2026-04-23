import subprocess
import json

def get_amd_gpu() -> dict:
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showuse", "--showmeminfo", "vram", "--json"],
            timeout=5
        )
        data = json.loads(out)
        card = list(data.keys())[0]
        return {
            "type": "amd",
            "utilisation_pct": float(data[card].get("GPU use (%)", 0)),
            "vram_used_mb": float(data[card].get("VRAM Total Used Memory (B)", 0)) / 1e6,
            "vram_total_mb": float(data[card].get("VRAM Total Memory (B)", 0)) / 1e6
        }
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def get_nvidia_gpu() -> dict:
    try:
        out = subprocess.check_output([
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits"
        ], timeout=5).decode().strip()

        parts = out.split(",")
        return {
            "type": "nvidia",
            "utilisation_pct": float(parts[0].strip()),
            "vram_used_mb": float(parts[1].strip()),
            "vram_total_mb": float(parts[2].strip())
        }
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def get_integrated_gpu() -> dict:
    # Intel and AMD integrated via sysfs
    try:
        with open("/sys/class/drm/card0/device/gpu_busy_percent") as f:
            usage = float(f.read().strip())
        return {
            "type": "integrated",
            "utilisation_pct": usage,
            "vram_used_mb": 0,
            "vram_total_mb": 0
        }
    except:
        return {}

def get_gpu() -> dict:
    # Try discrete first then integrated
    gpu = get_amd_gpu()
    if gpu:
        return gpu

    gpu = get_nvidia_gpu()
    if gpu:
        return gpu

    gpu = get_integrated_gpu()
    if gpu:
        return gpu

    # No GPU detected
    return {
        "type": "none",
        "utilisation_pct": 0,
        "vram_used_mb": 0,
        "vram_total_mb": 0
    }