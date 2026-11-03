#!/usr/bin/env python3
"""Install the orchestrator (core + preset + overlays) into a repository.

Idempotent: a second run with the same inputs changes nothing. Files the user
edited after install are never overwritten silently; the new version lands next
to them as `<file>.orchestrator-new` (or replaces them with a `.bak` on --force).

Standard library only (Python 3.8+).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "0.0.0"
MANIFEST = ".claude/orchestrator/.manifest.json"
BLOCK_START = "<!-- vinifig-claude-orchestrator:start -->"
BLOCK_END = "<!-- vinifig-claude-orchestrator:end -->"
GI_START = "# vinifig-claude-orchestrator:start"
GI_END = "# vinifig-claude-orchestrator:end"
TEXT_EXT = {".md", ".json", ".py", ".js", ".sh", ".yaml", ".yml", ".txt", ".mjs", ""}
EXECUTABLE_DIRS = (".claude/hooks/", ".claude/orchestrator/bin/")
SKIP_NAMES = {".DS_Store", "__pycache__"}


class Layer:
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        meta = path / "preset.json"
        self.meta = json.loads(meta.read_text()) if meta.exists() else {}

    def file(self, name: str) -> Path | None:
        p = self.path / name
        return p if p.exists() else None


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_layers(preset: str, overlays: list[str]) -> list[Layer]:
    layers: list[Layer] = [Layer("core", ROOT / "core")]
    seen: set[str] = set()

    def add_preset(name: str) -> None:
        if name in seen:
            return
        p = ROOT / "presets" / name
        if not p.is_dir():
            sys.exit(f"error: unknown preset '{name}'. Available: {', '.join(list_presets())}")
        layer = Layer(f"preset:{name}", p)
        for parent in layer.meta.get("extends", []):
            add_preset(parent)
        seen.add(name)
        layers.append(layer)

    add_preset(preset)
    for ov in overlays:
        p = Path(ov).expanduser().resolve()
        if not p.is_dir() and (ROOT / ov).is_dir():
            p = (ROOT / ov).resolve()
        if not p.is_dir():
            sys.exit(f"error: overlay not found: {ov}")
        layers.append(Layer(f"overlay:{p.name}", p))
    return layers


def list_presets() -> list[str]:
    return sorted(d.name for d in (ROOT / "presets").iterdir() if (d / "preset.json").exists())


def detect_pm(target: Path) -> str:
    if (target / "pnpm-lock.yaml").exists() or (target / "pnpm-workspace.yaml").exists():
        return "pnpm"
    if (target / "yarn.lock").exists():
        return "yarn"
    if (target / "bun.lockb").exists() or (target / "bun.lock").exists():
        return "bun"
    return "npm"


def template_vars(target: Path, pm: str | None) -> dict[str, str]:
    pm = pm or detect_pm(target)
    run = {"npm": "npm run", "pnpm": "pnpm", "yarn": "yarn", "bun": "bun run"}[pm]
    run_if = {"npm": "npm run --if-present", "pnpm": "pnpm run --if-present", "yarn": "yarn run", "bun": "bun run"}[pm]
    exe = {"npm": "npx", "pnpm": "pnpm exec", "yarn": "yarn", "bun": "bunx"}[pm]
    return {"{{PM_RUN_IF}}": run_if, "{{PM}}": pm, "{{PM_RUN}}": run, "{{PM_EXEC}}": exe, "{{ORCH_VERSION}}": VERSION}


def render(data: bytes, rel: str, tvars: dict[str, str]) -> bytes:
    if Path(rel).suffix not in TEXT_EXT:
        return data
    try:
        text = data.decode()
    except UnicodeDecodeError:
        return data
    for k, v in tvars.items():
        text = text.replace(k, v)
    return text.encode()


def collect_files(layers: list[Layer]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for layer in layers:
        base = layer.path / "files"
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_dir() or any(part in SKIP_NAMES for part in p.parts):
                continue
            rel = p.relative_to(base).as_posix()
            # a layer can delete an inherited file with an empty "<name>.remove" marker
            if rel.endswith(".remove"):
                out.pop(rel[: -len(".remove")], None)
                continue
            out[rel] = p
    return out


# ---------- JSON merging ----------

def merge_layers(a, b):
    """Later layer wins for scalars; dicts merge; lists union (order kept)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            if v is None:  # a layer removes an inherited key with null
                out.pop(k, None)
            else:
                out[k] = merge_layers(a[k], v) if k in a else v
        return out
    if isinstance(a, list) and isinstance(b, list):
        return union(a, b)
    return b


def merge_into_existing(new, existing, list_mode: str):
    """Existing (user) values win for scalars; dicts merge recursively.

    list_mode "union": add new items to the user's list (settings: permissions, hooks).
    list_mode "user": keep the user's list as is (orchestrator.json: gates, teams).
    """
    if isinstance(new, dict) and isinstance(existing, dict):
        out = dict(new)
        for k, v in existing.items():
            out[k] = merge_into_existing(new[k], v, list_mode) if k in new else v
        return out
    if isinstance(new, list) and isinstance(existing, list):
        return union(existing, new) if list_mode == "union" else existing
    return existing


def union(a: list, b: list) -> list:
    out, keys = [], set()
    for item in a + b:
        key = hook_key(item)
        if key in keys:
            continue
        keys.add(key)
        out.append(item)
    return out


def hook_key(item) -> str:
    # hook groups are equal when matcher and the set of commands match
    if isinstance(item, dict) and "hooks" in item:
        cmds = sorted(h.get("command", "") for h in item.get("hooks", []))
        return json.dumps({"m": item.get("matcher", ""), "c": cmds}, sort_keys=True)
    return json.dumps(item, sort_keys=True)


def load_json(p: Path):
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except json.JSONDecodeError as e:
        sys.exit(f"error: {p} is not valid JSON ({e}); fix it before installing")


def dump_json(obj) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()


# ---------- text blocks ----------

def upsert_block(existing: str | None, body: str, start: str, end: str, header: str = "") -> str:
    block = f"{start}\n{body.strip()}\n{end}\n"
    if existing is None:
        return (header + block) if header else block
    if start in existing and end in existing:
        pre = existing.split(start, 1)[0]
        post = existing.split(end, 1)[1]
        return pre + block.rstrip("\n") + post if post.strip() else pre + block
    sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + sep + block


def layer_text(layers: list[Layer], name: str, tvars: dict[str, str]) -> str:
    parts = []
    for layer in layers:
        f = layer.file(name)
        if f:
            parts.append(render(f.read_bytes(), name, tvars).decode().strip())
    return "\n\n".join(p for p in parts if p)


# ---------- installer ----------

class Installer:
    def __init__(self, target: Path, dry_run: bool, force: bool):
        self.target = target
        self.dry = dry_run
        self.force = force
        self.report: dict[str, list[str]] = {k: [] for k in ("created", "updated", "unchanged", "conflict", "merged", "removed")}
        self.manifest = load_json(target / MANIFEST) or {"files": {}}

    def write(self, rel: str, data: bytes, managed: bool = True) -> None:
        dest = self.target / rel
        recorded = self.manifest["files"].get(rel)
        if dest.exists():
            current = dest.read_bytes()
            if current == data:
                self.report["unchanged"].append(rel)
                if managed:
                    self.manifest["files"][rel] = sha(data)
                return
            user_touched = managed and recorded is not None and sha(current) != recorded
            unmanaged = managed and recorded is None
            if (user_touched or unmanaged) and not self.force:
                self.report["conflict"].append(rel)
                if not self.dry:
                    (dest.parent / (dest.name + ".orchestrator-new")).write_bytes(data)
                return
            if (user_touched or unmanaged) and not self.dry:
                shutil.copy2(dest, dest.parent / (dest.name + ".bak"))
            self.report["updated" if managed else "merged"].append(rel)
        else:
            self.report["created" if managed else "merged"].append(rel)
        if not self.dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            if rel.startswith(EXECUTABLE_DIRS) and rel.endswith((".py", ".sh")):
                dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        if managed:
            self.manifest["files"][rel] = sha(data)

    def write_merged(self, rel: str, data: bytes) -> None:
        dest = self.target / rel
        if dest.exists() and dest.read_bytes() == data:
            self.report["unchanged"].append(rel)
            return
        self.report["merged"].append(rel)
        if not self.dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

    def remove_stale(self, keep: set[str]) -> None:
        # files installed by an earlier version but no longer shipped (and untouched by the user)
        for rel, recorded in list(self.manifest["files"].items()):
            if rel in keep:
                continue
            dest = self.target / rel
            if dest.exists() and sha(dest.read_bytes()) == recorded:
                self.report["removed"].append(rel)
                if not self.dry:
                    dest.unlink()
            self.manifest["files"].pop(rel, None)


def main() -> int:
    ap = argparse.ArgumentParser(description="Install vinifig-claude-orchestrator into a repository.")
    ap.add_argument("--preset", help="stack preset (see --list)")
    ap.add_argument("--target", default=".", help="repository root (default: current directory)")
    ap.add_argument("--overlay", action="append", default=[], help="extra layer folder (project rules, agents); repeatable")
    ap.add_argument("--pm", choices=["npm", "pnpm", "yarn", "bun"], help="node package manager (default: detected from lockfile)")
    ap.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    ap.add_argument("--force", action="store_true", help="overwrite files you edited (keeps a .bak copy)")
    ap.add_argument("--list", action="store_true", help="list presets and exit")
    args = ap.parse_args()

    if args.list:
        for name in list_presets():
            meta = json.loads((ROOT / "presets" / name / "preset.json").read_text())
            ext = f" (extends {', '.join(meta['extends'])})" if meta.get("extends") else ""
            print(f"{name:18} {meta.get('description', '')}{ext}")
        return 0
    if not args.preset:
        ap.error("--preset is required (use --list to see the options)")

    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        sys.exit(f"error: target not found: {target}")
    layers = resolve_layers(args.preset, args.overlay)
    tvars = template_vars(target, args.pm)
    inst = Installer(target, args.dry_run, args.force)

    # 1. plain files
    files = collect_files(layers)
    for rel, src in files.items():
        inst.write(rel, render(src.read_bytes(), rel, tvars))
    inst.remove_stale(set(files))

    # 2. .claude/settings.json (permissions and hooks union with what is there)
    settings = {}
    for layer in layers:
        f = layer.file("settings.json")
        if f:
            settings = merge_layers(settings, json.loads(render(f.read_bytes(), "settings.json", tvars)))
    existing = load_json(target / ".claude/settings.json")
    merged = merge_into_existing(settings, existing, "union") if existing else settings
    inst.write_merged(".claude/settings.json", dump_json(merged))

    # 3. .claude/orchestrator.json (project config; the user's values win)
    config = {}
    for layer in layers:
        f = layer.file("orchestrator.json")
        if f:
            config = merge_layers(config, json.loads(render(f.read_bytes(), "orchestrator.json", tvars)))
    config["preset"] = args.preset
    config["overlays"] = [Path(o).name for o in args.overlay]
    config["version"] = VERSION
    existing = load_json(target / ".claude/orchestrator.json")
    if existing:
        merged = merge_into_existing(config, existing, "user")
        merged["preset"], merged["overlays"], merged["version"] = args.preset, config["overlays"], VERSION
    else:
        merged = config
    inst.write_merged(".claude/orchestrator.json", dump_json(merged))

    # 4. CLAUDE.md / AGENTS.md managed blocks
    for name, src in (("CLAUDE.md", "claude-md.md"), ("AGENTS.md", "agents-md.md")):
        body = layer_text(layers, src, tvars)
        if not body:
            continue
        dest = target / name
        current = dest.read_text() if dest.exists() else None
        header = "# Project instructions\n\n" if name == "CLAUDE.md" else "# Instructions for coding agents\n\n"
        inst.write_merged(name, upsert_block(current, body, BLOCK_START, BLOCK_END, header).encode())

    # 5. .gitignore block
    lines: list[str] = []
    for layer in layers:
        f = layer.file("gitignore.txt")
        if f:
            lines += [ln for ln in f.read_text().splitlines() if ln.strip() and ln not in lines]
    if lines:
        dest = target / ".gitignore"
        current = dest.read_text() if dest.exists() else None
        inst.write_merged(".gitignore", upsert_block(current, "\n".join(lines), GI_START, GI_END).encode())

    # 6. manifest
    inst.manifest.update({"version": VERSION, "preset": args.preset, "overlays": [Path(o).name for o in args.overlay]})
    if not args.dry_run:
        (target / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
        (target / MANIFEST).write_bytes(dump_json(inst.manifest))

    # report
    r = inst.report
    mode = "dry run: " if args.dry_run else ""
    print(f"{mode}vinifig-claude-orchestrator {VERSION} · preset {args.preset} · layers {' > '.join(l.name for l in layers)}")
    print(f"  created {len(r['created'])} · updated {len(r['updated'])} · merged {len(r['merged'])} · "
          f"unchanged {len(r['unchanged'])} · removed {len(r['removed'])} · conflicts {len(r['conflict'])}")
    for key in ("created", "updated", "merged", "removed"):
        if r[key] and (args.dry_run or os.environ.get("ORCH_VERBOSE")):
            for rel in r[key]:
                print(f"  {key:8} {rel}")
    for rel in r["conflict"]:
        print(f"  conflict {rel} (you edited it; new version saved as {rel}.orchestrator-new, or rerun with --force)")
    if not args.dry_run and (r["created"] or r["updated"]):
        print("Next: open Claude Code in the repo and run /initiative-execute <what you want done>.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
