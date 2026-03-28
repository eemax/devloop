from __future__ import annotations

import json
from typing import Any


BEGIN_MARKER = "DEVLOOP_JSON_BEGIN"
END_MARKER = "DEVLOOP_JSON_END"


class JsonProtocolError(RuntimeError):
    """Raised when structured output cannot be extracted."""


def extract_json_block(text: str) -> dict[str, Any]:
    begin = text.find(BEGIN_MARKER)
    end = text.find(END_MARKER)
    if begin == -1 or end == -1 or end <= begin:
        raise JsonProtocolError("missing structured JSON markers in agent output")

    payload = text[begin + len(BEGIN_MARKER) : end].strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise JsonProtocolError(f"invalid JSON payload between markers: {exc}") from exc


def wrap_json_block(payload: dict[str, Any]) -> str:
    return f"{BEGIN_MARKER}\n{json.dumps(payload, indent=2, sort_keys=True)}\n{END_MARKER}\n"
