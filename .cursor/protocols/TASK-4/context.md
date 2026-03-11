# Context: TASK-4 — CI/CD + Deploy

## Project
energy-reglaments-bot — Telegram bot для регламентов ОРЭМ.

## Текущее состояние
Все компоненты написаны и смержены в main:
- crawler/ — парсинг np-sr.ru, скачивание PDF
- indexer/ — PDF → Qdrant embeddings
- bot/ — aiogram 3, RAG pipeline
- openclaw-workspace/ — OpenClaw sidecar конфиг
- docker-compose.yml (dev), docker-compose.swarm.yml (prod)
- .github/workflows/deploy.yml — черновик CI/CD

## Что нужно сделать

### 1. Исправить и дополнить .github/workflows/deploy.yml
Текущий workflow строит только bot и crawler images. Нужно:
- job `build`: build + push ghcr.io/rast53/energy-reglaments-bot/bot и /crawler
- job `deploy`: SSH на VPS-2, записать .env, docker stack deploy
- Все envs: BOT_TOKEN, OPENROUTER_API_KEY, OPENCLAW_API_KEY, DATABASE_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, ADMIN_IDS, IMAGE_TAG

### 2. Создать scripts/init-vps.sh
Скрипт первоначальной настройки VPS-2:
- mkdir -p /opt/energy-reglaments-bot/openclaw-workspace/workspace
- mkdir -p /opt/energy-reglaments-bot/files
- rsync или scp openclaw-workspace/ на VPS
- chmod 777 на /opt/energy-reglaments-bot/openclaw-workspace

### 3. Исправить docker-compose.swarm.yml
- OpenClaw: volume bind mount → /opt/energy-reglaments-bot/openclaw-workspace/workspace:/data/workspace
- Crawler: cron schedule через labels или отдельный cron-like сервис
- Все сервисы в одной overlay сети energy-net

### 4. Создать scripts/setup-openclaw.sh
Генерирует OPENCLAW_API_KEY (random hex), прописывает его в openclaw config.
Аналогично 1c-docs-bot: через Node.js запись в /data/.openclaw/openclaw.json

### 5. Обновить scripts/deploy.sh
Рабочий deploy.sh для VPS-2:
- source .env
- docker login ghcr.io
- docker stack deploy -c docker-compose.swarm.yml energy-reglaments-bot
- sleep 10 && ./scripts/health.sh

## VPS-2 параметры
- Host: 5.35.88.34 (публичный, для CI)
- Tailscale: 100.102.159.115
- User: root
- Docker Swarm: уже настроен (там живёт 1c-docs-bot)
- GHCR: ghcr.io/rast53

## GitHub Secrets (уже установлены)
VPS2_HOST=5.35.88.34, VPS2_USER=root, VPS2_SSH_KEY, BOT_TOKEN,
OPENROUTER_API_KEY, OPENCLAW_API_KEY (пустой — нужно сгенерировать),
DATABASE_URL, POSTGRES_USER=energy, POSTGRES_PASSWORD=energy_secret,
POSTGRES_DB=energy, ADMIN_IDS=125525685, GHCR_TOKEN

## Важно
- OPENCLAW_API_KEY пока пустой — его нужно сгенерировать и вписать в GitHub Secrets и в openclaw конфиг
- Crawler должен запускаться по cron (02:00 UTC ежедневно). В Swarm это через healthcheck + restart или отдельный сервис
- После деплоя всегда проверять: docker service ls | grep energy
