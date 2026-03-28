import sys
from pathlib import Path

from devloop.config import load_config
from devloop.plan_parser import load_plan
from devloop.runner import run_devloop
from tests.helpers import build_config_text, init_git_repo, write_plan, write_script


def test_run_devloop_smoke(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)

    implementer = write_script(
        tmp_path / "implementer.py",
        """
        import json
        from pathlib import Path

        Path("hello.txt").write_text("hello from implementer\\n", encoding="utf-8")
        payload = {
            "summary": "created hello.txt",
            "files_touched": ["hello.txt"],
            "criteria_status": [],
            "checks_attempted": [],
            "known_risks": [],
            "notes_for_auditor": []
        }
        print("Implementer complete")
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps(payload))
        print("DEVLOOP_JSON_END")
        """,
    )

    auditor = write_script(
        tmp_path / "auditor.py",
        """
        import json

        payload = {
            "summary": "looks good",
            "decision": "approve",
            "findings": [],
            "missing_tests": []
        }
        print("Auditor complete")
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps(payload))
        print("DEVLOOP_JSON_END")
        """,
    )

    config_path = tmp_path / "devloop.toml"
    config_path.write_text(
        build_config_text(
            repo,
            [sys.executable, str(implementer)],
            [sys.executable, str(auditor)],
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

    plan_path = write_plan(tmp_path / "plan.md", "# Create hello file\n\nAcceptance criteria:\n- hello.txt exists\n")

    config = load_config(config_path)
    plan = load_plan(plan_path)
    outcome = run_devloop(config, plan)

    assert outcome.status.value == "success"
    assert "hello.txt" in outcome.changed_files
    assert outcome.report_path.exists()
    assert (repo / "hello.txt").read_text(encoding="utf-8") == "hello from implementer\n"
