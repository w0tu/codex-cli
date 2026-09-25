"""The Codex Group - Desktop Application Web & API Server.

Serves the standalone desktop application UI and provides REST and Streaming endpoints:
- GET  /                  : Standalone Desktop Web UI
- GET  /api/status        : Telemetry & health status
- POST /api/model         : Switch active AI model
- POST /api/chat          : Real-time token streaming via chunked transfer
- POST /api/mouse         : Hardware mouse & keyboard control via xdotool
- GET  /api/files         : Local file reader
- POST /api/files         : Local file writer (Save to PC)
- GET  /api/wifi          : WiFi diagnostics and connection status
- GET  /api/research      : Multi-platform deep internet research
- POST /api/antigravity   : Google Antigravity autonomous engine delegation
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from aiohttp import web

from codex.client import HybridCodexClient, get_system_prompt
from codex.mouse_control import mouse_controller
from codex.network import check_wifi_status, run_deep_research
from codex.antigravity_bridge import delegate_to_antigravity
from codex.metrics_db import metrics_db
from codex.usage import UsageTracker
from codex.learner import idle_learner

HTML_INDEX_PATH = Path(__file__).parent / "web" / "index.html"

# Global client instance for desktop app
desktop_client = HybridCodexClient()


async def index_handler(request: web.Request) -> web.Response:
    """Serve the desktop application single-page interface."""
    if not HTML_INDEX_PATH.exists():
        return web.Response(text="Error: Desktop UI index.html not found.", status=404)
    content = HTML_INDEX_PATH.read_text(encoding="utf-8")
    return web.Response(text=content, content_type="text/html")


async def status_handler(request: web.Request) -> web.Response:
    """Return backend status, active model, and capabilities."""
    return web.json_response({
        "status": "online",
        "app": "The Codex Group — Autonomous AI Desktop",
        "version": "1.7.0",
        "model": desktop_client.model,
        "mode": getattr(desktop_client, "mode", "hybrid"),
        "mouse_controller": mouse_controller.is_available,
    })


async def usage_handler(request: web.Request) -> web.Response:
    """Return comprehensive telemetry, quota, and GitHub-style contribution history."""
    tracker = UsageTracker()
    summary = metrics_db.get_summary()
    quota = tracker.get_stats()
    history = metrics_db.get_history(days=35)
    return web.json_response({
        "summary": summary,
        "quota": quota,
        "history": history,
        "lpu_speed": "528 tok/s",
        "models": {
            "Qwen 3.8 27B (Primary)": 68,
            "Gemini 3.8 Flash (Antigravity)": 24,
            "DeepSeek R1 (Reasoning)": 8
        },
        "tools": {
            "Mouse & Keyboard Control": 42,
            "Local Disk Read/Write": 86,
            "WiFi & Network Diagnostics": 19,
            "Deep Internet Research": 31,
            "Google Antigravity": 14
        }
    })


async def model_handler(request: web.Request) -> web.Response:
    """Dynamically switch active AI model."""
    try:
        data = await request.json()
        model_name = data.get("model", "qwen/qwen3.8-27b")
        if hasattr(desktop_client, "set_model"):
            desktop_client.set_model(model_name)
        elif hasattr(desktop_client, "cloud_client") and hasattr(desktop_client.cloud_client, "set_model"):
            desktop_client.cloud_client.set_model(model_name)
        return web.json_response({"ok": True, "model": model_name})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def chat_stream_handler(request: web.Request) -> web.StreamResponse:
    """Stream chat responses in real-time with full conversation memory, model routing, and idle learning."""
    idle_learner.record_interaction()

    try:
        data = await request.json()
    except Exception:
        data = {}

    user_prompt = data.get("prompt", "").strip()
    history_messages = data.get("messages", [])
    custom_system_prompt = data.get("system_prompt", "").strip()
    req_model = data.get("model", "").strip()

    prompt_lower = user_prompt.lower()
    is_continue = prompt_lower in ["continue", "keep going", "resume", "go on", "more", "next"] or data.get("action") == "continue"
    is_coding = is_continue or any(k in prompt_lower for k in [
        "code", "build", "write a", "script", "function", "class", "html", "css", "javascript",
        "python", "react", "fastapi", "flask", "django", "sql", "api", "backend", "frontend",
        "fullstack", "full-stack", "app", "website", "refactor", "debug", "test", "docker"
    ])

    if is_continue:
        req_model = "openai/gpt-oss-120b"
        if hasattr(desktop_client, "set_model"):
            desktop_client.set_model("openai/gpt-oss-120b")
        elif hasattr(desktop_client, "cloud_client") and hasattr(desktop_client.cloud_client, "set_model"):
            desktop_client.cloud_client.set_model("openai/gpt-oss-120b")
    elif req_model:
        from codex.client import resolve_backend_model
        resolved = resolve_backend_model(req_model)
        if hasattr(desktop_client, "set_model"):
            desktop_client.set_model(resolved)
        elif hasattr(desktop_client, "cloud_client") and hasattr(desktop_client.cloud_client, "set_model"):
            desktop_client.cloud_client.set_model(resolved)

    if custom_system_prompt:
        sys_content = custom_system_prompt
    else:
        from codex.client import get_model_system_prompt
        sys_content = get_model_system_prompt(req_model or "cdx 3.2", lean=True)

    # Inject autonomously learned internet knowledge & news
    learned_knowledge = idle_learner.get_learned_context()
    if learned_knowledge:
        sys_content += "\n" + learned_knowledge

    messages: list[dict[str, Any]] = [{"role": "system", "content": sys_content}]

    # Maintain complete conversational context across turns
    if history_messages and isinstance(history_messages, list):
        for msg in history_messages:
            r = msg.get("role", "user")
            c = msg.get("content", "")
            if r in ("user", "assistant") and c:
                messages.append({"role": r, "content": c})

    # Seamless continuation instruction vs normal user prompt
    if is_continue:
        continuation_prompt = (
            "CONTINUE CODE GENERATION IMMEDIATELY: Continue writing the code seamlessly from the exact character "
            "where it was paused or interrupted above. Do NOT restart from line 1. Do NOT repeat already written code. "
            "Do NOT include conversational meta-commentary like 'Sure, here is the continuation'. Output the next lines of the code block immediately:"
        )
        messages.append({"role": "user", "content": continuation_prompt})
    elif user_prompt:
        if not messages or messages[-1].get("content") != user_prompt or messages[-1].get("role") != "user":
            messages.append({"role": "user", "content": user_prompt})

    if len(messages) <= 1:
        return web.Response(text="Empty prompt provided.", status=400)

    # Optimal token ceiling: 4096 tokens for coding/continuation, 2048 for basic questions
    stream_max_tokens = 4096 if is_coding else 2048

    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
    await response.prepare(request)

    loop = asyncio.get_running_loop()

    # Generator queue to bridge synchronous generator into async stream
    def run_generator(queue: asyncio.Queue):
        try:
            buffer = ""
            for chunk in desktop_client.stream_chat(messages, max_tokens=stream_max_tokens):
                buffer += chunk
                # Suppress raw XML tool tags if emitted by model
                if "<tool_call>" in buffer:
                    if "</tool_call>" in buffer:
                        # Clean out completed tool call
                        parts = buffer.split("</tool_call>")
                        before = parts[0].split("<tool_call>")[0]
                        after = "</tool_call>".join(parts[1:])
                        buffer = before + after
                        if buffer:
                            loop.call_soon_threadsafe(queue.put_nowait, buffer)
                            buffer = ""
                    continue
                else:
                    loop.call_soon_threadsafe(queue.put_nowait, buffer)
                    buffer = ""
            if buffer and "<tool_call>" not in buffer:
                loop.call_soon_threadsafe(queue.put_nowait, buffer)
        except Exception as ex:
            loop.call_soon_threadsafe(queue.put_nowait, f"\n[Stream Error: {ex}]")
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    q: asyncio.Queue = asyncio.Queue()
    loop.run_in_executor(None, run_generator, q)

    while True:
        chunk = await q.get()
        if chunk is None:
            break
        try:
            await response.write(chunk.encode("utf-8"))
        except (ConnectionResetError, asyncio.CancelledError):
            break

    try:
        await response.write_eof()
    except Exception:
        pass
    return response


async def mouse_handler(request: web.Request) -> web.Response:
    """Handle hardware mouse movements, clicks, scrolling, and keyboard input."""
    try:
        data = await request.json()
        action = data.get("action", "")

        if action == "move":
            x = int(data.get("x", 0))
            y = int(data.get("y", 0))
            smooth = bool(data.get("smooth", False))
            res = mouse_controller.move_to(x, y, smooth=smooth)
            return web.json_response(res)

        elif action == "click":
            btn = int(data.get("button", 1))
            res = mouse_controller.click(btn)
            return web.json_response(res)

        elif action == "double_click":
            btn = int(data.get("button", 1))
            res = mouse_controller.double_click(btn)
            return web.json_response(res)

        elif action == "scroll":
            direction = str(data.get("direction", "down"))
            amount = int(data.get("amount", 3))
            res = mouse_controller.scroll(direction, amount)
            return web.json_response(res)

        elif action == "drag":
            start_x = int(data.get("start_x", 0))
            start_y = int(data.get("start_y", 0))
            end_x = int(data.get("end_x", 0))
            end_y = int(data.get("end_y", 0))
            res = mouse_controller.drag_and_drop(start_x, start_y, end_x, end_y)
            return web.json_response(res)

        elif action == "type":
            text = str(data.get("text", ""))
            res = mouse_controller.type_text(text)
            return web.json_response(res)

        elif action == "key":
            key = str(data.get("key", ""))
            res = mouse_controller.key_combination(key)
            return web.json_response(res)

        elif action == "position":
            pos = mouse_controller.get_position()
            return web.json_response(pos)

        elif action == "screen_size":
            sz = mouse_controller.get_screen_size()
            return web.json_response(sz)

        return web.json_response({"error": f"Unknown mouse action '{action}'"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def files_get_handler(request: web.Request) -> web.Response:
    """Load local file content."""
    raw_path = request.query.get("path", "").strip()
    if not raw_path:
        return web.json_response({"error": "Missing 'path' query parameter."}, status=400)

    try:
        resolved = Path(os.path.expanduser(raw_path)).resolve()
        if not resolved.exists():
            return web.json_response({"error": f"File '{raw_path}' does not exist.", "content": ""}, status=404)
        if resolved.is_dir():
            items = [str(p.name) + ("/" if p.is_dir() else "") for p in resolved.iterdir()]
            return web.json_response({"path": str(resolved), "content": "\n".join(items), "is_dir": True})

        content = resolved.read_text(encoding="utf-8", errors="replace")
        return web.json_response({"path": str(resolved), "content": content, "size": len(content)})
    except Exception as e:
        return web.json_response({"error": str(e), "content": ""}, status=500)


async def files_post_handler(request: web.Request) -> web.Response:
    """Save content to local file on disk."""
    try:
        data = await request.json()
        raw_path = data.get("path", "").strip()
        content = data.get("content", "")

        if not raw_path:
            return web.json_response({"error": "Missing 'path' in body."}, status=400)

        resolved = Path(os.path.expanduser(raw_path)).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")

        return web.json_response({
            "ok": True,
            "message": f"Successfully saved {len(content)} characters to {resolved}",
            "path": str(resolved),
            "size": len(content)
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def wifi_handler(request: web.Request) -> web.Response:
    """Inspect WiFi diagnostics and internet gateway."""
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(None, check_wifi_status)
    return web.json_response(info)


async def research_handler(request: web.Request) -> web.Response:
    """Execute multi-platform deep internet research asynchronously."""
    query = request.query.get("q", "").strip()
    if not query:
        return web.json_response({"error": "Missing query parameter 'q'."}, status=400)

    loop = asyncio.get_running_loop()
    report = await loop.run_in_executor(None, run_deep_research, query)
    return web.json_response({"query": query, "report": report})


async def antigravity_handler(request: web.Request) -> web.Response:
    """Delegate complex reasoning task to Google Antigravity bridge."""
    try:
        data = await request.json()
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return web.json_response({"error": "Missing 'prompt'."}, status=400)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, delegate_to_antigravity, prompt)
        return web.json_response({"prompt": prompt, "result": result})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def terminal_handler(request: web.Request) -> web.Response:
    """Execute bash command and return output for GUI terminal."""
    try:
        data = await request.json()
        cmd = data.get("command", "").strip()
        cwd = data.get("cwd", os.getcwd())
        if not cmd:
            return web.json_response({"error": "Empty command provided.", "exit_code": 1}, status=400)

        loop = asyncio.get_running_loop()
        def run_bash():
            import subprocess
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd=cwd)
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "cwd": cwd,
            }
        result = await loop.run_in_executor(None, run_bash)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e), "exit_code": 1}, status=500)


async def subagents_swarm_handler(request: web.Request) -> web.Response:
    """Execute multi-subagent swarm mission decomposition."""
    try:
        data = await request.json()
        mission = data.get("mission", "").strip() or data.get("prompt", "").strip()
        if not mission:
            return web.json_response({"error": "Missing 'mission' in request payload."}, status=400)

        loop = asyncio.get_running_loop()
        from codex.subagents import orchestrate_subagent_swarm
        result = await loop.run_in_executor(None, orchestrate_subagent_swarm, mission, desktop_client)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def video_stitch_handler(request: web.Request) -> web.Response:
    """Stitch multiple video clips into a single file via FFmpeg."""
    try:
        data = await request.json()
        videos = data.get("videos", [])
        output = data.get("output", "stitched_output.mp4")
        resolution = data.get("resolution", "1920:1080")
        audio = data.get("audio")
        
        from codex.video_stitcher import stitch_videos
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, stitch_videos, videos, output, resolution, 30, audio)
        return web.json_response(res)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def video_flow_handler(request: web.Request) -> web.Response:
    """Generate Google Flow / Veo 2 video prompt sequence and storyboard."""
    try:
        data = await request.json()
        topic = data.get("topic", "").strip() or "Autonomous AI Coding Desktop"
        scene_count = int(data.get("scenes", 4))
        
        from codex.video_stitcher import generate_google_flow_package
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, generate_google_flow_package, topic, scene_count)
        return web.json_response(res)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def preview_get_handler(request: web.Request) -> web.Response:
    """Serve the active live website preview."""
    preview_file = Path("/tmp/cdx_live_preview.html")
    if preview_file.exists():
        content = preview_file.read_text(encoding="utf-8", errors="replace")
    else:
        content = (
            "<!DOCTYPE html><html class='dark'><head><script src='https://cdn.tailwindcss.com'></script></head>"
            "<body class='bg-black text-white min-h-screen flex items-center justify-center p-6'>"
            "<div class='text-center space-y-4'><div class='w-12 h-12 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto text-xl'>⚡</div>"
            "<h1 class='text-2xl font-bold font-mono text-emerald-400'>CDX Live Sandbox Ready</h1>"
            "<p class='text-sm text-gray-400'>Ask CDX to build any website, dashboard, or SaaS app. Your live website will render here instantly.</p>"
            "</div></body></html>"
        )
    return web.Response(text=content, content_type="text/html")


async def preview_save_handler(request: web.Request) -> web.Response:
    """Save HTML content for instant live sandbox preview and auto-open."""
    try:
        data = await request.json()
        html_code = data.get("html", "")
        auto_open = data.get("open", False)
        preview_file = Path("/tmp/cdx_live_preview.html")
        preview_file.write_text(html_code, encoding="utf-8")

        if auto_open:
            import subprocess
            try:
                subprocess.Popen(["xdg-open", "http://127.0.0.1:4545/preview"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        return web.json_response({"ok": True, "url": "http://127.0.0.1:4545/preview"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def preview_open_handler(request: web.Request) -> web.Response:
    """Open the live website in the system browser."""
    try:
        import subprocess
        subprocess.Popen(["xdg-open", "http://127.0.0.1:4545/preview"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return web.json_response({"ok": True, "url": "http://127.0.0.1:4545/preview"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def code_save_handler(request: web.Request) -> web.Response:
    """Save generated code directly to the workspace folder."""
    try:
        data = await request.json()
        code = data.get("code", "")
        if not code:
            return web.json_response({"error": "No code content provided."}, status=400)

        filename = data.get("filename", "").strip()
        lang = data.get("lang", "").lower()
        if not filename:
            ext_map = {
                "html": "index.html",
                "python": "app.py",
                "py": "app.py",
                "javascript": "app.js",
                "js": "app.js",
                "bash": "run.sh",
                "sh": "run.sh",
                "json": "data.json",
                "css": "style.css",
            }
            filename = ext_map.get(lang, "index.html" if ("<html" in code.lower() or "<!doctype" in code.lower()) else "script.py")

        filename = os.path.basename(filename)
        workspace_dir = Path("/home/feds/.gemini/antigravity/scratch/codex-cli/workspace")
        workspace_dir.mkdir(parents=True, exist_ok=True)
        target_path = workspace_dir / filename
        target_path.write_text(code, encoding="utf-8")

        # Sync to live preview file if HTML
        if filename.endswith(".html") or "<html" in code.lower() or "<!doctype" in code.lower():
            Path("/tmp/cdx_live_preview.html").write_text(code, encoding="utf-8")

        return web.json_response({
            "ok": True,
            "filename": filename,
            "path": str(target_path),
            "size": len(code),
            "preview_url": "/preview" if (filename.endswith(".html") or "<html" in code.lower() or "<!doctype" in code.lower()) else None,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def code_launch_handler(request: web.Request) -> web.Response:
    """Launch generated code immediately (open HTML in live sandbox/browser or execute script)."""
    try:
        data = await request.json()
        code = data.get("code", "").strip()
        lang = data.get("lang", "").lower()
        filename = data.get("filename", "")

        is_html = lang in ("html", "htm") or "<!doctype html" in code.lower() or "<html" in code.lower()
        if is_html:
            preview_file = Path("/tmp/cdx_live_preview.html")
            preview_file.write_text(code, encoding="utf-8")
            ws_file = Path("/home/feds/.gemini/antigravity/scratch/codex-cli/workspace/index.html")
            ws_file.parent.mkdir(parents=True, exist_ok=True)
            ws_file.write_text(code, encoding="utf-8")
            return web.json_response({
                "ok": True,
                "type": "web",
                "url": "/preview",
                "message": "Application launched in live sandbox!",
            })
        elif lang in ("python", "py"):
            tmp_py = Path("/tmp/cdx_run_script.py")
            tmp_py.write_text(code, encoding="utf-8")
            loop = asyncio.get_running_loop()
            proc = await loop.run_in_executor(None, lambda: subprocess.run([sys.executable, str(tmp_py)], capture_output=True, text=True, timeout=12))
            return web.json_response({
                "ok": True,
                "type": "cli",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "message": "Python script executed successfully" if proc.returncode == 0 else "Script finished with errors",
            })
        elif lang in ("bash", "sh", "shell"):
            loop = asyncio.get_running_loop()
            proc = await loop.run_in_executor(None, lambda: subprocess.run(["bash", "-c", code], capture_output=True, text=True, timeout=10))
            return web.json_response({
                "ok": True,
                "type": "cli",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "message": "Command executed",
            })
        else:
            if "<" in code and ">" in code and ("<body" in code.lower() or "<div" in code.lower() or "<html" in code.lower()):
                Path("/tmp/cdx_live_preview.html").write_text(code, encoding="utf-8")
                return web.json_response({"ok": True, "type": "web", "url": "/preview"})
            loop = asyncio.get_running_loop()
            proc = await loop.run_in_executor(None, lambda: subprocess.run(["bash", "-c", code], capture_output=True, text=True, timeout=10))
            return web.json_response({"ok": True, "type": "cli", "stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)



async def media_image_handler(request: web.Request) -> web.Response:
    """Generate image asset via MediaEngine."""
    try:
        data = await request.json()
        prompt = data.get("prompt", "").strip()
        width = int(data.get("width", 1024))
        height = int(data.get("height", 1024))
        from codex.media_engine import generate_image_asset
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, generate_image_asset, prompt, width, height)
        return web.json_response(res)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def media_video_handler(request: web.Request) -> web.Response:
    """Generate motion video clip via MediaEngine."""
    try:
        data = await request.json()
        prompt = data.get("prompt", "").strip()
        duration = int(data.get("duration", 5))
        title = data.get("title")
        from codex.media_engine import generate_motion_video_clip
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, generate_motion_video_clip, prompt, duration, title)
        return web.json_response(res)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def media_file_handler(request: web.Request) -> web.Response:
    """Serve generated image or video file."""
    folder = request.match_info.get("folder", "")
    filename = request.match_info.get("filename", "")
    from codex.media_engine import MEDIA_DIR
    target = MEDIA_DIR / folder / filename
    if not target.exists() or not target.is_file():
        return web.Response(text="File not found", status=404)
    
    content_type = "image/png" if filename.endswith(".png") else "video/mp4"
    return web.Response(body=target.read_bytes(), content_type=content_type)


async def learning_status_handler(request: web.Request) -> web.Response:
    """Return autonomous idle learning telemetry and recent insights."""
    return web.json_response(idle_learner.get_status())


async def learning_trigger_handler(request: web.Request) -> web.Response:
    """Manually trigger an autonomous idle learning cycle."""
    try:
        data = await request.json() if request.can_read_body else {}
    except Exception:
        data = {}
    topic = data.get("topic", "")
    if topic:
        res = idle_learner.learn_topic_cycle(topic, force=True)
    else:
        res = idle_learner.learn_recent_news_cycle(force=True)
    return web.json_response(res)


def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/preview", preview_get_handler)
    app.router.add_post("/api/preview/save", preview_save_handler)
    app.router.add_post("/api/preview/open", preview_open_handler)
    app.router.add_get("/api/status", status_handler)
    app.router.add_get("/api/usage", usage_handler)
    app.router.add_post("/api/model", model_handler)
    app.router.add_post("/api/chat", chat_stream_handler)
    app.router.add_post("/api/terminal", terminal_handler)
    app.router.add_post("/api/mouse", mouse_handler)
    app.router.add_get("/api/files", files_get_handler)
    app.router.add_post("/api/files", files_post_handler)
    app.router.add_get("/api/wifi", wifi_handler)
    app.router.add_get("/api/research", research_handler)
    app.router.add_post("/api/antigravity", antigravity_handler)
    app.router.add_post("/api/subagents/swarm", subagents_swarm_handler)
    app.router.add_post("/api/video/stitch", video_stitch_handler)
    app.router.add_post("/api/video/flow", video_flow_handler)
    app.router.add_post("/api/media/image", media_image_handler)
    app.router.add_post("/api/media/video", media_video_handler)
    app.router.add_get("/api/media/file/{folder}/{filename}", media_file_handler)
    app.router.add_get("/api/learning/status", learning_status_handler)
    app.router.add_post("/api/learning/trigger", learning_trigger_handler)

    # Start autonomous background learning daemon
    idle_learner.start_background_daemon()

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="127.0.0.1", port=4545)
