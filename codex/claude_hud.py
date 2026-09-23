"""Claude HUD (Heads-Up Display) Statusline.

Implements the aesthetic and architectural telemetry of the Claude Code statusline,
displaying:
- Active Git Branch & Workspace root
- Current Model (e.g. MiniMax M2.7, GPT-OSS 120B)
- Token Consumption & Session Spend ($)
- Dynamic Headroom Gauge
- Active Subagents & Execution State
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from codex.context.headroom import headroom


class ClaudeHUD:
    """Real-time Claude Code-style Statusline & Heads-Up Display."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.enabled = True

    def get_git_branch(self) -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            branch = res.stdout.strip()
            return branch if branch else "detached"
        except Exception:
            return "no-git"

    def render_bar(
        self,
        model_name: str = "openai/gpt-oss-120b",
        total_tokens: int = 0,
        session_cost: float = 0.0,
        current_prompt: str = "",
        active_subagent: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ) -> str:
        """Render single-line ANSI Claude HUD statusline."""
        branch = self.get_git_branch()
        headroom.set_model(model_name)
        hr_info = headroom.calculate_headroom(current_prompt, history_tokens=total_tokens)
        free_k = hr_info["remaining_headroom"] / 1000.0
        pct = hr_info["headroom_pct"]

        # Tokyo Night / Claude Code palette
        c_brand = "\033[38;2;217;119;87m"   # Claude Terracotta / Coral
        c_model = "\033[38;2;122;162;247m"  # Tokyonight Blue
        c_git   = "\033[38;2;158;206;106m"  # Tokyonight Green
        c_tok   = "\033[38;2;187;154;247m"  # Tokyonight Purple
        c_cost  = "\033[38;2;224;175;104m"  # Tokyonight Orange/Gold
        c_hr    = "\033[38;2;115;218;202m"  # Tokyonight Teal
        c_agent = "\033[38;2;247;118;142m"  # Tokyonight Red/Pink
        c_dim   = "\033[38;2;86;95;137m"    # Tokyonight Dim Gray
        c_rst   = "\033[0m"

        tok_k = total_tokens / 1000.0
        sub_str = f" {c_dim}|{c_rst} {c_agent}✦ {active_subagent}{c_rst}" if active_subagent else ""
        lat_str = f" {c_dim}|{c_rst} {c_dim}{latency_ms:.0f}ms{c_rst}" if latency_ms else ""

        line = (
            f"{c_brand}╭─[ Claude HUD ]{c_rst} "
            f"{c_git} {branch}{c_rst} {c_dim}|{c_rst} "
            f"{c_model}󰚩 {model_name}{c_rst} {c_dim}|{c_rst} "
            f"{c_tok} {tok_k:.1f}k tok{c_rst} {c_dim}|{c_rst} "
            f"{c_cost}${session_cost:.4f}{c_rst} {c_dim}|{c_rst} "
            f"{c_hr}⚡ {free_k:.1f}k ({pct:.0f}% HR){c_rst}"
            f"{sub_str}{lat_str}"
        )
        return line

    def render_panel(
        self,
        model_name: str = "openai/gpt-oss-120b",
        total_tokens: int = 0,
        session_cost: float = 0.0,
        current_prompt: str = "",
        active_subagent: Optional[str] = None,
    ) -> None:
        """Render rich box panel Claude HUD."""
        branch = self.get_git_branch()
        headroom.set_model(model_name)
        hr_info = headroom.calculate_headroom(current_prompt, history_tokens=total_tokens)
        free_k = hr_info["remaining_headroom"] / 1000.0
        limit_k = hr_info["context_limit"] / 1000.0
        pct = hr_info["headroom_pct"]

        hud_text = Text()
        hud_text.append(" MODEL ", style="bold black on bright_blue")
        hud_text.append(f" {model_name}  ", style="bold white")
        hud_text.append(" BRANCH ", style="bold black on green")
        hud_text.append(f" {branch}  ", style="bold white")
        hud_text.append(" TOKENS ", style="bold black on magenta")
        hud_text.append(f" {total_tokens}  ", style="white")
        hud_text.append(" COST ", style="bold black on yellow")
        hud_text.append(f" ${session_cost:.4f}  ", style="yellow")
        hud_text.append(" HEADROOM ", style="bold black on cyan")
        hud_text.append(f" {free_k:.1f}k / {limit_k:.1f}k ({pct:.0f}% free) ", style="bold cyan")

        if active_subagent:
            hud_text.append(" AGENT ", style="bold white on red")
            hud_text.append(f" {active_subagent} ", style="bold magenta")

        self.console.print(Panel(hud_text, title="[bold #d97757]Claude Code System HUD[/]", border_style="#565f89", padding=(0, 1)))


claude_hud = ClaudeHUD()
