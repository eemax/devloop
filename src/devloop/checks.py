from __future__ import annotations

import subprocess
import time
from pathlib import Path

from devloop.models import CheckSpec, CommandResult


def run_checks(checks: list[CheckSpec], cwd: Path, required: bool) -> list[CommandResult]:
    results: list[CommandResult] = []

    for spec in checks:
        started_at = time.monotonic()
        try:
            completed = subprocess.run(
                spec.command,
                cwd=str(cwd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=spec.timeout_secs,
                check=False,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + f"\ncheck timed out after {spec.timeout_secs}s"
        results.append(
            CommandResult(
                name=spec.name,
                command=spec.command,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_secs=time.monotonic() - started_at,
                required=required,
            )
        )

    return results
