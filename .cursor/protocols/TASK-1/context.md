# Context: TASK-1 — Crawler

## Project
energy-reglaments-bot — Telegram bot для ответов на вопросы по регламентам ОРЭМ.
Репо: https://github.com/Rast53/energy-reglaments-bot

## Stack
- Python 3.12
- requests + BeautifulSoup4 (HTML парсинг)
- psycopg2 / asyncpg (PostgreSQL)
- Docker (контейнер crawler)

## Целевой сайт
- Base URL: https://www.np-sr.ru
- Индексная страница: /ru/regulation/joining/reglaments/index.htm
- Страница регламента: /ru/regulation/joining/reglaments/{id} (71 регламент, IDs: 1956-3445)
- ВАЖНО: verify=False во всех requests (сломанный SSL сертификат)
- ВАЖНО: User-Agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
- Задержка 2 сек между запросами

## Структура страницы регламента (проверено вручную)
На странице /reglaments/all/1956 видно:
- Список версий с "Дата вступления в силу: DD.MM.YYYY"
- Для каждой версии: DOCX ссылка, PDF ссылка, "Таблицы изменений" ссылка
- Версии идут от новых к старым

## Статус версии (логика)
- future:  valid_from > today
- current: valid_from <= today AND (нет следующей ИЛИ следующая.valid_from > today)
- archive: всё остальное

## PostgreSQL схема
```sql
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(50) UNIQUE NOT NULL,  -- напр. "appendix_1"
    title TEXT NOT NULL,
    appendix_num VARCHAR(20),            -- напр. "1", "1.1", "11.1.1"
    source_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_versions (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(50) NOT NULL REFERENCES documents(doc_id),
    version_date DATE NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('current','future','archive')),
    valid_from DATE NOT NULL,
    valid_until DATE,
    ns_date DATE,
    pdf_url TEXT,
    docx_url TEXT,
    changes_url TEXT,
    file_path TEXT,
    file_hash VARCHAR(64),
    indexed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(doc_id, valid_from)
);

CREATE TABLE IF NOT EXISTS crawler_log (
    id SERIAL PRIMARY KEY,
    run_at TIMESTAMP DEFAULT NOW(),
    docs_checked INTEGER DEFAULT 0,
    docs_updated INTEGER DEFAULT 0,
    errors TEXT,
    duration_ms INTEGER
);
```

## Файловая структура crawler/
```
crawler/
├── __init__.py
├── main.py          ← точка входа (python -m crawler.main)
├── db.py            ← PostgreSQL: init_db(), get_connection()
├── scraper.py       ← парсинг np-sr.ru (список регламентов + версии)
├── downloader.py    ← скачивание PDF с SHA256 dedup
├── models.py        ← dataclasses: Document, DocumentVersion
├── requirements.txt
└── Dockerfile
```

## Environment variables
- DATABASE_URL — postgresql://user:pass@host:5432/db
- CRAWLER_VERIFY_SSL — "false"
- CRAWLER_BASE_URL — "https://www.np-sr.ru"
- CRAWLER_DELAY_SEC — "2"

## Важные детали
- Логирование через logging (НЕ print)
- Идемпотентность: SHA256 → не скачивать если уже есть
- При ошибке скачивания одного документа — продолжить остальные (не падать)
- files/ папка для PDF (volume mount в Docker)
