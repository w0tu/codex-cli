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
    """Stream chat responses in real-time token-by-token using chunked transfer encoding."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    user_prompt = data.get("prompt", "").strip()
    if not user_prompt:
        return web.Response(text="Empty prompt provided.", status=400)

    messages = [
        {"role": "system", "content": get_system_prompt(lean=True)},
        {"role": "user", "content": user_prompt}
    ]

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
            for chunk in desktop_client.stream_chat(messages, max_tokens=2048):
                loop.call_soon_threadsafe(queue.put_nowait, chunk)
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
        await response.write(chunk.encode("utf-8"))

    await response.write_eof()
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


def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/api/status", status_handler)
    app.router.add_get("/api/usage", usage_handler)
    app.router.add_post("/api/model", model_handler)
    app.router.add_post("/api/chat", chat_stream_handler)
    app.router.add_post("/api/mouse", mouse_handler)
    app.router.add_get("/api/files", files_get_handler)
    app.router.add_post("/api/files", files_post_handler)
    app.router.add_get("/api/wifi", wifi_handler)
    app.router.add_get("/api/research", research_handler)
    app.router.add_post("/api/antigravity", antigravity_handler)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="127.0.0.1", port=4545)
