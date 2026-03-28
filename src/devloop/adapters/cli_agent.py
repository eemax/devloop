from __future__ import annotations

import shutil
from pathlib import Path

from devloop.adapters.base import AgentAdapter
from devloop.json_protocol import JsonProtocolError, extract_json_block
from devloop.models import AgentInvocationResult, InputMode
from devloop.subprocess_utils import run_command


class CliAgentAdapter(AgentAdapter):
    def run(self, prompt: str, cwd: Path, prompt_path: Path | None = None) -> AgentInvocationResult:
        command = list(self.config.command)
        stdin_text = None

        if self.config.input_mode == InputMode.STDIN:
            stdin_text = prompt
        else:
            if prompt_path is None:
                raise ValueError("prompt_path is required when input_mode=file")
            command.append(str(prompt_path))

        completed = run_command(
            command=command,
            cwd=cwd,
            timeout_secs=self.timeout_secs,
            stdin_text=stdin_text,
        )

        json_payload = None
        try:
            json_payload = extract_json_block(completed.stdout)
        except JsonProtocolError:
            pass

        return AgentInvocationResult(
            name=self.config.name,
            command=command,
            resolved_command=shutil.which(command[0]),
            cwd=cwd,
            input_mode=self.config.input_mode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            duration_secs=completed.duration_secs,
            started_at=completed.started_at,
            finished_at=completed.finished_at,
            json_payload=json_payload,
        )
