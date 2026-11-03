# Cloudflare additions for security-review

- Access: JWT verified (algorithm, `aud`, issuer, expiry) with JWKS from the team domain; service tokens limited to their routes.
- `workers_dev` and preview URLs disabled for anything behind Access; no route that skips the Worker in front of assets when auth is required (`run_worker_first`).
- Turnstile or rate limits (KV/Durable Object/Rate Limiting binding) on public forms and APIs.
- Secrets only via `wrangler secret`; none in `wrangler.toml`, `vars`, tests or logs.
- Every remote operation is listed under "Pending approval" with the exact command.
