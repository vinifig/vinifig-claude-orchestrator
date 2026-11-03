# Workstream `service`: the Go service

## Folders

See `.claude/orchestrator.json` → `workstreams.service.paths`.

## Team

| Role | Agent |
|---|---|
| Main architect | `go-arch-review` |
| Parallel specialists | by size: `tests-review` (M, L), `security-review` (L or label), `db-review` (label `db`), `perf-review` (label `perf`) |
| Plan · RED · GREEN · Audit | `plan-design` · `tests-implement` · `code-implement` · `plan-verify` |

## Gates (run before saying done)

`python3 .claude/orchestrator/bin/orch.py gates --workstream service --run`.

## Irreversible (only with the approver's written yes)

Production deploys, remote migrations, publishing release tags.
