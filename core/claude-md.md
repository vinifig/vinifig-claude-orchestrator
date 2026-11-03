## Orchestrator (vinifig-claude-orchestrator {{ORCH_VERSION}})

Work goes through the orchestrator in `.claude/` (map: `.claude/orchestrator/README.md`):

- `/initiative-execute <ask>` decides task vs epic and runs it. `/initiative-plan` only decides and prepares.
- `/epic-execute <epic>` runs an epic in waves with a team per task; `/task-execute <verb> <ask>` runs one task.
- `/task-board` is the only way flows read or change tasks (local `.ai/board/`, GitHub Issues or Linear).
- Project settings (language, workstreams, gates, team sizes, guards) live in `.claude/orchestrator.json`.

Rules every agent and flow follows:

- Write plans, commits, PR text and board comments in the language in `.claude/orchestrator.json` (`language`).
- TDD: the plan names the failing tests; tests-implement writes them (RED); code-implement makes them pass (GREEN).
- Validate for real before saying done: the workstream gates green and, when something visible changed, screenshots.
- Fix without asking what can be undone; ask only for what cannot (deploys, secrets, remote data, DNS, deletes).
- Commit one subject at a time, files added by name. Never `git add -A`, never push to a protected branch, never merge a PR yourself. (Hooks enforce these.)
- No secrets anywhere: never read or copy `.env*`, `*.generated`, keys or credentials; use variable names only.
- Every agent ends its reply with the ```json block its definition shows. State lives in `.ai/context/<epic>/state.json` and changes only through `orch.py`.
