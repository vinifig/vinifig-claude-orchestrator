# Node/TypeScript rules for tests-implement

- Runner: whatever the package uses (Vitest or Jest); run one file with `{{PM_EXEC}} vitest run <file>` or `{{PM_EXEC}} jest <file>`.
- UI: Testing Library queries by role and accessible name; MSW (or the project's fetch double) for HTTP; no real network.
- End to end and screenshots: Playwright (`{{PM_EXEC}} playwright test`), against a built app when the project has a preview server.
- Fake timers or an injected clock for anything time-based.
- Never `it.skip`, `it.only`, `expect.anything()` where an exact value is possible, or a loosened timeout to pass.
