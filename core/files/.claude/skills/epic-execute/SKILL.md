---
name: epic-execute
description: Main orchestrator. Runs an epic (or a list of tasks) end to end with teams of specialist agents per workstream. Reads tasks through the task board (local file, GitHub Issues or Linear), builds waves from blocked_by, sizes each task's team (S/M/L), and for each task runs specialists in parallel, then plan → failing tests → implementation → visual validation → audit → PR. State lives in .ai/context/<epic>/state.json (written by orch.py, rendered to _wave_strategy.md) with an events.jsonl log and cost per task. Default mode sequential-teams (one task at a time, stacked PRs); `parallel` uses worktrees and only groups tasks whose plans touch disjoint files. Resumes where it stopped. Usually called after /initiative-plan.
argument-hint: "<epic id | #issue | .ai/board/<file>.yaml> [parallel] [skip-ui]"
---

# Epic

Run: $ARGUMENTS

## Current context
- Branch: !`git branch --show-current`
- Uncommitted changes: !`git status --short | head -20`
- Epics in progress: !`ls .ai/context/*/state.json 2>/dev/null | head -5`

## Orchestrator contract

This skill runs in the main conversation and is the only one that calls agents (agents never call agents). Its job: **read → plan waves → call → wait → check → PR → record**. It writes no production code and runs no tests in place of the agents (only the gate checks).

`ORCH="python3 .claude/orchestrator/bin/orch.py"`. Every state change goes through `$ORCH state task ...`; never edit `state.json` or `_wave_strategy.md` by hand (the Markdown is rendered from the JSON).

Read first: `CLAUDE.md`, `.claude/orchestrator.json`, `.claude/skills/workstreams/SKILL.md`, `.claude/skills/task-board/SKILL.md`, `.claude/orchestrator/rubrics/plan-verify.md`.

## Modes

| Mode | Word | How it runs |
|---|---|---|
| **sequential-teams** | nothing, `sequential` | **Default.** One task at a time with its full team. Normal branch in the current checkout, no worktree. Stacked PRs (each on the previous one). |
| **parallel** | `parallel`, `swarm` | Plans for the whole wave first (read-only), then `orch.py overlap` groups tasks whose `files_touched` do not intersect; each group runs at the same time, one worktree per task, still with RED and GREEN in separate agents. Tasks that overlap wait for the next group. |

Visual validation turns on by itself for `ui` tasks. `skip-ui` turns it off (say in the PR there are no screenshots and why).

## Guardrails (mistakes that must not come back)

1. **Never merge plan, tests and implementation into one agent**, in either mode. Three calls.
2. **No worktree in sequential-teams.** Worktrees are only for `parallel`.
3. **Implementation agents run in the foreground**, never in the background.
4. **Each agent does only its phase.** The plan only writes the plan; `tests-implement` only writes failing tests; `code-implement` only makes them pass.
5. **Specialists before the plan, always** (the team for the task's size); `plan-design` reads their notes and does not redo them.
6. **Irreversible steps need the approver** named in `orchestrator.json` (deploy, secret, remote data, DNS, access rules, deletes). No agent and no step here runs them. They become `$ORCH state approval` items, listed in the PR and the report.
7. **No secrets**: no `.env*`, `*.generated`, keys or local config files read, copied, committed or quoted with values. (Hooks block reading them.)
8. **Structured output is the contract.** Every agent ends with a ```json block; the `SubagentStop` hook rejects replies without a valid one. Route on the JSON fields (`status`, `verdict`, `fixes`, `files_touched`), not on prose.

## Phase 0: load

### Resume (always first)

1. `$ORCH state resume <epic>`. If it prints a task, it is a resume:
   a. Say: `Resuming <EPIC>. <summary>.` (the `summary` field).
   b. Skip the rest of Phase 0 and Phase 1.
   c. Start that task at `resume_step` (see the step names in Phase 2). Confirm with git before trusting it:
      - `git log origin/<base>..<branch> --oneline`: no commits → `specialists` (reuse notes in `.ai/context/<epic>/<id>/`); only `docs(plans)` and `test(` → `green`; has `feat`/`fix` → `ui`/`audit`;
      - `gh pr list --head <branch> --json number,state`: an open PR → `$ORCH state task <epic> <id> status=done pr=<n> step=done` and move on.
2. No state → new run.

### New run

1. **Find the epic** through the task board (`fetch_task(epic)`, `fetch_children(epic)`). No tracker has it ("do items 3 and 4 of the roadmap"): create `.ai/board/<id>.yaml` in the local adapter, one task per item, and say so.
2. **Filter** actionable tasks: drop `done`, `canceled` and what is not code (product decisions, approvals, assets someone must provide).
3. **Workstream** of each task: field `workstream`, label `workstream:*`, or by paths with `.claude/orchestrator.json` → `workstreams.<name>.paths`.
4. **Size** of each task: field `size`, else measure it with the table in `initiative-plan` step 3.
5. **Save context**: `.ai/context/<epic>/<ID>.md` per task and `<EPIC>.md` for the epic (id, title, status, workstream, size, description, acceptance criteria, blocked_by, link). Agents read only these files and never call the board.
6. **Show the list** (id, title, workstream, size) and continue. Stop only if a task can be read two ways that change the outcome; otherwise state the reading you chose (`$ORCH state decision`).

## Phase 1: waves and state

```bash
$ORCH state init <epic> --board <board file or id> --mode <sequential-teams|parallel> --base <current branch> --board-adapter <local|github|linear>
```

It computes waves from `blocked_by` (fails on a cycle and prints it), writes `state.json`, renders `_wave_strategy.md` and logs `epic_started`. For a GitHub or Linear epic, write the fetched tasks to `.ai/context/<epic>/tasks.json` first and pass `--tasks-file`.

Within a wave (sequential-teams): priority, then natural order (data before core before UI). Show the waves in a few lines and continue. Stop only if an irreversible item sits on the critical path.

## Phase 2: run

### sequential-teams

For each task, in order. Mark progress with `$ORCH state task <epic> <id> step=<step>` at each step and `$ORCH current set <epic> <id> --workstream <ws> --size <S|M|L>` at the start (the hooks read it to run the right gates and attribute cost).

**Step 1 · Branch and status** (`step=context`)
```bash
git fetch origin <base> && git checkout <base>
$ORCH state task <epic> <id> status=in-progress step=specialists size=<S|M|L>
$ORCH team <size> --labels <labels>
```
Board: `update_status(id, in_progress)`. The plan agent creates the branch.

**Step 2a · Specialists in parallel** (one message, foreground, wait for all)

Team from `$ORCH team`: `arch` means the workstream's architect (`.claude/orchestrator.json` → `workstreams.<ws>.arch_agent`, falling back to `arch-review`), plus extra architects for other workstreams the task changes (at most 3 in total). Pass `model` per agent from the team's `models` map. Record the team: `$ORCH state task <epic> <id> team=<a,b,c>`.

| Agent | Writes |
|---|---|
| `<ws arch agent>` | `.ai/context/<epic>/<id>/architecture.md` (extras: `<agent>.md`) |
| `tests-review` (M, L) | `tests.md` |
| `security-review` (L, or label) | `security.md` |
| `db-review` (label `db`) | `db.md` |
| `perf-review` (label `perf`) | `perf.md` |

Specialist prompt (replace `<...>`):

```
You are the <role> for task <ID>: <TITLE>, workstream <WS>, size <SIZE>, in repository <ROOT>.
Run state: <ROOT>/.ai/context/<epic>/_wave_strategy.md. Task: <ROOT>/.ai/context/<epic>/<ID>.md. Epic: <ROOT>/.ai/context/<epic>/<EPIC>.md.
Workstream: <ROOT>/.claude/skills/workstreams/<ws>.md. Rules: <ROOT>/CLAUDE.md and <ROOT>/.claude/orchestrator/rules/<your agent name>.md if it exists.
Do what your agent definition says and write <ROOT>/.ai/context/<epic>/<id>/<file>.md.
No code. Do not call the task board. Nothing irreversible. End with the ```json block from your definition.
```

Pilot: with `orchestrator.json` → `workflows.specialists: true`, run the saved workflow instead: `/specialists-review` with args `{root, epic, task, title, workstream, size, specialists: [...], models: {...}}`. It fans the same specialists out with a schema on each output and resumes from saved results. Fall back to the manual call if workflows are off or unavailable.

**Step 2b · Plan** (`step=plan`, foreground, after all specialists)

```
Agent(subagent_type: "plan-design", model: <team.models.plan-design>, prompt:
  Plan for task <ID>: <TITLE>, workstream <WS>, size <SIZE>. Repository <ROOT>. Base <BASE>.
  Create the branch: git checkout -b <prefix><id>-<slug>
  Read: _wave_strategy.md, <ID>.md, <EPIC>.md and the notes in .ai/context/<epic>/<id>/.
  <size S: there is no tests-review note; write the test strategy yourself.>
  Read CLAUDE.md, .claude/skills/workstreams/<ws>.md, .claude/orchestrator/rules/plan-design.md if present.
  Write .ai/plans/<YYYY-MM-DD-HHMM>_<id>-<slug>.md, commit it (docs(plans): ...).
  The plan is pre-approved: do not wait for an answer. No code. End with the plan-output JSON block.)
```
From its JSON: `$ORCH state task <epic> <id> plan=<plan_path> branch=<branch> files=<files_touched joined by ,>`. If `steps > 7` or more than 3 workstreams appear, stop the task and send it back to `initiative-plan` to split.

**Step 3 · Failing tests** (`step=red`, foreground)
```
Agent(subagent_type: "tests-implement", model: <team.models.tests-implement>, prompt:
  RED for task <ID>. Branch <branch> is checked out. Plan: <plan_path>.
  Write the tests in the plan's RED table, prove they fail on the assertion, commit (test(<ws>): ...), push -u.
  No implementation. End with the JSON block.)
```
Check: the JSON lists test files and the RED gate shows `fail` for the right reason.

**Step 4 · Implementation** (`step=green`, foreground, never background)
```
Agent(subagent_type: "code-implement", model: <team.models.code-implement>, prompt:
  GREEN for task <ID>. Branch <branch>. Plan: <plan_path>. Tests are failing: make them pass.
  Run the gates of .claude/orchestrator.json → workstreams.<ws>.gates. Write <plan>_execution.md.
  Commits per subject, files by name. Push. No PR. Nothing irreversible. End with the JSON block.)
```
The `SubagentStop` hook runs the workstream gates when it reports `done` and sends failures back to it. Still check: `$ORCH gates --workstream <ws> --run` (last lines).

**Step 5 · Visual validation** (`step=ui`; tasks with label `ui`, skip with `skip-ui`)

Run the `ui-validate` skill with the task's acceptance criteria; for screens and components from size M also `ui-review`. Failure: call `code-implement` with the exact findings and validate again. Screenshots go where the skill says and into the PR.

**Step 6 · Audit** (`step=audit`)

Call `plan-verify` with the plan, the execution report, the screenshots and `git diff <base>...HEAD`. It scores against `.claude/orchestrator/rubrics/plan-verify.md` and returns the `verdict` JSON. Pilot: `workflows.audit: true` runs `/delivery-audit` (plan-verify + tests-review in review mode + security-review when labelled, then an adversarial cross-check) instead.

- `APPROVED`: `$ORCH state task <epic> <id> verdict=APPROVED step=pr`.
- `PARTIAL` / `REJECTED`: `$ORCH state task <epic> <id> rounds+=1 verdict=<v>`; call the `owner` of each item in `fixes` (`code-implement` or `tests-implement`) with exactly those fixes; audit again. At most `team.audit_rounds` rounds (S: 1, M/L: 2); then `status=skipped note="<why>"` and move to the next task that does not depend on it.

Alongside the audit, if the plan asks: `perf-review`, `docs-write` (workstream docs).

**Step 7 · PR** (Phase 3) → **Step 8 · next task**, with this PR's branch as the base.

### parallel

1. **Plans first**: for every task of the wave, run Step 2a and Step 2b (plans are read-mostly; run up to `parallel.max_concurrent` at a time). Each plan's JSON gives `files_touched`.
2. **Group**: `$ORCH overlap <epic> <ids of the wave>` returns groups with no shared file. A task without a file list never shares a group.
3. **Per group**, one worktree per task, created from the base:
   ```bash
   git worktree add "<parallel.worktree_dir>/<id>" <branch> 2>/dev/null || git worktree add "<dir>/<id>" -b <branch> <base>
   ```
   One message with a `tests-implement` per task (each in its worktree), wait; then one message with a `code-implement` per task, wait. RED and GREEN stay separate agents.
4. Per worktree: gates, visual validation, `plan-verify`, PR against the base branch.
5. Remove the worktrees: `git worktree remove <path>`. Next group.

## Phase 3: PR

```bash
gh pr create --base "<base>" --head "<branch>" \
  --title "<type>(<ws>): <short description>" \
  --body-file .ai/context/<epic>/<id>/pr.md
```

Body (`pr.md`), in the configured language:

```markdown
<attribution lines the session asks for, if any>

## Summary
- <what changed and why>

## Task
<board link or id> · Epic <EPIC> · Plan: `.ai/plans/<...>.md` · Size <S|M|L>

## How it was validated
- [x] `<workstream gates>` green
- [x] Audit: APPROVED (score <x>/10, <n> round(s))
- [x] Screenshots: <list or "no visible change">

## Cost
<tokens and time for this task from `orch.py cost <epic>`>

## Pending approval
- <command> (or "none")
```

After `gh pr create`: `$ORCH state task <epic> <id> status=done step=done pr=<n>`; board `post_comment(id, "PR #<n>")` and `update_status(id, in_review)`. `$ORCH current clear`.

## Phase 4: final check of the epic

1. `fetch_children(epic)` again.
2. New tasks that are not in the state and not done/canceled: write them to a JSON list and `$ORCH state discover <epic> <file>` (adds new waves by the same dependency rule and records when). Save their context and go back to Phase 2.

## Phase 5: final report

```
Epic <ID> — <TITLE> (sequential-teams | parallel)
  [done]    <ID>: <title> — PR #<n> — <rounds> round(s)
  [skipped] <ID>: <title> — <reason>
Waves: <N> · PRs: <N>
Cost: <orch.py cost <epic> first line>
Pending approval: <list or "none">
```

`$ORCH cost <epic>` gives tokens, time and rounds per task and per agent; quote the totals and the most expensive task. Board: `done` only after a person merges; until then `in_review`.

## Fixed rules

- sequential-teams = no worktree, normal branch, stacked PRs.
- Specialists before the plan; at least plan-design, tests-implement, code-implement and plan-verify per task, plus the specialists of its size.
- Board context saved before calling agents; agents never talk to the board.
- TDD always.
- Commits per subject; never `git add -A`; never push to a protected branch; never merge automatically (hooks block the first two).
- Merge conflict: resolve when it is obvious and reversible (two independent additions) and say what you did; if it touches a rule, stop and ask.
- State only through `orch.py`; `_wave_strategy.md` is generated.
- Everything people read (plans, commits, PRs, board comments) in the configured `language`.
