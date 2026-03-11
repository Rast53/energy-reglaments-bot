# Context: TASK-3 — Bot

## Project
energy-reglaments-bot — Telegram bot для ответов на вопросы по регламентам ОРЭМ.

## Stack
- Python 3.12, aiogram 3.x
- openai client — embeddings (text-embedding-3-large через OpenRouter)
- qdrant-client — async semantic search
- httpx — async HTTP для OpenClaw
- psycopg2 / asyncpg — PostgreSQL для /versions команды

## Архитектура бота (sink)
Каждый handler обрабатывает сообщение, отвечает, завершает. Никаких цепочек.

## Поток обработки вопроса
```
1. detect_mode(text) → "current" | "future" | "both"
2. embed(text) → vector (text-embedding-3-large через OpenRouter)
3. qdrant.search(vector, filter=mode_filter, limit=5) → chunks
4. build_context(chunks) → форматированный текст с метаданными
5. POST http://openclaw:18789/v1/chat/completions → JSON ответ
   headers: Authorization: Bearer $OPENCLAW_API_KEY
   body: {messages: [{role:"system", content: SYSTEM_PROMPT}, {role:"user", content: question}]}
   SYSTEM_PROMPT содержит [CONTEXT] с chunks
6. parse_json(response.choices[0].message.content) →
   {answer, sources, confidence, has_future_changes, future_changes_summary}
7. validate_sources(sources, chunks) — проверить что каждый source.doc_id+section есть в chunks
   если нет → confidence = "low"
8. format_answer(result) → Telegram markdown
9. Если confidence="low" → добавить дисклеймер
```

## Детектор режима
```python
FUTURE_KEYWORDS = [
    "будущ", "изменени", "вступ", "с 1", "с 01",
    "планируется", "предстоящ", "новая редакция",
    "когда изменится", "что изменится", "следующ редакц",
]

def detect_mode(text: str) -> str:
    text_lower = text.lower()
    has_future = any(kw in text_lower for kw in FUTURE_KEYWORDS)
    # если вопрос про "текущ" + "будущ" одновременно → "both"
    # если только будущ → "future"
    # иначе → "current"
```

## Qdrant фильтры
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

# current
Filter(must=[FieldCondition(key="is_current", match=MatchValue(value=True))])

# future
Filter(must=[FieldCondition(key="status", match=MatchValue(value="future"))])

# both
Filter(must=[FieldCondition(key="status", match=MatchAny(any=["current", "future"]))])
```

## Системный промпт для OpenClaw
```
Ты эксперт по регламентам ОРЭМ (Оптовый рынок электроэнергии и мощности).
Отвечай ТОЛЬКО на основе предоставленных выдержек. Не придумывай информацию.
Всегда указывай: название документа, редакция от [дата], пункт [N].

[CONTEXT]
{formatted_chunks}

Верни ответ строго в JSON (без markdown-оборачивания):
{{
  "answer": "текст ответа",
  "sources": [{{"doc_title": "...", "version_date": "...", "section": "...", "status": "current"}}],
  "confidence": "high|medium|low",
  "has_future_changes": false,
  "future_changes_summary": ""
}}
```

## Формат ответа пользователю (Telegram HTML)
```
📋 <b>Ответ</b>

{answer}

📌 <b>Источники:</b>
• {doc_title}, ред. {version_date}, п. {section}

⏰ <b>Будущие изменения (с {date}):</b>
{future_changes_summary}

⚠️ <i>Низкая уверенность. Рекомендую проверить на <a href="https://np-sr.ru">np-sr.ru</a></i>
```

## Команды бота
- /start — приветствие + инструкция
- /help — примеры вопросов
- /versions [номер приложения] — список версий (current, future, archive с датами)
- /update — (только ADMIN_IDS) уведомление что краулер будет запущен (реальный запуск через docker exec)

## Файловая структура bot/
```
bot/
├── __init__.py
├── main.py          ← точка входа (python -m bot.main)
├── handlers/
│   ├── __init__.py
│   ├── start.py     ← /start, /help
│   ├── question.py  ← текстовые вопросы (основной handler)
│   └── versions.py  ← /versions команда
├── services/
│   ├── __init__.py
│   ├── search.py    ← embed + qdrant search
│   ├── openclaw.py  ← POST /v1/chat/completions
│   └── validator.py ← validate_sources, detect_mode
├── utils/
│   ├── __init__.py
│   └── formatting.py ← format_answer для Telegram HTML
├── requirements.txt
└── Dockerfile
```

## Environment variables
- BOT_TOKEN
- OPENROUTER_API_KEY
- OPENCLAW_URL (default: http://openclaw:18789)
- OPENCLAW_API_KEY
- QDRANT_URL (default: http://qdrant:6333)
- QDRANT_COLLECTION (default: reglaments)
- EMBEDDING_MODEL (default: openai/text-embedding-3-large)
- ADMIN_IDS (comma-separated user IDs, e.g. "125525685")
- LOG_LEVEL (default: INFO)

## Важно
- Все handlers async
- Логирование через logging (НЕ print)
- Telegram parse_mode="HTML"
- При любой ошибке → вежливое сообщение пользователю, лог ERROR
- Не падать при JSON parse error от OpenClaw — fallback на текстовый ответ
