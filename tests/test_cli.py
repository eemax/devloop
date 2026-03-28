import sys
from pathlib import Path

from devloop.cli import main
from devloop.models import CommandResult, FinalStatus, RunOutcome
from tests.helpers import build_config_text, init_git_repo, write_plan


def test_cli_validate_config_and_doctor(tmp_path: Path, capsys) -> None:
    repo = init_git_repo(tmp_path)
    config_path = tmp_path / "devloop.toml"
    config_path.write_text(
        build_config_text(
            repo,
            [sys.executable, "-c", "print('implementer')"],
            [sys.executable, "-c", "print('auditor')"],
        ),
        encoding="utf-8",
    )

    assert main(["validate-config", "--config", str(config_path)]) == 0
    validate_output = capsys.readouterr()
    assert "config OK" in validate_output.out

    assert main(["doctor", "--config", str(config_path)]) == 0
    doctor_output = capsys.readouterr()
    assert str(repo) in doctor_output.out
    assert sys.executable in doctor_output.out


def test_cli_report_reads_markdown_file(tmp_path: Path, capsys) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "report.md").write_text("# report\n", encoding="utf-8")

    assert main(["report", str(run_dir)]) == 0
    output = capsys.readouterr()
    assert "# report" in output.out


def test_cli_resume_is_not_implemented(capsys) -> None:
    assert main(["resume", "run-123"]) == 1
    output = capsys.readouterr()
    assert "not implemented" in output.err


def test_cli_run_returns_success_exit_code_when_runner_succeeds(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "devloop.toml"
    plan_path = tmp_path / "plan.md"
    config_path.write_text(
        """
[run]
repo = "."

[agents.implementer]
name = "impl"
command = ["impl"]

[agents.auditor]
name = "audit"
command = ["audit"]
""".strip(),
        encoding="utf-8",
    )
    write_plan(plan_path)

    def fake_run_devloop(config, plan):
        return RunOutcome(
            status=FinalStatus.SUCCESS,
            rounds_completed=1,
            final_checks=[CommandResult(name="tests", command="pytest -q", exit_code=0, stdout="", stderr="", duration_secs=0.1, required=True)],
            final_findings=[],
            changed_files=["app.py"],
            commit_sha="abc123",
            branch_name="codex/devloop/run-1",
            report_path=Path("/tmp/report.md"),
            report_json_path=Path("/tmp/report.json"),
        )

    monkeypatch.setattr("devloop.cli.run_devloop", fake_run_devloop)

    assert main(["run", "--plan", str(plan_path), "--config", str(config_path)]) == 0
    output = capsys.readouterr()
    assert "devloop finished with status: success" in output.out
    assert "commit: abc123" in output.out
