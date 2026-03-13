# energy-reglaments-bot

Telegram bot for OREM (wholesale electricity market) regulations.
Answers questions based on actual document versions with RAG + OpenClaw.

## Tech Stack
- **Bot:** Python 3.12, aiogram 3
- **Crawler:** Python 3.12, requests, BeautifulSoup4
- **Indexer:** Python 3.12, pymupdf4llm, httpx (embeddings via OpenRouter)
- **Vector DB:** Qdrant (intfloat/multilingual-e5-large, 1024 dims)
- **Metadata DB:** PostgreSQL 16
- **LLM:** OpenRouter direct (google/gemini-2.0-flash-001)
- **Deploy:** Docker Compose, vps-tw-server (83.217.220.3)
- **CI/CD:** GitHub Actions → GHCR → vps-tw-server

## Commands
- `./scripts/check.sh` — lint + typecheck (ruff + mypy)
- `./scripts/run-crawler.sh` — run crawler once (scrape + download)
- `./scripts/run-indexer.sh` — run indexer once (PDF → Qdrant)
- `./scripts/deploy.sh` — deploy via SSH to vps-tw-server + health check
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
