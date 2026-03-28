from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def init_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "Devloop Test")
    git(repo, "config", "user.email", "devloop@example.com")
    (repo / ".gitignore").write_text(".devloop/\n", encoding="utf-8")
    (repo / "README.md").write_text("# repo\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "init")
    return repo


def write_script(path: Path, content: str) -> Path:
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return path


def write_plan(path: Path, content: str | None = None) -> Path:
    body = content or """
    # Example plan

    Acceptance criteria:
    - Example criterion
    """
    path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")
    return path


def build_config_text(
    repo: Path,
    implementer_command: list[str],
    auditor_command: list[str],
    *,
    max_rounds: int = 2,
    commit_on_success: bool = False,
    create_branch: bool = False,
    require_clean_worktree: bool = True,
    branch_prefix: str = "codex/devloop",
    artifact_dir: str = ".devloop/runs",
    timeout_secs: int = 120,
    implementer_input_mode: str = "stdin",
    implementer_cwd_mode: str = "repo",
    auditor_input_mode: str = "stdin",
    auditor_cwd_mode: str = "snapshot",
    observability_max_inline_text_chars: int = 20_000,
    required_checks: list[dict[str, object]] | None = None,
    advisory_checks: list[dict[str, object]] | None = None,
) -> str:
    lines = [
        "[run]",
        f"repo = {json.dumps(str(repo))}",
        f"max_rounds = {max_rounds}",
        f"commit_on_success = {str(commit_on_success).lower()}",
        f"create_branch = {str(create_branch).lower()}",
        f"branch_prefix = {json.dumps(branch_prefix)}",
        f"require_clean_worktree = {str(require_clean_worktree).lower()}",
        f"artifact_dir = {json.dumps(artifact_dir)}",
        f"timeout_secs = {timeout_secs}",
        "",
        "[agents.implementer]",
        'name = "implementer"',
        f"command = {json.dumps(implementer_command)}",
        f"input_mode = {json.dumps(implementer_input_mode)}",
        f"cwd_mode = {json.dumps(implementer_cwd_mode)}",
        "",
        "[agents.auditor]",
        'name = "auditor"',
        f"command = {json.dumps(auditor_command)}",
        f"input_mode = {json.dumps(auditor_input_mode)}",
        f"cwd_mode = {json.dumps(auditor_cwd_mode)}",
        "",
        "[observability]",
        f"max_inline_text_chars = {observability_max_inline_text_chars}",
    ]

    for check in required_checks or []:
        lines.extend([
            "",
            "[[checks.required]]",
            f"name = {json.dumps(str(check['name']))}",
            f"command = {json.dumps(str(check['command']))}",
            f"timeout_secs = {int(check.get('timeout_secs', 300))}",
        ])

    for check in advisory_checks or []:
        lines.extend([
            "",
            "[[checks.advisory]]",
            f"name = {json.dumps(str(check['name']))}",
            f"command = {json.dumps(str(check['command']))}",
            f"timeout_secs = {int(check.get('timeout_secs', 300))}",
        ])

    return "\n".join(lines) + "\n"
