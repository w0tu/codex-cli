"""Terminal UI components for Codex — dynamic thinking, custom errors, monochrome aesthetic."""

import os
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.live import Live
from rich import box

console = Console()

# Same compact 5-row single-block monochrome pixel mascot
MASCOT_GRID = [
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0],
]
BLOCK = "█"
EMPTY = " "

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
THINKING_GLYPHS = ["◇", "◈", "◆", "◈"]
COGNITIVE_PHASES = [
    "Deconstructing query semantics",
    "Inspecting project context & AST",
    "Evaluating architectural constraints",
    "Formulating optimal implementation",
    "Synthesizing verified solution",
]


def render_mascot() -> Text:
    """Render the compact monochrome mascot."""
    t = Text()
    for i, row in enumerate(MASCOT_GRID):
        line = "".join(BLOCK if cell else EMPTY for cell in row)
        t.append(line, style="bold white")
        if i < len(MASCOT_GRID) - 1:
            t.append("\n")
    return t


def render_header(model_name: str = "qwen/qwen3.8-27b", cwd: str | None = None) -> Panel:
    """Same compact monochrome header matching Claude Code aesthetic."""
    mascot = render_mascot()
    workspace = cwd or os.getcwd()

    info = Text()
    info.append("CODEX", style="bold white")
    info.append(" v1.5.0\n", style="dim")
    info.append("model:    ", style="dim")
    info.append(f"{model_name}\n", style="white")
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


def calculate_thinking_duration(prompt: str) -> float:
    """Calculate realistic thinking duration based on prompt length and complexity."""
    words = len(prompt.split())
    prompt_lower = prompt.lower()
    complex_keywords = [
        "refactor", "architect", "implement", "explain", "analyze",
        "compare", "debug", "create", "build", "design", "algorithm",
        "difference", "optimize", "kernel", "protocol", "rewrite",
        "stack", "network", "system", "memory"
    ]
    matches = sum(1 for kw in complex_keywords if kw in prompt_lower)
    complexity_bonus = matches * 0.45

    if words < 6:
        base = 1.0
    elif words < 15:
        base = 1.8
    elif words < 40:
        base = 2.8
    else:
        base = 3.8

    return min(base + complexity_bonus, 5.0)


def animate_thinking(prompt: str = "") -> float:
    """Custom Claude-style thinking animation that scales duration with prompt complexity."""
    if not sys.stdout.isatty():
        return 0.0

    duration = calculate_thinking_duration(prompt)
    t0 = time.perf_counter()
    fps = 25
    steps = max(int(duration * fps), 15)
    delay = duration / steps

    with Live(console=console, refresh_per_second=fps, transient=True) as live:
        for i in range(steps):
            elapsed = time.perf_counter() - t0
            glyph = THINKING_GLYPHS[(i // 3) % len(THINKING_GLYPHS)]
            spin = SPINNER_FRAMES[i % len(SPINNER_FRAMES)]
            phase_idx = min(int((i / steps) * len(COGNITIVE_PHASES)), len(COGNITIVE_PHASES) - 1)
            phase = COGNITIVE_PHASES[phase_idx]

            t = Text()
            t.append(f"{spin} ", style="bold white")
            t.append(f"[{glyph}] ", style="white")
            t.append(f"Thinking ({elapsed:.1f}s)", style="bold white")
            t.append(f" ... {phase}", style="dim")
            live.update(t)
            time.sleep(delay)

    total_elapsed = time.perf_counter() - t0
    # Claude 3.7 style settled thought marker
    console.print(f"[dim italic]Thought for {total_elapsed:.1f}s[/dim italic]\n")
    return total_elapsed


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


def print_prompt(cwd: str) -> None:
    """Print the clean monochrome prompt header."""
    dirname = os.path.basename(cwd) or "~"
    console.print(f"[dim]╭─[/] [bold white]codex[/] [dim]in[/] [white]{dirname}[/]")


def render_tool_call(name: str, args_summary: str) -> None:
    """Display an agent tool call start card in monochrome."""
    t = Text()
    t.append("╭─ [tool] ", style="dim")
    t.append(f"{name}: ", style="bold white")
    t.append(args_summary, style="dim")
    console.print(t)


def render_tool_result(result: str, max_lines: int = 15) -> None:
    """Display output from an executed tool in monochrome."""
    lines = result.strip().splitlines()
    if not lines:
        console.print("[dim]│[/] [dim](no output)[/]")
    elif len(lines) > max_lines:
        for line in lines[:max_lines]:
            console.print(f"[dim]│[/] {line}")
        omitted = len(lines) - max_lines
        console.print(f"[dim]│[/] [dim italic]... ({omitted} more lines omitted)[/dim italic]")
    else:
        for line in lines:
            console.print(f"[dim]│[/] {line}")
    console.print("[dim]╰─[/]\n")


def print_telemetry(tokens: int, elapsed: float) -> None:
    """Clean, single-line monochrome telemetry footer."""
    tps = tokens / max(elapsed, 0.001)
    console.print(
        f"[dim]> {tokens} tokens | {elapsed:.2f}s | {tps:.1f} tok/s | Groq[/]\n"
    )


def render_diff(diff_output: str) -> None:
    """Display git diff output with syntax coloring."""
    if not diff_output.strip():
        console.print("[dim]No uncommitted changes in working tree.[/]\n")
        return
    syntax = Syntax(diff_output, "diff", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="[bold white]Git Diff[/]", box=box.ROUNDED, border_style="grey35"))
    console.print()


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


def render_help() -> None:
    """Display slash command reference table."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Slash Commands[/]")
    t.add_column("Command", style="bold white", no_wrap=True)
    t.add_column("Description", style="white")
    t.add_row("/help", "Show this reference guide")
    t.add_row("/clear", "Clear screen and redraw header")
    t.add_row("/memory", "Inspect 300+ message memory ledger & stats")
    t.add_row("/compact", "Compact conversation context to save tokens")
    t.add_row("/doctor", "Run diagnostic health check on environment")
    t.add_row("/cost", "Show token usage & cost statistics")
    t.add_row("/diff", "View colored git diff of current changes")
    t.add_row("/export [file]", "Export session conversation to markdown")
    t.add_row("/init", "Initialize CODEX.md project context guidelines")
    t.add_row("/git", "Show git status, active branch, and diffs")
    t.add_row("/github [repo]", "Connect, clone, or inspect GitHub repository")
    t.add_row("/tools", "List available PC agent tools")
    t.add_row("/model [name]", "Switch or view active Groq model")
    t.add_row("/stats", "Display session token and latency stats")
    t.add_row("/reset", "Clear conversation history")
    t.add_row("/exit, /quit", "Exit Codex terminal (or Ctrl+D)")
    console.print(t)
    console.print()


def render_tools_list() -> None:
    """Display available PC agent tools."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]PC Agent Tools[/]")
    t.add_column("Tool", style="bold white", no_wrap=True)
    t.add_column("Capability", style="white")
    t.add_row("bash", "Execute shell commands, run tests, install packages, etc.")
    t.add_row("read_file", "Inspect file contents with line numbers")
    t.add_row("write_file", "Create new files or overwrite existing files")
    t.add_row("edit_file", "Precise find-and-replace text edits inside files")
    t.add_row("list_dir", "Inspect directory structure and file sizes")
    t.add_row("grep_search", "Fast regex / string search across project files")
    t.add_row("find_files", "Locate files matching glob patterns (e.g. *.py)")
    t.add_row("git_status", "Inspect active branch, staged files, and git diff")
    t.add_row("github_connect", "Clone or connect any GitHub repository")
    t.add_row("recall_memory", "Recall discussions and facts from earlier in the session")
    console.print(t)
    console.print()


def render_doctor(model: str) -> None:
    """Run system diagnostics like Claude Code /doctor."""
    import platform
    import shutil
    import subprocess

    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Codex Doctor Diagnostics[/]")
    t.add_column("Component", style="bold white")
    t.add_column("Status", style="white")
    t.add_column("Details", style="dim")

    py_ver = platform.python_version()
    t.add_row("Python", "OK", f"v{py_ver}")

    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    t.add_row("Operating System", "OK", os_info)

    git_check = subprocess.run("git --version", shell=True, capture_output=True, text=True)
    git_status = "OK" if git_check.returncode == 0 else "MISSING"
    t.add_row("Git CLI", git_status, git_check.stdout.strip())

    cols, rows = shutil.get_terminal_size()
    t.add_row("Terminal Geometry", "OK", f"{cols} columns x {rows} rows")

    writable = os.access(os.getcwd(), os.W_OK)
    t.add_row("Workspace Access", "WRITABLE" if writable else "READ-ONLY", os.getcwd())

    t.add_row("Inference Model", "READY", model)

    console.print(t)
    console.print()


def render_cost(queries: int, total_tokens: int) -> None:
    """Display session token spend and estimated costs."""
    t = Table(box=box.ROUNDED, border_style="grey35", title="[bold white]Cost & Usage Tracker[/]")
    t.add_column("Metric", style="bold white")
    t.add_column("Value", style="white")
    t.add_row("Total Session Turns", str(queries))
    t.add_row("Total Tokens Processed", f"{total_tokens:,}")
    t.add_row("Provider Service Tier", "Groq LPU (On-Demand / Free)")
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
