#!/bin/bash
STACK="energy-reglaments-bot"
SERVICE=${1:-bot}
LINES=${2:-50}
echo "=== Logs: ${STACK}_${SERVICE} (last $LINES) ==="
docker service logs "${STACK}_${SERVICE}" --tail "$LINES" --no-task-ids 2>&1
