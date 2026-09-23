import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from codex.cloud_fallback import resolve_cloud_credentials
from codex.client import ANTIGRAVITY_MODELS_MAP, HybridCodexClient
from codex.context.headroom import HeadroomManager, headroom
from codex.claude_hud import ClaudeHUD, claude_hud
from codex.personas import get_specialized_persona, list_specialized_personas
from codex.agents import AgentRegistry
from codex.snake_benchmark import SnakeArenaBenchmark, run_snake_benchmark
from codex.clash import ClashEngine, clash_engine
from codex.boss_loop import BossLoopSupervisor, boss_supervisor
from codex.ruflo_agency import RufloAgentAgency, ruflo_agency


def test_minimax_model_resolution():
    url, key, model_id = resolve_cloud_credentials(api_key="gsk_test_key_1234567890", model="minimax-m2.7")
    assert "minimax" in model_id.lower()
    assert "minimax-m2.7" in ANTIGRAVITY_MODELS_MAP
    assert ANTIGRAVITY_MODELS_MAP["minimax-m2.7"] == "minimax/minimax-m2.7"


def test_gpt_120b_cloud_resolution():
    url, key, model_id = resolve_cloud_credentials(api_key="gsk_test_key_1234567890")
    assert "120b" in model_id.lower()
    assert "openai/gpt-oss-120b" in ANTIGRAVITY_MODELS_MAP
    assert ANTIGRAVITY_MODELS_MAP["120b"] == "openai/gpt-oss-120b"


def test_hybrid_client_cloud_only():
    client = HybridCodexClient()
    assert client.mode == "cloud"
    assert client.cloud_enabled is True
    assert "120b" in client.model.lower()



def test_headroom_context_accounting():
    hm = HeadroomManager(model_name="minimax-m2.7")
    assert hm.context_limit == 204800
    info = hm.calculate_headroom("def test(): pass", history_tokens=1000)
    assert info["remaining_headroom"] > 190000
    assert info["headroom_pct"] > 90.0

    compacted, meta = hm.compact_prompt("Short prompt")
    assert compacted == "Short prompt"
    assert meta["compressed"] is False

    badge = hm.render_hud_badge("hello", 500)
    assert "Headroom" in badge


def test_claude_hud_rendering():
    hud = ClaudeHUD()
    line = hud.render_bar(model_name="minimax-m2.7", total_tokens=1500, session_cost=0.002)
    assert "Claude HUD" in line
    assert "minimax-m2.7" in line
    assert "tok" in line


def test_specialized_personas_and_registry():
    for name in ["frontend", "writer", "reddit", "wizard", "explore", "plan"]:
        p = get_specialized_persona(name)
        assert p is not None, f"Persona {name} not found"
        assert "system_prompt" in p
        assert len(p["system_prompt"]) > 50

    reg = AgentRegistry()
    assert reg.get_agent("wizard") is not None
    assert reg.get_agent("frontend") is not None
    assert reg.get_agent("reddit") is not None
    assert reg.get_agent("writer") is not None
    assert reg.get_agent("explore") is not None
    assert reg.get_agent("plan") is not None

    all_agents = reg.list_agents()
    names = [a.get("name", "") for a in all_agents]
    assert any("Wizard" in n for n in names)
    assert any("Reddit" in n for n in names)


def test_snake_benchmark_arena():
    arena = SnakeArenaBenchmark(grid_size=10, max_ticks=5)
    res = arena.run_benchmark(interactive=False)
    assert "winner" in res
    assert len(res["leaderboard"]) >= 5
    assert all("latency_ms" in p for p in res["leaderboard"])


def test_clash_mode_execution():
    ce = ClashEngine()
    res = ce.run_clash("Design a lock-free queue in Python")
    assert "winner" in res
    assert "synthesis" in res
    assert len(res["candidates"]) == 4
    assert any("minimax" in c["model_id"].lower() for c in res["candidates"])


def test_boss_loop_supervisor():
    bl = BossLoopSupervisor(max_iterations=2)
    # Mock verifier to simulate test outcome
    bl.verifier.run_tests = lambda: (True, "All 75 tests passed successfully")
    res = bl.run_boss_loop("Audit codebase for high performance invariants")
    assert res["success"] is True
    assert res["iterations_used"] == 1


def test_ruflo_agency_dispatch():
    agency = RufloAgentAgency()
    res = agency.run_mission("Capture screen frame and record mission dossier")
    assert res["success"] is True
    assert len(res["actions"]) >= 2


def test_code_synthesizer_live_edit(tmp_path):
    from codex.code_synthesizer import CodeSynthesizer
    synth = CodeSynthesizer()
    res = synth.edit_index_html("change color to red and add a cube", target_dir=tmp_path)
    assert res["success"] is True
    assert (tmp_path / "index.html").exists()
    content = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "#f7768e" in content
    assert "BoxGeometry" in content
    assert len(res["changes"]) >= 2


def test_code_synthesizer_speed_and_particles(tmp_path):
    from codex.code_synthesizer import CodeSynthesizer
    synth = CodeSynthesizer()
    res = synth.edit_index_html("make it spin faster with matrix green and dense galaxy particles", target_dir=tmp_path)
    assert res["success"] is True
    content = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "particlesCount = 4000" in content
    assert "elapsedTime * 0.55" in content


def test_desktop_window_manager_groq_automation(tmp_path, monkeypatch):
    from codex.screen_agent import DesktopWindowManager
    wm = DesktopWindowManager()
    
    # Test saving keys to custom document
    doc_file = "test_groq_keys.txt"
    res = wm.run_groq_keys_automation(filename=doc_file)
    assert res["success"] is True
    assert "groq_api_keys" in res["message"] or doc_file in res["message"]
    assert "primary_key" in res
    assert "keys" in res
    assert isinstance(res["keys"], list)


def test_web_messaging_platforms():
    from codex.screen_agent import DesktopWindowManager
    wm = DesktopWindowManager()

    # WhatsApp
    res_wa = wm.open_web_messaging(platform="whatsapp", recipient="+1234567890", message="Hello from Agent")
    assert res_wa["success"] is True
    assert "whatsapp" in res_wa["message"].lower()

    # Google Chat
    res_gc = wm.open_web_messaging(platform="google_chat")
    assert res_gc["success"] is True
    assert "chat.google.com" in res_gc["message"].lower() or "google" in res_gc["message"].lower()


def test_floating_agent_pointer():
    from codex.screen_agent import agent_pointer
    ok = agent_pointer.spawn(start_x=300, start_y=300, badge="✦ TEST AGENT")
    assert isinstance(ok, bool)
    agent_pointer.close()

