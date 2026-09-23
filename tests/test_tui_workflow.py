import unittest
import os
from unittest.mock import patch

from codex.main import Session
from codex.ui import (
    render_opencode_tokyonight_banner,
    render_opencode_dashboard,
    render_stage2_turn_header,
    render_sessions_catalog,
    render_inline_diff_box,
)


class TestTuiWorkflow(unittest.TestCase):
    def test_session_stage_tracking(self):
        s = Session()
        self.assertEqual(s.tui_stage, 1, "Session must initialize at Stage 1 (Welcome Screen)")
        s.tui_stage = 2
        self.assertEqual(s.tui_stage, 2, "Session must allow transitioning to Stage 2 (Active Workspace Dashboard)")
        s.reset()
        self.assertEqual(s.tui_stage, 1, "Session reset must return to Stage 1")

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 24)))
    def test_render_stage1_welcome_banner_80_col(self, mock_term):
        render_opencode_tokyonight_banner(model_name="Groq LPU (qwen3.8-27b)")

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 24)))
    def test_render_stage2_dashboard_80_col_stacked(self, mock_term):
        render_opencode_dashboard(
            active_agent="0m0",
            model_name="qwen/qwen3.8-27b",
            cwd=os.getcwd(),
            query_title="Test prompt in 80 col"
        )

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((120, 40)))
    def test_render_stage2_dashboard_120_col_split(self, mock_term):
        render_opencode_dashboard(
            active_agent="0m0",
            model_name="qwen/qwen3.8-27b",
            cwd=os.getcwd(),
            query_title="Test prompt in 120 col"
        )

    def test_render_stage2_turn_header(self):
        render_stage2_turn_header(query_text="Fix button color in settings.tsx", model_name="qwen/qwen3.8-27b")

    def test_render_sessions_catalog(self):
        render_sessions_catalog()

    def test_render_inline_diff_box_approval(self):
        diff_example = (
            "--- a/settings.tsx\n"
            "+++ b/settings.tsx\n"
            "@@ -1,3 +1,3 @@\n"
            " <Button\n"
            "-  variant=\"primary\"\n"
            "+  variant=\"danger\"\n"
            " />"
        )
        with patch("rich.console.Console.input", return_value="y"):
            approved = render_inline_diff_box("settings.tsx", diff_example, prompt_permission=True)
            self.assertTrue(approved, "Diff should be approved when user enters 'y'")

        with patch("rich.console.Console.input", return_value="n"):
            denied = render_inline_diff_box("settings.tsx", diff_example, prompt_permission=True)
            self.assertFalse(denied, "Diff should be denied when user enters 'n'")


if __name__ == "__main__":
    unittest.main()
