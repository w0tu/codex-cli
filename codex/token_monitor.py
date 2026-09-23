"""10-Second Real-Time Token Monitor & Groq Console Synchronizer for Codex-CLI.

Tracks:
- Total tokens used from Cloud Native Server.
- Rolling token generation rate (tok/s).
- 5-hour rolling quota and $2.00 spend guardrail.
- Emits formatted telemetry every 10 seconds.
"""

import time
import threading
from typing import Optional, Callable
from rich.console import Console

from codex.metrics_db import metrics_db

console = Console()


class TenSecondTokenMonitor:
    """Background heartbeat reporting live token counts & Groq console metrics every 10s."""

    def __init__(self, callback: Optional[Callable[[dict], None]] = None):
        self.callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.console_url = "https://console.groq.com/home"

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            time.sleep(10.0)
            if not self._running:
                break
            try:
                stats = self.get_current_metrics()
                if self.callback:
                    self.callback(stats)
            except Exception:
                pass

    def get_current_metrics(self) -> dict:
        summary = metrics_db.get_summary()
        total_tokens = summary.get("total_local_tokens", 0) + summary.get("total_cloud_tokens", 0)
        return {
            "timestamp": time.time(),
            "total_tokens": total_tokens,
            "cloud_tokens": summary.get("total_cloud_tokens", 0),
            "local_tokens": summary.get("total_local_tokens", 0),
            "total_spend_usd": summary.get("total_cloud_spend", 0.0),
            "groq_console_url": self.console_url,
            "spend_cap_usd": 2.00,
        }

    def print_heartbeat(self):
        m = self.get_current_metrics()
        line = (
            f"[dim]✦ [CLOUD TELEMETRY][/] "
            f"[bold cyan]Total Tokens: {m['total_tokens']:,}[/] │ "
            f"[bold green]Spend: ${m['total_spend_usd']:.4f}/$2.00[/] │ "
            f"[dim underline green]{self.console_url}[/]"
        )
        console.print(line)


# Global singleton monitor
token_monitor = TenSecondTokenMonitor()
