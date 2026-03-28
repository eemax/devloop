from __future__ import annotations

from pathlib import Path

from devloop.models import FinalStatus, RoundState, RunOutcome, RunSpec


def build_markdown_report(run_spec: RunSpec, rounds: list[RoundState], outcome: RunOutcome) -> str:
    lines = [
        f"# devloop report: {run_spec.run_id}",
        "",
        f"- Trace: {run_spec.trace_id}",
        f"- Goal: {run_spec.goal}",
        f"- Repo: {run_spec.repo_root}",
        f"- Base commit: {run_spec.base_commit}",
        f"- Implementer: {run_spec.implementer.name}",
        f"- Auditor: {run_spec.auditor.name}",
        f"- Final status: {outcome.status.value}",
        f"- Rounds completed: {outcome.rounds_completed}",
    ]

    if outcome.branch_name:
        lines.append(f"- Branch: {outcome.branch_name}")
    if outcome.commit_sha:
        lines.append(f"- Commit: {outcome.commit_sha}")

    lines.extend(["", "## Checks", ""])
    for check in outcome.final_checks:
        lines.append(f"- {'required' if check.required else 'advisory'} `{check.name}`: exit {check.exit_code}")

    lines.extend(["", "## Files changed", ""])
    if outcome.changed_files:
        for path in outcome.changed_files:
            lines.append(f"- {path}")
    else:
        lines.append("- None")

    lines.extend(["", "## Findings", ""])
    if outcome.final_findings:
        for finding in outcome.final_findings:
            lines.append(f"- [{finding.severity.value}] {finding.title}: {finding.evidence}")
    else:
        lines.append("- None")

    lines.extend(["", "## Round summaries", ""])
    if rounds:
        for round_state in rounds:
            lines.append(f"- Round {round_state.round_number}: {round_state.implementer_report.summary}")
    else:
        lines.append("- No rounds executed")

    return "\n".join(lines) + "\n"


def default_commit_message(run_spec: RunSpec) -> str:
    subject = run_spec.goal.strip().splitlines()[0]
    return (
        f"feat: {subject[:60]}\n\n"
        f"Devloop-Run: {run_spec.run_id}\n"
        f"Devloop-Implementer: {run_spec.implementer.name}\n"
        f"Devloop-Auditor: {run_spec.auditor.name}\n"
        f"Devloop-Rounds: {run_spec.max_rounds}"
    )


def final_status_from_success(success: bool) -> FinalStatus:
    return FinalStatus.SUCCESS if success else FinalStatus.FAILED


def report_paths(artifact_dir: Path) -> tuple[Path, Path]:
    return artifact_dir / "report.md", artifact_dir / "report.json"
