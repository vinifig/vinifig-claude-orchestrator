# Workstream `platform`: Android and iOS projects, plugins, platform channels

## Folders

See `.claude/orchestrator.json` → `workstreams.platform.paths`.

## Team

| Role | Agent |
|---|---|
| Main architect | `platform-native-arch-review` |
| Parallel specialists | by size: `tests-review` (M, L), `security-review` (L or label `auth`/`external-input`), `db-review` (local database changes) |
| Plan · RED · GREEN · Audit | `plan-design` · `tests-implement` · `code-implement` · `plan-verify` |

## Gates (run before saying done)

`python3 .claude/orchestrator/bin/orch.py gates --workstream platform --run`.

## Visual validation

When a permission prompt, splash, notification or deep link changes: capture it on both platforms.

## Irreversible (only with the approver's written yes)

Store uploads (TestFlight, Play Console), Firebase deploys, publishing packages, changing signing or bundle ids of released apps.

## Workstream rules

- `.claude/orchestrator/rules/code-implement.md` and `CLAUDE.md`.
