"""Desktop Application Launcher for The Codex Group.

Spawns the local backend API and launches a borderless, native desktop window:
- Binds to http://127.0.0.1:4545
- Spawns google-chrome in standalone application mode (--app)
- Falls back to chromium, firefox, or system default browser via xdg-open
- Gracefully handles shutdown when window closes
"""

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from aiohttp import web
from codex.app import create_app

PORT = 4545
APP_URL = f"http://127.0.0.1:{PORT}"
USER_DATA_DIR = Path.home() / ".codex" / "chrome_app_profile"


def is_port_in_use(port: int) -> bool:
    """Check if the desktop backend port is already open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_server():
    """Run aiohttp server in a dedicated event loop thread."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = create_app()
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, "127.0.0.1", PORT)
    loop.run_until_complete(site.start())
    loop.run_forever()


def wait_for_server(timeout: float = 8.0) -> bool:
    """Wait until server responds to health check."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{APP_URL}/api/status")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def find_browser_cmd() -> list[str]:
    """Find the best available browser executable for standalone app mode."""
    chrome_bin = shutil.which("google-chrome") or "/usr/bin/google-chrome"
    chromium_bin = shutil.which("chromium") or "/usr/bin/chromium"
    firefox_bin = shutil.which("firefox") or "/usr/bin/firefox"
    xdg_bin = shutil.which("xdg-open") or "/usr/bin/xdg-open"

    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if os.path.exists(chrome_bin):
        return [
            chrome_bin,
            f"--app={APP_URL}",
            f"--user-data-dir={USER_DATA_DIR}",
            "--window-size=1360,860",
            "--class=TheCodexGroup",
            "--no-first-run",
            "--no-default-browser-check"
        ]

    if os.path.exists(chromium_bin):
        return [
            chromium_bin,
            f"--app={APP_URL}",
            f"--user-data-dir={USER_DATA_DIR}",
            "--window-size=1360,860",
            "--class=TheCodexGroup",
            "--no-first-run",
            "--no-default-browser-check"
        ]

    if os.path.exists(firefox_bin):
        return [firefox_bin, "--new-window", APP_URL]

    if os.path.exists(xdg_bin):
        return [xdg_bin, APP_URL]

    return []


def launch_desktop_app(detach: bool = False):
    """Start server and launch standalone desktop application window."""
    # 1. Start server if not already running
    if not is_port_in_use(PORT):
        print(f"\033[1;34m[Codex Desktop]\033[0m Starting backend services on {APP_URL}...")
        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        if not wait_for_server():
            print("\033[1;31m[Codex Desktop Error]\033[0m Failed to start backend server.", file=sys.stderr)
            sys.exit(1)
        print(f"\033[1;32m[Codex Desktop]\033[0m Backend online.")
    else:
        print(f"\033[1;32m[Codex Desktop]\033[0m Connecting to active backend on {APP_URL}.")

    # 2. Launch browser app window
    cmd = find_browser_cmd()
    if not cmd:
        print(f"\033[1;31m[Error]\033[0m No suitable desktop browser found. Please open {APP_URL} manually.", file=sys.stderr)
        sys.exit(1)

    print(f"\033[1;34m[Codex Desktop]\033[0m Launching desktop window ({cmd[0]})...")
    
    if detach:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"\033[1;32m[Codex Desktop]\033[0m App running independently.")
    else:
        try:
            proc = subprocess.run(cmd)
            sys.exit(proc.returncode)
        except KeyboardInterrupt:
            print("\n\033[1;33m[Codex Desktop]\033[0m Window closed.")


if __name__ == "__main__":
    launch_desktop_app(detach="--detach" in sys.argv)
