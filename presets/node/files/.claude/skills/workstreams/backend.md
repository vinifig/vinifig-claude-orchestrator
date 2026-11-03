# Workstream `backend`: Node backend (HTTP, use cases, persistence)

## Folders

See `.claude/orchestrator.json` → `workstreams.backend.paths` (defaults; trim them to this repository).

## Team

| Role | Agent |
|---|---|
| Main architect | `backend-arch-review` |
| Parallel specialists | by size: `tests-review` (M, L), `security-review` (L or label `external-input`/`auth`), `db-review` (label `db`) |
| Plan · RED · GREEN · Audit | `plan-design` · `tests-implement` · `code-implement` · `plan-verify` |

## Gates (run before saying done)

`python3 .claude/orchestrator/bin/orch.py gates --workstream backend --run` (the list lives in `.claude/orchestrator.json`).

## Visual validation

Only when an API change alters what a screen shows: then the frontend validation applies.

## Irreversible (only with the approver's written yes)

Publishing packages, production deploys, database changes on remote environments.

## Workstream rules

- See `.claude/orchestrator/rules/code-implement.md` and `CLAUDE.md`.
