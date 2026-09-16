"""Usage tracker and rate limiting for Codex — 5-hour / 300-request quotas."""

import os
import json
import time
from pathlib import Path

USAGE_FILE = Path.home() / ".codex" / "usage.json"
WINDOW_5H_SECONDS = 5 * 3600       # 5 hours
WINDOW_DAY_SECONDS = 24 * 3600     # 24 hours
MAX_REQUESTS_5H = 300              # 300 requests per 5 hours
MAX_REQUESTS_DAY = 300             # 300 requests per day


class UsageTracker:
    """Tracks prompt requests with a rolling 5-hour / 300-prompt quota."""

    def __init__(self, filepath: Path = USAGE_FILE):
        self.filepath = filepath
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.timestamps: list[float] = self._load()

    def _load(self) -> list[float]:
        if not self.filepath.exists():
            return []
        try:
            data = json.loads(self.filepath.read_text(encoding="utf-8"))
            now = time.time()
            # Retain only timestamps from the last 24 hours
            return [t for t in data.get("requests", []) if (now - t) < WINDOW_DAY_SECONDS]
        except Exception:
            return []

    def _save(self) -> None:
        try:
            now = time.time()
            cleaned = [t for t in self.timestamps if (now - t) < WINDOW_DAY_SECONDS]
            self.timestamps = cleaned
            self.filepath.write_text(json.dumps({"requests": cleaned}, indent=2), encoding="utf-8")
        except Exception:
            pass

    def check_limit(self) -> tuple[bool, str, float]:
        """Check if user is within the 300-request / 5-hour limit.
        
        Returns:
            (allowed: bool, reason: str, wait_seconds: float)
        """
        now = time.time()
        # Clean expired
        recent_5h = [t for t in self.timestamps if (now - t) < WINDOW_5H_SECONDS]
        recent_day = [t for t in self.timestamps if (now - t) < WINDOW_DAY_SECONDS]

        if len(recent_5h) >= MAX_REQUESTS_5H:
            oldest = min(recent_5h)
            wait_time = max(0.0, WINDOW_5H_SECONDS - (now - oldest))
            mins = int(wait_time // 60)
            hours = mins // 60
            mins_rem = mins % 60
            time_str = f"{hours}h {mins_rem}m" if hours > 0 else f"{mins}m"
            return False, f"5-hour quota reached ({len(recent_5h)}/{MAX_REQUESTS_5H} requests). Resets in {time_str}.", wait_time

        if len(recent_day) >= MAX_REQUESTS_DAY:
            oldest = min(recent_day)
            wait_time = max(0.0, WINDOW_DAY_SECONDS - (now - oldest))
            mins = int(wait_time // 60)
            hours = mins // 60
            mins_rem = mins % 60
            time_str = f"{hours}h {mins_rem}m" if hours > 0 else f"{mins}m"
            return False, f"Daily quota reached ({len(recent_day)}/{MAX_REQUESTS_DAY} requests). Resets in {time_str}.", wait_time

        return True, "", 0.0

    def record_request(self) -> None:
        """Record a completed user prompt request."""
        self.timestamps.append(time.time())
        self._save()

    def get_stats(self) -> dict:
        """Get current usage breakdown."""
        now = time.time()
        recent_5h = [t for t in self.timestamps if (now - t) < WINDOW_5H_SECONDS]
        recent_day = [t for t in self.timestamps if (now - t) < WINDOW_DAY_SECONDS]

        # Reset time for 5-hour window
        reset_5h_str = "None"
        if recent_5h:
            oldest_5h = min(recent_5h)
            wait = max(0.0, WINDOW_5H_SECONDS - (now - oldest_5h))
            mins = int(wait // 60)
            hrs = mins // 60
            reset_5h_str = f"in {hrs}h {mins % 60}m" if hrs > 0 else f"in {mins}m"

        # Reset time for 24-hour daily quota
        reset_day_str = "None"
        if recent_day:
            oldest_day = min(recent_day)
            wait_day = max(0.0, WINDOW_DAY_SECONDS - (now - oldest_day))
            mins_day = int(wait_day // 60)
            hrs_day = mins_day // 60
            reset_day_str = f"in {hrs_day}h {mins_day % 60}m" if hrs_day > 0 else f"in {mins_day}m"

        return {
            "used_5h": len(recent_5h),
            "max_5h": MAX_REQUESTS_5H,
            "remaining_5h": max(0, MAX_REQUESTS_5H - len(recent_5h)),
            "reset_5h": reset_5h_str,
            "used_day": len(recent_day),
            "max_day": MAX_REQUESTS_DAY,
            "remaining_day": max(0, MAX_REQUESTS_DAY - len(recent_day)),
            "reset_day": reset_day_str,
        }

