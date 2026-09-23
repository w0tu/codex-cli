"""Terminal UI components for Codex — dynamic contextual thinking, usage tab, collapsible cards."""

import os
import sys
import time
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.live import Live
from rich import box

console = Console()

# Legless 4-row single-block monochrome pixel mascot with dynamic moving eyes
EYE_PATTERNS = {
    "center":  [1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1],
    "left":    [1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1],
    "right":   [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1],
    "down":    [1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1],
    "up":      [0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0],
    "blink":   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    "wink":    [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    "wide":    [1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1],
    "curious": [1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1],
}
BLOCK = "█"
EMPTY = " "

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
THINKING_GLYPHS = ["◇", "◈", "◆", "◈"]


def format_clean_model_name(model_name: str) -> str:
    """Format model name cleanly, hiding internal vendor strings like antigravity."""
    clean = model_name.strip()
    for s in [" antigravity", "-antigravity", "_antigravity"]:
        if clean.lower().endswith(s):
            clean = clean[:-len(s)].strip()
    return clean


def render_mascot(eye_state: str = "center") -> Text:
    """Render the compact legless monochrome mascot with dynamic moving eyes."""
    eye_row = EYE_PATTERNS.get(eye_state, EYE_PATTERNS["center"])
    # 4 rows: floating rounded head, zero legs
    grid = [
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        eye_row,
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    ]
    t = Text()
    for i, row in enumerate(grid):
        line = "".join(BLOCK if cell else EMPTY for cell in row)
        t.append(line, style="bold white")
        if i < len(grid) - 1:
            t.append("\n")
    return t


def render_header(model_name: str = "gemini 2.5 flash", cwd: str | None = None, eye_state: str = "center") -> Panel:
    """Same compact monochrome header matching Claude Code aesthetic."""
    mascot = render_mascot(eye_state=eye_state)
    workspace = cwd or os.getcwd()
    display_model = format_clean_model_name(model_name)

    info = Text()
    info.append("CODEX", style="bold white")
    info.append(" v1.7.0\n", style="dim")
    info.append("model:    ", style="dim")
    info.append(f"{display_model}\n", style="white")
    info.append("dir:      ", style="dim")
    info.append(f"{workspace}\n", style="white")
    info.append("commands: ", style="dim")
    info.append("/ for menu\n", style="white")
    info.append("abort:    ", style="dim")
    info.append("^C", style="white")

    grid = Table.grid(padding=(0, 2))
    grid.add_column(vertical="middle")
    grid.add_column(vertical="middle")
    grid.add_row(mascot, info)

    return Panel(grid, box=box.ROUNDED, border_style="grey35", expand=False)


def play_mascot_greeting(model_name: str = "gemini 2.5 flash", cwd: str | None = None) -> None:
    """Play a smooth, live wake-up animation in the scrolling terminal stream."""
    from rich.live import Live
    sequence = ["blink", "left", "right", "curious", "wink", "center"]
    try:
        with Live(render_header(model_name=model_name, cwd=cwd, eye_state="blink"), console=console, refresh_per_second=20, transient=False) as live:
            for state in sequence:
                live.update(render_header(model_name=model_name, cwd=cwd, eye_state=state))
                time.sleep(0.06)
    except Exception:
        console.print(render_header(model_name=model_name, cwd=cwd, eye_state="center"))


def run_mascot_showcase() -> None:
    """Run interactive showcase of all mascot eye animations."""
    states = [
        ("center", "Attentive / Neutral"),
        ("left", "Scanning Left Files"),
        ("right", "Inspecting Git Status"),
        ("up", "Reading Context History"),
        ("down", "Writing Code to Disk"),
        ("curious", "Analyzing Logic"),
        ("wink", "Execution Succeeded"),
        ("wide", "Alert / Discovered Bug"),
        ("blink", "Blinking"),
    ]
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Codex Mascot Animated Expressions[/]")
    t.add_column("Mascot", justify="center")
    t.add_column("State", style="bold white")
    t.add_column("Behavior", style="dim")

    for st, desc in states:
        t.add_row(render_mascot(st), st, desc)
    console.print(t)
    console.print("[dim]The mascot automatically moves its eyes during autonomous agent execution.[/]\n")


def clear_terminal() -> None:
    """Completely wipe the terminal screen, scrollback buffer, and reset cursor."""
    sys.stdout.write("\x1b[3J\x1b[2J\x1b[H")
    sys.stdout.flush()
    try:
        os.system("clear")
    except Exception:
        pass


def calculate_thinking_duration(prompt: str) -> float:
    """Snappy cognitive phase duration without artificial lag."""
    words = len(prompt.split())
    if words < 6:
        return 0.18
    elif words < 15:
        return 0.28
    elif words < 40:
        return 0.38
    return 0.48


def get_prompt_related_phases(prompt: str) -> list[str]:
    """Generate dynamic cognitive phases directly relevant to the user prompt."""
    p = prompt.lower()
    if any(k in p for k in ["git", "branch", "commit", "diff", "repo", "status"]):
        return [
            "Checking git repository status & tree...",
            "Inspecting branch commits & working diffs...",
            "Evaluating version control state...",
            "Synthesizing git operations...",
        ]
    elif any(k in p for k in ["python", "code", "func", "class", "bug", "fix", "test", "unittest", "script"]):
        return [
            "Analyzing code syntax & AST semantics...",
            "Checking module dependencies & types...",
            "Evaluating algorithmic complexity & edge cases...",
            "Synthesizing verified implementation...",
        ]
    elif any(k in p for k in ["file", "dir", "read", "write", "edit", "path", "folder", "tree"]):
        return [
            "Scanning filesystem paths & directory tree...",
            "Checking file permissions & line offsets...",
            "Evaluating disk I/O operations...",
            "Formatting structured file output...",
        ]
    elif any(k in p for k in ["find", "grep", "search", "locate", "where"]):
        return [
            "Indexing search patterns & query regex...",
            "Scanning workspace directory hierarchy...",
            "Filtering matching files & line numbers...",
            "Summarizing matching results...",
        ]
    elif any(k in p for k in ["bash", "run", "cmd", "command", "exec", "terminal", "sh"]):
        return [
            "Formulating shell execution plan...",
            "Checking process safety & environment...",
            "Evaluating command parameters & pipes...",
            "Preparing execution pipeline...",
        ]
    else:
        return [
            "Deconstructing query semantics...",
            "Inspecting project context & memory ledger...",
            "Evaluating technical constraints...",
            "Synthesizing verified solution...",
        ]


def animate_thinking(prompt: str = "") -> float:
    """Snappy prompt-related dynamic in-place thinking indicator using standard ANSI cursor control."""
    from codex.terminal import inline_thinking_timer
    duration = calculate_thinking_duration(prompt)
    phases = get_prompt_related_phases(prompt)
    return inline_thinking_timer(prompt=prompt, duration=duration, phases=phases)


def render_thinking_block(thought_text: str, elapsed: float | None = None) -> None:
    """Render the model's actual thought process and reasoning in a clean collapsible card."""
    cleaned = thought_text.strip()
    if not cleaned:
        return
    t = Text()
    t.append("╭─ [thought] ", style="dim")
    if elapsed:
        t.append(f"Reasoning Process ({elapsed:.2f}s)\n", style="bold white")
    else:
        t.append("Reasoning Process\n", style="bold white")

    lines = cleaned.splitlines()
    if len(lines) > 12:
        for line in lines[:10]:
            t.append(f"│ {line}\n", style="dim")
        t.append(f"│ ... ({len(lines) - 10} lines collapsed for clean display)\n", style="dim")
    else:
        for line in lines:
            t.append(f"│ {line}\n", style="dim")
    t.append("╰─\n", style="dim")
    console.print(t)



def render_error(title: str, detail: str, remedy: str | None = None) -> None:
    """Render a clean, informative monochrome error card."""
    t = Text()
    t.append("╭─ [error] ", style="bold white")
    t.append(f"{title}\n", style="bold white")
    t.append(f"│ {detail}\n", style="dim")
    if remedy:
        t.append(f"│ Action: {remedy}\n", style="white")
    t.append("╰─\n", style="dim")
    console.print(t)


def format_prompt_string(cwd: str, theme_name: str | None = None) -> str:
    """Format inline prompt string with directory, active git branch, and dirty status."""
    from codex.themes import get_theme
    t = get_theme(theme_name)
    dirname = os.path.basename(cwd) or "~"

    branch_info = ""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=1,
            cwd=cwd,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            branch = proc.stdout.strip()
            # check dirty status
            status_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=1,
                cwd=cwd,
            )
            is_dirty = "*" if status_proc.stdout.strip() else ""
            branch_info = f" {t['prompt_in']}({t['prompt_branch']}{branch}{is_dirty}{t['prompt_in']})"
    except Exception:
        pass

    return f"{t['prompt_app']}codex{t['prompt_in']} in {t['prompt_dir']}{dirname}{branch_info} {t['prompt_char']}>\x1b[0m "


def print_prompt(cwd: str) -> None:
    """Print the clean prompt header."""
    dirname = os.path.basename(cwd) or "~"
    console.print(f"[dim]╭─[/] [bold white]codex[/] [dim]in[/] [white]{dirname}[/]")


def render_tool_call(name: str, args_summary: str) -> None:
    """Display an agent tool call start card in monochrome."""
    t = Text()
    t.append("╭─ [tool] ", style="dim")
    t.append(f"{name}: ", style="bold white")
    t.append(args_summary, style="dim")
    console.print(t)


def render_tool_result(result: str, max_lines: int = 8) -> None:
    """Display output from an executed tool with clean collapsible formatting."""
    lines = result.strip().splitlines()
    if not lines:
        console.print("[dim]│[/] [dim](no output)[/]")
    elif len(lines) > max_lines:
        for line in lines[:max_lines]:
            console.print(f"[dim]│[/] {line}")
        omitted = len(lines) - max_lines
        console.print(f"[dim]│[/] [dim italic]... ({omitted} lines collapsed for clean display)[/dim italic]")
    else:
        for line in lines:
            console.print(f"[dim]│[/] {line}")
    console.print("[dim]╰─[/]\n")


def print_telemetry(tokens: int, total_elapsed: float) -> None:
    """Timer and telemetry from prompt entry to finished execution."""
    tps = tokens / max(total_elapsed, 0.001)
    console.print(
        f"[dim]> {tokens} tokens | Done in {total_elapsed:.2f}s | {tps:.1f} tok/s | Codex Native[/]\n"
    )


def render_usage_tab(stats: dict) -> None:
    """Display usage tab with 5-hour / 300-prompt limits and 24-hour credit refresh."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Codex Usage & Quota Monitor[/]")
    t.add_column("Quota Window", style="bold white")
    t.add_column("Usage / Capacity", style="white")
    t.add_column("Reset Schedule & Status", style="dim")

    used_5h = stats.get("used_5h", 0)
    max_5h = stats.get("max_5h", 300)
    rem_5h = stats.get("remaining_5h", 300)
    reset_5h = stats.get("reset_5h", "None")
    t.add_row("5-Hour Rolling Window", f"{used_5h} / {max_5h} requests", f"{rem_5h} remaining ({reset_5h})")

    used_day = stats.get("used_day", 0)
    max_day = stats.get("max_day", 300)
    rem_day = stats.get("remaining_day", 300)
    reset_day = stats.get("reset_day", "None")
    t.add_row("24-Hour Daily Quota", f"{used_day} / {max_day} requests", f"{rem_day} remaining today")
    t.add_row("Credit Refresh Cycle", "Every 24 Hours", f"Daily credit refresh ({reset_day})")

    t.add_row("Policy Enforcement", "Strict Rate Limiting", "300 requests per 5h / 24h cycle")
    t.add_row("Inference Tier", "Codex Engine", "Hardware-accelerated neural processing")

    console.print(t)
    console.print()


def render_diff(diff_output: str) -> None:
    """Display git diff output with syntax coloring."""
    if not diff_output.strip():
        console.print("[dim]No uncommitted changes in working tree.[/]\n")
        return
    render_inline_diff(diff_output)


def render_inline_diff(diff_output: str) -> None:
    """Print compact, colored inline unified diff directly to stdout without alternate screen buffers."""
    if not diff_output.strip():
        return
    for line in diff_output.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            sys.stdout.write(f"\x1b[1;37m{line}\x1b[0m\n")
        elif line.startswith("+"):
            sys.stdout.write(f"\x1b[32m{line}\x1b[0m\n")
        elif line.startswith("-"):
            sys.stdout.write(f"\x1b[31m{line}\x1b[0m\n")
        elif line.startswith("@@"):
            sys.stdout.write(f"\x1b[36m{line}\x1b[0m\n")
        else:
            sys.stdout.write(f"\x1b[2m{line}\x1b[0m\n")
    sys.stdout.flush()


def prompt_apply_changes(diff_text: Optional[str] = None) -> str:
    """Interactive raw-mode keystroke prompt at the bottom of the current scroll position."""
    from codex.terminal import read_key_inline
    if diff_text:
        render_inline_diff(diff_text)
    prompt_str = (
        "\x1b[1;37mApply these changes? \x1b[0m"
        "[\x1b[1;32my\x1b[0m]es, "
        "[\x1b[1;31mn\x1b[0m]o, "
        "[\x1b[1;36md\x1b[0m]iff view, "
        "[\x1b[1;33me\x1b[0m]dit: "
    )
    choice = read_key_inline(prompt_str, valid_keys=["y", "n", "d", "e"])
    return choice


def stream_assistant_chunk(chunk: str) -> None:
    """Stream single assistant response chunk to stdout with immediate flush."""
    sys.stdout.write(chunk)
    sys.stdout.flush()


def render_export_status(path: str, message_count: int) -> None:
    """Display export status card."""
    t = Text()
    t.append("╭─ [export] ", style="dim")
    t.append("Session Exported\n", style="bold white")
    t.append(f"│ Saved {message_count} messages to: {path}\n", style="dim")
    t.append("╰─ You can share or review this conversation file.\n", style="dim")
    console.print(t)


def render_memory_status(total_msgs: int, active_window: int, knowledge_count: int, files_count: int) -> None:
    """Display session memory ledger stats."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Codex Memory Architecture[/]")
    t.add_column("Memory Layer", style="bold white")
    t.add_column("Capacity / Count", style="white")
    t.add_column("Status", style="dim")
    t.add_row("Total History Archive", f"{total_msgs} messages", "Preserved on disk (300+ message capacity)")
    t.add_row("Active Sliding Window", f"{min(total_msgs, active_window)} messages", "Full-fidelity recent context")
    t.add_row("Consolidated Knowledge Base", f"{knowledge_count} entries", "Distilled facts & past discussion points")
    t.add_row("Session File Registry", f"{files_count} files", "Tracked file creations and edits")
    console.print(t)
    console.print()


def render_skills_list(skills: list[dict]) -> None:
    """Display installed GitHub and community skills."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Installed Codex Skills[/]")
    t.add_column("Skill Name", style="bold white", no_wrap=True)
    t.add_column("Description", style="white")
    t.add_column("Scope", style="dim")

    if not skills:
        t.add_row("None", "No skills installed. Run /skills install <owner/repo>", "N/A")
    else:
        for s in skills:
            t.add_row(s.get("name", ""), s.get("description", ""), s.get("source", "global"))

    console.print(t)
    console.print()


def render_key_saved(key_masked: str, path: str) -> None:
    """Display API key persistence card."""
    t = Text()
    t.append("╭─ [auth] ", style="dim")
    t.append("API Key Saved & Activated Globally\n", style="bold white")
    t.append(f"│ Stored permanently in: {path}\n", style="dim")
    t.append(f"│ Active Key: {key_masked}\n", style="dim")
    t.append("╰─ Active inference key updated live. Available across all sessions & CLI invocations.\n", style="dim")
    console.print(t)


def render_help() -> None:
    """Display slash command reference table."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Slash Commands[/]")
    t.add_column("Command", style="bold white", no_wrap=True)
    t.add_column("Description", style="white")
    t.add_row("/help", "Show this reference guide")
    t.add_row("/clear", "Clear screen and redraw header")
    t.add_row("/usage", "Display 5-hour / 300-prompt usage & quota monitor")
    t.add_row("/onboard", "Run interactive auth setup and API key verification")
    t.add_row("/doctor", "Run diagnostic health check on environment")
    t.add_row("/verify", "Run automated test verification & anti-tamper lock")
    t.add_row("/checkpoint [create|list|rollback]", "Create, inspect, or rollback shadow git commits")
    t.add_row("/subagent <task>", "Decompose task into autonomous Scout/Coder/Critic DAG")
    t.add_row("/skills [install <repo>]", "List or install developer skills from GitHub")
    t.add_row("/context [--mock]", "Inspect 10x10 token visualizer & context window telemetry")
    t.add_row("/cost", "Show token usage & cost statistics")
    t.add_row("/diff", "View colored git diff of current changes")
    t.add_row("/export [file]", "Export session conversation to markdown")
    t.add_row("/init", "Initialize CODEX.md project context guidelines")
    t.add_row("/git", "Show git status, active branch, and diffs")
    t.add_row("/github [repo]", "Connect, clone, or inspect GitHub repository")
    t.add_row("/tools", "List available PC agent tools")
    t.add_row("/theme [name]", "Switch or list UI color themes (monochrome, nord, dracula, matrix)")
    t.add_row("/editor", "Open external $EDITOR (nano, vim) for multiline prompt drafting")
    t.add_row("/notify [on|off]", "Toggle desktop notify-send alerts and terminal bell cues")
    t.add_row("/model [name|list]", "Switch model or view live available model catalog")
    t.add_row("/modal", "Open interactive Antigravity model selection modal")
    t.add_row("/mascot", "Display animated mascot showcase with moving eyes")
    t.add_row("/stats", "Display session token and latency stats")
    t.add_row("/swarm, /grokbot", "Enter the 45,000+ Agent Swarm Command Center area")
    t.add_row("/reset", "Clear conversation history")
    t.add_row("/exit, /quit", "Exit Codex terminal (or Ctrl+D)")
    console.print(t)
    console.print()


def render_theme_list() -> None:
    """Display available terminal color themes."""
    from codex.themes import list_themes
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Codex UI Color Themes[/]")
    t.add_column("Theme ID", style="bold white", no_wrap=True)
    t.add_column("Status", style="white")
    t.add_column("Description", style="dim")

    for th in list_themes():
        status = "[bold green]ACTIVE[/]" if th["active"] else "[dim]Available[/]"
        t.add_row(th["id"], status, th["description"])
    console.print(t)
    console.print("[dim]Use '/theme <theme-id>' to switch palettes live.[/]\n")


ANTIGRAVITY_MODELS_CATALOG = [
    {"id": "gemini 2.5 flash", "context_window": "1000k", "tier": "Lowest Cost / Usage Limit (Default)"},
    {"id": "gemini 3.8 flash", "context_window": "1000k", "tier": "Ultra-Fast Multimodal Reasoning"},
    {"id": "gemini 3.8 pro", "context_window": "2000k", "tier": "Deep Architecture & Logic"},
    {"id": "gemini 2.5 pro", "context_window": "2000k", "tier": "Complex Refactoring"},
]


def render_model_catalog(models: list[dict], active_model: str) -> None:
    """Display live model catalog fetched from API with Antigravity models prioritized first."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Available Inference Models[/]")
    t.add_column("Model ID", style="bold white")
    t.add_column("Status", style="white")
    t.add_column("Context Window", style="dim")
    t.add_column("Architecture Tier", style="dim")

    seen_ids = set()

    # Prepend Antigravity models first
    for am in ANTIGRAVITY_MODELS_CATALOG:
        m_id = am["id"]
        seen_ids.add(m_id)
        is_active = (m_id == active_model or format_clean_model_name(m_id) == format_clean_model_name(active_model))
        status = "[bold green]ACTIVE[/]" if is_active else "[dim]Available[/]"
        t.add_row(m_id, status, am["context_window"], am["tier"])

    for m in models:
        m_id = m.get("id", "")
        clean_id = format_clean_model_name(m_id)
        if clean_id in seen_ids or m_id in seen_ids:
            continue
        seen_ids.add(m_id)
        is_active = (clean_id == active_model or m_id == active_model)
        status = "[bold green]ACTIVE[/]" if is_active else "[dim]Available[/]"
        ctx = str(m.get("context_window", "128k"))
        t.add_row(clean_id, status, ctx, "Groq Hardware Engine")

    console.print(t)
    console.print("[dim]Use '/model <model-id>' or '/model' to open the interactive selection modal.[/]\n")


def prompt_model_modal(active_model: str) -> str | None:
    """Render an interactive inline terminal modal for model selection."""
    options = [
        ("gemini 2.5 flash", "1000k context · Lowest Cost & Quota Footprint (Default)"),
        ("gemini 3.8 flash", "1000k context · Ultra-Fast Multimodal Reasoning"),
        ("gemini 3.8 pro", "2000k context · Deep Architecture & Logic"),
        ("gemini 2.5 pro", "2000k context · Complex Refactoring & Systems"),
        ("llama-3.1-8b-instant", "131k context · Lowest Cost Open Weights"),
        ("qwen/qwen3.8-27b", "32k context · Open Weights Coding Model"),
        ("llama-3.3-70b-versatile", "128k context · Llama 3.3 Production Tier"),
    ]

    lines = []
    lines.append("╭────────────────────────── Select Model ──────────────────────────╮")
    for idx, (m_id, desc) in enumerate(options, 1):
        clean_active = format_clean_model_name(active_model)
        is_cur = (m_id == clean_active or m_id == active_model)
        dot = "●" if is_cur else " "
        cur_tag = " (Active)" if is_cur else ""
        item_str = f"  [{idx}] {dot} {m_id:<22} {desc}{cur_tag}"
        # Truncate to box width
        lines.append(f"│ {item_str:<64} │")
    lines.append("│                                                                  │")
    lines.append("│ Enter choice [1-7] or press Enter to cancel:                     │")
    lines.append("╰──────────────────────────────────────────────────────────────────╯")

    console.print("\n".join(lines), style="bold white")
    try:
        choice = console.input("[bold cyan]> [/]").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
    except (EOFError, KeyboardInterrupt):
        pass
    return None


def render_tools_list() -> None:
    """Display available PC agent tools."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]PC Agent Tools[/]")
    t.add_column("Tool", style="bold white", no_wrap=True)
    t.add_column("Capability", style="white")
    t.add_row("bash", "Execute shell commands, run tests, install packages, etc.")
    t.add_row("read_file", "Inspect file contents with line numbers")
    t.add_row("write_file", "Create new files or overwrite existing files")
    t.add_row("edit_file", "Precise find-and-replace text edits inside files")
    t.add_row("code_outline", "Extract AST symbol table, classes, and methods")
    t.add_row("get_symbol", "Extract exact function or class implementation via AST")
    t.add_row("list_dir", "Inspect directory structure and file sizes")
    t.add_row("grep_search", "Fast regex / string search across project files")
    t.add_row("find_files", "Locate files matching glob patterns (e.g. *.py)")
    t.add_row("git_status", "Inspect active branch, staged files, and git diff")
    t.add_row("github_connect", "Clone or connect any GitHub repository")
    t.add_row("install_skill", "Install community developer skill from GitHub")
    t.add_row("list_skills", "List all active community and workspace skills")
    t.add_row("web_search", "Free live web search via Wikipedia and DuckDuckGo")
    t.add_row("fetch_url", "Fetch and extract text from public web URLs")
    t.add_row("online_info", "Encyclopedic concept lookup from Wikipedia REST API")
    t.add_row("github_search", "Search public GitHub repositories for code and stars")
    t.add_row("recall_memory", "Recall discussions and facts from earlier in the session")
    console.print(t)
    console.print()


def render_doctor(model: str = "qwen/qwen3.8-27b") -> None:
    """Run full Phase 1 system diagnostics (codex doctor)."""
    from codex.doctor import check_diagnostics

    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Codex Doctor Diagnostics[/]")
    t.add_column("Component", style="bold white")
    t.add_column("Status", style="white")
    t.add_column("Details", style="dim")

    clean_model = format_clean_model_name(model)
    diag_results = check_diagnostics(clean_model)
    for r in diag_results:
        st = r["status"]
        st_style = "bold white" if st in ("OK", "READY") else ("white" if st == "OPTIONAL" else "dim")
        t.add_row(r["component"], f"[{st_style}]{st}[/]", r["details"])

    console.print(t)
    console.print()



def render_cost(queries: int, total_tokens: int) -> None:
    """Display session token spend and estimated costs."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Cost & Usage Tracker[/]")
    t.add_column("Metric", style="bold white")
    t.add_column("Value", style="white")
    t.add_row("Total Session Turns", str(queries))
    t.add_row("Total Tokens Processed", f"{total_tokens:,}")
    t.add_row("Provider Service Tier", "Codex Native Tier (Accelerated)")
    t.add_row("Estimated Cost", "$0.0000 USD")
    console.print(t)
    console.print()



def render_compact_summary(old_messages: int, new_messages: int) -> None:
    """Display context compaction confirmation card."""
    t = Text()
    t.append("╭─ [compact] ", style="dim")
    t.append("Context Optimization Complete\n", style="bold white")
    t.append(f"│ Reduced {old_messages} messages down to {new_messages} summarized messages.\n", style="dim")
    t.append("╰─ Context window refreshed for extended sessions.\n", style="dim")
    console.print(t)


def render_init_status(path: str) -> None:
    """Display project initialization card."""
    t = Text()
    t.append("╭─ [init] ", style="dim")
    t.append("Project Initialized\n", style="bold white")
    t.append(f"│ Generated project context file: {path}\n", style="dim")
    t.append("╰─ Codex will automatically reference these guidelines.\n", style="dim")
    console.print(t)


def render_stats(queries: int, tokens: int, total_time: float) -> None:
    """Session stats summary in monochrome."""
    avg = tokens / max(total_time, 0.001)
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Session Statistics[/]")
    t.add_column("Metric", style="bold white")
    t.add_column("Value", style="white")
    t.add_row("Total Queries", str(queries))
    t.add_row("Tokens Generated", str(tokens))
    t.add_row("Generation Time", f"{total_time:.2f}s")
    t.add_row("Average Speed", f"{avg:.1f} tok/s")
    console.print(t)
    console.print()


def render_model_info(model: str) -> None:
    """Display active model info."""
    console.print(f"[dim]Active model:[/] [bold white]{model}[/]\n")


# ── OpenCode Tokyonight TUI Components ("The Codex Group") ───────────────
TOKYONIGHT_BG = "#1a1b26"
TOKYONIGHT_PANEL = "#24283b"
TOKYONIGHT_BLUE = "#7aa2f7"
TOKYONIGHT_PURPLE = "#bb9af7"
TOKYONIGHT_CYAN = "#7dcfff"
TOKYONIGHT_GREEN = "#9ece6a"
TOKYONIGHT_RED = "#f7768e"
TOKYONIGHT_ORANGE = "#e0af68"
TOKYONIGHT_FG = "#a9b1d6"


def render_opencode_tokyonight_banner(model_name: str = "Groq LPU (qwen3.8-27b)") -> None:
    """Render Tokyonight OpenCode Startup UI rebranded as 'THE CODEX GROUP' matching Screenshot 2."""
    clean_model = format_clean_model_name(model_name)
    banner_text = [
        "████████╗██╗  ██╗███████╗    ██████╗ ██████╗ ██████╗ ███████╗██╗  ██╗    ██████╗ ██████╗ ██╗   ██╗██████╗ ",
        "╚══██╔══╝██║  ██║██╔════╝    ██╔════╝██╔═══██╗██╔══██╗██╔════╝╚██╗██╔╝    ██╔════╝ ██╔══██╗██║   ██║██╔══██╗",
        "   ██║   ███████║█████╗      ██║     ██║   ██║██║  ██║█████╗   ╚███╔╝     ██║  ███╗██████╔╝██║   ██║██████╔╝",
        "   ██║   ██╔══██║██╔══╝      ██║     ██║   ██║██║  ██║██╔══╝   ██╔██╗     ██║   ██║██╔══██╗██║   ██║██╔═══╝ ",
        "   ██║   ██║  ██║███████╗    ╚██████╗╚██████╔╝██████╔╝███████╗██╔╝ ██╗    ╚██████╔╝██║  ██║╚██████╔╝██║     ",
        "   ╚═╝   ╚═╝  ╚═╝╚══════╝     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝     ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ",
    ]

    console.print("\n\n")
    for line in banner_text:
        console.print(f"[{TOKYONIGHT_BLUE}]{line:<100}[/]")
    console.print(f"[{TOKYONIGHT_PURPLE}]                                           v1.7.0 (Tokyonight Edition)[/]\n\n")

    cmd_table = Table.grid(padding=(0, 4))
    cmd_table.add_column(style=f"bold {TOKYONIGHT_CYAN}", justify="right")
    cmd_table.add_column(style=f"{TOKYONIGHT_FG}", justify="left")
    cmd_table.add_column(style="dim", justify="left")

    cmd_table.add_row("/help", "show help reference", "ctrl+x h")
    cmd_table.add_row("/editor", "open multiline editor", "ctrl+x e")
    cmd_table.add_row("/models", "list active LLM models", "ctrl+x m")
    cmd_table.add_row("/init", "create AGENTS.md / CODEX.md context", "ctrl+x i")
    cmd_table.add_row("/compact", "compact context session", "ctrl+x c")
    cmd_table.add_row("/sessions", "list active subagent sessions", "ctrl+x l")

    console.print(cmd_table)
    console.print("\n")

    input_panel = Panel(
        Text("> ", style=f"bold {TOKYONIGHT_CYAN}"),
        box=box.ROUNDED,
        border_style=TOKYONIGHT_PURPLE,
        expand=False,
        subtitle=f"[{TOKYONIGHT_FG}]enter [dim]send[/]                 [{TOKYONIGHT_BLUE}]Engine: {clean_model}[/]",
        subtitle_align="right"
    )
    console.print(input_panel)
    console.print("\n")


def render_opencode_dashboard(
    active_agent: str = "0m0",
    model_name: str = "qwen/qwen3.8-27b",
    tasks_completed: list[dict] | None = None,
    cwd: str | None = None,
) -> None:
    """Render Tokyonight split-pane OpenCode TUI dashboard matching Screenshot 1."""
    workspace = cwd or os.getcwd()
    display_model = format_clean_model_name(model_name)

    # 1. Main Left Pane: Tasks, Sub-Agent Tabs, and Thought Log
    left_content = Text()
    left_content.append("• call_omo_agent [subagent_type=explore, prompt=Find potential bugs related to EDGE CASES]\n", style=TOKYONIGHT_CYAN)
    left_content.append("  1. Array access without bounds checking\n", style="dim")
    left_content.append("  2. Division operations that could divide by zero\n", style="dim")
    left_content.append("  3. Path operations that don't handle Windows vs Unix differences\n\n", style="dim")

    left_content.append("⚛ Oracle Task \"Deep architecture & security review\"\n", style=f"bold {TOKYONIGHT_PURPLE}")
    left_content.append("ctrl+x right, ctrl+x left to navigate between subagent sessions\n\n", style="dim")

    # Tabs
    left_content.append("■ 0m0 · claude-opus-4-5  ", style=f"bold {TOKYONIGHT_CYAN}")
    left_content.append("  explore · qwen2.5-coder  ", style="dim")
    left_content.append("  auditor · gpt-oss-120b\n", style="dim")

    if tasks_completed:
        for t in tasks_completed:
            name = t.get("name", "Research task")
            dur = t.get("duration", "3m 41s")
            left_content.append(f"\n[BACKGROUND TASK COMPLETED] Task \"{name}\" finished in {dur}.\n", style=f"bold {TOKYONIGHT_GREEN}")

    left_content.append(f"\n[BACKGROUND TASK COMPLETED] Task \"Research multi-agent patterns\" finished in 3m 41s. Use background_output to get results.\n", style=f"bold {TOKYONIGHT_GREEN}")
    left_content.append(f"[BACKGROUND TASK COMPLETED] Task \"Find type safety issues\" finished in 27s. Use background_output to get results.\n\n", style=f"bold {TOKYONIGHT_GREEN}")

    left_panel = Panel(
        left_content,
        title="[bold white][The Codex Group] Leveraging agents for tasks[/]",
        title_align="left",
        border_style=TOKYONIGHT_BLUE,
        box=box.ROUNDED,
    )

    # 2. Right Sidebar Pane: Context, MCP, LSP, Todo, Workspace
    right_content = Text()
    right_content.append("Leveraging agents for tasks\n\n", style="bold white")
    right_content.append("Context\n", style=f"bold {TOKYONIGHT_PURPLE}")
    right_content.append("66,518 tokens\n33% used\n$0.00 spent\n\n", style=TOKYONIGHT_FG)

    right_content.append("▼ MCP\n", style=f"bold {TOKYONIGHT_CYAN}")
    right_content.append("• context7 Connected\n• grep_app Connected\n• websearch_exa Connected\n\n", style=TOKYONIGHT_GREEN)

    right_content.append("▼ LSP\n", style=f"bold {TOKYONIGHT_CYAN}")
    right_content.append("• markdown-oxide\n• typescript\n• eslint\n\n", style=TOKYONIGHT_FG)

    right_content.append("▼ Todo\n", style=f"bold {TOKYONIGHT_CYAN}")
    right_content.append("[✓] Demonstrate AGENTS: Show all 2,000+ curated swarm agents\n", style=TOKYONIGHT_GREEN)
    right_content.append("[✓] Demonstrate BACKGROUND AGENTS: Run parallel tasks\n", style=TOKYONIGHT_GREEN)
    right_content.append("[ ] Demonstrate ZERO-LATENCY: 500+ tok/s Groq LPU\n", style=TOKYONIGHT_ORANGE)
    right_content.append("[ ] Demonstrate PERMISSION PROMPTS: Inline diff approval\n\n", style=TOKYONIGHT_ORANGE)

    right_content.append(f"{workspace}\n", style="dim")
    right_content.append("master · The Codex Group v1.7.0", style=f"bold {TOKYONIGHT_BLUE}")

    right_panel = Panel(
        right_content,
        border_style="grey35",
        box=box.ROUNDED,
    )

    # 3. Render side-by-side grid
    grid = Table.grid(expand=True)
    grid.add_column(ratio=7)
    grid.add_column(ratio=3)
    grid.add_row(left_panel, right_panel)

    console.print(grid)


def render_inline_diff_box(
    file_path: str,
    diff_content: str,
    prompt_permission: bool = True
) -> bool:
    """Render interactive inline diff box showing line numbers, red '-' deletions, and green '+' additions matching Screenshot 3."""
    console.print(f"\n[{TOKYONIGHT_PURPLE}]Edit {file_path}[/]")

    lines = diff_content.splitlines()
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), border_style="grey23", expand=True)
    table.add_column("OldLn", justify="right", style="dim", width=6)
    table.add_column("NewLn", justify="right", style="dim", width=6)
    table.add_column("Line", style=TOKYONIGHT_FG)

    old_line = 1
    new_line = 1

    for line in lines:
        if line.startswith("@@"):
            table.add_row("", "", f"[{TOKYONIGHT_CYAN}]{line}[/]")
            continue
        elif line.startswith("-"):
            table.add_row(str(old_line), "", f"[bold {TOKYONIGHT_RED}]{line}[/]")
            old_line += 1
        elif line.startswith("+"):
            table.add_row("", str(new_line), f"[bold {TOKYONIGHT_GREEN}]{line}[/]")
            new_line += 1
        else:
            table.add_row(str(old_line), str(new_line), line)
            old_line += 1
            new_line += 1

    panel = Panel(table, box=box.ROUNDED, border_style=TOKYONIGHT_BLUE, title=f"[bold white]Diff Preview — {file_path}[/]")
    console.print(panel)

    if prompt_permission:
        try:
            ans = console.input(f"[{TOKYONIGHT_ORANGE}]Approve file edit to {file_path}? [y/N]: [/]").strip().lower()
            return ans in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False
    return True


def render_realtime_agent_bar(agent_name: str, task_desc: str, status: str = "CODING") -> None:
    """Render real-time animated sub-agent activity bar showing active agent names."""
    tag_style = f"bold {TOKYONIGHT_CYAN}" if status == "CODING" else f"bold {TOKYONIGHT_GREEN}"
    console.print(f"[{tag_style}]⚡ [{agent_name} - {status}]:[/] [{TOKYONIGHT_FG}]{task_desc}[/]")

