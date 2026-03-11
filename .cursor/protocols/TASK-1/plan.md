# Plan: TASK-1 — Crawler

## Steps

### Step 1: crawler/models.py
Dataclasses: Document, DocumentVersion со всеми полями из схемы БД.

### Step 2: crawler/db.py
- `init_db(conn)` — создаёт таблицы (CREATE TABLE IF NOT EXISTS)
- `get_connection()` — psycopg2 connect из DATABASE_URL
- `upsert_document(conn, doc: Document)`
- `upsert_version(conn, version: DocumentVersion)`
- `get_existing_hashes(conn, doc_id) -> set[str]`
- `set_indexed_null_check(conn)` — ничего не делает (indexed_at ставит indexer)
- `log_run(conn, docs_checked, docs_updated, errors, duration_ms)`

### Step 3: crawler/scraper.py
- `fetch_doc_list(base_url) -> list[Document]`
  Парсит /ru/regulation/joining/reglaments/index.htm
  Возвращает список регламентов с title и source_url
- `fetch_versions(doc: Document, base_url) -> list[DocumentVersion]`
  Парсит страницу регламента, извлекает все версии
  Определяет статус (current/future/archive) по датам
- `_parse_date(text: str) -> date | None`
  Парсит "DD.MM.YYYY" из текста

### Step 4: crawler/downloader.py
- `download_pdf(version: DocumentVersion, files_dir: Path) -> tuple[Path, str]`
  Скачивает PDF, считает SHA256, сохраняет в files/{doc_id}/{valid_from}.pdf
  Возвращает (file_path, file_hash)
- `file_exists(file_hash: str, files_dir: Path) -> Path | None`
  Проверяет по хэшу

### Step 5: crawler/main.py
Основной цикл:
1. Подключиться к БД, init_db()
2. fetch_doc_list() → 71 регламент
3. Для каждого: upsert_document()
4. Для каждого: fetch_versions()
5. Для каждой версии:
   - upsert_version() (статус, даты)
   - Если pdf_url и нет file_hash → download_pdf()
   - Обновить file_path, file_hash в БД
6. log_run()

### Step 6: crawler/requirements.txt + Dockerfile
requirements.txt: requests, beautifulsoup4, psycopg2-binary, python-dateutil
Dockerfile: python:3.12-slim, WORKDIR /app, COPY, pip install, CMD

### Step 7: Проверка check.sh
ruff check crawler/ && mypy crawler/ --ignore-missing-imports

## Acceptance Criteria
- [ ] python -m crawler.main запускается без ошибок
- [ ] PostgreSQL заполнен документами и версиями с корректными статусами
- [ ] files/ содержит скачанные PDF
- [ ] Повторный запуск: "already exists, skipping"
- [ ] ./scripts/check.sh проходит (ruff + mypy)
