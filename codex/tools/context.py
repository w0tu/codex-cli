"""Inline 10x10 Token Visualizer & Context Window Breakdown for Codex."""

import sys
import os
from typing import Any
from codex.context.tracker import (
    ContextSnapshot,
    ContextTracker,
    format_tokens,
    format_ratio_tokens,
)

# Color definitions (24-bit TrueColor with ANSI fallback)
CLR_RESET = "\033[0m"
CLR_BOLD = "\033[1m"
CLR_DIM = "\033[2m"
CLR_WHITE = "\033[1;37m"

# Palette matching Claude Code context visualizer
CLR_AMBER = "\033[38;2;217;119;87m"       # System prompt (Coral/Amber)
CLR_TEAL = "\033[38;2;78;201;176m"        # System tools (Teal/Cyan)
CLR_LIGHTBLUE = "\033[38;2;56;189;248m"   # MCP tools (Light Blue)
CLR_ORANGE = "\033[38;2;229;128;96m"      # Memory files (Orange/Coral)
CLR_PURPLE = "\033[38;2;189;147;249m"     # Messages (Purple/Magenta)
CLR_GRAY = "\033[38;2;90;95;105m"         # Free space (Dim Gray)

CATEGORY_COLORS = {
    "system_prompt": CLR_AMBER,
    "system_tools": CLR_TEAL,
    "mcp_tools": CLR_LIGHTBLUE,
    "memory_files": CLR_ORANGE,
    "messages": CLR_PURPLE,
    "free_space": CLR_GRAY,
}

# Unicode Glyphs
GLYPH_DISK = "⛁"       # White Draughts King (Stacked Disks)
GLYPH_CORNERS = "⛶"    # Square Four Corners (Dashed/Empty Bracket)
GLYPH_CIRCLE = "⊝"     # Fallback circled dash
GLYPH_BRACKET = "[ ]"  # Fallback bracket


def build_context_view(snapshot: ContextSnapshot, fallback_glyphs: bool = False) -> str:
    """Construct the complete formatted context visualizer string."""
    glyph_filled = GLYPH_CIRCLE if fallback_glyphs else GLYPH_DISK
    glyph_free = GLYPH_BRACKET if fallback_glyphs else GLYPH_CORNERS

    # 100 cells divided into 10 rows of 10 cells
    cells = snapshot.generate_matrix_cells()
    matrix_rows = [cells[i * 10 : (i + 1) * 10] for i in range(10)]

    # Prepare Right-Column lines (10 lines to match 10 rows of the matrix)
    right_lines = [""] * 10

    # Line 0: Model Metadata & Total Used Ratio
    used_ratio = format_ratio_tokens(snapshot.total_used_tokens, snapshot.max_tokens)
    used_pct = snapshot.used_percentage
    # Format: <model_id> · <used_tokens>/<max_tokens> tokens (<used_percentage>%)
    right_lines[0] = (
        f"{CLR_DIM}{snapshot.model} · {used_ratio} ({round(used_pct)}%){CLR_RESET}"
    )

    # Line 1: Blank separator
    right_lines[1] = ""

    # Lines 2..7: Legend Items
    cats = snapshot.get_categories()
    # Map categories to lines 2..7
    for idx, cat in enumerate(cats):
        line_idx = 2 + idx
        if line_idx < 10:
            color = CATEGORY_COLORS.get(cat.name.lower().replace(" ", "_"), CLR_GRAY)
            sym = glyph_free if cat.is_free_space else glyph_filled
            
            # Format token count
            if cat.is_free_space:
                tok_str = format_tokens(cat.tokens, include_unit=False)
                # Matches screenshot: `⛶ Free space: 140k (70.2%)`
                right_lines[line_idx] = (
                    f"{color}{sym}{CLR_RESET} "
                    f"{CLR_WHITE}{cat.name}:{CLR_RESET} "
                    f"{CLR_DIM}{tok_str} ({cat.percentage}%){CLR_RESET}"
                )
            else:
                tok_str = format_tokens(cat.tokens, include_unit=True)
                # Matches screenshot: `⛁ System prompt: 2.5k tokens (1.2%)`
                right_lines[line_idx] = (
                    f"{color}{sym}{CLR_RESET} "
                    f"{CLR_WHITE}{cat.name}:{CLR_RESET} "
                    f"{CLR_DIM}{tok_str} ({cat.percentage}%){CLR_RESET}"
                )

    # Assemble lines
    out = []
    out.append(f"> {CLR_BOLD}/context{CLR_RESET}")
    out.append(f"  {CLR_DIM}└{CLR_RESET}")
    out.append(f"    {CLR_BOLD}Context Usage{CLR_RESET}")

    for row_idx in range(10):
        # Render left 10 cells (each glyph followed by space)
        row_cells = matrix_rows[row_idx]
        grid_row_str = ""
        for cell in row_cells:
            color = CATEGORY_COLORS.get(cell, CLR_GRAY)
            sym = glyph_free if cell == "free_space" else glyph_filled
            grid_row_str += f"{color}{sym}{CLR_RESET} "

        right_col = right_lines[row_idx]
        if right_col:
            # 4 spaces indent, 20 chars grid, 3 spaces gap
            out.append(f"    {grid_row_str}  {right_col}")
        else:
            out.append(f"    {grid_row_str}")

    out.append("")  # Empty line between grid and breakdowns

    # 4. Itemized Tree Breakdowns
    # MCP tools breakdown
    if snapshot.mcp_tools:
        out.append(f"    {CLR_BOLD}MCP tools{CLR_RESET} {CLR_DIM}· /mcp{CLR_RESET}")
        for item in snapshot.mcp_tools:
            tok_fmt = format_tokens(item.tokens)
            extra = f" ({item.extra})" if item.extra else ""
            out.append(
                f"    {CLR_DIM}└{CLR_RESET} {CLR_WHITE}{item.name}{CLR_RESET}{extra}: {CLR_DIM}{tok_fmt}{CLR_RESET}"
            )
        out.append("")

    # Memory files breakdown
    if snapshot.memory_files:
        out.append(f"    {CLR_BOLD}Memory files{CLR_RESET} {CLR_DIM}· /memory{CLR_RESET}")
        for item in snapshot.memory_files:
            tok_fmt = format_tokens(item.tokens)
            extra = f" ({item.extra})" if item.extra else ""
            out.append(
                f"    {CLR_DIM}└{CLR_RESET} {CLR_WHITE}{item.name}{CLR_RESET}{extra}: {CLR_DIM}{tok_fmt}{CLR_RESET}"
            )
        out.append("")

    # SlashCommand tool breakdown
    out.append(
        f"    {CLR_BOLD}SlashCommand Tool{CLR_RESET} {CLR_DIM}· {snapshot.slash_commands_count} commands{CLR_RESET}"
    )
    cmd_tok_fmt = format_tokens(snapshot.slash_commands_tokens)
    out.append(f"    {CLR_DIM}└ Total: {cmd_tok_fmt}{CLR_RESET}")

    return "\n".join(out) + "\n"


def render_context(
    session: Any = None,
    client: Any = None,
    snapshot: ContextSnapshot | None = None,
    use_mock: bool = False,
    fallback_glyphs: bool = False,
) -> None:
    """Print the context window visualizer inline to stdout."""
    if use_mock or (snapshot is None and session is None and client is None):
        snap = ContextTracker.get_mock_snapshot()
    elif snapshot is not None:
        snap = snapshot
    else:
        snap = ContextTracker.gather_live(session=session, client=client)

    output = build_context_view(snap, fallback_glyphs=fallback_glyphs)
    sys.stdout.write(output)
    sys.stdout.flush()


def main():
    """CLI entrypoint supporting --mock and --fallback flags."""
    import argparse
    parser = argparse.ArgumentParser(description="Codex Context Visualizer")
    parser.add_argument("--mock", action="store_true", help="Run with synthetic Claude Code mock telemetry")
    parser.add_argument("--fallback", action="store_true", help="Use fallback ASCII / simple Unicode glyphs (⊝, [ ])")
    args = parser.parse_args()

    render_context(use_mock=args.mock, fallback_glyphs=args.fallback)


if __name__ == "__main__":
    main()
