# energy-reglaments-bot

Telegram bot for OREM (wholesale electricity market) regulations.
Answers questions based on actual document versions with RAG + OpenClaw.

## Tech Stack
- **Bot:** Python 3.12, aiogram 3
- **Crawler:** Python 3.12, requests, BeautifulSoup4
- **Indexer:** Python 3.12, pymupdf4llm, openai client (embeddings via OpenRouter)
- **Vector DB:** Qdrant (text-embedding-3-large, 3072 dims)
- **Metadata DB:** PostgreSQL 16
- **LLM Agent:** OpenClaw sidecar (OpenRouter → Gemini Flash)
- **Deploy:** Docker Swarm, VPS-2 (5.35.88.34)
- **CI/CD:** GitHub Actions → GHCR → VPS-2

## Commands
- `./scripts/check.sh` — lint + typecheck (ruff + mypy)
- `./scripts/run-crawler.sh` — run crawler once (scrape + download)
- `./scripts/run-indexer.sh` — run indexer once (PDF → Qdrant)
- `./scripts/deploy.sh` — deploy stack to VPS-2 + health check
- `./scripts/logs.sh [service]` — show service logs
- `./scripts/health.sh` — check all services

## Project Structure
```
crawler/     ← scrapes np-sr.ru, downloads PDFs, updates PostgreSQL
indexer/     ← PDF → chunks → embeddings → Qdrant
bot/         ← aiogram 3 bot, Qdrant search, OpenClaw call, validation
openclaw-workspace/ ← OpenClaw sidecar config (SOUL, AGENTS, knowledge)
scripts/     ← bash scripts (check, deploy, crawler, indexer, logs)
files/       ← downloaded PDFs (not in git, Docker volume)
```

## Constraints
See `.openclaw/CONSTRAINTS.md`

## Architecture
See `.openclaw/ARCHITECTURE.md`
