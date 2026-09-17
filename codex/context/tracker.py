"""Token Accounting Engine for Codex Context Window Telemetry."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Try importing tiktoken for accurate tokenizer, with fallback
try:
    import tiktoken
    _TIKTOKEN_ENCODING = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_ENCODING = None


class TokenCounter:
    """Accurate token estimator and tokenizer helper."""

    @staticmethod
    def count(text: str | None) -> int:
        """Count tokens in a string using tiktoken or fallback regex/heuristic."""
        if not text:
            return 0
        if _TIKTOKEN_ENCODING is not None:
            try:
                return len(_TIKTOKEN_ENCODING.encode(text, disallowed_special=()))
            except Exception:
                pass
        # Fallback: regex tokenization matching words and punctuation
        tokens = re.findall(r"\w+|[^\w\s]", text)
        return max(1, len(tokens)) if text.strip() else 0

    @classmethod
    def count_schema(cls, schemas: list[dict[str, Any]]) -> int:
        """Count tokens of tool schema definitions serialized to JSON."""
        if not schemas:
            return 0
        try:
            dumped = json.dumps(schemas, separators=(",", ":"))
            return cls.count(dumped)
        except Exception:
            return 0

    @classmethod
    def count_messages(cls, messages: list[dict[str, Any]]) -> int:
        """Count tokens across a list of chat messages."""
        total = 0
        for msg in messages:
            # Per message overhead (~4 tokens for role/envelope)
            total += 4
            content = msg.get("content") or ""
            total += cls.count(str(content))
            # Include tool_calls if present
            if "tool_calls" in msg and msg["tool_calls"]:
                try:
                    total += cls.count(json.dumps(msg["tool_calls"], separators=(",", ":")))
                except Exception:
                    pass
        return total


MODEL_CONTEXT_LIMITS: dict[str, int] = {
    # Antigravity / Gemini Models
    "gemini 3.8 flash": 1048576,
    "gemini 3.8 pro": 2097152,
    "gemini 2.5 flash": 1048576,
    "gemini 2.5 pro": 2097152,
    "gemini-2.0-flash": 1048576,
    # Groq & Open Models
    "qwen/qwen3.8-27b": 32768,
    "qwen-2.5-coder-32b": 32768,
    "qwen-2.5-72b-instruct": 131072,
    "llama-3.3-70b-versatile": 131072,
    "llama-3.1-8b-instant": 131072,
    "llama-3.2-3b-preview": 131072,
    "mixtral-8x7b-32768": 32768,
    "deepseek-r1-distill-llama-70b": 131072,
    # Claude Models
    "claude-sonnet-4-5-20250929": 200000,
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-5-haiku-20241022": 200000,
    "claude-3-opus-20240229": 200000,
    # GPT Models
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
}
DEFAULT_CONTEXT_LIMIT = 131072


@dataclass
class ResourceItem:
    """Individual item within a breakdown tree."""
    name: str
    category: str
    tokens: int
    extra: str = ""


@dataclass
class CategoryBreakdown:
    """Summary metrics for a specific context category."""
    name: str
    tokens: int
    percentage: float  # e.g. 1.2 for 1.2%
    color: str
    is_free_space: bool = False
    cells_count: int = 0


@dataclass
class ContextSnapshot:
    """Complete snapshot of context accounting and visual telemetry."""
    model: str
    max_tokens: int
    system_prompt_tokens: int
    system_tools_tokens: int
    mcp_tools_tokens: int
    memory_files_tokens: int
    messages_tokens: int
    
    # Detailed tree items
    mcp_tools: list[ResourceItem] = field(default_factory=list)
    memory_files: list[ResourceItem] = field(default_factory=list)
    slash_commands_count: int = 0
    slash_commands_tokens: int = 0

    @property
    def total_used_tokens(self) -> int:
        return (
            self.system_prompt_tokens
            + self.system_tools_tokens
            + self.mcp_tools_tokens
            + self.memory_files_tokens
            + self.messages_tokens
        )

    @property
    def free_tokens(self) -> int:
        return max(0, self.max_tokens - self.total_used_tokens)

    @property
    def used_percentage(self) -> float:
        if self.max_tokens <= 0:
            return 0.0
        return round((self.total_used_tokens / self.max_tokens) * 100, 1)

    def get_categories(self) -> list[CategoryBreakdown]:
        """Compute percentages and breakdown across the 5 buckets + free space."""
        mt = max(1, self.max_tokens)
        categories = [
            CategoryBreakdown(
                name="System prompt",
                tokens=self.system_prompt_tokens,
                percentage=round((self.system_prompt_tokens / mt) * 100, 1),
                color="amber",
            ),
            CategoryBreakdown(
                name="System tools",
                tokens=self.system_tools_tokens,
                percentage=round((self.system_tools_tokens / mt) * 100, 1),
                color="teal",
            ),
            CategoryBreakdown(
                name="MCP tools",
                tokens=self.mcp_tools_tokens,
                percentage=round((self.mcp_tools_tokens / mt) * 100, 1),
                color="lightblue",
            ),
            CategoryBreakdown(
                name="Memory files",
                tokens=self.memory_files_tokens,
                percentage=round((self.memory_files_tokens / mt) * 100, 1),
                color="orange",
            ),
            CategoryBreakdown(
                name="Messages",
                tokens=self.messages_tokens,
                percentage=round((self.messages_tokens / mt) * 100, 1),
                color="purple",
            ),
            CategoryBreakdown(
                name="Free space",
                tokens=self.free_tokens,
                percentage=round((self.free_tokens / mt) * 100, 1),
                color="gray",
                is_free_space=True,
            ),
        ]
        return categories

    def generate_matrix_cells(self) -> list[str]:
        """Generate 100 sequential cells (10x10) representing 1% each.
        
        Order:
        1. System prompt
        2. System tools
        3. MCP tools
        4. Memory files
        5. Messages
        6. Free space
        """
        mt = max(1, self.max_tokens)
        cells: list[str] = []

        active_categories = [
            ("system_prompt", self.system_prompt_tokens),
            ("system_tools", self.system_tools_tokens),
            ("mcp_tools", self.mcp_tools_tokens),
            ("memory_files", self.memory_files_tokens),
            ("messages", self.messages_tokens),
        ]

        total_allocated = 0
        for cat_name, tok in active_categories:
            if tok > 0:
                # Calculate squares: minimum 1 square if tokens exist, proportional to 100 squares
                squares = max(1, round((tok / mt) * 100))
                # Ensure we do not overflow 100 total squares
                squares = min(squares, 100 - total_allocated)
                cells.extend([cat_name] * squares)
                total_allocated += squares

        # Fill the remainder with free space
        while len(cells) < 100:
            cells.append("free_space")

        return cells[:100]


class ContextTracker:
    """Gathers context telemetry from live Codex runtime or mock generators."""

    @classmethod
    def get_max_tokens(cls, model_id: str | None) -> int:
        if not model_id:
            return DEFAULT_CONTEXT_LIMIT
        model_lower = model_id.lower()
        for k, v in MODEL_CONTEXT_LIMITS.items():
            if k.lower() in model_lower:
                return v
        return DEFAULT_CONTEXT_LIMIT

    @classmethod
    def gather_live(cls, session: Any = None, client: Any = None) -> ContextSnapshot:
        """Inspect active session, client, system prompt, tools, MCP, and memory files."""
        model_id = getattr(client, "model", None) or "qwen/qwen3.8-27b"
        max_tokens = cls.get_max_tokens(model_id)

        # 1. System Prompt (Base + Skills)
        system_prompt_text = ""
        try:
            from codex.client import BASE_SYSTEM_PROMPT
            system_prompt_text = BASE_SYSTEM_PROMPT
        except Exception:
            system_prompt_text = "You are Codex, an elite coding agent."

        try:
            from codex.skills import SkillsManager
            skills_ctx = SkillsManager().get_skills_prompt_context()
            if skills_ctx:
                system_prompt_text += skills_ctx
        except Exception:
            pass
        system_prompt_tokens = TokenCounter.count(system_prompt_text)

        # 2. System Tools (TOOLS_SCHEMA)
        system_tools_tokens = 0
        try:
            from codex.tools import TOOLS_SCHEMA
            system_tools_tokens = TokenCounter.count_schema(TOOLS_SCHEMA)
        except Exception:
            system_tools_tokens = 12000

        # 3. MCP Tools
        mcp_tools_tokens = 0
        mcp_tools_details: list[ResourceItem] = []
        try:
            from codex.mcp import MCPManager
            mcp_mgr = MCPManager()
            for server in mcp_mgr.list_servers():
                sname = server.get("name", "server")
                # Simulated or registered tools
                tools = server.get("tools", [])
                for t in tools:
                    tname = t.get("name", "tool")
                    ttok = TokenCounter.count(json.dumps(t))
                    mcp_tools_details.append(ResourceItem(name=tname, category="MCP", tokens=ttok, extra=sname))
                    mcp_tools_tokens += ttok
        except Exception:
            pass

        # 4. Memory Files
        memory_files_tokens = 0
        memory_files_details: list[ResourceItem] = []
        cwd = Path.cwd()
        for fname in ["CODEX.md", "CLAUDE.md", "AGENTS.md"]:
            fpath = cwd / fname
            if fpath.exists() and fpath.is_file():
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    tok = TokenCounter.count(content)
                    memory_files_tokens += tok
                    memory_files_details.append(
                        ResourceItem(name="Project", category="Memory", tokens=tok, extra=str(fpath.resolve()))
                    )
                except Exception:
                    pass

        # 5. Messages
        messages_tokens = 0
        if session and hasattr(session, "memory") and hasattr(session.memory, "history"):
            messages_tokens = TokenCounter.count_messages(session.memory.history)

        # SlashCommand Tool Info
        slash_count = 0
        slash_tokens = 0
        try:
            from codex.main import SlashCommandCompleter
            slash_count = len(SlashCommandCompleter.COMMANDS)
            slash_desc = " ".join(f"{c} {d}" for c, d in SlashCommandCompleter.COMMANDS)
            slash_tokens = TokenCounter.count(slash_desc)
        except Exception:
            slash_count = 25
            slash_tokens = 864

        return ContextSnapshot(
            model=model_id,
            max_tokens=max_tokens,
            system_prompt_tokens=system_prompt_tokens,
            system_tools_tokens=system_tools_tokens,
            mcp_tools_tokens=mcp_tools_tokens,
            memory_files_tokens=memory_files_tokens,
            messages_tokens=messages_tokens,
            mcp_tools=mcp_tools_details,
            memory_files=memory_files_details,
            slash_commands_count=slash_count,
            slash_commands_tokens=slash_tokens,
        )

    @classmethod
    def get_mock_snapshot(cls) -> ContextSnapshot:
        """Synthetic mock snapshot matching telemetry from Claude Code screenshot."""
        return ContextSnapshot(
            model="claude-sonnet-4-5-20250929",
            max_tokens=200000,
            system_prompt_tokens=2470,
            system_tools_tokens=13260,
            mcp_tools_tokens=1293,
            memory_files_tokens=2210,
            messages_tokens=40400,
            mcp_tools=[
                ResourceItem(name="mcp__ide__getDiagnostics", category="MCP", tokens=611, extra="ide"),
                ResourceItem(name="mcp__ide__executeCode", category="MCP", tokens=682, extra="ide"),
            ],
            memory_files=[
                ResourceItem(
                    name="Project",
                    category="Memory",
                    tokens=2210,
                    extra="/home/ubuntu/investment-99/CLAUDE.md",
                )
            ],
            slash_commands_count=0,
            slash_commands_tokens=864,
        )


def format_tokens(n: int, include_unit: bool = True) -> str:
    """Format token counts according to Claude Code standards:
    - < 1000: '611 tokens' (or '611')
    - 1000..99999: '2.5k tokens' or '40.4k tokens' (or '2.5k')
    - >= 100000: '140k' or '200k'
    """
    if n < 1000:
        val = str(n)
        return f"{val} tokens" if include_unit else val
    elif n < 100000:
        val = f"{n / 1000:.1f}k".replace(".0k", "k")
        return f"{val} tokens" if include_unit else val
    else:
        val = f"{round(n / 1000)}k"
        return f"{val} tokens" if include_unit else val


def format_ratio_tokens(used: int, total: int) -> str:
    """Format as '60k/200k tokens'."""
    u_str = f"{round(used / 1000)}k" if used >= 1000 else str(used)
    t_str = f"{round(total / 1000)}k" if total >= 1000 else str(total)
    return f"{u_str}/{t_str} tokens"
