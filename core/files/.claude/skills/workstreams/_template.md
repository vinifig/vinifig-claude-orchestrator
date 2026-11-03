# Workstream `<name>`: <one line on what it is>

## Folders

`<path>`, `<path>`

## Team

| Role | Agent |
|---|---|
| Main architect | `<name>-arch-review` (or `arch-review`) |
| Extra architects (when) | `<other>-arch-review` when <condition> |
| Parallel specialists | `tests-review`, `security-review` (when <condition>), `db-review` (when <condition>) |
| Plan | `plan-design` |
| Tests (RED) | `tests-implement` |
| Implementation (GREEN) | `code-implement` |
| Audit | `plan-verify` |
| Docs | `docs-write` |

## Gates (run before saying done)

Same list as `.claude/orchestrator.json` → `workstreams.<name>.gates`:

```bash
<command>
```

## Visual validation

<when it applies and how>

## Docs to keep

<files>

## Irreversible (only with the approver's written yes)

<deploys, secrets, remote data, DNS> — the agent leaves the command ready in the report and the PR; the main session runs it after approval.

## Workstream rules

- <rule that a test or a reviewer will enforce>
