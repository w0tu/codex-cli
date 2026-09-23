<p align="center">
  <img src="assets/logo.png" width="220" alt="Codex Logo" />
</p>

<h1 align="center">The Codex Project</h1>

<p align="center">
  <strong>Autonomous AI Coding Assistant & Terminal Agent for Linux</strong><br />
  <em>Hardware-accelerated by Groq LPUs · Real-time Tool Execution · Claude Code Aesthetic</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.5.0-black?style=flat-square" alt="Version" />
  <img src="https://img.shields.io/badge/inference-Groq_LPU-white?style=flat-square&logo=linux&logoColor=black" alt="Inference" />
  <img src="https://img.shields.io/badge/python-3.9+-black?style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-white?style=flat-square" alt="License" />
</p>

---

## Overview

**Codex** (`cdx`) is a terminal-native and desktop AI coding agent designed for Linux developers, created by **Saad Kashif**. Inspired by the ergonomics of Claude Code, Antigravity, and OpenAI Codex, it pairs ultra-fast Groq LPU cloud inference with autonomous local operating system execution.

### Quick Install (`sudo apt install`)
Install natively on Debian / Ubuntu systems with a single command:
```bash
# Direct Debian package install
sudo apt install ./dist/cdx_1.7.0_all.deb

# Or launch immediately
cdx        # Terminal CLI
cdx-app    # Desktop GUI App with Agents Hub
```

### Models Lineup (`cdx 2.7` to `cdx 3.6`)
- **`cdx 2.7 Instant`**: Ultra-fast local edge inference for rapid syntax and local bash workflows.
- **`cdx 3.0 Turbo`**: Rapid triage, testing harnesses, and fast scripting.
- **`cdx 3.2 LPU Ultra`**: 500+ tok/s hardware-accelerated full-stack web and code builder.
- **`cdx 3.5 Pro`**: Enterprise systems architect for distributed design and large-scale refactors.
- **`cdx 3.6 Max`**: Deep mathematical reasoning and formal verification engine.

### Autonomous Specialists (Agents Hub)
1. **CDX-Marketing**: Viral product launch copy, 30s commercial scripts, campaign strategy.
2. **CDX-Frontend**: Tailwind CSS, Vue/React, micro-interactions, responsive design.
3. **CDX-Legal**: Open-source license audits (MIT/Apache/GPL), Terms of Service, Privacy Policies.
4. **CDX-Automator**: Native Linux mouse/keyboard macro automation and daemon workflows.
5. **CDX-Architect**: Distributed architecture, API schemas, and systems design.
6. **CDX-FullStack**: Complete end-to-end web apps, backend APIs, and database migrations.
7. **CDX-Auditor**: Security audits, secret detection, vulnerability remediation.
8. **CDX-Research**: Multi-source live internet research and GitHub intelligence synthesis.

👉 **Special Feature**: See [`BRAG_AD_AND_IMPROVEMENTS.md`](BRAG_AD_AND_IMPROVEMENTS.md) for our 30-second commercial script and technical improvements for [`latent-spaces/brag`](https://github.com/latent-spaces/brag).

---

## Key Features

- **Ultra-Fast Groq LPU Inference**: Streams tokens at 150–300+ tok/s using the official `groq` SDK.
- **Autonomous Agentic Tools**:
  - `bash`: Executes shell commands directly on your PC with timeout protection and output capture.
  - `read_file`: Line-numbered source code inspection with configurable windowing.
  - `write_file`: Atomic file creation and overwriting with automatic directory creation.
  - `edit_file`: Precise find-and-replace text modifications.
  - `list_dir`: Directory tree explorer with file size metadata.
  - `grep_search`: Fast regex / string search across project repositories.
  - `find_files`: Glob-based file finder (e.g. `*.py`, `**/*.json`).
  - `git_status`: Working tree and branch inspector.
  - `github_connect`: Clones or connects remote GitHub repositories autonomously.
- **Dynamic Claude-Style Thinking Engine**:
  - Cognitive reasoning animation with animated geometric glyphs (`[◇]` $\to$ `[◈]` $\to$ `[◆]`).
  - Scales thinking duration dynamically based on prompt complexity and technical depth (1.0s – 4.8s).
  - Claude 3.7-style settled thought marker (`Thought for 2.4s`).
- **Claude Code & Antigravity Slash Commands**:
  - `/compact`: Compacts conversation history to preserve context tokens.
  - `/doctor`: Complete environment health check (Python, kernel, Git, terminal, model).
  - `/cost`: Real-time session token usage and pricing calculation.
  - `/diff`: Syntax-highlighted git diff view directly in the terminal.
  - `/export`: Exports the active conversation session to a standalone markdown document.
  - `/init`: Generates a `CODEX.md` project memory file that Codex automatically adheres to.
  - `/git`: Direct git status and diff integration.
  - `/github [repo]`: Connects or clones remote repositories.
  - `/tools`: Interactive list of available agent capabilities.
  - `/model`: Live model switching (`qwen/qwen3.8-27b`, `openai/gpt-oss-20b`).
  - `/clear`, `/reset`, `/help`, `/exit`.
- **Pure Monochrome & Zero Emojis**:
  - Clean, high-contrast black & white terminal UI.
  - Strict 0-emoji rule enforced across all code, prompts, and interface elements.
- **Linux Desktop Application**:
  - Registered `.desktop` entry in your application launcher / start menu.
  - Desktop shortcut on `~/Desktop/Codex.desktop`.
  - Dedicated windowed launcher `codex-app`.

---

## Installation

### Prerequisites
- Linux OS (Debian, Ubuntu, Kali, Arch, Fedora)
- Python 3.9+
- A Groq API key (get one free at [console.groq.com](https://console.groq.com))

### Quick Install

```bash
# Clone the repository
git clone https://github.com/tqus/codex-cli.git
cd codex-cli

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Configure your Groq API key
export GROQ_API_KEY="gsk_..."
# Or store permanently:
mkdir -p ~/.codex && echo '{"api_key": "gsk_..."}' > ~/.codex/config.json

# Link to local path (if not already in PATH)
ln -sf $(pwd)/.venv/bin/cdx ~/.local/bin/cdx
```

---

## Usage

### Direct CLI Mode
Execute single prompts or commands directly:

```bash
cdx "Inspect my git status and summarize uncommitted changes."
cdx "Find all occurrences of 'TODO' across Python files and list them."
cdx "Write a memoized fibonacci function in /tmp/fib.py and run it with python3."
```

### Interactive REPL Mode
Start an interactive pair-programming session:

```bash
cdx
```

```
╭─────────────────────────────────────────╮
│  █████████   CODEX v1.5.0               │
│ ██ █████ ██  model:    qwen/qwen3.8-27b │
│ ███████████  dir:      /home/feds       │
│  █████████   commands: / for menu       │
│  █ █   █ █   abort:    ^C               │
╰─────────────────────────────────────────╯

╭─ codex in my-project
╰─> /
```

Pressing `/` opens an interactive dropdown menu with fuzzy completion and descriptions.

---

## Project Structure

```
codex-cli/
├── pyproject.toml          # Package build & dependency metadata
├── setup.py                # Console script entry point (cdx = codex.main:main)
├── assets/                 # Brand assets & logos
│   ├── logo.png            # Official abstract monochrome logo
│   └── codex.png           # Transparent app icon
├── codex/                  # Core package
│   ├── __init__.py         # Package version (1.5.0)
│   ├── client.py           # Official Groq SDK client & system prompt
│   ├── tools.py            # PC agent tools (bash, file I/O, grep, glob, git)
│   ├── ui.py               # Rich UI components, thinking animation, error cards
│   └── main.py             # REPL loop, slash commands, CLI argument parser
└── tests/
    └── test_codex_unittest.py  # Comprehensive test suite
```

---

## Testing

Run the full unit test suite:

```bash
python -m unittest tests.test_codex_unittest -v
```

---

## License

MIT License. Developed by the Codex Project contributors.
