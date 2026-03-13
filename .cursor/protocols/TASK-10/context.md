# Context: Issue #10

## Стек
- Python 3.12, aiogram 3, Qdrant, PostgreSQL, Docker Compose
- OpenRouter для embeddings и LLM
- Деплой на vps-tw-server через ghcr.io images

## Текущее состояние (хотфиксы через docker cp — НЕ в коде)
Все фиксы применены вручную, но при следующем деплое откатятся.

## Фиксированные файлы (рабочие версии через docker cp):
- `bot/services/search.py` — httpx вместо openai SDK
- `bot/services/openclaw.py` — OpenRouter напрямую + robust JSON парсер
- `docker-compose.yml` — добавлен EMBEDDING_MODEL в env бота

## Что НЕ изменено в коде (нужно сделать):
- `indexer/embedder.py` — всё ещё openai SDK
- `bot/services/search.py` — всё ещё openai SDK в репо
- `bot/services/openclaw.py` — всё ещё openclaw sidecar в репо
- `docker-compose.yml` — нет volume energy-files-data, нет EMBEDDING_MODEL
- `.env.example` — нет новых переменных
- `indexer/chunker.py` — doc_title = "Подробнее" (мусорный заголовок из PDF)

## Рабочая модель embeddings
- `intfloat/multilingual-e5-large` (dim=1024)
- НЕ `openai/text-embedding-3-large` (недоступна на OpenRouter)

## Почему openai SDK не работает с OpenRouter для embeddings
OpenAI Python SDK автоматически добавляет `encoding_format: base64`.
OpenRouter возвращает 200 OK но {"error": "No successful provider responses"}.
Решение: httpx напрямую.

## Почему openclaw sidecar не работает как LLM backend
OpenClaw gateway слушает только 127.0.0.1:18789 — недоступен из других контейнеров.
Решение: использовать OpenRouter chat/completions напрямую.
