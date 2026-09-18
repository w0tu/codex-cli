"""Multi-provider inference client with Groq, local Ollama offline mode, and Antigravity bridge."""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Generator, Any
from codex.tools import TOOLS_SCHEMA

CONFIG_PATH = Path.home() / ".codex" / "config.json"
DEFAULT_MODEL = "gemini 2.5 flash"
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

4. THINKING & REASONING TRANSPARENCY:
   - When analyzing code, diagnosing complex errors, formulating plans, or evaluating tool options, write your reasoning inside a `<think>...</think>` block.
   - Outline your hypothesis, the steps you plan to take, and what you are checking.
   - Keep thinking concise, rigorous, and technical.

5. ONLINE RESEARCH & REAL-TIME DATA:
   - You have free built-in access to live online research tools: `web_search`, `fetch_url`, `online_info`, and `github_search`.
   - When asked about up-to-date topics, documentation, libraries, or external code, autonomously call `web_search`, `fetch_url`, or `github_search` to fetch accurate information.
"""


def get_system_prompt() -> str:
    """Build system prompt, injecting CODEX.md guidelines and active skills."""
    prompt = BASE_SYSTEM_PROMPT
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

    # Inject installed skills context
    try:
        from codex.skills import SkillsManager
        skills_ctx = SkillsManager().get_skills_prompt_context()
        if skills_ctx:
            prompt += skills_ctx
    except Exception:
        pass

    return prompt


SYSTEM_PROMPT = get_system_prompt()


from codex.config import (
    DEFAULT_CONFIG_PATH as CONFIG_PATH,
    DEFAULT_MODEL,
    get_api_key as _resolve_api_key,
    save_api_key,
    rotate_api_key,
    load_config,
)

ANTIGRAVITY_MODELS_MAP = {
    "gemini 3.8 flash": "qwen/qwen3.8-27b",
    "gemini 3.8 pro": "llama-3.3-70b-versatile",
    "gemini 2.5 flash": "llama-3.1-8b-instant",
    "gemini 2.5 pro": "deepseek-r1-distill-llama-70b",
    "gemini-2.0-flash": "llama-3.1-8b-instant",
}


def resolve_backend_model(model_name: str) -> str:
    """Resolve user-facing model (e.g. gemini 3.8 flash) to available hardware backend."""
    clean = model_name.strip().lower()
    for s in [" antigravity", "-antigravity", "_antigravity"]:
        if clean.endswith(s):
            clean = clean[:-len(s)].strip()
    return ANTIGRAVITY_MODELS_MAP.get(clean, model_name)


class OllamaClient:
    """100% Offline client connecting to local Ollama with tools & streaming."""

    def __init__(self, model: str = "qwen2.5-coder:1.5b", base_url: str = "http://localhost:11434"):
        import httpx
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = "local-offline"

    def set_api_key(self, key: str) -> None:
        pass

    def chat_turn(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1000,
        temperature: float = 0.2,
    ):
        import httpx
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_thread": 4,
            },
        }
        if TOOLS_SCHEMA:
            payload["tools"] = TOOLS_SCHEMA

        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

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
        max_tokens: int = 1000,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        import httpx
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_thread": 4,
            },
        }
        with httpx.stream("POST", url, json=payload, timeout=180.0) as response:
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        c = chunk.get("message", {}).get("content", "")
                        if c:
                            yield c
                    except Exception:
                        pass

    def set_model(self, model: str) -> None:
        self.model = model


class AntigravityClient:
    """Client that sends prompts and coding tasks directly to the Google Antigravity CLI."""

    def __init__(self, model: str = "gemini 3.8 flash"):
        self.model = model
        self.agy_path = Path.home() / ".local" / "bin" / "agy"
        self.api_key = "antigravity-bridge"

    def set_api_key(self, key: str) -> None:
        pass

    def chat_turn(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ):
        user_prompt = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_prompt = m.get("content", "")
                break
        if not user_prompt:
            user_prompt = "Hello"

        cmd = [str(self.agy_path), "-p", user_prompt]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
            output = res.stdout.strip()
            if not output and res.stderr:
                output = f"[Antigravity Notice]: {res.stderr.strip()}"
            elif not output:
                output = "[Antigravity completed requested turn]"
        except Exception as e:
            output = f"[Antigravity Execution Error]: {e}"

        class MessageObj:
            role = "assistant"
            content = output
            tool_calls = None

        class ChoiceObj:
            message = MessageObj()

        class RespObj:
            choices = [ChoiceObj()]

        return RespObj()

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        resp = self.chat_turn(messages, max_tokens, temperature)
        yield resp.choices[0].message.content

    def set_model(self, model: str) -> None:
        self.model = model


class GroqClient:
    """Wrapper around the official groq Python SDK with auto-failover to local Ollama when offline."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None):
        from groq import Groq
        self.api_key = api_key or _resolve_api_key()
        self.client = Groq(api_key=self.api_key)
        self.model = model
        self._offline_fallback = None

    def set_api_key(self, api_key: str) -> None:
        from groq import Groq
        self.api_key = api_key.strip()
        self.client = Groq(api_key=self.api_key)

    def rotate_failover(self) -> str | None:
        new_key = rotate_api_key()
        if new_key:
            self.set_api_key(new_key)
            return new_key
        return None

    def chat_turn(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 600,
        temperature: float = 0.2,
    ):
        backend_model = resolve_backend_model(self.model)
        try:
            return self.client.chat.completions.create(
                model=backend_model,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            err_msg = str(e)
            # Failover 1: API key rotation
            if "401" in err_msg or "429" in err_msg or "rate_limit" in err_msg.lower():
                new_key = self.rotate_failover()
                if new_key:
                    return self.client.chat.completions.create(
                        model=backend_model,
                        messages=messages,
                        tools=TOOLS_SCHEMA,
                        tool_choice="auto",
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
            # Failover 2: Network unreachable / offline fallback to local Ollama
            if "connection" in err_msg.lower() or "connect" in err_msg.lower() or "offline" in err_msg.lower():
                sys.stderr.write("\n[Notice: Offline/Network error detected. Routing turn to local Ollama (qwen2.5-coder:1.5b)...]\n")
                if not self._offline_fallback:
                    self._offline_fallback = OllamaClient()
                return self._offline_fallback.chat_turn(messages, max_tokens, temperature)
            raise

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 600,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        backend_model = resolve_backend_model(self.model)
        try:
            response = self.client.chat.completions.create(
                model=backend_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            err_msg = str(e)
            if "connection" in err_msg.lower() or "connect" in err_msg.lower():
                if not self._offline_fallback:
                    self._offline_fallback = OllamaClient()
                yield from self._offline_fallback.stream_chat(messages, max_tokens, temperature)
            else:
                raise

    def set_model(self, model: str) -> None:
        self.model = model
