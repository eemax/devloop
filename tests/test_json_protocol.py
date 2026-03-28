import pytest

from devloop.json_protocol import JsonProtocolError, extract_json_block, wrap_json_block


def test_extract_json_block_round_trips() -> None:
    payload = {"summary": "ok", "findings": []}
    text = f"note\n{wrap_json_block(payload)}"

    assert extract_json_block(text) == payload


def test_extract_json_block_requires_markers() -> None:
    with pytest.raises(JsonProtocolError):
        extract_json_block("{}")
