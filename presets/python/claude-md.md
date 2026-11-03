### Python stack

- Environment and commands through `uv` (`uv run pytest`, `uv add <pkg>`); if the project uses pip/poetry instead, change the gates in `.claude/orchestrator.json`.
- Type hints on public functions; run the type checker the project configures (mypy or pyright) when it exists.
- No secrets in settings modules; configuration from the environment, validated at startup (pydantic-settings or the project's equivalent).
