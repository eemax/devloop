import json
import sys
from pathlib import Path

from devloop.config import load_config
from devloop.plan_parser import load_plan
from devloop.runner import run_devloop
from tests.helpers import build_config_text, init_git_repo, write_plan, write_script


def test_run_devloop_writes_invocation_artifacts_with_truncated_inline_text(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)
    implementer = write_script(
        tmp_path / "implementer.py",
        """
        import json
        from pathlib import Path

        Path("hello.txt").write_text("hello from implementer\\n", encoding="utf-8")
        print("implementer-" + ("x" * 40))
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({
            "summary": "created hello.txt",
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
        import sys

        print("auditor-" + ("y" * 40), file=sys.stderr)
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({
            "summary": "looks good",
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
            observability_max_inline_text_chars=12,
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

    outcome = run_devloop(load_config(config_path), load_plan(plan_path))
    artifact_dir = outcome.report_json_path.parent

    run_spec = json.loads((artifact_dir / "run_spec.json").read_text(encoding="utf-8"))
    trace_manifest = json.loads((artifact_dir / "trace.json").read_text(encoding="utf-8"))
    implementer_invocation = json.loads((artifact_dir / "rounds" / "01" / "implementer_invocation.json").read_text(encoding="utf-8"))
    auditor_invocation = json.loads((artifact_dir / "rounds" / "01" / "auditor_invocation.json").read_text(encoding="utf-8"))
    report_payload = json.loads(outcome.report_json_path.read_text(encoding="utf-8"))

    assert run_spec["observability"]["max_inline_text_chars"] == 12
    assert run_spec["trace_id"].startswith("devloop:")
    assert trace_manifest["trace_id"] == run_spec["trace_id"]
    assert trace_manifest["run_id"] == run_spec["run_id"]
    assert trace_manifest["threads"][0]["thread_id"] == f"{run_spec['trace_id']}:implementer"
    assert trace_manifest["threads"][1]["thread_id"] == f"{run_spec['trace_id']}:auditor"
    assert trace_manifest["threads"][0]["invocations"][0]["artifact"] == "rounds/01/implementer_invocation.json"

    assert implementer_invocation["command"] == [sys.executable, str(implementer)]
    assert implementer_invocation["resolved_command"]
    assert implementer_invocation["transport"] == "cli_subprocess"
    assert implementer_invocation["cli_name"] == Path(sys.executable).name
    assert implementer_invocation["input_mode"] == "stdin"
    assert implementer_invocation["trace_id"] == run_spec["trace_id"]
    assert implementer_invocation["thread_id"] == f"{run_spec['trace_id']}:implementer"
    assert implementer_invocation["invocation_id"] == f"{run_spec['trace_id']}:implementer:round:01"
    assert implementer_invocation["prompt"]["path"] == "rounds/01/implementer_prompt.txt"
    assert implementer_invocation["prompt"]["truncated"] is True
    assert implementer_invocation["stdout"]["path"] == "rounds/01/implementer_stdout.txt"
    assert implementer_invocation["stdout"]["text"].endswith("...[truncated +" + str(implementer_invocation["stdout"]["omitted_chars"]) + " chars]")
    assert implementer_invocation["stdout"]["truncated"] is True

    assert auditor_invocation["trace_id"] == run_spec["trace_id"]
    assert auditor_invocation["thread_id"] == f"{run_spec['trace_id']}:auditor"
    assert auditor_invocation["invocation_id"] == f"{run_spec['trace_id']}:auditor:round:01"
    assert auditor_invocation["stderr"]["path"] == "rounds/01/auditor_stderr.txt"
    assert auditor_invocation["stderr"]["truncated"] is True

    full_stdout = (artifact_dir / "rounds" / "01" / "implementer_stdout.txt").read_text(encoding="utf-8")
    full_prompt = (artifact_dir / "rounds" / "01" / "implementer_prompt.txt").read_text(encoding="utf-8")
    assert "implementer-" + ("x" * 40) in full_stdout
    assert "Acceptance criteria:" in full_prompt

    report_round = report_payload["rounds"][0]
    assert report_payload["trace"]["trace_id"] == run_spec["trace_id"]
    assert report_round["implementer_result"]["invocation_artifact"] == "rounds/01/implementer_invocation.json"
    assert report_round["implementer_result"]["trace_id"] == run_spec["trace_id"]
    assert report_round["implementer_result"]["thread_id"] == f"{run_spec['trace_id']}:implementer"
    assert report_round["implementer_result"]["stdout"]["truncated"] is True
    assert report_round["audit_result"]["thread_id"] == f"{run_spec['trace_id']}:auditor"
    assert report_round["audit_result"]["stderr"]["truncated"] is True
