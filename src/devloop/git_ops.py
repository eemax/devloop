from __future__ import annotations

from pathlib import Path

from devloop.subprocess_utils import run_command


class GitError(RuntimeError):
    """Raised when git preconditions or commands fail."""


def ensure_git_repo(path: Path) -> Path:
    completed = run_command(["git", "rev-parse", "--show-toplevel"], cwd=path, timeout_secs=30)
    if completed.returncode != 0:
        raise GitError(f"current directory is not inside a git repository: {completed.stderr.strip()}")
    return Path(completed.stdout.strip())


def current_head(path: Path) -> str:
    completed = run_command(["git", "rev-parse", "HEAD"], cwd=path, timeout_secs=30)
    if completed.returncode != 0:
        raise GitError(f"failed to resolve HEAD: {completed.stderr.strip()}")
    return completed.stdout.strip()


def status_porcelain(path: Path) -> str:
    completed = run_command(["git", "status", "--porcelain"], cwd=path, timeout_secs=30)
    if completed.returncode != 0:
        raise GitError(f"failed to read git status: {completed.stderr.strip()}")
    return completed.stdout


def ensure_clean_worktree(path: Path) -> None:
    if status_porcelain(path).strip():
        raise GitError("worktree is dirty; commit or stash changes before running devloop")


def create_branch(path: Path, branch_name: str) -> None:
    completed = run_command(["git", "checkout", "-b", branch_name], cwd=path, timeout_secs=30)
    if completed.returncode != 0:
        raise GitError(f"failed to create branch {branch_name}: {completed.stderr.strip()}")


def changed_files(path: Path, base_commit: str) -> list[str]:
    completed = run_command(
        ["git", "diff", "--name-only", base_commit],
        cwd=path,
        timeout_secs=30,
    )
    if completed.returncode != 0:
        raise GitError(f"failed to read changed files: {completed.stderr.strip()}")
    tracked = {line.strip() for line in completed.stdout.splitlines() if line.strip()}
    return sorted(tracked | set(untracked_files(path)))


def diff_against(path: Path, base_commit: str) -> str:
    completed = run_command(["git", "diff", "--binary", base_commit], cwd=path, timeout_secs=60)
    if completed.returncode != 0:
        raise GitError(f"failed to compute git diff: {completed.stderr.strip()}")
    return completed.stdout + _untracked_diff(path)


def diff_worktree(path: Path) -> str:
    completed = run_command(["git", "diff", "--binary"], cwd=path, timeout_secs=60)
    if completed.returncode != 0:
        raise GitError(f"failed to compute worktree diff: {completed.stderr.strip()}")
    return completed.stdout + _untracked_diff(path)


def untracked_files(path: Path) -> list[str]:
    completed = run_command(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=path,
        timeout_secs=30,
    )
    if completed.returncode != 0:
        raise GitError(f"failed to list untracked files: {completed.stderr.strip()}")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def show_file_at_commit(path: Path, commit: str, file_path: str) -> str | None:
    completed = run_command(
        ["git", "show", f"{commit}:{file_path}"],
        cwd=path,
        timeout_secs=30,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def commit_all(path: Path, message: str) -> str:
    add_result = run_command(["git", "add", "-A"], cwd=path, timeout_secs=60)
    if add_result.returncode != 0:
        raise GitError(f"failed to stage changes: {add_result.stderr.strip()}")

    commit_result = run_command(["git", "commit", "-m", message], cwd=path, timeout_secs=60)
    if commit_result.returncode != 0:
        raise GitError(f"failed to create commit: {commit_result.stderr.strip()}")

    return current_head(path)


def _untracked_diff(path: Path) -> str:
    chunks: list[str] = []
    for file_path in untracked_files(path):
        completed = run_command(
            ["git", "diff", "--no-index", "--binary", "--", "/dev/null", file_path],
            cwd=path,
            timeout_secs=30,
        )
        if completed.returncode not in (0, 1):
            raise GitError(f"failed to compute diff for untracked file {file_path}: {completed.stderr.strip()}")
        chunks.append(completed.stdout)
    return "".join(chunks)
