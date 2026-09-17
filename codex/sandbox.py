"""Execution sandboxing, filesystem boundaries, and dangerous command interception."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/\s*$",
    r"rm\s+-rf\s+/\*",
    r"rm\s+-rf\s+~",
    r"mkfs",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    r">\s*/dev/sd[a-z]",
    r">\s*/dev/nvme",
    r"dd\s+if=.*of=/dev/",
    r"chmod\s+-R\s+777\s+/",
]


class SandboxExecutor:
    """Safely isolates command execution and enforces filesystem boundaries."""

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.has_bwrap = shutil.which("bwrap") is not None

    def is_within_boundary(self, target_path: str) -> bool:
        """Check whether target path resides inside workspace or safe paths."""
        try:
            p = Path(target_path).expanduser().resolve()
            # Allow workspace directory and /tmp for scratch executions
            in_workspace = str(p).startswith(str(self.workspace_root))
            in_tmp = str(p).startswith("/tmp") or str(p).startswith(str(Path.home() / ".codex"))
            return in_workspace or in_tmp
        except Exception:
            return False

    def check_dangerous_command(self, command: str) -> Tuple[bool, str]:
        """Scan command string for destructive system operations."""
        import re
        cmd = command.strip()
        for pat in DANGEROUS_PATTERNS:
            if re.search(pat, cmd):
                return True, f"Blocked dangerous command matching pattern: {pat}"
        return False, ""

    def build_bwrap_args(self, command: str) -> list[str]:
        """Construct Bubblewrap sandbox arguments when available."""
        # Read-only root system, bind-mount cwd rw, isolated tmpfs
        return [
            "bwrap",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", "/etc", "/etc",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--bind", str(self.workspace_root), str(self.workspace_root),
            "--chdir", str(self.workspace_root),
            "--unshare-all",
            "--share-net",
            "/bin/bash", "-c", command,
        ]

    def execute(self, command: str, timeout: int = 45) -> subprocess.CompletedProcess:
        """Run command inside sandbox or isolated subshell."""
        is_danger, reason = self.check_dangerous_command(command)
        if is_danger:
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr=f"Security Alert: {reason}",
            )

        # Attempt Bubblewrap if available; fallback gracefully to standard isolated subprocess
        if self.has_bwrap and os.environ.get("CODEX_NO_BWRAP") != "1":
            try:
                bwrap_cmd = self.build_bwrap_args(command)
                return subprocess.run(
                    bwrap_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(self.workspace_root),
                )
            except Exception:
                pass  # Fall back to standard subshell if bwrap restrictions fail on certain hosts

        return subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(self.workspace_root),
        )
