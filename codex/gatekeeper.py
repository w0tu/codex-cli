"""Directory Trust Gatekeeper: Workspace Security and Tool Permissions.

Enforces directory trust check whenever launched in a working directory not listed
in ~/.config/codex_cli/trusted_workspaces.json.
Prompts:
[SECURITY] Untrusted workspace detected: <path>. Allow AI file edits and terminal tool execution? [y/N]
If rejected, forces session into safe read-only advisory mode.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Tuple

CONFIG_DIR = Path.home() / ".config" / "codex_cli"
TRUSTED_WORKSPACES_FILE = CONFIG_DIR / "trusted_workspaces.json"


class DirectoryTrustGatekeeper:
    """Manages workspace access control and read-only isolation."""

    def __init__(self, trust_file: Path = TRUSTED_WORKSPACES_FILE):
        self.trust_file = trust_file
        self.trust_file.parent.mkdir(parents=True, exist_ok=True)
        self.read_only_mode = False

    def load_trusted_workspaces(self) -> List[str]:
        if not self.trust_file.exists():
            return []
        try:
            data = json.loads(self.trust_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [str(Path(p).resolve()) for p in data]
            elif isinstance(data, dict) and "trusted" in data:
                return [str(Path(p).resolve()) for p in data["trusted"]]
            return []
        except Exception:
            return []

    def save_trusted_workspaces(self, workspaces: List[str]) -> None:
        try:
            cleaned = sorted(list(set(str(Path(p).resolve()) for p in workspaces)))
            self.trust_file.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
        except Exception:
            pass

    def is_workspace_trusted(self, target_dir: Path | str) -> bool:
        resolved = str(Path(target_dir).resolve())
        trusted = self.load_trusted_workspaces()
        return resolved in trusted

    def trust_workspace(self, target_dir: Path | str) -> None:
        resolved = str(Path(target_dir).resolve())
        trusted = self.load_trusted_workspaces()
        if resolved not in trusted:
            trusted.append(resolved)
            self.save_trusted_workspaces(trusted)

    def check_and_prompt(self, target_dir: Path | str | None = None, interactive: bool = True) -> Tuple[bool, bool]:
        """Perform gatekeeper check on startup.
        
        Returns:
            (is_trusted: bool, read_only_mode: bool)
        """
        cwd_path = Path(target_dir or os.getcwd()).resolve()
        resolved_str = str(cwd_path)

        if self.is_workspace_trusted(cwd_path):
            self.read_only_mode = False
            return True, False

        prompt_str = (
            f"\033[1;33m[SECURITY] Untrusted workspace detected: {resolved_str}\033[0m\n"
            f"Allow AI file edits and terminal tool execution? [y/N] "
        )
        sys.stdout.write(prompt_str)
        sys.stdout.flush()

        if not interactive or not sys.stdin.isatty():
            sys.stdout.write("N (non-interactive default)\n")
            sys.stdout.flush()
            self.read_only_mode = True
            return False, True

        try:
            choice = sys.stdin.readline().strip().lower()
            if choice in ["y", "yes"]:
                self.trust_workspace(cwd_path)
                sys.stdout.write("\033[1;32m✓ Workspace trusted. Full agent edit permissions granted.\033[0m\n\n")
                sys.stdout.flush()
                self.read_only_mode = False
                return True, False
            else:
                self.read_only_mode = True
                sys.stdout.write("\033[1;33m⚠ Workspace marked untrusted. Operating in safe read-only advisory mode.\033[0m\n\n")
                sys.stdout.flush()
                return False, True
        except Exception:
            self.read_only_mode = True
            return False, True


# Global gatekeeper instance
gatekeeper = DirectoryTrustGatekeeper()
