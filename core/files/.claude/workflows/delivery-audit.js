export const meta = {
  name: 'delivery-audit',
  description: 'Pilot: audit one delivered task from independent angles, then cross-check the findings adversarially into one verdict',
  phases: ['Audit', 'Cross-check'],
}

// args: { root, epic, task, base, plan, report, labels: [], workstream }
if (!args || !args.task || !args.plan) throw new Error('args must include root, epic, task, base, plan, report, workstream')

const verdictSchema = {
  type: 'object',
  required: ['agent', 'verdict', 'score', 'rubric', 'fixes', 'summary'],
  properties: {
    agent: { type: 'string' },
    verdict: { enum: ['APPROVED', 'PARTIAL', 'REJECTED'] },
    score: { type: 'number' },
    summary: { type: 'string' },
    rubric: { type: 'array', items: { type: 'object', required: ['criterion', 'weight', 'score', 'evidence'], properties: { criterion: { type: 'string' }, weight: { type: 'number' }, score: { type: 'number' }, evidence: { type: 'string' } } } },
    fixes: { type: 'array', items: { type: 'object', required: ['file', 'change'], properties: { file: { type: 'string' }, change: { type: 'string' }, owner: { type: 'string' } } } },
  },
}

const common = `Repository ${args.root}. Task ${args.task}, workstream ${args.workstream}. Plan ${args.plan}. ` +
  `Execution report ${args.report}. Diff: git diff ${args.base}...HEAD. Rubric: ${args.root}/.claude/orchestrator/rubrics/plan-verify.md. Read-only: change no file.`

const angles = [
  ['plan-verify', 'Audit the delivery against the plan with the rubric; run the workstream gates yourself.'],
  ['tests-review', 'Review mode: judge whether the new tests would fail if the code were wrong. Score only rubric criteria 2 and 6.'],
]
if ((args.labels || []).some((l) => ['external-input', 'auth', 'db'].includes(l))) {
  angles.push(['security-review', 'Review mode on the diff. Score only rubric criterion 7.'])
}

phase('Audit')
const findings = await parallel(angles.map(([name, focus]) => () =>
  agent(`Act as the ${name} agent (${args.root}/.claude/agents/${name}.md). ${focus}\n${common}`, { label: name, schema: verdictSchema }),
))

phase('Cross-check')
const merged = await agent(
  `You are a skeptical referee. Below are independent audits of task ${args.task}. For every fix and every low score, ` +
  `check the evidence in the code yourself and drop what does not hold; for every high score, look for the calibration traps ` +
  `in the rubric. Return one verdict with agent "plan-verify".\n${common}\n\nAudits:\n${JSON.stringify(findings.filter(Boolean), null, 2)}`,
  { label: 'referee', schema: verdictSchema },
)

return merged
