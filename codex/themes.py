"""Terminal color themes and styling palettes for Codex CLI."""

from typing import Any, Dict

THEMES: Dict[str, Dict[str, str]] = {
    "monochrome": {
        "name": "Monochrome",
        "description": "High-contrast minimalist black & white aesthetic (Default)",
        "prompt_app": "\x1b[1;37m",       # Bold White
        "prompt_in": "\x1b[2m",           # Dim
        "prompt_dir": "\x1b[37m",         # White
        "prompt_branch": "\x1b[36m",      # Cyan
        "prompt_char": "\x1b[1;37m",      # Bold White
        "primary": "bold white",
        "secondary": "white",
        "dim": "dim",
        "border": "grey35",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
    },
    "nord": {
        "name": "Nord",
        "description": "Arctic, north-bluish palette with clean contrast",
        "prompt_app": "\x1b[1;38;5;110m", # Frost Blue
        "prompt_in": "\x1b[38;5;103m",    # Dim Slate
        "prompt_dir": "\x1b[38;5;152m",   # Light Ice
        "prompt_branch": "\x1b[38;5;149m",# Polar Green
        "prompt_char": "\x1b[1;38;5;110m",
        "primary": "bold #88c0d0",
        "secondary": "#e5e9f0",
        "dim": "#4c566a",
        "border": "#434c5e",
        "success": "bold #a3be8c",
        "error": "bold #bf616a",
        "warning": "bold #ebcb8b",
    },
    "dracula": {
        "name": "Dracula",
        "description": "Vibrant dark theme with purples and pinks",
        "prompt_app": "\x1b[1;38;5;212m", # Hot Pink
        "prompt_in": "\x1b[38;5;141m",    # Purple
        "prompt_dir": "\x1b[38;5;84m",    # Neon Green
        "prompt_branch": "\x1b[38;5;117m",# Cyan
        "prompt_char": "\x1b[1;38;5;212m",
        "primary": "bold #ff79c6",
        "secondary": "#f8f8f2",
        "dim": "#6272a4",
        "border": "#bd93f9",
        "success": "bold #50fa7b",
        "error": "bold #ff5555",
        "warning": "bold #f1fa8c",
    },
    "matrix": {
        "name": "Matrix",
        "description": "Classic hacker phosphorescent terminal green",
        "prompt_app": "\x1b[1;32m",       # Bright Green
        "prompt_in": "\x1b[2;32m",        # Dim Green
        "prompt_dir": "\x1b[32m",         # Green
        "prompt_branch": "\x1b[1;33m",    # Amber
        "prompt_char": "\x1b[1;32m",
        "primary": "bold green",
        "secondary": "green",
        "dim": "dim green",
        "border": "green",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
    }
}

ACTIVE_THEME = "monochrome"


def get_theme(theme_name: str | None = None) -> Dict[str, str]:
    """Retrieve color palette for given theme or active default."""
    name = (theme_name or ACTIVE_THEME).lower().strip()
    return THEMES.get(name, THEMES["monochrome"])


def set_active_theme(theme_name: str) -> bool:
    """Set the globally active CLI theme."""
    global ACTIVE_THEME
    clean = theme_name.lower().strip()
    if clean in THEMES:
        ACTIVE_THEME = clean
        return True
    return False


def list_themes() -> list[dict[str, Any]]:
    """Return all available themes with active flag."""
    return [
        {
            "id": tid,
            "name": t["name"],
            "description": t["description"],
            "active": tid == ACTIVE_THEME,
        }
        for tid, t in THEMES.items()
    ]
