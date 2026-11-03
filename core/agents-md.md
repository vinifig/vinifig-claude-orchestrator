## Orchestrator roles (any coding agent)

This repository uses the vinifig-claude-orchestrator layout. Other agents (Codex, Copilot, Cursor) can follow it too:

- `.claude/agents/<role>.md` is the brief for each role (plan-design, tests-implement, code-implement, plan-verify, reviewers).
- `.claude/skills/workstreams/<workstream>.md` lists the folders, gates and rules of each part of the code; the gates are also in `.claude/orchestrator.json`.
- `.claude/orchestrator/rules/<role>.md`, when present, holds this project's extra rules for a role.
- Plans go to `.ai/plans/`; local tasks and run state stay out of git in `.ai/board/` and `.ai/context/`.
- Never stage everything, push to the main branch, skip hooks, or read secret files.
