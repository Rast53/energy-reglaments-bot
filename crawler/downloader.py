from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import requests
import urllib3

from crawler.models import DocumentVersion

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

CHUNK_SIZE = 8192


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def download_pdf(
    version: DocumentVersion,
    files_dir: Path,
    existing_hashes: set[str],
    verify_ssl: bool = False,
) -> tuple[str, str] | None:
    """Download PDF for a version. Returns (file_path, file_hash) or None if skipped."""
    if not version.pdf_url:
        logger.debug("No PDF URL for %s/%s", version.doc_id, version.valid_from)
        return None

    doc_dir = files_dir / version.doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{version.valid_from}.pdf"
    file_path = doc_dir / filename

    if file_path.exists():
        file_hash = _sha256(file_path)
        if file_hash in existing_hashes:
            logger.debug(
                "File already exists: %s (hash: %s...)", file_path, file_hash[:12]
            )
            return str(file_path), file_hash

    try:
        logger.info("Downloading PDF: %s → %s", version.pdf_url, file_path)
        resp = requests.get(
            version.pdf_url, headers=HEADERS, verify=verify_ssl, timeout=60, stream=True
        )
        resp.raise_for_status()

        tmp_path = file_path.with_suffix(".tmp")
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)

        file_hash = _sha256(tmp_path)

        if file_hash in existing_hashes:
            tmp_path.unlink()
            logger.info(
                "Duplicate hash detected, skipping: %s (hash: %s...)",
                version.pdf_url,
                file_hash[:12],
            )
            return None

        tmp_path.rename(file_path)
        logger.info("Downloaded: %s (hash: %s...)", file_path, file_hash[:12])
        return str(file_path), file_hash

    except requests.RequestException:
        logger.exception("Failed to download %s", version.pdf_url)
        return None
