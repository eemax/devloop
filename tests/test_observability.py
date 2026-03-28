from pathlib import Path

from devloop.observability import invocation_id_for_round, text_capture, thread_id_for_role, trace_id_for_run, truncate_text


def test_truncate_text_marks_omitted_chars() -> None:
    result = truncate_text("abcdefghij", 4)

    assert result == {
        "text": "abcd...[truncated +6 chars]",
        "truncated": True,
        "original_chars": 10,
        "omitted_chars": 6,
    }


def test_text_capture_includes_relative_path_and_hash(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    path = artifact_root / "rounds" / "01" / "stdout.txt"
    payload = text_capture("hello", path, artifact_root, 20)

    assert payload["path"] == "rounds/01/stdout.txt"
    assert payload["text"] == "hello"
    assert payload["truncated"] is False
    assert payload["original_chars"] == 5
    assert payload["sha256"]


def test_trace_helpers_produce_stable_ids() -> None:
    trace_id = trace_id_for_run("20260328-120000-deadbeef")

    assert trace_id == "devloop:20260328-120000-deadbeef"
    assert thread_id_for_role(trace_id, "implementer") == "devloop:20260328-120000-deadbeef:implementer"
    assert invocation_id_for_round(trace_id, "auditor", 2) == "devloop:20260328-120000-deadbeef:auditor:round:02"
