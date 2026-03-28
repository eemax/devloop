from pathlib import Path

import pytest

from devloop.canary import (
    CANARY_GITIGNORE,
    CANARY_README,
    DEFAULT_AUDITOR_COMMAND,
    DEFAULT_IMPLEMENTER_COMMAND,
    prepare_canary_workspace,
)
from devloop.config import load_config
from devloop.git_ops import GitError
from tests.helpers import git


def test_prepare_canary_workspace_creates_clean_repo_and_loadable_config(tmp_path: Path) -> None:
    workspace = prepare_canary_workspace(tmp_path / "canary", reset=True)

    assert workspace.repo.exists()
    assert workspace.plan_path.exists()
    assert workspace.config_path.exists()
    assert (workspace.repo / "README.md").read_text(encoding="utf-8") == CANARY_README
    assert (workspace.repo / ".gitignore").read_text(encoding="utf-8") == CANARY_GITIGNORE
    assert git(workspace.repo, "status", "--porcelain") == ""

    config = load_config(workspace.config_path)
    assert config.run.repo == workspace.repo
    assert config.run.max_rounds == 1
    assert config.run.commit_on_success is False
    assert config.run.create_branch is False
    assert config.implementer.command == DEFAULT_IMPLEMENTER_COMMAND
    assert config.auditor.command == DEFAULT_AUDITOR_COMMAND
    assert config.checks.required[0].name == "readme-canary"
    assert "canary: devloop ok" in config.checks.required[0].command


def test_prepare_canary_workspace_requires_reset_when_repo_is_dirty(tmp_path: Path) -> None:
    workspace = prepare_canary_workspace(tmp_path / "canary", reset=True)
    (workspace.repo / "README.md").write_text("# changed\n", encoding="utf-8")

    with pytest.raises(GitError, match="rerun with --reset"):
        prepare_canary_workspace(workspace.root)


def test_prepare_canary_workspace_reset_recreates_baseline(tmp_path: Path) -> None:
    workspace = prepare_canary_workspace(tmp_path / "canary", reset=True)
    (workspace.repo / "README.md").write_text("# changed\n", encoding="utf-8")

    reset_workspace = prepare_canary_workspace(workspace.root, reset=True)

    assert (reset_workspace.repo / "README.md").read_text(encoding="utf-8") == CANARY_README
    assert git(reset_workspace.repo, "status", "--porcelain") == ""
