"""Zero-Latency Local Ollama Inference Client with Cloaked Cloud Fallback.

- Connects directly via httpx socket streaming to http://127.0.0.1:11434/api/chat. Zero subprocess overhead.
- Sends 'keep_alive': -1 in every payload to permanently pin 1B/3B models in RAM/VRAM.
- Streams responses using unbuffered token flushes (sys.stdout.write + sys.stdout.flush).
- Cloaked Cloud Fallback: Automatically escalates to OSS-120B High-Precision when query exceeds 1B capacity.
- Enforces $2.00 daily budget limit, automatically falling back to local Ollama when limit is reached.
- Updates persistent SQLite telemetry database (~/.config/codex_cli/metrics.db).
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Generator, Any, Optional, Dict, List, Tuple

from codex.tools import TOOLS_SCHEMA
from codex.metrics_db import metrics_db
from codex.billing import billing_guardrail
from codex.cloud_fallback import (
    CLOAKED_ENGINE_LABEL,
    detect_query_complexity,
    is_internet_available,
    cloaked_cloud_client,
)

CONFIG_PATH = Path.home() / ".config" / "codex_cli" / "config.json"
DEFAULT_LOCAL_MODEL = "qwen2.5-coder:1.5b"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

BASE_SYSTEM_PROMPT = """You are Codex, an elite principal software engineer and terminal-native AI coding assistant designed for Linux.
You have direct, hardware-accelerated access to the user's computer via tools.

CORE OPERATIONAL PRINCIPLES:
1. AUTONOMOUS INITIATIVE:
   - When asked to write code, debug issues, investigate bugs, or check system state, USE YOUR TOOLS immediately.
   - Never ask the user to run commands or read files that you can execute or inspect yourself with `bash`, `read_file`, `grep_search`, or `find_files`.
   - Before modifying existing files, inspect them first to match existing idioms, imports, and code style.
   - After writing or editing code, verify changes by running tests or linters using `bash`.

2. RIGOROUS ENGINEERING STANDARDS:
   - Write robust, production-grade, maintainable code.
   - Never use lazy placeholders (e.g. '# TODO', 'pass', '// implement later'). Write complete, fully functional solutions.
   - Handle edge cases, exceptions, and resource cleanup cleanly.

3. COMMUNICATION & TONE:
   - Communicate like a senior peer engineer: razor-sharp, concise, objective, and insightful.
   - Zero conversational filler: Never say "Certainly!", "Sure thing!", "I'd be happy to help!", or "As an AI".
   - Start immediately with the answer, code, or tool invocation.
   - Never use emojis in text, code, comments, or terminal output.
   - Use GitHub-flavored Markdown with explicit syntax highlighting tags for code blocks.
"""


def get_system_prompt(lean: bool = True) -> str:
    """Build lean, zero-latency system prompt for fast, elite inference."""
    prompt = (
        "You are Codex, an elite principal software engineer and terminal-native AI assistant for Linux. "
        "Be direct, concise, and technically rigorous. Never use robotic corporate boilerplate (e.g. 'How can I assist you today?'). "
        "When greeted casually (e.g. 'hi bro'), greet back briefly as a fellow hacker and engineer. "
        "When asked for code or system solutions, deliver clean, working, complete implementations immediately."
    )
    if not lean:
        prompt += "\n" + BASE_SYSTEM_PROMPT
        cwd = Path.cwd()
        for fname in ["CODEX.md", "CLAUDE.md", "AGENTS.md"]:
            guidelines_path = cwd / fname
            if guidelines_path.exists() and guidelines_path.is_file():
                try:
                    content = guidelines_path.read_text(encoding="utf-8", errors="replace").strip()
                    if content:
                        prompt += f"\n\nPROJECT GUIDELINES ({fname}):\n{content}\n"
                        break
                except Exception:
                    pass
        try:
            from codex.skills import SkillsManager
            skills_ctx = SkillsManager().get_skills_prompt_context()
            if skills_ctx:
                prompt += skills_ctx
        except Exception:
            pass
    return prompt


SYSTEM_PROMPT = get_system_prompt(lean=True)


class OllamaClient:
    """Zero-latency client connecting directly via HTTP socket streaming with permanent VRAM/RAM pinning."""

    def __init__(self, model: str = DEFAULT_LOCAL_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = "local-pinned"

    def set_model(self, model: str) -> None:
        self.model = model

    def set_api_key(self, key: str) -> None:
        pass

    def chat_turn(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1200,
        temperature: float = 0.2,
    ) -> Any:
        """Non-streaming chat turn with keep_alive=-1."""
        import httpx
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": -1,  # Pinned permanently in RAM/VRAM
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_thread": 4,
            },
        }
        should_include_tools = False
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content", "").lower()
                break
        tool_keywords = ["run", "execute", "check", "file", "list", "grep", "find", "search", "read", "write", "edit", "git", "status", "terminal", "bash", "ls", "test"]
        if any(k in user_text for k in tool_keywords) or any(m.get("role") == "tool" for m in messages):
            should_include_tools = True

        if TOOLS_SCHEMA and should_include_tools:
            payload["tools"] = TOOLS_SCHEMA

        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Record token metrics
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)
        total_tokens = eval_count + prompt_eval_count
        if total_tokens > 0:
            try:
                metrics_db.record_turn(local_tokens=total_tokens, cloud_tokens=0, cloud_spend=0.0)
            except Exception:
                pass

        msg_data = data.get("message", {})
        raw_tools = msg_data.get("tool_calls")
        tool_calls = None
        if raw_tools:
            class ToolCallFunction:
                def __init__(self, name, arguments):
                    self.name = name
                    self.arguments = json.dumps(arguments) if isinstance(arguments, dict) else str(arguments)

            class ToolCallObj:
                def __init__(self, id_val, fn):
                    self.id = id_val
                    self.type = "function"
                    self.function = fn

            tool_calls = []
            for i, tc in enumerate(raw_tools):
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                fn_args = fn.get("arguments", {})
                tool_calls.append(ToolCallObj(f"call_ollama_{i}", ToolCallFunction(fn_name, fn_args)))

        class MessageObj:
            def __init__(self, content, tc):
                self.role = "assistant"
                self.content = content
                self.tool_calls = tc

        class ChoiceObj:
            def __init__(self, m):
                self.message = m

        class RespObj:
            def __init__(self, c):
                self.choices = [c]

        return RespObj(ChoiceObj(MessageObj(msg_data.get("content", ""), tool_calls)))

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Direct HTTP socket stream with keep_alive=-1 and zero process overhead."""
        import httpx
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "keep_alive": -1,  # Keep pinned in RAM/VRAM permanently
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_thread": 4,
            },
        }

        total_tokens = 0
        with httpx.stream("POST", url, json=payload, timeout=180.0) as response:
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    c = chunk.get("message", {}).get("content", "")
                    if c:
                        yield c
                    if chunk.get("done", False):
                        total_tokens = chunk.get("eval_count", 0) + chunk.get("prompt_eval_count", 0)
                except Exception:
                    pass

        if total_tokens > 0:
            try:
                metrics_db.record_turn(local_tokens=total_tokens, cloud_tokens=0, cloud_spend=0.0)
            except Exception:
                pass

    def stream_chat_unbuffered(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> str:
        """Stream responses with direct unbuffered stdout flushes."""
        collected: list[str] = []
        for chunk in self.stream_chat(messages, max_tokens=max_tokens, temperature=temperature):
            sys.stdout.write(chunk)
            sys.stdout.flush()
            collected.append(chunk)
        return "".join(collected)


class HybridCodexClient:
    """Smart inference client routing between local pinned Ollama and cloaked OSS-120B High-Precision."""

    def __init__(
        self,
        model: Optional[str] = None,
        local_model: Optional[str] = None,
        cloud_enabled: bool = True,
        api_key: Optional[str] = None,
        mode: Optional[str] = None,
    ):
        # Resolve preferred local model from config if not explicitly set
        if not model and not local_model:
            try:
                cfg_path = Path.home() / ".config" / "codex_cli" / "config.json"
                if cfg_path.exists():
                    cfg_data = json.loads(cfg_path.read_text(encoding="utf-8"))
                    local_model = cfg_data.get("local_model")
            except Exception:
                pass

        chosen_model = model or local_model or DEFAULT_LOCAL_MODEL
        self.local_client = OllamaClient(model=chosen_model)
        self.cloud_client = cloaked_cloud_client
        if api_key:
            self.cloud_client.set_api_key(api_key)
        self.cloud_enabled = cloud_enabled

        # Set execution mode: 'cloud', 'local', or 'auto'
        from codex.cloud_fallback import is_cloud_available
        if mode:
            self.mode = mode.lower()
        elif is_cloud_available() and self.cloud_enabled:
            # Cloud-first for high performance and sub-second 120B quality
            self.mode = "cloud"
        else:
            self.mode = "auto"

        self.model = CLOAKED_ENGINE_LABEL if self.mode == "cloud" else chosen_model
        self.last_engine_used = self.model

    def set_mode(self, mode: str) -> str:
        """Switch routing mode between 'cloud', 'local', and 'auto'."""
        mode_clean = mode.lower().strip()
        if mode_clean in ["cloud", "remote", "oss-120b"]:
            self.mode = "cloud"
            self.model = CLOAKED_ENGINE_LABEL
        elif mode_clean in ["local", "ollama", "offline"]:
            self.mode = "local"
            self.model = self.local_client.model
        else:
            self.mode = "auto"
            self.model = self.local_client.model
        return self.mode

    def rotate_failover(self) -> Optional[str]:
        from codex.config import rotate_api_key
        new_key = rotate_api_key()
        if new_key:
            self.set_api_key(new_key)
            return new_key
        return None

    def set_model(self, model: str) -> None:
        if model == CLOAKED_ENGINE_LABEL or "120b" in model.lower():
            self.mode = "cloud"
            self.model = CLOAKED_ENGINE_LABEL
        else:
            self.model = model
            self.local_client.set_model(model)
            if self.mode == "cloud":
                self.mode = "auto"

    def set_api_key(self, key: str) -> None:
        self.cloud_client.set_api_key(key)

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Intelligently route turn to local pinned engine or cloaked cloud fallback."""
        user_prompt = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_prompt = m.get("content", "")
                break

        est_tokens = sum(len(m.get("content", "")) // 4 for m in messages if isinstance(m.get("content"), str))
        exceeds_1b, reason = detect_query_complexity(user_prompt, est_tokens)

        route_to_cloud = False
        if self.cloud_enabled and self.mode != "local":
            if is_internet_available():
                allowed, notice = billing_guardrail.check_cloud_escalation()
                if allowed:
                    if self.mode == "cloud" or exceeds_1b:
                        route_to_cloud = True
                        self.last_engine_used = CLOAKED_ENGINE_LABEL
                else:
                    sys.stdout.write(f"\n\033[1;33m{notice}\033[0m\n")
                    sys.stdout.flush()
                    self.last_engine_used = self.local_client.model
            else:
                self.last_engine_used = self.local_client.model
        else:
            self.last_engine_used = self.local_client.model

        if route_to_cloud:
            try:
                # If auto-escalated on complexity in auto mode, display subtle notice
                if self.mode == "auto" and exceeds_1b:
                    sys.stdout.write(f"\033[38;2;120;120;130m▌\033[0m \033[38;2;80;160;255m[ESCALATION]\033[0m Routing complex query to \033[1;37m{CLOAKED_ENGINE_LABEL}\033[0m ({reason})...\n")
                    sys.stdout.flush()
                yield from self.cloud_client.stream_chat(messages, max_tokens=max_tokens, temperature=temperature)
                return
            except Exception as e:
                sys.stdout.write(f"\n\033[1;33m[Fallback Notice: Cloud engine error: {e}. Routing to pinned local model]\033[0m\n")
                sys.stdout.flush()
                self.last_engine_used = self.local_client.model

        # Default local zero-latency pinned inference
        yield from self.local_client.stream_chat(messages, max_tokens=max_tokens, temperature=temperature)

    def chat_turn(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1200,
        temperature: float = 0.2,
    ) -> Any:
        if self.cloud_enabled and self.mode != "local" and is_internet_available():
            allowed, _ = billing_guardrail.check_cloud_escalation()
            if allowed:
                try:
                    self.last_engine_used = CLOAKED_ENGINE_LABEL
                    return self.cloud_client.chat_turn(messages, max_tokens=max_tokens, temperature=temperature)
                except Exception:
                    pass
        self.last_engine_used = self.local_client.model
        return self.local_client.chat_turn(messages, max_tokens=max_tokens, temperature=temperature)


# Backward compatibility aliases for existing commands & tests
GroqClient = HybridCodexClient
CodexClient = HybridCodexClient
DEFAULT_MODEL = DEFAULT_LOCAL_MODEL


class AntigravityClient:
    """Client bridging to Google Antigravity CLI."""

    def __init__(self, model: str = "gemini 3.8 flash"):
        self.model = model
        self.agy_path = Path.home() / ".local" / "bin" / "agy"
        self.api_key = "antigravity-bridge"

    def set_api_key(self, key: str) -> None:
        pass

    def chat_turn(self, messages: list[dict[str, Any]], max_tokens: int = 1500, temperature: float = 0.2):
        import subprocess
        user_prompt = "Hello"
        for m in reversed(messages):
            if m.get("role") == "user":
                user_prompt = m.get("content", "")
                break
        cmd = [str(self.agy_path), "-p", user_prompt]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
            output = res.stdout.strip() or f"[Antigravity Notice: {res.stderr.strip()}]"
        except Exception as e:
            output = f"[Antigravity Bridge Error: {e}]"

        class MessageObj:
            role = "assistant"
            content = output
            tool_calls = None

        class ChoiceObj:
            message = MessageObj()

        class RespObj:
            choices = [ChoiceObj()]

        return RespObj()

    def stream_chat(self, messages: list[dict[str, Any]], max_tokens: int = 1500, temperature: float = 0.2):
        resp = self.chat_turn(messages, max_tokens, temperature)
        yield resp.choices[0].message.content

from codex.config import save_api_key, rotate_api_key

ANTIGRAVITY_MODELS_MAP = {
    "gemini 3.8 flash": "qwen/qwen3.8-27b",
    "gemini 3.8 pro": "llama-3.3-70b-versatile",
    "gemini 2.5 flash": "llama-3.1-8b-instant",
    "gemini 2.5 pro": "deepseek-r1-distill-llama-70b",
    "gemini-2.0-flash": "llama-3.1-8b-instant",
}


def resolve_backend_model(model_name: str) -> str:
    clean = model_name.strip().lower()
    for s in [" antigravity", "-antigravity", "_antigravity"]:
        if clean.endswith(s):
            clean = clean[:-len(s)].strip()
    return ANTIGRAVITY_MODELS_MAP.get(clean, model_name)


def _resolve_api_key(path=None) -> str:
    try:
        from codex.config import get_api_key
        return get_api_key(path)
    except Exception:
        return ""


