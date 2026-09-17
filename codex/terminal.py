"""Inline terminal line management, ANSI cursor manipulation, and live streaming primitives."""

import os
import re
import shutil
import sys
import termios
import threading
import time
import tty
from contextlib import contextmanager
from typing import Callable, Generator, List, Optional, Tuple

ANSI_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

BRAILLE_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text for clean logging or non-TTY piping."""
    return ANSI_REGEX.sub("", text)


def is_interactive() -> bool:
    """Check whether stdout is connected to an interactive TTY."""
    return sys.stdout.isatty() and sys.stdin.isatty()


def get_terminal_width(default: int = 80) -> int:
    """Retrieve current terminal columns safely."""
    try:
        return shutil.get_terminal_size(fallback=(default, 24)).columns
    except Exception:
        return default


def clear_line() -> None:
    """Clear the entire current terminal line and return cursor to column 0."""
    if is_interactive():
        sys.stdout.write("\r\x1b[2K")
        sys.stdout.flush()


def cursor_up(lines: int = 1) -> None:
    """Move cursor up by N lines."""
    if is_interactive() and lines > 0:
        sys.stdout.write(f"\x1b[{lines}A")
        sys.stdout.flush()


def hide_cursor() -> None:
    """Hide terminal cursor."""
    if is_interactive():
        sys.stdout.write("\x1b[?25l")
        sys.stdout.flush()


def show_cursor() -> None:
    """Show terminal cursor."""
    if is_interactive():
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()


def read_key_inline(prompt: str, valid_keys: Optional[List[str]] = None) -> str:
    """Read a single key press in raw mode without requiring Enter on TTY."""
    sys.stdout.write(prompt)
    sys.stdout.flush()

    if not is_interactive():
        try:
            line = sys.stdin.readline().strip().lower()
            return line[0] if line else ""
        except Exception:
            return ""

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            # Handle Ctrl+C or Ctrl+D
            if ch in ("\x03", "\x04"):
                raise KeyboardInterrupt
            key = ch.lower()
            if not valid_keys or key in [k.lower() for k in valid_keys]:
                sys.stdout.write(f"{ch}\n")
                sys.stdout.flush()
                return key
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def inline_thinking_timer(
    prompt: str = "",
    duration: float = 0.35,
    phases: Optional[List[str]] = None
) -> float:
    """In-place dynamic thinking timer that updates on a single line and finalizes without clearing scrollback."""
    t0 = time.perf_counter()
    if not is_interactive():
        return 0.0

    phases = phases or [
        "Analyzing intent & context...",
        "Evaluating technical constraints...",
        "Formulating verified solution..."
    ]

    hide_cursor()
    fps = 25
    steps = max(int(duration * fps), 6)
    delay = duration / steps

    try:
        for i in range(steps):
            elapsed = time.perf_counter() - t0
            spin = BRAILLE_SPINNER[i % len(BRAILLE_SPINNER)]
            phase_idx = min(int((i / steps) * len(phases)), len(phases) - 1)
            phase = phases[phase_idx]

            # In-place single-line update using \r and \x1b[2K
            line = f"\r\x1b[2K\x1b[1;37m{spin}\x1b[0m \x1b[1;37mThinking... [{elapsed:.1f}s]\x1b[0m \x1b[2m· {phase}\x1b[0m"
            sys.stdout.write(line)
            sys.stdout.flush()
            time.sleep(delay)

        total_elapsed = time.perf_counter() - t0
        # Finalize on the exact same line
        final_line = f"\r\x1b[2K\x1b[2;3mThought for {total_elapsed:.2f}s\x1b[0m\n\n"
        sys.stdout.write(final_line)
        sys.stdout.flush()
        return total_elapsed
    finally:
        show_cursor()


class InlineToolSpinner:
    """Renders a live single-line Braille spinner while a tool runs, then overwrites with success/failure status."""

    def __init__(self, label: str):
        self.label = label
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        if is_interactive():
            hide_cursor()
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        else:
            sys.stdout.write(f"-> {self.label}...\n")
            sys.stdout.flush()
        return self

    def _spin(self):
        idx = 0
        while not self.stop_event.is_set():
            spin = BRAILLE_SPINNER[idx % len(BRAILLE_SPINNER)]
            elapsed_ms = int((time.perf_counter() - self.start_time) * 1000)
            sys.stdout.write(f"\r\x1b[2K\x1b[1;37m{spin}\x1b[0m \x1b[37m{self.label}\x1b[0m \x1b[2m({elapsed_ms}ms)\x1b[0m")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)

    def finish(self, success: bool, summary: str, stderr: Optional[str] = None) -> None:
        """Stop spinner and overwrite the line in-place with finalized status."""
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.3)
        show_cursor()

        elapsed_ms = int((time.perf_counter() - self.start_time) * 1000)
        if success:
            mark = "\x1b[1;32m✔\x1b[0m"
            status_text = f"\r\x1b[2K{mark} \x1b[1;37m{summary}\x1b[0m \x1b[2m({elapsed_ms}ms)\x1b[0m\n"
            sys.stdout.write(status_text)
            sys.stdout.flush()
        else:
            mark = "\x1b[1;31m✖\x1b[0m"
            status_text = f"\r\x1b[2K{mark} \x1b[1;31mFailed\x1b[0m \x1b[1;37m{summary}\x1b[0m \x1b[2m({elapsed_ms}ms)\x1b[0m\n"
            sys.stdout.write(status_text)
            if stderr and stderr.strip():
                # Indented preview of error output
                lines = stderr.strip().splitlines()
                preview = lines[:6]
                for l in preview:
                    sys.stdout.write(f"  \x1b[2;31m│\x1b[0m \x1b[31m{l}\x1b[0m\n")
                if len(lines) > 6:
                    sys.stdout.write(f"  \x1b[2m│ ... ({len(lines)-6} more error lines omitted)\x1b[0m\n")
            sys.stdout.flush()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.stop_event.is_set():
            self.finish(success=(exc_type is None), summary=self.label)


def render_progress_bar(current: int, total: int, label: str = "", bar_width: int = 20) -> None:
    """Render an in-place single-line progress bar."""
    if not is_interactive() or total <= 0:
        return
    fraction = min(max(current / total, 0.0), 1.0)
    filled = int(fraction * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    percent = int(fraction * 100)
    sys.stdout.write(f"\r\x1b[2K[\x1b[1;37m{bar}\x1b[0m] {percent}% \x1b[2m{label}\x1b[0m")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")
        sys.stdout.flush()


def render_box(title: str, lines: List[str], style: str = "white") -> None:
    """Render formatted box-drawing boundaries (╭─, │, ╰─) fitted to terminal width."""
    width = min(get_terminal_width(80), 100)
    inner_w = max(width - 4, 20)

    # Header
    title_display = f" {title} " if title else ""
    dashes = "─" * max(inner_w - len(title_display), 2)
    sys.stdout.write(f"\x1b[2m╭─\x1b[0m\x1b[1m{title_display}\x1b[0m\x1b[2m{dashes}\x1b[0m\n")

    # Body
    for line in lines:
        sys.stdout.write(f"\x1b[2m│\x1b[0m {line}\n")

    # Footer
    bot_dashes = "─" * (inner_w + len(title_display))
    sys.stdout.write(f"\x1b[2m╰─{bot_dashes}\x1b[0m\n\n")
    sys.stdout.flush()
