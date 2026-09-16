"""Unit tests for Codex CLI v1.5.0 — tools, dynamic thinking, export, error handling."""

import os
import unittest
import tempfile
from pathlib import Path

from codex import __version__
from codex.client import GroqClient, _resolve_api_key, DEFAULT_MODEL
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
)
from prompt_toolkit.document import Document


class TestVersion(unittest.TestCase):
    def test_version_string(self):
        self.assertEqual(__version__, "1.5.0")


class TestSession(unittest.TestCase):
    def test_empty_session(self):
        s = Session()
        self.assertEqual(len(s.messages), 1)
        self.assertEqual(s.messages[0]["role"], "system")

    def test_add_user_assistant(self):
        s = Session()
        s.add_user("hello")
        s.add_assistant("hi")
        self.assertEqual(len(s.messages), 3)

    def test_compact_session(self):
        s = Session()
        for i in range(10):
            s.add_user(f"question {i}")
            s.add_assistant(f"answer {i}")
        old_c, new_c = s.compact()
        self.assertEqual(old_c, 21)
        self.assertLess(new_c, old_c)

    def test_export_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "exported.md")
            s = Session()
            s.add_user("how does quicksort work?")
            s.add_assistant("Quicksort is a divide and conquer algorithm.")
            exported_path = s.export(out_file)
            self.assertTrue(os.path.exists(exported_path))
            content = Path(exported_path).read_text()
            self.assertIn("quicksort", content)


class TestThinkingDuration(unittest.TestCase):
    def test_short_prompt_duration(self):
        d = calculate_thinking_duration("hello")
        self.assertGreaterEqual(d, 1.0)
        self.assertLessEqual(d, 1.5)

    def test_complex_prompt_duration(self):
        d = calculate_thinking_duration("Architect and refactor the entire kernel network stack to implement high throughput eBPF packet filtering.")
        self.assertGreaterEqual(d, 3.5)


class TestSlashMenu(unittest.TestCase):
    def test_slash_triggers_all_commands(self):
        completer = SlashCommandCompleter()
        doc = Document("/", 1)
        completions = list(completer.get_completions(doc, None))
        cmd_names = [c.text for c in completions]
        expected = ["/help", "/clear", "/compact", "/doctor", "/cost", "/diff", "/export", "/init", "/git", "/github", "/tools", "/model", "/stats", "/reset", "/exit"]
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
        render_help()
        render_tools_list()


if __name__ == "__main__":
    unittest.main()
