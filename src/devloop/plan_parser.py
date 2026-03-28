from __future__ import annotations

from pathlib import Path

from devloop.models import PlanSpec


def load_plan(path: Path) -> PlanSpec:
    text = path.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in text.splitlines()]

    goal = ""
    acceptance_criteria: list[str] = []
    constraints: list[str] = []
    out_of_scope: list[str] = []
    checks: list[str] = []

    current: str | None = None

    sections: dict[str, list[str]] = {
        "acceptance_criteria": acceptance_criteria,
        "constraints": constraints,
        "out_of_scope": out_of_scope,
        "checks": checks,
    }
    section_headers: dict[str, str] = {
        "acceptance criteria:": "acceptance_criteria",
        "constraints:": "constraints",
        "out of scope:": "out_of_scope",
        "checks:": "checks",
    }

    for raw_line in lines:
        line = raw_line.strip()
        lower = line.lower()

        if line.startswith("# ") and not goal:
            goal = line[2:].strip()
            continue

        if lower.startswith("goal:"):
            goal = line.split(":", 1)[1].strip()
            current = None
            continue

        matched = False
        for header, section_name in section_headers.items():
            if lower.startswith(header):
                current = section_name
                remainder = line.split(":", 1)[1].strip()
                if remainder:
                    sections[section_name].append(remainder)
                matched = True
                break
        if matched:
            continue

        if line.startswith(("-", "*")) and current and current in sections:
            item = line[1:].strip()
            if item:
                sections[current].append(item)

    if not goal:
        non_empty = [line for line in lines if line.strip()]
        goal = non_empty[0].lstrip("# ").strip() if non_empty else "Untitled devloop run"

    return PlanSpec(
        goal=goal,
        acceptance_criteria=acceptance_criteria,
        constraints=constraints,
        out_of_scope=out_of_scope,
        checks=checks,
        body=text,
        source_path=path,
    )
