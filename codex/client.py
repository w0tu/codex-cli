"""Groq inference client with tool calling and streaming support."""

import os
import json
from pathlib import Path
from typing import Generator, Any
from codex.tools import TOOLS_SCHEMA

CONFIG_PATH = Path.home() / ".codex" / "config.json"
DEFAULT_MODEL = "qwen/qwen3.8-27b"
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


def _resolve_api_key() -> str:
    """Resolve API key: env var > config file > raise."""
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key

    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            key = data.get("api_key")
            if key:
                return key
        except Exception:
            pass

    raise RuntimeError(
        "No Groq API key found.\n"
        "Set GROQ_API_KEY environment variable or create ~/.codex/config.json:\n"
        '  {"api_key": "gsk_..."}'
    )


def save_api_key(api_key: str) -> Path:
    """Save API key permanently to ~/.codex/config.json and set in environment."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["api_key"] = api_key.strip()
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.environ["GROQ_API_KEY"] = api_key.strip()
    return CONFIG_PATH


class GroqClient:
    """Wrapper around the official groq Python SDK."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None):
        from groq import Groq
        self.api_key = api_key or _resolve_api_key()
        self.client = Groq(api_key=self.api_key)
        self.model = model

    def set_api_key(self, api_key: str) -> None:
        """Update active API key and reinitialize Groq SDK client."""
        from groq import Groq
        self.api_key = api_key.strip()
        self.client = Groq(api_key=self.api_key)


    def chat_turn(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 600,
        temperature: float = 0.2,
    ):
        """Perform a chat turn with tool support."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 600,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Stream chat tokens directly."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def set_model(self, model: str) -> None:
        self.model = model
