"""LLM backends. Default for local use: the logged-in `claude` CLI (your Claude subscription) — no API key needed.
Optional: Anthropic API if ANTHROPIC_API_KEY is set. Both expose .complete(system, user) -> str."""
from __future__ import annotations
import subprocess
import tempfile
from types import SimpleNamespace

CLI_MODELS = {"claude-haiku-5-5": "haiku", "claude-sonnet-5-5": "sonnet", "claude-opus-5-5": "opus", "claude-fable-5-1": "fable"}


class ClaudeCLI:
    """Runs `claude -p` with ALL tools disabled, no session persistence, in an empty temp dir (job text is untrusted)."""
    def __init__(self, model: str = "haiku", timeout: int = 120, runner=None):
        self.model, self.timeout = CLI_MODELS.get(model, model), timeout
        self._run = runner or subprocess.run

    def complete(self, system: str, user: str) -> str:
        with tempfile.TemporaryDirectory() as empty:
            p = self._run(["claude", "-p", "--model", self.model, "--tools", "", "--no-session-persistence",
                           "--append-system-prompt", system, "--output-format", "text"],
                          input=user, capture_output=True, text=True, timeout=self.timeout, cwd=empty)
        if p.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {(p.stderr or '')[:200]}")
        return p.stdout.strip()


class AnthropicAPI:
    def __init__(self, api_key: str, model: str):
        from anthropic import Anthropic
        self.client, self.model = Anthropic(api_key=api_key), model

    def complete(self, system: str, user: str) -> str:
        m = self.client.messages.create(model=self.model, max_tokens=400, system=system, messages=[{"role": "user", "content": user}])
        return m.content[0].text


def make_llm(secrets: dict, model: str):
    key = (secrets.get("ANTHROPIC_API_KEY") or "").strip()
    return AnthropicAPI(key, model) if key else ClaudeCLI(model)


class _ClientAdapter:
    """Lets LLMScorer keep its messages.create() shape while using any backend."""
    def __init__(self, llm):
        self.messages = SimpleNamespace(create=lambda **kw: SimpleNamespace(
            content=[SimpleNamespace(text=llm.complete(kw["system"], kw["messages"][0]["content"]))]))
