"""Autonomous Viral Marketing & Video Flow Studio for Codex-CLI and Grokbot.

Features:
1. Instagram Content Generator & Auto-Upload Prep (Reels, Carousels, Stories, Captions, Hashtags).
2. Google Flow / Veo Video Prompt Engine (Cinematic camera prompts, lighting, motion vectors).
3. Storyboard & Script Generator (Scene-by-scene pacing, audio cues, voiceover scripts).
4. Auto-Upload Queue & Scheduler with viral hook optimization.
"""

import os
import sys
import time
import json
import random
from pathlib import Path
from typing import Dict, Any, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box

console = Console()

MARKETING_QUEUE_FILE = Path.home() / ".codex" / "marketing_queue.json"


class VideoFlowEngine:
    """Generates prompt sequences and storyboards optimized for Google Flow and Veo text-to-video."""

    CAMERA_MOVEMENTS = [
        "Dynamic low-angle slow push-in, cinematic gimbal stabilization, 4K 60fps",
        "Orbiting dolly sweep around subject, shallow depth of field (f/1.4), volumetric lighting",
        "FPV drone dive through neon architectural canyon, high-speed motion blur, anamorphic lens flare",
        "Macro tilt-shift pan across hyper-detailed circuit matrix, cinematic rack focus",
        "SnorriCam chest-mount tracking shot, rhythmic forward momentum, dramatic chiaroscuro shadows"
    ]

    VISUAL_STYLES = [
        "Cyberpunk Noir: bioluminescent neon reflections on wet asphalt, rain droplets, atmospheric haze",
        "Hyperreal Cinematic Documentary: Arri Alexa 65 sensor, natural golden hour rim light, film grain",
        "Futuristic Tech Commercial: pristine clean obsidian glass, holographic floating HUD vectors, raytraced reflections",
        "Dark High-Voltage Anime: ufotable style dynamic line-art, lightning particle bursts, vibrant chromatic aberration",
        "Minimalist Brutalist Architecture: raw concrete monoliths, dramatic sun shafts, architectural precision"
    ]

    @classmethod
    def generate_flow_prompts(cls, concept: str, scene_count: int = 3) -> Dict[str, Any]:
        """Generate ready-to-render Google Flow / Veo video generation prompts."""
        scenes = []
        for i in range(1, scene_count + 1):
            cam = random.choice(cls.CAMERA_MOVEMENTS)
            style = random.choice(cls.VISUAL_STYLES)
            duration = random.choice([4.0, 5.0, 6.0])
            
            prompt = (
                f"{concept}, scene {i}. {style}. Camera: {cam}. "
                f"Photorealistic 8K resolution, photoreal octane render, masterpiece, hyper-detailed, seamless motion."
            )
            
            scenes.append({
                "scene_number": i,
                "duration_seconds": duration,
                "camera_movement": cam,
                "visual_style": style,
                "prompt": prompt,
                "audio_cue": f"Deep bass pulse with rising cyberpunk synth swell, BPM 128 (Scene {i})",
                "voiceover_line": f"The future isn't automated—it's autonomous. Step {i} activates."
            })

        return {
            "concept": concept,
            "total_scenes": scene_count,
            "total_duration": sum(s["duration_seconds"] for s in scenes),
            "scenes": scenes,
            "flow_spec": {
                "aspect_ratio": "9:16 (Instagram Reel / TikTok)",
                "target_fps": 60,
                "color_grading": "Teal & Orange Rec.709",
                "recommended_tool": "Google Flow / Veo 2.0 / Luma Dream Machine"
            }
        }


class InstagramAutomationEngine:
    """Generates viral Instagram packages: captions, hashtags, hooks, and auto-upload specs."""

    VIRAL_HOOKS = [
        "99% of programmers have no idea this AI workflow exists...",
        "Stop coding manually in 2026. Watch this 45,000-agent swarm do it in seconds:",
        "This one AI terminal tool completely replaced my entire dev stack:",
        "The secret high-speed coding setup Silicon Valley engineers aren't talking about:",
        "How 45,000 autonomous sub-agents build full-stack apps while you sleep:"
    ]

    NICHE_HASHTAGS = [
        "#ai", "#coding", "#programmer", "#tech", "#softwareengineer",
        "#developer", "#vibecoding", "#python", "#cyberpunk", "#webdev",
        "#machinelearning", "#artificialintelligence", "#linux", "#devlife",
        "#codex", "#grok", "#innovation", "#buildinpublic", "#futuretech",
        "#algorithm", "#technology", "#fullstack", "#startup", "#productivity"
    ]

    @classmethod
    def create_campaign(cls, topic: str) -> Dict[str, Any]:
        """Create complete Instagram package ready for auto-publishing."""
        hook = random.choice(cls.VIRAL_HOOKS)
        flow_data = VideoFlowEngine.generate_flow_prompts(topic, scene_count=3)
        hashtags = random.sample(cls.NICHE_HASHTAGS, 18)
        
        caption = (
            f"⚡ {hook}\n\n"
            f"We just deployed an autonomous 45,000-agent AI swarm in terminal. "
            f"Strategic decomposition, BFS deep research, and instant consensus—all running at 500+ tok/s.\n\n"
            f"✦ Core Features:\n"
            f"• 3-Tier Multi-Agent Hierarchy (Commander ➔ 45 Managers ➔ 45K Workers)\n"
            f"• Sub-second Cloud Native Server Pipeline\n"
            f"• Automated State Bubbling Shards\n\n"
            f"Drop a 'SWARM' below and we'll DM you the open-source CLI setup! 👇\n\n"
            f"{' '.join(hashtags)}"
        )

        campaign = {
            "id": f"CAMP-{int(time.time()*1000)%100000:05d}",
            "created_at": time.time(),
            "topic": topic,
            "status": "QUEUED_FOR_AUTO_UPLOAD",
            "hook": hook,
            "caption": caption,
            "hashtags": hashtags,
            "video_flow": flow_data,
            "target_platform": "Instagram Reels",
            "auto_upload_schedule": "Next Peak Window (18:00 UTC)",
        }

        # Save to persistent queue
        cls.save_to_queue(campaign)
        return campaign

    @classmethod
    def save_to_queue(cls, campaign: Dict[str, Any]):
        MARKETING_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        queue = []
        if MARKETING_QUEUE_FILE.exists():
            try:
                queue = json.loads(MARKETING_QUEUE_FILE.read_text(encoding="utf-8"))
            except Exception:
                queue = []
        queue.append(campaign)
        MARKETING_QUEUE_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")

    @classmethod
    def get_queue(cls) -> List[Dict[str, Any]]:
        if not MARKETING_QUEUE_FILE.exists():
            return []
        try:
            return json.loads(MARKETING_QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []


def render_marketing_campaign(campaign: Dict[str, Any]):
    """Render the generated Instagram campaign and video flow prompts in rich UI."""
    console.print(Panel(
        f"[bold white]{campaign['hook']}[/]\n\n"
        f"[bold cyan]Campaign ID:[/] {campaign['id']}  │  [bold cyan]Platform:[/] {campaign['target_platform']}\n"
        f"[bold cyan]Auto-Upload Schedule:[/] [bold green]{campaign['auto_upload_schedule']}[/]  │  [bold cyan]Status:[/] [bold green]{campaign['status']}[/]",
        title="[bold green]✦ Instagram Viral Reel & Flow Video Campaign[/]",
        border_style="green"
    ))

    # Render Scenes Table
    t = Table(box=box.ROUNDED, border_style="cyan", title="[bold cyan]Google Flow / Veo Video Prompt Sequences[/]")
    t.add_column("Scene", style="bold green", width=7)
    t.add_column("Duration", style="dim", width=10)
    t.add_column("Flow Video Prompt", style="white")
    t.add_column("Audio / Voiceover", style="dim cyan")

    for s in campaign["video_flow"]["scenes"]:
        t.add_row(
            f"#{s['scene_number']}",
            f"{s['duration_seconds']}s",
            s["prompt"],
            f"{s['audio_cue']}\n\"{s['voiceover_line']}\""
        )
    console.print(t)

    # Render Caption Box
    console.print(Panel(
        campaign["caption"],
        title="[bold yellow]Optimized Instagram Caption & Hashtags[/]",
        border_style="yellow"
    ))
    console.print()
