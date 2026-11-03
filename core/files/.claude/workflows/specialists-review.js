export const meta = {
  name: 'specialists-review',
  description: 'Pilot: run the specialist reviewers of one task in parallel, each returning a schema-checked note, before plan-design',
  phases: ['Specialists'],
}

// args: { root, epic, task, title, workstream, size, specialists: ['server-arch-review', 'tests-review', ...], models: { agentName: 'opus' } }
if (!args || !args.task || !Array.isArray(args.specialists)) {
  throw new Error('args must include root, epic, task, title, workstream, size and specialists[]')
}

const outputSchema = {
  type: 'object',
  required: ['agent', 'task', 'status', 'summary', 'files', 'gates', 'risks', 'next'],
  properties: {
    agent: { type: 'string' },
    task: { type: 'string' },
    status: { enum: ['done', 'blocked', 'failed', 'needs_input'] },
    summary: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    artifacts: { type: 'array', items: { type: 'string' } },
    gates: { type: 'array', items: { type: 'object', required: ['command', 'result'], properties: { command: { type: 'string' }, result: { enum: ['pass', 'fail', 'skipped'] } } } },
    risks: { type: 'array', items: { type: 'string' } },
    next: { type: 'string' },
  },
}

const noteFile = (name) => {
  if (name.endsWith('arch-review')) return name === args.specialists[0] ? 'architecture.md' : `${name}.md`
  return { 'tests-review': 'tests.md', 'security-review': 'security.md', 'db-review': 'db.md', 'perf-review': 'perf.md' }[name] || `${name}.md`
}

phase('Specialists')
const ctx = `${args.root}/.ai/context/${args.epic}`
const notes = await parallel(args.specialists.map((name) => () =>
  agent(
    `Act as the ${name} agent: read ${args.root}/.claude/agents/${name}.md and follow it exactly.\n` +
    `Task ${args.task}: ${args.title}, workstream ${args.workstream}, size ${args.size}, repository ${args.root}.\n` +
    `Read ${ctx}/_wave_strategy.md, ${ctx}/${args.task}.md, ${args.root}/.claude/skills/workstreams/${args.workstream}.md, ` +
    `${args.root}/CLAUDE.md and ${args.root}/.claude/orchestrator/rules/${name}.md if it exists.\n` +
    `Write your note to ${ctx}/${String(args.task).toLowerCase()}/${noteFile(name)}. No code, no task board, nothing irreversible.`,
    { label: name, schema: outputSchema, model: (args.models || {})[name] },
  ),
))

return { task: args.task, notes: notes.filter(Boolean) }
