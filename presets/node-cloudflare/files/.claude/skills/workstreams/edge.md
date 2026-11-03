# Workstream `edge`: Cloudflare Workers, Pages Functions and bindings

## Folders

See `.claude/orchestrator.json` → `workstreams.edge.paths`.

## Team

| Role | Agent |
|---|---|
| Main architect | `cloudflare-arch-review` |
| Extra architects (when) | `backend-arch-review` if the use cases change; `frontend-arch-review` if a screen changes |
| Parallel specialists | `tests-review`, `security-review` (always for routes and auth), `db-review` (D1 changes) |
| Plan · RED · GREEN · Audit | `plan-design` · `tests-implement` · `code-implement` · `plan-verify` |

## Gates (run before saying done)

`python3 .claude/orchestrator/bin/orch.py gates --workstream edge --run` (typecheck, tests, `wrangler deploy --dry-run`).

## Visual validation

Only when a Pages site or a screen served by the Worker changes.

## Irreversible (only with the approver's written yes)

`wrangler deploy`, `wrangler pages deploy`, `wrangler secret put`, `wrangler d1 migrations apply --remote`, `wrangler d1 execute --remote`, KV/R2 writes, Access policies, routes and DNS. The agent leaves the command ready in the report and the PR; the main session runs it after approval.

## Workstream rules

- `.claude/orchestrator/rules/code-implement.edge.md` and the Cloudflare section of `CLAUDE.md`.
