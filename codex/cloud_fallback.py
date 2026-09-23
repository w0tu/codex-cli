"""Cloaked Cloud Fallback Engine: OSS-120B High-Precision.

Disguises all remote escalation under the engine label 'OSS-120B High-Precision' or 'Cloud OSS-120B'.
Zero vendor leakage in logs, prompts, or UI frames.
Enforces the $2.00 daily budget limit via codex.billing.
"""

import os
import sys
import json
import time
import socket
from pathlib import Path
from typing import Any, Generator, Optional, Tuple

from codex.billing import billing_guardrail

CLOAKED_ENGINE_LABEL = "Cloud Native (GPT-OSS 120B)"
CLOAKED_CLOUD_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_CLOAKED_MODEL = "openai/gpt-oss-120b"


def is_internet_available(host: str = "8.8.8.8", port: int = 53, timeout: float = 1.2) -> bool:
    """Check whether host has an active network route."""
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def detect_query_complexity(prompt: str, context_tokens: int = 0) -> Tuple[bool, str]:
    """Determine whether a task exceeds 1B/3B parameter capacity.
    
    Escalation triggers:
    1. Multi-file refactoring requests
    2. Architecture & systems decomposition tasks
    3. Large context tokens (> 1200 tokens)
    4. Explicit requests for high-precision reasoning
    """
    text_lower = prompt.lower()

    if context_tokens > 1200:
        return True, f"Context tokens ({context_tokens}) exceed 1B model parameter ceiling"

    multi_file_indicators = [
        "multi-file", "refactor across", "entire codebase", "architecture",
        "system design", "monorepo", "migration", "overhaul",
        "across all files", "project structure", "dependency graph"
    ]
    for pattern in multi_file_indicators:
        if pattern in text_lower:
            return True, f"Detected high-complexity multi-file operation: '{pattern}'"

    # Count distinct file extensions or paths mentioned
    file_pattern_count = sum(text_lower.count(ext) for ext in [".py", ".ts", ".js", ".go", ".rs", ".cpp", ".c", ".h"])
    if file_pattern_count >= 3:
        return True, f"Detected multi-file scope ({file_pattern_count} target files referenced)"

    return False, "Query matches 1B local model capacity"


def resolve_cloud_credentials(api_key: Optional[str] = None, model: Optional[str] = None) -> Tuple[str, str, str]:
    """Resolve endpoint URL, bearer key, and model ID with strict zero-leakage cloaking."""
    req_model = (model or DEFAULT_CLOAKED_MODEL).lower()
    # Map virtual or external model IDs to available Groq / Cloud endpoints
    if "minimax" in req_model or "m2.7" in req_model:
        primary_groq_model = "minimax/minimax-m2.7"
    elif "20b" in req_model:
        primary_groq_model = "openai/gpt-oss-20b"
    elif "qwen" in req_model:
        primary_groq_model = "qwen/qwen3.8-27b"
    elif "120b" in req_model or "oss" in req_model or "gpt" in req_model or "pro" in req_model:
        primary_groq_model = "openai/gpt-oss-120b"
    else:
        primary_groq_model = "openai/gpt-oss-120b"  # Default flagship GPT 120B engine

    # Check for direct MiniMax API key if minimax model requested
    minimax_env = os.environ.get("MINIMAX_API_KEY", "").strip()
    if ("minimax" in req_model or "m2.7" in req_model) and minimax_env:
        return "https://api.minimax.chat/v1/text/chatcompletion_v2", minimax_env, "MiniMax-Text-01"

    if api_key:
        key = api_key.strip()
        if key.startswith("mm-") or key.startswith("minimax-"):
            return "https://api.minimax.chat/v1/text/chatcompletion_v2", key, "MiniMax-Text-01"
        elif key.startswith("gsk_"):
            return "https://api.groq.com/openai/v1/chat/completions", key, primary_groq_model
        elif key.startswith("xai-"):
            return "https://api.x.ai/v1/chat/completions", key, "grok-2-latest"
        elif key.startswith("sk-"):
            return "https://api.openai.com/v1/chat/completions", key, "gpt-4o-mini"
        return "https://api.groq.com/openai/v1/chat/completions", key, primary_groq_model

    # Check env vars
    groq_env = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_env:
        return "https://api.groq.com/openai/v1/chat/completions", groq_env, primary_groq_model

    # Check ~/.codex/config.json
    try:
        from codex.config import load_config
        cfg = load_config()
        for k in [cfg.get("api_key", "")] + cfg.get("backup_keys", []):
            if k and isinstance(k, str) and k.startswith("gsk_") and not k.startswith("gsk_test"):
                return "https://api.groq.com/openai/v1/chat/completions", k.strip(), primary_groq_model
    except Exception:
        pass

    xai_env = os.environ.get("XAI_API_KEY", "").strip()
    if xai_env:
        return "https://api.x.ai/v1/chat/completions", xai_env, "grok-2-latest"

    openai_env = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_env:
        return "https://api.openai.com/v1/chat/completions", openai_env, "gpt-4o-mini"

    return CLOAKED_CLOUD_URL, "", DEFAULT_CLOAKED_MODEL


def is_cloud_available() -> bool:
    """Return True if internet is up and a valid cloud key is configured."""
    if not is_internet_available():
        return False
    _, key, _ = resolve_cloud_credentials()
    return bool(key)


class CloakedCloudClient:
    """Zero-leakage remote inference client labeled strictly as 'Cloud Native (Zero-Latency)'."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY") or os.environ.get("XAI_API_KEY") or os.environ.get("CODEX_CLOUD_KEY") or ""
        self.engine_label = CLOAKED_ENGINE_LABEL
        self.model = DEFAULT_CLOAKED_MODEL

    def set_api_key(self, key: str) -> None:
        self.api_key = key.strip()

    def set_model(self, model: str) -> None:
        """Set cloud model preference."""
        if model:
            self.model = model

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Stream tokens directly from cloaked cloud endpoint token-by-token with zero buffering."""
        import httpx

        # Verify budget before starting
        allowed, notice = billing_guardrail.check_cloud_escalation()
        if not allowed:
            raise PermissionError(notice)

        prompt_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        prompt_tokens_est = max(1, len(prompt_text) // 4)
        completion_tokens_est = 0

        attempts = 2
        while attempts > 0:
            attempts -= 1
            endpoint_url, active_key, model_id = resolve_cloud_credentials(self.api_key, getattr(self, "model", None))
            if not active_key:
                raise RuntimeError("Cloud escalation key not found. Configure GROQ_API_KEY or XAI_API_KEY.")

            actual_max_tokens = max(max_tokens, 4096)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {active_key}",
            }
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": actual_max_tokens,
                "temperature": temperature,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if "gpt-oss" in model_id:
                payload["include_reasoning"] = False

            with httpx.Client(timeout=45.0) as client:
                with client.stream("POST", endpoint_url, json=payload, headers=headers) as response:
                    if response.status_code == 429 and attempts > 0:
                        from codex.config import rotate_api_key
                        new_k = rotate_api_key()
                        if new_k:
                            self.api_key = new_k
                            continue
                    if response.status_code != 200:
                        body = response.read().decode("utf-8", errors="replace")
                        raise RuntimeError(f"Cloud escalation returned HTTP {response.status_code}: {body}")

                    for line in response.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                        if line.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line)
                            usage = chunk.get("usage")
                            if usage:
                                self.last_usage = usage
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    completion_tokens_est += 1
                                    yield content
                        except Exception:
                            pass
                    break

        # Record spend under budget guardrail
        billing_guardrail.record_cloud_spend(prompt_tokens_est, completion_tokens_est)

    def chat_turn(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> Any:
        """Non-streaming chat turn with cloaked cloud endpoint."""
        import httpx

        allowed, notice = billing_guardrail.check_cloud_escalation()
        if not allowed:
            raise PermissionError(notice)

        attempts = 2
        while attempts > 0:
            attempts -= 1
            endpoint_url, active_key, model_id = resolve_cloud_credentials(self.api_key, getattr(self, "model", None))
            if not active_key:
                raise RuntimeError("Cloud escalation key not found. Configure GROQ_API_KEY or XAI_API_KEY.")

            actual_max_tokens = max(max_tokens, 4096)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {active_key}",
            }
            from codex.tools import TOOLS_SCHEMA
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": actual_max_tokens,
                "temperature": temperature,
                "stream": False,
            }
            if TOOLS_SCHEMA:
                payload["tools"] = TOOLS_SCHEMA
                payload["tool_choice"] = "auto"
            if "gpt-oss" in model_id:
                payload["include_reasoning"] = False

            with httpx.Client(timeout=45.0) as client:
                resp = client.post(endpoint_url, json=payload, headers=headers)
                if resp.status_code == 429 and attempts > 0:
                    from codex.config import rotate_api_key
                    new_k = rotate_api_key()
                    if new_k:
                        self.api_key = new_k
                        continue
                if resp.status_code != 200:
                    raise RuntimeError(f"Cloud escalation returned HTTP {resp.status_code}: {resp.text}")
                data = resp.json()
                break

        class FuncObj:
            def __init__(self, name, args):
                self.name = name
                self.arguments = args if isinstance(args, str) else json.dumps(args)

        class ToolCallObj:
            def __init__(self, id_val, name, args):
                self.id = id_val
                self.type = "function"
                self.function = FuncObj(name, args)

        class MsgObj:
            def __init__(self, content, tc):
                self.role = "assistant"
                self.content = content
                self.tool_calls = tc

        class ChoiceObj:
            def __init__(self, m):
                self.message = m

        class UsageObj:
            def __init__(self, pt, ct, tt):
                self.prompt_tokens = pt
                self.completion_tokens = ct
                self.total_tokens = tt

        class RespObj:
            def __init__(self, c, u):
                self.choices = [c]
                self.usage = u

        usage_data = data.get("usage", {})
        pt = usage_data.get("prompt_tokens", 0)
        ct = usage_data.get("completion_tokens", 0)
        tt = usage_data.get("total_tokens", pt + ct)
        billing_guardrail.record_cloud_spend(pt, ct)

        c0 = data.get("choices", [{}])[0]
        msg = c0.get("message", {})
        raw_tc = msg.get("tool_calls")
        tc_objects = None
        if raw_tc:
            tc_objects = []
            for item in raw_tc:
                f = item.get("function", {})
                tc_objects.append(
                    ToolCallObj(
                        item.get("id", f"call_{int(time.time()*1000)}"),
                        f.get("name", ""),
                        f.get("arguments", "{}")
                    )
                )

        return RespObj(ChoiceObj(MsgObj(msg.get("content", ""), tc_objects)), UsageObj(pt, ct, tt))


# Global singleton instance
cloaked_cloud_client = CloakedCloudClient()

