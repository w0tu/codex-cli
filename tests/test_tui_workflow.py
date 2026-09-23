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
        render_opencode_tokyonight_banner(model_name="Cloud Native (qwen3.8-27b)")

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
        with patch("codex.ui.console.input", return_value="y"):
            approved = render_inline_diff_box("settings.tsx", diff_example, prompt_permission=True)
            self.assertTrue(approved, "Diff should be approved when user enters 'y'")

        with patch("codex.ui.console.input", return_value="n"):
            denied = render_inline_diff_box("settings.tsx", diff_example, prompt_permission=True)
            self.assertFalse(denied, "Diff should be denied when user enters 'n'")

    def test_mouse_controller(self):
        from codex.mouse_control import mouse_controller
        self.assertTrue(mouse_controller.is_available)
        pos = mouse_controller.get_position()
        self.assertIn("x", pos)
        self.assertIn("y", pos)
        sz = mouse_controller.get_screen_size()
        self.assertIn("width", sz)
        self.assertIn("height", sz)

    def test_tools_mouse_and_wifi(self):
        from codex.tools import run_tool
        res_pos = run_tool("control_mouse", {"action": "position"})
        self.assertIn("Mouse cursor at", res_pos)
        res_sz = run_tool("control_mouse", {"action": "screen_size"})
        self.assertIn("Screen resolution:", res_sz)
        res_wifi = run_tool("wifi_status", {})
        self.assertIn("WiFi Status:", res_wifi)

    def test_antigravity_bridge(self):
        from codex.antigravity_bridge import delegate_to_antigravity
        with patch("os.path.exists", return_value=False), patch("codex.client.AntigravityClient.chat_turn") as mock_chat:
            class DummyChoice:
                class DummyMsg:
                    content = "Mocked Antigravity architectural output"
                message = DummyMsg()
            class DummyResp:
                choices = [DummyChoice()]
            mock_chat.return_value = DummyResp()
            res = delegate_to_antigravity("Build microservice scaffold")
            self.assertIn("Antigravity", res)


if __name__ == "__main__":
    unittest.main()
