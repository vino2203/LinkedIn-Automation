from types import SimpleNamespace
from pathlib import Path
from linkiden.llm import ClaudeCLI, make_llm, _ClientAdapter, AnthropicAPI
from linkiden.scorer import LLMScorer
from linkiden.config import Settings

def fake_run(captured, out='{"score": 92, "reasons": "ok", "missing": []}', rc=0):
    def run(cmd, **kw):
        captured["cmd"], captured["kw"] = cmd, kw
        return SimpleNamespace(returncode=rc, stdout=out, stderr="boom")
    return run

def test_cli_disables_tools_and_isolates():
    c = {}; llm = ClaudeCLI("claude-haiku-5-5", runner=fake_run(c))
    assert llm.complete("sys", "user text") == '{"score": 92, "reasons": "ok", "missing": []}'
    cmd = c["cmd"]
    assert cmd[cmd.index("--tools") + 1] == "" and "--no-session-persistence" in cmd and cmd[cmd.index("--model") + 1] == "haiku"
    assert c["kw"]["input"] == "user text" and c["kw"]["cwd"] != str(Path.cwd())

def test_cli_failure_raises():
    import pytest
    with pytest.raises(RuntimeError): ClaudeCLI(runner=fake_run({}, rc=1)).complete("s", "u")

def test_backend_selection_without_key_uses_cli():
    assert isinstance(make_llm({}, "claude-haiku-5-5"), ClaudeCLI)
    assert isinstance(make_llm({"ANTHROPIC_API_KEY": ""}, "claude-haiku-5-5"), ClaudeCLI)

def test_scorer_works_through_cli_adapter():
    sc = LLMScorer(_ClientAdapter(ClaudeCLI(runner=fake_run({}))), "m", Path(__file__).resolve().parents[1])
    assert sc({"title": "GenAI Engineer", "company": "A", "description": "x"})[0] == 92

def test_anthropic_key_not_required():
    assert "ANTHROPIC_API_KEY" not in Settings({}, {}, {}).missing_secrets()
