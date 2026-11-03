### Cloudflare

- **No Cloudflare change without the approver's written yes in the conversation**: deploys (Workers, Pages), secrets, remote D1/KV/R2, Access, routes, DNS. Agents leave the exact command in the report and the PR under "Pending approval"; the main session runs it after the yes. Hooks and permissions ask before any of these run.
- Local work uses `wrangler dev`, `--local` D1 and `wrangler deploy --dry-run`.
- Never read or copy `.dev.vars*` or generated credentials; `wrangler.toml` values that are secrets go through `wrangler secret`, never into the file.
- Keep `workers_dev = false` and preview URLs off for anything behind Access (they bypass it).
