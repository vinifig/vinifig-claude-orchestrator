# Cloudflare rules for code-implement (edge workstream)

- Never run `wrangler deploy`, `pages deploy`, `secret put`, remote D1/KV/R2, Access or DNS changes. Leave the command in the report under "Pending approval". Use `wrangler dev`, `--local` and `deploy --dry-run` for checks.
- Bindings only inside adapters; type them in one `Env` interface.
- New D1 migration = new file at the end of the migrations folder; never edit an applied one.
- No Node-only APIs in Worker code unless `nodejs_compat` is on and the plan says so.
