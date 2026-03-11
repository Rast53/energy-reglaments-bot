# Progress: TASK-4 — CI/CD + Deploy

## Status: SUCCESS

## Steps
- [x] Step 1: .github/workflows/deploy.yml — полный build+deploy pipeline
- [x] Step 2: docker-compose.swarm.yml — healthcheck, bind mounts, crawler replicas=0
- [x] Step 3: /health endpoint в bot (aiohttp :8080)
- [x] Step 4: scripts/deploy.sh обновлён
- [x] Step 5: scripts/init-vps.sh создан и выполнен (VPS-2 инициализирован)
- [x] Step 6: OPENCLAW_API_KEY сгенерирован и установлен в GitHub Secrets
- [x] Step 7: ruff — All checks passed
- [x] Step 8: VPS-2 /opt/energy-reglaments-bot/ создан, openclaw-workspace скопирован

## Notes
- VPS-2 инициализирован: /opt/energy-reglaments-bot/ готов
- OPENCLAW_API_KEY: установлен в GitHub Secrets
- Crawler replicas=0 — запускается вручную через docker service scale
