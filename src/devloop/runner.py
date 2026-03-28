from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from devloop.adapters.cli_agent import CliAgentAdapter
from devloop.artifacts import copy_file, ensure_dir, safe_rel_path, write_json, write_text
from devloop.checks import run_checks
from devloop.git_ops import (
    changed_files,
    commit_all,
    create_branch,
    current_head,
    diff_against,
    diff_worktree,
    ensure_clean_worktree,
    ensure_git_repo,
    show_file_at_commit,
    status_porcelain,
)
from devloop.models import (
    AuditReport,
    CommandResult,
    Config,
    FinalStatus,
    Finding,
    ImplementerReport,
    PlanSpec,
    RoundState,
    RunOutcome,
    RunSpec,
)
from devloop.prompts import render_auditor_prompt, render_implementer_prompt
from devloop.report import build_markdown_report, default_commit_message, report_paths
from devloop.stop_conditions import blocking_findings, decide_round_stop
from devloop.subprocess_utils import ensure_command_available


class RunnerError(RuntimeError):
    """Raised when the run cannot complete."""


def run_devloop(config: Config, plan: PlanSpec) -> RunOutcome:
    repo_root = ensure_git_repo(config.run.repo.resolve())
    if config.run.require_clean_worktree:
        ensure_clean_worktree(repo_root)

    ensure_command_available(config.implementer.command[0])
    ensure_command_available(config.auditor.command[0])

    run_id = _run_id(current_head(repo_root))
    artifact_dir = ensure_dir((repo_root / config.run.artifact_dir / run_id).resolve())

    branch_name = None
    if config.run.create_branch:
        branch_name = f"{config.run.branch_prefix}/{run_id}"
        create_branch(repo_root, branch_name)

    base_commit = current_head(repo_root)
    run_spec = RunSpec(
        run_id=run_id,
        repo_root=repo_root,
        base_commit=base_commit,
        artifact_dir=artifact_dir,
        goal=plan.goal,
        acceptance_criteria=plan.acceptance_criteria,
        constraints=plan.constraints,
        out_of_scope=plan.out_of_scope,
        checks=plan.checks,
        max_rounds=config.run.max_rounds,
        commit_on_success=config.run.commit_on_success,
        create_branch=config.run.create_branch,
        branch_prefix=config.run.branch_prefix,
        implementer=config.implementer,
        auditor=config.auditor,
        plan_path=plan.source_path,
        raw_plan=plan.body,
    )
    write_json(artifact_dir / "run_spec.json", run_spec.model_dump(mode="json"))

    implementer = CliAgentAdapter(config.implementer, timeout_secs=config.run.timeout_secs)
    auditor = CliAgentAdapter(config.auditor, timeout_secs=config.run.timeout_secs)

    unresolved_findings: list[Finding] = []
    rounds: list[RoundState] = []
    previous_fingerprint: str | None = None
    previous_summary: str | None = None
    final_status = FinalStatus.FAILED
    changed: list[str] = []

    for round_number in range(1, config.run.max_rounds + 1):
        round_dir = ensure_dir(artifact_dir / "rounds" / f"{round_number:02d}")

        implementer_prompt = render_implementer_prompt(run_spec, plan, unresolved_findings, previous_summary)
        implementer_prompt_path = round_dir / "implementer_prompt.txt"
        write_text(implementer_prompt_path, implementer_prompt)
        implementer_result = implementer.run(implementer_prompt, cwd=repo_root, prompt_path=implementer_prompt_path)
        write_text(round_dir / "implementer_stdout.txt", implementer_result.stdout)
        write_text(round_dir / "implementer_stderr.txt", implementer_result.stderr)

        if implementer_result.exit_code != 0:
            raise RunnerError(f"implementer command exited with {implementer_result.exit_code}")
        if implementer_result.json_payload is None:
            raise RunnerError("implementer did not return a valid structured JSON payload")

        try:
            implementer_report = ImplementerReport.model_validate(implementer_result.json_payload)
        except ValidationError as exc:
            raise RunnerError(f"implementer JSON payload did not match schema: {exc}") from exc
        write_json(round_dir / "implementer_report.json", implementer_report.model_dump(mode="json"))

        current_status = status_porcelain(repo_root)
        write_text(round_dir / "git_status.txt", current_status)

        cumulative_patch = diff_against(repo_root, base_commit)
        round_patch = diff_worktree(repo_root)
        write_text(round_dir / "cumulative.patch", cumulative_patch)
        write_text(round_dir / "round.patch", round_patch)

        changed = changed_files(repo_root, base_commit)
        write_text(round_dir / "changed_files.txt", "\n".join(changed) + ("\n" if changed else ""))

        before_dir = ensure_dir(round_dir / "before")
        after_dir = ensure_dir(round_dir / "after")
        _snapshot_changed_files(repo_root, base_commit, changed, before_dir, after_dir)

        check_results = []
        check_results.extend(run_checks(config.checks.required, repo_root, required=True))
        check_results.extend(run_checks(config.checks.advisory, repo_root, required=False))
        write_json(round_dir / "checks.json", _serialize_checks(check_results))

        snapshot_dir = _build_audit_snapshot(round_dir, run_spec, implementer_report, cumulative_patch, round_patch, check_results, unresolved_findings)
        auditor_prompt = render_auditor_prompt(run_spec, unresolved_findings)
        auditor_prompt_path = round_dir / "auditor_prompt.txt"
        write_text(auditor_prompt_path, auditor_prompt)
        audit_cwd = snapshot_dir if config.auditor.cwd_mode.value == "snapshot" else repo_root
        audit_result = auditor.run(auditor_prompt, cwd=audit_cwd, prompt_path=auditor_prompt_path)
        write_text(round_dir / "auditor_stdout.txt", audit_result.stdout)
        write_text(round_dir / "auditor_stderr.txt", audit_result.stderr)

        if audit_result.exit_code != 0:
            raise RunnerError(f"auditor command exited with {audit_result.exit_code}")
        if audit_result.json_payload is None:
            raise RunnerError("auditor did not return a valid structured JSON payload")

        try:
            audit_report = AuditReport.model_validate(audit_result.json_payload)
        except ValidationError as exc:
            raise RunnerError(f"auditor JSON payload did not match schema: {exc}") from exc
        write_json(round_dir / "findings.json", audit_report.model_dump(mode="json"))

        unresolved_findings = _dedupe_findings(audit_report.findings)
        current_fingerprint = _findings_fingerprint(unresolved_findings)
        repeated = bool(current_fingerprint) and current_fingerprint == previous_fingerprint
        previous_fingerprint = current_fingerprint
        previous_summary = implementer_report.summary

        required_checks_pass = all(result.exit_code == 0 for result in check_results if result.required)
        diff_changed = bool(cumulative_patch.strip())
        round_state = RoundState(
            round_number=round_number,
            changed_files=changed,
            implementer_result=implementer_result,
            implementer_report=implementer_report,
            audit_result=audit_result,
            audit_report=audit_report,
            checks=check_results,
            blocking_findings=blocking_findings(unresolved_findings),
            diff_changed=diff_changed,
        )
        rounds.append(round_state)

        stop = decide_round_stop(unresolved_findings, required_checks_pass, diff_changed, repeated)
        if stop.stop:
            final_status = stop.status or FinalStatus.FAILED
            break
    else:
        final_status = FinalStatus.FAILED

    if final_status == FinalStatus.SUCCESS and rounds:
        # Auditor is read-only, so the last round's checks are still valid.
        final_checks = list(rounds[-1].checks)
    else:
        final_checks = []
        final_checks.extend(run_checks(config.checks.required, repo_root, required=True))
        final_checks.extend(run_checks(config.checks.advisory, repo_root, required=False))

    if any(result.exit_code != 0 for result in final_checks if result.required):
        final_status = FinalStatus.FAILED
    elif blocking_findings(unresolved_findings):
        final_status = FinalStatus.FAILED if final_status != FinalStatus.STALLED else final_status

    commit_sha = None
    if final_status == FinalStatus.SUCCESS and config.run.commit_on_success:
        commit_sha = commit_all(repo_root, default_commit_message(run_spec))

    report_md_path, report_json_path = report_paths(artifact_dir)
    outcome = RunOutcome(
        status=final_status,
        rounds_completed=len(rounds),
        final_checks=final_checks,
        final_findings=unresolved_findings,
        changed_files=changed,
        commit_sha=commit_sha,
        branch_name=branch_name,
        report_path=report_md_path,
        report_json_path=report_json_path,
    )

    write_text(report_md_path, build_markdown_report(run_spec, rounds, outcome))
    write_json(
        report_json_path,
        {
            "run_spec": run_spec.model_dump(mode="json"),
            "rounds": [round_state.model_dump(mode="json") for round_state in rounds],
            "outcome": outcome.model_dump(mode="json"),
        },
    )

    return outcome


def _run_id(head_sha: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{head_sha[:8]}"


def _snapshot_changed_files(
    repo_root: Path,
    base_commit: str,
    changed_files_list: list[str],
    before_dir: Path,
    after_dir: Path,
) -> None:
    for relative_path in changed_files_list:
        source = repo_root / relative_path
        if source.exists():
            copy_file(source, after_dir / relative_path)

        before_content = show_file_at_commit(repo_root, base_commit, relative_path)
        if before_content is not None:
            destination = before_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(before_content, encoding="utf-8")


def _build_audit_snapshot(
    round_dir: Path,
    run_spec: RunSpec,
    implementer_report: ImplementerReport,
    cumulative_patch: str,
    round_patch: str,
    check_results: list,
    previous_findings: list[Finding],
) -> Path:
    snapshot_dir = ensure_dir(round_dir / "audit_snapshot")
    write_json(snapshot_dir / "run_spec.json", run_spec.model_dump(mode="json"))
    write_json(snapshot_dir / "implementer_report.json", implementer_report.model_dump(mode="json"))
    write_json(snapshot_dir / "previous_findings.json", [finding.model_dump(mode="json") for finding in previous_findings])
    write_text(snapshot_dir / "cumulative.patch", cumulative_patch)
    write_text(snapshot_dir / "round.patch", round_patch)
    write_json(snapshot_dir / "checks.json", _serialize_checks(check_results))

    source_before = round_dir / "before"
    source_after = round_dir / "after"
    if source_before.exists():
        for file_path in source_before.rglob("*"):
            if file_path.is_file():
                copy_file(file_path, snapshot_dir / "before" / safe_rel_path(file_path, source_before))
    if source_after.exists():
        for file_path in source_after.rglob("*"):
            if file_path.is_file():
                copy_file(file_path, snapshot_dir / "after" / safe_rel_path(file_path, source_after))
    return snapshot_dir


def _dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[str] = set()
    deduped: list[Finding] = []
    for finding in findings:
        fingerprint = finding.id or _finding_key(finding)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduped.append(finding)
    return deduped


def _serialize_checks(check_results: list[CommandResult]) -> list[dict[str, Any]]:
    return [result.model_dump(mode="json") | {"status": result.status.value} for result in check_results]


def _finding_key(finding: Finding) -> str:
    return "|".join((
        finding.severity.value,
        finding.title.strip().lower(),
        finding.file.strip().lower(),
        finding.evidence.strip().lower(),
    ))


def _findings_fingerprint(findings: list[Finding]) -> str:
    parts = sorted(_finding_key(finding) for finding in findings)
    return "|".join(parts)
