#!/usr/bin/env bash
# Install vinifig-claude-orchestrator into the current repository (or --target DIR).
#
#   From a clone:   bash /path/to/vinifig-claude-orchestrator/install.sh --preset node
#   Without clone:  bash <(gh api repos/vinifig/vinifig-claude-orchestrator/contents/install.sh -H 'Accept: application/vnd.github.raw') --preset node
#                   (the repo is private: the script clones it with your git credentials)
#
# Every argument goes to installer/install.py (--preset, --overlay, --pm, --target, --dry-run, --force, --list).
set -euo pipefail

command -v python3 >/dev/null || { echo "error: python3 (3.8+) is required" >&2; exit 1; }

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/installer/install.py" ]; then
  exec python3 "$SELF_DIR/installer/install.py" "$@"
fi

REPO="${ORCH_REPO:-https://github.com/vinifig/vinifig-claude-orchestrator.git}"
REF="${ORCH_REF:-main}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone --quiet --depth 1 --branch "$REF" "$REPO" "$TMP/orch"
python3 "$TMP/orch/installer/install.py" "$@"
