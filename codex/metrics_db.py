"""Metrics & Usage Tracking: Persistent SQLite Database and Telemetry Dashboard.

Tracks:
- lifetime_tokens: Cumulative tokens evaluated locally and in cloud across all sessions.
- daily_usage: Daily token breakdown and cloud spend.
- streak: Consecutive active usage days (with automatic daily streak incrementation).
- peak_day: Date and token count of the single highest usage day on record.
"""

import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".config" / "codex_cli"
DB_PATH = CONFIG_DIR / "metrics.db"


class MetricsDB:
    """Persistent SQLite telemetry store for Codex-CLI."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_kv (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_usage (
                    date TEXT PRIMARY KEY,
                    local_tokens INTEGER DEFAULT 0,
                    cloud_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cloud_spend REAL DEFAULT 0.0,
                    turns_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

        # Seed defaults if not present
        self._seed_default("lifetime_tokens", "0")
        self._seed_default("streak", "1")
        self._seed_default("last_active_date", date.today().isoformat())
        self._seed_default("peak_day_date", date.today().isoformat())
        self._seed_default("peak_day_tokens", "0")

    def _seed_default(self, key: str, default_val: str) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config_kv WHERE key = ?", (key,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT OR REPLACE INTO config_kv (key, value) VALUES (?, ?)", (key, default_val))
                conn.commit()

    def _get_kv(self, key: str, default: str = "") -> str:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config_kv WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def _set_kv(self, key: str, value: str) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO config_kv (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def record_turn(self, local_tokens: int = 0, cloud_tokens: int = 0, cloud_spend: float = 0.0) -> None:
        """Record token usage and update streak, peak day, and lifetime counters."""
        today_str = date.today().isoformat()
        total_turn_tokens = local_tokens + cloud_tokens

        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Update or insert daily row
            cursor.execute("""
                INSERT INTO daily_usage (date, local_tokens, cloud_tokens, total_tokens, cloud_spend, turns_count)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(date) DO UPDATE SET
                    local_tokens = local_tokens + excluded.local_tokens,
                    cloud_tokens = cloud_tokens + excluded.cloud_tokens,
                    total_tokens = total_tokens + excluded.total_tokens,
                    cloud_spend = cloud_spend + excluded.cloud_spend,
                    turns_count = turns_count + 1
            """, (today_str, local_tokens, cloud_tokens, total_turn_tokens, cloud_spend))
            conn.commit()

        # Update streak
        last_active = self._get_kv("last_active_date", "")
        current_streak = int(self._get_kv("streak", "1"))

        if last_active:
            try:
                last_dt = datetime.strptime(last_active, "%Y-%m-%d").date()
                today_dt = date.today()
                diff_days = (today_dt - last_dt).days

                if diff_days == 1:
                    # Consecutive day! Increment streak
                    current_streak += 1
                    self._set_kv("streak", str(current_streak))
                    self._set_kv("last_active_date", today_str)
                elif diff_days > 1:
                    # Missed days, reset streak to 1
                    current_streak = 1
                    self._set_kv("streak", "1")
                    self._set_kv("last_active_date", today_str)
                elif diff_days == 0:
                    # Same day activity, maintain streak
                    pass
            except Exception:
                self._set_kv("last_active_date", today_str)
        else:
            self._set_kv("last_active_date", today_str)
            self._set_kv("streak", "1")

        # Update lifetime tokens
        lifetime = int(self._get_kv("lifetime_tokens", "0")) + total_turn_tokens
        self._set_kv("lifetime_tokens", str(lifetime))

        # Check peak day
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT total_tokens FROM daily_usage WHERE date = ?", (today_str,))
            today_row = cursor.fetchone()
            today_total = today_row["total_tokens"] if today_row else 0

        peak_tokens = int(self._get_kv("peak_day_tokens", "0"))
        if today_total > peak_tokens:
            self._set_kv("peak_day_tokens", str(today_total))
            self._set_kv("peak_day_date", today_str)

    def get_summary(self) -> Dict[str, Any]:
        """Fetch all aggregated metrics for telemetry reporting."""
        today_str = date.today().isoformat()
        lifetime_tokens = int(self._get_kv("lifetime_tokens", "0"))
        streak = int(self._get_kv("streak", "1"))
        peak_day_date = self._get_kv("peak_day_date", today_str)
        peak_day_tokens = int(self._get_kv("peak_day_tokens", "0"))

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_usage WHERE date = ?", (today_str,))
            row = cursor.fetchone()

        if row:
            daily_local = row["local_tokens"]
            daily_cloud = row["cloud_tokens"]
            daily_total = row["total_tokens"]
            daily_spend = row["cloud_spend"]
            turns_count = row["turns_count"]
        else:
            daily_local = 0
            daily_cloud = 0
            daily_total = 0
            daily_spend = 0.0
            turns_count = 0

        # Peak day tokens fallback
        if peak_day_tokens == 0 and daily_total > 0:
            peak_day_tokens = daily_total
            peak_day_date = today_str

        return {
            "lifetime_tokens": lifetime_tokens,
            "daily_total_tokens": daily_total,
            "daily_local_tokens": daily_local,
            "daily_cloud_tokens": daily_cloud,
            "daily_spend": daily_spend,
            "daily_budget": 2.00,
            "streak": streak,
            "peak_day_date": peak_day_date,
            "peak_day_tokens": peak_day_tokens,
            "turns_count": turns_count,
        }

    def render_block_telemetry_card(self) -> str:
        """Render a clean block-style telemetry card for /usage using █, ░, ▓."""
        data = self.get_summary()
        spend = data["daily_spend"]
        budget = data["daily_budget"]
        spend_pct = min(100.0, (spend / budget) * 100.0) if budget > 0 else 0.0

        # 20-character progress bar
        bar_len = 20
        filled = int((spend_pct / 100.0) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        lines = [
            f"\033[38;2;120;120;130m▌\033[0m \033[1;37mCODEX-CLI TELEMETRY & USAGE DASHBOARD\033[0m \033[38;2;100;100;110m░▒▓\033[0m",
            f"\033[38;2;90;90;100m▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀\033[0m",
            f"\033[38;2;120;120;130m▌\033[0m \033[38;2;80;160;255mLifetime Tokens:\033[0m     \033[1;37m{data['lifetime_tokens']:,}\033[0m tokens evaluated (local + cloaked)",
            f"\033[38;2;120;120;130m▌\033[0m \033[38;2;80;200;120mDaily Active Streak:\033[0m \033[1;32m{data['streak']}\033[0m consecutive days active",
            f"\033[38;2;120;120;130m▌\033[0m \033[38;2;240;180;60mAll-Time Peak Record:\033[0m\033[1;37m{data['peak_day_tokens']:,}\033[0m tokens on {data['peak_day_date']}",
            f"\033[38;2;120;120;130m▌\033[0m",
            f"\033[38;2;120;120;130m▌\033[0m \033[38;2;220;80;80mDaily Cloud Spend:\033[0m   \033[1;37m${spend:.4f}\033[0m / \033[1;37m${budget:.2f}\033[0m budget cap",
            f"\033[38;2;120;120;130m▌\033[0m Budget Meter:        [{bar}] \033[1;37m{spend_pct:.1f}%\033[0m",
            f"\033[38;2;120;120;130m▌\033[0m Today Breakdown:     Local: \033[1;37m{data['daily_local_tokens']:,}\033[0m | Cloud: \033[1;37m{data['daily_cloud_tokens']:,}\033[0m | Turns: \033[1;37m{data['turns_count']}\033[0m",
            f"\033[38;2;90;90;100m▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀\033[0m",
        ]
        return "\n".join(lines)


# Global singleton instance
metrics_db = MetricsDB()
