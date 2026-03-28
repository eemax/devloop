from __future__ import annotations

from pathlib import Path

from devloop.models import AgentConfig, AgentInvocationResult


class AgentAdapter:
    def __init__(self, config: AgentConfig, timeout_secs: int) -> None:
        self.config = config
        self.timeout_secs = timeout_secs

    def run(self, prompt: str, cwd: Path, prompt_path: Path | None = None) -> AgentInvocationResult:
        raise NotImplementedError
