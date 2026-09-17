# Codex System Architecture Specification (SPEC.md)

## Overview
Codex is an elite, autonomous terminal-native AI engineering assistant designed for Linux. It bridges the gap between open-source scripts and commercial developer tools through reactive terminal user interfaces, strict safety sandboxing, multi-agent orchestration, and token efficiency.

---

## Roadmap & Implementation Phases

### Phase 1: Config, Auth Lifecycle & Doctor Diagnostics (CURRENT FOCUS)
1. **Configuration Loader (`~/.codex/config.json`)**:
   - Structured JSON schema supporting primary `api_key`, `backup_keys` list for zero-downtime failover, default `model`, `theme`, and permissions.
   - Atomic reading and saving with directory bootstrapping.
2. **First-Run Interactive Onboarding Wizard**:
   - Intercepts missing/empty config on startup.
   - Prompts for API keys with masked input (`••••`), validates keys via live ping, and saves validated configuration.
3. **HTTP 401 & 429 Error Interceptors with Auto-Failover**:
   - Catches 401 (Authentication) and 429 (Rate Limit) exceptions.
   - Rotates automatically to secondary/backup API keys if configured.
   - Presents actionable recovery remedies.
4. **`codex doctor` Diagnostic Command**:
   - Verifies system environment: Python version, Git tree status, terminal geometry/UTF-8 support, workspace access permissions, config integrity, and live API ping reachability & latency.
5. **Phase 1 Verification**:
   - 100% test coverage with automated unit tests for all Phase 1 components.

---

### Phase 2: Context Intelligence, AST Pruning & Sandboxing
- Tree-sitter AST parsing and symbol graph navigation.
- Dual-tier memory ledger (active sliding window + consolidated knowledge summary).
- Model Context Protocol (MCP) server integration.
- Linux namespaces / Bubblewrap execution isolation.

---

### Phase 3: Sub-Agent Orchestration, Interactive Diff Navigator & CI
- Multi-agent planner/worker DAG hierarchy.
- Interactive hunk-by-hunk diff inspector (`[y] accept`, `[n] skip`, `[e] edit`).
- Headless CI/CD pipeline mode (`--headless`).
- Git shadow checkpoint commits (`refs/codex/history`).
