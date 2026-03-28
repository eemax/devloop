# devloop

`devloop` is a Python CLI for running a structured two-agent code loop inside a git repository.

One agent acts as the implementer. A second agent audits that work against the plan, the diff, and the check output. `devloop` wraps that loop with git-aware artifacts, deterministic checks, stop conditions, and optional commit creation.

## Status

The repository currently provides a tested v0.1 skeleton with:

- config loading from TOML
- plan loading from Markdown
- generic non-interactive CLI agent adapters
- per-round artifacts for prompts, outputs, diffs, changed files, and check results
- snapshot-based auditing
- loop stop conditions for success, failure, and stall states
- optional branch creation and final commit creation

## Core ideas

- The plan is the source of truth.
- The implementer is the only agent that edits the live repository.
- The auditor runs in a read-only snapshot by default.
- Model feedback is useful, but executable checks are the hard gate.
- Every run leaves behind inspectable artifacts.

## Repository layout

```text
src/devloop/
  cli.py
  runner.py
  models.py
  config.py
  plan_parser.py
  git_ops.py
  checks.py
  prompts.py
  report.py
tests/
examples/
docs/
AGENTS.md
```

## Quick start

1. Create a virtual environment and install the package in editable mode.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e . pytest
```

2. Copy the example config and plan.

```bash
cp examples/devloop.toml devloop.toml
cp examples/plan.md plan.md
```

3. Adjust the agent commands in `devloop.toml` for the CLIs you want to use.

4. Run `devloop`.

```bash
devloop run --plan plan.md --config devloop.toml
```

## Required agent protocol

The current adapter is intentionally generic. Whatever command you configure for an agent must be able to run non-interactively and write a structured JSON payload to `stdout` wrapped with these markers:

```text
DEVLOOP_JSON_BEGIN
{...json...}
DEVLOOP_JSON_END
```

If those markers are missing, the run fails.

## Minimal plan format

`devloop` accepts plain Markdown and understands a small section vocabulary:

```md
# Add login audit logging

Acceptance criteria:
- New login attempts are logged
- Required checks pass

Constraints:
- Keep the diff focused

Out of scope:
- Refactoring the auth module

Checks:
- pytest -q
```

The parser also supports inline forms like `Goal: ...` and `Constraints: ...`.

## Artifacts

By default, each run is written under `.devloop/runs/<run_id>/`.

Important files include:

- `run_spec.json`
- `rounds/<n>/implementer_prompt.txt`
- `rounds/<n>/implementer_stdout.txt`
- `rounds/<n>/checks.json`
- `rounds/<n>/cumulative.patch`
- `rounds/<n>/audit_snapshot/`
- `rounds/<n>/findings.json`
- `report.md`
- `report.json`

You should usually ignore `.devloop/` in git so run artifacts do not become part of the reviewed diff.

## CLI commands

- `devloop run --plan <path> --config <path>`
- `devloop validate-config --config <path>`
- `devloop doctor --config <path>`
- `devloop report <run_dir>`
- `devloop resume <run_id>`

`resume` is reserved for future work and currently returns a not-implemented error.

## Testing

Run the test suite with:

```bash
.venv/bin/python -m pytest
```

The current suite covers config validation, plan parsing, artifact helpers, subprocess handling, check execution, prompt rendering, git helpers, CLI behavior, the generic CLI agent adapter, and multiple runner scenarios including success, commit creation, blocking audit failure, and stall detection.

## Documentation

- [Agent playbook](AGENTS.md)
- [Architecture](docs/architecture.md)
- [Config reference](docs/config-reference.md)

## Current limitations

- The agent adapter is generic and does not yet include CLI-specific handling for `claude -p` or `codex exec`.
- `resume` is not implemented.
- There is no persistent state store beyond the run artifact directory.
- There is no third judge agent or automatic plan synthesis in v0.1.
