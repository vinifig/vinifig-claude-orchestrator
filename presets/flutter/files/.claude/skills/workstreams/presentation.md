# Workstream `presentation`: screens, widgets, view models, navigation, theme

## Folders

See `.claude/orchestrator.json` → `workstreams.presentation.paths`.

## Team

| Role | Agent |
|---|---|
| Main architect | `flutter-arch-review` |
| Parallel specialists | by size: `tests-review` (M, L), `security-review` (L or label `auth`/`external-input`), `db-review` (local database changes) |
| Plan · RED · GREEN · Audit | `plan-design` · `tests-implement` · `code-implement` · `plan-verify` |

## Gates (run before saying done)

`python3 .claude/orchestrator/bin/orch.py gates --workstream presentation --run`.

## Visual validation

Always for visible changes: `/app-run`, then `/ui-validate` (simulator screenshots, goldens) and `/ui-review`.

## Irreversible (only with the approver's written yes)

Store uploads (TestFlight, Play Console), Firebase deploys, publishing packages, changing signing or bundle ids of released apps.

## Workstream rules

- `.claude/orchestrator/rules/code-implement.md` and `CLAUDE.md`.
