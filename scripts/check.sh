#!/bin/bash
set -e
echo "=== energy-reglaments-bot check ==="

# Pre-flight
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found"
  echo "FIX: install python3.12"
  exit 1
fi

if [ ! -f .env ] && [ "$CI" != "true" ]; then
  echo "WARN: .env not found (ok in CI)"
fi

echo "--- ruff lint ---"
python3 -m ruff check crawler/ indexer/ bot/ || { echo "ERROR: ruff failed. FIX: ruff check --fix"; exit 1; }

echo "--- mypy typecheck ---"
python3 -m mypy crawler/ indexer/ bot/ --ignore-missing-imports || { echo "ERROR: mypy failed"; exit 1; }

echo "=== ALL CHECKS PASSED ==="
