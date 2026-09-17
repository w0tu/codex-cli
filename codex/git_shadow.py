"""Shadow Git checkpoint versioning using custom ref refs/codex/history."""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional


class GitShadowManager:
    """Manages shadow checkpoints of the working tree without altering user branch history."""

    SHADOW_REF = "refs/codex/history"

    def __init__(self, repo_path: str | None = None):
        self.repo_path = Path(repo_path or os.getcwd()).resolve()

    def _run_git(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=str(self.repo_path)
        )

    def is_git_repo(self) -> bool:
        res = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return res.returncode == 0 and res.stdout.strip() == "true"

    def create_checkpoint(self, message: str = "") -> Optional[str]:
        """Create shadow checkpoint commit on refs/codex/history without touching the working branch."""
        if not self.is_git_repo():
            return None

        # 1. Write current directory index to tree object
        tree_res = self._run_git(["write-tree"])
        if tree_res.returncode != 0:
            # Stage temporary index if unstaged
            return None
        tree_id = tree_res.stdout.strip()

        # 2. Check if parent commit exists on shadow ref
        parent_res = self._run_git(["rev-parse", "--verify", self.SHADOW_REF])
        parents = ["-p", parent_res.stdout.strip()] if parent_res.returncode == 0 else []

        # 3. Create commit object
        commit_msg = message.strip() or f"Codex Shadow Checkpoint: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        commit_args = ["commit-tree", tree_id] + parents + ["-m", commit_msg]
        commit_res = self._run_git(commit_args)
        if commit_res.returncode != 0:
            return None
        commit_id = commit_res.stdout.strip()

        # 4. Update shadow ref to point to new commit
        self._run_git(["update-ref", self.SHADOW_REF, commit_id])
        return commit_id

    def list_checkpoints(self, limit: int = 10) -> list[dict[str, str]]:
        """List recent shadow checkpoints."""
        if not self.is_git_repo():
            return []
        log_res = self._run_git([
            "log",
            "-n", str(limit),
            "--format=%H|%ct|%s",
            self.SHADOW_REF
        ])
        if log_res.returncode != 0:
            return []

        checkpoints = []
        for line in log_res.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                checkpoints.append({
                    "commit_id": parts[0],
                    "timestamp": parts[1],
                    "message": parts[2],
                })
        return checkpoints

    def rollback(self, commit_id: str) -> bool:
        """Roll back working directory to match the specified checkpoint commit."""
        if not self.is_git_repo():
            return False
        # Read tree of checkpoint into working index
        res = self._run_git(["read-tree", commit_id])
        if res.returncode != 0:
            return False
        # Checkout index files into workspace
        checkout_res = self._run_git(["checkout-index", "-a", "-f"])
        return checkout_res.returncode == 0
