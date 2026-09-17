"""Security & secret scrubbing engine: redacts sensitive keys and credentials."""

import re
from typing import Any

# Regular expressions for high-risk secrets and API credentials
SECRET_PATTERNS = [
    # Groq API keys
    (re.compile(r"gsk_[A-Za-z0-9]{40,}"), "[REDACTED_GROQ_KEY]"),
    # OpenAI API keys
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"sk-proj-[A-Za-z0-9_-]{40,}"), "[REDACTED_OPENAI_PROJECT_KEY]"),
    # Anthropic API keys
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{40,}"), "[REDACTED_ANTHROPIC_KEY]"),
    # GitHub Personal Access Tokens
    (re.compile(r"ghp_[A-Za-z0-9]{36,}"), "[REDACTED_GITHUB_PAT]"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{60,}"), "[REDACTED_GITHUB_FINE_GRAINED]"),
    # AWS Access Key IDs and Secrets
    (re.compile(r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}"), "[REDACTED_AWS_KEY_ID]"),
    # Private RSA / OpenSSH Keys
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    # Generic env secret assignments (e.g. SECRET_KEY=..., PASSWORD=...)
    (re.compile(r"(?i)\b(password|secret|token|api_key|auth_token)\s*=\s*['\"][^'\"]{8,}['\"]"), r"\1=[REDACTED_SECRET]"),
]


class SecretScrubber:
    """Scans and redacts credentials, environment variables, and tokens before transmission."""

    @classmethod
    def scrub_text(cls, text: str) -> str:
        """Sanitize plain text or code string."""
        if not text or not isinstance(text, str):
            return text

        scrubbed = text
        for pattern, replacement in SECRET_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)

        return scrubbed

    @classmethod
    def scrub_messages(cls, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sanitize a list of chat turn messages before sending to remote inference."""
        cleaned = []
        for msg in messages:
            copy_m = dict(msg)
            if "content" in copy_m and isinstance(copy_m["content"], str):
                copy_m["content"] = cls.scrub_text(copy_m["content"])
            cleaned.append(copy_m)
        return cleaned

    @classmethod
    def has_exposed_secret(cls, text: str) -> bool:
        """Check whether text contains unredacted credentials."""
        for pattern, _ in SECRET_PATTERNS:
            if pattern.search(text):
                return True
        return False
