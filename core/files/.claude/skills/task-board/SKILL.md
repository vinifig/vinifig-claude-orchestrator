---
name: task-board
description: Single port to read and update tasks and epics, with three adapters — local file (YAML in .ai/board/, out of git, default), GitHub Issues (gh) and Linear (MCP). Defines the task format (with blocked_by, workstream, size) and the six operations /epic-execute, /task-execute and /initiative-plan use. Same contract as the TaskBoard port of vinifig_orchestrator. Use whenever a flow needs to fetch, list, comment on or change the status of a task.
---

# Task board

The flows never talk to a tracker directly. They call the operations below and this skill translates them for the adapter in use. Same shape as the `TaskBoard` port of `vinifig/vinifig_orchestrator` (`fetch_task`, `fetch_children`, `update_status`, `post_comment`, `attach_label`, `remove_label`), plus `blocked_by` to build waves and `size` to pick the team.

## Task

```yaml
id: APP-12                    # adapter id (local: free; GitHub: "#12"; Linear: "ABC-123")
title: "Download route for reports"
description: |
  What and why. Acceptance criteria can live here or in acceptance_criteria.
status: todo                  # backlog | todo | in_progress | in_review | done | canceled | blocked
parent_id: APP-10             # the epic; empty on the epic itself
workstream: server            # one of .claude/orchestrator.json → workstreams; empty = found from paths
size: M                       # S | M | L (team size); empty = measured by the flow
blocked_by: [APP-11]          # ids that must be done first (builds the waves)
priority: medium              # urgent | high | medium | low
git_branch_name: feat/app-12-download-route   # optional; filled by /epic-execute
labels: [external-input]      # ui | db | external-input | auth | perf add specialists
acceptance_criteria:
  - "a signed-in user downloads the PDF from the report page"
source: local                 # local | github | linear
metadata: {}                  # comments, PR, links
```

## Operations

GitHub repo: `.claude/orchestrator.json` → `board.github_repo`, else `gh repo view --json nameWithOwner -q .nameWithOwner`.

| Operation | Local | GitHub (`gh`) | Linear (MCP) |
|---|---|---|---|
| `fetch_task(id)` | read the YAML (`orch.py board show <file>`) | `gh issue view <n> --json number,title,body,state,labels` | `get_issue` |
| `fetch_children(parent_id)` | tasks of `.ai/board/<epic>.yaml`, or `parent_id` match in `tasks.yaml` | sub-issues: `gh api repos/<repo>/issues/<n>/sub_issues`; without them, the task list (`- [ ] #n`) in the epic body | `list_issues` with `parentId` |
| `update_status(id, status)` | edit the YAML | `done`/`canceled` close (`gh issue close`, `--reason "not planned"` for canceled); others become label `status:<value>` | `update_issue` with the matching state |
| `post_comment(id, body)` | `metadata.comments` | `gh issue comment` | `create_comment` |
| `attach_label(id, label)` | `labels` | `gh issue edit --add-label` | `update_issue` |
| `remove_label(id, label)` | `labels` | `gh issue edit --remove-label` | `update_issue` |

`blocked_by` on GitHub: the issue's "blocked by" relation if present, else lines `Blocked by: #11, #13` in the body. On Linear: the `blockedBy` relation. `workstream` and `size`: labels `workstream:<name>` and `size:<S|M|L>` on GitHub and Linear.

## Local adapter (default)

- Folder `.ai/board/` (out of git). One file per epic: `.ai/board/<epic-id>.yaml` with `epic:` and `tasks:`; loose tasks in `.ai/board/tasks.yaml`.
- For epics that exist in no tracker yet (a roadmap section, a list in a doc).
- Edit the YAML with Read + Edit, keeping the rest of the file. Check it with `python3 .claude/orchestrator/bin/orch.py waves .ai/board/<epic-id>.yaml` (prints waves, fails on cycles).

```yaml
epic:
  id: APP-10
  title: "Export reports as PDF"
  description: "Renderer port, adapter and download route."
tasks:
  - id: APP-11
    title: "Renderer port and in-memory adapter"
    workstream: core
    size: M
    status: todo
    blocked_by: []
  - id: APP-12
    title: "Download route"
    workstream: server
    size: M
    status: todo
    blocked_by: [APP-11]
```

## Pick the adapter

1. The argument says: `#12` or a GitHub URL → GitHub; `ABC-123` with the Linear MCP connected → Linear; a `.yaml` file or an id found in `.ai/board/` → local.
2. No hint: look for the id in `.ai/board/*.yaml`; then `gh issue view`; then `board.default`.
3. Not found: ask once which one, and offer to create the epic in the local adapter.

## Rules

- **Read once, keep in context**: `/epic-execute` copies each task to `.ai/context/<epic>/<id>.md`; agents read that file and never call the board.
- **Writing to the board belongs to the main flow**, not to agents.
- Comments and status changes on GitHub or Linear are visible to other people: only what the flow defines (start, PR opened, end), in the configured language.
- Never put a secret in a task, comment or label.
