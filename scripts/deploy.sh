#!/bin/bash
set -e
VPS_HOST="root@83.217.220.3"
PROJECT_DIR="/opt/energy-reglaments-bot"
echo "=== Deploying to $VPS_HOST ==="

if [ ! -f .env ]; then
  echo "ERROR: .env not found"
  echo "FIX: cp .env.example .env && fill values"
  echo "SECRETS: cat /root/.openclaw/credentials/energy-reglaments-bot.env"
  exit 1
fi

echo "--- Deploying via docker compose ---"
ssh "$VPS_HOST" "cd $PROJECT_DIR && docker compose pull && docker compose up -d"

echo "--- Waiting for services ---"
sleep 10

echo "--- Health check ---"
ssh "$VPS_HOST" "cd $PROJECT_DIR && docker compose ps"

echo "--- Recent logs ---"
ssh "$VPS_HOST" "cd $PROJECT_DIR && docker compose logs bot --tail 30"

echo "=== DEPLOY DONE ==="
