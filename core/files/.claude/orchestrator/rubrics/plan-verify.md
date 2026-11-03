# Rubric: plan-verify

The auditor scores each criterion 0 to 10 with evidence (command output or file:line). Score = weighted mean. A **blocking** criterion below 7 makes the verdict at best `PARTIAL`, below 4 `REJECTED`, whatever the mean.

| # | Criterion | Weight | Blocking | 10 looks like | 0 looks like |
|---|---|---|---|---|---|
| 1 | Plan coverage | 3 | yes | every promised behaviour, file, route, migration, text and acceptance criterion is in the code | a central item missing |
| 2 | Tests are real | 3 | yes | tests fail if the code is wrong; RED was proven before GREEN; no skip/only/loosened limit | tests that cannot fail, or weakened to pass |
| 3 | Gates green | 3 | yes | every workstream gate ran here, output quoted | a red gate, or gates not run |
| 4 | Scope | 2 | yes | diff touches only `files_touched` from the plan | unrelated files, drive-by refactors |
| 5 | Project rules | 2 | yes | `CLAUDE.md` and `.claude/orchestrator/rules/*` respected | a rule broken |
| 6 | Edge cases and errors | 2 | no | each failure in the plan handled, with a test | happy path only |
| 7 | Security and secrets | 2 | yes | no secret in the diff, validation at the edge, no irreversible command run | a secret, an unvalidated input, a deploy run |
| 8 | Visual evidence (UI tasks) | 2 | yes for `ui` | screenshots per range and theme, criteria checked | "looks fine" without screenshots |
| 9 | Docs | 1 | no | docs the plan lists are updated | behaviour changed, docs did not |
| 10 | Hidden gaps | 1 | no | no TODO, stub, debug print, hard-coded config | stubs left behind |

## Calibration: deliveries that look done and are not

These are the traps auditors approved before. Score them low.

1. **Report says "all tests pass", gate not run.** The execution report is a claim. Run the gate yourself; quote the last lines. If you cannot run it, criterion 3 is 0.
2. **Test asserts the mock.** `expect(repo.save).toHaveBeenCalled()` with no check of what was saved passes with a wrong implementation. Criterion 2 ≤ 3.
3. **RED never failed for the right reason.** The test failed on an import error, then the implementation was written; the test was never seen failing on its assertion. Criterion 2 ≤ 5.
4. **Snapshot or golden updated to make CI green**, with no explanation of which visual change was intended. Criterion 2 ≤ 3 and criterion 8 ≤ 3.
5. **Scope creep that looks helpful**: a rename across 20 files bundled with a bug fix. Criterion 4 ≤ 4: ask for a separate PR.
6. **Screenshots of the happy path only** when the plan lists empty, loading, error and stale states. Criterion 8 ≤ 5.
7. **Deploy command run "just to test"** or a secret pasted in a test fixture. Criterion 7 = 0, verdict `REJECTED`.

Project-specific examples (real rejected deliveries of this repository) live in `.claude/orchestrator/rubrics/examples/` when the project adds them; read them too.

## Verdict

- `APPROVED`: score ≥ 8 and every blocking criterion ≥ 7.
- `PARTIAL`: core is right; the gaps are enumerable and fixable without a new plan.
- `REJECTED`: a central gap, a red gate, a security failure, or a divergence that needs a new plan.

When torn between two verdicts, pick the stricter and say why.
