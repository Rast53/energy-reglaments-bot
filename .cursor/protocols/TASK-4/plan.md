# Plan: TASK-4 — CI/CD + Deploy

## Steps

### Step 1: Обновить .github/workflows/deploy.yml
Полный рабочий workflow:
- trigger: push to main
- job build: docker/build-push-action для bot и crawler → ghcr.io, тег sha + latest
- job deploy: appleboy/ssh-action с ВСЕМИ envs перечисленными в envs: и env:
  script: mkdir -p /opt/energy-reglaments-bot, записать .env (все переменные!),
  docker login ghcr.io, docker stack deploy, sleep 10, docker service ls

### Step 2: Исправить docker-compose.swarm.yml
- volumes: openclaw использует bind /opt/energy-reglaments-bot/openclaw-workspace/workspace:/data/workspace
- crawler: добавить deploy.restart_policy + labels для cron-подобного поведения
- Добавить healthcheck для bot (curl /health или просто alive)
- Убедиться что все сервисы в сети energy-net

### Step 3: Добавить /health endpoint в bot
В bot/main.py добавить простой HTTP health endpoint на порту 8080:
```python
from aiohttp import web
async def health(request): return web.Response(text="ok")
```
Запускать параллельно с aiogram polling.

### Step 4: Обновить scripts/deploy.sh
Рабочий скрипт для ручного деплоя с VPS-1:
```bash
ssh root@100.102.159.115 "cd /opt/energy-reglaments-bot && docker stack deploy ..."
```

### Step 5: Создать scripts/init-vps.sh
```bash
#!/bin/bash
# Первоначальная настройка VPS-2
VPS=root@5.35.88.34
ssh $VPS "mkdir -p /opt/energy-reglaments-bot/files"
scp -r openclaw-workspace/ $VPS:/opt/energy-reglaments-bot/
scp docker-compose.swarm.yml $VPS:/opt/energy-reglaments-bot/
echo "VPS initialized"
```

### Step 6: Сгенерировать OPENCLAW_API_KEY и обновить GitHub Secret
```bash
OPENCLAW_API_KEY=$(openssl rand -hex 32)
gh secret set OPENCLAW_API_KEY --body "$OPENCLAW_API_KEY"
```
Также прописать в openclaw-workspace/workspace/openclaw-config.json (если нужен статичный конфиг).

### Step 7: Обновить scripts/check.sh
Добавить проверку что Dockerfile существует для bot и crawler.

### Step 8: Commit + push + проверить что CI запускается
git add -A && git commit -m "feat: CI/CD deploy pipeline (#4)" && git push
Проверить: gh run list --repo Rast53/energy-reglaments-bot

## Acceptance Criteria
- [ ] Push в main → GitHub Actions запускается
- [ ] Images собираются и пушатся в ghcr.io
- [ ] Deploy job завершается успешно (или с ошибкой из-за пустого VPS — допустимо)
- [ ] scripts/init-vps.sh создан и исполняемый
- [ ] ruff check не ломается (только bash скрипты, не Python)
