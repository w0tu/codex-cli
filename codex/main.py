"""CLI controller for Codex — animated REPL with 300+ message memory, usage tracking, and 5-hour limit."""

import os
import sys
import json
import time
import re
import argparse
import subprocess
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession as PTSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import CompleteStyle

from codex import __version__
from codex.client import GroqClient, OllamaClient, AntigravityClient, get_system_prompt, DEFAULT_MODEL, save_api_key
from codex.memory import MemoryManager
from codex.usage import UsageTracker
from codex.skills import SkillsManager
from codex.agents import AgentRegistry
from codex.tools import run_tool, execute_git_status, execute_github_connect
from codex.ui import (
    console,
    clear_terminal,
    render_header,
    animate_thinking,
    render_thinking_block,
    render_error,
    print_prompt,
    render_tool_call,
    render_tool_result,
    print_telemetry,
    render_help,
    render_tools_list,
    render_skills_list,
    render_key_saved,
    render_usage_tab,
    render_doctor,
    render_cost,
    render_diff,
    render_export_status,
    render_memory_status,
    render_compact_summary,
    render_init_status,
    render_stats,
    render_model_info,
)
from rich.markdown import Markdown

HISTORY_PATH = Path.home() / ".codex_history"


# ── Slash command autocomplete menu ────────────────────────────────────
class SlashCommandCompleter(Completer):
    """Triggers an interactive menu when user types '/'."""

    COMMANDS = [
        ("/help", "Show help reference and available commands"),
        ("/clear", "Clear screen and redraw header"),
        ("/usage", "Display 5-hour / 300-prompt usage & quota monitor"),
        ("/onboard", "Run interactive auth setup and API key verification"),
        ("/doctor", "Run diagnostic health check on environment"),
        ("/verify", "Run automated test verification & anti-tamper lock"),
        ("/checkpoint", "Create, list, or rollback shadow git checkpoints"),
        ("/subagent", "Decompose prompt into autonomous Scout/Coder/Critic DAG"),
        ("/skills", "Manage or install community developer skills from GitHub"),
        ("/memory", "Inspect 300+ message memory ledger & stats"),
        ("/compact", "Compact session context to preserve tokens"),
        ("/context", "Display 10x10 token visualizer & context window breakdown"),
        ("/cost", "Show token spend and cost tracker"),
        ("/diff", "View colored git diff of current changes"),
        ("/export", "Export session conversation to markdown file"),
        ("/init", "Initialize CODEX.md project context file"),
        ("/git", "Show git repository branch and status"),
        ("/github", "Connect or clone a GitHub repository"),
        ("/tools", "List available PC agent tools"),
        ("/theme", "Switch or list UI color themes (monochrome, nord, dracula, matrix)"),
        ("/editor", "Open external $EDITOR for multiline prompt authoring"),
        ("/notify", "Toggle desktop notifications and terminal bell on/off"),
        ("/model", "Switch active model or list live models (/model list)"),
        ("/modal", "Open interactive Antigravity model selection modal"),
        ("/mascot", "Display animated mascot showcase with moving eyes"),
        ("/stats", "Show session token usage and stats"),
        ("/panel", "Open interactive Cyberpunk telemetry & Groq usage dashboard"),
        ("/marketing", "Generate viral Instagram Reel package & Google Flow video prompts"),
        ("/lawyer", "Run autonomous legal counsel audit on contracts and IP compliance"),
        ("/legal", "Alias for /lawyer contract audit"),
        ("/swarm", "Enter the 45,000+ Agent Swarm Command Center area"),
        ("/grokbot", "Enter the 45,000+ Agent Swarm Command Center area"),
        ("/agents", "Search and list 220+ specialized domain engineering agents"),
        ("/agent", "Activate a specialized agent persona (/agent <name>)"),
        ("/reach", "Access 16+ platforms via Agent Reach router (/reach doctor|search|url|...)"),
        ("/offline", "Switch to 100% offline local Ollama agent mode"),
        ("/local", "Switch to 100% offline local Ollama agent mode"),
        ("/antigravity", "Forward tasks and prompts to Google Antigravity CLI"),
        ("/agy", "Shortcut to forward tasks to Google Antigravity CLI"),
        ("/mouse", "Desktop mouse automation (move, click, drag, scroll, pos)"),
        ("/wifi", "Inspect or connect WiFi and network status"),
        ("/research", "Run deep multi-platform internet research"),
        ("/run", "Directly execute terminal shell command on PC"),
        ("/save", "Directly write and save file to local PC disk"),
        ("/docs", "Save text or report directly into ~/Documents folder"),
        ("/pointer", "Spawn smooth animated floating second agent mouse cursor"),
        ("/screen", "Capture real-time desktop screen frame with ffmpeg x11grab"),
        ("/groq", "Automated Groq keys retrieval, visual mouse glide, and ~/Documents save"),
        ("/online", "Switch back to online cloud inference (Cloud Native Zero-Latency)"),
        ("/cloud", "Switch to online cloud inference (Cloud Native Zero-Latency)"),
        ("/dashboard", "Open the Stage 2 OpenCode TUI dashboard"),
        ("/tui", "Open the Stage 2 OpenCode TUI dashboard"),
        ("/welcome", "Return to Stage 1 Tokyonight welcome screen"),
        ("/sessions", "List active subagent sessions and status"),
        ("/reset", "Clear conversation history context"),
        ("/exit", "Exit Codex terminal"),
    ]

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            query = text.lower()
            for cmd, desc in self.COMMANDS:
                if cmd.lower().startswith(query):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display=cmd,
                        display_meta=desc
                    )


MENU_STYLE = Style.from_dict({
    "completion-menu.completion": "bg:#1e1e1e #ffffff",
    "completion-menu.completion.current": "bg:#ffffff #000000 bold",
    "completion-menu.meta.completion": "bg:#1e1e1e #888888",
    "completion-menu.meta.completion.current": "bg:#ffffff #444444 italic",
    "scrollbar.background": "bg:#1e1e1e",
    "scrollbar.button": "bg:#555555",
})


# ── Session state with 300+ message memory manager ──────────────────────
class Session:
    def __init__(self):
        self.memory = MemoryManager()
        self.usage_tracker = UsageTracker()
        self.total_tokens = 0
        self.total_time = 0.0
        self.total_queries = 0
        self.notifications_enabled = False
        self.tui_stage = 1  # 1 = Stage 1 (Tokyonight Welcome Screen), 2 = Stage 2 (Active Workspace TUI Dashboard)

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Bounded context window compiled from 300+ message history and knowledge base."""
        return self.memory.get_context_window(get_system_prompt())

    def add_user(self, text: str):
        self.memory.add_message("user", text)

    def add_assistant(self, text: str, tool_calls=None):
        extra = {}
        if tool_calls:
            extra["tool_calls"] = tool_calls
        self.memory.add_message("assistant", text, **extra)

    def add_tool_result(self, tool_call_id: str, content: str):
        self.memory.add_message("tool", content, tool_call_id=tool_call_id)

    def reset(self):
        self.memory.clear()
        self.tui_stage = 1

    def record(self, tokens: int, elapsed: float):
        self.total_tokens += tokens
        self.total_time += elapsed
        self.total_queries += 1
        self.usage_tracker.record_request()

    def compact(self) -> tuple[int, int]:
        """Compact conversation history by retaining system prompt and recent turns."""
        old_count = len(self.memory.history)
        self.memory._consolidate_older_messages()
        return old_count, len(self.memory.history)

    def export(self, filename: str = "") -> str:
        """Export all session messages across the entire history to a markdown file."""
        out_name = filename.strip() if filename.strip() else f"codex_session_{int(time.time())}.md"
        out_path = Path(out_name).resolve()
        lines = [
            "# Codex AI Session Export\n",
            f"- Session ID: `{self.memory.session_id}`\n",
            f"- Total Messages Archived: {len(self.memory.history)}\n",
            f"- Exported at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n"
        ]
        for m in self.memory.history:
            role = m.get("role", "unknown").upper()
            if role == "SYSTEM":
                continue
            content = m.get("content", "")
            lines.append(f"### {role}\n\n{content}\n\n---\n")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return str(out_path)


# ── Autonomous Agent Execution Loop ─────────────────────────────────────
def execute_turn(session: Session, client: GroqClient, prompt_text: str = "", max_steps: int = 6) -> None:
    """Run an agent turn with quota check, dynamic prompt thinking, and total prompt-to-finish timing."""
    # 1. Quota Check (300 requests / 5-hour rolling limit)
    allowed, reason, wait_secs = session.usage_tracker.check_limit()
    if not allowed:
        render_error("Request Quota Limit Reached", reason, "Please wait until the 5-hour rolling window replenishes.")
        return

    prompt_start_time = time.perf_counter()
    turn_tokens = 0

    if getattr(session, "tui_stage", 1) == 2 and prompt_text:
        from codex.ui import render_stage2_turn_header
        render_stage2_turn_header(query_text=prompt_text, model_name=client.model)

    for _ in range(max_steps):
        try:
            from codex.security import SecretScrubber
            scrubbed_msgs = SecretScrubber.scrub_messages(session.messages)

            # Direct Zero-Latency token stream if tools are not required
            user_text = ""
            for m in reversed(scrubbed_msgs):
                if m.get("role") == "user":
                    user_text = m.get("content", "").lower()
                    break
            explicit_tool_directives = [
                "run command", "run bash", "run in terminal", "execute command",
                "create file", "write to file", "edit file", "save to file",
                "read file", "inspect file", "search files", "git commit",
                "git diff", "git status", "run tests", "run pytest", "run linter",
                "search codebase", "grep for"
            ]
            needs_tools = (
                any(d in user_text for d in explicit_tool_directives)
                or any(m.get("role") == "tool" for m in scrubbed_msgs)
                or user_text.startswith("!")
                or user_text.startswith("bash ")
                or user_text.startswith("run ")
            )

            if not needs_tools and hasattr(client, "stream_chat"):
                chunks = []
                gen_start_time = None
                token_count = 0
                for chunk in client.stream_chat(scrubbed_msgs):
                    if gen_start_time is None:
                        gen_start_time = time.perf_counter()
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    chunks.append(chunk)
                    token_count += 1
                sys.stdout.write("\n\n")
                sys.stdout.flush()
                full_resp = "".join(chunks)
                session.add_assistant(full_resp)
                
                # Retrieve actual Groq usage tokens if available
                last_usage = getattr(getattr(client, "cloud_client", None), "last_usage", None)
                if last_usage and "completion_tokens" in last_usage:
                    turn_tokens = last_usage["completion_tokens"]
                else:
                    turn_tokens = max(token_count, len(full_resp) // 4)

                gen_elapsed = (time.perf_counter() - gen_start_time) if gen_start_time else (time.perf_counter() - prompt_start_time)
                session.record(turn_tokens, gen_elapsed)
                print_telemetry(turn_tokens, gen_elapsed)
                return

            resp = client.chat_turn(scrubbed_msgs)
        except Exception as e:
            err_str = str(e).lower()
            if "rate_limit" in err_str or "429" in err_str:
                render_error(
                    "Rate Limit Exceeded (HTTP 429)",
                    "Token rate limit reached for the active model tier.",
                    "Wait a few seconds before re-trying, or switch models with /model."
                )
            elif "401" in err_str or "authentication" in err_str or "api_key" in err_str:
                render_error(
                    "Authentication Failed (HTTP 401)",
                    "Invalid, missing, or expired API key.",
                    "Paste your API key directly into the terminal or configure ~/.codex/config.json"
                )
            elif "404" in err_str or "not_found" in err_str:
                render_error(
                    "Model Unavailable (HTTP 404)",
                    f"The requested model '{client.model}' is currently unavailable.",
                    "Use /model to switch to an active model (e.g. /model qwen/qwen3.8-27b)"
                )
            elif "connection" in err_str or "timeout" in err_str:
                render_error(
                    "Network Connection Failure",
                    "Unable to establish connection to inference endpoint.",
                    "Check network connectivity and DNS resolution."
                )
            else:
                render_error("Inference Error", str(e), "Verify prompt input and active model status.")
            return

        usage = getattr(resp, "usage", None)
        if usage:
            turn_tokens += getattr(usage, "completion_tokens", 0) or getattr(usage, "total_tokens", 0)

        choice = resp.choices[0]
        msg = choice.message

        if msg.tool_calls:
            if msg.content:
                raw_c = msg.content.strip()
                thought_text = ""
                if "<think>" in raw_c and "</think>" in raw_c:
                    thought_text = raw_c.split("</think>", 1)[0].replace("<think>", "").strip()
                elif "<think>" in raw_c:
                    thought_text = raw_c.replace("<think>", "").strip()
                if thought_text:
                    render_thinking_block(thought_text, elapsed=time.perf_counter() - prompt_start_time)

            tool_calls_dict = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in msg.tool_calls
            ]
            session.add_assistant(msg.content or "", tool_calls=tool_calls_dict)

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}

                # Record file actions in memory ledger
                if tool_name in ("write_file", "edit_file", "read_file") and "path" in args:
                    session.memory.record_file_op(args["path"], tool_name)

                # Interactive permission prompt & diff rendering for file edits
                if tool_name in ("write_file", "edit_file"):
                    target_path = args.get("path", "")
                    content_to_write = args.get("content") or args.get("new_string") or ""
                    old_content = ""
                    if target_path and Path(target_path).exists():
                        try:
                            old_content = Path(target_path).read_text(encoding="utf-8", errors="replace")
                        except Exception:
                            pass
                    import difflib
                    diff_lines = list(difflib.unified_diff(old_content.splitlines(), content_to_write.splitlines(), lineterm=""))
                    diff_text = "\n".join(diff_lines) or f"+ {content_to_write[:200]}"
                    from codex.ui import render_inline_diff_box
                    approved = render_inline_diff_box(target_path, diff_text, prompt_permission=True)
                    if not approved:
                        result = f"Error: User denied permission to modify {target_path}"
                        session.add_tool_result(tc.id, result)
                        continue

                summary = args.get("command") or args.get("path") or args.get("repo") or args.get("query") or args.get("url") or args.get("topic") or json.dumps(args)
                tool_label = f"{tool_name} {summary}"

                from codex.terminal import InlineToolSpinner
                with InlineToolSpinner(tool_label) as spinner:
                    result = run_tool(tool_name, args)
                    is_err = result.startswith("Error:") or result.startswith("Security Error:")
                    stderr_preview = result if is_err else None
                    spinner.finish(success=not is_err, summary=tool_label, stderr=stderr_preview)

                session.add_tool_result(tc.id, result)
        else:
            content = msg.content or ""
            thought_text = ""
            if "<think>" in content and "</think>" in content:
                thought_part, content = content.split("</think>", 1)
                thought_text = thought_part.replace("<think>", "").strip()
            elif "</think>" in content:
                thought_part, content = content.split("</think>", 1)
                thought_text = thought_part.replace("<think>", "").strip()

            if thought_text:
                render_thinking_block(thought_text, elapsed=time.perf_counter() - prompt_start_time)

            content = content.strip()
            if content.endswith("</"):
                content = content[:-2].strip()
            elif content.endswith("</think"):
                content = content[:-7].strip()
            if content:
                console.print(Markdown(content))
                session.add_assistant(content)
            break

    # Total timer from entering prompt to finished
    total_turn_elapsed = time.perf_counter() - prompt_start_time
    session.record(turn_tokens, total_turn_elapsed)
    print_telemetry(turn_tokens, total_turn_elapsed)

    if getattr(session, "notifications_enabled", False):
        try:
            sys.stdout.write("\a")
            sys.stdout.flush()
            subprocess.run(
                ["notify-send", "Codex AI", f"Agent turn completed in {total_turn_elapsed:.1f}s ({turn_tokens} tokens)"],
                capture_output=True,
                timeout=2,
            )
        except Exception:
            pass


# ── Direct mode ─────────────────────────────────────────────────────────
def run_direct(prompt: str, client: Any) -> None:
    clean_prompt = prompt.strip()
    if clean_prompt == "/usage":
        from codex.metrics_db import metrics_db
        sys.stdout.write("\n" + metrics_db.render_block_telemetry_card() + "\n\n")
        sys.stdout.flush()
        return

    if clean_prompt == "/screen":
        from codex.screen_agent import window_manager
        res = window_manager.capture_screen_frame()
        if res.get("success"):
            console.print(f"\n[bold green]✦ Screen Frame Captured:[/] {res.get('path')} ({res.get('geometry')}, {res.get('size')} bytes)\n")
        else:
            console.print(f"\n[bold red]Screen capture failed:[/] {res.get('message')}\n")
        return

    if clean_prompt.startswith("/pointer"):
        from codex.screen_agent import agent_pointer
        ok = agent_pointer.glide_to(target_x=900, target_y=550, badge="✦ CODEX AGENT MOUSE", click=True)
        console.print(f"\n[bold green]✦ Floating Agent Mouse Activated:[/] Gliding across desktop ({'OK' if ok else 'FAILED'})\n")
        return

    if clean_prompt == "/groq":
        from codex.screen_agent import window_manager
        console.print("\n[bold cyan]✦ Executing Groq Keys Desktop Automation...[/]")
        res = window_manager.run_groq_keys_automation()
        console.print(f"[bold green]✦ {res.get('message')}[/]")
        console.print(f"  • Primary Key: [bold white]{res.get('primary_key')}[/]")
        console.print(f"  • Total Keys: [cyan]{res.get('keys_found')}[/]")
        console.print(f"  • Document: [yellow]{res.get('documents_file')}[/]\n")
        return

    if clean_prompt.startswith("/subagent"):
        from codex.subagents import MultiAgentStateMachine
        parts = clean_prompt.split(maxsplit=1)
        task_prompt = parts[1].strip() if len(parts) > 1 else "Perform codebase verification audit"
        console.print(f"\n[bold white]✦ Launching Multi-Agent State Machine (Planner ➔ Coder ➔ Auditor ➔ Executor)...[/]\n")
        sm = MultiAgentStateMachine()
        def code_gen(step):
            p = f"Write python code for: {step.description}\nTarget file: {step.target_path}\nOutput valid raw python code."
            chunks = []
            for c in client.stream_chat([{"role": "user", "content": p}], max_tokens=300):
                chunks.append(c)
            raw = "".join(chunks).strip()
            if "```python" in raw:
                raw = raw.split("```python", 1)[1].split("```", 1)[0].strip()
            elif "```" in raw:
                raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
            return raw
        sm.run_workflow(task_prompt, code_generator=code_gen, logger=lambda m: console.print(m))
        return

    session = Session()
    session.add_user(prompt)
    from codex.banner_renderer import display_welcome_banner
    display_welcome_banner(model_label=client.model, status_text="ONLINE | ZERO-LATENCY PINNED", cwd=os.getcwd())
    execute_turn(session, client, prompt_text=prompt)




# ── Interactive REPL ────────────────────────────────────────────────────
def run_repl(client: Any) -> None:
    # 1. Onboarding & First-Boot Profiling
    from codex.profiler import run_first_boot_profiling
    profile = run_first_boot_profiling(interactive=True)
    if profile.get("recommended_model"):
        if hasattr(client, "local_client"):
            client.local_client.set_model(profile["recommended_model"])
        elif isinstance(client, OllamaClient) and not getattr(client, "_explicit_model_flag", False):
            client.set_model(profile["recommended_model"])

    # 2. Directory Trust Gatekeeper
    from codex.gatekeeper import gatekeeper
    gatekeeper.check_and_prompt(os.getcwd(), interactive=True)

    session = Session()

    # 3. Stage 1: Tokyonight OpenCode TUI Welcome Screen ("THE CODEX GROUP")
    clear_terminal()
    from codex.ui import render_opencode_tokyonight_banner, format_clean_model_name
    render_opencode_tokyonight_banner(model_name=client.model)

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    pt = PTSession(
        history=FileHistory(str(HISTORY_PATH)),
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        complete_style=CompleteStyle.COLUMN,
        style=MENU_STYLE,
    )

    from prompt_toolkit.formatted_text import HTML, ANSI

    while True:
        try:
            clean_model = format_clean_model_name(client.model)
            if session.tui_stage == 1:
                prompt_str = "\x1b[38;2;125;207;255m> \x1b[0m"
                def get_toolbar():
                    return HTML(
                        f'<style fg="#7aa2f7">enter</style> <style fg="#565f89">send</style>   '
                        f'<style fg="#bb9af7">ctrl+x</style> <style fg="#565f89">shortcuts</style>   '
                        f'<style fg="#7dcfff">/</style> <style fg="#565f89">commands</style>       '
                        f'│ <style fg="#9ece6a">Codex Native · {clean_model}</style>'
                    )
            else:
                from codex.ui import format_prompt_string
                prompt_str = format_prompt_string(os.getcwd())
                def get_toolbar():
                    return HTML(
                        f'<style fg="#7aa2f7">The Codex Group v1.7.0</style> <style fg="#565f89">│</style> '
                        f'<style fg="#9ece6a">Codex Native · {clean_model}</style> <style fg="#565f89">│</style> '
                        f'<style fg="#bb9af7">tab</style> <style fg="#565f89">BUILD MODE</style>'
                    )

            user_input = pt.prompt(ANSI(prompt_str), bottom_toolbar=get_toolbar).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("[dim]Goodbye.[/]")
            break

        if not user_input:
            continue

        # Two-Stage TUI Transition:
        # As soon as the user says anything (enters query or command), transition to Stage 2 Active TUI Dashboard!
        if session.tui_stage == 1 and user_input != "/welcome":
            session.tui_stage = 2
            clear_terminal()
            from codex.ui import render_opencode_dashboard
            render_opencode_dashboard(
                active_agent="0m0",
                model_name=client.model,
                cwd=os.getcwd(),
                query_title=user_input
            )

        # Automatic API key capture & global persistence
        key_match = re.search(r"\b(gsk_[a-zA-Z0-9]{20,})\b", user_input)
        if key_match:
            captured_key = key_match.group(1)
            cfg_path = save_api_key(captured_key)
            client.set_api_key(captured_key)
            masked = captured_key[:7] + "*" * (len(captured_key) - 11) + captured_key[-4:]
            render_key_saved(masked, str(cfg_path))

            # Strip the key from user input
            cleaned_input = re.sub(r"\b" + re.escape(captured_key) + r"\b", "", user_input).strip()
            norm = cleaned_input.lower()
            if not cleaned_input or norm in [
                "api key", "my key", "key", "groq key", "groq_api_key",
                "here is my key", "here is the key", "api key:", "key:"
            ] or all(w in ["my", "key", "api", "is", "here", "the", "groq", "set", ":", "="] for w in norm.split()):
                continue
            user_input = cleaned_input

        # Slash commands
        if user_input == "/welcome":
            session.tui_stage = 1
            clear_terminal()
            from codex.ui import render_opencode_tokyonight_banner
            render_opencode_tokyonight_banner(model_name=client.model)
            continue

        if user_input in ["/dashboard", "/tui", "/opencode"]:
            session.tui_stage = 2
            clear_terminal()
            from codex.ui import render_opencode_dashboard
            render_opencode_dashboard(
                active_agent="0m0",
                model_name=client.model,
                cwd=os.getcwd(),
                query_title="The Codex Group Workspace Dashboard"
            )
            continue

        if user_input == "/sessions":
            from codex.ui import render_sessions_catalog
            render_sessions_catalog()
            continue

        if user_input.startswith("/mouse"):
            parts = user_input.split()
            subcmd = parts[1].lower() if len(parts) > 1 else "pos"
            from codex.mouse_control import mouse_controller
            if subcmd in ("pos", "position"):
                pos = mouse_controller.get_position()
                sz = mouse_controller.get_screen_size()
                console.print(f"\n[bold cyan]✦ Mouse Position:[/] x={pos.get('x')}, y={pos.get('y')} (Screen: {sz.get('width')}x{sz.get('height')})\n")
            elif subcmd == "move" and len(parts) >= 4:
                try:
                    mx, my = int(parts[2]), int(parts[3])
                    res = mouse_controller.move_to(mx, my, smooth=True)
                    console.print(f"\n[bold green]✦ {res.get('message')}[/]\n")
                except ValueError:
                    console.print("[dim]Usage: /mouse move <x> <y>[/]\n")
            elif subcmd == "click":
                btn = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
                res = mouse_controller.click(button=btn)
                console.print(f"\n[bold green]✦ {res.get('message')}[/]\n")
            elif subcmd == "scroll" and len(parts) >= 3:
                direction = parts[2].lower()
                res = mouse_controller.scroll(direction=direction)
                console.print(f"\n[bold green]✦ {res.get('message')}[/]\n")
            elif subcmd == "screen":
                sz = mouse_controller.get_screen_size()
                console.print(f"\n[bold cyan]✦ Screen Geometry:[/] {sz.get('width')}x{sz.get('height')}\n")
            else:
                console.print("[dim]Usage: /mouse [pos | move <x> <y> | click [1|2|3] | scroll <up|down> | screen][/]\n")
            continue

        if user_input.startswith("/wifi"):
            parts = user_input.split(maxsplit=2)
            if len(parts) >= 2 and parts[1].lower() == "connect":
                ssid = parts[2].strip() if len(parts) > 2 else ""
                if ssid:
                    from codex.network import connect_wifi
                    console.print(f"[dim]Connecting to WiFi '{ssid}'...[/]")
                    msg = connect_wifi(ssid)
                    console.print(f"[white]{msg}[/]\n")
                else:
                    console.print("[dim]Usage: /wifi connect <SSID>[/]\n")
            else:
                from codex.network import check_wifi_status
                st = check_wifi_status()
                conn_color = "bold green" if st.get("connected") else "bold red"
                inet_color = "bold green" if st.get("internet") else "bold red"
                console.print(f"\n[{conn_color}]✦ WiFi Status: {'CONNECTED' if st.get('connected') else 'DISCONNECTED'}[/]")
                console.print(f"  • SSID: [bold white]{st.get('ssid')}[/]")
                console.print(f"  • Interface: [cyan]{st.get('interface')}[/]")
                console.print(f"  • Signal: [white]{st.get('signal')}%[/]")
                console.print(f"  • Local IP: [cyan]{st.get('ip')}[/]")
                console.print(f"  • Internet: [{inet_color}]{'ONLINE' if st.get('internet') else 'OFFLINE'}[/]\n")
            continue

        if user_input.startswith("/research"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                q = parts[1].strip()
                console.print(f"\n[bold cyan]✦ Running Deep Internet Research:[/] [white]{q}[/]\n")
                from codex.network import run_deep_research
                report = run_deep_research(q)
                console.print(Markdown(report))
                console.print()
            else:
                console.print("[dim]Usage: /research <topic or query>[/]\n")
            continue

        if user_input.startswith("/run"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                cmd_to_run = parts[1].strip()
                console.print(f"\n[bold yellow]✦ Executing on PC:[/] [dim]{cmd_to_run}[/]\n")
                from codex.tools import execute_bash
                res = execute_bash(cmd_to_run)
                console.print(res)
                console.print()
            else:
                console.print("[dim]Usage: /run <shell command>[/]\n")
            continue

        if user_input.startswith("/save"):
            parts = user_input.split(maxsplit=2)
            if len(parts) >= 3:
                target_f = parts[1].strip()
                content_f = parts[2]
                from codex.tools import execute_write_file
                res = execute_write_file(target_f, content_f)
                console.print(f"\n[bold green]✦ {res}[/]\n")
            else:
                console.print("[dim]Usage: /save <filepath> <content>[/]\n")
            continue

        if user_input.startswith("/docs"):
            parts = user_input.split(maxsplit=2)
            if len(parts) >= 3:
                target_f = parts[1].strip()
                content_f = parts[2]
                from codex.screen_agent import window_manager
                res = window_manager.save_to_documents(target_f, content_f)
                console.print(f"\n[bold green]✦ {res.get('message')}[/]\n")
            else:
                console.print("[dim]Usage: /docs <filename> <content>[/]\n")
            continue

        if user_input == "/screen":
            from codex.screen_agent import window_manager
            res = window_manager.capture_screen_frame()
            if res.get("success"):
                console.print(f"\n[bold green]✦ Screen Frame Captured:[/] {res.get('path')} ({res.get('geometry')}, {res.get('size')} bytes)\n")
            else:
                console.print(f"\n[bold red]Screen capture failed:[/] {res.get('message')}\n")
            continue

        if user_input.startswith("/pointer"):
            from codex.screen_agent import agent_pointer
            ok = agent_pointer.glide_to(target_x=900, target_y=550, badge="✦ CODEX AGENT MOUSE", click=True)
            console.print(f"\n[bold green]✦ Floating Agent Mouse Activated:[/] Gliding across desktop ({'OK' if ok else 'FAILED'})\n")
            continue

        if user_input == "/groq":
            from codex.screen_agent import window_manager
            console.print("\n[bold cyan]✦ Executing Groq Keys Desktop Automation...[/]")
            res = window_manager.run_groq_keys_automation()
            console.print(f"[bold green]✦ {res.get('message')}[/]")
            console.print(f"  • Primary Key: [bold white]{res.get('primary_key')}[/]")
            console.print(f"  • Total Keys: [cyan]{res.get('keys_found')}[/]")
            console.print(f"  • Document: [yellow]{res.get('documents_file')}[/]\n")
            continue

        if user_input.startswith("/antigravity") or user_input.startswith("/agy"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                prompt_agy = parts[1].strip()
                console.print(f"\n[bold magenta]✦ Delegating Complex Task to Google Antigravity...[/]\n")
                from codex.antigravity_bridge import delegate_to_antigravity
                res = delegate_to_antigravity(prompt_agy)
                console.print(res)
                console.print()
                continue
            else:
                from codex.client import AntigravityClient
                client = AntigravityClient()
                console.print("\n[bold white]✦ Connected to Google Antigravity CLI[/] (prompts will bridge to agy)\n")
                continue

        if user_input == "/clear":
            clear_terminal()
            if session.tui_stage == 1:
                from codex.ui import render_opencode_tokyonight_banner
                render_opencode_tokyonight_banner(model_name=client.model)
            else:
                from codex.ui import render_opencode_dashboard
                render_opencode_dashboard(model_name=client.model)
            continue

        if user_input == "/help":
            render_help()
            continue

        if user_input == "/usage":
            from codex.metrics_db import metrics_db
            sys.stdout.write("\n" + metrics_db.render_block_telemetry_card() + "\n\n")
            sys.stdout.flush()
            continue

        if user_input in ["/cloud", "/remote"]:
            if hasattr(client, "set_mode"):
                client.set_mode("cloud")
                console.print(f"\n[bold cyan]✦ Mode switched to Cloud ([/][bold white]{client.model}[/][bold cyan]). 120B high-precision reasoning active.[/]\n")
            continue

        if user_input in ["/local", "/ollama"]:
            if hasattr(client, "set_mode"):
                client.set_mode("local")
                console.print(f"\n[bold yellow]✦ Mode switched to Local Ollama ([/][bold white]{client.model}[/][bold yellow]).[/]\n")
            continue

        if user_input.startswith("/mode"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1 and hasattr(client, "set_mode"):
                new_m = client.set_mode(parts[1])
                console.print(f"\n[bold green]✦ Mode set to: {new_m} ({client.model})[/]\n")
            else:
                curr_mode = getattr(client, "mode", "auto")
                console.print(f"\n[bold white]Current Mode: {curr_mode} | Active Model: {client.model}[/]")
                console.print("[dim]Use /cloud, /local, or /mode [auto|cloud|local] to switch modes.[/]\n")
            continue

        if user_input == "/onboard":
            from codex.profiler import run_first_boot_profiling
            profile = run_first_boot_profiling(interactive=True, force=True)
            if hasattr(client, "local_client") and profile.get("recommended_model"):
                client.local_client.set_model(profile["recommended_model"])
            elif isinstance(client, OllamaClient) and profile.get("recommended_model"):
                client.set_model(profile["recommended_model"])
            continue

        if user_input.startswith("/skills"):
            parts = user_input.split(maxsplit=2)
            if len(parts) >= 2 and parts[1].lower() == "install":
                if len(parts) >= 3:
                    repo_target = parts[2].strip()
                    console.print(f"[dim]Installing skill from {repo_target}...[/]")
                    res = SkillsManager().install_from_github(repo_target)
                    console.print(f"[white]{res}[/]\n")
                else:
                    console.print("[dim]Usage: /skills install <owner/repo or github-url>[/]\n")
            elif len(parts) >= 2 and parts[1].lower() == "remove":
                if len(parts) >= 3:
                    skill_target = parts[2].strip()
                    res = SkillsManager().remove_skill(skill_target)
                    console.print(f"[white]{res}[/]\n")
                else:
                    console.print("[dim]Usage: /skills remove <skill-name>[/]\n")
            else:
                skills = SkillsManager().list_skills()
                render_skills_list(skills)
            continue

        if user_input in ("/panel", "/dashboard"):
            from codex.panel import display_panel_once
            display_panel_once()
            continue

        if user_input.startswith("/marketing") or user_input.startswith("/insta"):
            parts = user_input.split(maxsplit=1)
            topic = parts[1].strip() if len(parts) > 1 else "Autonomous AI Coding Agents in Linux Terminal"
            from codex.marketing import InstagramAutomationEngine, render_marketing_campaign
            console.print(f"[bold cyan]✦ Synthesizing Instagram Viral Campaign & Google Flow Prompts for: '{topic}'...[/]")
            camp = InstagramAutomationEngine.create_campaign(topic)
            render_marketing_campaign(camp)
            continue

        if user_input.startswith("/lawyer") or user_input.startswith("/legal"):
            parts = user_input.split(maxsplit=1)
            contract = parts[1].strip() if len(parts) > 1 else "Standard SaaS Developer Agreement with unlimited indemnification and non-compete."
            from codex.lawyers import AutonomousLegalCounsel, render_legal_audit
            console.print(f"[bold cyan]✦ Convening Autonomous Legal Counsel Contract Audit...[/]")
            audit = AutonomousLegalCounsel.audit_contract(contract)
            render_legal_audit(audit)
            continue

        if user_input.startswith("/agents"):
            parts = user_input.split(maxsplit=1)
            registry = AgentRegistry()
            query = parts[1].strip() if len(parts) > 1 else None
            matches = registry.list_agents(query=query)
            console.print(f"\n[bold green]✦ MASSIVE 45,046 ACTIVE AGENTS SWARM MATRIX[/] [dim]({len(matches)} matching)[/]:")
            console.print("[dim]Structure: Tier 1 Commander (#0) ➔ 45 Cluster Managers (#1-#45) ➔ 45,000 Workers (#46-#45045)[/]")
            for a in matches[:28]:
                t_str = f"Tier {a.get('tier', 3)}"
                console.print(f"  [bold cyan]{a['name']:<32}[/] [dim]({t_str} - {a.get('category', 'General')})[/] - {a.get('description', '')[:70]}...")
            if len(matches) > 28:
                console.print(f"\n[dim]...and {len(matches)-28} more agents. Filter with /agents <query> or activate any node with /agent <id|name>[/]\n")
            else:
                console.print("\n[dim]Activate any agent with: /agent <id|name> (e.g. /agent 0, /agent 15, /agent marketing, /agent react-architect)[/]\n")
            continue

        if user_input.startswith("/agent"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                target = parts[1].strip()
                registry = AgentRegistry()
                found = registry.get_agent(target)
                if found:
                    session.add_user(f"[Directive: Adopt persona and guidelines of {found['name']}: {found['system_prompt']}]")
                    console.print(f"\n[bold white]✦ Activated Agent Persona:[/] [bold cyan]{found['role']}[/]")
                    console.print(f"[dim]{found['description']}[/]\n")
                else:
                    console.print(f"[dim]Agent '{target}' not found. Type /agents to view all 45,046 available agents.[/]\n")
            else:
                console.print("[dim]Usage: /agent <id|name> (e.g. /agent 0, /agent 1, /agent marketing, /agent react-architect)[/]\n")
            continue

        if user_input.startswith("/swarm") or user_input.startswith("/grokbot"):
            from codex.swarm import run_swarm_area
            run_swarm_area(client=client)
            continue

        if user_input.startswith("/offline") or user_input.startswith("/local"):
            parts = user_input.split(maxsplit=1)
            off_model = parts[1] if len(parts) > 1 else "qwen2.5-coder:1.5b"
            if hasattr(client, "set_mode"):
                client.set_mode("local")
                if hasattr(client, "local_client"):
                    client.local_client.set_model(off_model)
            else:
                client = OllamaClient(model=off_model)
            console.print(f"\n[bold white]✦ Switched to 100% Offline Mode[/] via local Ollama ([cyan]{off_model}[/])\n")
            continue

        if user_input in ("/antigravity", "/agy"):
            client = AntigravityClient()
            console.print("\n[bold white]✦ Connected to Google Antigravity CLI[/] (prompts will bridge to agy)\n")
            continue

        if user_input.startswith("/online") or user_input.startswith("/cloud"):
            if hasattr(client, "set_mode"):
                client.set_mode("cloud")
            else:
                from codex.client import HybridCodexClient
                client = HybridCodexClient(mode="cloud")
            console.print("\n[bold white]✦ Switched to Online Cloud Mode[/] (Cloud Native Zero-Latency)\n")
            continue

        if user_input.startswith("/reach"):
            parts = user_input.split(maxsplit=2)
            from codex.tools import execute_agent_reach
            if len(parts) == 1 or (len(parts) > 1 and parts[1].lower() == "doctor"):
                console.print("\n[bold white]✦ Running Agent Reach Diagnostics (Doctor)...[/]")
                res = execute_agent_reach(action="doctor")
                console.print(res)
            elif len(parts) >= 2 and parts[1].lower() == "url":
                target_url = parts[2].strip() if len(parts) > 2 else ""
                console.print(f"\n[bold white]✦ Fetching Web Content via Jina Reader:[/] [cyan]{target_url}[/]")
                res = execute_agent_reach(action="read", url=target_url)
                console.print(res)
            elif len(parts) >= 2 and parts[1].lower() == "search":
                query_str = parts[2].strip() if len(parts) > 2 else ""
                console.print(f"\n[bold white]✦ Searching Web via Agent Reach (Exa):[/] [cyan]{query_str}[/]")
                res = execute_agent_reach(action="search", query=query_str)
                console.print(res)
            elif len(parts) >= 2 and parts[1].lower() in ("bilibili", "bili"):
                query_str = parts[2].strip() if len(parts) > 2 else ""
                console.print(f"\n[bold white]✦ Bilibili Search via Agent Reach:[/] [cyan]{query_str}[/]")
                res = execute_agent_reach(action="bilibili", query=query_str)
                console.print(res)
            elif len(parts) >= 2 and parts[1].lower() in ("v2ex", "hot"):
                console.print("\n[bold white]✦ Fetching V2EX Hot Topics via Agent Reach...[/]")
                res = execute_agent_reach(action="v2ex")
                console.print(res)
            else:
                q = user_input[6:].strip()
                console.print(f"\n[bold white]✦ Agent Reach Query:[/] [cyan]{q}[/]")
                res = execute_agent_reach(action="search", query=q)
                console.print(res)
            console.print()
            continue

        if user_input.startswith("/memory"):
            parts = user_input.split(maxsplit=2)
            if len(parts) >= 3 and parts[1].lower() == "search":
                q = parts[2].strip()
                matches = session.memory.search(q)
                if matches:
                    console.print(f"[bold white]Memory Search Results for '{q}':[/]")
                    for m in matches:
                        console.print(f"[dim]Turn {m['turn']} ({m['role']}):[/] {m['content']}")
                    console.print()
                else:
                    console.print(f"[dim]No occurrences of '{q}' in memory ({len(session.memory.history)} turns).[/]\n")
            else:
                render_memory_status(
                    total_msgs=len(session.memory.history),
                    active_window=session.memory.max_active_window,
                    knowledge_count=len(session.memory.knowledge_summary) + len(session.memory.decisions_and_facts),
                    files_count=len(session.memory.file_ledger),
                )
            continue

        if user_input == "/compact":
            old_c, new_c = session.compact()
            render_compact_summary(old_c, new_c)
            continue

        if user_input.strip() == "/context" or user_input.strip().startswith("/context "):
            from codex.tools.context import render_context
            mock_mode = "--mock" in user_input
            fallback_mode = "--fallback" in user_input
            render_context(session=session, client=client, use_mock=mock_mode, fallback_glyphs=fallback_mode)
            continue

        if user_input == "/doctor":
            render_doctor(client.model)
            continue

        if user_input == "/cost":
            render_cost(session.total_queries, session.total_tokens)
            continue

        if user_input == "/diff":
            proc = subprocess.run("git diff", shell=True, capture_output=True, text=True)
            render_diff(proc.stdout)
            if proc.stdout.strip():
                try:
                    from codex.diff_navigator import DiffNavigator
                    ans = console.input("[dim]Inspect diff hunks interactively? [y/N]: [/]").strip().lower()
                    if ans in ("y", "yes"):
                        acc, tot = DiffNavigator.inspect_diff_interactive(proc.stdout)
                        console.print(f"[white]Accepted {acc}/{tot} diff hunks.[/]\n")
                except Exception:
                    pass
            continue

        if user_input.startswith("/checkpoint"):
            from codex.git_shadow import GitShadowManager
            shadow_mgr = GitShadowManager()
            parts = user_input.split(maxsplit=2)
            subcmd = parts[1].lower() if len(parts) > 1 else "list"
            if subcmd == "create":
                msg = parts[2] if len(parts) > 2 else ""
                cid = shadow_mgr.create_checkpoint(msg)
                if cid:
                    console.print(f"[bold green]Shadow Checkpoint Created:[/] [white]{cid[:8]}[/]\n")
                else:
                    console.print("[dim]Failed to create shadow checkpoint (ensure git repo with committed HEAD exists).[/]\n")
            elif subcmd == "rollback":
                if len(parts) > 2:
                    target_cid = parts[2].strip()
                    ok = shadow_mgr.rollback(target_cid)
                    if ok:
                        console.print(f"[bold green]Successfully rolled back to checkpoint:[/] {target_cid[:8]}\n")
                    else:
                        console.print(f"[bold red]Failed to rollback to:[/] {target_cid}\n")
                else:
                    console.print("[dim]Usage: /checkpoint rollback <commit_id>[/]\n")
            else:
                checkpoints = shadow_mgr.list_checkpoints()
                if checkpoints:
                    console.print("[bold white]Shadow Git Checkpoints (refs/codex/history):[/]")
                    for cp in checkpoints:
                        console.print(f"  [cyan]{cp['commit_id'][:8]}[/] - {cp['message']}")
                    console.print()
                else:
                    console.print("[dim]No shadow checkpoints found. Use '/checkpoint create <message>' to snapshot.[/]\n")
            continue

        if user_input.startswith("/verify"):
            from codex.anti_tamper import AntiTamperGuard
            from codex.verifier import AutonomousVerifier
            console.print("[bold white]Running Autonomous Verification & Tamper Audit...[/]")
            guard = AntiTamperGuard()
            tampered, mod_files = guard.audit_tampering()
            if tampered:
                console.print(f"[bold red]Anti-Test Tampering Alert![/] Test files were modified:")
                for mf in mod_files:
                    console.print(f"  - [red]{mf}[/]")
                console.print("[dim]Constraint Enforced: Implement fixes in source code rather than modifying test assertions.[/]\n")
            else:
                console.print("[bold green]Anti-Tamper Lock:[/] Clean (all test signatures verified).")

            verifier = AutonomousVerifier()
            passed, test_out = verifier.run_tests()
            status_tag = "[bold green]PASS[/]" if passed else "[bold red]FAIL[/]"
            console.print(f"Test Suite Status: {status_tag}")
            if test_out:
                first_lines = "\n".join(test_out.splitlines()[-10:])
                console.print(f"[dim]{first_lines}[/]\n")
            continue

        if user_input.startswith("/subagent"):
            from codex.subagents import MultiAgentStateMachine
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                task_prompt = parts[1].strip()
                console.print(f"\n[bold white]✦ Launching Multi-Agent State Machine (Planner ➔ Coder ➔ Auditor ➔ Executor)...[/]\n")
                sm = MultiAgentStateMachine()
                def code_gen(step):
                    prompt = f"Write python code for: {step.description}\nTarget: {step.target_path}\nOutput valid raw python code."
                    chunks = []
                    for c in client.stream_chat([{"role": "user", "content": prompt}], max_tokens=300):
                        chunks.append(c)
                    raw = "".join(chunks).strip()
                    if "```python" in raw:
                        raw = raw.split("```python", 1)[1].split("```", 1)[0].strip()
                    elif "```" in raw:
                        raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
                    return raw
                sm.run_workflow(task_prompt, code_generator=code_gen, logger=lambda m: console.print(m))
            else:
                console.print("[dim]Usage: /subagent <task description>[/]\n")
            continue

        if user_input.startswith("/export"):
            parts = user_input.split(maxsplit=1)
            fname = parts[1].strip() if len(parts) > 1 else ""
            out_file = session.export(fname)
            render_export_status(out_file, len(session.memory.history))
            continue

        if user_input == "/init":
            guidelines = (
                f"# Project Guidelines for Codex\n\n"
                f"- Directory: `{os.getcwd()}`\n"
                f"- Model: `{client.model}`\n"
                f"- Style: Concise, clean, idiomatic code without unnecessary comments.\n"
            )
            Path("CODEX.md").write_text(guidelines, encoding="utf-8")
            render_init_status(str(Path("CODEX.md").resolve()))
            continue

        if user_input.startswith("/git"):
            parts = user_input.split(maxsplit=1)
            subcmd = parts[1].strip() if len(parts) > 1 else "status"
            if subcmd in ("status", ""):
                console.print(execute_git_status())
            else:
                proc = subprocess.run(f"git {subcmd}", shell=True, capture_output=True, text=True)
                console.print(proc.stdout or proc.stderr or "[dim](empty git output)[/]")
            console.print()
            continue

        if user_input.startswith("/github"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                target = parts[1].strip()
                res = execute_github_connect(target)
                console.print(f"[white]{res}[/]\n")
            else:
                console.print("[dim]Usage: /github [owner/repo or URL][/]\n")
            continue

        if user_input == "/tools":
            render_tools_list()
            continue

        if user_input == "/stats":
            render_stats(session.total_queries, session.total_tokens, session.total_time)
            continue

        if user_input.startswith("/theme"):
            from codex.themes import set_active_theme, list_themes
            from codex.ui import render_theme_list
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                target_theme = parts[1].strip().lower()
                ok = set_active_theme(target_theme)
                if ok:
                    console.print(f"[bold green]Switched theme to:[/] [bold white]{target_theme}[/]\n")
                else:
                    console.print(f"[bold red]Unknown theme '{target_theme}'.[/] Available themes: monochrome, nord, dracula, matrix\n")
            else:
                render_theme_list()
            continue

        if user_input == "/editor":
            import tempfile
            editor = os.environ.get("EDITOR", "nano")
            with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tf:
                tmp_name = tf.name
                tf.write(b"# Draft your complex multi-line prompt below. Save and exit when done.\n\n")
            try:
                subprocess.run([editor, tmp_name])
                content = Path(tmp_name).read_text(encoding="utf-8")
                clean_lines = [l for l in content.splitlines() if not l.startswith("# Draft your complex")]
                draft_prompt = "\n".join(clean_lines).strip()
                if draft_prompt:
                    console.print(f"[bold white]Drafted prompt via editor ({len(draft_prompt)} chars). Executing...[/]\n")
                    user_input = draft_prompt
                    session.add_user(user_input)
                    execute_turn(session, client, prompt_text=user_input)
                else:
                    console.print("[dim]Empty buffer. Prompt cancelled.[/]\n")
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            continue

        if user_input.startswith("/notify"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                sub = parts[1].strip().lower()
                if sub in ("on", "true", "enable", "1"):
                    session.notifications_enabled = True
                    console.print("[bold green]Desktop notifications & terminal bell ENABLED.[/]\n")
                else:
                    session.notifications_enabled = False
                    console.print("[dim]Desktop notifications & terminal bell DISABLED.[/]\n")
            else:
                state = "ENABLED" if session.notifications_enabled else "DISABLED"
                console.print(f"[dim]Notifications currently {state}. Use '/notify on' or '/notify off'.[/]\n")
            continue

        if user_input.startswith("/model") or user_input == "/modal":
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip().lower() == "list":
                try:
                    from codex.ui import render_model_catalog
                    models_resp = client.client.models.list()
                    raw_models = [{"id": m.id, "context_window": getattr(m, "context_window", "128k")} for m in models_resp.data]
                    render_model_catalog(raw_models, client.model)
                except Exception as e:
                    from codex.ui import render_model_catalog
                    render_model_catalog([], client.model)
            elif len(parts) > 1 and parts[1].strip().lower() not in ("modal", "dialog"):
                client.set_model(parts[1].strip())
                console.print(f"[white]Switched model to:[/] [bold white]{client.model}[/]\n")
            else:
                from codex.ui import prompt_model_modal
                chosen = prompt_model_modal(client.model)
                if chosen:
                    client.set_model(chosen)
                    console.print(f"[bold green]Switched model to:[/] [bold white]{client.model}[/]\n")
                else:
                    render_model_info(client.model)
            continue

        if user_input == "/mascot":
            from codex.ui import run_mascot_showcase
            run_mascot_showcase()
            continue

        if user_input == "/reset":
            session.reset()
            console.print("[white]Context cleared.[/]\n")
            continue

        if user_input in ("/exit", "/quit"):
            console.print("[dim]Goodbye.[/]")
            break

        if user_input.startswith("/"):
            console.print("[dim]Unknown command.[/] Press [bold white]/[/] to view available commands.\n")
            continue

        # Execute autonomous agent turn
        session.add_user(user_input)
        try:
            execute_turn(session, client, prompt_text=user_input)
        except KeyboardInterrupt:
            console.print("\n[dim]Operation aborted by user.[/]\n")
        except Exception as e:
            render_error("Runtime Error", str(e), "Check input arguments or system permissions.")


# ── CLI entry point ─────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cdx",
        description="The Codex Project — Autonomous AI terminal for Linux.",
    )
    parser.add_argument("prompt", nargs="*", help="Run a single prompt and exit.")
    parser.add_argument("--model", type=str, default=None, help="Inference model ID.")
    parser.add_argument("--key", type=str, default=None, help="API key.")
    parser.add_argument("--headless", action="store_true", help="Run non-interactively in headless CI mode.")
    parser.add_argument("--ci", action="store_true", help="Alias for --headless.")
    parser.add_argument("--cloud", action="store_true", help="Force cloaked cloud escalation (OSS-120B High-Precision)")
    parser.add_argument("--local", action="store_true", help="Force local pinned Ollama inference")
    parser.add_argument("--offline", action="store_true", help="Run in fully offline mode using local Ollama model.")
    parser.add_argument("--antigravity", "--agy", action="store_true", help="Forward prompts to Google Antigravity CLI.")
    parser.add_argument("--swarm", "--grokbot", action="store_true", help="Launch the massive 45,000+ agent Swarm Command Center area.")
    parser.add_argument("--boot", action="store_true", help="Launch Cyberpunk terminal coding screen loader and boot selector.")
    parser.add_argument("--panel", action="store_true", help="Display live telemetry & Groq console HUD panel.")
    parser.add_argument("--max-cost", type=float, default=0.0, help="Spending cap in USD.")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    if args.boot:
        from codex.bootloader import play_coding_screen_loader, run_boot_selector
        play_coding_screen_loader(duration_seconds=0.6)
        boot_choice = run_boot_selector()
        if boot_choice == "swarm":
            from codex.swarm import run_swarm_area
            run_swarm_area()
            return
        elif boot_choice == "marketing":
            from codex.marketing import InstagramAutomationEngine, render_marketing_campaign
            camp = InstagramAutomationEngine.create_campaign("Autonomous AI Terminal Swarm 2026")
            render_marketing_campaign(camp)
            return
        elif boot_choice == "legal":
            from codex.lawyers import AutonomousLegalCounsel, render_legal_audit
            audit = AutonomousLegalCounsel.audit_contract("Standard Developer IP Assignment and Indemnification Agreement")
            render_legal_audit(audit)
            return

    if args.panel or (args.prompt and args.prompt[0].lower() in ("panel", "dashboard")):
        from codex.panel import display_panel_once
        display_panel_once()
        return

    if args.prompt and args.prompt[0].lower() in ("marketing", "insta"):
        topic = " ".join(args.prompt[1:]) or "Autonomous AI Coding Agents in Linux Terminal"
        from codex.marketing import InstagramAutomationEngine, render_marketing_campaign
        camp = InstagramAutomationEngine.create_campaign(topic)
        render_marketing_campaign(camp)
        return

    if args.prompt and args.prompt[0].lower() in ("lawyer", "legal"):
        contract = " ".join(args.prompt[1:]) or "Standard SaaS Developer Agreement with unlimited indemnification and non-compete."
        from codex.lawyers import AutonomousLegalCounsel, render_legal_audit
        audit = AutonomousLegalCounsel.audit_contract(contract)
        render_legal_audit(audit)
        return

    if args.swarm or (args.prompt and args.prompt[0].lower() in ("swarm", "grokbot")):
        from codex.swarm import run_swarm_area
        run_swarm_area()
        return

    if args.key:
        os.environ["GROQ_API_KEY"] = args.key

    model = args.model or DEFAULT_MODEL

    mode_arg = "local" if (args.local or args.offline) else "cloud"

    if args.offline:
        off_model = args.model or "qwen2.5-coder:1.5b"
        client = OllamaClient(model=off_model)
    elif args.antigravity:
        client = AntigravityClient(model=args.model or "gemini 3.8 flash")
    else:
        # Default: High-Performance Cloud Native Server with offline local fallback
        from codex.client import HybridCodexClient
        client = HybridCodexClient(model=model if args.model else None, local_model=model, mode=mode_arg)

    if args.model:
        client._explicit_model_flag = True

    if args.headless or args.ci:
        from codex.ci import HeadlessCIRunner
        prompt_str = " ".join(args.prompt)
        if not prompt_str and not sys.stdin.isatty():
            prompt_str = sys.stdin.read().strip()
        if not prompt_str:
            prompt_str = "Perform codebase verification audit."
        runner = HeadlessCIRunner(client, prompt_str, max_cost=args.max_cost)
        report = runner.run()
        runner.print_report(report, format_type="json")
        sys.exit(report.get("exit_code", 0))

    if args.prompt:
        run_direct(" ".join(args.prompt), client)
    else:
        run_repl(client)


if __name__ == "__main__":
    main()
