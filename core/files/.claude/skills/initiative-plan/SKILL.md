---
name: initiative-plan
description: Entry point for any work in this repository. Takes an initiative (an ask, idea, issue, epic id), measures size, workstreams and dependencies, picks the team size (S/M/L) and decides between /task-execute (one task) and /epic-execute (an epic with waves). For an epic it breaks the work into tasks with workstream, blocked_by and acceptance criteria and writes them to the task board. Ends with a JSON decision that /initiative-execute dispatches without interpretation. Use before any work that is not obviously a single small task, or when asked to plan, break down or size something.
argument-hint: "<initiative in plain words | #issue | board id>"
---

# Initiative plan

Initiative: $ARGUMENTS

This skill decides **how** the work runs and leaves everything ready for the right executor. It writes no code and calls no implementation agent. Read first: `CLAUDE.md`, `.claude/orchestrator.json`, `.claude/skills/workstreams/SKILL.md`, `.claude/skills/task-board/SKILL.md`.

## 1. Understand

1. An id: read it through the task board (`fetch_task`, `fetch_children`). Children already exist: it is an epic, go to step 4 to check them.
2. Text: read what it points at (docs, issue, code). For code use one quick `Explore` agent (haiku): never grep from the repository root, `grep -l` first, at most 5 files on the first pass.
3. Find the workstreams it touches with the map in `.claude/orchestrator.json` → `workstreams` (paths).
4. When there is UI, find the source artifact (design, story, screenshot). A new screen with no source is an open question, not an invention.

## 2. Measure

Answer each with what you read, not a guess:

| Criterion | Question | JSON field |
|---|---|---|
| Deliverables | How many changes make sense alone (one reviewable PR each)? | `why.deliverables` |
| Workstreams | How many have real changes (not just reads)? | `why.workstreams` |
| Dependencies | Does one deliverable need another first (migration before repository, core before screen)? | `why.dependencies` |
| Steps | Does the plan fit in 7 atomic steps? | `why.steps` |
| Contract | Does a public contract change (API, schema, package API)? | `why.contract_change` |
| External input | Does it touch auth, user input, webhooks, secrets? | `why.external_input` |
| UI | Does anything visible change? | `why.ui` |
| Irreversible | Does the path need a deploy, a secret, remote data, DNS, a delete? | `why.irreversible` |

## 3. Size the team

Size drives cost. Pick the smallest that fits; `orch.py team <size> --labels ...` prints the team from `.claude/orchestrator.json` → `teams`.

| Size | When | Team (default config) |
|---|---|---|
| **S** | 1 deliverable, 1 workstream, ≤ 3 steps, no contract change | workstream arch (sonnet) → plan (tests strategy folded in) → RED → GREEN → audit (1 round) |
| **M** | 1 deliverable, ≤ 2 workstreams, ≤ 7 steps | arch ∥ tests-review → plan → RED → GREEN → audit (2 rounds) |
| **L** | contract change, auth or external input, or > 2 workstreams | arch (+ up to 2 extra) ∥ tests-review ∥ security-review → plan → RED → GREEN → audit |

Labels add specialists: `external-input`/`auth` → `security-review`; `db` → `db-review`; `ui` → `ui-validate` (+ `ui-review` from M); `perf` → `perf-review`. Each epic task gets its own size.

## 4. Decide

**`/task-execute`** when **all** hold: one deliverable; one workstream (or the main one plus a small read or tweak in another); no internal dependency; ≤ 7 steps; no public contract change, or a small compatible one.

**`/epic-execute`** when **any** holds: two or more deliverables or a dependency between parts; three or more workstreams with changes; more than 7 steps; a contract change that needs migration, versioning or coexistence; work that will span sessions (resume comes from `state.json`).

Edge cases:
- **Investigate before you know the size**: `/task-execute investigate` first; its result comes back here.
- **Vague ask with no defined rule**: `/task-execute discovery`; then this skill breaks the result down.
- **Only irreversible work** (publish, set a secret): decision `none`; prepare the command and ask the approver named in `orchestrator.json`.
- **Open product decision**: record it under `open_questions` with the reading you chose; `blocks: true` only when the two readings lead to different deliverables.

## 5. Prepare

### Task

Write the ready command with verb and target: `/task-execute <verb> <ask with path, workstream, id, acceptance criterion> [size=S|M|L]`. If someone wants to follow it on the board and there is no id, create it in the local adapter (`.ai/board/tasks.yaml`, no `parent_id`).

### Epic

1. Break into tasks. Each one is a PR that stands alone with tests, belongs to one `workstream` (the one that owns the rule), has verifiable `acceptance_criteria` (ideally visible in a screenshot or a test), `blocked_by` with the tasks that must land first, a `size`, and labels (`ui`, `db`, `external-input`, `perf`).
2. Use only real dependencies. The usual order is data/schema → core/domain → server/adapters → UI → docs.
3. Mode: `sequential-teams` (default). `parallel` only when the person wants speed; the executor then checks file overlap per wave.
4. Write the board. With no tracker named, the local adapter:

```yaml
# .ai/board/<EPIC-ID>.yaml
epic:
  id: APP-20
  title: "Export reports as PDF"
  description: |
    Origin: issue #41. Every report gets a PDF download.
  workstreams: [core, server, web]
  mode: sequential-teams
tasks:
  - id: APP-21
    title: "Report renderer port and in-memory adapter"
    workstream: core
    size: M
    status: todo
    blocked_by: []
    acceptance_criteria:
      - "use cases ask for the PDF through the port; contract tests cover the in-memory adapter"
  - id: APP-22
    title: "Download route"
    workstream: server
    size: M
    labels: [external-input]
    status: todo
    blocked_by: [APP-21]
  - id: APP-23
    title: "Download button on the report screen"
    workstream: web
    size: S
    labels: [ui]
    status: todo
    blocked_by: [APP-22]
```

Check it parses and has no cycle: `python3 .claude/orchestrator/bin/orch.py waves .ai/board/<EPIC-ID>.yaml`.

On GitHub or Linear, create the epic and children through the adapter only if the person asked for that tracker: issues are visible to other people.

5. The ready command: `/epic-execute <EPIC-ID>` (add `parallel` if chosen).

## 6. Answer

Show 5 to 8 lines for the person (decision, why, workstreams, tasks, questions, approvals, next command). Then end with the decision block, which must match `.claude/orchestrator/schemas/initiative-decision.schema.json` (check with `orch.py output-check --schema initiative-decision`):

```json
{
  "initiative": "Export reports as PDF",
  "decision": "epic-execute",
  "size": "L",
  "why": {"deliverables": 3, "workstreams": 3, "dependencies": true, "steps": 11, "contract_change": true, "external_input": true, "ui": true, "irreversible": false},
  "workstreams": ["core", "server", "web"],
  "team": ["arch", "tests-review", "security-review"],
  "epic_id": "APP-20",
  "board": "local",
  "mode": "sequential-teams",
  "tasks": [{"id": "APP-21", "title": "Report renderer port", "workstream": "core", "size": "M", "blocked_by": [], "labels": [], "acceptance_criteria": ["..."]}],
  "open_questions": [],
  "approvals_needed": [],
  "next_command": "/epic-execute APP-20"
}
```

If the person asked to execute (not only plan), go straight to the chosen command unless an open question has `blocks: true` or an irreversible step sits on the path.
