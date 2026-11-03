#!/usr/bin/env python3
"""PreToolUse(Bash): hard rules the agents must not break, enforced instead of asked for.

Denies: staging everything (git add -A/./--all, commit -a), pushing to a protected
branch, force push without lease, --no-verify, reading secret files from the shell.
Asks: patterns listed in orchestrator.json guards.bash_ask (e.g. cloud deploys).
"""
import re
import shlex
import subprocess

from _hooklib import decide, guards, is_secret, read_input

data = read_input()
cmd = (data.get("tool_input") or {}).get("command", "")
if not cmd:
    raise SystemExit(0)

g = guards()
protected = g.get("protected_branches", ["main", "master"])
segments = [s.strip() for s in re.split(r"&&|\|\||;|\n|\|", cmd) if s.strip()]


def current_branch() -> str:
    try:
        return subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


for seg in segments:
    try:
        words = shlex.split(seg)
    except ValueError:
        words = seg.split()
    # strip env assignments and wrappers: FOO=1 git ..., command git ...
    while words and (re.match(r"^\w+=", words[0]) or words[0] in ("command", "exec", "nohup", "time")):
        words = words[1:]
    if not words:
        continue

    if words[0] == "git" and len(words) > 1:
        sub = words[1]
        rest = words[2:]
        if sub == "add" and any(w in ("-A", "--all", ".", ":/", "-u", "--update") for w in rest):
            decide("deny", "Stage files by name (git add <file> ...), never everything at once: commits stay one subject each.")
        if sub == "commit" and any(re.fullmatch(r"-[a-zA-Z]*a[a-zA-Z]*", w) for w in rest if not w.startswith("--")):
            decide("deny", "git commit -a stages every tracked change. Add the files of this subject by name, then commit.")
        if sub in ("commit", "push", "merge", "rebase") and "--no-verify" in rest:
            decide("deny", "--no-verify skips the repository's checks. Fix what the hook reports instead.")
        if sub == "push":
            if any(w in ("--force", "-f") for w in rest) or any(re.fullmatch(r"\+\S+", w) for w in rest):
                decide("deny", "Force push is blocked. Use --force-with-lease on your own feature branch if history really must change.")
            refs = [w for w in rest if not w.startswith("-")]
            targets = []
            for r in refs[1:]:
                targets.append(r.split(":")[-1].replace("refs/heads/", ""))
            if not refs[1:] and current_branch() in protected:
                targets.append(current_branch())
            if "--force-with-lease" in " ".join(rest) and any(t in protected for t in targets):
                decide("deny", f"Rewriting {', '.join(protected)} is blocked.")
            hit = [t for t in targets if t in protected or t == "HEAD" and current_branch() in protected]
            if hit:
                decide("deny", f"Push to protected branch ({', '.join(hit)}) is blocked. Push a feature branch and open a PR; a person merges.")

    if words[0] in ("cat", "less", "more", "head", "tail", "bat", "grep", "rg", "sed", "awk", "cp", "mv", "scp", "source", ".", "base64", "xxd", "strings", "open", "code"):
        for w in words[1:]:
            if not w.startswith("-") and is_secret(w):
                decide("deny", f"{w} looks like a secret file. Never read or copy secret values; use the variable name only.")

for rule in g.get("bash_deny", []):
    if re.search(rule["pattern"], cmd):
        decide("deny", rule.get("reason", f"blocked by guards.bash_deny: {rule['pattern']}"))
for rule in g.get("bash_ask", []):
    if re.search(rule["pattern"], cmd):
        decide("ask", rule.get("reason", f"needs a person's approval: {rule['pattern']}"))
raise SystemExit(0)
