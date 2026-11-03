#!/usr/bin/env bash
# End-to-end checks for the installer, orch.py and the hooks. Standard tools only:
# bash, git, python3. Run from anywhere: bash tests/test_install.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL="$HERE/installer/install.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok()   { PASS=$((PASS + 1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf '  FAIL %s\n' "$1"; [ -n "${2:-}" ] && printf '       %s\n' "$2"; }
check(){ local name="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$name"; else bad "$name" "$*"; fi; }
new_repo() {  # new_repo <dir> [lockfile]
  rm -rf "$1"; mkdir -p "$1"; git -C "$1" init -q -b main
  git -C "$1" config user.email t@t; git -C "$1" config user.name t
  [ -n "${2:-}" ] && touch "$1/$2"
  printf '# Repo\n\nOwn rules.\n' > "$1/CLAUDE.md"
  printf 'node_modules/\n' > "$1/.gitignore"
}
summary() { python3 "$INSTALL" "$@" | sed -n 2p; }

echo "== installer, per preset"
for preset in $(python3 "$INSTALL" --list | awk '{print $1}'); do
  R="$TMP/$preset"; new_repo "$R" "$([ "$preset" = node ] || [ "$preset" = node-cloudflare ] && echo pnpm-lock.yaml)"
  out=$(summary --preset "$preset" --target "$R")
  case "$out" in *"conflicts 0"*) ok "$preset: fresh install ($out)";; *) bad "$preset: fresh install" "$out";; esac
  check "$preset: orchestrator.json valid, preset recorded" python3 -c "import json,sys;d=json.load(open('$R/.claude/orchestrator.json'));sys.exit(d['preset']!='$preset')"
  check "$preset: settings.json has the hooks" python3 -c "import json,sys;d=json.load(open('$R/.claude/settings.json'));sys.exit('SubagentStop' not in d['hooks'])"
  check "$preset: CLAUDE.md keeps own text + block" bash -c "grep -q 'Own rules.' '$R/CLAUDE.md' && grep -q 'vinifig-claude-orchestrator:start' '$R/CLAUDE.md'"
  check "$preset: .gitignore keeps own lines + block" bash -c "grep -q node_modules '$R/.gitignore' && grep -q '.ai/context/' '$R/.gitignore'"
  check "$preset: hooks executable" test -x "$R/.claude/hooks/guard_bash.py"
  check "$preset: no unrendered template vars" bash -c "! grep -rl '{{PM' '$R/.claude' '$R/CLAUDE.md'"
  out=$(summary --preset "$preset" --target "$R")
  case "$out" in *"created 0 · updated 0 · merged 0"*"conflicts 0"*) ok "$preset: rerun changes nothing";; *) bad "$preset: rerun changes nothing" "$out";; esac
done

echo "== installer, edits, merges and layers"
R="$TMP/node"
echo "my edit" >> "$R/.claude/agents/plan-design.md"
out=$(summary --preset node --target "$R")
case "$out" in *"conflicts 1"*) ok "user edit kept as conflict";; *) bad "user edit kept as conflict" "$out";; esac
check "user edit untouched" grep -q "my edit" "$R/.claude/agents/plan-design.md"
check "new version saved next to it" test -f "$R/.claude/agents/plan-design.md.orchestrator-new"
python3 "$INSTALL" --preset node --target "$R" --force >/dev/null
check "--force replaces and keeps .bak" bash -c "! grep -q 'my edit' '$R/.claude/agents/plan-design.md' && grep -q 'my edit' '$R/.claude/agents/plan-design.md.bak'"
check "pnpm detected from lockfile" grep -q "pnpm run --if-present test" "$R/.claude/orchestrator.json"

R="$TMP/merge"; new_repo "$R"
mkdir -p "$R/.claude"
cat > "$R/.claude/settings.json" <<'J'
{"permissions": {"allow": ["Bash(make:*)"]}, "model": "opus"}
J
cat > "$R/.claude/orchestrator.json" <<'J'
{"language": "Deutsch", "gates": {"default": ["make test"]}}
J
python3 "$INSTALL" --preset node --target "$R" --pm npm >/dev/null
check "settings: user permission kept, core ones added" python3 -c "
import json,sys;d=json.load(open('$R/.claude/settings.json'))
sys.exit(not('Bash(make:*)' in d['permissions']['allow'] and d['model']=='opus' and any('orch.py' in x for x in d['permissions']['allow'])))"
check "orchestrator.json: user values win" python3 -c "
import json,sys;d=json.load(open('$R/.claude/orchestrator.json'))
sys.exit(not(d['language']=='Deutsch' and d['gates']['default']==['make test'] and 'backend' in d['workstreams']))"
check "npm templating" grep -q "npm run --if-present lint" "$R/.claude/orchestrator.json"

check "node-cloudflare: edge workstream + inherited node ones" python3 -c "
import json,sys;d=json.load(open('$TMP/node-cloudflare/.claude/orchestrator.json'))
sys.exit(not({'edge','backend','frontend'} <= set(d['workstreams'])))"

OV="$TMP/overlay"; mkdir -p "$OV/files/.claude/agents" "$OV/files/.claude/skills/workstreams"
touch "$OV/files/.claude/agents/backend-arch-review.md.remove"
printf -- '---\nname: api-arch-review\n---\nx\n' > "$OV/files/.claude/agents/api-arch-review.md"
cat > "$OV/orchestrator.json" <<'J'
{"language": "Português", "workstreams": {"backend": null, "api": {"paths": ["api"], "arch_agent": "api-arch-review", "gates": ["true"]}}}
J
printf '### Overlay note\n' > "$OV/claude-md.md"
R="$TMP/ov"; new_repo "$R" pnpm-lock.yaml
python3 "$INSTALL" --preset node --overlay "$OV" --target "$R" >/dev/null
check "overlay: .remove drops inherited file" test ! -e "$R/.claude/agents/backend-arch-review.md"
check "overlay: adds its file" test -f "$R/.claude/agents/api-arch-review.md"
check "overlay: null drops inherited workstream" python3 -c "
import json,sys;d=json.load(open('$R/.claude/orchestrator.json'));w=d['workstreams']
sys.exit(not('backend' not in w and 'api' in w and d['language']=='Português' and d['overlays']==['overlay']))"
check "overlay: CLAUDE.md block has overlay text" grep -q "Overlay note" "$R/CLAUDE.md"
out=$(summary --preset node --overlay "$OV" --target "$R")
case "$out" in *"created 0 · updated 0 · merged 0"*) ok "overlay: rerun changes nothing";; *) bad "overlay: rerun changes nothing" "$out";; esac
python3 "$INSTALL" --preset node --target "$R" >/dev/null
check "dropping the overlay removes its untouched files" test ! -e "$R/.claude/agents/api-arch-review.md"
check "dry run writes nothing" bash -c "R2='$TMP/dry'; mkdir -p \$R2; python3 '$INSTALL' --preset go --target \$R2 --dry-run >/dev/null; test ! -e \$R2/.claude"

echo "== orch.py"
R="$TMP/node-cloudflare"; ORCH="$R/.claude/orchestrator/bin/orch.py"
export CLAUDE_PROJECT_DIR="$R"
mkdir -p "$R/.ai/board"
cat > "$R/.ai/board/EP-1.yaml" <<'Y'
epic:
  id: EP-1
  title: "Demo epic"   # comment
tasks:
  - id: T1
    title: First
    workstream: backend
    labels: [db, ui]
  - id: T2
    title: Second
    blocked_by: [T1]
    priority: high
  - id: T3
    title: Third
    blocked_by: [T1]
    notes: |
      line one
      line two
  - id: T4
    title: Done already
    status: done
Y
check "YAML subset: flow list, comment, block scalar" python3 -c "
import json,subprocess,sys
d=json.loads(subprocess.check_output(['python3','$ORCH','board','show','EP-1']))
t={x['id']:x for x in d['tasks']}
sys.exit(not(d['epic']['title']=='Demo epic' and t['T1']['labels']==['db','ui'] and 'line two' in t['T3']['notes']))"
check "YAML subset parser without PyYAML" python3 -c "
import sys;sys.modules['yaml']=None;sys.argv=['orch'];sys.path.insert(0,'$R/.claude/orchestrator/bin');import orch
d=orch.load_board('EP-1');t={x['id']:x for x in d['tasks']}
sys.exit(not(d['epic']['title']=='Demo epic' and t['T1']['labels']==['db','ui'] and t['T3']['notes'].startswith('line one\\nline two') and t['T2']['blocked_by']==['T1']))"
check "waves from blocked_by (priority first, done skipped)" bash -c "[ \"\$(python3 '$ORCH' waves EP-1)\" = '[[\"T1\"], [\"T2\", \"T3\"]]' ]"
printf '[{"id":"A","blocked_by":["B"]},{"id":"B","blocked_by":["A"]}]' > "$TMP/cycle.json"
python3 "$ORCH" waves "$TMP/cycle.json" >/dev/null 2>&1; rc=$?
[ "$rc" = 3 ] && ok "cycle detected (exit 3)" || bad "cycle detected (exit 3)" "exit $rc"
check "state init" python3 "$ORCH" state init EP-1 --board EP-1 --mode sequential-teams --base main
check "state init refuses to overwrite" bash -c "! python3 '$ORCH' state init EP-1 --board EP-1"
check "state task update + stacked base" bash -c "python3 '$ORCH' state task EP-1 T1 status=in-progress branch=feat/t1 files+=a.ts,b.ts rounds+=1 >/dev/null && python3 '$ORCH' state show EP-1 --json | python3 -c \"
import json,sys;s=json.load(sys.stdin);t=[x for w in s['waves'] for x in w['tasks']]
sys.exit(not(t[0]['files']==['a.ts','b.ts'] and t[0]['rounds']==1 and t[1]['base']=='feat/t1'))\""
check "state task rejects bad status" bash -c "! python3 '$ORCH' state task EP-1 T1 status=nope"
check "render writes _wave_strategy.md" bash -c "python3 '$ORCH' state render EP-1 >/dev/null && grep -q 'feat/t1' '$R/.ai/context/ep-1/_wave_strategy.md'"
check "resume points at the in-progress task" bash -c "python3 '$ORCH' state resume EP-1 | grep -q '\"task\": \"T1\"'"
python3 "$ORCH" state task EP-1 T2 files=b.ts >/dev/null; python3 "$ORCH" state task EP-1 T3 files=c.ts >/dev/null
check "overlap keeps tasks sharing files apart" bash -c "python3 '$ORCH' overlap EP-1 T1 T2 T3 | python3 -c \"
import json,sys;g=json.load(sys.stdin)['groups'];sys.exit(not(g==[['T1','T3'],['T2']]))\""
printf 'text\n```json\n{"agent":"code-implement","task":"T1","status":"done","summary":"s","files":[],"gates":[],"risks":[],"next":"n"}\n```\n' > "$TMP/good.txt"
printf 'text\n```json\n{"agent":"x","status":"maybe"}\n```\n' > "$TMP/bad.txt"
check "output-check accepts a valid block" python3 "$ORCH" output-check --file "$TMP/good.txt"
check "output-check rejects an invalid block" bash -c "! python3 '$ORCH' output-check --file '$TMP/bad.txt'"
check "gates per workstream (edge)" bash -c "python3 '$ORCH' gates --workstream edge | grep -q 'wrangler deploy --dry-run'"
check "team M with labels" bash -c "python3 '$ORCH' team M --labels db,ui | python3 -c \"
import json,sys;d=json.load(sys.stdin);sys.exit(not({'arch','tests-review','db-review','ui-validate'}<=set(d['specialists'])))\""
cat >> "$R/.ai/context/ep-1/events.jsonl" <<'E'
{"type":"agent_stopped","agent":"plan-design","task":"T1","model":"m","usage":{"input_tokens":1000,"output_tokens":500},"seconds":120}
{"type":"agent_stopped","agent":"code-implement","task":"T1","model":"m","usage":{"input_tokens":2000,"cache_read_input_tokens":3000},"seconds":60}
E
check "cost sums tokens and time per task" bash -c "python3 '$ORCH' cost EP-1 --json | python3 -c \"
import json,sys;d=json.load(sys.stdin);t=d['per_task']['T1'];sys.exit(not(t['tokens']==6500 and t['seconds']==180 and t['rounds']==1 and d['total']['agents']==2))\""

echo "== hooks"
H="$R/.claude/hooks"
hook() {  # hook <script> <json> -> prints decision (allow when silent)
  local out; out=$(cd "$R" && printf '%s' "$2" | python3 "$H/$1" 2>/dev/null)
  python3 -c "import json,sys;s=sys.argv[1];print(json.loads(s)['hookSpecificOutput']['permissionDecision'] if s.strip() else 'allow')" "$out"
}
bash_is() { local got; got=$(hook guard_bash.py "{\"tool_input\":{\"command\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$2")}}"); [ "$got" = "$1" ] && ok "bash $1: $2" || bad "bash $1: $2" "got $got"; }
git -C "$R" checkout -q -b feat/x 2>/dev/null
bash_is deny "git add -A"
bash_is deny "git add ."
bash_is deny "git commit -am wip"
bash_is deny "git push origin main"
bash_is deny "git push --force origin feat/x"
bash_is deny "git commit --no-verify -m x"
bash_is deny "cat .env"
bash_is deny "cd app && cat .dev.vars"
bash_is ask  "pnpm exec wrangler deploy"
bash_is ask  "npx wrangler d1 execute DB --remote --command 'select 1'"
bash_is ask  "wrangler secret put TOKEN"
bash_is allow "pnpm exec wrangler deploy --dry-run --outdir .wrangler/dry-run"
bash_is allow "wrangler d1 execute DB --local --command 'select 1'"
bash_is allow "git add src/a.ts && git commit -m 'feat: a'"
bash_is allow "git push -u origin feat/x"
bash_is allow "cat .env.example"
got=$(hook guard_files.py '{"tool_input":{"file_path":"'"$R"'/.env.local"}}'); [ "$got" = deny ] && ok "Read .env.local denied" || bad "Read .env.local denied" "got $got"
got=$(hook guard_files.py '{"tool_input":{"file_path":"'"$R"'/src/a.ts"}}'); [ "$got" = allow ] && ok "Read src/a.ts allowed" || bad "Read src/a.ts allowed" "got $got"

stop() { (cd "$R" && printf '%s' "$1" | python3 "$H/subagent_stop.py" >/dev/null 2>&1); echo $?; }
python3 "$ORCH" current set EP-1 T1 --workstream nope >/dev/null
rc=$(stop '{"agent_type":"plan-verify","agent_id":"a1","last_assistant_message":"no block here"}')
[ "$rc" = 2 ] && ok "subagent_stop blocks a reply without the JSON block (exit 2)" || bad "subagent_stop blocks missing block" "exit $rc"
msg=$(python3 -c 'import json;print(json.dumps({"agent_type":"tests-review","agent_id":"a2","last_assistant_message":open("'"$TMP/good.txt"'").read()}))')
rc=$(stop "$msg"); [ "$rc" = 0 ] && ok "subagent_stop accepts a valid block" || bad "subagent_stop accepts a valid block" "exit $rc"
rc=$(stop '{"agent_type":"Explore","agent_id":"a3","last_assistant_message":"free text"}')
[ "$rc" = 0 ] && ok "subagent_stop ignores agents outside structured_output" || bad "subagent_stop ignores other agents" "exit $rc"
check "subagent_stop logged telemetry" grep -q '"agent": "tests-review"' "$R/.ai/context/ep-1/events.jsonl"
python3 - "$R" <<'P'
import json,sys
p=sys.argv[1]+"/.claude/orchestrator.json";d=json.load(open(p));d["workstreams"]["failing"]={"paths":[],"gates":["false"]};json.dump(d,open(p,"w"))
P
python3 "$ORCH" current set EP-1 T1 --workstream failing >/dev/null
msg=$(python3 -c 'import json;print(json.dumps({"agent_type":"code-implement","agent_id":"a4","last_assistant_message":open("'"$TMP/good.txt"'").read()}))')
rc=$(stop "$msg"); [ "$rc" = 2 ] && ok "subagent_stop sends a red gate back to code-implement" || bad "red gate goes back" "exit $rc"
check "session_start lists the epic in progress" bash -c "cd '$R' && python3 '$H/session_start.py' | grep -q 'EP-1'"
unset CLAUDE_PROJECT_DIR

echo "== bin wrappers"
check "install.sh --list" bash "$HERE/install.sh" --list
if command -v node >/dev/null; then check "npx bin --list" node "$HERE/bin/vinifig-claude-orchestrator.js" --list; fi

echo
echo "passed $PASS · failed $FAIL"
[ "$FAIL" = 0 ]
