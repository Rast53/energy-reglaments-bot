#!/bin/bash
# Первоначальная настройка VPS-2 для energy-reglaments-bot
set -e

VPS="${1:-root@5.35.88.34}"
echo "=== Initializing VPS: $VPS ==="

echo "--- Creating directories ---"
ssh "$VPS" "mkdir -p /opt/energy-reglaments-bot/files && \
  mkdir -p /opt/energy-reglaments-bot/openclaw-workspace/workspace && \
  chmod 777 /opt/energy-reglaments-bot/openclaw-workspace && \
  chmod 777 /opt/energy-reglaments-bot/files"

echo "--- Copying openclaw workspace ---"
scp -r openclaw-workspace/workspace/* "$VPS":/opt/energy-reglaments-bot/openclaw-workspace/workspace/

echo "--- Copying compose file ---"
scp docker-compose.swarm.yml "$VPS":/opt/energy-reglaments-bot/

echo "=== VPS initialized. Now run CI/CD to deploy ==="
