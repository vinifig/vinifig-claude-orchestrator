---
name: workstreams
description: Map of the workstreams (parts of the codebase) of this repository — for each one the folders, the architect agent, the gates (commands that must be green), visual validation, docs to keep and irreversible operations. Use to find which workstream a request belongs to before running /epic-execute or /task-execute.
---

# Workstreams

The machine-readable map is `.claude/orchestrator.json` → `workstreams`:

```json
"server": {
  "paths": ["apps/server/src"],
  "arch_agent": "server-arch-review",
  "gates": ["pnpm --filter server typecheck", "pnpm --filter server test"],
  "ui": false,
  "docs": ["docs/server.md"]
}
```

Each workstream also has a human file in this folder (`<name>.md`) with its team, gates, rules, docs and irreversible operations. `/epic-execute` and `/task-execute` read it before calling any agent. `python3 .claude/orchestrator/bin/orch.py gates --workstream <name>` prints the gates; `--run` runs them.

## How to choose

1. By the paths the task will touch (the most specific wins).
2. A task that crosses workstreams: the **main** one is the one that owns the rule; the others join as extra architects on the same team (at most three architects per task).
3. When unsure, the workstream that holds the domain rules.

## Default team of a task

```
[<ws>-arch-review (+ extras) ∥ tests-review ∥ security-review (∥ db-review)]  →  plan-design  →  tests-implement  →  code-implement  →  ui-validate (if UI)  →  plan-verify  →  PR
```

The specialists in brackets depend on the task size (`orch.py team <S|M|L> --labels ...`).

## Adding a workstream

1. Add it to `.claude/orchestrator.json` → `workstreams` (paths, arch_agent, gates, ui, docs).
2. Copy `_template.md` in this folder to `<name>.md` and fill it in.
3. If it needs its own architect, copy `.claude/agents/arch-review.md` to `.claude/agents/<name>-arch-review.md` and specialise the "What it is" and "Decisions that hold" sections.
