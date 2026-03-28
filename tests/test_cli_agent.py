import sys
from pathlib import Path

from devloop.adapters.cli_agent import CliAgentAdapter
from devloop.models import AgentConfig, InputMode
from tests.helpers import write_script


def test_cli_agent_adapter_reads_json_from_stdout(tmp_path: Path) -> None:
    script = write_script(
        tmp_path / "agent.py",
        """
        import json
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({"summary": "ok"}))
        print("DEVLOOP_JSON_END")
        """,
    )
    adapter = CliAgentAdapter(AgentConfig(name="agent", command=[sys.executable, str(script)]), timeout_secs=10)

    result = adapter.run("prompt", cwd=tmp_path)

    assert result.exit_code == 0
    assert result.json_payload == {"summary": "ok"}


def test_cli_agent_adapter_supports_file_input_mode(tmp_path: Path) -> None:
    script = write_script(
        tmp_path / "agent.py",
        """
        import json
        import sys
        from pathlib import Path

        prompt = Path(sys.argv[1]).read_text(encoding="utf-8")
        print("saw:", prompt.strip())
        print("DEVLOOP_JSON_BEGIN")
        print(json.dumps({"summary": prompt.strip()}))
        print("DEVLOOP_JSON_END")
        """,
    )
    adapter = CliAgentAdapter(
        AgentConfig(name="agent", command=[sys.executable, str(script)], input_mode=InputMode.FILE),
        timeout_secs=10,
    )
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("from file\n", encoding="utf-8")

    result = adapter.run("from file\n", cwd=tmp_path, prompt_path=prompt_path)

    assert result.exit_code == 0
    assert result.json_payload == {"summary": "from file"}


def test_cli_agent_adapter_leaves_json_payload_empty_without_markers(tmp_path: Path) -> None:
    script = write_script(tmp_path / "agent.py", "print('plain text only')")
    adapter = CliAgentAdapter(AgentConfig(name="agent", command=[sys.executable, str(script)]), timeout_secs=10)

    result = adapter.run("prompt", cwd=tmp_path)

    assert result.exit_code == 0
    assert result.json_payload is None
