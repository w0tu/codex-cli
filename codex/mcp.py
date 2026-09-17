"""Model Context Protocol (MCP) integration client and server configuration loader."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_MCP_CONFIG = Path.home() / ".codex" / "mcp_servers.json"


class MCPManager:
    """Manages connections to external Model Context Protocol (MCP) servers."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or DEFAULT_MCP_CONFIG
        self.servers: dict[str, dict[str, Any]] = {}
        self.tools: list[dict[str, Any]] = []
        self.load_servers()

    def load_servers(self) -> dict[str, dict[str, Any]]:
        """Load configured MCP servers from config file."""
        if not self.config_path.exists():
            return {}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.servers = data.get("mcpServers", {})
            return self.servers
        except Exception:
            return {}

    def register_server(self, name: str, command: str, args: list[str] | None = None, env: dict[str, str] | None = None) -> None:
        """Register a new MCP server in the config."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        servers = self.load_servers()
        servers[name] = {
            "command": command,
            "args": args or [],
            "env": env or {},
        }
        self.config_path.write_text(json.dumps({"mcpServers": servers}, indent=2), encoding="utf-8")
        self.servers = servers

    def list_servers(self) -> list[dict[str, Any]]:
        """Return list of configured MCP servers."""
        return [{"name": k, **v} for k, v in self.servers.items()]

    def ping_server(self, name: str) -> bool:
        """Simple handshake probe with an MCP server via stdio JSON-RPC."""
        server_cfg = self.servers.get(name)
        if not server_cfg:
            return False
        cmd = [server_cfg["command"]] + server_cfg.get("args", [])
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, **server_cfg.get("env", {})},
            )
            req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}) + "\n"
            stdout, _ = proc.communicate(input=req, timeout=3)
            return proc.returncode == 0 or len(stdout) > 0
        except Exception:
            return False

    def convert_to_tools_schema(self, mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert MCP tool specifications into standard OpenAI/Groq function call schema."""
        converted = []
        for t in mcp_tools:
            converted.append({
                "type": "function",
                "function": {
                    "name": f"mcp_{t.get('name', '')}",
                    "description": t.get("description", "External MCP tool"),
                    "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
                }
            })
        return converted
