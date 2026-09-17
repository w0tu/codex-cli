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
from codex.client import GroqClient, get_system_prompt, DEFAULT_MODEL, save_api_key
from codex.memory import MemoryManager
from codex.usage import UsageTracker
from codex.skills import SkillsManager
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
        ("/stats", "Show session token usage and stats"),
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

    # 2. Dynamic prompt-related thinking animation
    animate_thinking(prompt=prompt_text)

    turn_tokens = 0

    for _ in range(max_steps):
        try:
            from codex.security import SecretScrubber
            scrubbed_msgs = SecretScrubber.scrub_messages(session.messages)
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
def run_direct(prompt: str, client: GroqClient) -> None:
    session = Session()
    session.add_user(prompt)
    console.print(render_header(model_name=client.model))
    console.print()
    execute_turn(session, client, prompt_text=prompt)


# ── Interactive REPL ────────────────────────────────────────────────────
def run_repl(client: GroqClient) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    pt = PTSession(
        history=FileHistory(str(HISTORY_PATH)),
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        complete_style=CompleteStyle.COLUMN,
        style=MENU_STYLE,
    )

    session = Session()

    console.print(render_header(model_name=client.model))
    console.print()

    while True:
        try:
            from codex.ui import format_prompt_string
            prompt_str = format_prompt_string(os.getcwd())
            user_input = pt.prompt(ANSI(prompt_str)).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("[dim]Goodbye.[/]")
            break

        if not user_input:
            continue

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
            # If the user only passed the key or key-setting text, don't execute as a prompt
            norm = cleaned_input.lower()
            if not cleaned_input or norm in [
                "api key", "my key", "key", "groq key", "groq_api_key",
                "here is my key", "here is the key", "api key:", "key:"
            ] or all(w in ["my", "key", "api", "is", "here", "the", "groq", "set", ":", "="] for w in norm.split()):
                continue
            user_input = cleaned_input

        # Slash commands
        if user_input == "/clear":
            clear_terminal()
            console.print(render_header(model_name=client.model))
            console.print()
            continue

        if user_input == "/help":
            render_help()
            continue

        if user_input == "/usage":
            render_usage_tab(session.usage_tracker.get_stats())
            continue

        if user_input == "/onboard":
            from codex.config import run_onboarding_wizard
            new_key = run_onboarding_wizard()
            client.set_api_key(new_key)
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
            from codex.subagents import Orchestrator
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                task_prompt = parts[1].strip()
                console.print(f"[bold white]Decomposing task into multi-agent DAG...[/]")
                orch = Orchestrator()
                dag = orch.build_plan_for_prompt(task_prompt)
                logs = orch.execute_dag(dag)
                for log in logs:
                    console.print(f"  [dim]{log}[/]")
                console.print(f"[bold green]Sub-Agent DAG execution completed cleanly.[/]\n")
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

        if user_input.startswith("/model"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip().lower() == "list":
                try:
                    from codex.ui import render_model_catalog
                    models_resp = client.client.models.list()
                    raw_models = [{"id": m.id, "context_window": getattr(m, "context_window", "128k")} for m in models_resp.data]
                    render_model_catalog(raw_models, client.model)
                except Exception as e:
                    console.print(f"[dim]Unable to fetch live model catalog: {e}[/]\n")
            elif len(parts) > 1:
                client.set_model(parts[1].strip())
                console.print(f"[white]Switched model to:[/] [bold white]{client.model}[/]\n")
            else:
                render_model_info(client.model)
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
    parser.add_argument("--max-cost", type=float, default=0.0, help="Spending cap in USD.")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    if args.key:
        os.environ["GROQ_API_KEY"] = args.key

    model = args.model or DEFAULT_MODEL
    try:
        client = GroqClient(model=model, api_key=args.key)
    except RuntimeError:
        try:
            from codex.config import run_onboarding_wizard
            key = run_onboarding_wizard()
            client = GroqClient(model=model, api_key=key)
        except Exception as e:
            render_error("Configuration Error", str(e), "Configure ~/.codex/config.json with a valid API key.")
            sys.exit(1)

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
