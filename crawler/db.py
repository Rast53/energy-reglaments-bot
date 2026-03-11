from __future__ import annotations

import logging
import os

import psycopg2
from psycopg2.extensions import connection as PgConnection

from crawler.models import Document, DocumentVersion

logger = logging.getLogger(__name__)

SQL_CREATE_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(50) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    appendix_num VARCHAR(20),
    source_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

SQL_CREATE_VERSIONS = """
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
"""

SQL_CREATE_CRAWLER_LOG = """
CREATE TABLE IF NOT EXISTS crawler_log (
    id SERIAL PRIMARY KEY,
    run_at TIMESTAMP DEFAULT NOW(),
    docs_checked INTEGER DEFAULT 0,
    docs_updated INTEGER DEFAULT 0,
    errors TEXT,
    duration_ms INTEGER
);
"""


def get_connection() -> PgConnection:
    database_url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    return conn


def init_db(conn: PgConnection) -> None:
    with conn.cursor() as cur:
        cur.execute(SQL_CREATE_DOCUMENTS)
        cur.execute(SQL_CREATE_VERSIONS)
        cur.execute(SQL_CREATE_CRAWLER_LOG)
    logger.info("Database tables initialized")


def upsert_document(conn: PgConnection, doc: Document) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (doc_id, title, appendix_num, source_url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (doc_id) DO UPDATE SET
                title = EXCLUDED.title,
                appendix_num = EXCLUDED.appendix_num,
                source_url = EXCLUDED.source_url
            """,
            (doc.doc_id, doc.title, doc.appendix_num, doc.source_url),
        )


def upsert_version(conn: PgConnection, version: DocumentVersion) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO document_versions
                (doc_id, version_date, status, valid_from, valid_until,
                 ns_date, pdf_url, docx_url, changes_url, file_path, file_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (doc_id, valid_from) DO UPDATE SET
                version_date = EXCLUDED.version_date,
                status = EXCLUDED.status,
                valid_until = EXCLUDED.valid_until,
                ns_date = EXCLUDED.ns_date,
                pdf_url = EXCLUDED.pdf_url,
                docx_url = EXCLUDED.docx_url,
                changes_url = EXCLUDED.changes_url,
                file_path = COALESCE(
                    document_versions.file_path, EXCLUDED.file_path
                ),
                file_hash = COALESCE(
                    document_versions.file_hash, EXCLUDED.file_hash
                )
            """,
            (
                version.doc_id,
                version.version_date,
                version.status,
                version.valid_from,
                version.valid_until,
                version.ns_date,
                version.pdf_url,
                version.docx_url,
                version.changes_url,
                version.file_path,
                version.file_hash,
            ),
        )


def update_version_file(
    conn: PgConnection, doc_id: str, valid_from: str, file_path: str, file_hash: str
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE document_versions
            SET file_path = %s, file_hash = %s
            WHERE doc_id = %s AND valid_from = %s
            """,
            (file_path, file_hash, doc_id, valid_from),
        )


def get_existing_hashes(conn: PgConnection, doc_id: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT file_hash FROM document_versions WHERE doc_id = %s AND file_hash IS NOT NULL",
            (doc_id,),
        )
        return {row[0] for row in cur.fetchall()}


def version_has_file(conn: PgConnection, doc_id: str, valid_from: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT file_hash FROM document_versions
            WHERE doc_id = %s AND valid_from = %s AND file_hash IS NOT NULL
            """,
            (doc_id, valid_from),
        )
        return cur.fetchone() is not None


def log_run(
    conn: PgConnection,
    docs_checked: int,
    docs_updated: int,
    errors: str | None,
    duration_ms: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO crawler_log (docs_checked, docs_updated, errors, duration_ms)
            VALUES (%s, %s, %s, %s)
            """,
            (docs_checked, docs_updated, errors, duration_ms),
        )
    logger.info(
        "Crawler run logged: checked=%d, updated=%d, duration=%dms",
        docs_checked,
        docs_updated,
        duration_ms,
    )
