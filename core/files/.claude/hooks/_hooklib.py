"""Shared helpers for the orchestrator hooks (standard library only)."""
from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT / ".claude/orchestrator/bin"))

import orch  # noqa: E402

DEFAULT_SECRETS = [".env", ".env.*", "*.env", ".dev.vars", ".dev.vars.*", "*.generated", "*.pem", "*.p12", "*.key",
                   "id_rsa*", "id_ed25519*", "*.keystore", "*.jks", "credentials.json", "service-account*.json",
                   ".npmrc", ".netrc"]
SECRET_ALLOW = ["*.example", "*.example.*", "*.sample", "*.template", "*.dist"]


def read_input() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def config() -> dict:
    try:
        return orch.config()
    except Exception:
        return {}


def guards() -> dict:
    return config().get("guards", {})


def secret_patterns() -> list[str]:
    g = guards()
    return list(dict.fromkeys(DEFAULT_SECRETS + g.get("secret_paths", [])))


def is_secret(path: str) -> bool:
    name = Path(path).name
    rel = path
    try:
        rel = str(Path(path).resolve().relative_to(ROOT))
    except Exception:
        pass
    if any(fnmatch.fnmatch(name, a) for a in SECRET_ALLOW + guards().get("secret_allow", [])):
        return False
    return any(fnmatch.fnmatch(name, p) or fnmatch.fnmatch(rel, p) for p in secret_patterns())


def decide(decision: str, reason: str) -> None:
    """PreToolUse structured decision: allow | deny | ask."""
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": decision,
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)
