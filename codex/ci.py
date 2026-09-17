"""Headless CI/CD execution mode for GitHub Actions and pipeline automation."""

import json
import sys
import time
from typing import Any


class HeadlessCIRunner:
    """Executes prompt non-interactively and formats output for CI/CD pipelines."""

    def __init__(self, client: Any, prompt: str, max_cost: float = 0.0):
        self.client = client
        self.prompt = prompt
        self.max_cost = max_cost

    def run(self) -> dict[str, Any]:
        """Run single-pass headless execution and return structured report."""
        start_time = time.time()
        report: dict[str, Any] = {
            "status": "success",
            "prompt": self.prompt,
            "output": "",
            "tokens_used": 0,
            "elapsed_seconds": 0.0,
            "exit_code": 0,
            "review_comments": [],
        }

        try:
            messages = [
                {"role": "system", "content": "You are Codex CI Assistant. Provide concise, actionable automated review findings."},
                {"role": "user", "content": self.prompt}
            ]
            resp = self.client.chat_turn(messages)
            content = resp.choices[0].message.content or ""
            report["output"] = content

            usage = getattr(resp, "usage", None)
            if usage:
                report["tokens_used"] = getattr(usage, "total_tokens", 0)

            # Auto-extract review comments if prompt was a PR review
            if "review" in self.prompt.lower():
                lines = [l.strip() for l in content.splitlines() if l.strip().startswith(("-", "*", "1.", "2.", "3."))]
                report["review_comments"] = lines[:10]

        except Exception as e:
            report["status"] = "error"
            report["output"] = str(e)
            report["exit_code"] = 1

        report["elapsed_seconds"] = round(time.time() - start_time, 2)
        return report

    def print_report(self, report: dict[str, Any], format_type: str = "json") -> None:
        """Output report in json or markdown format to stdout."""
        if format_type == "json":
            print(json.dumps(report, indent=2))
        else:
            print(f"## Codex CI Automated Report\n")
            print(f"- **Status**: {report['status']}")
            print(f"- **Elapsed**: {report['elapsed_seconds']}s")
            print(f"- **Tokens**: {report['tokens_used']}\n")
            print(f"### Output\n\n{report['output']}")
