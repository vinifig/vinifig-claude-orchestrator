#!/usr/bin/env python3
"""PreToolUse(Read|Edit|Write|MultiEdit|NotebookEdit): never open or write secret files."""
from _hooklib import decide, is_secret, read_input

data = read_input()
ti = data.get("tool_input") or {}
path = ti.get("file_path") or ti.get("notebook_path") or ti.get("path") or ""
if path and is_secret(path):
    decide("deny", f"{path} looks like a secret file (guards.secret_paths). Use the variable names from the .example file instead.")
raise SystemExit(0)
