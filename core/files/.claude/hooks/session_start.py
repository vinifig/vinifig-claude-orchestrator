#!/usr/bin/env python3
"""SessionStart: tell the session about epics that are mid-run, so resuming is one command."""
import json

from _hooklib import ROOT, orch

lines = []
for p in sorted((ROOT / ".ai/context").glob("*/state.json")):
    try:
        st = json.loads(p.read_text())
    except Exception:
        continue
    flat = [t for w in st.get("waves", []) for t in w.get("tasks", [])]
    if any(t.get("status") in ("in-progress", "pending") for t in flat):
        lines.append(f"- {orch.summary_line(st)} Resume with /epic-execute {st['epic']}.")
if lines:
    print("Orchestrator: epics in progress in this repository:\n" + "\n".join(lines))
raise SystemExit(0)
