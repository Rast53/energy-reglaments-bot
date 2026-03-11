# Plan: TASK-2 — Indexer

## Steps

### Step 1: indexer/models.py
Dataclass Chunk: doc_id, doc_title, appendix_num, version_id, valid_from, valid_until,
status, is_current, is_changes_table, section, section_title, text, chunk_index,
source_url, file_hash, point_id (str UUID).

### Step 2: indexer/db.py
- `get_connection()` — psycopg2 из DATABASE_URL
- `get_unindexed_versions(conn) -> list[dict]`
  SELECT * FROM document_versions v JOIN documents d ON v.doc_id=d.doc_id
  WHERE v.indexed_at IS NULL AND v.file_path IS NOT NULL
- `mark_indexed(conn, version_id: int)` — UPDATE indexed_at = NOW()

### Step 3: indexer/chunker.py
- `pdf_to_chunks(file_path: str, version_meta: dict) -> list[Chunk]`
  1. pymupdf4llm.to_markdown(file_path) → md_text
  2. split_into_sections(md_text) → list[(section_num, section_title, text)]
     regex: r"^(\d+(?:\.\d+)*)\s+(.{0,80})" на начало строки
  3. Для каждого раздела: size_check → merge если < 50 токенов, split если > 400
  4. Создать Chunk объекты с point_id (md5 UUID)

### Step 4: indexer/embedder.py
- `embed_chunks(chunks: list[Chunk], api_key: str, model: str) -> list[list[float]]`
  Батчи по 20. openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
  client.embeddings.create(model=model, input=[c.text for c in batch])
  Возвращает список векторов (порядок совпадает с входом)

### Step 5: indexer/qdrant_client_helper.py
- `get_qdrant_client(url: str) -> QdrantClient`
- `ensure_collection(client, name: str, vector_size: int)`
  Создаёт коллекцию с Distance.COSINE если не существует.
  Создаёт payload индексы: is_current (bool), status (keyword), doc_id (keyword), valid_from (keyword)
- `upsert_points(client, collection: str, chunks: list[Chunk], vectors: list[list[float]])`
  PointStruct(id=chunk.point_id, vector=vector, payload=chunk_to_payload(chunk))

### Step 6: indexer/main.py
Основной цикл:
1. Подключиться к БД, Qdrant
2. ensure_collection()
3. get_unindexed_versions() → список
4. Для каждой версии:
   a. pdf_to_chunks(file_path, meta)
   b. embed_chunks(chunks)
   c. upsert_points(chunks, vectors)
   d. mark_indexed(conn, version.id)
   e. Лог: "Indexed doc_id version_date: N chunks"
5. Итого: "Indexed X versions, Y chunks total"

### Step 7: requirements.txt + Dockerfile
requirements.txt: pymupdf4llm, openai>=1.0, qdrant-client, psycopg2-binary
Dockerfile: python:3.12-slim, WORKDIR /app

### Step 8: ./scripts/check.sh passes
ruff check indexer/ (All checks passed)

## Acceptance Criteria
- [ ] python -m indexer.main запускается без ошибок (с реальным Qdrant/PG или mock)
- [ ] Qdrant коллекция создаётся с правильными полями
- [ ] Чанки содержат корректные payload (is_current, status, section)
- [ ] mark_indexed обновляет indexed_at в PostgreSQL
- [ ] ruff: All checks passed
