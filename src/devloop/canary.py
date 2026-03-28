from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from devloop.artifacts import ensure_dir, write_text
from devloop.config import load_config
from devloop.git_ops import GitError, ensure_clean_worktree, ensure_git_repo
from devloop.models import RunOutcome
from devloop.plan_parser import load_plan
from devloop.runner import run_devloop
from devloop.subprocess_utils import run_command

CANARY_README = """# Canary Repo

This repository is used for a disposable devloop canary run.
"""

CANARY_GITIGNORE = ".devloop/\n"
CANARY_MARKER = "canary: devloop ok"

CANARY_PLAN = """# Add canary marker

Acceptance criteria:
- README.md contains the exact line `canary: devloop ok`

Constraints:
- Only edit README.md

Checks:
- python3 -c "from pathlib import Path; text = Path('README.md').read_text(encoding='utf-8'); raise SystemExit(0 if 'canary: devloop ok' in text else 1)"
"""

DEFAULT_IMPLEMENTER_COMMAND = ["claude", "-p", "--permission-mode", "bypassPermissions"]
DEFAULT_AUDITOR_COMMAND = ["codex", "exec", "--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox"]
CANARY_CHECK_SCRIPT = (
    "from pathlib import Path; "
    "text = Path('README.md').read_text(encoding='utf-8'); "
    f"raise SystemExit(0 if {CANARY_MARKER!r} in text else 1)"
)
CANARY_CHECK_COMMAND = f"python3 -c {json.dumps(CANARY_CHECK_SCRIPT)}"


@dataclass(frozen=True)
class CanaryWorkspace:
    root: Path
    repo: Path
    config_path: Path
    plan_path: Path


def default_canary_root() -> Path:
    return Path.home() / ".devloop-canary"


def prepare_canary_workspace(root: Path, *, reset: bool = False) -> CanaryWorkspace:
    root = root.expanduser().resolve()
    repo = root / "repo"
    config_path = root / "config.toml"
    plan_path = root / "plan.md"

    if reset and root.exists():
        shutil.rmtree(root)

    ensure_dir(root)
    ensure_dir(repo)

    if not (repo / ".git").exists():
        _init_repo(repo)
        _write_repo_baseline(repo)
        _git(repo, "add", "README.md", ".gitignore")
        _git(repo, "commit", "-m", "init canary repo")
    else:
        ensure_git_repo(repo)
        try:
            ensure_clean_worktree(repo)
        except GitError as exc:
            raise GitError("canary workspace has uncommitted changes; rerun with --reset to recreate it") from exc
        _ensure_repo_baseline(repo)

    write_text(config_path, build_canary_config(repo))
    write_text(plan_path, CANARY_PLAN)
    return CanaryWorkspace(root=root, repo=repo, config_path=config_path, plan_path=plan_path)


def run_canary(root: Path, *, reset: bool = False) -> tuple[CanaryWorkspace, RunOutcome]:
    workspace = prepare_canary_workspace(root, reset=reset)
    outcome = run_devloop(load_config(workspace.config_path), load_plan(workspace.plan_path))
    return workspace, outcome


def build_canary_config(repo: Path) -> str:
    lines = [
        "[run]",
        f"repo = {json.dumps(str(repo))}",
        "max_rounds = 1",
        "commit_on_success = false",
        "create_branch = false",
        'branch_prefix = "codex/devloop"',
        "require_clean_worktree = true",
        'artifact_dir = ".devloop/runs"',
        "timeout_secs = 1800",
        "",
        "[agents.implementer]",
        'name = "claude"',
        f"command = {json.dumps(DEFAULT_IMPLEMENTER_COMMAND)}",
        'input_mode = "stdin"',
        'cwd_mode = "repo"',
        "",
        "[agents.auditor]",
        'name = "codex"',
        f"command = {json.dumps(DEFAULT_AUDITOR_COMMAND)}",
        'input_mode = "stdin"',
        'cwd_mode = "snapshot"',
        "",
        "[observability]",
        "max_inline_text_chars = 4000",
        "",
        "[[checks.required]]",
        'name = "readme-canary"',
        f"command = {json.dumps(CANARY_CHECK_COMMAND)}",
        "timeout_secs = 30",
    ]
    return "\n".join(lines) + "\n"


def _init_repo(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.name", "Devloop Canary")
    _git(repo, "config", "user.email", "canary@example.com")


def _write_repo_baseline(repo: Path) -> None:
    write_text(repo / "README.md", CANARY_README)
    write_text(repo / ".gitignore", CANARY_GITIGNORE)


def _ensure_repo_baseline(repo: Path) -> None:
    readme = repo / "README.md"
    gitignore = repo / ".gitignore"
    if not readme.exists() or readme.read_text(encoding="utf-8") != CANARY_README:
        raise GitError("canary repo does not match the expected README baseline; rerun with --reset to recreate it")
    if not gitignore.exists() or gitignore.read_text(encoding="utf-8") != CANARY_GITIGNORE:
        raise GitError("canary repo does not match the expected .gitignore baseline; rerun with --reset to recreate it")


def _git(repo: Path, *args: str) -> str:
    completed = run_command(["git", *args], cwd=repo, timeout_secs=30)
    if completed.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()
