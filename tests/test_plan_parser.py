from pathlib import Path

from devloop.plan_parser import load_plan


def test_load_plan_parses_all_supported_sections(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(
        """
# Ship feature

Acceptance criteria:
- tests pass
- diff stays small

Constraints:
- do not touch unrelated files

Out of scope:
- refactoring

Checks:
- pytest -q
""".strip(),
        encoding="utf-8",
    )

    plan = load_plan(plan_path)

    assert plan.goal == "Ship feature"
    assert plan.acceptance_criteria == ["tests pass", "diff stays small"]
    assert plan.constraints == ["do not touch unrelated files"]
    assert plan.out_of_scope == ["refactoring"]
    assert plan.checks == ["pytest -q"]
    assert plan.source_path == plan_path


def test_load_plan_supports_inline_section_values(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(
        """
Goal: Inline goal
Acceptance criteria: first criterion
Constraints: stay narrow
Out of scope: broad rewrite
Checks: pytest -q
""".strip(),
        encoding="utf-8",
    )

    plan = load_plan(plan_path)

    assert plan.goal == "Inline goal"
    assert plan.acceptance_criteria == ["first criterion"]
    assert plan.constraints == ["stay narrow"]
    assert plan.out_of_scope == ["broad rewrite"]
    assert plan.checks == ["pytest -q"]


def test_load_plan_falls_back_to_first_non_empty_line(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.md"
    plan_path.write_text("\n\nImplement something useful\n\nMore detail\n", encoding="utf-8")

    plan = load_plan(plan_path)

    assert plan.goal == "Implement something useful"
    assert "More detail" in plan.body
