# Workstream `domain`: pure Dart entities, value objects, use cases

## Folders

See `.claude/orchestrator.json` → `workstreams.domain.paths`.

## Team

| Role | Agent |
|---|---|
| Main architect | `flutter-arch-review` |
| Parallel specialists | by size: `tests-review` (M, L), `security-review` (L or label `auth`/`external-input`), `db-review` (local database changes) |
| Plan · RED · GREEN · Audit | `plan-design` · `tests-implement` · `code-implement` · `plan-verify` |

## Gates (run before saying done)

`python3 .claude/orchestrator/bin/orch.py gates --workstream domain --run`.

## Visual validation

No.

## Irreversible (only with the approver's written yes)

Store uploads (TestFlight, Play Console), Firebase deploys, publishing packages, changing signing or bundle ids of released apps.

## Workstream rules

- `.claude/orchestrator/rules/code-implement.md` and `CLAUDE.md`.
