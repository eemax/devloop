from __future__ import annotations

import json

from devloop.json_protocol import BEGIN_MARKER, END_MARKER
from devloop.models import Finding, PlanSpec, RunSpec


def render_implementer_prompt(
    run_spec: RunSpec,
    plan: PlanSpec,
    unresolved_findings: list[Finding],
    previous_summary: str | None = None,
) -> str:
    findings_json = json.dumps([finding.model_dump(mode="json") for finding in unresolved_findings], indent=2)
    previous = previous_summary or "No previous implementer summary."

    return f"""You are the implementer for a devloop run.

Goal:
{run_spec.goal}

Acceptance criteria:
{_render_list(run_spec.acceptance_criteria)}

Constraints:
{_render_list(run_spec.constraints)}

Out of scope:
{_render_list(run_spec.out_of_scope)}

Plan body:
{plan.body}

Previous round summary:
{previous}

Unresolved findings:
{findings_json}

Make the smallest reasonable set of code changes in the live repository to satisfy the plan.
If you run checks yourself, mention them in your structured report.
Return a short prose note followed by a JSON object wrapped with these exact markers:
{BEGIN_MARKER}
<json>
{END_MARKER}

Use this JSON schema:
{{
  "summary": "string",
  "files_touched": ["string"],
  "criteria_status": [{{"criterion": "string", "status": "done|partial|not_done"}}],
  "checks_attempted": [{{"name": "string", "status": "pass|fail|not_run"}}],
  "known_risks": ["string"],
  "notes_for_auditor": ["string"]
}}
"""


def render_auditor_prompt(
    run_spec: RunSpec,
    unresolved_findings: list[Finding],
) -> str:
    findings_json = json.dumps([finding.model_dump(mode="json") for finding in unresolved_findings], indent=2)
    return f"""You are the auditor for a devloop run.

Audit the implementation strictly against the run goal, acceptance criteria, constraints, and available artifacts in the current working directory.

Goal:
{run_spec.goal}

Acceptance criteria:
{_render_list(run_spec.acceptance_criteria)}

Constraints:
{_render_list(run_spec.constraints)}

Out of scope:
{_render_list(run_spec.out_of_scope)}

Previously unresolved findings:
{findings_json}

Review the provided diffs, changed files, and check outputs. Do not assume facts not present in the artifacts.
Return a short prose note followed by a JSON object wrapped with these exact markers:
{BEGIN_MARKER}
<json>
{END_MARKER}

Use this JSON schema:
{{
  "summary": "string",
  "decision": "approve|needs_changes",
  "findings": [
    {{
      "id": "string",
      "severity": "blocking|major|minor|info",
      "title": "string",
      "file": "string",
      "evidence": "string",
      "fix_hint": "string",
      "confidence": 0.0
    }}
  ],
  "missing_tests": ["string"]
}}
"""


def _render_list(items: list[str]) -> str:
    if not items:
        return "- None specified"
    return "\n".join(f"- {item}" for item in items)
