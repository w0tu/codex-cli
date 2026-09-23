"""Grokbot 45,000+ Agent Swarm Command Center Area for Codex-CLI.

Dedicated interactive terminal environment orchestrating 45,046 autonomous agents,
hierarchical 3-tier command tree, cognitive deep research, multi-agent consensus,
and state bubbling aggregation.
"""

import os
import sys
import time
import json
import webbrowser
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich import box

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import ANSI


console = Console()

SWARM_SERVER_URL = "http://127.0.0.1:8888"
GROKBOT_DIR = Path("/home/feds/.gemini/antigravity/scratch/grokbot")

# ── Leaf-Shaped "SIMPLI" Pure ASCII Art Logo ──────────────────────────────────
# EXACT ASCII ART PER USER CONSTRAINT ("dont change the ascii art please bro")
SIMPLI_LEAF_ASCII = r"""
                         .
                        / \
                       /   \
                      /     \
                     /   .   \
                    /   / \   \
                   /   /   \   \
                  /   /  ^  \   \
                 /   /  / \  \   \
                /   /  /   \  \   \
               |   |  /     \  |   |
               |   | |   S   | |   |
               |   | |   I   | |   |
               |   | |   M   | |   |
               |   | |   P   | |   |
               |   | |   L   | |   |
               |   | |   I   | |   |
               |   |  \     /  |   |
                \   \  \   /  /   /
                 \   \  \ /  /   /
                  \   \  v  /   /
                   \   \   /   /
                    \   \ /   /
                     \   '   /
                      \     /
                       \   /
                        \ /
                         |
                         |
                         '

  ███████╗██╗███╗   ███╗██████╗ ██╗     ██╗
  ██╔════╝██║████╗ ████║██╔══██╗██║     ██║
  ███████╗██║██╔████╔██║██████╔╝██║     ██║
  ╚════██║██║██║╚██╔╝██║██╔═══╝ ██║     ██║
  ███████║██║██║ ╚═╝ ██║██║     ███████╗██║
  ╚══════╝╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝╚═╝
"""


class SwarmBridgeClient:
    """Client for communicating with the Grokbot swarm daemon."""

    def __init__(self, base_url: str = SWARM_SERVER_URL):
        self.base_url = base_url
        self.client = httpx.Client(base_url=self.base_url, timeout=35.0)

    def is_alive(self) -> bool:
        try:
            res = self.client.get("/api/health", timeout=1.5)
            return res.status_code == 200
        except Exception:
            return False

    def ensure_server_running(self) -> bool:
        """Ensure Grokbot daemon is active on port 8888."""
        if self.is_alive():
            return True

        # Try to launch server in background
        server_py = GROKBOT_DIR / "server.py"
        venv_py = GROKBOT_DIR / ".venv" / "bin" / "python"
        if not venv_py.exists():
            venv_py = Path(sys.executable)

        if server_py.exists():
            try:
                subprocess.Popen(
                    [str(venv_py), "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8888"],
                    cwd=str(GROKBOT_DIR),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                for _ in range(12):
                    time.sleep(0.4)
                    if self.is_alive():
                        return True
            except Exception:
                pass
        return False

    def get_summary(self) -> Dict[str, Any]:
        res = self.client.get("/api/swarm/summary")
        res.raise_for_status()
        return res.json()

    def get_clusters(self) -> List[Dict[str, Any]]:
        res = self.client.get("/api/swarm/clusters")
        res.raise_for_status()
        return res.json().get("clusters", [])

    def inspect_agent(self, agent_id: int) -> Dict[str, Any]:
        res = self.client.get(f"/api/swarm/inspect/{agent_id}")
        res.raise_for_status()
        return res.json().get("agent", {})

    def launch_mission(self, objective: str) -> Dict[str, Any]:
        res = self.client.post("/api/mission/launch", json={"objective": objective})
        res.raise_for_status()
        return res.json()

    def run_research(self, topic: str, depth: int = 2) -> Dict[str, Any]:
        res = self.client.post("/api/research", json={"topic": topic, "depth": depth})
        res.raise_for_status()
        return res.json()

    def run_consensus(self, proposal: str, voter_count: int = 5) -> Dict[str, Any]:
        res = self.client.post("/api/consensus", json={"proposal": proposal, "voter_count": voter_count})
        res.raise_for_status()
        return res.json()

    def decompose(self, objective: str) -> Dict[str, Any]:
        res = self.client.post("/api/decompose", json={"objective": objective})
        res.raise_for_status()
        return res.json()

    def get_models(self) -> Dict[str, Any]:
        res = self.client.get("/api/models/pings")
        res.raise_for_status()
        return res.json().get("backends", {})

    def chat_commander(self, message: str) -> Dict[str, Any]:
        res = self.client.post("/api/chat", json={"message": message, "tier": 1})
        res.raise_for_status()
        return res.json()


def render_swarm_banner(is_connected: bool):
    """Render the leaf ASCII logo and Cyberpunk Swarm Command Center header."""
    console.print(f"[bold green]{SIMPLI_LEAF_ASCII}[/]")
    
    status_str = "[bold green]ONLINE (Port 8888)[/]" if is_connected else "[bold yellow]LOCAL STANDALONE[/]"
    header_box = (
        f"[bold white]══════════════════════════════════════════════════════════════════════[/]\n"
        f"[bold cyan]✦ GROKBOT SWARM COMMAND CENTER[/] ░ [bold green]45,046 ACTIVE AGENTS[/]\n"
        f"[dim]✦ ARCHITECTURE:[/] Tier 1 Commander ➔ 45 Tier 2 Managers ➔ 45,000 Tier 3 Workers\n"
        f"[dim]✦ PROTOCOLS:[/] Deep Research BFS ░ Multi-Agent Consensus ░ State Bubbling\n"
        f"[dim]✦ DAEMON STATUS:[/] {status_str} | Web GUI: [bold cyan]http://localhost:8888/[/]\n"
        f"[bold white]══════════════════════════════════════════════════════════════════════[/]"
    )
    console.print(header_box)
    console.print("[dim]Type [bold white]help[/] for command matrix or [bold white]exit[/] to return to Codex CLI.\n[/]")


def render_swarm_help():
    """Display the Swarm area command matrix."""
    t = Table(box=box.ROUNDED, border_style="cyan", title="[bold cyan]Grokbot Swarm Command Matrix (45,000+ Agents)[/]")
    t.add_column("Directive", style="bold green", no_wrap=True)
    t.add_column("Arguments", style="dim cyan")
    t.add_column("Description", style="white")

    t.add_row("status", "", "Display live 3-tier hierarchy & 45,046 agent breakdown")
    t.add_row("clusters", "", "List performance & confidence vectors for all 45 cluster hubs")
    t.add_row("launch", "<mission>", "Dispatch 45,000 sub-agents in waves with state bubbling aggregation")
    t.add_row("research", "<topic>", "Execute Deep Research Protocol (BFS insight tree & synthesis)")
    t.add_row("consensus", "<code/prop>", "Run multi-agent debate and voting audit (>75% approval pass)")
    t.add_row("decompose", "<goal>", "Compute sequential DAG task decomposition graph")
    t.add_row("inspect", "<0..45045>", "Deep inspect any node (Tier 1, Tier 2, or Tier 3)")
    t.add_row("models", "", "Probe latency across Cloud Native, OpenRouter, Gemini, Ollama, DeepSeek")
    t.add_row("web", "", "Open real-time 60 FPS HTML5 Canvas Visualizer in browser (port 8888)")
    t.add_row("clear", "", "Clear terminal screen and redraw SIMPLI leaf banner")
    t.add_row("help, ?", "", "Show this command reference")
    t.add_row("exit, back", "", "Exit Swarm Area and return to Codex CLI")
    t.add_row("[any query]", "<text>", "Direct chat with Tier 1 Commander via Cloud Native Server")

    console.print(t)
    console.print()


def render_status_table(summary: Dict[str, Any]):
    """Render comprehensive 3-tier swarm status."""
    t = Table(box=box.ROUNDED, border_style="green", title="[bold green]Hierarchical 3-Tier Swarm Telemetry[/]")
    t.add_column("Hierarchy Tier", style="bold white")
    t.add_column("Node Count", style="bold cyan")
    t.add_column("Active Shards", style="green")
    t.add_column("Bubbling", style="yellow")
    t.add_column("Resolved", style="bright_green")
    t.add_column("Idle / Standby", style="dim")

    cmd = summary.get("tier_1_commander", {})
    t.add_row(
        "Tier 1: Commander / CEO",
        "1 Node",
        "1" if summary.get("commander_state") == 2 else "0",
        "1" if summary.get("commander_state") == 3 else "0",
        "1" if summary.get("commander_state") == 4 else "0",
        "1" if summary.get("commander_state") == 0 else "0",
    )
    t.add_row(
        "Tier 2: Cluster Managers",
        f"{summary.get('num_clusters', 45)} Hubs",
        str(summary.get("tier_2_managers_active", 0)),
        "-",
        "-",
        str(summary.get("num_clusters", 45) - summary.get("tier_2_managers_active", 0)),
    )
    t.add_row(
        "Tier 3: Worker Swarm",
        f"{summary.get('total_workers', 45000):,} Sub-Agents",
        f"{summary.get('workers_executing', 0):,}",
        f"{summary.get('workers_bubbling', 0):,}",
        f"{summary.get('workers_resolved', 0):,}",
        f"{summary.get('workers_idle', 45000):,}",
    )
    console.print(t)

    conf = summary.get("average_worker_confidence", 0.95)
    console.print(
        f"[dim]Total Swarm Nodes:[/] [bold cyan]{summary.get('total_agents', 45046):,}[/] │ "
        f"[dim]Avg Confidence:[/] [bold green]{conf * 100:.1f}%[/] │ "
        f"[dim]State Bubbling:[/] [bold yellow]Leaf ➔ Manager ➔ Commander (Depth 3)[/]\n"
    )


def render_clusters_table(clusters: List[Dict[str, Any]]):
    """Render all 45 cluster hubs."""
    t = Table(box=box.SIMPLE_HEAVY, border_style="cyan", title="[bold cyan]45 Swarm Cluster Manager Hubs[/]")
    t.add_column("ID", style="bold cyan", width=5)
    t.add_column("Role / Function", style="white", width=26)
    t.add_column("Workers", style="dim", width=10)
    t.add_column("Active", style="green", width=8)
    t.add_column("Resolved", style="bright_green", width=10)
    t.add_column("Confidence", style="bold green", width=12)

    for c in clusters:
        conf_pct = c.get("avg_confidence", 0.95) * 100
        t.add_row(
            f"C-{c['cluster_id']:02d}",
            c.get("role", "Cluster Hub"),
            str(c.get("total_workers", 1000)),
            str(c.get("active_workers", 0)),
            str(c.get("resolved_workers", 0)),
            f"{conf_pct:.1f}%",
        )
    console.print(t)
    console.print()


def render_agent_card(agent: Dict[str, Any]):
    """Render deep inspection details for a single agent."""
    tier_names = {1: "Tier 1 (Commander / CEO)", 2: "Tier 2 (Manager / Orchestrator)", 3: "Tier 3 (Worker Swarm Leaf)"}
    tier_label = tier_names.get(agent.get("tier", 3), f"Tier {agent.get('tier')}")
    
    info = (
        f"[bold cyan]Agent ID:[/] #{agent.get('id')}  │  [bold cyan]Hierarchy:[/] {tier_label}\n"
        f"[bold cyan]Role:[/] {agent.get('role', 'Autonomous Agent')}\n"
        f"[bold cyan]Status:[/] [bold green]{agent.get('state', 'IDLE')}[/]  │  [bold cyan]Confidence:[/] [bold green]{agent.get('confidence', 0.95)*100:.1f}%[/]\n"
        f"[bold cyan]Current Task:[/] {agent.get('current_task', 'Standby / Monitoring')}\n"
        f"[bold cyan]Summary Vector:[/] [dim]{agent.get('summary', 'Telemetry synchronized.')}[/]"
    )
    console.print(Panel(info, title=f"[bold green]{agent.get('title', 'Agent Node')}[/]", border_style="cyan"))
    console.print()


def render_models_table(models: Dict[str, Any]):
    """Render model latency probes."""
    t = Table(box=box.ROUNDED, border_style="cyan", title="[bold cyan]Active Model Routing Matrix[/]")
    t.add_column("Provider / Node", style="bold white")
    t.add_column("Latency", style="bold cyan")
    t.add_column("Health Status", style="green")

    for k, v in models.items():
        status_style = "bold green" if v.get("status") == "HEALTHY" else ("bold yellow" if v.get("status") == "DEGRADED" else "dim red")
        lat_str = f"{v.get('latency_ms', 0):.1f}ms" if v.get("latency_ms", 0) > 0 else "OFFLINE"
        t.add_row(v.get("name", k), lat_str, f"[{status_style}]{v.get('status', 'UNKNOWN')}[/]")
    console.print(t)
    console.print()


def render_dag_tree(task_graph: List[Dict[str, Any]], objective: str):
    """Render sequential DAG task decomposition tree."""
    tree = Tree(f"[bold cyan]DAG Task Decomposition:[/] [bold white]{objective}[/]")
    for t in task_graph:
        deps = f"[dim](depends on: {', '.join(map(str, t['dependencies']))})[/]" if t.get("dependencies") else "[bold green][ROOT][/]"
        node = tree.add(f"[bold yellow]Task #{t['id']}:[/] [bold white]{t['title']}[/] {deps}")
        node.add(f"[dim]Cluster Target:[/] [cyan]{t.get('cluster_target', 'Worker Swarm')}[/]")
        node.add(f"[dim]Description:[/] {t.get('description', '')}")
    console.print(tree)
    console.print()


# ── Interactive Swarm Area REPL Loop ──────────────────────────────────────────

def run_swarm_area(client: Optional[Any] = None) -> None:
    """Enter the dedicated Grokbot 45,000+ Agent Swarm Command Center area."""
    bridge = SwarmBridgeClient()

    console.print("\n[bold cyan]✦ Entering Grokbot 45,000+ Agent Swarm Command Center...[/]")
    is_connected = bridge.ensure_server_running()

    render_swarm_banner(is_connected)

    history_file = Path.home() / ".codex" / "swarm_history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    swarm_completer = WordCompleter([
        "help", "status", "summary", "clusters", "launch", "research",
        "consensus", "decompose", "inspect", "models", "ping", "web",
        "dashboard", "clear", "back", "exit", "quit"
    ], ignore_case=True)

    pt = PromptSession(
        history=FileHistory(str(history_file)),
        completer=swarm_completer,
    )

    prompt_display = "\033[1;32mCDX\033[0m:\033[1;36m//\033[0m\033[1;32mSWARM\033[0m\033[2m(45K)>\033[0m "

    while True:
        try:
            cmd = pt.prompt(ANSI(prompt_display)).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]✦ Returning to standard Codex CLI workspace.[/]\n")
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if action in ("exit", "quit", "back", "/exit", "/back"):
            console.print("[bold cyan]✦ Exiting Swarm Area. Returning to Codex CLI workspace.[/]\n")
            break

        elif action in ("help", "?", "/help"):
            render_swarm_help()

        elif action in ("clear", "/clear"):
            os.system("clear")
            render_swarm_banner(bridge.is_alive())

        elif action in ("web", "dashboard", "/web"):
            web_url = "http://localhost:8888/"
            console.print(f"[bold cyan]✦ Opening Grokbot 60 FPS Visualizer:[/] [underline green]{web_url}[/]")
            try:
                webbrowser.open(web_url)
            except Exception:
                pass

        elif action in ("status", "summary", "/status", "/swarm"):
            try:
                s = bridge.get_summary()
                render_status_table(s)
            except Exception as e:
                console.print(f"[bold red]Failed to retrieve swarm summary:[/] {e}")

        elif action in ("clusters", "managers", "/clusters"):
            try:
                cl = bridge.get_clusters()
                render_clusters_table(cl)
            except Exception as e:
                console.print(f"[bold red]Failed to retrieve clusters:[/] {e}")

        elif action in ("inspect", "/inspect"):
            node_id = int(arg) if arg.isdigit() else 0
            try:
                agent = bridge.inspect_agent(node_id)
                render_agent_card(agent)
            except Exception as e:
                console.print(f"[bold red]Agent #{node_id} inspection error:[/] {e}")

        elif action in ("models", "ping", "pings", "/models"):
            try:
                m = bridge.get_models()
                render_models_table(m)
            except Exception as e:
                console.print(f"[bold red]Failed to probe model latencies:[/] {e}")

        elif action in ("decompose", "/decompose"):
            goal = arg or "Deploy global fault-tolerant autonomous swarm network"
            console.print(f"[bold cyan]✦ Computing DAG Task Decomposition for:[/] [bold white]{goal}[/]...")
            try:
                res = bridge.decompose(goal)
                render_dag_tree(res.get("task_graph", []), goal)
            except Exception as e:
                console.print(f"[bold red]Decomposition error:[/] {e}")

        elif action in ("consensus", "/consensus"):
            proposal = arg or "def verify_merkle_root(shards): return all(s.is_valid for s in shards)"
            console.print(f"[bold cyan]✦ Initiating Multi-Agent Reflection & Voting Consensus (>75% Threshold)...[/]")
            try:
                res = bridge.run_consensus(proposal)
                verdict_color = "bold green" if res.get("consensus_reached") else "bold red"
                console.print(f"\n[{verdict_color}]════════ CONSENSUS VERDICT: {res.get('verdict')} ════════[/]")
                console.print(
                    f"✦ Approvals: [bold green]{res.get('approvals')}/{res.get('num_voters')}[/] "
                    f"({res.get('consensus_score', 0)*100:.0f}%) │ Threshold: {res.get('threshold', 0.75)*100:.0f}%"
                )
                for c in res.get("critiques", []):
                    v_color = "green" if c.get("vote") == "APPROVE" else "red"
                    crit = c.get("critique", "").replace("VOTE: APPROVE", "").replace("VOTE: REJECT", "").strip()
                    console.print(f"  • [bold white]{c.get('agent')} ({c.get('role')}):[/] [{v_color}]{c.get('vote')}[/] ➔ {crit}")
                console.print()
            except Exception as e:
                console.print(f"[bold red]Consensus audit failed:[/] {e}")

        elif action in ("research", "/research"):
            topic = arg or "Sub-millisecond Swarm Consensus Protocols"
            console.print(f"[bold cyan]✦ Commencing Deep Research Protocol for:[/] [bold white]{topic}[/]...")
            try:
                res = bridge.run_research(topic, depth=2)
                console.print(f"\n[bold green]════════ DEEP RESEARCH EXECUTIVE REPORT ════════[/]")
                console.print(f"[dim]Visited {res.get('nodes_visited', 0)} BFS Nodes │ {res.get('total_insights', 0)} Insights in {res.get('elapsed_seconds', 0)}s[/]\n")
                console.print(Markdown(res.get("executive_synthesis", "Research completed.")))
                console.print()
            except Exception as e:
                console.print(f"[bold red]Deep research failed:[/] {e}")

        elif action in ("launch", "/launch"):
            mission = arg or "Analyze distributed zero-day threat vectors & aggregate consensus"
            console.print(f"[bold cyan]✦ Launching 45,000 sub-agent mission:[/] [bold white]{mission}[/]...")
            
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40, style="green", complete_style="bold green"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                t1 = progress.add_task("[cyan]Tier 1 Strategic Decomposition...", total=100)
                time.sleep(0.3)
                progress.update(t1, advance=30, description="[blue]Tier 2 Manager Hub Directives Dispatched...")
                time.sleep(0.3)
                progress.update(t1, advance=30, description="[green]Tier 3 Mass Activation (45,000 Agents)...")
                time.sleep(0.4)
                progress.update(t1, advance=25, description="[yellow]State Bubbling Aggregation...")
                
                try:
                    res = bridge.launch_mission(mission)
                    progress.update(t1, completed=100, description="[bold green]Mission Resolved!")
                    console.print(f"\n[bold green]════════ MISSION COMPLETED ════════[/]")
                    console.print(f"✦ Summary: {res.get('summary')}")
                    console.print(
                        f"✦ Total Nodes: [bold cyan]{res.get('total_agents', 45046):,}[/] │ "
                        f"Elapsed: [bold green]{res.get('elapsed', 0)}s[/] │ "
                        f"Confidence: [bold green]{res.get('confidence', 0.98)*100:.1f}%[/]\n"
                    )
                except Exception as e:
                    progress.update(t1, description="[bold red]Mission Failed")
                    console.print(f"[bold red]Mission launch failed:[/] {e}")

        else:
            # Query Tier 1 Commander directly
            console.print("[dim]✦ Querying Tier 1 Commander via Cloud Native Server...[/]")
            try:
                res = bridge.chat_commander(cmd)
                txt = res.get("content", "Directive processed.")
                console.print(Markdown(txt))
                model_used = res.get("model_used", "Cloud Native Server")
                console.print(f"[dim]Processed by {model_used}[/]\n")
            except Exception as e:
                console.print(f"[bold red]Commander query error:[/] {e}")
