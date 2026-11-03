# Rubric: ui-review

Score 0 to 10 per criterion with evidence (screenshot name or file:line). Blocking criteria below 7 cap the verdict at `PARTIAL`.

| # | Criterion | Weight | Blocking |
|---|---|---|---|
| 1 | Matches the source artifact and the project's design rules (tokens only, shared components, no invented screen) | 3 | yes |
| 2 | Acceptance criteria visible in the screenshots | 3 | yes |
| 3 | States: empty, loading, error, stale/offline where data can be old | 2 | yes |
| 4 | Accessibility AA: contrast, names for controls, focus visible and in order, not color alone | 2 | yes |
| 5 | Responsive: 400 px without horizontal scroll, touch targets ≥ 44 px, tables scroll inside | 2 | yes |
| 6 | Usability heuristics (status visible, user language, undo, consistency, error prevention, recognition, efficiency, minimal, recovery, help) read for the real user | 2 | no |
| 7 | Text: user's language, no internal names, no fixed strings where the project uses i18n | 1 | no |
| 8 | Light and dark both checked | 1 | no |

## Calibration

1. Screenshot only in light theme; dark has unreadable text. Criterion 8 ≤ 3, criterion 4 ≤ 5.
2. New color written as a hex value instead of a token. Criterion 1 ≤ 5.
3. Error state is a blank area. Criterion 3 ≤ 3.
4. Icon-only button without an accessible name. Criterion 4 ≤ 4.

Project examples: `.claude/orchestrator/rubrics/examples/ui-*.md` when present.
