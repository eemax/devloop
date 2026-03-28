import json
from pathlib import Path

from devloop.artifacts import copy_file, ensure_dir, safe_rel_path, write_json, write_text


def test_write_text_and_json_create_parent_directories(tmp_path: Path) -> None:
    text_path = tmp_path / "nested" / "note.txt"
    json_path = tmp_path / "nested" / "payload.json"

    write_text(text_path, "hello")
    write_json(json_path, {"ok": True})

    assert text_path.read_text(encoding="utf-8") == "hello"
    assert json.loads(json_path.read_text(encoding="utf-8")) == {"ok": True}


def test_copy_file_and_safe_rel_path(tmp_path: Path) -> None:
    source = tmp_path / "src.txt"
    source.write_text("content", encoding="utf-8")
    destination = tmp_path / "nested" / "dst.txt"

    copy_file(source, destination)

    assert destination.read_text(encoding="utf-8") == "content"
    assert safe_rel_path(destination, tmp_path) == "nested/dst.txt"
    assert safe_rel_path(destination, tmp_path / "elsewhere") == "dst.txt"


def test_ensure_dir_returns_created_path(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b"
    returned = ensure_dir(target)

    assert returned == target
    assert target.is_dir()
