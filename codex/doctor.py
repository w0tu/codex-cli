"""Diagnostic system health checks for Codex (codex doctor)."""

import os
import shutil
import subprocess
import platform
import time
from pathlib import Path
from typing import Any

from codex.config import DEFAULT_CONFIG_PATH, load_config, verify_api_key


def check_diagnostics(model: str = "qwen/qwen3.8-27b", config_path: Path | None = None) -> list[dict[str, str]]:
    """Run all Phase 1 diagnostic checks and return structured results."""
    results = []

    # 1. Python Environment
    py_ver = platform.python_version()
    results.append({
        "component": "Python Runtime",
        "status": "OK",
        "details": f"v{py_ver} ({platform.python_implementation()})",
    })

    # 2. Operating System
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    results.append({
        "component": "Operating System",
        "status": "OK",
        "details": os_info,
    })

    # 3. Git Repository & Working Tree
    git_cmd = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if git_cmd.returncode == 0:
        lines = [l for l in git_cmd.stdout.splitlines() if l.strip()]
        tree_status = f"Indexed ({len(lines)} uncommitted changes)" if lines else "Clean working tree"
        results.append({
            "component": "Git Repository",
            "status": "OK",
            "details": tree_status,
        })
    else:
        results.append({
            "component": "Git Repository",
            "status": "WARNING",
            "details": "Not a git repository (or git CLI missing)",
        })

    # 4. Terminal Geometry & UTF-8 / Color
    cols, rows = shutil.get_terminal_size()
    colorterm = os.environ.get("COLORTERM", "256color")
    results.append({
        "component": "Terminal Display",
        "status": "OK",
        "details": f"{cols}x{rows} cols/rows | UTF-8 | {colorterm}",
    })

    # 5. Workspace Permissions
    cwd = os.getcwd()
    writable = os.access(cwd, os.W_OK)
    results.append({
        "component": "Workspace Path",
        "status": "OK" if writable else "READ-ONLY",
        "details": f"{cwd} ({'Writable' if writable else 'Read-Only'})",
    })

    # 6. Ripgrep binary
    rg_path = shutil.which("rg")
    results.append({
        "component": "Ripgrep Engine",
        "status": "OK" if rg_path else "OPTIONAL",
        "details": rg_path or "Not found (using Python native grep search)",
    })

    # 7. Configuration & Auth Lifecycle
    cfg_file = config_path or DEFAULT_CONFIG_PATH
    if cfg_file.exists():
        cfg = load_config(cfg_file)
        active_key = cfg.get("api_key", "").strip()
        backups = cfg.get("backup_keys", [])
        if active_key:
            masked = active_key[:7] + "****" + active_key[-4:]
            results.append({
                "component": "Config File",
                "status": "OK",
                "details": f"{cfg_file} ({masked}, {len(backups)} backup keys)",
            })

            # 8. API Reachability Probe Ping
            valid, msg, latency = verify_api_key(active_key)
            results.append({
                "component": "API Reachability",
                "status": "OK" if valid else "FAILED",
                "details": f"{msg} | {latency:.1f}ms latency",
            })
        else:
            results.append({
                "component": "Config File",
                "status": "WARNING",
                "details": f"{cfg_file} (No active API key set)",
            })
            results.append({
                "component": "API Reachability",
                "status": "SKIPPED",
                "details": "No API key configured",
            })
    else:
        results.append({
            "component": "Config File",
            "status": "MISSING",
            "details": f"{cfg_file} does not exist",
        })
        results.append({
            "component": "API Reachability",
            "status": "SKIPPED",
            "details": "Run /onboard or cdx to configure key",
        })

    # 9. Active AI Model
    results.append({
        "component": "Inference Model",
        "status": "READY",
        "details": model,
    })

    return results
