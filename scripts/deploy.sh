#!/bin/bash
set -e
STACK="energy-reglaments-bot"
echo "=== Deploying $STACK ==="

if [ ! -f .env ]; then
  echo "ERROR: .env not found"
  echo "FIX: cp .env.example .env && fill values"
  echo "SECRETS: cat /root/.openclaw/credentials/energy-reglaments-bot.env"
  exit 1
fi

source .env

echo "--- Deploying stack ---"
docker stack deploy -c docker-compose.swarm.yml $STACK --with-registry-auth

echo "--- Waiting for services ---"
sleep 10

echo "--- Health check ---"
./scripts/health.sh

echo "--- Recent logs ---"
./scripts/logs.sh bot 30
echo "=== DEPLOY DONE ==="
