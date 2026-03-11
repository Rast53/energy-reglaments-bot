from __future__ import annotations

import logging
import os

import psycopg2
from psycopg2.extensions import connection as PgConnection

logger = logging.getLogger(__name__)


def get_connection() -> PgConnection:
    database_url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    return conn


def get_unindexed_versions(conn: PgConnection) -> list[dict]:
    """Return document versions that have a file but haven't been indexed yet."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                v.id,
                v.doc_id,
                d.title       AS doc_title,
                d.appendix_num,
                d.source_url,
                v.version_date,
                v.status,
                v.valid_from,
                v.valid_until,
                v.file_path,
                v.file_hash
            FROM document_versions v
            JOIN documents d ON v.doc_id = d.doc_id
            WHERE v.indexed_at IS NULL
              AND v.file_path IS NOT NULL
            ORDER BY v.valid_from
            """,
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def mark_indexed(conn: PgConnection, version_id: int) -> None:
    """Set indexed_at = NOW() for a given document_versions row."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE document_versions SET indexed_at = NOW() WHERE id = %s",
            (version_id,),
        )
    logger.info("Marked version id=%d as indexed", version_id)
