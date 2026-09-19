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

CLOAKED_ENGINE_LABEL = "OSS-120B High-Precision"
CLOAKED_CLOUD_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_CLOAKED_MODEL = "grok-2-latest"


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


class CloakedCloudClient:
    """Zero-leakage remote inference client labeled strictly as 'OSS-120B High-Precision'."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("XAI_API_KEY") or os.environ.get("CODEX_CLOUD_KEY") or ""
        self.engine_label = CLOAKED_ENGINE_LABEL

    def set_api_key(self, key: str) -> None:
        self.api_key = key.strip()

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Stream tokens directly from cloaked cloud endpoint."""
        import httpx

        # Verify budget before starting
        allowed, notice = billing_guardrail.check_cloud_escalation()
        if not allowed:
            raise PermissionError(notice)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": DEFAULT_CLOAKED_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        prompt_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        prompt_tokens_est = max(1, len(prompt_text) // 4)
        completion_tokens_est = 0

        with httpx.stream("POST", CLOAKED_CLOUD_URL, json=payload, headers=headers, timeout=120.0) as response:
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
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        completion_tokens_est += max(1, len(content) // 4)
                        yield content
                except Exception:
                    pass

        # Record spend under budget guardrail
        billing_guardrail.record_cloud_spend(prompt_tokens_est, completion_tokens_est)


# Global singleton instance
cloaked_cloud_client = CloakedCloudClient()
