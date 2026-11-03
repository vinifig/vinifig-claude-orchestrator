# Node/TypeScript rules for code-implement

- Follow the module system the package already uses (ESM vs CJS); do not mix.
- Validate external input at the edge with the schema library the project uses (zod, valibot, yup); types come from the schema.
- Configuration is read in one module and validated at startup (fail early); nowhere else reads `process.env`.
- One composition root wires implementations; domain and use cases never import adapters, frameworks or `node:` modules.
- Async: always `await` or return promises; no floating promises; errors become the project's error type at the boundary.
- UI: shared components and design tokens only; no inline hex colours; texts through the project's i18n if it has one.
- Commands: `{{PM_RUN}} test`, `{{PM_RUN}} typecheck`, `{{PM_RUN}} lint`, `{{PM_RUN}} build` (check `package.json` scripts; in a monorepo filter by package, e.g. `pnpm --filter <pkg> test`).
