# Plan: Issue #10 — Production bugs fix

## Steps

### Step 1: indexer/embedder.py
- Убрать `from openai import OpenAI` и `_create_client`
- Заменить на httpx.Client
- Модель по умолчанию: `intfloat/multilingual-e5-large`
- Убрать `BATCH_SIZE` до 5 (было 20)

### Step 2: bot/services/search.py
- Убрать `from openai import AsyncOpenAI` и `_create_openai_client`
- Заменить `embed_text` на async httpx запрос
- Модель по умолчанию: `intfloat/multilingual-e5-large`

### Step 3: bot/services/openclaw.py
- Убрать обращение к openclaw sidecar
- Использовать `https://openrouter.ai/api/v1/chat/completions` напрямую
- Брать ключ из `OPENROUTER_API_KEY` (не `OPENCLAW_API_KEY`)
- Модель из env `LLM_MODEL` (default: `google/gemini-2.0-flash-001`)
- Robust JSON парсер: strip markdown block + find("{") / rfind("}")

### Step 4: docker-compose.yml
- Добавить volume `energy-files-data` (named volume)
- В сервис `bot`: добавить `EMBEDDING_MODEL=${EMBEDDING_MODEL:-intfloat/multilingual-e5-large}`
- В сервис `bot`: добавить `LLM_MODEL=${LLM_MODEL:-google/gemini-2.0-flash-001}`
- В сервис `bot`: добавить `QDRANT_COLLECTION=${QDRANT_COLLECTION:-reglaments}`
- Crawler и indexer при запуске через run-* скрипты должны монтировать этот volume

### Step 5: .env.example
- Добавить `EMBEDDING_MODEL=intfloat/multilingual-e5-large`
- Добавить `QDRANT_VECTOR_SIZE=1024`
- Добавить `CRAWLER_FILES_DIR=/app/files`
- Добавить `LLM_MODEL=google/gemini-2.0-flash-001`

### Step 6: indexer/chunker.py — doc_title fix
- Найти где устанавливается `doc_title` в payload
- Вместо заголовка страницы использовать `doc_id` и `doc_title` из БД (передаётся через `version` объект)
- Убедиться что `version.doc_title` или аналог попадает в chunk payload

## Verification
- `grep -r "AsyncOpenAI\|from openai" bot/ indexer/` — должен быть пустой
- `grep -r "openclaw:18789\|OPENCLAW_URL" bot/` — должен быть пустой
- `grep "EMBEDDING_MODEL" docker-compose.yml` — должно быть
- `grep "energy-files-data" docker-compose.yml` — должно быть
