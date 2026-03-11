# Context: TASK-2 — Indexer

## Project
energy-reglaments-bot — RAG бот по регламентам ОРЭМ.

## Stack
- Python 3.12, type hints everywhere
- pymupdf4llm — PDF → Markdown
- openai Python client (embeddings через OpenRouter, base_url=https://openrouter.ai/api/v1)
- qdrant-client — upsert в Qdrant
- psycopg2 — чтение из PostgreSQL (indexed_at IS NULL)

## Что делает Indexer
Читает незаиндексированные PDF из PostgreSQL → парсит → чанкует → делает embeddings → заливает в Qdrant.

## Embeddings
- Провайдер: OpenRouter
- Модель: openai/text-embedding-3-large
- Размерность: 3072
- API: POST https://openrouter.ai/api/v1/embeddings
  headers: Authorization: Bearer $OPENROUTER_API_KEY
  body: {"model": "openai/text-embedding-3-large", "input": ["text..."]}
- Использовать openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

## Qdrant
- URL: $QDRANT_URL (default http://qdrant:6333)
- Коллекция: reglaments (создать если не существует)
- Размерность вектора: 3072
- Distance: COSINE
- Индексированные payload поля: is_current, status, doc_id, valid_from

## Чанкинг (структурный по номерам разделов)
Regex для обнаружения начала раздела: r"^(\d+(?:\.\d+)*)\s+\S"  (напр. "1.1 Термины", "5.2.1 Порядок")
- Каждый чанк = один раздел (номер + заголовок + текст)
- Если чанк < 50 токенов → склеить с соседним
- Если чанк > 400 токенов → разбить по абзацам, каждый sub-chunk содержит prefix с номером раздела
- Приближённый подсчёт токенов: len(text.split()) * 1.3

## Payload каждого чанка в Qdrant
```python
{
    "doc_id": "appendix_1",
    "doc_title": "Приложение 1. Регламент допуска...",
    "appendix_num": "1",
    "version_id": "2025-03-15",        # str(valid_from)
    "valid_from": "2025-03-15",        # str
    "valid_until": "2025-06-30",       # str или None
    "status": "current",               # current / future / archive
    "is_current": True,                # bool
    "is_changes_table": False,         # True для "Таблицы изменений"
    "section": "4.1",
    "section_title": "Порядок подачи заявок",
    "text": "...",
    "chunk_index": 0,
    "source_url": "https://np-sr.ru/...",
    "file_hash": "sha256:abc...",
}
```

## Point ID в Qdrant
UUID генерировать из doc_id + version_date + chunk_index:
```python
import hashlib, uuid
point_id = str(uuid.UUID(hashlib.md5(f"{doc_id}:{version_date}:{chunk_index}".encode()).hexdigest()))
```

## Файловая структура indexer/
```
indexer/
├── __init__.py
├── main.py          ← точка входа (python -m indexer.main)
├── db.py            ← чтение из PostgreSQL: get_unindexed_versions(), mark_indexed()
├── chunker.py       ← PDF → Markdown → chunks
├── embedder.py      ← text → vectors (OpenRouter API)
├── qdrant_client_helper.py  ← create_collection_if_needed(), upsert_points()
├── models.py        ← Chunk dataclass
├── requirements.txt
└── Dockerfile
```

## Environment variables
- DATABASE_URL
- OPENROUTER_API_KEY
- QDRANT_URL (default: http://qdrant:6333)
- QDRANT_COLLECTION (default: reglaments)
- QDRANT_VECTOR_SIZE (default: 3072)
- EMBEDDING_MODEL (default: openai/text-embedding-3-large)
- LOG_LEVEL (default: INFO)

## Важно
- Логирование через logging (НЕ print)
- Батчинг embeddings: по 20 чанков за раз (OpenRouter лимиты)
- При ошибке одного документа — продолжить остальные
- files/ папка с PDF читается из пути file_path в document_versions
