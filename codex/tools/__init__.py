"""PC agent tools for Codex — file operations, bash, grep, glob, git, and GitHub integration."""

import os
import subprocess
from pathlib import Path
from typing import Any

from codex.ast_parser import SymbolExtractor
from codex.security import SecretScrubber
from codex.sandbox import SandboxExecutor

_sandbox = SandboxExecutor()

MAX_OUTPUT_CHARS = 4000

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Execute a shell / bash command on the user's Linux system. "
                "Use this to run terminal commands, compile code, run tests, install packages, check git, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute, e.g. 'pytest', 'git status', 'cat file'"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the filesystem with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative or absolute path to the file."
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting line number (1-based, optional, default 1)."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (optional, default 100)."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to create or overwrite."
                    },
                    "content": {
                        "type": "string",
                        "description": "The full text content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific snippet of text in a file with new text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit."
                    },
                    "old_str": {
                        "type": "string",
                        "description": "Exact existing text to be replaced."
                    },
                    "new_str": {
                        "type": "string",
                        "description": "New text that will replace old_str."
                    }
                },
                "required": ["path", "old_str", "new_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_outline",
            "description": "Extract structured symbols, classes, methods, and functions from a source code file using AST parsing without dumping the entire file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the source file to inspect."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_symbol",
            "description": "Extract the specific code definition of a function, method, or class by name from a file using AST parsing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the source file."
                    },
                    "symbol_name": {
                        "type": "string",
                        "description": "Exact name of the class, function, or method to retrieve."
                    }
                },
                "required": ["path", "symbol_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and subdirectories in a directory path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (default: current directory '.')."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Search for a regex or string pattern across files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query pattern or string."
                    },
                    "path": {
                        "type": "string",
                        "description": "Target folder or path (default: '.')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files matching a glob pattern (e.g. '*.py', '**/*.json').",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match."
                    },
                    "path": {
                        "type": "string",
                        "description": "Base directory to search in (default: '.')."
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Get current git repository branch, status, and modified files.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_skill",
            "description": "Install or update a developer skill from a GitHub repository (e.g. 'owner/repo' or full URL).",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "GitHub repository shorthand (owner/repo) or clone URL."
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List all active installed developer skills.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Search past messages, earlier topics, and decisions discussed in this session (even 100+ turns ago).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword or concept to search for in past session history."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_connect",
            "description": "Connect to a GitHub repository by URL or owner/repo (e.g. 'torvalds/linux'). Clones if not present.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "GitHub repository URL or 'owner/repo' shorthand."
                    },
                    "dest_dir": {
                        "type": "string",
                        "description": "Optional destination directory (defaults to repo name)."
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the live web using free online APIs (Wikipedia, DuckDuckGo) for real-time information, documentation, news, facts, and code references.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g. 'Python 3.14 features', 'Rust tokio tutorial', 'FastAPI background tasks'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch and extract readable plain-text or documentation content from any public web URL (strips scripts and HTML tags).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full HTTP or HTTPS URL to fetch."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "online_info",
            "description": "Retrieve comprehensive encyclopedic reference knowledge for any concept, tech stack, library, or entity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Name of the topic or concept to look up, e.g. 'Kubernetes', 'B-tree', 'Git'"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_search",
            "description": "Search public GitHub repositories for open source projects, stars, descriptions, and URLs without requiring API tokens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term for GitHub repositories."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "agent_reach",
            "description": (
                "Agent Reach router for multi-platform internet retrieval. "
                "Search and read from 16+ internet platforms without official API keys: "
                "Web search (Exa), general URLs (Jina Reader), GitHub, Bilibili, YouTube transcripts, "
                "Reddit, V2EX, Twitter/X, and social discussions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "read", "doctor", "bilibili", "github", "v2ex", "youtube"],
                        "description": "The action or platform to target. Default 'search' for queries, 'read' for URLs."
                    },
                    "query": {
                        "type": "string",
                        "description": "The search query or keyword."
                    },
                    "url": {
                        "type": "string",
                        "description": "Web URL to read, parse, or transcribe (optional)."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_mouse",
            "description": (
                "Automate the user's PC desktop mouse and keyboard via native Linux xdotool. "
                "Move mouse cursor, click buttons, drag, scroll, inspect cursor coordinates, get screen size, type text, or press keys."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["move", "click", "double_click", "drag", "scroll", "position", "screen_size", "type", "key"],
                        "description": "Mouse/desktop action to perform."
                    },
                    "x": {"type": "integer", "description": "X coordinate on screen."},
                    "y": {"type": "integer", "description": "Y coordinate on screen."},
                    "button": {"type": "integer", "description": "Mouse button: 1=Left, 2=Middle, 3=Right (default: 1)."},
                    "direction": {"type": "string", "enum": ["up", "down"], "description": "Scroll direction (up or down)."},
                    "amount": {"type": "integer", "description": "Scroll amount (default: 3)."},
                    "text": {"type": "string", "description": "Text to type into active window."},
                    "key": {"type": "string", "description": "Key or hotkey combination to press, e.g. 'Return', 'ctrl+c'."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wifi_status",
            "description": "Inspect local PC WiFi status, active SSID, signal strength, local IP address, and internet gateway connectivity.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "deep_research",
            "description": "Conduct deep internet research across multiple platforms (Exa, web, news, docs) for any complex query when asked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The research question or topic to investigate."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_antigravity",
            "description": "Delegate complex reasoning, architectural refactoring, and multi-file workflows to Google Antigravity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The complex task prompt or problem description."
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "minimize_window",
            "description": "Minimize currently active focused terminal window to reveal the PC desktop.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_browser",
            "description": "Launch web browser to any target URL (e.g. https://console.groq.com/keys) and bring it into focus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The web URL to open."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_screen",
            "description": "Capture live real-time screenshot of Linux desktop using ffmpeg x11grab and inspect display state.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_second_mouse",
            "description": "Spawn a floating, animated second agent mouse cursor overlay on screen that smoothly glides to (x, y) with an action badge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_x": {"type": "integer", "description": "Target X screen coordinate."},
                    "target_y": {"type": "integer", "description": "Target Y screen coordinate."},
                    "badge": {"type": "string", "description": "Action text badge to display next to the cursor, e.g. '✦ AGENT: Opening Groq Console'."},
                    "click": {"type": "boolean", "description": "Whether to perform a visual click ripple at target."}
                },
                "required": ["target_x", "target_y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_documents",
            "description": "Directly write and save any text, API keys, report, or code file into the user's PC ~/Documents folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename to save into ~/Documents (e.g. 'groq_api_keys.txt')."},
                    "content": {"type": "string", "description": "The text or file contents to save."}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_web_chat",
            "description": "Open and automate web messaging apps like WhatsApp Web, Google Chat, Discord, or Telegram.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": ["whatsapp", "google_chat", "discord", "telegram"], "description": "Messaging platform to open."},
                    "recipient": {"type": "string", "description": "Recipient phone number or contact identifier."},
                    "message": {"type": "string", "description": "Message text to stage or send."}
                },
                "required": ["platform"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "automate_groq_keys",
            "description": "Fully automated workflow: minimize window, pop up moving agent mouse, launch Chrome to Groq console, extract keys, and save to ~/Documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Document filename to save keys into (default: 'groq_api_keys.txt')."}
                },
                "required": []
            }
        }
    }
]



def execute_bash(command: str) -> str:
    """Run bash command safely inside sandbox, intercept dangerous operations, and scrub secrets."""
    try:
        proc = _sandbox.execute(command, timeout=45)
        out = proc.stdout
        err = proc.stderr
        combined = []
        if out:
            combined.append(out)
        if err:
            combined.append(f"[stderr]\n{err}")
        result = "".join(combined).strip()
        if not result:
            result = f"(Command completed with exit code {proc.returncode}, no output)"
        # Scrub credentials before exposing output
        result = SecretScrubber.scrub_text(result)
        if len(result) > MAX_OUTPUT_CHARS:
            result = result[:MAX_OUTPUT_CHARS] + f"\n... [truncated, {len(result) - MAX_OUTPUT_CHARS} chars omitted]"
        return result
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 45 seconds."
    except Exception as e:
        return f"Error executing command: {e}"


def execute_read_file(path: str, offset: int = 1, limit: int = 100) -> str:
    """Read file with line numbering and scrub secrets."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"Error: File not found: {path}"
    if not p.is_file():
        return f"Error: Path is a directory, not a file: {path}"
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        offset = max(1, offset)
        start_idx = offset - 1
        end_idx = min(len(lines), start_idx + limit)
        selected = lines[start_idx:end_idx]
        output = []
        for i, line in enumerate(selected, start=offset):
            output.append(f"{i:4d} | {line}")
        total_info = f"Viewing lines {offset}-{end_idx} of {len(lines)} in {path}"
        body = "\n".join(output)
        return SecretScrubber.scrub_text(f"{total_info}\n\n{body}")
    except Exception as e:
        return f"Error reading file: {e}"


def execute_code_outline(path: str) -> str:
    """Extract structured symbol outline from file using AST."""
    return SymbolExtractor.outline_file(path)


def execute_get_symbol(path: str, symbol_name: str) -> str:
    """Extract specific function or class definition from file using AST."""
    return SymbolExtractor.extract_symbol(path, symbol_name)


def execute_write_file(path: str, content: str) -> str:
    """Write or overwrite file with boundary safety enforcement."""
    if not _sandbox.is_within_boundary(path):
        return f"Security Error: Cannot write to '{path}' outside workspace boundary."
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters ({len(content.encode('utf-8'))} bytes) to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def execute_edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace exact text block in file with boundary safety enforcement."""
    if not _sandbox.is_within_boundary(path):
        return f"Security Error: Cannot edit '{path}' outside workspace boundary."
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: File not found: {path}"
        text = p.read_text(encoding="utf-8")
        if old_str not in text:
            return f"Error: Target text not found in {path}. Make sure whitespace matches."
        occurrences = text.count(old_str)
        new_text = text.replace(old_str, new_str, 1)
        p.write_text(new_text, encoding="utf-8")
        return f"Successfully replaced 1 occurrence (found {occurrences} total) in {path}"
    except Exception as e:
        return f"Error editing file: {e}"


def execute_list_dir(path: str = ".") -> str:
    """List directory contents."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: Directory not found: {path}"
        if not p.is_dir():
            return f"Error: Path is not a directory: {path}"
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = [f"Directory contents for {p}:"]
        for item in items[:100]:
            if item.is_dir():
                lines.append(f"  [DIR]  {item.name}/")
            else:
                try:
                    sz = item.stat().st_size
                    lines.append(f"  [FILE] {item.name} ({sz:,} bytes)")
                except Exception:
                    lines.append(f"  [FILE] {item.name}")
        if len(items) > 100:
            lines.append(f"  ... and {len(items) - 100} more items")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing directory: {e}"


def execute_grep_search(query: str, path: str = ".") -> str:
    """Grep for pattern across files."""
    try:
        cmd = f"grep -rnI --exclude-dir='.git' --exclude-dir='.venv' --exclude-dir='node_modules' '{query}' {path} 2>/dev/null | head -n 30"
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
        res = proc.stdout.strip()
        if not res:
            return f"No matches found for '{query}' in {path}."
        return res
    except Exception as e:
        return f"Error running grep: {e}"


def execute_find_files(pattern: str, path: str = ".") -> str:
    """Find files matching glob pattern."""
    try:
        p = Path(path).expanduser().resolve()
        matches = list(p.glob(pattern))[:50]
        if not matches:
            return f"No files matching '{pattern}' in {path}."
        lines = [f"Found {len(matches)} matches for '{pattern}':"]
        for m in matches:
            lines.append(f"  {m.relative_to(p)}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching files: {e}"


def execute_git_status() -> str:
    """Run git status and branch summary."""
    try:
        proc = subprocess.run("git status -s && git branch --show-current", shell=True, capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            return "Not a git repository (or git is not installed)."
        res = proc.stdout.strip()
        return res if res else "Working tree clean, on active branch."
    except Exception as e:
        return f"Error checking git: {e}"


def execute_github_connect(repo: str, dest_dir: str = "") -> str:
    """Connect or clone a GitHub repo."""
    repo = repo.strip()
    if not repo.startswith("http") and not repo.startswith("git@"):
        # Convert owner/repo to https URL
        url = f"https://github.com/{repo}.git"
    else:
        url = repo

    target = dest_dir.strip() if dest_dir.strip() else repo.split("/")[-1].replace(".git", "")
    target_path = Path(target).expanduser().resolve()

    if target_path.exists() and (target_path / ".git").exists():
        # Already exists, fetch and check remotes
        proc = subprocess.run(f"cd {target_path} && git remote -v && git status -s", shell=True, capture_output=True, text=True, timeout=15)
        return f"Repository already connected at {target_path}:\n{proc.stdout}"

    # Clone
    proc = subprocess.run(f"git clone {url} {target_path}", shell=True, capture_output=True, text=True, timeout=60)
    if proc.returncode == 0:
        return f"Successfully cloned and connected GitHub repository '{repo}' to {target_path}."
    else:
        return f"Failed to connect GitHub repository:\n{proc.stderr}"


def execute_recall_memory(query: str) -> str:
    """Search earlier conversation memory."""
    from codex.memory import SESSIONS_DIR
    files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not files:
        return f"No session archives found on disk."
    latest = files[0]
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        history = data.get("history", [])
        q = query.lower().strip()
        matches = []
        for i, m in enumerate(history):
            content = str(m.get("content", ""))
            if q in content.lower():
                matches.append(f"[Turn {i+1} - {m.get('role', '').upper()}]: {content[:200]}")
                if len(matches) >= 5:
                    break
        if not matches:
            return f"No mentions of '{query}' found in session memory ({len(history)} turns searched)."
        return f"Found {len(matches)} mentions of '{query}' in session history:\n" + "\n\n".join(matches)
    except Exception as e:
        return f"Error querying session memory: {e}"


def execute_install_skill(repo: str) -> str:
    """Install skill from GitHub."""
    from codex.skills import SkillsManager
    return SkillsManager().install_from_github(repo)


def execute_list_skills() -> str:
    """List all installed skills."""
    from codex.skills import SkillsManager
    skills = SkillsManager().list_skills()
    if not skills:
        return "No skills currently installed."
    lines = ["Installed Developer Skills:"]
    for s in skills:
        lines.append(f"- {s['name']} ({s['source']}): {s['description']}")
    return "\n".join(lines)


def execute_web_search(query: str) -> str:
    """Free web search combining Wikipedia and DuckDuckGo Instant APIs."""
    import urllib.request
    import urllib.parse
    import json
    import html
    import re

    query_clean = query.strip()
    results = []

    # 1. DuckDuckGo Instant Answer API
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query_clean)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(ddg_url, headers={"User-Agent": "CodexCLI/1.7.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            abstract = data.get("AbstractText", "").strip()
            source_url = data.get("AbstractURL", "")
            if abstract:
                results.append(f"### DuckDuckGo Summary ({source_url}):\n{abstract}\n")
            topics = data.get("RelatedTopics", [])
            for t in topics[:3]:
                if isinstance(t, dict) and "Text" in t:
                    results.append(f"- {t['Text']}")
    except Exception:
        pass

    # 2. Wikipedia Search API
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query_clean)}&format=json&srlimit=4"
        req = urllib.request.Request(wiki_url, headers={"User-Agent": "CodexCLI/1.7.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            search_items = data.get("query", {}).get("search", [])
            if search_items:
                results.append("### Relevant Wikipedia Articles:")
                for item in search_items:
                    title = item.get("title", "")
                    snippet = html.unescape(re.sub(r"<[^>]+>", "", item.get("snippet", "")))
                    page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                    results.append(f"- **[{title}]({page_url})**: {snippet}")
    except Exception:
        pass

    if not results:
        return f"No online search results found for: '{query}'."
    return "\n".join(results)


def execute_fetch_url(url: str, max_chars: int = 4000) -> str:
    """Fetch URL and extract clean text without HTML boilerplate."""
    import urllib.request
    import re
    import html

    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # Strip scripts, styles, comments
        text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.IGNORECASE)
        title = html.unescape(title_match.group(1)).strip() if title_match else url
        # Replace tags with spaces or newlines
        text = re.sub(r"<(p|br|div|li|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        # Collapse whitespace
        text = re.sub(r"[ \t]+", " ", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + f"\n... [truncated, {len(cleaned)} chars total]"

        return f"### {title}\nURL: {url}\n\n{cleaned}"
    except Exception as e:
        return f"Error fetching URL '{url}': {e}"


def execute_online_info(topic: str) -> str:
    """Fetch encyclopedic summary for a topic from Wikipedia REST API."""
    import urllib.request
    import urllib.parse
    import json

    topic_clean = topic.strip().replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(topic_clean)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CodexCLI/1.7.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            extract = data.get("extract", "").strip()
            title = data.get("title", topic)
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            if extract:
                return f"### {title}\nSource: {page_url}\n\n{extract}"
    except Exception:
        pass
    return execute_web_search(topic)


def execute_github_search(query: str) -> str:
    """Search public GitHub repositories for projects and stars."""
    import urllib.request
    import urllib.parse
    import json

    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&per_page=5"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CodexCLI/1.7.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            items = data.get("items", [])
            if not items:
                return f"No GitHub repositories found for query: '{query}'."

            lines = [f"### Top GitHub Repositories for '{query}':"]
            for repo in items:
                name = repo.get("full_name", "")
                desc = repo.get("description", "No description") or "No description"
                stars = repo.get("stargazers_count", 0)
                forks = repo.get("forks_count", 0)
                html_url = repo.get("html_url", "")
                lines.append(f"- **[{name}]({html_url})** (★ {stars:,} | ⑂ {forks:,})\n  {desc}")

            return "\n".join(lines)
    except Exception as e:
        return f"Error searching GitHub: {e}"


def execute_agent_reach(action: str = "search", query: str = "", url: str = "") -> str:
    """Execute multi-platform internet retrieval via Agent Reach router."""
    env = os.environ.copy()
    npm_bin = f"{Path.home()}/.npm-global/bin"
    local_bin = f"{Path.home()}/.local/bin"
    env["PATH"] = f"{npm_bin}:{local_bin}:" + env.get("PATH", "")

    action = (action or "search").lower().strip()
    query = (query or "").strip()
    url = (url or "").strip()

    if action == "doctor":
        proc = subprocess.run("agent-reach doctor", shell=True, env=env, capture_output=True, text=True, timeout=30)
        return (proc.stdout or proc.stderr)[:MAX_OUTPUT_CHARS]

    if action in ("read", "url") or url:
        target = url or query
        if not target.startswith("http"):
            target = "https://" + target
        cmd = f'curl -s -L --max-time 20 "https://r.jina.ai/{target}"'
        proc = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True, timeout=25)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout[:MAX_OUTPUT_CHARS]
        return f"Failed to retrieve content from {target} via Jina Reader."

    if action == "v2ex":
        cmd = 'curl -s -L --max-time 15 "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"'
        proc = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True, timeout=20)
        return (proc.stdout or proc.stderr)[:MAX_OUTPUT_CHARS]

    if action in ("bilibili", "bili"):
        cmd = f'bili search "{query}" --type video -n 5'
        proc = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True, timeout=25)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout[:MAX_OUTPUT_CHARS]
        return f"bili search output: {(proc.stdout or proc.stderr)[:MAX_OUTPUT_CHARS]}"

    if action in ("github", "gh"):
        cmd = f'gh search repos "{query}" --sort stars --limit 5'
        proc = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True, timeout=20)
        return (proc.stdout or proc.stderr)[:MAX_OUTPUT_CHARS]

    if action in ("youtube", "yt"):
        target = url or query
        cmd = f'yt-dlp --dump-json "{target}"'
        proc = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True, timeout=25)
        return (proc.stdout or proc.stderr)[:MAX_OUTPUT_CHARS]

    # General Search: Try mcporter Exa, fallback to execute_web_search
    if action == "search" or query:
        cmd = f'mcporter call exa.web_search_exa query="{query}" numResults=5'
        proc = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True, timeout=25)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout[:MAX_OUTPUT_CHARS]
        return execute_web_search(query)

    return f"Unsupported agent-reach action '{action}'"


def run_tool(name: str, args: dict[str, Any]) -> str:
    """Dispatch tool call by name, enforcing Directory Gatekeeper permissions."""
    from codex.gatekeeper import gatekeeper

    if gatekeeper.read_only_mode and name in ("bash", "write_file", "edit_file", "install_skill"):
        return "Security Error: Workspace is in safe read-only advisory mode. File modifications and terminal tool execution are disabled."

    if name == "bash":
        return execute_bash(args.get("command", ""))
    elif name == "read_file":
        return execute_read_file(
            args.get("path", ""),
            offset=args.get("offset", 1),
            limit=args.get("limit", 100)
        )
    elif name == "write_file":
        return execute_write_file(args.get("path", ""), args.get("content", ""))
    elif name == "edit_file":
        return execute_edit_file(
            args.get("path", ""),
            args.get("old_str", ""),
            args.get("new_str", "")
        )
    elif name == "code_outline":
        return execute_code_outline(args.get("path", ""))
    elif name == "get_symbol":
        return execute_get_symbol(args.get("path", ""), args.get("symbol_name", ""))
    elif name == "list_dir":
        return execute_list_dir(args.get("path", "."))
    elif name == "grep_search":
        return execute_grep_search(args.get("query", ""), args.get("path", "."))
    elif name == "find_files":
        return execute_find_files(args.get("pattern", "*"), args.get("path", "."))
    elif name == "git_status":
        return execute_git_status()
    elif name == "github_connect":
        return execute_github_connect(args.get("repo", ""), args.get("dest_dir", ""))
    elif name == "recall_memory":
        return execute_recall_memory(args.get("query", ""))
    elif name == "install_skill":
        return execute_install_skill(args.get("repo", ""))
    elif name == "list_skills":
        return execute_list_skills()
    elif name == "web_search":
        return execute_web_search(args.get("query", ""))
    elif name == "fetch_url":
        return execute_fetch_url(args.get("url", ""))
    elif name == "online_info":
        return execute_online_info(args.get("topic", ""))
    elif name == "github_search":
        return execute_github_search(args.get("query", ""))
    elif name == "agent_reach":
        return execute_agent_reach(
            action=args.get("action", "search"),
            query=args.get("query", ""),
            url=args.get("url", "")
        )
    elif name == "control_mouse":
        return execute_control_mouse(args)
    elif name == "wifi_status":
        return execute_wifi_status()
    elif name == "deep_research":
        return execute_deep_research(args.get("query", ""))
    elif name == "delegate_antigravity":
        return execute_delegate_antigravity(args.get("task", ""))
    elif name == "minimize_window":
        from codex.screen_agent import window_manager
        res = window_manager.minimize_active_window()
        return res.get("message", "Window minimized")
    elif name == "open_browser":
        from codex.screen_agent import window_manager
        res = window_manager.open_browser(args.get("url", "https://console.groq.com/keys"))
        return res.get("message", "Browser opened")
    elif name == "capture_screen":
        from codex.screen_agent import window_manager
        res = window_manager.capture_screen_frame()
        if res.get("success"):
            return f"Screen frame captured ({res.get('geometry')}, {res.get('size')} bytes) saved to: {res.get('path')}"
        return f"Failed to capture screen: {res.get('message')}"
    elif name == "move_second_mouse":
        from codex.screen_agent import agent_pointer
        tx = int(args.get("target_x", 800))
        ty = int(args.get("target_y", 500))
        badge = args.get("badge", "✦ AGENT MOUSE")
        click = bool(args.get("click", False))
        ok = agent_pointer.glide_to(target_x=tx, target_y=ty, badge=badge, click=click)
        return f"Second agent mouse cursor glided to ({tx}, {ty}) [badge: {badge}]" if ok else "Failed to glide agent mouse"
    elif name == "save_to_documents":
        from codex.screen_agent import window_manager
        res = window_manager.save_to_documents(args.get("filename", "output.txt"), args.get("content", ""))
        return res.get("message", "Saved to Documents")
    elif name == "manage_web_chat":
        from codex.screen_agent import window_manager
        res = window_manager.open_web_messaging(
            platform=args.get("platform", "whatsapp"),
            recipient=args.get("recipient", ""),
            message=args.get("message", "")
        )
        return res.get("message", "Web chat opened")
    elif name == "automate_groq_keys":
        from codex.screen_agent import window_manager
        res = window_manager.run_groq_keys_automation(filename=args.get("filename", "groq_api_keys.txt"))
        return (
            f"Groq Keys Automation Completed:\n"
            f"- Status: Success\n"
            f"- Primary Key: {res.get('primary_key')}\n"
            f"- Total Keys: {res.get('keys_found')}\n"
            f"- Persisted To: {res.get('documents_file')}\n"
            f"- Screen Frame: {res.get('screen_frame')}"
        )
    else:
        return f"Error: Unknown tool '{name}'"


def execute_control_mouse(args: dict[str, Any]) -> str:
    """Execute desktop mouse automation."""
    from codex.mouse_control import mouse_controller
    action = args.get("action", "position").lower()
    x = args.get("x")
    y = args.get("y")
    button = args.get("button", 1)
    text = args.get("text", "")
    key = args.get("key", "")
    direction = args.get("direction", "down")
    amount = args.get("amount", 3)

    if action == "move":
        if x is None or y is None:
            return "Error: 'move' action requires 'x' and 'y' integer coordinates."
        res = mouse_controller.move_to(int(x), int(y))
        return res.get("message", "Mouse moved")
    elif action == "click":
        res = mouse_controller.click(button=int(button), x=int(x) if x is not None else None, y=int(y) if y is not None else None)
        return res.get("message", "Clicked")
    elif action == "double_click":
        res = mouse_controller.double_click(x=int(x) if x is not None else None, y=int(y) if y is not None else None)
        return res.get("message", "Double-clicked")
    elif action == "drag":
        curr = mouse_controller.get_position()
        start_x = curr.get("x", 0)
        start_y = curr.get("y", 0)
        if x is None or y is None:
            return "Error: 'drag' requires target 'x' and 'y' coordinates."
        res = mouse_controller.drag(start_x, start_y, int(x), int(y), button=int(button))
        return res.get("message", "Dragged")
    elif action == "scroll":
        res = mouse_controller.scroll(direction=direction, amount=int(amount))
        return res.get("message", "Scrolled")
    elif action == "position":
        pos = mouse_controller.get_position()
        return f"Mouse cursor at x={pos.get('x')}, y={pos.get('y')} (screen: {pos.get('screen')})"
    elif action == "screen_size":
        sz = mouse_controller.get_screen_size()
        return f"Screen resolution: {sz.get('width')}x{sz.get('height')}"
    elif action == "type":
        if not text:
            return "Error: 'type' action requires 'text' parameter."
        res = mouse_controller.type_text(text)
        return res.get("message", "Typed text")
    elif action == "key":
        if not key:
            return "Error: 'key' action requires 'key' combination parameter."
        res = mouse_controller.press_key(key)
        return res.get("message", "Pressed key")
    return f"Unsupported mouse action '{action}'"


def execute_wifi_status() -> str:
    """Inspect and format WiFi connectivity status."""
    from codex.network import check_wifi_status
    st = check_wifi_status()
    conn_str = "CONNECTED" if st.get("connected") else "DISCONNECTED"
    inet_str = "ONLINE (Internet OK)" if st.get("internet") else "OFFLINE"
    return (
        f"WiFi Status: {conn_str}\n"
        f"- SSID: {st.get('ssid')}\n"
        f"- Interface: {st.get('interface')}\n"
        f"- Signal Strength: {st.get('signal')}%\n"
        f"- Local IP: {st.get('ip')}\n"
        f"- Gateway Connectivity: {inet_str}"
    )


def execute_deep_research(query: str) -> str:
    """Execute multi-engine internet research."""
    from codex.network import run_deep_research
    return run_deep_research(query)


def execute_delegate_antigravity(task: str) -> str:
    """Delegate complex task to Google Antigravity."""
    from codex.antigravity_bridge import delegate_to_antigravity
    return delegate_to_antigravity(task)

