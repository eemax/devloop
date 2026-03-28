from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from devloop.canary import default_canary_root, prepare_canary_workspace, run_canary
from devloop.config import ConfigError, load_config
from devloop.git_ops import GitError, ensure_git_repo
from devloop.plan_parser import load_plan
from devloop.report import report_paths
from devloop.runner import RunnerError, run_devloop
from devloop.subprocess_utils import CommandExecutionError, ensure_command_available


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="devloop", description="Run a two-agent implementation loop.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a devloop session.")
    run_parser.add_argument("--plan", type=Path, required=True, help="Path to the plan markdown file.")
    run_parser.add_argument("--config", type=Path, required=True, help="Path to the devloop TOML config.")

    validate_parser = subparsers.add_parser("validate-config", help="Validate a devloop config file.")
    validate_parser.add_argument("--config", type=Path, required=True, help="Path to the devloop TOML config.")

    doctor_parser = subparsers.add_parser("doctor", help="Check basic environment prerequisites.")
    doctor_parser.add_argument("--config", type=Path, required=True, help="Path to the devloop TOML config.")

    report_parser = subparsers.add_parser("report", help="Print a previously generated report.")
    report_parser.add_argument("run_dir", type=Path, help="Path to a run artifact directory.")

    resume_parser = subparsers.add_parser("resume", help="Resume a paused run.")
    resume_parser.add_argument("run_id", help="Run identifier.")

    canary_parser = subparsers.add_parser("canary", help="Prepare or run the disposable canary smoke test.")
    canary_parser.add_argument("--root", type=Path, default=default_canary_root(), help="Workspace root for the canary repo.")
    canary_parser.add_argument("--reset", action="store_true", help="Recreate the canary workspace from scratch before preparing it.")
    canary_parser.add_argument("--prepare-only", action="store_true", help="Only prepare the canary workspace; do not execute the run.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "run":
            config = load_config(args.config)
            plan = load_plan(args.plan)
            outcome = run_devloop(config, plan)
            print(f"devloop finished with status: {outcome.status.value}")
            print(f"report: {outcome.report_path}")
            print(f"report json: {outcome.report_json_path}")
            if outcome.commit_sha:
                print(f"commit: {outcome.commit_sha}")
            return 0 if outcome.status.value == "success" else 3

        if args.command == "validate-config":
            load_config(args.config)
            print(f"config OK: {args.config}")
            return 0

        if args.command == "doctor":
            return run_doctor(args.config)

        if args.command == "report":
            return print_report(args.run_dir)

        if args.command == "resume":
            print(f"resume is not implemented yet for run {args.run_id}", file=sys.stderr)
            return 1

        if args.command == "canary":
            return run_canary_command(args.root, reset=args.reset, prepare_only=args.prepare_only)
    except (ConfigError, GitError, RunnerError, CommandExecutionError) as exc:
        print(str(exc), file=sys.stderr)
        return _exit_code_for_error(exc)

    parser.error(f"unknown command: {args.command}")
    return 1


def run_doctor(config_path: Path) -> int:
    config = load_config(config_path)
    repo_root = ensure_git_repo(config.run.repo.resolve())
    impl = ensure_command_available(config.implementer.command[0])
    auditor = ensure_command_available(config.auditor.command[0])
    print(json.dumps(
        {
            "repo_root": str(repo_root),
            "implementer_command": impl,
            "auditor_command": auditor,
        },
        indent=2,
    ))
    return 0


def run_canary_command(root: Path, *, reset: bool, prepare_only: bool) -> int:
    if prepare_only:
        workspace = prepare_canary_workspace(root, reset=reset)
        print(f"canary workspace prepared at: {workspace.root}")
        print(f"repo: {workspace.repo}")
        print(f"plan: {workspace.plan_path}")
        print(f"config: {workspace.config_path}")
        return 0

    workspace, outcome = run_canary(root, reset=reset)
    print(f"canary workspace: {workspace.root}")
    print(f"devloop finished with status: {outcome.status.value}")
    print(f"report: {outcome.report_path}")
    print(f"report json: {outcome.report_json_path}")
    return 0 if outcome.status.value == "success" else 3


def print_report(run_dir: Path) -> int:
    report_md, report_json = report_paths(run_dir)
    if report_md.exists():
        print(report_md.read_text(encoding="utf-8"))
        return 0
    if report_json.exists():
        print(report_json.read_text(encoding="utf-8"))
        return 0
    print(f"no report found in {run_dir}", file=sys.stderr)
    return 1


def _exit_code_for_error(exc: Exception) -> int:
    if isinstance(exc, ConfigError):
        return 1
    if isinstance(exc, CommandExecutionError):
        return 2
    if isinstance(exc, RunnerError):
        return 3
    if isinstance(exc, GitError):
        return 1
    return 1
