---
name: ui-validate
description: Real visual validation — opens the screen, story or page in a real browser or device at desktop, tablet and phone sizes, light and dark, checks the acceptance criteria and the project's design rules, and saves screenshots as evidence. Use before saying any visible change is done (screens, components, pages, notifications).
argument-hint: "<what to validate and the acceptance criteria>"
---

# Visual validation

Validate: $ARGUMENTS

"Done" for visual work only counts with real screenshots. A DOM test (jsdom, widget test) does not replace them.

Read `.claude/orchestrator/rules/ui-validate.md` first when it exists: it holds this stack's commands (how to start the app, the story tool, the device list). The steps below are the contract.

## 1. Start what will be seen

Use the commands in the stack rules (dev server, story tool, simulator). Run servers in the background and wait for the port to answer before opening.

## 2. Capture

Minimum matrix per changed screen or story:

| Range | Size |
|---|---|
| desktop | 1440 × 900 |
| tablet | 768 × 1024 (touch) |
| phone | Pixel 7 (Chromium) and iPhone 14 (WebKit), or the stack's simulators |

× light and dark theme. Interactions (open a drawer, switch tab, submit with an error): do the step, then capture each state.

For web stacks, a helper script kept outside the repository (scratchpad), paths passed as arguments, run from the folder whose `package.json` has `@playwright/test`:

```js
// node <scratchpad>/shots.mjs <url> <out-dir> <name>
import { createRequire } from 'node:module';
const { chromium, webkit, devices } = createRequire(`${process.cwd()}/package.json`)('@playwright/test');
const [url, out, name] = process.argv.slice(2);
const cases = [
  ['desktop', chromium, { viewport: { width: 1440, height: 900 } }],
  ['tablet', chromium, { viewport: { width: 768, height: 1024 }, hasTouch: true }],
  ['phone', chromium, devices['Pixel 7']],
  ['iphone', webkit, devices['iPhone 14']],
];
for (const [range, type, opts] of cases) {
  const browser = await type.launch(process.env.PW_CHROMIUM && type === chromium ? { executablePath: process.env.PW_CHROMIUM } : {});
  for (const scheme of ['light', 'dark']) {
    const page = await browser.newPage({ ...opts, colorScheme: scheme });
    const errors = [];
    page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.screenshot({ path: `${out}/${name}-${range}-${scheme}.png`, fullPage: true });
    if (errors.length) console.log(`${range}/${scheme} console errors:`, errors);
    await page.close();
  }
  await browser.close();
}
```

## 3. Check

For each screenshot:
- Each acceptance criterion: visible or not.
- The project's design rules (`CLAUDE.md`, `.claude/orchestrator/rules/ui-validate.md`).
- 400 px wide without horizontal scroll; wide tables scroll inside their block; visible keyboard focus.
- Compared with the source artifact (story, design, earlier screenshots).
- No console errors.

## 4. Keep the evidence

- Folder: `.claude/orchestrator.json` → `ui.screenshots_dir` (default `docs/evidence/<subject>/`), or what the stack rules say.
- Videos stay out of git.
- Show the main screenshots in the conversation and list the files in the PR.

## 5. Result

End with the human summary and the JSON block (`agent-output` schema; `gates` holds one entry per checked criterion):

```
VISUAL VALIDATION: PASSED | FAILED
<screen/story> · <ranges> · <themes> · <browsers>
- [x] <criterion> — <screenshot>
- [ ] <criterion> — <what is wrong, with screenshot>
Screenshots: <folder>
```

```json
{"agent": "ui-validate", "task": "<id>", "status": "done", "summary": "...", "files": [], "artifacts": ["<screenshots>"],
 "gates": [{"command": "criterion: <text>", "result": "pass"}], "risks": [], "next": "audit"}
```

Failed: return the exact findings to the orchestrator for `code-implement`, then validate again.
