from pathlib import Path

import pytest

from devloop.git_ops import (
    changed_files,
    commit_all,
    create_branch,
    current_head,
    diff_against,
    ensure_clean_worktree,
    ensure_git_repo,
    show_file_at_commit,
    status_porcelain,
    untracked_files,
)
from devloop.git_ops import GitError
from tests.helpers import git, init_git_repo


def test_git_repo_helpers_detect_repo_and_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)

    assert ensure_git_repo(repo) == repo
    assert len(current_head(repo)) == 40


def test_ensure_clean_worktree_raises_when_repo_is_dirty(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")

    with pytest.raises(GitError, match="worktree is dirty"):
        ensure_clean_worktree(repo)


def test_changed_files_and_diff_include_untracked_files(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)
    base = current_head(repo)
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")
    (repo / "hello.txt").write_text("hello\n", encoding="utf-8")

    files = changed_files(repo, base)
    diff = diff_against(repo, base)

    assert files == ["README.md", "hello.txt"]
    assert "hello.txt" in untracked_files(repo)
    assert "diff --git a/hello.txt b/hello.txt" in diff
    assert "changed" in diff


def test_create_branch_commit_all_and_show_file(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path)
    base = current_head(repo)

    create_branch(repo, "codex/devloop/test-branch")
    assert git(repo, "branch", "--show-current") == "codex/devloop/test-branch"

    (repo / "feature.txt").write_text("content\n", encoding="utf-8")
    commit_sha = commit_all(repo, "feat: add feature")

    assert commit_sha != base
    assert status_porcelain(repo) == ""
    assert show_file_at_commit(repo, commit_sha, "feature.txt") == "content\n"
