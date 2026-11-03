---
name: initiative-execute
description: Runs an initiative end to end without the person choosing the flow. Runs the /initiative-plan decision and dispatches in the same run to /task-execute (one task) or /epic-execute (an epic, written to the task board first), using the JSON decision block as the routing input. Use when someone asks to get something done and does not care whether it is a task or an epic ("do this", "ship item 4", "fix issue #12").
argument-hint: "<initiative in plain words | #issue | board id>"
---

# Initiative execute

Initiative: $ARGUMENTS

This skill has no flow of its own: it decides and dispatches. The decision rules live in `initiative-plan`; the execution lives in `task-execute` and `epic-execute`.

## 1. Plan

Read `.claude/skills/initiative-plan/SKILL.md` and do its steps 1 to 5 with `$ARGUMENTS`. You end with the **decision block** (JSON). Validate it:

```bash
python3 .claude/orchestrator/bin/orch.py output-check --schema initiative-decision <<'EOF'
<your reply with the ```json block>
EOF
```

Invalid: fix the block, do not guess. Show the person the short summary (decision, why, workstreams, tasks).

## 2. Stop only when needed

Go to step 3 **without waiting for confirmation**, unless:

- an entry in `open_questions` has `blocks: true`;
- `approvals_needed` is not empty and sits on the critical path: run everything that does not depend on it and leave that step pending for the approver;
- `decision` is `none`: answer with what is missing.

## 3. Dispatch (from the JSON, no interpretation)

| `decision` | Call |
|---|---|
| `task-execute` | `Skill("task-execute", args: <next_command without the leading /task-execute>)` |
| `epic-execute` | `Skill("epic-execute", args: "<epic_id> [parallel when mode == parallel]")` |

From here the called skill's contract applies. Do not measure or plan again.

## 4. Come back if the size changes

- A `task-execute` whose plan gate says it passed 7 steps or 3 workstreams: return to `initiative-plan` with what was already learned, write the epic, dispatch to `epic-execute`, and say why it changed.
- `investigate` or `discovery` that ends with work to do: back to step 1 with the result as the new initiative.

## 5. Close

The final report is the dispatched skill's report, with one extra line on top:

```
INITIATIVE: <title> → <task-execute | epic-execute> (size <S|M|L>; <reason in one line>)
```
