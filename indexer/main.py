from __future__ import annotations

import logging
import os
import sys
import time

from indexer.chunker import pdf_to_chunks
from indexer.db import get_connection, get_unindexed_versions, mark_indexed
from indexer.embedder import embed_chunks
from indexer.qdrant_client_helper import (
    ensure_collection,
    get_qdrant_client,
    upsert_points,
)

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def main() -> None:
    setup_logging()
    logger.info("Indexer started")

    api_key = os.environ["OPENROUTER_API_KEY"]
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    collection_name = os.environ.get("QDRANT_COLLECTION", "reglaments")
    vector_size = int(os.environ.get("QDRANT_VECTOR_SIZE", "3072"))
    embedding_model = os.environ.get("EMBEDDING_MODEL", "openai/text-embedding-3-large")

    start_ms = int(time.time() * 1000)
    total_chunks = 0
    indexed_count = 0
    errors: list[str] = []

    conn = get_connection()
    qdrant = get_qdrant_client(qdrant_url)

    try:
        ensure_collection(qdrant, collection_name, vector_size)

        versions = get_unindexed_versions(conn)
        logger.info("Found %d unindexed versions", len(versions))

        if not versions:
            logger.info("Nothing to index, exiting")
            return

        for version in versions:
            doc_id = version["doc_id"]
            valid_from = str(version["valid_from"])
            file_path = version["file_path"]

            try:
                chunks = pdf_to_chunks(file_path, version)
                if not chunks:
                    logger.warning(
                        "No chunks produced for %s (%s)", doc_id, valid_from,
                    )
                    continue

                vectors = embed_chunks(chunks, api_key, embedding_model)

                upsert_points(qdrant, collection_name, chunks, vectors)

                mark_indexed(conn, version["id"])
                indexed_count += 1
                total_chunks += len(chunks)

                logger.info(
                    "Indexed %s %s: %d chunks",
                    doc_id, valid_from, len(chunks),
                )

            except Exception:
                error_msg = f"Error indexing {doc_id} ({valid_from}): {file_path}"
                logger.exception(error_msg)
                errors.append(error_msg)

        duration_ms = int(time.time() * 1000) - start_ms
        logger.info(
            "Indexer finished: indexed=%d versions, %d chunks, errors=%d, duration=%dms",
            indexed_count,
            total_chunks,
            len(errors),
            duration_ms,
        )

        if errors:
            logger.warning("Errors:\n%s", "\n".join(errors))

    finally:
        conn.close()


if __name__ == "__main__":
    main()
