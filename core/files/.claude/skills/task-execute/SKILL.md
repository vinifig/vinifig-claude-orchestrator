---
name: task-execute
description: Orchestrator for a single task (fix, implement, refactor, test, review, explain, migrate, investigate, doc, discovery), no epic. Short pipeline Context → plan gate → Execution → Review with the workstream architect, a team sized to the task (S/M/L) and model routing; every agent returns a JSON block and run events and cost are logged. Reads the task from the task board when there is an id. For several tasks or an epic use /epic-execute; when unsure, /initiative-plan decides.
argument-hint: "<verb> <ask in plain words, with #issue, id or path if any> [size=S|M|L]"
---

# Single task

Ask: $ARGUMENTS

Coordinate the agents. Do not write code yourself. Read first `CLAUDE.md`, `.claude/orchestrator.json` and `.claude/skills/workstreams/SKILL.md`. `ORCH="python3 .claude/orchestrator/bin/orch.py"`.

## Format

```
/task-execute <verb> <ask> [size=S|M|L]
```

Verbs: `fix`, `implement`, `refactor`, `test`, `review`, `explain`, `migrate`, `investigate`, `doc`, `discovery` (also accept the same verbs in the configured language).

Extract: **verb**; **target** (path, package or screen, or `null`); **workstream** (from the target with `workstreams.<name>.paths`); **id** (`#12`, `APP-12`, `ABC-123` or `null`; with an id, `fetch_task` and save to `.ai/context/tasks/<id>.md`); **size** (given, or measured with `initiative-plan` step 3; default S for `fix` with a known cause, M otherwise).

Start the log: `$ORCH current set tasks <id or slug> --workstream <ws> --size <size>` (the hooks then attribute cost and run the right gates); `$ORCH event tasks task_started verb=<verb> task=<id> size=<size>`.

## Pipeline

```
Context (fast) → [Plan gate] → Execution → Review
```

### Step 1 · Context

One `Explore` agent (haiku) and, in parallel, the workstream architect (`workstreams.<ws>.arch_agent`, model from `teams.<size>.models.arch`). Explore prompt:

- verb, target, full ask, workstream file (`.claude/skills/workstreams/<ws>.md`);
- start at the docs index and the area's doc; stop at the first relevant one;
- map only the target files, their direct imports and related tests (neighbours only for `refactor`);
- never grep from the repository root: always inside the workstream folder; `grep -l` first; at most 5 files on the first read;
- **required output**:

```
## Files
- <path>:<lines> — <role>
## Gaps
- <expected file or export that does not exist>
## Constraints
- <pattern or rule the change must not break>
## Proposed plan
1. <atomic change with file:line>
(at most 7 steps)
## Files touched
- <every file the plan changes>
```

### Plan gate

Read the context and the architect's note. **Go on without asking** when the plan has ≤ 7 steps, stays in one workstream (or the main one plus one), and everything is reversible. **Stop and ask** only when:
- it passes 7 steps or touches more than 3 workstreams (suggest `/epic-execute` through `/initiative-plan`);
- the ask can be read two ways that lead to different results;
- a step cannot be undone: deploy, secret, remote data, deletes, a closed product decision (approver from `orchestrator.json`).

Skip the gate for `investigate`, `explain`, `doc`.

### Step 2 · Execution

For `implement` with a new business rule, or size M/L: `tests-implement` first (RED) with the Step 1 plan.

Then one `code-implement` (model from the team) with: the whole Step 1 output, the architect's note, verb, target and ask. Instruction: **do exactly the plan**, run the workstream gates, fix broken tests and add tests for what is new, update docs if behaviour changed; if the plan is ambiguous or a file it names does not exist, stop and return. The `SubagentStop` hook checks its JSON block and runs the gates.

Skip for `investigate`, `explain`, `review`.

### Step 3 · Review

One `plan-verify` (read-only) with the Step 1 plan, the Step 2 JSON and the diff, scored with `.claude/orchestrator/rubrics/plan-verify.md`. Extra blocking checks:
- **Tests**: gates green; new method has a test.
- **Scope**: the diff touches only files in "Files touched"; extra files = changes requested.
- **Project rules**: `CLAUDE.md` and `.claude/orchestrator/rules/*.md`.
- **Security**: no secret, no customer data in logs, validation at the edge (if it touched external input, also call `security-review`).
- Screen changed: `ui-validate` and `ui-review` before saying done.

Verdict from the JSON: `APPROVED`, `PARTIAL` or `REJECTED` with `fixes`.

Skip for `investigate`, `explain`, `discovery`.

### After the review

- **APPROVED**: show the summary and the diff. With an id, `post_comment(id, <summary>)`. Open a PR if the person asked or it is what this conversation agreed (never push to a protected branch). Report cost: `$ORCH cost tasks`. `$ORCH current clear`.
- **PARTIAL / REJECTED**: call only the `owner` of each fix (usually `code-implement`) with the Step 1 context and the `fixes`; review again. At most `teams.<size>.audit_rounds` rounds; then show the state and ask for a decision.

## Per verb

| Verb | Pipeline |
|---|---|
| `fix`, `refactor`, `implement`, `migrate`, `test` | full |
| `investigate` | See **Investigate** below. Then fix (the natural next step) unless the fix falls into a plan-gate case. |
| `explain` | Context → answer in the main conversation |
| `doc` | all fast: Context → `docs-write` → `plan-verify` (accuracy against the code; Mermaid for flows; tables for facts) |
| `review` | Context (reads the diff) → `plan-verify` + `security-review` (+ `ui-review` if there is UI) |
| `discovery` | no agents: discovery conversation with the person, few questions at a time, ending with an epic draft in the local board (`.ai/board/`) |

### Investigate

Competing hypotheses beat one long trail:

1. Context step as usual, then write 2 to 4 hypotheses for the cause, each with what would confirm or refute it.
2. **With agent teams** (`investigate.agent_teams` is `auto` and `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, or `on`): create a team with one teammate per hypothesis, read-only, asked to try to refute the others' hypotheses through messages; the lead collects the survivor. **Without**: one `Explore` agent per hypothesis in a single message (parallel, read-only), each returning evidence for and against.
3. In the main conversation, compare the working and broken paths for the surviving hypothesis, write the cause with file:line and the fix steps.

Agent teams are used only here (read-only investigation), as their documentation recommends; implementation always stays on single-writer subagents.

## Model routing

| Step | Model |
|---|---|
| Context (Explore) | haiku |
| Architect, reviewers, plan-verify | `teams.<size>.models` (S: sonnet; M/L: opus) |
| Execution | `teams.<size>.models.code-implement` (sonnet) |
| doc | fast in every step |

## Read limits (in every prompt)

- Never grep from the root; `-l` first; at most 5 files on the first pass.
- Execution reads only the plan's files; a missing file becomes a gap, not a speculative read.
- Review reads the diff and the plan's files.
- Logs and databases: nothing from production unless the person asks; `LIMIT 100`; never secret values.
