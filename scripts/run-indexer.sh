#!/bin/bash
set -e
echo "=== Running indexer ==="

if [ ! -f .env ]; then
  echo "ERROR: .env not found"
  echo "FIX: cp .env.example .env && fill values"
  exit 1
fi

source .env

echo "--- Checking Qdrant ---"
curl -sf "${QDRANT_URL}/healthz" || { echo "ERROR: Qdrant not reachable at ${QDRANT_URL}"; exit 1; }
echo "Qdrant: OK"

echo "--- Running indexer ---"
python3 -m indexer.main 2>&1 | tee /tmp/indexer.log
echo "=== LAST 30 LINES ==="
tail -n 30 /tmp/indexer.log
echo "=== INDEXER DONE ==="
