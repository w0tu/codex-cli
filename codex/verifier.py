"""Autonomous closed-loop verification, test runner, loop breaker, and conventional commits."""

import os
import subprocess
from pathlib import Path
from typing import Any, List, Optional, Tuple


class AutonomousVerifier:
    """Discovers, executes, and validates project test suites and linters."""

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.failure_history: List[str] = []

    def detect_test_command(self) -> Optional[str]:
        """Auto-detect test command based on repository markers."""
        if (self.workspace_root / "pytest.ini").exists() or (self.workspace_root / "tests").exists():
            # Check if pytest or unittest is appropriate
            return "python3 -m unittest discover tests" if not (self.workspace_root / "pytest.ini").exists() else "pytest"
        if (self.workspace_root / "package.json").exists():
            return "npm test"
        if (self.workspace_root / "Cargo.toml").exists():
            return "cargo test"
        if (self.workspace_root / "go.mod").exists():
            return "go test ./..."
        return None

    def detect_linter_command(self) -> Optional[str]:
        """Auto-detect linter command based on environment and config."""
        if (self.workspace_root / "ruff.toml").exists() or (self.workspace_root / "pyproject.toml").exists():
            return "ruff check ."
        if (self.workspace_root / ".eslintrc.json").exists() or (self.workspace_root / ".eslintrc.js").exists():
            return "npx eslint ."
        if (self.workspace_root / "Cargo.toml").exists():
            return "cargo clippy"
        return None

    def run_tests(self, custom_command: str | None = None) -> Tuple[bool, str]:
        """Execute test suite inside an isolated subshell."""
        cmd = custom_command or self.detect_test_command()
        if not cmd:
            return True, "No test suite detected in workspace."

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.workspace_root),
            )
            passed = proc.returncode == 0
            output = (proc.stdout + "\n" + proc.stderr).strip()

            if not passed:
                self.record_failure(output)
            else:
                self.failure_history.clear()

            return passed, output
        except Exception as e:
            return False, f"Error executing test suite: {e}"

    def record_failure(self, error_output: str) -> None:
        """Record error output to track repetitive failure loops."""
        first_line = error_output.splitlines()[0] if error_output.splitlines() else "Unknown failure"
        self.failure_history.append(first_line)

    def is_looping(self, threshold: int = 3) -> bool:
        """Check whether the last N failures are identical (3-cycle failure loop)."""
        if len(self.failure_history) < threshold:
            return False
        recent = self.failure_history[-threshold:]
        return all(f == recent[0] for f in recent)

    @staticmethod
    def generate_conventional_commit_msg(diff_text: str) -> str:
        """Analyze git diff text and generate a standard conventional commit message."""
        lines = diff_text.splitlines()
        modified_files = [l[6:].strip() for l in lines if l.startswith("+++ b/")]

        if any("test" in f.lower() for f in modified_files):
            prefix = "test"
        elif any("doc" in f.lower() or f.endswith(".md") for f in modified_files):
            prefix = "docs"
        elif "fix" in diff_text.lower() or "bug" in diff_text.lower():
            prefix = "fix"
        elif "refactor" in diff_text.lower():
            prefix = "refactor"
        else:
            prefix = "feat"

        scope = ""
        if modified_files:
            main_file = Path(modified_files[0]).stem
            scope = f"({main_file})"

        return f"{prefix}{scope}: apply verified changes across {len(modified_files)} files"
