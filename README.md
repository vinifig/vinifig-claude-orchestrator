# vinifig-claude-orchestrator

A Claude Code orchestrator you install into any repository: one command decides whether an ask is a single task or an epic and runs it with a team of review agents, TDD, real gates and stacked PRs. Hard rules are enforced by hooks, run state lives in JSON, and every agent run is measured.

```text
/initiative-execute fix the stale-data badge on the Data screen
/initiative-plan proofs one click away from every number
/epic-execute EP-10                 # local board .ai/board/EP-10.yaml
/epic-execute #12 parallel          # GitHub epic, parallel waves in worktrees
/task-execute investigate #15
```

## Install

Needs `python3` 3.8+ and `git` (standard library only, nothing else to install). The repository is private, so every route uses your own GitHub credentials.

```bash
# from a clone (recommended: rerun it to update)
git clone git@github.com:vinifig/vinifig-claude-orchestrator.git ~/workspace/vinifig-claude-orchestrator
cd my-repo
python3 ~/workspace/vinifig-claude-orchestrator/installer/install.py --preset node-cloudflare
# or: bash ~/workspace/vinifig-claude-orchestrator/install.sh --preset node-cloudflare

# with npx (Node 18+)
npx github:vinifig/vinifig-claude-orchestrator --preset node

# without a clone (install.sh clones to a temp dir and runs the installer)
bash <(gh api repos/vinifig/vinifig-claude-orchestrator/contents/install.sh -H 'Accept: application/vnd.github.raw') --preset flutter
```

Options: `--list` (presets), `--overlay DIR` (repeatable), `--pm npm|pnpm|yarn|bun` (default: from the lockfile), `--target DIR`, `--dry-run`, `--force`.

Then open Claude Code in the repo, check `.claude/orchestrator.json` (language, approver, workstream paths and gates) and run `/initiative-execute <ask>`.

## Presets

| Preset | Extends | Adds |
|---|---|---|
| `node` | | `backend`, `frontend`, `shared` workstreams; lint/typecheck/test/build gates through the detected package manager; Vitest/Jest and Playwright rules |
| `node-cloudflare` | `node` | `edge` workstream (Workers, Pages Functions, D1, KV, R2), `cloudflare-arch-review`; every `wrangler` deploy, secret or remote-data command asks a person; `.dev.vars*` blocked |
| `flutter` | | `presentation`, `domain`, `data`, `platform` workstreams; `dart format`, `flutter analyze`, `flutter test`; simulators, goldens, Widgetbook; `app-run` skill |
| `python` | | `app` workstream; ruff, mypy/pyright when configured, pytest |
| `go` | | `service` workstream; gofmt, go vet, `go test -race`, golangci-lint when present |

`python3 installer/install.py --list` prints them. A new stack is a folder in `presets/` with a `preset.json` (`description`, optional `extends`).

## Layers and overlays

The installer stacks layers, each a folder with the same shape:

```text
core/ → presets/<preset>/ (after the presets it extends) → --overlay DIR ...

<layer>/
  preset.json        presets only: description, extends
  files/             copied into the repo (.claude/agents, skills, hooks, orchestrator/rules ...)
  orchestrator.json  merged into .claude/orchestrator.json
  settings.json      merged into .claude/settings.json
  claude-md.md       goes into the managed block of CLAUDE.md
  agents-md.md       goes into the managed block of AGENTS.md
  gitignore.txt      goes into the managed block of .gitignore
```

- Later layers win for scalars, dicts merge, lists union. `null` in a layer's JSON removes an inherited key (an overlay drops the generic `backend` workstream with `"backend": null`). An empty `files/<path>.remove` removes an inherited file.
- Project-specific content (workstreams, architects in the project's language, role rules) belongs in an **overlay kept in that project's repo**, e.g. `.claude/orchestrator-overlay/`, never in this repo.

## Updating is safe

- Idempotent: a second run with the same inputs reports `created 0 · updated 0 · merged 0`.
- A manifest (`.claude/orchestrator/.manifest.json`) records the hash of every installed file. A file you edited is never overwritten: the new version lands next to it as `*.orchestrator-new` (or `--force` replaces it and keeps a `.bak`).
- Your `settings.json` permissions and hooks are kept (union); your values in `orchestrator.json` win; your text in `CLAUDE.md`, `AGENTS.md` and `.gitignore` stays outside the marked blocks.
- Files a newer version (or a dropped overlay) no longer ships are removed only if you never edited them.

## What gets installed

| Path | What |
|---|---|
| `.claude/skills/` | `initiative-plan`, `initiative-execute`, `epic-execute`, `task-execute`, `task-board`, `workstreams`, `ui-validate`, `ui-review`, `eval-suite-run` |
| `.claude/agents/` | `plan-design`, `plan-verify`, `tests-review`, `tests-implement`, `code-implement`, `security-review`, `db-review`, `perf-review`, `docs-write`, `arch-review` + the preset's architects |
| `.claude/hooks/` | `guard_bash`, `guard_files`, `subagent_start`, `subagent_stop`, `session_start` |
| `.claude/orchestrator/` | `bin/orch.py`, JSON schemas, rubrics with calibration examples, role rules |
| `.claude/workflows/` | dynamic-workflow pilots `specialists-review` and `delivery-audit` (off by default) |
| `.claude/orchestrator.json` | the project's config: language, approver, board, workstreams, gates, team sizes, guards |
| `.ai/plans/`, `.ai/evals/` | plans and reports (in git); eval cases |

The map installed in each repo is `.claude/orchestrator/README.md`.

## The 10 improvements from the market comparison

From the comparison with 15 market and open-source orchestrators (verdict: keep the orchestrator-worker model over shared files; A2A is not needed for a dev orchestrator):

| # | Improvement | Where |
|---|---|---|
| 1 | Structured output: every agent ends with a JSON block validated against a schema | `core/files/.claude/orchestrator/schemas/`, `hooks/subagent_stop.py`, `orch.py output-check` |
| 2 | Hard rules as hooks, not reminders: no `git add -A`, no push to main, no force push, no `--no-verify`, no secret reads, cloud deploys ask | `hooks/guard_bash.py`, `hooks/guard_files.py`, `guards` in `orchestrator.json` |
| 3 | Run state in `state.json` with a schema; `_wave_strategy.md` is a rendered view | `orch.py state ...`, `schemas/state.schema.json` |
| 4 | Team sized by task (S/M/L, labels add specialists) and cost per task/agent | `teams` in `orchestrator.json`, `orch.py team`, `orch.py cost` |
| 5 | Dynamic-workflow pilots for specialist review and the delivery audit | `core/files/.claude/workflows/` |
| 6 | Event log per epic (agent start/stop, tokens, time, gates, blocks) | `.ai/context/<epic>/events.jsonl`, `orch.py event` |
| 7 | Rubrics with examples for `plan-verify` and `ui-review` | `core/files/.claude/orchestrator/rubrics/` |
| 8 | Parallel mode only for tasks with disjoint files, phases separated | `orch.py overlap`, `/epic-execute ... parallel` |
| 9 | Eval set to measure the orchestrator itself (pass rate, cost, time vs a baseline) | `/eval-suite-run`, `orch.py eval`, `.ai/evals/` |
| 10 | Agent teams only for `investigate` | `investigate.agent_teams` in `orchestrator.json`, `task-execute` |

## Naming

Skills and agents are English, `<noun>-<secondary noun>-<verb>` (`epic-execute`, `app-core-arch-review`). Text the agents write follows `language` in `orchestrator.json`.

## Development

```bash
bash tests/test_install.sh      # every preset (fresh, rerun, edit conflict, merges, overlays), orch.py and hooks
```

CI runs the same script on every push and PR (`.github/workflows/test.yml`). Bump `VERSION` (and `package.json`) when a change should reach installed repos.
