# Codex System Architecture Specification (SPEC.md)

## Overview
Codex is an elite, autonomous terminal-native AI engineering assistant designed for Linux. It bridges the gap between open-source scripts and commercial developer tools through reactive terminal user interfaces, strict safety sandboxing, multi-agent orchestration, and token efficiency.

---

## Roadmap & Implementation Phases

### Phase 1: Config, Auth Lifecycle & Doctor Diagnostics (VERIFIED)
- Configuration loader for `~/.codex/config.json`.
- First-run interactive onboarding wizard (`/onboard`).
- HTTP 401 & 429 error interceptors with auto-failover key rotation.
- `codex doctor` diagnostic health inspection command.
- Verified transparent shield logo and 4-row legless floating mascot with moving eyes.

---

### Phase 2: Context Intelligence, AST Pruning & Sandboxing (VERIFIED)
- Tree-sitter & AST parsing (`codex/ast_parser.py`) for symbol extraction and outlines (`code_outline`, `get_symbol`).
- Smart secret scrubber (`codex/security.py`) redacting API keys, PATs, AWS secrets, and `.env` credentials before transmission.
- Execution sandboxing (`codex/sandbox.py`) using Bubblewrap (`bwrap`) with filesystem boundary locks and dangerous command interceptors.
- Model Context Protocol (`codex/mcp.py`) client with dynamic JSON-RPC server registry and tool schema conversion.
- Dual-tier memory ledger with token budget allocator (`codex/memory.py`).

---

### Phase 3: Sub-Agent Orchestration, Interactive Diff Navigator & CI (VERIFIED)
- Multi-agent planner/worker DAG hierarchy (`codex/subagents.py`): Planner, Scout (read-only), Coder (implementation), and Critic (auditing).
- Interactive hunk-by-hunk diff inspector (`codex/diff_navigator.py`) supporting `[y] accept`, `[n] skip`, `[a] all`, and `[q] quit`.
- Headless CI/CD pipeline mode (`codex/ci.py`) with `--headless` and `--ci` flags and JSON/Markdown automated report generation.
- Shadow Git checkpoint commits (`codex/git_shadow.py`) using custom plumbing ref `refs/codex/history` via `/checkpoint`.

---

### Phase 4: Autonomous Closed-Loop Verification & Tamper Protection (VERIFIED)
- Anti-test tampering guard (`codex/anti_tamper.py`) computing cryptographic SHA-256 fingerprints to ensure implementation fixes rather than rewritten assertions.
- Autonomous test suite and linter validation runner (`codex/verifier.py`).
- 3-cycle repetitive loop breaker detection.
- Automated conventional commit message generation from git diffs (`feat:`, `fix:`, `refactor:`, `test:`).

