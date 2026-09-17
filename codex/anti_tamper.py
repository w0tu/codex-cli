"""Anti-test tampering lock: uses cryptographic SHA-256 hashes to prevent test assertion modifications."""

import hashlib
import os
from pathlib import Path
from typing import Dict, List, Tuple


class AntiTamperGuard:
    """Enforces that agents fix implementation code rather than rewriting test assertions to force a pass."""

    TEST_PATTERNS = ["test_*.py", "*_test.py", "tests/**/*.py", "test/**/*.py"]

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.baseline_hashes: Dict[str, str] = {}
        self.snapshot_baselines()

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute SHA-256 hex digest of a file."""
        h = hashlib.sha256()
        h.update(file_path.read_bytes())
        return h.hexdigest()

    def discover_test_files(self) -> List[Path]:
        """Find all test files in the workspace."""
        found: set[Path] = set()
        for pat in self.TEST_PATTERNS:
            for p in self.workspace_root.glob(pat):
                if p.is_file() and not any(part.startswith(".") for part in p.parts):
                    found.add(p)
        return sorted(list(found))

    def snapshot_baselines(self) -> Dict[str, str]:
        """Record baseline cryptographic fingerprints for all test suites."""
        self.baseline_hashes.clear()
        for test_file in self.discover_test_files():
            rel = str(test_file.relative_to(self.workspace_root))
            self.baseline_hashes[rel] = self.compute_sha256(test_file)
        return self.baseline_hashes

    def audit_tampering(self) -> Tuple[bool, List[str]]:
        """Verify whether any existing test file assertions have been modified.
        
        Returns (is_tampered, list_of_modified_files).
        """
        tampered_files: List[str] = []
        for rel_path, baseline_hash in self.baseline_hashes.items():
            full_path = self.workspace_root / rel_path
            if not full_path.exists():
                tampered_files.append(f"{rel_path} (deleted)")
            else:
                current_hash = self.compute_sha256(full_path)
                if current_hash != baseline_hash:
                    tampered_files.append(rel_path)

        return len(tampered_files) > 0, tampered_files
