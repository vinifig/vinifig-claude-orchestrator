# Node web stack: how to show what changed

| What | How |
|---|---|
| App (dev) | `{{PM_RUN}} dev` (read the port from the output) |
| App (built) | `{{PM_RUN}} build && {{PM_RUN}} preview` |
| Stories | `{{PM_RUN}} storybook` when the project has Storybook |

Use the Playwright helper in the `ui-validate` skill from the package that depends on `@playwright/test`. If its Chromium is not installed, point `PW_CHROMIUM` to an installed Chrome. Safari: WebKit from Playwright; on a Mac, real Safari when the change is layout-sensitive.
