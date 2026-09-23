"""Network and WiFi inspection, connection, and deep internet research module for Codex CLI."""

import os
import shutil
import subprocess
import urllib.request
from typing import Any


def check_wifi_status() -> dict[str, Any]:
    """Inspect local WiFi connection, signal strength, IP address, and internet gateway connectivity."""
    info: dict[str, Any] = {
        "connected": False,
        "ssid": "Offline / Disconnected",
        "interface": "wlan0",
        "signal": 0,
        "ip": "127.0.0.1",
        "internet": False,
        "mode": "Client"
    }

    # 1. Inspect nmcli WiFi status
    nmcli_bin = shutil.which("nmcli") or "/usr/bin/nmcli"
    if os.path.exists(nmcli_bin):
        try:
            proc = subprocess.run(
                [nmcli_bin, "-t", "-f", "ACTIVE,SSID,SIGNAL,DEVICE", "dev", "wifi"],
                capture_output=True,
                text=True,
                timeout=4
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 4 and parts[0].lower() == "yes":
                        info["connected"] = True
                        info["ssid"] = parts[1] or "Unknown Network"
                        info["signal"] = int(parts[2]) if parts[2].isdigit() else 80
                        info["interface"] = parts[3] or "wlan0"
                        break
        except Exception:
            pass

    # 2. Inspect Local IP
    try:
        proc_ip = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=2)
        ips = proc_ip.stdout.strip().split()
        if ips:
            info["ip"] = ips[0]
            info["connected"] = True
    except Exception:
        pass

    # 3. Quick Internet Gateway Verification
    try:
        req = urllib.request.Request("https://www.google.com", headers={"User-Agent": "Codex-CLI/1.7.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                info["internet"] = True
    except Exception:
        pass

    return info


def connect_wifi(ssid: str, password: str | None = None) -> str:
    """Connect to a WiFi network using nmcli."""
    nmcli_bin = shutil.which("nmcli") or "/usr/bin/nmcli"
    if not os.path.exists(nmcli_bin):
        return "Error: nmcli command not found on this system."

    cmd = [nmcli_bin, "dev", "wifi", "connect", ssid]
    if password:
        cmd.extend(["password", password])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if proc.returncode == 0:
            return f"Successfully connected to WiFi network '{ssid}'."
        return f"Failed to connect to '{ssid}': {proc.stderr.strip() or proc.stdout.strip()}"
    except Exception as e:
        return f"WiFi connection error: {e}"


def run_deep_research(query: str, max_results: int = 5) -> str:
    """Conduct multi-source deep internet research using free online APIs and Agent Reach."""
    from codex.tools import execute_agent_reach, execute_web_search

    findings: list[str] = [f"# Deep Research Report: {query}\n"]

    # 1. Query Web Search
    try:
        web_res = execute_web_search(query)
        if web_res and not web_res.startswith("Error"):
            findings.append("### Live Web Search Insights:\n" + web_res[:1500] + "\n")
    except Exception:
        pass

    # 2. Query Agent Reach
    try:
        reach_res = execute_agent_reach(action="search", query=query)
        if reach_res and not reach_res.startswith("Error"):
            findings.append("### Multi-Platform Community Discussion (Agent Reach):\n" + reach_res[:1500] + "\n")
    except Exception:
        pass

    if len(findings) == 1:
        # Fallback to wikipedia / ddg summary
        from codex.tools import execute_online_info
        info_res = execute_online_info(query)
        findings.append("### Encyclopedia Summary:\n" + info_res + "\n")

    return "\n---\n".join(findings)
