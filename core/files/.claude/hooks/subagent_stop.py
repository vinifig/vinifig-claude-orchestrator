#!/usr/bin/env python3
"""SubagentStop: the checks that used to depend on the agent remembering.

1. Structured output: agents listed in orchestrator.json structured_output.agents must end
   with a ```json block that matches their schema. Missing or invalid -> the agent is told
   to add it (exit 2 keeps it running).
2. Gates: agents listed in gates.on_subagent_stop (code-implement by default) must leave the
   current workstream's gates green. Red -> the failing output goes back to the agent.
3. Telemetry: tokens (from the agent transcript), model, time and result go to events.jsonl,
   which `orch.py cost` sums per task and per agent.
Each agent is blocked at most hooks.max_blocks times, then the orchestrator decides.
"""
from __future__ import annotations

import fnmatch
import json
import sys
import time
from pathlib import Path

from _hooklib import ROOT, config, orch, read_input

data = read_input()
cfg = config()
agent = data.get("agent_type") or ""
agent_id = data.get("agent_id") or ""
cur = orch.current()
state_file = ROOT / ".ai/context/_agents" / f"{agent_id}.json"
info = {}
if agent_id and state_file.exists():
    try:
        info = json.loads(state_file.read_text())
    except json.JSONDecodeError:
        info = {}
max_blocks = int(cfg.get("hooks", {}).get("max_blocks", 2))


def usage_from_transcript() -> tuple[dict, str]:
    path = data.get("agent_transcript_path") or ""
    totals, model = {}, ""
    if not path or not Path(path).exists():
        return totals, model
    for line in Path(path).read_text(errors="ignore").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        model = msg.get("model") or model
        for k, v in (msg.get("usage") or {}).items():
            if isinstance(v, (int, float)):
                totals[k] = totals.get(k, 0) + int(v)
    return totals, model


def block(reason: str) -> None:
    info["blocks"] = info.get("blocks", 0) + 1
    if agent_id:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(info))
    orch.event(cur.get("epic"), "agent_blocked", {"agent": agent, "task": cur.get("task", ""), "reason": reason[:500]})
    print(reason, file=sys.stderr)
    sys.exit(2)


text = data.get("last_assistant_message") or ""
if isinstance(text, list):
    text = "\n".join(p.get("text", "") for p in text if isinstance(p, dict))
so = cfg.get("structured_output", {})
checked = any(fnmatch.fnmatch(agent, pat) for pat in so.get("agents", []))
parsed, problem = None, ""
if checked:
    parsed, err = orch.extract_json_block(text)
    if err:
        problem = err
    else:
        errs = orch.validate(parsed, orch.load_schema(orch.schema_for_agent(agent)))
        if errs:
            problem = "; ".join(errs[:8])
    if problem and info.get("blocks", 0) < max_blocks:
        block(f"Your reply must end with the ```json block defined in .claude/agents/{agent}.md "
              f"(schema .claude/orchestrator/schemas/{orch.schema_for_agent(agent)}.schema.json). Problem: {problem}. "
              f"Reply again with only that block, filled in.")

gate_agents = cfg.get("gates", {}).get("on_subagent_stop", [])
gate_results = []
if any(fnmatch.fnmatch(agent, pat) for pat in gate_agents) and (not parsed or parsed.get("status") == "done"):
    gates = orch.gates_for(cur.get("workstream") or None)
    if gates:
        gate_results = orch.run_gates(gates, int(cfg.get("hooks", {}).get("gate_timeout_seconds", 900)))
        failed = [r for r in gate_results if r["result"] == "fail"]
        if failed and info.get("blocks", 0) < max_blocks:
            f = failed[0]
            block(f"Gate failed: `{f['command']}`\n{f['detail']}\nFix it (do not weaken tests or checks), rerun the gates, "
                  f"then end with the updated ```json block.")

usage, model = usage_from_transcript()
seconds = int(time.time() - info["start"]) if info.get("start") else None
orch.event(cur.get("epic"), "agent_stopped", {
    "agent": agent, "agent_id": agent_id, "task": cur.get("task", "") or info.get("task", ""),
    "model": model, "usage": usage, "seconds": seconds,
    "status": (parsed or {}).get("status"), "verdict": (parsed or {}).get("verdict"),
    "output_valid": (not problem) if checked else None, "blocks": info.get("blocks", 0),
    "gates": [{k: r[k] for k in ("command", "result")} for r in gate_results],
})
if agent_id and state_file.exists():
    state_file.unlink()
sys.exit(0)
