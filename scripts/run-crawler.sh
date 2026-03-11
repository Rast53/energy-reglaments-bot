#!/bin/bash
set -e
echo "=== Running crawler ==="

if [ ! -f .env ]; then
  echo "ERROR: .env not found"
  echo "FIX: cp .env.example .env && fill values"
  echo "SECRETS: cat /root/.openclaw/credentials/energy-reglaments-bot.env"
  exit 1
fi

source .env

echo "--- Checking DB connection ---"
python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
print('DB: OK')
conn.close()
" || { echo "ERROR: DB not reachable. FIX: check DATABASE_URL and postgres service"; exit 1; }

echo "--- Running crawler ---"
python3 -m crawler.main 2>&1 | tee /tmp/crawler.log
echo "=== LAST 30 LINES ==="
tail -n 30 /tmp/crawler.log
echo "=== CRAWLER DONE ==="
