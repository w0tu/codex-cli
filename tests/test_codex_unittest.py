"""Unit tests for Codex CLI v1.5.0 — 300+ message memory, tools, and UI."""

import os
import unittest
import tempfile
from pathlib import Path

from codex import __version__
from codex.client import GroqClient, _resolve_api_key, DEFAULT_MODEL
from codex.memory import MemoryManager
from codex.ui import (
    render_mascot,
    render_header,
    render_help,
    render_tools_list,
    render_stats,
    render_doctor,
    render_cost,
    render_diff,
    render_error,
    render_export_status,
    render_memory_status,
    render_compact_summary,
    render_init_status,
    calculate_thinking_duration,
)
from codex.main import Session, SlashCommandCompleter
from codex.tools import (
    run_tool,
    execute_bash,
    execute_read_file,
    execute_write_file,
    execute_edit_file,
    execute_list_dir,
    execute_grep_search,
    execute_find_files,
    execute_git_status,
    execute_recall_memory,
)
from prompt_toolkit.document import Document


class TestVersion(unittest.TestCase):
    def test_version_string(self):
        self.assertEqual(__version__, "1.5.0")


class Test300MessageMemory(unittest.TestCase):
    def test_300_plus_message_capacity(self):
        """Verify that memory retains 350+ messages while context window remains bounded."""
        mem = MemoryManager(session_id="test_350_turns")

        # Simulate 350 conversation turns
        for i in range(1, 351):
            mem.add_message("user", f"Turn {i}: What is the status of subsystem {i % 10}?")
            mem.add_message("assistant", f"Turn {i}: Subsystem {i % 10} is operating normally.")

        self.assertEqual(len(mem.history), 700)  # 350 user + 350 assistant

        # Check search across 300+ messages
        results = mem.search("subsystem 7")
        self.assertGreater(len(results), 0)

        # Check bounded context window (must not blow up token limits)
        context = mem.get_context_window(system_prompt="Base System Prompt")
        # System prompt + knowledge base + recent window <= 30
        self.assertLess(len(context), 35)

    def test_file_ledger_tracking(self):
        mem = MemoryManager(session_id="test_ledger")
        mem.record_file_op("/path/to/app.py", "write_file")
        self.assertIn("/path/to/app.py", mem.file_ledger)

    def test_session_wrapping(self):
        s = Session()
        s.add_user("Remember that our database port is 5433.")
        s.add_assistant("Understood, noted port 5433.")
        self.assertGreaterEqual(len(s.memory.history), 2)
        self.assertIn("5433", str(s.memory.decisions_and_facts))


class TestSlashMenu(unittest.TestCase):
    def test_slash_triggers_all_commands(self):
        completer = SlashCommandCompleter()
        doc = Document("/", 1)
        completions = list(completer.get_completions(doc, None))
        cmd_names = [c.text for c in completions]
        expected = ["/help", "/clear", "/memory", "/compact", "/doctor", "/cost", "/diff", "/export", "/init", "/git", "/github", "/tools", "/model", "/stats", "/reset", "/exit"]
        for exp in expected:
            self.assertIn(exp, cmd_names)


class TestTools(unittest.TestCase):
    def test_bash_echo(self):
        res = execute_bash("echo 'codex_test'")
        self.assertIn("codex_test", res)

    def test_write_read_edit_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")
            write_res = execute_write_file(file_path, "hello world\nline 2")
            self.assertIn("Successfully wrote", write_res)

            read_res = execute_read_file(file_path, offset=1, limit=2)
            self.assertIn("hello world", read_res)

            edit_res = execute_edit_file(file_path, "world", "codex")
            self.assertIn("Successfully replaced", edit_res)
            self.assertEqual(Path(file_path).read_text(), "hello codex\nline 2")

    def test_list_dir(self):
        res = execute_list_dir(".")
        self.assertIn("Directory contents", res)

    def test_grep_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "sample.py")
            Path(file_path).write_text("TARGET_STRING = 42\n")
            res = execute_grep_search("TARGET_STRING", path=tmpdir)
            self.assertIn("TARGET_STRING", res)

    def test_find_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(os.path.join(tmpdir, "findme.txt")).write_text("test")
            res = execute_find_files("*.txt", path=tmpdir)
            self.assertIn("findme.txt", res)

    def test_git_status(self):
        res = execute_git_status()
        self.assertIsNotNone(res)

    def test_recall_memory_tool(self):
        res = execute_recall_memory("database")
        self.assertIsNotNone(res)


class TestUI(unittest.TestCase):
    def test_mascot_monochrome(self):
        m = render_mascot()
        self.assertIn("█", m.plain)
        self.assertNotIn("GROQ LPU", m.plain)

    def test_header_render(self):
        h = render_header(model_name="test-model")
        self.assertIsNotNone(h)

    def test_ui_components_render(self):
        render_doctor("qwen/qwen3.8-27b")
        render_cost(5, 500)
        render_compact_summary(10, 4)
        render_init_status("CODEX.md")
        render_diff("")
        render_error("Test Title", "Test detail message", "Test remedy action")
        render_export_status("codex_session.md", 4)
        render_memory_status(350, 24, 12, 5)
        render_help()
        render_tools_list()


if __name__ == "__main__":
    unittest.main()
