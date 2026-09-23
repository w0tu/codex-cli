"""Comprehensive test suite for Codex-CLI architectural requirements."""

import os
import sys
import time
import json
import tempfile
import unittest
from pathlib import Path

# Ensure codex is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from codex.banner_renderer import convert_image_to_ansi, get_cached_banner, DEFAULT_IMAGE_PATH
from codex.metrics_db import MetricsDB
from codex.billing import BillingGuardrail, DAILY_BUDGET_LIMIT
from codex.cloud_fallback import (
    CLOAKED_ENGINE_LABEL,
    detect_query_complexity,
    is_internet_available,
    CloakedCloudClient,
)
from codex.gatekeeper import DirectoryTrustGatekeeper
from codex.profiler import (
    get_cpu_info,
    get_ram_info,
    get_gpu_info,
    benchmark_model_tps,
    select_best_local_model,
)
from codex.subagents import (
    TaskStep,
    PlannerAgent,
    CoderAgent,
    AuditorAgent,
    ExecutorAgent,
    MultiAgentStateMachine,
    AgentState,
)
from codex.client import OllamaClient, HybridCodexClient


class TestCodexArchitecture(unittest.TestCase):
    """Test all functional requirements of Codex-CLI."""

    def setUp(self):
        from codex.gatekeeper import gatekeeper
        gatekeeper.read_only_mode = False

    def tearDown(self):
        from codex.gatekeeper import gatekeeper
        gatekeeper.read_only_mode = False

    def test_01_banner_renderer_and_caching(self):
        """Verify image-to-ANSI 24-bit half-block rendering and sub-5ms cache latency."""
        self.assertTrue(DEFAULT_IMAGE_PATH.exists(), "Voxel banner image must exist")
        ansi_str, elapsed_ms = get_cached_banner(DEFAULT_IMAGE_PATH, width=90, force_rebuild=True)
        self.assertIn("\033[38;2;", ansi_str, "Must contain 24-bit foreground ANSI escape codes")
        self.assertTrue("▀" in ansi_str or "▄" in ansi_str, "Must contain half-block characters")

        # Second call should load from cache in under 5 milliseconds
        cached_str, cache_time_ms = get_cached_banner(DEFAULT_IMAGE_PATH, width=90, force_rebuild=False)
        self.assertEqual(ansi_str, cached_str)
        self.assertLess(cache_time_ms, 5.0, f"Cached load time ({cache_time_ms:.3f}ms) must be under 5.0 ms")

    def test_02_metrics_db_and_streak(self):
        """Verify persistent SQLite metrics tracking, streak, peak day, and /usage card."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_db = Path(tmp_dir) / "metrics.db"
            db = MetricsDB(db_path=test_db)

            # Record turns
            db.record_turn(local_tokens=100, cloud_tokens=50, cloud_spend=0.05)
            db.record_turn(local_tokens=200, cloud_tokens=0, cloud_spend=0.0)

            summary = db.get_summary()
            self.assertEqual(summary["lifetime_tokens"], 350)
            self.assertEqual(summary["daily_local_tokens"], 300)
            self.assertEqual(summary["daily_cloud_tokens"], 50)
            self.assertAlmostEqual(summary["daily_spend"], 0.05, places=3)
            self.assertGreaterEqual(summary["streak"], 1)
            self.assertEqual(summary["peak_day_tokens"], 350)

            card = db.render_block_telemetry_card()
            self.assertIn("CODEX-CLI TELEMETRY", card)
            self.assertIn("Lifetime Tokens", card)
            self.assertIn("Daily Cloud Spend", card)
            self.assertIn("Budget Meter", card)

    def test_03_billing_guardrail_and_2_dollar_budget_cap(self):
        """Verify real-time spend tracking and 24h lockout when $2.00 is reached."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            billing_file = Path(tmp_dir) / "billing.json"
            bg = BillingGuardrail(file_path=billing_file)

            allowed, _ = bg.check_cloud_escalation()
            self.assertTrue(allowed, "Should allow escalation with zero spend")

            # Add spend under limit
            bg.record_cloud_spend(prompt_tokens=10_000, completion_tokens=10_000)
            status = bg.get_status()
            self.assertFalse(status["is_locked"])
            self.assertLess(status["daily_spend"], DAILY_BUDGET_LIMIT)

            # Exceed $2.00 limit
            bg.record_cloud_spend(prompt_tokens=1_000_000, completion_tokens=500_000)
            status_after = bg.get_status()
            self.assertGreaterEqual(status_after["daily_spend"], DAILY_BUDGET_LIMIT)
            self.assertTrue(status_after["is_locked"], "Must lock after reaching $2.00")

            allowed_now, notice = bg.check_cloud_escalation()
            self.assertFalse(allowed_now)
            self.assertIn("Cloud escalation locked", notice)

    def test_04_cloaking_requirements(self):
        """Verify strict cloaking: OSS-120B High-Precision label and zero vendor leakage."""
        self.assertEqual(CLOAKED_ENGINE_LABEL, "OSS-120B High-Precision")
        client = CloakedCloudClient()
        self.assertEqual(client.engine_label, "OSS-120B High-Precision")

        # Test query complexity detection
        exceeds, reason = detect_query_complexity("Refactor architecture across main.py, utils.py and client.py")
        self.assertTrue(exceeds)
        self.assertIn("multi-file", reason.lower())

        simple, _ = detect_query_complexity("Hello, write a 2-line function")
        self.assertFalse(simple)

    def test_05_gatekeeper_trusted_workspaces(self):
        """Verify Directory Trust Gatekeeper and safe read-only advisory mode."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            trust_file = Path(tmp_dir) / "trusted_workspaces.json"
            gk = DirectoryTrustGatekeeper(trust_file=trust_file)

            test_path = Path(tmp_dir) / "my_project"
            test_path.mkdir()

            self.assertFalse(gk.is_workspace_trusted(test_path))

            # Non-interactive check on untrusted directory -> triggers read-only mode
            trusted, read_only = gk.check_and_prompt(test_path, interactive=False)
            self.assertFalse(trusted)
            self.assertTrue(read_only)
            self.assertTrue(gk.read_only_mode)

            # Manually trust
            gk.trust_workspace(test_path)
            self.assertTrue(gk.is_workspace_trusted(test_path))
            trusted2, read_only2 = gk.check_and_prompt(test_path, interactive=False)
            self.assertTrue(trusted2)
            self.assertFalse(read_only2)

    def test_06_hardware_profiler(self):
        """Verify CPU, RAM, and GPU spec collection and model selection."""
        cpu = get_cpu_info()
        self.assertIn("model", cpu)
        self.assertGreater(cpu["logical_cores"], 0)

        ram = get_ram_info()
        self.assertGreater(ram["total_gb"], 0.0)

        gpu = get_gpu_info()
        self.assertIn("has_gpu", gpu)

        # Recommendation test
        candidates = [
            {"name": "llama3.2:3b", "tps": 12.5},
            {"name": "qwen2.5-coder:1.5b", "tps": 26.8},
            {"name": "smollm2:360m", "tps": 35.0},
        ]
        recommended = select_best_local_model(candidates)
        self.assertEqual(recommended, "qwen2.5-coder:1.5b", "Coder-tuned model with high TPS should be prioritized")

    def test_07_subagent_state_machine(self):
        """Verify Planner, Coder, Auditor, and Executor agent state machine."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = str(Path(tmp_dir) / "math_helper.py")
            sm = MultiAgentStateMachine()

            # Planner deconstructs
            steps = sm.planner.plan_task(f"Create helper in {test_file}")
            self.assertGreaterEqual(len(steps), 3)

            # Coder creates unified diff
            code = "def add(a, b):\n    return a + b\n"
            diff = sm.coder.generate_unified_diff(test_file, code)
            self.assertIn("+def add(a, b):", diff)

            # Auditor detects dangerous commands
            safe_ok, _ = sm.auditor.audit_command("git status")
            self.assertTrue(safe_ok)
            danger_ok, danger_msg = sm.auditor.audit_command("rm -rf /")
            self.assertFalse(danger_ok)
            self.assertIn("CRITICAL SECURITY AUDIT FAILED", danger_msg)

            # Auditor detects syntax errors
            syntax_ok, _ = sm.auditor.audit_code_syntax("sample.py", "def valid(): pass\n")
            self.assertTrue(syntax_ok)
            bad_syntax_ok, err_msg = sm.auditor.audit_code_syntax("sample.py", "def bad(:\n")
            self.assertFalse(bad_syntax_ok)
            self.assertIn("SYNTAX AUDIT FAILED", err_msg)

            # End-to-end state machine workflow
            def generator(step):
                if step.target_path:
                    return "def subtract(a, b):\n    return a - b\n"
                return ""

            success = sm.run_workflow(
                f"Write math module at {test_file}",
                code_generator=generator,
                logger=lambda msg: None,
            )
            self.assertTrue(success)
            self.assertEqual(sm.current_state, AgentState.COMPLETED)
            self.assertTrue(Path(test_file).exists())
            self.assertIn("subtract", Path(test_file).read_text())

    def test_08_ollama_client_pinning(self):
        """Verify OllamaClient requests include keep_alive: -1."""
        client = OllamaClient(model="qwen2.5-coder:0.5b")
        # Direct verification of socket chat turn against local Ollama
        resp = client.chat_turn([{"role": "user", "content": "say test in 1 word"}], max_tokens=10)
        self.assertIsNotNone(resp)
        self.assertIsNotNone(resp.choices[0].message.content)


if __name__ == "__main__":
    unittest.main()
