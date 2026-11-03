---
name: ui-review
description: Heuristic review of a screen or component before merge — the project's design rules, 10 usability heuristics read for the actual user, accessibility AA, responsive behaviour and the component tests — scored with a weighted rubric calibrated by examples of rejected work. Use on every PR that creates or changes a screen, component, design token or UI text.
---

# UI review

`ui-validate` must have run first: this review looks at its screenshots.

1. Read `.claude/orchestrator/rubrics/ui-review.md` (criteria, weights, failing examples) and, when present, `.claude/orchestrator/rules/ui-review.md` (the project's design source, e.g. a design system review skill, which takes precedence).
2. Automatic checks first: lint, component tests, accessibility checks the stack has (axe, semantics).
3. Walk the rubric. Each finding: item · where (file:line or screenshot) · severity (blocking, major, minor) · suggestion.
4. Blocking findings that are reversible and inside the task's scope: fix them through `code-implement` and review again, without asking.

End with the table, "ready to merge" or "not ready" with the reason in one sentence, and the `verdict` JSON block (schema `.claude/orchestrator/schemas/verdict.schema.json`, `agent: "ui-review"`).
