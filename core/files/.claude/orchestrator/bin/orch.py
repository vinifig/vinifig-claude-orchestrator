#!/usr/bin/env python3
"""orch: machine-readable state, events, gates, cost and evals for the orchestrator.

The skills (/epic-execute, /task-execute, /initiative-plan) call this script so
that execution state lives in JSON with a schema instead of a Markdown table the
model edits by hand. Standard library only.

  orch.py board show <board.yaml|json>             tasks as JSON (local adapter)
  orch.py waves <board-or-tasks.json>              waves from blocked_by (fails on cycles)
  orch.py state init <epic> --board B --mode M --base BR [--tasks-file F]
  orch.py state show <epic> [--json]
  orch.py state task <epic> <id> key=value ...     status, branch, base, pr, plan, size, team, files+=a,b, rounds+=1
  orch.py state decision <epic> "<text>"
  orch.py state approval <epic> "<command>" "<why>"
  orch.py state render <epic>                      writes _wave_strategy.md from state.json
  orch.py state resume <epic>                      next task and the step to resume from
  orch.py current set <epic> <task> [--workstream W] [--size S]   | current clear | current show
  orch.py event <epic> <type> key=value ...        appends to events.jsonl
  orch.py output-check [--schema NAME] [--file F]  validates the last ```json block of an agent reply
  orch.py overlap <epic> [ids...]                  groups tasks of a wave so no two in a group share files
  orch.py gates [--workstream W] [--run]           lists (or runs) the gates of a workstream
  orch.py team <size> [--labels a,b]               the team for a task size, from orchestrator.json
  orch.py cost <epic> [--json]                     tokens, time and rounds per task and per agent
  orch.py eval list | eval run <case> | eval compare <run.json> [--baseline F] | eval baseline <run.json>
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

STATUSES = ["pending", "in-progress", "done", "skipped", "blocked"]
STEPS = ["context", "specialists", "plan", "red", "green", "ui", "audit", "pr", "done"]


# ---------------------------------------------------------------- paths/config

def root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except Exception:
        return Path.cwd()


def config() -> dict:
    p = root() / ".claude/orchestrator.json"
    return json.loads(p.read_text()) if p.exists() else {}


def schemas_dir() -> Path:
    return root() / ".claude/orchestrator/schemas"


def epic_key(epic: str) -> str:
    e = epic.strip().lower()
    if e.startswith("#"):
        e = "gh-" + e[1:]
    e = re.sub(r"\.ya?ml$|\.json$", "", Path(e).name)
    return re.sub(r"[^a-z0-9._-]+", "-", e).strip("-") or "epic"


def ctx_dir(epic: str) -> Path:
    return root() / ".ai/context" / epic_key(epic)


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def die(msg: str, code: int = 1):
    print(f"orch: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- tiny YAML

def parse_yaml(text: str):
    """YAML subset used by the local board: maps, lists, scalars, [a, b], | blocks."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        pass
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            lines.append((None, raw))
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), raw))
    pos = 0

    def scalar(s: str):
        s = s.strip()
        if s[:1] in ("'", '"'):
            end = s.find(s[0], 1)
            if end > 0 and s[end + 1:].strip().startswith("#"):
                s = s[: end + 1]  # "quoted"  # comment
        elif " #" in s:
            s = s.split(" #", 1)[0].rstrip()
        if s in ("", "~", "null"):
            return None
        if s in ("true", "false"):
            return s == "true"
        if s.startswith("[") and s.endswith("]"):
            inner = s[1:-1].strip()
            return [scalar(x) for x in split_flow(inner)] if inner else []
        if s.startswith("{") and s.endswith("}"):
            return {} if s == "{}" else {k.strip(): scalar(v) for k, v in (x.split(":", 1) for x in split_flow(s[1:-1]))}
        if (s[0] == s[-1]) and s[0] in "'\"" and len(s) > 1:
            return s[1:-1]
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        if re.fullmatch(r"-?\d+\.\d+", s):
            return float(s)
        return s

    def split_flow(s: str):
        out, buf, q, depth = [], "", None, 0
        for ch in s:
            if q:
                buf += ch
                q = None if ch == q else q
            elif ch in "'\"":
                q = ch
                buf += ch
            elif ch in "[{":
                depth += 1
                buf += ch
            elif ch in "]}":
                depth -= 1
                buf += ch
            elif ch == "," and depth == 0:
                out.append(buf)
                buf = ""
            else:
                buf += ch
        if buf.strip():
            out.append(buf)
        return out

    def skip_blank():
        nonlocal pos
        while pos < len(lines) and lines[pos][0] is None:
            pos += 1

    def block_scalar(indent: int, folded: bool) -> str:
        nonlocal pos
        body = []
        while pos < len(lines):
            ind, raw = lines[pos]
            if ind is not None and ind <= indent:
                break
            body.append(raw)
            pos += 1
        nonempty = [l for l in body if l.strip()]
        cut = min((len(l) - len(l.lstrip(" ")) for l in nonempty), default=0)
        text_lines = [l[cut:] for l in body]
        while text_lines and not text_lines[-1].strip():
            text_lines.pop()
        return (" ".join(text_lines) if folded else "\n".join(text_lines)) + "\n"

    def parse_block(indent: int):
        nonlocal pos
        skip_blank()
        if pos >= len(lines):
            return None
        ind, raw = lines[pos]
        if raw.strip().startswith("- ") or raw.strip() == "-":
            return parse_list(ind)
        return parse_map(ind)

    def parse_value(rest: str, indent: int):
        nonlocal pos
        rest = rest.strip()
        if rest in ("|", "|-", ">", ">-"):
            return block_scalar(indent, rest.startswith(">"))
        if rest == "":
            skip_blank()
            if pos < len(lines) and lines[pos][0] is not None and (
                lines[pos][0] > indent or (lines[pos][0] == indent and lines[pos][1].strip().startswith("-"))
            ):
                return parse_block(lines[pos][0])
            return None
        return scalar(rest)

    def parse_map(indent: int):
        nonlocal pos
        out = {}
        while True:
            skip_blank()
            if pos >= len(lines):
                break
            ind, raw = lines[pos]
            if ind != indent or raw.strip().startswith("- "):
                break
            m = re.match(r"\s*([^:]+?):(\s+.*|)$", raw)
            if not m:
                break
            pos += 1
            out[m.group(1).strip().strip("'\"")] = parse_value(m.group(2), indent)
        return out

    def parse_list(indent: int):
        nonlocal pos
        out = []
        while True:
            skip_blank()
            if pos >= len(lines):
                break
            ind, raw = lines[pos]
            if ind != indent or not raw.strip().startswith("-"):
                break
            item = raw.strip()[1:].strip()
            if re.match(r"^[^'\"\[{][^:]*:(\s|$)", item):
                # "- key: value" starts a map whose keys sit at indent + 2
                after_dash = raw.lstrip(" ")[1:]
                child = indent + 1 + (len(after_dash) - len(after_dash.lstrip(" ")))
                lines[pos] = (child, " " * child + item)
                out.append(parse_map(child))
            else:
                pos += 1
                out.append(parse_value(item, indent))
        return out

    return parse_block(0)


def load_board(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        p = root() / ".ai/board" / path
        if not p.suffix:
            for ext in (".yaml", ".yml", ".json"):
                if p.with_suffix(ext).exists():
                    p = p.with_suffix(ext)
                    break
    if not p.exists():
        die(f"board not found: {path}")
    text = p.read_text()
    data = json.loads(text) if p.suffix == ".json" else parse_yaml(text)
    if isinstance(data, list):
        data = {"tasks": data}
    data.setdefault("tasks", [])
    for t in data["tasks"]:
        t.setdefault("blocked_by", [])
        t.setdefault("labels", [])
        t["id"] = str(t["id"])
        t["blocked_by"] = [str(x) for x in (t["blocked_by"] or [])]
    return data


# ---------------------------------------------------------------- waves

def compute_waves(tasks: list[dict]) -> list[list[str]]:
    actionable = {t["id"]: t for t in tasks if t.get("status") not in ("done", "canceled")}
    done = {t["id"] for t in tasks if t.get("status") == "done"}
    placed: set[str] = set()
    waves: list[list[str]] = []
    while len(placed) < len(actionable):
        wave = [tid for tid, t in actionable.items() if tid not in placed
                and all(d in placed or d in done or d not in actionable for d in t["blocked_by"])]
        if not wave:
            rest = sorted(set(actionable) - placed)
            die("dependency cycle among: " + ", ".join(rest), 3)
        prio = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        wave.sort(key=lambda i: (prio.get(str(actionable[i].get("priority", "medium")), 2), i))
        waves.append(wave)
        placed.update(wave)
    return waves


# ---------------------------------------------------------------- state

def state_path(epic: str) -> Path:
    return ctx_dir(epic) / "state.json"


def load_state(epic: str) -> dict:
    p = state_path(epic)
    if not p.exists():
        die(f"no state for {epic} ({p}); run: orch.py state init", 2)
    return json.loads(p.read_text())


def save_state(epic: str, st: dict) -> None:
    st["updated_at"] = now()
    errs = validate(st, load_schema("state"))
    if errs:
        die("state.json would be invalid: " + "; ".join(errs[:5]))
    p = state_path(epic)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(p)
    render_md(epic, st)


def find_task(st: dict, tid: str) -> dict:
    for w in st["waves"]:
        for t in w["tasks"]:
            if t["id"].lower() == tid.lower():
                return t
    die(f"task {tid} not in state for {st['epic']}")


def cmd_state(args: list[str]) -> None:
    if not args:
        die("state needs a subcommand")
    sub, rest = args[0], args[1:]
    if sub == "init":
        epic = rest[0]
        opts = kv_opts(rest[1:])
        board = load_board(opts.get("board", epic))
        tasks = board["tasks"]
        if opts.get("tasks-file"):
            tasks = json.loads(Path(opts["tasks-file"]).read_text())
        waves = compute_waves(tasks)
        by_id = {t["id"]: t for t in tasks}
        mode = opts.get("mode", "sequential-teams")
        base = opts.get("base") or git_branch()
        st = {
            "schema": 1,
            "epic": board.get("epic", {}).get("id", epic) if isinstance(board.get("epic"), dict) else epic,
            "title": (board.get("epic") or {}).get("title", "") if isinstance(board.get("epic"), dict) else "",
            "mode": mode,
            "board": opts.get("board-adapter", "local"),
            "base_branch": base,
            "created_at": now(),
            "updated_at": now(),
            "waves": [],
            "decisions": [],
            "approvals_pending": [],
            "discovered": [],
        }
        prev = base
        for i, wave in enumerate(waves, 1):
            entries = []
            for tid in wave:
                t = by_id[tid]
                entries.append({
                    "id": tid,
                    "title": t.get("title", ""),
                    "workstream": t.get("workstream") or "",
                    "labels": t.get("labels") or [],
                    "blocked_by": t.get("blocked_by") or [],
                    "size": t.get("size") or "",
                    "status": "pending",
                    "step": "context",
                    "branch": t.get("git_branch_name") or "",
                    "base": "",
                    "pr": None,
                    "plan": "",
                    "files": [],
                    "rounds": 0,
                    "team": [],
                    "verdict": "",
                    "note": "",
                })
            st["waves"].append({"n": i, "tasks": entries})
        # sequential: each task's base is the previous task's branch (stacked PRs)
        for w in st["waves"]:
            for t in w["tasks"]:
                t["base"] = base if mode == "parallel" else prev
                if mode != "parallel":
                    prev = t["branch"] or f"<branch of {t['id']}>"
        if state_path(epic).exists() and "--force" not in rest:
            die(f"state exists for {epic}; resume instead (or pass --force)")
        save_state(epic, st)
        event(epic, "epic_started", {"mode": mode, "tasks": len(by_id), "waves": len(waves)})
        print(json.dumps({"state": str(state_path(epic)), "waves": waves}, indent=2))
    elif sub == "show":
        st = load_state(rest[0])
        if "--json" in rest:
            print(json.dumps(st, indent=2, ensure_ascii=False))
        else:
            print(summary_line(st))
            for w in st["waves"]:
                for t in w["tasks"]:
                    print(f"  W{w['n']} {t['id']:<10} {t['status']:<12} {t['step']:<12} {t['branch'] or '-':<30} PR {t['pr'] or '-'}")
    elif sub == "task":
        epic, tid, pairs = rest[0], rest[1], rest[2:]
        st = load_state(epic)
        t = find_task(st, tid)
        changes = {}
        for pair in pairs:
            if "+=" in pair:
                k, v = pair.split("+=", 1)
                if k == "rounds":
                    t["rounds"] = int(t.get("rounds", 0)) + int(v or 1)
                elif k in ("files", "team", "labels"):
                    t[k] = sorted(set(t.get(k, [])) | {x.strip() for x in v.split(",") if x.strip()})
                else:
                    die(f"cannot += {k}")
                changes[k] = t[k]
                continue
            k, v = pair.split("=", 1)
            if k == "status" and v not in STATUSES:
                die(f"status must be one of {STATUSES}")
            if k == "step" and v not in STEPS:
                die(f"step must be one of {STEPS}")
            if k == "pr":
                v = int(v.lstrip("#")) if v.lstrip("#").isdigit() else v
            if k in ("files", "team", "labels"):
                v = [x.strip() for x in v.split(",") if x.strip()]
            t[k] = v
            changes[k] = v
        # keep the stacked base of the next task in sync with this task's branch
        if "branch" in changes and st["mode"] != "parallel":
            flat = [x for w in st["waves"] for x in w["tasks"]]
            for a, b in zip(flat, flat[1:]):
                if a is t:
                    b["base"] = t["branch"]
        save_state(epic, st)
        event(epic, "task_updated", {"task": t["id"], **changes})
        print(json.dumps(t, ensure_ascii=False))
    elif sub == "decision":
        st = load_state(rest[0])
        st["decisions"].append({"at": now(), "text": " ".join(rest[1:])})
        save_state(rest[0], st)
        event(rest[0], "decision", {"text": " ".join(rest[1:])})
    elif sub == "approval":
        st = load_state(rest[0])
        item = {"command": rest[1], "why": " ".join(rest[2:]), "at": now()}
        st["approvals_pending"].append(item)
        save_state(rest[0], st)
        event(rest[0], "approval_needed", item)
    elif sub == "discover":
        # orch.py state discover <epic> <tasks.json>: append new tasks as new waves
        epic = rest[0]
        st = load_state(epic)
        known = {t["id"] for w in st["waves"] for t in w["tasks"]}
        new = [t for t in json.loads(Path(rest[1]).read_text()) if str(t["id"]) not in known]
        for t in new:
            t["id"] = str(t["id"])
            t.setdefault("blocked_by", [])
        for i, wave in enumerate(compute_waves(new), len(st["waves"]) + 1):
            st["waves"].append({"n": i, "tasks": [{
                "id": tid, "title": next(x for x in new if x["id"] == tid).get("title", ""),
                "workstream": next(x for x in new if x["id"] == tid).get("workstream", ""),
                "labels": [], "blocked_by": next(x for x in new if x["id"] == tid).get("blocked_by", []),
                "size": "", "status": "pending", "step": "context", "branch": "", "base": "", "pr": None,
                "plan": "", "files": [], "rounds": 0, "team": [], "verdict": "", "note": ""} for tid in wave]})
        st["discovered"].append({"at": now(), "ids": [t["id"] for t in new]})
        save_state(epic, st)
        print(json.dumps([t["id"] for t in new]))
    elif sub == "render":
        st = load_state(rest[0])
        render_md(rest[0], st)
        print(ctx_dir(rest[0]) / "_wave_strategy.md")
    elif sub == "resume":
        st = load_state(rest[0])
        for w in st["waves"]:
            for t in w["tasks"]:
                if t["status"] in ("in-progress", "pending"):
                    print(json.dumps({"summary": summary_line(st), "task": t["id"], "title": t["title"],
                                      "status": t["status"], "resume_step": t["step"], "branch": t["branch"],
                                      "base": t["base"], "plan": t["plan"]}, ensure_ascii=False))
                    return
        print(json.dumps({"summary": summary_line(st), "task": None}))
    else:
        die(f"unknown state subcommand {sub}")


def summary_line(st: dict) -> str:
    flat = [t for w in st["waves"] for t in w["tasks"]]
    done = sum(t["status"] == "done" for t in flat)
    nxt = next((t for t in flat if t["status"] in ("in-progress", "pending")), None)
    tail = f" Next: {nxt['id']} {nxt['title']} (step {nxt['step']})." if nxt else " All tasks finished."
    return f"Epic {st['epic']}: {done}/{len(flat)} done.{tail}"


def render_md(epic: str, st: dict) -> None:
    out = [f"# Epic run: {st['epic']} {('· ' + st['title']) if st.get('title') else ''}".rstrip(), "",
           "> Generated from `state.json` by `orch.py state render`. Do not edit by hand.", "",
           f"**Created:** {st['created_at']} · **Updated:** {st['updated_at']} · **Mode:** {st['mode']} · "
           f"**Base:** {st['base_branch']} · **Board:** {st['board']}", "", summary_line(st), "", "## Waves", ""]
    for w in st["waves"]:
        out += [f"### Wave {w['n']}", "", "| ID | Title | Workstream | Size | Branch | Base | Status | Step | Rounds | PR |",
                "|----|-------|------------|------|--------|------|--------|------|--------|----|"]
        for t in w["tasks"]:
            out.append(f"| {t['id']} | {t['title']} | {t['workstream']} | {t.get('size') or '-'} | {t['branch'] or '-'} | "
                       f"{t['base'] or '-'} | {t['status']} | {t['step']} | {t['rounds']} | {('#' + str(t['pr'])) if t['pr'] else '-'} |")
        out.append("")
    out += ["## Decisions", ""] + [f"- {d['at']}: {d['text']}" for d in st["decisions"]] + [""]
    out += ["## Pending approval", ""] + [f"- `{a['command']}`: {a['why']}" for a in st["approvals_pending"]] + [""]
    if st.get("discovered"):
        out += ["## Discovered", ""] + [f"- {d['at']}: {', '.join(d['ids'])}" for d in st["discovered"]] + [""]
    cost = cost_summary(epic)
    if cost["total"]["agents"]:
        tt = cost["total"]
        out += ["## Cost so far", "", f"{tt['agents']} agent runs · {fmt_tokens(tt['tokens'])} tokens · "
                f"{tt['seconds'] // 60} min" + (f" · ~US$ {tt['usd']:.2f}" if tt.get("usd") else ""), ""]
    (ctx_dir(epic) / "_wave_strategy.md").write_text("\n".join(out))


def git_branch() -> str:
    try:
        return subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip() or "main"
    except Exception:
        return "main"


def kv_opts(args: list[str]) -> dict:
    out, i = {}, 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:]
            if "=" in key:
                k, v = key.split("=", 1)
                out[k] = v
            elif i + 1 < len(args) and not args[i + 1].startswith("--"):
                out[key] = args[i + 1]
                i += 1
            else:
                out[key] = True
        i += 1
    return out


# ---------------------------------------------------------------- current task (read by hooks)

def cmd_current(args: list[str]) -> None:
    p = root() / ".ai/context/current.json"
    if not args or args[0] == "show":
        print(p.read_text() if p.exists() else "{}")
    elif args[0] == "set":
        opts = kv_opts(args[3:])
        data = {"epic": epic_key(args[1]), "task": args[2], "workstream": opts.get("workstream", ""),
                "size": opts.get("size", ""), "since": now()}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2) + "\n")
        print(json.dumps(data))
    elif args[0] == "clear":
        if p.exists():
            p.unlink()
    else:
        die("current set|clear|show")


def current() -> dict:
    p = root() / ".ai/context/current.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------- events

def event(epic: str | None, etype: str, data: dict) -> None:
    epic = epic or current().get("epic") or "_session"
    d = ctx_dir(epic)
    d.mkdir(parents=True, exist_ok=True)
    rec = {"at": now(), "type": etype, **data}
    with open(d / "events.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def cmd_event(args: list[str]) -> None:
    epic, etype = args[0], args[1]
    data = {}
    for pair in args[2:]:
        k, v = pair.split("=", 1)
        try:
            data[k] = json.loads(v)
        except json.JSONDecodeError:
            data[k] = v
    event(epic, etype, data)


# ---------------------------------------------------------------- structured output

def load_schema(name: str) -> dict:
    p = schemas_dir() / f"{name}.schema.json"
    if not p.exists():
        die(f"schema not found: {p}")
    return json.loads(p.read_text())


def validate(obj, schema: dict, path: str = "$") -> list[str]:
    """Small JSON Schema subset: type, required, properties, items, enum, minLength, minItems, anyOf, const."""
    errs: list[str] = []
    if "anyOf" in schema:
        if all(validate(obj, s, path) for s in schema["anyOf"]):
            errs.append(f"{path}: matches none of anyOf")
        return errs
    t = schema.get("type")
    types = t if isinstance(t, list) else [t] if t else []
    pymap = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool, "null": type(None)}
    if types and not any(isinstance(obj, pymap[x]) and not (x in ("integer", "number") and isinstance(obj, bool)) for x in types):
        return [f"{path}: expected {'/'.join(types)}, got {type(obj).__name__}"]
    if "const" in schema and obj != schema["const"]:
        errs.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and obj not in schema["enum"]:
        errs.append(f"{path}: {obj!r} not in {schema['enum']}")
    if isinstance(obj, str) and len(obj) < schema.get("minLength", 0):
        errs.append(f"{path}: too short")
    if isinstance(obj, dict):
        for k in schema.get("required", []):
            if k not in obj:
                errs.append(f"{path}: missing '{k}'")
        for k, sub in schema.get("properties", {}).items():
            if k in obj:
                errs += validate(obj[k], sub, f"{path}.{k}")
    if isinstance(obj, list):
        if len(obj) < schema.get("minItems", 0):
            errs.append(f"{path}: needs at least {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(obj):
                errs += validate(item, schema["items"], f"{path}[{i}]")
    return errs


def extract_json_block(text: str):
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
    if not blocks:
        return None, "no ```json block found at the end of the reply"
    try:
        return json.loads(blocks[-1]), None
    except json.JSONDecodeError as e:
        return None, f"last ```json block is not valid JSON: {e}"


def schema_for_agent(agent: str) -> str:
    cfg = config().get("structured_output", {})
    return cfg.get("schemas", {}).get(agent, "agent-output")


def cmd_output_check(args: list[str]) -> None:
    opts = kv_opts(args)
    text = Path(opts["file"]).read_text() if opts.get("file") else sys.stdin.read()
    obj, err = extract_json_block(text)
    if err:
        die(err, 2)
    name = opts.get("schema") or (schema_for_agent(opts["agent"]) if opts.get("agent") else "agent-output")
    errs = validate(obj, load_schema(name))
    if errs:
        die(f"output does not match {name}: " + "; ".join(errs[:8]), 2)
    print(json.dumps(obj, ensure_ascii=False))


# ---------------------------------------------------------------- overlap (parallel mode)

def cmd_overlap(args: list[str]) -> None:
    epic, ids = args[0], [a.lower() for a in args[1:]]
    st = load_state(epic)
    tasks = [t for w in st["waves"] for t in w["tasks"] if not ids or t["id"].lower() in ids]
    missing = [t["id"] for t in tasks if not t.get("files")]
    groups: list[list[dict]] = []
    for t in tasks:
        for g in groups:
            if not any(set(t["files"]) & set(o["files"]) or not t["files"] or not o["files"] for o in g):
                g.append(t)
                break
        else:
            groups.append([t])
    print(json.dumps({"groups": [[t["id"] for t in g] for g in groups],
                      "without_file_list": missing,
                      "note": "tasks without a file list never share a group"}, indent=2))


# ---------------------------------------------------------------- gates

def gates_for(workstream: str | None) -> list[str]:
    cfg = config()
    ws = cfg.get("workstreams", {})
    out = list(cfg.get("gates", {}).get("always", []))
    if workstream and workstream in ws:
        out += ws[workstream].get("gates", [])
    elif not workstream:
        out += cfg.get("gates", {}).get("default", [])
    seen, uniq = set(), []
    for g in out:
        if g not in seen:
            seen.add(g)
            uniq.append(g)
    return uniq


def run_gates(gates: list[str], timeout: int = 900) -> list[dict]:
    results = []
    for g in gates:
        start = dt.datetime.now()
        try:
            p = subprocess.run(g, shell=True, cwd=root(), capture_output=True, text=True, timeout=timeout)
            ok, out = p.returncode == 0, (p.stdout + p.stderr)
        except subprocess.TimeoutExpired:
            ok, out = False, f"timeout after {timeout}s"
        results.append({"command": g, "result": "pass" if ok else "fail",
                         "seconds": int((dt.datetime.now() - start).total_seconds()),
                         "detail": "\n".join(out.strip().splitlines()[-25:])})
        if not ok:
            break  # later gates usually depend on earlier ones
    return results


def cmd_gates(args: list[str]) -> None:
    opts = kv_opts(args)
    ws = opts.get("workstream") or current().get("workstream")
    gates = gates_for(ws)
    if not opts.get("run"):
        print(json.dumps({"workstream": ws, "gates": gates}, indent=2))
        return
    res = run_gates(gates)
    event(None, "gates_run", {"workstream": ws, "results": [{k: r[k] for k in ("command", "result", "seconds")} for r in res]})
    print(json.dumps(res, indent=2, ensure_ascii=False))
    sys.exit(0 if all(r["result"] == "pass" for r in res) else 1)


# ---------------------------------------------------------------- team sizing

def cmd_team(args: list[str]) -> None:
    size = args[0].upper()
    opts = kv_opts(args[1:])
    labels = set((opts.get("labels") or "").split(",")) - {""}
    teams = config().get("teams", {})
    if size not in teams:
        die(f"size must be one of {list(teams)}")
    team = teams[size]
    specialists = list(team.get("specialists", []))
    for label, extra in team.get("when_label", {}).items():
        if label in labels:
            specialists += [x for x in extra if x not in specialists]
    print(json.dumps({"size": size, "specialists": specialists, **{k: v for k, v in team.items() if k not in ("specialists", "when_label")}}, indent=2))


# ---------------------------------------------------------------- cost

def fmt_tokens(n: int) -> str:
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else str(n)


def cost_summary(epic: str) -> dict:
    p = ctx_dir(epic) / "events.jsonl"
    prices = config().get("cost", {}).get("usd_per_mtok", {})
    per_task: dict[str, dict] = {}
    per_agent: dict[str, dict] = {}
    total = {"agents": 0, "tokens": 0, "seconds": 0, "usd": 0.0}
    if p.exists():
        for line in p.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") != "agent_stopped":
                continue
            u = e.get("usage") or {}
            tok = sum(int(u.get(k, 0)) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
            usd = 0.0
            price = prices.get(e.get("model", ""), prices.get("default"))
            if price:
                usd = sum(int(u.get(k, 0)) * float(price.get(k, 0)) for k in price) / 1e6
            secs = int(e.get("seconds") or 0)
            for bucket, key in ((per_task, e.get("task") or "-"), (per_agent, e.get("agent") or "-")):
                b = bucket.setdefault(key, {"agents": 0, "tokens": 0, "seconds": 0, "usd": 0.0, "rounds": 0})
                b["agents"] += 1
                b["tokens"] += tok
                b["seconds"] += secs
                b["usd"] += usd
            total["agents"] += 1
            total["tokens"] += tok
            total["seconds"] += secs
            total["usd"] += usd
    try:
        st = load_state(epic) if state_path(epic).exists() else None
    except SystemExit:
        st = None
    if st:
        for t in (t for w in st["waves"] for t in w["tasks"]):
            per_task.setdefault(t["id"], {"agents": 0, "tokens": 0, "seconds": 0, "usd": 0.0, "rounds": 0})["rounds"] = t["rounds"]
    return {"total": total, "per_task": per_task, "per_agent": per_agent, "priced": bool(prices)}


def cmd_cost(args: list[str]) -> None:
    c = cost_summary(args[0])
    if "--json" in args:
        print(json.dumps(c, indent=2))
        return
    t = c["total"]
    print(f"{t['agents']} agent runs · {fmt_tokens(t['tokens'])} tokens · {t['seconds'] // 60} min"
          + (f" · ~US$ {t['usd']:.2f}" if c["priced"] else " · (set cost.usd_per_mtok in orchestrator.json for US$)"))
    for title, bucket in (("per task", c["per_task"]), ("per agent", c["per_agent"])):
        print(f"\n{title}:")
        for k, v in sorted(bucket.items(), key=lambda kv: -kv[1]["tokens"]):
            print(f"  {k:<28} {v['agents']:>3} runs {fmt_tokens(v['tokens']):>8} tok {v['seconds'] // 60:>4} min"
                  + (f"  rounds {v['rounds']}" if title == "per task" else "") + (f"  US$ {v['usd']:.2f}" if c["priced"] else ""))


# ---------------------------------------------------------------- evals

def evals_dir() -> Path:
    return root() / ".ai/evals"


def cmd_eval(args: list[str]) -> None:
    sub = args[0] if args else "list"
    cases = evals_dir() / "cases"
    if sub == "list":
        for p in sorted(cases.glob("*.json")):
            c = json.loads(p.read_text())
            print(f"{c['id']:<20} {c.get('title', '')}")
    elif sub == "run":
        print(json.dumps(eval_run(args[1], kv_opts(args[2:])), indent=2, ensure_ascii=False))
    elif sub == "compare":
        run = json.loads(Path(args[1]).read_text())
        opts = kv_opts(args[2:])
        base_p = Path(opts.get("baseline") or evals_dir() / "baseline.json")
        base = json.loads(base_p.read_text()) if base_p.exists() else {}
        rows, worse = [], False
        for case_id, r in run.items():
            b = base.get(case_id)
            row = {"case": case_id, "passed": r["passed"], "cost_usd": r.get("cost_usd"), "seconds": r.get("seconds"), "turns": r.get("turns")}
            if b:
                row["vs_baseline"] = {k: (r.get(k), b.get(k)) for k in ("passed", "cost_usd", "seconds", "turns")}
                worse |= (b.get("passed") and not r["passed"]) or (
                    b.get("cost_usd") and r.get("cost_usd") and r["cost_usd"] > b["cost_usd"] * 1.25)
            rows.append(row)
        print(json.dumps({"rows": rows, "regression": worse}, indent=2))
        sys.exit(1 if worse else 0)
    elif sub == "baseline":
        run = json.loads(Path(args[1]).read_text())
        (evals_dir() / "baseline.json").write_text(json.dumps(run, indent=2) + "\n")
        print(evals_dir() / "baseline.json")
    else:
        die("eval list|run|compare|baseline")


def eval_run(case_id: str, opts: dict) -> dict:
    """Replays a solved task in a throwaway worktree with `claude -p` and scores it."""
    case = json.loads((evals_dir() / "cases" / f"{case_id}.json").read_text())
    cfg = config().get("evals", {})
    wt = root().parent / f".orch-evals/{root().name}-{case_id}"
    if wt.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=root())
    subprocess.run(["git", "worktree", "add", "--detach", str(wt), case["base_ref"]], cwd=root(), check=True)
    start = dt.datetime.now()
    cmd = ["claude", "-p", case["command"], "--output-format", "json",
           "--permission-mode", cfg.get("permission_mode", "acceptEdits")]
    if cfg.get("allowed_tools"):
        cmd += ["--allowedTools", " ".join(cfg["allowed_tools"])]
    if opts.get("model"):
        cmd += ["--model", opts["model"]]
    proc = subprocess.run(cmd, cwd=wt, capture_output=True, text=True, timeout=int(cfg.get("timeout_seconds", 5400)))
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {"result": proc.stdout[-2000:], "is_error": True}
    checks = []
    for g in case.get("checks", []):
        p = subprocess.run(g, shell=True, cwd=wt, capture_output=True, text=True, timeout=900)
        checks.append({"command": g, "result": "pass" if p.returncode == 0 else "fail"})
    result = {
        "case": case_id,
        "passed": not out.get("is_error") and all(c["result"] == "pass" for c in checks),
        "checks": checks,
        "cost_usd": out.get("total_cost_usd"),
        "turns": out.get("num_turns"),
        "seconds": int((dt.datetime.now() - start).total_seconds()),
        "worktree": str(wt),
    }
    runs = evals_dir() / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    agg_p = runs / f"{stamp}.json"
    agg = json.loads(agg_p.read_text()) if agg_p.exists() else {}
    agg[case_id] = result
    agg_p.write_text(json.dumps(agg, indent=2) + "\n")
    if not opts.get("keep"):
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=root())
    result["run_file"] = str(agg_p)
    return result


# ---------------------------------------------------------------- main

def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "board" and args and args[0] == "show":
        print(json.dumps(load_board(args[1]), indent=2, ensure_ascii=False))
    elif cmd == "waves":
        src = args[0]
        tasks = json.loads(Path(src).read_text()) if src.endswith(".json") and Path(src).exists() else load_board(src)["tasks"]
        if isinstance(tasks, dict):
            tasks = tasks.get("tasks", [])
        for t in tasks:
            t["id"] = str(t["id"])
            t["blocked_by"] = [str(x) for x in t.get("blocked_by") or []]
        print(json.dumps(compute_waves(tasks)))
    elif cmd == "state":
        cmd_state(args)
    elif cmd == "current":
        cmd_current(args)
    elif cmd == "event":
        cmd_event(args)
    elif cmd == "output-check":
        cmd_output_check(args)
    elif cmd == "overlap":
        cmd_overlap(args)
    elif cmd == "gates":
        cmd_gates(args)
    elif cmd == "team":
        cmd_team(args)
    elif cmd == "cost":
        cmd_cost(args)
    elif cmd == "eval":
        cmd_eval(args)
    else:
        die(f"unknown command {cmd}; see orch.py --help")


if __name__ == "__main__":
    main()
