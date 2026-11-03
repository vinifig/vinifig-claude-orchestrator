# Workstream `frontend`: Web frontend (screens, components, client data)

## Folders

See `.claude/orchestrator.json` → `workstreams.frontend.paths` (defaults; trim them to this repository).

## Team

| Role | Agent |
|---|---|
| Main architect | `frontend-arch-review` |
| Parallel specialists | by size: `tests-review` (M, L), `security-review` (L or label `external-input`/`auth`), `db-review` (label `db`) |
| Plan · RED · GREEN · Audit | `plan-design` · `tests-implement` · `code-implement` · `plan-verify` |

## Gates (run before saying done)

`python3 .claude/orchestrator/bin/orch.py gates --workstream frontend --run` (the list lives in `.claude/orchestrator.json`).

## Visual validation

Always for visible changes: `/ui-validate` with the task's acceptance criteria, then `/ui-review`.

## Irreversible (only with the approver's written yes)

Publishing packages, production deploys, database changes on remote environments.

## Workstream rules

- See `.claude/orchestrator/rules/code-implement.md` and `CLAUDE.md`.
