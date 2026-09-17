"""Unit tests for Codex /context command, token accounting engine, and 10x10 matrix visualizer."""

import unittest
import subprocess
import sys
from codex.context.tracker import (
    TokenCounter,
    ContextSnapshot,
    ContextTracker,
    ResourceItem,
    format_tokens,
    format_ratio_tokens,
)
from codex.tools.context import build_context_view, render_context
import src.context.tracker as src_tracker


class TestContextTracker(unittest.TestCase):
    """Test token counter, snapshot calculations, and 100-cell matrix allocation."""

    def test_token_counter(self):
        cnt = TokenCounter.count("Hello world, this is a test.")
        self.assertGreater(cnt, 0)
        self.assertEqual(TokenCounter.count(""), 0)
        self.assertEqual(TokenCounter.count(None), 0)

    def test_schema_and_messages_token_counting(self):
        tools = [{"type": "function", "function": {"name": "test_fn"}}]
        tok_tools = TokenCounter.count_schema(tools)
        self.assertGreater(tok_tools, 0)

        msgs = [{"role": "user", "content": "Hello Codex"}]
        tok_msgs = TokenCounter.count_messages(msgs)
        self.assertGreater(tok_msgs, 4)

    def test_snapshot_metrics_and_percentages(self):
        snap = ContextSnapshot(
            model="claude-sonnet-4-5-20250929",
            max_tokens=200000,
            system_prompt_tokens=2470,
            system_tools_tokens=13260,
            mcp_tools_tokens=1293,
            memory_files_tokens=2210,
            messages_tokens=40400,
        )
        self.assertEqual(snap.total_used_tokens, 59633)
        self.assertEqual(snap.free_tokens, 200000 - 59633)
        self.assertEqual(snap.used_percentage, 29.8)

        categories = snap.get_categories()
        self.assertEqual(len(categories), 6)
        cat_map = {c.name: c for c in categories}
        self.assertIn("System prompt", cat_map)
        self.assertIn("System tools", cat_map)
        self.assertIn("MCP tools", cat_map)
        self.assertIn("Memory files", cat_map)
        self.assertIn("Messages", cat_map)
        self.assertIn("Free space", cat_map)

        self.assertEqual(cat_map["System prompt"].percentage, 1.2)
        self.assertEqual(cat_map["System tools"].percentage, 6.6)
        self.assertEqual(cat_map["MCP tools"].percentage, 0.6)
        self.assertEqual(cat_map["Memory files"].percentage, 1.1)
        self.assertEqual(cat_map["Messages"].percentage, 20.2)
        self.assertEqual(cat_map["Free space"].percentage, 70.2)

    def test_matrix_cells_exactly_100(self):
        snap = ContextTracker.get_mock_snapshot()
        cells = snap.generate_matrix_cells()
        self.assertEqual(len(cells), 100)

        # Check sequential ordering
        # First cells must be system_prompt, followed by system_tools, mcp_tools, memory_files, messages, free_space
        self.assertEqual(cells[0], "system_prompt")
        self.assertIn("system_tools", cells)
        self.assertIn("mcp_tools", cells)
        self.assertIn("memory_files", cells)
        self.assertIn("messages", cells)
        self.assertEqual(cells[-1], "free_space")

    def test_token_formatting(self):
        self.assertEqual(format_tokens(611), "611 tokens")
        self.assertEqual(format_tokens(682), "682 tokens")
        self.assertEqual(format_tokens(2470), "2.5k tokens")
        self.assertEqual(format_tokens(13260), "13.3k tokens")
        self.assertEqual(format_tokens(40400), "40.4k tokens")
        self.assertEqual(format_tokens(140377, include_unit=False), "140k")
        self.assertEqual(format_ratio_tokens(60000, 200000), "60k/200k tokens")

    def test_src_tracker_compatibility(self):
        self.assertTrue(hasattr(src_tracker, "ContextTracker"))
        self.assertTrue(hasattr(src_tracker, "ContextSnapshot"))
        self.assertTrue(hasattr(src_tracker, "TokenCounter"))


import re


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences for text comparison."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


class TestContextRendering(unittest.TestCase):
    """Test visual output rendering and CLI mock harness."""

    def test_build_context_view_structure(self):
        snap = ContextTracker.get_mock_snapshot()
        raw_view = build_context_view(snap)
        view = strip_ansi(raw_view)

        self.assertIn("> /context", view)
        self.assertIn("Context Usage", view)
        self.assertIn("claude-sonnet-4-5-20250929 · 60k/200k tokens (30%)", view)
        self.assertIn("System prompt: 2.5k tokens (1.2%)", view)
        self.assertIn("System tools: 13.3k tokens (6.6%)", view)
        self.assertIn("MCP tools: 1.3k tokens (0.6%)", view)
        self.assertIn("Memory files: 2.2k tokens (1.1%)", view)
        self.assertIn("Messages: 40.4k tokens (20.2%)", view)
        self.assertIn("Free space: 140k (70.2%)", view)

        # Check tree breakdowns
        self.assertIn("MCP tools · /mcp", view)
        self.assertIn("mcp__ide__getDiagnostics (ide): 611 tokens", view)
        self.assertIn("mcp__ide__executeCode (ide): 682 tokens", view)
        self.assertIn("Memory files · /memory", view)
        self.assertIn("Project (/home/ubuntu/investment-99/CLAUDE.md): 2.2k tokens", view)
        self.assertIn("SlashCommand Tool · 0 commands", view)
        self.assertIn("└ Total: 864 tokens", view)

    def test_fallback_glyphs_rendering(self):
        snap = ContextTracker.get_mock_snapshot()
        view = build_context_view(snap, fallback_glyphs=True)
        self.assertIn("⊝", view)
        self.assertIn("[ ]", view)

    def test_cli_mock_command_execution(self):
        res = subprocess.run(
            [sys.executable, "-m", "codex.tools.context", "--mock"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        clean = strip_ansi(res.stdout)
        self.assertIn("Context Usage", clean)
        self.assertIn("Free space: 140k (70.2%)", clean)

    def test_npm_script_execution(self):
        res = subprocess.run(
            ["npm", "run", "test:context"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        clean = strip_ansi(res.stdout)
        self.assertIn("Context Usage", clean)
        self.assertIn("Free space: 140k (70.2%)", clean)


if __name__ == "__main__":
    unittest.main()
