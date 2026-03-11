from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from crawler.db import (
    get_connection,
    get_existing_hashes,
    init_db,
    log_run,
    update_version_file,
    upsert_document,
    upsert_version,
    version_has_file,
)
from crawler.downloader import download_pdf
from crawler.scraper import fetch_doc_list, fetch_versions

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
    logger.info("Crawler started")

    base_url = os.environ.get("CRAWLER_BASE_URL", "https://www.np-sr.ru")
    delay_sec = float(os.environ.get("CRAWLER_DELAY_SEC", "2"))
    verify_ssl = os.environ.get("CRAWLER_VERIFY_SSL", "false").lower() == "true"
    files_dir = Path(os.environ.get("CRAWLER_FILES_DIR", "files"))
    files_dir.mkdir(parents=True, exist_ok=True)

    start_ms = int(time.time() * 1000)
    docs_checked = 0
    docs_updated = 0
    errors: list[str] = []

    conn = get_connection()
    try:
        init_db(conn)

        documents = fetch_doc_list(base_url, delay_sec)
        logger.info("Processing %d documents", len(documents))

        for doc in documents:
            docs_checked += 1
            try:
                upsert_document(conn, doc)

                versions = fetch_versions(doc, base_url, delay_sec)
                if not versions:
                    logger.warning("No versions found for %s", doc.doc_id)
                    continue

                existing_hashes = get_existing_hashes(conn, doc.doc_id)

                for version in versions:
                    upsert_version(conn, version)

                    if version.pdf_url and not version_has_file(
                        conn, doc.doc_id, str(version.valid_from)
                    ):
                        result = download_pdf(
                            version, files_dir, existing_hashes, verify_ssl
                        )
                        if result:
                            file_path, file_hash = result
                            update_version_file(
                                conn,
                                doc.doc_id,
                                str(version.valid_from),
                                file_path,
                                file_hash,
                            )
                            existing_hashes.add(file_hash)
                            docs_updated += 1
                            time.sleep(delay_sec)

            except Exception:
                error_msg = f"Error processing {doc.doc_id}: {doc.source_url}"
                logger.exception(error_msg)
                errors.append(error_msg)

        duration_ms = int(time.time() * 1000) - start_ms
        errors_text = "\n".join(errors) if errors else None
        log_run(conn, docs_checked, docs_updated, errors_text, duration_ms)

        logger.info(
            "Crawler finished: checked=%d, updated=%d, errors=%d, duration=%dms",
            docs_checked,
            docs_updated,
            len(errors),
            duration_ms,
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
