#!/bin/bash
STACK="energy-reglaments-bot"
echo "=== Health check: $STACK ==="

check_service() {
  local svc=$1
  local replicas
  replicas=$(docker service ls --filter "name=${STACK}_${svc}" --format "{{.Replicas}}" 2>/dev/null)
  if echo "$replicas" | grep -q "^[1-9]"; then
    echo "✅ $svc: $replicas"
  else
    echo "❌ $svc: $replicas"
    return 1
  fi
}

check_service bot
check_service openclaw
check_service qdrant
check_service postgres
check_service crawler

echo "=== HEALTH DONE ==="
