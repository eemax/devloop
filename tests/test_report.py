from pathlib import Path

from devloop.models import (
    AgentConfig,
    AgentInvocationResult,
    AuditReport,
    CommandResult,
    FinalStatus,
    Finding,
    FindingSeverity,
    ImplementerReport,
    RoundState,
    RunOutcome,
    RunSpec,
)
from devloop.report import build_markdown_report, default_commit_message, final_status_from_success, report_paths


def test_build_markdown_report_includes_core_sections() -> None:
    run_spec = _run_spec()
    round_state = RoundState(
        round_number=1,
        changed_files=["app.py"],
        implementer_result=_agent_result("impl"),
        implementer_report=ImplementerReport(summary="Implemented feature"),
        audit_result=_agent_result("audit"),
        audit_report=AuditReport(summary="Looks good", decision="approve"),
        checks=[CommandResult(name="tests", command="pytest -q", exit_code=0, stdout="", stderr="", duration_secs=0.1, required=True)],
        blocking_findings=[],
        diff_changed=True,
    )
    outcome = RunOutcome(
        status=FinalStatus.SUCCESS,
        rounds_completed=1,
        final_checks=[CommandResult(name="tests", command="pytest -q", exit_code=0, stdout="", stderr="", duration_secs=0.1, required=True)],
        final_findings=[Finding(id="f1", severity=FindingSeverity.INFO, title="Note", evidence="FYI")],
        changed_files=["app.py"],
        commit_sha="deadbeef",
        branch_name="codex/devloop/run-1",
        report_path=Path("/tmp/report.md"),
        report_json_path=Path("/tmp/report.json"),
    )

    report = build_markdown_report(run_spec, [round_state], outcome)

    assert "# devloop report: run-1" in report
    assert "- Final status: success" in report
    assert "- Commit: deadbeef" in report
    assert "- [info] Note: FYI" in report
    assert "- Round 1: Implemented feature" in report


def test_report_helpers_return_expected_values() -> None:
    run_spec = _run_spec()

    assert final_status_from_success(True).value == "success"
    assert final_status_from_success(False).value == "failed"
    assert "Devloop-Run: run-1" in default_commit_message(run_spec)
    assert report_paths(Path("/tmp/run")) == (Path("/tmp/run/report.md"), Path("/tmp/run/report.json"))


def _run_spec() -> RunSpec:
    return RunSpec(
        run_id="run-1",
        repo_root=Path("/tmp/repo"),
        base_commit="abc123",
        artifact_dir=Path("/tmp/repo/.devloop/runs/run-1"),
        goal="Build something",
        acceptance_criteria=["done"],
        constraints=[],
        out_of_scope=[],
        checks=[],
        max_rounds=2,
        commit_on_success=False,
        create_branch=False,
        branch_prefix="codex/devloop",
        implementer=AgentConfig(name="impl", command=["impl"]),
        auditor=AgentConfig(name="audit", command=["audit"]),
        plan_path=Path("/tmp/repo/plan.md"),
        raw_plan="# Build something",
    )


def _agent_result(name: str) -> AgentInvocationResult:
    return AgentInvocationResult(
        name=name,
        command=[name],
        cwd=Path("/tmp/repo"),
        stdout="",
        stderr="",
        exit_code=0,
        duration_secs=0.1,
        json_payload={},
    )
