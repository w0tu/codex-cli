"""PC Desktop and Mouse Automation Controller for Codex CLI using native Linux xdotool."""

import os
import re
import shutil
import subprocess
import time
from typing import Any


class DesktopMouseController:
    """Controls mouse movement, clicks, dragging, scrolling, and keyboard actions on Linux."""

    def __init__(self):
        self.xdotool_bin = shutil.which("xdotool") or "/usr/bin/xdotool"
        self._available = os.path.exists(self.xdotool_bin) and bool(os.environ.get("DISPLAY"))

    @property
    def is_available(self) -> bool:
        return self._available

    def _run_cmd(self, args: list[str]) -> tuple[bool, str]:
        if not self.xdotool_bin or not os.path.exists(self.xdotool_bin):
            return False, "Error: xdotool is not installed on this system."
        if not os.environ.get("DISPLAY"):
            # Set default DISPLAY if running under X11
            os.environ["DISPLAY"] = ":0"

        cmd = [self.xdotool_bin] + args
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, res.stdout.strip()
            return False, res.stderr.strip() or f"Command failed with exit code {res.returncode}"
        except Exception as e:
            return False, f"Execution failed: {e}"

    def get_screen_size(self) -> dict[str, int]:
        """Get current screen resolution."""
        ok, out = self._run_cmd(["getdisplaygeometry"])
        if ok and out:
            parts = out.split()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return {"width": int(parts[0]), "height": int(parts[1])}
        return {"width": 1920, "height": 1080}

    def get_position(self) -> dict[str, Any]:
        """Get current mouse cursor coordinates and active window ID."""
        ok, out = self._run_cmd(["getmouselocation"])
        if ok and out:
            # Format: x:1536 y:864 screen:0 window:1033
            data: dict[str, Any] = {}
            for token in out.split():
                if ":" in token:
                    k, v = token.split(":", 1)
                    data[k] = int(v) if v.isdigit() else v
            return data
        return {"x": 0, "y": 0, "screen": 0, "window": 0}

    def move_to(self, x: int, y: int, smooth: bool = False, steps: int = 15) -> dict[str, Any]:
        """Move mouse cursor to (x, y) coordinates."""
        if smooth:
            curr = self.get_position()
            curr_x = curr.get("x", 0)
            curr_y = curr.get("y", 0)
            for i in range(1, steps + 1):
                inter_x = int(curr_x + (x - curr_x) * (i / steps))
                inter_y = int(curr_y + (y - curr_y) * (i / steps))
                self._run_cmd(["mousemove", str(inter_x), str(inter_y)])
                time.sleep(0.01)
        ok, out = self._run_cmd(["mousemove", str(x), str(y)])
        curr = self.get_position()
        return {
            "success": ok,
            "action": "move",
            "target": {"x": x, "y": y},
            "current": curr,
            "message": f"Mouse cursor moved to ({x}, {y})" if ok else out
        }

    def click(self, button: int = 1, x: int | None = None, y: int | None = None) -> dict[str, Any]:
        """Click mouse button (1=Left, 2=Middle, 3=Right)."""
        if x is not None and y is not None:
            self.move_to(x, y)
        ok, out = self._run_cmd(["click", str(button)])
        btn_name = {1: "Left", 2: "Middle", 3: "Right"}.get(button, f"Button {button}")
        curr = self.get_position()
        return {
            "success": ok,
            "action": "click",
            "button": btn_name,
            "position": curr,
            "message": f"{btn_name} click executed at ({curr.get('x')}, {curr.get('y')})" if ok else out
        }

    def double_click(self, x: int | None = None, y: int | None = None) -> dict[str, Any]:
        """Double-click left mouse button."""
        if x is not None and y is not None:
            self.move_to(x, y)
        ok, out = self._run_cmd(["click", "--repeat", "2", "--delay", "50", "1"])
        curr = self.get_position()
        return {
            "success": ok,
            "action": "double_click",
            "position": curr,
            "message": f"Double click executed at ({curr.get('x')}, {curr.get('y')})" if ok else out
        }

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, button: int = 1) -> dict[str, Any]:
        """Drag mouse from start coordinates to end coordinates."""
        self.move_to(start_x, start_y)
        self._run_cmd(["mousedown", str(button)])
        self.move_to(end_x, end_y, smooth=True)
        ok, out = self._run_cmd(["mouseup", str(button)])
        return {
            "success": ok,
            "action": "drag",
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y},
            "message": f"Mouse drag executed from ({start_x}, {start_y}) to ({end_x}, {end_y})"
        }

    def scroll(self, direction: str = "down", amount: int = 3) -> dict[str, Any]:
        """Scroll mouse wheel (direction: 'up' or 'down')."""
        btn = "4" if direction.lower() == "up" else "5"
        ok, out = self._run_cmd(["click", "--repeat", str(amount), "--delay", "30", btn])
        return {
            "success": ok,
            "action": "scroll",
            "direction": direction,
            "amount": amount,
            "message": f"Mouse scrolled {direction} by {amount} units"
        }

    def type_text(self, text: str) -> dict[str, Any]:
        """Type text at current focus location."""
        ok, out = self._run_cmd(["type", "--delay", "12", text])
        return {
            "success": ok,
            "action": "type_text",
            "length": len(text),
            "message": f"Typed {len(text)} characters into active window" if ok else out
        }

    def press_key(self, key_combination: str) -> dict[str, Any]:
        """Press a keyboard key or combination (e.g. 'Return', 'ctrl+c', 'BackSpace')."""
        ok, out = self._run_cmd(["key", key_combination])
        return {
            "success": ok,
            "action": "press_key",
            "key": key_combination,
            "message": f"Key combination '{key_combination}' sent to system" if ok else out
        }


# Global singleton controller
mouse_controller = DesktopMouseController()
