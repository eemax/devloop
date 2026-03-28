from pathlib import Path

from devloop.models import AgentConfig, Finding, FindingSeverity, PlanSpec, RunSpec
from devloop.prompts import render_auditor_prompt, render_implementer_prompt


def test_render_implementer_prompt_includes_markers_and_findings() -> None:
    run_spec = _run_spec()
    plan = _plan()
    findings = [Finding(id="f1", severity=FindingSeverity.BLOCKING, title="Bug", file="app.py", evidence="Broken")]

    prompt = render_implementer_prompt(run_spec, plan, findings, previous_summary="Tried a first pass")

    assert "You are the implementer" in prompt
    assert "Tried a first pass" in prompt
    assert "DEVLOOP_JSON_BEGIN" in prompt
    assert '"id": "f1"' in prompt
    assert "- ship it" in prompt


def test_render_auditor_prompt_includes_constraints_and_schema() -> None:
    run_spec = _run_spec()
    findings = [Finding(id="f2", severity=FindingSeverity.MINOR, title="Note", evidence="Missing note")]

    prompt = render_auditor_prompt(run_spec, findings)

    assert "You are the auditor" in prompt
    assert "- stay narrow" in prompt
    assert '"severity": "blocking|major|minor|info"' in prompt
    assert "DEVLOOP_JSON_END" in prompt


def _run_spec() -> RunSpec:
    return RunSpec(
        run_id="run-1",
        repo_root=Path("/tmp/repo"),
        base_commit="abc123",
        artifact_dir=Path("/tmp/repo/.devloop/runs/run-1"),
        goal="Ship it",
        acceptance_criteria=["ship it"],
        constraints=["stay narrow"],
        out_of_scope=["rewrite everything"],
        checks=["pytest -q"],
        max_rounds=2,
        commit_on_success=False,
        create_branch=False,
        branch_prefix="codex/devloop",
        implementer=AgentConfig(name="impl", command=["impl"]),
        auditor=AgentConfig(name="audit", command=["audit"]),
        plan_path=Path("/tmp/repo/plan.md"),
        raw_plan="# plan",
    )


def _plan() -> PlanSpec:
    return PlanSpec(
        goal="Ship it",
        acceptance_criteria=["ship it"],
        constraints=["stay narrow"],
        out_of_scope=["rewrite everything"],
        checks=["pytest -q"],
        body="# Ship it",
        source_path=Path("/tmp/repo/plan.md"),
    )
