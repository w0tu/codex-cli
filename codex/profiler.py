"""Hardware Profiler & First-Boot Onboarding.

Benchmarking host CPU, RAM, and GPU.
Executes an unbuffered 32-token benchmark test against available local Ollama models
to record real-time Tokens Per Second (TPS).
Automatically recommends and selects the optimal local coding model.
Configures isolated code syntax themes ([1] Dark, [2] Light, [3] High Contrast).
"""

import os
import sys
import json
import time
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None

CONFIG_DIR = Path.home() / ".config" / "codex_cli"
PROFILE_FILE = CONFIG_DIR / "hardware_profile.json"
CONFIG_FILE = CONFIG_DIR / "config.json"
OLLAMA_API = "http://127.0.0.1:11434"

CODE_THEMES = {
    "1": ("Dark Mode", "monokai"),
    "2": ("Light Mode", "friendly"),
    "3": ("High Contrast", "native"),
}


def get_cpu_info() -> Dict[str, Any]:
    """Retrieve host CPU specifications."""
    cores_physical = psutil.cpu_count(logical=False) if psutil else (os.cpu_count() or 2)
    cores_logical = psutil.cpu_count(logical=True) if psutil else (os.cpu_count() or 4)
    freq = psutil.cpu_freq() if psutil and hasattr(psutil, "cpu_freq") else None
    max_mhz = f"{freq.max:.0f}MHz" if freq and freq.max else "2.4GHz"

    model_name = platform.processor() or "x86_64 Processor"
    if Path("/proc/cpuinfo").exists():
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if "model name" in line:
                    model_name = line.split(":", 1)[1].strip()
                    break
        except Exception:
            pass

    return {
        "model": model_name,
        "physical_cores": cores_physical or 2,
        "logical_cores": cores_logical or 4,
        "freq": max_mhz,
    }


def get_ram_info() -> Dict[str, Any]:
    """Retrieve host RAM statistics."""
    if psutil:
        vm = psutil.virtual_memory()
        total_gb = vm.total / (1024 ** 3)
        avail_gb = vm.available / (1024 ** 3)
        pct = vm.percent
    else:
        total_gb, avail_gb, pct = 8.0, 4.0, 50.0
        if Path("/proc/meminfo").exists():
            try:
                meminfo = Path("/proc/meminfo").read_text()
                for line in meminfo.splitlines():
                    if line.startswith("MemTotal:"):
                        total_gb = int(line.split()[1]) / (1024 * 1024)
                    elif line.startswith("MemAvailable:"):
                        avail_gb = int(line.split()[1]) / (1024 * 1024)
                pct = round(100.0 * (1.0 - (avail_gb / total_gb)), 1)
            except Exception:
                pass

    return {
        "total_gb": round(total_gb, 2),
        "available_gb": round(avail_gb, 2),
        "percent_used": pct,
    }


def get_gpu_info() -> Dict[str, Any]:
    """Check for NVIDIA, AMD, or integrated GPU hardware."""
    # Check nvidia-smi
    if shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                gpu_line = res.stdout.strip().splitlines()[0]
                parts = [p.strip() for p in gpu_line.split(",")]
                return {
                    "has_gpu": True,
                    "type": "NVIDIA",
                    "name": parts[0],
                    "total_vram": parts[1] if len(parts) > 1 else "Unknown",
                    "free_vram": parts[2] if len(parts) > 2 else "Unknown",
                }
        except Exception:
            pass

    # Check lspci or sysfs
    try:
        if Path("/sys/class/drm").exists():
            cards = list(Path("/sys/class/drm").glob("card*"))
            if cards:
                return {
                    "has_gpu": True,
                    "type": "Integrated / PCI Accelerator",
                    "name": "Hardware Accelerated Graphics DRM",
                    "total_vram": "Host Unified Memory",
                    "free_vram": "Dynamic",
                }
    except Exception:
        pass

    return {
        "has_gpu": False,
        "type": "None",
        "name": "CPU Acceleration (AVX2/AVX512)",
        "total_vram": "0 MB",
        "free_vram": "0 MB",
    }


def get_installed_ollama_models() -> List[str]:
    """Fetch all installed models from local Ollama instance."""
    import httpx
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{OLLAMA_API}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
    except Exception:
        pass
    return []


def benchmark_model_tps(model_name: str, num_tokens: int = 32) -> Tuple[float, float]:
    """Run an unbuffered 32-token test against Ollama model to record real-time TPS.
    
    Returns:
        (real_time_tps, wall_clock_seconds)
    """
    import httpx
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Write a 20-word python code snippet."}],
        "stream": False,
        "keep_alive": -1,  # Keep pinned in RAM/VRAM
        "options": {
            "num_predict": num_tokens,
            "temperature": 0.0,
        },
    }
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(f"{OLLAMA_API}/api/chat", json=payload)
            elapsed = time.perf_counter() - t0
            if resp.status_code == 200:
                data = resp.json()
                eval_count = data.get("eval_count", 0)
                eval_dur_ns = data.get("eval_duration", 0)
                if eval_dur_ns > 0:
                    real_time_tps = eval_count / (eval_dur_ns / 1e9)
                else:
                    real_time_tps = eval_count / max(0.001, elapsed)
                return round(real_time_tps, 2), round(elapsed, 3)
    except Exception:
        pass
    return 0.0, 0.0


def select_best_local_model(candidates: List[Dict[str, Any]]) -> str:
    """Recommend and pick the optimal coding model based on TPS and capability."""
    if not candidates:
        return "qwen2.5-coder:1.5b"

    # Prioritize coder-tuned models with acceptable TPS (>10 TPS preferred)
    coding_models = [c for c in candidates if "coder" in c["name"].lower()]
    if coding_models:
        # Sort by TPS descending
        coding_models.sort(key=lambda x: x["tps"], reverse=True)
        return coding_models[0]["name"]

    candidates.sort(key=lambda x: x["tps"], reverse=True)
    return candidates[0]["name"]


def run_first_boot_profiling(interactive: bool = True, force: bool = False) -> Dict[str, Any]:
    """Run complete hardware profiling and onboarding setup."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not force and PROFILE_FILE.exists():
        try:
            return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    sys.stdout.write("\033[1;36m[ONBOARDING] Initializing Codex-CLI Hardware Profiler & Benchmark...\033[0m\n")
    sys.stdout.flush()

    cpu = get_cpu_info()
    ram = get_ram_info()
    gpu = get_gpu_info()

    sys.stdout.write(f"▌ CPU: {cpu['model']} ({cpu['physical_cores']}C/{cpu['logical_cores']}T @ {cpu['freq']})\n")
    sys.stdout.write(f"▌ RAM: {ram['total_gb']} GB total ({ram['available_gb']} GB available)\n")
    sys.stdout.write(f"▌ GPU: {gpu['name']} ({gpu['total_vram']})\n\n")
    sys.stdout.flush()

    # Discover and benchmark Ollama models
    installed_models = get_installed_ollama_models()
    benchmark_results: List[Dict[str, Any]] = []

    if installed_models:
        sys.stdout.write("\033[1;37mRunning unbuffered 32-token TPS benchmark on available Ollama engines...\033[0m\n")
        sys.stdout.flush()
        
        # Test candidate small models suitable for 1B/3B fast inference
        test_candidates = [
            m for m in installed_models
            if any(k in m for k in ["coder", "qwen", "llama", "smollm"])
        ][:4]

        if not test_candidates:
            test_candidates = installed_models[:3]

        for m in test_candidates:
            sys.stdout.write(f"  • Benchmarking \033[1;33m{m}\033[0m... ")
            sys.stdout.flush()
            tps, duration = benchmark_model_tps(m, num_tokens=32)
            if tps > 0:
                sys.stdout.write(f"\033[1;32m{tps:.1f} TPS\033[0m ({duration:.2f}s)\n")
                benchmark_results.append({"name": m, "tps": tps, "duration": duration})
            else:
                sys.stdout.write("\033[1;31mUnavailable/Timeout\033[0m\n")
            sys.stdout.flush()
    else:
        sys.stdout.write("\033[1;33m⚠ Local Ollama daemon unreachable at 127.0.0.1:11434. Defaulting to qwen2.5-coder:1.5b.\033[0m\n")

    recommended_model = select_best_local_model(benchmark_results)
    sys.stdout.write(f"\n\033[1;32m✓ Recommended primary local engine: \033[1;37m{recommended_model}\033[0m\n\n")
    sys.stdout.flush()

    # Code Theme Selection
    selected_theme_key = "1"
    if interactive and sys.stdin.isatty():
        sys.stdout.write("\033[1;37mSelect Isolated Code Syntax Theme (applies strictly to code blocks):\033[0m\n")
        sys.stdout.write("  [1] Dark Mode (Monokai)\n")
        sys.stdout.write("  [2] Light Mode (Friendly)\n")
        sys.stdout.write("  [3] High Contrast (Native)\n")
        sys.stdout.write("Choice [1-3] (default: 1): ")
        sys.stdout.flush()
        try:
            choice = sys.stdin.readline().strip()
            if choice in CODE_THEMES:
                selected_theme_key = choice
        except Exception:
            pass

    theme_name, pygments_style = CODE_THEMES.get(selected_theme_key, CODE_THEMES["1"])
    sys.stdout.write(f"\033[1;32m✓ Code syntax theme set to: {theme_name}\033[0m\n\n")
    sys.stdout.flush()

    profile_data = {
        "timestamp": time.time(),
        "cpu": cpu,
        "ram": ram,
        "gpu": gpu,
        "recommended_model": recommended_model,
        "benchmark_results": benchmark_results,
        "code_theme": {
            "key": selected_theme_key,
            "name": theme_name,
            "pygments_style": pygments_style,
        },
    }

    try:
        PROFILE_FILE.write_text(json.dumps(profile_data, indent=2), encoding="utf-8")
        
        # Save to main config as well
        config_data = {}
        if CONFIG_FILE.exists():
            try:
                config_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        config_data["local_model"] = recommended_model
        config_data["code_theme"] = pygments_style
        CONFIG_FILE.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    except Exception:
        pass

    return profile_data


def get_active_code_theme_style() -> str:
    """Retrieve Pygments style strictly for code block rendering."""
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return cfg.get("code_theme", "monokai")
        except Exception:
            pass
    return "monokai"
