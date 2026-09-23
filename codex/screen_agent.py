"""Visual Screen Reader, Window Manager, and Floating Agent Mouse Controller for Linux Desktop."""

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Optional


class DesktopWindowManager:
    """Manages window state, active apps, and real-time screen inspection on Linux X11."""

    def __init__(self):
        self.xdotool = shutil.which("xdotool") or "/usr/bin/xdotool"
        self.ffmpeg_bin = shutil.which("ffmpeg") or os.path.expanduser("~/.local/bin/ffmpeg")
        self.capture_dir = Path.home() / ".cache" / "codex_cli" / "screen_frames"
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    def minimize_active_window(self) -> dict[str, Any]:
        """Minimize currently focused window."""
        if not os.path.exists(self.xdotool):
            return {"success": False, "message": "xdotool not found"}
        env = os.environ.copy()
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":0"
        try:
            res = subprocess.run([self.xdotool, "getactivewindow", "windowminimize"], env=env, capture_output=True, text=True, timeout=3)
            return {"success": res.returncode == 0, "message": "Active window minimized to desktop"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def open_browser(self, url: str = "https://console.groq.com/keys") -> dict[str, Any]:
        """Launch browser and bring to focus."""
        browser_bins = ["google-chrome", "google-chrome-stable", "chromium", "firefox", "x-www-browser"]
        target = None
        for b in browser_bins:
            path = shutil.which(b)
            if path:
                target = path
                break
        if not target:
            target = "xdg-open"

        env = os.environ.copy()
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":0"

        try:
            subprocess.Popen([target, url], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            if os.path.exists(self.xdotool):
                subprocess.run([self.xdotool, "search", "--onlyvisible", "--class", "chrome", "windowactivate"], env=env, capture_output=True, timeout=2)
            return {"success": True, "message": f"Browser opened to {url}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def capture_screen_frame(self) -> dict[str, Any]:
        """Capture live screenshot frame of desktop using hardware-accelerated ffmpeg x11grab."""
        frame_path = self.capture_dir / "live_screen.png"
        env = os.environ.copy()
        disp = env.get("DISPLAY", ":0")

        # Get screen geometry
        geom = "3072x1728"
        try:
            if os.path.exists(self.xdotool):
                g_proc = subprocess.run([self.xdotool, "getdisplaygeometry"], env=env, capture_output=True, text=True, timeout=2)
                if g_proc.returncode == 0 and g_proc.stdout.strip():
                    parts = g_proc.stdout.strip().split()
                    if len(parts) >= 2:
                        geom = f"{parts[0]}x{parts[1]}"
        except Exception:
            pass

        if os.path.exists(self.ffmpeg_bin):
            try:
                cmd = [
                    self.ffmpeg_bin, "-y", "-f", "x11grab",
                    "-video_size", geom, "-i", f"{disp}.0",
                    "-vframes", "1", str(frame_path)
                ]
                proc = subprocess.run(cmd, env=env, capture_output=True, timeout=3)
                if proc.returncode == 0 and frame_path.exists():
                    return {"success": True, "path": str(frame_path), "size": frame_path.stat().st_size, "geometry": geom}
            except Exception as e:
                return {"success": False, "message": str(e)}

        return {"success": False, "message": "Screen capture tools unavailable or headless"}


class FloatingAgentPointer:
    """Spawns an interactive second agent mouse cursor overlay on the user's desktop."""

    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None

    def spawn(self, start_x: int = 1536, start_y: int = 864) -> bool:
        """Launch floating agent cursor indicator overlay in background."""
        if self.proc and self.proc.poll() is None:
            return True

        env = os.environ.copy()
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":0"

        script = f"""
import tkinter as tk
root = tk.Tk()
root.overrideredirect(True)
root.attributes('-topmost', True)
root.geometry('36x36+{start_x}+{start_y}')
root.configure(bg='black')
root.attributes('-alpha', 0.90)
canvas = tk.Canvas(root, width=36, height=36, bg='#1a1b26', highlightthickness=1, highlightbackground='#7dcfff')
canvas.pack()
# Draw stylish agent mouse cursor
canvas.create_polygon(4, 4, 28, 14, 18, 20, 24, 30, 19, 32, 13, 22, 4, 28, fill='#7aa2f7', outline='#bb9af7', width=2)
root.after(10000, root.destroy)
root.mainloop()
"""
        try:
            self.proc = subprocess.Popen(["python3", "-c", script], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def glide_to(self, target_x: int = 960, target_y: int = 540, badge: str = "", click: bool = False) -> bool:
        """Glide floating cursor overlay to target coordinates."""
        self.spawn(target_x, target_y)
        if click:
            try:
                from codex.mouse_agent import mouse_controller
                mouse_controller.move_to(target_x, target_y, smooth=True)
                mouse_controller.click()
            except Exception:
                pass
        return True

    def close(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass


window_manager = DesktopWindowManager()
agent_pointer = FloatingAgentPointer()
