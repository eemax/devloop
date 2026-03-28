from __future__ import annotations

import dataclasses
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


class CommandExecutionError(RuntimeError):
    """Raised when a command cannot be started."""


@dataclasses.dataclass(frozen=True)
class CommandOutput:
    process: subprocess.CompletedProcess[str]
    duration_secs: float
    started_at: datetime
    finished_at: datetime

    @property
    def returncode(self) -> int:
        return self.process.returncode

    @property
    def stdout(self) -> str:
        return self.process.stdout

    @property
    def stderr(self) -> str:
        return self.process.stderr


def ensure_command_available(command: str) -> str:
    resolved = shutil.which(command)
    if not resolved:
        raise CommandExecutionError(f"command not found on PATH: {command}")
    return resolved


def run_command(
    command: list[str],
    cwd: Path,
    timeout_secs: int,
    stdin_text: str | None = None,
    check: bool = False,
) -> CommandOutput:
    started_wall = datetime.now(timezone.utc)
    started_at = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout_secs,
            check=check,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandExecutionError(
            f"command timed out after {timeout_secs}s: {' '.join(command)}"
        ) from exc
    except OSError as exc:
        raise CommandExecutionError(f"failed to execute {' '.join(command)}: {exc}") from exc

    return CommandOutput(
        process=result,
        duration_secs=time.monotonic() - started_at,
        started_at=started_wall,
        finished_at=datetime.now(timezone.utc),
    )
