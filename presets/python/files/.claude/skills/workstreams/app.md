# Workstream `app`: the Python package

## Folders

See `.claude/orchestrator.json` → `workstreams.app.paths`. Split it into more workstreams (e.g. `api`, `worker`, `domain`) as the project grows.

## Team

| Role | Agent |
|---|---|
| Main architect | `python-arch-review` |
| Parallel specialists | by size: `tests-review` (M, L), `security-review` (L or label), `db-review` (label `db`) |
| Plan · RED · GREEN · Audit | `plan-design` · `tests-implement` · `code-implement` · `plan-verify` |

## Gates (run before saying done)

`python3 .claude/orchestrator/bin/orch.py gates --workstream app --run` (ruff check, ruff format --check, pytest).

## Irreversible (only with the approver's written yes)

Publishing to PyPI, production deploys, remote database migrations.
