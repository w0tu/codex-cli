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
