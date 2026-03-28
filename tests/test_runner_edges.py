import sys
from pathlib import Path

import pytest

from devloop.config import load_config
from devloop.plan_parser import load_plan
from devloop.runner import RunnerError, run_devloop
from tests.helpers import build_config_text, git, init_git_repo, write_plan, write_script


def test_run_devloop_commits_and_creates_branch_on_success(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)
    implementer = write_script(
        tmp_path / "implementer.py",
        """
        import json
        from pathlib import Path

        Path("hello.txt").write_text("hello\\n", encoding="utf-8")
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({
            "summary": "created hello",
            "files_touched": ["hello.txt"],
            "criteria_status": [],
            "checks_attempted": [],
            "known_risks": [],
            "notes_for_auditor": []
        }))
        print("DEVLOOP_JSON_END")
        """,
    )
    auditor = write_script(
        tmp_path / "auditor.py",
        """
        import json
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({
            "summary": "approved",
            "decision": "approve",
            "findings": [],
            "missing_tests": []
        }))
        print("DEVLOOP_JSON_END")
        """,
    )
    config_path = tmp_path / "devloop.toml"
    config_path.write_text(
        build_config_text(
            repo,
            [sys.executable, str(implementer)],
            [sys.executable, str(auditor)],
            commit_on_success=True,
            create_branch=True,
            required_checks=[
                {
                    "name": "hello-check",
                    "command": f"{sys.executable} -c \"from pathlib import Path; raise SystemExit(0 if Path('hello.txt').exists() else 1)\"",
                    "timeout_secs": 30,
                }
            ],
        ),
        encoding="utf-8",
    )
    plan_path = write_plan(tmp_path / "plan.md", "# Create hello file\n")

    outcome = run_devloop(load_config(config_path), load_plan(plan_path))

    assert outcome.status.value == "success"
    assert outcome.commit_sha is not None
    assert outcome.branch_name is not None
    assert git(repo, "branch", "--show-current") == outcome.branch_name
    assert git(repo, "rev-parse", "HEAD") == outcome.commit_sha


def test_run_devloop_raises_when_implementer_payload_is_missing(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)
    implementer = write_script(tmp_path / "implementer.py", "print('no markers')")
    auditor = write_script(
        tmp_path / "auditor.py",
        """
        import json
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({"summary": "ok", "decision": "approve", "findings": [], "missing_tests": []}))
        print("DEVLOOP_JSON_END")
        """,
    )
    config_path = tmp_path / "devloop.toml"
    config_path.write_text(
        build_config_text(repo, [sys.executable, str(implementer)], [sys.executable, str(auditor)]),
        encoding="utf-8",
    )
    plan_path = write_plan(tmp_path / "plan.md")

    with pytest.raises(RunnerError, match="implementer did not return a valid structured JSON payload"):
        run_devloop(load_config(config_path), load_plan(plan_path))


def test_run_devloop_fails_when_blocking_findings_remain(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)
    implementer = write_script(
        tmp_path / "implementer.py",
        """
        import json
        from pathlib import Path

        Path("hello.txt").write_text("hello\\n", encoding="utf-8")
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({
            "summary": "created hello",
            "files_touched": ["hello.txt"],
            "criteria_status": [],
            "checks_attempted": [],
            "known_risks": [],
            "notes_for_auditor": []
        }))
        print("DEVLOOP_JSON_END")
        """,
    )
    auditor = write_script(
        tmp_path / "auditor.py",
        """
        import json
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({
            "summary": "needs changes",
            "decision": "needs_changes",
            "findings": [{
                "id": "blk-1",
                "severity": "blocking",
                "title": "Missing safety",
                "file": "hello.txt",
                "evidence": "Needs extra safety",
                "fix_hint": "Add safety",
                "confidence": 0.9
            }],
            "missing_tests": []
        }))
        print("DEVLOOP_JSON_END")
        """,
    )
    config_path = tmp_path / "devloop.toml"
    config_path.write_text(
        build_config_text(
            repo,
            [sys.executable, str(implementer)],
            [sys.executable, str(auditor)],
            max_rounds=1,
            required_checks=[
                {
                    "name": "hello-check",
                    "command": f"{sys.executable} -c \"from pathlib import Path; raise SystemExit(0 if Path('hello.txt').exists() else 1)\"",
                    "timeout_secs": 30,
                }
            ],
        ),
        encoding="utf-8",
    )
    plan_path = write_plan(tmp_path / "plan.md", "# Create hello file\n")

    outcome = run_devloop(load_config(config_path), load_plan(plan_path))

    assert outcome.status.value == "failed"
    assert len(outcome.final_findings) == 1
    assert outcome.final_findings[0].severity.value == "blocking"


def test_run_devloop_stalls_when_no_material_diff_is_created(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)
    implementer = write_script(
        tmp_path / "implementer.py",
        """
        import json
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({
            "summary": "did nothing",
            "files_touched": [],
            "criteria_status": [],
            "checks_attempted": [],
            "known_risks": [],
            "notes_for_auditor": []
        }))
        print("DEVLOOP_JSON_END")
        """,
    )
    auditor = write_script(
        tmp_path / "auditor.py",
        """
        import json
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({
            "summary": "approve",
            "decision": "approve",
            "findings": [],
            "missing_tests": []
        }))
        print("DEVLOOP_JSON_END")
        """,
    )
    config_path = tmp_path / "devloop.toml"
    config_path.write_text(
        build_config_text(repo, [sys.executable, str(implementer)], [sys.executable, str(auditor)], max_rounds=1),
        encoding="utf-8",
    )
    plan_path = write_plan(tmp_path / "plan.md", "# Do nothing\n")

    outcome = run_devloop(load_config(config_path), load_plan(plan_path))

    assert outcome.status.value == "stalled"
