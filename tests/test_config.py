from pathlib import Path

import pytest

from devloop.config import load_config
from devloop.config import ConfigError


def test_load_config_parses_example(tmp_path: Path) -> None:
    config_path = tmp_path / "devloop.toml"
    config_path.write_text(
        """
[run]
repo = "."

[agents.implementer]
name = "claude"
command = ["claude", "-p"]

[agents.auditor]
name = "codex"
command = ["codex", "exec"]
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.run.max_rounds == 2
    assert config.implementer.name == "claude"
    assert config.auditor.command == ["codex", "exec"]


def test_load_config_requires_both_agents(tmp_path: Path) -> None:
    config_path = tmp_path / "devloop.toml"
    config_path.write_text(
        """
[run]
repo = "."

[agents.implementer]
name = "claude"
command = ["claude", "-p"]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="missing required agent config entries: auditor"):
        load_config(config_path)


def test_load_config_rejects_invalid_values(tmp_path: Path) -> None:
    config_path = tmp_path / "devloop.toml"
    config_path.write_text(
        """
[run]
repo = "."
max_rounds = 0

[agents.implementer]
name = "claude"
command = ["claude", "-p"]

[agents.auditor]
name = "codex"
command = ["codex", "exec"]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="max_rounds"):
        load_config(config_path)


def test_load_config_missing_file_raises_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config file not found"):
        load_config(tmp_path / "missing.toml")


def test_load_config_invalid_toml_raises_error(tmp_path: Path) -> None:
    config_path = tmp_path / "devloop.toml"
    config_path.write_text("[run\nrepo = \".\"\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(config_path)
