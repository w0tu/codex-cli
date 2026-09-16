"""PC agent tools for Codex — file operations, bash, grep, glob, git, and GitHub integration."""

import os
import subprocess
from pathlib import Path
from typing import Any

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
    }
]


def execute_bash(command: str) -> str:
    """Run bash command safely and return output."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=45,
            cwd=os.getcwd()
        )
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
        if len(result) > MAX_OUTPUT_CHARS:
            result = result[:MAX_OUTPUT_CHARS] + f"\n... [truncated, {len(result) - MAX_OUTPUT_CHARS} chars omitted]"
        return result
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 45 seconds."
    except Exception as e:
        return f"Error executing command: {e}"


def execute_read_file(path: str, offset: int = 1, limit: int = 100) -> str:
    """Read file with line numbering."""
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
        return f"{total_info}\n\n{body}"
    except Exception as e:
        return f"Error reading file: {e}"


def execute_write_file(path: str, content: str) -> str:
    """Write or overwrite file."""
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters ({len(content.encode('utf-8'))} bytes) to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def execute_edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace exact text block in file."""
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


def run_tool(name: str, args: dict[str, Any]) -> str:
    """Dispatch tool call by name."""
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
    else:
        return f"Error: Unknown tool '{name}'"
