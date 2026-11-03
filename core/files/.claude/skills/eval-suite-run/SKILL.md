---
name: eval-suite-run
description: Runs the orchestrator's own evaluation suite — 3 to 5 real, already solved tasks replayed headless in throwaway worktrees — and compares pass rate, cost, turns and time with the baseline. Use after changing any agent, skill, rubric, hook or model routing, before trusting the change; also to find parts of the harness that stopped helping when models improve.
argument-hint: "[case id ...] [--model <model>] [--baseline]"
---

# Eval suite

Run: $ARGUMENTS

The orchestrator is a set of hypotheses about what the model will not do alone. This suite tests them on real work.

## Cases

`.ai/evals/cases/<id>.json` (in git):

```json
{
  "id": "fix-freshness-badge",
  "title": "Freshness badge never turns stale after 24 h",
  "base_ref": "<commit before the real fix>",
  "command": "/task-execute fix the freshness badge does not turn stale after 24 h on the data screen",
  "checks": ["pnpm --filter app test -- freshness", "git log --oneline -1 | grep -q ."],
  "reference_pr": "#42",
  "notes": "the real fix touched domain/freshness.ts and one screen"
}
```

Good cases: small to medium, already merged, with a test that proves the fix (the check), covering different workstreams and at least one `investigate`. Write them from merged PRs; never include secrets or production data.

## Run

```bash
python3 .claude/orchestrator/bin/orch.py eval list
python3 .claude/orchestrator/bin/orch.py eval run <case> [--model <m>] [--keep]
```

Each run: `git worktree add` at `base_ref` → `claude -p "<command>" --output-format json --permission-mode <evals.permission_mode> --allowedTools <evals.allowed_tools>` → runs `checks` → records `passed`, `cost_usd`, `turns`, `seconds` in `.ai/evals/runs/<date>.json` → removes the worktree. Hooks stay active inside the run (the guards still apply). Runs cost real tokens: start with one case.

Run the cases one at a time in the background (`run_in_background`), not in parallel, so they do not fight over ports.

## Compare

```bash
python3 .claude/orchestrator/bin/orch.py eval compare .ai/evals/runs/<date>.json
```

Regression = a case that passed now fails, or cost grew more than 25 %. Report a table per case (passed, cost, turns, time, vs baseline) and the verdict. When the person accepts the new numbers: `orch.py eval baseline <run file>`.

## Use the result

- A change to an agent or skill ships only without regression.
- A step that can be removed with no loss (same pass rate, lower cost) is a candidate for removal: say which.
