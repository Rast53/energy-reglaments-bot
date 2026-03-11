# Constraints

## Hard Rules (never violate)

- **No secrets in code.** All secrets via environment variables. No hardcoded tokens, URLs with credentials, API keys.
- **No git-tracked secrets.** `.env` is in `.gitignore`. Only `.env.example` with empty values.
- **No direct DB writes from bot.** Bot is read-only: Qdrant search + OpenClaw call. Only crawler and indexer write to DB.
- **No scraping without verify=False.** np-sr.ru has broken SSL cert. Always use `verify=False` + suppress warnings.
- **No deleting Qdrant points without explicit version migration.** Archive by updating `status` field, never delete.
- **No f-strings for SQL.** Use parameterized queries only. No SQL injection vectors.
- **No blocking calls in bot handlers.** All I/O must be async (aiohttp, asyncpg, qdrant-client async).

## Architecture Rules

- **Sinks only.** Components terminate after completing work. No cross-service HTTP calls except bot→openclaw.
- **Idempotent crawler.** SHA256 check before download. Running twice must produce same result.
- **Chunk metadata immutable.** Once indexed, never update chunk payload — only add new version chunks.
- **Status logic in crawler only.** Bot and indexer never compute current/future/archive — read from DB.

## Code Style

- Python 3.12, type hints everywhere
- ruff for linting (line-length = 100)
- mypy for type checking
- No `print()` — use `logging` module
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
