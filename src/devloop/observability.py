from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from devloop.artifacts import safe_rel_path
from devloop.models import AgentInvocationResult, RunOutcome, RoundState, RunSpec


def trace_id_for_run(run_id: str) -> str:
    return f"devloop:{run_id}"


def thread_id_for_role(trace_id: str, role: str) -> str:
    return f"{trace_id}:{role}"


def invocation_id_for_round(trace_id: str, role: str, round_number: int) -> str:
    return f"{thread_id_for_role(trace_id, role)}:round:{round_number:02d}"


def cli_name(command: list[str], resolved_command: str | None) -> str:
    candidate = resolved_command or (command[0] if command else "")
    return Path(candidate).name if candidate else ""


def truncate_text(text: str, max_chars: int) -> dict[str, Any]:
    original_chars = len(text)
    omitted_chars = max(0, original_chars - max_chars)
    if omitted_chars == 0:
        return {
            "text": text,
            "truncated": False,
            "original_chars": original_chars,
            "omitted_chars": 0,
        }

    prefix = text[:max_chars]
    return {
        "text": f"{prefix}...[truncated +{omitted_chars} chars]",
        "truncated": True,
        "original_chars": original_chars,
        "omitted_chars": omitted_chars,
    }


def text_capture(text: str, path: Path, artifact_root: Path, max_chars: int) -> dict[str, Any]:
    preview = truncate_text(text, max_chars)
    return {
        "path": safe_rel_path(path, artifact_root),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        **preview,
    }


def build_agent_invocation_artifact(
    *,
    role: str,
    round_number: int,
    trace_id: str,
    result: AgentInvocationResult,
    prompt: str,
    prompt_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    artifact_root: Path,
    max_inline_text_chars: int,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "thread_id": thread_id_for_role(trace_id, role),
        "invocation_id": invocation_id_for_round(trace_id, role, round_number),
        "round_number": round_number,
        "role": role,
        "name": result.name,
        "transport": "cli_subprocess",
        "cli_name": cli_name(result.command, result.resolved_command),
        "command": result.command,
        "resolved_command": result.resolved_command,
        "cwd": str(result.cwd),
        "input_mode": result.input_mode.value,
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "duration_secs": result.duration_secs,
        "exit_code": result.exit_code,
        "json_payload": result.json_payload,
        "prompt": text_capture(prompt, prompt_path, artifact_root, max_inline_text_chars),
        "stdout": text_capture(result.stdout, stdout_path, artifact_root, max_inline_text_chars),
        "stderr": text_capture(result.stderr, stderr_path, artifact_root, max_inline_text_chars),
    }


def build_report_payload(run_spec: RunSpec, rounds: list[RoundState], outcome: RunOutcome) -> dict[str, Any]:
    round_payloads = []
    for round_state in rounds:
        round_id = f"{round_state.round_number:02d}"
        round_payloads.append(
            {
                "round_number": round_state.round_number,
                "changed_files": round_state.changed_files,
                "implementer_report": round_state.implementer_report.model_dump(mode="json"),
                "audit_report": round_state.audit_report.model_dump(mode="json"),
                "implementer_result": _report_agent_result(
                    round_state.implementer_result,
                    trace_id=run_spec.trace_id,
                    artifact_dir=run_spec.artifact_dir,
                    round_id=round_id,
                    role="implementer",
                    max_inline_text_chars=run_spec.observability.max_inline_text_chars,
                ),
                "audit_result": _report_agent_result(
                    round_state.audit_result,
                    trace_id=run_spec.trace_id,
                    artifact_dir=run_spec.artifact_dir,
                    round_id=round_id,
                    role="auditor",
                    max_inline_text_chars=run_spec.observability.max_inline_text_chars,
                ),
                "checks": [check.model_dump(mode="json") | {"status": check.status.value} for check in round_state.checks],
                "blocking_findings": [finding.model_dump(mode="json") for finding in round_state.blocking_findings],
                "diff_changed": round_state.diff_changed,
            }
        )

    return {
        "run_spec": run_spec.model_dump(mode="json"),
        "trace": build_trace_manifest(run_spec, rounds),
        "rounds": round_payloads,
        "outcome": outcome.model_dump(mode="json"),
    }


def build_trace_manifest(run_spec: RunSpec, rounds: list[RoundState]) -> dict[str, Any]:
    threads = []
    for role, agent_name, command in (
        ("implementer", run_spec.implementer.name, run_spec.implementer.command),
        ("auditor", run_spec.auditor.name, run_spec.auditor.command),
    ):
        thread_id = thread_id_for_role(run_spec.trace_id, role)
        invocations = []
        for round_state in rounds:
            round_id = f"{round_state.round_number:02d}"
            invocations.append(
                {
                    "round_number": round_state.round_number,
                    "invocation_id": invocation_id_for_round(run_spec.trace_id, role, round_state.round_number),
                    "artifact": safe_rel_path(
                        run_spec.artifact_dir / "rounds" / round_id / f"{role}_invocation.json",
                        run_spec.artifact_dir,
                    ),
                }
            )
        threads.append(
            {
                "role": role,
                "thread_id": thread_id,
                "agent_name": agent_name,
                "transport": "cli_subprocess",
                "cli_name": Path(command[0]).name if command else "",
                "invocations": invocations,
            }
        )

    return {
        "trace_id": run_spec.trace_id,
        "run_id": run_spec.run_id,
        "threads": threads,
    }


def _report_agent_result(
    result: AgentInvocationResult,
    *,
    trace_id: str,
    artifact_dir: Path,
    round_id: str,
    role: str,
    max_inline_text_chars: int,
) -> dict[str, Any]:
    round_dir = artifact_dir / "rounds" / round_id
    stdout_path = round_dir / f"{role}_stdout.txt"
    stderr_path = round_dir / f"{role}_stderr.txt"
    prompt_path = round_dir / f"{role}_prompt.txt"
    invocation_path = round_dir / f"{role}_invocation.json"
    round_number = int(round_id)
    return {
        "trace_id": trace_id,
        "thread_id": thread_id_for_role(trace_id, role),
        "invocation_id": invocation_id_for_round(trace_id, role, round_number),
        "round_number": round_number,
        "name": result.name,
        "transport": "cli_subprocess",
        "cli_name": cli_name(result.command, result.resolved_command),
        "command": result.command,
        "resolved_command": result.resolved_command,
        "cwd": str(result.cwd),
        "input_mode": result.input_mode.value,
        "exit_code": result.exit_code,
        "duration_secs": result.duration_secs,
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "json_payload": result.json_payload,
        "prompt_artifact": safe_rel_path(prompt_path, artifact_dir),
        "invocation_artifact": safe_rel_path(invocation_path, artifact_dir),
        "stdout": text_capture(result.stdout, stdout_path, artifact_dir, max_inline_text_chars),
        "stderr": text_capture(result.stderr, stderr_path, artifact_dir, max_inline_text_chars),
    }
