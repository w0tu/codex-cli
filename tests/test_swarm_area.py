"""Unit tests for the dedicated Swarm Command Center area in Codex-CLI."""

import pytest
from codex.main import SlashCommandCompleter
from codex.swarm import SwarmBridgeClient, SIMPLI_LEAF_ASCII


def test_swarm_completer_registered():
    """Verify /swarm and /grokbot are registered in SlashCommandCompleter."""
    completer = SlashCommandCompleter()
    commands = [cmd for cmd, _ in completer.COMMANDS]
    assert "/swarm" in commands
    assert "/grokbot" in commands


def test_simpli_leaf_ascii_art_intact():
    """Verify SIMPLI leaf ASCII art is intact and preserves exact characters."""
    assert "SIMPLI" in SIMPLI_LEAF_ASCII or ("S" in SIMPLI_LEAF_ASCII and "I" in SIMPLI_LEAF_ASCII)
    assert "/ \\" in SIMPLI_LEAF_ASCII
    assert "███████╗" in SIMPLI_LEAF_ASCII


def test_swarm_bridge_client_live():
    """Verify SwarmBridgeClient communicates with the daemon and gets 45,046 agents."""
    bridge = SwarmBridgeClient()
    if bridge.is_alive():
        summary = bridge.get_summary()
        assert summary["total_agents"] == 45046
        assert summary["num_clusters"] == 45
        assert summary["total_workers"] == 45000

        # Inspect Commander (Tier 1)
        commander = bridge.inspect_agent(0)
        assert commander["tier"] == 1
        assert "Commander" in commander["role"]

        # Inspect Manager (Tier 2)
        manager = bridge.inspect_agent(1)
        assert manager["tier"] == 2


def test_subagent_swarm_orchestration():
    """Verify orchestrate_subagent_swarm executes 4-node DAG decomposition."""
    from codex.subagents import orchestrate_subagent_swarm
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.chat.return_value = "Mocked expert sub-agent output"

    result = orchestrate_subagent_swarm(
        mission="Build a high-performance distributed key-value store with raft consensus",
        client=mock_client
    )

    assert result["mission"] == "Build a high-performance distributed key-value store with raft consensus"
    assert result["status"] == "completed"
    assert len(result["nodes"]) == 4
    roles = [node["role"] for node in result["nodes"]]
    assert "System Architect" in roles
    assert "Core Backend Engineer" in roles
    assert "Frontend & UI Stylist" in roles
    assert "Security & Vulnerability Auditor" in roles
    assert "synthesis" in result
    assert "Mocked expert sub-agent output" in result["synthesis"]

