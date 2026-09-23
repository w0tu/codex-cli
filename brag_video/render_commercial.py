import sys
import os
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
HEIGHT = 1080
FPS = 30
TOTAL_FRAMES = 900 # 30 seconds * 30 fps

# Fonts
FONT_MONO = "/home/feds/.local/share/fonts/JetBrainsMono/JetBrainsMonoNLNerdFontMono-SemiBold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SANS_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

font_title_huge = ImageFont.truetype(FONT_SANS, 64)
font_title_large = ImageFont.truetype(FONT_SANS, 48)
font_title_med = ImageFont.truetype(FONT_SANS, 34)
font_mono_large = ImageFont.truetype(FONT_MONO, 28)
font_mono_med = ImageFont.truetype(FONT_MONO, 22)
font_mono_small = ImageFont.truetype(FONT_MONO, 17)
font_caption = ImageFont.truetype(FONT_SANS, 26)

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# Color palette
BG_DARK = (10, 11, 16)
BG_CARD = (20, 22, 32)
BORDER_COL = (45, 50, 70)
CYAN = (56, 189, 248)
EMERALD = (52, 211, 153)
PURPLE = (168, 85, 247)
ROSE = (244, 63, 94)
WHITE = (255, 255, 255)
GRAY = (156, 163, 175)
DARK_GRAY = (75, 85, 99)

def draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)

def render_frame(f):
    # Base canvas
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)
    t = f / FPS

    # Subtle ambient background grid & star glow
    for gx in range(0, WIDTH, 80):
        draw.line([(gx, 0), (gx, HEIGHT)], fill=(18, 20, 30), width=1)
    for gy in range(0, HEIGHT, 80):
        draw.line([(0, gy), (WIDTH, gy)], fill=(18, 20, 30), width=1)

    # ──────────────────────────────────────────────────────────
    # SCENE 1: 0.0s - 5.0s (Frames 0 - 149)
    # "You just spent 14 hours building something incredible..."
    # ──────────────────────────────────────────────────────────
    if f < 150:
        p = f / 150.0
        # Zoom scale effect
        box_w = int(1400 + p * 60)
        box_h = int(720 + p * 30)
        bx1 = (WIDTH - box_w) // 2
        by1 = 120
        bx2 = bx1 + box_w
        by2 = by1 + box_h

        # Terminal Window
        draw_rounded_rect(draw, [bx1, by1, bx2, by2], 18, fill=(13, 15, 22), outline=(40, 48, 68), width=2)
        
        # Window Header
        draw_rounded_rect(draw, [bx1, by1, bx2, by1 + 45], 18, fill=(22, 25, 38))
        draw.rectangle([bx1, by1 + 25, bx2, by1 + 45], fill=(22, 25, 38)) # flatten bottom corners
        draw.line([(bx1, by1 + 45), (bx2, by1 + 45)], fill=(40, 48, 68), width=1)

        # macOS traffic lights
        draw.ellipse([bx1 + 20, by1 + 15, bx1 + 34, by1 + 29], fill=(239, 68, 68))
        draw.ellipse([bx1 + 44, by1 + 15, bx1 + 58, by1 + 29], fill=(245, 158, 11))
        draw.ellipse([bx1 + 68, by1 + 15, bx1 + 82, by1 + 29], fill=(34, 197, 94))
        draw.text((bx1 + 105, by1 + 12), "zsh — developer@workstation: ~/saas-platform — 528 tok/s", font=font_mono_small, fill=GRAY)

        # Streaming code lines
        code_lines = [
            ("import asyncio, os, time, sys", CYAN),
            ("from fastapi import FastAPI, WebSocket, Depends", PURPLE),
            ("from pydantic import BaseModel, Field", PURPLE),
            ("from database.engine import async_session_factory", GRAY),
            ("", GRAY),
            ("app = FastAPI(title='Autonomous SaaS Engine', version='3.0.0')", EMERALD),
            ("@app.post('/api/v1/deploy')", CYAN),
            ("async def handle_deploy(payload: DeployRequest):", WHITE),
            ("    cluster = await Orchestrator.initialize_worker_nodes()", GRAY),
            ("    await cluster.verify_zero_downtime_tls()", GRAY),
            ("    return {'status': 'DEPLOYED_LIVE', 'latency_ms': 0.84}", EMERALD),
            ("", GRAY),
            ("# Zero-Trust Sandbox AST Verification Check passed (0 CVEs)", (100, 180, 100)),
            ("git add . && git commit -m 'feat: complete entire SaaS app'", CYAN),
        ]

        # Animate code scroll
        scroll_offset = int(f * 2.8) % 240
        start_y = by1 + 65 - (scroll_offset if f > 60 else 0)

        for i, (line, color) in enumerate(code_lines):
            ly = start_y + i * 36
            if by1 + 45 < ly < by2 - 40:
                draw.text((bx1 + 30, ly), line, font=font_mono_med, fill=color)

        # Big commit flash at frame 70+
        if f >= 65:
            cf_alpha = min(1.0, (f - 65) / 15.0)
            cbox_w = 900
            cbox_h = 130
            cbx1 = (WIDTH - cbox_w) // 2
            cby1 = by1 + 260
            cbx2 = cbx1 + cbox_w
            cby2 = cby1 + cbox_h

            draw_rounded_rect(draw, [cbx1, cby1, cbx2, cby2], 14, fill=(16, 26, 22), outline=EMERALD, width=2)
            draw.text((cbx1 + 30, cby1 + 25), "✓ [main 9f3a1c] feat: complete entire SaaS app", font=font_mono_large, fill=EMERALD)
            draw.text((cbx1 + 30, cby1 + 75), "18 files changed, 4,820 insertions(+), 0 deletions(-)", font=font_mono_med, fill=WHITE)

        # Bottom Caption Banner
        draw_rounded_rect(draw, [180, HEIGHT - 130, WIDTH - 180, HEIGHT - 50], 12, fill=(15, 17, 26), outline=(40, 48, 70), width=1)
        cap_text = "YOU JUST SPENT 14 HOURS BUILDING SOMETHING INCREDIBLE."
        draw.text((WIDTH // 2, HEIGHT - 92), cap_text, font=font_title_med, fill=WHITE, anchor="mm")

    # ──────────────────────────────────────────────────────────
    # SCENE 2: 5.0s - 11.0s (Frames 150 - 329)
    # "And nobody is going to see it. Because you hate making demo videos."
    # ──────────────────────────────────────────────────────────
    elif f < 330:
        p = (f - 150) / 180.0
        # Twitter composer window
        card_w = 1100
        card_h = 580
        cx1 = (WIDTH - card_w) // 2
        cy1 = 180
        cx2 = cx1 + card_w
        cy2 = cy1 + card_h

        # Slightly desaturated card
        draw_rounded_rect(draw, [cx1, cy1, cx2, cy2], 18, fill=(18, 20, 26), outline=(45, 48, 58), width=2)

        # Twitter user row
        draw.ellipse([cx1 + 40, cy1 + 40, cx1 + 100, cy1 + 100], fill=(45, 52, 65))
        draw.text((cx1 + 70, cy1 + 70), "DEV", font=font_mono_small, fill=WHITE, anchor="mm")

        draw.text((cx1 + 120, cy1 + 45), "Alex Builder", font=font_title_med, fill=(220, 220, 220))
        draw.text((cx1 + 120, cy1 + 82), "@alex_codes · 2m", font=font_mono_small, fill=DARK_GRAY)

        # Blank composer area
        blink = (f // 15) % 2 == 0
        prompt_str = "What is happening?!"
        draw.text((cx1 + 120, cy1 + 160), prompt_str, font=font_title_med, fill=(80, 85, 98))
        if blink:
            draw.line([(cx1 + 450, cy1 + 160), (cx1 + 450, cy1 + 195)], fill=(120, 130, 150), width=3)

        # Dummy post toolbar
        icons = ["🖼️ Media", "📊 Poll", "😊 Emoji", "📍 Location"]
        for j, ic in enumerate(icons):
            draw.text((cx1 + 120 + j * 160, cy1 + 470), ic, font=font_mono_small, fill=DARK_GRAY)

        # Disabled Post Button
        draw_rounded_rect(draw, [cx2 - 170, cy1 + 455, cx2 - 40, cy1 + 510], 25, fill=(35, 40, 50))
        draw.text((cx2 - 105, cy1 + 482), "Post", font=font_title_med, fill=(90, 95, 105), anchor="mm")

        # Big dramatic warning overlay
        if f >= 180:
            glow_y = HEIGHT - 240
            draw_rounded_rect(draw, [200, glow_y, WIDTH - 200, glow_y + 160], 16, fill=(24, 14, 18), outline=(220, 38, 38), width=2)
            draw.text((WIDTH // 2, glow_y + 50), "AND NOBODY IS GOING TO SEE IT.", font=font_title_huge, fill=(248, 113, 113), anchor="mm")
            draw.text((WIDTH // 2, glow_y + 115), "Because you hate making demo videos.", font=font_title_med, fill=WHITE, anchor="mm")

    # ──────────────────────────────────────────────────────────
    # SCENE 3: 11.0s - 18.0s (Frames 330 - 539)
    # "Stop shipping in silence. Meet Brag."
    # ──────────────────────────────────────────────────────────
    elif f < 540:
        p = (f - 330) / 210.0
        # Bass drop neon shockwave
        if f < 360:
            sw_r = int((f - 330) * 45)
            draw.ellipse([WIDTH//2 - sw_r, HEIGHT//2 - sw_r, WIDTH//2 + sw_r, HEIGHT//2 + sw_r], outline=(CYAN[0], CYAN[1], CYAN[2]), width=3)

        # Hero Header
        draw.text((WIDTH // 2, 85), "STOP SHIPPING IN SILENCE.", font=font_title_huge, fill=CYAN, anchor="mm")
        draw.text((WIDTH // 2, 155), "Meet Brag — The 1-Command Launch Video Studio", font=font_title_large, fill=WHITE, anchor="mm")

        # Terminal Card
        term_w = 1200
        term_h = 580
        tx1 = (WIDTH - term_w) // 2
        ty1 = 220
        tx2 = tx1 + term_w
        ty2 = ty1 + term_h

        draw_rounded_rect(draw, [tx1, ty1, tx2, ty2], 18, fill=(12, 14, 22), outline=CYAN, width=2)

        # Header bar
        draw_rounded_rect(draw, [tx1, ty1, tx2, ty1 + 45], 18, fill=(20, 24, 38))
        draw.rectangle([tx1, ty1 + 25, tx2, ty1 + 45], fill=(20, 24, 38))
        draw.ellipse([tx1 + 20, ty1 + 15, tx1 + 34, ty1 + 29], fill=(239, 68, 68))
        draw.ellipse([tx1 + 44, ty1 + 15, tx1 + 58, ty1 + 29], fill=(245, 158, 11))
        draw.ellipse([tx1 + 68, ty1 + 15, tx1 + 82, ty1 + 29], fill=(34, 197, 94))
        draw.text((tx1 + 105, ty1 + 12), "cdx-cli — /brag pipeline", font=font_mono_small, fill=GRAY)

        # Typing out command
        cmd_text = "❯ /brag"
        draw.text((tx1 + 40, ty1 + 80), cmd_text, font=font_mono_large, fill=CYAN)

        # Pipeline progress items
        tasks = [
            ("✦ Analyzing Git Diff, AST Components & Hero Screens...", 360, EMERALD),
            ("✦ Synthesizing Neural Voiceover with Kokoro TTS...", 400, PURPLE),
            ("✦ Hyperframes Compositor: 60 FPS 1080p Canvas Engine...", 440, CYAN),
            ("✦ Finalizing Synchronized Sound Design & Bass Drop...", 480, (250, 204, 21)),
        ]

        for idx, (task_str, trigger_f, col) in enumerate(tasks):
            if f >= trigger_f:
                py = ty1 + 150 + idx * 60
                draw.text((tx1 + 50, py), task_str, font=font_mono_med, fill=col)
                # Checkmark
                draw.text((tx2 - 120, py), "[ DONE ]", font=font_mono_med, fill=EMERALD)

        # Audio Waveform spikes at bottom of terminal
        wave_y = ty2 - 70
        for wx in range(tx1 + 40, tx2 - 40, 14):
            bar_h = int(12 + 35 * abs(math.sin(f * 0.35 + wx * 0.05)))
            draw.line([(wx, wave_y - bar_h // 2), (wx, wave_y + bar_h // 2)], fill=PURPLE, width=4)

        # Footer Badge
        draw_rounded_rect(draw, [WIDTH//2 - 250, HEIGHT - 110, WIDTH//2 + 250, HEIGHT - 55], 25, fill=(25, 20, 45), outline=PURPLE, width=2)
        draw.text((WIDTH // 2, HEIGHT - 82), "✦ Zero Video Editing Skills Required", font=font_mono_med, fill=WHITE, anchor="mm")

    # ──────────────────────────────────────────────────────────
    # SCENE 4: 18.0s - 25.0s (Frames 540 - 749)
    # "One command turns your codebase, commits, and diffs into a studio-grade launch video..."
    # ──────────────────────────────────────────────────────────
    elif f < 750:
        p = (f - 540) / 210.0
        # Title
        draw.text((WIDTH // 2, 70), "ONE COMMAND. FULL LAUNCH VIDEO.", font=font_title_huge, fill=WHITE, anchor="mm")
        draw.text((WIDTH // 2, 130), "Studio-Grade Motion Design · Synchronized Audio · Instant MP4", font=font_title_med, fill=CYAN, anchor="mm")

        # Two split cards
        card_w = 720
        card_h = 620
        y_top = 180

        # Left Card: Codebase & Diff
        lx1 = 160
        lx2 = lx1 + card_w
        draw_rounded_rect(draw, [lx1, y_top, lx2, y_top + card_h], 18, fill=(14, 16, 24), outline=(45, 55, 75), width=2)
        draw_rounded_rect(draw, [lx1, y_top, lx2, y_top + 45], 18, fill=(22, 26, 40))
        draw.text((lx1 + 25, y_top + 12), "Codebase Diff & AST Analysis", font=font_mono_small, fill=GRAY)

        diff_items = [
            ("+++ src/components/Dashboard.tsx", EMERALD),
            ("+ export function LiveAnalytics() {", CYAN),
            ("+   const [stats] = useRealtimeFeed();", WHITE),
            ("+   return (", WHITE),
            ("+     <div className='glow-card'>", PURPLE),
            ("+       <Chart data={stats.latency} />", (100, 220, 240)),
            ("+     </div>", PURPLE),
            ("+   );", WHITE),
            ("+ }", CYAN),
            ("--- /dev/null", DARK_GRAY),
            ("+++ tests/test_performance.py (100% PASS)", EMERALD),
        ]
        for di, (d_line, d_col) in enumerate(diff_items):
            draw.text((lx1 + 30, y_top + 70 + di * 34), d_line, font=font_mono_small, fill=d_col)

        # Right Card: Rendered Video Studio Preview
        rx1 = WIDTH - 160 - card_w
        rx2 = rx1 + card_w
        draw_rounded_rect(draw, [rx1, y_top, rx2, y_top + card_h], 18, fill=(16, 18, 28), outline=PURPLE, width=2)
        draw_rounded_rect(draw, [rx1, y_top, rx2, y_top + 45], 18, fill=(28, 22, 45))
        draw.text((rx1 + 25, y_top + 12), "Hyperframes Launch Video Preview (60 FPS)", font=font_mono_small, fill=PURPLE)

        # Inner Preview Screen
        px1 = rx1 + 30
        py1 = y_top + 65
        px2 = rx2 - 30
        py2 = py1 + 330
        draw_rounded_rect(draw, [px1, py1, px2, py2], 12, fill=(8, 10, 16), outline=(50, 40, 70), width=1)
        
        # Draw mock video content inside preview
        draw.text(((px1 + px2)//2, py1 + 90), "brag", font=font_title_large, fill=WHITE, anchor="mm")
        draw.text(((px1 + px2)//2, py1 + 155), "AUTONOMOUS LAUNCH VIDEO", font=font_mono_med, fill=CYAN, anchor="mm")
        draw.text(((px1 + px2)//2, py1 + 210), "1080p · 60fps · Sound Design", font=font_caption, fill=EMERALD, anchor="mm")

        # Timeline Tracks beneath video
        tly = py2 + 25
        track_names = ["🎬 Video Motion Track", "🎙️ Kokoro Voiceover", "🎵 Future Bass Audio"]
        track_cols = [CYAN, PURPLE, EMERALD]
        for ti, (t_name, t_col) in enumerate(zip(track_names, track_cols)):
            draw_rounded_rect(draw, [px1, tly + ti * 55, px2, tly + ti * 55 + 40], 8, fill=(20, 24, 36), outline=t_col, width=1)
            draw.text((px1 + 15, tly + ti * 55 + 10), t_name, font=font_mono_small, fill=WHITE)
            # Animated playhead bar
            playhead_x = px1 + 260 + int((f * 3.5) % (px2 - px1 - 280))
            draw.line([(playhead_x, tly + ti * 55 + 5), (playhead_x, tly + ti * 55 + 35)], fill=(255, 255, 255), width=2)

        # Bottom Feature Pill
        draw_rounded_rect(draw, [WIDTH//2 - 300, HEIGHT - 110, WIDTH//2 + 300, HEIGHT - 55], 25, fill=(18, 25, 38), outline=CYAN, width=1)
        draw.text((WIDTH // 2, HEIGHT - 82), "✦ AST Parser + Kokoro TTS + Motion Graphics Compositor", font=font_mono_med, fill=WHITE, anchor="mm")

    # ──────────────────────────────────────────────────────────
    # SCENE 5: 25.0s - 30.0s (Frames 750 - 899)
    # "You built it. Now brag. Run /brag in your terminal today."
    # ──────────────────────────────────────────────────────────
    else:
        p = (f - 750) / 150.0
        
        # Social Proof Cards Floating
        sp_x = 220
        sp_y = 160
        draw_rounded_rect(draw, [sp_x, sp_y, sp_x + 420, sp_y + 220], 16, fill=(18, 20, 30), outline=(45, 50, 70), width=1)
        draw.text((sp_x + 25, sp_y + 30), "launch.mp4", font=font_mono_med, fill=EMERALD)
        draw.text((sp_x + 25, sp_y + 70), "1080p 60fps · 18.4 MB", font=font_mono_small, fill=GRAY)
        draw.text((sp_x + 25, sp_y + 120), "❤️ 12.4K  🔄 3.8K  💬 942", font=font_title_med, fill=WHITE)
        draw.text((sp_x + 25, sp_y + 175), "Top Trending on X & GitHub", font=font_mono_small, fill=CYAN)

        # Main Brand Hero Card
        bx = WIDTH // 2 + 50
        by = 130
        bw = 640
        bh = 720
        draw_rounded_rect(draw, [bx, by, bx + bw, by + bh], 22, fill=(14, 16, 26), outline=PURPLE, width=2)

        # Brag Logo
        draw.text((bx + bw // 2, by + 100), "✦ brag", font=font_title_huge, fill=WHITE, anchor="mm")
        draw.text((bx + bw // 2, by + 180), "You built it. Now brag.", font=font_title_large, fill=CYAN, anchor="mm")
        draw.text((bx + bw // 2, by + 235), "Turn any codebase into a viral launch video", font=font_mono_med, fill=GRAY, anchor="mm")

        # Command Box
        cbx1 = bx + 40
        cby1 = by + 300
        cbx2 = bx + bw - 40
        cby2 = cby1 + 80
        draw_rounded_rect(draw, [cbx1, cby1, cbx2, cby2], 12, fill=(8, 10, 18), outline=EMERALD, width=2)
        draw.text(((cbx1 + cbx2)//2, (cby1 + cby2)//2), "npx @latent-spaces/brag", font=font_mono_large, fill=EMERALD, anchor="mm")

        # Second Command Box
        c2by1 = cby2 + 25
        c2by2 = c2by1 + 80
        draw_rounded_rect(draw, [cbx1, c2by1, cbx2, c2by2], 12, fill=(8, 10, 18), outline=CYAN, width=2)
        draw.text(((cbx1 + cbx2)//2, (c2by1 + c2by2)//2), "cdx --brag  (or /brag in REPL)", font=font_mono_large, fill=CYAN, anchor="mm")

        # GitHub URL
        draw.text((bx + bw // 2, by + 560), "github.com/latent-spaces/brag", font=font_mono_large, fill=WHITE, anchor="mm")
        draw.text((bx + bw // 2, by + 640), "Created by Saad Kashif & The Codex Group", font=font_mono_small, fill=DARK_GRAY, anchor="mm")

        # Floating left badges
        badge_y = sp_y + 260
        badges = [
            ("🚀 Automatic AST & Diff Analysis", EMERALD),
            ("🎙️ Multi-Voice Kokoro TTS Engine", PURPLE),
            ("📱 16:9 & 9:16 Shorts/Reels Support", CYAN),
            ("⚡ Zero Dependencies: Instant Preview", (250, 204, 21)),
        ]
        for bi, (b_txt, b_c) in enumerate(badges):
            draw_rounded_rect(draw, [sp_x, badge_y + bi * 65, sp_x + 420, badge_y + bi * 65 + 48], 10, fill=(16, 18, 28), outline=b_c, width=1)
            draw.text((sp_x + 20, badge_y + bi * 65 + 14), b_txt, font=font_mono_small, fill=WHITE)

    return img

def main():
    print(f"Starting commercial render: {TOTAL_FRAMES} frames ({TOTAL_FRAMES/FPS}s) at {WIDTH}x{HEIGHT}...")
    
    # Setup ffmpeg process reading rawvideo from stdin and muxing master_audio.aac
    ffmpeg_cmd = [
        "/home/feds/.local/bin/ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-", # stdin
        "-i", "brag_video/master_audio.aac",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-shortest",
        "brag_video/brag_commercial_30s.mp4"
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    for frame_idx in range(TOTAL_FRAMES):
        if frame_idx % 60 == 0:
            print(f"Rendering frame {frame_idx}/{TOTAL_FRAMES} ({(frame_idx/FPS):.1f}s)...")
        img = render_frame(frame_idx)
        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    proc.wait()
    print("Render complete: brag_video/brag_commercial_30s.mp4")

if __name__ == '__main__':
    main()
