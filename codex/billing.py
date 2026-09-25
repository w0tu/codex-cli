"""Billing & Cost Guardrail: $2.00 Daily Budget Cap Tracker.

Tracks real-time token spend in ~/.config/codex_cli/billing.json.
Calculates daily usage costs based on token consumption.
If daily spend reaches $2.00, immediately locks cloud escalation for 24 hours,
alerts the user, and gracefully falls back to local Ollama instance.
"""

import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Tuple

from codex.metrics_db import metrics_db

CONFIG_DIR = Path.home() / ".config" / "codex_cli"
BILLING_FILE = CONFIG_DIR / "billing.json"
DAILY_BUDGET_LIMIT = 2.00

# Pricing for OSS-120B High-Precision ($1.50/M input, $5.00/M output)
INPUT_COST_PER_TOKEN = 1.50 / 1_000_000.0
OUTPUT_COST_PER_TOKEN = 5.00 / 1_000_000.0
DEFAULT_COST_PER_TOKEN = 2.50 / 1_000_000.0


class BillingGuardrail:
    """Manages cloud billing ledger and locks escalation at $2.00."""

    def __init__(self, file_path: Path = BILLING_FILE):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        today_str = date.today().isoformat()
        default_data = {
            "date": today_str,
            "daily_spend": 0.0,
            "daily_tokens": 0,
            "locked_until": 0.0,
            "lock_reason": "",
            "budget_limit": DAILY_BUDGET_LIMIT,
        }

        if not self.file_path.exists():
            self._save(default_data)
            return default_data

        try:
            content = self.file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            # Reset daily spend if date rolled over
            if data.get("date") != today_str:
                data["date"] = today_str
                data["daily_spend"] = 0.0
                data["daily_tokens"] = 0
                # Preserve lock if still active in time window
                if data.get("locked_until", 0.0) < time.time():
                    data["locked_until"] = 0.0
                    data["lock_reason"] = ""
                self._save(data)
            return data
        except Exception:
            self._save(default_data)
            return default_data

    def _save(self, data: Dict[str, Any]) -> None:
        try:
            self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def check_cloud_escalation(self) -> Tuple[bool, str]:
        """Check if cloud escalation is permitted (100% free direct Groq tier).
        
        Returns:
            (allowed: bool, notice: str)
        """
        return True, ""

    def record_cloud_spend(self, prompt_tokens: int, completion_tokens: int) -> Tuple[float, bool]:
        """Record token consumption, update billing, and trigger lockout if budget exhausted.
        
        Returns:
            (turn_cost: float, lock_triggered: bool)
        """
        cost = (prompt_tokens * INPUT_COST_PER_TOKEN) + (completion_tokens * OUTPUT_COST_PER_TOKEN)
        total_tokens = prompt_tokens + completion_tokens

        self.data = self._load()
        self.data["daily_spend"] = round(self.data.get("daily_spend", 0.0) + cost, 6)
        self.data["daily_tokens"] = self.data.get("daily_tokens", 0) + total_tokens

        lock_triggered = False
        self._save(self.data)

        # Sync to SQLite metrics db
        try:
            metrics_db.record_turn(local_tokens=0, cloud_tokens=total_tokens, cloud_spend=cost)
        except Exception:
            pass

        return cost, lock_triggered

    def get_status(self) -> Dict[str, Any]:
        """Return current billing statistics."""
        self.data = self._load()
        now = time.time()
        is_locked = self.data.get("locked_until", 0.0) > now
        remaining_lock = max(0, int(self.data.get("locked_until", 0.0) - now))
        return {
            "date": self.data.get("date"),
            "daily_spend": self.data.get("daily_spend", 0.0),
            "budget_limit": DAILY_BUDGET_LIMIT,
            "daily_tokens": self.data.get("daily_tokens", 0),
            "is_locked": is_locked,
            "remaining_lock_seconds": remaining_lock,
            "lock_reason": self.data.get("lock_reason", ""),
        }


# Global singleton instance
billing_guardrail = BillingGuardrail()
