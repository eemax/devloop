import sys
from pathlib import Path

import pytest

from devloop.subprocess_utils import CommandExecutionError, CommandOutput, ensure_command_available, run_command


def test_ensure_command_available_finds_existing_command() -> None:
    assert ensure_command_available("git")


def test_ensure_command_available_raises_for_missing_command() -> None:
    with pytest.raises(CommandExecutionError, match="command not found"):
        ensure_command_available("devloop-command-that-does-not-exist")


def test_run_command_supports_stdin(tmp_path: Path) -> None:
    completed = run_command(
        [sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"],
        cwd=tmp_path,
        timeout_secs=5,
        stdin_text="hello",
    )

    assert isinstance(completed, CommandOutput)
    assert completed.returncode == 0
    assert completed.stdout.strip() == "HELLO"
    assert completed.duration_secs >= 0


def test_run_command_wraps_timeout(tmp_path: Path) -> None:
    with pytest.raises(CommandExecutionError, match="timed out"):
        run_command(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            cwd=tmp_path,
            timeout_secs=1,
        )


def test_run_command_wraps_missing_executable(tmp_path: Path) -> None:
    with pytest.raises(CommandExecutionError, match="failed to execute"):
        run_command(["/definitely/missing/devloop"], cwd=tmp_path, timeout_secs=1)
