#!/usr/bin/env python3
"""SubagentStart: remember when each agent started (for time per agent) and log it."""
import json
import time

from _hooklib import ROOT, orch, read_input

data = read_input()
agent_id = data.get("agent_id") or ""
cur = orch.current()
if agent_id:
    d = ROOT / ".ai/context/_agents"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{agent_id}.json").write_text(json.dumps({"start": time.time(), "agent": data.get("agent_type", ""), "blocks": 0,
                                                     "epic": cur.get("epic", ""), "task": cur.get("task", "")}))
orch.event(cur.get("epic"), "agent_started", {"agent": data.get("agent_type", ""), "agent_id": agent_id, "task": cur.get("task", "")})
raise SystemExit(0)
