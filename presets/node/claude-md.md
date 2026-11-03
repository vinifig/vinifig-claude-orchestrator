### Node stack ({{PM}})

- Package manager: `{{PM}}`. Never mix lockfiles; add dependencies with `{{PM}}` only, with a reason in the plan.
- Gates per workstream are in `.claude/orchestrator.json`; adjust paths and scripts to this repository.
- TypeScript strict where the project already is; no `any` to silence errors; no `// @ts-ignore` without a comment saying why.
