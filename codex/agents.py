"""Agent Registry for 45,000+ Hierarchical Swarm Agents & Domain Personas."""

import json
from pathlib import Path
from typing import Any, List, Dict, Optional

GLOBAL_AGENTS_PATH = Path.home() / ".codex" / "agents" / "agents.json"

CLUSTER_DEFINITIONS = [
    ("C-00", "Deep Web Scraping & Sharding", "Parallel data gathering, headless browser scraping, API ingestion"),
    ("C-01", "Data Synthesis & Normalization", "ETL transformation, deduplication, schema validation"),
    ("C-02", "Code Audit & Static Analysis", "AST parsing, vulnerability detection, security heuristics"),
    ("C-03", "Pattern Recognition & Heuristics", "Code smell detection, anti-pattern identification"),
    ("C-04", "Crypto Verify & Zero-Knowledge", "Merkle tree proofs, cryptographic verification, signature validation"),
    ("C-05", "Net Telemetry & Flow Monitoring", "Packet latency analysis, connection health, mesh heartbeat"),
    ("C-06", "Semantic Index & Vector Embeds", "Dense retrieval, embedding cluster indexing, vector search"),
    ("C-07", "AST Parser & Syntax Engine", "Language grammar compilation, tree transformation"),
    ("C-08", "Security Scan & Penetration Test", "OWASP top 10 auditing, memory corruption checks"),
    ("C-09", "Distributed Consensus & Voting", "Byzantine fault tolerance, multi-agent debate resolution"),
    ("C-10", "Vector Embeds & Memory Matrix", "Long-term episodic recall, memory shard retrieval"),
    ("C-11", "Algorithmic Solver & Graph Theory", "DAG scheduling, shortest path resolution, dependency graphs"),
    ("C-12", "Recursive Search & Expansion", "BFS/DFS insight trees, autonomous follow-up inquiry"),
    ("C-13", "API Gateway & Microsegmentation", "Zero-trust ingress, token rate limits, proxy routing"),
    ("C-14", "Anomaly Detect & Sentinel Watch", "Outlier detection, runtime behavioral monitoring"),
    ("C-15", "Viral Marketing & Social Growth", "Instagram Reels hooks, viral captions, engagement loops"),
    ("C-16", "Insta Video & Flow Reels Pipeline", "Google Flow / Veo video generation prompts, storyboard pacing"),
    ("C-17", "Legal Counsel & Contract Audit", "Agreement reviews, indemnification analysis, liability shields"),
    ("C-18", "IP & Compliance Gatekeeper", "Copyright infringement scanning, GDPR/CCPA TOS generation"),
    ("C-19", "Autonomous Database Optimizer", "PostgreSQL indexing, query plan tuning, connection pooling"),
    ("C-20", "Frontend React & Next.js Architect", "App router optimization, Server Components, hydration tuning"),
    ("C-21", "DevOps & Kubernetes Orchestrator", "Helm manifests, container security, rolling zero-downtime"),
    ("C-22", "High-Throughput Streaming Engine", "WebSocket backpressure, SSE buffering, zero-copy serialization"),
] + [
    (f"C-{i:02d}", f"Specialized Cluster Hub #{i:02d}", f"Autonomous sub-agent shard manager for Domain Shard #{i}")
    for i in range(23, 45)
]


class AgentRegistry:
    """Discovers, filters, and activates across all 45,046 agents in the swarm."""

    def __init__(self):
        self.static_agents: list[dict[str, Any]] = []
        self._load_static_agents()
        self.total_swarm_agents = 45046
        self.num_clusters = 45
        self.workers_per_cluster = 1000

    def _load_static_agents(self) -> None:
        if GLOBAL_AGENTS_PATH.exists():
            try:
                self.static_agents = json.loads(GLOBAL_AGENTS_PATH.read_text(encoding="utf-8"))
            except Exception:
                self.static_agents = []

    def get_agent(self, name_or_id: str) -> dict[str, Any] | None:
        """Find agent by ID (0..45045) or specialized persona name."""
        clean = name_or_id.strip().lower()

        # 1. Numeric Swarm Node ID lookup (0 to 45045)
        if clean.isdigit() or (clean.startswith("#") and clean[1:].isdigit()):
            node_id = int(clean.lstrip("#"))
            if 0 <= node_id <= 45045:
                if node_id == 0:
                    return {
                        "id": 0,
                        "name": "The Commander / CEO Node",
                        "tier": 1,
                        "role": "Supreme Commander / CEO Node",
                        "category": "Executive",
                        "description": "Top-level strategic planning, mission decomposition, and final executive synthesis for 45,000 sub-agents.",
                        "system_prompt": "You are the Tier 1 Commander / CEO of the 45,000+ Agent Swarm. Formulate decisive, architectural, strategic solutions."
                    }
                elif 1 <= node_id <= 45:
                    c_idx = node_id - 1
                    c_tag, c_name, c_desc = CLUSTER_DEFINITIONS[c_idx]
                    return {
                        "id": node_id,
                        "name": f"Manager #{c_idx} ({c_name})",
                        "tier": 2,
                        "cluster_id": c_idx,
                        "role": f"Tier 2 Manager: {c_name}",
                        "category": "Cluster Orchestrator",
                        "description": f"Directs 1,000 specialized workers for {c_name}. {c_desc}",
                        "system_prompt": f"You are Cluster Manager #{c_idx} ({c_name}). Route domain goals and aggregate bubbling shards."
                    }
                else:
                    w_idx = node_id - 46
                    c_idx = w_idx // 1000
                    c_tag, c_name, _ = CLUSTER_DEFINITIONS[c_idx]
                    return {
                        "id": node_id,
                        "name": f"Swarm Leaf Agent #{node_id}",
                        "tier": 3,
                        "cluster_id": c_idx,
                        "role": f"Sub-Agent: {c_name}",
                        "category": "Worker Swarm",
                        "description": f"Parallel leaf execution shard in {c_name} (Cluster {c_idx}).",
                        "system_prompt": f"You are Leaf Sub-Agent #{node_id} specialized in {c_name}."
                    }

        # 2. Check specialized personas (frontend, writer, reddit, wizard, explore, plan)
        from codex.personas import get_specialized_persona, list_specialized_personas
        sp = get_specialized_persona(clean)
        if sp:
            return sp

        # 3. Check static domain personas (react-architect, security-auditor, etc.)
        for a in self.static_agents:
            if a["name"].lower() == clean:
                return a
        for a in self.static_agents:
            if clean in a["name"].lower() or clean in a.get("role", "").lower():
                return a

        # 4. Check cluster names (marketing, legal, scraping, crypto, etc.)
        for i, (tag, name, desc) in enumerate(CLUSTER_DEFINITIONS):
            if clean in name.lower() or clean in tag.lower():
                return self.get_agent(str(i + 1))

        return None

    def list_agents(self, category: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
        """List and filter agents across the 45,000 swarm and domain specialists."""
        results = []

        # Add Commander
        results.append(self.get_agent("0"))

        # Add 45 Cluster Managers
        for i in range(1, 46):
            results.append(self.get_agent(str(i)))

        # Add specialized personas (frontend, writer, reddit, wizard, explore, plan)
        from codex.personas import list_specialized_personas
        results.extend(list_specialized_personas())

        # Add specialized domain agents
        results.extend(self.static_agents)

        if category:
            cat_clean = category.strip().lower()
            results = [a for a in results if a.get("category", "").lower() == cat_clean]

        if query:
            q_clean = query.strip().lower()
            results = [
                a for a in results
                if q_clean in a.get("name", "").lower()
                or q_clean in a.get("role", "").lower()
                or q_clean in a.get("description", "").lower()
            ]

        return results

    def get_categories(self) -> list[str]:
        cats = {"Executive", "Cluster Orchestrator", "Worker Swarm"}
        for a in self.static_agents:
            cats.add(a.get("category", "General"))
        return sorted(cats)
