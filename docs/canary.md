# Canary Smoke Test

`devloop` includes a built-in canary so you can verify the end-to-end loop against a disposable repository before pointing it at a real project.

## Run it

```bash
uv run devloop canary --reset
```

This command recreates `~/.devloop-canary`, seeds a tiny git repo at `~/.devloop-canary/repo`, writes a stock `config.toml` and `plan.md`, and runs a one-round smoke test.

The canary task is intentionally small and deterministic:

- only `README.md` should change
- the exact line `canary: devloop ok` must be added
- a required check verifies that marker

## Prepare only

If you want to inspect or tweak the generated files first, prepare the workspace without running it:

```bash
uv run devloop canary --prepare-only --reset
```

That leaves these files ready to inspect:

- `~/.devloop-canary/config.toml`
- `~/.devloop-canary/plan.md`
- `~/.devloop-canary/repo/`

You can then launch the run manually with:

```bash
cd ~/.devloop-canary
uv run devloop run --plan plan.md --config config.toml
```

## Artifacts

Run artifacts land under:

```text
~/.devloop-canary/repo/.devloop/runs/<run_id>/
```

Useful files to inspect:

- `report.md`
- `report.json`
- `trace.json`
- `rounds/01/implementer_invocation.json`
- `rounds/01/auditor_invocation.json`

## Reruns

Use `--reset` for most reruns. A successful canary changes `README.md`, so the disposable repo is expected to be dirty after the run finishes.
