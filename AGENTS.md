# AGENTS

This file is the collaboration playbook for agents and humans working on `devloop`.

## Product intent

`devloop` exists to orchestrate a disciplined implementation-review loop between two coding agents. The product should optimize for:

- reproducibility
- inspectable artifacts
- safe git behavior
- clear model contracts
- boring operational reliability over clever prompt tricks

## Default role model

- Implementer: edits the live repository to satisfy the plan.
- Auditor: reviews the plan, diffs, changed files, and check output from a snapshot directory.
- Orchestrator: the Python runner that decides what to run, what to persist, and when to stop.

The implementer owns code changes. The auditor does not edit the repo.

## Shared rules

- Keep changes narrow and task-focused.
- Treat the plan as the primary contract.
- Prefer deterministic checks over model opinion when the two disagree.
- Persist artifacts for every meaningful step.
- Do not silently ignore malformed agent output.
- Do not mutate unrelated files to appease the audit loop.
- Avoid hidden state. If the runner depends on something, write it to artifacts.

## Agent output contract

Configured agent commands must return structured JSON inside exact markers:

```text
DEVLOOP_JSON_BEGIN
{...json...}
DEVLOOP_JSON_END
```

The implementer and auditor each have their own expected schema. The orchestrator trusts the JSON payload, not surrounding prose.

## Implementer expectations

- Work only against the requested plan and unresolved findings.
- Make the minimum reasonable code changes.
- Report what changed, what criteria were addressed, and any known risks.
- If running checks manually, say so in the structured report.
- Do not fabricate successful checks.

## Auditor expectations

- Review against the plan, not personal style preferences.
- Use the diff, before/after files, and check output as evidence.
- Prefer concrete, actionable findings.
- Reserve `blocking` for issues that should stop the run.
- Avoid duplicate findings with different wording.

## Findings guidance

- `blocking`: correctness, safety, or acceptance-criteria failures
- `major`: important but not always release-blocking issues
- `minor`: polish, readability, or narrow maintainability issues
- `info`: notes that should not hold the loop open

Every finding should ideally include:

- stable `id`
- short `title`
- affected `file`
- concrete `evidence`
- a concise `fix_hint`
- confidence score

## Repo extension guidance

If you extend the project, prefer to preserve these boundaries:

- `cli.py`: argument parsing and top-level exit codes
- `config.py`: TOML loading and validation
- `models.py`: shared schemas
- `runner.py`: orchestration logic only
- `git_ops.py`: git interactions
- `checks.py`: deterministic command execution
- `prompts.py`: prompt rendering
- `report.py`: final reporting

## Near-term roadmap

Good next improvements after the current skeleton:

- CLI-specific adapters for `claude -p` and `codex exec`
- richer retry behavior
- run resume support
- artifact filtering so `.devloop` never pollutes diffs even when not ignored
- stronger finding dedupe and convergence heuristics
