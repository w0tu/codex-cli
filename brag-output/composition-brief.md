# Hyperframes Composition Brief: CDX

## Objective
Create a short cinematic launch-style brag video for CDX — an autonomous AI coding assistant for Linux.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds

## Source Material
- Project root: `/home/feds/.gemini/antigravity/scratch/codex-cli/`
- Primary files read: `codex/web/index.html`, `codex/app.py`, `codex/client.py`, `codex/subagents.py`, `README.md`
- Product name: CDX
- Tagline / strongest claim: "Autonomous AI Desktop for Linux · 500+ tok/s on Groq LPUs · 4-Agent Concurrent Swarm"
- Key UI or visual moment to recreate: The Sub-Agents Swarm DAG with 4 concurrent nodes processing and completing, and the glassmorphic chat interface streaming code
- Copy that must appear verbatim:
  - "CDX"
  - "Build an AI-powered SaaS MVP"
  - "cdx 3.2 LPU Ultra · 528 tok/s"
  - "12 Autonomous Specialists"
  - "Autonomous AI Desktop for Linux"
  - "sudo apt install cdx"
  - "Created by Saad Kashif"

## Creative Direction
- Tone preset: cinematic
- Creative direction: futuristic developer workstation reveal — OLED noir meets engineering power
- Interpretation: Dramatic reveals with weighted motion. The OLED black amplifies every emerald glow. Transitions are smooth wipes and crossfades. Confidence through craft, not volume.
- Angle: Your entire engineering team fits inside one dark terminal window. While other tools chat, CDX *executes* — orchestrating 4 autonomous agents in parallel.
- Hook: Pure black, blinking cursor, mission directive types itself out
- Outro / punchline: Minimal brand card — CDX wordmark, tagline, install command, creator credit, emerald glow pulse
- Avoid:
  - Generic SaaS language ("streamline", "supercharge", "unlock")
  - Abstract filler visuals (gradient meshes, AI blobs)
  - Unrelated visual redesign — use the project's actual OLED/emerald palette

## Visual Identity
- Background: #000000 (pure OLED black)
- Text: #ffffff (primary), #9ca3af (secondary)
- Accent: #10b981 (emerald green), glow: rgba(16, 185, 129, 0.3)
- Secondary accents: #8b5cf6 (violet/Architect), #0d9488 (teal/Backend), #06b6d4 (cyan/Frontend), #f97316 (orange/Auditor)
- Display font: Inter 700 (or system fallback)
- Body font: Inter 400
- Code font: JetBrains Mono 500 (for install command and code blocks)
- Visual references from the project: glassmorphic cards (backdrop-filter: blur(14px), border: 1px solid rgba(255,255,255,0.07)), ambient particle canvas, emerald glow borders, 4-node DAG status grid

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. The Hook — 4s — Cursor blinks, mission types out character by character, model badge appears, glassmorphic card materializes
2. The Swarm Explosion — 5s — 4 DAG nodes fire simultaneously (violet/teal/cyan/orange), pulse RUNNING→DONE one by one, synthesis panel slides up
3. The Arsenal — 5s — Code streams at 528 tok/s with counter, then 12 agent cards fan out in staggered grid reveal
4. The Brand Card — 6s — Pure black, CDX wordmark, tagline, install command, creator credit, emerald glow pulse

## Audio
- Audio role: cinematic support with electronic textures
- Audio arc: tension build (0-4s) → explosive drop at swarm launch (4-9s) → sustained energy through showcase (9-14s) → duck and fade under brand card (14-20s)
- Music: happy-beats-business-moves-vol-12-by-ende-dot-app.mp3
- Music treatment: fade in at 0s (60% vol), build to 80% at 4s, sustain through highlights, duck to 40% at 16s, fade out by 20s
- Music cue guidance: Bundled preset at `assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`. Strong cues to target: 8.74s for swarm completion reveal, 13.11s for agent hub fan-out, 17.47s for brand card wordmark. Beat grid at ~0.55s intervals for sequential card arrivals.
- Audio-reactive treatment: subtle; emerald glow intensity breathes with RMS energy, particle canvas opacity responds to bass. No waveform/equalizer visuals.
- Audio-coupled moments:
  - Scene 1 (0-4s) — typing: key ticks per character
  - Scene 2 (4-9s) — swarm launch: impact hit on button, UI click per node DONE, announcement cue on synthesis
  - Scene 3 (9-14s) — code stream: subtle digital cascade; agent cards: beat-grid reveals at 13.11s window
  - Scene 4 (14-20s) — brand card: deep logo hit with reverb at 17.47s
- SFX selection guidance: use interface/click sounds for node completions, impact sounds for swarm launch and logo hit. Prefer low high-frequency-risk files for repeated elements.
- SFX analysis guidance: see `<skill-dir>/assets/sfx/sfx-analysis.md` and `sfx-analysis.json`
- Exact SFX choice: Hyperframes should choose filenames, timestamps, density, and volume based on the implemented animation.
- Audio files: copy the chosen music and any Hyperframes-selected SFX into `brag-output/composition/assets/`

## Hyperframes Instructions
Load the composition-building Hyperframes domain skills — `hyperframes-core` (composition contract + `data-*` timing), `hyperframes-animation` (motion), `hyperframes-creative` (design spec, beats, audio-reactive), `hyperframes-keyframes` (seek-safe keyframes), and `hyperframes-cli` (lint/check/render). /brag is its own workflow: do not enter the `hyperframes` entry-point intent interview and do not route into its generic promo / launch-video workflow. Prefer native Hyperframes conventions over anything in `/brag`.

Requirements:
- Show at least one real UI, copy, or visual element from the source project.
- Keep all text readable in the final render.
- Keep the video within 15-25 seconds.
- Include the planned music/SFX layer unless audio was explicitly disabled or documented as intentionally silent.
- Treat `/brag` audio notes as guidance, not a fixed cue sheet. Choose SFX after the visual animation exists.
- Treat music cue metadata as optional timing hints. Hyperframes decides exact animation timing and should ignore cues that hurt readability, scene pacing, or the product story.
- Major reveals may move toward nearby strong cues within about 0.15s. Smaller entrances may align to nearby beat points within about 0.10s. Use only 1-3 strong cue locks in a 15-25s video unless the edit clearly benefits from more.
- Use SFX to support motion and interaction: card sounds for card-like reveals, short announcement cues for major payoffs, key/click sounds for text or user actions, and restraint when the edit is already busy.
- Honor planned music treatment such as fade-outs, ducking, beat-aligned reveals, or letting a final SFX ring over the music, using the best Hyperframes-supported implementation.
- When music is present and the treatment is not `none`, consider Hyperframes audio-reactive workflow: extract audio data and use RMS/frequency bands for subtle, brand-specific motion. Good targets are glow, depth, background warmth, card presence, title emphasis, or other existing visual elements. Avoid waveform/equalizer visuals, musical-note graphics, generic particle systems, strobing, or heavy pulsing.
- Use local assets for audio and any required runtime/media dependencies when possible.
- Run `hyperframes check` before render — it is brag's single gate.
