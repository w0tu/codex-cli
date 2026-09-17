"""Unit tests for Codex CLI v1.6.0 — usage quotas, contextual thinking, memory, tools."""

import os
import time
import unittest
import tempfile
from pathlib import Path

from codex import __version__
from codex.client import GroqClient, _resolve_api_key, DEFAULT_MODEL
from codex.memory import MemoryManager
from codex.usage import UsageTracker, MAX_REQUESTS_5H
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
    render_usage_tab,
    render_compact_summary,
    render_init_status,
    calculate_thinking_duration,
    get_prompt_related_phases,
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
        self.assertEqual(__version__, "1.7.0")


class TestUsageTracker(unittest.TestCase):
    def test_quota_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / "usage.json"
            tracker = UsageTracker(filepath=usage_file)

            # Initially allowed
            allowed, _, _ = tracker.check_limit()
            self.assertTrue(allowed)

            # Record some requests
            for _ in range(5):
                tracker.record_request()

            stats = tracker.get_stats()
            self.assertEqual(stats["used_5h"], 5)
            self.assertEqual(stats["remaining_5h"], MAX_REQUESTS_5H - 5)
            self.assertEqual(stats["used_day"], 5)
            self.assertIn("reset_day", stats)

    def test_quota_enforcement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / "usage.json"
            tracker = UsageTracker(filepath=usage_file)
            now = time.time()
            tracker.timestamps = [now - 100 for _ in range(MAX_REQUESTS_5H)]
            allowed, reason, wait_secs = tracker.check_limit()
            self.assertFalse(allowed)
            self.assertIn("5-hour quota reached", reason)
            self.assertGreater(wait_secs, 0)


class TestContextualThinking(unittest.TestCase):
    def test_prompt_related_phases(self):
        git_phases = get_prompt_related_phases("show my git branch")
        self.assertTrue(any("git" in p.lower() for p in git_phases))

        code_phases = get_prompt_related_phases("write python class")
        self.assertTrue(any("code" in p.lower() or "syntax" in p.lower() for p in code_phases))

        file_phases = get_prompt_related_phases("read file /etc/hosts")
        self.assertTrue(any("file" in p.lower() or "path" in p.lower() for p in file_phases))


class Test300MessageMemory(unittest.TestCase):
    def test_300_plus_message_capacity(self):
        mem = MemoryManager(session_id="test_350_turns")
        for i in range(1, 351):
            mem.add_message("user", f"Turn {i}: What is the status of subsystem {i % 10}?")
            mem.add_message("assistant", f"Turn {i}: Subsystem {i % 10} is operating normally.")

        self.assertEqual(len(mem.history), 700)
        results = mem.search("subsystem 7")
        self.assertGreater(len(results), 0)

        context = mem.get_context_window(system_prompt="Base System Prompt")
        self.assertLess(len(context), 35)


class TestSlashMenu(unittest.TestCase):
    def test_slash_triggers_all_commands(self):
        completer = SlashCommandCompleter()
        doc = Document("/", 1)
        completions = list(completer.get_completions(doc, None))
        cmd_names = [c.text for c in completions]
        expected = [
            "/help", "/clear", "/usage", "/skills", "/memory", "/compact",
            "/doctor", "/cost", "/diff", "/export", "/init", "/git",
            "/github", "/tools", "/model", "/stats", "/reset", "/exit"
        ]
        for exp in expected:
            self.assertIn(exp, cmd_names)


class TestSkillsSystem(unittest.TestCase):
    def test_skills_manager(self):
        from codex.skills import SkillsManager
        mgr = SkillsManager()
        skills = mgr.list_skills()
        self.assertGreater(len(skills), 0)
        skill_names = [s["name"] for s in skills]
        self.assertIn("code-reviewer", skill_names)
        self.assertIn("git-workflow", skill_names)

        ctx = mgr.get_skills_prompt_context()
        self.assertIn("ACTIVE COMMUNITY & GITHUB SKILLS", ctx)


class TestKeySaving(unittest.TestCase):
    def test_save_api_key(self):
        from codex.client import save_api_key, CONFIG_PATH
        test_key = "gsk_test1234567890abcdef12345678"
        orig_env = os.environ.get("GROQ_API_KEY")
        orig_cfg_bytes = CONFIG_PATH.read_bytes() if CONFIG_PATH.exists() else None
        try:
            cfg = save_api_key(test_key)
            self.assertTrue(cfg.exists())
            self.assertEqual(os.environ.get("GROQ_API_KEY"), test_key)
        finally:
            if orig_env is not None:
                os.environ["GROQ_API_KEY"] = orig_env
            elif "GROQ_API_KEY" in os.environ:
                del os.environ["GROQ_API_KEY"]
            if orig_cfg_bytes is not None:
                CONFIG_PATH.write_bytes(orig_cfg_bytes)
            elif CONFIG_PATH.exists():
                CONFIG_PATH.unlink()


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

    def test_online_tools(self):
        from codex.tools import execute_web_search, execute_fetch_url, execute_online_info, execute_github_search
        search_res = execute_web_search("Python programming")
        self.assertTrue("Python" in search_res or "results" in search_res)

        info_res = execute_online_info("Linux")
        self.assertTrue("Linux" in info_res or "results" in info_res)

        github_res = execute_github_search("linux")
        self.assertTrue("GitHub" in github_res or "linux" in github_res.lower())


class TestPhase1Config(unittest.TestCase):
    def test_config_load_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dummy_path = Path(tmpdir) / "nonexistent_config.json"
            from codex.config import load_config
            cfg = load_config(dummy_path)
            self.assertEqual(cfg["model"], "qwen/qwen3.8-27b")
            self.assertEqual(cfg["backup_keys"], [])

    def test_config_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            from codex.config import save_config, load_config
            save_config({"api_key": "gsk_primary", "backup_keys": ["gsk_backup1"]}, cfg_path)
            loaded = load_config(cfg_path)
            self.assertEqual(loaded["api_key"], "gsk_primary")
            self.assertEqual(loaded["backup_keys"], ["gsk_backup1"])

    def test_add_api_key_primary_and_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            from codex.config import add_api_key, load_config
            add_api_key("gsk_key1", cfg_path)
            cfg = load_config(cfg_path)
            self.assertEqual(cfg["api_key"], "gsk_key1")

            add_api_key("gsk_key2", cfg_path)
            cfg2 = load_config(cfg_path)
            self.assertEqual(cfg2["api_key"], "gsk_key1")
            self.assertIn("gsk_key2", cfg2["backup_keys"])

    def test_rotate_api_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            from codex.config import save_config, rotate_api_key, load_config
            save_config({"api_key": "gsk_first", "backup_keys": ["gsk_second", "gsk_third"]}, cfg_path)

            new_key = rotate_api_key(cfg_path)
            self.assertEqual(new_key, "gsk_second")
            cfg = load_config(cfg_path)
            self.assertEqual(cfg["api_key"], "gsk_second")
            self.assertEqual(cfg["backup_keys"], ["gsk_third", "gsk_first"])

    def test_get_api_key_env_and_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            from codex.config import save_config, get_api_key
            save_config({"api_key": "gsk_from_file"}, cfg_path)

            # File key
            orig_env = os.environ.pop("GROQ_API_KEY", None)
            try:
                self.assertEqual(get_api_key(cfg_path), "gsk_from_file")
                # Env var takes precedence
                os.environ["GROQ_API_KEY"] = "gsk_from_env"
                self.assertEqual(get_api_key(cfg_path), "gsk_from_env")
            finally:
                if orig_env:
                    os.environ["GROQ_API_KEY"] = orig_env
                else:
                    os.environ.pop("GROQ_API_KEY", None)


class TestPhase1Doctor(unittest.TestCase):
    def test_check_diagnostics(self):
        from codex.doctor import check_diagnostics
        results = check_diagnostics(model="qwen/qwen3.8-27b")
        components = [r["component"] for r in results]
        self.assertIn("Python Runtime", components)
        self.assertIn("Operating System", components)
        self.assertIn("Git Repository", components)
        self.assertIn("Terminal Display", components)
        self.assertIn("Workspace Path", components)
        self.assertIn("Inference Model", components)


class TestPhase1MascotAndModelNames(unittest.TestCase):
    def test_legless_mascot_has_four_rows(self):
        from codex.ui import render_mascot
        for state in ["center", "left", "right", "down", "blink"]:
            rendered = render_mascot(eye_state=state)
            lines = rendered.plain.splitlines()
            # Must be 4 rows (floating body without legs)
            self.assertEqual(len(lines), 4)

    def test_clean_model_name(self):
        from codex.ui import format_clean_model_name
        self.assertEqual(format_clean_model_name("gemini 3.8 flash antigravity"), "gemini 3.8 flash")
        self.assertEqual(format_clean_model_name("qwen3.8-27b-antigravity"), "qwen3.8-27b")
        self.assertEqual(format_clean_model_name("qwen/qwen3.8-27b"), "qwen/qwen3.8-27b")


class TestPhase1AuthFailover(unittest.TestCase):
    def test_client_rotate_failover(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            from codex.config import save_config
            save_config({
                "api_key": "gsk_primary_test",
                "backup_keys": ["gsk_backup_test"]
            }, cfg_path)
            from codex.client import GroqClient
            client = GroqClient(api_key="gsk_primary_test")
            # Rotate using custom config path
            from codex.config import rotate_api_key
            new_k = rotate_api_key(cfg_path)
            self.assertEqual(new_k, "gsk_backup_test")


class TestUI(unittest.TestCase):
    def test_ui_renders(self):
        from codex.ui import render_skills_list, render_key_saved, render_thinking_block, clear_terminal
        render_usage_tab({
            "used_5h": 12, "max_5h": 300, "remaining_5h": 288, "reset_5h": "in 4h 12m",
            "used_day": 12, "max_day": 300, "remaining_day": 288, "reset_day": "in 23h 48m"
        })
        render_doctor("qwen/qwen3.8-27b")
        render_memory_status(350, 24, 12, 5)
        render_help()
        render_skills_list([{"name": "test-skill", "description": "Unit test skill", "source": "global"}])
        render_key_saved("gsk_1234****5678", "/home/user/.codex/config.json")
        render_thinking_block("1. Inspect system\n2. Run verified implementation", elapsed=0.25)
        clear_terminal()


if __name__ == "__main__":
    unittest.main()



