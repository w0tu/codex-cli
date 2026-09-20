"""Configuration management, auth lifecycle, key rotation, and onboarding for Codex."""

import os
import json
import time
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path.home() / ".codex" / "config.json"
DEFAULT_MODEL = "gemini 2.5 flash"

DEFAULT_CONFIG: dict[str, Any] = {
    "api_key": "",
    "backup_keys": [],
    "model": DEFAULT_MODEL,
    "default_mode": "cloud",
    "theme": "monochrome",
    "permission_mode": "safe",
}


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load configuration from ~/.codex/config.json with safe defaults."""
    cfg_file = path or DEFAULT_CONFIG_PATH
    if not cfg_file.exists():
        return dict(DEFAULT_CONFIG)
    try:
        content = cfg_file.read_text(encoding="utf-8")
        data = json.loads(content)
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        if not isinstance(merged.get("backup_keys"), list):
            merged["backup_keys"] = []
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(data: dict[str, Any], path: Path | None = None) -> Path:
    """Save configuration atomically to disk."""
    cfg_file = path or DEFAULT_CONFIG_PATH
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return cfg_file


def get_api_key(path: Path | None = None) -> str:
    """Resolve active API key: env var > config file > raise RuntimeError."""
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    cfg = load_config(path)
    key = cfg.get("api_key", "").strip()
    if key:
        return key

    raise RuntimeError(
        "No API key found.\n"
        "Set GROQ_API_KEY environment variable or configure ~/.codex/config.json:\n"
        '  {"api_key": "gsk_..."}'
    )


def set_active_api_key(key: str, path: Path | None = None) -> Path:
    """Set the primary active API key directly, moving existing key to backups."""
    cfg_file = path or DEFAULT_CONFIG_PATH
    cfg = load_config(cfg_file)
    clean_key = key.strip()
    old_key = cfg.get("api_key", "").strip()

    if old_key and old_key != clean_key:
        backups = [k for k in cfg.get("backup_keys", []) if k != clean_key and k != old_key]
        backups.insert(0, old_key)
        cfg["backup_keys"] = backups

    cfg["api_key"] = clean_key
    os.environ["GROQ_API_KEY"] = clean_key
    return save_config(cfg, cfg_file)


save_api_key = set_active_api_key


def add_api_key(key: str, path: Path | None = None) -> Path:
    """Add a new API key. Sets active key if empty, or stores in backup_keys."""
    cfg_file = path or DEFAULT_CONFIG_PATH
    cfg = load_config(cfg_file)
    clean_key = key.strip()

    if not cfg.get("api_key"):
        cfg["api_key"] = clean_key
    elif cfg["api_key"] == clean_key:
        pass
    else:
        backups = [k for k in cfg.get("backup_keys", []) if k != clean_key]
        backups.append(clean_key)
        cfg["backup_keys"] = backups

    os.environ["GROQ_API_KEY"] = cfg["api_key"]
    return save_config(cfg, cfg_file)


def rotate_api_key(path: Path | None = None) -> str | None:
    """Rotate to the next available backup key on 429/401 rate limits or auth errors."""
    cfg_file = path or DEFAULT_CONFIG_PATH
    cfg = load_config(cfg_file)
    backups: list[str] = [k for k in cfg.get("backup_keys", []) if k.strip()]

    if not backups:
        return None

    old_key = cfg.get("api_key", "")
    new_key = backups.pop(0)
    if old_key:
        backups.append(old_key)

    cfg["api_key"] = new_key
    cfg["backup_keys"] = backups
    save_config(cfg, cfg_file)
    os.environ["GROQ_API_KEY"] = new_key
    return new_key


def verify_api_key(api_key: str) -> tuple[bool, str, float]:
    """Test API key reachability and latency via a lightweight probe ping."""
    from groq import Groq
    t0 = time.perf_counter()
    try:
        client = Groq(api_key=api_key.strip(), timeout=8.0)
        models = client.models.list()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return True, f"Verified ({len(models.data)} models available)", elapsed_ms
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        err_msg = str(e)
        if "401" in err_msg or "Invalid" in err_msg:
            return False, "Invalid API key (HTTP 401 Unauthorized)", elapsed_ms
        elif "429" in err_msg:
            return False, "Rate limit reached (HTTP 429)", elapsed_ms
        return False, f"Connection error: {err_msg[:60]}", elapsed_ms


def run_onboarding_wizard(path: Path | None = None) -> str:
    """Interactive first-run onboarding prompt for missing/invalid API keys."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from prompt_toolkit import prompt as pt_prompt

    con = Console()
    con.print()
    panel_text = Text()
    panel_text.append("Welcome to Codex\n", style="bold white")
    panel_text.append("Autonomous AI Terminal for Linux\n\n", style="dim")
    panel_text.append("To enable hardware-accelerated intelligence, provide your API key.\n", style="white")
    panel_text.append("Keys are encrypted and stored locally in ~/.codex/config.json.\n", style="dim")
    con.print(Panel(panel_text, border_style="grey35", expand=False))
    con.print()

    while True:
        try:
            user_key = pt_prompt("Enter your API key (gsk_...): ", is_password=True).strip()
        except (KeyboardInterrupt, EOFError):
            con.print("\n[dim]Setup canceled.[/]\n")
            raise SystemExit(1)

        if not user_key:
            con.print("[dim]Key cannot be empty. Please try again.[/]\n")
            continue

        con.print("[dim]Verifying API key reachability...[/]")
        valid, msg, latency = verify_api_key(user_key)
        if valid:
            con.print(f"[bold white]Key verified successfully[/] [dim]({latency:.1f}ms latency)[/]")
            add_api_key(user_key, path)
            con.print("[dim]Configuration saved. Launching Codex...[/]\n")
            return user_key
        else:
            con.print(f"[dim]Verification failed: {msg}[/]")
            con.print("[dim]Please check your key and try again.[/]\n")
