# Config reference

This document lists every supported config option in the current `devloop` TOML schema.

The commented starter template lives in `examples/config.toml`.

## Top-level structure

```toml
[run]
...

[agents.implementer]
...

[agents.auditor]
...

[[checks.required]]
...

[[checks.advisory]]
...

[observability]
...
```

## `run`

### `run.repo`

- Type: string path
- Default: `"."`
- Meaning: path to the git repository `devloop` should operate in

### `run.max_rounds`

- Type: integer
- Default: `2`
- Minimum: `1`
- Meaning: maximum implementer/auditor rounds before finalization

### `run.commit_on_success`

- Type: boolean
- Default: `false`
- Meaning: when `true`, stage all changes and create a commit after a successful run

### `run.create_branch`

- Type: boolean
- Default: `true`
- Meaning: when `true`, create a new branch before the loop starts

### `run.branch_prefix`

- Type: string
- Default: `"codex/devloop"`
- Meaning: prefix used when `create_branch = true`
- Resulting branch shape: `<branch_prefix>/<run_id>`

### `run.require_clean_worktree`

- Type: boolean
- Default: `true`
- Meaning: when `true`, abort if the repository has uncommitted changes before the run starts

### `run.artifact_dir`

- Type: string path
- Default: `".devloop/runs"`
- Meaning: base directory, relative to the repo root unless absolute, where run artifacts are written
- Recommendation: add `.devloop/` to `.gitignore`

### `run.timeout_secs`

- Type: integer
- Default: `1800`
- Minimum: `1`
- Meaning: timeout used for implementer and auditor command execution

## `agents.implementer`

### `agents.implementer.name`

- Type: string
- Required: yes
- Meaning: display name written into reports and run metadata

### `agents.implementer.command`

- Type: array of strings
- Required: yes
- Constraint: must contain at least one element
- Meaning: executable plus arguments used to launch the implementer agent

### `agents.implementer.input_mode`

- Type: string enum
- Allowed values: `"stdin"`, `"file"`
- Default: `"stdin"`
- Meaning:
  - `"stdin"` sends the rendered prompt on standard input
  - `"file"` appends the prompt file path to the configured command

### `agents.implementer.cwd_mode`

- Type: string enum
- Allowed values: `"repo"`, `"snapshot"`
- Default: `"repo"`
- Meaning: working directory used when invoking the agent
- Recommendation: keep the implementer on `"repo"` so it can edit the live worktree

## `agents.auditor`

### `agents.auditor.name`

- Type: string
- Required: yes
- Meaning: display name written into reports and run metadata

### `agents.auditor.command`

- Type: array of strings
- Required: yes
- Constraint: must contain at least one element
- Meaning: executable plus arguments used to launch the auditor agent

### `agents.auditor.input_mode`

- Type: string enum
- Allowed values: `"stdin"`, `"file"`
- Default: `"stdin"`
- Meaning:
  - `"stdin"` sends the rendered prompt on standard input
  - `"file"` appends the prompt file path to the configured command

### `agents.auditor.cwd_mode`

- Type: string enum
- Allowed values: `"repo"`, `"snapshot"`
- Default: `"repo"` at the schema level
- Recommended value: `"snapshot"`
- Meaning: working directory used when invoking the auditor

## `checks.required`

Each `[[checks.required]]` table defines one required command.

### `checks.required[].name`

- Type: string
- Required: yes
- Meaning: human-readable name used in artifacts and reports

### `checks.required[].command`

- Type: string
- Required: yes
- Meaning: shell command to execute in the repo root

### `checks.required[].timeout_secs`

- Type: integer
- Default: `300`
- Minimum: `1`
- Meaning: timeout for the command
- Runtime behavior: timeouts are recorded as a failing result with exit code `124`

Required checks are hard gates. A final run cannot succeed if any required check exits non-zero.

## `checks.advisory`

Each `[[checks.advisory]]` table has the same fields as `[[checks.required]]`:

- `name`
- `command`
- `timeout_secs`

Advisory checks are recorded in artifacts and reports but do not by themselves force a failed final status.

## `observability`

### `observability.max_inline_text_chars`

- Type: integer
- Default: `20000`
- Minimum: `0`
- Meaning: maximum number of characters in inline JSON previews for prompts, stdout, and stderr
- Runtime behavior: full prompt/stdout/stderr bodies are still written to `.txt` artifacts; JSON artifacts and `report.json` store previews like `text_here...[truncated +15592 chars]` when the limit is exceeded
- Trace behavior: each run also gets a `trace_id`, each agent lane gets a stable `thread_id`, and each agent call gets an `invocation_id` in `trace.json`, `report.json`, and the per-round `*_invocation.json` artifacts

## Example

```toml
[run]
repo = "."
max_rounds = 2
commit_on_success = false
create_branch = true
branch_prefix = "codex/devloop"
require_clean_worktree = true
artifact_dir = ".devloop/runs"
timeout_secs = 1800

[agents.implementer]
name = "claude"
command = ["claude", "-p"]
input_mode = "stdin"
cwd_mode = "repo"

[agents.auditor]
name = "codex"
command = ["codex", "exec"]
input_mode = "stdin"
cwd_mode = "snapshot"

[observability]
max_inline_text_chars = 20000

[[checks.required]]
name = "tests"
command = "uv run pytest -q"
timeout_secs = 900

[[checks.advisory]]
name = "lint"
command = "uv run ruff check ."
timeout_secs = 300
```

## Validation notes

The current validator enforces:

- `run.max_rounds >= 1`
- `run.timeout_secs >= 1`
- `checks.*.timeout_secs >= 1`
- both `agents.implementer` and `agents.auditor` must exist
- each agent command array must be non-empty

## Not yet configurable

These behaviors exist in code today but are not yet exposed as config:

- retry counts
- per-agent timeout overrides
- custom commit message templates
- branch naming templates beyond a simple prefix
- artifact exclusion rules for git diff collection
