"""Agent Registry for 200+ specialized engineering personas."""

import json
from pathlib import Path
from typing import Any

GLOBAL_AGENTS_PATH = Path.home() / ".codex" / "agents" / "agents.json"


class AgentRegistry:
    """Discovers, filters, and activates specialized agents."""

    def __init__(self):
        self.agents: list[dict[str, Any]] = []
        self._load_agents()

    def _load_agents(self) -> None:
        if GLOBAL_AGENTS_PATH.exists():
            try:
                self.agents = json.loads(GLOBAL_AGENTS_PATH.read_text(encoding="utf-8"))
            except Exception:
                self.agents = []

    def get_agent(self, name_or_query: str) -> dict[str, Any] | None:
        """Find agent by exact name or substring match."""
        clean = name_or_query.strip().lower()
        # 1. Exact match
        for a in self.agents:
            if a["name"].lower() == clean:
                return a
        # 2. Substring match
        for a in self.agents:
            if clean in a["name"].lower() or clean in a["role"].lower():
                return a
        return None

    def list_agents(self, category: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
        """Filter agents by category or keyword query."""
        results = self.agents
        if category:
            cat_clean = category.strip().lower()
            results = [a for a in results if a.get("category", "").lower() == cat_clean]
        if query:
            q_clean = query.strip().lower()
            results = [a for a in results if q_clean in a["name"].lower() or q_clean in a["description"].lower()]
        return results

    def get_categories(self) -> list[str]:
        cats = sorted({a.get("category", "general") for a in self.agents})
        return cats
