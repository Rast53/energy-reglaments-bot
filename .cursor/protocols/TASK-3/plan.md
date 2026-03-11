# Plan: TASK-3 — Bot

## Steps

### Step 1: bot/services/validator.py
- `detect_mode(text: str) -> str` — "current" | "future" | "both"
- `validate_sources(sources: list[dict], chunks: list) -> bool`
  Каждый source должен иметь doc_id+section среди chunk.payload

### Step 2: bot/services/search.py
- `embed_text(text: str, api_key: str, model: str) -> list[float]`
  openai.OpenAI(base_url="https://openrouter.ai/api/v1") → embeddings
- `search_qdrant(vector, mode: str, client, collection: str, limit=5) -> list`
  Фильтры по mode (current/future/both), возвращает scored points

### Step 3: bot/services/openclaw.py
- `ask_openclaw(question: str, chunks: list, url: str, api_key: str) -> dict`
  Строит system prompt с [CONTEXT] (форматированные chunks)
  POST /v1/chat/completions
  Парсит JSON из ответа, fallback если не JSON

### Step 4: bot/utils/formatting.py
- `format_chunks_for_prompt(chunks: list) -> str`
  Форматирует chunks в читаемый контекст для промпта
- `format_answer(result: dict) -> str`
  Telegram HTML: answer + sources + future_changes + disclaimer если low

### Step 5: bot/handlers/start.py
- `/start` — приветствие с описанием бота и примерами
- `/help` — примеры вопросов по ОРЭМ

### Step 6: bot/handlers/question.py
- Обработчик текстовых сообщений (не команд)
- Полный pipeline: detect_mode → embed → search → openclaw → validate → format → reply
- Typing action во время обработки
- Error handling: любая ошибка → "Произошла ошибка, попробуйте позже"

### Step 7: bot/handlers/versions.py
- `/versions [N]` — запрос к PostgreSQL, список версий регламента N
- Если N не указан → попросить уточнить
- Вывод: current/future/archive с датами

### Step 8: bot/main.py
- Инициализация: Bot, Dispatcher, QdrantClient, aiogram router
- Регистрация handlers
- `asyncio.run(main())`

### Step 9: requirements.txt + Dockerfile
requirements.txt: aiogram>=3.0, openai>=1.0, qdrant-client, httpx, psycopg2-binary
Dockerfile: python:3.12-slim

### Step 10: ruff passes
ruff check bot/

## Acceptance Criteria
- [ ] /start отвечает
- [ ] Текстовый вопрос → ответ с источниками
- [ ] confidence=low → дисклеймер ⚠️
- [ ] /versions N → список редакций
- [ ] ruff: All checks passed
