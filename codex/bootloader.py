"""Cyberpunk Terminal Coding Bootloader & Interactive Boot Selector for Codex-CLI.

Renders high-speed scrolling assembly, neural matrix initialization, and boot mode selector:
[1] 45,000+ Swarm Command Center
[2] Codex-CLI Autonomous Coding REPL
[3] Viral Marketing & Insta Flow Video Studio
[4] Autonomous Legal Counsel & Contract Audit
"""

import sys
import time
import random
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

CYBER_CODE_SNIPPETS = [
    "0x7FFF8010: mov eax, cr0; or eax, 0x80000001; mov cr0, eax  # ENABLE_PAGING_64",
    "init_neural_mesh: sharding 45,000 sub-agents across 45 cluster matrices...",
    "[CUDA_KERNEL_0] <<<128, 512>>> stream_tensor_weights(dim=4096, dtype=fp16)",
    "crypt_verify: Merkle tree root hash = 0x9f8a32b1c4e85d9972a11b7d5e4f2038",
    "groq_lpu_matrix: establishing cloaked pipeline ➔ 500+ tok/s throughput verified",
    "bubbling_state: leaf vectors bound to managers 0x00 through 0x2C (Depth: 3)",
    "instagram_flow_engine: compiling Google Flow / Veo 9:16 cinematography hooks",
    "legal_shield: liability disclaimer loaded, IP protection gates active",
    "sys_security: zero-trust perimeter verified. Memory scrubber initialized.",
    "0x7FFF9200: call swarm_executive_dispatch; test rax, rax; jz .HALT_ERR",
    "consensus_engine: 5-persona voting quorum verified with threshold 0.75",
    "telemetry_link: WebSocket streaming on port 8888. 45,046 nodes locked."
]


def play_coding_screen_loader(duration_seconds: float = 0.8):
    """Render animated high-speed terminal scrolling code lines."""
    end_time = time.time() + duration_seconds
    colors = ["dim green", "green", "bold green", "bright_green", "cyan", "dim cyan"]

    while time.time() < end_time:
        line = random.choice(CYBER_CODE_SNIPPETS)
        col = random.choice(colors)
        prefix = f"[{random.randint(10, 99)}.{random.randint(100, 999)}ms]"
        console.print(f"[dim]{prefix}[/] [{col}]{line}[/]")
        time.sleep(0.04)


def run_boot_selector(interactive: bool = True) -> str:
    """Display interactive Cyberpunk Boot Mode Selector.
    
    Returns: 'swarm', 'repl', 'marketing', or 'legal'
    """
    selector_text = (
        "[bold cyan]SELECT SYSTEM BOOT ENVIRONMENT:[/]\n\n"
        "  [bold green][1][/] [bold white]45,000+ AGENT SWARM COMMAND CENTER[/]  [dim](Command Core, Clusters, 60 FPS Visualizer)[/]\n"
        "  [bold green][2][/] [bold white]CODEX-CLI AUTONOMOUS CODING REPL[/]    [dim](Sub-second Groq LPU, 222 Personas, Local Mode)[/]\n"
        "  [bold green][3][/] [bold white]INSTAGRAM & GOOGLE FLOW VIDEO STUDIO[/] [dim](Reels generation, Flow prompts, viral hooks)[/]\n"
        "  [bold green][4][/] [bold white]AUTONOMOUS LEGAL COUNSEL & AUDIT[/]    [dim](Contract auditor, IP copyright scan, TOS shield)[/]\n\n"
        "[dim]Press [1-4] or hit ENTER for default [2]:[/] "
    )

    console.print(Panel(selector_text, title="[bold green]✦ SYSTEM BOOTLOADER 2.0[/]", border_style="cyan", box=box.ROUNDED))

    if not interactive or not sys.stdin.isatty():
        return "repl"

    try:
        choice = input("BOOT> ").strip()
        if choice == "1":
            return "swarm"
        elif choice == "3":
            return "marketing"
        elif choice == "4":
            return "legal"
        else:
            return "repl"
    except (KeyboardInterrupt, EOFError):
        return "repl"
