"""Interactive hunk-by-hunk diff navigator and patch application engine."""

import re
from pathlib import Path
from typing import Callable, List, Optional


class DiffHunk:
    """Represents a single hunk in a unified diff."""

    def __init__(self, header: str, lines: list[str], old_start: int, old_len: int, new_start: int, new_len: int):
        self.header = header
        self.lines = lines
        self.old_start = old_start
        self.old_len = old_len
        self.new_start = new_start
        self.new_len = new_len
        self.accepted = False

    def render(self) -> str:
        return f"{self.header}\n" + "\n".join(self.lines)


class FileDiff:
    """Diff for a single file containing one or more hunks."""

    def __init__(self, file_path: str, hunks: list[DiffHunk]):
        self.file_path = file_path
        self.hunks = hunks


class DiffNavigator:
    """Parses unified diffs and navigates hunk-by-hunk with interactive acceptance."""

    HUNK_HEADER_REGEX = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")

    @classmethod
    def parse_unified_diff(cls, diff_text: str) -> list[FileDiff]:
        """Parse raw unified diff output into structured FileDiff and DiffHunk objects."""
        file_diffs: list[FileDiff] = []
        current_file: Optional[str] = None
        current_hunks: list[DiffHunk] = []
        current_lines: list[str] = []
        current_header = ""
        old_start, old_len, new_start, new_len = 0, 0, 0, 0

        def save_current_hunk():
            nonlocal current_lines, current_header
            if current_header and current_lines:
                hunk = DiffHunk(current_header, list(current_lines), old_start, old_len, new_start, new_len)
                current_hunks.append(hunk)
                current_lines = []
                current_header = ""

        def save_current_file():
            nonlocal current_file, current_hunks
            save_current_hunk()
            if current_file and current_hunks:
                file_diffs.append(FileDiff(current_file, list(current_hunks)))
                current_hunks = []
                current_file = None

        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                save_current_file()
                current_file = line[6:].strip()
            elif line.startswith("@@"):
                save_current_hunk()
                current_header = line
                m = cls.HUNK_HEADER_REGEX.match(line)
                if m:
                    old_start = int(m.group(1))
                    old_len = int(m.group(2) or 1)
                    new_start = int(m.group(3))
                    new_len = int(m.group(4) or 1)
            elif current_header:
                current_lines.append(line)

        save_current_file()
        return file_diffs

    @classmethod
    def inspect_diff_interactive(
        cls,
        diff_text: str,
        input_fn: Callable[[str], str] | None = None
    ) -> tuple[int, int]:
        """Interactively prompt user for each hunk ([y] accept, [n] skip, [a] accept all, [q] quit).
        
        Returns (accepted_count, total_count).
        """
        file_diffs = cls.parse_unified_diff(diff_text)
        total_hunks = sum(len(fd.hunks) for fd in file_diffs)
        accepted_count = 0
        accept_all = False

        prompt_reader = input_fn or input

        for fd in file_diffs:
            for i, hunk in enumerate(fd.hunks, start=1):
                if accept_all:
                    hunk.accepted = True
                    accepted_count += 1
                    continue

                prompt_msg = (
                    f"\n[Diff Hunk {i}/{len(fd.hunks)} for {fd.file_path}]\n"
                    f"{hunk.render()}\n"
                    "Accept this hunk? ([y]es / [n]o / [a]ll / [q]uit): "
                )
                try:
                    choice = prompt_reader(prompt_msg).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    return accepted_count, total_hunks

                if choice in ("y", "yes"):
                    hunk.accepted = True
                    accepted_count += 1
                elif choice in ("a", "all"):
                    hunk.accepted = True
                    accepted_count += 1
                    accept_all = True
                elif choice in ("q", "quit"):
                    return accepted_count, total_hunks
                else:
                    hunk.accepted = False

        return accepted_count, total_hunks
