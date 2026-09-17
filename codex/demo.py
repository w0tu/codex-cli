"""Standalone demonstration of Codex Phase 2 Inline Streaming Terminal UI.

Can be run via:
    python3 -m codex.demo [--non-interactive]
"""

import argparse
import os
import sys
import time
from codex.terminal import (
    clear_line,
    cursor_up,
    get_terminal_width,
    inline_thinking_timer,
    InlineToolSpinner,
    is_interactive,
    read_key_inline,
    render_box,
    render_progress_bar,
    strip_ansi,
)
from codex.ui import (
    prompt_apply_changes,
    render_header,
    render_inline_diff,
    stream_assistant_chunk,
)


def run_demo(non_interactive: bool = False) -> None:
    """Execute live simulation of inline streaming terminal UI."""
    print("=" * 60)
    print("  Codex Inline Streaming Terminal UI Demonstration")
    print("=" * 60)
    print()

    # 1. Visual Branding & ASCII Header (Standard stdout lines)
    header = render_header(model_name="qwen/qwen3.8-27b", cwd=os.getcwd())
    from rich.console import Console
    Console().print(header)
    print()

    # 2. Inline Prompt
    dirname = os.path.basename(os.getcwd()) or "~"
    sys.stdout.write(f"\x1b[1;37mcodex\x1b[0m \x1b[2min\x1b[0m \x1b[36m{dirname}\x1b[0m \x1b[1;37m>\x1b[0m Refactor authentication token verification\n\n")
    sys.stdout.flush()

    # 3. Dynamic In-Place Thinking Timer
    print("[1/4] Demonstrating in-place thinking timer...")
    if non_interactive:
        sys.stdout.write("Thought for 0.19s\n\n")
    else:
        inline_thinking_timer(
            prompt="Refactor authentication token verification",
            duration=0.6,
            phases=[
                "Parsing AST symbol table for src/auth.py...",
                "Evaluating token expiration and HMAC security...",
                "Synthesizing isolated patch..."
            ]
        )

    # 4. Inline Tool Execution with Braille Spinner -> In-Place Status Overwrite
    print("[2/4] Demonstrating inline tool execution summaries...")

    # Tool 1: Successful read
    with InlineToolSpinner("Read src/auth.py") as sp:
        time.sleep(0.3 if not non_interactive else 0.05)
        sp.finish(success=True, summary="Read src/auth.py")

    # Tool 2: Progress bar for multi-step indexing
    if not non_interactive:
        for i in range(1, 6):
            render_progress_bar(i, 5, label="Indexing project symbols...")
            time.sleep(0.08)

    # Tool 3: Failed command with indented stderr preview
    with InlineToolSpinner("pytest tests/test_login.py") as sp:
        time.sleep(0.3 if not non_interactive else 0.05)
        mock_stderr = (
            "FAILED tests/test_login.py::test_auth_expired - AssertionError: TokenExpired\n"
            "assert False == True\n"
            "tests/test_login.py:42: in test_auth_expired"
        )
        sp.finish(success=False, summary="pytest tests/test_login.py", stderr=mock_stderr)

    print()

    # 5. Streaming Markdown Response
    print("[3/4] Demonstrating streaming response chunks...")
    assistant_text = (
        "I have identified the authentication bug in `src/auth.py`. "
        "The token validator did not check for unix timestamp expiration.\n\n"
        "Here is the proposed atomic patch:\n"
    )
    for word in assistant_text.split(" "):
        stream_assistant_chunk(word + " ")
        if not non_interactive:
            time.sleep(0.02)
    print("\n")

    # 6. Inline Diff and Keystroke Prompt
    print("[4/4] Demonstrating compact inline diff and [y/n/d/e] prompt...")
    sample_diff = """--- a/src/auth.py
+++ b/src/auth.py
@@ -14,4 +14,6 @@ def verify_token(token: str) -> bool:
     payload = decode_jwt(token)
+    if payload.get("exp", 0) < time.time():
+        return False
     return payload.get("active", False)
"""
    render_inline_diff(sample_diff)
    print()

    if non_interactive:
        print("Apply these changes? [y]es, [n]o, [d]iff view, [e]dit: y (simulated)")
        choice = "y"
    else:
        choice = prompt_apply_changes()

    print(f"\n[Inline Prompt Result] User selected: '{choice}'")
    render_box("Execution Summary", [
        f"Selected Option: {choice.upper()}",
        "Scrollback: Completely preserved",
        "Terminal Buffers: Alternate screen buffer not used",
        "ANSI Control: In-place line updates verified",
    ])


def main():
    parser = argparse.ArgumentParser(description="Codex Phase 2 Inline Streaming Terminal UI Demo")
    parser.add_argument("--non-interactive", action="store_true", help="Run without requiring manual keystroke inputs.")
    args = parser.parse_args()
    run_demo(non_interactive=args.non_interactive)


if __name__ == "__main__":
    main()
